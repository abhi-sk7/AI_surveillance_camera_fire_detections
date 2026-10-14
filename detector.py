"""Detectors: YOLO (trained best.pt) ya Classic (colour + motion, bina training ke)."""
import os
import cv2
import numpy as np

FONT = cv2.FONT_HERSHEY_SIMPLEX
COLORS = {"fire": (0, 0, 255), "smoke": (220, 220, 220)}


class ClassicDetector:
    """Aag: garam rang (orange/peela) + harkat/flicker.  Dhuan: dhundla grey + harkat.
    Static cheezein (diya, bulb, orange kapda) background me seekh li jati hain, isliye ignore hoti hain."""
    name = "Built-in (colour + motion)"

    def __init__(self, C):
        self.C = C
        self.bg = cv2.createBackgroundSubtractorMOG2(history=150, varThreshold=28, detectShadows=False)
        self.k3 = np.ones((3, 3), np.uint8)
        self.k7 = np.ones((7, 7), np.uint8)
        self.k15 = np.ones((15, 15), np.uint8)
        self.n = 0
        self.slow = None            # dhimi background (dhuan jaisi halki badlav ke liye)

    def detect(self, frame):
        h, w = frame.shape[:2]
        area = float(h * w)
        blur = cv2.GaussianBlur(frame, (5, 5), 0)
        motion = self.bg.apply(blur, learningRate=0.004)
        self.n += 1
        if self.n < 25:                      # shuru me background seekh raha hai
            return []
        motion = cv2.morphologyEx(motion, cv2.MORPH_OPEN, self.k3)
        motion = cv2.dilate(motion, self.k7, iterations=2)
        hsv = cv2.cvtColor(blur, cv2.COLOR_BGR2HSV)
        gray = cv2.cvtColor(blur, cv2.COLOR_BGR2GRAY).astype(np.float32)
        if self.slow is None:
            self.slow = gray.copy()
        slow_motion = (cv2.absdiff(gray, self.slow) > 9).astype(np.uint8) * 255
        cv2.accumulateWeighted(gray, self.slow, 0.003)

        dets = []
        fire = cv2.inRange(hsv, (0, 100, 170), (38, 255, 255))
        fire = cv2.bitwise_and(fire, motion)
        fire = cv2.morphologyEx(fire, cv2.MORPH_CLOSE, self.k7, iterations=2)
        dets += self._boxes(fire, "fire", area, self.C.MIN_FIRE_AREA, 25.0)

        if self.C.CLASSIC_SMOKE:
            smoke = cv2.inRange(hsv, (0, 0, 80), (180, 70, 215))
            smoke = cv2.bitwise_and(smoke, slow_motion)
            smoke = cv2.morphologyEx(smoke, cv2.MORPH_OPEN, self.k7)
            smoke = cv2.morphologyEx(smoke, cv2.MORPH_CLOSE, self.k15)
            dets += self._boxes(smoke, "smoke", area, self.C.MIN_SMOKE_AREA, 8.0, max_ratio=0.6)
        return dets

    @staticmethod
    def _boxes(mask, label, area, min_ratio, gain, max_ratio=1.0):
        cs, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        out = []
        for c in cs:
            a = cv2.contourArea(c) / area
            if a < min_ratio or a > max_ratio:      # poore frame ki roshni badalna = dhuan nahi
                continue
            x, y, bw, bh = cv2.boundingRect(c)
            out.append((label, min(0.99, 0.5 + a * gain), (x, y, x + bw, y + bh)))
        return out


class YoloDetector:
    name = "YOLO (best.pt)"

    def __init__(self, C):
        import torch
        from ultralytics import YOLO          # yahin import, taki bina ultralytics ke bhi app chale
        if not torch.cuda.is_available():
            torch.set_num_threads(1)
        self.C = C
        self.model = YOLO(C.MODEL_PATH)

    def detect(self, frame):
        C = self.C
        res = self.model(frame, conf=C.CONF, imgsz=C.IMG_SIZE, verbose=False)[0]
        h, w = frame.shape[:2]
        out = []
        for b in res.boxes:
            n = res.names[int(b.cls)].lower()
            label = "fire" if "fire" in n else "smoke" if "smoke" in n else None
            if label is None:
                continue
            x1, y1, x2, y2 = [int(v) for v in b.xyxy[0].tolist()]
            if (x2 - x1) * (y2 - y1) / float(h * w) < C.MIN_BOX_AREA:
                continue
            out.append((label, float(b.conf), (x1, y1, x2, y2)))
        return out


def make_detector(C):
    mode = str(C.DETECTOR).lower()
    if mode in ("auto", "yolo") and os.path.isfile(C.MODEL_PATH):
        try:
            d = YoloDetector(C)
            print("Detector: YOLO", C.MODEL_PATH, flush=True)
            return d
        except Exception as e:
            print("YOLO load nahi hua (", e, ") -> built-in detector use ho raha hai", flush=True)
    elif mode == "yolo":
        print(f"'{C.MODEL_PATH}' nahi mili -> built-in detector use ho raha hai", flush=True)
    print("Detector: built-in (colour + motion)", flush=True)
    return ClassicDetector(C)


def draw(frame, dets):
    out = frame.copy()
    for label, conf, (x1, y1, x2, y2) in dets:
        col = COLORS.get(label, (0, 255, 255))
        cv2.rectangle(out, (x1, y1), (x2, y2), col, 2)
        cv2.putText(out, f"{label} {conf:.0%}", (x1, max(18, y1 - 6)), FONT, 0.6, col, 2, cv2.LINE_AA)
    return out