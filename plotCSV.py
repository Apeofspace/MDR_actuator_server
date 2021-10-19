import csv
import sys
import matplotlib.pyplot as plt
import os
import re

xcom, ycom, xobj, yobj = [], [], [], []
try:
    arg = sys.argv[1]
except:
    print("""Use -latest or a filename as an argument""")
    sys.exit()
if arg == '-latest' or 'l':
    latest = None
    for i in re.findall("Data_\d+_\d\d_\d\d-\d+\.csv", ' '.join(os.listdir())):
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
        print("Opening file: {}".format(arg))
try:
    with open(arg,"r", newline='') as csv_file:
        reader = csv.DictReader(csv_file)
        i = 0
        for row in reader:
            if i == 0:
                initial_com_time = float(row['Time COM'])/80000
                initial_obj_time = float(row['Time OBJ']) / 80000
            if row != {'Time COM': '0', 'Time OBJ': '0', 'COM': '0', 'OBJ': '0'}:
                xcom.append(float(row['Time COM'])/80000-initial_com_time)
                ycom.append(int(row['COM']))
                xobj.append(float(row['Time OBJ'])/80000-initial_obj_time)
                yobj.append(int(row['OBJ']))
                i += 1

    fig, ax = plt.subplots(tight_layout=True)
    line1, = ax.plot(xcom, ycom, label='Управляющий сигнал')
    line2, = ax.plot(xobj, yobj, label='Значение с потенциометра')

    # every_nth = 100
    # for n, label in enumerate(ax.xaxis.get_ticklabels()):
    #     if n % every_nth != 0:
    #         label.set_visible(False)
    #
    # every_nth = 10
    # for n, label in enumerate(ax.yaxis.get_ticklabels()):
    #     if n % every_nth != 0:
    #         label.set_visible(False)

    # ymin, ymax = ax.get_ylim()
    # ax.set_yticks(np.round(np.linspace(ymin, ymax, N), 2))
    plt.xlabel("[мс]")
    plt.grid(b=True, which='major', axis='both')
    fig.legend()
    plt.show()
except Exception as e:
    print(e)
    sys.exit()
