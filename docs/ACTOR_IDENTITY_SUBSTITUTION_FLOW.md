# Actor scraping, enrichment, publication, and Emby delivery

Updated 2026-09-29. Read with the [stack and host map](METATUBE_STACK_ARCHITECTURE.md).

**Two different flows exist:** ordinary Emby actor metadata/image lookup, and
database-backed **Identify & Publish**. The second includes canonical identity
maintenance, INI generation, whole-table delivery and Emby refresh. A successful
MetaTube lookup alone does not prove publication ran or Emby saved an image.

This replaces the obsolete description of DB-to-INI automation as unimplemented.
The automation exists in the Windmill repository. This review checked source,
live container placement, mounts and caller paths; it did **not** run a live
publication, restart Emby, change actors or verify every deployed script/DLL.

## 1. Normal Emby actor Identify / metadata refresh

```mermaid
flowchart TD
  E["Emby Person: Identify or Refresh"] --> P["MetaTube plugin ActorProvider"]
  P --> Q{"Existing provider and actor ID?"}
  Q -->|No| S["MetaTube2 actor search by name"]
  S --> C["Manual selection or automatic first result"]
  Q -->|Yes| D["MetaTube2 actor details"]
  C --> D
  D --> R["Provider implementation / cached details"]
  R --> U["External actor provider"]
  R -->|When required| B["Bridge2 / FlareSolverr2"]
  B --> U
  D --> M["Plugin maps metadata to Emby Person"]
  M --> SAVE["Emby stores metadata and provider IDs"]
  SAVE --> I["ActorImageProvider requests portraits"]
  I --> IMG["MetaTube image endpoint to image source"]
  IMG --> FILE["Emby downloads and stores Primary portrait"]
```

- Emby is container `EmbyServer` on Kraken, service IP `192.168.10.151:8096`.
  Its dedicated MetaTube service is `192.168.10.167:8080`.
- Plugin source `ActorProvider.cs` searches when no usable provider identity
  exists; an existing identity can go straight to details. Search previews and
  applying the selected actor are separate requests.
- SDK endpoints: `/v1/actors/search` and `/v1/actors/{provider}/{id}`. Results can
  include aliases, birthday, measurements, nationality and image URLs. The
  plugin maps supported fields, not necessarily every returned field.
- `ActorImageProvider.cs` is separate: it needs a saved provider identity and
  offers **Primary** actor portraits. Preview images are not proof of a final
  Person image download.
- Direct HTTP, cache, provider adapters and browser-solver fallback are
  conditional paths, not a mandatory bridge/solver chain for every actor.
  Movie scan provider order is not an actor-provider order contract.
- SDK actor sources include AV-LEAGUE, Minnano-AV, XsList and GFriends. In
  `engine/actor.go`, all-provider actor search fans out concurrently to registered
  actor providers under their throttles, then sorts results by provider priority;
  it is not sequential first-match movie scanning. When enabled, database
  fallback can contribute cached results.
- Successful Japanese-provider actor details can additionally trigger
  **GFriends portrait injection**. A GFriends call alongside another selected
  actor provider is therefore expected, not necessarily an extra identity match.
- Custom resolver integration can additionally canonicalize names during
  movie/Person processing. Resolver cache/overrides are not the canonical Actor
  DB. Match the installed DLL/configuration to source before claiming exact
  deployed behavior.

## 2. What starts database enrichment and publication?

| Entry point | Behavior | Boundary |
| --- | --- | --- |
| Actor browser `:8093`, Identify & Publish | Explicitly submits a Windmill publication job | Pass the exact Emby Person ID. Distinct from ordinary metadata lookup. |
| Native Emby Identify + `jav-actor-identify-watcher` | Watches `RemoteSearch/Apply` log entries, resolves the Person and queues publication with durable pending/offset state | Best-effort log integration, not a native transactional webhook. Check actual submission and job ID. |
| Explicit Windmill invocation | Supplied identity, aliases, Person ID, optional duplicate IDs and dry-run flag | Current canonical flow defaults `dry_run=true`; a preview is not applied changes. |
| JAV Master Actors UI / other consumers | May read/edit data or invoke their own integrations | Do not assume every editor Save publishes the INI; verify its explicit publish action. |

### Verified routing drift

The **live** actor browser and watcher on 2026-09-29 still submit to workspace
`homelab`, flow **`f/jav_actor_db/publish_actor_substitutions`**:

```text
POST /api/w/homelab/jobs/run/f/f/jav_actor_db/publish_actor_substitutions
```

