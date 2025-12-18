import sqlite3
import csv
from datetime import datetime


class DatabaseManager:
    def __init__(self, db_name='pipeline_results.db'):
        self.db_name = db_name
        self.init_database()

    def init_database(self):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS calculations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    calculation_type TEXT,
                    num_points INTEGER,
                    description TEXT
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stationary_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    calc_id INTEGER,
                    x_km REAL,
                    x_m REAL,
                    pressure_Pa REAL,
                    pressure_MPa REAL,
                    velocity_ms REAL,
                    FOREIGN KEY (calc_id) REFERENCES calculations (id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS unsteady_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    calc_id INTEGER,
                    time_step INTEGER,
                    time_s REAL,
                    x_km REAL,
                    x_m REAL,
                    pressure_Pa REAL,
                    pressure_MPa REAL,
                    velocity_ms REAL,
                    FOREIGN KEY (calc_id) REFERENCES calculations (id)
                )
            ''')

            conn.commit()

    def save_stationary_calculation(self, pipeline):
        if not pipeline.stationary_calculated:
            raise ValueError("Нет данных стационарного расчёта для сохранения")

        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''
                INSERT INTO calculations (timestamp, calculation_type, num_points, description)
                VALUES (?, ?, ?, ?)
            ''', (timestamp, 'stationary', len(pipeline.x_km), f'Stationary calculation, v={pipeline.v:.4f} m/s'))

            calc_id = cursor.lastrowid

            for i in range(len(pipeline.x_km)):
                cursor.execute('''
                    INSERT INTO stationary_results
                    (calc_id, x_km, x_m, pressure_Pa, pressure_MPa, velocity_ms)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (calc_id, pipeline.x_km[i], pipeline.x_m[i], pipeline.P[i], pipeline.P[i]/1e6, pipeline.v_arr[i]))

            conn.commit()

        return calc_id

    def save_unsteady_calculation(self, pipeline):
        if not pipeline.p_history:
            raise ValueError("Нет данных нестационарного расчёта для сохранения")

        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''
                INSERT INTO calculations (timestamp, calculation_type, num_points, description)
                VALUES (?, ?, ?, ?)
            ''', (timestamp, 'unsteady', len(pipeline.x_km), f'Unsteady calculation, {len(pipeline.t_history)} time steps'))

            calc_id = cursor.lastrowid

            for t_idx, t in enumerate(pipeline.t_history):
                p_array = pipeline.p_history[t_idx]
                v_array = pipeline.v_history[t_idx]
                for i in range(len(pipeline.x_km)):
                    cursor.execute('''
                        INSERT INTO unsteady_results
                        (calc_id, time_step, time_s, x_km, x_m, pressure_Pa,
                        pressure_MPa, velocity_ms)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (calc_id, t_idx, t, pipeline.x_km[i], pipeline.x_m[i], p_array[i], p_array[i]/1e6, v_array[i]))

            conn.commit()

        return calc_id

    def get_all_calculations(self):
        """Получение списка всех расчётов"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, timestamp, calculation_type, num_points, description
                FROM calculations
                ORDER BY id DESC
            ''')

            rows = cursor.fetchall()

        return rows

    def get_stationary_data(self, calc_id):
        """Получение данных стационарного расчёта"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT x_km, x_m, pressure_Pa, velocity_ms
                FROM stationary_results
                WHERE calc_id = ?
                ORDER BY x_km
            ''', (calc_id,))

            rows = cursor.fetchall()

        return rows

    def get_unsteady_data(self, calc_id):
        """Получение данных нестационарного расчёта"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            # Получаем все временные слои
            cursor.execute('''
                SELECT DISTINCT time_s
                FROM unsteady_results
                WHERE calc_id = ?
                ORDER BY time_s
            ''', (calc_id,))

            times = [row[0] for row in cursor.fetchall()]

            # Получаем данные для каждого временного слоя
            data_by_time = []
            for t in times:
                cursor.execute('''
                    SELECT x_km, x_m, pressure_Pa, velocity_ms
                    FROM unsteady_results
                    WHERE calc_id = ? AND time_s = ?
                    ORDER BY x_km
                ''', (calc_id, t))

                rows = cursor.fetchall()
                data_by_time.append((t, rows))

        return times, data_by_time

    def delete_calculation(self, calc_id):
        """Удаление расчёта по ID"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            cursor.execute('DELETE FROM stationary_results WHERE calc_id = ?', (calc_id,))
            cursor.execute('DELETE FROM unsteady_results WHERE calc_id = ?', (calc_id,))
            cursor.execute('DELETE FROM calculations WHERE id = ?', (calc_id,))

            conn.commit()

    def clear_database(self):
        """Полная очистка базы данных"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            cursor.execute('DELETE FROM stationary_results')
            cursor.execute('DELETE FROM unsteady_results')
            cursor.execute('DELETE FROM calculations')

            conn.commit()

    def export_to_csv(self, calc_id, calc_type, filename):
        """Экспорт данных в CSV"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                if calc_type == "Стационарный":
                    writer.writerow(['x_km', 'P_MPa', 'v_ms'])
                    cursor.execute('''
                        SELECT x_km, pressure_MPa, velocity_ms
                        FROM stationary_results
                        WHERE calc_id = ?
                        ORDER BY x_km
                    ''', (calc_id,))
                else:
                    writer.writerow(['time_s', 'x_km', 'P_MPa', 'v_ms'])
                    cursor.execute('''
                        SELECT time_s, x_km, pressure_MPa, velocity_ms
                        FROM unsteady_results
                        WHERE calc_id = ?
                        ORDER BY time_s, x_km
                    ''', (calc_id,))

                rows = cursor.fetchall()
                writer.writerows(rows)
