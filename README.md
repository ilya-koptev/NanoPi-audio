# NanoPi-audio

Turn a **NanoPi NEO** (Allwinner H3) into a small networked audio player driving a
**MAX98357A I²S DAC**, controlled from a browser or over MQTT.

Everything ships as one Debian package: the device-tree overlay for the DAC, the
MPD output configuration, a dependency-free web UI, and an MQTT bridge — plus an
apt-based auto-update.

---

## Features

- **I²S output** to a MAX98357A class-D amp (2 analog channels mixed to mono),
  via a self-contained device-tree overlay — no kernel patching.
- **MPD** as the player, reachable on the network (port 6600) for any MPD client.
- **Web UI** at `http://<board-ip>/` — no external dependencies, no cloud:
  - track list with play / delete,
  - drag-and-drop file upload,
  - stop, volume, **loop / play-once** toggle,
  - **network settings** (DHCP ⇄ static IP) with a safety **auto-revert**.
- **MQTT control** — publish to `audio/track`, `audio/volume`, `audio/play`,
  `audio/loop`; the board publishes `audio/state` (retained) and `audio/log`.
- **Install & manual update** over apt (GitHub Pages repo) or a downloaded `.deb`.

## Hardware

Full parts list with links: **[docs/BOM.md](docs/BOM.md)** (NanoPi NEO, MAX98357A,
12 V→5 V buck, speaker).

Only three signal wires plus power, ground and a mute line. Solder with the board
**powered off**. Pins refer to the NanoPi NEO 12-pin header.

| Header pin | Signal        | SoC   | MAX98357A |
|-----------:|---------------|-------|-----------|
| 1          | VDD_5V        | —     | Vin       |
| 8          | I2S0_LRC      | PA18  | LRC       |
| 9          | I2S0_BCK      | PA19  | BCLK      |
| 10         | I2S0_SDOUT    | PA20  | DIN       |
| 11         | (GPIO)        | PA21  | SD (mute) |
| 12         | GND           | —     | GND       |

Leave **GAIN** unconnected (9 dB). Speaker: 4–8 Ω on the amp output.
Enabling I²S disables `i2c1` (shared PA18/PA19) — this is expected.

## Signal chain

```
MQTT audio/*  ─▶  nanopi-audio-mqtt  ─▶  mpc ─▶ MPD ─▶ ALSA hw:max98357a
                                                   ─▶ sun4i-i2s @1c22000
                                                   ─▶ PA18/19/20 ─▶ MAX98357A ─▶ speaker
Web UI (:80)  ─▶  MPD / netplan / uploads
```

## Install

On a NanoPi NEO already running Armbian (see [docs/SETUP.md](docs/SETUP.md) to get there):

```bash
# add the apt repo and install
curl -fsSL https://ilya-koptev.github.io/NanoPi-audio/nanopi-audio.list \
  | sudo tee /etc/apt/sources.list.d/nanopi-audio.list
sudo apt-get update && sudo apt-get install -y nanopi-audio
sudo reboot        # required once: the overlay is applied by U-Boot at boot

# update later (manual):
sudo apt update && sudo apt install --only-upgrade nanopi-audio
```

Or install a single `.deb` from the [Releases](https://github.com/ilya-koptev/NanoPi-audio/releases):

```bash
sudo apt-get install -y ./nanopi-audio_*.deb
sudo reboot
```

After reboot, `aplay -l` should list `card 0: max98357a`. Open `http://<board-ip>/`.

Full walkthrough: **[docs/SETUP.md](docs/SETUP.md)** · Day-to-day use: **[docs/USAGE.md](docs/USAGE.md)**.

## Build from source

The package is `Architecture: all` (the overlay is compiled on the target at
install time), so it builds on any Linux with `dpkg-deb`:

```bash
git clone https://github.com/ilya-koptev/NanoPi-audio
cd NanoPi-audio
bash packaging/build-deb.sh      # -> build/nanopi-audio_<version>_all.deb
```

Tagging `vX.Y.Z` triggers CI (`.github/workflows/release.yml`) to build the
`.deb`, attach it to a GitHub Release, and publish the apt repo to GitHub Pages.

## Repository layout

```
overlay/     max98357a.dts            device-tree overlay (DAC + I2S pins + SD mute)
src/         mpd-web.py               web UI server (stdlib only)
             mqtt-audio.sh            MQTT <-> MPD bridge + state/log publisher
             net-rollback.sh          network auto-revert helper
             nanopi-audio-update.sh   apt self-update
config/      mosquitto + apt source
systemd/     web / mqtt / update units + timer
packaging/   Debian control + maintainer scripts + build-deb.sh
docs/        SETUP.md, USAGE.md
```

## Notes learned the hard way

Four independent issues each had to be fixed before clean audio came out; they are
baked into the overlay and config here so you don't hit them again:

1. **`sun4i-i2s: Unsupported oversample rate`** — needs `mclk-fs=512` and a clock
   master in the simple-audio-card.
2. **Silent output** — the I²S pins must be muxed (`pinctrl`), or nothing reaches
   the header even though playback "works".
3. **Quiet tones** — the DAC is fine; verify source level (`ffmpeg … volumedetect`).
4. **Crackle at stop** — the amp amplifies I²S garbage on stop; the `SD → PA21`
   mute line (`sdmode-gpios`) silences it.

## License

MIT — see [LICENSE](LICENSE).
