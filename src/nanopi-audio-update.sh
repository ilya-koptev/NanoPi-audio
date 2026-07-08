#!/bin/bash
# Update nanopi-audio to the latest GitHub Release (no apt repo / GitHub Pages needed).
# Fetches the latest release, downloads its .deb and installs it.
set -e
export DEBIAN_FRONTEND=noninteractive
API="https://api.github.com/repos/ilya-koptev/NanoPi-audio/releases/latest"

url=$(curl -fsSL -H "Accept: application/vnd.github+json" "$API" \
      | grep -oE '"browser_download_url"[^,]*\.deb"' \
      | head -n1 | sed -E 's/.*"(https[^"]+)"$/\1/')
if [ -z "$url" ]; then
    echo "nanopi-audio-update: no .deb asset in latest release" >&2
    exit 1
fi

tmp=$(mktemp --suffix=.deb)
trap 'rm -f "$tmp"' EXIT
echo "nanopi-audio-update: downloading $url"
curl -fsSL -o "$tmp" "$url"
apt-get install -y --allow-downgrades "$tmp"
echo "nanopi-audio-update: done"
