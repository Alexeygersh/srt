import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading

from .plots import PlotWindow
from .animation import AnimationWindow
from .database import DatabaseWindow

import constants as c
import db_manager as db
from calc import PipelineFlow


class PipelineGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Моделирование течения нефти в трубопроводе")
        self.root.geometry("800x800")

        # Основные объекты
        self.pipeline = PipelineFlow()
        self.db_manager = db.DatabaseManager()

        # Флаги состояния
        self.calculation_running = False
        self.stop_requested = False

        # Окна
        self.plot_window = None
        self.animation_window = None
        self.database_window = None

        # Создание интерфейса
        self.create_widgets()

    def create_widgets(self):
        """Создание всех элементов интерфейса"""
        self._create_parameters_panel()
        self._create_control_panel()
        self._create_log_panel()

    def _create_parameters_panel(self):
        """Создание панели параметров"""
        params_frame = ttk.LabelFrame(self.root, text="Параметры моделирования", padding=10)
        params_frame.pack(fill=tk.X, padx=10, pady=5)

        # Левая колонка - Параметры трубы
        pipe_frame = ttk.Frame(params_frame)
        pipe_frame.grid(row=0, column=0, padx=10, sticky='n')

        ttk.Label(pipe_frame, text="ТРУБА", font=('Arial', 10, 'bold')).grid(
            row=0, column=0, columnspan=2, pady=5
        )

        ttk.Label(pipe_frame, text="Длина, км:").grid(row=1, column=0, sticky='w', pady=2)
        self.length_var = tk.StringVar(value=str(c.XN_KM - c.X0_KM))
        ttk.Entry(pipe_frame, textvariable=self.length_var, width=15).grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(pipe_frame, text="Диаметр (внеш.), мм:").grid(row=2, column=0, sticky='w', pady=2)
        self.diameter_var = tk.StringVar(value=str(c.EXTERNAL_DIAMETER_MM))
        ttk.Entry(pipe_frame, textvariable=self.diameter_var, width=15).grid(row=2, column=1, padx=5, pady=2)

        ttk.Label(pipe_frame, text="Толщина стенки, мм:").grid(row=3, column=0, sticky='w', pady=2)
        self.thickness_var = tk.StringVar(value=str(c.WALL_THICKNESS_MM))
        ttk.Entry(pipe_frame, textvariable=self.thickness_var, width=15).grid(row=3, column=1, padx=5, pady=2)

        ttk.Label(pipe_frame, text="Шероховатость, мм:").grid(row=4, column=0, sticky='w', pady=2)
        self.roughness_var = tk.StringVar(value=str(c.ABS_ROUGHTNESS_MM))
        ttk.Entry(pipe_frame, textvariable=self.roughness_var, width=15).grid(row=4, column=1, padx=5, pady=2)

        # Средняя колонка - Параметры нефти и давления
        oil_frame = ttk.Frame(params_frame)
        oil_frame.grid(row=0, column=1, padx=10, sticky='n')

        ttk.Label(oil_frame, text="НЕФТЬ И ДАВЛЕНИЕ", font=('Arial', 10, 'bold')).grid(row=0, column=0, columnspan=2, pady=5)

        ttk.Label(oil_frame, text="Температура, °C:").grid(row=1, column=0, sticky='w', pady=2)
        self.temp_var = tk.StringVar(value=str(c.TC))
        ttk.Entry(oil_frame, textvariable=self.temp_var, width=15).grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(oil_frame, text="Давление вход, МПа:").grid(row=2, column=0, sticky='w', pady=2)
        self.p_inlet_var = tk.StringVar(value=str(c.P_INITIAL_MPA))
        ttk.Entry(oil_frame, textvariable=self.p_inlet_var, width=15).grid(row=2, column=1, padx=5, pady=2)

        ttk.Label(oil_frame, text="Давление выход, МПа:").grid(row=3, column=0, sticky='w', pady=2)
        self.p_outlet_var = tk.StringVar(value=str(c.P_END_MPA))
        ttk.Entry(oil_frame, textvariable=self.p_outlet_var, width=15).grid(row=3, column=1, padx=5, pady=2)

        ttk.Label(oil_frame, text="Скорость звука, м/с:").grid(row=4, column=0, sticky='w', pady=2)
        self.sound_speed_var = tk.StringVar(value=str(c.SPEED_OF_SOUND))
        ttk.Entry(oil_frame, textvariable=self.sound_speed_var, width=15).grid(row=4, column=1, padx=5, pady=2)

        # Правая колонка - Параметры расчёта
        calc_frame = ttk.Frame(params_frame)
        calc_frame.grid(row=0, column=2, padx=10, sticky='n')

        ttk.Label(calc_frame, text="РАСЧЁТ", font=('Arial', 10, 'bold')).grid(row=0, column=0, columnspan=2, pady=5)

        ttk.Label(calc_frame, text="Шаг сетки, км:").grid(row=1, column=0, sticky='w', pady=2)
        self.dx_var = tk.StringVar(value=str(c.dx_km))
        ttk.Entry(calc_frame, textvariable=self.dx_var, width=15).grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(calc_frame, text="Метод расчёта λ:").grid(row=2, column=0, sticky='w', pady=2)
        self.lambda_method_var = tk.StringVar(value='auto')
        lambda_combo = ttk.Combobox(calc_frame, textvariable=self.lambda_method_var,
                                    values=['auto', 'stokes', 'ginzburg', 'blasius', 'altshul', 'shifrinson', 'colebrook'],
                                    state='readonly', width=13)
        lambda_combo.grid(row=2, column=1, padx=5, pady=2)

        ttk.Label(calc_frame, text="Шагов по времени:").grid(row=3, column=0, sticky='w', pady=2)
        self.time_steps_var = tk.StringVar(value="2000")
        ttk.Entry(calc_frame, textvariable=self.time_steps_var, width=15).grid(row=3, column=1, padx=5, pady=2)

        ttk.Label(calc_frame, text="Сохранять каждые:").grid(row=4, column=0, sticky='w', pady=2)
        self.store_every_var = tk.StringVar(value="5")
        ttk.Entry(calc_frame, textvariable=self.store_every_var, width=15).grid(row=4, column=1, padx=5, pady=2)

        self.parallel_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(calc_frame, text="Параллельные вычисления",
                        variable=self.parallel_var).grid(row=5, column=0, columnspan=2, pady=2, sticky='w')

    def _create_control_panel(self):
        """Создание панели управления"""
        control_frame = ttk.Frame(self.root)
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        # Левая часть - Кнопки расчёта
        buttons_frame = ttk.LabelFrame(control_frame, text="Управление", padding=10)
        buttons_frame.pack(side=tk.LEFT, padx=5)

        ttk.Button(buttons_frame, text="▶ Стационарный расчёт",
                   command=self.run_stationary, width=28).grid(row=0, column=0, padx=5, pady=5)

        ttk.Button(buttons_frame, text="▶ Нестационарный расчёт",
                   command=self.run_unsteady_animated, width=28).grid(row=1, column=0, padx=5, pady=5)

        ttk.Separator(buttons_frame, orient='horizontal').grid(row=2, column=0, sticky='ew', pady=10)

        ttk.Button(buttons_frame, text="Открыть визуализацию",
                   command=self.open_plot_window, width=28).grid(row=3, column=0, padx=5, pady=5)

        ttk.Button(buttons_frame, text="Показать таблицу",
                   command=self.show_table, width=28).grid(row=4, column=0, padx=5, pady=5)

        ttk.Separator(buttons_frame, orient='horizontal').grid(row=5, column=0, sticky='ew', pady=10)

        ttk.Button(buttons_frame, text="Сохранить в БД",
                   command=self.save_to_db, width=28).grid(row=6, column=0, padx=5, pady=5)

        ttk.Button(buttons_frame, text="Загрузить из БД",
                   command=self.open_database_window, width=28).grid(row=7, column=0, padx=5, pady=5)

        # Правая часть - Граничные условия
        bc_frame = ttk.LabelFrame(control_frame,
                                  text="Граничные условия (нестационарный)", padding=10)
        bc_frame.pack(side=tk.LEFT, padx=5, fill=tk.BOTH, expand=True)

        ttk.Label(bc_frame, text="Тип:").grid(row=0, column=0, sticky='w', pady=2)
        self.bc_type_var = tk.StringVar(value='valve_closure')
        bc_combo = ttk.Combobox(bc_frame, textvariable=self.bc_type_var,
                                values=['valve_closure', 'pressure_inlet', 'pressure_outlet'],
                                state='readonly', width=20)
        bc_combo.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(bc_frame, text="Время изменения, с:").grid(row=1, column=0, sticky='w', pady=2)
        self.bc_time_var = tk.StringVar(value="0")
        ttk.Entry(bc_frame, textvariable=self.bc_time_var, width=22).grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(bc_frame, text="Новое значение:").grid(row=2, column=0, sticky='w', pady=2)
        self.bc_value_var = tk.StringVar(value="0")
        ttk.Entry(bc_frame, textvariable=self.bc_value_var, width=22).grid(row=2, column=1, padx=5, pady=2)

        ttk.Label(bc_frame, text="(МПа для давления)",
                  font=('Arial', 8, 'italic')).grid(row=3, column=1, sticky='w')

    def _create_log_panel(self):
        """Создание панели логов"""
        log_frame = ttk.LabelFrame(self.root, text="Лог расчётов", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.log_text = scrolledtext.ScrolledText(
            log_frame, height=15, state='normal',
            wrap=tk.WORD, font=('Consolas', 9)
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def log_message(self, message):
        """Добавление сообщения в лог"""
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + '\n')
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        self.root.update()

    # ============================================================
    # Методы расчётов
    # ============================================================

    def requires_stationary_calculation(func):
        """Декоратор для методов, требующих выполненного стационарного расчёта"""
        def wrapper(self, *args, **kwargs):
            if not self.pipeline.stationary_calculated:
                messagebox.showwarning("Предупреждение", "Сначала выполните стационарный расчёт!")
                return
            return func(self, *args, **kwargs)
        return wrapper

    def update_constants(self):
        """Обновление констант из полей ввода"""
        try:
            total_length = float(self.length_var.get())
            c.XN_KM = total_length

            c.EXTERNAL_DIAMETER_MM = float(self.diameter_var.get())
            c.WALL_THICKNESS_MM = float(self.thickness_var.get())
            c.Delta_mm = float(self.roughness_var.get())
            c.EXTERNAL_DIAMETER = c.EXTERNAL_DIAMETER_MM / 1000
            c.delta = c.WALL_THICKNESS_MM / 1000
            c.INTERNAL_DIAMETER = c.EXTERNAL_DIAMETER - 2 * c.delta
            c.Delta = c.Delta_mm / 1000
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
            self.pipeline = PipelineFlow()
            self.pipeline.calculate_stationary(lambda_method=lambda_method, verbose=False)

            self.log_message(f"Плотность при {c.TC}°C: ρ = {self.pipeline.rho:.2f} кг/м³")
            self.log_message(f"Кинематическая вязкость: ν = {self.pipeline.nu*1e6:.2f} сСт")
            self.log_message(f"Скорость нефти: v = {self.pipeline.v:.4f} м/с")
            self.log_message(f"Число Рейнольдса: Re = {self.pipeline.Re:.0f}")
            self.log_message(f"Коэффициент сопротивления: λ = {self.pipeline.lambda_:.5f}")
            self.log_message(f"Число точек сетки: {len(self.pipeline.x_km)}")
            self.log_message("Расчёт завершён успешно!")
            self.log_message("=" * 60)

            # Автоматическое открытие графика
            if self.plot_window:
                self.plot_window.update_plot()

        except Exception as e:
            self.log_message(f"ОШИБКА: {e}")
            messagebox.showerror("Ошибка расчёта", str(e))

    @requires_stationary_calculation
    def run_unsteady_animated(self):
        """Запуск нестационарного расчёта с анимацией"""

        # Сохраняем оригинальные данные
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
            if not self.animation_window:
                self.animation_window = AnimationWindow(self.root, self.pipeline)

            self.animation_window.open()
            self.animation_window.set_stop_command(self.stop_calculation)

            self.animation_window.parent_gui = self

            # Запуск в отдельном потоке
            thread = threading.Thread(
                target=self._run_unsteady_with_animation,
                args=(num_steps, store_every, bc_type, bc_time, bc_value, lambda_method, use_parallel),
                daemon=True
            )
            thread.start()

        except ValueError as e:
            messagebox.showerror("Ошибка", f"Неверный формат данных: {e}")

    def _run_unsteady_with_animation(self, num_steps, store_every, bc_type, bc_time, bc_value, lambda_method, use_parallel):
        """Выполнение нестационарного расчёта с динамической анимацией"""
        try:
            self.calculation_running = True
            self.stop_requested = False

            # Сбрасываем счётчик кадров в окне анимации
            if self.animation_window:
                self.animation_window.frame_counter = 0

            # Функция обратной связи
            def update_progress_and_plot(current, total, current_time, p_array, v_array):
                if self.stop_requested:
                    return False

                percent = 100.0 * current / total

                # Обновляем график через окно анимации
                if self.animation_window:
                    should_continue = self.animation_window.update_plot(
                        current_time, p_array, v_array, percent
                    )
                    return should_continue

                return True

            # запуск расчёта с коллбэком
            # Уменьшаем частоту сохранения для расчёта, но окно анимации само решит когда обновлять
            effective_store_every = max(1, store_every // 2)  # Увеличиваем частоту обновления callback

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

            def finalize_ui():
                if self.animation_window:
                    self.animation_window.finalize(success=True)

                self.log_message("Расчёт завершён успешно!")
                self.log_message(f"Сохранено {len(self.pipeline.t_history)} временных слоёв")
                self.log_message("=" * 60)

            self.root.after(0, finalize_ui)

        except Exception as e:
            self.calculation_running = False

            error_msg = str(e)
            import traceback
            error_trace = traceback.format_exc()

            self.log_message(f"ОШИБКА: {error_msg}")
            self.log_message(f"Трассировка:\n{error_trace}")

            def finalize_error():
                if self.animation_window:
                    self.animation_window.finalize(success=False)
                messagebox.showerror("Ошибка расчёта", f"{error_msg}\n\nПроверьте лог для подробностей")

            self.root.after(0, finalize_error)

        finally:
            self.calculation_running = False

            # Восстанавливаем стационарные данные
            if hasattr(self.pipeline, 'P_original') and self.pipeline.P_original is not None:
                self.pipeline.P = self.pipeline.P_original.copy()
                self.pipeline.v_arr = self.pipeline.v_arr_original.copy()
                self.log_message("Стационарные данные восстановлены")

    def stop_calculation(self):
        """Остановка расчёта"""
        if self.calculation_running:
            self.stop_requested = True
            self.log_message("Запрос на остановку расчёта...")

    # ============================================================
    # Методы работы с окнами
    # ============================================================

    def open_plot_window(self):
        """Открытие окна с графиками"""
        # если стационарный расчёт выполнен, но атрибут не установлен
        if not self.pipeline.stationary_calculated:
            # Дополнительная проверка: есть ли данные расчёта
            if self.pipeline.P is not None and self.pipeline.v is not None:
                # Принудительно устанавливаем флаг
                self.pipeline.stationary_calculated = True
                self.log_message("Стационарные данные обнаружены")
            else:
                messagebox.showwarning("Предупреждение", "Сначала выполните стационарный расчёт!")
                return

        if not self.plot_window:
            self.plot_window = PlotWindow(self.root, self.pipeline)

        self.plot_window.open()

    def open_database_window(self):
        """Открытие окна базы данных"""
        if not self.database_window:
            self.database_window = DatabaseWindow(
                self.root, self.pipeline, self.db_manager,
                log_callback=self.log_message
            )

        self.database_window.open()

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

        from .table import TableWindow
        table_window = TableWindow(self.root, self.pipeline)
        table_window.open()
