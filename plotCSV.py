import csv
import sys
import matplotlib.pyplot as plt
import os
import re

xcom, ycom, xobj, yobj, duty = [], [], [], [], []
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
        i = 0
        for row in reader:
            if i == 0:
                initial_com_time = float(row['Time COM']) / 80000
                initial_obj_time = float(row['Time OBJ']) / 80000
            if row != {'Time COM': '0', 'Time OBJ': '0', 'COM': '0', 'OBJ': '0', 'Duty': '0'}:
                xcom.append(float(row['Time COM']) / 80000 - initial_com_time)
                ycom.append(int(row['COM']))
                xobj.append(float(row['Time OBJ']) / 80000 - initial_obj_time)
                yobj.append(int(row['OBJ']))
                duty.append(399- int(row['Duty']))
                i += 1

    fig, ax = plt.subplots(tight_layout=True)
    ax2 = ax.twinx()
    ax.set_ylim(0, 4100)
    ax2.set_ylim(0, 400)
    line1, = ax.plot(xcom, ycom, label='Управляющий сигнал')
    line2, = ax.plot(xobj, yobj, label='Значение с потенциометра')
    line3, = ax2.plot(xcom, duty,  label='Коэффициент заполнения', color = 'green', linewidth = 0.5)
    fig.canvas.manager.set_window_title(arg)
    plt.xlabel("[мс]")
    plt.grid(b=True, which='major', axis='both')
    fig.legend()
    plt.show()
except Exception as e:
    print(e)
    sys.exit()
