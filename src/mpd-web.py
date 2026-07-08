#!/usr/bin/env python3
import os, re, json, subprocess, urllib.parse, html, pwd, grp, ipaddress
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MUSIC = "/var/lib/mpd/music"
EXT = (".mp3", ".flac", ".wav", ".ogg", ".m4a", ".aac", ".opus", ".wma")
NETPLAN = "/etc/netplan"
WEBYAML = NETPLAN + "/99-web.yaml"
SNAP = "/run/netplan.rollback"
ROLLBACK = "/usr/local/bin/net-rollback.sh"
try:
    UID = pwd.getpwnam("mpd").pw_uid
    GID = grp.getgrnam("audio").gr_gid
except KeyError:
    UID = GID = -1


def run(*a, timeout=30):
    try:
        return subprocess.run(a, capture_output=True, text=True, timeout=timeout)
    except Exception:
        return subprocess.CompletedProcess(a, 1, "", "")


def mpc(*a):
    return run("mpc", "-q", *a, timeout=10).stdout


def mpc_o(*a):
    return run("mpc", *a, timeout=10).stdout


def tracks():
    try:
        return sorted((f for f in os.listdir(MUSIC) if f.lower().endswith(EXT)), key=str.lower)
    except FileNotFoundError:
        return []


def safe(name):
    n = os.path.basename((name or "").replace("\\", "/"))
    return n if n and n in tracks() else None


# ---------------- network ----------------
def net_iface():
    out = run("ip", "-o", "-br", "link").stdout
    for line in out.splitlines():
        parts = line.split()
        if parts and parts[0] != "lo" and parts[0].startswith(("e", "en", "eth")):
            return parts[0]
    return "end0"


def net_status():
    iface = net_iface()
    ip = cidr = gw = ""
    a = run("ip", "-o", "-4", "addr", "show", "dev", iface).stdout
    m = re.search(r"inet (\d+\.\d+\.\d+\.\d+)/(\d+)", a)
    if m:
        ip, cidr = m.group(1), m.group(2)
    r = run("ip", "-4", "route", "show", "default").stdout
    m = re.search(r"default via (\d+\.\d+\.\d+\.\d+)", r)
    if m:
        gw = m.group(1)
    dns = []
    d = run("resolvectl", "dns", iface).stdout
    dns = re.findall(r"\d+\.\d+\.\d+\.\d+", d)
    if not dns:
        try:
            for ln in open("/etc/resolv.conf"):
                mm = re.match(r"\s*nameserver\s+(\d+\.\d+\.\d+\.\d+)", ln)
                if mm and mm.group(1) != "127.0.0.53":
                    dns.append(mm.group(1))
        except OSError:
            pass
    mode = "static" if (os.path.exists(WEBYAML) and "dhcp4: false" in open(WEBYAML).read()) else "dhcp"
    pending = run("systemctl", "is-active", "netplan-rollback.timer").stdout.strip() == "active"
    return {"iface": iface, "ip": ip, "cidr": cidr, "gateway": gw,
            "dns": dns, "mode": mode, "pending": pending}


def net_apply(mode, ip, cidr, gw, dns_list, revert):
    iface = net_iface()
    if mode == "static":
        ipaddress.ip_interface("%s/%s" % (ip, cidr))   # raises on bad input
        if gw:
            ipaddress.ip_address(gw)
        for d in dns_list:
            ipaddress.ip_address(d)
        dns_line = "        addresses: [%s]\n" % ", ".join(dns_list) if dns_list else ""
        route = ""
        if gw:
            route = "      routes:\n        - to: default\n          via: %s\n" % gw
        ns = ""
        if dns_list:
            ns = "      nameservers:\n" + dns_line
        cfg = ("network:\n  version: 2\n  renderer: networkd\n  ethernets:\n"
               "    %s:\n      dhcp4: false\n      addresses:\n        - %s/%s\n%s%s"
               % (iface, ip, cidr, route, ns))
    else:
        cfg = ("network:\n  version: 2\n  renderer: networkd\n  ethernets:\n"
               "    %s:\n      dhcp4: true\n" % iface)

    # snapshot current config for rollback
    run("rm", "-rf", SNAP)
    run("cp", "-a", NETPLAN, SNAP)
    # replace netplan with our single file
    for f in os.listdir(NETPLAN):
        if f.endswith(".yaml"):
            try:
                os.remove(os.path.join(NETPLAN, f))
            except OSError:
                pass
    with open(WEBYAML, "w") as w:
        w.write(cfg)
    os.chmod(WEBYAML, 0o600)
    # schedule auto-revert unless confirmed
    run("systemctl", "stop", "netplan-rollback.timer")
    run("systemctl", "reset-failed", "netplan-rollback.service")
    run("systemd-run", "--unit=netplan-rollback", "--on-active=%ds" % int(revert), ROLLBACK)
    run("netplan", "apply")
    return iface


