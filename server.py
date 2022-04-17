from pytz import timezone
from pixoo import Pixoo
from display import Display
from time import sleep
from datetime import datetime, timezone
import socket

HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
PORT = 1337       # Port to listen on (non-privileged ports are > 1023)


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    while True:
        try:
            s.bind((HOST, PORT))
            s.listen()
        except OSError as oe:
            sleep(0.5)
            continue
        
        while True:
            pix = Pixoo("11:22:33:44:55:66")
            pix.connect()
            pix.set_date_time()
            # evo.connect()
            # evo.set_date_time()
            try:
                di = Display()
                conn, addr = s.accept()
            except OSError as oe:
                print(oe)
                sleep(0.5)
                continue
            with conn:
                print('Connected by', addr)
                while True:
                    try:
                        data = conn.recv(16*16*3)
                    except ConnectionResetError as cre:
                        print(str(cre))
                        break
                    if data:
                        di.putData(data)
                        pix.draw(di)
                    else:
                        print("no data")
                        sleep(0.5)
                        break
                    



