# Actor publication release regression — 2026-09-30 UTC

Status: deployed and accepted, 2026-09-30 UTC. JAV Master 2.1.76, the unified
outbox publisher and future-event watcher are live. Real enrichment, overview
Save/restore and mapping suppression/restore passed; complete effective state
was independently verified. Historical evidence below is retained chronologically.

## Verified before rollout

| Layer | Check | Result |
| --- | --- | --- |
| Canonical DB | Transaction rollback, immutable snapshots, duplicate Save, metadata-only Save, reassignment with unchanged INI, deletion/restore, alias tombstones, collision refusal, status/retry authorization boundary | 17 PostgreSQL regressions passed, zero skips, including fresh/repeated full-schema installation |
| Worker | Full sequence, metadata-only no restart, two rapid Saves, ordered predecessor, stale unqueued revision, exact Person, readback failure, drift, playback deferral, expired lease/uncertain restart, crash after write, advisory locks, unrelated-field preservation | 17 PostgreSQL + fake-API regressions passed, zero skips; no production API calls from this suite |
| Bridge | Authentication, full replacement/backup, rollback, checksum/duplicate validation, baseline CAS, retry, mixed files/disabled plugin | 8 isolated tests passed |
| Production-data preview | Read-only production snapshot copied into rollback-only test schema; new export semantics | 5,791 mappings before/after, zero changed targets, all 7 review holds preserved |

Preview counts: 1,713 actors, 3,468 aliases, 3,294 provider substitutions,
4,239 inventory records, 37 exact Person links; zero manual mapping decisions
or alias suppressions. SHA-256 before/after:
`507268bcb9cb289d8bb1f340c524d9189cfdb240ecc56796e1a37829fa32ffa3`.
At that pre-rollout checkpoint, production had `actor_alias_suppressions` but
the outbox was not installed. The completed migration is recorded below.

Broad Windmill actor suite: **72 passed + 7 subtests**, zero skips. Includes
the 17 new worker cases and existing importer/enrichment, INI export, review
preservation, inventory opt-in, reload, sync and watcher parser/backoff tests.
Fixed two test-harness defects exposed by running the whole suite together:
the watcher test referenced its pre-move repository path, and a sync unit test
overwrote the real psycopg row factory with a stub. No watcher was enabled.

## Required final deployed regression

- [x] App coordinator reviews/integrates gated Save/status/retry candidate;
  exact module parity with canonical Actor DB, flag-off compatibility and stale
  browser response/draft preservation tests pass.
- [x] Back up and explicitly apply new schema, verify no unrelated mapping
  changes, seed installed publication head only from verified external state.
- [x] Deploy publication-only worker and request-ID-only resource-bound flow;
  runtime caller uses scoped credentials, not a deployment administrator token.
- [x] Route legacy enrichment producers through the same publication lane;
  do not activate a second uncoordinated publisher or replay seven old events.
- [x] Verify deployed bridge capability/auth/provider routes, rollback image,
  unchanged INI/config hashes and unchanged other service image/start times.
- [x] Verify live Editor Save → committed DB/outbox → full INI/GitHub → plugin
  replacement/reload → exact Person metadata → fresh Editor read.
- [x] Verify metadata-only Save, repeat-submit/status/retry, invalid/stale Save,
  dirty drafts, alias change/delete semantics and review-hold preservation.
- [x] Smoke-test existing Actors, lookup, jobs and download routes on the final
  app deployment; verify old manual enrichment still preserves reviewed data.
- [x] Record exact app/worker/bridge source and image IDs, backup location,
  test evidence and remaining limitations in release/deploy logs.

Bridge-only rollout completed `2026-09-30T02:01:08Z`: source `c6058df`, image
`sha256:a2517e07a609bea8a65ff08a8ed26dd694979dc0697b8dcbf5f667f0a3c33ccb`.
Live unauthorized status=401; wrong-baseline blank-line-only candidate=409;
authenticated status and provider stats=200. INI/JSON/XML hashes unchanged.
Other three containers' image IDs and start timestamps match preflight.
Rollback image `kinlshum/metatube-provider-bridge:rollback-cas-c6058df`;
source backup and private live report under Kraken
`/mnt/cache_nvme_apps/appdata/metatube-stack/actor-cas-c6058df.HzpebJ/`.
No Emby restart, actor edit or automatic-publication activation in this rollout.

