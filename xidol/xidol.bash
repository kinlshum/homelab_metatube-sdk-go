#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage: xidol.bash [-m | --json] VIDEO_CODE_OR_FILENAME

Search public X-Idol metadata by video code.

Options:
  -m          Print only the alternate X-Idol match filename, when listed.
  --json      Print the scraped record as JSON.

Examples:
  xidol.bash FWAY-033
  xidol.bash 'REBD-1065.mp4'
  xidol.bash -m REBD-1065.mp4       # REBDB-1050.mp4
  xidol.bash --json FWAY-033
EOF
}

die() {
  printf 'xidol: %s\n' "$*" >&2
  exit 1
}

output_mode=text
case ${1:-} in
  -m) output_mode=match; shift ;;
  --json) output_mode=json; shift ;;
esac
[[ $# == 1 ]] || { usage >&2; exit 2; }
command -v curl >/dev/null 2>&1 || die 'curl is required'
command -v python3 >/dev/null 2>&1 || die 'python3 is required'

input=$1
code=$(python3 - "$input" <<'PY'
import re
import sys

value = sys.argv[1].strip().upper()
match = re.search(r'([A-Z]{2,12})[ _-]*(\d{2,7})(?!\d)', value)
if not match:
    raise SystemExit(1)
print(f"{match.group(1)}-{match.group(2)}")
PY
) || die "cannot find a video code in: $input"

encoded_query=$(python3 - "$code" <<'PY'
import sys
from urllib.parse import quote_plus
print(quote_plus(sys.argv[1]))
PY
)
api_url="https://x-idol.net/wp-json/wp/v2/search?search=${encoded_query}&per_page=100"
records=$(curl -fsSL --connect-timeout 10 --max-time 30 \
  -A 'Mozilla/5.0 (compatible; HomelabMetaTubeSDKGo/1.0)' "$api_url") ||
  die 'X-Idol request failed'

python3 - "$code" "$api_url" "$output_mode" 3<<<"$records" <<'PY'
import html
import json
import re
import sys

requested, source_url, output_mode = sys.argv[1:]
try:
    records = json.load(open(3, encoding='utf-8'))
except (json.JSONDecodeError, OSError) as error:
    print(f'xidol: invalid X-Idol API response: {error}', file=sys.stderr)
    raise SystemExit(4)

if not isinstance(records, list):
    print('xidol: unexpected X-Idol API response', file=sys.stderr)
    raise SystemExit(4)

code_pattern = re.compile(r'(?<![A-Z0-9])([A-Z]{2,12})[-_ ]*(\d{2,7})(?!\d)', re.I)

def codes_in(value):
    codes = []
    for prefix, number in code_pattern.findall(html.unescape(value).upper()):
        item = f'{prefix}-{number}'
        if item not in codes:
            codes.append(item)
    return codes

match = None
for record in records:
    title = html.unescape(str(record.get('title', '')))
    listed_codes = codes_in(title)
    if requested in listed_codes:
        match = (record, title, listed_codes)
        break

if match is None:
    print(f'xidol: no exact X-Idol match for {requested}', file=sys.stderr)
    raise SystemExit(3)

record, title, listed_codes = match
alternate = next((item for item in listed_codes if item != requested), requested)
name = re.sub(r'\s*\[(?:MP4|MKV|AVI|WMV)[^\]]*\]\s*$', '', title, flags=re.I)
name = re.sub(r'^\s*\[[^\]]+\]\s*', '', name)
filename = f'{alternate} - {name}'
filename = re.sub(r'[\\/:*?"<>|\x00-\x1f]', ' ', filename)
filename = re.sub(r'\s+', ' ', filename).strip(' .') + '.mp4'
data = {
    'source': record.get('url', source_url),
    'query': requested,
    'codes': listed_codes,
    'match': alternate,
    'title': title,
    'filename': filename,
}

if output_mode == 'match':
    print(f'{alternate}.mp4')
elif output_mode == 'json':
    print(json.dumps(data, ensure_ascii=False))
else:
    print(f"Source: {data['source']}")
    print(f"Query: {requested}")
    print(f"Codes: {', '.join(listed_codes)}")
    print(f"Match: {alternate}.mp4")
    print(f"Title: {title}")
    print(f"Filename: {filename}")
PY
