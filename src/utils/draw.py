from __future__ import annotations

import cv2
import numpy as np


def draw_cursor(
    canvas,
    x: int,
    y: int,
    alpha: float,
    *,
    radius_outer: int = 30,
    radius_inner: int = 25,
    color_outer: tuple[int, int, int] = (0, 0, 255),
    color_inner: tuple[int, int, int] = (255, 255, 255),
):
    if alpha <= 0.0:
        return canvas

    overlay = canvas.copy()
    cv2.circle(overlay, (int(x), int(y)), radius_outer, color_outer, -1)
    if radius_inner > 0:
        cv2.circle(overlay, (int(x), int(y)), radius_inner, color_inner, -1)

    cv2.addWeighted(overlay, alpha * 0.6, canvas, 1 - alpha * 0.6, 0, canvas)
    return canvas


def draw_gaze_point(
    canvas,
    x: int,
    y: int,
    alpha: float = 1.0,
    style: str = "crosshair",
    color: tuple[int, int, int] = (255, 0, 0),
    size: int = 15,
):
    """
    Draw gaze prediction point with different styles
    
    Styles:
    - 'crosshair': Cross with circle
    - 'diamond': Diamond shape
    - 'square': Square with border
    - 'pulse': Pulsing circle
    - 'target': Target-like circles
    """
    if alpha <= 0.0:
        return canvas
    
    x, y = int(x), int(y)
    overlay = canvas.copy()
    
    if style == "crosshair":
        # Cross lines
        cv2.line(overlay, (x - size, y), (x + size, y), color, 3)
        cv2.line(overlay, (x, y - size), (x, y + size), color, 3)
        # Center circle
        cv2.circle(overlay, (x, y), size // 3, color, -1)
        cv2.circle(overlay, (x, y), size // 5, (255, 255, 255), -1)
        
    elif style == "diamond":
        # Diamond shape
        pts = np.array([
            [x, y - size],
            [x + size, y],
            [x, y + size],
            [x - size, y]
        ], np.int32)
        cv2.fillPoly(overlay, [pts], color)
        cv2.polylines(overlay, [pts], True, (255, 255, 255), 2)
        
    elif style == "square":
        # Square with border
        cv2.rectangle(overlay, (x - size, y - size), (x + size, y + size), color, -1)
        cv2.rectangle(overlay, (x - size + 3, y - size + 3), (x + size - 3, y + size - 3), (255, 255, 255), -1)
        
    elif style == "pulse":
        # Pulsing effect (size varies with time)
        import time
        pulse_factor = 0.7 + 0.3 * abs(np.sin(time.time() * 4))
        radius = int(size * pulse_factor)
        cv2.circle(overlay, (x, y), radius, color, -1)
        cv2.circle(overlay, (x, y), radius // 2, (255, 255, 255), -1)
        
    elif style == "target":
        # Target-like concentric circles
        cv2.circle(overlay, (x, y), size, color, 3)
        cv2.circle(overlay, (x, y), size // 2, color, 2)
        cv2.circle(overlay, (x, y), size // 4, color, -1)
        
    else:  # default circle
        cv2.circle(overlay, (x, y), size, color, -1)
        cv2.circle(overlay, (x, y), size // 2, (255, 255, 255), -1)
    
    cv2.addWeighted(overlay, alpha, canvas, 1 - alpha, 0, canvas)
    return canvas


def draw_target_point(
    canvas,
    x: int,
    y: int,
    style: str = "modern",
    color: tuple[int, int, int] = (0, 255, 0),
    size: int = 20,
    animation_phase: float = 0.0,
):
    """
    Draw target/calibration point with different styles
    
    Styles:
    - 'modern': Sleek circle with glow
    - 'classic': Traditional double circle
    - 'animated': Animated expanding rings
    - 'gradient': Gradient filled circle
    """
    x, y = int(x), int(y)
    
    if style == "modern":
        # Glow effect
        for i in range(5, 0, -1):
            alpha = 0.1 * i
            radius = size + i * 3
            overlay = canvas.copy()
            cv2.circle(overlay, (x, y), radius, color, -1)
            cv2.addWeighted(overlay, alpha, canvas, 1 - alpha, 0, canvas)
        
        # Main circle
        cv2.circle(canvas, (x, y), size, color, -1)
        cv2.circle(canvas, (x, y), size // 2, (255, 255, 255), -1)
        
    elif style == "animated":
        # Expanding rings
        for i in range(3):
            phase_offset = i * 0.33
            ring_alpha = max(0, 1 - ((animation_phase + phase_offset) % 1))
            ring_radius = int(size * (1 + ((animation_phase + phase_offset) % 1) * 2))
            
            if ring_alpha > 0:
                overlay = canvas.copy()
                cv2.circle(overlay, (x, y), ring_radius, color, 3)
                cv2.addWeighted(overlay, ring_alpha * 0.5, canvas, 1 - ring_alpha * 0.5, 0, canvas)
        
        # Center point
        cv2.circle(canvas, (x, y), size // 2, color, -1)
        
    elif style == "gradient":
        # Simulate gradient with multiple circles
        for i in range(size, 0, -2):
            intensity = int(255 * (i / size))
            grad_color = (
                min(255, color[0] * intensity // 255),
                min(255, color[1] * intensity // 255),
                min(255, color[2] * intensity // 255)
            )
            cv2.circle(canvas, (x, y), i, grad_color, -1)
        
    else:  # classic
        cv2.circle(canvas, (x, y), size, color, -1)
        cv2.circle(canvas, (x, y), size // 2, (255, 255, 255), -1)
    
    return canvas


def make_thumbnail(
    frame,
    *,
    size: tuple[int, int] = (320, 240),
    border: int = 2,
    border_color: tuple[int, int, int] = (255, 255, 255),
):
    img = cv2.resize(frame, size)
    return cv2.copyMakeBorder(
        img,
        border,
        border,
        border,
        border,
        cv2.BORDER_CONSTANT,
        value=border_color,
    )
