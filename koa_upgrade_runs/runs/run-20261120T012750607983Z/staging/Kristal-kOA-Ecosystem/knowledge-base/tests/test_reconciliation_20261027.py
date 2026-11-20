import json, pathlib, unittest, collections
ROOT=pathlib.Path(__file__).resolve().parents[2]
S=ROOT/'knowledge-base/sources'
def values(n,key):return json.loads((S/n).read_text(encoding='utf8'))[key]
class ReconciliationTests(unittest.TestCase):
 def test_koa_155_records_all_mapped(self):
  report=json.loads((ROOT/'knowledge-base/documentation/KOA_20261027_RECONCILIATION.json').read_text(encoding='utf8'))
  self.assertEqual(report['source_registry_koa_entries'],155)
  self.assertEqual(len(report['mapping']),155)
  allids={x['id'] for x in values('repositories.json','repositories')}
  self.assertTrue(all(x['kristal_repository_id'] in allids for x in report['mapping']))
  self.assertEqual(len({x['kristal_repository_id'] for x in report['mapping']}),155)
 def test_sources_registered(self):
  registry=json.loads((S/'source-registry/source-registry.json').read_text(encoding='utf8'))
  names={x['source_id'] for x in registry['sources']}
  self.assertIn('src:koa-inventory-20261027',names)
  self.assertIn('src:snapshot-kristaldiag-20261027',names)
 def test_no_local_as_public_remote(self):
  for repo in values('repositories.json','repositories'):
   if str(repo.get('koa_inventory_identity','')).startswith('LOCAL/'):
    if repo.get('c0_inventory_registered'):
     self.assertIn('src:smartdump-c0-20261119',repo.get('source_refs',[]))
    else:
     self.assertFalse(repo.get('public_remote_url'))
 def test_corpus_role_boundaries(self):
  data={x['id']:x for x in values('components.json','components')}
  for n in ('koa:ekole','koa:ekole-pastorale','koa:ekole-quebec','koa:akor','koa:inkuisite','koa:dik','koa:kristalizer','koa:kristal-authoring-kit'):
   self.assertIn(n,data)
  self.assertNotEqual(data['koa:ekole']['repository_ref'],data['koa:ekole-quebec']['repository_ref'])
  self.assertNotEqual(data['koa:ekole']['repository_ref'],data['koa:ekole-pastorale']['repository_ref'])
 def test_no_automatic_activation(self):
  report=json.loads((ROOT/'knowledge-base/documentation/KOA_20261027_RECONCILIATION.json').read_text(encoding='utf8'))
  for key in ('deployment_checked','github_remote_reachability_checked','git_push_authorization_changed','v11_migration_executed'):
   self.assertFalse(report[key])
 def test_ambiguous_checkouts_not_collapsed(self):
  report=json.loads((ROOT/'knowledge-base/documentation/KOA_20261027_RECONCILIATION.json').read_text(encoding='utf8'))
  self.assertEqual(len(report['ambiguous_inventory_github_identities']),7)
  for pair in report['ambiguous_inventory_github_identities']:
   rows=[x for x in report['mapping'] if x['koa_identity'].casefold()==pair['github_repo'].casefold()]
   self.assertEqual(len({x['kristal_repository_id'] for x in rows}),pair['count'])
if __name__=='__main__': unittest.main()
