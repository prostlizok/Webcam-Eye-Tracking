import sys
import subprocess
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QLabel, QComboBox, QGroupBox,
                             QGridLayout, QFrame, QTextEdit, QProgressBar, QMessageBox, QSlider)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QPoint
from PyQt5.QtGui import QFont, QPalette, QColor, QPainter, QBrush, QPen, QPixmap

from src.utils.screen import get_screen_size


class PreviewWidget(QWidget):
    """Віджет для попереднього перегляду калібрування та фільтрів"""
    
    def __init__(self):
        super().__init__()
        self.calibration_points = 9
        self.filter_type = "kalman"
        self.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #FFFFFF, stop:1 #F8F9FA);
            border: 1px solid rgba(0, 0, 0, 0.1);
            border-radius: 15px;
        """)
        
    def set_calibration_points(self, points):
        self.calibration_points = points
        self.update()
        
    def set_filter_type(self, filter_type):
        self.filter_type = filter_type
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Чистий білий фон як у macOS
        painter.fillRect(self.rect(), QColor(255, 255, 255))
        
        # Малюємо точки калібрування
        self._draw_calibration_points(painter)
        
        # Малюємо приклад фільтрації
        self._draw_filter_example(painter)
        
    def _draw_calibration_points(self, painter):
        """Малює точки калібрування як на реальному екрані"""
        # Отримуємо розміри віджета
        w, h = self.width(), self.height()
        
        # Відступи від країв (як на реальному екрані)
        margin_x = w * 0.1  # 10% від ширини
        margin_y = h * 0.1  # 10% від висоти
        
        # Робоча область екрану
        work_w = w - 2 * margin_x
        work_h = h - 2 * margin_y
        
        if self.calibration_points == 5:
            # 5-точкове калібрування (кути + центр)
            points = [
                (w//2, h//2),                           # Центр
                (margin_x, margin_y),                   # Верх-ліво
                (w - margin_x, margin_y),               # Верх-право
                (margin_x, h - margin_y),               # Низ-ліво
                (w - margin_x, h - margin_y)            # Низ-право
            ]
        else:  # 9 точок
            # 9-точкове калібрування (сітка 3x3)
            points = [
                (w//2, h//2),                           # Центр
                (margin_x, margin_y),                   # Верх-ліво
                (w - margin_x, margin_y),               # Верх-право
                (margin_x, h - margin_y),               # Низ-ліво
                (w - margin_x, h - margin_y),           # Низ-право
                (w//2, margin_y),                       # Верх-центр
                (margin_x, h//2),                       # Ліво-центр
                (w - margin_x, h//2),                   # Право-центр
                (w//2, h - margin_y)                    # Низ-центр
            ]
        
        # Малюємо точки калібрування
        for i, (x, y) in enumerate(points):
            # Помаранчева точка замість сірої
            painter.setBrush(QBrush(QColor(255, 165, 0, 220)))  # Помаранчевий
            painter.setPen(QPen(QColor(200, 120, 0), 3))
            painter.drawEllipse(int(x-20), int(y-20), 40, 40)
            
            # Середнє кільце (світло-помаранчеве)
            painter.setBrush(QBrush(QColor(255, 200, 100, 180)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(int(x-15), int(y-15), 30, 30)
            
            # Внутрішнє кільце (біле)
            painter.setBrush(QBrush(QColor(255, 255, 255, 200)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(int(x-10), int(y-10), 20, 20)
            
            # Центральна точка (темно-помаранчева)
            painter.setBrush(QBrush(QColor(200, 100, 0)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(int(x-4), int(y-4), 8, 8)
            
            # Номер точки (опціонально для демонстрації)
            if i == 0:  # Центральна точка
                painter.setPen(QPen(QColor(200, 100, 0), 2))
                font = QFont("Arial", 10, QFont.Bold)
                painter.setFont(font)
                painter.drawText(int(x-25), int(y-25), "START")
    
    def _draw_filter_example(self, painter):
        """Малює приклад роботи фільтра як на реальному екрані"""
        import math
        import time
        
        # Симуляція траєкторії погляду в центральній області екрану
        w, h = self.width(), self.height()
        center_x, center_y = w // 2, h // 2
        t = time.time()
        
        # Обмежуємо рух курсора в центральній області
        movement_radius_x = w * 0.15  # 15% від ширини
        movement_radius_y = h * 0.1   # 10% від висоти
        
        if self.filter_type == "kalman":
            # Kalman - синій курсор з плавним рухом
            smooth_x = center_x + math.cos(t * 1.5) * movement_radius_x
            smooth_y = center_y + math.sin(t * 1.5) * movement_radius_y
            
            # Зовнішнє кільце (синє)
            painter.setBrush(QBrush(QColor(0, 150, 255, 200)))
            painter.setPen(QPen(QColor(50, 50, 50, 200), 3))
            painter.drawEllipse(int(smooth_x-18), int(smooth_y-18), 36, 36)
            
            # Внутрішнє кільце (світло-сіре)
            painter.setBrush(QBrush(QColor(200, 200, 200, 150)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(int(smooth_x-14), int(smooth_y-14), 28, 28)
            
            # Центральна точка (синя)
            painter.setBrush(QBrush(QColor(0, 150, 255, 255)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(int(smooth_x-3), int(smooth_y-3), 6, 6)
            
        elif self.filter_type == "kde":
            # KDE - фіолетові полігональні області довіри
            main_x = center_x + math.cos(t * 1.5) * movement_radius_x
            main_y = center_y + math.sin(t * 1.5) * movement_radius_y
            
            # Полігональні області довіри
            for i in range(3):
                alpha = 40 + i * 20
                
                # Створюємо неправильний полігон навколо точки
                polygon_points = []
                num_points = 8 + i * 2
                
                for j in range(num_points):
                    angle = (j / num_points) * 2 * math.pi
                    radius = 25 + math.sin(t * 2 + i + j) * 10 + math.cos(t * 3 + j) * 6
                    noise_angle = angle + math.sin(t + i + j) * 0.3
                    
                    x = main_x + radius * math.cos(noise_angle)
                    y = main_y + radius * math.sin(noise_angle)
                    polygon_points.append(QPoint(int(x), int(y)))
                
                # Малюємо полігональну область
                painter.setBrush(QBrush(QColor(150, 50, 255, alpha)))
                painter.setPen(QPen(QColor(100, 30, 200, alpha + 30), 2))
                painter.drawPolygon(polygon_points)
            
            # Основний курсор KDE (фіолетовий з кільцями)
            # Зовнішнє кільце
            painter.setBrush(QBrush(QColor(150, 50, 255, 200)))
            painter.setPen(QPen(QColor(50, 50, 50, 200), 3))
            painter.drawEllipse(int(main_x-20), int(main_y-20), 40, 40)
            
            # Середнє кільце
            painter.setBrush(QBrush(QColor(200, 100, 255, 180)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(int(main_x-16), int(main_y-16), 32, 32)
            
            # Внутрішнє кільце
            painter.setBrush(QBrush(QColor(220, 220, 220, 150)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(int(main_x-12), int(main_y-12), 24, 24)
            
            # Центральна точка
            painter.setBrush(QBrush(QColor(150, 50, 255, 255)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(int(main_x-3), int(main_y-3), 6, 6)
            
        else:  # raw - червоний курсор з шумом
            # Raw траєкторія з більшим шумом
            raw_x = center_x + math.cos(t * 1.5) * movement_radius_x + math.sin(t * 12) * 8
            raw_y = center_y + math.sin(t * 1.5) * movement_radius_y + math.cos(t * 10) * 8
            
            # Простий червоний курсор для raw даних
            painter.setBrush(QBrush(QColor(255, 100, 100, 200)))
            painter.setPen(QPen(QColor(50, 50, 50, 200), 3))
            painter.drawEllipse(int(raw_x-12), int(raw_y-12), 24, 24)
            
            painter.setBrush(QBrush(QColor(200, 200, 200, 150)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(int(raw_x-8), int(raw_y-8), 16, 16)
            
            painter.setBrush(QBrush(QColor(255, 100, 100, 255)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(int(raw_x-3), int(raw_y-3), 6, 6)


class LaunchThread(QThread):
    """Потік для запуску програми"""
    finished = pyqtSignal()
    error = pyqtSignal(str)
    
    def __init__(self, script_name):
        super().__init__()
        self.script_name = script_name
        
    def run(self):
        try:
            # Запускаємо скрипт
            result = subprocess.run([sys.executable, self.script_name], 
                                  capture_output=True, text=True, cwd=os.getcwd())
            if result.returncode != 0:
                self.error.emit(f"Помилка запуску: {result.stderr}")
            else:
                self.finished.emit()
        except Exception as e:
            self.error.emit(f"Помилка: {str(e)}")


class GazeTrackerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_thread = None
        self.init_ui()
        
        # Таймер для оновлення попереднього перегляду
        self.preview_timer = QTimer()
        self.preview_timer.timeout.connect(self.update_preview)
        self.preview_timer.start(50)  # 20 FPS
        
    def init_ui(self):
        self.setWindowTitle("Gaze Tracker - Система Відстеження Погляду")
        self.setGeometry(100, 100, 1280, 720)  # 16:9 aspect ratio
        
        # macOS-стиль дизайн
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #f8f9fa, stop:1 #e9ecef);
                color: #212529;
                border-radius: 15px;
            }
            QGroupBox {
                font-weight: 600;
                border: 1px solid rgba(0, 0, 0, 0.1);
                border-radius: 12px;
                margin-top: 1ex;
                padding-top: 15px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 255, 255, 0.9),
                    stop:1 rgba(255, 255, 255, 0.7));
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #495057;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(0, 122, 255, 0.8), stop:1 rgba(0, 86, 204, 0.8));
                border: none;
                color: white;
                padding: 12px 20px;
                text-align: center;
                font-size: 13px;
                border-radius: 8px;
                font-weight: 500;
                min-height: 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(0, 86, 204, 0.9), stop:1 rgba(0, 61, 153, 0.9));
                transform: translateY(-1px);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(0, 61, 153, 1.0), stop:1 rgba(0, 41, 102, 1.0));
                transform: translateY(0px);
            }
            QPushButton:disabled {
                background: rgba(229, 229, 231, 0.6);
                color: rgba(142, 142, 147, 0.8);
            }
            QLabel {
                color: #495057;
                font-size: 12px;
                font-weight: 500;
            }
            QComboBox {
                background: #FFFFFF;
                color: #212529;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 12px;
                min-width: 120px;
                font-weight: 400;
            }
            QComboBox:hover {
                border-color: #007AFF;
                background: #F8F9FA;
            }
            QComboBox:focus {
                border-color: #007AFF;
                outline: none;
            }
            QComboBox::drop-down {
                background: transparent;
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid #6B7280;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background: #FFFFFF;
                color: #212529;
                selection-background-color: #007AFF;
                selection-color: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                outline: none;
            }
            QSlider::groove:horizontal {
                border: none;
                height: 4px;
                background: #E5E5E7;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #FFFFFF;
                border: 1px solid #D1D5DB;
                width: 20px;
                height: 20px;
                margin: -8px 0;
                border-radius: 10px;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }
            QSlider::handle:horizontal:hover {
                background: #F8F9FA;
                border-color: #007AFF;
                box-shadow: 0 2px 8px rgba(0, 122, 255, 0.3);
            }
            QSlider::handle:horizontal:pressed {
                background: #007AFF;
                border-color: #007AFF;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #007AFF, stop:1 #0056CC);
                border-radius: 2px;
            }
            QTextEdit {
                background: #FFFFFF;
                color: #212529;
                border: 1px solid #D1D5DB;
                border-radius: 8px;
                font-family: 'SF Mono', 'Monaco', 'Courier New', monospace;
                font-size: 11px;
                padding: 8px;
            }
            QProgressBar {
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                text-align: center;
                background: #F3F4F6;
                color: #495057;
                font-weight: 500;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #34D399, stop:1 #10B981);
                border-radius: 5px;
            }
        """)
        
        # Центральний віджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Основний layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(10)
        
        # Ліва панель - налаштування (менша)
        settings_panel = self.create_settings_panel()
        main_layout.addWidget(settings_panel, 0)  # Не розтягується
        
        # Права панель - попередній перегляд (більша)
        preview_panel = self.create_preview_panel()
        main_layout.addWidget(preview_panel, 1)  # Розтягується
        
    def create_settings_panel(self):
        """Створює панель налаштувань"""
        settings_group = QGroupBox("Налаштування")
        settings_group.setFixedWidth(280)
        layout = QVBoxLayout(settings_group)
        layout.setSpacing(8)
        
        # Калібрування
        calib_layout = QVBoxLayout()
        calib_layout.addWidget(QLabel("Кількість точок калібрування:"))
        
        # Слайдер для вибору кількості точок калібрування
        self.calibration_slider = QSlider(Qt.Horizontal)
        self.calibration_slider.setMinimum(0)
        self.calibration_slider.setMaximum(1)
        self.calibration_slider.setValue(1)  # 9 точок за замовчуванням
        self.calibration_slider.setTickPosition(QSlider.TicksBelow)
        self.calibration_slider.setTickInterval(1)
        self.calibration_slider.valueChanged.connect(self.on_calibration_changed)
        calib_layout.addWidget(self.calibration_slider)
        
        # Підписи для слайдера калібрування
        calib_labels_widget = QWidget()
        calib_labels_widget.setFixedHeight(20)
        
        # Створюємо підписи з абсолютним позиціонуванням
        points_5_label = QLabel("5", calib_labels_widget)
        points_5_label.setStyleSheet("color: #6B7280; font-size: 10px; font-weight: 500;")
        points_5_label.move(0, 0)
        
        points_9_label = QLabel("9", calib_labels_widget)
        points_9_label.setStyleSheet("color: #6B7280; font-size: 10px; font-weight: 500;")
        
        # Функція для оновлення позицій підписів калібрування
        def update_calib_label_positions():
            if hasattr(self, 'calibration_slider'):
                slider_width = self.calibration_slider.width()
                
                # Для 2-позиційного слайдера використовуємо відступи
                margin = 15  # Відступ від країв
                
                # Позиції для 2 значень (0, 1)
                pos_0 = margin
                pos_1 = slider_width - margin
                
                # Вирівнюємо підписи
                points_5_label.move(pos_0 - points_5_label.width() // 2, 0)
                points_9_label.move(pos_1 - points_9_label.width() // 2, 0)
        
        # Зберігаємо функцію для пізнішого використання
        calib_labels_widget.update_positions = update_calib_label_positions
        self.calib_labels_widget = calib_labels_widget  # Зберігаємо посилання
        
        calib_layout.addWidget(calib_labels_widget)
        layout.addLayout(calib_layout)
        
        # Фільтрація
        filter_layout = QVBoxLayout()
        filter_layout.addWidget(QLabel("Тип фільтрації:"))
        
        # Слайдер для вибору фільтра
        self.filter_slider = QSlider(Qt.Horizontal)
        self.filter_slider.setMinimum(0)
        self.filter_slider.setMaximum(2)
        self.filter_slider.setValue(1)  # Kalman за замовчуванням (тепер позиція 1)
        self.filter_slider.setTickPosition(QSlider.TicksBelow)
        self.filter_slider.setTickInterval(1)
        self.filter_slider.valueChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.filter_slider)
        
        # Підписи для слайдера з точним вирівнюванням
        filter_labels_widget = QWidget()
        filter_labels_widget.setFixedHeight(20)
        
        # Створюємо підписи з абсолютним позиціонуванням
        kde_label = QLabel("KDE", filter_labels_widget)
        kde_label.setStyleSheet("color: #6B7280; font-size: 10px; font-weight: 500;")
        kde_label.move(0, 0)
        
        kalman_label = QLabel("Kalman", filter_labels_widget)
        kalman_label.setStyleSheet("color: #6B7280; font-size: 10px; font-weight: 500;")
        
        raw_label = QLabel("Raw", filter_labels_widget)
        raw_label.setStyleSheet("color: #6B7280; font-size: 10px; font-weight: 500;")
        
        # Функція для оновлення позицій підписів
        def update_label_positions():
            if hasattr(self, 'filter_slider'):
                slider_width = self.filter_slider.width()
                handle_width = 20  # Ширина handle
                
                # Позиції для 3 значень (0, 1, 2)
                pos_0 = handle_width // 2
                pos_1 = slider_width // 2
                pos_2 = slider_width - handle_width // 2
                
                # Центруємо підписи відносно позицій handle
                kde_label.move(pos_0 - kde_label.width() // 2, 0)
                kalman_label.move(pos_1 - kalman_label.width() // 2, 0)
                raw_label.move(pos_2 - raw_label.width() // 2, 0)
        
        # Зберігаємо функцію для пізнішого використання
        filter_labels_widget.update_positions = update_label_positions
        self.filter_labels_widget = filter_labels_widget  # Зберігаємо посилання
        
        filter_layout.addWidget(filter_labels_widget)
        
        layout.addLayout(filter_layout)
        
        # ML модель
        model_layout = QVBoxLayout()
        model_layout.addWidget(QLabel("ML модель:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(["Ridge Regression", "SVR"])
        self.model_combo.setCurrentText("Ridge Regression")
        model_layout.addWidget(self.model_combo)
        layout.addLayout(model_layout)
        
        # Debug режим
        debug_layout = QVBoxLayout()
        debug_layout.addWidget(QLabel("Debug режим:"))
        self.debug_combo = QComboBox()
        self.debug_combo.addItems(["Вимкнено", "Увімкнено"])
        debug_layout.addWidget(self.debug_combo)
        layout.addLayout(debug_layout)
        
        layout.addStretch()
        
        # Кнопки запуску
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(6)
        
        self.main_button = QPushButton("Запустити Основний Трекер")
        self.main_button.clicked.connect(self.launch_main_tracker)
        buttons_layout.addWidget(self.main_button)
        
        self.trajectory_button = QPushButton("Тест Траєкторії")
        self.trajectory_button.clicked.connect(self.launch_trajectory_test)
        buttons_layout.addWidget(self.trajectory_button)
        
        self.benchmark_button = QPushButton("Бенчмарк Моделей")
        self.benchmark_button.clicked.connect(self.launch_benchmark)
        buttons_layout.addWidget(self.benchmark_button)
        
        layout.addLayout(buttons_layout)
        
        return settings_group
        
    def create_preview_panel(self):
        """Створює панель попереднього перегляду"""
        # Віджет попереднього перегляду без рамки
        self.preview_widget = PreviewWidget()
        return self.preview_widget
    
    def showEvent(self, event):
        """Викликається коли вікно показується"""
        super().showEvent(event)
        # Оновлюємо позиції підписів після показу вікна
        QTimer.singleShot(100, self.update_filter_labels)
    
    def update_filter_labels(self):
        """Оновлює позиції підписів слайдерів"""
        if hasattr(self, 'filter_labels_widget'):
            self.filter_labels_widget.update_positions()
        if hasattr(self, 'calib_labels_widget'):
            self.calib_labels_widget.update_positions()
    
    def on_calibration_changed(self):
        """Обробник зміни кількості точок калібрування"""
        value = self.calibration_slider.value()
        points = 5 if value == 0 else 9
        self.preview_widget.set_calibration_points(points)
        
    def on_filter_changed(self):
        """Обробник зміни типу фільтра"""
        value = self.filter_slider.value()
        if value == 0:
            filter_type = "kde"
        elif value == 1:
            filter_type = "kalman"
        else:
            filter_type = "raw"
        self.preview_widget.set_filter_type(filter_type)
    
    def update_preview(self):
        """Оновлює попередній перегляд"""
        self.preview_widget.update()
    
    def launch_main_tracker(self):
        """Запускає основний трекер"""
        filter_value = self.filter_slider.value()
        if filter_value == 0:
            script = "kde-demo.py"
        else:
            script = "main-demo.py"
        self.launch_script(script)
    
    def launch_trajectory_test(self):
        """Запускає тест траєкторії"""
        script = "trajectory-test-white.py"
        self.launch_script(script)
    
    def launch_benchmark(self):
        """Запускає бенчмарк"""
        script = "model_benchmark_test.py"
        self.launch_script(script)
        
    def launch_script(self, script_name):
        """Запускає скрипт в окремому потоці"""
        if self.current_thread and self.current_thread.isRunning():
            QMessageBox.warning(self, "Попередження", "Програма вже запущена!")
            return
            
        if not os.path.exists(script_name):
            QMessageBox.critical(self, "Помилка", f"Файл {script_name} не знайдено!")
            return
            
        # Вимикаємо кнопки
        self.main_button.setEnabled(False)
        self.trajectory_button.setEnabled(False)
        self.benchmark_button.setEnabled(False)
        
        # Запускаємо в потоці
        self.current_thread = LaunchThread(script_name)
        self.current_thread.finished.connect(self.on_launch_finished)
        self.current_thread.error.connect(self.on_launch_error)
        self.current_thread.start()
    
    def on_launch_finished(self):
        """Обробник завершення запуску"""
        self.main_button.setEnabled(True)
        self.trajectory_button.setEnabled(True)
        self.benchmark_button.setEnabled(True)
        
    def on_launch_error(self, error_msg):
        """Обробник помилки запуску"""
        QMessageBox.critical(self, "Помилка запуску", error_msg)
        self.on_launch_finished()


def main():
    app = QApplication(sys.argv)
    
    # Встановлюємо темну тему для всього додатку
    app.setStyle('Fusion')
    
    window = GazeTrackerGUI()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main() 