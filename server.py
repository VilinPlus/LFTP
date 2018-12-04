import os
import random
import socket
import threading
import time
from queue import Queue

from header import *

recvSize = 2048
content_size = 1024
default_port = 10000
gain_port = 10001
split = '|:|'
windSize = 50


def get_command():
    global gain_port
    global split
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', default_port))
    data, addr = sock.recvfrom(recvSize)
    pk = Packet()
    pk.decode(data)
    str_to_decode = pk.data.decode('utf-8').split(split)
    method = str_to_decode[0]
    filename = str_to_decode[1]
    print(method)
    print(filename)

    str_to_send = method + split + filename + split + str(gain_port)
    pk_return = Packet()
    pk_return.make({'seqNo': 0, 'ackNo': 0, 'receiveWindowSize': windSize, 'ACK': 0, 'SYN': 0, 'FIN': 0,
                    'data': str_to_send.encode('utf-8')})
    sock.sendto(pk_return.bitStream, addr)
    sock.settimeout(2)
    data, addr = sock.recvfrom(recvSize)
    time.sleep(0.3)
    # sock.close()
    return method, filename, addr


def handle(method, filename, addr, server_port):
    temp = server(server_port, addr, method, filename)
    temp.server_client()


class server:
    method = ''
    filename = ''
    client_port = 0
    sock = 0
    f = 0
    buffer = []
    pk_recv = []
    current_ack = 0
    current_send = 0
    fin = 0
    address = 0
    need_re_send = False
    client_win_size = 50
    client_ack = -1
    rwnd = 50
    addr = 0

    written_ack = -1

    #网络丢包的情况
    retransmit = False

    # 阻塞控制
    sleep_time = 0.001
    duplicate_ack = 0
    cwnd = 0
    ssthresh = 32
    time_out = 1
    state = "slow start"

    def from_slow_start_get_into_fast_recovery(self):
        self.ssthresh = int(self.cwnd/2)
        self.cwnd = self.ssthresh + 3
        self.duplicate_ack = 0
        self.state = "fast recovery"
        print("From slow start into Fast recovery")

    def from_slow_start_into_congestion_avoidance(self):
        self.state = "congestion avoidance"
        print("slow_start into congestion avoidance")
        self.state = "congestion avoidance"
        pass

    def still_in_slow_start_when_new_ack(self):
        self.cwnd = self.cwnd + 1
        self.state = "slow start"
        print("still in slow start when new ack")

    def still_in_slow_start_when_timeout(self):
        self.ssthresh = int(self.cwnd/2)
        self.cwnd = self.ssthresh + 3
        self.state = "slow start"
        print("still slow start when timeout")

    def still_in_slow_start_when_duplicate_ack(self):
        self.duplicate_ack += 1
        self.state = "slow start"
        print("still slow start when timeout")

    def from_fast_recovery_get_into_congestion_avoidance(self):
        self.cwnd = self.ssthresh
        self.state = "congestion avoidance"
        print("Fast recovery into Congestion avoidance")

    def from_fast_recovery_get_into_slow_start(self):
        self.cwnd = 1
        self.state = "slow start"
        print("Fast recoverye into Slow start")

    def still_in_fast_recovery_when_duplicate_ack(self):
        self.cwnd = self.cwnd + 1
        self.state = "fast recovery"
        print("still in fast recovery  when duplicate ack")

    def from_congestion_avoidance_get_into_slow_start(self):
        self.ssthresh = int(self.cwnd)
        self.cwnd = 1
        self.state = "slow start"
        print("Congestion avoidance into Slow start")

    def from_congestion_avoidance_into_fast_recovery(self):
        self.ssthresh = int(self.cwnd/2)
        self.duplicate_ack = 0
        self.cwnd = self.ssthresh + 3
        self.state = "fast recovery"
        print("Congestion avoidance into Slow start")

    def still_in_congestion_avoidance_when_ne_ack(self):
        self.cwnd = self.cwnd + 1
        self.state = "congestion avoidance"
        print("still in congestion avoidance when new ack")

    def still_in_congestion_avoidance_when_duplicate_ack(self):
        self.duplicate_ack += 1
        self.state = "congestion avoidance"
        print("still in congestion avoidance when duplicate ack")

    def is_pk_in_cache(self, ack):
        for pk in self.pk_recv:
            if ack == pk.ackNo:
                return True

    def __init__(self, port, addr, method, filename):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('', port))
        self.method = method
        self.filename = filename
        self.addr = addr
        self.need_re_send = False

        self.fin = 0

        print('new a thread to server ' + str(addr))

    # mothod lsend
    def lsend(self):
        try:
            self.f = open('server/' + self.filename, 'wb')
        except:
            print('open file error')
        currAck = 0
        resend = 0

        print("Ready to get data from client", self.addr)
        while True:
            if len(self.pk_recv) < windSize:
                pk = Packet()
                try:
                    data, addr = self.sock.recvfrom(recvSize)
                    pk.decode(data)
                except:
                    p =Packet()
                    if len(self.pk_recv) == 0:
                        p.make({'seqNo': 0, 'ackNo': resend, 'receiveWindowSize': self.rwnd, 'ACK': 0, 'SYN': 0, 'FIN': 0})
                        self.sock.sendto(p.bitStream, self.addr)
                    else:
                        p_b = self.pk_recv[0]
                        e_m = 0
                        if p_b.FIN == 1:
                            e_m = 1
                        p.make({'seqNo': 0, 'ackNo': p_b.ackNo, 'receiveWindowSize': self.rwnd, 'ACK': 0, 'SYN': 0, 'FIN': e_m})
                        self.sock.sendto(p.bitStream, self.addr)
                        if p_b.FIN == 1:
                            print("File getting is over")
                            break
                        # read data from cache randomly
                        random_read_cache = random.randint(1, 10)
                        random_read_num = random.randint(1, 10)
                        print("size", len(self.pk_recv))
                        if random_read_cache > 5:
                            count = 0
                            while count < random_read_num and len(self.pk_recv) > 0:
                                print("PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP")
                                e_pk_read = self.pk_recv[0]
                                del self.pk_recv[0]
                                self.rwnd += 1
                                count += 1
                                if self.written_ack >= e_pk_read.ackNo:
                                    continue
                                #print("Now writing the package", pk_read.ackNo, "into file")
                                self.f.write(e_pk_read.data)
                                self.written_ack += 1
                        continue

                ran = random.randint(1, 10)
                if ran < 2 and currAck != 0:
                    print("Package", pk.ackNo, "drop")
                    pk_req = Packet()
                    if currAck - 1 < 0:
                        req_ack = 0
                    else:
                        req_ack = currAck - 1
                    pk_req.make({'seqNo': 0, 'ackNo': req_ack, 'receiveWindowSize': self.rwnd, 'ACK': 0, 'SYN': 0, 'FIN': 0})
                    self.sock.sendto(pk_req.bitStream, self.addr)
                    continue

                if self.is_pk_in_cache(pk.ackNo):
                    pk_back = Packet()
                    pk_back.make({'seqNo': 0, 'ackNo': pk.ackNo, 'receiveWindowSize': self.rwnd, 'ACK': 0, 'SYN': 0, 'FIN': 0})
                    resend = pk.ackNo
                    self.sock.sendto(pk_back.bitStream, self.addr)
                    continue

                print("Package", pk.ackNo, "save in cache")
                self.pk_recv.append(pk)
                self.rwnd -= 1

                currAck += 1

                if self.rwnd < 0:
                    self.rwnd = 0

                if pk.FIN == 1:
                    m = 1
                else:
                    m = 0

                pk_re = self.pk_recv[0]
                pk_re.make({'seqNo': 0, 'ackNo': pk.ackNo, 'receiveWindowSize': self.rwnd, 'ACK': 0, 'SYN': 0, 'FIN': m})
                self.sock.sendto(pk_re.bitStream, self.addr)

                if pk.FIN == 1:
                    print("File getting is over")
                    break

            # read data from cache randomly
            random_read_cache = random.randint(1, 10)
            random_read_num = random.randint(1, 10)
            print("Cache size", len(self.pk_recv))
            if random_read_cache > 5:
                count = 0
                while count < random_read_num and len(self.pk_recv) > 0:
                    pk_read = self.pk_recv[0]
                    del self.pk_recv[0]
                    self.rwnd += 1
                    count += 1
                    if self.written_ack >= pk_read.ackNo:
                        continue
                    print("Now writing the package", pk_read.ackNo, "into file")
                    self.f.write(pk_read.data)
                    self.written_ack += 1

        while len(self.pk_recv) > 0:
            pk_in_cache = self.pk_recv[0]
            del self.pk_recv[0]
            self.rwnd += 1
            if self.written_ack >= pk_in_cache.ackNo:
                continue
            print("Now writing the package", pk_in_cache.ackNo, "into file")
            self.f.write(pk_in_cache.data)
            self.written_ack += 1

        print("Link with", addr, "end")
        self.f.close()
        self.sock.close()

    def method_lget(self):
        try:
            self.f = open('server/' + self.filename, 'rb')
            filesize = os.path.getsize("server/"+self.filename)
            m = 0
            if filesize % content_size != 0:
                m = 1
            block_num = int(filesize / content_size) + m
            print("bolck "+str(block_num))
        except:
            print('open file error')

        re_send_num = 0
        while 1:
            if self.cwnd >= self.ssthresh and self.state == "slow start":
                self.from_slow_start_into_congestion_avoidance()
            if self.client_win_size > 0:
                # 发送一个包
                if not self.need_re_send:
                    if self.current_send < block_num:
                        if self.current_send == block_num - 1:
                            f = 1
                            content = self.f.read(filesize % content_size)
                        else:
                            f = 0
                            content = self.f.read(content_size)

                        pk = Packet()
                        pk.make({'seqNo': 0, 'ackNo': self.current_send, 'receiveWindowSize': self.client_win_size,
                                 'ACK': 0, 'SYN': 0, 'FIN': f, 'data': content})
                        time.sleep(self.sleep_time)
                        self.sock.sendto(pk.bitStream, self.addr)
                        print('send a packet '+str(pk.ackNo))
                        self.pk_recv.append(pk)
                        self.current_send = self.current_send + 1
                if self.need_re_send:
                    pk = self.pk_recv[0]
                    self.sock.sendto(pk.bitStream, self.addr)
                    print('resend a packet '+str(pk.ackNo))
            else:# 窗口满了，不发包，但可以接包
                pass
            # 接收一个包

            try:
                data, addr = self.sock.recvfrom(recvSize)
            except:
                pk = self.pk_recv[0]
                self.sock.sendto(pk.bitStream, self.addr)
                if self.state == "slow start":
                    self.still_in_slow_start_when_timeout()
                if self.state == "fast recovery":
                    self.from_fast_recovery_get_into_slow_start()
                if self.state == "congestion avoidance":
                    self.from_congestion_avoidance_get_into_slow_start()
                continue
            pk = Packet()
            pk.decode(data)
            if pk.seqNo == 1:
                self.need_re_send = False
                self.client_ack = pk.ackNo
                continue

            self.client_win_size = pk.receiveWindowSize
            if self.client_win_size < self.cwnd:
                if self.sleep_time <= 0.00004:
                    self.sleep_time += 0.00001
                else:
                    if self.sleep_time > 0.00001:
                        self.sleep_time -= 0.00001
            self.fin = pk.FIN
            print("receive " + str(pk.ackNo))

            self.client_ack = pk.ackNo
            '''
            print("client_ack ", self.client_ack)
            print("current_ack ", self.current_ack)
            '''
            if self.current_ack == self.client_ack:
                if self.duplicate_ack >= 3:
                    self.from_slow_start_get_into_fast_recovery()
                self.current_ack = self.current_ack + 1
                del self.pk_recv[0]
                if self.state == "slow start":
                    self.still_in_slow_start_when_new_ack()
                if self.state == "congestion avoidance":
                    self.still_in_congestion_avoidance_when_ne_ack()
                if self.state == "fast recovery":
                    self.from_fast_recovery_get_into_congestion_avoidance()
                self.need_re_send = False
            else:
                self.need_re_send = True
                if self.state == "congestion avoidance":
                    self.still_in_congestion_avoidance_when_duplicate_ack()
                if self.state == "fast recovery":
                    self.still_in_fast_recovery_when_duplicate_ack()
                if self.state == "slow start":
                    self.still_in_slow_start_when_duplicate_ack()

            # get three dupicate
            if self.duplicate_ack == 3:
                if self.state == "slow start":
                    self.from_slow_start_get_into_fast_recovery()
                if self.state == "congestion avoidance":
                    self.from_congestion_avoidance_into_fast_recovery()
                if self.state == "fast recovery":
                    self.from_fast_recovery_get_into_slow_start()

            if self.duplicate_ack > 3:
                self.cwnd += 1

            if self.fin:
                print("server end ", self.addr)
                break
        self.sock.close()

    def server_client(self):
        if self.method == 'lget':
            self.method_lget()
        else:
            self.lsend()


def main():
    global gain_port
    while 1:
        print("begin")
        method, filename, addr = get_command()
        print(method)
        print(filename)
        print(addr)

        thread = threading.Thread(target=handle, args=(method, filename, addr, gain_port,))
        print("gain "+str(gain_port))
        gain_port = gain_port + 1
        thread.start()


if __name__ == '__main__':
    main()
