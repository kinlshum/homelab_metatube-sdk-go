"""Specification integrity checks only; these do not test production merging."""
import json
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.dictionary = json.loads((ROOT / "dictionary.json").read_text())
        self.template = json.loads((ROOT / "template.json").read_text())
        self.example = json.loads((ROOT / "aika-yumeno.example.json").read_text())

    def test_eight_distinct_sources(self):
        keys = [s["key"] for s in self.dictionary["sources"]]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(set(keys), {"AV-LEAGUE", "Minnano-AV", "JAVDatabase",
                                    "Babepedia", "Gfriends", "JAVDB", "JavLibrary", "XsList"})
        self.assertEqual(set(keys), {s["source"] for s in self.example["sources"]})

    def test_field_and_overview_references(self):
        fields = [f["key"] for f in self.dictionary["fields"]]
        self.assertEqual(len(fields), len(set(fields)))
        valid = set(fields + self.dictionary["derived_overview_rows"])
        self.assertTrue(set(self.dictionary["overview_order"]) <= valid)
        for claim in self.example["claims"]:
            self.assertIn(claim["field"], fields)
            self.assertTrue(set(self.dictionary["claim_required"]) <= set(claim))
        for source in self.example["sources"]:
            self.assertIn(source["state"], self.dictionary["source_states"])

    def test_name_and_dates(self):
        expected = self.example["expected"]
        self.assertEqual(self.dictionary["name"]["with_year"].format(**expected), expected["name"])
        self.assertEqual(self.dictionary["name"]["without_year"].format(**expected), expected["name_without_year"])
        birthday = date.fromisoformat(expected["birth_date"])
        debut = date.fromisoformat(expected["debut_date"])
        age = debut.year - birthday.year - ((debut.month, debut.day) < (birthday.month, birthday.day))
        self.assertEqual(age, expected["debut_age"])
        self.assertEqual(birthday.year, expected["birth_year"])

    def test_count_and_publication_boundaries(self):
        count_sources = [s["key"] for s in self.dictionary["sources"] if "source_movie_count" in s["roles"]]
        self.assertEqual(count_sources, ["JAVDB"])
        self.assertIsNone(self.example["expected"]["javdb_movie_count"])
        self.assertFalse(self.dictionary["movie_counts"]["historical_max_is_current"])
        self.assertFalse(self.dictionary["publication"]["source_failure_deletes_data"])
        self.assertEqual(self.template["publication"]["state"], "not_requested")
        self.assertFalse(self.example["expected"]["ini_contains_full_biography"])

    def test_versions_and_no_guessed_missing_ids(self):
        for document in (self.template, self.example):
            self.assertEqual(document["contract_version"], self.dictionary["contract_version"])
        for source in self.example["sources"]:
            if source["state"] != "matched":
                self.assertIsNone(source["id"])

    def test_review_section_is_last_and_not_an_alias(self):
        self.assertEqual(self.dictionary["overview_order"][-1], "needs_review")
        rule = self.dictionary["review_section"]
        example = self.example["expected"]["overview_review_section"]
        for key in ("position", "divider", "heading"):
            self.assertEqual(example[key], rule[key])
        self.assertTrue(rule["omit_when_empty"])
        self.assertTrue(rule["regenerate_not_append"])
        self.assertTrue(rule["escape_html"])
        self.assertFalse(rule["export_as_alias"])

    def test_reviewed_miyu_identity_and_alias_targets(self):
        fixture = json.loads((ROOT / "miyu-kanade.example.json").read_text())
        self.assertEqual(fixture["contract_version"], self.dictionary["contract_version"])
        mapping = next(m for m in self.dictionary["reviewed_identity_mappings"]
                       if m["key"] == fixture["reviewed_mapping_key"])
        expected = fixture["expected"]
        self.assertEqual(expected["name"], mapping["preserve_display_name"])
        self.assertEqual(expected["historical_aliases"], mapping["historical_aliases"])
        self.assertEqual(set(expected["ini_alias_targets"]), set(mapping["historical_aliases"]))
        self.assertEqual(set(expected["ini_alias_targets"].values()), {expected["name"]})
        self.assertTrue(set(expected["unapproved_identity_labels"]).isdisjoint(expected["ini_alias_targets"]))
        self.assertFalse(expected["old_profile_title_overwrites_canonical_name"])
        self.assertFalse(expected["alias_mapping_deletes_person"])

    def test_cleanup_is_separate_and_not_falsely_completed(self):
        policy = self.dictionary["identity_policy"]
        self.assertFalse(policy["alias_mapping_authorizes_person_deletion"])
        self.assertFalse(policy["delete_http_success_alone_is_completion"])
        self.assertIn("verified_deletion_readback", policy["person_cleanup_requires"])
        self.assertEqual(self.template["person_cleanup"]["state"], "not_requested")
        observation = json.loads((ROOT / "miyu-kanade.example.json").read_text())["deployment_observation"]
        self.assertEqual(observation["movies_relinked"], observation["already_linked_movies"] + observation["new_canonical_links"])
        self.assertEqual(observation["canonical_movie_count_after"], observation["canonical_movie_count_before"] + observation["new_canonical_links"])
        self.assertFalse(observation["deletion_readback_verified"])
        self.assertFalse(observation["video_files_moved_or_deleted"])


if __name__ == "__main__":
    unittest.main()
