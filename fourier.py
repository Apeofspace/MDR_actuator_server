import math


# коэффициенты ряда Фурье
def A(F, t, f, n, k=1):
    """аргументы: функция (массив точек), время(массив точек),
    частота, количество точек, номер гармоники"""
    return 2 / n * sum([F[i] * math.cos(2 * math.pi * f * k * t[i]) for i in range(len(F))])


def B(F, t, f, n, k=1):
    """аргументы: функция (массив точек), время(массив точек),
    частота, количество точек, номер гармоники"""
    return 2 / n * sum([F[i] * math.sin(2 * math.pi * f * k * t[i]) for i in range(len(F))])


def A0(F, n):
    """аргументы: функция (массив точек), количество точек"""
    return 2 / n * sum(F)


# Разложение в ряд Фурье
def fourier(t, f, A0, A1, B1):
    """Создание списка типа [t, F] для построения ряда Фурье
    Аргументы: массив времени, частота, коэффициенты"""
    F = [A0 / 2 + A1 * math.cos(2 * math.pi * f * t[i]) + B1 * math.sin(2 * math.pi * f * t[i]) for i in range(len(t))]
    return [t, F]

def abs_W():
    """Создание списка типа [t, F] для построения ЛАХ
    Аргументы: массив времени, массив амплитуд"""
    AbsW = max(abs(i) for i in FurOut[1])/max(abs(i) for i in FurIn[1])
    AbsWlog =20*math.log(max(abs(i) for i in FurOut[1])/max(abs(i) for i in FurIn[1]))
    print('Отношение амплитуд выходного к входному: {} [В/B]'.format(AbsW))
    print('Отношение амплитуд выходного к входному: {} [дБ]'.format(AbsWlog))

def ksi():
    """Создание списка типа [t, F] для построения ЛАЧХ
    Аргументы: массив времени, массив амплитуд"""
    ksi = (math.atan(A1Uin / B1Uin) - math.atan(A1Uout / B1Uout)) * 180 / math.pi
    print('Запаздывание по фазе равно: {} градусов'.format(ksi))

