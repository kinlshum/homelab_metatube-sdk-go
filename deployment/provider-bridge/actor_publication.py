"""Authenticated whole-table actor publication; independent of provider lookups.

Restores the Actor DB bridge contract in the shared SDK bridge build. A file
lock in the shared Emby mount serializes both bridge containers. Verification
here is disk verification, not proof that Emby's in-memory plugin has reloaded.
"""
import fcntl
import hashlib
import hmac
import json
import os
from pathlib import Path
import shutil
import tempfile
import time
import uuid
import xml.etree.ElementTree as ET


def paths():
    return {
        'ini': Path(os.getenv('ACTOR_SUB_INI_PATH','/emby-config/metadata/temp/JAV-ACTOR-SUB.ini')),
        'json': Path(os.getenv('METATUBE_CONFIG_PATH','/emby-config/plugins/configurations/MetaTube.json')),
        'xml': Path(os.getenv('METATUBE_XML_CONFIG_PATH','/emby-config/plugins/configurations/MetaTube.xml')),
    }


def digest(content):
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def validate(content):
    if not isinstance(content,str) or len(content.encode())>20*1024*1024:
        raise ValueError('Invalid substitution content size/type')
    aliases={}
    for line in content.splitlines():
        if not line.strip() or line.startswith(('#',';')):continue
        if '=' not in line or '\x00' in line:raise ValueError('Invalid INI mapping')
        alias,target=line.split('=',1)
        if not alias.strip():raise ValueError('Empty alias')
        if alias in aliases:raise ValueError('Duplicate INI alias')
        aliases[alias]=target
    if not aliases:raise ValueError('Empty substitution table')
    return len(aliases)


def xml_table(tree):
    node=next((n for n in tree.iter() if n.tag.rsplit('}',1)[-1]=='ActorRawSubstitutionTable'),None)
    if node is None:raise ValueError('XML actor table is missing')
    return node


def status():
    p=paths()
    ini=digest(p['ini'].read_text())
    cfg=json.loads(p['json'].read_text())
    j=digest(cfg.get('ActorRawSubstitutionTable') or '')
    x=digest(xml_table(ET.parse(p['xml'])).text or '')
    return {'status':'READY' if ini==j==x else 'OUT_OF_SYNC',
            'sha256':ini,'ini_sha256':ini,'metatube_sha256':j,'metatube_xml_sha256':x,
            'verification_scope':'files_only','actor_substitution_enabled':cfg.get('EnableActorSubstitution') is True}


def atomic_write(path,data):
    # Existing files are required: fail closed instead of creating fresh plugin
    # configuration or accidentally erasing unrelated plugin settings.
    stat=path.stat()
    fd,tmp=tempfile.mkstemp(prefix='.actor-publication-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:
            f.write(data);f.flush();os.fsync(f.fileno())
        os.chmod(tmp,stat.st_mode & 0o777)
        os.chown(tmp,stat.st_uid,stat.st_gid)
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)


def deploy(content,expected,git_revision=None):
    count=validate(content)
    if not hmac.compare_digest(digest(content),str(expected or '')):
        raise ValueError('Requested content SHA-256 mismatch')
    p=paths()
    with open(p['json'].parent/'.actor-publication.lock','a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        before=status()
        if all(before[k]==expected for k in ['ini_sha256','metatube_sha256','metatube_xml_sha256']):
            return {**before,'status':'UNCHANGED','entry_count':count,'git_revision':git_revision}
        cfg=json.loads(p['json'].read_text())
        tree=ET.parse(p['xml'])
        xml_table(tree).text=content
        cfg['ActorRawSubstitutionTable']=content
        backup_root=Path(os.getenv('SUBSTITUTION_BACKUP_DIR','/state/actor-substitution-backups'))
        backup=backup_root/(time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-'+uuid.uuid4().hex[:8])
        backup.mkdir(parents=True,mode=0o700)
        copies={}
        for key,path in p.items():
            copies[key]=backup/path.name
            shutil.copy2(path,copies[key]);os.chmod(copies[key],0o600)
        try:
            atomic_write(p['ini'],content.encode())
            atomic_write(p['json'],(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n').encode())
            atomic_write(p['xml'],ET.tostring(tree.getroot(),encoding='utf-8',xml_declaration=True))
            after=status()
            if any(after[k]!=expected for k in ['ini_sha256','metatube_sha256','metatube_xml_sha256']):
                raise RuntimeError('Post-deployment hash mismatch')
        except Exception:
            for key,path in p.items():atomic_write(path,copies[key].read_bytes())
            raise
        return {**after,'status':'DEPLOYED','entry_count':count,'git_revision':git_revision,
                'deployed_sha256':expected,'backup_directory':str(backup)}


def handle(handler):
    if handler.path not in ['/v1/actor-substitutions/status','/v1/actor-substitutions/deploy']:
        return False
    def reply(code,data):
        body=json.dumps(data,ensure_ascii=False).encode()
        handler.send_response(code);handler.send_header('Content-Type','application/json')
        handler.send_header('Content-Length',str(len(body)));handler.end_headers();handler.wfile.write(body)
    try:
        token=Path(os.getenv('BRIDGE_TOKEN_FILE','/run/secrets/bridge_token')).read_text().strip()
        if len(token)<32:raise ValueError('Bridge authentication is not configured')
        if not hmac.compare_digest(handler.headers.get('Authorization',''),'Bearer '+token):
            reply(401,{'error':'unauthorized'});return True
        if handler.command=='GET' and handler.path.endswith('/status'):
            reply(200,status())
        elif handler.command=='POST' and handler.path.endswith('/deploy'):
            length=int(handler.headers.get('Content-Length','0'))
            if length<=0 or length>21*1024*1024:raise ValueError('Invalid request size')
            data=json.loads(handler.rfile.read(length))
            reply(200,deploy(data.get('content'),data.get('sha256'),data.get('git_revision')))
        else:reply(405,{'error':'method not allowed'})
    except ValueError as e:reply(400,{'error':str(e)})
    except Exception:reply(500,{'error':'Actor publication failed; inspect bridge deployment and backups'})
    return True
