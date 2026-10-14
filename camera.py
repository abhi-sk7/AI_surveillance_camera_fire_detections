"""Camera reader: DroidCam / webcam / video file. Disconnect hone par auto-reconnect."""
import os, time, threading
import cv2


def _candidates(src):
    if isinstance(src, int) or os.path.isfile(str(src)):
        return [src]
    base = str(src).rstrip("/")
    if base.count("/") > 2:                      # pura path diya hai
        return [base]
    return [base + "/video", base + "/mjpegfeed", base + "/video?640x480"]


def _capture(url):
    if isinstance(url, str) and url.startswith("http"):
        try:   # timeout ke saath (OpenCV >= 4.5.2), taki band camera par atke nahi
            return cv2.VideoCapture(url, cv2.CAP_FFMPEG,
                                    [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 6000,
                                     cv2.CAP_PROP_READ_TIMEOUT_MSEC, 6000])
        except Exception:
            pass
    return cv2.VideoCapture(url)


def open_source(src, quiet=False):
    for url in _candidates(src):
        if not quiet:
            print("   try:", url, flush=True)
        try:
            cap = _capture(url)
        except Exception:
            continue
        ok = False
        if cap.isOpened():
            for _ in range(8):
                ok, _f = cap.read()
                if ok:
                    break
                time.sleep(0.15)
        if ok:
            try:
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            except Exception:
                pass
            return cap
        cap.release()
    return None


class CamStream:
    """Background thread: hamesha latest frame rakhta hai (lag nahi), band hone par reconnect."""
    def __init__(self, sources):
        self.sources = sources if isinstance(sources, list) else [sources]
        self.frame, self.idx = None, 0
        self.connected, self.active, self.fps = False, None, 25.0
        self.running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def _connect(self):
        for s in self.sources:
            print("Camera source:", s, flush=True)
            cap = open_source(s)
            if cap is not None:
                self.active = s
                f = cap.get(cv2.CAP_PROP_FPS)
                self.fps = f if f and 5 < f < 120 else 25.0
                return cap
        return None

    def _loop(self):
        cap = None
        while self.running:
            if cap is None:
                cap = self._connect()
                if cap is None:
                    self.connected = False
                    time.sleep(3)
                    continue
                self.connected = True
                print("Camera connected:", self.active, flush=True)
            ok, frame = cap.read()
            is_file = os.path.isfile(str(self.active))
            if ok:
                self.frame = frame
                self.idx += 1
                if is_file:
                    time.sleep(1.0 / self.fps)
            elif is_file:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)      # video khatam -> dobara
            else:
                print("Camera disconnect, reconnect ho raha hai...", flush=True)
                cap.release()
                cap = None
                self.connected = False

    def stop(self):
        self.running = False
