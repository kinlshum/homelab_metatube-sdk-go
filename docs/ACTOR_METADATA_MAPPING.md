# Actor identification and metadata mapping contract

Specification version 1.0.0, 2026-09-30. This contract defines how actor
identification, external profile discovery, enrichment and manual edits produce
one canonical identity, overview and provider-ID set. It is a specification and
test fixture. Runtime deployment status is recorded separately below and in the
deployment log; the complete eight-source contract is not yet implemented.

## Runtime adapter checkpoint — 2026-09-30

Candidate implementation: `deployment/actor_mapping_policy.py` is loaded into
Windmill's deterministic producer bundle alongside the exact dictionary bytes
and SHA256. It recognizes reviewed identities, filters provider aliases against
the reviewed set, refuses an old duplicate Person as the canonical target,
preserves an installed conflicting birth date, and prepares idempotent escaped
review notes at the bottom of the overview. The existing transaction stores the
decision evidence and exact-Person snapshot together; publication traces gain an
`actor_dictionary_applied` event with safe version/hash/count details.

This adapter does **not** implement the complete eight-source discovery and
biographical merge checklist below. It does not delete Persons, move videos,
change provider order, bypass manual Editor decisions or start a second publisher.
The legacy debut-minus-19 birth-year estimate is removed from the candidate
collector; unknown years remain unknown.

The user approved `Miyu Kanade (JAP、1994、かなで自由)` as the canonical display;
the short `Miyu Kanade (かなで自由)` label is legacy input, not a preserved output.
The producer still fails closed and rolls back if the generated label differs
from the reviewed dictionary. Both conflicting full birthdays share the approved
year 1994; accepting that year does not resolve the day conflict. Old Person
cleanup is left to a subsequent user scan and must be verified, not assumed.

Use the [machine-readable dictionary](actor-mapping/dictionary.json),
[empty actor envelope](actor-mapping/template.json) and
[Aika Yumeno review fixture](actor-mapping/aika-yumeno.example.json) together.
The [publication flow](ACTOR_IDENTITY_SUBSTITUTION_FLOW.md) remains responsible
for transactional saves, immutable snapshots and verified delivery.

## Sources and discovery

The eight requested sources are AV-LEAGUE, Minnano-AV, JAVDatabase, Babepedia,
Gfriends, JAVDB, JavLibrary and XsList. They are independent namespaces, not
eight required successful responses. Gfriends is principally an image source.
JAVDatabase is not JAVDB. Only JAVDB supplies the source movie total.

For each source, first verify the existing stored profile ID. If missing or
invalid, search that source using the accepted Japanese name, reading,
Romanized name and reviewed aliases. If internal search fails, use a
domain-restricted external search to discover candidate profile URLs. Fetch
the actual profile: search snippets, guessed slugs and movie-page actor labels
alone must not become accepted IDs. Search is discovery, not identity proof.

Automatically accept a new profile only with an exact accepted name/alias plus
a corroborating fact (such as matching full DOB), or an authoritative direct
cross-link. Conflicting DOB/identity, common names, stage-name changes and
photo-only resemblance require review. An explicit manual confirmation may
resolve a candidate and must retain operator, reason and evidence. Multiple
profiles for a stage-name change remain separate linked records; do not combine
people because their names resemble one another.

Validate provider host and profile path, encode IDs as path/query components,
and validate redirects. Reject arbitrary internal URLs and credentials. Use
existing pacing, concurrency limits, bounded timeouts and authorized solver
fallback. Do not create accounts or bypass access restrictions. Record every
source as matched, not_found, unavailable, ambiguous or not_attempted. Missing
evidence is null, never a fabricated ID, zero count or empty overwrite.

## Evidence and merge rules

Every field claim retains provider, profile ID, URL, raw value, normalized
value, unit/system, observation time, effective date if supplied, and selection
reason. Scrape time does not establish when a biography changed. Preserve all
claims in evidence; select fields independently instead of choosing one whole
provider record or taking its first nonempty summary.

1. Preserve explicitly reviewed manual values and publication holds. A new
   disagreement creates a review item; it never silently overwrites them.
2. For unreviewed fields, prefer corroborated identity evidence and direct
   official profile evidence when available. Source order is a tie-breaker,
   not proof. Copied pages do not count as independent corroboration.
3. Normalize equivalent dates, whitespace and measurement units before checking
   conflicts. Different dated measurements can coexist; do not average them.
   Cup sizes retain their sizing system. Birthday is a date, not a timezone
   timestamp. Never infer birth year from debut age or appearance.
