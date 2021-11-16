import multiprocessing
import tkinter as tk
from gui import MainWindow

if __name__ == "__main__":
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
    root.title("Sin Animation")
    MainWindow = MainWindow(root, connected_flag, stop_flag, msg_queue, main_queue, lock, hertz, mode)
    MainWindow.pack(side="top", fill="both", expand=True)
    root.wm_protocol("WM_DELETE_WINDOW", MainWindow.on_closing)
    root.mainloop()
