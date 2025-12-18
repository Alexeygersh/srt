import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv


class TableWindow:
    """Окно для отображения таблиц результатов"""

    def __init__(self, root, pipeline):
        self.root = root
        self.pipeline = pipeline
        self.window = None

    def open(self):
        """Открытие окна с таблицами"""
        if not self.pipeline.stationary_calculated:
            messagebox.showwarning("Предупреждение", "Сначала выполните расчёт!")
            return

        # Создание нового окна
        self.window = tk.Toplevel(self.root)
        self.window.title("Таблица результатов")
        self.window.geometry("900x700")

        # Notebook для вкладок
        notebook = ttk.Notebook(self.window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # вкладка 1 стац расчет
        self._create_stationary_tab(notebook)

        # вкладка 2
        if self.pipeline.p_history and len(self.pipeline.p_history) > 0:
            self._create_unsteady_tab(notebook)

    def _create_stationary_tab(self, notebook):
        """Создание вкладки стационарного расчёта"""
        stationary_frame = ttk.Frame(notebook)
        notebook.add(stationary_frame, text="Стационарный расчёт")

        # Frame для Treeview
        tree_frame = ttk.Frame(stationary_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")

        # Treeview
        columns = ('x_km', 'P_MPa', 'v_ms')
        tree_stat = ttk.Treeview(tree_frame, columns=columns, show='headings',
                                 yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.config(command=tree_stat.yview)
        hsb.config(command=tree_stat.xview)

        # Заголовки
        tree_stat.heading('x_km', text='x, км')
        tree_stat.heading('P_MPa', text='P, МПа')
        tree_stat.heading('v_ms', text='v, м/с')

        # Ширины
        tree_stat.column('x_km', width=200, anchor='center')
        tree_stat.column('P_MPa', width=200, anchor='center')
        tree_stat.column('v_ms', width=200, anchor='center')

        # Используем ОРИГИНАЛЬНЫЕ стационарные данные
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

        # Размещение
        tree_stat.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')

        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # Информация
        info_label = ttk.Label(stationary_frame,
                               text=f"Всего точек: {len(self.pipeline.x_km)}",
                               font=('Arial', 10))
        info_label.pack(pady=5)

        # Кнопка экспорта
        ttk.Button(stationary_frame, text="Экспорт в CSV",
                   command=self.export_stationary_to_csv).pack(pady=5)

    def _create_unsteady_tab(self, notebook):
        """Создание вкладки нестационарного расчёта"""
        unsteady_frame = ttk.Frame(notebook)
        notebook.add(unsteady_frame, text="Нестационарный расчёт")

        # Панель выбора временного слоя
        control_frame = ttk.Frame(unsteady_frame)
        control_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(control_frame, text="Временной слой:",
                  font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=5)

        # Список временных точек
        time_var = tk.StringVar()
        time_values = [f"t = {t:.2f} с" for t in self.pipeline.t_history]
        time_combo = ttk.Combobox(control_frame, textvariable=time_var, values=time_values, state='readonly', width=20)
        time_combo.pack(side=tk.LEFT, padx=5)
        time_combo.current(0)

        # Информация о выбранном слое
        info_label = ttk.Label(control_frame, text="", font=('Arial', 9))
        info_label.pack(side=tk.LEFT, padx=20)

        # Frame для Treeview
        tree_frame = ttk.Frame(unsteady_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")

        # Treeview
        columns = ('x_km', 'P_MPa', 'v_ms')
        tree_unst = ttk.Treeview(tree_frame, columns=columns, show='headings',
                                 yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.config(command=tree_unst.yview)
        hsb.config(command=tree_unst.xview)

        # Заголовки
        tree_unst.heading('x_km', text='x, км')
        tree_unst.heading('P_MPa', text='P, МПа')
        tree_unst.heading('v_ms', text='v, м/с')

        # Ширина
        tree_unst.column('x_km', width=200, anchor='center')
        tree_unst.column('P_MPa', width=200, anchor='center')
        tree_unst.column('v_ms', width=200, anchor='center')

        # Размещение
        tree_unst.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')

        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

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
                # Обновляем информацию
            t = self.pipeline.t_history[time_idx]
            info_label.config(
                text=f"Слой {time_idx+1}/{len(self.pipeline.t_history)} | Точек: {len(self.pipeline.x_km)}")

        # Связываем выбор с обновлением таблицы
        time_combo.bind('<<ComboboxSelected>>', update_unsteady_table)

        # Заполняем начальными данными
        update_unsteady_table()

        # Кнопки экспорта
        export_frame = ttk.Frame(unsteady_frame)
        export_frame.pack(pady=5)

        ttk.Button(export_frame, text="Экспорт текущего слоя в CSV",
                   command=lambda: self.export_current_unsteady_to_csv(
                    time_combo.current())).pack(side=tk.LEFT, padx=5)

        ttk.Button(export_frame, text="Экспорт всех слоёв в CSV",
                   command=self.export_all_unsteady_to_csv).pack(side=tk.LEFT, padx=5)

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

    def export_current_unsteady_to_csv(self, time_idx):
        """Экспорт текущего временного слоя нестационарного расчёта в CSV"""
        if time_idx < 0 or time_idx >= len(self.pipeline.p_history):
            messagebox.showwarning("Предупреждение", "Выберите временной слой")
            return

        t = self.pipeline.t_history[time_idx]

        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"unsteady_t_{t:.2f}s.csv"
        )

        if not filename:
            return

        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['x_km', 'P_MPa', 'v_ms'])

                p_array = self.pipeline.p_history[time_idx]
                v_array = self.pipeline.v_history[time_idx]

                for i in range(len(self.pipeline.x_km)):
                    writer.writerow([
                        self.pipeline.x_km[i],
                        p_array[i]/1e6,
                        v_array[i]
                    ])

            messagebox.showinfo("Успех", f"Данные экспортированы в {filename}")
        except Exception as e:
            messagebox.showerror("Ошибка экспорта", str(e))

    def export_all_unsteady_to_csv(self):
        """Экспорт всех временных слоёв нестационарного расчёта в CSV"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile="unsteady_all_results.csv"
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
