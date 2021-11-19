from math import sin, cos, pi, sqrt, pow, atan, log10


# коэффициенты ряда Фурье
def A(F, t, f, k=1):
    """аргументы: функция (массив точек), время(массив точек),
    частота, количество точек в периоде, номер гармоники"""
    n = len(F)
    # return (2 / n) * sum([F[i] * cos(t[i] * 2 * pi * f * k * T_count) for i in range(n)])
    return (2 / n) * sum([F[i] * cos(t[i] * 2 * pi * f * k) for i in range(n)])


def B(F, t, f, k=1):
    """аргументы: функция (массив точек), время(массив точек),
    частота, количество точек в периоде, номер гармоники"""
    n = len(F)
    # return 2 / n * sum([F[i] * sin(2 * pi * f * k * T_count * t[i]) for i in range(n)])
    return 2 / n * sum([F[i] * sin(2 * pi * f * k * t[i]) for i in range(n)])


def A0(F):
    """аргументы: функция (массив точек), количество точек в периоде"""
    n = len(F)
    return 2 / n * sum(F)


# Разложение в ряд Фурье
def fourier(t, F, f):
    """Создание списка F для построения ряда Фурье
    Аргументы: массив времени, частота, коэффициенты"""
    A_0 = A0(F)
    A1 = A(F, t, f, 1)
    B1 = B(F, t, f, 1)
    # F = [A_0 / 2 + A1 * cos(2 * pi * f * t[i] * T_count) + B1 * sin(2 * pi * f * t[i]* T_count) for i in range(len(t))]
    F = [A_0 / 2 + A1 * cos(2 * pi * f * t[i]) + B1 * sin(2 * pi * f * t[i]) for i in range(len(t))]
    return F


def abs_W(Ain, Bin, Aout, Bout):
    """Отношение амплитуд на одной частоте"""
    return 20 * log10(sqrt((pow(Aout, 2) + pow(Bout, 2)) / (pow(Ain, 2) + pow(Bin, 2))))


def ksi(Ain, Bin, Aout, Bout):
    """Фаза на частоте (градусы)
    аргументы: """
    ksi = -(atan(Ain / Bin) - atan(Aout / Bout)) * 180 / pi
    print(f"Запаздывание = {ksi}")
    return ksi


def LAFCH(Out, In, t, f):
    """Считает ЛАФЧХ для каждой отдельной частоты"""
    Ain = A(In, t, f)
    Bin = B(In, t, f)
    Aout = A(Out, t, f)
    Bout = B(Out, t, f)
    return [abs_W(Ain, Bin, Aout, Bout), ksi(Ain, Bin, Aout, Bout)]


if __name__ == "__main__":
    ...
    # tests
