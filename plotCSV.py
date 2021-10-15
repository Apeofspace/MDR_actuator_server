import csv
import sys
import matplotlib.pyplot as plt

xcom, ycom, xobj, yobj = [], [], [], []
with open(sys.argv[1],"r", newline='') as csv_file:
# with open("Data_2021_10_15-131402.csv", "r", newline='') as csv_file:
    reader = csv.DictReader(csv_file)
    for row in reader:
        if row != {'Time COM': '0', 'Time OBJ': '0', 'COM': '0', 'OBJ': '0'}:
            xcom.append(int(row['Time COM']))
            ycom.append(int(row['COM']))
            xobj.append(int(row['Time OBJ']))
            yobj.append(int(row['OBJ']))

# fig = plt.Figure(tight_layout=True)
# ax = fig.add_subplot(111)
fig, ax = plt.subplots(tight_layout=True)
line1, = ax.plot(xcom, ycom, label='COM')
line2, = ax.plot(xobj, yobj, label='OBJ')

# every_nth = 100
# for n, label in enumerate(ax.xaxis.get_ticklabels()):
#     if n % every_nth != 0:
#         label.set_visible(False)
#
# every_nth = 10
# for n, label in enumerate(ax.yaxis.get_ticklabels()):
#     if n % every_nth != 0:
#         label.set_visible(False)

fig.legend()
plt.show()
