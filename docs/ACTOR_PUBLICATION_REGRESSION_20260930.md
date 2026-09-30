# Actor publication release regression — 2026-09-30 UTC

Status: candidate testing in progress; **not final deployed acceptance**.
The previous Mai enrichment canary is evidence for the existing manual flow,
not proof that automatic Editor Save delivery is deployed.

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
Production already has `actor_alias_suppressions`; outbox is not installed yet.

## Required final deployed regression

- [ ] App coordinator reviews/integrates gated Save/status/retry candidate;
  exact module parity with canonical Actor DB, flag-off compatibility and stale
  browser response/draft preservation tests pass.
- [ ] Back up and explicitly apply new schema, verify no unrelated mapping
  changes, seed installed publication head only from verified external state.
- [ ] Deploy publication-only worker and request-ID-only resource-bound flow;
  runtime caller uses scoped credentials, not a deployment administrator token.
- [ ] Route legacy enrichment producers through the same publication lane;
  do not activate a second uncoordinated publisher or replay seven old events.
- [ ] Verify deployed bridge capability/auth/provider routes, rollback image,
  unchanged INI/config hashes and unchanged other service image/start times.
- [ ] Verify live Editor Save → committed DB/outbox → full INI/GitHub → plugin
  replacement/reload → exact Person metadata → fresh Editor read.
- [ ] Verify metadata-only Save, repeat-submit/status/retry, invalid/stale Save,
  dirty drafts, alias change/delete semantics and review-hold preservation.
- [ ] Smoke-test existing Actors, lookup, jobs and download routes on the final
  app deployment; verify old manual enrichment still preserves reviewed data.
- [ ] Record exact app/worker/bridge source and image IDs, backup location,
  test evidence and remaining limitations in release/deploy logs.

Never label file replacement alone as applied: direct plugin-memory table
readback is unavailable with the current SimpleUI/API-key route. Evidence must
state its real scope: file hashes, observed application restart when needed,
and exact Person stable readback. Do not interrupt active playback.