def net_keep():
    run("systemctl", "stop", "netplan-rollback.timer")
    run("systemctl", "reset-failed", "netplan-rollback.service")
    run("rm", "-rf", SNAP)


PAGE = """<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>NanoPi audio</title>
<style>
:root{--bg:#f6f8f8;--fg:#131a1d;--dim:#58656a;--card:#fff;--bd:#dbe2e2;--ac:#0b8a7c;--acw:#e0f0ed;--warn:#b26e12;--crit:#c13f39}
@media(prefers-color-scheme:dark){:root{--bg:#0d1215;--fg:#e6ecee;--dim:#8d9ea4;--card:#141b1f;--bd:#253138;--ac:#33b7a6;--acw:#12302a;--warn:#dfa24c;--crit:#e5685f}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:640px;margin:0 auto;padding:1.5rem 1.1rem 4rem}
h1{font-size:1.5rem;margin:.2rem 0 1rem;letter-spacing:-.01em}
h2{font-size:.8rem;text-transform:uppercase;letter-spacing:.09em;color:var(--dim);margin:2rem 0 .6rem;font-family:ui-monospace,Menlo,Consolas,monospace}
.mono{font-family:ui-monospace,Menlo,Consolas,monospace}
.status{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.9rem;background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:.7rem .9rem;color:var(--dim)}
.status b{color:var(--fg)}
.ctl{display:flex;align-items:center;gap:1rem;margin-top:.8rem;flex-wrap:wrap}
input[type=range]{flex:1;min-width:140px;accent-color:var(--ac)}
button{font:inherit;cursor:pointer;border:1px solid var(--bd);background:var(--card);color:var(--fg);border-radius:8px;padding:.45rem .8rem}
button:hover{border-color:var(--ac)}
button:focus-visible{outline:2px solid var(--ac);outline-offset:2px}
.primary{background:var(--acw);border-color:var(--ac);color:var(--ac);font-weight:600}
ul{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:.4rem}
li{display:flex;align-items:center;gap:.6rem;background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:.4rem .5rem .4rem .4rem}
li .name{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:.94rem}
.play{background:var(--acw);border-color:var(--ac);color:var(--ac);font-weight:600}
.del{color:var(--dim);padding:.4rem .55rem}
.empty{color:var(--dim);font-style:italic}
form{display:flex;gap:.6rem;flex-wrap:wrap;align-items:center;background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:.9rem}
input[type=file]{flex:1;min-width:180px;font-size:.9rem}
.net{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:.9rem}
.net .cur{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.86rem;color:var(--dim);margin-bottom:.8rem}
.net .cur b{color:var(--fg)}
.net .row{display:flex;gap:.6rem;flex-wrap:wrap;align-items:center;margin:.35rem 0}
.net label{font-size:.85rem;color:var(--dim);min-width:74px}
.net input[type=text],.net input[type=number]{font:inherit;padding:.4rem .5rem;border:1px solid var(--bd);border-radius:7px;background:var(--bg);color:var(--fg)}
.net input.ip{width:150px}.net input.sm{width:70px}
.warn{color:var(--warn);font-size:.82rem;margin:.5rem 0}
.msg{margin-top:.7rem;font-size:.9rem}
.msg.ok{color:var(--ac)}.msg.err{color:var(--crit)}
footer{margin-top:2.5rem;color:var(--dim);font-size:.8rem;font-family:ui-monospace,Menlo,Consolas,monospace}
.mqtt{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:.9rem}
.mqtt p{margin:.2rem 0 .7rem;font-size:.88rem;color:var(--dim)}
.mqtt p b{color:var(--fg)}
table.mqtt-t{width:100%;border-collapse:collapse;font-size:.84rem;margin-bottom:.9rem}
table.mqtt-t th,table.mqtt-t td{text-align:left;padding:.35rem .55rem;border-bottom:1px solid var(--bd);white-space:nowrap}
table.mqtt-t th{color:var(--dim);font-weight:600;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.7rem;text-transform:uppercase;letter-spacing:.06em}
table.mqtt-t td:first-child,table.mqtt-t td:nth-child(2){font-family:ui-monospace,Menlo,Consolas,monospace}
pre{background:var(--bg);border:1px solid var(--bd);border-radius:8px;padding:.8rem;overflow-x:auto;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.78rem;line-height:1.55;margin:0}
[hidden]{display:none!important}
</style></head><body><main>
<h1><span id="spk" style="cursor:pointer;-webkit-user-select:none;user-select:none">&#128266;</span> <span id="ttl">NanoPi &mdash; audio</span></h1>
<div class="status" id="st">&hellip;</div>
<div class="ctl">
  <button onclick="api('/api/stop').then(upd)">&#9632; Stop</button>
  <button id="loopbtn" onclick="toggleLoop()">&#8635; Loop: off</button>
  <label style="flex:1;display:flex;gap:.6rem;align-items:center">Volume
    <input id="vol" type="range" min="0" max="100" oninput="api('/api/vol?v='+this.value)"></label>
</div>
<h2>Tracks</h2>
<ul>%TRACKS%</ul>
<h2>Upload files</h2>
<form method="post" action="/upload" enctype="multipart/form-data">
  <input type="file" name="f" multiple accept="audio/*" required>
  <button type="submit">Upload</button>
</form>

<h2>Network</h2>
<div class="net">
  <div class="cur" id="netcur">&hellip;</div>
  <div class="row"><label>Mode</label>
    <label><input type="radio" name="mode" value="dhcp" onchange="toggleStatic()"> DHCP</label>
    <label><input type="radio" name="mode" value="static" onchange="toggleStatic()"> Static</label>
  </div>
  <div id="staticfields">
    <div class="row"><label>IP / mask</label>
      <input class="ip" type="text" id="ip" placeholder="192.168.100.15">
      <span class="mono">/</span><input class="sm" type="number" id="cidr" min="1" max="32" value="24"></div>
    <div class="row"><label>Gateway</label><input class="ip" type="text" id="gw" placeholder="192.168.100.1"></div>
    <div class="row"><label>DNS</label><input class="ip" type="text" id="dns" placeholder="192.168.100.1, 8.8.8.8" style="width:220px"></div>
  </div>
  <div class="row"><label>Auto-revert</label><input class="sm" type="number" id="revert" min="30" max="600" value="120"><span class="mono">s</span></div>
  <p class="warn">&#9888; Wrong static settings can cut off access. After Apply, reopen the page at the NEW IP and press &laquo;Keep&raquo; within the timeout &mdash; otherwise it reverts automatically.</p>
  <div class="row">
    <button class="primary" id="applybtn" onclick="applyNet()">Apply</button>
    <button id="keepbtn" hidden onclick="keepNet()">Keep this config</button>
  </div>
  <div class="msg" id="netmsg"></div>
</div>

<h2>MQTT control</h2>
<div class="mqtt">
  <p>Broker <b>192.168.100.15:1883</b> &mdash; anonymous, LAN only. You <em>publish</em> commands; <em>subscribe</em> to read state &amp; logs.</p>
  <div style="overflow-x:auto"><table class="mqtt-t">
    <tr><th>Topic</th><th>Payload</th><th>Action</th></tr>
    <tr><td>audio/track</td><td>N</td><td>play file whose name starts with <b>N.</b></td></tr>
    <tr><td>audio/volume</td><td>0&ndash;100</td><td>set volume</td></tr>
    <tr><td>audio/play</td><td>1 / 0</td><td>play / stop</td></tr>
    <tr><td>audio/loop</td><td>1 / 0</td><td>loop current track / play once</td></tr>
    <tr><td>audio/state</td><td>&larr; publ.</td><td>retained current state</td></tr>
    <tr><td>audio/log</td><td>&larr; publ.</td><td>event log line</td></tr>
  </table></div>
  <p>Example (from any device on the LAN):</p>
  <pre>mosquitto_pub -h 192.168.100.15 -t audio/track  -m 2   <span style="color:var(--dim)"># play 2.*</span>
mosquitto_pub -h 192.168.100.15 -t audio/loop   -m 1   <span style="color:var(--dim)"># loop it</span>
mosquitto_pub -h 192.168.100.15 -t audio/volume -m 80
mosquitto_pub -h 192.168.100.15 -t audio/play   -m 0   <span style="color:var(--dim)"># stop</span>
mosquitto_sub -h 192.168.100.15 -t 'audio/#' -v        <span style="color:var(--dim)"># watch state+logs</span></pre>
</div>
<footer>MPD :6600 &middot; web :80 &middot; mqtt :1883</footer>
</main><script>
function api(u,o){return fetch(u,o)}
function play(f){api('/api/play?f='+encodeURIComponent(f)).then(upd)}
function del(f){if(confirm('Delete '+f+'?'))fetch('/api/del?f='+encodeURIComponent(f)).then(function(){location.reload()})}
var LOOP=false;
function upd(){fetch('/api/status').then(function(r){return r.json()}).then(function(s){
  document.getElementById('st').innerHTML=s.playing?('&#9654; <b>'+s.song+'</b>'):'stopped';
  var v=document.getElementById('vol'); if(s.volume>=0 && document.activeElement!==v) v.value=s.volume;
  LOOP=!!s.loop; var lb=document.getElementById('loopbtn');
  if(lb){lb.innerHTML=(LOOP?'&#8635; Loop: on':'&#8635; Loop: off');lb.className=LOOP?'primary':'';}
}).catch(function(){})}
function toggleLoop(){api('/api/loop?v='+(LOOP?0:1)).then(upd)}
function toggleStatic(){var m=document.querySelector('input[name=mode]:checked');document.getElementById('staticfields').hidden=(m&&m.value==='dhcp')}
function loadNet(){fetch('/api/net').then(function(r){return r.json()}).then(function(n){
  document.getElementById('netcur').innerHTML='iface <b>'+n.iface+'</b> &middot; <b>'+(n.ip||'?')+'/'+(n.cidr||'?')+'</b> &middot; gw '+(n.gateway||'-')+' &middot; dns '+(n.dns.join(', ')||'-')+' &middot; mode <b>'+n.mode+'</b>';
  var r=document.querySelector('input[name=mode][value='+n.mode+']'); if(r)r.checked=true; toggleStatic();
  if(!document.getElementById('ip').value)document.getElementById('ip').value=n.ip;
  if(n.gateway&&!document.getElementById('gw').value)document.getElementById('gw').value=n.gateway;
  if(n.cidr)document.getElementById('cidr').value=n.cidr;
  document.getElementById('keepbtn').hidden=!n.pending;
  if(n.pending){var m=document.getElementById('netmsg');m.className='msg ok';m.textContent='Pending config detected — press Keep to make it permanent.';}
})}
function applyNet(){
  var mode=document.querySelector('input[name=mode]:checked');mode=mode?mode.value:'dhcp';
  var body='mode='+mode+'&revert='+encodeURIComponent(document.getElementById('revert').value);
  if(mode==='static'){
    body+='&ip='+encodeURIComponent(document.getElementById('ip').value)
        +'&cidr='+encodeURIComponent(document.getElementById('cidr').value)
        +'&gw='+encodeURIComponent(document.getElementById('gw').value)
        +'&dns='+encodeURIComponent(document.getElementById('dns').value);
    if(!confirm('Apply STATIC '+document.getElementById('ip').value+'/'+document.getElementById('cidr').value+'?\\nReopen at the new IP and press Keep, or it reverts.'))return;
  }
  var m=document.getElementById('netmsg');m.className='msg';m.textContent='Applying…';
  fetch('/api/net/apply',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:body})
   .then(function(r){return r.json()}).then(function(res){
     if(res.ok){m.className='msg ok';
       m.innerHTML=(mode==='static'
         ?'Applied. Now open <b>http://'+document.getElementById('ip').value+'/</b> and press Keep within '+document.getElementById('revert').value+'s.'
         :'Applied (DHCP). Reconnect via the new address; press Keep to confirm.');
       document.getElementById('keepbtn').hidden=false;
     }else{m.className='msg err';m.textContent='Error: '+(res.error||'failed');}
   }).catch(function(){var m2=document.getElementById('netmsg');m2.className='msg ok';
     m2.innerHTML='Connection dropped (expected on IP change). Open the page at the new IP and press Keep.';
     document.getElementById('keepbtn').hidden=false;});
}
function keepNet(){fetch('/api/net/keep').then(function(){var m=document.getElementById('netmsg');m.className='msg ok';m.textContent='Kept. Config is now permanent.';document.getElementById('keepbtn').hidden=true;})}
setInterval(upd,2000);upd();loadNet();
document.getElementById('spk').addEventListener('click',function(){fetch('/api/egg').then(upd)});
</script></body></html>"""


