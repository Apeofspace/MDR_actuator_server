import threading
from threading import Thread
import tkinter as tk
from tkinter import ttk
import serial
import serial.tools.list_ports
from time import sleep
import re


def manage():
    global recieveonly
    while True:
        if stopflag:
            break
        if connected:
            try:
                if recieveonly.get():
                    line = ser.read(size = 2)
                    scale.set(int.from_bytes(line, "little"))
                else:
                    sleep(0.1)
                    i = scale.get()
                    ser.write(i)
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
    global connected
    global senderthread
    global stopflag
    try:
        senderthread = threading.Thread(target=manage, daemon=True, name="senderthread")
        ser.baudrate = cbbaud.get()
        p = re.search("COM[0-9]+", cb.get())
        if p:
            ser.port = p[0]
        if ser.portstr is not None:
            labelStatus.configure(text='Подключение...')
            ser.open()
            stopflag = False
            senderthread.start()
            connected = True
            labelStatus.configure(text='Подключено к {}'.format(ser.portstr))
            buttonConnect["text"] = "Disconnect"
    except serial.SerialException as e:
        labelStatus.configure(text=e)
        ser.close()


def disconnect():
    global senderthread
    try:
        if senderthread is not None:
            if senderthread.is_alive():
                global stopflag
                global connected
                connected = False
                stopflag = True
                labelStatus.configure(text='Закрытие порта...')
                # if senderthread is not None:
                #     while senderthread.is_alive():
                #         pass
                senderthread = None
                labelStatus.configure(text='Порт закрыт успешно')
        buttonConnect["text"] = "Connect"
    except Exception as e:
        labelStatus.configure(text=e)
    finally:
        ser.close()


senderthread = None
ser = serial.Serial()
stopflag = False
connected = False
root = tk.Tk()
frame1 = tk.Frame(root, padx=20, pady=100)
frame1.pack(expand=True, fill='both', side='top')
scale = tk.Scale(frame1, from_=0, to=0xfff, orient=tk.HORIZONTAL)
scale.pack(fill='x')
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
cbbaud['values'] = (300, 600, 1200, 1800, 2400, 3600, 4800, 7200, 9600, 14400, 19200, 28800, 38400, 57600, 115200, 230400, 500000)
cbbaud.set(115200)
cbbaud.pack(side='left', padx=20)
buttonConnect = tk.Button(frame2, text="Connect", command=btnconnect, width = 30)
buttonConnect.pack(side='left', padx=30)
labelStatus = tk.Label(frame2, text="Not connected", width = 30)
labelStatus.pack(side='left', padx=5)
recieveonly = tk.IntVar()
checkbox1 = tk.Checkbutton(root, text = "Только приём", variable = recieveonly)
checkbox1.pack(side = "left", padx = 15, pady=20)
root.protocol("WM_DELETE_WINDOW", on_closing)
root.mainloop()
