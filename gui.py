import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np
import threading
import time
import os
import csv

import constants as c
import db_manager as db
from calc import PipelineFlow


class PipelineGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Моделирование течения нефти в трубопроводе")
        self.root.geometry("800x800")

        self.pipeline = PipelineFlow()
        self.db_manager = db.DatabaseManager()
        self.calculation_running = False
        self.stop_requested = False

        # Окна для визуализации
        self.plot_window = None
        self.animation_fig = None
        self.animation_canvas = None
        self.animation_axes = None

        self.plot_type_var = tk.StringVar(value='stationary_both')
        self.live_mode_var = tk.BooleanVar(value=True)

        self.create_widgets()

    def create_widgets(self):
        """Создание всех элементов интерфейса"""
        # ============================================================
        # Верхняя панель - Параметры
        # ============================================================
        params_frame = ttk.LabelFrame(self.root, text="Параметры моделирования",
                                      padding=10)
        params_frame.pack(fill=tk.X, padx=10, pady=5)

        # Левая колонка - Параметры трубы
        pipe_frame = ttk.Frame(params_frame)
        pipe_frame.grid(row=0, column=0, padx=10, sticky='n')

        ttk.Label(pipe_frame, text="ТРУБА", font=('Arial', 10, 'bold')).grid(row=0, column=0, columnspan=2, pady=5)

        ttk.Label(pipe_frame, text="Длина, км:").grid(row=1, column=0, sticky='w')
        self.length_var = tk.StringVar(value=str(c.XN_KM - c.X0_KM))
        ttk.Entry(pipe_frame, textvariable=self.length_var, width=15).grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(pipe_frame, text="Диаметр (внеш.), мм:").grid(row=2, column=0, sticky='w')
        self.diameter_var = tk.StringVar(value=str(c.EXTERNAL_DIAMETER_MM))
        ttk.Entry(pipe_frame, textvariable=self.diameter_var, width=15).grid(row=2, column=1, padx=5, pady=2)

        ttk.Label(pipe_frame, text="Толщина стенки, мм:").grid(row=3, column=0, sticky='w')
        self.thickness_var = tk.StringVar(value=str(c.WALL_THICKNESS_MM))
        ttk.Entry(pipe_frame, textvariable=self.thickness_var, width=15).grid(row=3, column=1, padx=5, pady=2)

        ttk.Label(pipe_frame, text="Шероховатость, мм:").grid(row=4, column=0, sticky='w')
        self.roughness_var = tk.StringVar(value=str(c.ABS_ROUGHTNESS_MM))
        ttk.Entry(pipe_frame, textvariable=self.roughness_var, width=15).grid(row=4, column=1, padx=5, pady=2)

        # Средняя колонка - Параметры нефти и давления
        oil_frame = ttk.Frame(params_frame)
        oil_frame.grid(row=0, column=1, padx=10, sticky='n')

        ttk.Label(oil_frame, text="НЕФТЬ И ДАВЛЕНИЕ", font=('Arial', 10, 'bold')).grid(row=0, column=0, columnspan=2, pady=5)

        ttk.Label(oil_frame, text="Температура, °C:").grid(row=1, column=0, sticky='w')
        self.temp_var = tk.StringVar(value=str(c.TC))
        ttk.Entry(oil_frame, textvariable=self.temp_var, width=15).grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(oil_frame, text="Давление вход, МПа:").grid(row=2, column=0, sticky='w')
        self.p_inlet_var = tk.StringVar(value=str(c.P_INITIAL_MPA))
        ttk.Entry(oil_frame, textvariable=self.p_inlet_var, width=15).grid(row=2, column=1, padx=5, pady=2)

        ttk.Label(oil_frame, text="Давление выход, МПа:").grid(row=3, column=0, sticky='w')
        self.p_outlet_var = tk.StringVar(value=str(c.P_END_MPA))
        ttk.Entry(oil_frame, textvariable=self.p_outlet_var, width=15).grid(row=3, column=1, padx=5, pady=2)

        ttk.Label(oil_frame, text="Скорость звука, м/с:").grid(row=4, column=0, sticky='w')
        self.sound_speed_var = tk.StringVar(value=str(c.SPEED_OF_SOUND))
        ttk.Entry(oil_frame, textvariable=self.sound_speed_var, width=15).grid(row=4, column=1, padx=5, pady=2)

        # Правая колонка - Параметры расчёта
        calc_frame = ttk.Frame(params_frame)
        calc_frame.grid(row=0, column=2, padx=10, sticky='n')

        ttk.Label(calc_frame, text="РАСЧЁТ", font=('Arial', 10, 'bold')).grid(row=0, column=0, columnspan=2, pady=5)

        ttk.Label(calc_frame, text="Шаг сетки, км:").grid(row=1, column=0, sticky='w')
        self.dx_var = tk.StringVar(value=str(c.dx_km))
        ttk.Entry(calc_frame, textvariable=self.dx_var, width=15).grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(calc_frame, text="Метод расчёта λ:").grid(row=2, column=0, sticky='w')
        self.lambda_method_var = tk.StringVar(value='auto')
        lambda_combo = ttk.Combobox(calc_frame, textvariable=self.lambda_method_var,
                                    values=['auto', 'stokes', 'ginzburg', 'blasius', 'altshul', 'shifrinson', 'colebrook'],
                                    state='readonly', width=13)
        lambda_combo.grid(row=2, column=1, padx=5, pady=2)

        ttk.Label(calc_frame, text="Шагов по времени:").grid(row=3, column=0, sticky='w')
        self.time_steps_var = tk.StringVar(value="2000")
        ttk.Entry(calc_frame, textvariable=self.time_steps_var, width=15).grid(row=3, column=1, padx=5, pady=2)

        ttk.Label(calc_frame, text="Сохранять каждые:").grid(row=4, column=0, sticky='w')
        self.store_every_var = tk.StringVar(value="5")
        ttk.Entry(calc_frame, textvariable=self.store_every_var, width=15).grid(row=4, column=1, padx=5, pady=2)

        self.parallel_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(calc_frame, text="Параллельные вычисления", variable=self.parallel_var).grid(row=5, column=0, columnspan=2, pady=2, sticky='w')

        # ============================================================
        # Средняя панель - Управление и Граничные условия
        # ============================================================
        control_frame = ttk.Frame(self.root)
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        # Левая часть - Кнопки расчёта
        buttons_frame = ttk.LabelFrame(control_frame, text="Управление", padding=10)
        buttons_frame.pack(side=tk.LEFT, padx=5)

        self.btn_stationary = ttk.Button(buttons_frame, text="▶ Стационарный расчёт", command=self.run_stationary, width=28)
        self.btn_stationary.grid(row=0, column=0, padx=5, pady=5)

        self.btn_unsteady = ttk.Button(buttons_frame, text="▶ Нестационарный расчёт", command=self.run_unsteady_animated, width=28)
        self.btn_unsteady.grid(row=1, column=0, padx=5, pady=5)

        ttk.Separator(buttons_frame, orient='horizontal').grid(row=3, column=0, sticky='ew', pady=10)

        self.btn_visualize = ttk.Button(buttons_frame, text="Открыть визуализацию", command=self.open_plot_window, width=28)
        self.btn_visualize.grid(row=4, column=0, padx=5, pady=5)

        self.btn_table = ttk.Button(buttons_frame, text="Показать таблицу", command=self.show_table, width=28)
        self.btn_table.grid(row=5, column=0, padx=5, pady=5)

        ttk.Separator(buttons_frame, orient='horizontal').grid(row=6, column=0, sticky='ew', pady=10)

        self.btn_save = ttk.Button(buttons_frame, text="Сохранить в БД", command=self.save_to_db, width=28)
        self.btn_save.grid(row=7, column=0, padx=5, pady=5)

        self.btn_load = ttk.Button(buttons_frame, text="Загрузить из БД", command=self.show_database_window, width=28)
        self.btn_load.grid(row=8, column=0, padx=5, pady=5)

        # Правая часть - Граничные условия для нестационарного расчёта
        bc_frame = ttk.LabelFrame(control_frame, text="Граничные условия (нестационарный)", padding=10)
        bc_frame.pack(side=tk.LEFT, padx=5, fill=tk.BOTH, expand=True)

        ttk.Label(bc_frame, text="Тип:").grid(row=0, column=0, sticky='w')
        self.bc_type_var = tk.StringVar(value='valve_closure')
        bc_combo = ttk.Combobox(bc_frame, textvariable=self.bc_type_var,
                                values=['valve_closure', 'pressure_inlet', 'pressure_outlet'],
                                state='readonly', width=20)
        bc_combo.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(bc_frame, text="Время изменения, с:").grid(row=1, column=0, sticky='w')
        self.bc_time_var = tk.StringVar(value="0")
        ttk.Entry(bc_frame, textvariable=self.bc_time_var, width=22).grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(bc_frame, text="Новое значение:").grid(row=2, column=0, sticky='w')
        self.bc_value_var = tk.StringVar(value="0")
        ttk.Entry(bc_frame, textvariable=self.bc_value_var, width=22).grid(row=2, column=1, padx=5, pady=2)

        ttk.Label(bc_frame, text="(МПа для давления)", font=('Arial', 8, 'italic')).grid(row=3, column=1, sticky='w')

        # ============================================================
        # Ползунок
        # ============================================================
        speed_frame = ttk.LabelFrame(self.root, text="Скорость анимации", padding=5)
        speed_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(speed_frame, text="Задержка между кадрами (мс):").pack(side=tk.LEFT, padx=5)
        self.anim_speed_var = tk.IntVar(value=50)
        speed_slider = ttk.Scale(speed_frame, from_=1, to=300, orient=tk.HORIZONTAL, variable=self.anim_speed_var)
        speed_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        ttk.Label(speed_frame, textvariable=self.anim_speed_var).pack(side=tk.LEFT, padx=5)

        # ============================================================
        # Лог
        # ============================================================
        log_frame = ttk.LabelFrame(self.root, text="Лог расчётов", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, state='normal', wrap=tk.WORD, font=('Consolas', 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def log_message(self, message):
        """Добавление сообщения в лог"""
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + '\n')
        self.log_text.see(tk.END)
        # self.log_text.config(state='disabled')
        self.root.update()

    def update_constants(self):
        """Обновление констант из полей ввода"""
        try:

            total_length = float(self.length_var.get())
            c.XN_KM = total_length

            c.EXTERNAL_DIAMETER_MM = float(self.diameter_var.get())
            c.WALL_THICKNESS_MM = float(self.thickness_var.get())
            c.ABS_ROUGHTNESS_MM = float(self.roughness_var.get())

            c.EXTERNAL_DIAMETER = c.EXTERNAL_DIAMETER_MM / 1000
            c.WALL_THICKNESS = c.WALL_THICKNESS_MM / 1000
            c.INTERNAL_DIAMETER = c.EXTERNAL_DIAMETER - 2 * c.WALL_THICKNESS
            c.ABS_ROUGHTNESS = c.ABS_ROUGHTNESS_MM / 1000
            c.L = c.XN_KM * 1000

            c.TC = float(self.temp_var.get())
            c.T = c.TC + 273.15
            c.P_INITIAL_MPA = float(self.p_inlet_var.get())
            c.P_END_MPA = float(self.p_outlet_var.get())
            c.P_INITIAL = c.P_INITIAL_MPA * 1e6
            c.P_END = c.P_END_MPA * 1e6
            c.SPEED_OF_SOUND = float(self.sound_speed_var.get())

            c.dx_km = float(self.dx_var.get())

            return True
        except ValueError as e:
            messagebox.showerror("Ошибка", f"Неверный формат данных: {e}")
            return False

    def run_stationary(self):
        """Запуск стационарного расчёта"""
        if not self.update_constants():
            return
        try:
            lambda_method = self.lambda_method_var.get()
            self.pipeline = PipelineFlow()  # Новый объект
            self.pipeline.calculate_stationary(lambda_method=lambda_method, verbose=False)

            self.log_message(f"Плотность при {c.TC}°C: ρ = {self.pipeline.rho:.2f} кг/м³")
            self.log_message(f"Кинематическая вязкость: ν = {self.pipeline.nu*1e6:.2f} сСт")
            self.log_message(f"Скорость нефти: v = {self.pipeline.v:.4f} м/с")
            self.log_message(f"Число Рейнольдса: Re = {self.pipeline.Re:.0f}")
            self.log_message(f"Коэффициент сопротивления: λ = {self.pipeline.lambda_:.5f}")
            self.log_message(f"Число точек сетки: {len(self.pipeline.x_km)}")
            self.log_message("Расчёт завершён успешно!")
            self.log_message("=" * 60)

            self.update_static_plot()

        except Exception as e:
            self.log_message(f"ОШИБКА: {e}")
            messagebox.showerror("Ошибка расчёта", str(e))

    def run_unsteady_animated(self):
        """Запуск нестационарного расчёта"""
        if not self.pipeline.stationary_calculated:
            messagebox.showwarning("Предупреждение", "Сначала выполните стационарный расчёт!")
            return

        if not hasattr(self.pipeline, 'P_original') or self.pipeline.P_original is None:
            self.pipeline.P_original = self.pipeline.P.copy()
            self.pipeline.v_arr_original = self.pipeline.v_arr.copy()
            self.log_message("Стационарные данные сохранены для восстановления")

        self.log_message("\n" + "=" * 60)
        self.log_message("Запуск нестационарного расчёта с анимацией...")
        self.log_message("=" * 60)

        try:
            num_steps = int(self.time_steps_var.get())
            store_every = int(self.store_every_var.get())
            bc_type = self.bc_type_var.get()

            bc_time = None
            bc_value = None

            if bc_type != 'valve_closure':
                bc_time = float(self.bc_time_var.get())
                bc_value_mpa = float(self.bc_value_var.get())
                bc_value = bc_value_mpa * 1e6

            lambda_method = self.lambda_method_var.get()
            use_parallel = self.parallel_var.get()

            self.log_message(f"Шагов по времени: {num_steps}")
            self.log_message(f"Граничное условие: {bc_type}")
            if bc_time is not None:
                self.log_message(f"Изменение в момент t = {bc_time:.2f} с")

            # Открываем окно анимации
            self.open_animation_window()

            # Блокируем кнопки
            self.btn_stationary.config(state='disabled')
            self.btn_unsteady.config(state='disabled')
            if hasattr(self, 'anim_btn_close'):
                self.anim_btn_close.config(state='disabled')

            # Запуск в отдельном потоке
            thread = threading.Thread(
                target=self._run_unsteady_with_animation,
                args=(num_steps, store_every, bc_type, bc_time, bc_value, lambda_method, use_parallel),
                daemon=True
            )
            thread.start()

            # Разблокировка кнопок после завершения
            def check_completion():
                if not thread.is_alive():
                    self.btn_stationary.config(state='normal')
                    self.btn_unsteady.config(state='normal')
                    self.calculation_running = False

                    # разблокируем кнопку закрытия окна анимации
                    if hasattr(self, 'anim_btn_close'):
                        self.anim_btn_close.config(state='normal')

                    if hasattr(self.pipeline, 'P_original') and self.pipeline.P_original is not None:
                        self.pipeline.P = self.pipeline.P_original.copy()
                        self.pipeline.v_arr = self.pipeline.v_arr_original.copy()
                        self.log_message("Стационарные данные восстановлены")
                else:
                    self.root.after(100, check_completion)

            self.root.after(100, check_completion)

        except ValueError as e:
            messagebox.showerror("Ошибка", f"Неверный формат данных: {e}")

    def _run_unsteady_with_animation(self, num_steps, store_every, bc_type, bc_time, bc_value, lambda_method, use_parallel):
        """Выполнение нестационарного расчёта с динамической анимацией"""
        try:
            self.calculation_running = True
            self.stop_requested = False

            # Инициализируем пределы для графиков (для стабильности отображения)
            self.p_y_limits = None
            self.v_y_limits = None

            # уменьшаем интервал обновления для плавной анимации
            self.update_counter = 0
            self.update_frequency = max(1, store_every // 5)  # Обновляем в 5 раз чаще, чем сохраняем

            # Функция обратной связи для обновления прогресса и графика
            def update_progress_and_plot(current, total, current_time, p_array, v_array):
                if self.stop_requested:
                    return False  # Сигнал остановки

                percent = 100.0 * current / total

                # Устанавливаем пределы графиков при первом вызове (для стабильности)
                if self.p_y_limits is None and len(p_array) > 0:
                    p_min, p_max = np.min(p_array) / 1e6, np.max(p_array) / 1e6
                    p_range = p_max - p_min
                    self.p_y_limits = (p_min - 0.1 * p_range, p_max + 0.1 * p_range)

                if self.v_y_limits is None and len(v_array) > 0:
                    v_min, v_max = np.min(v_array), np.max(v_array)
                    v_range = max(abs(v_max - v_min), 0.1)  # Минимальный диапазон
                    self.v_y_limits = (v_min - 0.1 * v_range, v_max + 0.1 * v_range)

                def update_ui():
                    # Обновление графика (каждый раз)
                    if self.animation_axes:
                        self.update_animation_plot(current_time, p_array, v_array, percent)

                self.root.after(0, update_ui)

                # Небольшая задержка для контроля скорости
                # Используем меньшее значение для более плавной анимации
                delay = self.anim_speed_var.get() / 1000.0
                time.sleep(delay * 0.3)  # 30% от установленной задержки

                return True  # Продолжить расчёт

            # Запускаем расчёт (с меньшим store_every для плавности)
            # Уменьшаем store_every для частого обновления
            effective_store_every = max(1, store_every // 10)  # В 10 раз чаще

            self.pipeline.calculate_unsteady_with_callback(
                num_steps=num_steps,
                store_every=effective_store_every,
                boundary_condition=bc_type,
                bc_change_time=bc_time,
                bc_change_value=bc_value,
                lambda_method=lambda_method,
                use_parallel=use_parallel,
                verbose=False,
                progress_callback=update_progress_and_plot
            )

            # Обновляем кнопку остановки при завершении
            def finalize_ui():
                if hasattr(self, 'anim_btn_stop'):
                    self.anim_btn_stop.config(state='disabled', text="Расчёт завершён")

                # Разблокировка кнопки закрытия
                if hasattr(self, 'anim_btn_close'):
                    self.anim_btn_close.config(state='normal')

            self.root.after(0, finalize_ui)

            self.log_message("Расчёт завершён успешно!")
            self.log_message(f"Сохранено {len(self.pipeline.t_history)} временных слоёв")
            self.log_message("=" * 60)
        except Exception as e:
            self.calculation_running = False

            error_msg = str(e)
            import traceback
            error_trace = traceback.format_exc()

            self.log_message(f"ОШИБКА: {error_msg}")
            self.log_message(f"Трассировка:\n{error_trace}")

            def finalize_error():
                if hasattr(self, 'anim_btn_stop'):
                    self.anim_btn_stop.config(state='disabled', text="Ошибка")
                messagebox.showerror("Ошибка расчёта", f"{error_msg}\n\nПроверьте лог для подробностей")

            self.root.after(0, finalize_error)
        finally:
            self.calculation_running = False

    def stop_calculation(self):
        """Остановка расчёта"""
        if self.calculation_running:
            self.stop_requested = True
            self.log_message("Запрос на остановку расчёта...")
            if hasattr(self, 'anim_btn_stop'):
                self.anim_btn_stop.config(state='disabled', text="⏹ Остановка...")

            # После остановки разблокируем кнопку закрытия
            def enable_close_button():
                if hasattr(self, 'anim_btn_close'):
                    self.anim_btn_close.config(state='normal')

            self.root.after(100, enable_close_button)

    # ============================================================
    # Окно динамической анимации
    # ============================================================

    def open_animation_window(self):
        """Открытие окна для динамической анимации"""
        if self.plot_window and tk.Toplevel.winfo_exists(self.plot_window):
            self.plot_window.lift()
            return

        self.plot_window = tk.Toplevel(self.root)
        self.plot_window.title("Динамическая анимация нестационарного процесса")
        self.plot_window.geometry("1400x900")

        self.plot_window.protocol("WM_DELETE_WINDOW", self.on_animation_window_close)

        # Создаем фигуру с двумя графиками
        self.animation_fig = Figure(figsize=(14, 9))
        self.animation_axes = {
            'pressure': self.animation_fig.add_subplot(211),
            'velocity': self.animation_fig.add_subplot(212)
        }

        # Настройка графика давления
        self.animation_axes['pressure'].set_xlabel('Расстояние, км', fontsize=11)
        self.animation_axes['pressure'].set_ylabel('Давление, МПа', fontsize=11)
        self.animation_axes['pressure'].set_title('Давление P(x, t) - реальное время', fontsize=12)
        self.animation_axes['pressure'].grid(True, alpha=0.3)

        # Настройка графика скорости
        self.animation_axes['velocity'].set_xlabel('Расстояние, км', fontsize=11)
        self.animation_axes['velocity'].set_ylabel('Скорость, м/с', fontsize=11)
        self.animation_axes['velocity'].set_title('Скорость v(x, t) - реальное время', fontsize=12)
        self.animation_axes['velocity'].grid(True, alpha=0.3)

        anim_progress_frame = ttk.LabelFrame(self.plot_window, text="Прогресс расчёта", padding=5)
        anim_progress_frame.pack(fill=tk.X, padx=10, pady=5)

        # Кнопка остановки слева
        self.anim_btn_stop = ttk.Button(anim_progress_frame, text="⏹ Остановить", command=self.stop_calculation, width=20, state='normal')
        self.anim_btn_stop.pack(side=tk.LEFT, padx=5)

        # Прогресс-бар и метки
        self.anim_progress_label = ttk.Label(anim_progress_frame, text="Инициализация...", font=('Arial', 9))
        self.anim_progress_label.pack(side=tk.LEFT, padx=5)

        self.anim_progress_bar = ttk.Progressbar(anim_progress_frame, mode='determinate', length=400)
        self.anim_progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        self.anim_progress_percent = ttk.Label(anim_progress_frame, text="0%", font=('Arial', 9, 'bold'))
        self.anim_progress_percent.pack(side=tk.LEFT, padx=5)

        # Canvas для отображения
        self.animation_canvas = FigureCanvasTkAgg(self.animation_fig, master=self.plot_window)
        self.animation_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.animation_fig.tight_layout()
        self.animation_canvas.draw()

    def on_animation_window_close(self):
        # Обработчик попытки закрытия окна анимации
        if self.calculation_running:
            messagebox.showwarning(
                "Расчёт выполняется",
                "Невозможно закрыть окно во время выполнения расчёта.\n\n"
                "Дождитесь завершения расчёта или нажмите 'Остановить расчёт'."
            )
            return

        self.close_animation_window()

    def close_animation_window(self):
        """Безопасное закрытие окна анимации"""
        if self.plot_window and tk.Toplevel.winfo_exists(self.plot_window):
            self.plot_window.destroy()
            self.plot_window = None

    def update_animation_plot(self, current_time, p_array, v_array, percent):
        """Обновление графика анимации в реальном времени"""
        if not self.animation_axes:
            return

        try:
            # Обновляем прогресс-бар в окне анимации
            def update_anim_progress():
                self.anim_progress_bar.configure(value=percent)
                self.anim_progress_label.config(text=f"Время: {current_time:.2f} с")
                self.anim_progress_percent.config(text=f"{percent:.1f}%")

            self.root.after(0, update_anim_progress)

            # Обновление графика давления
            self.animation_axes['pressure'].clear()
            x_km = self.pipeline.x_km

            self.animation_axes['pressure'].plot(x_km, p_array / 1e6, 'b-', linewidth=2.5, alpha=0.8)
            self.animation_axes['pressure'].set_xlabel('Расстояние, км', fontsize=11)
            self.animation_axes['pressure'].set_ylabel('Давление, МПа', fontsize=11)
            self.animation_axes['pressure'].set_title(f'Давление P(x, t) | t = {current_time:.2f} с', fontsize=12)
            self.animation_axes['pressure'].grid(True, alpha=0.3)

            pressure_min = 0  # МПа
            pressure_max = 10  # МПа
            self.animation_axes['pressure'].set_ylim(pressure_min, pressure_max)
            # Автоматическое масштабирование для давления
            # if len(p_array) > 0:
            #     p_mpa = p_array / 1e6
            #     p_min, p_max = np.min(p_mpa), np.max(p_mpa)
            #     p_range = max(p_max - p_min, 0.1)  # Минимальный диапазон 0.1 МПа
            #     margin = p_range * 0.1  # 10% отступ
            #     self.animation_axes['pressure'].set_ylim(p_min - margin, p_max + margin)

            # Обновление графика скорости
            self.animation_axes['velocity'].clear()

            self.animation_axes['velocity'].plot(x_km, v_array, 'orange', linewidth=2.5, alpha=0.8)
            self.animation_axes['velocity'].set_xlabel('Расстояние, км', fontsize=11)
            self.animation_axes['velocity'].set_ylabel('Скорость, м/с', fontsize=11)
            self.animation_axes['velocity'].set_title(f'Скорость v(x, t) | t = {current_time:.2f} с', fontsize=12)
            self.animation_axes['velocity'].grid(True, alpha=0.3)

            # Автоматическое масштабирование для скорости
            # if len(v_array) > 0:
            #     v_min, v_max = np.min(v_array), np.max(v_array)
            #     v_range = max(abs(v_max - v_min), 0.01)  # Минимальный диапазон 0.01 м/с
            #     margin = v_range * 0.1  # 10% отступ

            #     # Если скорость становится отрицательной, показываем симметричный диапазон
            #     if v_min < 0:
            #         abs_max = max(abs(v_min), abs(v_max))
            #         self.animation_axes['velocity'].set_ylim(-abs_max - margin, abs_max + margin)
            #     else:
            #         self.animation_axes['velocity'].set_ylim(v_min - margin, v_max + margin)
            velocity_min = -5  # м/с
            velocity_max = 5   # м/с
            self.animation_axes['velocity'].set_ylim(velocity_min, velocity_max)

            # Отрисовка
            self.animation_fig.tight_layout()
            self.animation_canvas.draw()

        except Exception as e:
            print(f"Ошибка обновления графика: {e}")
            import traceback
            traceback.print_exc()

    # ============================================================
    # Визуализация для стационарных результатов
    # ============================================================

    def open_plot_window(self):
        """Открытие окна с графиками"""
        if not self.pipeline.stationary_calculated:
            messagebox.showwarning("Предупреждение", "Сначала выполните расчёт!")
            return

        # Если окно уже открыто - активируем его
        if self.plot_window and tk.Toplevel.winfo_exists(self.plot_window):
            self.plot_window.lift()
            self.plot_window.focus()
            return

        # Создаём новое окно
        self.plot_window = tk.Toplevel(self.root)
        self.plot_window.title("Визуализация результатов")
        self.plot_window.geometry("1200x800")

        # Панель выбора типа графика
        plot_control = ttk.Frame(self.plot_window)
        plot_control.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(plot_control, text="Тип графика:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=10)

        plot_types = [
            ('Стац. P(x)', 'stationary_p'),
            ('Стац. v(x)', 'stationary_v'),
            ('Стац. P+v', 'stationary_both'),
        ]

        for text, value in plot_types:
            ttk.Radiobutton(plot_control, text=text,
                            variable=self.plot_type_var,
                            value=value,
                            command=self.update_static_plot).pack(side=tk.LEFT, padx=5)

        # Кнопка обновления
        ttk.Button(plot_control, text="Обновить", command=self.update_static_plot).pack(side=tk.RIGHT, padx=5)

        # Кнопка сохранения
        ttk.Button(plot_control, text="Сохранить изображение", command=self.save_plot).pack(side=tk.RIGHT, padx=5)

        # Canvas для графика
        self.static_fig = Figure(figsize=(12, 7))
        self.static_canvas = FigureCanvasTkAgg(self.static_fig, master=self.plot_window)
        self.static_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Рисуем график
        self.update_static_plot()

    def update_static_plot(self):
        """Обновление статического графика"""
        if not self.plot_window or not tk.Toplevel.winfo_exists(self.plot_window):
            return

        plot_type = self.plot_type_var.get()
        self.static_fig.clear()

        try:
            # Используем оригинальные стационарные данные для графика
            # если они существуют, иначе используем текущие
            if hasattr(self.pipeline, 'P_original') and self.pipeline.P_original is not None:
                # Временно заменяем данные для построения графика
                P_backup = self.pipeline.P
                v_backup = self.pipeline.v_arr

                self.pipeline.P = self.pipeline.P_original
                self.pipeline.v_arr = self.pipeline.v_arr_original

                if plot_type == 'stationary_p':
                    self.plot_stationary_pressure()
                elif plot_type == 'stationary_v':
                    self.plot_stationary_velocity()
                elif plot_type == 'stationary_both':
                    self.plot_stationary_both()

                # Восстанавливаем текущие данные
                self.pipeline.P = P_backup
                self.pipeline.v_arr = v_backup
            else:
                # Используем текущие данные
                if plot_type == 'stationary_p':
                    self.plot_stationary_pressure()
                elif plot_type == 'stationary_v':
                    self.plot_stationary_velocity()
                elif plot_type == 'stationary_both':
                    self.plot_stationary_both()

            self.static_canvas.draw()

        except Exception as e:
            messagebox.showerror("Ошибка отображения", str(e))

    def plot_stationary_pressure(self):
        """График стационарного давления"""
        if not self.pipeline.stationary_calculated:
            return

        ax = self.static_fig.add_subplot(111)
        ax.plot(self.pipeline.x_km, self.pipeline.P / 1e6, 'b-o', markersize=4, linewidth=2)
        ax.set_xlabel('Расстояние, км', fontsize=12)
        ax.set_ylabel('Давление, МПа', fontsize=12)
        ax.set_title('Стационарное распределение давления P(x)', fontsize=14)
        ax.grid(True, alpha=0.3)

        ax.annotate(f'P₀ = {c.P_INITIAL_MPA:.1f} МПа',
                    xy=(0, c.P_INITIAL_MPA), xytext=(5, c.P_INITIAL_MPA - 0.3),
                    arrowprops=dict(arrowstyle='->', color='blue'),
                    fontsize=10, color='blue')

        ax.annotate(f'Pₙ = {c.P_END_MPA:.1f} МПа',
                    xy=(c.XN_KM, c.P_END_MPA), xytext=(c.XN_KM - 15, c.P_END_MPA + 0.3),
                    arrowprops=dict(arrowstyle='->', color='blue'),
                    fontsize=10, color='blue')

        self.static_fig.tight_layout()

    def plot_stationary_velocity(self):
        """График стационарной скорости"""
        if not self.pipeline.stationary_calculated:
            return

        ax = self.static_fig.add_subplot(111)
        ax.plot(self.pipeline.x_km, self.pipeline.v_arr, 'orange', linewidth=2)
        ax.set_xlabel('Расстояние, км', fontsize=12)
        ax.set_ylabel('Скорость, м/с', fontsize=12, color='orange')
        ax.set_title('Стационарное распределение скорости v(x)', fontsize=14)
        ax.grid(True, alpha=0.3)
        ax.tick_params(axis='y', labelcolor='orange')

        self.static_fig.tight_layout()

    def plot_stationary_both(self):
        """График стационарного давления и скорости"""
        if not self.pipeline.stationary_calculated:
            return

        ax1 = self.static_fig.add_subplot(111)
        ax1.plot(self.pipeline.x_km, self.pipeline.P / 1e6, 'b-o',
                 markersize=4, label='Давление', linewidth=2)
        ax1.set_xlabel('Расстояние, км', fontsize=12)
        ax1.set_ylabel('Давление, МПа', fontsize=12, color='b')
        ax1.tick_params(axis='y', labelcolor='b')
        ax1.grid(True, alpha=0.3)

        ax2 = ax1.twinx()
        ax2.plot(self.pipeline.x_km, self.pipeline.v_arr, 'orange',
                 linewidth=2, label='Скорость')
        ax2.set_ylabel('Скорость, м/с', fontsize=12, color='orange')
        ax2.tick_params(axis='y', labelcolor='orange')

        ax1.set_title('Стационарное распределение P(x) и v(x)', fontsize=14)

        self.static_fig.tight_layout()

    def save_plot(self):
        """Сохранение текущего графика в файл"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[
                ("PNG files", "*.png"),
                ("PDF files", "*.pdf"),
                ("SVG files", "*.svg"),
                ("All files", "*.*")
            ]
        )

        if filename:
            try:
                if hasattr(self, 'static_fig'):
                    self.static_fig.savefig(filename, dpi=300, bbox_inches='tight')
                elif hasattr(self, 'animation_fig'):
                    self.animation_fig.savefig(filename, dpi=300, bbox_inches='tight')
                messagebox.showinfo("Успех", f"График сохранён: {filename}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить: {e}")

    def save_to_db(self):
        """Сохранение результатов в БД"""
        if not self.pipeline.stationary_calculated:
            messagebox.showwarning("Предупреждение", "Нет данных для сохранения!")
            return

        try:
            self.pipeline.save_to_database()
            self.log_message("Результаты сохранены в базу данных!")
            messagebox.showinfo("Успех", "Результаты сохранены в БД!")
        except Exception as e:
            messagebox.showerror("Ошибка сохранения", str(e))

    def show_table(self):
        """Показать таблицу результатов"""
        if not self.pipeline.stationary_calculated:
            messagebox.showwarning("Предупреждение", "Сначала выполните расчёт!")
            return

        # Создание нового окна
        table_window = tk.Toplevel(self.root)
        table_window.title("Таблица результатов")
        table_window.geometry("900x700")

        # Создаем Notebook для вкладок
        notebook = ttk.Notebook(table_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # ===== ВКЛАДКА 1: СТАЦИОНАРНЫЙ РАСЧЁТ =====
        stationary_frame = ttk.Frame(notebook)
        notebook.add(stationary_frame, text="Стационарный расчёт")

        # Treeview для стационарных данных
        tree_frame_stat = ttk.Frame(stationary_frame)
        tree_frame_stat.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        vsb_stat = ttk.Scrollbar(tree_frame_stat, orient="vertical")
        hsb_stat = ttk.Scrollbar(tree_frame_stat, orient="horizontal")

        tree_stat = ttk.Treeview(tree_frame_stat, columns=('x_km', 'P_MPa', 'v_ms'),
                                 show='headings', yscrollcommand=vsb_stat.set,
                                 xscrollcommand=hsb_stat.set)

        vsb_stat.config(command=tree_stat.yview)
        hsb_stat.config(command=tree_stat.xview)

        # Заголовки
        tree_stat.heading('x_km', text='x, км')
        tree_stat.heading('P_MPa', text='P, МПа')
        tree_stat.heading('v_ms', text='v, м/с')

        tree_stat.column('x_km', width=200, anchor='center')
        tree_stat.column('P_MPa', width=200, anchor='center')
        tree_stat.column('v_ms', width=200, anchor='center')

        # Используем оригинальные стационарные данные
        if hasattr(self.pipeline, 'P_original') and self.pipeline.P_original is not None:
            P_MPa = self.pipeline.P_original / 1e6
            v_arr = self.pipeline.v_arr_original
        else:
            P_MPa = self.pipeline.P / 1e6
            v_arr = self.pipeline.v_arr

        for i in range(len(self.pipeline.x_km)):
            tree_stat.insert('', tk.END, values=(
                f'{self.pipeline.x_km[i]:.3f}',
                f'{P_MPa[i]:.3f}',
                f'{v_arr[i]:.4f}'
            ))

        tree_stat.grid(row=0, column=0, sticky='nsew')
        vsb_stat.grid(row=0, column=1, sticky='ns')
        hsb_stat.grid(row=1, column=0, sticky='ew')

        tree_frame_stat.grid_rowconfigure(0, weight=1)
        tree_frame_stat.grid_columnconfigure(0, weight=1)

        # Кнопка экспорта для стационарного
        export_btn_stat = ttk.Button(stationary_frame, text="Экспорт в CSV",
                                     command=lambda: self.export_stationary_to_csv())
        export_btn_stat.pack(pady=5)

        # ===== Вкладка 2 нестационарный расчёт =====
        if self.pipeline.p_history and len(self.pipeline.p_history) > 0:
            unsteady_frame = ttk.Frame(notebook)
            notebook.add(unsteady_frame, text="Нестационарный расчёт")

            # Панель выбора временного слоя
            control_frame = ttk.Frame(unsteady_frame)
            control_frame.pack(fill=tk.X, padx=10, pady=10)

            ttk.Label(control_frame, text="Временной слой:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=5)

            # Список временных точек
            time_var = tk.StringVar()
            time_values = [f"t = {t:.2f} с" for t in self.pipeline.t_history]
            time_combo = ttk.Combobox(control_frame, textvariable=time_var,
                                      values=time_values, state='readonly', width=20)
            time_combo.pack(side=tk.LEFT, padx=5)
            time_combo.current(0)  # Выбираем первый элемент

            # Treeview для нестационарных данных
            tree_frame_unst = ttk.Frame(unsteady_frame)
            tree_frame_unst.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            vsb_unst = ttk.Scrollbar(tree_frame_unst, orient="vertical")
            hsb_unst = ttk.Scrollbar(tree_frame_unst, orient="horizontal")

            tree_unst = ttk.Treeview(tree_frame_unst, columns=('x_km', 'P_MPa', 'v_ms'),
                                     show='headings', yscrollcommand=vsb_unst.set,
                                     xscrollcommand=hsb_unst.set)

            vsb_unst.config(command=tree_unst.yview)
            hsb_unst.config(command=tree_unst.xview)

            tree_unst.heading('x_km', text='x, км')
            tree_unst.heading('P_MPa', text='P, МПа')
            tree_unst.heading('v_ms', text='v, м/с')

            tree_unst.column('x_km', width=200, anchor='center')
            tree_unst.column('P_MPa', width=200, anchor='center')
            tree_unst.column('v_ms', width=200, anchor='center')

            tree_unst.grid(row=0, column=0, sticky='nsew')
            vsb_unst.grid(row=0, column=1, sticky='ns')
            hsb_unst.grid(row=1, column=0, sticky='ew')

            tree_frame_unst.grid_rowconfigure(0, weight=1)
            tree_frame_unst.grid_columnconfigure(0, weight=1)

            # Функция обновления таблицы при выборе временного слоя
            def update_unsteady_table(*args):
                # Очищаем таблицу
                for item in tree_unst.get_children():
                    tree_unst.delete(item)

                # Получаем индекс выбранного временного слоя
                time_idx = time_combo.current()
                if time_idx < 0 or time_idx >= len(self.pipeline.p_history):
                    return

                # Заполняем таблицу данными
                p_array = self.pipeline.p_history[time_idx]
                v_array = self.pipeline.v_history[time_idx]

                for i in range(len(self.pipeline.x_km)):
                    tree_unst.insert('', tk.END, values=(
                        f'{self.pipeline.x_km[i]:.3f}',
                        f'{p_array[i]/1e6:.3f}',
                        f'{v_array[i]:.4f}'
                    ))

            # Связываем выбор с обновлением таблицы
            time_combo.bind('<<ComboboxSelected>>', update_unsteady_table)

            # Заполняем начальными данными
            update_unsteady_table()

            # Кнопка экспорта для нестационарного
            export_btn_unst = ttk.Button(unsteady_frame, text="Экспорт всех временных слоёв в CSV",
                                         command=lambda: self.export_unsteady_to_csv())
            export_btn_unst.pack(pady=5)

    def export_stationary_to_csv(self):
        """Экспорт стационарных данных в CSV"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile="stationary_results.csv"
        )

        if not filename:
            return

        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['x_km', 'P_MPa', 'v_ms'])

                # Используем оригинальные стационарные данные
                if hasattr(self.pipeline, 'P_original') and self.pipeline.P_original is not None:
                    P_MPa = self.pipeline.P_original / 1e6
                    v_arr = self.pipeline.v_arr_original
                else:
                    P_MPa = self.pipeline.P / 1e6
                    v_arr = self.pipeline.v_arr

                for i in range(len(self.pipeline.x_km)):
                    writer.writerow([
                        self.pipeline.x_km[i],
                        P_MPa[i],
                        v_arr[i]
                    ])

            messagebox.showinfo("Успех", f"Данные экспортированы в {filename}")
        except Exception as e:
            messagebox.showerror("Ошибка экспорта", str(e))

    def export_unsteady_to_csv(self):
        """Экспорт всех временных слоёв нестационарного расчёта в CSV"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile="unsteady_results.csv"
        )

        if not filename:
            return

        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['time_s', 'x_km', 'P_MPa', 'v_ms'])

                for t_idx, t in enumerate(self.pipeline.t_history):
                    p_array = self.pipeline.p_history[t_idx]
                    v_array = self.pipeline.v_history[t_idx]

                    for i in range(len(self.pipeline.x_km)):
                        writer.writerow([
                            t,
                            self.pipeline.x_km[i],
                            p_array[i]/1e6,
                            v_array[i]
                        ])

            messagebox.showinfo("Успех", f"Данные экспортированы в {filename}")
        except Exception as e:
            messagebox.showerror("Ошибка экспорта", str(e))

    # -=--=--==--=-=--=-=--=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
    def show_database_window(self):
        """Окно просмотра и загрузки данных из БД"""

        db_name = 'pipeline_results.db'

        if not os.path.exists(db_name):
            messagebox.showinfo("Информация", "База данных пуста. Сначала сохраните расчёты.")
            return

        # Создание окна
        db_window = tk.Toplevel(self.root)
        db_window.title("База данных расчётов")
        db_window.geometry("1000x600")

        # Верхняя панель - список расчётов
        list_frame = ttk.LabelFrame(db_window, text="Сохранённые расчёты", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Treeview для списка расчётов
        columns = ('id', 'timestamp', 'type', 'points', 'description')
        tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)

        tree.heading('id', text='ID')
        tree.heading('timestamp', text='Дата и время')
        tree.heading('type', text='Тип')
        tree.heading('points', text='Точек')
        tree.heading('description', text='Описание')

        tree.column('id', width=50, anchor='center')
        tree.column('timestamp', width=150, anchor='center')
        tree.column('type', width=120, anchor='center')
        tree.column('points', width=80, anchor='center')
        tree.column('description', width=500, anchor='w')

        # Scrollbar
        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # Загрузка данных из БД через DatabaseManager
        try:
            calculations = self.db_manager.get_all_calculations()

            for calc in calculations:
                calc_id, timestamp, calc_type, num_points, description = calc
                type_display = "Стационарный" if calc_type == "stationary" else "Нестационарный"
                tree.insert('', tk.END, values=(calc_id, timestamp, type_display,
                                                num_points, description))

            if not calculations:
                messagebox.showinfo("Информация", "База данных пуста")
                db_window.destroy()
                return

        except Exception as e:
            messagebox.showerror("Ошибка БД", f"Не удалось загрузить данные: {e}")
            db_window.destroy()
            return

        # Нижняя панель - кнопки управления
        control_frame = ttk.Frame(db_window)
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(control_frame, text="Загрузить",
                   command=lambda: self.load_from_database(tree, db_window),
                   width=30).pack(side=tk.LEFT, padx=5)

        ttk.Button(control_frame, text="Показать таблицу данных",
                   command=lambda: self.show_db_table(tree),
                   width=30).pack(side=tk.LEFT, padx=5)

        ttk.Button(control_frame, text="Удалить выбранный",
                   command=lambda: self.delete_from_database(tree),
                   width=30).pack(side=tk.LEFT, padx=5)

        ttk.Button(control_frame, text="Закрыть",
                   command=db_window.destroy,
                   width=15).pack(side=tk.RIGHT, padx=5)

        ttk.Button(control_frame, text="Очистить всю БД",
                   command=self.clear_database,
                   width=20).pack(side=tk.RIGHT, padx=5)

    def load_from_database(self, tree, parent_window):
        """Загрузка выбранного расчёта из БД"""
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("Предупреждение", "Выберите расчёт для загрузки")
            return

        item = tree.item(selected[0])
        calc_id = item['values'][0]
        calc_type = item['values'][2]

        try:
            if calc_type == "Стационарный":
                # Загрузка стационарного расчёта
                rows = self.db_manager.get_stationary_data(calc_id)

                if not rows:
                    messagebox.showerror("Ошибка", "Данные не найдены")
                    return

                # Создаём НОВЫЙ объект PipelineFlow
                self.pipeline = PipelineFlow()

                # Восстанавливаем данные
                self.pipeline.x_km = np.array([row[0] for row in rows])
                self.pipeline.x_m = np.array([row[1] for row in rows])
                self.pipeline.P = np.array([row[2] for row in rows])
                self.pipeline.v_arr = np.array([row[3] for row in rows])

                # Восстанавливаем все необходимые атрибуты
                self.pipeline.v = self.pipeline.v_arr[0] if len(self.pipeline.v_arr) > 0 else 0
                self.pipeline.stationary_calculated = True

                # Вычисляем недостающие параметры
                if len(self.pipeline.x_km) > 1:
                    self.pipeline.dx = self.pipeline.x_km[1] - self.pipeline.x_km[0]

                # Сохраняем оригинальные стационарные данные
                self.pipeline.P_original = self.pipeline.P.copy()
                self.pipeline.v_arr_original = self.pipeline.v_arr.copy()

                # Восстанавливаем параметры из констант
                self.pipeline.rho = c.RO20 * (1 - 0.0008 * (c.TC - 20))
                self.pipeline.nu = self.pipeline.get_kinematic_viscosity(c.T, c.VISCOSITY_20, c.VISCOSITY_50)
                self.pipeline.epsilon = c.ABS_ROUGHTNESS / c.INTERNAL_DIAMETER

                if len(self.pipeline.v_arr) > 0:
                    self.pipeline.Re = self.pipeline.get_reynolds(
                        self.pipeline.v, c.INTERNAL_DIAMETER, self.pipeline.nu
                    )
                    self.pipeline.lambda_ = self.pipeline.get_lambda(
                        self.pipeline.Re, self.pipeline.epsilon
                    )

                self.log_message(f"\nЗагружен стационарный расчёт (ID: {calc_id})")
                self.log_message(f"  Точек: {len(self.pipeline.x_km)}")
                if len(self.pipeline.P) > 0:
                    self.log_message(f"  Давление: {self.pipeline.P[0]/1e6:.3f} - {self.pipeline.P[-1]/1e6:.3f} МПа")
                self.log_message(f"  Скорость: {self.pipeline.v:.4f} м/с")

            else:  # Нестационарный
                # Загрузка нестационарного расчёта
                times, data_by_time = self.db_manager.get_unsteady_data(calc_id)

                if not times:
                    messagebox.showerror("Ошибка", "Данные не найдены")
                    return

                # Создаём новый объект PipelineFlow
                self.pipeline = PipelineFlow()

                # Восстанавливаем данные
                self.pipeline.t_history = times
                self.pipeline.p_history = []
                self.pipeline.v_history = []

                for t, rows in data_by_time:
                    if len(self.pipeline.p_history) == 0:  # Первая итерация
                        self.pipeline.x_km = np.array([row[0] for row in rows])
                        self.pipeline.x_m = np.array([row[1] for row in rows])

                    p_array = np.array([row[2] for row in rows])
                    v_array = np.array([row[3] for row in rows])

                    self.pipeline.p_history.append(p_array)
                    self.pipeline.v_history.append(v_array)

                # Устанавливаем текущее и оригинальное состояние
                if self.pipeline.p_history:
                    # Первый временной слой = стационарное состояние
                    self.pipeline.P_original = self.pipeline.p_history[0].copy()
                    self.pipeline.v_arr_original = self.pipeline.v_history[0].copy()

                    # Текущее состояние = последний временной слой
                    self.pipeline.P = self.pipeline.p_history[-1].copy()
                    self.pipeline.v_arr = self.pipeline.v_history[-1].copy()
                    self.pipeline.v = self.pipeline.v_arr[0] if len(self.pipeline.v_arr) > 0 else 0

                    self.pipeline.stationary_calculated = True

                    # Восстанавливаем dx
                    if len(self.pipeline.x_km) > 1:
                        self.pipeline.dx = self.pipeline.x_km[1] - self.pipeline.x_km[0]

                    # Восстанавливаем параметры
                    self.pipeline.rho = c.RO20 * (1 - 0.0008 * (c.TC - 20))
                    self.pipeline.nu = self.pipeline.get_kinematic_viscosity(c.T, c.VISCOSITY_20, c.VISCOSITY_50)
                    self.pipeline.epsilon = c.ABS_ROUGHTNESS / c.INTERNAL_DIAMETER

                self.log_message(f"\n✓ Загружен нестационарный расчёт (ID: {calc_id})")
                self.log_message(f"  Точек: {len(self.pipeline.x_km)}")
                self.log_message(f"  Временных слоёв: {len(times)}")
                if times:
                    self.log_message(f"  Время: {times[0]:.2f} - {times[-1]:.2f} с")

            parent_window.destroy()
            messagebox.showinfo("Успех", "Расчёт загружен из базы данных!")

            # Автоматически обновляем график после загрузки
            self.update_static_plot()

        except Exception as e:
            messagebox.showerror("Ошибка", f"Произошла ошибка: {e}")
            import traceback
            self.log_message(f"Трассировка ошибки:\n{traceback.format_exc()}")

    def show_db_table(self, tree):
        """Показать таблицу данных выбранного расчёта"""

        selected = tree.selection()
        if not selected:
            messagebox.showwarning("Предупреждение", "Выберите расчёт")
            return

        item = tree.item(selected[0])
        calc_id = item['values'][0]
        calc_type = item['values'][2]

        # Создание окна таблицы
        table_window = tk.Toplevel(self.root)
        table_window.title(f"Данные расчёта ID: {calc_id}")
        table_window.geometry("900x600")

        # Frame для таблицы
        frame = ttk.Frame(table_window)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Scrollbars
        vsb = ttk.Scrollbar(frame, orient="vertical")
        hsb = ttk.Scrollbar(frame, orient="horizontal")

        try:
            if calc_type == "Стационарный":
                # Таблица стационарных данных
                columns = ('x_km', 'P_MPa', 'v_ms')
                data_tree = ttk.Treeview(frame, columns=columns, show='headings',
                                         yscrollcommand=vsb.set,
                                         xscrollcommand=hsb.set)

                data_tree.heading('x_km', text='x, км')
                data_tree.heading('P_MPa', text='P, МПа')
                data_tree.heading('v_ms', text='v, м/с')

                data_tree.column('x_km', width=200, anchor='center')
                data_tree.column('P_MPa', width=200, anchor='center')
                data_tree.column('v_ms', width=200, anchor='center')

                # Получение данных через DatabaseManager
                rows = self.db_manager.get_stationary_data(calc_id)
                for row in rows:
                    data_tree.insert('', tk.END, values=(
                        f'{row[0]:.3f}',
                        f'{row[2]/1e6:.3f}',  # Преобразование Па в МПа
                        f'{row[3]:.4f}'
                    ))

            else:  # Нестационарный
                columns = ('time_s', 'x_km', 'P_MPa', 'v_ms')
                data_tree = ttk.Treeview(frame, columns=columns, show='headings',
                                         yscrollcommand=vsb.set,
                                         xscrollcommand=hsb.set)

                data_tree.heading('time_s', text='t, с')
                data_tree.heading('x_km', text='x, км')
                data_tree.heading('P_MPa', text='P, МПа')
                data_tree.heading('v_ms', text='v, м/с')

                data_tree.column('time_s', width=150, anchor='center')
                data_tree.column('x_km', width=150, anchor='center')
                data_tree.column('P_MPa', width=150, anchor='center')
                data_tree.column('v_ms', width=150, anchor='center')

                # Получение данных через DatabaseManager
                times, data_by_time = self.db_manager.get_unsteady_data(calc_id)
                for t, rows in data_by_time:
                    for row in rows:
                        data_tree.insert('', tk.END, values=(
                            f'{t:.2f}',
                            f'{row[0]:.3f}',
                            f'{row[2]/1e6:.3f}',  # Преобразование Па в МПа
                            f'{row[3]:.4f}'
                        ))

            vsb.config(command=data_tree.yview)
            hsb.config(command=data_tree.xview)

            data_tree.grid(row=0, column=0, sticky='nsew')
            vsb.grid(row=0, column=1, sticky='ns')
            hsb.grid(row=1, column=0, sticky='ew')

            frame.grid_rowconfigure(0, weight=1)
            frame.grid_columnconfigure(0, weight=1)

            # Информация
            info_label = ttk.Label(table_window,
                                   text=f"Всего записей: {data_tree.get_children().__len__()}",
                                   font=('Arial', 10))
            info_label.pack(pady=5)

            # Кнопка экспорта
            export_btn = ttk.Button(table_window, text="Экспорт в CSV",
                                    command=lambda: self.export_db_to_csv(calc_id, calc_type))
            export_btn.pack(pady=5)

        except Exception as e:
            messagebox.showerror("Ошибка БД", f"Не удалось загрузить данные: {e}")
            table_window.destroy()

    def delete_from_database(self, tree):
        """Удаление выбранного расчёта из БД"""

        selected = tree.selection()
        if not selected:
            messagebox.showwarning("Предупреждение", "Выберите расчёт для удаления")
            return

        item = tree.item(selected[0])
        calc_id = item['values'][0]

        # Подтверждение
        confirm = messagebox.askyesno("Подтверждение", f"Удалить расчёт ID: {calc_id}?")
        if not confirm:
            return

        try:
            # Удаление через DatabaseManager
            self.db_manager.delete_calculation(calc_id)

            # Удаление из списка
            tree.delete(selected[0])

            self.log_message(f"Расчёт ID: {calc_id} удалён из базы данных")
            messagebox.showinfo("Успех", "Расчёт удалён")

        except Exception as e:
            messagebox.showerror("Ошибка БД", f"Не удалось удалить данные: {e}")

    def export_db_to_csv(self, calc_id, calc_type):
        """Экспорт данных из БД в CSV"""

        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"calculation_{calc_id}.csv"
        )

        if not filename:
            return

        try:
            # Экспорт через DatabaseManager
            self.db_manager.export_to_csv(calc_id, calc_type, filename)
            messagebox.showinfo("Успех", f"Данные экспортированы в {filename}")

        except Exception as e:
            messagebox.showerror("Ошибка экспорта", str(e))

    def clear_database(self):
        """Полная очистка базы данных"""

        confirm = messagebox.askyesno("Удалить ВСЕ расчёты из базы данных?\n Это действие необратимо!")
        if not confirm:
            return

        try:
            # Очистка через DatabaseManager
            self.db_manager.clear_database()
            self.log_message("База данных полностью очищена")
            messagebox.showinfo("Успех", "База данных очищена")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось очистить БД: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = PipelineGUI(root)
    root.mainloop()
