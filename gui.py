import math
import multiprocessing
import tkinter as tk
from tkinter import ttk
import serial.tools.list_ports
import re
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from queue import Empty

from src_processes import *
import fourier
import numpy as np


class MainWindow(tk.Frame):
    t_s = 1 / 1000  # частота дискретизации (также надо поменять в LAFCH)
    buffer_size = 16000
    show_on_plot = 4000

    def __init__(self, parent, connected_flag, stop_flag, msg_queue, main_queue, lock, hertz, amp, mode, *args,
                 **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.connected_flag = connected_flag
        self.stop_flag = stop_flag
        self.msg_queue = msg_queue
        self.lock = lock
        self.main_queue = main_queue
        self.hertz = hertz
        self.amp = amp
        self.reader_process = None
        self.lakh_process = None
        self.mode = mode
        self.lakh_time_offset = 0
        self.lakh_stripe = True
        self.n = 0
        buffer_names = ['COM',
                        'OBJ',
                        'Duty',
                        'Time',
                        'Frequency',
                        'lah',
                        'lfh',
                        'log_omega']
        self.buffers = {name: [] for name in buffer_names}
        # TabControl
        self.tabControl = ttk.Notebook(self)
        self.tab_animation = tk.Frame(self)
        self.tab_lakh = tk.Frame(self)
        self.tabControl.add(self.tab_animation, text='Отслеживание')
        self.tabControl.add(self.tab_lakh, text='ЛАФЧХ')
        self.tabControl.pack(side='top', fill='both', expand=True)

        self.draw_animation_tab()
        self.draw_control_frame()
        self.draw_lakh_tab()

    def draw_animation_tab(self):
        # ANIMATION
        self.fig_anim, self.ax1_anim = plt.subplots(figsize=(12, 6), tight_layout=True)
        self.canvas_anim = FigureCanvasTkAgg(self.fig_anim, master=self.tab_animation)
        self.canvas_anim.get_tk_widget().pack(side='top', fill='both', expand=True)
        self.toolbar_anim = NavigationToolbar2Tk(self.canvas_anim, self.tab_animation)
        self.toolbar_anim.update()
        self.toolbar_anim.pack(side='top')
        plt.grid(b=True, which='major', axis='both')  # grid can be done thro axes.grid
        self.ax3_current = self.ax1_anim.twinx()
        self.ax3_current.set_ylim(-3, 3)
        self.ax2_anim = self.ax1_anim.twinx()
        self.ax2_anim.set_yticklabels([])  # hide y ticks
        self.ax2_anim.format_coord = self.make_format(self.ax1_anim, self.ax2_anim)
        self.line_duty, = self.ax2_anim.plot(0, 0, label='Коэффициент заполнения',
                                             color='green', linewidth=0.5)
        # self.line_dir, = self.ax2_anim.plot(0, 0, label='Направление движения',
        #                                     color='red', linewidth=0.5)
        self.line_COM, = self.ax1_anim.plot(0, 0, label='Управляющий сигнал')
        self.line_OBJ, = self.ax1_anim.plot(0, 0, label='Значение с потенциометра')
        # self.line_CUR, = self.ax3_current.plot(0, 0, label='Ток', color='purple', linewidth=0.7)
        self.fig_anim.legend(fontsize='small')
        self.ax1_anim.set_ylim(0, 4100)
        self.ax2_anim.set_ylim(0, 4100)
        self.animation = FuncAnimation(self.fig_anim, self.animate, interval=16, blit=False)
        self.animation.pause()  # dont let the animation run. doesnt work?
        plt.xlabel("[с]")
        # hertz
        self.hertz_label = tk.Label(self.tab_animation, text='Частота [Гц]: ')
        self.hertz_label.pack(side='left', padx=10)
        self.hertz_var = tk.StringVar()
        self.hertz_var.set(self.hertz.value)
        self.hertz_var.trace("w", lambda name, index, mode, hertz_var=self.hertz_var: self.hertz_callback(hertz_var))
        self.hertz_entry = tk.Entry(self.tab_animation, textvariable=self.hertz_var)
        self.hertz_entry.pack(side='left', padx=(0, 15))
        # amplitude
        self.amplitude_label = tk.Label(self.tab_animation, text='Амплитуда [град]: ')
        self.amplitude_label.pack(side='left', padx=(5, 10))
        self.amplitude_var = tk.StringVar()
        self.amplitude_var.set(self.amp.value)
        self.amplitude_var.trace("w",
                                 lambda name, index, mode, amplitude_var=self.amplitude_var: self.amplitude_callback(
                                     amplitude_var))
        self.amplitude_entry = tk.Entry(self.tab_animation, textvariable=self.amplitude_var)
        self.amplitude_entry.pack(side='left', padx=(0, 15))
        # mode combobox
        self.mode_label = tk.Label(self.tab_animation, text='Тип сигнала: ')
        self.mode_label.pack(side='left', padx=(5, 10))
        self.mode_combobox_var = tk.StringVar()
        self.mode_combobox = tk.ttk.Combobox(self.tab_animation, textvariable=self.mode_combobox_var)
        self.mode_combobox['values'] = ["Синусоида", "Меандр"]
        self.mode_combobox['state'] = 'readonly'
        self.mode_combobox.current(newindex=0)
        self.mode_combobox.bind('<<ComboboxSelected>>', lambda func: self.mode_combobox_modified_callback())
        self.mode_combobox.pack(side='left')

    def draw_control_frame(self):
        # COMbobox, button and label
        self.frame_controls = tk.Frame(self)
        self.frame_controls.pack(side='bottom', padx=10, pady=10, fill='x')
        self.label_com = tk.Label(self.frame_controls, text='Порт ')
        self.label_com.pack(side='left', padx=10)
        self.COMboboxvar = tk.StringVar()
        self.COMbobox = tk.ttk.Combobox(self.frame_controls, textvariable=self.COMboboxvar)
        self.COMbobox['values'] = list(serial.tools.list_ports.comports())
        self.COMbobox['state'] = 'readonly'
        self.COMbobox.bind('<Button-1>', lambda func: self.COMbobox_modified_callback())
        try:
            self.COMbobox.current(len(self.COMbobox['values']) - 1)
        except:
            print('no items for combobox')
        self.COMbobox.pack(side='left')
        self.button_connect = tk.Button(self.frame_controls, text="Подключиться", command=self.button_press, width=25)
        self.button_connect.pack(side='left', padx=(20, 10))
        # labelstatus
        self.label_status = tk.Label(self.frame_controls, text="Не подключено")
        self.label_status.pack(side='left', padx=5, fill='x')

    def draw_lakh_tab(self):
        self.fig_lakh, (self.ax2_lakh, self.ax1_lakh) = plt.subplots(nrows=2, figsize=(12, 6), tight_layout=True)
        self.canvas_lakh = FigureCanvasTkAgg(self.fig_lakh, master=self.tab_lakh)
        self.canvas_lakh.get_tk_widget().pack(side='top', fill='both', expand=True)
        self.toolbar_lakh = NavigationToolbar2Tk(self.canvas_lakh, self.tab_lakh)
        self.toolbar_lakh.update()
        self.toolbar_lakh.pack(side='top')
        self.ax1_lakh.format_coord = self.make_format_lakh()
        # lines
        self.line_lakh_amp, = self.ax1_lakh.plot(0, 0, label='Lm', marker='.')
        self.line_lakh_phase, = self.ax1_lakh.plot(0, 0, label="\u03C8", marker='.')
        # visuals
        self.init_lakh_plot()
        # amplitude
        self.amplitude_label_lakh = tk.Label(self.tab_lakh, text='Амплитуда [град]: ')
        self.amplitude_label_lakh.pack(side='left', padx=10)
        if self.amplitude_var is None:
            self.amplitude_var = tk.StringVar()
            self.amplitude_var.set(self.amp.value)
            self.amplitude_var.trace("w", lambda name, index, mode,
                                                 amplitude_var=self.amplitude_var: self.amplitude_callback(
                amplitude_var))
        self.amplitude_entry_lakh = tk.Entry(self.tab_lakh, textvariable=self.amplitude_var)
        self.amplitude_entry_lakh.pack(side='left', padx=(0, 15))
        # frequencies
        self.hertz_lakh_var = tk.StringVar()
        self.hertz_lakh_var.set("1 2 3 4 5 6.3 10 16 25 40")
        # self.hertz_lakh_var.set("1 2 6.3 10 16 25 40")
        self.hertz_lakh_label = tk.Label(self.tab_lakh, text="Частоты [Гц]: ")
        self.hertz_lakh_entry = tk.Entry(self.tab_lakh, textvariable=self.hertz_lakh_var, width=70)
        self.hertz_lakh_label.pack(side='left', padx=(5, 10))
        self.hertz_lakh_entry.pack(side='left')

    def init_lakh_plot(self):
        self.ax2_lakh.clear()
        self.ax1_lakh.set_xticks(np.arange(-2, 5, step=1))
        self.ax1_lakh.set_yticks(np.arange(-300, 300, step=20))
        self.ax1_lakh.set_ylim(-180, 20)
        self.ax1_lakh.set_xlim(0, 3)
        self.ax2_lakh.set_ylim(0, 4100)
        self.ax1_lakh.grid(b=True, which='major', axis='both')
        self.ax2_lakh.grid(b=True, which='major', axis='both')
        self.ax1_lakh.legend(fontsize='small')

    def lakh_plot(self):
        i = 0
        while self.main_queue.qsize():
            try:
                buf = self.main_queue.get()
                self.buffers["Time"].append(round(i * self.t_s, 4))
                i += 1
                # to change later: dict apprehension instead of append
                for key in buf.keys():
                    self.buffers[key].append(buf[key])
            except Empty:
                # doesnt ever work with manager ques, ugh..
                print("empty que =(")
        print(f"\nЧастота = {self.buffers['Frequency'][0]} Гц\nКоличество точек = {i}")
        lah, lfh = fourier.LAFCH(self.buffers['OBJ'],
                                 self.buffers['COM'],
                                 self.buffers['Time'],
                                 self.buffers['Frequency'][0])
        self.buffers['lah'].append(lah)
        self.buffers['lfh'].append(lfh)
        omega = self.buffers['Frequency'][0] * 2 * pi
        self.buffers['log_omega'].append(math.log10(omega))
        self.line_lakh_amp.set_data(self.buffers['log_omega'], self.buffers['lah'])
        self.line_lakh_phase.set_data(self.buffers['log_omega'], self.buffers['lfh'])
        print(f'time offset is {self.lakh_time_offset} on frequency {self.buffers["Frequency"][0]}')
        offset_time_buffer = [t + self.lakh_time_offset for t in self.buffers['Time']]
        line_lakh_com = self.ax2_lakh.plot(offset_time_buffer, self.buffers['COM'],
                                           color=u'#1f77b4')
        line_lakh_obj = self.ax2_lakh.plot(offset_time_buffer, self.buffers['OBJ'],
                                           color=u'#ff7f0e')
        # line_lakh_duty = self.ax2_lakh.plot(offset_time_buffer, self.buffers['Duty'],
        #                                     color='green', linewidth=0.5)
        lakh_line_lin_com = self.ax2_lakh.plot(offset_time_buffer, fourier.fourier(self.buffers['Time'],
                                                                                   self.buffers['COM'],
                                                                                   self.buffers['Frequency'][0])
                                               , color="pink", linewidth=0.5)
        lakh_line_lin_obj = self.ax2_lakh.plot(offset_time_buffer, fourier.fourier(self.buffers['Time'],
                                                                                   self.buffers['OBJ'],
                                                                                   self.buffers['Frequency'][0])
                                               , color="purple", linewidth=0.5)
        # lakh_line_lin_com2 = self.ax2_lakh.plot(offset_time_buffer, fourier.fourier2(self.buffers['Time'],
        #                                                                            self.buffers['COM'],
        #                                                                            self.buffers['Frequency'][0])
        #                                        , color="brown", linewidth=1)
        # lakh_line_lin_obj2= self.ax2_lakh.plot(offset_time_buffer, fourier.fourier2(self.buffers['Time'],
        #                                                                            self.buffers['OBJ'],
        #                                                                            self.buffers['Frequency'][0])
        #                                        , color="teal", linewidth=1)
        # print(f'about to put text on freq = {self.buffers["Frequency"][0]} Hz')
        self.ax2_lakh.text(self.lakh_time_offset, 3800,
                           s=f"{self.buffers['Frequency'][0]} Гц", fontsize='small', fontstretch='semi-condensed',
                           fontweight='ultralight', clip_on=True)
        self.lakh_stripe = not self.lakh_stripe
        if self.lakh_stripe:
            self.ax2_lakh.bar(self.lakh_time_offset, width=self.buffers['Time'][-1], align='edge',
                              height=4100, color=u'#e3e3e3')
        self.lakh_time_offset += self.buffers['Time'][-1]
        # это просто средняя линия вокруг которой должна в теории идти синусоида
        self.ax2_lakh.plot([offset_time_buffer[0], offset_time_buffer[-1]],
                           [middle_point, middle_point], color="black", linewidth=0.5)
        plt.draw()
        for key in self.buffers.keys():
            if key not in ("lah", "lfh", "log_omega"):
                self.buffers[key] = []

    def mode_combobox_modified_callback(self):
        self.mode.value = self.mode_combobox.current()

    def COMbobox_modified_callback(self):
        self.COMbobox['values'] = list(serial.tools.list_ports.comports())

    def hertz_callback(self, hertz_var):
        d = re.match("(\d+(\.)?(\d+)?)", hertz_var.get())
        if d is not None:
            hertz_var.set(d.group(1))
            self.hertz.value = float(d.group(1))
        else:
            hertz_var.set('')
            self.hertz.value = 0

    def amplitude_callback(self, amplitude_var):
        d = re.match("(\d+(\.)?(\d+)?)", amplitude_var.get())
        if d is not None:
            amplitude_var.set(d.group(1))
            self.amp.value = float(d.group(1))
        else:
            amplitude_var.set('')
            self.amp.value = 0

    def make_format(self, other, current):
        # current and other are axes
        def format_coord(x, y):
            # x, y are data coordinates
            y_com = self.buffers["COM"]
            y_obj = self.buffers["OBJ"]
            y_duty = self.buffers["Duty"]
            x_time = self.buffers['Time']
            # y_tok = self.buffers['Current']
            if len(x_time):
                com = np.interp(x, x_time, y_com)
                obj = np.interp(x, x_time, y_obj)
                duty = np.interp(x, x_time, y_duty)
                return (
                    "Упр. сигнал: {:.0f},   вых. сигнал: {:.0f},   коэф. заполнения: {:.0f},   время: {:.4f} с,".format(
                        com, obj, duty, x))
            else:
                # convert to display coords
                display_coord = current.transData.transform((x, y))
                inv = other.transData.inverted()
                # convert back to data coords with respect to ax
                ax_coord = inv.transform(display_coord)
                return "Координата: {:.0f},   коэф. заполнения: {:.0f},   время: {:.4f}".format(ax_coord[1], y, x)

        return format_coord

    def make_format_lakh(self):
        def format_coord(x, y):
            # x, y are data coordinates
            y_lah = self.buffers["lah"]
            y_lfh = self.buffers["lfh"]
            x_log_omega = self.buffers['log_omega']
            rad = pow(10, x)
            hz = rad / (2 * pi)
            if len(y_lah):
                lm = np.interp(x, x_log_omega, y_lah)
                ksi = np.interp(x, x_log_omega, y_lfh)
                return "В декадах: {:.2f},   в Гц: {:.2f},  Lm: {:.1f},  \u03C8: {:.1f}".format(x, hz, lm, ksi)
            else:
                return "В декадах: {:.2f},   в Гц: {:.2f},  y: {:.1f}}".format(x, hz, y)

        return format_coord

    def button_press(self):
        if self.button_connect["text"] == "Подключиться":
            self.connect()
        else:
            self.disconnect()

    def animate(self, i):
        if self.connected_flag.value == 0:
            self.animation.pause()  # костыль без которого не ставится на паузу в начале почему-то
            return
        while self.main_queue.qsize():
            try:
                buf = self.main_queue.get()
                self.buffers["Time"].append(round(self.n * self.t_s, 4))
                self.n += 1
                for key in buf.keys():
                    self.buffers[key].append(buf[key])
                # print(self.buffers)
                if len(self.buffers["Time"]) > self.buffer_size:
                    for list in self.buffers.values():
                        if len(list):
                            list.pop(0)
                if len(self.buffers["Time"]) > self.show_on_plot:
                    # print(f'{self.buffers["Time"][-self.show_on_plot]=}, {self.buffers["Time"][-1]=}')
                    self.ax1_anim.set_xlim(self.buffers["Time"][-self.show_on_plot], self.buffers["Time"][-1])
                elif len(self.buffers["Time"]) > 1:
                    # print(f'{self.buffers["Time"][0]=}, {self.buffers["Time"][-1]=}')
                    self.ax1_anim.set_xlim(self.buffers["Time"][0], self.buffers["Time"][-1])
                # print(f'{self.n=}')
                self.line_COM.set_data(self.buffers["Time"], self.buffers["COM"])
                self.line_OBJ.set_data(self.buffers["Time"], self.buffers["OBJ"])
                self.line_duty.set_data(self.buffers["Time"], self.buffers["Duty"])
                # self.line_dir.set_data(self.buffers["Time COM"], self.buffers["Dir"])
                # self.line_CUR.set_data(self.buffers["Time OBJ"], self.buffers["Current"])
            except Empty:
                # this doesnt work with manager que for some reason
                print("empty que =(")

    def check_msg(self):
        with self.lock:
            stop_flag = self.stop_flag.value
        if stop_flag == 0:
            if self.msg_queue.empty() is False:
                msg = self.msg_queue.get()
                if msg == "draw":
                    self.lakh_plot()
                else:
                    self.disconnect()
                    self.label_status.configure(text=msg)
            self.after(100, self.check_msg)

    def connect(self):
        p = re.search("COM[0-9]+", self.COMbobox.get())
        if p:
            selected_tab = self.tabControl.index("current")
            self.tabControl.tab(not selected_tab, state='disabled')
            for key in self.buffers.keys():
                self.buffers[key] = []
            com_port = p[0]
            self.label_status.configure(text='Подключение...')
            # АНИМАЦИЯ
            if selected_tab == 0:
                with self.lock:
                    self.stop_flag.value = 0
                print("process starting...")
                self.reader_process = multiprocessing.Process(target=read_process, args=(
                    self.stop_flag, self.connected_flag, com_port, self.lock, self.main_queue, self.msg_queue,
                    self.hertz, self.mode, self.amp), daemon=True)
                self.reader_process.start()
                with self.lock:
                    self.connected_flag.value = 1
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
                    if isinstance(msg, Exception):
                        self.disconnect()
                        self.label_status.configure(text=msg)
                    else:
                        self.label_status.configure(text=f'Подключено к {msg}')
                        self.button_connect.configure(text="Отключиться")
                        self.animation.resume()
                        self.check_msg()
            # ЛАХИ
            elif selected_tab == 1:
                self.init_lakh_plot()
                self.lakh_time_offset = 0
                frequencies = re.findall("(\d+[\.]?[\d+]?)", self.hertz_lakh_var.get())
                frequencies = sorted([float(f) for f in frequencies])
                # это место можно усовершенствовать. Нужно, чтобы строка искалась до запятой
                print(frequencies)
                with self.lock:
                    self.stop_flag.value = 0
                print("lakh process starting...")
                self.lakh_process = multiprocessing.Process(target=lakh_process, args=(
                    self.stop_flag, self.connected_flag, com_port, self.lock, self.main_queue, self.msg_queue,
                    frequencies, self.amp), daemon=True)
                self.lakh_process.start()
                with self.lock:
                    self.connected_flag.value = 1
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
                    if isinstance(msg, Exception):
                        self.disconnect()
                        self.label_status.configure(text=msg)
                    else:
                        self.label_status.configure(text=f'Подключено к {msg}')
                        self.button_connect.configure(text="Отключиться")
                        self.check_msg()
        self.n = 0

    def disconnect(self):
        # этот спагетти код можно уменьшить
        selected_tab = self.tabControl.index("current")
        self.tabControl.tab(not selected_tab, state='normal')
        if selected_tab == 0:
            try:
                if self.reader_process is not None:
                    with self.lock:
                        self.connected_flag.value = 0
                        self.stop_flag.value = 1
                    self.label_status.configure(text='Закрытие порта...')
                    self.reader_process.join()
                    print("process closed")
                    self.reader_process = None
                    while not self.main_queue.empty():
                        self.main_queue.get()
                    while not self.msg_queue.empty():
                        self.msg_queue.get()
                    self.label_status.configure(text='Порт закрыт успешно')
                    self.animation.pause()
            except Exception as e:
                self.label_status.configure(text=e)
            finally:
                self.button_connect["text"] = "Подключиться"
        elif selected_tab == 1:
            try:
                if self.lakh_process is not None:
                    with self.lock:
                        self.connected_flag.value = 0
                        self.stop_flag.value = 1
                    self.label_status.configure(text='Закрытие порта...')
                    self.lakh_process.join()
                    print("lakh process closed")
                    self.lakh_process = None
                    while not self.main_queue.empty():
                        self.main_queue.get()
                    while not self.msg_queue.empty():
                        self.msg_queue.get()
                    self.label_status.configure(text='Порт закрыт успешно')
            except Exception as e:
                self.label_status.configure(text=e)
            finally:
                self.button_connect["text"] = "Подключиться"

    def on_closing(self):
        self.disconnect()
        self.quit()
