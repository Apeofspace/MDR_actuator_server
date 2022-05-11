from math import sin, cos, pi, sqrt, pow, atan, log10
from src_processes import t_s

# коэффициенты ряда Фурье
def A(F, t, f, k=1):
    """аргументы: функция (массив точек), время(массив точек),
    частота, номер гармоники"""
    n = len(F)
    return (2 / n) * sum([F[i] * cos(t[i] * 2 * pi * f * k) for i in range(n)])


def B(F, t, f, k=1):
    """аргументы: функция (массив точек), время(массив точек),
    частота, номер гармоники"""
    n = len(F)
    return 2 / n * sum([F[i] * sin(2 * pi * f * k * t[i]) for i in range(n)])


def A0(F):
    """аргументы: функция (массив точек)"""
    n = len(F)
    return 2 / n * sum(F)


# Разложение в ряд Фурье
def fourier(t, F, f):
    """Создание списка F для построения ряда Фурье (первая гармоники) """
    A_0 = A0(F)
    A1 = A(F, t, f, 1)
    B1 = B(F, t, f, 1)
    fur = [A_0 / 2 + A1 * cos(2 * pi * f * t[i]) + B1 * sin(2 * pi * f * t[i]) for i in range(len(t))]
    return fur


def abs_W(Ain, Bin, Aout, Bout):
    """Отношение амплитуд на одной частоте"""
    return 20 * log10(sqrt((pow(Aout, 2) + pow(Bout, 2)) / (pow(Ain, 2) + pow(Bin, 2))))


def ksi(Ain, Bin, Aout, Bout):
    """Фаза на частоте (градусы)"""
    ksi = (atan(Ain / Bin) - atan(Aout / Bout) * 180 / pi)
    if ksi > 0:
        ksi = ksi * (-1)
    print(f"Запаздывание = {ksi}\nAin = {Ain} Bin = {Bin} Aout = {Aout} Bout = {Bout}")
    return ksi


def LAFCH(Out, In, t, f):
    """Считает ЛАФЧХ для каждой отдельной частоты"""
    Ain = A(In, t, f)
    Bin = B(In, t, f)
    Aout = A(Out, t, f)
    Bout = B(Out, t, f)
    # return [abs_W(Ain, Bin, Aout, Bout), ksi(Ain, Bin, Aout, Bout)]

    # метод максимальнейшей дубины
    furin = [A0(In) / 2 + Ain * cos(2 * pi * f * t[i]) + Bin * sin(2 * pi * f * t[i]) for i in range(len(t))]
    furout = [A0(Out) / 2 + Aout * cos(2 * pi * f * t[i]) + Bout * sin(2 * pi * f * t[i]) for i in range(len(t))]
    N = 1/t_s # количество точек в секунду
    aw = ((max(furout)-min(furout))/2) / ((max(furin)-min(furin))/2) # решение не очень, надо починить съезжание периода
    index_max_furin = furin.index(max(furin))
    index_max_furout = furout.index(max(furout))
    index_min_furin = furin.index(min(furin))
    index_min_furout = furout.index(min(furout))
    min_dif = min(abs(index_max_furin-index_max_furout), abs(index_min_furin-index_min_furout))
    ksi = min_dif * (-360)/(N/f)
    print(f'{index_max_furout=}, {index_max_furin=}, {ksi=} , {(-360)/(N/f)=}')
    return 20*log10(aw), ksi
