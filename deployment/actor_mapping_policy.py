"""Pure reviewed-identity adapter, bundled with immutable dictionary bytes.

No network, database writes, Person deletion or INI publication here. The
Windmill producer applies the result through its existing guarded transaction.
This first runtime adapter implements reviewed identity/alias rules, not the
entire eight-source biography/discovery specification.
"""
import copy
import hashlib
import html
import json
import re
import unicodedata
from pathlib import Path


def load_dictionary():
    raw = globals().get("BUNDLED_DICTIONARY_JSON")
    if raw is None:
        raw = (Path(__file__).resolve().parents[1] / "docs/actor-mapping/dictionary.json").read_text()
    contract = json.loads(raw)
    if contract.get("contract_version") != "1.0.0":
        raise ValueError("unsupported_actor_dictionary_version")
    return contract, hashlib.sha256(raw.encode()).hexdigest()


def key(value):
    return " ".join(unicodedata.normalize("NFKC", str(value or "")).split()).casefold()


def reviewed_mapping(name):
    contract, _ = load_dictionary()
    matches = []
    for mapping in contract.get("reviewed_identity_mappings", []):
        if key(name) in {key(v) for v in mapping["unapproved_identity_labels"]}:
            raise ValueError("needs_review: unapproved dictionary identity label")
        accepted = [mapping["japanese_name"], mapping["western_name"],
                    mapping["preserve_display_name"], *mapping.get("legacy_display_names", []), *mapping["historical_aliases"]]
        if key(name) in {key(v) for v in accepted}:
            matches.append(mapping)
    if len(matches) > 1:
        raise ValueError("needs_review: ambiguous dictionary identity")
    return copy.deepcopy(matches[0]) if matches else None


def filter_aliases(mapping, values):
    accepted = {key(v): v for v in mapping["historical_aliases"]}
    identities = {key(mapping["japanese_name"]), key(mapping["western_name"]),
                  key(mapping["preserve_display_name"]),
                  *(key(v) for v in mapping.get("legacy_display_names", []))}
    rejected = sorted({str(v).strip() for v in values if v and
                       key(v) not in accepted and key(v) not in identities})
    # The explicit user decision supplies these aliases even if a provider is
    # unavailable; DB suppression/ownership rules are still applied downstream.
    return list(accepted.values()), rejected


def apply_to_collections(mapping, prepared_import, prepared_enrichment, params):
    """Validate exact target and return copies; never mutate caller evidence."""
    imported, enriched, resolved = map(copy.deepcopy, (prepared_import, prepared_enrichment, params))
    if not mapping:
        return imported, enriched, resolved, None
    detail = imported["values"]["detail"]
    display = str(detail.get("Name") or "")
    # An old duplicate Person may not take over the canonical database link.
    # Reassignment/cleanup is a separately authorized operation.
    if not (key(display) in {key(mapping["preserve_display_name"]),
                            *(key(v) for v in mapping.get("legacy_display_names", []))} or
            (display.startswith(mapping["western_name"] + " (") and
             mapping["japanese_name"] in display)):
        raise ValueError("needs_review: run dictionary enrichment on the canonical Emby Person")
    raw_aliases = [*params.get("aliases", []), *imported["result"].get("aliases", []),
                   *enriched.get("result", enriched).get("aliases", [])]
    aliases, rejected = filter_aliases(mapping, raw_aliases)
    resolved.update(primary_japanese_name=mapping["japanese_name"],
                    western_name=mapping["western_name"], aliases=aliases,
                    country_code=mapping["country_code"], birth_year=mapping["birth_year"])
    imported["values"].update(primary_japanese_name=mapping["japanese_name"],
                              inferred_western=mapping["western_name"], country_code=mapping["country_code"],
                              resolved_birth_year=mapping["birth_year"])
    imported["result"].update(primary_japanese_name=mapping["japanese_name"],
                              western_name=mapping["western_name"], aliases=aliases)
    values = enriched.get("values")
    preview = enriched.get("result", enriched)
    preview.update(western_name=mapping["western_name"], aliases=aliases)
    notes = []
    if rejected:
        notes.append("Provider aliases not approved by the reviewed identity mapping: " + ", ".join(rejected))
    if values:
        values.update(japanese=mapping["japanese_name"], western=mapping["western_name"],
                      aliases=aliases, javdb_aliases=[], overview="")
        # Keep installed date on disagreement, and never estimate a date/year.
        installed_date = str(detail.get("PremiereDate") or "")[:10]
        if not re.fullmatch(r"(?:19|20)\d{2}-\d{2}-\d{2}", installed_date):
            installed_date = None
        candidate_date = values.get("selected_birth_date")
        if candidate_date and installed_date and candidate_date != installed_date:
            notes.append(f"Birth date: provider {candidate_date}; installed {installed_date} retained pending review.")
        conflicts = values.get("resolver_conflicts") or {}
        if conflicts:
            notes.append("Provider facts disagree: " + ", ".join(sorted(conflicts)) + ". Existing reviewed facts remain authoritative.")
        if "birthday" in conflicts or "birth_date" in conflicts:
            values["selected_birth_date"] = installed_date
            values["birthdays"] = []
        elif installed_date:
            values["selected_birth_date"] = installed_date
        if values.get("selected_birth_date"):
            values["birth_year"] = int(values["selected_birth_date"][:4])
        elif preview.get("birth_year_source") == "debut_year_minus_19":
            values["birth_year"] = None
        values["birth_year"] = mapping["birth_year"]
        preview["birth_year"] = mapping["birth_year"]
    preview["emby_name"] = mapping["preserve_display_name"]
    _, sha = load_dictionary()
    evidence = {"mapping_key": mapping["key"], "dictionary_sha256": sha,
                "contract_version": "1.0.0", "accepted_aliases": aliases,
                "held_aliases": rejected, "review_notes": notes,
                "expected_display_name": mapping["preserve_display_name"],
                "person_cleanup": "not_performed", "scope": "reviewed_identity_adapter"}
    preview["dictionary"] = evidence
    return imported, enriched, resolved, evidence


def render_review(overview, notes):
    """Replace only our marked section; preserve all other manual overview."""
    start, end = "<!-- actor-dictionary-review:start -->", "<!-- actor-dictionary-review:end -->"
    body = re.sub(re.escape(start) + r".*?" + re.escape(end), "", overview or "", flags=re.S).rstrip()
    notes = list(dict.fromkeys(notes))
    if not notes:
        return body
    section = "<br>".join(html.escape(note) for note in notes)
    return body + ("\n" if body else "") + start + "<div>---------------------<br>Needs review<br>" + section + "</div>" + end
