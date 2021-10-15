import threading
import tkinter as tk
from tkinter import ttk
import serial
import serial.tools.list_ports
import re
import math
import time
import csv
import datetime


def sendthread():
    global sinenabled, sinhertz
    while True:
        if stopflag:
            break
        if connected:
            try:
                if sinenabled.get():
                    scale.set(sinwaveControl(hertz))  # сделать глобальную переменную и метод который вызывается когда менется значение в поле. тогда и будет меняться глобальная переменная
                ser.write(getAngleFromScale())
            except serial.SerialException:
                disconnect()


def getAngleFromScale():
    global scale
    return (str(scale.get()).encode()).zfill(4)


def sinwaveControl(f):
    global told, k
    tnew = time.time()
    dt = tnew - told  # сколько прошло секунд
    told = tnew
    k = k + dt * float(f)
    sinwave = math.sin(2 * math.pi * k)  # -1..1
    sinwave += 1  # 0..2
    # sinwave = (sinwave * 0xfff) / 2  # 0..0xFFF
    leftLim = 0x100
    rightLim = 0xEFF
    sinwave = (sinwave * (rightLim-leftLim))/2 + leftLim
    return sinwave

ri = 0
def readthread():
    global ri
    with open("Data_{}.csv".format(datetime.datetime.now().strftime("%Y_%m_%d-%H%M%S")), 'w', newline='') as csv_file:
        csv_writer = csv.DictWriter(csv_file, fieldnames=["Time COM", "Time OBJ", "COM", "OBJ"])
        csv_writer.writeheader()
        while True:
            if stopflag:
                break
            if connected:
                try:
                    line = ser.read(size=16)
                    csv_writer.writerow({'Time COM':int.from_bytes(line[:4], "little"),  'Time OBJ':int.from_bytes(line[4:8], "little"), 'COM':int.from_bytes(line[8:12], "little"), 'OBJ':int.from_bytes(line[12:16], "little")})
                    ri+=1
                    if ri>20: #временный хак
                        scaleread.set(int.from_bytes(line[12:16], "little"))
                        ri=0
                except serial.SerialException:
                    disconnect()



def on_closing():
    disconnect()
    root.quit()
    root.destroy()


def btnconnect():
    if buttonConnect["text"] == "Connect":
        connect()
    else:
        disconnect()


def connect():
    global senderthread, readerthread, connected, stopflag, told, k
    try:
        readerthread = threading.Thread(target=readthread, daemon=True, name="readerthread")
        senderthread = threading.Thread(target=sendthread, daemon=True, name="senderthread")
        ser.baudrate = cbbaud.get()
        p = re.search("COM[0-9]+", cb.get())
        if p:
            ser.port = p[0]
        if ser.portstr is not None:
            labelStatus.configure(text='Подключение...')
            ser.open()
            stopflag = False
            readerthread.start()
            senderthread.start()
            k = 0
            told = time.time()
            connected = True
            labelStatus.configure(text='Подключено к {}'.format(ser.portstr))
            buttonConnect["text"] = "Disconnect"
    except serial.SerialException as e:
        labelStatus.configure(text=e)
        ser.close()


def disconnect():
    global senderthread, readerthread
    try:
        if senderthread is not None or readerthread is not None:
            global stopflag
            global connected
            connected = False
            stopflag = True
            labelStatus.configure(text='Закрытие порта...')
            senderthread = None
            readerthread = None
            labelStatus.configure(text='Порт закрыт успешно')
        buttonConnect["text"] = "Connect"
    except Exception as e:
        labelStatus.configure(text=e)
    finally:
        ser.close()


def sinhertzcallback(sinhertz):
    global hertz
    d = re.match("(\d+(\.)?(\d+)?)",sinhertz.get())
    if d is not None:
        sinhertz.set(d.group(1))
        hertz = d.group(1)
    else:
        hertz = 0

def sincheckboxChecked():
    global k, told
    # k = 0
    told = time.time()


told = k = 0
senderthread = None
readerthread = None
stopflag = False
connected = False
hertz = 1

ser = serial.Serial()
root = tk.Tk()

# frame3
frame3 = tk.Frame(root, padx=20, pady=20)
frame3.pack(expand=True, fill='both', side='top')
sinenabled = tk.IntVar()
sincheckbox = tk.Checkbutton(frame3, text="Синусоида", variable=sinenabled, command = sincheckboxChecked)
sincheckbox.pack(side="left")
sinhertz = tk.StringVar()
sinhertz.set('1')
sinhertz.trace("w", lambda name, index, mode, sinhertz = sinhertz: sinhertzcallback(sinhertz))
sinhertzentry = tk.Entry(frame3, text='1', textvariable=sinhertz)
sinhertzentry.pack(side="left", padx=5)
sinlabel = tk.Label(frame3, text="Гц").pack(side='left', padx=5)
# frame1
frame1 = tk.Frame(root, padx=20, pady=50)
frame1.pack(expand=True, fill='both', side='top')
labelscale = tk.Label(frame1, text="Командный сигнал")
labelscale.pack()
scale = tk.Scale(frame1, from_=0, to=0xfff, orient=tk.HORIZONTAL)
scale.set(2000)
scale.pack(fill='x')
labelscaleread = tk.Label(frame1, text="Отклонение объекта управления")
labelscaleread.pack()
scaleread = tk.Scale(frame1, from_=0, to=0xfff, orient=tk.HORIZONTAL)
scaleread.pack(fill='x')

# frame2
frame2 = tk.Frame(root, pady=20)
frame2.pack(expand=True, fill='both', side='top')
CBvar = tk.StringVar()
cb = tk.ttk.Combobox(frame2, textvariable=CBvar)
cb['values'] = list(serial.tools.list_ports.comports())
cb['state'] = 'readonly'
cb.set('COM13')
cb.pack(side='left', padx=20)
CBvarbaud = tk.StringVar()
cbbaud = tk.ttk.Combobox(frame2, textvariable=CBvarbaud)
cbbaud['values'] = (
    300, 600, 1200, 1800, 2400, 3600, 4800, 7200, 9600, 14400, 19200, 28800, 38400, 57600, 115200, 230400, 500000)
cbbaud.set(115200)
cbbaud.pack(side='left', padx=20)
buttonConnect = tk.Button(frame2, text="Connect", command=btnconnect, width=30)
buttonConnect.pack(side='left', padx=30)
labelStatus = tk.Label(frame2, text="Not connected", width=30)
labelStatus.pack(side='left', padx=5)

root.protocol("WM_DELETE_WINDOW", on_closing)
root.mainloop()
