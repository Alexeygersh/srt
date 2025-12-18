import tkinter as tk
from tkinter import ttk, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np
import time


class AnimationWindow:
    def __init__(self, root, pipeline):
        self.root = root
        self.pipeline = pipeline
        self.window = None
        self.fig = None
        self.canvas = None
        self.axes = None

        self.parent_gui = None

        # Прогресс-бар и кнопки
        self.progress_bar = None
        self.progress_label = None
        self.progress_percent = None
        self.btn_stop = None
        self.btn_close = None

        # Пределы для стабильного отображения
        self.p_y_limits = None
        self.v_y_limits = None

        # Для управления скоростью
        self.last_update_time = 0
        self.min_update_interval = 0.05  # секунд (20 кадров/с по умолчанию)
        self.frame_counter = 0
        self.update_enabled = True

    def open(self):
        """Открытие окна анимации"""
        if self.window and tk.Toplevel.winfo_exists(self.window):
            self.window.lift()
            return

        self.window = tk.Toplevel(self.root)
        self.window.title("Анимация нестационарного процесса")
        self.window.geometry("1400x900")

        # Сохраняем ссылку на родительское GUI для проверки статуса расчёта
        # Ищем объект PipelineGUI среди виджетов root
        for widget in self.root.winfo_children():
            if hasattr(widget, 'calculation_running'):
                self.parent_gui = widget
                break
        else:
            # Если это сам root
            self.parent_gui = self.root

        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

        # Создаём фигуру с двумя графиками
        self.fig = Figure(figsize=(14, 9))
        self.axes = {
            'pressure': self.fig.add_subplot(211),
            'velocity': self.fig.add_subplot(212)
        }

        # Настройка графика давления
        self.axes['pressure'].set_xlabel('Расстояние, км', fontsize=11)
        self.axes['pressure'].set_ylabel('Давление, МПа', fontsize=11)
        self.axes['pressure'].set_title('Давление P(x, t) - реальное время', fontsize=12)
        self.axes['pressure'].grid(True, alpha=0.3)

        # Настройка графика скорости
        self.axes['velocity'].set_xlabel('Расстояние, км', fontsize=11)
        self.axes['velocity'].set_ylabel('Скорость, м/с', fontsize=11)
        self.axes['velocity'].set_title('Скорость v(x, t) - реальное время', fontsize=12)
        self.axes['velocity'].grid(True, alpha=0.3)

        # Панель прогресса и управления скоростью
        self._create_control_panel()

        # Canvas для отображения
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.window)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.fig.tight_layout()
        self.canvas.draw()

        self.calculation_in_progress = False

    def _create_control_panel(self):
        """Создание панели управления"""
        control_frame = ttk.LabelFrame(self.window, text="Управление анимацией", padding=5)
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        # Левая часть - кнопки
        left_frame = ttk.Frame(control_frame)
        left_frame.pack(side=tk.LEFT, padx=5)

        self.btn_stop = ttk.Button(left_frame, text="Остановить расчёт", width=20, state='normal')
        self.btn_stop.pack(side=tk.LEFT, padx=5)

        # fps
        center_frame = ttk.Frame(control_frame)
        center_frame.pack(side=tk.LEFT, padx=20, fill=tk.X, expand=True)

        ttk.Label(center_frame, text="fps:").pack(side=tk.LEFT)

        self.speed_var = tk.IntVar(value=5)  # 1-10 шкала
        speed_slider = ttk.Scale(center_frame, from_=1, to=10,
                                 orient=tk.HORIZONTAL, variable=self.speed_var,
                                 length=200, command=self._update_speed)
        speed_slider.pack(side=tk.LEFT, padx=10)

        self.speed_label = ttk.Label(center_frame, text="5", width=10)
        self.speed_label.pack(side=tk.LEFT)

        # Правая часть - прогресс
        right_frame = ttk.Frame(control_frame)
        right_frame.pack(side=tk.RIGHT, padx=5)

        self.progress_label = ttk.Label(right_frame, text="Инициализация...", font=('Arial', 9))
        self.progress_label.pack(side=tk.TOP)

        progress_bar_frame = ttk.Frame(right_frame)
        progress_bar_frame.pack(side=tk.TOP, fill=tk.X, expand=True)

        self.progress_bar = ttk.Progressbar(progress_bar_frame, mode='determinate', length=200)
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        self.progress_percent = ttk.Label(progress_bar_frame, text="0%", font=('Arial', 9, 'bold'), width=5)
        self.progress_percent.pack(side=tk.LEFT)

    def _update_speed(self, *args):
        """Обновление скорости анимации при движении ползунка"""
        speed = self.speed_var.get()
        self.min_update_interval = 1.0 / speed

        self.speed_label.config(text=f"{speed}")

    def update_plot(self, current_time, p_array, v_array, percent):
        """Обновление графика анимации с контролем скорости"""
        if not self.axes:
            return True  # Продолжать расчёт

        try:
            current_time_sec = time.time()

            # Проверяем, прошло ли достаточно времени с последнего обновления
            time_since_last_update = current_time_sec - self.last_update_time

            if time_since_last_update < self.min_update_interval:
                # Пропускаем обновление графика, но обновляем прогресс
                self._update_progress_only(current_time, percent)
                return True  # Продолжать расчёт

            self.last_update_time = current_time_sec
            self.frame_counter += 1

            # Обновляем прогресс-бар
            self.progress_bar.configure(value=percent)
            self.progress_label.config(text=f"Время: {current_time:.2f} с | Кадр: {self.frame_counter}")
            self.progress_percent.config(text=f"{percent:.1f}%")

            # Обновление графика давления
            self.axes['pressure'].clear()
            x_km = self.pipeline.x_km

            self.axes['pressure'].plot(x_km, p_array / 1e6, 'b-', linewidth=2.5, alpha=0.8)
            self.axes['pressure'].set_xlabel('Расстояние, км', fontsize=11)
            self.axes['pressure'].set_ylabel('Давление, МПа', fontsize=11)
            self.axes['pressure'].set_title(f'Давление P(x, t) | t = {current_time:.2f} с', fontsize=12)
            self.axes['pressure'].grid(True, alpha=0.3)

            # Автоматическое масштабирование для давления
            # if len(p_array) > 0:
            #     p_mpa = p_array / 1e6
            #     p_min, p_max = np.min(p_mpa), np.max(p_mpa)
            #     p_range = max(p_max - p_min, 0.1)
            #     margin = p_range * 0.1
            #     self.axes['pressure'].set_ylim(p_min - margin, p_max + margin)
            pressure_min = 0
            pressure_max = 10
            self.axes['pressure'].set_ylim(pressure_min, pressure_max)

            # Обновление графика скорости
            self.axes['velocity'].clear()
            self.axes['velocity'].plot(x_km, v_array, 'orange', linewidth=2.5, alpha=0.8)
            self.axes['velocity'].set_xlabel('Расстояние, км', fontsize=11)
            self.axes['velocity'].set_ylabel('Скорость, м/с', fontsize=11)
            self.axes['velocity'].set_title(f'Скорость v(x, t) | t = {current_time:.2f} с', fontsize=12)
            self.axes['velocity'].grid(True, alpha=0.3)

            velocity_min = -5
            velocity_max = 5
            self.axes['velocity'].set_ylim(velocity_min, velocity_max)
            # Автоматическое масштабирование для скорости
            # if len(v_array) > 0:
            #     v_min, v_max = np.min(v_array), np.max(v_array)
            #     v_range = max(abs(v_max - v_min), 0.01)
            #     margin = v_range * 0.1

            #     if v_min < 0:
            #         abs_max = max(abs(v_min), abs(v_max))
            #         self.axes['velocity'].set_ylim(-abs_max - margin, abs_max + margin)
            #     else:
            #         self.axes['velocity'].set_ylim(v_min - margin, v_max + margin)

            # Отрисовка
            self.fig.tight_layout()
            self.canvas.draw()

            # Небольшая пауза для обработки событий GUI
            self.window.update_idletasks()

        except Exception as e:
            print(f"Ошибка обновления графика: {e}")
            import traceback
            traceback.print_exc()

        return True  # Продолжать расчёт

    def _update_progress_only(self, current_time, percent):
        """Обновляем только прогресс-бар (без перерисовки графика)"""
        if not self.progress_bar:
            return

        self.progress_bar.configure(value=percent)
        self.progress_label.config(text=f"Время: {current_time:.2f} с | Кадр: {self.frame_counter}")
        self.progress_percent.config(text=f"{percent:.1f}%")

        # Обрабатываем события GUI
        self.window.update_idletasks()

    def _on_close(self):
        """Обработчик попытки закрытия окна анимации"""
        # Получаем ссылку на главное окно GUI
        main_gui = None
        for widget in self.root.winfo_children():
            if hasattr(widget, 'calculation_running'):
                main_gui = widget
                break

        # Если не нашли через children, пробуем через атрибут
        if main_gui is None and hasattr(self, 'parent_gui'):
            main_gui = self.parent_gui

        # Проверяем статус расчёта
        if main_gui and hasattr(main_gui, 'calculation_running') and main_gui.calculation_running:
            messagebox.showwarning(
                "Расчёт выполняется",
                "Невозможно закрыть окно во время выполнения расчёта.\n\n"
                "Дождитесь завершения расчёта или нажмите 'Остановить расчёт'."
            )
        else:
            self.close()

    def close(self):
        """Безопасное закрытие окна анимации"""
        if self.window and tk.Toplevel.winfo_exists(self.window):
            self.window.destroy()
            self.window = None

    def set_stop_command(self, command):
        """Установка команды для кнопки остановки"""
        if self.btn_stop:
            self.btn_stop.config(command=command)

    def finalize(self, success=True):
        """Завершение анимации"""
        if self.btn_stop:
            if success:
                self.btn_stop.config(state='disabled', text="Расчёт завершён")
            else:
                self.btn_stop.config(state='disabled', text="Ошибка")

        # Показываем финальный кадр
        if success and self.pipeline.p_history:
            # Показываем последний кадр
            self._show_final_frame()

    def _show_final_frame(self):
        """Показать финальный кадр"""
        if not self.pipeline.p_history or not self.axes:
            return

        last_idx = len(self.pipeline.p_history) - 1
        current_time = self.pipeline.t_history[last_idx]
        p_array = self.pipeline.p_history[last_idx]
        v_array = self.pipeline.v_history[last_idx]

        self.update_plot(current_time, p_array, v_array, 100.0)

        # Обновляем заголовок
        self.axes['pressure'].set_title(f'Финальное состояние | t = {current_time:.2f} с', fontsize=12)
        self.axes['velocity'].set_title(f'Финальное состояние | t = {current_time:.2f} с', fontsize=12)

        self.canvas.draw()
