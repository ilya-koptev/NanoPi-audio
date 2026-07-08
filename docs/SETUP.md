# Setup — from a blank SD card to playing audio

This walks through preparing a NanoPi NEO from scratch: flashing the OS from the
official image, first boot, wiring the amplifier, and installing `nanopi-audio`.

---

## 1. Get the OS image (official site)

The board runs **Armbian** (Debian-based). Download an image built for the
NanoPi NEO from an official source:

- **Armbian** — <https://www.armbian.com/nanopi-neo/> → a *Debian (Trixie/Bookworm)*
  server image (CLI, no desktop). This is what this project is tested on.
- Or **FriendlyELEC** — <https://www.friendlyelec.com/> (Resources → NanoPi NEO)
  for their vendor image.

You get a file like `Armbian_<ver>_Nanopineo_trixie_current_<kernel>.img.xz`.

## 2. Flash it to a microSD card

Use an **8 GB+** card. Easiest cross-platform tool is **balenaEtcher**
(<https://etcher.balena.io/>): select the `.img.xz` (no need to unpack), select
the card, Flash. Verify is automatic.

<details>
<summary>Command line alternatives</summary>

- **Windows (Git Bash):** unpack then write with `dd` (elevated). Double-check the
  device path — writing to the wrong disk destroys it.
- **Linux/macOS:** `xzcat image.img.xz | sudo dd of=/dev/sdX bs=4M status=progress conv=fsync`

Always eject/sync and read-back-verify before removing the card.
</details>

## 3. First boot

1. Insert the card, connect **Ethernet**, then power via the micro-USB port.
2. Wait ~1–2 minutes for the first boot (it resizes the filesystem and reboots).
3. Find the board's IP — check your router's DHCP leases, or `ping nanopineo.local`,
   or scan the subnet. A **serial debug console** (separate 4-pin UART header,
   **115200 8N1**) is the reliable fallback if the network doesn't come up.
4. SSH in and complete Armbian's first-run (set root password, create a user):
   ```bash
   ssh root@<board-ip>
   ```

> Tip: set up an SSH key so later steps (and updates) are password-free.

## 4. Wire the amplifier — board powered OFF

Solder per the table below (NanoPi NEO **12-pin** header). Keep leads short.

| Header pin | Signal      | → MAX98357A |
|-----------:|-------------|-------------|
| 1          | VDD_5V      | Vin         |
| 8          | I2S0_LRC    | LRC         |
| 9          | I2S0_BCK    | BCLK        |
| 10         | I2S0_SDOUT  | DIN         |
| 11         | PA21 (GPIO) | SD (mute)   |
| 12         | GND         | GND         |

- **GAIN**: leave unconnected → 9 dB. Tie to GND for more gain (up to 15 dB).
- **SD**: the mute line. A weak on-board pull-up (≈1 MΩ) is fine — the GPIO drives it.
- **Speaker**: 4–8 Ω across the amp's OUT+ / OUT−.

## 5. Install nanopi-audio

```bash
curl -fsSL https://ilya-koptev.github.io/NanoPi-audio/nanopi-audio.list \
  | sudo tee /etc/apt/sources.list.d/nanopi-audio.list
sudo apt-get update && sudo apt-get install -y nanopi-audio
sudo reboot
```

The reboot is **required once**: the audio overlay is applied by U-Boot at boot,
so the sound card only appears after restarting.

## 6. Verify

```bash
aplay -l                       # expect: card 0: max98357a [max98357a] ...
systemctl status nanopi-audio-web nanopi-audio-mqtt --no-pager
```

Open **`http://<board-ip>/`** in a browser. Upload a track and press ▶ — you should
hear audio. If not, see Troubleshooting in [USAGE.md](USAGE.md).

## 7. (Optional) static IP

You can set a static address later from the web UI (**Network** section) — it applies
with an **auto-revert**, so a wrong setting reverts itself if you don't confirm from
the new address. See [USAGE.md](USAGE.md#network).