Current Windmill source lives at
**`f/jav_master_app/actor_db/publish_actor_substitutions.flow/flow.yaml`**.
The sequence below describes this source. Deployed equivalence or an old-path
compatibility flow was **not verified**. Compare the deployed flow before moving
callers; update browser, watcher and scoped token permissions together.
The separate Emby Windmill UI/API on `:7810` has its own integration/workspace
and is not a required hop for actor-browser publication.

## 3. Full Identify & Publish sequence

```mermaid
flowchart TD
  T["Explicit publish / watcher"] --> W["Windmill on Unraid .150"]
  W --> A["1 Import exact Emby Person"]
  A --> B["2 Enrich from MetaTube and resolver"]
  B --> DB["3 Upsert canonical Actor DB record and aliases"]
  DB --> INV["4 Inventory Emby People for mapping coverage"]
  INV --> DUP["5 Consolidate explicitly supplied duplicates"]
  DUP --> INI["6 Render complete deterministic INI"]
  INI --> GH["7 Publish changed artifact to GitHub"]
  GH --> BR["8 Bridge file delivery and plugin configuration API"]
  BR --> RE["9 Restart only on change; wait ready"]
  RE --> RF["10 Refresh exact Emby Person"]
  RF --> SY["11 Restore canonical identity and verify stable name"]
  SY --> TEL["12 Record success / idempotent telemetry"]
```

All script names below are in `f/jav_master_app/actor_db`.

| Stage / script | Responsibility and evidence |
| --- | --- |
| `import_actor_from_emby` | Import existing facts/aliases while retaining the exact Person identity. |
| `refresh_actor_from_metatube` | Search/details from the resource-configured MetaTube URL; call resolver `/resolve?refresh=true`. Can also fetch JavDB aliases using an existing external actor profile, outside the SDK provider path. Merge identity/profile evidence into Actor DB. Do not assume this resource always selects MetaTube2. |
| `upsert_actor_substitution` | Store canonical name, country/year and confirmed aliases; explicit supplied identity fields participate in precedence. |
| `sync_emby_actor_inventory` | Inventory Western-named Emby People for mapping coverage, not just the edited actor. |
| `consolidate_emby_actor_people` | Reassign movie references before retiring explicitly supplied duplicate People. Empty duplicate list is not blanket cleanup authorization. |
| `render_actor_substitutions` | Live export reads `actor_effective_substitutions`; validates/sorts mappings and returns content, count and SHA-256. Dry-run overlays proposed mappings onto the existing Kraken INI, so it is not identical to live DB export. |
| `publish_substitutions_to_github` | Commit only changed content. Repository/ref/path are resource-configured; default filename `JAV-ACTOR-SUB.ini`. An old SDK snapshot is not authoritative. |
| `deploy_actor_substitutions` | POST content/hash/revision to bridge `/v1/actor-substitutions/deploy`; compare hash. Also attempt complete replacement through Emby's plugin Configuration API. Check `live_config_verified` separately from `verified`. |
| `reload_emby_after_substitution` | Current flow sets `restart_on_change=true`: changed delivery restarts `EmbyServer`; unchanged skips restart. Both check readiness. |
| `refresh_emby_person` | Refresh exact Person after verified delivery/readiness. Accepted request is not completed refresh. |
| `sync_actor_to_emby` | Wait for settling; restore canonical name, IDs/aliases and Also known as line while retaining the rest of the biography; verify stable name over a time window. |
| `record_actor_flow_telemetry` | Record unique root-job success/idempotent replay and change flags in Actor DB. Final-stage telemetry is not a complete failure log for all preceding steps. |

## 4. Database -> INI -> Actor substitution table

**Edit authoritative Actor DB -> publish -> render full export -> GitHub artifact
-> bridge -> replace entire Emby MetaTube table -> reload / refresh / verify.**
This is not append-only upload.

Bridge targets under Kraken's existing EmbyServer tree:

```text
/mnt/cache_nvme_apps/appdata/EmbyServer/
  metadata/temp/JAV-ACTOR-SUB.ini
  plugins/configurations/MetaTube.json
  plugins/configurations/MetaTube.xml
```

The publication bridge is maintained in Actor DB's
`ops/homelab-identity/metatube_provider_bridge.py`. It validates the hash,
backs up existing files, updates active INI/configuration representations and
reports verification. Per-file writes and a process-local lock are **not** one
distributed transaction across DB, GitHub and Emby. Exception rollback is
limited to available backups; inspect individual targets after failure.

```text
EnableActorSubstitution = true
ActorRawSubstitutionTable = complete generated INI text
```