Fresh browser read after bridge rollout: live JAV Master is still `2.1.74`.
Actor Editor loads 5,791 mappings; searching Mai Takeda shows the verified
canonical group with 12 provider aliases, alongside separately flagged
inventory proposals. UI still truthfully says Save changes PostgreSQL only
and publishing is separate. This was read-only and is not the new Save-path
canary. Candidate source checkpoints: Actor DB `e82ffcf` (full-schema test
`43559c6`), Windmill `119a943`; app candidate remains with its coordinator.

Never label file replacement alone as applied: direct plugin-memory table
readback is unavailable with the current SimpleUI/API-key route. Evidence must
state its real scope: file hashes, observed application restart when needed,
and exact Person stable readback. Do not interrupt active playback.

## Unified runtime rollout

Production additive migrations applied with backup
`/mnt/cache_nvme_apps/appdata/actor-publication-20260930/jav_actor_db.before.dump`.
The new view retained all 5,791 mappings byte-for-byte and all 7 holds. Installed
head seeded from matching DB/GitHub/INI/JSON/XML plus the earlier observed
restart evidence; no invented plugin-memory readback.

Windmill source `0b5aa33`, binding correction `c983ebd`: provider collection
happens before the DB transaction. Import + enrichment + substitution writes
and immutable outbox enqueue then commit together. Both old and canonical
publication entrypoint names use this producer and the same publisher; direct
legacy GitHub/bridge publishing scripts are retired with recoverable backups.
No bulk inventory/consolidation occurs in this flow.

The Windmill-owned `f/jav_master_app/actor_db/publication_drain_tick` is enabled
every minute, with static resource bindings and no application runtime token.
It attempts only the oldest non-applied request, respects lease/backoff, stops
behind blocked/failed requests and reconciles uncertain delivery before writes.
Current worker head `587ba5c082e22d4c`, producer `bcd48b22672be0c0`, drain
`664343511048472a`. All are self-contained, source-hash-inventoried bundles.

Live tests:

- Empty drain `01a0f026-e8c0-14c7-6476-ffff3f78d737`: succeeded, idle.
- Enrichment `01a0f027-ce9a-0bea-93c3-43e993547fda`: committed one request,
  then exposed a Windmill default-argument binding defect before publication.
  Corrected to a literal default plus explicit flow input binding.
- Same saved request `0a449385-56c8-4046-8a15-532ce8c13b2b` resumed via
  `01a0f029-a754-cad5-fae7-19d59eb3a4f1`: applied, exact Person7759 verified,
  unchanged table hash; no re-enrichment or duplicate DB request.
- Corrected full flow replay `01a0f02b-2ee6-fd9c-bdb9-ddebabd0c0ff`: succeeded
  in 1.937s, same applied receipt. Existing watcher runtime credential replay
  `01a0f02d-261c-08bd-bcc7-125936f0abe2` also succeeded in 1.917s.
- Final backend suite after canonical compatibility-flow parity checks:
  **105 passed + 7 subtests**, zero skips, 32.41s. Windmill source `54c54b3`.

App2.1.75 is coordinator-owned; final forward/restore Editor canaries and
future-only watcher cutover are recorded below when verified, not inferred
from the backend tests.

Live Editor pre-save guard caught a lossless-edit issue: the existing overview
would be NFKC-normalized by Save. No Save occurred in that attempt. App 2.1.76
corrected free-text overview preservation, added exact-Unicode round-trip tests
and corrected the DB-only help text before the live canary proceeded.

## App 2.1.76 metadata-only live acceptance

Patch `5728f465d324` preserves biography Unicode/whitespace exactly and corrects
both editors' publication help. 24 app backend tests and 14 browser tests pass,
including exact-Unicode no-op/edit/restore/replay and publication enabled/legacy
response behavior; production build passes. Required Kraken deployment script
reported healthy. Owned scrape pause removed; independent browser checks found
Actors rows, Lookup controls, running Jobs and connected Downloads. Mapping
editor loads 5,791 mappings and review notes with corrected help, version 2.1.76.

Real authenticated overview Save on Mai Person7759:

