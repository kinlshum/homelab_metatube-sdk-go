"""Deploy one shared experimental-provider release to an explicitly selected instance.

Usage on Kraken: python3 deploy.py PRIVATE_RELEASE_DIRECTORY 1|2 EXPECTED_OLD_IMAGE VERSION RELEASE_ID
No cookies, questionnaire answers, Emby metadata or media are changed.
"""
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse
import zipfile

STACK = Path('/mnt/cache_nvme_apps/appdata/metatube-stack')
TAG = sys.argv[5] if len(sys.argv) == 6 else ''
PROFILES = json.loads(Path(__file__).with_name('instances.json').read_text())

ENV = {'METATUBE_JAVBUS_AGE_ACKNOWLEDGED': 'true', 'METATUBE_JAVBUS_COOKIE_FILE': '/config/private/javbus-session.json'}
ALL = ['metatube', 'metatube2', 'metatube-postgres', 'metatube-provider-bridge', 'metatube-flaresolverr', 'metatube2-postgres', 'metatube2-provider-bridge', 'metatube2-flaresolverr', 'EmbyServer', 'jav-actor-resolver', 'jav-actor-identify-watcher', 'jav-master-api']

def run(*args): return subprocess.check_output(args, text=True).strip()
def inspect(name): return json.loads(run('docker', 'inspect', name))[0]
def private(path, value):
    with open(path, 'x') as f:
        os.chmod(path, 0o600)
        f.write(value)

