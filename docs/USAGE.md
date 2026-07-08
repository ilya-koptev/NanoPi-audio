# Usage

How to drive `nanopi-audio` day to day — web UI, MQTT, adding music, and fixes.

The board exposes three things on the LAN:

| Service | Address | For |
|---------|---------|-----|
| Web UI  | `http://<ip>/` (port 80) | browser control + uploads + network |
| MQTT    | `<ip>:1883` (anonymous)  | automation / home control |
| MPD     | `<ip>:6600`              | any MPD client (e.g. M.A.L.P.) |

---

## Web UI

Open `http://<board-ip>/`.

- **Now playing** line at the top shows state and current track.
- **Tracks** — press ▶ to play, ✕ to delete.
- **Stop** / **Volume** slider / **Loop** toggle (loop the current track vs play once).
- **Upload files** — pick one or more audio files; they land in the library and the
  database refreshes automatically.
- **Network** — see [below](#network).

Supported files: mp3, flac, wav, ogg, m4a, aac, opus, wma.

## MQTT

Publish commands; subscribe to read state and logs. Broker is on the board,
port 1883, anonymous (LAN only — add auth if it's reachable more widely).

| Topic          | Payload | Direction | Meaning |
|----------------|---------|-----------|---------|
| `audio/track`  | `N`     | in  | play the file whose name starts with `N.` (e.g. `2.mp3`) |
| `audio/volume` | `0`–`100` | in | set volume |
| `audio/play`   | `1` / `0` | in | play / stop |
| `audio/loop`   | `1` / `0` | in | loop the current track / play once |
| `audio/state`  | text    | out (retained) | e.g. `playing: 2.mp3 \| vol=80 loop=on` |
| `audio/log`    | text    | out | timestamped event line per command |

Examples (from any machine on the LAN):

```bash
mosquitto_pub -h <ip> -t audio/track  -m 2     # play 2.*
mosquitto_pub -h <ip> -t audio/loop   -m 1     # loop it
mosquitto_pub -h <ip> -t audio/volume -m 80
mosquitto_pub -h <ip> -t audio/play   -m 0     # stop  (1 = play/resume)
mosquitto_sub -h <ip> -t 'audio/#' -v          # watch state + logs
```

**Play once vs loop:** publish `audio/loop 0`, then `audio/track N` — the track plays
and stops. Publish `audio/loop 1` to repeat the current track.

## Adding music

Copy files into the library and refresh the database:

```bash
scp track.mp3 <user>@<ip>:/var/lib/mpd/music/
ssh <ip> 'mpc update'
```

…or just use the **Upload** button in the web UI.

For MQTT `audio/track N`, name files with a leading number: `1.mp3`, `2.flac`, `10.wav`.
The board ships demo tones `1/2/3.wav` (440/660/880 Hz) you can replace.

## Network

**Network** section of the web UI shows the current interface, IP, gateway, DNS and
mode, and lets you switch **DHCP ⇄ Static**.

Static apply is **safety-gated**:

1. Choose *Static*, fill IP / mask (CIDR), gateway, DNS, set the *Auto-revert* timeout.
2. Press **Apply** — the connection to the old IP drops (expected).
3. Reopen the page at the **new** IP and press **Keep** within the timeout.
   - **Keep** → the config becomes permanent.
   - No confirmation (e.g. the new IP is unreachable) → it **auto-reverts** to the
     previous working configuration.

Do **not** reboot during the wait window — the revert snapshot lives in RAM. If you
ever lock yourself out, recover via the serial console or by editing
`/etc/netplan` on the SD card.

## Updates

Updates are **manual** — nothing auto-upgrades. When a new version is published,
on the board run:

```bash
sudo apt update && sudo apt install --only-upgrade nanopi-audio
# or install a downloaded package directly:
sudo apt install ./nanopi-audio_*.deb
```

(There is also `/usr/local/bin/nanopi-audio-update.sh`, which does the apt upgrade
in one step — run it by hand when you want to update.)

## Easter egg

Clicking the 🔊 speaker icon at the top of the web page plays the track
`/var/lib/mpd/music/egg.wav`. The package ships a short placeholder jingle there —
replace that file on the device with any track you like (keep the name `egg.wav`)
and it becomes your click sound.

## Troubleshooting

| Symptom | Check |
|---------|-------|
| No `card 0: max98357a` in `aplay -l` | did you **reboot** after install? `dmesg \| grep -i i2s` |
| Card present but silent | I²S pins muxed? `cat /sys/kernel/debug/pinctrl/1c20800.pinctrl/pinmux-pins \| grep 'pin 18'` |
| Very quiet | check the file's level: `ffmpeg -i f -af volumedetect -f null -` (the amp is fine) |
| Crackle at stop | SD wire to **pin 11 (PA21)** present? `cat /sys/kernel/debug/gpio \| grep sdmode` |
| Web UI down | `systemctl status nanopi-audio-web` |
| MQTT no response | `systemctl status nanopi-audio-mqtt mosquitto` |

Services: `nanopi-audio-web`, `nanopi-audio-mqtt`, `mpd`, `mosquitto`.
