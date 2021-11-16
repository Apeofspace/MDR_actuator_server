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
        self.lakh_process = None
        self.mode = mode
        self.buffer_size = 15000
        self.show_on_plot = 2000
        buffer_names = ['Time COM',
                        'COM',
                        'Time OBJ',
                        'OBJ',
                        'Duty',
                        'Dir',
                        'Frequency']
        self.buffers = {name: [] for name in buffer_names}

        # Style
        # style = ttk.Style()
        # style.theme_create('pastel', settings={
        #     "TNotebook.Tab": {
        #         "configure": {
        #             "background": '#d9ffcc',  # tab color when not selected
        #             "padding": [10, 2],
        #             # [space between text and horizontal tab-button border, space between text and vertical tab_button border]
        #             "font": "white",
        #             "borderwidth": 2
        #         },
        #         "map": {
        #             "background": [("selected", '#ccffff')],  # Tab color when selected\
        #             "expand": [("selected", [1, 1, 1, 0])]  # text margins
        #         }
        #     }
        # })
        # style.theme_use('pastel')
        # TabControl
        self.tabControl = ttk.Notebook(self)
        self.tab_animation = tk.Frame(self)
        self.tab_lakh = tk.Frame(self)
        self.tabControl.add(self.tab_animation, text='Анимация')
        self.tabControl.add(self.tab_lakh, text='ЛАХ')
        self.tabControl.pack(side='top', fill='both', expand=True)

        self.draw_animation_tab()
        self.draw_control_frame()
        self.draw_lakh_tab()

    def draw_animation_tab(self):
        # ANIMATION
        # self.tab_animation.pack(side='top', padx=10, fill='both', expand=True)
        self.fig_anim, self.ax1_anim = plt.subplots(figsize=(10, 5), tight_layout=True)
        self.canvas_anim = FigureCanvasTkAgg(self.fig_anim, master=self.tab_animation)
        self.toolbar_anim = NavigationToolbar2Tk(self.canvas_anim, self.tab_animation)
        self.toolbar_anim.update()
        self.toolbar_anim.pack(side='top')
        plt.grid(b=True, which='major', axis='both')
        self.ax2_anim = self.ax1_anim.twinx()
        self.ax2_anim.format_coord = self.make_format(self.ax1_anim, self.ax2_anim)
        self.line_duty, = self.ax2_anim.plot(0, 0, label='Коэффициент заполнения',
                                             color='green', linewidth=0.5)
        self.line_dir, = self.ax2_anim.plot(0, 0, label='Направление',
                                            color='red', linewidth=0.5)
        self.line_COM, = self.ax1_anim.plot(0, 0, label='Управляющий сигнал')
        self.line_OBJ, = self.ax1_anim.plot(0, 0, label='Значение с потенциометра')
        self.fig_anim.legend()
        self.ax1_anim.set_ylim(0, 4100)
        self.ax2_anim.set_ylim(0, 4100)
        self.canvas_anim.get_tk_widget().pack(side='top', fill='both', expand=True)
        self.animation = FuncAnimation(self.fig_anim, self.animate, interval=16, blit=False)
        self.animation.pause()  # dont let the animation run. doesnt work?
        plt.xlabel("[мс]")
        # hertz
        self.hertz_label = tk.Label(self.tab_animation, text='Частота [Гц]: ')
        self.hertz_label.pack(side='left', padx=10)
        self.hertz_var = tk.StringVar()
        self.hertz_var.set(self.hertz.value)
        self.hertz_var.trace("w", lambda name, index, mode, hertz_var=self.hertz_var: self.hertz_callback(hertz_var))
        self.hertz_entry = tk.Entry(self.tab_animation, textvariable=self.hertz_var)
        self.hertz_entry.pack(side='left', padx=(0, 15))
        # mode combobox
        self.mode_combobox_var = tk.StringVar()
        self.mode_combobox = tk.ttk.Combobox(self.tab_animation, textvariable=self.mode_combobox_var)
        self.mode_combobox['values'] = ["Синусоида", "Меандр"]
        self.mode_combobox['state'] = 'readonly'
        self.mode_combobox.current(newindex=0)
        self.mode_combobox.bind('<<ComboboxSelected>>', lambda func: self.mode_combobox_modified())
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
        self.COMbobox.set('COM13')
        self.COMbobox.pack(side='left')
        self.button_connect = tk.Button(self.frame_controls, text="Подключиться", command=self.button_press, width=25)
        self.button_connect.pack(side='left', padx=(20, 10))
        # labelstatus
        self.label_status = tk.Label(self.frame_controls, text="Не подключено")
        self.label_status.pack(side='left', padx=5, fill='x')

    def draw_lakh_tab(self):
        self.fig_lakh, self.ax1_lakh = plt.subplots(figsize=(10, 5), tight_layout=True)
        self.canvas_lakh = FigureCanvasTkAgg(self.fig_lakh, master=self.tab_lakh)
        self.toolbar_lakh = NavigationToolbar2Tk(self.canvas_lakh, self.tab_lakh)
        self.toolbar_lakh.update()
        self.toolbar_lakh.pack(side='top')
        self.line_lakh_amp, = self.ax1_lakh.plot(0, 0, label='Lm')
        self.line_lakh_phase, = self.ax1_lakh.plot(0, 0, label="\u03C8")
        self.fig_lakh.legend()
        self.ax1_lakh.set_ylim(0, 100)
        self.ax1_lakh.set_xlim(-1, 3)
        self.canvas_lakh.get_tk_widget().pack(side='top', fill='both', expand=True)

        self.hertz_lakh_var = tk.StringVar()
        # self.hertz_lakh_var.set("0.2, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 5, 6, 7, 8, 9, 10, 12, 14, 17, 20, 25")
        self.hertz_lakh_var.set("1, 1.5, 2, 2.5, 3")  # укороченная тестовая программа
        self.hertz_lakh_label = tk.Label(self.tab_lakh, text="Частоты [Гц]: ")
        self.hertz_lakh_entry = tk.Entry(self.tab_lakh, textvariable=self.hertz_lakh_var, width=70)
        self.hertz_lakh_label.pack(side='left', padx=10)
        self.hertz_lakh_entry.pack(side='left')

    def mode_combobox_modified(self):
        self.mode.value = self.mode_combobox.current()

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
        selected_tab = self.tabControl.index("current")
        if self.button_connect["text"] == "Подключиться":
            self.connect()
            self.tabControl.tab(not selected_tab, state='disabled')
        else:
            self.disconnect()
            self.tabControl.tab(not selected_tab, state='normal')

    def animate(self, i):
        if self.connected_flag.value == 0:
            self.animation.pause()  # костыль без которого не ставится на паузу в начале почему-то
        while self.main_queue.qsize():
            try:
                buf = self.main_queue.get()
                for key in self.buffers.keys():
                    self.buffers[key].append(buf[key])
                if len(self.buffers["Time COM"]) > self.buffer_size:
                    for value in self.buffers.values():
                        value.pop(0)
                if len(self.buffers["Time COM"]) > self.show_on_plot:
                    self.ax1_anim.set_xlim(self.buffers["Time COM"][-self.show_on_plot], self.buffers["Time COM"][-1])
                elif len(self.buffers["Time COM"]) > 1:
                    self.ax1_anim.set_xlim(self.buffers["Time COM"][0], self.buffers["Time COM"][-1])
                self.line_COM.set_data(self.buffers["Time COM"], self.buffers["COM"])
                self.line_OBJ.set_data(self.buffers["Time OBJ"], self.buffers["OBJ"])
                self.line_duty.set_data(self.buffers["Time COM"], self.buffers["Duty"])
                self.line_dir.set_data(self.buffers["Time COM"], self.buffers["Dir"])
            except Empty:
                print("empty que =(")

    def check_msg(self):
        self.lock.acquire()
        stop_flag = self.stop_flag.value
        self.lock.release()
        if stop_flag == 0:
            if self.msg_queue.empty() is False:
                msg = self.msg_queue.get()
                if isinstance(msg, Exception):
                    self.disconnect()
            self.after(250, self.check_msg)

    def connect(self):
        p = re.search("COM[0-9]+", self.COMbobox.get())
        selected_tab = self.tabControl.index("current")
        if p:
            for key in self.buffers.keys():
                self.buffers[key] = []
            com_port = p[0]
            self.label_status.configure(text='Подключение...')
            # АНИМАЦИЯ
            if selected_tab == 0:
                self.lock.acquire()
                self.stop_flag.value = 0
                self.lock.release()
                print("process starting...")
                self.reader_process = multiprocessing.Process(target=read_process, args=(
                    self.stop_flag, self.connected_flag, com_port, self.lock, self.main_queue, self.msg_queue,
                    self.hertz,
                    self.mode), daemon=True)
                self.reader_process.start()
                self.lock.acquire()
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
                        self.animation.resume()
                        self.check_msg()
            # ЛАХИ
            elif selected_tab == 1:
                frequencies = re.findall("(\d+[\.]?[\d+]?)", self.hertz_lakh_var.get())
                # frequencies = [1, 2, 3, 5]
                #это место можно усовершенствовать. Нужно, чтобы строка искалась до запятой
                print(frequencies)
                self.lock.acquire()
                self.stop_flag.value = 0
                self.lock.release()
                print("lakh process starting...")
                self.lakh_process = multiprocessing.Process(target=lakh_process, args=(
                    self.stop_flag, self.connected_flag, com_port, self.lock, self.main_queue, self.msg_queue,
                    frequencies), daemon=True)
                self.lakh_process.start()
                self.lock.acquire()
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
                        self.animation.resume()
                        self.check_msg()

    def disconnect(self):
        # этот спагетти код можно уменьшить
        selected_tab = self.tabControl.index("current")
        if selected_tab == 0:
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
                    while not self.main_queue.empty():
                        self.main_queue.get()
                    while not self.msg_queue.empty():
                        self.msg_queue.get()
                    self.label_status.configure(text='Порт закрыт успешно')
                    # self.animation.event_source.stop()
                    self.animation.pause()
            except Exception as e:
                self.label_status.configure(text=e)
            finally:
                self.button_connect["text"] = "Подключиться"
        elif selected_tab == 1:
            try:
                if self.lakh_process is not None:
                    self.lock.acquire()
                    self.connected_flag.value = 0
                    self.stop_flag.value = 1
                    self.lock.release()
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
        # root.quit()
        # root.destroy()
        self.quit()

