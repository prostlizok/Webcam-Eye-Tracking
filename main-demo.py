import sys
import time
import math
import cv2
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont

from src.calibration import run_9_point_calibration
from src.filters import KalmanSmoother, make_kalman, make_conservative_kalman
from src.gaze import GazeEstimator
from src.utils.screen import get_screen_size


class GazeDemo(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.screen_width, self.screen_height = get_screen_size()
        self.setGeometry(0, 0, self.screen_width, self.screen_height)
        
        print("🚀 Ініціалізація системи...")
        self.gaze_estimator = GazeEstimator(model_name="ridge")
        
        print("🎯 Запуск калібрування...")
        run_9_point_calibration(self.gaze_estimator, camera_index=0)
        
        print("🔧 Ініціалізація Kalman фільтра...")
        kalman = make_conservative_kalman()
        self.smoother = KalmanSmoother(kalman)
        self.smoother.tune(self.gaze_estimator, camera_index=0)
        
        self.cap = cv2.VideoCapture(0)
        
        self.gaze_x = self.gaze_y = None
        self.filtered_x = self.filtered_y = None
        self.blink_detected = False
        
        # Cursor animation
        self.cursor_alpha = 0.0
        self.cursor_step = 0.05
        
        # Display
        self.fps = 0
        self.prev_time = time.time()
        
        # Debug info
        self.contours = []
        
        # Set up timer for frame processing
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(16)  # ~60 fps
        
        print("🎬 Gaze tracking demo розпочато!")
        print("👁️ Дивіться на екран, курсор буде слідкувати за вашим поглядом")
        self.show()
    
    def update_frame(self):
        """Оновлює кадр та обробляє gaze tracking"""
        current_time = time.time()
        
        # Gaze tracking
        ret, frame = self.cap.read()
        if ret:
            features, self.blink_detected = self.gaze_estimator.extract_features(frame)
            
            if features is not None and not self.blink_detected:
                gaze_point = self.gaze_estimator.predict(np.array([features]))[0]
                self.gaze_x, self.gaze_y = map(int, gaze_point)
                self.filtered_x, self.filtered_y = self.smoother.step(self.gaze_x, self.gaze_y)
                
                # Get debug contours if available
                self.contours = self.smoother.debug.get("contours", [])
                
                # Increase cursor alpha (fade in)
                self.cursor_alpha = min(self.cursor_alpha + self.cursor_step, 1.0)
                
                # Debug output
                print(f"Gaze: ({self.filtered_x:4d}, {self.filtered_y:4d}) | FPS: {int(self.fps):3d} | Blink: {self.blink_detected}")
            else:
                self.gaze_x = self.gaze_y = None
                self.filtered_x = self.filtered_y = None
                self.contours = []
                
                # Decrease cursor alpha (fade out)
                self.cursor_alpha = max(self.cursor_alpha - self.cursor_step, 0.0)
        
        # Calculate FPS
        self.fps = 1 / (current_time - self.prev_time) if current_time - self.prev_time > 0 else 0
        self.prev_time = current_time
        
        # Update display
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Фон для інформації (темний напівпрозорий)
        info_rect_height = 120
        painter.setBrush(QBrush(QColor(0, 0, 0, 150)))
        painter.setPen(Qt.NoPen)
        painter.drawRect(0, 0, 400, info_rect_height)
        
        # Інформація про систему
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        font = QFont("Arial", 12, QFont.Bold)
        painter.setFont(font)
        
        y_offset = 25
        painter.drawText(10, y_offset, "👁️ Gaze Tracking Demo")
        
        y_offset += 25
        painter.drawText(10, y_offset, f"FPS: {int(self.fps)}")
        
        y_offset += 25
        blink_text = "👁️ Моргання" if self.blink_detected else "👁️ Відстеження"
        blink_color = QColor(255, 100, 100) if self.blink_detected else QColor(100, 255, 100)
        painter.setPen(QPen(blink_color, 2))
        painter.drawText(10, y_offset, blink_text)
        
        y_offset += 25
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        if self.filtered_x is not None:
            painter.drawText(10, y_offset, f"Gaze: ({self.filtered_x}, {self.filtered_y})")
        
        # Малюємо debug контури (якщо є)
        if self.contours and self.cursor_alpha > 0:
            painter.setPen(QPen(QColor(15, 182, 242, int(200 * self.cursor_alpha)), 5))
            painter.setBrush(Qt.NoBrush)
            for contour in self.contours:
                # Конвертуємо контур в QPolygon для малювання
                if len(contour) > 2:
                    points = [QPoint(int(pt[0][0]), int(pt[0][1])) for pt in contour]
                    from PyQt5.QtGui import QPolygon
                    polygon = QPolygon(points)
                    painter.drawPolygon(polygon)
        
        # Малюємо gaze cursor (якщо є та alpha > 0)
        if (self.filtered_x is not None and self.filtered_y is not None and 
            self.cursor_alpha > 0):
            
            # Raw gaze (помаранчева точка) - менша та напівпрозора
            if self.gaze_x is not None and self.gaze_y is not None:
                painter.setBrush(QBrush(QColor(255, 165, 0, int(150 * self.cursor_alpha))))
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(QPoint(self.gaze_x, self.gaze_y), 6, 6)
            
            # Filtered gaze cursor - основний курсор
            # Зовнішнє кільце
            outer_alpha = int(200 * self.cursor_alpha)
            painter.setBrush(QBrush(QColor(0, 150, 255, outer_alpha)))
            painter.setPen(QPen(QColor(255, 255, 255, outer_alpha), 2))
            painter.drawEllipse(QPoint(self.filtered_x, self.filtered_y), 30, 30)
            
            # Внутрішнє кільце
            inner_alpha = int(150 * self.cursor_alpha)
            painter.setBrush(QBrush(QColor(255, 255, 255, inner_alpha)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPoint(self.filtered_x, self.filtered_y), 25, 25)
            
            # Центральна точка
            center_alpha = int(255 * self.cursor_alpha)
            painter.setBrush(QBrush(QColor(0, 150, 255, center_alpha)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPoint(self.filtered_x, self.filtered_y), 3, 3)
        
        # Інструкції внизу екрану
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        font_large = QFont("Arial", 16, QFont.Bold)
        painter.setFont(font_large)
        
        instruction = "Дивіться на екран - синій курсор слідкує за вашим поглядом"
        text_width = painter.fontMetrics().width(instruction)
        painter.drawText((self.screen_width - text_width) // 2, self.screen_height - 50, instruction)
        
        # ESC для виходу
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        font_small = QFont("Arial", 10)
        painter.setFont(font_small)
        painter.drawText(self.screen_width - 150, self.screen_height - 20, "ESC - вихід")
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
    
    def closeEvent(self, event):
        self.timer.stop()
        if hasattr(self, 'cap'):
            self.cap.release()
        print("👋 Gaze tracking demo завершено!")
        event.accept()


def run_demo():
    """Запускає gaze tracking demo"""
    app = QApplication(sys.argv)
    demo = GazeDemo()
    return app.exec_()


if __name__ == "__main__":
    run_demo()