4. Material unresolved conflicts retain the installed/reviewed value. A new
   optional field remains null; a new unresolved identity blocks automatic
   identity publication. Safe unrelated fields can proceed with explicit
   partial/review status under the existing publication guards.
5. Empty/failed source responses never delete accepted facts, IDs or images.
   Deletion requires an explicit reviewed action with an audit record.

### Names

Store Western name, country code, birth date/year and Japanese name separately.
Render `Western Name (JAP、YYYY、日本語名)` only from accepted components. `JAP`
is this application's legacy display code; it is not an ISO code. Use an
explicit country-code mapping. Birthplace, language and a Japanese-looking
name do not establish nationality. If country or Western identity is unknown,
retain an existing accepted display name and request review; do not invent one.
Unknown year is omitted: `Western Name (JAP、日本語名)`.

Strip age suffixes such as `/32岁` only under recognized parser rules. Never
derive a Western name from a social handle. Reverse surname-first Romanization
only when the source's order is known, not every two-word name. Preserve valid
hyphens, apostrophes and accents; uncertain long vowels remain review evidence.
Keep aliases separate from social accounts and remove duplicate/self aliases
from the displayed Also known as line. Reapply alias suppression decisions.

`# needs review: <reason>` is an Editor annotation and, where supported, an INI
comment above the affected group. It must never be prepended to the actor's
actual name or alias key. Verify comments survive export/import round trips.

## Field and output mapping

### Reviewed identity: Miyu Kanade

The dictionary now records the user's 2026-09-30 canonical-identity decision;
see the [Miyu Kanade fixture](actor-mapping/miyu-kanade.example.json).

| Input label | Mapping decision |
| --- | --- |
| かなで自由 / Miyu Kanade | Canonical identity; publish `Miyu Kanade (JAP、1994、かなで自由)` |
| Miyu Kanade (かなで自由) | Legacy display label; overwrite through exact-Person publication |
| 白石みお | Historical alias → canonical identity |
| 白石未央 | Historical alias → canonical identity |
| 白石みお（白石未央） | Combined legacy label → canonical identity |
| 聖菜アリサ or the mixed 聖菜アリサ / 白石 label | Not approved as aliases here; hold for review, do not merge |

An accepted provider profile may use a historical alias as its heading. That
does not rename the reviewed canonical identity or create a separate active
actor. This decision does not automatically accept every alias returned by a
provider. Keep the conflicting February 13/14 birthday under review; this
alias correction does not authorize changing the installed full birthday. The
standard country/year name format was subsequently explicitly approved.

On the existing Emby server, 12 movies were reassigned to Person `8827`: seven
already had that credit and five gained it, resulting in 215 linked movies at
verification. Source Persons `874202` and `981097` have zero links but remain
readable after delete requests. Their deletion is **unconfirmed**, not complete.
The fixture records the backup receipt and historical counts; do not replay
these installation-specific IDs against another server or publish stale counts.

Alias/INI mapping and Person cleanup are separate operations. Cleanup requires
explicit authorization, verified identity, backups, verified credit transfer,
zero remaining references and deletion readback. An HTTP success alone is not
proof of deletion. No movie files were moved or deleted. These dictionary
fixture does not itself publish an alias table; the bundled workflow adapter
uses the existing guarded publication transaction.

The JSON dictionary contains every field below, its merge rule, canonical
storage target and output target. Existing database columns are identified
separately from structured facts requiring adapter work.

| Group | Fields | Output |
| --- | --- | --- |
| Identity | Western/Japanese names, country code, birth date/year | Emby Name, birth date, canonical INI target |
| Aliases | Accepted alternate names/readings | Also known as, JAVAlsoKnownAs, effective INI mappings |
| Debut | AV debut date, work, derived age | Overview and JAVDebutDate/JAVDebutTitle |
| Biography | Height, measurements, cup/system, blood, nationality, birthplace, agency, hobbies, skills, activity period, sign | Ordered overview rows and supported custom fields |
| Profiles | All verified source IDs and URLs, selected primary profile | ProviderIds, overview Links and Editor profile records |
| Social | Verified X, Instagram, blog and official profile links | Social IDs/links; never actor-name input |
| Images | Verified portrait candidates and selected/custom image | Separate exact-Person Primary image delivery |
| Counts | Emby linked movies; JAVDB actor catalogue total | `Emby / JAVDB movie(s)`; separate counts and freshness |
| Review | Conflicting facts and unresolved identity/profile details | Editor review panel, correlated traces and a final Needs review overview section; not identity strings |

