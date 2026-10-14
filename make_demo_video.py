"""Demo video banata hai (simulated flame + smoke) taaki bina asli aag ke system test ho sake.
Timeline: 0-6s normal (insaan guzarta hai + steady orange bulb), 6-18s aag + dhuan, phir shant."""
import math, random
import numpy as np
import cv2

W, H, FPS, SECONDS = 640, 360, 25, 28
FIRE_ON, FIRE_OFF = 6.0, 18.0
CX, BASE = 330, 305


def _background():
    g = np.linspace(26, 62, H, dtype=np.float32)[:, None, None]
    tint = np.array([1.0, 0.96, 0.9], np.float32)[None, None, :]
    bg = (g * tint * np.ones((1, W, 1), np.float32)).astype(np.uint8)
    cv2.rectangle(bg, (60, 40), (200, 170), (70, 62, 55), -1)
    cv2.rectangle(bg, (60, 40), (200, 170), (95, 85, 75), 3)
    cv2.rectangle(bg, (0, 330), (W, H), (35, 38, 44), -1)
    cv2.rectangle(bg, (240, 308), (430, 332), (45, 52, 70), -1)
    cv2.circle(bg, (570, 70), 15, (70, 170, 255), -1)          # steady orange bulb: alarm NAHI hona chahiye
    return bg


def _envelope(t):
    if t < FIRE_ON:
        return 0.0
    if t < FIRE_ON + 1.5:
        return (t - FIRE_ON) / 1.5
    if t < FIRE_OFF:
        return 1.0
    if t < FIRE_OFF + 1.0:
        return max(0.0, 1 - (t - FIRE_OFF))
    return 0.0


def _flame(t, k, rng):
    layer = np.zeros((H, W, 3), np.uint8)
    for i in range(9):
        dx = rng.gauss(0, 22 * k)
        hgt = (70 + 60 * rng.random()) * k * (0.8 + 0.2 * math.sin(t * 9 + i))
        wd = (16 + 10 * rng.random()) * k
        cv2.ellipse(layer, (int(CX + dx), int(BASE - hgt / 2)), (max(1, int(wd)), max(1, int(hgt / 2))),
                    0, 0, 360, (0, 90 + int(60 * rng.random()), 255), -1)
        cv2.ellipse(layer, (int(CX + dx * 0.6), int(BASE - hgt * 0.35)),
                    (max(1, int(wd * 0.6)), max(1, int(hgt * 0.3))), 0, 0, 360, (40, 200, 255), -1)
    cv2.ellipse(layer, (CX, int(BASE - 18 * k)), (max(1, int(26 * k)), max(1, int(18 * k))), 0, 0, 360, (200, 245, 255), -1)
    return cv2.GaussianBlur(layer, (9, 9), 0)


def generate(path="demo.mp4"):
    rng, nrng = random.Random(7), np.random.default_rng(7)
    bg = _background()
    wr = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    if not wr.isOpened():
        raise RuntimeError("VideoWriter nahi khula")
    smoke = []
    for i in range(FPS * SECONDS):
        t = i / FPS
        f = bg.copy()
        if 1.5 < t < 5.0:                                       # insaan guzarta hai (harkat, par aag nahi)
            x = int(70 + (t - 1.5) * 150)
            cv2.rectangle(f, (x, 215), (x + 42, 330), (200, 90, 40), -1)
            cv2.circle(f, (x + 21, 195), 18, (40, 50, 70), -1)
        k = _envelope(t)
        if k > 0:
            fl = _flame(t, k, rng)
            f = cv2.add(f, fl)
            f = cv2.addWeighted(f, 1.0, cv2.GaussianBlur(fl, (0, 0), 22), 0.9, 0)
        if FIRE_ON + 1 < t < FIRE_OFF + 4:
            for _ in range(2):
                smoke.append([CX + rng.gauss(0, 12), BASE - 110 * max(k, 0.4), 14.0, 0])
        layer = np.zeros((H, W), np.float32)
        alive = []
        for p in smoke:
            p[1] -= 1.7; p[0] += rng.gauss(0, 0.7); p[2] += 0.35; p[3] += 1
            if p[3] < 150 and p[1] > -40:
                cv2.circle(layer, (int(p[0]), int(p[1])), int(p[2]), 0.30, -1)
                alive.append(p)
        smoke = alive
        layer = cv2.GaussianBlur(layer, (0, 0), 12)
        a = np.clip(layer * 1.4, 0, 0.65)[..., None]
        f = (f.astype(np.float32) * (1 - a) + 172 * a)
        f = np.clip(f + nrng.normal(0, 2.0, f.shape), 0, 255).astype(np.uint8)
        wr.write(f)
    wr.release()
    return path


if __name__ == "__main__":
    print("Created:", generate())
