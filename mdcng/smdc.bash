#!/usr/bin/env bash

# Query MDC-NG for FC2 metadata using a temporary, disposable placeholder file.
set -euo pipefail

MDC_SSH="${MDC_SSH:-root@192.168.10.170}"
MDC_CONTAINER="${MDC_CONTAINER:-MDC-NG}"
WAIT_SECONDS="${MDC_WAIT_SECONDS:-900}"
POLL_SECONDS="${MDC_POLL_SECONDS:-3}"
PROGRESS_SECONDS="${MDC_PROGRESS_SECONDS:-10}"

die() {
  printf 'smdc: %s\n' "$*" >&2
  exit 1
}

[[ $# == 1 ]] || die "usage: smdc.bash FC2_NUMBER_OR_FILENAME"
command -v jq >/dev/null 2>&1 || die "jq is required"
command -v python3 >/dev/null 2>&1 || die "python3 is required"
command -v ssh >/dev/null 2>&1 || die "ssh is required"

input=$(printf '%s' "$1" | tr '[:lower:]' '[:upper:]')
if [[ $input =~ FC2[-_[:space:]]*(PPV[-_[:space:]]*)?([0-9]+) ]]; then
  number=${BASH_REMATCH[2]}
elif [[ $input =~ ^[[:space:]]*([0-9]+)[[:space:]]*$ ]]; then
  number=${BASH_REMATCH[1]}
else
  number=
fi
[[ $number =~ ^[0-9]+$ ]] || die "cannot find an FC2 number in: $1"
[[ $WAIT_SECONDS =~ ^[0-9]+$ ]] || die "MDC_WAIT_SECONDS must be a whole number"
[[ $POLL_SECONDS =~ ^[1-9][0-9]*$ ]] || die "MDC_POLL_SECONDS must be a positive whole number"
[[ $PROGRESS_SECONDS =~ ^[1-9][0-9]*$ ]] || die "MDC_PROGRESS_SECONDS must be a positive whole number"

lookup_started=$SECONDS
next_progress=$((SECONDS + PROGRESS_SECONDS))
progress() {
  if [[ -t 2 && -z ${NO_COLOR:-} ]]; then
    printf '\033[0;32msmdc: FC2-%s:\033[0m \033[0;33m%s\033[0m\n' "$number" "$*" >&2
  else
    printf 'smdc: FC2-%s: %s\n' "$number" "$*" >&2
  fi
}
progress_waiting() {
  local stage=$1
  if (( SECONDS >= next_progress )); then
    progress "$stage ($((SECONDS - lookup_started))s elapsed)"
    next_progress=$((SECONDS + PROGRESS_SECONDS))
  fi
}

remote_api() {
  local method=$1 endpoint=$2 body=${3-} remote
  printf -v remote \
    'ip=$(docker inspect -f '\''{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'\'' %q) || exit; curl -fsS -X %q' \
    "$MDC_CONTAINER" "$method"
  if [[ -n $body ]]; then
    printf '%s' "$body" | ssh "$MDC_SSH" \
      "$remote -H 'Content-Type: application/json' --data-binary @- \"http://\$ip:9207$endpoint\""
  else
    ssh "$MDC_SSH" "$remote \"http://\$ip:9207$endpoint\""
  fi
}

temp_name=".smdc-query-${number}-$(date +%s)-$$"
host_dir="/mnt/user/downloads/$temp_name"
container_dir="/downloads_kraken/$temp_name"
host_file="$host_dir/FC2-PPV-$number.mp4"
container_file="$container_dir/FC2-PPV-$number.mp4"
quoted_host_dir=$(printf '%q' "$host_dir")
quoted_host_file=$(printf '%q' "$host_file")

cleanup() {
  ssh "$MDC_SSH" "rm -rf -- $quoted_host_dir" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

progress "preparing temporary MDC query on $MDC_SSH"
ssh "$MDC_SSH" \
  "mkdir -p -- $quoted_host_dir && ffmpeg -loglevel error -f lavfi -i color=c=black:s=16x16:d=1 -an -c:v mpeg4 -y $quoted_host_file && truncate -s 101M $quoted_host_file && chmod 777 $quoted_host_dir && chmod 666 $quoted_host_file"

marker="smdc-$number-$(date +%s)-$$"
payload=$(jq -cn --arg path "$container_file" --arg target "$container_dir" \
  --arg marker "$marker" \
  '{pathes:[$path],target_folder:$target,link_mode:3,
    delete_empty_parent_after_move:false,ts_id:$marker,copy_config_from:null}')
remote_api POST /api/manual-jobs "$payload" >/dev/null
progress 'query submitted; waiting for MDC job'

job_id=""
deadline=$((SECONDS + WAIT_SECONDS))
while [[ -z $job_id && $SECONDS -lt $deadline ]]; do
  jobs=$(remote_api GET '/api/manual-jobs?page=1&page_size=25')
  job_id=$(jq -r --arg path "$container_file" \
    '.data | map(select(.source_pathes | contains($path))) | first | .id // empty' <<<"$jobs")
  if [[ -z $job_id ]]; then
    progress_waiting 'waiting for job registration'
    sleep "$POLL_SECONDS"
  fi
done
[[ -n $job_id ]] || die "MDC-NG did not return the query job before timeout"
progress "job $job_id registered; metadata processing started"

while ((SECONDS < deadline)); do
  job=$(remote_api GET "/api/manual-jobs/$job_id")
  status=$(jq -r '.status // empty' <<<"$job")
  [[ $status == 2 ]] && break
  progress_waiting "metadata processing (status ${status:-unknown})"
  sleep "$POLL_SECONDS"
done
[[ ${status:-} == 2 ]] || die "MDC-NG query job $job_id timed out"
progress "metadata processing finished ($((SECONDS - lookup_started))s elapsed)"
errors=$(jq -r '.error_count // 0' <<<"$job")
if ((errors != 0)); then
  tasks=$(remote_api GET "/api/tasks?page=1&page_size=10&manual_job_id=$job_id")
  task_error=$(jq -r '.data[0].error_message // "unknown provider error"' <<<"$tasks")
  printf 'MDC-NG: no valid metadata for FC2-%s (%s).\n' "$number" "$task_error" >&2
  fallback="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/sfc2.bash"
  if [[ -x $fallback ]]; then
    printf 'Falling back to FC2CMADB...\n' >&2
    "$fallback" "$number"
    exit $?
  fi
  die "FC2CMADB fallback script is not installed next to smdc.bash"
fi

nfo=$(ssh "$MDC_SSH" "find $quoted_host_dir -maxdepth 1 -type f -iname '*.nfo' -print -quit")
[[ -n $nfo ]] || die "MDC-NG returned no metadata for FC2-$number"
progress 'reading actor metadata'
quoted_nfo=$(printf '%q' "$nfo")
python3 - "$number" 3< <(ssh "$MDC_SSH" "cat -- $quoted_nfo") <<'PY'
import os
import sys
import xml.etree.ElementTree as ET

number = sys.argv[1]
with os.fdopen(3) as nfo:
    root = ET.fromstring(nfo.read())

def one(*names):
    for name in names:
        node = root.find(name)
        if node is not None and node.text and node.text.strip():
            return node.text.strip()
    return "(not listed)"

def many(*names):
    values = []
    for name in names:
        for node in root.findall(name):
            if node.text and node.text.strip() and node.text.strip() not in values:
                values.append(node.text.strip())
    return ", ".join(values) or "(not listed)"

print("Source: MDC-NG")
print(f"Number: FC2-{number}")
print(f"Title: {one('title', 'originaltitle')}")
print(f"Original title: {one('originaltitle')}")
print(f"Date: {one('premiered', 'releasedate', 'date')}")
print(f"Runtime: {one('runtime')}")
print(f"Studio: {one('studio', 'maker')}")
print(f"Director: {many('director')}")
print(f"Actors: {many('actor/name')}")
print(f"Genres: {many('genre', 'tag')}")
print(f"Plot: {one('plot', 'outline')}")
PY
