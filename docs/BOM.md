# Bill of materials

A single **12 V** input feeds a step-down converter; its **5 V** rail powers the
NanoPi and the amplifier together (one rail for everything).

| # | Part | Spec / purpose | Qty | Link |
|---|------|----------------|:---:|------|
| 1 | **NanoPi NEO** | Allwinner H3, 512 MB — runs Armbian, MPD, web UI, MQTT | 1 | [friendlyelec.com](https://www.friendlyelec.com/) |
| 2 | **MAX98357A** I²S DAC + class-D amp (breakout) | I²S in, 3.2 W @ 4 Ω, GAIN 9 dB, SD mute — DAC + amp | 1 | — |
| 3 | **DC-DC step-down** | **12 V → 5 V** logic supply — same module as ship-driver (U3) | 1 | [AliExpress](https://aliexpress.ru/item/1005003502071127.html?sku_id=12000026080547853) |
| 4 | **Speaker** | 4–8 Ω, ≥ 3 W | 1 | — |
| 5 | **microSD card** | 8 GB+, class 10 | 1 | — |
| 6 | Hook-up wire, header pins/socket | I²S + power wiring (see below) | — | — |

## Power

```
12 V in ──▶ [ DC-DC buck 12→5 V, ≥3 A ] ──┬──▶ NanoPi NEO  (5 V, header pin 1 / VDD_5V)
                                          └──▶ MAX98357A   (Vin)
                            common GND ─────── NanoPi GND ── amp GND ── speaker −
```

- **Budget:** NanoPi NEO under load ≈ 0.4–0.8 A @ 5 V; MAX98357A draws up to ~1 A on
  peaks. A **3 A** buck gives comfortable headroom and keeps rails clean on bass hits.
- Set the buck output to **~5.1 V** (allow for wire drop). Prefer a module with low
  ripple — switching noise on the 5 V rail can leak into the analog output.
- Feeding 5 V into the NanoPi's header VDD_5V pin back-powers the board (bypasses the
  micro-USB path); make sure you power it from **only one** source at a time.

> **DC-DC:** this is the same step-down module used for logic power (U3) in the
> [ship-driver](https://github.com/ilya-koptev/ship-driver) build — see its
> [BOM](https://github.com/ilya-koptev/ship-driver/blob/HEAD/Ship%20PCB/v1.1/BOM.md).
> Set its output to ~5.1 V and confirm it can supply the NanoPi + amp peaks (≈2 A);
> any equivalent 12→5 V buck with enough headroom works.

## Wiring (NanoPi NEO 12-pin header → MAX98357A)

| Header pin | Signal      | → MAX98357A |
|-----------:|-------------|-------------|
| 1          | VDD_5V      | Vin (and buck 5 V) |
| 8          | I2S0_LRC    | LRC         |
| 9          | I2S0_BCK    | BCLK        |
| 10         | I2S0_SDOUT  | DIN         |
| 11         | PA21 (GPIO) | SD (mute)   |
| 12         | GND         | GND (and buck GND / speaker −) |

GAIN: unconnected = 9 dB (tie to GND for up to 15 dB). See [SETUP.md](SETUP.md) for the
full assembly and first-boot procedure.
