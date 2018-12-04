import os
import socket, random, json, threading, queue, sys
import time
from header import *


split = '|:|'
clientPort = 9999
#serverAddress = '172.18.33.148'
#serverAddress = '192.168.1.230'
#serverAddress = '127.0.0.1'

#serverAddress = '4006:e024:680:b5fc:4de3:9b8:d2d6:9724'
serverPort = 10000
server_addr_and_port = ('', 0)
buffersize = 1024
sockSize = 2048
totalAck = 0
windSize = 50


class client():
    correctCommand = False
    method = ''
    ip = ''
    filename = ''
    sock = 0
    portForLink = 0
    fp = 0
    filesize = 0
    pk_sent = []
    pk_recv = []
    rwnd = 50
    written_ack = -1

    resend_seq = 0
    server_ack = 0
    server_rwnd = 50
    current_send = 0
    need_re_send = False
    fin = 0
    current_ack = 0

    # 阻塞控制
    sleep_time = 0.00001
    duplicate_ack = 0
    cwnd = 0
    ssthresh = 32
    sleep_time = 0
    time_out = 1
    state = "slow start"

    def from_slow_start_get_into_fast_recovery(self):
        self.ssthresh = int(self.cwnd/2)
        self.cwnd = self.ssthresh + 3
        self.duplicate_ack = 0
        self.state = "fast recovery"
        #print("From slow start into Fast recovery")

    def from_slow_start_into_congestion_avoidance(self):
        self.state = "congestion avoidance"
        #print("slow_start into congestion avoidance")
        self.state = "congestion avoidance"
        pass

    def still_in_slow_start_when_new_ack(self):
        self.cwnd = self.cwnd + 1
        self.state = "slow start"
        #print("still in slow start when new ack")

    def still_in_slow_start_when_timeout(self):
        self.ssthresh = int(self.cwnd/2)
        self.cwnd = self.ssthresh + 3
        self.state = "slow start"
        #print("still slow start when timeout")

    def still_in_slow_start_when_duplicate_ack(self):
        self.duplicate_ack += 1
        self.state = "slow start"
        #print("still slow start when timeout")

    def from_fast_recovery_get_into_congestion_avoidance(self):
        self.cwnd = self.ssthresh
        self.state = "congestion avoidance"
        #print("Fast recovery into Congestion avoidance")

    def from_fast_recovery_get_into_slow_start(self):
        self.cwnd = 1
        self.state = "slow start"
        #print("Fast recoverye into Slow start")

    def still_in_fast_recovery_when_duplicate_ack(self):
        self.cwnd = self.cwnd + 1
        self.state = "fast recovery"
        #print("still in fast recovery  when duplicate ack")

    def from_congestion_avoidance_get_into_slow_start(self):
        self.ssthresh = int(self.cwnd)
        self.cwnd = 1
        self.state = "slow start"
        #print("Congestion avoidance into Slow start")

    def from_congestion_avoidance_into_fast_recovery(self):
        self.ssthresh = int(self.cwnd/2)
        self.duplicate_ack = 0
        self.cwnd = self.ssthresh + 3
        self.state = "fast recovery"
        #print("Congestion avoidance into Slow start")

    def still_in_congestion_avoidance_when_ne_ack(self):
        self.cwnd = self.cwnd + 1
        self.state = "congestion avoidance"
        #print("still in congestion avoidance when new ack")

    def still_in_congestion_avoidance_when_duplicate_ack(self):
        self.duplicate_ack += 1
        self.state = "congestion avoidance"
        #print("still in congestion avoidance when duplicate ack")

    # method link server
    def linkToServer(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('', clientPort))
        #sock.sendto(b'111', (self.serverAddress, self.serverPort))
        #self.sock.settimeout(10)

    # method to send command
    def sendCommandAndGetPortFromServer(self):
        global server_addr_and_port
        while not self.correctCommand:
            command = input('Please enter your command with the format: [LFTP] [lsend/lget] [addr] [filename]\n')
            commands = command.split(' ')
            if commands[0] != 'LFTP':
                print('Please enter right command')
                continue
            self.method = commands[1]
            self.ip = commands[2]
            self.filename = commands[3]
            self.correctCommand = True
        data_to_send = self.method + split + self.filename + split +str(clientPort)

        pk = Packet()
        pk.make({'seqNo': 0, 'ackNo': 1, 'receiveWindowSize': 0, 'ACK': 0, 'SYN': 0, 'FIN': 0,
                 'data': data_to_send.encode('utf-8')})
        print(self.ip)
        self.sock.sendto(pk.bitStream, (self.ip, 10000))

        self.sock.settimeout(10)
        data, addr = self.sock.recvfrom(sockSize)
        pk1 = Packet()
        pk1.decode(data)

        data_from_server = pk1.data.decode("utf-8")

        dataList = data_from_server.split(split)
        self.portForLink = int(dataList[2])
        print(self.portForLink)
        server_addr_and_port = (self.ip, self.portForLink)

        shake = Packet()
        shake.make({'seqNo': 0, 'ackNo': 0, 'receiveWindowSize': 0, 'ACK': 0, 'SYN': 0, 'FIN': 0})
        self.sock.sendto(shake.bitStream, addr)
        time.sleep(1)

    def is_pk_in_cache(self, ack):
        for pk in self.pk_recv:
            if ack == pk.ackNo:
                return True

