import queue
import threading
import multiprocessing
import tkinter
import tkinter as tk
from tkinter import ttk
import serial
import serial.tools.list_ports
import re
import time
import csv
import datetime
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import numpy as np
import math
from queue import Empty, Full


class MainWindow(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        # PLOT
        self.fig, self.ax = plt.subplots(figsize=(10, 5), tight_layout=True)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.toolbar = NavigationToolbar2Tk(self.canvas, self)
        self.toolbar.update()
        self.toolbar.pack(side='top')

        self.x = np.arange(0, 2 * np.pi, 0.01)
        self.line1, = self.ax.plot(self.x, np.sin(self.x), label='Управляющий сигнал')
        self.line2, = self.ax.plot(self.x, np.sin(self.x) + np.pi, label='Значение с потенциометра')
        self.fig.legend()
        plt.xlabel("[мс]")
        plt.grid(b=True, which='major', axis='both')
        self.ax.set_ylim(0, 4100)

        self.buffer_size = 15000
        self.show_on_plot = 2000
        self.buffer_x_com = []
        self.buffer_y_com = []
        self.buffer_x_obj = []
        self.buffer_y_obj = []

        self.canvas.get_tk_widget().pack(side='top', fill='both', expand=True)
        self.ani = FuncAnimation(self.fig, self.animate, interval=17, blit=False)
        # COMbobox, button and label
        self.frame1 = tk.Frame(root)
        self.frame1.pack(side='bottom', padx=10, pady=10, fill='x')
        self.label_com = tk.Label(self.frame1, text='COM ')
        self.label_com.pack(side='left', padx=10)
        self.COMboboxvar = tk.StringVar()
        self.COMbobox = tk.ttk.Combobox(self.frame1, textvariable=self.COMboboxvar)
        self.COMbobox['values'] = list(serial.tools.list_ports.comports())
        self.COMbobox['state'] = 'readonly'
        self.COMbobox.set('COM13')
        self.COMbobox.pack(side='left')
        self.button_connect = tk.Button(self.frame1, text="Подключиться", command=self.button_press)
        self.button_connect.pack(side='left', padx=(20, 10))
        self.label_status = tk.Label(self.frame1, text="Не подключено")
        self.label_status.pack(side='left', padx=5, fill='x')
        # other
        self.reader_process = None
        self.start_process_thread = None

    def button_press(self):
        if self.button_connect["text"] == "Подключиться":
            self.connect()
        else:
            self.disconnect()

    def animate(self, i):
        global main_queue
        while main_queue.qsize():
            try:
                # конечно слоу это весьма
                buf = main_queue.get()
                self.buffer_x_com.append(buf["Time COM"])
                self.buffer_y_com.append(buf["COM"])
                self.buffer_x_obj.append(buf["Time OBJ"])
                self.buffer_y_obj.append(buf["OBJ"])
                if len(self.buffer_x_com) > self.buffer_size:
                    self.buffer_x_com.pop(0)
                    self.buffer_y_com.pop(0)
                    self.buffer_x_obj.pop(0)
                    self.buffer_y_obj.pop(0)
                if len(self.buffer_x_com) > self.show_on_plot:
                    self.ax.set_xlim(self.buffer_x_com[-self.show_on_plot], self.buffer_x_com[-1])
                    self.line1.set_data(self.buffer_x_com, self.buffer_y_com)
                    self.line2.set_data(self.buffer_x_obj, self.buffer_y_obj)
                elif len(self.buffer_x_com) > 1:
                    self.ax.set_xlim(self.buffer_x_com[0], self.buffer_x_com[-1])
                    # self.ax.set_xlim(min(self.buffer_x_com), max(self.buffer_x_com))
                    self.line1.set_data(self.buffer_x_com, self.buffer_y_com)
                    self.line2.set_data(self.buffer_x_obj, self.buffer_y_obj)
            except Empty:
                print("empty que =(")

    def check_msg(self):
        if msg_queue.empty() is False:
            print("cheching msg {}".format(msg_queue.get()))
        self.after(75, self.check_msg)

    def connect(self):
        global connected_flag, stop_flag, told, k, msg_queue, lock
        p = re.search("COM[0-9]+", self.COMbobox.get())
        if p:
            self.buffer_x_com = []
            self.buffer_y_com = []
            self.buffer_x_obj = []
            self.buffer_y_obj = []
            com_port = p[0]
            self.label_status.configure(text='Подключение...')
            lock.acquire()
            stop_flag.value = 0
            self.start_process_thread = threading.Thread(target=self.start_process, args=(com_port,), daemon=True)
            self.start_process_thread.start()
            # k = 0
            # told = time.time()
            connected_flag.value = 1
            lock.release()
            i = 0
            while msg_queue.empty():
                pass
                i += 1
                if i == 1000000:
                    self.label_status.configure(text="Queue timeout error")
                    print("Queue timeout error")
                    self.disconnect()
            if msg_queue.empty() is False:
                msg = msg_queue.get()
                print("message in connect: {}".format(msg))
                if msg == serial.SerialException:
                    self.label_status.configure(text=msg)
                    self.disconnect()
                else:
                    self.label_status.configure(text='Подключено к {}'.format(msg))
                    self.button_connect.configure(text="Отключиться")

    def start_process(self, com_port):
        global stop_flag, connected_flag, lock, main_queue, msg_queue
        print("thread started")
        self.reader_process = multiprocessing.Process(target=read_process, args=(
            stop_flag, connected_flag, com_port, lock, main_queue, msg_queue), daemon=True)
        self.reader_process.start()
        self.reader_process.join()
        print("thread ended")

    def disconnect(self):
        global stop_flag, connected_flag, lock
        try:
            if self.start_process_thread is not None:
                lock.acquire()
                connected_flag.value = 0
                stop_flag.value = 1
                lock.release()
                self.label_status.configure(text='Закрытие порта...')
                self.reader_process.join()
                while self.start_process_thread.is_alive():
                    pass
                self.start_process_thread = None
                self.label_status.configure(text='Порт закрыт успешно')
        except Exception as e:
            self.label_status.configure(text=e)
        finally:
            self.button_connect["text"] = "Подключиться"

    def on_closing(self):
        self.disconnect()
        root.quit()
        root.destroy()


def read_process(stop_flag, connected_flag, com_port, lock, queue, msg_queue):
    ser = serial.Serial()
    told = time.perf_counter()
    k = 0
    first_time = True

    try:
        ser.baudrate = 115200
        ser.port = com_port
        ser.open()
        msg_queue.put(ser.portstr)
        with open("Data_{}.csv".format(datetime.datetime.now().strftime("%Y_%m_%d-%H%M%S")), 'w',
                  newline='') as csv_file:
            csv_writer = csv.DictWriter(csv_file, fieldnames=["Time COM", "Time OBJ", "COM", "OBJ"])
            csv_writer.writeheader()
            while True:
                lock.acquire()
                stop = stop_flag.value
                connected = connected_flag.value
                lock.release()
                if stop:
                    print("stopping process")
                    ser.close()
                    print("serial closed")
                    break
                if connected:
                    line = ser.read(size=20)
                    if first_time:
                        initial_com_time = float(int.from_bytes(line[4:12], "little")) / 80000
                        initial_obj_time = float(int.from_bytes(line[12:20], "little")) / 80000
                        first_time = False
                    decoded = {'Time COM': float(int.from_bytes(line[4:12], "little")) / 80000 - initial_com_time,
                               'Time OBJ': float(int.from_bytes(line[12:20], "little")) / 80000 - initial_obj_time,
                               'COM': int.from_bytes(line[2:4], "little"),
                               'OBJ': int.from_bytes(line[0:2], "little")}
                    csv_writer.writerow(decoded)
                    queue.put(decoded)
                    tnew = time.perf_counter()
                    dt = tnew - told
                    told = tnew
                    k = k + dt * float(1)  # цифра это герцы
                    sinwave = math.sin(2 * math.pi * k)
                    sinwave += 1
                    leftLim = 0x100
                    rightLim = 0xEFF
                    sinwave = (sinwave * (rightLim - leftLim)) / 2 + leftLim
                    ser.write(str(int(sinwave)).encode().zfill(4))
    except serial.SerialException as e:
        ser.close()
        msg_queue.put(e)


if __name__ == "__main__":
    q_manager = multiprocessing.Manager()
    main_queue = q_manager.Queue()
    msg_queue = multiprocessing.SimpleQueue()
    stop_flag = multiprocessing.Value("i", 0)
    connected_flag = multiprocessing.Value("i", 0)
    lock = multiprocessing.Lock()
    root = tk.Tk()
    MainWindow = MainWindow(root)
    MainWindow.pack(side="top", fill="both", expand=True)
    root.wm_protocol("WM_DELETE_WINDOW", MainWindow.on_closing)
    root.mainloop()
