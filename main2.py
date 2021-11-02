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
    def __init__(self, parent, connected_flag, stop_flag, msg_queue, main_queue, lock, hertz, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.connected_flag = connected_flag
        self.stop_flag = stop_flag
        self.msg_queue = msg_queue
        self.lock = lock
        self.main_queue = main_queue
        self.hertz = hertz
        self.reader_process = None
        self.start_process_thread = None
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
        self.buffer_x_com = []
        self.buffer_y_com = []
        self.buffer_x_obj = []
        self.buffer_y_obj = []
        self.buffer_duty = []
        self.buffer_dir = []
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
        # labelstatus
        self.label_status = tk.Label(self.frame1, text="Не подключено")
        self.label_status.pack(side='left', padx=5, fill='x')

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
            return("Координата: {:.0f},   коэф. заполнения: {:.0f},   время: {:.2f}".format(ax_coord[1], y, x))
        return format_coord

    def button_press(self):
        if self.button_connect["text"] == "Подключиться":
            self.connect()
        else:
            self.disconnect()

    def animate(self, i):
        while self.main_queue.qsize():
            try:
                # ахтунг! спагетти код
                buf = self.main_queue.get()
                self.buffer_x_com.append(buf["Time COM"])
                self.buffer_y_com.append(buf["COM"])
                self.buffer_x_obj.append(buf["Time OBJ"])
                self.buffer_y_obj.append(buf["OBJ"])
                self.buffer_duty.append(buf["Duty"])
                self.buffer_dir.append(buf["Dir"])
                if len(self.buffer_x_com) > self.buffer_size:
                    self.buffer_x_com.pop(0)
                    self.buffer_y_com.pop(0)
                    self.buffer_x_obj.pop(0)
                    self.buffer_y_obj.pop(0)
                    self.buffer_duty.pop(0)
                    self.buffer_dir.pop(0)
                if len(self.buffer_x_com) > self.show_on_plot:
                    self.ax.set_xlim(self.buffer_x_com[-self.show_on_plot], self.buffer_x_com[-1])
                elif len(self.buffer_x_com) > 1:
                    self.ax.set_xlim(self.buffer_x_com[0], self.buffer_x_com[-1])
                self.line1.set_data(self.buffer_x_com, self.buffer_y_com)
                self.line2.set_data(self.buffer_x_obj, self.buffer_y_obj)
                self.line_duty.set_data(self.buffer_x_com, self.buffer_duty)
                self.line_dir.set_data(self.buffer_x_com, self.buffer_dir)
            except Empty:
                print("empty que =(")

    def check_msg(self):
        if self.msg_queue.empty() is False:
            print("cheching msg {}".format(self.msg_queue.get()))
        self.after(75, self.check_msg)

    def connect(self):
        p = re.search("COM[0-9]+", self.COMbobox.get())
        if p:
            self.buffer_x_com = []
            self.buffer_y_com = []
            self.buffer_x_obj = []
            self.buffer_y_obj = []
            self.buffer_duty = []
            self.buffer_dir = []
            com_port = p[0]
            self.label_status.configure(text='Подключение...')
            self.lock.acquire()
            stop_flag.value = 0
            self.start_process_thread = threading.Thread(target=self.start_process, args=(com_port,), daemon=True)
            self.start_process_thread.start()
            # k = 0
            # told = time.time()
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
                print("message in connect: {}".format(msg))
                if msg == serial.SerialException:
                    self.label_status.configure(text=msg)
                    self.disconnect()
                else:
                    self.label_status.configure(text='Подключено к {}'.format(msg))
                    self.button_connect.configure(text="Отключиться")

    def start_process(self, com_port):
        print("thread started")
        self.reader_process = multiprocessing.Process(target=read_process, args=(
            self.stop_flag, self.connected_flag, com_port, self.lock, self.main_queue, self.msg_queue, self.hertz),
                                                      daemon=True)
        self.reader_process.start()
        self.reader_process.join()
        print("thread ended")

    def disconnect(self):
        try:
            if self.start_process_thread is not None:
                self.lock.acquire()
                self.connected_flag.value = 0
                self.stop_flag.value = 1
                self.lock.release()
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


def read_process(stop_flag, connected_flag, com_port, lock, queue, msg_queue, hertz):
    ser = serial.Serial()
    told = time.perf_counter()
    k = 0
    first_time = True
    sinwave = 0
    try:
        ser.baudrate = 115200
        ser.port = com_port
        ser.open()
        msg_queue.put(ser.portstr)
        with open("Data_{}.csv".format(datetime.datetime.now().strftime("%Y_%m_%d-%H%M%S")), 'w',
                  newline='') as csv_file:
            csv_writer = csv.DictWriter(csv_file, fieldnames=["Time COM", "Time OBJ", "COM", "OBJ", "Duty", "Dir"])
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
                    tnew = time.perf_counter()
                    dt = tnew - told
                    #синусоида
                    told = tnew
                    k = k + dt * float(Hz)  # цифра это герцы
                    sinwave = math.sin(2 * math.pi * k)
                    sinwave += 1
                    leftLim = 0x200
                    rightLim = 0xFFF - leftLim
                    sinwave = (sinwave * (rightLim - leftLim)) / 2 + leftLim
                    ser.write(str(int(sinwave)).encode().zfill(4))

                    #миандр
                    # if dt>1/Hz:
                    #     told = tnew
                    #     if sinwave == 3500:
                    #         sinwave = 1000
                    #     else:
                    #         sinwave = 3500
                    #     ser.write(str(int(sinwave)).encode().zfill(4))
    except serial.SerialException as e:
        ser.close()
        msg_queue.put(e)


if __name__ == "__main__":
    q_manager = multiprocessing.Manager()
    main_queue = q_manager.Queue()
    msg_queue = multiprocessing.SimpleQueue()
    stop_flag = multiprocessing.Value("i", 0)
    connected_flag = multiprocessing.Value("i", 0)
    hertz = multiprocessing.Value("f", 1)
    lock = multiprocessing.Lock()
    root = tk.Tk()
    root.title("Sin Animation")
    MainWindow = MainWindow(root, connected_flag, stop_flag, msg_queue, main_queue, lock, hertz)
    MainWindow.pack(side="top", fill="both", expand=True)
    root.wm_protocol("WM_DELETE_WINDOW", MainWindow.on_closing)
    root.mainloop()
