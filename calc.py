import numpy as np
import constants as c
import concurrent.futures
import db_manager as db


class PipelineFlow:
    def __init__(self):
        # Параметры нефти
        self.rho = None
        self.nu = None
        self.epsilon = None

        # Результаты расчета
        self.v = None
        self.lambda_ = None
        self.Re = None

        # Сетка
        self.x_km = None
        self.x_m = None
        self.dx = None
        self.P = None
        self.v_arr = None

        # Нестационарный расчёт
        self.C = c.SPEED_OF_SOUND  # м/с
        self.dt = None
        self.B = None  # B = ρ * c

        # История для визуализации
        self.p_history = []
        self.v_history = []
        self.t_history = []

        # Флаг выполнения стационарного расчёта
        self.stationary_calculated = False

    @staticmethod
    def get_kinematic_viscosity(T, nu1, nu2) -> float:
        """Вычисление кинематической вязкости при температуре T"""
        T20 = 20 + 273.15
        T50 = 50 + 273.15
        ln_nu1 = np.log(nu1)
        ln_nu2 = np.log(nu2)
        k = (ln_nu1 - ln_nu2) / (T50 - T20)
        nu = nu1 * 1 / (np.exp(k * (T - T20)))
        return nu

    @staticmethod
    def get_reynolds(v, d, nu) -> float:
        """Число Рейнольдса"""
        if abs(v) < 1e-10 or nu < 1e-10:
            return 0.0
        return abs(v) * d / nu

    @staticmethod
    def lambda_stokes(Re) -> float:
        if Re < 1e-6:
            return 64.0
        return 64 / Re

    @staticmethod
    def lambda_ginzburg(Re) -> float:
        if Re < 1e-6:
            return 64.0
        gamma = 1 - np.exp(-0.002 * (Re - 2320))
        return ((64 / Re) * (1 - gamma)) + (0.3164 * gamma / Re**0.25)

    @staticmethod
    def lambda_blasius(Re) -> float:
        if Re < 1e-6:
            return 0.03164
        return 0.3164 / Re**0.25

    @staticmethod
    def lambda_altshul(Re, epsilon) -> float:
        if Re < 1e-6:
            return 0.11 * epsilon**0.25
        return 0.11 * (epsilon + 68 / Re)**0.25

    @staticmethod
    def lambda_shifrinson(epsilon) -> float:
        return 0.11 * epsilon**0.25

    @staticmethod
    def lambda_colebrook_white(Re, epsilon, max_iter=10) -> float:
        if Re < 1e-6:
            return 0.03

        lambda_prev = 0.11 * (epsilon + 68 / Re)**0.25

        for _ in range(max_iter):
            if lambda_prev < 1e-10:
                lambda_prev = 0.03
            sqrt_lambda = np.sqrt(lambda_prev)
            term = epsilon / 3.7 + 2.51 / (Re * sqrt_lambda)
            if term <= 0:
                break
            inv_sqrt_lambda = -2 * np.log10(term)
            lambda_new = 1 / (inv_sqrt_lambda ** 2)

            if abs(lambda_new - lambda_prev) < 1e-6:
                break
            lambda_prev = lambda_new

        return lambda_prev

    def get_lambda(self, Re, epsilon, method='auto') -> float:
        """
        Определение коэффициента гидравлического сопротивления
        в зависимости от режима течения
        """
        if method == 'stokes':
            return self.lambda_stokes(Re)
        elif method == 'ginzburg':
            return self.lambda_ginzburg(Re)
        elif method == 'blasius':
            return self.lambda_blasius(Re)
        elif method == 'altshul':
            return self.lambda_altshul(Re, epsilon)
        elif method == 'shifrinson':
            return self.lambda_shifrinson(epsilon)
        elif method == 'colebrook':
            return self.lambda_colebrook_white(Re, epsilon)

        # Автоматический выбор
        Re_I = 1e5 / epsilon
        Re_II = 500 / epsilon

        if Re < 2320:
            return self.lambda_stokes(Re)
        elif 2320 <= Re < 1e4:
            return self.lambda_ginzburg(Re)
        elif 1e4 <= Re < Re_I:
            return self.lambda_blasius(Re)
        elif Re_I <= Re < Re_II:
            return self.lambda_altshul(Re, epsilon)
        else:
            return self.lambda_shifrinson(epsilon)

    def refine_grid(self, X0, XN, dx_initial):
        """Создание равномерной сетки с шагом близким к dx_initial"""
        length = XN - X0
        n_intervals = max(1, int(round(length / dx_initial)))
        dx = length / n_intervals
        x_km = np.linspace(X0, XN, n_intervals + 1)
        return dx, x_km

    def calculate_stationary(self, lambda_method='auto', verbose=True):
        if verbose:
            print("=" * 60)
            print("Стационарный расчёт")
            print("=" * 60)

        # Корректировка плотности на температуру
        alpha = 0.0008
        self.rho = c.RO20 * (1 - alpha * (c.TC - 20))
        if verbose:
            print(f"Плотность при {c.TC}°C: ρ = {self.rho:.2f} кг/м³")

        # Кинематическая вязкость
        self.nu = self.get_kinematic_viscosity(c.T, c.VISCOSITY_20, c.VISCOSITY_50)
        if verbose:
            print(f"Кинематическая вязкость: ν = {self.nu*1e6:.2f} сСт")

        # Относительная шероховатость
        self.epsilon = c.ABS_ROUGHTNESS / c.INTERNAL_DIAMETER
        if verbose:
            print(f"Относительная шероховатость: ε = {self.epsilon:.6f}")
            print(f"Метод расчёта λ: {lambda_method}")

        # Итерационный расчет скорости
        v = 1.0
        tol = 1e-6
        max_iter = 20

        if verbose:
            print("\nИтерационный расчёт скорости:")

        for iteration in range(max_iter):
            Re = self.get_reynolds(v, c.INTERNAL_DIAMETER, self.nu)
            lambda_ = self.get_lambda(Re, self.epsilon, method=lambda_method)
            DeltaP = c.P_INITIAL - c.P_END
            v_new = np.sqrt((2 * DeltaP * c.INTERNAL_DIAMETER) / (self.rho * lambda_ * c.L))

            if verbose and iteration < 5:
                print(f"  Итерация {iteration+1}: v = {v_new:.4f} м/с, "
                      f"Re = {Re:.0f}, λ = {lambda_:.5f}")

            if abs(v_new - v) < tol:
                if verbose:
                    print(f"  Сходимость достигнута за {iteration+1} итераций")
                break
            v = v_new

        self.v = v
        self.Re = self.get_reynolds(v, c.INTERNAL_DIAMETER, self.nu)
        self.lambda_ = self.get_lambda(self.Re, self.epsilon, method=lambda_method)

        if verbose:
            print("\nФинальные результаты:")
            print(f"  Скорость нефти: v = {self.v:.4f} м/с")
            print(f"  Число Рейнольдса: Re = {self.Re:.0f}")
            print(f"  Коэффициент сопротивления: λ = {self.lambda_:.5f}")

        # 5. Создание расчетной сетки
        self.dx, self.x_km = self.refine_grid(c.X0_KM, c.XN_KM, c.dx_km)
        self.x_m = self.x_km * 1000

        if verbose:
            print("\nРасчётная сетка:")
            print(f"  Число точек: {len(self.x_km)}")
            print(f"  Шаг сетки: dx = {self.dx:.3f} км = {self.dx*1000:.1f} м")

        # 6. Распределение давления вдоль трубопровода
        dp_dx = -(self.lambda_ * self.rho * self.v**2) / (2 * c.INTERNAL_DIAMETER)
        self.P = c.P_INITIAL + dp_dx * self.x_m
        self.v_arr = np.full_like(self.x_km, self.v)

        if verbose:
            print(f"\nГрадиент давления: dP/dx = {dp_dx:.2f} Па/м")
            print(f"Давление в начале: P₀ = {self.P[0]/1e6:.3f} МПа")
            print(f"Давление в конце: Pₖ = {self.P[-1]/1e6:.3f} МПа")
            print("=" * 60)

        self.stationary_calculated = True

    def calculate_unsteady_with_callback(self, num_steps=2000, store_every=10,
                                         boundary_condition='valve_closure',
                                         bc_change_time=None, bc_change_value=None,
                                         lambda_method='auto', verbose=True,
                                         use_parallel=True, progress_callback=None):
        """
        Нестационарный расчёт

        store_every : int
            Обновлять график каждые store_every шагов
        boundary_condition : str
            'valve_closure' - мгновенное закрытие клапана на выходе
            'pressure_inlet' - изменение давления на входе
            'pressure_outlet' - изменение давления на выходе
        bc_change_time : float
            Момент времени изменения ГУ (секунды)
        bc_change_value : float
            Новое значение ГУ (Па для давления)
        progress_callback :
            Функция callback(step, total_steps, time, p_array, v_array) -> bool
            Возвращает False для остановки расчёта
        """
        if not self.stationary_calculated:
            raise ValueError("Сначала выполните calculate_stationary()")

        if verbose:
            print("\n" + "=" * 60)
            print("Нестационарный расчёт с динамической визуализацией")
            print("=" * 60)

        # Сохраняем исходные стационарные данные
        if not hasattr(self, 'P_original') or self.P_original is None:
            self.P_original = self.P.copy()
            self.v_arr_original = self.v_arr.copy()

        # Параметры сетки
        N = len(self.x_m)
        dx_m = self.x_m[1] - self.x_m[0]

        # Шаг по времени из условия Куранта (CFL = 1)
        self.dt = dx_m / self.C

        # Коэффициент B = ρ * c
        self.B = self.rho * self.C

        if verbose:
            print(f"Шаг по времени: dt = {self.dt:.4f} с")
            print(f"Число точек сетки: N = {N}")
            print(f"Шаг по пространству: dx = {dx_m:.1f} м")
            print(f"Коэффициент B = ρ·c = {self.B:.0f} Па·с/м")
            print(f"Параллельные вычисления: {'Да' if use_parallel else 'Нет'}")

            L = self.x_m[-1]
            period = 2 * L / self.C
            print(f"Длина трубопровода: L = {L/1000:.1f} км")
            print(f"Период отражения волны: T = 2L/c = {period:.2f} с")
            print(f"Общее время моделирования: {num_steps * self.dt:.2f} с")
            print(f"Граничное условие: {boundary_condition}")
            if bc_change_time is not None:
                print(f"Изменение ГУ в момент t = {bc_change_time:.2f} с")
            print("=" * 60)

        # Начальные условия (из стационарного расчёта)
        p = self.P.copy()
        v = self.v_arr.copy()

        # Сохранение начального состояния
        self.p_history = [p.copy()]
        self.v_history = [v.copy()]
        self.t_history = [0.0]

        # Граничные условия по умолчанию
        p_inlet = c.P_INITIAL
        p_outlet = c.P_END

        # Вспомогательные функции для параллельных вычислений
        def compute_I_a_single(i, p_prev, v_prev):
            """
            Вычисление одной инварианты I_a[i]
            Характеристика C+ приходит из точки (i-1, t) в точку (i, t+dt)
            """
            if i == 0:
                return 0.0

            p_a = p_prev[i-1]
            v_a = v_prev[i-1]

            dx_local = dx_m

            # Расчёт λ для текущей скорости
            if abs(v_a) < 1e-10:
                lambda_a = self.lambda_
            else:
                Re_a = self.get_reynolds(abs(v_a), c.INTERNAL_DIAMETER, self.nu)
                lambda_a = self.get_lambda(Re_a, self.epsilon, method=lambda_method)

            # Член трения
            R_a = lambda_a * dx_local * self.rho * v_a * abs(v_a) / (2 * c.INTERNAL_DIAMETER)

            # Инварианта вдоль C+
            I_a = p_a + self.B * v_a - R_a

            return I_a

        def compute_I_b_single(i, p_prev, v_prev):
            """
            Вычисление одной инварианты I_b[i]
            Характеристика C- приходит из точки (i+1, t) в точку (i, t+dt)
            """
            if i == N - 1:
                return 0.0

            p_b = p_prev[i+1]
            v_b = v_prev[i+1]

            dx_local = dx_m

            # Расчёт λ для текущей скорости
            if abs(v_b) < 1e-10:
                lambda_b = self.lambda_
            else:
                Re_b = self.get_reynolds(abs(v_b), c.INTERNAL_DIAMETER, self.nu)
                lambda_b = self.get_lambda(Re_b, self.epsilon, method=lambda_method)

            # Член трения
            R_b = lambda_b * dx_local * self.rho * v_b * abs(v_b) / (2 * c.INTERNAL_DIAMETER)

            # Инварианта вдоль C-
            I_b = p_b - self.B * v_b + R_b

            return I_b

        # Главный цикл по времени
        for step in range(1, num_steps + 1):
            current_t = step * self.dt

            # Изменение граничных условий в заданный момент времени
            if bc_change_time is not None and current_t >= bc_change_time:
                if boundary_condition == 'pressure_inlet':
                    p_inlet = bc_change_value
                elif boundary_condition == 'pressure_outlet':
                    p_outlet = bc_change_value

            p_new = np.zeros(N)
            v_new = np.zeros(N)

            # ШАГ 1: Инварианты I_a и I_b
            I_a = np.zeros(N)
            I_b = np.zeros(N)

            if use_parallel:
                # Параллельные вычисления инвариант
                with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                    future_I_a = {
                        executor.submit(compute_I_a_single, i, p, v): i
                        for i in range(1, N)
                    }

                    future_I_b = {
                        executor.submit(compute_I_b_single, i, p, v): i
                        for i in range(N-1)
                    }

                    for future in concurrent.futures.as_completed(future_I_a):
                        i = future_I_a[future]
                        I_a[i] = future.result()

                    for future in concurrent.futures.as_completed(future_I_b):
                        i = future_I_b[future]
                        I_b[i] = future.result()
            else:
                # Последовательные вычисления
                for i in range(1, N):
                    I_a[i] = compute_I_a_single(i, p, v)

                for i in range(N-1):
                    I_b[i] = compute_I_b_single(i, p, v)

            # ШАГ 2: Решение для внутренних точек (i = 1, 2, ..., N-2)
            for i in range(1, N-1):
                p_new[i] = (I_a[i] + I_b[i]) / 2.0
                v_new[i] = (I_a[i] - I_b[i]) / (2.0 * self.B)

            # ШАГ 3: Граничные условия
            # Левая граница (i = 0): задано давление p_inlet
            p_new[0] = p_inlet
            v_new[0] = (p_new[0] - I_b[0]) / self.B

            # Правая граница (i = N-1): зависит от типа ГУ
            if boundary_condition == 'valve_closure':
                # Закрытие клапана: скорость = 0
                v_new[N-1] = 0.0
                # Давление определяется из характеристики C+
                p_new[N-1] = I_a[N-1] - self.B * v_new[N-1]

            elif boundary_condition == 'pressure_outlet':
                # Задано давление на выходе
                p_new[N-1] = p_outlet
                v_new[N-1] = (I_a[N-1] - p_new[N-1]) / self.B

            elif boundary_condition == 'pressure_inlet':
                # Изменение давления на входе
                p_new[0] = p_inlet
                v_new[0] = (p_new[0] - I_b[0]) / self.B
                # Правая граница: задано постоянное давление
                p_new[N-1] = c.P_END
                v_new[N-1] = (I_a[N-1] - p_new[N-1]) / self.B

            else:
                # По умолчанию: задано давление на выходе
                p_new[N-1] = c.P_END
                v_new[N-1] = (I_a[N-1] - p_new[N-1]) / self.B

            # ШАГ 4: Обновление решения
            p = p_new.copy()
            v = v_new.copy()

            # ШАГ 5: Коллюэк
            if progress_callback and step % max(store_every, 5) == 0:
                # Вызываем коллбэк с текущими данными
                should_continue = progress_callback(step, num_steps, current_t, p.copy(), v.copy())

                # Проверка на запрос остановки
                if should_continue is False:
                    if verbose:
                        print(f"\n Расчёт остановлен пользователем на шаге {step}")
                    break

            # ШАГ 6: Сохраниение результатов в историю
            if step % store_every == 0 or step == num_steps:
                self.p_history.append(p.copy())
                self.v_history.append(v.copy())
                self.t_history.append(current_t)

                if verbose and step % (store_every * 10) == 0:
                    max_p = np.max(p) / 1e6
                    min_p = np.min(p) / 1e6
                    max_v = np.max(np.abs(v))

                    # Проверка на NaN или Inf
                    if np.isnan(max_p) or np.isinf(max_p):
                        print(f"ВНИМАНИЕ: Обнаружены NaN/Inf на шаге {step}!")
                        print("   Проверьте параметры расчёта")
                        break

                    print(f"t = {current_t:7.2f} с | "
                          f"P: [{min_p:.3f}, {max_p:.3f}] МПа | "
                          f"v_max: {max_v:.4f} м/с")

        # Финальное состояние
        self.P = p
        self.v_arr = v

        if verbose:
            print("=" * 60)
            print("Нестационарный расчёт завершён")
            print(f"Сохранено {len(self.t_history)} временных слоёв")
            print("=" * 60)
        # Проверка результатов
        self.check_unsteady_results()

    def check_unsteady_results(self):
        if not self.p_history:
            return

        # Последний временной слой
        p_final = self.p_history[-1]
        v_final = self.v_history[-1]
        t_final = self.t_history[-1]

        # Начальное среднее давление (ожидаемое конечное значение)
        p_initial = self.p_history[0]
        p_avg_expected = (p_initial[0] + p_initial[-1]) / 2

        print(f"\n{'='*60}")
        print("Проверка")
        print(f"{'='*60}")
        print(f"Время окончания: {t_final:.2f} с")
        print(f"Скорость в начале: {v_final[0]:.6f} м/с")
        print(f"Скорость в конце: {v_final[-1]:.6f} м/с")
        print(f"Макс. скорость: {np.max(np.abs(v_final)):.6f} м/с")
        print(f"Макс. давление: {np.max(p_final)/1e6:.3f} МПа")
        print(f"Мин. давление: {np.min(p_final)/1e6:.3f} МПа")
        print(f"Среднее давление (расчётное): {np.mean(p_final)/1e6:.3f} МПа")
        print(f"Ожидаемое среднее давление: {p_avg_expected/1e6:.3f} МПа")
        print(f"Разность начальных давлений: {(abs(p_initial[0] - p_initial[-1]))/1e6:.3f} МПа")
        print(f"Разность конечных давлений: {(abs(p_final[0] - p_final[-1]))/1e6:.3f} МПа")

    def check_steady_state(self, p_array, v_array, tolerance=1e-6):
        """Проверка достижения установившегося состояния"""
        # Проверяем, что скорости близки к нулю
        max_velocity = np.max(np.abs(v_array))
        if max_velocity > tolerance:
            return False

        # Проверяем, что давление выровнялось
        p_diff = np.max(p_array) - np.min(p_array)
        if p_diff > tolerance * np.mean(p_array):
            return False

        return True

    def restore_stationary_data(self):
        """Восстановление исходных стационарных данных после нестационарного расчёта"""
        if hasattr(self, 'P_original') and self.P_original is not None:
            self.P = self.P_original.copy()
            self.v_arr = self.v_arr_original.copy()

    def save_to_database(self, db_name='pipeline_results.db'):
        db_manager = db.DatabaseManager(db_name)

        if self.stationary_calculated:
            db_manager.save_stationary_calculation(self)

        if self.p_history:
            db_manager.save_unsteady_calculation(self)

    def print_results_table(self):
        """Вывод таблицы значений"""
        if self.P is None or self.v_arr is None:
            raise ValueError("Сначала выполните расчёт")

        P_MPa = self.P / 1e6
        print("\n" + "=" * 60)
        print("Таблица результатов")
        print("=" * 60)
        print(f"{'x, км':>10} | {'P, МПа':>10} | {'v, м/с':>10}")
        print("-" * 60)
        for i in range(len(self.x_km)):
            print(f"{self.x_km[i]:10.3f} | {P_MPa[i]:10.3f} | "
                  f"{self.v_arr[i]:10.4f}")
        print("=" * 60)


# if __name__ == "__main__":
#     pipeline = PipelineFlow()
#     pipeline.calculate_stationary()

#     pipeline.calculate_unsteady_with_callback(
#         num_steps=3000,
#         store_every=50,
#         boundary_condition='valve_closure',
#         verbose=True
#     )
