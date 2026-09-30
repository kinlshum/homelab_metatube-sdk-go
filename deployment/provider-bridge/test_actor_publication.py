import io,json,os,tempfile,unittest,xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch,Mock
import actor_publication as a

class PublicationTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  self.paths={'ini':self.root/'a.ini','json':self.root/'MetaTube.json','xml':self.root/'MetaTube.xml'}
  self.paths['ini'].write_text('old=Old\n')
  self.paths['json'].write_text(json.dumps({'ActorRawSubstitutionTable':'old=Old\n','Server':'unchanged','EnableActorSubstitution':True}))
  self.paths['xml'].write_text('<Config><Server>unchanged</Server><ActorRawSubstitutionTable>old=Old\n</ActorRawSubstitutionTable></Config>')
  self.p=patch.object(a,'paths',return_value=self.paths);self.p.start()
  self.e=patch.dict(os.environ,{'SUBSTITUTION_BACKUP_DIR':str(self.root/'backups')});self.e.start()
 def tearDown(self):self.p.stop();self.e.stop();self.tmp.cleanup()
 def test_whole_replace_hashes_backup_and_idempotency(self):
  content='新=New\nremoved=\n';sha=a.digest(content)
  r=a.deploy(content,sha)
  self.assertEqual(r['status'],'DEPLOYED');self.assertEqual(a.status()['status'],'READY')
  self.assertEqual(json.loads(self.paths['json'].read_text())['Server'],'unchanged')
  self.assertEqual(ET.parse(self.paths['xml']).getroot().findtext('Server'),'unchanged')
  self.assertEqual((Path(r['backup_directory'])/'a.ini').read_text(),'old=Old\n')
  self.assertEqual(a.deploy(content,sha)['status'],'UNCHANGED')
 def test_invalid_hash_does_not_write(self):
  with self.assertRaises(ValueError):a.deploy('new=New\n','a'*64)
  self.assertEqual(self.paths['ini'].read_text(),'old=Old\n')
 def test_rollback_on_mid_write_failure(self):
  original=a.atomic_write;calls=[]
  def write(path,data):
   calls.append(path)
   if len(calls)==2:raise OSError('test')
   original(path,data)
  with patch.object(a,'atomic_write',side_effect=write),self.assertRaises(OSError):a.deploy('new=New\n',a.digest('new=New\n'))
  self.assertEqual(a.status()['sha256'],a.digest('old=Old\n'))
  self.assertEqual(a.status()['status'],'READY')
 def test_duplicate_keys_rejected(self):
  with self.assertRaises(ValueError):a.validate('a=A\na=B\n')
 def test_auth_and_readonly_status_route(self):
  token=self.root/'token';token.write_text('x'*32)
  handler=Mock();handler.path='/v1/actor-substitutions/status';handler.command='GET'
  handler.headers={};handler.wfile=io.BytesIO()
  with patch.dict(os.environ,{'BRIDGE_TOKEN_FILE':str(token)}):
   self.assertTrue(a.handle(handler));handler.send_response.assert_called_with(401)
   handler.headers={'Authorization':'Bearer '+'x'*32};handler.wfile=io.BytesIO()
   self.assertTrue(a.handle(handler));handler.send_response.assert_called_with(200)
   self.assertEqual(json.loads(handler.wfile.getvalue())['status'],'READY')
  self.assertEqual(self.paths['ini'].read_text(),'old=Old\n')

if __name__=='__main__':unittest.main()
