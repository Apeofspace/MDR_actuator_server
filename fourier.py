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
    """Создание списка типа [t, F] для построения ряда Фурье"""
    # F = []
    # for i in range(len(t)):
    #     ft = A0 / 2 + A1 * math.cos(2 * math.pi * f * t[i]) + B1 * math.sin(2 * math.pi * f * t[i])
    #     F.append(ft)
    F = [A0 / 2 + A1 * math.cos(2 * math.pi * f * t[i]) + B1 * math.sin(2 * math.pi * f * t[i]) for i in range(len(t))]
    return [t, F]

