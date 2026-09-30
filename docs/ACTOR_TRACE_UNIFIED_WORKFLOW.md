# Unified actor tracing and Romanized-name recovery

Release candidate 2026.09.30.2. Deployment evidence belongs in DEPLOYMENT_LOG.md.

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

## Regression gates

- 110 Windmill/actor tests plus seven subtests on disposable PostgreSQL.
- 17 resolver tests, including 403 solver recovery, heading parsing, unknown
  birth year, rejected social handles and preserved live alias behavior.
- Go internal/trace and route suites: publication cannot masquerade as lookup,
  reporter presence is not Applied, ingestion remains authenticated when enabled.
- Verify production version, publisher script hashes, one exact-Person canary,
  DB/INI/plugin file agreement, held mappings, and expanded actor trace UI.
