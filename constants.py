EXTERNAL_DIAMETER_MM = 1020  # внешний диаметр, мм
WALL_THICKNESS_MM = 10  # толщина стенки, мм
ABS_ROUGHTNESS_MM = 0.1  # абсолютная шероховатость, мм
X0_KM = 0  # начальная координата, км
XN_KM = 105.5  # конечная координата, км
RO20 = 853.5  # плотность при 20C, кг/м3
VISCOSITY_20_SST = 13.76  # вязкость при 20C, сСт
VISCOSITY_50_SST = 5.72  # вязкость при 50C, сСт
P_INITIAL_MPA = 5.2  # давление в начале, МПа
P_END_MPA = 0.8  # давление в конце, МПа
TC = 8.1  # температура, C
dx_km = 1  # грубый шаг

# Преобразование единиц
EXTERNAL_DIAMETER = EXTERNAL_DIAMETER_MM / 1000  # м
WALL_THICKNESS = WALL_THICKNESS_MM / 1000  # м
INTERNAL_DIAMETER = EXTERNAL_DIAMETER - 2 * WALL_THICKNESS  # внутренний диаметр, м
ABS_ROUGHTNESS = ABS_ROUGHTNESS_MM / 1000  # м
L = XN_KM * 1000  # длина, м
P_INITIAL = P_INITIAL_MPA * 1e6  # Па
P_END = P_END_MPA * 1e6  # Па
T = TC + 273.15  # K
VISCOSITY_20 = VISCOSITY_20_SST * 1e-6  # m^2/s
VISCOSITY_50 = VISCOSITY_50_SST * 1e-6
SPEED_OF_SOUND = 1000
