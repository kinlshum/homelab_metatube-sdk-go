import unittest
import json
import os
import tempfile
import time
import threading
from unittest.mock import Mock, patch
from urllib.error import HTTPError

import resolver


class ResolverTests(unittest.TestCase):
    def test_metatube_actor_requests_carry_one_resolver_request_id(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def read(self): return b'{"data": []}'

        resolver._request_context.run_id = 'resolver-request-123'
        try:
            with patch.object(resolver.urllib.request, 'urlopen', return_value=Response()) as opened:
                resolver.request_json(resolver.METATUBE_URL + '/v1/actors/search?q=test')
                self.assertEqual(opened.call_args.args[0].get_header('X-metatube-run-id'), 'resolver-request-123')
                self.assertEqual(opened.call_args.args[0].get_header('X-metatube-client'), 'actor-resolver')
                resolver.request_json('https://example.test/actors')
                self.assertIsNone(opened.call_args.args[0].get_header('X-metatube-run-id'))
        finally:
            del resolver._request_context.run_id

    def test_source_workers_preserve_request_id(self):
        resolver._request_context.run_id = 'resolver-request-456'
        try:
            observed = resolver.collect_sources([(lambda _: resolver._request_context.run_id, None)], time.monotonic() + 2)
            self.assertEqual(observed, ['resolver-request-456'])
        finally:
            del resolver._request_context.run_id

    def test_resolver_request_receipts_are_persistent_and_exact_name_scoped(self):
        with patch.object(resolver, "TRACE_FILE", os.path.join(self.temporary.name, "resolve-events.jsonl")):
            resolver.append_resolve_event({"request_id": "one", "name": "みなと羽琉", "client_ip": "192.168.10.151", "status": "resolved"})
            resolver.append_resolve_event({"request_id": "other", "name": "another actor", "status": "resolved"})
            resolver.append_resolve_event({"request_id": "two", "name": "みなと羽琉", "client_ip": "192.168.10.167", "status": "resolved"})
            self.assertEqual([item["request_id"] for item in resolver.recent_resolve_events("みなと羽琉")], ["two", "one"])
            self.assertEqual(resolver.recent_resolve_events("unknown"), [])

    def test_single_word_stage_name_and_age_label(self):
        for provider in ('XsList', 'Minnano-AV', 'JavLibrary'):
            with self.subTest(provider=provider):
                detail = dict(provider=provider, id='4257', name='佐知子',
                              aliases=['Sachiko/27岁', 'さちこ', 'Sachiko'], birthday='2000-02-02')
                record = resolver.merge('佐知子', [detail])
                self.assertEqual(record['name'], 'Sachiko (JAP、2000、佐知子)')
                self.assertEqual(record['aliases'], ['さちこ'])

    def test_single_word_does_not_relax_handle_url_or_numeric_rejection(self):
        for value in ('@Sachiko', 'https://Sachiko', 'Sachiko27', 'Sachiko/27profile',
                      'Sachiko/123', '佐知子 Sachiko', 'One Two Three Four Five'):
            with self.subTest(value=value):
                self.assertEqual(resolver.latin_alias([value]), '')
        self.assertEqual(resolver.latin_alias(['Sachiko']), 'Sachiko')
        self.assertEqual(resolver.latin_alias(['Rin Asahi/25歳']), 'Rin Asahi')

    def test_old_parser_cache_cannot_mask_single_word_fix(self):
        resolver.CACHE_FILE = os.path.join(self.temporary.name, 'cache.json')
        resolver.save_cache({'佐知子': {'saved_at': time.time(), 'name_parser_version': 3,
                                      'record': {'name': '佐知子'}}})
        detail = dict(provider='XsList', id='4257', name='佐知子', aliases=['Sachiko'], birthday='2000-02-02')
        with patch.object(resolver, 'request_json', return_value={'data': [detail]}) as search, \
             patch.object(resolver, 'actor_detail', return_value=detail):
            self.assertEqual(resolver.resolve('佐知子')['name'], 'Sachiko (JAP、2000、佐知子)')
            self.assertEqual(resolver.resolve('佐知子')['name'], 'Sachiko (JAP、2000、佐知子)')
            search.assert_called_once()

    def test_retry_transient_get_reconnects(self):
        from unittest.mock import MagicMock
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{"data": []}'
        failure = HTTPError('http://test', 503, 'Unavailable', {}, None)
        with patch.object(resolver.urllib.request, 'urlopen', side_effect=[failure, response]) as get, patch.object(resolver.time, 'sleep'):
            self.assertEqual(resolver.request_json('http://test'), {'data': []})
        self.assertEqual(get.call_count, 2)

    def test_permanent_404_not_retried(self):
        with patch.object(resolver.urllib.request, 'urlopen', side_effect=HTTPError('http://test',404,'missing',{},None)) as get:
            with self.assertRaises(HTTPError): resolver.request_json('http://test')
        self.assertEqual(get.call_count, 1)

    def test_retry_after_cannot_exceed_deadline(self):
        resolver._request_context.deadline = time.monotonic() + 0.1
        try:
            with patch.object(resolver.urllib.request, 'urlopen', side_effect=HTTPError('http://test',429,'busy',{'Retry-After':'5'},None)) as get:
                with self.assertRaises(TimeoutError): resolver.request_json('http://test')
            self.assertEqual(get.call_count, 1)
        finally:
            del resolver._request_context.deadline

    def test_slow_optional_source_does_not_block_rin_identity(self):
        release = threading.Event()
        def slow(_):
            release.wait(2)
            return {'provider': 'late'}
        detail = {'provider':'XsList','id':'133984','name':'朝日りん',
                  'aliases':['Rin Asahi'], 'birthday':'2001-03-10'}
        started = time.monotonic()
        try:
            facts = resolver.collect_sources([(lambda _:detail, None), (slow, None)], started + 0.1)
            self.assertLess(time.monotonic() - started, 0.8)
            self.assertEqual(resolver.merge('朝日りん', facts)['name'], 'Rin Asahi (JAP、2001、朝日りん)')
            self.assertEqual(len(facts), 1)
        finally:
            release.set()

    def test_source_completion_order_does_not_change_precedence(self):
        def first(_):
            time.sleep(0.03)
            return {'provider':'XsList'}
        self.assertEqual(resolver.collect_sources([(first,None),(lambda _:{'provider':'AV-LEAGUE'},None)],time.monotonic()+1),
                         [{'provider':'XsList'},{'provider':'AV-LEAGUE'}])

    def test_gfriends_is_only_used_without_another_profile(self):
        gfriends = {'provider': 'Gfriends', 'id': 'portrait', 'name': 'みなと羽琉',
                    'homepage': 'https://example.test/portrait', 'aliases': ['Wrong Name'],
                    'images': ['wrong.jpg'], 'birthday': '2000-01-01'}
        verified = {'provider': 'AV-LEAGUE', 'id': '36135', 'name': 'みなと羽琉',
                    'homepage': 'https://example.test/36135', 'aliases': ['Minato Haru'],
                    'images': ['right.jpg'], 'birthday': '1996-06-09'}
        record = resolver.merge('みなと羽琉', [gfriends, verified])
        self.assertEqual(record['birthday'], '1996-06-09')
        self.assertEqual(record['images'], ['right.jpg'])
        self.assertNotIn('Gfriends', record['external_ids'])
        self.assertEqual(record['urls']['Gfriends'], 'https://example.test/portrait')

    def test_gfriends_is_searched_last_only_when_no_other_profile_matches(self):
        self.assertEqual(resolver.SOURCE_ORDER[:3],
                         ('AV-LEAGUE', 'Minnano-AV', 'XsList'))
        self.assertEqual(resolver.SOURCE_ORDER[-1], 'Gfriends')
        primary = {'provider': 'AV-LEAGUE', 'id': '36135', 'name': 'みなと羽琉',
                   'aliases': ['Minato Haru'], 'birthday': '1996-06-09'}
        placeholder = {'provider': 'Gfriends', 'id': 'portrait', 'name': 'みなと羽琉',
                       'aliases': ['Wrong Name'], 'birthday': '2000-01-01',
                       'images': ['portrait.jpg']}
        calls = []
        def detail(result):
            calls.append(result['provider'])
            return result
        with patch.object(resolver, 'CACHE_FILE', os.path.join(self.temporary.name, 'cache.json')), \
             patch.object(resolver, 'request_json', return_value={'data': [primary, placeholder]}), \
             patch.object(resolver, 'actor_detail', side_effect=detail), \
             patch.object(resolver, 'actor_db_identity', return_value=None), \
             patch.object(resolver, 'xslist_search_detail', return_value=None), \
             patch.object(resolver, 'javlibrary_detail', return_value=None), \
             patch.object(resolver, 'minnano_search_detail', return_value=None), \
             patch.object(resolver, 'javdatabase_detail', return_value=None), \
             patch.object(resolver, 'babepedia_detail', return_value=None), \
             patch.object(resolver, 'javlink_detail', return_value=None), \
             patch.object(resolver, 'javmodel_detail', return_value=None), \
             patch.object(resolver, 'javdb_detail', return_value=None):
            record = resolver.resolve('みなと羽琉', refresh=True)
        self.assertEqual(calls, ['AV-LEAGUE'])
        self.assertEqual(record['source_status']['Gfriends'], 'placeholder (not needed)')

        calls.clear()
        with patch.object(resolver, 'CACHE_FILE', os.path.join(self.temporary.name, 'fallback.json')), \
             patch.object(resolver, 'request_json', return_value={'data': [placeholder]}), \
             patch.object(resolver, 'actor_detail', side_effect=detail):
            fallback = resolver.resolve('みなと羽琉', refresh=True)
        self.assertEqual(calls, ['Gfriends'])
        self.assertEqual(fallback['source_status']['Gfriends'], 'found')
        self.assertEqual(fallback['name'], 'みなと羽琉')
        self.assertEqual(fallback['birthday'], '')
        self.assertEqual(fallback['aliases'], [])
        self.assertEqual(fallback['images'], ['portrait.jpg'])
        self.assertEqual(fallback['external_ids'], {})

    def test_all_rejected_search_retains_source_evidence_without_a_fake_actor(self):
        candidate = {'provider': 'AV-LEAGUE', 'id': '456', 'name': 'みなと羽琉'}
        rejected_url = 'https://www.av-league.com/actress/456.html'
        with patch.object(resolver, 'CACHE_FILE', os.path.join(self.temporary.name, 'rejected.json')), \
             patch.object(resolver, 'request_json', return_value={'data': [candidate]}), \
             patch.object(resolver, 'actor_detail', side_effect=resolver.SourceIdentityMismatch(rejected_url)), \
             patch.object(resolver, 'actor_db_identity', return_value=None), \
             patch.object(resolver, 'xslist_search_detail', return_value=None), \
             patch.object(resolver, 'javlibrary_detail', return_value=None), \
             patch.object(resolver, 'minnano_search_detail', return_value=None), \
             patch.object(resolver, 'javdatabase_detail', return_value=None), \
             patch.object(resolver, 'babepedia_detail', return_value=None), \
             patch.object(resolver, 'javlink_detail', return_value=None), \
             patch.object(resolver, 'javmodel_detail', return_value=None), \
             patch.object(resolver, 'javdb_detail', return_value=None):
            with self.assertRaises(resolver.NoActorMatch) as caught:
                resolver.resolve('みなと羽琉', refresh=True)
        self.assertEqual(caught.exception.source_status['AV-LEAGUE'], 'identity mismatch')
        self.assertEqual(caught.exception.rejected_urls['AV-LEAGUE'], rejected_url)

    def test_not_found_http_response_exposes_rejections_to_workflow(self):
        handler = resolver.Handler.__new__(resolver.Handler)
        handler.path = '/resolve?name=%E3%81%BF%E3%81%AA%E3%81%A8%E7%BE%BD%E7%90%89'
        handler.client_address = ('127.0.0.1', 0)
        handler.send_json = Mock()
        rejected = resolver.NoActorMatch('みなと羽琉', {'AV-LEAGUE': 'identity mismatch'},
                                          {'AV-LEAGUE': 'https://www.av-league.com/actress/456.html'})
        with patch.object(resolver, 'resolve', side_effect=rejected), \
             patch.object(resolver, 'append_resolve_event'):
            handler.do_GET()
        status, body = handler.send_json.call_args.args
        self.assertEqual(status, 404)
        self.assertEqual(body['source_status']['AV-LEAGUE'], 'identity mismatch')
        self.assertEqual(body['source_priority'][-1], 'Gfriends')
        self.assertNotIn('data', body)

    def test_old_priority_cache_is_recollected_before_primary_id_selection(self):
        cache_file = os.path.join(self.temporary.name, 'old-priority.json')
        candidates = [{'provider': 'XsList', 'id': '162', 'name': '水城奈緒'},
                      {'provider': 'Minnano-AV', 'id': '556877', 'name': '水城奈緒'}]
        details = [dict(item, aliases=['Nao Mizuki'], birthday='1984-09-17')
                   for item in candidates]
        with patch.object(resolver, 'CACHE_FILE', cache_file):
            resolver.save_cache({'水城奈緒': {'saved_at': time.time(), 'name_parser_version': 5,
                                           'record': {'id': 'XsList:162', 'name': 'Nao Mizuki'}}})
            with patch.object(resolver, 'request_json', return_value={'data': candidates}) as search, \
                 patch.object(resolver, 'actor_detail', side_effect=lambda item: next(
                     detail for detail in details if detail['provider'] == item['provider'])), \
                 patch.object(resolver, 'actor_db_identity', return_value=None), \
                 patch.object(resolver, 'javlibrary_detail', return_value=None), \
                 patch.object(resolver, 'javdatabase_detail', return_value=None), \
                 patch.object(resolver, 'babepedia_detail', return_value=None), \
                 patch.object(resolver, 'javlink_detail', return_value=None), \
                 patch.object(resolver, 'javmodel_detail', return_value=None), \
                 patch.object(resolver, 'javdb_detail', return_value=None):
                record = resolver.resolve('水城奈緒')
            self.assertTrue(search.called)
            self.assertEqual(record['id'], 'Minnano-AV:556877')
            self.assertEqual(resolver.load_cache()['水城奈緒']['name_parser_version'], 6)

    def test_source_outcomes_expose_timeout_instead_of_silently_dropping_it(self):
        release = threading.Event()
        outcomes = {'Minnano-AV': 'not returned by search'}
        try:
            found = resolver.collect_sources([(lambda _: release.wait(1), None)],
                                             time.monotonic() + .01, ['Minnano-AV'], outcomes)
            self.assertEqual(found, [])
            self.assertEqual(outcomes['Minnano-AV'], 'timed out')
        finally:
            release.set()

    def test_minnano_former_names_include_original_identity(self):
        document = '''<h1>みなみ羽琉<span>みなみはる / Minami Haru</span></h1>
        <span>別名</span><p>ひなた （ひなた / Hinata）</p>
        <span>別名</span><p>みなと羽琉 （みなとはる / Minato Haru）</p>
        <span>生年月日</span><p>1996年06月09日</p>'''
        with patch.object(resolver, 'minnano_text', return_value=document):
            detail = resolver.minnano_detail('677238')
        self.assertIn('みなと羽琉', detail['aliases'])
        self.assertIn('Minato Haru', detail['aliases'])
        self.assertTrue(resolver.exact_match(detail, ['みなと羽琉']))

    def test_actor_db_identity_is_exact_and_forms_name_after_sources(self):
        self.lookups[-1].stop()
        class Response:
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def read(self): return json.dumps({'actor_db': {'actor_id': 'actor-1',
                'name': 'Minato Haru (JAP、みなと羽琉)', 'western_name': 'Minato Haru',
                'japanese_name': 'みなと羽琉', 'mapping': []}}).encode()
        with patch.object(resolver.urllib.request, 'urlopen', return_value=Response()):
            identity = resolver.actor_db_identity('みなと羽琉')
        detail = {'provider': 'AV-LEAGUE', 'id': '36135', 'name': 'みなと羽琉',
                  'aliases': [], 'birthday': '1996-06-09'}
        record = resolver.merge('みなと羽琉', [detail], identity)
        self.assertEqual(record['name'], 'Minato Haru (JAP、1996、みなと羽琉)')
        self.assertEqual(record['provenance']['western_name'], 'Actor DB')

    def test_javlink_requires_matching_japanese_name(self):
        self.lookups[-2].stop()
        good = '<h1>Haru Minato - みなと羽琉</h1><p>Born : 06/09/1996</p>'
        bad = '<h1>Haru Minato - 湊波流</h1><p>Born : 06/09/2003</p>'
        with patch.object(resolver, 'request_text', side_effect=[bad, good]):
            detail = resolver.javlink_detail(['みなと羽琉', 'Minato Haru', 'Haru Minato'])
        self.assertEqual(detail['homepage'], 'https://jav.link/jav/haru-minato/')
        self.assertEqual(detail['birthday'], '1996-06-09')

    def test_javmodel_requires_matching_japanese_subheading(self):
        self.lookups[-4].stop()
        good = '<h1>Haru Minato</h1><h2>みなと羽琉 - 湊羽琉</h2><p>Born : 06/09/1996</p>'
        bad = '<h1>Haru Minato</h1><h2>湊波流</h2><p>Born : 06/09/2003</p>'
        with patch.object(resolver, 'request_text', side_effect=[bad, good]):
            detail = resolver.javmodel_detail(['みなと羽琉', 'Minato Haru', 'Haru Minato'])
        self.assertEqual(detail['homepage'], 'https://javmodel.com/jav/haru-minato/')
        self.assertEqual(detail['birthday'], '1996-06-09')

    def test_javdb_uses_saved_id_and_verifies_japanese_name(self):
        self.lookups[-3].stop()
        identity = {'japanese_name': 'みなと羽琉', 'external_ids': {'JavdbActor': 'eKY01'}}
        with patch.object(resolver, 'request_text', return_value='<h1>湊羽琉, みなと羽琉</h1>'):
            detail = resolver.javdb_detail(identity)
        self.assertEqual(detail['id'], 'eKY01')
        with patch.object(resolver, 'request_text', return_value='<h1>湊波流</h1>'):
            with self.assertRaises(resolver.SourceIdentityMismatch):
                resolver.javdb_detail(identity)

    def test_javdatabase_rejects_same_western_name_with_different_japanese_name(self):
        self.lookups[3].stop()
        search = '<a href="https://www.javdatabase.com/idols/haru-minato/">Haru Minato</a>'
        profile = '<h1 class="idol-name">Haru Minato - JAV Profile</h1><p>JP: 湊波流</p>'
        with patch.object(resolver, 'flare_text', side_effect=[search, profile]):
            with self.assertRaises(resolver.SourceIdentityMismatch) as error:
                resolver.javdatabase_detail(['みなと羽琉', 'Minato Haru'])
        self.assertEqual(error.exception.url, 'https://www.javdatabase.com/idols/haru-minato/')

    def test_minnano_challenge_uses_solver_and_heading_romanization(self):
        document = '<h1>今井美優<span>いまいみゆ / Imai Miyu</span></h1>'
        with patch.object(resolver, 'request_text', side_effect=HTTPError('https://example',403,'Forbidden',{},None)), patch.object(resolver,'flare_text',return_value=document) as solver:
            detail = resolver.minnano_detail('123')
        self.assertEqual(detail['name'], '今井美優')
        self.assertEqual(resolver.western_name([detail], detail['aliases']), 'Miyu Imai')
        solver.assert_called_once()

    def test_social_handles_and_urls_are_not_names(self):
        self.assertEqual(resolver.latin_alias(['@imai_miyu', 'https://x.com/imai_miyu', 'miyu123', '今井 Miyu', 'Imai Miyuu']), 'Imai Miyuu')
        self.assertEqual(resolver.latin_alias(['@MiyuuImai']), '')

    def test_unknown_birth_year_omitted_not_question_mark(self):
        detail = dict(provider='Minnano-AV', id='123', name='今井美優', aliases=['Imai Miyu'])
        self.assertEqual(resolver.merge('今井美優',[detail])['name'], 'Miyu Imai (JAP、今井美優)')

    def test_parses_minnano_profile_and_former_name(self):
        document = '''
        <script type="application/ld+json">{"@type":"Person","name":"あかね麗",
        "alternateName":"あかねうらら","additionalName":"Akane Urara",
        "birthDate":"1999-11-30","image":"actor.jpg"}</script>
        <span>別名</span><p>二階堂麗【旧名】 （にかいどううらら / Nikaidou Urara）</p>
        <span>生年月日</span><p>1999年11月30日 （現在26歳）いて座</p>
        <span>サイズ</span><p>T162 / B88(<a>Fカップ</a>) / W56 / H88 / S</p>
        <span>趣味・特技</span><p>ヘアセット</p>
        <span>AV出演期間</span><p>2024年-</p>
        <span>デビュー作品</span><p>大型巨乳新人（2024年05月 21日）</p>
        '''
        original = resolver.request_text
        resolver.request_text = lambda _url: document
        try:
            detail = resolver.minnano_detail("251960")
        finally:
            resolver.request_text = original
        self.assertEqual("1999-11-30", detail["birthday"])
        self.assertEqual("2024-05-21", detail["debut_date"])
        self.assertEqual("Nikaidou Urara", detail["aliases"][-1])
        self.assertEqual("B88/W56/H88", detail["measurements"])
        self.assertEqual("いて座", detail["sign"])

    def test_invalid_date_falls_through_to_next_source(self):
        details = [
            {
                "id": "1", "name": "南見京", "provider": "AV-LEAGUE",
                "homepage": "", "aliases": ["Minami Kei"], "images": [],
                "birthday": "0001-01-01T00:00:00Z", "debut_date": "0001-01-01T00:00:00Z",
                "blood_type": "", "cup_size": "", "measurements": "",
                "nationality": "", "height": 0, "hobby": "", "skill": "", "summary": "",
            },
            {
                "id": "19739", "name": "南見京", "provider": "Minnano-AV",
                "homepage": "https://www.minnano-av.com/actress19739.html",
                "aliases": ["みなみけい", "Minami Kei"], "images": [],
                "birthday": "2005-01-01T00:00:00Z", "debut_date": "2026-01-16T00:00:00Z",
                "blood_type": "", "cup_size": "K", "measurements": "B112/W66/H96",
                "nationality": "日本", "height": 170, "hobby": "", "skill": "", "summary": "",
            },
        ]

        record = resolver.merge("南見京", details)

        self.assertEqual("2005-01-01", record["birthday"])
        self.assertEqual("Minnano-AV", record["provenance"]["birthday"])

    def test_minnano_debut_fields_flow_into_merged_record(self):
        details = [{
            "id": "38990", "name": "南見京", "provider": "AV-LEAGUE",
            "homepage": "https://www.av-league.com/actress/38990.html",
            "aliases": ["Minami Kei"], "images": [], "birthday": "",
            "debut_date": "2026-01-16T00:00:00Z", "debut_title": "",
            "av_appearance_period": "", "tags": [], "blood_type": "", "cup_size": "K",
            "measurements": "", "nationality": "", "height": 170, "hobby": "",
            "skill": "", "summary": "",
        }, {
            "id": "19739", "name": "南見京", "provider": "Minnano-AV",
            "homepage": "https://www.minnano-av.com/actress19739.html",
            "aliases": ["みなみけい", "Minami Kei"], "images": [],
            "birthday": "2005-01-01T00:00:00Z",
            "debut_date": "2026-01-20T00:00:00Z",
            "debut_title": "大型新人 南見京AVデビュー",
            "av_appearance_period": "2026年 -", "tags": ["長身", "巨乳"],
            "blood_type": "", "cup_size": "K", "measurements": "B112/W66/H96",
            "nationality": "日本", "height": 170, "hobby": "", "skill": "",
            "summary": "",
        }]

        record = resolver.merge("南見京", details)

        self.assertEqual("2026-01-20", record["debut_date"])
        self.assertEqual("大型新人 南見京AVデビュー", record["debut_title"])
        self.assertEqual("2026年 -", record["av_appearance_period"])
        self.assertEqual(["長身", "巨乳"], record["tags"])
        self.assertEqual("Minnano-AV", record["provenance"]["debut_date"])

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        resolver.OVERRIDES_FILE = os.path.join(self.temporary.name, "overrides.json")
        # Unit tests never scrape production sites.
        self.lookups = [patch.object(resolver, name, return_value=None) for name in
                        ('xslist_search_detail','javlibrary_detail','minnano_search_detail',
                         'javdatabase_detail','babepedia_detail','javmodel_detail','javdb_detail',
                         'javlink_detail','actor_db_identity')]
        for lookup in self.lookups:
            lookup.start()
            self.addCleanup(lookup.stop)

    def tearDown(self):
        self.temporary.cleanup()

    def test_extracts_japanese_name_from_emby_labels(self):
        self.assertEqual("水城奈緒", resolver.lookup_name("[JAV_CUSTOM_PROVIDER] 水城奈緒"))
        self.assertEqual("水城奈緒", resolver.lookup_name("Nao Mizuki (JAP、1984、水城奈緒)"))
        self.assertEqual("Nao Mizuki (JAP、1984、水城奈緒)",
                         resolver.mapped_canonical_name("Nao Mizuki (JAP、1984、水城奈緒)"))

    def test_cleans_mochizuki_aliases(self):
        aliases = [
            "望月円", "もちづきまどか", "Mochizuki Madoka", "Madoka Mochizuki",
            "Also known as: En Mochizuki", "Mochizuki En",
        ]
        self.assertEqual(
            ["もちづきまどか", "Mochizuki Madoka", "Madoka Mochizuki"],
            resolver.clean_aliases(aliases, "En Mochizuki (JAP、2005、望月円)"),
        )

    def test_cleans_mixed_language_latin_noise(self):
        aliases = [
            "水澄ひかり", "Hikari Mizusumashi/29岁", "みすみひかり", "Misumi Hikari",
        ]
        self.assertEqual(
            ["みすみひかり"],
            resolver.clean_aliases(aliases, "Hikari Misumi (JAP、1996、水澄ひかり)"),
        )

    def test_merges_nao_mizuki_identity(self):
        record = resolver.merge("水城奈緒", [
            {"id": "162", "name": "水城奈緒", "provider": "XsList",
             "homepage": "https://xslist.org/zh/model/162.html", "aliases": ["Nao Mizuki"],
             "images": ["one.jpg"], "birthday": "1984-09-17T00:00:00Z",
             "blood_type": "B", "cup_size": "G", "measurements": "B90/W58/H87",
             "nationality": "日本", "height": 159, "hobby": "", "skill": "",
             "summary": "", "debut_date": ""},
            {"id": "556877", "name": "水城奈緒", "provider": "Minnano-AV",
             "homepage": "https://www.minnano-av.com/actress556877.html",
             "aliases": ["みずきなお", "Mizuki Nao"], "images": ["two.jpg"],
             "birthday": "1984-09-18T00:00:00Z", "blood_type": "B", "cup_size": "H",
             "measurements": "B90/W65/H95", "nationality": "日本", "height": 160,
             "hobby": "華道、茶道", "skill": "", "summary": "出身地：東京都。", "debut_date": ""},
        ])
        self.assertEqual("Nao Mizuki (JAP、1984、水城奈緒)", record["name"])
        self.assertEqual("Minnano-AV:556877", record["id"])
        self.assertEqual("H", record["cup_size"])
        self.assertEqual("華道、茶道", record["hobby"])
        self.assertEqual("東京都", record["place_of_birth"])
        self.assertIn("birthday", record["conflicts"])

    def test_prefers_reversed_minnano_western_name(self):
        record = resolver.merge("海老咲あお", [{
            "id": "36633", "name": "海老咲あお", "provider": "AV-LEAGUE",
            "homepage": "", "aliases": ["Ebisaki Ao"], "images": [],
            "birthday": "2000-02-02", "debut_date": "", "blood_type": "",
            "cup_size": "", "measurements": "", "nationality": "日本",
            "height": 0, "hobby": "", "skill": "", "summary": "",
        }, {
            "id": "539148", "name": "海老咲あお", "provider": "Minnano-AV",
            "homepage": "", "aliases": ["えびさきあお", "Ebisaki Ao"],
            "images": [], "birthday": "2000-09-15", "debut_date": "",
            "blood_type": "", "cup_size": "", "measurements": "",
            "nationality": "日本", "height": 0, "hobby": "", "skill": "",
            "summary": "",
        }])
        self.assertEqual("Ao Ebisaki (JAP、2000、海老咲あお)", record["name"])

    def test_reverses_javlibrary_western_name(self):
        record = resolver.merge("海老咲あお", [{
            "id": "actor", "name": "海老咲あお", "provider": "JavLibrary",
            "homepage": "", "aliases": ["Ebisaki Ao"], "images": [],
            "birthday": "2000-09-15", "debut_date": "", "blood_type": "",
            "cup_size": "", "measurements": "", "nationality": "日本",
            "height": 0, "hobby": "", "skill": "", "summary": "",
        }])
        self.assertEqual("Ao Ebisaki (JAP、2000、海老咲あお)", record["name"])

    def test_preferred_name_override_matches_any_alias(self):
        with open(resolver.OVERRIDES_FILE, "w", encoding="utf-8") as handle:
            json.dump({"actors": [{
                "canonical": "Kiho Aisaka", "original": "逢坂希穂", "birth_year": 2004,
                "aliases": ["Ousaka Kiho", "おうさかきほ"]
            }]}, handle, ensure_ascii=False)
        record = resolver.merge("逢坂希穂", [{
            "id": "37757", "name": "逢坂希穂", "provider": "AV-LEAGUE",
            "homepage": "https://www.av-league.com/actress/37757.html",
            "aliases": ["おうさかきほ", "Ousaka Kiho"], "images": [],
            "birthday": "2004-02-02T00:00:00Z", "debut_date": "", "blood_type": "",
            "cup_size": "F", "measurements": "", "nationality": "日本", "height": 157,
            "hobby": "", "skill": "", "summary": ""
        }])
        self.assertEqual("Kiho Aisaka (JAP、2004、逢坂希穂)", record["name"])

    def test_override_supplies_name_when_sources_have_no_latin_alias(self):
        with open(resolver.OVERRIDES_FILE, "w", encoding="utf-8") as handle:
            json.dump({"actors": [{
                "canonical": "Yuuka Niizuma", "original": "新妻ゆうか", "birth_year": 1993,
                "aliases": ["夕花(ゆうか)", "Niiduma Yuuka"]
            }]}, handle, ensure_ascii=False)
        record = resolver.merge("新妻ゆうか", [{
            "id": "37965", "name": "新妻ゆうか", "provider": "AV-LEAGUE",
            "homepage": "https://www.av-league.com/actress/37965.html", "aliases": [],
            "images": [], "birthday": "1993-02-02T00:00:00Z", "debut_date": "",
            "blood_type": "", "cup_size": "H", "measurements": "", "nationality": "日本",
            "height": 160, "hobby": "", "skill": "", "summary": ""
        }])
        self.assertEqual("Yuuka Niizuma (JAP、1993、新妻ゆうか)", record["name"])

    def test_aika_yumeno_override_keeps_distinct_identity(self):
        with open(resolver.OVERRIDES_FILE, "w", encoding="utf-8") as handle:
            json.dump({"actors": [{
                "canonical": "Aika Yumeno", "original": "夢乃あいか", "birth_year": 1994,
                "aliases": ["夢乃愛華", "ゆめのあいか", "Yumeno Aika"]
            }]}, handle, ensure_ascii=False)
        record = resolver.merge("夢乃あいか", [{
            "id": "9", "name": "夢乃あいか", "provider": "XsList",
            "homepage": "https://xslist.org/en/model/9.html",
            "aliases": ["ゆめのあいか", "Yumeno Aika"], "images": [],
            "birthday": "1994-08-25T00:00:00Z", "debut_date": "",
            "blood_type": "", "cup_size": "", "measurements": "",
            "nationality": "日本", "height": 0, "hobby": "", "skill": "", "summary": ""
        }])
        self.assertEqual("Aika Yumeno (JAP、1994、夢乃あいか)", record["name"])
        self.assertEqual("XsList:9", record["id"])

    def test_akane_rei_uses_latest_javlibrary_name(self):
        with open(resolver.OVERRIDES_FILE, "w", encoding="utf-8") as handle:
            json.dump({"actors": [{
                "canonical": "Rei Akane", "original": "あかね麗",
                "aliases": ["Akane Rei", "Akane Urara"],
                "historical_aliases": ["二階堂麗", "Nikaidou Urara"],
                "external_ids": {"JavLibrary Idol": "aatva"},
                "urls": {"JavLibrary Idol":
                         "https://www.javlibrary.com/en/vl_star.php?s=aatva"},
            }]}, handle, ensure_ascii=False)
        record = resolver.merge("あかね麗", [{
            "id": "251960", "name": "あかね麗", "provider": "Minnano-AV",
            "homepage": "https://www.minnano-av.com/actress251960.html",
            "aliases": ["あかねうらら", "Akane Urara"], "images": [],
            "birthday": "", "debut_date": "", "blood_type": "", "cup_size": "",
            "measurements": "", "nationality": "日本", "height": 0,
            "hobby": "", "skill": "", "summary": "",
        }])
        self.assertEqual("Rei Akane (JAP、?、あかね麗)", record["name"])
        self.assertIn("二階堂麗", record["aliases"])
        self.assertIn("Nikaidou Urara", record["aliases"])
        self.assertEqual("aatva", record["external_ids"]["JavLibrary Idol"])

    def test_resolve_searches_override_original_for_alias(self):
        with open(resolver.OVERRIDES_FILE, "w", encoding="utf-8") as handle:
            json.dump({"actors": [{
                "canonical": "Aika Yumeno", "original": "夢乃あいか", "birth_year": 1994,
                "aliases": ["夢乃愛華", "ゆめのあいか"]
            }]}, handle, ensure_ascii=False)
        resolver.CACHE_FILE = os.path.join(self.temporary.name, "cache.json")
        requested = []
        original_request_json = resolver.request_json
        original_actor_detail = resolver.actor_detail
        try:
            def request_json(url):
                requested.append(url)
                return {"data": [{
                    "id": "9", "name": "夢乃あいか", "provider": "XsList",
                    "aliases": ["ゆめのあいか"]
                }]}
            resolver.request_json = request_json
            resolver.actor_detail = lambda result: {
                **result, "homepage": "", "images": [], "birthday": "1994-08-25",
                "debut_date": "", "blood_type": "", "cup_size": "",
                "measurements": "", "nationality": "日本", "height": 0,
                "hobby": "", "skill": "", "summary": ""
            }
            record = resolver.resolve("夢乃愛華", refresh=True)
        finally:
            resolver.request_json = original_request_json
            resolver.actor_detail = original_actor_detail
        self.assertIn("q=%E5%A4%A2%E4%B9%83%E3%81%82%E3%81%84%E3%81%8B", requested[0])
        self.assertEqual("Aika Yumeno (JAP、1994、夢乃あいか)", record["name"])


if __name__ == "__main__":
    unittest.main()
