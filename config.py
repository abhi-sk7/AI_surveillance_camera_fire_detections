# ======================= SETTINGS (yahan sab change karo) =======================
DETECTOR = "auto"        # "auto"   : best.pt ho to YOLO, nahi to built-in detector (bina training ke chalega)
                         # "yolo"   : sirf YOLO     |  "classic": sirf built-in (colour + motion)
MODEL_PATH = "best.pt"   # Colab se trained model (optional)

SOURCE = 0                            # PC par connected DroidCam Video virtual camera
FALLBACK_SOURCES = []                 # e.g. [1] -> another local webcam

MAX_WIDTH = 960          # bada frame is width tak chhota kiya jata hai (speed ke liye)

# --- YOLO settings ---
CONF = 0.70
IMG_SIZE = 320             # CPU-friendly inference size for the live camera
MIN_BOX_AREA = 0.002

# --- Built-in (classic) detector settings ---
MIN_FIRE_AREA = 0.0015   # aag ka hissa frame ka kam se kam itna (0.15%)
MIN_SMOKE_AREA = 0.02    # dhuan ka hissa kam se kam itna (2%)
CLASSIC_SMOKE = True     # dhuan detection (experimental, False karo agar false alarm aaye)

# --- Alert logic ---
WINDOW = 12              # last kitne frames dekhne hain
MIN_HITS = 7             # in me se kitno me detect ho to ALERT
COOLDOWN = 30            # seconds, ek alert ke baad dobara alert se pehle wait
SIREN = True             # PC par beep (Windows)
SAVE_DIR = "alerts"      # alert photos

# --- Web dashboard ---
WEB_HOST = "127.0.0.1"   # "0.0.0.0" karo to same WiFi ke phone se bhi khulega
WEB_PORT = 5000          # busy ho to agla free port apne aap use hoga
AUTO_OPEN_BROWSER = True
# ================================================================================