Movie actor-list substitution uses case-insensitive exact alias matching before
canonical resolution/Person creation. Replacing the table does not rewrite all
existing Emby People/movies retroactively; wider cleanup is a separate job.

**Suppression caveat:** the plugin supports `alias=` to omit an actor, but the
current Windmill renderer rejects empty canonical targets and its preview omits
blank mappings. Do not claim legacy suppressions survive automatic export.
Reconcile suppression policy and test case-insensitive alias collisions before
relying on full replacement of a table containing exclusions.

**Shared writer caveat:** bridge1 and bridge2 have separate state directories,
but both live containers mount these same Emby configuration directories.
Separate lookup stacks do not isolate actor-table writers. Serialize publication
for this Emby target; do not run competing bridge jobs.

## 5. Data stores and end-state verification

| Store | Owns | Does not prove |
| --- | --- | --- |
| Actor PostgreSQL 17, Kraken `:5433` | Canonical actors, aliases, profiles/evidence, export views and publication telemetry | Emby loaded the table or downloaded a portrait. |
| MetaTube1/2 PostgreSQL 15 | Separate SDK/provider caches | Canonical actor editorial authority or workflow history. |
| Windmill PostgreSQL 16, Unraid `:5434` | Jobs, steps and workflow state | Correct final Emby Person data. |
| Resolver cache/overrides, Kraken `:9211` | Resolution and configured overrides | Automatic synchronization of every canonical DB edit. |
| Emby data and people folders | Saved Person/movie relationships and portraits | Complete actor-source enrichment in Actor DB. |
| Generated INI / GitHub revision | Published mapping snapshot | Plugin in-memory application or completed refresh. |

For one actor, check Windmill step results, DB identity, export hash/revision,
bridge per-target hashes, live plugin configuration result, readiness/restart
outcome, exact Person's final name/aliases/provider IDs and retrievable portrait.

The deploy script can return bridge `verified=true` after an Emby Configuration
API HTTP failure, with `live_config_verified=false`. That is **not** fully
verified plugin runtime state. File hashes, HTTP readiness and correct final
Person data are distinct checkpoints.

Keep the current **legacy flat** EmbyServer people layout. No nested migration,
filesystem deletion, direct Emby DB rewrite or global cleanup is included here.

## 6. Where to inspect failures

- **Emby:** plugin metadata/image logs plus exact Person ID. Separate search,
  selected-result application, refresh and image download.
- **MetaTube2 Admin:** actor lookup traces and individual provider errors;
  successful fallback need not mean every provider succeeded.
- **Watcher/browser:** Identify detection, pending state, submission errors and
  returned Windmill job ID.
- **Windmill `homelab`:** complete job/step outputs for publication, reload,
  refresh and final sync. Ordinary Emby lookup may have no Windmill job.
- **Bridge/resolver:** per-target hash errors and source/cache decisions.
  FlareSolverr is relevant only when a request uses it.
- **Graylog1 .155:** application GELF and container context. Graylog2 .153 is
  system/syslog. Uncorrelated service lines are context, not actor-run evidence.

Admin1's `2026.09.28.1` contextual actor-log slice was deployed on 2026-09-29.
This does not mean Admin2 has the same release or all components share one
durable trace. See [deployment log](DEPLOYMENT_LOG.md).
No end-to-end publication was executed for this documentation review.

## 7. Canonical sources

- [Windmill flow/scripts](https://github.com/kinlshum/homelab_windmill/tree/main/f/jav_master_app/actor_db): orchestration/export/publication. Reviewed local source at `65bbf14`; deployed old-path equivalence remains unchecked.
- [Actor DB repository](https://github.com/kinlshum/homelab_jav-actor-db): canonical schema, actor data and operations. Historical docs may retain old hosts/namespaces.
- [Identify watcher](https://github.com/kinlshum/homelab_jav-actor-db/blob/main/ops/actor-identify-watcher/watcher.py): native Identify integration and old-path caller.
- [Publication bridge](https://github.com/kinlshum/homelab_jav-actor-db/blob/main/ops/homelab-identity/metatube_provider_bridge.py): INI/config delivery, distinct from the SDK generic bridge source.
- [Plugin repository](https://github.com/kinlshum/homelab_jellyfin-plugin-metatube): ActorProvider, ActorImageProvider, MovieProvider, configuration and substitution parser; match source to installed DLL before claiming deployed equivalence.
- This SDK repository owns actor APIs/providers, Admin and this stack map.
  `metatube-work/` snapshots and legacy hand-push scripts are historical
  references, not the canonical DB-driven publication source.