def render():
    rows = ""
    for f in tracks():
        disp = html.escape(f)
        arg = html.escape(json.dumps(f))
        rows += ('<li><button class="play" onclick="play(' + arg + ')">&#9654;</button>'
                 '<span class="name">' + disp + '</span>'
                 '<button class="del" onclick="del(' + arg + ')">&#10005;</button></li>')
    if not rows:
        rows = '<li class="empty">empty &mdash; upload files below</li>'
    return PAGE.replace("%TRACKS%", rows)


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body=b"", ctype="text/html; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8")

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        p = u.path
        if p == "/":
            self._send(200, render().encode("utf-8"))
        elif p == "/api/status":
            song = mpc_o("current").strip()
            st = mpc_o("status")
            m = re.search(r"(\d+)", mpc_o("volume"))
            self._json({"playing": bool(song), "song": song,
                        "volume": int(m.group(1)) if m else -1,
                        "loop": "repeat: on" in st})
        elif p == "/api/loop":
            v = q.get("v", [""])[0]
            if v == "1":
                mpc("repeat", "on"); mpc("single", "on")
            elif v == "0":
                mpc("repeat", "off"); mpc("single", "off")
            self._send(204)
        elif p == "/api/play":
            f = safe(q.get("f", [""])[0])
            if f:
                mpc("clear"); mpc("add", f); mpc("play")
            self._send(204 if f else 404)
        elif p == "/api/egg":
            egg = next((f for f in tracks() if f.lower().startswith("egg.")), None)
            if egg:
                mpc("clear"); mpc("add", egg); mpc("play")
            self._send(204 if egg else 404)
        elif p == "/api/stop":
            mpc("stop"); self._send(204)
        elif p == "/api/vol":
            v = q.get("v", [""])[0]
            if v.isdigit():
                mpc("volume", str(max(0, min(100, int(v)))))
            self._send(204)
        elif p == "/api/del":
            f = safe(q.get("f", [""])[0])
            if f:
                try:
                    os.remove(os.path.join(MUSIC, f)); mpc("update")
                except OSError:
                    pass
            self._send(204 if f else 404)
        elif p == "/api/net":
            self._json(net_status())
        elif p == "/api/net/keep":
            net_keep(); self._json({"ok": True})
        else:
            self._send(404)

    def do_POST(self):
        if self.path == "/upload":
            self._upload(); return
        if self.path == "/api/net/apply":
            self._net_apply(); return
        self._send(404)

    def _net_apply(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8", "replace")
        f = urllib.parse.parse_qs(body)
        mode = f.get("mode", ["dhcp"])[0]
        try:
            revert = max(30, min(600, int(f.get("revert", ["120"])[0])))
        except ValueError:
            revert = 120
        try:
            if mode == "static":
                ip = f.get("ip", [""])[0].strip()
                cidr = f.get("cidr", ["24"])[0].strip()
                gw = f.get("gw", [""])[0].strip()
                dns = [d.strip() for d in re.split(r"[,\s]+", f.get("dns", [""])[0]) if d.strip()]
                net_apply("static", ip, cidr, gw, dns, revert)
            else:
                net_apply("dhcp", "", "", "", [], revert)
            self._json({"ok": True})
        except Exception as e:
            self._json({"ok": False, "error": str(e)}, 400)

    def _upload(self):
        ctype = self.headers.get("Content-Type", "")
        length = int(self.headers.get("Content-Length", "0"))
        if "multipart/form-data" not in ctype or "boundary=" not in ctype or length <= 0:
            self._send(400); return
        boundary = ("--" + ctype.split("boundary=", 1)[1].strip()).encode()
        body = self.rfile.read(length)
        saved = 0
        for part in body.split(boundary):
            if b"Content-Disposition" not in part or b'filename="' not in part:
                continue
            head, _, data = part.partition(b"\r\n\r\n")
            if not data:
                continue
            try:
                fn = head.split(b'filename="', 1)[1].split(b'"', 1)[0].decode("utf-8", "replace")
            except IndexError:
                continue
            fn = os.path.basename(fn.replace("\\", "/")).strip()
            if not fn:
                continue
            if data.endswith(b"\r\n"):
                data = data[:-2]
            try:
                path = os.path.join(MUSIC, fn)
                with open(path, "wb") as w:
                    w.write(data)
                if UID >= 0:
                    os.chown(path, UID, GID)
                saved += 1
            except OSError:
                pass
        if saved:
            mpc("update")
        self.send_response(303)
        self.send_header("Location", "/")
        self.end_headers()


if __name__ == "__main__":
    ThreadingHTTPServer(("", 80), H).serve_forever()
