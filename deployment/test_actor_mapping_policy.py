import copy
import unittest
import actor_mapping_policy as policy


class MappingTests(unittest.TestCase):
    def setUp(self):
        self.mapping = policy.reviewed_mapping('かなで自由')
        self.imported = {'values': {'detail': {'Id':'8827', 'Name':'Miyu Kanade (かなで自由)', 'PremiereDate':'1994-02-13T05:00:00Z'}},
                         'result': {'aliases':['聖菜アリサ']}}
        self.enriched = {'values': {'selected_birth_date':'1994-02-14', 'birth_year':1994,
                                    'resolver_conflicts':{'birthday':['1994-02-13','1994-02-14']}},
                         'result': {'aliases':['Miyu Kanade/32岁','白石みお'], 'birth_year_source':'birth_date'}}
        self.params = {'primary_japanese_name':'かなで自由', 'aliases':[], 'birth_year':None}

    def test_historical_labels_resolve_to_one_identity(self):
        for name in ['かなで自由','Miyu Kanade','白石みお','白石未央','白石みお(白石未央)', 'Miyu Kanade (かなで自由)', 'Miyu Kanade (JAP、1994、かなで自由)']:
            self.assertEqual(policy.reviewed_mapping(name)['key'], 'miyu-kanade')
        self.assertIsNone(policy.reviewed_mapping('Unrelated Actor'))

    def test_unapproved_mixed_label_is_not_substring_matched(self):
        for value in ['聖菜アリサ','聖菜アリサ   白石みお（白石未央）']:
            with self.assertRaisesRegex(ValueError,'unapproved'):
                policy.reviewed_mapping(value)

    def test_provider_aliases_filtered_and_installed_date_retained(self):
        original = copy.deepcopy(self.enriched)
        imported,enriched,params,evidence = policy.apply_to_collections(self.mapping,self.imported,self.enriched,self.params)
        self.assertEqual(self.enriched,original)
        self.assertEqual(enriched['values']['selected_birth_date'],'1994-02-13')
        self.assertEqual(params['western_name'],'Miyu Kanade')
        self.assertEqual(params['birth_year'],1994)
        self.assertEqual(enriched['result']['emby_name'],'Miyu Kanade (JAP、1994、かなで自由)')
        self.assertEqual(params['aliases'],self.mapping['historical_aliases'])
        self.assertIn('聖菜アリサ',evidence['held_aliases'])
        self.assertNotIn('聖菜アリサ',imported['result']['aliases'])
        self.assertEqual(evidence['person_cleanup'],'not_performed')
        self.assertEqual(len(evidence['dictionary_sha256']),64)

    def test_old_person_cannot_take_over_link(self):
        self.imported['values']['detail']['Name']='白石みお（白石未央）'
        with self.assertRaisesRegex(ValueError,'canonical Emby Person'):
            policy.apply_to_collections(self.mapping,self.imported,self.enriched,self.params)

    def test_missing_installed_date_on_conflict_not_invented(self):
        self.imported['values']['detail'].pop('PremiereDate')
        _,enriched,_,_=policy.apply_to_collections(self.mapping,self.imported,self.enriched,self.params)
        self.assertIsNone(enriched['values']['selected_birth_date'])
        self.assertEqual(enriched['values']['birthdays'],[])

    def test_unrelated_actor_is_unchanged(self):
        i,e,p,evidence=policy.apply_to_collections(None,self.imported,self.enriched,self.params)
        self.assertEqual((i,e,p),(self.imported,self.enriched,self.params))
        self.assertIsNone(evidence)

    def test_review_is_last_idempotent_and_escaped(self):
        before='Manual biography\nLinks: kept'
        once=policy.render_review(before,['<script>bad</script>'])
        self.assertTrue(once.startswith(before))
        self.assertNotIn('<script>',once)
        self.assertEqual(policy.render_review(once,['<script>bad</script>']),once)
        self.assertEqual(policy.render_review(once,[]),before)
        self.assertEqual(once.count('Needs review'),1)


if __name__=='__main__': unittest.main()
