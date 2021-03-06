import csv
import sys
import matplotlib.pyplot as plt
import os
import re
import numpy as np
from src_processes import t_s


def make_format(other, current, buffers):
    # current and other are axes
    def format_coord(x, y):
        # x, y are data coordinates
        if len(buffers['buffer_time']):
            com = np.interp(x, buffers['buffer_time'], buffers['buffer_com'])
            obj = np.interp(x, buffers['buffer_time'], buffers['buffer_obj'])
            duty = np.interp(x, buffers['buffer_time'], buffers['buffer_duty'])
            return (
                "Упр. сигнал: {:.0f},   вых. сигнал: {:.0f},   коэф. заполнения: {:.0f},   время: {:.2f}".format(
                    com, obj, duty, x))
        else:
            # convert to display coords
            display_coord = current.transData.transform((x, y))
            inv = other.transData.inverted()
            # convert back to data coords with respect to ax
            ax_coord = inv.transform(display_coord)
            return "Координата: {:.0f},   коэф. заполнения: {:.0f},   время: {:.4f} мс".format(ax_coord[1], y, x)

    return format_coord


def find_latest_file():
    latest = None
    for i in re.findall("Data_\d+_\d+_\d+-\d+\.csv", ' '.join(os.listdir())):
        if latest is None:
            latest = i
        else:
            if int(re.sub("[^0-9]", "", i)) > int(re.sub("[^0-9]", "", latest)):
                latest = i
    if latest is None:
        print('Nothing found')
        return None
    else:
        return latest


def read_from_csv(filename):
    buffer_time, buffer_com, buffer_obj, buffer_duty = [], [], [], []
    try:
        print("Opening file: {}".format(filename))
        with open(filename, "r", newline='') as csv_file:
            reader = csv.DictReader(csv_file)
            time = 0
            for row in reader:
                if row != {'Frequency': '0', 'COM': '0', 'OBJ': '0',
                           'Duty': '0'}:
                    time += t_s
                    buffer_time.append(time)
                    buffer_com.append(int(row['COM']))
                    buffer_obj.append(int(row['OBJ']))
                    buffer_duty.append(int(row['Duty']))
        return {'buffer_time': buffer_time, 'buffer_com': buffer_com, 'buffer_obj': buffer_obj, 'buffer_duty': buffer_duty}
    except FileNotFoundError as e:
        print(e)
        return None


def plot_and_show(buffers, filename):
    fig, ax = plt.subplots(figsize=(12, 6), tight_layout=True)
    plt.grid(b=True, which='major', axis='both')
    ax3 = ax.twinx()
    ax2 = ax.twinx()
    ax2.format_coord = make_format(ax, ax2, buffers)
    ax3.set_ylim(-3, 3)
    ax.set_ylim(0, 4100)
    ax2.set_ylim(0, 4100)
    ax2.set_yticklabels([])
    line1, = ax.plot(buffers['buffer_time'], buffers['buffer_com'], label='Управляющий сигнал')
    line2, = ax.plot(buffers['buffer_time'], buffers['buffer_obj'], label='Значение с потенциометра')
    line3, = ax2.plot(buffers['buffer_time'], buffers['buffer_duty'], label='Коэффициент заполнения', color='green',
                      linewidth=0.5)
    fig.canvas.manager.set_window_title(filename)
    plt.xlabel("[с]")
    fig.legend()
    plt.show()


if __name__ == '__main__':
    try:
        arg = sys.argv[1]
        filename = arg
    except Exception:
        print("""Use -latest or a filename as an argument \nDefault: -latest""")
        arg = '-latest'
    if arg == '-latest' or arg == 'l':
        filename = find_latest_file()
        if filename is None:
            sys.exit()
    buffers = read_from_csv(filename)
    if buffers is None:
        sys.exit()
    plot_and_show(buffers, filename)