# method lsend
    def lsend(self):
        m = 0
        if self.filesize % buffersize != 0:
            m = 1
        block_num = int(self.filesize / buffersize) + m
        print("bolck "+str(block_num))
        while 1:
            if self.cwnd >= self.ssthresh and self.state == "slow start":
                self.from_slow_start_into_congestion_avoidance()
            if self.server_rwnd > 0:
                #发送一个包
                if not self.need_re_send:
                    if self.current_send < block_num:
                        if self.current_send == block_num - 1:

                            f = 1
                            content = self.fp.read(self.filesize % buffersize)
                        else:
                            f = 0
                            content = self.fp.read(buffersize)

                        pk = Packet()
                        pk.make({'seqNo': 0, 'ackNo': self.current_send, 'receiveWindowSize': self.server_rwnd, 'ACK': 0,
                                 'SYN': 0, 'FIN': f, 'data': content})
                        self.sock.sendto(pk.bitStream, (self.ip, self.portForLink))
                        print('send a packet '+str(pk.ackNo))
                        self.pk_sent.append(pk)
                        self.current_send += 1

                if self.need_re_send:
                    pk = self.pk_sent[0]
                    self.sock.sendto(pk.bitStream, (self.ip, self.portForLink))
                    print('resend a packet '+str(pk.ackNo))
            else:#窗口满了，不发包，但可以接包
                pass
            #接收一个包

            try:
                data, addr = self.sock.recvfrom(sockSize)
            except:
                pk = self.pk_sent[0]
                self.sock.sendto(pk.bitStream, (self.ip, self.portForLink))
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
                self.server_ack = pk.ackNo
                continue

            self.server_rwnd = pk.receiveWindowSize
            if self.server_rwnd < self.cwnd:
                if self.sleep_time <= 0.00004:
                    self.sleep_time += 0.00001
                else:
                    if self.sleep_time > 0.00001:
                        self.sleep_time -= 0.00001
            self.fin = pk.FIN
            print("receive " + str(pk.ackNo))

            self.server_ack = pk.ackNo

            if self.current_ack == self.server_ack:
                if self.duplicate_ack >= 3:
                    self.from_slow_start_get_into_fast_recovery()
                self.current_ack = self.current_ack + 1
                del self.pk_sent[0]
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
                print("File sending is over")
                break
        self.sock.close()

    # lget method
    def lget(self):
        #self.sock_.settimeout(10)

        currAck = 0
        resend = 0
        print("Ready to get data from server")
        while True:
            if len(self.pk_recv) < windSize:
                pk = Packet()
                try:
                    data, addr = self.sock.recvfrom(sockSize)
                    pk.decode(data)
                except:
                    p =Packet()
                    if len(self.pk_recv) == 0:
                        p.make({'seqNo': 0, 'ackNo': resend, 'receiveWindowSize': self.rwnd, 'ACK': 0, 'SYN': 0, 'FIN': 0})
                        self.sock.sendto(p.bitStream, (self.ip, self.portForLink))
                    else:
                        p_b = self.pk_recv[0]
                        e_m = 0
                        if p_b.FIN == 1:
                            e_m = 1
                        p.make({'seqNo': 0, 'ackNo': p_b.ackNo, 'receiveWindowSize': self.rwnd, 'ACK': 0, 'SYN': 0, 'FIN': e_m})
                        self.sock.sendto(p.bitStream, (self.ip, self.portForLink))
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
                                # print("PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP")
                                e_pk_read = self.pk_recv[0]
                                del self.pk_recv[0]
                                self.rwnd += 1
                                count += 1
                                if self.written_ack >= e_pk_read.ackNo:
                                    continue
                                #print("Now writing the package", pk_read.ackNo, "into file")
                                self.fp.write(e_pk_read.data)
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
                    self.sock.sendto(pk_req.bitStream, (self.ip, self.portForLink))
                    continue

                if self.is_pk_in_cache(pk.ackNo):
                    pk_back = Packet()
                    pk_back.make({'seqNo': 0, 'ackNo': pk.ackNo, 'receiveWindowSize': self.rwnd, 'ACK': 0, 'SYN': 0, 'FIN': 0})
                    self.sock.sendto(pk_back.bitStream, (self.ip, self.portForLink))
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

                print("Client tells server the package", pk.ackNo, "has been received.")
                pk_re = self.pk_recv[0]
                pk_re.make({'seqNo': 0, 'ackNo': pk.ackNo, 'receiveWindowSize': self.rwnd, 'ACK': 0, 'SYN': 0, 'FIN': m})
                resend = pk.ackNo
                self.sock.sendto(pk_re.bitStream, (self.ip, self.portForLink))

                if pk.FIN == 1:
                    print("File getting is over")
                    break

            # read data from cache randomly
            random_read_cache = random.randint(1, 10)
            random_read_num = random.randint(1, 10)
            print("size", len(self.pk_recv))
            if random_read_cache > 5:
                count = 0
                while count < random_read_num and len(self.pk_recv) > 0:
                    pk_read = self.pk_recv[0]
                    del self.pk_recv[0]
                    self.rwnd += 1
                    count += 1
                    if self.written_ack >= pk_read.ackNo:
                        continue
                    # print("Now writing the package", pk_read.ackNo, "into file")
                    self.fp.write(pk_read.data)
                    self.written_ack += 1

        while len(self.pk_recv) > 0:
            pk_in_cache = self.pk_recv[0]
            del self.pk_recv[0]
            self.rwnd += 1
            if self.written_ack >= pk_in_cache.ackNo:
                continue
            # print("Now writing the package", pk_in_cache.ackNo, "into file")
            self.fp.write(pk_in_cache.data)
            self.written_ack += 1

        self.fp.close()

    # judge method
    def judge_mothod(self):
        if self.method == 'lsend':
            try:
                self.fp = open("client/" + self.filename, 'rb')
                self.filesize = os.path.getsize("client/"+self.filename)
            except:
                print("file cannot open")

            self.lsend()
        elif self.method == 'lget':
            try:
                self.fp = open("client/" + self.filename, 'wb')
            except:
                print("File cannot open")
            self.lget()
        else:
            pass


client = client()
client.linkToServer()
client.sendCommandAndGetPortFromServer()
client.judge_mothod()
