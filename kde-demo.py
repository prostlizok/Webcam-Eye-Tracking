import sys
import time
import math
import cv2
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont

from src.calibration import run_9_point_calibration
from src.filters import KDESmoother
from src.gaze import GazeEstimator
from src.utils.screen import get_screen_size


class KDEGazeDemo(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Set up transparent overlay window
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Get screen dimensions
        self.screen_width, self.screen_height = get_screen_size()
        self.setGeometry(0, 0, self.screen_width, self.screen_height)
        
        # Initialize gaze estimator
        print("🚀 Ініціалізація системи з KDE фільтром...")
        self.gaze_estimator = GazeEstimator(model_name="ridge")
        
        # Run calibration
        print("🎯 Запуск калібрування...")
        run_9_point_calibration(self.gaze_estimator, camera_index=0)
        
        # Initialize KDE filter
        print("🔧 Ініціалізація KDE фільтра...")
        self.smoother = KDESmoother(
            self.screen_width, 
            self.screen_height,
            time_window=0.5,      # Вікно часу для згладжування
            confidence=0.7,       # Рівень довіри
            grid=(160, 100)       # Сітка для KDE
        )
        
        # Set up camera
        self.cap = cv2.VideoCapture(0)
        
        # Gaze tracking
        self.gaze_x = self.gaze_y = None
        self.filtered_x = self.filtered_y = None
        self.blink_detected = False
        
        # Cursor animation
        self.cursor_alpha = 0.0
        self.cursor_step = 0.05
        
        # Display
        self.fps = 0
        self.prev_time = time.time()
        
        # Set up timer for frame processing
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(16)  # ~60 fps
        
        print("🎬 KDE Gaze tracking demo розпочато!")
        print("👁️ Дивіться на екран, курсор буде слідкувати за вашим поглядом")
        print("📊 KDE фільтр використовує статистичне згладжування")
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
                
                # Increase cursor alpha (fade in)
                self.cursor_alpha = min(self.cursor_alpha + self.cursor_step, 1.0)
                
                # Debug output
                print(f"Gaze: ({self.filtered_x:4d}, {self.filtered_y:4d}) | FPS: {int(self.fps):3d} | Blink: {self.blink_detected}")
            else:
                self.gaze_x = self.gaze_y = None
                self.filtered_x = self.filtered_y = None
                
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
        
        # Фон для інформації (темний напівпрозорий з фіолетовим відтінком для KDE)
        info_rect_height = 140
        painter.setBrush(QBrush(QColor(50, 0, 50, 150)))  # Темно-фіолетовий
        painter.setPen(Qt.NoPen)
        painter.drawRect(0, 0, 450, info_rect_height)
        
        # Інформація про систему
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        font = QFont("Arial", 12, QFont.Bold)
        painter.setFont(font)
        
        y_offset = 25
        painter.drawText(10, y_offset, "📊 KDE Gaze Tracking Demo")
        
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
        
        y_offset += 25
        painter.setPen(QPen(QColor(200, 150, 255), 2))  # Світло-фіолетовий
        painter.drawText(10, y_offset, "Фільтр: KDE (статистичний)")
        
        # Візуалізація KDE області (якщо є дані в debug)
        if hasattr(self.smoother, 'debug') and 'mask' in self.smoother.debug:
            mask = self.smoother.debug['mask']
            contours = self.smoother.debug.get('contours', [])
            
            # Конвертуємо маску в QImage для відображення
            if mask is not None and mask.shape[0] > 0 and mask.shape[1] > 0:
                # Створюємо напівпрозору область KDE
                kde_alpha = int(80 * self.cursor_alpha)  # Напівпрозора
                
                # Малюємо контури KDE області
                for contour in contours:
                    if len(contour) > 2:
                        # Конвертуємо контур в QPolygon
                        points = []
                        for point in contour:
                            x, y = point[0]
                            points.append(QPoint(int(x), int(y)))
                        
                        if len(points) > 2:
                            # Малюємо заповнену область
                            painter.setBrush(QBrush(QColor(150, 50, 255, kde_alpha)))  # Фіолетова область
                            painter.setPen(QPen(QColor(200, 100, 255, kde_alpha + 50), 2))  # Контур
                            painter.drawPolygon(points)
        
        # Малюємо gaze cursor (якщо є та alpha > 0)
        if (self.filtered_x is not None and self.filtered_y is not None and 
            self.cursor_alpha > 0):
            
            # Raw gaze (помаранчева точка) - менша та напівпрозора
            if self.gaze_x is not None and self.gaze_y is not None:
                painter.setBrush(QBrush(QColor(255, 165, 0, int(150 * self.cursor_alpha))))
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(QPoint(self.gaze_x, self.gaze_y), 6, 6)
            
            # KDE filtered gaze cursor - фіолетовий курсор для KDE
            # Зовнішнє кільце
            outer_alpha = int(200 * self.cursor_alpha)
            painter.setBrush(QBrush(QColor(150, 50, 255, outer_alpha)))  # Фіолетовий
            painter.setPen(QPen(QColor(255, 255, 255, outer_alpha), 2))
            painter.drawEllipse(QPoint(self.filtered_x, self.filtered_y), 35, 35)
            
            # Середнє кільце (додаткове для KDE)
            middle_alpha = int(180 * self.cursor_alpha)
            painter.setBrush(QBrush(QColor(200, 100, 255, middle_alpha)))  # Світліший фіолетовий
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPoint(self.filtered_x, self.filtered_y), 28, 28)
            
            # Внутрішнє кільце
            inner_alpha = int(150 * self.cursor_alpha)
            painter.setBrush(QBrush(QColor(255, 255, 255, inner_alpha)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPoint(self.filtered_x, self.filtered_y), 22, 22)
            
            # Центральна точка
            center_alpha = int(255 * self.cursor_alpha)
            painter.setBrush(QBrush(QColor(150, 50, 255, center_alpha)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPoint(self.filtered_x, self.filtered_y), 4, 4)
            
            # Додаткові точки навколо для візуалізації статистичного характеру KDE
            if self.cursor_alpha > 0.5:
                for i in range(8):
                    angle = i * math.pi / 4
                    offset_x = int(15 * math.cos(angle + time.time() * 2))
                    offset_y = int(15 * math.sin(angle + time.time() * 2))
                    dot_alpha = int(100 * self.cursor_alpha * (0.5 + 0.5 * math.sin(time.time() * 3 + i)))
                    
                    painter.setBrush(QBrush(QColor(200, 150, 255, dot_alpha)))
                    painter.setPen(Qt.NoPen)
                    painter.drawEllipse(
                        QPoint(self.filtered_x + offset_x, self.filtered_y + offset_y), 
                        2, 2
                    )
        
        # Інструкції внизу екрану
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        font_large = QFont("Arial", 16, QFont.Bold)
        painter.setFont(font_large)
        
        instruction = "Дивіться на екран - фіолетовий курсор з KDE фільтром слідкує за поглядом"
        text_width = painter.fontMetrics().width(instruction)
        painter.drawText((self.screen_width - text_width) // 2, self.screen_height - 50, instruction)
        
        # Додаткова інформація про KDE
        painter.setPen(QPen(QColor(200, 150, 255), 1))
        font_medium = QFont("Arial", 12)
        painter.setFont(font_medium)
        
        kde_info = "KDE: Kernel Density Estimation - статистичне згладжування з адаптивністю"
        info_width = painter.fontMetrics().width(kde_info)
        painter.drawText((self.screen_width - info_width) // 2, self.screen_height - 25, kde_info)
        
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
        print("👋 KDE Gaze tracking demo завершено!")
        event.accept()


def run_kde_demo():
    """Запускає KDE gaze tracking demo"""
    app = QApplication(sys.argv)
    demo = KDEGazeDemo()
    return app.exec_()


if __name__ == "__main__":
    run_kde_demo() 