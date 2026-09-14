"""
╔══════════════════════════════════════════════════════════════════════╗
║        AIR-WRITING — CHALK BOARD EDITION  v3.0                      ║
║        MediaPipe + OpenCV  |  Dual-Hand  |  HSV Color Picker        ║
╚══════════════════════════════════════════════════════════════════════╝

TANGAN KANAN — MENGGAMBAR (ketebalan mengikuti jumlah jari):
  1 jari   → Gambar, tebal  4px
  2 jari   → Gambar, tebal  8px
  3 jari   → Gambar, tebal 16px
  4 jari   → Gambar, tebal 24px
  5 jari   → Gambar, tebal 30px
  PINCH    (jempol+telunjuk < 40px) → COLOR PICKER — geser kiri/kanan
                                       untuk ubah Hue (0-360 derajat)

TANGAN KIRI — MENGHAPUS (ukuran mengikuti jumlah jari):
  1 jari   → Hapus, ukuran  8px
  2 jari   → Hapus, ukuran 16px
  3 jari   → Hapus, ukuran 32px
  4 jari   → Hapus, ukuran 50px
  5 jari (bergerak) → Hapus, ukuran 72px
  5 jari (DIAM ~1.2 detik) → CLEAR PAGE

GESTURE GABUNGAN:
  5 jari KANAN + 5 jari KIRI bersamaan → SCREEN CAPTURE
  (mengalahkan aksi gambar/hapus individual pada frame itu)

KEYBOARD:
  B  → Ganti background PNG
  C  → Clear canvas
  S  → Save screenshot
  Q  → Keluar
"""

import cv2
import mediapipe as mp
import numpy as np
from collections import deque
import time
import glob
import os
import sys


# ─────────────────────────────────────────────────────────────────
# KONFIGURASI
# ─────────────────────────────────────────────────────────────────
CONFIG = {
    "CAMERA_INDEX": 0,
    "FRAME_WIDTH":  1280,
    "FRAME_HEIGHT": 720,
    "DETECTION_CONFIDENCE": 0.75,
    "TRACKING_CONFIDENCE":  0.75,
    "SMOOTH_BUFFER": 5,
    # Pinch threshold: jarak piksel jempol-telunjuk di bawah nilai ini
    "PINCH_THRESHOLD": 40,
    # Sensitivitas color picker: derajat Hue per piksel gerakan X
    "HUE_SENSITIVITY": 0.25,
    # Debounce capture (detik) agar satu gesture tidak memicu berkali-kali
    "CAPTURE_DEBOUNCE": 1.5,
    # "5 jari diam" = tahan 5 jari kiri tetap diam di satu titik selama
    # durasi ini (detik) untuk memicu Clear Page
    "CLEAR_HOLD_DURATION": 1.2,
    # Toleransi pergerakan (piksel) selama menahan — di atas ini dianggap
    # gerak (hapus biasa 72px), bukan diam untuk clear page
    "CLEAR_HOLD_TOLERANCE": 18,
}

# Ketebalan gambar — tangan kanan (1-5 jari, termasuk jempol)
RIGHT_SIZE_MAP = {1: 4, 2: 8, 3: 16, 4: 24, 5: 30}

# Ukuran hapus — tangan kiri (1-5 jari, termasuk jempol)
LEFT_SIZE_MAP = {1: 8, 2: 16, 3: 32, 4: 50, 5: 72}

# ─────────────────────────────────────────────────────────────────
# LANDMARK IDs
# ─────────────────────────────────────────────────────────────────
mp_hands = mp.solutions.hands
LM       = mp_hands.HandLandmark

TIPS = [LM.INDEX_FINGER_TIP, LM.MIDDLE_FINGER_TIP,
        LM.RING_FINGER_TIP,  LM.PINKY_TIP]
PIPS = [LM.INDEX_FINGER_PIP, LM.MIDDLE_FINGER_PIP,
        LM.RING_FINGER_PIP,  LM.PINKY_PIP]


