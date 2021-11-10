import threading
import multiprocessing
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
    def __init__(self, parent, connected_flag, stop_flag, msg_queue, main_queue, lock, hertz, mode, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.connected_flag = connected_flag
        self.stop_flag = stop_flag
        self.msg_queue = msg_queue
        self.lock = lock
        self.main_queue = main_queue
        self.hertz = hertz
        self.reader_process = None
        self.mode = mode
        # PLOT
        self.fig, self.ax = plt.subplots(figsize=(10, 5), tight_layout=True)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.toolbar = NavigationToolbar2Tk(self.canvas, self)
        self.toolbar.update()
        self.toolbar.pack(side='top')
        self.x = np.arange(0, 2 * np.pi, 0.01)
        plt.grid(b=True, which='major', axis='both')
        self.ax2 = self.ax.twinx()
        self.ax2.format_coord = self.make_format(self.ax, self.ax2)
        self.line_duty, = self.ax2.plot(self.x, 2000 * np.sin(self.x) + np.pi, label='Коэффициент заполнения',
                                        color='green', linewidth=0.5)
        self.line_dir, = self.ax2.plot(self.x, 2000 * np.sin(self.x) + np.pi, label='Направление',
                                       color='red', linewidth=0.5)
        # , linewidth = 0.5, marker = "o", markersize = 0.5
        self.line1, = self.ax.plot(self.x, 2000 * np.sin(self.x), label='Управляющий сигнал')
        self.line2, = self.ax.plot(self.x, 2000 * np.sin(self.x) + np.pi, label='Значение с потенциометра')
        self.fig.legend()
        self.ax.set_ylim(0, 4100)
        self.ax2.set_ylim(0, 4100)
        self.buffer_size = 15000
        self.show_on_plot = 2000
        self.buffers = {name: [] for name in
                        ['Time COM',
                         'COM',
                         'Time OBJ',
                         'OBJ',
                         'Duty',
                         'Dir']}
        self.canvas.get_tk_widget().pack(side='top', fill='both', expand=True)
        self.ani = FuncAnimation(self.fig, self.animate, interval=16, blit=False)
        plt.xlabel("[мс]")
        # plt.grid(b=True, which='major', axis='both')
        # COMbobox, button and label
        self.frame1 = tk.Frame(root)
        self.frame1.pack(side='bottom', padx=10, pady=10, fill='x')
        self.label_com = tk.Label(self.frame1, text='Порт ')
        self.label_com.pack(side='left', padx=10)
        self.COMboboxvar = tk.StringVar()
        self.COMbobox = tk.ttk.Combobox(self.frame1, textvariable=self.COMboboxvar)
        self.COMbobox['values'] = list(serial.tools.list_ports.comports())
        self.COMbobox['state'] = 'readonly'
        self.COMbobox.set('COM13')
        self.COMbobox.pack(side='left')
        self.button_connect = tk.Button(self.frame1, text="Подключиться", command=self.button_press, width=25)
        self.button_connect.pack(side='left', padx=(20, 10))
        # hertz
        self.hertz_label = tk.Label(self.frame1, text='Частота [Гц]: ')
        self.hertz_label.pack(side='left', padx=10)
        self.hertz_var = tk.StringVar()
        self.hertz_var.set('1')
        self.hertz_var.trace("w", lambda name, index, mode, hertz_var=self.hertz_var: self.hertz_callback(hertz_var))
        self.hertz_entry = tk.Entry(self.frame1, text='1', textvariable=self.hertz_var)
        self.hertz_entry.pack(side='left', padx=(0, 15))
        # mode combobox
        self.mode_combobox_var = tk.StringVar()
        self.mode_combobox = tk.ttk.Combobox(self.frame1, textvariable=self.mode_combobox_var)
        self.mode_combobox['values'] = ["Синусоида", "Меандр"]
        self.mode_combobox['state'] = 'readonly'
        self.mode_combobox.current(newindex=0)
        self.mode_combobox.bind('<<ComboboxSelected>>', lambda func: self.mode_combobox_modified())
        self.mode_combobox.pack(side='left')
        # labelstatus
        self.label_status = tk.Label(self.frame1, text="Не подключено")
        self.label_status.pack(side='left', padx=5, fill='x')

    def mode_combobox_modified(self):
        self.mode.value = self.mode_combobox.current()
        # print(self.mode.value)

    def hertz_callback(self, hertz_var):
        global hertz
        d = re.match("(\d+(\.)?(\d+)?)", hertz_var.get())
        if d is not None:
            hertz_var.set(d.group(1))
            hertz.value = float(d.group(1))
        else:
            hertz_var.set('')
            hertz.value = 0

    def make_format(self, other, current):
        # current and other are axes
        def format_coord(x, y):
            # x, y are data coordinates
            # convert to display coords
            display_coord = current.transData.transform((x, y))
            inv = other.transData.inverted()
            # convert back to data coords with respect to ax
            ax_coord = inv.transform(display_coord)
            return ("Координата: {:.0f},   коэф. заполнения: {:.0f},   время: {:.2f}".format(ax_coord[1], y, x))

        return format_coord

    def button_press(self):
        if self.button_connect["text"] == "Подключиться":
            self.connect()
        else:
            self.disconnect()

    def animate(self, i):
        while self.main_queue.qsize():
            try:
                buf = self.main_queue.get()
                for key in self.buffers.keys():
                    self.buffers[key].append(buf[key])
                if len(self.buffers["Time COM"]) > self.buffer_size:
                    for value in self.buffers.values():
                        value.pop()
                if len(self.buffers["Time COM"]) > self.show_on_plot:
                    self.ax.set_xlim(self.buffers["Time COM"][-self.show_on_plot], self.buffers["Time COM"][-1])
                elif len(self.buffers["Time COM"]) > 1:
                    self.ax.set_xlim(self.buffers["Time COM"][0], self.buffers["Time COM"][-1])
                self.line1.set_data(self.buffers["Time COM"], self.buffers["COM"])
                self.line2.set_data(self.buffers["Time OBJ"], self.buffers["OBJ"])
                self.line_duty.set_data(self.buffers["Time COM"], self.buffers["Duty"])
                self.line_dir.set_data(self.buffers["Time COM"], self.buffers["Dir"])
            except Empty:
                print("empty que =(")

    def check_msg(self):
        if self.msg_queue.empty() is False:
            msg = self.msg_queue.get()
            if isinstance(msg, Exception):
                self.disconnect()
        self.after(250, self.check_msg)

    def connect(self):
        p = re.search("COM[0-9]+", self.COMbobox.get())
        if p:
            for key in self.buffers.keys():
                self.buffers[key] = []
            com_port = p[0]
            self.label_status.configure(text='Подключение...')
            self.lock.acquire()
            stop_flag.value = 0
            print("process starting...")
            self.reader_process = multiprocessing.Process(target=read_process, args=(
                self.stop_flag, self.connected_flag, com_port, self.lock, self.main_queue, self.msg_queue, self.hertz,
                self.mode), daemon=True)
            self.reader_process.start()
            self.check_msg()
            self.connected_flag.value = 1
            self.lock.release()
            i = 0
            while self.msg_queue.empty():
                pass
                i += 1
                if i == 1000000:
                    self.label_status.configure(text="Queue timeout error")
                    print("Queue timeout error")
                    self.disconnect()
            if self.msg_queue.empty() is False:
                msg = self.msg_queue.get()
                print(f"Connected to : {msg}")
                if msg == serial.SerialException:
                    self.label_status.configure(text=msg)
                    self.disconnect()
                else:
                    self.label_status.configure(text=f'Подключено к {msg}')
                    self.button_connect.configure(text="Отключиться")

    def disconnect(self):
        try:
            if self.reader_process is not None:
                self.lock.acquire()
                self.connected_flag.value = 0
                self.stop_flag.value = 1
                self.lock.release()
                self.label_status.configure(text='Закрытие порта...')
                self.reader_process.join()
                print("process closed")
                self.reader_process = None
                self.label_status.configure(text='Порт закрыт успешно')
        except Exception as e:
            self.label_status.configure(text=e)
        finally:
            self.button_connect["text"] = "Подключиться"

    def on_closing(self):
        self.disconnect()
        root.quit()
        root.destroy()


def read_process(stop_flag, connected_flag, com_port, lock, queue, msg_queue, hertz, mode):
    print("process started")
    ser = serial.Serial()
    told = time.perf_counter()
    k = 0
    first_time = True
    signal = 0
    fields = ["Time COM", "Time OBJ", "COM", "OBJ", "Duty", "Dir"]
    try:
        ser.baudrate = 115200
        ser.port = com_port
        ser.open()
        msg_queue.put(ser.portstr)
        with open("Data_{}.csv".format(datetime.datetime.now().strftime("%Y_%m_%d-%H%M%S")), 'w',
                  newline='') as csv_file:
            csv_writer = csv.DictWriter(csv_file, fieldnames=fields)
            csv_writer.writeheader()
            while True:
                lock.acquire()
                stop = stop_flag.value
                connected = connected_flag.value
                Hz = hertz.value
                lock.release()
                if stop:
                    print("stopping process")
                    ser.close()
                    print("serial closed")
                    break
                if connected:
                    line = ser.read(size=28)
                    if first_time:
                        initial_com_time = float(int.from_bytes(line[4:12], "little")) / 80000
                        initial_obj_time = float(int.from_bytes(line[12:20], "little")) / 80000
                        first_time = False
                    decoded = {'Time COM': float(int.from_bytes(line[4:12], "little")) / 80000 - initial_com_time,
                               'Time OBJ': float(int.from_bytes(line[12:20], "little")) / 80000 - initial_obj_time,
                               'COM': int.from_bytes(line[2:4], "little"),
                               'OBJ': int.from_bytes(line[0:2], "little"),
                               'Duty': int.from_bytes(line[20:24], "little"),
                               'Dir': int.from_bytes(line[24:28], "little") * 100}
                    csv_writer.writerow(decoded)
                    queue.put(decoded)
                    t_new = time.perf_counter()
                    dt = t_new - told
                    left_lim = 0x200
                    right_lim = 0xFFF - left_lim
                    if mode.value == 0:
                        # синусоида
                        told = t_new
                        k = k + dt * float(Hz)  # цифра это герцы
                        signal = math.sin(2 * math.pi * k)
                        signal += 1
                        signal = (signal * (right_lim - left_lim)) / 2 + left_lim
                        ser.write(str(int(signal)).encode().zfill(4))
                    elif mode.value == 1:
                        # меандр
                        if not (Hz == 0):
                            if dt > 1 / Hz:
                                told = t_new
                                if signal == right_lim:
                                    signal = left_lim
                                else:
                                    signal = right_lim
                                ser.write(str(int(signal)).encode().zfill(4))
    except serial.SerialException as e:
        print(f"Serial exception in process : {e}")
        ser.close()
        msg_queue.put(e)


if __name__ == "__main__":
    q_manager = multiprocessing.Manager()
    main_queue = q_manager.Queue()
    msg_queue = multiprocessing.SimpleQueue()
    stop_flag = multiprocessing.Value("i", 0)
    connected_flag = multiprocessing.Value("i", 0)
    hertz = multiprocessing.Value("f", 1)
    mode = multiprocessing.Value("i", 0)
    lock = multiprocessing.Lock()
    root = tk.Tk()
    root.title("Sin Animation")
    MainWindow = MainWindow(root, connected_flag, stop_flag, msg_queue, main_queue, lock, hertz, mode)
    MainWindow.pack(side="top", fill="both", expand=True)
    root.wm_protocol("WM_DELETE_WINDOW", MainWindow.on_closing)
    root.mainloop()
