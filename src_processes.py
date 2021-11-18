import time
import csv
import datetime
from math import sin, pi
import serial

def lakh_process(stop_flag, connected_flag, com_port, lock, queue, msg_queue, frequencies):
    print("lakh process started")
    ser = serial.Serial()
    told = time.perf_counter()
    k = 0
    kold = 0
    first_time = True
    fields = ["Time COM", "Time OBJ", "COM", "OBJ", "Duty", "Dir", "Frequency"]
    left_lim = 0x100  # 0x600 is a quarter
    right_lim = 0xFFF - left_lim
    periods_to_use = 5
    period_to_rec = 4
    frequency_to_change_periods = 6
    periods_to_use2 = 12
    period_to_rec2 = 10
    try:
        number_of_frequencies = len(frequencies)
        if number_of_frequencies == 0:
            raise IndexError
        current_frequency = frequencies[0]
        current_frequency_index = 0
        period = 0
        ser.baudrate = 115200
        ser.port = com_port
        ser.open()
        msg_queue.put(ser.portstr)
        with open("LAKH_{}.csv".format(datetime.datetime.now().strftime("%Y_%m_%d-%H%M%S")), 'w',
                  newline='') as csv_file:
            csv_writer = csv.DictWriter(csv_file, fieldnames=fields)
            csv_writer.writeheader()
            print("header written")
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
                    t_new = time.perf_counter()
                    dt = t_new - told
                    told = t_new
                    if period >= periods_to_use:
                        # переход на следующую частоту
                        msg_queue.put("draw") #!!сообщение о том, что очередь заполнена!!
                        if current_frequency_index == number_of_frequencies - 1:
                            print('Конец эксперимента')
                            msg_queue.put("Конец эксперимента")
                            return  # закончен эксперимент
                        current_frequency_index += 1
                        current_frequency = frequencies[current_frequency_index]
                        print(f'Новая частота: {current_frequency}')
                        period = 0
                        if current_frequency > frequency_to_change_periods: #смена количества периодов
                            periods_to_use = periods_to_use2
                            period_to_rec = period_to_rec2
                    k = k + dt * float(current_frequency)  # цифра это герцы
                    signal = sin(2 * pi * k)
                    signal += 1
                    signal = (signal * (right_lim - left_lim)) / 2 + left_lim
                    ser.write(str(int(signal)).encode().zfill(4))
                    if k > (kold + 1):
                        # обнаружена смена периода
                        kold = k
                        period += 1
                        # print(f'Новый период {period}')
                        first_time=True
                    #страшный ужасающий костыль (это все должно быть под период == 4)
                    #но в этом случае процесс выполняется слишком быстро и виснет
                    line = ser.read(size=28)
                    if first_time:
                        initial_com_time = float(int.from_bytes(line[4:12], "little")) / 80000000
                        initial_obj_time = float(int.from_bytes(line[12:20], "little")) / 80000000
                        first_time = False
                    decoded = {'Time COM': float(int.from_bytes(line[4:12], "little")) / 80000000 - initial_com_time,
                               'Time OBJ': float(int.from_bytes(line[12:20], "little")) / 80000000 - initial_obj_time,
                               'COM': int.from_bytes(line[2:4], "little"),
                               'OBJ': int.from_bytes(line[0:2], "little"),
                               'Duty': int.from_bytes(line[20:24], "little"),
                               'Dir': int.from_bytes(line[24:28], "little") * 100,
                               'Frequency': current_frequency}
                    if period == period_to_rec:
                        # !!ОТПРАВКА ДАННЫХ В ОЧЕРЕДЬ!!
                        csv_writer.writerow(decoded)
                        queue.put(decoded)

    except Exception as e:
        print(f"Exception in lakh process : {e}")
        ser.close()
        msg_queue.put(e)


def read_process(stop_flag, connected_flag, com_port, lock, queue, msg_queue, hertz, mode):
    print("process started")
    ser = serial.Serial()
    told = time.perf_counter()
    k = 0
    first_time = True
    signal = 0
    fields = ["Time COM", "Time OBJ", "COM", "OBJ", "Duty", "Dir", "Frequency"]
    left_lim = 0x100  # 0x600 is a quarter
    right_lim = 0xFFF - left_lim
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
                               'Dir': int.from_bytes(line[24:28], "little") * 100,
                               'Frequency': Hz}
                    csv_writer.writerow(decoded)
                    queue.put(decoded)
                    t_new = time.perf_counter()
                    dt = t_new - told
                    if mode.value == 0:
                        # синусоида
                        told = t_new
                        k = k + dt * float(Hz)  # цифра это герцы
                        signal = sin(2 * pi * k)
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
    except Exception as e:
        print(f"Serial exception in process : {e}")
        ser.close()
        msg_queue.put(e)
