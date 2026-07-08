#!/bin/bash
# Build nanopi-audio_<version>_all.deb from the source tree.
# Runs on any Linux with dpkg-deb (target NanoPi, or a CI runner).
set -e
cd "$(dirname "$0")/.."

VERSION="$(cat VERSION)"
MAINTAINER="Ilya Koptev <ilya.koptev@struhe.com>"
HOMEPAGE="https://github.com/ilya-koptev/NanoPi-audio"
PKG="nanopi-audio"
ROOT="build/${PKG}"

rm -rf build
mkdir -p "$ROOT/DEBIAN"

# payload
install -Dm755 src/mpd-web.py             "$ROOT/usr/local/bin/mpd-web.py"
install -Dm755 src/mqtt-audio.sh          "$ROOT/usr/local/bin/mqtt-audio.sh"
install -Dm755 src/net-rollback.sh        "$ROOT/usr/local/bin/net-rollback.sh"
install -Dm755 src/nanopi-audio-update.sh "$ROOT/usr/local/bin/nanopi-audio-update.sh"
install -Dm644 overlay/max98357a.dts      "$ROOT/usr/share/nanopi-audio/max98357a.dts"
install -Dm644 assets/egg.wav             "$ROOT/usr/share/nanopi-audio/egg.wav"
install -Dm644 config/nanopi-audio-mosquitto.conf "$ROOT/etc/mosquitto/conf.d/nanopi-audio.conf"
for u in web mqtt update; do
    install -Dm644 "systemd/nanopi-audio-${u}.service" "$ROOT/lib/systemd/system/nanopi-audio-${u}.service"
done

# control + maintainer scripts
sed -e "s/__VERSION__/${VERSION}/" \
    -e "s|__MAINTAINER__|${MAINTAINER}|" \
    -e "s|__HOMEPAGE__|${HOMEPAGE}|" \
    packaging/DEBIAN/control > "$ROOT/DEBIAN/control"
install -m644 packaging/DEBIAN/conffiles "$ROOT/DEBIAN/conffiles"
install -m755 packaging/DEBIAN/postinst  "$ROOT/DEBIAN/postinst"
install -m755 packaging/DEBIAN/prerm     "$ROOT/DEBIAN/prerm"
install -m755 packaging/DEBIAN/postrm    "$ROOT/DEBIAN/postrm"

OUT="build/${PKG}_${VERSION}_all.deb"
dpkg-deb --root-owner-group --build "$ROOT" "$OUT"
echo "built $OUT"
dpkg-deb --info "$OUT" | sed -n '1,20p'
