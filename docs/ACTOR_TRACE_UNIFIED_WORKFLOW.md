# Unified actor tracing and Romanized-name recovery

Release 2026.09.30.2 deployed to MetaTube2 on 2026-09-30 UTC. MetaTube1 was not
recreated. Deployment evidence belongs in DEPLOYMENT_LOG.md.

## Identity failure and correction

Person 922542 (今井美優) resolved only from AV-LEAGUE/Gfriends. Minnano's direct
HTTP request returned 403; the cached resolver result had no Latin alias. The
watcher rejected that Japanese-only name before enrichment, so there was no
canonical Actor DB row. Fix the pipeline rather than hardcoding that identity:

- Minnano 403/503 uses the configured solver; parse both structured data and H1
  pronunciation/Romanization. Keep source surname-first order explicit.
- Latin-name validation excludes handles, URLs, numeric account IDs and mixed
  prose. Reverse two-token names only for known surname-first sources.
- Expire unresolved results after 60 seconds and invalidate old parser caches.
- Unknown birth year is omitted, not represented with `?` in canonical labels.
- Japanese-only native Identify submits the exact Person to the normal guarded
  enrichment transaction. Missing Latin evidence fails closed for review.
- Preserve existing reviewed fields and distinct aliases. Never derive a name
  from a Twitter handle alone or silently equate Miyu and Miyuu across people.

## Trace contract

Actor DB remains authoritative. Each immutable publication request is a `publish`
trace with trace_id=request_id and run_id=save_request_id. Enrichment MetaTube
requests propagate X-MetaTube-Run-ID so their lookup traces can be grouped with
publication. Editor and mapping saves have their own publication trace even when
no provider lookup was needed. Existing unrelated lookup traces are not linked
by guessing from names.

Durable checkpoints in outbox evidence cover queued immutable INI, GitHub write,
file replacement/verification, playback deferral, reload verification/skipping,
exact Person writes and final Applied verification. Events include safe IDs,
hashes, origin and stable error codes, not credentials, biographies or raw INI.

`publication_status` is separate from lookup success and reporter presence.
Windmill+Emby events alone never mean Applied. Mapping-only requests truthfully
have no exact-Person verification target. File/restart/Person readback is not
direct inspection of the plugin's in-memory substitution table.

After releasing publication locks, the worker and minute drain mirror a bounded
batch to configured MetaTube Admin. Idempotency keys prevent duplicate events.
Acknowledgments live in additive `actor_trace_deliveries`, never in immutable
Applied receipts. Apply `database/actor_trace_delivery.sql` from the Actor DB
repository before enabling the mirror. A logging failure returns retry_pending;
it cannot mark publication failed or repeat publication writes.

The mirror covers the latest 100 receipts from seven days, five changed receipts
per tick; it is not a historical migration. Older receipts within that window
are labeled historical snapshots; no stage times are fabricated. MetaTube trace
retention/deletion is independent of durable Actor DB receipt retention.

The current trace header's Started/Completed values are **report-ingestion
times** for mirrored publications. Durable event `at` values are the actual
workflow checkpoint times; duration comes from the publication receipt. Do not
infer publication start from ingestion time. Collector requests carry the run
ID, but nested calls made internally by the resolver do not yet propagate it.
Uncorrelated service-log searches are explicitly not proof of run membership.

## Live acceptance: 今井美優

- Resolver source evidence yields **Miyu Imai**, not an independently verified
  `Miyuu Imai`. No hardcoded actor override or Twitter-handle transliteration.
- Full flow `01a0f0a4-0e17-e215-47b7-e6867767caf7` completed successfully in
  117.203 seconds. Publication request `f4b411f1-87d4-45ce-95cb-333fc58dcbf2`
  is Applied; grouped run ID `85d570e3-53c9-4626-9460-7c5db5cf981e` connects
  four collector lookups and the publication trace.
- Actor `e80d91f3-9068-4866-97c5-799a5fa3d362`, exact Emby Person `922542`,
  now reads `Miyu Imai (JAP、2002、今井美優)`; birth date `2002-08-22` is consistent
  with the selected year. Conflicting birthday/height/cup/measurement evidence
  is retained in one `provider_fact_conflict` review note. These biographical
  fields are source-selected, not claimed to be independently verified.
- Fresh Actor Editor search visibly shows the canonical name, two aliases
  (`今井美優`, `いまいみゆ`) and `# needs review: Provider facts disagree…`.
- 5,793 effective mappings equal GitHub, installed INI and plugin JSON/XML:
  `015ff86121dc70f1f187edc00e4836b29988dd9a10ccd36312b1c9cde2d48b4f`.
  All previous 5,791 mappings, seven holds and 4,239 inventory rows are unchanged.
- Trace drawer shows 11 publication events, observed application restart,
  verified exact Person and Applied proof; the full grouped run has five traces.
- Deployed watcher parsed the Japanese-only name with no invented Western name.
  Scoped-credential replay `01a0f0a9-5b45-1890-eb2d-efbbac745c42` returned the
  same Applied receipt, `trace_delivery.sent=0`, seven held events and no pending
  entries. This verifies the running queue integration without a new mutation.
- Private backups and machine-readable before/after reports are on Kraken in
  `/mnt/cache_nvme_apps/appdata/metatube-stack/actor-trace-20260930.AcnM8B/`.
  Secrets, raw database exports and Emby configuration are not committed.

## Regression gates

- 112 Windmill/actor tests plus seven subtests on disposable PostgreSQL, no skips.
- 17 resolver tests, including 403 solver recovery, heading parsing, unknown
  birth year, rejected social handles and preserved live alias behavior.
- Go internal/trace and route suites: publication cannot masquerade as lookup,
  reporter presence is not Applied, ingestion remains authenticated when enabled.
- Verify production version, publisher script hashes, one exact-Person canary,
  DB/INI/plugin file agreement, held mappings, and expanded actor trace UI.