# ─────────────────────────────────────────────────────────────────
# KONVERSI WARNA HSV
# ─────────────────────────────────────────────────────────────────

def hue_to_bgr(hue_deg):
    """
    Konversi Hue (0-360 derajat) ke BGR dengan Saturation=255, Value=255.
    OpenCV menyimpan Hue sebagai 0-179 (setengah dari 360 derajat).
    """
    hue_cv    = int(hue_deg / 2) % 180
    hsv_pixel = np.uint8([[[hue_cv, 255, 255]]])
    bgr_pixel = cv2.cvtColor(hsv_pixel, cv2.COLOR_HSV2BGR)
    b = int(bgr_pixel[0, 0, 0])
    g = int(bgr_pixel[0, 0, 1])
    r = int(bgr_pixel[0, 0, 2])
    return (b, g, r)


def hue_to_name(hue_deg):
    """Nama warna kasar berdasarkan Hue."""
    h = hue_deg % 360
    if h < 15 or h >= 345:
        return "Merah"
    elif h < 45:
        return "Oranye"
    elif h < 75:
        return "Kuning"
    elif h < 150:
        return "Hijau"
    elif h < 195:
        return "Cyan"
    elif h < 255:
        return "Biru"
    elif h < 285:
        return "Ungu"
    else:
        return "Pink"


# ─────────────────────────────────────────────────────────────────
# CHALK RENDERING
# ─────────────────────────────────────────────────────────────────

