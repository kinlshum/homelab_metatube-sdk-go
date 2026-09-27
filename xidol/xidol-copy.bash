#!/usr/bin/env bash

# Copy a downloaded video file using the paired X-Idol code as its alias.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: xidol-copy.bash [-m | --dry-run] VIDEO_FILE_OR_CODE

Examples:
  xidol-copy.bash REBD-200.mp4
  xidol-copy.bash --dry-run /downloads/REBD-200.mp4
  xidol-copy.bash -m REBD-200

Looks up the paired code with xidol.bash -m and copies the source file beside
it. It never overwrites an existing destination file. With -m, it only prints
the paired filename and does not require a local file.
EOF
}

die() {
  printf 'xidol-copy: %s\n' "$*" >&2
  exit 1
}

dry_run=false
match_only=false
case ${1:-} in
  --dry-run) dry_run=true; shift ;;
  -m) match_only=true; shift ;;
esac
[[ $# == 1 ]] || { usage >&2; exit 2; }

source_input=$1

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
lookup="$script_dir/xidol.bash"
[[ -x $lookup ]] || die "xidol.bash is not executable: $lookup"

if [[ $match_only == true ]]; then
  exec "$lookup" -m "$source_input"
fi

[[ -f $source_input ]] || die "file not found: $source_input"

source_dir=$(cd "$(dirname "$source_input")" && pwd -P)
source_name=$(basename "$source_input")
[[ $source_name == *.* ]] || die "source file needs an extension: $source_name"
extension=${source_name##*.}
source_path="$source_dir/$source_name"

match_name=$("$lookup" -m "$source_name")
match_stem=${match_name%.*}
source_stem=${source_name%.*}
[[ ${match_stem^^} != ${source_stem^^} ]] ||
  die "X-Idol did not list an alternate code for: $source_name"

target_path="$source_dir/$match_stem.$extension"
[[ ! -e $target_path ]] || die "destination already exists: $target_path"

if [[ $dry_run == true ]]; then
  printf 'Would copy: %s\n' "$source_path"
  printf 'To: %s\n' "$target_path"
  exit 0
fi

cp -p "$source_path" "$target_path"
printf 'Copied: %s\n' "$target_path"