Render overview rows in the dictionary's order. Omit unavailable optional rows,
escape HTML, and allow only verified safe links. Compute current age at render
time; compute debut age using the accepted debut date. Do not copy source age
text. Separate X from Blog. Optional biographies must be short factual summaries,
not concatenated promotional prose. Subjective provider tags require review;
do not import them automatically. Unknown counts display `?`, not zero.

### Needs review at the bottom of the overview

As requested, append unresolved user-facing review items **after every other
overview row, including Links**, using this exact divider and heading:

```text
---------------------
Needs review
Blood type: B (AV-LEAGUE, Minnano-AV) versus A (JAVDatabase, cached XsList).
Cup size: G versus H; source dates and sizing systems need reconciliation.
Measurements: 79–52–78 versus 95–52–78 cm.
JAVDB: Actor ID and movie total not yet verified.
JavLibrary: Actor ID not yet verified.
```

This is an example of provisional research findings, not a live Person update.
Use the current open review records to generate the section; include conflicting
values/source labels and whether the installed value was preserved. Missing
optional sources alone are not identity errors, but unresolved required ID/count
discovery can be listed as incomplete enrichment. Keep operational retry state
in the Editor/traces rather than inserting raw stack traces into biography.
Never include secrets, private infrastructure URLs or internal credentials.

Deduplicate review items by stable issue identity. Regenerate rather than append
on each enrichment/Save, preserving unrelated manual overview text. Resolved
issues disappear; omit the divider and heading when no open items remain.
Escape review text in HTML just like normal overview rows. Editor review notes
and this rendered section must originate from the same review records. Neither
the divider nor review prose is exported as an actor alias or INI target.

### Movie count rules

The denominator is the total on the **matched JAVDB actor catalogue**, not
AV-LEAGUE, JavLibrary or JAVDatabase, not matched-source count and not search
page size. Prefer an explicit validated total. If absent, count unique JAVDB
movie IDs only after traversing every page under an identical recorded filter.
An incomplete traversal cannot publish a total. Keep filter/scope, URL and
checked time. Cross-profile union is allowed only with accepted identity links
and movie-ID deduplication. Never sum potentially overlapping totals.

The numerator comes from Emby movies linked to the exact accepted Person ID(s),
deduplicated by Emby item ID with library scope recorded. These catalogues may
cover different editions; the ratio is a comparison, not proof of missing
files. No retrieval means null. An unavailable refresh preserves the last
verified value and marks it stale. A material decrease requires review;
historical maximum is separate and must not replace the current verified count.

## External IDs

Persist every accepted source profile in `actor_provider_profiles` with its
evidence and stage-name context. Maintain compatible primary entries in
`actor_external_ids` and `actor_site_profiles` through adapters. Do not overwrite
one source with another, or discard additional profiles because Emby exposes
only one field per source. Emby receives the accepted primary profile; the
Editor retains all profiles.

Normalize legacy key aliases at ingestion using the JSON dictionary. In
particular, `JavdbActor`, `JavDBActor` and `JAVDB` cannot be blindly treated as
equal when their values differ. Confirm they are actor IDs, reconcile values,
then use the plugin's supported output key. Build JAVDB URLs without appending
an unverified `.html` suffix. Keep MetaTube's selected provider routing ID
separate from database UUID and external IDs. Do not rewrite the routing ID
without validating the matching metadata and image routes.

## Database and publication contract

`jav_actor_db` is authoritative. Provider cache is evidence, not a second
editable canonical database. Actor Editor Save and enrichment use the same
field validation, revision checks, manual protection and publication outbox.

1. Collect outside the write lock; produce candidate evidence and field choices.
2. Under the existing actor writer/revision guard, persist accepted fields,
   IDs, evidence, aliases and review notes. Capture an immutable full INI plus
   exact Person metadata/ID snapshot and outbox entry in the same transaction.
3. Publish the INI as a **whole-table replacement**, preserving unrelated actors,
   suppression decisions and installed review holds. INI carries name mappings,
   not birthdays, full biography or arbitrary provider IDs.
4. The existing ordered worker verifies GitHub and plugin replacement, performs
   playback-safe reload only where needed, then synchronizes exact Person
   metadata/IDs and separately verifies the intended portrait. Preserve
   unrelated Emby IDs and manual image choices.
