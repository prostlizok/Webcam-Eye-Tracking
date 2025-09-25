import sys
import time
import math
import cv2
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont

from src.calibration import run_9_point_calibration
from src.filters import KalmanSmoother, make_kalman
from src.gaze import GazeEstimator
from src.utils.screen import get_screen_size


class TrajectoryTest(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        
        self.screen_width, self.screen_height = get_screen_size()
        self.setGeometry(0, 0, self.screen_width, self.screen_height)
        
        print("Ініціалізація системи...")
        self.gaze_estimator = GazeEstimator(model_name="ridge")
        
        print("Запуск калібрування...")
        run_9_point_calibration(self.gaze_estimator, camera_index=0)
        
        print("🔧 Ініціалізація Kalman фільтра...")
        kalman = make_kalman(
            process_var=8.0,
            measurement_var=2.0
        )
        self.smoother = KalmanSmoother(kalman)
        self.smoother.tune(self.gaze_estimator, camera_index=0)
        
        self.cap = cv2.VideoCapture(0)
        
        self.test_phase = "bounce" 
        self.bounce_time = 3.0  
        self.trajectory_duration = 20.0 
        
        self.start_time = time.time()
        self.phase_start_time = time.time()
        
        self.target_x = self.screen_width // 2
        self.target_y = self.screen_height // 2
        self.bounce_amplitude = 50  
        
        self.trajectory_points = self._generate_trajectory()
        self.trajectory_index = 0
        
        self.gaze_x = self.gaze_y = None
        self.filtered_x = self.filtered_y = None
        self.blink_detected = False
        
        self.trajectory_data = []
        
        self.fps = 0
        self.prev_time = time.time()
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(16)  
        
        print("Тест розпочато з Kalman фільтром (білий фон)!")
        print("Фаза 1: Попригування точки (3 сек)")
        self.show()
    
    def _generate_trajectory(self):
        points = []
        
        center_x = self.screen_width // 2
        center_y = self.screen_height // 2
        
        a = min(self.screen_width, self.screen_height) // 1.5
        b = a // 1 
        
        num_points = 400  
        
        for i in range(num_points):
            t = 2 * math.pi * i / (num_points - 1)
            
            sin_t = math.sin(t)
            cos_t = math.cos(t)
            denominator = 1 + sin_t * sin_t
            
            x = center_x + (a * cos_t) / denominator
            y = center_y + (b * sin_t * cos_t) / denominator
            
            points.append((int(x), int(y)))
        
        return points
    
    def update_frame(self):
        current_time = time.time()
        elapsed = current_time - self.phase_start_time
        
        if self.test_phase == "bounce":
            self._update_bounce_phase(elapsed)
        elif self.test_phase == "trajectory":
            self._update_trajectory_phase(elapsed)
        elif self.test_phase == "finished":
            self._finish_test()
            return
        
        ret, frame = self.cap.read()
        if ret:
            features, self.blink_detected = self.gaze_estimator.extract_features(frame)
            
            if features is not None and not self.blink_detected:
                gaze_point = self.gaze_estimator.predict(np.array([features]))[0]
                self.gaze_x, self.gaze_y = map(int, gaze_point)
                self.filtered_x, self.filtered_y = self.smoother.step(self.gaze_x, self.gaze_y)
            else:
                self.gaze_x = self.gaze_y = None
                self.filtered_x = self.filtered_y = None
        
        if self.test_phase == "trajectory" and self.gaze_x is not None:
            self.trajectory_data.append((
                current_time - self.start_time,
                self.target_x, self.target_y,
                self.gaze_x, self.gaze_y,
                self.filtered_x, self.filtered_y
            ))
        
        self.fps = 1 / (current_time - self.prev_time) if current_time - self.prev_time > 0 else 0
        self.prev_time = current_time
        
        self.update()
    
    def _update_bounce_phase(self, elapsed):
        if elapsed >= self.bounce_time:
            self.test_phase = "trajectory"
            self.phase_start_time = time.time()
            self.trajectory_index = 0
            print("📍 Фаза 2: Траєкторія ∞ з Kalman фільтром (20 сек)")
            return
        
        bounce_freq = 3.0  # Hz
        angle = 2 * math.pi * bounce_freq * elapsed
        offset_x = self.bounce_amplitude * math.cos(angle)
        offset_y = self.bounce_amplitude * math.sin(angle * 1.3) 
        
        self.target_x = int(self.screen_width // 2 + offset_x)
        self.target_y = int(self.screen_height // 2 + offset_y)
    
    def _update_trajectory_phase(self, elapsed):
        if elapsed >= self.trajectory_duration:
            self.test_phase = "finished"
            return
        
        progress = elapsed / self.trajectory_duration
        target_index = int(progress * (len(self.trajectory_points) - 1))
        target_index = min(target_index, len(self.trajectory_points) - 1)
        
        if target_index < len(self.trajectory_points):
            self.target_x, self.target_y = self.trajectory_points[target_index]
    
    def _finish_test(self):
        print("Тест завершено!")
        print(f"Зібрано {len(self.trajectory_data)} точок даних")
        
        if self.trajectory_data:
            self._save_results()
        
        self.timer.stop()
        self.cap.release()
        self.close()
    
    def _save_results(self):
        import csv
        filename = f"trajectory_test_{int(time.time())}.csv"
        
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['time', 'target_x', 'target_y', 'gaze_x', 'gaze_y', 'filtered_x', 'filtered_y'])
            writer.writerows(self.trajectory_data)
        
        print(f"Результати збережено в {filename}")
        
        if len(self.trajectory_data) > 10:
            errors_raw = []
            errors_filtered = []
            
            for data in self.trajectory_data:
                _, tx, ty, gx, gy, fx, fy = data
                if gx is not None and fx is not None:
                    error_raw = math.sqrt((tx - gx)**2 + (ty - gy)**2)
                    error_filtered = math.sqrt((tx - fx)**2 + (ty - fy)**2)
                    errors_raw.append(error_raw)
                    errors_filtered.append(error_filtered)
            
            if errors_raw and errors_filtered:
                avg_error_raw = np.mean(errors_raw)
                avg_error_filtered = np.mean(errors_filtered)
                
                var_raw = np.var(errors_raw)
                var_filtered = np.var(errors_filtered)
                smoothing_effect = ((var_raw - var_filtered) / var_raw) * 100 if var_raw > 0 else 0
                
                print(f"Середня помилка (raw): {avg_error_raw:.1f}px")
                print(f"Середня помилка (Kalman): {avg_error_filtered:.1f}px")
                print(f"Згладжування: {smoothing_effect:.1f}%")
                print(f"Для детального аналізу запустіть: python trajectory_analysis.py {filename}")
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        painter.fillRect(self.rect(), QColor(255, 255, 255))
        
        info_rect_height = 120
        painter.setBrush(QBrush(QColor(255, 248, 231, 200))) 
        painter.setPen(Qt.NoPen)
        painter.drawRect(0, 0, 400, info_rect_height)
        
        painter.setPen(QPen(QColor(44, 62, 80), 2)) 
        font = QFont("Arial", 12, QFont.Bold)
        painter.setFont(font)
        
        y_offset = 25
        if self.test_phase == "bounce":
            remaining = self.bounce_time - (time.time() - self.phase_start_time)
            painter.drawText(10, y_offset, f"🔄 Попригування: {remaining:.1f}s")
        elif self.test_phase == "trajectory":
            remaining = self.trajectory_duration - (time.time() - self.phase_start_time)
            progress = ((time.time() - self.phase_start_time) / self.trajectory_duration) * 100
            painter.drawText(10, y_offset, f"📍 Траєкторія ∞: {remaining:.1f}s ({progress:.0f}%)")
        
        y_offset += 25
        painter.drawText(10, y_offset, f"FPS: {int(self.fps)}")
        
        y_offset += 25
        blink_text = "Моргання" if self.blink_detected else "Відстеження"
        blink_color = QColor(255, 107, 107) if self.blink_detected else QColor(78, 205, 196)  
        painter.setPen(QPen(blink_color, 2))
        painter.drawText(10, y_offset, blink_text)
        
        y_offset += 25
        painter.setPen(QPen(QColor(44, 62, 80), 2))
        if self.filtered_x is not None:
            painter.drawText(10, y_offset, f"Gaze: ({self.filtered_x}, {self.filtered_y})")
        
        if self.test_phase in ["bounce", "trajectory"]:
            if self.test_phase == "bounce":
                pulse = 0.8 + 0.2 * math.sin(time.time() * 8)
                outer_radius = int(25 * pulse)
                painter.setBrush(QBrush(QColor(255, 179, 71, 150)))  
            else:
                outer_radius = 20
                painter.setBrush(QBrush(QColor(255, 107, 107, 150)))  
            
            painter.setPen(QPen(QColor(44, 62, 80), 3))  
            painter.drawEllipse(QPoint(self.target_x, self.target_y), outer_radius, outer_radius)
            
            painter.setBrush(QBrush(QColor(44, 62, 80)))  
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPoint(self.target_x, self.target_y), 8, 8)
        
        if self.filtered_x is not None and self.filtered_y is not None:
            if self.gaze_x is not None and self.gaze_y is not None:
                painter.setBrush(QBrush(QColor(255, 179, 71, 180)))
                painter.setPen(QPen(QColor(255, 255, 255), 1))  
                painter.drawEllipse(QPoint(self.gaze_x, self.gaze_y), 6, 6)
            
            painter.setBrush(QBrush(QColor(78, 205, 196, 220)))
            painter.setPen(QPen(QColor(255, 255, 255), 2))  
            painter.drawEllipse(QPoint(self.filtered_x, self.filtered_y), 12, 12)
            
            painter.setBrush(QBrush(QColor(44, 62, 80))) 
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPoint(self.filtered_x, self.filtered_y), 3, 3)
        
        if self.test_phase == "bounce":
            instruction = "Дивіться на помаранчеву точку що попригує"
        elif self.test_phase == "trajectory":
            instruction = "Слідкуйте очима за рожевою точкою ∞"
        else:
            instruction = "Тест завершено"
        
        painter.setPen(QPen(QColor(44, 62, 80), 2))  
        font_large = QFont("Arial", 16, QFont.Bold)
        painter.setFont(font_large)
        text_width = painter.fontMetrics().width(instruction)
        painter.drawText((self.screen_width - text_width) // 2, self.screen_height - 50, instruction)
        
        painter.setPen(QPen(QColor(120, 120, 120), 1))
        font_small = QFont("Arial", 10)
        painter.setFont(font_small)
        painter.drawText(self.screen_width - 150, self.screen_height - 20, "ESC - вихід")
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.test_phase = "finished"
            self._finish_test()
    
    def closeEvent(self, event):
        self.timer.stop()
        if hasattr(self, 'cap'):
            self.cap.release()
        event.accept()


def run_trajectory_test():
    app = QApplication(sys.argv)
    test = TrajectoryTest()
    return app.exec_()


if __name__ == "__main__":
    run_trajectory_test() 