# One application release, two instance profiles

MetaTube1 and MetaTube2 use the **same application source, build tags, binary,
Admin UI, and packaged assets**. Do not maintain instance-specific code forks.
Differences belong to runtime properties and persistent state, not source edits.
The non-secret deployment inventory is [instances.json](instances.json).
The shared deployment driver is [deploy-shared-release.py](deploy-shared-release.py).

## Instance and dependency mapping

Observed on Kraken, 2026-10-03. Both servers listen on container port 8080.
The host stack is `/mnt/cache_nvme_apps/appdata/metatube-stack/compose.yaml`.
The repository [compose.yaml](compose.yaml) is a template, not permission to
overwrite the live host's credentials or independently maintained properties.

| Property | Instance 1 | Instance 2 |
| --- | --- | --- |
| Consumer | JAV Master pipeline | Emby |
| Compose service/container | `metatube` | `metatube2` |
| LAN endpoint | `192.168.10.166:8080` | `192.168.10.167:8080` |
| Public Admin | `metatube-admin.madtechinc.com` | `metatube-admin2.madtechinc.com` |
| Compatibility image tag | `kinlshum/metatube-server-providers:local` | `kinlshum/metatube-server-providers:emby` |
| Host /config directory under /mnt/cache_nvme_apps/appdata | `metatube-server-charleshuang233` | `metatube2-server` |
| DSN host (port 5432; database metatube) | `postgres` | `metatube2-postgres` |
| Database container | `metatube-postgres` | `metatube2-postgres` |
| Host database directory | `/mnt/user/appdata/metatube/postgres` | `/mnt/user/appdata/metatube2/postgres` |
| METATUBE_PROVIDER_BRIDGE_URL | `http://provider-bridge:9210` | `http://provider-bridge2:9210` |
| Bridge container | `metatube-provider-bridge` | `metatube2-provider-bridge` |
| Bridge host diagnostic port | 9210 | 9212 |
| Bridge /state directory relative to stack | `provider-bridge/state` | `provider-bridge2/state` |
| Bridge FLARE_URL | `http://flaresolverr:8191/v1` | `http://flaresolverr2:8191/v1` |
| Solver container | `metatube-flaresolverr` | `metatube2-flaresolverr` |
| Solver host diagnostic port | 8191 | 8192 |
| METATUBE_GELF_APPLICATION | `metatube` | `metatube2` |
| METATUBE_GELF_SERVICE | `metatube-server` | `metatube-emby` |
| METATUBE_EMBY_CLEANUP_CONFIG_FILE | unset / disabled | `/run/secrets/emby_cleanup.json` |
| Observed ordered movie search policy | disabled | enabled: AVBASE, JavBus, JAV321 |

The ordered search policy above is an observation, not a deployment default:
preserve each instance's current policy, throttles and provider priorities.
The same Emby-cleanup code is available in both builds, but instance 1 has no
Emby cleanup secret/configuration and must not silently inherit instance 2's.

Both applications join `br0` with the fixed LAN addresses above, and the
`metatube_internal` dependency network. Use Compose DNS service names for
dependencies, never their transient `172.22.*` addresses.

## Independent state versus intentionally shared integrations

- Each /config holds its own `traces.db`, `provider-throttles.json`,
  `movie-search-policy.json`, and `private/javbus-session.json`.
  Identical container paths do **not** mean shared host files. Never copy a
  cookie/session, database, scan order or throttle file to achieve code parity.
- Each bridge has separate /state and solver routing. Both solvers currently
  have separate Docker-managed /config volumes. Preserve these volumes.
- Both bridges currently use MDC at `http://192.168.10.170:9208`, the shared
  downloads mount `/mnt/user/downloads:/host-downloads`, and query roots
  `/host-downloads/.metatube-provider` and
  `/downloads_kraken/.metatube-provider`. These are **not fully isolated**.
- Both bridges currently mount the same Emby metadata/temp and plugin
  configuration directories under `/mnt/cache_nvme_apps/appdata/EmbyServer`.
  Their actor substitution INI target is
  `/emby-config/metadata/temp/JAV-ACTOR-SUB.ini`, plugin config target is
  `/emby-config/plugins/configurations/MetaTube.json`; state/backups remain
  under each bridge's own /state. A server code rollout must not write these.