| Leg | Publication request | Applied UTC | Result |
| --- | --- | --- | --- |
| Temporary overview marker | `bdda2070-62ed-4e48-b5d0-016efd98da97` | 2026-09-30 03:03:07 | Revision 83→84; same-payload replay returns original receipt; fresh Editor read matches; exact Person verified |
| Restore original overview | `053676d0-8a66-4961-b194-7ca5d13743c8` | 2026-09-30 03:05:07 | Revision 85; replay idempotent; original Unicode biography restored |

Independent read-only acceptance compared the complete effective DB mapping,
GitHub artifact, installed INI and plugin JSON/XML: all retain the baseline
SHA `507268bc…3ffa3` with 5,791 mappings, 7 holds and 4,239 inventory rows. Exact Person
name/birthday and overview SHA256 match the DB. All 3 outbox requests Applied.
These metadata-only requests correctly skipped restart using the verified
unchanged table. Private report: `actor-publication-20260930/editor-overview-acceptance.json`.
Live retry authorization returned 403 without the editor token and 409 for an
already-Applied request, leaving its stage unchanged.

## Changed-table mapping acceptance and final restoration

The existing, non-held `Mai Imai` alias was suppressed through authenticated
Mapping Save, then restored through `Use source`. Both legs returned identical
receipts on replay. No prior mapping decision/hold/suppression existed; actor
fields and all holds/suppressions were checked against the protected baseline.

| Leg | Request | Applied UTC | Verified result |
| --- | --- | --- | --- |
| Suppress one alias | `b3157574-337d-4be5-9582-760e7411e983` | 2026-09-30 03:07:15 | 5,790 mappings, SHA `464958cb0cfe310c85d88f284d2e7ab462d77aed927bb5f49529adc788b95870`; Git commit `08b3c16d1c421ba008961c76f98a7474d50a37ff`; matching installed files and observed application restart |
| Use source restore | `9d9681fb-ade6-4626-a47d-40da24314712` | 2026-09-30 03:08:14 | Original 5,791 mappings/SHA `507268bc…3ffa3`; Git commit `937b36019eeb5315158aa4c4588d872c5bc455a4`; matching installed files and observed application restart |

Both are table-only requests (`verified_person_ids=[]`), not Person mutations.
Audit history deliberately remains, including the revisioned `revert` decision.
Independent `final-acceptance.json` confirms all five requests Applied,
DB/GitHub/INI/JSON/XML equality, seven holds unchanged, 4,239 inventory rows,
and original exact Person7759 name/birthday/overview at actor revision85.
The worker checks playback before restart; no playback was interrupted.

## Native Identify watcher cutover

Started `2026-09-30T03:09:43.280607995Z`, source `c96d998`, image
`sha256:3ad133e910d02339e13e127305f2a768641472b73282d477bacd17bedcb3bfd7`.
Uses active Windmill `http://192.168.10.150:8001` and its existing scoped runtime
credential. Seven historical entries moved to `held_pending`; existing logs
baselined at EOF, zero active pending at cutover. Future events persist a UUID
and frozen input before submission. No old events were replayed.

In-container queue replay of the original enrichment request ran real job
`01a0f04a-5001-bbff-66d0-43805ffd2eb5`: both modules succeeded in2.029s and returned
the original Applied receipt, not a new mutation. Watcher running, restart count0,
no error events, seven held and zero pending. Parser/idempotency are covered by
the regression suite; no fabricated native Emby Identify event was injected.

Rollback: stopped old container
`jav-actor-identify-watcher-before-outbox-20260930` is retained with restart off;
private original state/container definitions and acceptance reports are under
`/mnt/cache_nvme_apps/appdata/actor-publication-20260930/`. Never re-enable the
old endpoint or replay its state implicitly. No People-folder migration or
unrelated actor cleanup occurred.

## Final app image inventory

Release2.1.76, source `5728f465d324`, both containers started2026-09-30 02:59:09UTC:

- API: `sha256:abff5c5c18db331535bff40ed451f9ae00981963beafd653781a3290047de664`.
- Web: `sha256:664d3429c44bd0039145b6cfa48c0179750d6fe7482eb330d16d0d3bf7050109`.

The complete installed table is verified via file hashes plus observed reload
when changed and exact Person readback, not a plugin-memory-table API. Editor
shows current DB state; delivery remains asynchronous, so check Applied status
before treating a new Save as installed. Actor cleanup/review is not complete
merely because publication is working.
