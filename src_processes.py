import time
import csv
import datetime
from math import sin, pi
import serial

package_length = 32
left_lim = 660  # 0x600 is a quarter
right_lim = 3720
zero_point_current = 3135

def lakh_process(stop_flag, connected_flag, com_port, lock, queue, msg_queue, frequencies):
    global package_length, left_lim, right_lim
    print("lakh process started")
    ser = serial.Serial()
    told = time.perf_counter()
    k = 0
    kold = 0
    first_time = True
    fields = ["Time COM", "Time OBJ", "COM", "OBJ", "Duty", "Dir", "Frequency"]
    periods_to_use = 5
    periods_to_rec = (3, 4)
    frequency_to_change_periods = 6
    periods_to_use2 = 13
    periods_to_rec2 = (9, 10, 11)
    try:
        number_of_frequencies = len(frequencies)
        if number_of_frequencies == 0:
            raise IndexError
        current_frequency = frequencies[0]
        current_frequency_index = 0
        block_half_freq_switching_kostil = True
        period = 1
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
                    k = k + dt * float(current_frequency)  # цифра это герцы
                    signal = sin(2 * pi * k)
                    signal += 1
                    signal = (signal * (right_lim - left_lim)) / 2 + left_lim
                    ser.write(str(int(signal)).encode().zfill(4))
                    if k > (kold + 1):
                        # обнаружена смена периода
                        kold = k
                        if period not in periods_to_rec:
                            first_time = True
                            # todo: check if this is correct
                        period += 1
                    # страшный ужасающий костыль (это все должно быть под период == 4)
                    # но в этом случае процесс выполняется слишком быстро и виснет
                    line = ser.read(size=package_length)
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
                    if period in periods_to_rec:
                        # !!ОТПРАВКА ДАННЫХ В ОЧЕРЕДЬ!!
                        csv_writer.writerow(decoded)
                        queue.put(decoded)
                    if not block_half_freq_switching_kostil:
                        if all([period > p for p in periods_to_rec]):
                            current_frequency = current_frequency / 2
                            block_half_freq_switching_kostil = True
                            # в теории если запаздывание больше 180 то уже не спасёт никак.
                    if period > periods_to_use:
                        # print(f'draw now period {period}')
                        msg_queue.put("draw")  # !!сообщение о том, что очередь заполнена!!
                        # переход на следующую частоту
                        if current_frequency_index == number_of_frequencies - 1:
                            msg_queue.put("Конец эксперимента")
                            return  # закончен эксперимент
                        current_frequency_index += 1
                        current_frequency = frequencies[current_frequency_index]
                        period = 0
                        if current_frequency > frequency_to_change_periods:  # смена количества периодов
                            block_half_freq_switching_kostil = False
                            periods_to_use = periods_to_use2
                            periods_to_rec = periods_to_rec2
    except Exception as e:
        print(f"Exception in lakh process : {e}")
        ser.close()
        msg_queue.put(e)


def read_process(stop_flag, connected_flag, com_port, lock, queue, msg_queue, hertz, mode):
    global package_length, left_lim, right_lim
    print("process started")
    ser = serial.Serial()
    told = time.perf_counter()
    k = 0
    first_time = True
    signal = 0
    fields = ["Time COM", "Time OBJ", "COM", "OBJ", "Duty", "Dir", "Frequency", "Current"]
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
                    line = ser.read(size=package_length)
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
                               'Frequency': Hz,
                               'Current': ((zero_point_current-float(int.from_bytes(line[28:32], "little")))*3.3/0xfff)*10}  #Amps
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
