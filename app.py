"""Fire & Smoke AI Surveillance - live web dashboard
   python app.py            -> http://localhost:5000   (DroidCam / webcam)
   python app.py --demo     -> demo video par test
"""
import os, sys, time, socket, argparse, threading, webbrowser
from collections import deque

os.chdir(os.path.dirname(os.path.abspath(__file__)))

import cv2
import numpy as np
from flask import Flask, Response, jsonify, send_from_directory

import config as C
from camera import CamStream
from detector import make_detector, draw

app = Flask(__name__)
lock = threading.Lock()
cam = None
state = {"jpeg": None, "ver": 0, "alarm": False, "label": "-", "conf": 0.0, "hits": 0, "fps": 0.0,
         "camera": False, "source": "-", "detector": "loading...", "events": [], "total": 0}


def set_frame(img):
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 80])
    if ok:
        with lock:
            state["jpeg"] = buf.tobytes()
            state["ver"] += 1


def status_frame(lines):
    img = np.full((360, 640, 3), 24, np.uint8)
    for i, t in enumerate(lines):
        cv2.putText(img, t, (24, 120 + i * 32), cv2.FONT_HERSHEY_SIMPLEX, 0.65 if i else 0.8,
                    (235, 235, 235) if i == 0 else (150, 150, 150), 1 if i else 2, cv2.LINE_AA)
    return img


def beep():
    try:
        import winsound
        for _ in range(3):
            winsound.Beep(2500, 400)
    except ImportError:
        print("\a\a\a", end="", flush=True)


