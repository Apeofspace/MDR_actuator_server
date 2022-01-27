import csv
import sys
import matplotlib.pyplot as plt
import os
import re
import numpy as np


def make_format(other, current):
    # current and other are axes
    def format_coord(x, y):
        # x, y are data coordinates
        if len(buffer_xcom):
            com = np.interp(x, buffer_xcom, buffer_ycom)
            obj = np.interp(x, buffer_xcom, buffer_yobj)
            duty = np.interp(x, buffer_xcom, buffer_duty)
            tok = np.interp(x, buffer_xcom, buffer_tok)
            return (
                "Упр. сигнал: {:.0f},   вых. сигнал: {:.0f},   коэф. заполнения: {:.0f},   время: {:.2f}, ток: {:.2f} A".format(
                    com, obj, duty, x, tok))
        else:
            # convert to display coords
            display_coord = current.transData.transform((x, y))
            inv = other.transData.inverted()
            # convert back to data coords with respect to ax
            ax_coord = inv.transform(display_coord)
            return "Координата: {:.0f},   коэф. заполнения: {:.0f},   время: {:.2f} мс".format(ax_coord[1], y, x)

    return format_coord


buffer_xcom, buffer_ycom, buffer_xobj, buffer_yobj, buffer_duty, buffer_dir, buffer_tok, buffer_v = [], [], [], [], [], [], [], []
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
                       'Duty': '0', 'Dir': 0, 'Current': 0}:
                buffer_xcom.append(float(row['Time COM']))
                buffer_ycom.append(int(row['COM']))
                buffer_xobj.append(float(row['Time OBJ']))
                buffer_yobj.append(int(row['OBJ']))
                buffer_duty.append(int(row['Duty']))
                buffer_dir.append(int(row['Dir']))
                buffer_tok.append(float(row['Current']))

    fig, ax = plt.subplots(figsize=(12, 6), tight_layout=True)
    plt.grid(b=True, which='major', axis='both')
    ax3 = ax.twinx()
    ax2 = ax.twinx()
    ax2.format_coord = make_format(ax, ax2)
    ax3.set_ylim(-3, 3)
    ax.set_ylim(0, 4100)
    ax2.set_ylim(0, 4100)
    ax2.set_yticklabels([])
    line1, = ax.plot(buffer_xcom, buffer_ycom, label='Управляющий сигнал')
    line2, = ax.plot(buffer_xobj, buffer_yobj, label='Значение с потенциометра')
    line3, = ax2.plot(buffer_xcom, buffer_duty, label='Коэффициент заполнения', color='green', linewidth=0.5)
    line4, = ax2.plot(buffer_xcom, buffer_dir, label='Направление движения', color='red', linewidth=0.5)
    line5, = ax3.plot(buffer_xobj, buffer_tok, label='Ток', color='purple', linewidth=0.7)
    fig.canvas.manager.set_window_title(arg)
    plt.xlabel("[мс]")
    fig.legend()
    plt.show()
except FileNotFoundError as e:
    print(e)
    sys.exit()
