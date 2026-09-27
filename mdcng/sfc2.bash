#!/usr/bin/env bash

# FC2CMADB fallback lookup for smdc.bash, routed through FlareSolverr.
set -euo pipefail

FLARE_SSH="${FLARE_SSH:-root@192.168.10.170}"
FLARE_URL="${FLARE_URL:-http://127.0.0.1:8191/v1}"

die() {
  printf 'sfc2: %s\n' "$*" >&2
  exit 1
}

[[ $# == 1 ]] || die "usage: sfc2.bash FC2_NUMBER_OR_FILENAME"
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

url="https://fc2cmadb.com/articles/$number"
payload=$(jq -cn --arg url "$url" \
  '{cmd:"request.get",url:$url,maxTimeout:60000}')
response=$(printf '%s' "$payload" | ssh "$FLARE_SSH" \
  "curl -fsS -X POST '$FLARE_URL' -H 'Content-Type: application/json' --data-binary @-")

jq -e '.status == "ok" and .solution.status == 200' >/dev/null <<<"$response" ||
  die "FC2CMADB request failed: $(jq -r '.message // .solution.status // "unknown error"' <<<"$response")"

python3 - "$url" 3< <(jq -r '.solution.response' <<<"$response") <<'PY'
import html
import os
import re
import sys
from html.parser import HTMLParser


class ArticleParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_title = False
        self.title_done = False
        self.title_parts = []
        self.in_row = False
        self.cell = None
        self.cell_parts = []
        self.row = {}
        self.rows = []

    def handle_starttag(self, tag, attrs):
        if tag == "h1" and not self.title_done:
            self.in_title = True
        if tag == "tr":
            self.in_row = True
            self.row = {}
        elif self.in_row and tag in ("th", "td"):
            self.cell = tag
            self.cell_parts = []
        elif self.cell and tag in ("a", "span", "br"):
            self.cell_parts.append(" ")

    def handle_endtag(self, tag):
        if tag == "h1":
            if self.in_title:
                self.title_done = True
            self.in_title = False
        if self.in_row and tag in ("th", "td") and self.cell == tag:
            self.row[tag] = " ".join("".join(self.cell_parts).split())
            self.cell = None
        elif tag == "tr" and self.in_row:
            if self.row.get("th"):
                self.rows.append((self.row["th"], self.row.get("td", "")))
            self.in_row = False

    def handle_data(self, data):
        if self.in_title:
            self.title_parts.append(data)
        if self.cell:
            self.cell_parts.append(data)


source = sys.argv[1]
parser = ArticleParser()
with os.fdopen(3) as article:
    parser.feed(article.read())
fields = {re.sub(r"[：:]$", "", key.strip()): value for key, value in parser.rows}
aliases = {
    "ID": ("ID",),
    "Seller": ("販売者", "Seller"),
    "Actress": ("女優", "Actress"),
    "Mosaic": ("モザイク", "Mosaic"),
    "Sale date": ("販売日", "Sale date"),
    "Recording time": ("収録時間", "Recording time"),
    "Tags": ("タグ", "Tag", "Tags"),
    "Link": ("リンク", "Link"),
}

title = " ".join("".join(parser.title_parts).split())
print(f"Source: {source}")
print(f"Title: {html.unescape(title) or '(not listed)'}")
for label, names in aliases.items():
    value = next((fields[name] for name in names if fields.get(name)), "")
    print(f"{label}: {html.unescape(value) if value else '(not listed)'}")
PY
