#!/bin/bash
# MQTT <-> MPD bridge.
#   IN : audio/track(N)  audio/volume(0-100)  audio/play(1/0)  audio/loop(1/0)
#   OUT: audio/state (retained, current state)   audio/log (event lines)
MUSIC=/var/lib/mpd/music
H=127.0.0.1
MPC="mpc -q"

log() { mosquitto_pub -h "$H" -t audio/log -m "$(date '+%Y-%m-%d %H:%M:%S') $*"; }

pub_state() {
  local song raw state vol loop msg
  song=$(mpc current 2>/dev/null)
  raw=$(mpc status 2>/dev/null)
  if printf '%s' "$raw" | grep -q '\[playing\]'; then state=playing
  elif printf '%s' "$raw" | grep -q '\[paused\]'; then state=paused
  else state=stopped; fi
  vol=$(printf '%s\n' "$raw" | grep -oE 'volume: *[0-9]+' | grep -oE '[0-9]+' | head -1)
  if printf '%s' "$raw" | grep -q 'repeat: on'; then loop=on; else loop=off; fi
  msg="$state"
  [ -n "$song" ] && msg="$state: $song"
  msg="$msg | vol=${vol:-?} loop=$loop"
  mosquitto_pub -h "$H" -r -t audio/state -m "$msg"
}

# event-driven state publisher (fires on player/mixer/options changes)
(
  while true; do
    pub_state
    mpc idle player mixer options >/dev/null 2>&1 || sleep 2
  done
) &

log "bridge started"
pub_state

mosquitto_sub -h "$H" -t audio/track -t audio/volume -t audio/play -t audio/loop -F '%t %p' | \
while read -r topic payload; do
  val=$(printf '%s' "$payload" | tr -dc '0-9')
  name=$(printf '%s' "$payload" | tr -d '\r' | sed 's#.*/##; s/^[[:space:]]*//; s/[[:space:]]*$//')
  case "$topic" in
    audio/track)
      [ -z "$name" ] && continue
      # match a file by name without extension (e.g. "sovy" -> sovy.mp3, "2" -> 2.wav);
      # a full filename also works. egg.* stays hidden.
      f=""
      for cand in "$MUSIC"/*.*; do
        [ -e "$cand" ] || continue
        b=${cand##*/}
        case "${b,,}" in egg.*) continue ;; esac
        stem=${b%.*}
        if [ "${stem,,}" = "${name,,}" ] || [ "${b,,}" = "${name,,}" ]; then f=$b; break; fi
      done
      if [ -n "$f" ]; then
        $MPC clear; $MPC add "$f"; $MPC play; log "track '$name' -> $f"
      else
        log "track '$name': not found"
      fi
      ;;
    audio/volume)
      [ -n "$val" ] && { $MPC volume "$val"; log "volume $val"; }
      ;;
    audio/play)
      case "$val" in
        1) $MPC play; log "play" ;;
        0) $MPC stop; log "stop" ;;
      esac
      ;;
    audio/loop)
      case "$val" in
        1) $MPC repeat on;  $MPC single on;  log "loop on" ;;
        0) $MPC repeat off; $MPC single off; log "loop off" ;;
      esac
      ;;
  esac
done
