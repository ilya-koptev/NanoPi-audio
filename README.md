# NanoPi-audio

Превращает **NanoPi NEO** (Allwinner H3) в небольшой сетевой аудиоплеер на базе
**I²S-ЦАП MAX98357A**, управляемый из браузера или по MQTT.

Всё поставляется одним Debian-пакетом: оверлей устройства для ЦАП, настройка вывода
MPD, веб-интерфейс без внешних зависимостей и MQTT-мост.

---

## Возможности

- **Вывод по I²S** на усилитель класса D MAX98357A (2 канала сводятся в моно), через
  самодостаточный device-tree overlay — без правок ядра.
- **MPD** как проигрыватель, доступен по сети (порт 6600) для любого MPD-клиента.
- **Веб-интерфейс** по адресу `http://<ip-платы>/` — без внешних зависимостей и облака:
  - список треков с воспроизведением / удалением,
  - загрузка файлов,
  - стоп, громкость, **повтор / один раз**,
  - **настройки сети** (DHCP ⇄ статический IP) с безопасным **автооткатом**,
  - строка **обновления** (проверка apt, обновление по кнопке).
- **Управление по MQTT** — публикация в `audio/track`, `audio/volume`, `audio/play`,
  `audio/loop`; плата публикует `audio/state` (retained) и `audio/log`.
- **Установка и ручное обновление** через apt (репозиторий на GitHub Pages) или `.deb`.

## Железо

Полный список деталей со ссылками: **[docs/BOM.md](docs/BOM.md)** (NanoPi NEO,
MAX98357A, понижайка 12 В→5 В, динамик).

Всего три сигнальных провода плюс питание, земля и линия mute. Паять при
**обесточенной** плате. Пины — 12-контактная гребёнка NanoPi NEO.

| Пин | Сигнал        | SoC   | MAX98357A |
|----:|---------------|-------|-----------|
| 1   | VDD_5V        | —     | Vin       |
| 8   | I2S0_LRC      | PA18  | LRC       |
| 9   | I2S0_BCK      | PA19  | BCLK      |
| 10  | I2S0_SDOUT    | PA20  | DIN       |
| 11  | (GPIO)        | PA21  | SD (mute) |
| 12  | GND           | —     | GND       |

**GAIN** не подключать (9 дБ). Динамик: 4–8 Ом на выход усилителя.
Включение I²S отключает `i2c1` (общие пины PA18/PA19) — это ожидаемо.

## Сигнальная цепь

```
MQTT audio/*  ─▶  nanopi-audio-mqtt  ─▶  mpc ─▶ MPD ─▶ ALSA hw:max98357a
                                                   ─▶ sun4i-i2s @1c22000
                                                   ─▶ PA18/19/20 ─▶ MAX98357A ─▶ динамик
Веб (:80)     ─▶  MPD / netplan / загрузка файлов
```

## Установка

На NanoPi NEO с уже установленным Armbian (как к этому прийти — см.
[docs/SETUP.md](docs/SETUP.md)):

```bash
# добавить apt-репозиторий и поставить
curl -fsSL https://ilya-koptev.github.io/NanoPi-audio/nanopi-audio.list \
  | sudo tee /etc/apt/sources.list.d/nanopi-audio.list
sudo apt-get update && sudo apt-get install -y nanopi-audio
sudo reboot        # один раз: оверлей применяется U-Boot при загрузке

# обновление потом (вручную):
sudo apt update && sudo apt install --only-upgrade nanopi-audio
```

Либо поставить один `.deb` из [релизов](https://github.com/ilya-koptev/NanoPi-audio/releases):

```bash
sudo apt-get install -y ./nanopi-audio_*.deb
sudo reboot
```

После перезагрузки `aplay -l` должен показать `card 0: max98357a`.
Откройте `http://<ip-платы>/`.

Подробно: **[docs/SETUP.md](docs/SETUP.md)** · Как пользоваться: **[docs/USAGE.md](docs/USAGE.md)**.

## Сборка из исходников

Пакет `Architecture: all` (оверлей компилируется на плате при установке), поэтому
собирается на любом Linux с `dpkg-deb`:

```bash
git clone https://github.com/ilya-koptev/NanoPi-audio
cd NanoPi-audio
bash packaging/build-deb.sh      # -> build/nanopi-audio_<версия>_all.deb
```

Тег `vX.Y.Z` запускает CI (`.github/workflows/release.yml`): собрать `.deb`,
приложить к GitHub Release и опубликовать apt-репозиторий на GitHub Pages.

## Структура репозитория

```
overlay/     max98357a.dts            оверлей (ЦАП + пины I2S + mute SD)
src/         mpd-web.py               веб-сервер (только stdlib)
             mqtt-audio.sh            мост MQTT <-> MPD + публикация состояния/логов
             net-rollback.sh          автооткат сети
             nanopi-audio-update.sh   ручное обновление через apt
config/      mosquitto + apt-источник
systemd/     юниты web / mqtt / update
packaging/   Debian control + сопровождающие скрипты + build-deb.sh
docs/        SETUP.md, USAGE.md, BOM.md
```

## Грабли, на которые мы наступили

Четыре независимые проблемы, каждую пришлось решить до чистого звука; всё уже учтено
в оверлее и конфигах здесь:

1. **`sun4i-i2s: Unsupported oversample rate`** — нужны `mclk-fs=512` и мастер
   тактирования в simple-audio-card.
2. **Тишина при рабочем ПО** — пины I²S должны быть замультиплексированы (`pinctrl`),
   иначе сигнал не выходит на гребёнку.
3. **Тихий звук** — ЦАП исправен; проверяйте уровень источника (`ffmpeg … volumedetect`).
4. **Треск на стопе** — усилитель озвучивает мусор I²S; линия mute `SD → PA21`
   (`sdmode-gpios`) это убирает.

## Лицензия

MIT — см. [LICENSE](LICENSE).