def main():
    os.umask(0o077)
    root = Path(sys.argv[1]).resolve()
    selected = sys.argv[2]
    profile = PROFILES[selected]
    name, ip, image_tag, config_dir = (profile[k] for k in ('service', 'ip_suffix', 'image_tag', 'config_directory'))
    expected_image, version = sys.argv[3:5]
    assert re.fullmatch(r'[a-z0-9-]+', TAG), 'Invalid release ID'
    assert re.fullmatch(r'sha256:[0-9a-f]{64}', expected_image), 'Invalid old image'
    assert re.fullmatch(r'[0-9.]+', version), 'Invalid version'
    assert root.parent == STACK and root.name.startswith(TAG + '.')
    lock = open('/var/lock/deploy-metatube-chrome.lock', 'a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    old = inspect(name)
    assert old['Image'] == expected_image, 'Image drift'
    image = 'kinlshum/metatube-server-providers:' + image_tag
    assert old['Config']['Image'] == image
    private(root/'before.json', json.dumps(old))
    preserve = [n for n in ALL if n != name]
    before = {n: (inspect(n)['Id'], inspect(n)['State']['StartedAt']) for n in preserve}
    private(root/'preserved-before.json', json.dumps(before))
    compose = STACK/'compose.yaml'
    original = compose.read_text()
    private(root/'compose-before.yaml', original)
    cfg = json.loads(run('docker', 'compose', '-f', str(compose), 'config', '--format', 'json'))
    env = dict(x.split('=', 1) for x in old['Config']['Env'])
    assert all(str(v) == env.get(k) for k, v in cfg['services'][name]['environment'].items()), 'Environment drift'
    blocks = re.findall(r'(?ms)^  ' + name + r':\n.*?(?=^  \S|^\S|\Z)', original)
    assert len(blocks) == 1
    target = blocks[0]
    missing = {}
    for k, v in ENV.items():
        if k in env: assert env[k] == v, 'Session environment drift'
        else:
            assert k not in target
            missing[k] = v
    assert target.count('    environment:\n') == 1
    added = ''.join('      ' + k + ': "' + v + '"\n' for k, v in missing.items())
    updated = original.replace(target, target.replace('    environment:\n', '    environment:\n' + added, 1), 1)
    mount = next(m for m in old['Mounts'] if m['Destination'] == '/config')
    assert mount['Source'] == '/mnt/cache_nvme_apps/appdata/' + config_dir
    directory = Path(mount['Source'])/'private'
    assert not directory.is_symlink()
    directory.mkdir(mode=0o700, exist_ok=True)
    assert directory.stat().st_mode & 0o077 == 0
    rollback = image + '-rollback-' + TAG
    release_image = 'kinlshum/metatube-server-providers:' + TAG + '-' + selected
    run('docker', 'tag', expected_image, rollback)
    private(root/'runtime/Dockerfile', 'FROM ' + rollback + '\nCOPY metatube-server /metatube-server\n')
    subprocess.run(['docker', 'build', '-t', release_image, str(root/'runtime')], check=True)
    command = ['docker', 'compose', '-f', str(compose), 'up', '-d', '--no-deps', '--no-build', '--force-recreate', name]
    base = 'http://192.168.10.' + ip + ':8080'
    def http(path, body=None, origin=None):
        headers = {'Content-Type': 'application/json', 'X-JavBus-Verification': '1'}
        if origin: headers['Origin'] = origin
        req = urllib.request.Request(base + path, data=body, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=10) as r: return r.status, r.read()
        except urllib.error.HTTPError as e: return e.code, b''
    def config_fingerprints():
        paths = ['provider-throttles.json', 'movie-search-policy.json', 'private/javbus-session.json']
        return {p: hashlib.sha256((Path(mount['Source'])/p).read_bytes()).hexdigest()
                if (Path(mount['Source'])/p).exists() else None for p in paths}
    saved_files = config_fingerprints()
    status, data = http('/admin/api/provider-throttles')
    assert status == 200
    old_providers = {p['provider']: p for p in json.loads(data)['providers']}
    status, data = http('/admin/api/movie-search-policy')
    assert status == 200
    saved_policy = json.loads(data)['policy']
    assert env['METATUBE_PROVIDER_BRIDGE_URL'] == profile['bridge_url'], 'Bridge mismatch'
    assert env['METATUBE_GELF_SERVICE'] == profile['gelf_service'], 'Log identity mismatch'
    assert env['METATUBE_GELF_APPLICATION'] == profile['gelf_application'], 'Log application mismatch'
    assert urlparse(env['DSN']).hostname == profile['database_host'], 'Database cross-wiring'
    assert env.get('METATUBE_EMBY_CLEANUP_CONFIG_FILE', '') == profile['cleanup_config_file'], 'Cleanup configuration mismatch'
    assert old['NetworkSettings']['Networks']['br0']['IPAddress'] == '192.168.10.' + ip
    bridge = inspect(profile['bridge_container'])
    bridge_env = dict(x.split('=', 1) for x in bridge['Config']['Env'])
    assert bridge_env['FLARE_URL'] == profile['solver_url'], 'Solver cross-wiring'
    assert next(m['Source'] for m in bridge['Mounts'] if m['Destination'] == '/state') == str(STACK / profile['bridge_state_directory'])
    assert bridge['HostConfig']['PortBindings']['9210/tcp'][0]['HostPort'] == profile['bridge_host_port']
    database = inspect(profile['database_container'])
    assert next(m['Source'] for m in database['Mounts'] if m['Destination'] == '/var/lib/postgresql/data') == profile['database_directory']
    solver = inspect(profile['solver_container'])
    assert solver['HostConfig']['PortBindings']['8191/tcp'][0]['HostPort'] == profile['solver_host_port']
    assert not missing, 'Code-only deployment cannot add environment properties'
    activated = False
    stage = 'compose validation'
    try:
        assert compose.read_text() == original
        compose.write_text(updated)
        after = json.loads(run('docker', 'compose', '-f', str(compose), 'config', '--format', 'json'))
        expected = json.loads(json.dumps(cfg))
        expected['services'][name]['environment'].update(missing)
        assert after == expected, 'Unexpected Compose change'
        stage = 'activate'
        activated = True
        run('docker', 'tag', release_image, image)
        subprocess.run(command, check=True)
        stage = 'readiness'
        for attempt in range(25):
            try:
                status, page = http('/admin')
                assert status == 200 and version.encode() in page and b'javbusSessionPanel' not in page and b'No questionnaire blockage' in page
                break
            except Exception:
                if attempt == 24: raise RuntimeError('Admin readiness failed') from None
                time.sleep(1)
        stage = 'provider acceptance'
        status, data = http('/admin/api/provider-throttles')
        assert status == 200
        providers = {p['provider']: p for p in json.loads(data)['providers']}
        assert len(providers) == 31 and providers['avbase']['movie'] and providers['av-league']['actor'], 'Required provider set absent'
        assert all(providers.get(k) == v for k, v in old_providers.items()), 'Existing throttles changed'
        status, data = http('/admin/api/movie-search-policy')
        assert status == 200 and json.loads(data)['policy'] == saved_policy, 'Search policy changed'
        assert config_fingerprints() == saved_files, 'Persistent settings/session changed'
        stage = 'receiver safety'
        status, data = http('/admin/api/javbus-session')
        session = json.loads(data)
        assert status == 200 and session['enabled'] and session['persistent'] and session['state'] != 'cookie_store_error'
        assert http('/admin/api/javbus-session/import', b'{}', base)[0] == 400
        assert http('/admin/api/javbus-session/import', b'{}', 'https://evil.example')[0] == 403
        assert http('/admin/api/javbus-session/import', b'{}')[0] == 403
        assert http('/admin/api/javbus-session/start', b'{}', base)[0] == 410
        status, archive = http('/admin/javbus-chrome-extension.zip')
        assert status == 200
        with zipfile.ZipFile(io.BytesIO(archive)) as z:
            assert len(z.namelist()) == 5
            manifest = json.loads(z.read('metatube-javbus-chrome/manifest.json'))
            assert manifest['permissions'] == ['cookies']
        stage = 'preservation'
        for n in preserve:
            d = inspect(n)
            assert before[n] == (d['Id'], d['State']['StartedAt']), 'Other service changed: ' + n
        live = inspect(name)
        assert dict(x.split('=', 1) for x in live['Config']['Env']) == dict(env, **ENV)
        assert sorted(live['Mounts'], key=lambda m: m['Destination']) == sorted(old['Mounts'], key=lambda m: m['Destination']), 'Mount drift'
        report = {'target': name, 'provider_count': len(providers), 'provider_names': sorted(providers), 'config_preserved': True, 'admin_sha256': hashlib.sha256(page).hexdigest(), 'image': live['Image'], 'started_at': live['State']['StartedAt'], 'rollback_image': rollback, 'binary_sha256': hashlib.sha256((root/'runtime/metatube-server').read_bytes()).hexdigest(), 'extension_sha256': hashlib.sha256(archive).hexdigest(), 'preserved_services': preserve, 'live_cookie_import_tested': False, 'questionnaire_answers_submitted': 0}
        private(root/'deployment-report.json', json.dumps(report, indent=2))
        print(json.dumps(report))
    except Exception as error:
        print(json.dumps({'failed_stage': stage, 'error_type': type(error).__name__}))
        compose.write_text(original)
        if activated:
            run('docker', 'tag', rollback, image)
            subprocess.run(command, check=True)
        raise RuntimeError('Acceptance failed; target configuration/image restored. Inspect private release records.') from None

if __name__ == '__main__': main()
