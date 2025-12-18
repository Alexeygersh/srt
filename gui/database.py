import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import numpy as np

import constants as c


class DatabaseWindow:
    """Окно для работы с базой данных"""

    def __init__(self, root, pipeline, db_manager, log_callback=None):
        self.root = root
        self.pipeline = pipeline
        self.db_manager = db_manager
        self.log_callback = log_callback
        self.window = None
        self.tree = None

    def open(self):
        """Открытие окна базы данных"""
        db_name = 'pipeline_results.db'

        if not os.path.exists(db_name):
            messagebox.showinfo("Информация", "База данных пуста. Сначала сохраните расчёты.")
            return

        # Создание окна
        self.window = tk.Toplevel(self.root)
        self.window.title("База данных расчётов")
        self.window.geometry("1000x600")

        # Верхняя панель - список расчётов
        list_frame = ttk.LabelFrame(self.window, text="Сохранённые расчёты", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Frame для Treeview
        tree_frame = ttk.Frame(list_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")

        # Treeview
        columns = ('id', 'timestamp', 'type', 'points', 'description')
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings',
                                 yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)

        # Заголовки
        self.tree.heading('id', text='ID')
        self.tree.heading('timestamp', text='Дата и время')
        self.tree.heading('type', text='Тип')
        self.tree.heading('points', text='Точек')
        self.tree.heading('description', text='Описание')

        # Ширины колонок
        self.tree.column('id', width=50, anchor='center')
        self.tree.column('timestamp', width=150, anchor='center')
        self.tree.column('type', width=120, anchor='center')
        self.tree.column('points', width=80, anchor='center')
        self.tree.column('description', width=500, anchor='w')

        # Размещение
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')

        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # Загрузка данных из БД
        self._load_calculations()

        # Нижняя панель - кнопки управления
        self._create_control_panel()

    def _load_calculations(self):
        """Загрузка списка расчётов из БД"""
        try:
            calculations = self.db_manager.get_all_calculations()

            for calc in calculations:
                calc_id, timestamp, calc_type, num_points, description = calc
                type_display = "Стационарный" if calc_type == "stationary" else "Нестационарный"
                self.tree.insert('', tk.END, values=(
                    calc_id, timestamp, type_display, num_points, description
                ))

            if not calculations:
                messagebox.showinfo("Информация", "База данных пуста")
                self.window.destroy()

        except Exception as e:
            messagebox.showerror("Ошибка БД", f"Не удалось загрузить данные: {e}")
            self.window.destroy()

    def _create_control_panel(self):
        """Создание панели управления"""
        control_frame = ttk.Frame(self.window)
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        buttons_config = [
            ("Загрузить", self._load_and_visualize, 30),
            ("Показать таблицу данных", self._show_table, 30),
            ("Удалить выбранный", self._delete_calculation, 30),
        ]

        for text, command, width in buttons_config:
            ttk.Button(control_frame, text=text, command=command, width=width).pack(side=tk.LEFT, padx=5)

        ttk.Button(control_frame, text="Очистить всю БД",
                   command=self._clear_database,
                   width=20).pack(side=tk.RIGHT, padx=5)

        ttk.Button(control_frame, text="Закрыть",
                   command=self.window.destroy,
                   width=15).pack(side=tk.RIGHT, padx=5)

    def _load_and_visualize(self):
        """Загрузка выбранного расчёта"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Предупреждение", "Выберите расчёт для загрузки")
            return

        item = self.tree.item(selected[0])
        calc_id = item['values'][0]
        calc_type = item['values'][2]

        try:
            if calc_type == "Стационарный":
                self._load_stationary(calc_id)
            else:
                self._load_unsteady(calc_id)

            self.window.destroy()
            messagebox.showinfo("Успех", "Расчёт загружен из базы данных!")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Произошла ошибка: {e}")
            import traceback
            if self.log_callback:
                self.log_callback(f"Трассировка ошибки:\n{traceback.format_exc()}")

    def _load_stationary(self, calc_id):
        """Загрузка стационарного расчёта"""
        rows = self.db_manager.get_stationary_data(calc_id)

        if not rows:
            raise ValueError("Данные не найдены")

        # Создаём новый объект PipelineFlow
        from calc import PipelineFlow
        self.pipeline.__class__ = PipelineFlow
        self.pipeline.__init__()

        # Восстанавливаем данные
        self.pipeline.x_km = np.array([row[0] for row in rows])
        self.pipeline.x_m = np.array([row[1] for row in rows])
        self.pipeline.P = np.array([row[2] for row in rows])
        self.pipeline.v_arr = np.array([row[3] for row in rows])

        # Восстанавливаем атрибуты
        self.pipeline.v = self.pipeline.v_arr[0] if len(self.pipeline.v_arr) > 0 else 0
        self.pipeline.stationary_calculated = True

        if len(self.pipeline.x_km) > 1:
            self.pipeline.dx = self.pipeline.x_km[1] - self.pipeline.x_km[0]

        # Сохраняем оригинальные стационарные данные
        self.pipeline.P_original = self.pipeline.P.copy()
        self.pipeline.v_arr_original = self.pipeline.v_arr.copy()

        # Восстанавливаем параметры
        self.pipeline.rho = c.RO20 * (1 - 0.0008 * (c.TC - 20))
        self.pipeline.nu = self.pipeline.get_kinematic_viscosity(
            c.T, c.VISCOSITY_20, c.VISCOSITY_50
        )
        self.pipeline.epsilon = c.ABS_ROUGHTNESS / c.INTERNAL_DIAMETER

        if len(self.pipeline.v_arr) > 0:
            self.pipeline.Re = self.pipeline.get_reynolds(
                self.pipeline.v, c.INTERNAL_DIAMETER, self.pipeline.nu
            )
            self.pipeline.lambda_ = self.pipeline.get_lambda(
                self.pipeline.Re, self.pipeline.epsilon
            )

        if self.log_callback:
            self.log_callback(f"\n✓ Загружен стационарный расчёт (ID: {calc_id})")
            self.log_callback(f"  Точек: {len(self.pipeline.x_km)}")
            if len(self.pipeline.P) > 0:
                self.log_callback(
                    f"  Давление: {self.pipeline.P[0]/1e6:.3f} - "
                    f"{self.pipeline.P[-1]/1e6:.3f} МПа"
                )
            self.log_callback(f"  Скорость: {self.pipeline.v:.4f} м/с")

    def _load_unsteady(self, calc_id):
        """Загрузка нестационарного расчёта"""
        times, data_by_time = self.db_manager.get_unsteady_data(calc_id)

        if not times:
            raise ValueError("Данные не найдены")

        # Создаём новый объект PipelineFlow
        from calc import PipelineFlow
        self.pipeline.__class__ = PipelineFlow
        self.pipeline.__init__()

        # Восстанавливаем данные
        self.pipeline.t_history = times
        self.pipeline.p_history = []
        self.pipeline.v_history = []

        for t, rows in data_by_time:
            if len(self.pipeline.p_history) == 0:
                self.pipeline.x_km = np.array([row[0] for row in rows])
                self.pipeline.x_m = np.array([row[1] for row in rows])

            p_array = np.array([row[2] for row in rows])
            v_array = np.array([row[3] for row in rows])

            self.pipeline.p_history.append(p_array)
            self.pipeline.v_history.append(v_array)

        # Устанавливаем текущее и оригинальное состояние
        if self.pipeline.p_history:
            self.pipeline.P_original = self.pipeline.p_history[0].copy()
            self.pipeline.v_arr_original = self.pipeline.v_history[0].copy()

            self.pipeline.P = self.pipeline.p_history[-1].copy()
            self.pipeline.v_arr = self.pipeline.v_history[-1].copy()
            self.pipeline.v = self.pipeline.v_arr[0] if len(self.pipeline.v_arr) > 0 else 0

            self.pipeline.stationary_calculated = True

            if len(self.pipeline.x_km) > 1:
                self.pipeline.dx = self.pipeline.x_km[1] - self.pipeline.x_km[0]

            # Восстанавливаем параметры
            self.pipeline.rho = c.RO20 * (1 - 0.0008 * (c.TC - 20))
            self.pipeline.nu = self.pipeline.get_kinematic_viscosity(
                c.T, c.VISCOSITY_20, c.VISCOSITY_50
            )
            self.pipeline.epsilon = c.ABS_ROUGHTNESS / c.INTERNAL_DIAMETER

        if self.log_callback:
            self.log_callback(f"\nЗагружен нестационарный расчёт (ID: {calc_id})")
            self.log_callback(f"  Точек: {len(self.pipeline.x_km)}")
            self.log_callback(f"  Временных слоёв: {len(times)}")
            if times:
                self.log_callback(f"  Время: {times[0]:.2f} - {times[-1]:.2f} с")

    def _show_table(self):
        """Показать таблицу данных выбранного расчёта"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Предупреждение", "Выберите расчёт")
            return

        item = self.tree.item(selected[0])
        calc_id = item['values'][0]
        calc_type = item['values'][2]

        # Создаём окно таблицы
        table_window = tk.Toplevel(self.root)
        table_window.title(f"Данные расчёта ID: {calc_id}")
        table_window.geometry("900x600")

        try:
            if calc_type == "Стационарный":
                self._show_stationary_table(table_window, calc_id)
            else:
                self._show_unsteady_table(table_window, calc_id)

        except Exception as e:
            messagebox.showerror("Ошибка БД", f"Не удалось загрузить данные: {e}")
            table_window.destroy()

    def _show_stationary_table(self, parent, calc_id):
        """Таблица стационарных данных"""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Scrollbars
        vsb = ttk.Scrollbar(frame, orient="vertical")
        hsb = ttk.Scrollbar(frame, orient="horizontal")

        # Treeview
        columns = ('x_km', 'P_MPa', 'v_ms')
        data_tree = ttk.Treeview(frame, columns=columns, show='headings',
                                 yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.config(command=data_tree.yview)
        hsb.config(command=data_tree.xview)

        # Заголовки
        data_tree.heading('x_km', text='x, км')
        data_tree.heading('P_MPa', text='P, МПа')
        data_tree.heading('v_ms', text='v, м/с')

        # Ширины
        data_tree.column('x_km', width=200, anchor='center')
        data_tree.column('P_MPa', width=200, anchor='center')
        data_tree.column('v_ms', width=200, anchor='center')

        # Получение данных
        rows = self.db_manager.get_stationary_data(calc_id)
        for row in rows:
            data_tree.insert('', tk.END, values=(
                f'{row[0]:.3f}',
                f'{row[2]/1e6:.3f}',
                f'{row[3]:.4f}'
            ))

        # Размещение
        data_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')

        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        # Информация
        info_label = ttk.Label(parent, text=f"Всего записей: {len(rows)}", font=('Arial', 10))
        info_label.pack(pady=5)

        # Кнопка экспорта
        ttk.Button(parent, text="Экспорт в CSV",
                   command=lambda: self._export_to_csv(calc_id, "Стационарный")).pack(pady=5)

    def _show_unsteady_table(self, parent, calc_id):
        """Таблица нестационарных данных"""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Scrollbars
        vsb = ttk.Scrollbar(frame, orient="vertical")
        hsb = ttk.Scrollbar(frame, orient="horizontal")

        # Treeview
        columns = ('time_s', 'x_km', 'P_MPa', 'v_ms')
        data_tree = ttk.Treeview(frame, columns=columns, show='headings',
                                 yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.config(command=data_tree.yview)
        hsb.config(command=data_tree.xview)

        # Заголовки
        data_tree.heading('time_s', text='t, с')
        data_tree.heading('x_km', text='x, км')
        data_tree.heading('P_MPa', text='P, МПа')
        data_tree.heading('v_ms', text='v, м/с')

        # Ширины
        data_tree.column('time_s', width=150, anchor='center')
        data_tree.column('x_km', width=150, anchor='center')
        data_tree.column('P_MPa', width=150, anchor='center')
        data_tree.column('v_ms', width=150, anchor='center')

        # Получение данных
        times, data_by_time = self.db_manager.get_unsteady_data(calc_id)
        total_rows = 0
        for t, rows in data_by_time:
            for row in rows:
                data_tree.insert('', tk.END, values=(
                    f'{t:.2f}',
                    f'{row[0]:.3f}',
                    f'{row[2]/1e6:.3f}',
                    f'{row[3]:.4f}'
                ))
                total_rows += 1

        # Размещение
        data_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')

        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        # Информация
        info_label = ttk.Label(parent,
                               text=f"Всего записей: {total_rows} (временных слоёв: {len(times)})",
                               font=('Arial', 10))
        info_label.pack(pady=5)

        # Кнопка экспорта
        ttk.Button(parent, text="Экспорт в CSV",
                   command=lambda: self._export_to_csv(calc_id, "Нестационарный")).pack(pady=5)

    def _delete_calculation(self):
        """Удаление выбранного расчёта из БД"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Предупреждение", "Выберите расчёт для удаления")
            return

        item = self.tree.item(selected[0])
        calc_id = item['values'][0]

        confirm = messagebox.askyesno("Подтверждение", f"Удалить расчёт ID: {calc_id}?")
        if not confirm:
            return

        try:
            self.db_manager.delete_calculation(calc_id)
            self.tree.delete(selected[0])

            if self.log_callback:
                self.log_callback(f"Расчёт ID: {calc_id} удалён из базы данных")

            messagebox.showinfo("Успех", "Расчёт удалён")

        except Exception as e:
            messagebox.showerror("Ошибка БД", f"Не удалось удалить данные: {e}")

    def _clear_database(self):
        """Полная очистка базы данных"""
        confirm = messagebox.askyesno(
            "Удалить ВСЕ расчёты из базы данных?\nЭто действие необратимо!"
        )
        if not confirm:
            return

        try:
            self.db_manager.clear_database()

            # Очищаем дерево
            for item in self.tree.get_children():
                self.tree.delete(item)

            if self.log_callback:
                self.log_callback("База данных полностью очищена")

            messagebox.showinfo("Успех", "База данных очищена")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось очистить БД: {e}")

    def _export_to_csv(self, calc_id, calc_type):
        """Экспорт данных из БД в CSV"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"calculation_{calc_id}.csv"
        )

        if not filename:
            return

        try:
            self.db_manager.export_to_csv(calc_id, calc_type, filename)
            messagebox.showinfo("Успех", f"Данные экспортированы в {filename}")

        except Exception as e:
            messagebox.showerror("Ошибка экспорта", str(e))
