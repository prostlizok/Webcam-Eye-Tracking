import time

import cv2
import numpy as np


def compute_grid_points(order, sw: int, sh: int, margin_ratio: float = 0.10):
    if not order:
        return []

    max_r = max(r for r, _ in order)
    max_c = max(c for _, c in order)

    mx, my = int(sw * margin_ratio), int(sh * margin_ratio)
    gw, gh = sw - 2 * mx, sh - 2 * my

    step_x = 0 if max_c == 0 else gw / max_c
    step_y = 0 if max_r == 0 else gh / max_r

    return [(mx + int(c * step_x), my + int(r * step_y)) for r, c in order]


def wait_for_face_and_countdown(cap, gaze_estimator, sw, sh, dur: int = 2) -> bool:
    cv2.namedWindow("Calibration", cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty("Calibration", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    fd_start = None
    countdown = False
    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        f, blink = gaze_estimator.extract_features(frame)
        face = f is not None and not blink
        canvas = np.full((sh, sw, 3), 255, dtype=np.uint8)
        now = time.time()
        if face:
            if not countdown:
                fd_start = now
                countdown = True
            elapsed = now - fd_start
            if elapsed >= dur:
                return True
            t = elapsed / dur
            e = t * t * (3 - 2 * t)
            ang = 360 * (1 - e)
            cv2.ellipse(
                canvas,
                (sw // 2, sh // 2),
                (50, 50),
                0,
                -90,
                -90 + ang,
                (0, 165, 255),
                -1,
            )
            
            countdown_txt = "Calibration starting..."
            countdown_size, _ = cv2.getTextSize(countdown_txt, cv2.FONT_HERSHEY_SIMPLEX, 1.5, 2)
            countdown_x = (sw - countdown_size[0]) // 2
            countdown_y = sh // 2 + 120
            cv2.putText(
                canvas, countdown_txt, (countdown_x, countdown_y), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (50, 50, 50), 2
            )
        else:
            countdown = False
            fd_start = None
            if f is None:
                txt = "Face not detected - Position yourself in front of camera"
            else:
                txt = "Blinking detected - Keep eyes open"
            fs = 1.5
            thick = 2
            size, _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, fs, thick)
            tx = (sw - size[0]) // 2
            ty = (sh + size[1]) // 2
            cv2.putText(
                canvas, txt, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, fs, (0, 0, 255), thick
            )
            
            inst_txt = "Press ESC to cancel"
            inst_size, _ = cv2.getTextSize(inst_txt, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)
            inst_x = (sw - inst_size[0]) // 2
            inst_y = ty + 60
            cv2.putText(
                canvas, inst_txt, (inst_x, inst_y), cv2.FONT_HERSHEY_SIMPLEX, 1, (100, 100, 100), 2
            )
        cv2.imshow("Calibration", canvas)
        if cv2.waitKey(1) == 27:
            return False


def _pulse_and_capture(
    gaze_estimator,
    cap,
    pts,
    sw: int,
    sh: int,
    pulse_d: float = 1.0,
    cd_d: float = 1.0,
):
    feats, targs = [], []

    for x, y in pts:
        ps = time.time()
        final_radius = 20
        while True:
            e = time.time() - ps
            if e > pulse_d:
                break
            ok, frame = cap.read()
            if not ok:
                continue
            canvas = np.full((sh, sw, 3), 255, dtype=np.uint8)
            radius = 15 + int(15 * abs(np.sin(2 * np.pi * e)))
            final_radius = radius
            cv2.circle(canvas, (x, y), radius, (0, 165, 255), -1)
            cv2.imshow("Calibration", canvas)
            if cv2.waitKey(1) == 27:
                return None
        cs = time.time()
        while True:
            e = time.time() - cs
            if e > cd_d:
                break
            ok, frame = cap.read()
            if not ok:
                continue
            canvas = np.full((sh, sw, 3), 255, dtype=np.uint8)
            
            cv2.circle(canvas, (x, y), final_radius, (0, 165, 255), -1)
            
            t = e / cd_d
            ease = t * t * (3 - 2 * t)
            angle_rad = 2 * np.pi * ease - np.pi/2
            
            clock_radius = 35
            clock_x = x + int(clock_radius * np.cos(angle_rad))
            clock_y = y + int(clock_radius * np.sin(angle_rad))
            
            cv2.circle(canvas, (x, y), clock_radius, (200, 200, 200), 2)
            
            cv2.circle(canvas, (clock_x, clock_y), 8, (100, 100, 100), -1)
            
            cv2.imshow("Calibration", canvas)
            if cv2.waitKey(1) == 27:
                return None
            ft, blink = gaze_estimator.extract_features(frame)
            if ft is not None and not blink:
                feats.append(ft)
                targs.append([x, y])

    return feats, targs