def worker():
    set_frame(status_frame(["Detector load ho raha hai..."]))
    det = make_detector(C)
    with lock:
        state["detector"] = det.name
    history = deque(maxlen=C.WINDOW)
    last_idx, last_alert, recent, n, fps, t0 = -1, 0.0, None, 0, 0.0, time.time()

    while True:
        if not cam.connected or cam.frame is None:
            with lock:
                state.update(camera=False, alarm=False, hits=0)
            set_frame(status_frame([
                "Camera connect ho raha hai...",
                f"Source: {cam.sources[0]}",
                "1) Phone me DroidCam app khula hai?",
                "2) Phone aur PC same WiFi par hain?",
                "3) Test ke liye: python app.py --demo"]))
            time.sleep(0.7)
            continue
        if cam.idx == last_idx:
            time.sleep(0.004)
            continue
        last_idx, frame = cam.idx, cam.frame
        if frame.shape[1] > C.MAX_WIDTH:
            s = C.MAX_WIDTH / frame.shape[1]
            frame = cv2.resize(frame, None, fx=s, fy=s)
        try:
            dets = det.detect(frame)
        except Exception as e:
            print("detect error:", e, flush=True)
            dets = []

        history.append(bool(dets))
        if dets:
            recent = max(dets, key=lambda d: d[1])
        hits = sum(history)
        alarm = hits >= C.MIN_HITS and recent is not None
        out = draw(frame, dets)
        if alarm:
            cv2.rectangle(out, (0, out.shape[0] - 40), (out.shape[1], out.shape[0]), (0, 0, 255), -1)
            cv2.putText(out, f"!!! {recent[0].upper()} ALERT !!!", (10, out.shape[0] - 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
            if time.time() - last_alert > C.COOLDOWN:
                last_alert = time.time()
                stamp = time.strftime("%d-%m-%Y %H:%M:%S")
                path = os.path.join(C.SAVE_DIR, f"{recent[0]}_{time.strftime('%Y%m%d_%H%M%S')}.jpg")
                cv2.imwrite(path, out)
                print(f"ALERT: {recent[0].upper()} {recent[1]:.0%}  -> {path}", flush=True)
                if C.SIREN:
                    threading.Thread(target=beep, daemon=True).start()
                with lock:
                    state["events"] = ([{"t": stamp, "label": recent[0], "conf": round(recent[1], 2)}]
                                       + state["events"])[:8]
                    state["total"] += 1
        n += 1
        if n % 15 == 0:
            fps, t0 = 15 / (time.time() - t0), time.time()
        with lock:
            state.update(alarm=alarm, hits=hits, fps=round(fps, 1), camera=True, source=str(cam.active),
                         label=recent[0] if recent else "-", conf=round(recent[1], 2) if recent else 0.0)
        set_frame(out)


def mjpeg():
    last = -1
    while True:
        with lock:
            jpg, ver = state["jpeg"], state["ver"]
        if jpg and ver != last:
            last = ver
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpg + b"\r\n"
        else:
            time.sleep(0.02)


@app.route("/video_feed")
def video_feed():
    return Response(mjpeg(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/snapshot")
def snapshot():
    with lock:
        jpg = state["jpeg"]
    return Response(jpg or b"", mimetype="image/jpeg", headers={"Cache-Control": "no-store"})


@app.route("/status")
def status():
    with lock:
        return jsonify({k: v for k, v in state.items() if k not in ("jpeg", "ver")})


@app.route("/alerts_list")
def alerts_list():
    files = [f for f in os.listdir(C.SAVE_DIR) if f.lower().endswith(".jpg")]
    files.sort(key=lambda f: os.path.getmtime(os.path.join(C.SAVE_DIR, f)), reverse=True)
    return jsonify(files[:8])


@app.route("/alerts/<path:name>")
def alert_file(name):
    return send_from_directory(os.path.abspath(C.SAVE_DIR), name)


PAGE = """<!doctype html><html lang="hi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Fire &amp; Smoke Surveillance</title>
<style>
:root{--bg:#0f1115;--card:#181b21;--line:#262a33;--tx:#e8eaed;--mut:#8b93a1;--ok:#1f9d55;--bad:#e03131}
*{box-sizing:border-box}body{margin:0;font-family:system-ui,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--tx)}
header{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:12px 20px;background:var(--card);border-bottom:1px solid var(--line)}
h1{font-size:17px;margin:0}
#badge{padding:7px 16px;border-radius:999px;font-weight:700;font-size:14px;background:var(--ok);color:#fff}
#badge.alarm{background:var(--bad);animation:blink .8s infinite}
@keyframes blink{50%{opacity:.55}}
main{display:flex;flex-wrap:wrap;gap:16px;padding:16px;max-width:1300px;margin:auto}
#cam{flex:3 1 520px}#cam img{width:100%;display:block;border-radius:10px;background:#000;border:1px solid var(--line)}
#side{flex:1 1 280px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px;margin-bottom:14px}
.card h3{margin:0 0 10px;font-size:12px;letter-spacing:.08em;color:var(--mut)}
.row{display:flex;justify-content:space-between;padding:4px 0;font-size:14px}.row span:first-child{color:var(--mut)}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:6px;background:var(--bad)}.dot.on{background:var(--ok)}
.ev{font-size:13px;padding:5px 0;border-bottom:1px solid var(--line)}.ev:last-child{border:0}
#alerts{display:grid;grid-template-columns:1fr 1fr;gap:6px}#alerts img{width:100%;border-radius:6px;display:block}
button{background:#2b303b;color:var(--tx);border:1px solid var(--line);padding:8px 12px;border-radius:8px;cursor:pointer;width:100%}
.none{color:var(--mut);font-size:13px}
</style></head><body>
<header><h1>🔥 Fire &amp; Smoke AI Surveillance</h1><span id="badge">SAFE</span></header>
<main>
<div id="cam"><img src="/video_feed" alt="live camera"></div>
<div id="side">
 <div class="card"><h3>SYSTEM</h3>
  <div class="row"><span>Camera</span><span><i class="dot" id="dot"></i><span id="cam_s">-</span></span></div>
  <div class="row"><span>Source</span><span id="src">-</span></div>
  <div class="row"><span>Detector</span><span id="det">-</span></div>
  <div class="row"><span>FPS</span><span id="fps">-</span></div>
  <div class="row"><span>Confirm</span><span><b id="hits">0</b> / %WINDOW% (alert &ge; %MIN%)</span></div>
  <div class="row"><span>Total alerts</span><span id="total">0</span></div>
  <button id="snd">🔔 Browser sound ON karo</button></div>
 <div class="card"><h3>EVENTS</h3><div id="events"><div class="none">Abhi koi alert nahi</div></div></div>
 <div class="card"><h3>SAVED ALERT PHOTOS</h3><div id="alerts"></div></div>
</div></main>
<script>
const $=id=>document.getElementById(id);let ctx=null,was=false;
function beep(){if(!ctx)return;for(let i=0;i<3;i++){const o=ctx.createOscillator(),g=ctx.createGain();o.frequency.value=1800;o.connect(g);g.connect(ctx.destination);const t=ctx.currentTime+i*.35;g.gain.setValueAtTime(.2,t);o.start(t);o.stop(t+.2);}}
$('snd').onclick=()=>{ctx=new (window.AudioContext||window.webkitAudioContext)();$('snd').textContent='🔔 Sound ON';beep();};
async function tick(){try{
 const s=await (await fetch('/status')).json();
 $('badge').textContent=s.alarm?('🚨 '+s.label.toUpperCase()+' DETECTED'):'SAFE';$('badge').className=s.alarm?'alarm':'';
 if(s.alarm&&!was)beep();was=s.alarm;
 $('dot').className='dot'+(s.camera?' on':'');$('cam_s').textContent=s.camera?'connected':'connecting...';
 $('src').textContent=s.source;$('det').textContent=s.detector;$('fps').textContent=s.fps;$('hits').textContent=s.hits;$('total').textContent=s.total;
 if(s.events.length)$('events').innerHTML=s.events.map(e=>'<div class="ev">🚨 <b>'+e.label.toUpperCase()+'</b> '+Math.round(e.conf*100)+'% &middot; '+e.t+'</div>').join('');
 const a=await (await fetch('/alerts_list')).json();
 $('alerts').innerHTML=a.map(f=>'<a href="/alerts/'+f+'" target="_blank"><img src="/alerts/'+f+'"></a>').join('');
}catch(e){}}
setInterval(tick,1000);tick();
</script></body></html>""".replace("%WINDOW%", str(C.WINDOW)).replace("%MIN%", str(C.MIN_HITS))


@app.route("/")
def index():
    return PAGE


def free_port(host, start):
    for p in range(start, start + 30):
        with socket.socket() as s:
            try:
                s.bind((host, p))
                return p
            except OSError:
                continue
    return start


def main():
    global cam
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="demo video par chalao")
    ap.add_argument("--source", help="0 / 1 / http://IP:4747 / video.mp4")
    ap.add_argument("--port", type=int)
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()

    os.makedirs(C.SAVE_DIR, exist_ok=True)
    if a.demo:
        if not os.path.isfile("demo.mp4"):
            from make_demo_video import generate
            print("demo.mp4 ban raha hai...", flush=True)
            generate("demo.mp4")
        sources = ["demo.mp4"]
    elif a.source:
        sources = [int(a.source) if a.source.isdigit() else a.source]
    else:
        sources = [C.SOURCE] + list(C.FALLBACK_SOURCES)

    cam = CamStream(sources)
    threading.Thread(target=worker, daemon=True).start()
    port = free_port(C.WEB_HOST, a.port or C.WEB_PORT)
    url = f"http://localhost:{port}"
    print(f"\n=== Dashboard: {url} ===  (band karne ke liye Ctrl+C)\n", flush=True)
    if C.AUTO_OPEN_BROWSER and not a.no_browser:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    app.run(host=C.WEB_HOST, port=port, threaded=True, use_reloader=False)


if __name__ == "__main__":
    main()
