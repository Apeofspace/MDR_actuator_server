import time
import csv
import datetime
from math import sin, pi
import serial

package_length = 8
# left_lim = 800  # 0x600 is a quarter
# right_lim = 3800
middle_point = 2300
one_degree = 100
zero_point_current = 3135
fields = ["Frequency", "COM", "OBJ", "Duty"]
baudrate = 230400
t_s = 1/1000  # частота дискретизации

def lakh_process(stop_flag, connected_flag, com_port, lock, queue, msg_queue, frequencies, amplitude):
    global package_length, left_lim, right_lim, fields
    print("lakh process started")
    ser = serial.Serial()
    told = time.perf_counter()
    k = 0
    kold = 0
    periods_to_use = 5
    periods_to_rec = (3,)
    frequency_to_change_periods = 6
    periods_to_use2 = 13
    periods_to_rec2 = (10,)
    amp = amplitude.value
    try:
        number_of_frequencies = len(frequencies)
        if number_of_frequencies == 0:
            raise IndexError
        current_frequency = frequencies[0]
        current_frequency_index = 0
        block_half_freq_switching_kostil = True
        period = 1
        ser.baudrate = baudrate
        ser.timeout = 1
        ser.parity = serial.PARITY_NONE
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
                    signal = one_degree * amp * sin(2 * pi * k)
                    signal += middle_point
                    if k > (kold + 1):
                        # обнаружена смена периода
                        kold = k
                        if period not in periods_to_rec:
                            first_time = True
                            # todo: check if this is correct
                        period += 1
                    # страшный ужасающий костыль (это все должно быть под период == 4)
                    # но в этом случае процесс выполняется слишком быстро и виснет
                    send_signal(signal, ser)
                    line = ser.read(size=package_length)
                    decoded = decode_line(line, current_frequency)
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


def read_process(stop_flag, connected_flag, com_port, lock, queue, msg_queue, hertz, mode, amplitude):
    global package_length, fields
    print("process started")
    ser = serial.Serial()
    told = time.perf_counter()
    k = 0
    signal = 0
    amp = amplitude.value
    right_lim = middle_point + one_degree * amp
    left_lim = middle_point
    try:
        ser.baudrate = baudrate
        ser.timeout = 1
        ser.port = com_port
        ser.parity = serial.PARITY_NONE
        ser.open()
        msg_queue.put(ser.portstr)
        with open("Data_{}.csv".format(datetime.datetime.now().strftime("%Y_%m_%d-%H%M%S")), 'w',
                  newline='') as csv_file:
            csv_writer = csv.DictWriter(csv_file, fieldnames=fields)
            csv_writer.writeheader()
            send_signal(2150, ser)
            while True:
                lock.acquire()
                stop = stop_flag.value
                connected = connected_flag.value
                Hz = hertz.value
                amp = amplitude.value
                lock.release()
                if stop:
                    print("stopping process")
                    ser.close()
                    print("serial closed")
                    break
                if connected:
                    line = ser.read(size=package_length)
                    if len(line) < package_length:
                        print("timeout?")
                    decoded = decode_line(line, Hz)
                    csv_writer.writerow(decoded)
                    queue.put(decoded)
                    t_new = time.perf_counter()
                    dt = t_new - told
                    if mode.value == 0:
                        # синусоида
                        told = t_new
                        k = k + dt * float(Hz)  # цифра это герцы
                        signal = one_degree * amp * sin(2 * pi * k)
                        signal += middle_point
                        send_signal(signal, ser)
                    elif mode.value == 1:
                        # меандр
                        if not (Hz == 0):
                            if dt > 1 / Hz:
                                told = t_new
                                if signal == left_lim:
                                    signal = right_lim
                                else:
                                    signal = left_lim
                            send_signal(signal, ser)
    except Exception as e:
        print(f"Serial exception in process : {e}")
        ser.close()
        msg_queue.put(e)


def send_signal(signal, ser):
    ser.write(int(signal).to_bytes(2, 'little'))


def decode_line(line, current_frequency):
    decoded = {'COM': int.from_bytes(line[2:4], "little"),
               'OBJ': int.from_bytes(line[0:2], "little"),
               'Duty': int.from_bytes(line[4:8], "little"),
               'Frequency': current_frequency
               }
    return decoded
