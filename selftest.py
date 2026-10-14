"""Offline self-test: camera ke bina detection pipeline check karta hai.  python selftest.py"""
import os, sys
from collections import deque
import cv2

os.chdir(os.path.dirname(os.path.abspath(__file__)))
import config as C
from detector import make_detector, draw
from make_demo_video import generate, FIRE_ON, FIRE_OFF

if not os.path.isfile("demo.mp4"):
    generate("demo.mp4")
det = make_detector(C)
cap = cv2.VideoCapture("demo.mp4")
fps = cap.get(cv2.CAP_PROP_FPS) or 25
hist, first_alarm, alarm_before, i, last_alarm_t = deque(maxlen=C.WINDOW), None, False, 0, None
os.makedirs("preview", exist_ok=True)
saved = set()
while True:
    ok, f = cap.read()
    if not ok:
        break
    t = i / fps
    i += 1
    dets = det.detect(f)
    hist.append(bool(dets))
    alarm = sum(hist) >= C.MIN_HITS
    if alarm:
        last_alarm_t = t
        if first_alarm is None:
            first_alarm = t
        if t < FIRE_ON:
            alarm_before = True
    out = draw(f, dets)
    for tag, cond in (("1_safe", 4.5 < t < 4.6), ("2_alarm", first_alarm is not None and t > first_alarm + 1 and "2_alarm" not in saved),
                      ("3_smoke", 20.0 < t < 20.1)):
        if cond and tag not in saved:
            saved.add(tag)
            if alarm:
                cv2.rectangle(out, (0, out.shape[0] - 40), (out.shape[1], out.shape[0]), (0, 0, 255), -1)
                cv2.putText(out, "!!! ALERT !!!", (10, out.shape[0] - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
            cv2.imwrite(f"preview/{tag}.jpg", out)

print(f"Detector     : {det.name}")
print(f"Aag shuru    : {FIRE_ON:.1f}s   |  pehla ALERT: {first_alarm if first_alarm is None else round(first_alarm,2)}s")
print(f"Aag se pehle false alarm: {'HAAN (kharab)' if alarm_before else 'nahi (achha)'}")
ok = (first_alarm is not None) and (FIRE_ON <= first_alarm <= FIRE_ON + 4) and not alarm_before
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
