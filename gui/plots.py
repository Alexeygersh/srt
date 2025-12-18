import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import constants as c


class PlotWindow:
    """Окно для статических графиков"""

    def __init__(self, root, pipeline):
        self.root = root
        self.pipeline = pipeline
        self.window = None
        self.fig = None
        self.canvas = None
        self.plot_type_var = tk.StringVar(value='stationary_both')

    def open(self):
        """Открытие окна с графиками"""
        if not self.pipeline.stationary_calculated:
            messagebox.showwarning("Предупреждение", "Сначала выполните расчёт!")
            return

        # Если окно уже открыто - активируем его
        if self.window and tk.Toplevel.winfo_exists(self.window):
            self.window.lift()
            self.window.focus()
            return

        # Создаём новое окно
        self.window = tk.Toplevel(self.root)
        self.window.title("Визуализация результатов")
        self.window.geometry("1200x800")

        # Панель выбора типа графика
        self._create_control_panel()

        # Canvas для графика
        self.fig = Figure(figsize=(12, 7))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.window)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Рисуем график
        self.update_plot()

    def _create_control_panel(self):
        """Создание панели управления"""
        control_frame = ttk.Frame(self.window)
        control_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(control_frame, text="Тип графика:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=10)

        plot_types = [
            ('Стац. P(x)', 'stationary_p'),
            ('Стац. v(x)', 'stationary_v'),
            ('Стац. P+v', 'stationary_both'),
        ]

        for text, value in plot_types:
            ttk.Radiobutton(control_frame, text=text,
                            variable=self.plot_type_var,
                            value=value,
                            command=self.update_plot).pack(side=tk.LEFT, padx=5)

        ttk.Button(control_frame, text="Обновить", command=self.update_plot).pack(side=tk.RIGHT, padx=5)

        ttk.Button(control_frame, text="Сохранить изображение", command=self.save_plot).pack(side=tk.RIGHT, padx=5)

    def update_plot(self):
        """Обновление графика"""
        if not self.window or not tk.Toplevel.winfo_exists(self.window):
            return

        plot_type = self.plot_type_var.get()
        self.fig.clear()

        try:
            # Используем оригинальные стационарные данные
            if hasattr(self.pipeline, 'P_original') and self.pipeline.P_original is not None:
                P_backup = self.pipeline.P
                v_backup = self.pipeline.v_arr

                self.pipeline.P = self.pipeline.P_original
                self.pipeline.v_arr = self.pipeline.v_arr_original

                if plot_type == 'stationary_p':
                    self._plot_pressure()
                elif plot_type == 'stationary_v':
                    self._plot_velocity()
                elif plot_type == 'stationary_both':
                    self._plot_both()

                self.pipeline.P = P_backup
                self.pipeline.v_arr = v_backup
            else:
                if plot_type == 'stationary_p':
                    self._plot_pressure()
                elif plot_type == 'stationary_v':
                    self._plot_velocity()
                elif plot_type == 'stationary_both':
                    self._plot_both()

            self.canvas.draw()

        except Exception as e:
            messagebox.showerror("Ошибка отображения", str(e))

    def _plot_pressure(self):
        """График стационарного давления"""
        ax = self.fig.add_subplot(111)
        ax.plot(self.pipeline.x_km, self.pipeline.P / 1e6, 'b-o', markersize=4, linewidth=2)
        ax.set_xlabel('Расстояние, км', fontsize=12)
        ax.set_ylabel('Давление, МПа', fontsize=12)
        ax.set_title('Стационарное распределение давления P(x)', fontsize=14)
        ax.grid(True, alpha=0.3)

        ax.annotate(f'P0 = {c.P_INITIAL_MPA:.1f} МПа',
                    xy=(0, c.P_INITIAL_MPA), xytext=(5, c.P_INITIAL_MPA - 0.3),
                    arrowprops=dict(arrowstyle='->', color='blue'),
                    fontsize=10, color='blue')

        ax.annotate(f'Pn = {c.P_END_MPA:.1f} МПа',
                    xy=(c.XN_KM, c.P_END_MPA), xytext=(c.XN_KM - 15, c.P_END_MPA + 0.3),
                    arrowprops=dict(arrowstyle='->', color='blue'),
                    fontsize=10, color='blue')

        self.fig.tight_layout()

    def _plot_velocity(self):
        """График стационарной скорости"""
        ax = self.fig.add_subplot(111)
        ax.plot(self.pipeline.x_km, self.pipeline.v_arr, 'orange', linewidth=2)
        ax.set_xlabel('Расстояние, км', fontsize=12)
        ax.set_ylabel('Скорость, м/с', fontsize=12, color='orange')
        ax.set_title('Стационарное распределение скорости v(x)', fontsize=14)
        ax.grid(True, alpha=0.3)
        ax.tick_params(axis='y', labelcolor='orange')

        self.fig.tight_layout()

    def _plot_both(self):
        """График стационарного давления и скорости"""
        ax1 = self.fig.add_subplot(111)
        ax1.plot(self.pipeline.x_km, self.pipeline.P / 1e6, 'b-o', markersize=4, label='Давление', linewidth=2)
        ax1.set_xlabel('Расстояние, км', fontsize=12)
        ax1.set_ylabel('Давление, МПа', fontsize=12, color='b')
        ax1.tick_params(axis='y', labelcolor='b')
        ax1.grid(True, alpha=0.3)

        ax2 = ax1.twinx()
        ax2.plot(self.pipeline.x_km, self.pipeline.v_arr, 'orange', linewidth=2, label='Скорость')
        ax2.set_ylabel('Скорость, м/с', fontsize=12, color='orange')
        ax2.tick_params(axis='y', labelcolor='orange')

        ax1.set_title('Стационарное распределение P(x) и v(x)', fontsize=14)

        self.fig.tight_layout()

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
                self.fig.savefig(filename, dpi=300, bbox_inches='tight')
                messagebox.showinfo(f"График сохранён: {filename}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить: {e}")
