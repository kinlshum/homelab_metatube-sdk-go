"""Scoped Kraken resolver cutover. Preserve mounts/env/network and keep rollback.

Usage: python3 deploy-actor-resolver.py EXISTING_RELEASE_DIR EXPECTED_SOURCE_SHA
Release directory contains tested resolver.py, Dockerfile and overrides.json.
Never changes the mounted live overrides or actor data; only resolver cache may
subsequently be refreshed by ordinary requests.
"""
import hashlib
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

def docker(*args): return subprocess.check_output(['docker',*args],text=True).strip()
root=Path(sys.argv[1]); expected=sys.argv[2]
name='jav-actor-resolver'; image='kinlshum/jav-actor-resolver:actor-trace-20260930'
old=json.loads(docker('inspect',name))[0]
current=docker('exec',name,'sha256sum','/resolver.py').split()[0]
assert current==expected, 'Live source drift; stop before replacing'
assert len(old['NetworkSettings']['Networks'])==1
with open(root/'resolver-before.json','x') as f: json.dump(old,f)
(root/'resolver-before.json').chmod(0o600)
subprocess.run(['docker','build','-t',image,str(root)],check=True)
backup=name+'-before-actor-trace-20260930'
args=['run','-d','--name',name,'--restart','unless-stopped',
      '--network',next(iter(old['NetworkSettings']['Networks']))]
for env in old['Config']['Env']:args+=['-e',env]
for mount in old['Mounts']:
    assert mount['Type']=='bind'
    args+=['-v',mount['Source']+':'+mount['Destination']+('' if mount['RW'] else ':ro')]
for port,bindings in (old['HostConfig'].get('PortBindings') or {}).items():
    for binding in bindings:
        host=binding.get('HostIp') or '0.0.0.0'
        args+=['-p',host+':'+binding['HostPort']+':'+port]
docker('stop',name); docker('update','--restart=no',name); docker('rename',name,backup)
try:
    docker(*args,image)
    for attempt in range(15):
        try:
            with urllib.request.urlopen('http://127.0.0.1:9211/health',timeout=3) as response:
                assert json.load(response)['status']=='ok'
            break
        except Exception:
            if attempt==14:raise
            time.sleep(1)
    live=json.loads(docker('inspect',name))[0]
    report={'image':live['Image'],'source_sha256':docker('exec',name,'sha256sum','/resolver.py').split()[0],
            'started_at':live['State']['StartedAt'],'rollback_container':backup}
    (root/'resolver-deployed.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))
except Exception:
    docker('stop',name); docker('rename',name,name+'-failed-actor-trace-20260930')
    docker('rename',backup,name);docker('update','--restart=unless-stopped',name);docker('start',name)
    raise