5. Read back exact name, accepted metadata, IDs and image state; record Applied
   only for verified stages. Actor Editor reloads the same canonical revision
   and shows saved/pending/applied, review and stale-source states separately.

Trace stages should include profile discovery, identity acceptance, field
selection/conflicts, canonical revision, INI hash, plugin replacement/reload,
Person metadata/IDs, image verification and Editor-visible revision. Record
safe correlation IDs and evidence references, not secrets or full source HTML.
Do not claim a frontend refresh without observing it; distinguish DB-visible
revision from browser-rendered confirmation.

## Aika Yumeno worked example

Read-only research on 2026-09-30 located six cached source profiles. JAVDB and
JavLibrary were absent from that cache and from her queried canonical profile
rows; this is not evidence that those sites lack her profile. A live resolver
request timed out after 55 seconds, so cached claims are explicitly labeled.

| Source | Profile | Evidence used in fixture |
| --- | --- | --- |
| AV-LEAGUE | [9657](https://www.av-league.com/actress/9657.html) | Japanese identity; August 26 birthday; 149 cm; B blood; G cup; 79/52/78; social accounts; conflicting February debut |
| Minnano-AV | [545220](https://www.minnano-av.com/actress545220.html) | Yumeno Aika; August 26 birthday; May AV debut; H cup; agency, hobbies and activity |
| JAVDatabase | [aika-yumeno](https://www.javdatabase.com/idols/aika-yumeno/) | Aika Yumeno; August 26 birthday; conflicting A blood and 95 cm bust |
| Babepedia | [Aika_Yumeno](https://www.babepedia.com/babe/Aika_Yumeno) | Cached matching identity/DOB and differently expressed measurements; not freshly retrieved |
| Gfriends | [repository](https://github.com/gfriends/gfriends) | Cached Japanese-name portrait candidates |
| JAVDB | Unresolved | No verified ID or total; do not substitute another catalogue |
| JavLibrary | Unresolved | No verified star ID; discover and verify before writing |
| XsList | [9](https://xslist.org/zh/model/9.html) | Cached name/aliases; August 25 DOB and A blood conflict |

Additional validation: the [manufacturer profile](https://tameikegoro.jp/actress/detail/245419)
supports 1994-08-26 and 149 cm; [Styley](https://www.styley.site/performer/yumeno_aika/)
supports May 7, 2013 debut and the social accounts. These are auxiliary evidence,
not additional mandatory resolver sources. Fixture choices are provisional,
not user-reviewed facts. Blood type, cup and measurements retain review state.

The fixture prevents two observed cached defects from becoming accepted output:
August 25 selected despite August 26 provenance, and Tokyo stored as nationality.
It also removes the age suffix from the name. Birthplace and nationality remain
separate; an eight-source completeness claim is not made from six matches.

## Implementation and acceptance checklist

- [ ] Add versioned field adapters and per-field evidence to resolver/collector;
      invalidate cache on mapping/parser changes and preserve raw evidence.
- [ ] Implement bounded JAVDB/JavLibrary and other missing-profile discovery;
      verify IDs before canonical upsert. Respect source throttles.
- [ ] Persist resolver-only IDs/facts, not only MetaTube detail rows.
- [ ] Share merge/name/overview rules across enrichment and manual Save;
      avoid the current first-summary behavior and inconsistent ID spellings.
- [ ] Extend snapshot/Person writer to carry accepted facts and IDs, preserve
      unrelated values and verify image application separately.
- [ ] Extend Editor/trace review, completeness and provenance views using the
      existing authorized cross-repository coordination workflow; render open
      review items at the bottom of Emby Overview without duplicate sections.
- [ ] Runtime tests: all eight matched; six matched/two unavailable; conflicting
      birthday; date-only round trip; protected edit; long-vowel/name ambiguity;
      invalid URL; alias suppression; multiple stage profiles; source timeout;
      partial count; explicit zero; count decrease; duplicate request; stale
      revision; lost publication acknowledgment; metadata-only no-restart;
      review section last, repeated Save deduplication, resolved-section removal,
      HTML escaping and preservation of unrelated manual overview text.
- [ ] Canary one approved existing actor through DB → full INI → plugin → exact
      Person metadata/IDs/image → fresh Editor; verify unrelated mappings
      unchanged, record rollback and update release/deploy logs only on shipment.

Validate the document artifacts with
`python3 -m unittest discover -s docs/actor-mapping -p 'test_*.py'`.
These checks test the specification's consistency, **not production merging**.
