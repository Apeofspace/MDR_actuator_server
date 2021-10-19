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
        x = np.arange(0, 2 * np.pi, 0.01)
        self.line1, = self.ax.plot(x, np.sin(x))
        self.line2, = self.ax.plot(x, np.sin(x + np.pi))
        self.canvas.get_tk_widget().pack(side='top', fill='x', expand=True)
        ani = FuncAnimation(self.fig, self.animate, interval=100, blit=False)
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
        buf = recv_pipe.recv()
        # тут должен обновляться список из которого рисуется график
        # self.line1.set_data(self.x, np.sin(self.x+i/10.0))
        # self.line2.set_data(self.x, np.sin(-self.x+i/10.0))

    def check_msg(self):
        if msg_queue.empty() is False:
            print(msg_queue.get())
        self.after(75, self.check_msg)

    def connect(self):
        global connected_flag, stop_flag, told, k, msg_queue
        p = re.search("COM[0-9]+", self.COMbobox.get())
        if p:
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
                    # надо сделать еще какойто лейбел чтоли, этот же никогда не увидится
                    self.disconnect()
            if msg_queue.empty() is False:
                msg = msg_queue.get()
                print(msg)
                if msg == serial.SerialException:
                    self.label_status.configure(text=msg)
                    self.disconnect()
                else:
                    self.label_status.configure(text='Подключено к {}'.format(msg))
                    self.button_connect.configure(text="Отключиться")

    def start_process(self, com_port):
        global stop_flag, connected_flag, lock, send_pipe, msg_queue
        print("thread started")
        self.reader_process = multiprocessing.Process(target=read_process, args=(
            stop_flag, connected_flag, com_port, lock, send_pipe, msg_queue), daemon=True)
        self.reader_process.start()
        self.reader_process.join()
        print("thread ended")

    def disconnect(self):
        global stop_flag, connected_flag
        try:
            if self.start_process_thread is not None:
                lock.acquire()
                connected_flag.value = 0
                stop_flag.value = 1
                lock.release()
                self.label_status.configure(text='Закрытие порта...')
                self.start_process_thread = None
                # чето тут мутное
                self.label_status.configure(text='Порт закрыт успешно')
        except Exception as e:
            self.label_status.configure(text=e)
        finally:
            # ser.close()
            self.button_connect["text"] = "Подключиться"

    def on_closing(self):
        self.disconnect()
        root.quit()
        root.destroy()


def read_process(stop_flag, connected_flag, com_port, lock, pipe, msg_queue):
    # msg_queue.put('Hello')
    ser = serial.Serial()
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
                if stop_flag.value:
                    lock.release()
                    ser.close()
                    break
                if connected_flag.value:
                    lock.release()
                    line = ser.read(size=16)
                    decoded = {'Time COM': int.from_bytes(line[:4], "little"),
                               'Time OBJ': int.from_bytes(line[4:8], "little"),
                               'COM': int.from_bytes(line[8:12], "little"),
                               'OBJ': int.from_bytes(line[12:16], "little")}
                    csv_writer.writerow(decoded)
                    pipe.send(decoded)
                    ser.write()
    except serial.SerialException as e:
        ser.close()
        msg_queue.send(e)


if __name__ == "__main__":
    # q = multiprocessing.Queue()
    recv_pipe, send_pipe = multiprocessing.Pipe(duplex=False)
    # recv_msg_pipe, send_msg_pipe = multiprocessing.Pipe(duplex=False)
    msg_queue = multiprocessing.SimpleQueue()
    stop_flag = multiprocessing.Value("i", 0)
    connected_flag = multiprocessing.Value("i", 0)
    lock = multiprocessing.Lock()
    root = tk.Tk()
    MainWindow = MainWindow(root)
    MainWindow.pack(side="top", fill="both", expand=True)
    root.wm_protocol("WM_DELETE_WINDOW", MainWindow.on_closing)
    root.mainloop()
