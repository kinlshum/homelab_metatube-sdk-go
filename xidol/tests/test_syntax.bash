#!/usr/bin/env bash

set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)
bash -n "$root/xidol/xidol.bash"
bash -n "$root/xidol/xidol-copy.bash"
bash -n "$root/mdcng/smdc.bash"
bash -n "$root/mdcng/sfc2.bash"