def chalk_line(canvas, pt1, pt2, color, thickness):
    """
    Gambar garis efek kapur: multi-serat + noise granular.
    Setiap serat di-offset sedikit dari garis utama,
    dengan opacity dan ukuran titik yang acak per titik.
    """
    if pt1 is None or pt2 is None:
        return
    x1, y1  = pt1
    x2, y2  = pt2
    dist    = max(1, int(np.hypot(x2 - x1, y2 - y1)))
    num_pts = max(dist, 2)
    strands = max(2, thickness // 3)
    ch, cw  = canvas.shape[:2]

    for _ in range(strands):
        ox = np.random.randint(-max(1, thickness // 4), max(2, thickness // 4))
        oy = np.random.randint(-max(1, thickness // 4), max(2, thickness // 4))
        xs = np.linspace(x1 + ox, x2 + ox, num_pts).astype(int)
        ys = np.linspace(y1 + oy, y2 + oy, num_pts).astype(int)
        for px, py in zip(xs, ys):
            if 0 <= px < cw and 0 <= py < ch:
                alpha      = np.random.uniform(0.4, 1.0)
                brightness = np.random.uniform(0.7, 1.0)
                r_size     = max(1, np.random.randint(1, max(2, thickness // 2)))
                c          = tuple(int(ch_val * alpha * brightness)
                                   for ch_val in color)
                cv2.circle(canvas, (px, py), r_size, c, -1, cv2.LINE_AA)


def chalk_eraser(canvas, cx, cy, radius):
    """Hapus area dengan efek kapur soft-edge. Ukuran mengikuti `radius`."""
    radius = max(radius, 3)
    mask = np.zeros(canvas.shape[:2], dtype=np.uint8)
    cv2.circle(mask, (cx, cy), radius, 255, -1)
    mask = cv2.GaussianBlur(mask, (21, 21), 0)
    for c in range(3):
        canvas[:, :, c] = np.where(
            mask > 0,
            np.maximum(0, canvas[:, :, c].astype(int) - mask.astype(int) // 4),
            canvas[:, :, c]
        ).astype(np.uint8)
    cv2.circle(canvas, (cx, cy), max(1, radius // 2), (0, 0, 0), -1)


# ─────────────────────────────────────────────────────────────────
# FINGER STATE
# ─────────────────────────────────────────────────────────────────

def fingers_up_count(lm, hand_label):
    """
    Deteksi jari tegak: tip.y < pip.y (Y lebih kecil = lebih atas layar).
    Ibu jari dideteksi secara horizontal (sumbu X) karena arah gerakannya
    berbeda dari 4 jari lainnya.

    Returns: total_count (0-5, termasuk ibu jari)
    """
    states = [lm[tip].y < lm[pip].y for tip, pip in zip(TIPS, PIPS)]
    if hand_label == "Right":
        thumb = lm[LM.THUMB_TIP].x < lm[LM.THUMB_IP].x
    else:
        thumb = lm[LM.THUMB_TIP].x > lm[LM.THUMB_IP].x
    total = sum(states) + (1 if thumb else 0)
    return total


def pinch_distance(lm, fw, fh):
    """
    Hitung jarak Euclidean piksel antara jempol (ID 4) dan telunjuk (ID 8):
        d = sqrt((x2-x1)^2 + (y2-y1)^2)

    Returns: (jarak_pixel, midpoint_x, midpoint_y)
    """
    tx = lm[LM.THUMB_TIP].x * fw
    ty = lm[LM.THUMB_TIP].y * fh
    ix = lm[LM.INDEX_FINGER_TIP].x * fw
    iy = lm[LM.INDEX_FINGER_TIP].y * fh
    dist = np.sqrt((tx - ix) ** 2 + (ty - iy) ** 2)
    mx   = int((tx + ix) / 2)
    my   = int((ty + iy) / 2)
    return float(dist), mx, my


def lm_pixel(lm_point, fw, fh):
    """Konversi landmark ternormalisasi ke piksel."""
    return int(lm_point.x * fw), int(lm_point.y * fh)


# ─────────────────────────────────────────────────────────────────
# WEIGHTED MOVING AVERAGE
# ─────────────────────────────────────────────────────────────────

class WMA:
    def __init__(self, size):
        self.size = size
        self.bx   = deque(maxlen=size)
        self.by   = deque(maxlen=size)
        self.w    = np.arange(1, size + 1, dtype=float)

    def update(self, x, y):
        self.bx.append(x)
        self.by.append(y)

    def get(self):
        if not self.bx:
            return None, None
        n = len(self.bx)
        w = self.w[-n:]
        return (int(np.average(list(self.bx), weights=w)),
                int(np.average(list(self.by), weights=w)))

    def reset(self):
        self.bx.clear()
        self.by.clear()


# ─────────────────────────────────────────────────────────────────
# BACKGROUND LOADER
# ─────────────────────────────────────────────────────────────────

def load_backgrounds(script_dir, fw, fh):
    files = []
    for pat in ["*.png", "*.jpg", "*.jpeg"]:
        files.extend(glob.glob(os.path.join(script_dir, pat)))
    files = [f for f in files
             if "screenshot" not in f.lower() and "airchalk" not in f.lower()]
    bgs = []
    for f in files:
        img = cv2.imread(f)
        if img is not None:
            bgs.append((cv2.resize(img, (fw, fh)), os.path.basename(f)))
    if not bgs:
        board = np.zeros((fh, fw, 3), dtype=np.uint8)
        board[:] = (40, 70, 45)
        noise = np.random.randint(0, 12, (fh, fw, 3), dtype=np.uint8)
        board = np.clip(board.astype(int) + noise, 0, 255).astype(np.uint8)
        bgs.append((board, "Papan Tulis (default)"))
    return bgs


# ─────────────────────────────────────────────────────────────────
# COLOR PICKER VISUAL
# ─────────────────────────────────────────────────────────────────

def draw_color_picker_ui(frame, current_hue, pinch_x, pinch_y):
    """
    Tampilkan rainbow bar horizontal di atas layar sebagai spektrum Hue.
    Indikator putih menunjukkan posisi Hue saat ini.
    """
    fw     = frame.shape[1]
    bar_h  = 28
    bar_y0 = 130
    bar_x0 = 60
    bar_w  = fw - 120

    for i in range(bar_w):
        hue_i   = int(i / bar_w * 360)
        color_i = hue_to_bgr(hue_i)
        cv2.line(frame,
                 (bar_x0 + i, bar_y0),
                 (bar_x0 + i, bar_y0 + bar_h),
                 color_i, 1)

    cv2.rectangle(frame,
                  (bar_x0 - 1, bar_y0 - 1),
                  (bar_x0 + bar_w + 1, bar_y0 + bar_h + 1),
                  (220, 220, 220), 1)

    ind_x = bar_x0 + int(current_hue / 360.0 * bar_w)
    ind_x = max(bar_x0 + 4, min(bar_x0 + bar_w - 4, ind_x))
    cv2.rectangle(frame,
                  (ind_x - 4, bar_y0 - 5),
                  (ind_x + 4, bar_y0 + bar_h + 5),
                  (255, 255, 255), 2)
    cv2.rectangle(frame,
                  (ind_x - 3, bar_y0 - 4),
                  (ind_x + 3, bar_y0 + bar_h + 4),
                  hue_to_bgr(current_hue), -1)

    label = f"COLOR PICKER  Hue: {current_hue:.0f}  {hue_to_name(current_hue)}"
    cv2.putText(frame, label, (bar_x0, bar_y0 - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                (220, 220, 220), 1, cv2.LINE_AA)

    cur_bgr = hue_to_bgr(current_hue)
    cv2.circle(frame, (pinch_x, pinch_y), 18, cur_bgr,       -1, cv2.LINE_AA)
    cv2.circle(frame, (pinch_x, pinch_y), 20, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(frame, "PILIH",
                (pinch_x - 18, pinch_y + 35),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                (220, 220, 220), 1, cv2.LINE_AA)


def draw_save_flash(frame, fw, fh, text="TERSIMPAN!"):
    """Flash hijau semi-transparan sebagai feedback saat save/capture."""
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (fw, fh), (50, 200, 80), -1)
    cv2.addWeighted(overlay, 0.25, frame, 0.75, 0, frame)
    text_x = fw // 2 - (len(text) * 17)
    cv2.putText(frame, text,
                (text_x, fh // 2),
                cv2.FONT_HERSHEY_SIMPLEX, 1.6,
                (255, 255, 255), 3, cv2.LINE_AA)


def draw_hold_progress(frame, cx, cy, progress, radius=34):
    """
    Gambar cincin progres (arc) di sekitar titik tangan kiri saat
    'genggam 2 jari' sedang ditahan menuju Clear Page.

    progress: nilai 0.0-1.0, makin penuh cincinnya makin dekat ke trigger.
    """
    progress = max(0.0, min(1.0, progress))
    # Lingkaran dasar (track) — abu-abu redup
    cv2.circle(frame, (cx, cy), radius, (70, 70, 70), 3, cv2.LINE_AA)
    # Arc progres — mulai dari atas (-90 derajat), searah jarum jam
    end_angle = -90 + int(360 * progress)
    color = (60, 140, 255) if progress < 1.0 else (60, 220, 80)
    cv2.ellipse(frame, (cx, cy), (radius, radius), 0,
                -90, end_angle, color, 4, cv2.LINE_AA)
    cv2.putText(frame, "TAHAN DIAM",
                (cx - 48, cy + radius + 22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                (60, 140, 255), 1, cv2.LINE_AA)


# ─────────────────────────────────────────────────────────────────
# HUD
# ─────────────────────────────────────────────────────────────────

def draw_hud(frame, color_bgr, color_name, hue_deg,
             gesture_r, gesture_l, fps, bg_name):
    h, w = frame.shape[:2]
    font = cv2.FONT_HERSHEY_SIMPLEX

    cv2.rectangle(frame, (8, 8), (370, 125), (15, 15, 15), -1)
    cv2.rectangle(frame, (8, 8), (370, 125), (60, 60, 60),  1)

    cv2.rectangle(frame, (18, 18), (52, 52), color_bgr, -1)
    cv2.rectangle(frame, (18, 18), (52, 52), (200, 200, 200), 1)
    cv2.putText(frame, f"{color_name}  Hue: {hue_deg:.0f}",
                (60, 38), font, 0.58, (220, 220, 220), 1, cv2.LINE_AA)
    cv2.putText(frame, f"Kanan: {gesture_r}",
                (18, 65), font, 0.52, (180, 180, 180), 1, cv2.LINE_AA)
    cv2.putText(frame, f"Kiri : {gesture_l}",
                (18, 90), font, 0.52, (180, 180, 180), 1, cv2.LINE_AA)
    cv2.putText(frame, f"BG: {bg_name}",
                (18, 112), font, 0.42, (100, 100, 100), 1, cv2.LINE_AA)

    cv2.putText(frame, f"FPS {fps:.0f}",
                (w - 110, 35), font, 0.65, (160, 160, 160), 1, cv2.LINE_AA)


def draw_gesture_guide(frame):
    """
    Panel panduan gesture lengkap di pojok kiri bawah layar.
    Latar semi-transparan agar tidak terlalu menutupi kamera.
    """
    h, w   = frame.shape[:2]
    font   = cv2.FONT_HERSHEY_SIMPLEX

    panel_w = 300
    panel_h = 190
    x0      = 8
    y0      = h - panel_h - 8

    # Latar semi-transparan
    overlay = frame.copy()
    cv2.rectangle(overlay, (x0, y0), (x0 + panel_w, y0 + panel_h),
                  (15, 15, 15), -1)
    cv2.addWeighted(overlay, 0.78, frame, 0.22, 0, frame)
    cv2.rectangle(frame, (x0, y0), (x0 + panel_w, y0 + panel_h),
                  (70, 70, 70), 1)

    # Baris-baris panduan: (teks, warna, skala)
    lines = [
        ("PANDUAN GESTURE", (255, 255, 255), 0.5),
        ("Kanan: 1-5 jari = Gambar 4-30px", (180, 230, 180), 0.38),
        ("       Pinch = Pilih Warna",       (180, 230, 180), 0.38),
        ("Kiri : 1-4 jari = Hapus 8-50px",   (180, 200, 255), 0.38),
        ("       5 jari gerak = Hapus 72px", (180, 200, 255), 0.38),
        ("       5 jari DIAM = Clear Page",  (140, 180, 255), 0.38),
        ("Gabungan: 5+5 jari = Capture",     (255, 220, 140), 0.38),
        ("B:BG  C:Clear  S:Save  Q:Keluar",  (140, 140, 140), 0.36),
    ]

    y = y0 + 24
    for text, color, scale in lines:
        cv2.putText(frame, text, (x0 + 10, y),
                    font, scale, color, 1, cv2.LINE_AA)
        y += 21


def draw_hue_swatches(frame):
    """Tampilkan 8 swatch warna referensi di sisi kanan layar."""
    x0   = frame.shape[1] - 32
    hues = [0, 30, 60, 120, 180, 210, 270, 300]
    for i, h in enumerate(hues):
        y0  = 140 + i * 46
        bgr = hue_to_bgr(h)
        cv2.rectangle(frame, (x0, y0), (x0 + 24, y0 + 38), bgr, -1)
        cv2.rectangle(frame, (x0, y0), (x0 + 24, y0 + 38),
                      (150, 150, 150), 1)


# ─────────────────────────────────────────────────────────────────
# SAVE / CAPTURE HELPER
# ─────────────────────────────────────────────────────────────────

def composite_and_save(canvas, bg_img, script_dir, shot_idx):
    """Gabungkan background + canvas (tanpa skeleton), simpan ke disk."""
    sf   = bg_img.copy()
    mask = np.any(canvas > 10, axis=2)
    sf[mask] = canvas[mask]
    fname = os.path.join(script_dir, f"airchalk_screenshot_{shot_idx:03d}.png")
    cv2.imwrite(fname, sf)
    return fname


# ─────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────

def main():
    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))

    cap = cv2.VideoCapture(CONFIG["CAMERA_INDEX"])
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CONFIG["FRAME_WIDTH"])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CONFIG["FRAME_HEIGHT"])
    cap.set(cv2.CAP_PROP_FPS, 60)
    FW = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    FH = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"[AirChalk v3] Kamera: {FW}x{FH}")

    backgrounds = load_backgrounds(script_dir, FW, FH)
    bg_idx = 0
    print(f"[AirChalk v3] {len(backgrounds)} background:")
    for i, (_, name) in enumerate(backgrounds):
        print(f"  [{i}] {name}")

    canvas = np.zeros((FH, FW, 3), dtype=np.uint8)

    hands_sol = mp_hands.Hands(
        static_image_mode        = False,
        max_num_hands            = 2,
        min_detection_confidence = CONFIG["DETECTION_CONFIDENCE"],
        min_tracking_confidence  = CONFIG["TRACKING_CONFIDENCE"],
    )
    mp_draw = mp.solutions.drawing_utils

    # State warna (HSV)
    current_hue = 0.0
    color_bgr   = hue_to_bgr(current_hue)
    color_name  = hue_to_name(current_hue)

    # Color picker state
    picker_active     = False
    picker_anchor_x   = None
    picker_anchor_hue = 0.0

    # Draw / erase smoothing (terpisah untuk tiap tangan)
    prev_pt_r    = None
    prev_pt_l    = None
    smoother_r   = WMA(CONFIG["SMOOTH_BUFFER"])
    smoother_l   = WMA(CONFIG["SMOOTH_BUFFER"])

    # Save / capture state
    last_capture_time = 0.0
    flash_until        = 0.0
    flash_text          = "TERSIMPAN!"
    shot_idx           = 0

    # 5 jari kiri diam -> Clear Page state
    clear_hold_anchor = None     # posisi (x,y) saat genggaman dimulai
    clear_hold_start  = 0.0      # timestamp mulai genggam
    clear_triggered   = False    # sudah ter-trigger, tunggu jari dilepas

    gesture_r_label = "—"
    gesture_l_label = "—"

    fps_buf = deque(maxlen=30)
    t_prev  = time.perf_counter()

    print("[AirChalk v3] Siap! Tekan Q untuk keluar.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # 1. Flip horizontal — efek cermin
        frame = cv2.flip(frame, 1)

        # 2. MediaPipe hand detection
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = hands_sol.process(rgb)
        rgb.flags.writeable = True

        # 3. FPS
        now = time.perf_counter()
        fps_buf.append(1.0 / max(now - t_prev, 1e-9))
        t_prev = now
        fps    = float(np.mean(fps_buf))

        # 4. Pisahkan tangan kanan & kiri
        right_lm = None
        left_lm  = None
        if results.multi_hand_landmarks:
            for hand_lm, hand_info in zip(results.multi_hand_landmarks,
                                           results.multi_handedness):
                label = hand_info.classification[0].label
                if label == "Right":
                    right_lm = hand_lm
                else:
                    left_lm = hand_lm

                mp_draw.draw_landmarks(
                    frame, hand_lm, mp_hands.HAND_CONNECTIONS,
                    mp_draw.DrawingSpec(
                        color=(255, 255, 255), thickness=1, circle_radius=3),
                    mp_draw.DrawingSpec(
                        color=(180, 220, 255), thickness=2),
                )

        # ── Hitung status awal kedua tangan (untuk cek gesture gabungan) ──
        cnt_r = fingers_up_count(right_lm.landmark, "Right") if right_lm else 0
        cnt_l = fingers_up_count(left_lm.landmark, "Left")   if left_lm  else 0

        dist_r = pmx_r = pmy_r = None
        if right_lm:
            dist_r, pmx_r, pmy_r = pinch_distance(right_lm.landmark, FW, FH)
        is_pinch_r = (dist_r is not None) and (dist_r < CONFIG["PINCH_THRESHOLD"])

        # ══════════════════════════════════════════════════════════
        # GESTURE GABUNGAN: 5 jari kanan + 5 jari kiri → SCREEN CAPTURE
        # ══════════════════════════════════════════════════════════
        combo_capture = (right_lm is not None and left_lm is not None
                          and not is_pinch_r
                          and cnt_r == 5 and cnt_l == 5)

        if combo_capture:
            gesture_r_label = "5j+5j -> CAPTURE"
            gesture_l_label = "5j+5j -> CAPTURE"
            prev_pt_r = None
            prev_pt_l = None
            clear_hold_anchor = None
            clear_triggered   = False

            if (now - last_capture_time) > CONFIG["CAPTURE_DEBOUNCE"]:
                bg_s, _ = backgrounds[bg_idx]
                fname   = composite_and_save(canvas, bg_s, script_dir, shot_idx)
                shot_idx          += 1
                last_capture_time  = now
                flash_until        = now + 0.7
                flash_text         = "CAPTURED!"
                print(f"[AirChalk v3] Screen capture: {fname}")

        else:
            # ══════════════════════════════════════════════════════
            # TANGAN KANAN — Color Picker / Gambar
            # ══════════════════════════════════════════════════════
            if right_lm:
                lm_r = right_lm.landmark
                raw_x, raw_y = lm_pixel(lm_r[LM.INDEX_FINGER_TIP], FW, FH)
                smoother_r.update(raw_x, raw_y)
                sx, sy = smoother_r.get()

                if is_pinch_r:
                    picker_active = True
                    prev_pt_r     = None

                    if picker_anchor_x is None:
                        picker_anchor_x   = pmx_r
                        picker_anchor_hue = current_hue

                    delta_x     = pmx_r - picker_anchor_x
                    current_hue = (picker_anchor_hue
                                   + delta_x * CONFIG["HUE_SENSITIVITY"]) % 360
                    color_bgr   = hue_to_bgr(current_hue)
                    color_name  = hue_to_name(current_hue)

                    gesture_r_label = f"PINCH -> Hue {current_hue:.0f}"
                    draw_color_picker_ui(frame, current_hue, pmx_r, pmy_r)

                else:
                    if picker_active:
                        picker_active   = False
                        picker_anchor_x = None

                    if cnt_r >= 1:
                        thickness = RIGHT_SIZE_MAP[cnt_r]
                        gesture_r_label = f"{cnt_r} jari -> {thickness}px"

                        if prev_pt_r is not None:
                            chalk_line(canvas, prev_pt_r, (sx, sy),
                                       color_bgr, thickness)
                        else:
                            chalk_line(canvas, (sx, sy), (sx + 1, sy + 1),
                                       color_bgr, thickness)
                        prev_pt_r = (sx, sy)

                        cv2.circle(frame, (sx, sy),
                                   max(3, thickness // 2),
                                   color_bgr, -1, cv2.LINE_AA)
                        cv2.circle(frame, (sx, sy),
                                   max(4, thickness // 2 + 2),
                                   (255, 255, 255), 1, cv2.LINE_AA)
                    else:
                        gesture_r_label = "Idle"
                        prev_pt_r = None
                        smoother_r.reset()
            else:
                gesture_r_label = "—"
                prev_pt_r       = None
                picker_active   = False
                picker_anchor_x = None
                smoother_r.reset()

            # ══════════════════════════════════════════════════════
            # TANGAN KIRI — Hapus / 5 Jari Diam = Clear Page
            # ══════════════════════════════════════════════════════
            if left_lm:
                lm_l = left_lm.landmark
                raw_xl, raw_yl = lm_pixel(lm_l[LM.INDEX_FINGER_TIP], FW, FH)
                smoother_l.update(raw_xl, raw_yl)
                slx, sly = smoother_l.get()

                if cnt_l == 5:
                    # ── Cek apakah 5 jari ditahan diam ─────────────────
                    if clear_hold_anchor is None:
                        clear_hold_anchor   = (slx, sly)
                        clear_hold_start    = now
                        clear_triggered     = False

                    hd = np.hypot(slx - clear_hold_anchor[0],
                                  sly - clear_hold_anchor[1])

                    if hd <= CONFIG["CLEAR_HOLD_TOLERANCE"]:
                        # Tangan diam → hitung durasi menahan
                        held = now - clear_hold_start

                        if clear_triggered:
                            gesture_l_label = "Page Cleared (lepas dulu)"
                        elif held >= CONFIG["CLEAR_HOLD_DURATION"]:
                            # ── TRIGGER: Clear Page ─────────────────
                            canvas[:] = 0
                            clear_triggered = True
                            flash_until = now + 0.7
                            flash_text  = "PAGE CLEARED!"
                            gesture_l_label = "5j DIAM -> CLEARED"
                            print("[AirChalk v3] 5 jari diam -> Page Cleared.")
                        else:
                            progress = held / CONFIG["CLEAR_HOLD_DURATION"]
                            gesture_l_label = f"Diam... {held:.1f}s"
                            draw_hold_progress(frame, slx, sly, progress)
                    else:
                        # Bergerak melebihi toleransi → batal,
                        # perlakukan sebagai hapus biasa 72px
                        clear_hold_anchor = (slx, sly)
                        clear_hold_start  = now
                        clear_triggered   = False

                        radius = LEFT_SIZE_MAP[5]
                        gesture_l_label = f"5 jari -> hapus {radius}px"
                        cv2.circle(frame, (slx, sly), radius,
                                   (80, 80, 220), 2, cv2.LINE_AA)
                        chalk_eraser(canvas, slx, sly, radius)

                    prev_pt_l = (slx, sly)

                elif cnt_l >= 1:
                    # 1-4 jari → hapus normal, reset status diam
                    clear_hold_anchor = None
                    clear_triggered   = False

                    radius = LEFT_SIZE_MAP[cnt_l]
                    gesture_l_label = f"{cnt_l} jari -> hapus {radius}px"

                    cv2.circle(frame, (slx, sly), radius,
                               (80, 80, 220), 2, cv2.LINE_AA)
                    chalk_eraser(canvas, slx, sly, radius)
                    prev_pt_l = (slx, sly)

                else:
                    gesture_l_label   = "Idle"
                    prev_pt_l         = None
                    clear_hold_anchor = None
                    clear_triggered   = False
                    smoother_l.reset()
            else:
                gesture_l_label   = "—"
                prev_pt_l         = None
                clear_hold_anchor = None
                clear_triggered   = False
                smoother_l.reset()

        # ══════════════════════════════════════════════════════════
        # COMPOSITING: BG + Canvas + Skeleton
        # ══════════════════════════════════════════════════════════
        bg_img, bg_name = backgrounds[bg_idx]
        output = bg_img.copy()
        mask_draw = np.any(canvas > 10, axis=2)
        output[mask_draw] = canvas[mask_draw]

        # Overlay skeleton tangan (frame webcam, blended sangat tipis)
        output = cv2.addWeighted(output, 1.0, frame, 0.08, 0)

        if now < flash_until:
            draw_save_flash(output, FW, FH, flash_text)

        draw_hud(output, color_bgr, color_name, current_hue,
                 gesture_r_label, gesture_l_label, fps, bg_name)
        draw_hue_swatches(output)
        draw_gesture_guide(output)

        cv2.imshow("Air Writing — Chalk Board v3", output)

        # ── Keyboard ──────────────────────────────────────────────
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q') or key == 27:
            break
        elif key == ord('c'):
            canvas[:] = 0
            prev_pt_r = None
            prev_pt_l = None
            smoother_r.reset()
            smoother_l.reset()
            print("[AirChalk v3] Canvas dibersihkan.")
        elif key == ord('b'):
            bg_idx = (bg_idx + 1) % len(backgrounds)
            print(f"[AirChalk v3] Background: {backgrounds[bg_idx][1]}")
        elif key == ord('s'):
            bg_s, _ = backgrounds[bg_idx]
            fname   = composite_and_save(canvas, bg_s, script_dir, shot_idx)
            shot_idx    += 1
            flash_until  = now + 0.7
            flash_text   = "TERSIMPAN!"
            print(f"[AirChalk v3] Disimpan via keyboard: {fname}")

    cap.release()
    hands_sol.close()
    cv2.destroyAllWindows()
    print("[AirChalk v3] Selesai.")


if __name__ == "__main__":
    main()
