import csv
import sys
import matplotlib.pyplot as plt
import os
import re
from fourier import *
import numpy as np


# def make_format(other, current):
#     # current and other are axes
#     def format_coord(x, y):
#         # x, y are data coordinates
#         # convert to display coords
#         display_coord = current.transData.transform((x, y))
#         inv = other.transData.inverted()
#         # convert back to data coords with respect to ax
#         ax_coord = inv.transform(display_coord)
#         return "Координата: {:.0f},   коэф. заполнения: {:.0f},   время: {:.2f}".format(ax_coord[1], y, x)
#
#     return format_coord

def make_format(other, current):
    # current and other are axes
    def format_coord(x, y):
        # x, y are data coordinates
        if len(xcom):
            com = np.interp(x, xcom, ycom)
            obj = np.interp(x, xcom, yobj)
            dut = np.interp(x, xcom, duty)
            t = np.interp(x, xcom, tok)
            napr = np.interp(x, xcom, v)
            return (
                "Упр. сигнал: {:.0f},   вых. сигнал: {:.0f},   коэф. заполнения: {:.0f},   время: {:.2f}, ток: {:.2f} A, напр. {:.2f}".format(
                    com, obj, dut, y, t, napr))
        else:
            # convert to display coords
            display_coord = current.transData.transform((x, y))
            inv = other.transData.inverted()
            # convert back to data coords with respect to ax
            ax_coord = inv.transform(display_coord)
            return "Координата: {:.0f},   коэф. заполнения: {:.0f},   время: {:.2f}".format(ax_coord[1], y, x)

    return format_coord


def linearize(xobj, yobj):
    # частоту f надо что бы он сам определял
    # надо чтобы он сам определял начало и конец периода
    # надо чтобы гарантированно каждый период отрабатывал с одинаковой частотой
    n = 2000
    t = [x/1000 for x in xobj[2000:4000]]
    # n = len(xobj)
    # t = [x / 1000 for x in xobj]
    f = 0.5
    k = 1
    F = yobj[2000:4000]
    # F = yobj
    x, y = fourier(t, f, A0(F, n), A(F, t, f, n), B(F, t, f, n))
    return [x1*1000 for x1 in x], y


xcom, ycom, xobj, yobj, duty, dir, tok, v = [], [], [], [], [], [], [], []
try:
    arg = sys.argv[1]
except Exception:
    print("""Use -latest or a filename as an argument \nDefault: -latest""")
    arg = '-latest'
if arg == '-latest' or arg == 'l':
    latest = None
    for i in re.findall("Data_\d+_\d+_\d+-\d+\.csv", ' '.join(os.listdir())):
        if latest is None:
            latest = i
        else:
            if int(re.sub("[^0-9]", "", i)) > int(re.sub("[^0-9]", "", latest)):
                latest = i
    if latest is None:
        print('Nothing found')
        sys.exit()
    else:
        arg = latest
try:
    print("Opening file: {}".format(arg))
    with open(arg, "r", newline='') as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            if row != {'Time COM': '0', 'Time OBJ': '0', 'COM': '0', 'OBJ': '0',
                       'Duty': '0', 'Dir': 0, 'Current': 0, 'Voltage': 0}:
                xcom.append(float(row['Time COM']))
                ycom.append(int(row['COM']))
                xobj.append(float(row['Time OBJ']))
                yobj.append(int(row['OBJ']))
                duty.append(int(row['Duty']))
                dir.append(int(row['Dir']))
                tok.append(float(row['Current']))
                v.append(float(row['Voltage']))

    fig, ax = plt.subplots(figsize=(12, 6), tight_layout=True)
    plt.grid(b=True, which='major', axis='both')
    ax3 = ax.twinx()
    ax4 = ax.twinx()
    ax2 = ax.twinx()
    ax2.format_coord = make_format(ax, ax2)
    ax3.set_ylim(-3, 3)
    ax.set_ylim(0, 4100)
    ax2.set_ylim(0, 4100)
    ax4.set_ylim(0, 30)
    ax2.set_yticklabels([])
    ax4.set_yticklabels([])
    line1, = ax.plot(xcom, ycom, label='Управляющий сигнал')
    line2, = ax.plot(xobj, yobj, label='Значение с потенциометра')
    line3, = ax2.plot(xcom, duty, label='Коэффициент заполнения', color='green', linewidth=0.5)
    line4, = ax2.plot(xcom, dir, label='Направление', color='red', linewidth=0.5)
    line5, = ax3.plot(xobj, tok, label='Ток', color='purple', linewidth=0.7)
    line6, = ax4.plot(xobj, v, label='Напр.', color='cyan', linewidth=0.7)
    # linxobj, linyobj = linearize(xobj, yobj)
    # line5, = ax.plot(linxobj, linyobj, label='Линеаризованное значение', color='purple', linewidth=0.5)
    fig.canvas.manager.set_window_title(arg)
    plt.xlabel("[мс]")
    fig.legend()
    plt.show()
except FileNotFoundError as e:
    print(e)
    sys.exit()
