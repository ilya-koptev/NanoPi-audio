#!/bin/bash
# Pull the latest nanopi-audio from its apt repo and upgrade in place.
# Run by nanopi-audio-update.timer (daily). Only refreshes our own source.
export DEBIAN_FRONTEND=noninteractive
apt-get update \
    -o Dir::Etc::SourceList=/etc/apt/sources.list.d/nanopi-audio.list \
    -o Dir::Etc::SourceParts=/dev/null \
    -o APT::Get::List-Cleanup=0 >/dev/null 2>&1
apt-get install -y --only-upgrade nanopi-audio