- Graylog endpoints and host-only secret files are shared integrations.
  Instance-specific GELF application/service names distinguish traffic.
  Bridge credentials and Graylog tokens remain host-only; do not check their
  contents, Docker inspect dumps, cookies, or resolved DSNs into Git.

## Shared build and staged promotion

1. Review the source revision and working tree; record any working-tree build
   honestly. Select one release version and one release ID for both instances.
2. Run tests with production tags. **experimental is required** for AVBASE and
   AV-LEAGUE. A successful untagged test/build is not release acceptance.

   ```sh
   go test -tags experimental ./engine ./route -count=1
   go test -race -tags experimental ./provider/javbus -run '^Test(Age|Verification|Browser|Health)' -count=1
   node deployment/e2e/admin-javbus-session.js
   node deployment/e2e/chrome-session-unit.cjs
   ```

3. Build **once**, then copy the exact same binary into both staging directories:

   ```sh
   CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -tags experimental -trimpath \
     -ldflags "-s -w -X github.com/metatube-community/metatube-sdk-go/internal/version.Version=$RELEASE_VERSION -X github.com/metatube-community/metatube-sdk-go/internal/version.GitCommit=$SOURCE_LABEL" \
     -o "$RELEASE_DIR/runtime/metatube-server" ./cmd/server
   shasum -a 256 "$RELEASE_DIR/runtime/metatube-server"
   go version -m "$RELEASE_DIR/runtime/metatube-server"
   ```

   Set the three release variables explicitly. Docker's existing
   `make development` also includes experimental; bare `go build` does not.
   Existing Semaphore per-instance wrappers independently rebuild; they are
   legacy paths and do not prove build-once parity. Use this shared promotion
   process when requiring identical artifacts. Their host installation is
   not changed by adding this guide.

4. On Kraken create a private release directory per target with
   `mktemp -d /mnt/cache_nvme_apps/appdata/metatube-stack/RELEASE_ID.XXXXXX`.
   Copy runtime/, deploy-shared-release.py and instances.json there.
   Obtain the selected container's current image ID; pass it explicitly:

   ```sh
   python3 PRIVATE_RELEASE_DIRECTORY/deploy-shared-release.py \
     PRIVATE_RELEASE_DIRECTORY 2 EXPECTED_OLD_IMAGE RELEASE_VERSION RELEASE_ID
   # After instance 2 passes, repeat using a separate directory and instance 1.
   ```

   The driver checks the instance's database/bridge/solver routing, ports,
   mount paths and logging identity against the non-secret profile. It refuses
   image/environment drift, snapshots private rollback records and recreates
   only the selected server with --no-deps --no-build. It never copies profile
   values into the host configuration or restarts the dependency stack.
   Pause concurrent deployments/operator settings or cookie changes while
   acceptance compares state; a mismatch aborts the release.

5. Acceptance requires version/Admin availability; exactly the currently
   expected 31 provider rows including AVBASE(movie) and AV-LEAGUE(actor);
   preserved existing throttles, ordered policy, config/session fingerprints;
   unchanged environment/mounts and other container IDs/start times. Missing
   provider registration triggers rollback, even if /admin returns HTTP 200.
   Update the reviewed expected provider set when intentionally adding/removing
   providers; never simply relax a failing check.
6. Across both public Admin hosts compare version/source label, binary SHA256,
   rendered HTML SHA256, extension ZIP SHA256 and sorted provider names.
   Runtime settings/session health may legitimately differ. Compatibility image
   tags/base-layer history may give different image digests while application
   binary hashes match; record both rather than claiming identical images.
7. Append immutable evidence/rollback rows in
   [DEPLOYMENT_LOG.md](../docs/DEPLOYMENT_LOG.md). A failed acceptance restores
   only that target's previous image; investigate before promoting the other.
   A manual rollback retags the recorded target-specific rollback image and
   recreates only that same service with --no-deps --no-build.

Provider registration is not proof of live upstream scraping, questionnaire
clearance, real Chrome cookie import, or Emby Identify/image acceptance.
Those require separate explicitly recorded end-to-end tests.
