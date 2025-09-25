import cv2
import numpy as np
import mediapipe as mp
import math
from collections import deque
import time

from src.constants import LEFT_EYE_INDICES, RIGHT_EYE_INDICES, MUTUAL_INDICES
from src.gaze import GazeEstimator


class FaceLandmarksVisualizer:
    def __init__(self):
        self.face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
        )
        
        self.gaze_estimator = GazeEstimator()
        
        # Кольори для різних груп точок
        self.colors = {
            'left_eye': (0, 255, 0),        # Зелений - ліве око
            'right_eye': (255, 0, 0),       # Синій - праве око
            'mutual': (0, 0, 255),          # Червоний - опорні точки
            'nose_anchor': (255, 255, 0),   # Жовтий - носовий анкер
            'eye_corners': (255, 0, 255),   # Магента - кути очей
            'text': (255, 255, 255),        # Білий - текст
            'ratios': (0, 255, 255),        # Циан - співвідношення
            'angles': (128, 0, 128),        # Фіолетовий - кути
        }
        
        # Історія для згладжування
        self.ear_history = deque(maxlen=30)
        self.angle_history = deque(maxlen=10)
        
    def draw_landmarks_group(self, image, landmarks, indices, color, radius=2):
        """Малює групу landmarks певним кольором"""
        for idx in indices:
            if 0 <= idx < len(landmarks):
                x = int(landmarks[idx].x * image.shape[1])
                y = int(landmarks[idx].y * image.shape[0])
                cv2.circle(image, (x, y), radius, color, -1)
    
    def draw_connections(self, image, landmarks, connections, color, thickness=1):
        """Малює з'єднання між точками"""
        for connection in connections:
            start_idx, end_idx = connection
            if 0 <= start_idx < len(landmarks) and 0 <= end_idx < len(landmarks):
                start_point = (
                    int(landmarks[start_idx].x * image.shape[1]),
                    int(landmarks[start_idx].y * image.shape[0])
                )
                end_point = (
                    int(landmarks[end_idx].x * image.shape[1]),
                    int(landmarks[end_idx].y * image.shape[0])
                )
                cv2.line(image, start_point, end_point, color, thickness)
    
    def calculate_distance(self, landmark1, landmark2, image_shape):
        """Обчислює відстань між двома landmarks"""
        x1, y1 = landmark1.x * image_shape[1], landmark1.y * image_shape[0]
        x2, y2 = landmark2.x * image_shape[1], landmark2.y * image_shape[0]
        return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
    
    def draw_eye_box(self, image, landmarks, eye_indices, color):
        """Малює рамку навколо ока"""
        if not eye_indices:
            return
            
        # Знаходимо границі ока
        x_coords = [landmarks[idx].x * image.shape[1] for idx in eye_indices if 0 <= idx < len(landmarks)]
        y_coords = [landmarks[idx].y * image.shape[0] for idx in eye_indices if 0 <= idx < len(landmarks)]
        
        if x_coords and y_coords:
            min_x, max_x = int(min(x_coords)), int(max(x_coords))
            min_y, max_y = int(min(y_coords)), int(max(y_coords))
            cv2.rectangle(image, (min_x-5, min_y-5), (max_x+5, max_y+5), color, 2)
    
    def draw_text_info(self, image, text_lines, start_y=30):
        """Малює інформаційний текст"""
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        thickness = 2
        
        for i, (text, color) in enumerate(text_lines):
            y_pos = start_y + i * 25
            # Чорна обводка для кращого читання
            cv2.putText(image, text, (15, y_pos), font, font_scale, (0, 0, 0), thickness + 2)
            cv2.putText(image, text, (15, y_pos), font, font_scale, color, thickness)
    
    def process_frame(self, image):
        """Обробляє кадр та додає всю візуалізацію"""
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(image_rgb)
        
        if not results.multi_face_landmarks:
            cv2.putText(image, "No face detected", (50, 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            return image
        
        face_landmarks = results.multi_face_landmarks[0]
        landmarks = face_landmarks.landmark
        
        # Обчислюємо та відображаємо метрики
        try:
            # Отримуємо features від gaze estimator
            features, blink_detected = self.gaze_estimator.extract_features(image)
            
            if features is not None:
                # Розпаковуємо останні 6 елементів (пропорції)
                left_eye_ratio = features[-6]
                right_eye_ratio = features[-5]
                left_eye_to_jaw_ratio = features[-4]
                right_eye_to_jaw_ratio = features[-3]
                face_symmetry = features[-2]
                vertical_proportion = features[-1]
                
                # Кути орієнтації (3 елементи перед пропорціями)
                yaw = features[-9]
                pitch = features[-8]
                roll = features[-7]
                
                # Обчислюємо EAR вручну для візуалізації
                left_eye_width = self.calculate_distance(landmarks[33], landmarks[133], image.shape)
                left_eye_height = self.calculate_distance(landmarks[159], landmarks[145], image.shape)
                right_eye_width = self.calculate_distance(landmarks[263], landmarks[362], image.shape)
                right_eye_height = self.calculate_distance(landmarks[386], landmarks[374], image.shape)
                
                left_ear = left_eye_height / (left_eye_width + 1e-9)
                right_ear = right_eye_height / (right_eye_width + 1e-9)
                avg_ear = (left_ear + right_ear) / 2
                
                self.ear_history.append(avg_ear)
                avg_ear_smooth = np.mean(self.ear_history) if self.ear_history else avg_ear
                
                # Зберігаємо кути для згладжування
                self.angle_history.append([yaw, pitch, roll])
                if len(self.angle_history) > 1:
                    avg_angles = np.mean(self.angle_history, axis=0)
                    yaw_smooth, pitch_smooth, roll_smooth = avg_angles
                else:
                    yaw_smooth, pitch_smooth, roll_smooth = yaw, pitch, roll
                
                # Обчислюємо реальні відстані для візуалізації
                left_eye_outer_point = (int(landmarks[33].x * image.shape[1]), int(landmarks[33].y * image.shape[0]))
                right_eye_outer_point = (int(landmarks[263].x * image.shape[1]), int(landmarks[263].y * image.shape[0]))
                left_jaw_point = (int(landmarks[58].x * image.shape[1]), int(landmarks[58].y * image.shape[0]))
                right_jaw_point = (int(landmarks[288].x * image.shape[1]), int(landmarks[288].y * image.shape[0]))
                
                # Міжочна відстань для нормалізації
                inter_eye_distance = self.calculate_distance(landmarks[33], landmarks[263], image.shape)
                left_eye_to_jaw_px = self.calculate_distance(landmarks[33], landmarks[58], image.shape)
                right_eye_to_jaw_px = self.calculate_distance(landmarks[263], landmarks[288], image.shape)
                
                # Малюємо лінії для візуалізації співвідношень
                # Лінії для EAR (ширина та висота очей)
                # Ліве око
                left_outer = (int(landmarks[33].x * image.shape[1]), int(landmarks[33].y * image.shape[0]))
                left_inner = (int(landmarks[133].x * image.shape[1]), int(landmarks[133].y * image.shape[0]))
                left_top = (int(landmarks[159].x * image.shape[1]), int(landmarks[159].y * image.shape[0]))
                left_bottom = (int(landmarks[145].x * image.shape[1]), int(landmarks[145].y * image.shape[0]))
                
                cv2.line(image, left_outer, left_inner, self.colors['ratios'], 3)  # Ширина
                cv2.line(image, left_top, left_bottom, self.colors['ratios'], 3)   # Висота
                
                # Праве око
                right_outer = (int(landmarks[263].x * image.shape[1]), int(landmarks[263].y * image.shape[0]))
                right_inner = (int(landmarks[362].x * image.shape[1]), int(landmarks[362].y * image.shape[0]))
                right_top = (int(landmarks[386].x * image.shape[1]), int(landmarks[386].y * image.shape[0]))
                right_bottom = (int(landmarks[374].x * image.shape[1]), int(landmarks[374].y * image.shape[0]))
                
                cv2.line(image, right_outer, right_inner, self.colors['ratios'], 3)  # Ширина
                cv2.line(image, right_top, right_bottom, self.colors['ratios'], 3)   # Висота
                
                # Лінії Око -> Щелепа для візуалізації відстаней
                cv2.line(image, left_eye_outer_point, left_jaw_point, (0, 128, 255), 4)   # Ліве око -> ліва щелепа
                cv2.line(image, right_eye_outer_point, right_jaw_point, (0, 128, 255), 4) # Праве око -> права щелепа
                
                # Лінія між кутами очей (inter-eye distance) - БАЗОВА одиниця нормалізації
                cv2.line(image, left_outer, right_outer, (255, 192, 203), 4)
                
                # Лінія від носа до підборіддя (вертикальна пропорція: ніс→підборіддя / міжочна_відстань)
                nose_point = (int(landmarks[4].x * image.shape[1]), int(landmarks[4].y * image.shape[0]))
                chin_point = (int(landmarks[152].x * image.shape[1]), int(landmarks[152].y * image.shape[0]))
                cv2.line(image, nose_point, chin_point, self.colors['mutual'], 3)
                
        except Exception as e:
            cv2.putText(image, f"Error: {str(e)[:50]}", (50, image.shape[0] - 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        return image
    
    def run(self):
        """Запускає візуалізатор"""
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("❌ Не можу відкрити камеру")
            return
        
        print("🎯 Face Ratios Visualizer")
        print("=" * 50)
        print("🔗 Циан лінії: EAR вимірювання (ширина/висота очей)")
        print("🔗 Помаранчеві лінії: Відстані Око->Щелепа")
        print("🔗 Рожева лінія: Міжочна відстань")
        print("🔗 Червона лінія: Ніс->Підборіддя (вертикальна пропорція)")
        print("📊 Ліва панель: EAR та кути голови")
        print("📊 Права панель: Пропорції обличчя та якість")
        print("=" * 50)
        print("Натисніть 'q' для виходу")
        
        fps_counter = 0
        fps_start_time = time.time()
        
        while True:
            ret, frame = cap.read()
            if not ret:
                print("❌ Не можу отримати кадр")
                break
            
            # Відзеркалюємо кадр для зручності
            frame = cv2.flip(frame, 1)
            
            # Обробляємо кадр
            processed_frame = self.process_frame(frame)
            
            # Лічимо FPS
            fps_counter += 1
            if fps_counter % 30 == 0:
                fps = 30 / (time.time() - fps_start_time)
                fps_start_time = time.time()
                cv2.putText(processed_frame, f"FPS: {fps:.1f}", 
                           (processed_frame.shape[1] - 150, processed_frame.shape[0] - 20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Показуємо результат
            cv2.imshow('Face Landmarks Visualizer', processed_frame)
            
            # Перевіряємо натискання клавіш
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord(' '):  # Пауза на пробіл
                cv2.waitKey(0)
        
        cap.release()
        cv2.destroyAllWindows()


def main():
    """Головна функція"""
    visualizer = FaceLandmarksVisualizer()
    visualizer.run()


if __name__ == "__main__":
    main() 