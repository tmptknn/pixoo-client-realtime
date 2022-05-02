import asyncio
import queue

from base64 import decode
from pytz import timezone
from pixoo import Pixoo
from display import Display
from datetime import datetime, timezone
import socket

HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
PORT = 1337       # Port to listen on (non-privileged ports are > 1023)

async def read_processing(q):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        while True:
            try:
                s.bind((HOST, PORT))
                s.listen()
            except OSError as oe:
                print(oe)
                await asyncio.sleep(0.5)
                continue
            while True:
                try:
                    conn, addr = s.accept()
                    conn.setblocking(True)
                except OSError as oe:
                    print(oe)
                    await asyncio.sleep(0.5)
                    continue
                with conn:
                    print('Connected by', addr)
                    while True:
                        try:
                            data = bytearray(b'')
                            while len(data) < 16*16*3:
                                recvamount= 16*16*3-len(data)
                                data.extend(conn.recv(recvamount))
                        
                            await asyncio.sleep(0.01)
                        

                            if data:
                                if not q.full():
                                    #print("put to queueu")
                                    q.put(data)
                                    await asyncio.sleep(0.01)
                            else:
                                print("no data.")
                                await asyncio.sleep(0.01)
                                break
                        
                        except ConnectionResetError as cre:
                            print(str(cre))
                            break


async def write_to_divoom(q):
    di = Display()
    while True:
        pix = Pixoo("11:22:33:44:55:66")
        pix.connect()
        pix.set_date_time()
        while True:
            if not q.empty():
                #print("read data")
                data = q.get()
                di.putData(data)
                pix.draw(di)
            
            await asyncio.sleep(0.01)


async def main():
    q = queue.Queue(4)
    task_list = await asyncio.gather(
        read_processing(q),
        write_to_divoom(q)

    )

asyncio.run(main())