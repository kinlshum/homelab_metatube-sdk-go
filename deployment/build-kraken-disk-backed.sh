#!/usr/bin/env bash
# Compile in Docker on Kraken, with Go scratch/cache outside docker.img.
# Usage: script EXISTING_RELEASE_DIR EXACT_COMMIT
set -euo pipefail
release_dir=$1
source_commit=$2
[[ "$release_dir" == /mnt/cache_nvme_apps/appdata/metatube-stack/actor-trace-* ]]
[[ -d "$release_dir/src" && "$source_commit" =~ ^[0-9a-f]{40}$ ]]
mkdir -p "$release_dir/go-work/cache" "$release_dir/go-work/mod" "$release_dir/go-work/tmp" "$release_dir/runtime"
docker run --rm --memory=3g --cpus=2 \
  -v "$release_dir/src:/src:ro" -v "$release_dir/go-work:/work" \
  -v "$release_dir/runtime:/out" -w /src \
  -e GOCACHE=/work/cache -e GOMODCACHE=/work/mod -e GOTMPDIR=/work/tmp \
  -e GOMAXPROCS=2 -e CGO_ENABLED=0 \
  golang:alpine go build -p 2 -tags experimental -trimpath \
  -ldflags "-w -s -X github.com/metatube-community/metatube-sdk-go/internal/version.Version=2026.09.30.2 -X github.com/metatube-community/metatube-sdk-go/internal/version.GitCommit=$source_commit" \
  -o /out/metatube-server cmd/server/main.go
docker build -f "$release_dir/Dockerfile.runtime" -t kinlshum/metatube-server-providers:actor-trace-20260930 "$release_dir/runtime"
