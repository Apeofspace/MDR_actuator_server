import multiprocessing
import tkinter as tk
from gui import MainWindow
import sys
import plotCSV


def normal_start():
    multiprocessing.freeze_support()
    q_manager = multiprocessing.Manager()
    main_queue = q_manager.Queue()
    msg_queue = multiprocessing.SimpleQueue()
    stop_flag = multiprocessing.Value("i", 0)
    connected_flag = multiprocessing.Value("i", 0)
    hertz = multiprocessing.Value("f", 0.5)
    mode = multiprocessing.Value("i", 0)
    lock = multiprocessing.Lock()
    root = tk.Tk()
    root.title("Пульт управления")
    main_window = MainWindow(root, connected_flag, stop_flag, msg_queue, main_queue, lock, hertz, mode)
    main_window.pack(side="top", fill="both", expand=True)
    root.wm_protocol("WM_DELETE_WINDOW", main_window.on_closing)
    root.mainloop()


def plot_mode_start(filename):
    buffers = plotCSV.read_from_csv(filename)
    if buffers is None:
        normal_start()
    else:
        plotCSV.plot_and_show(buffers, filename)


if __name__ == "__main__":
    try:
        arg = sys.argv[1]
        plot_mode_start(arg)
    except IndexError as e:
        normal_start()


