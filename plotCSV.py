import csv
import sys
import matplotlib.pyplot as plt
import os
import re


def make_format(other, current):
    # current and other are axes
    def format_coord(x, y):
        # x, y are data coordinates
        # convert to display coords
        display_coord = current.transData.transform((x, y))
        inv = other.transData.inverted()
        # convert back to data coords with respect to ax
        ax_coord = inv.transform(display_coord)
        return "Координата: {:.0f},   коэф. заполнения: {:.0f},   время: {:.2f}".format(ax_coord[1], y, x)

    return format_coord


xcom, ycom, xobj, yobj, duty, dir = [], [], [], [], [], []
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
            if row != {'Time COM': '0', 'Time OBJ': '0', 'COM': '0', 'OBJ': '0', 'Duty': '0', 'Dir': 0}:
                xcom.append(float(row['Time COM']))
                ycom.append(int(row['COM']))
                xobj.append(float(row['Time OBJ']))
                yobj.append(int(row['OBJ']))
                duty.append(int(row['Duty']))
                dir.append(int(row['Dir']))

    fig, ax = plt.subplots(tight_layout=True)
    plt.grid(b=True, which='major', axis='both')
    ax2 = ax.twinx()
    ax2.format_coord = make_format(ax, ax2)
    ax.set_ylim(0, 4100)
    ax2.set_ylim(0, 4100)
    line1, = ax.plot(xcom, ycom, label='Управляющий сигнал')
    line2, = ax.plot(xobj, yobj, label='Значение с потенциометра')
    line3, = ax2.plot(xcom, duty, label='Коэффициент заполнения', color='green', linewidth=0.5)
    line4, = ax2.plot(xcom, dir, label='Направление', color='red', linewidth=0.5)
    fig.canvas.manager.set_window_title(arg)
    plt.xlabel("[мс]")
    fig.legend()
    plt.show()
except Exception as e:
    print(e)
    sys.exit()
