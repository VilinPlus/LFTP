
"""
seqNo;32bits
ackNo:32bits
receiveWindowSize:16bits
ACK:1bits
SYN:1bits
FIN:1bits
data: 100bytes
"""
#change int to bits
def intToBit(value, len):
    tempBit = bytes(bin(value)[2:].zfill(len), encoding='utf-8')
    return tempBit
def Hex2Bit(heximal):
    '''对于16进制bytes，转换为01bytes'''
    bit = b''
    for hex in heximal:
        bit += intToBit(hex,8)
    return bit

def getStreamFromDict(dict):
    #print(dict)
    bitStr = b''
    for key in dict:
        if key == 'seqNo':
            bitStr += intToBit(dict[key], 32)
        if key == 'ackNo':
            bitStr += intToBit(dict[key], 32)
        if key == 'receiveWindowSize':
            bitStr += intToBit(dict[key], 16)
        if key == 'ACK':
            bit = b'0'
            if dict[key] == 1:
                bit = b'1'
            bitStr += bit
        if key == 'SYN':
            bit = b'0'
            if dict[key] == 1:
                bit = b'1'
            bitStr += bit
        if key == 'FIN':
            bit = b'0'
            if dict[key] == 1:
                bit = b'1'
            bitStr += bit
            #bitStr += b'00000'
    if 'data' in dict:
        bitStr += dict['data']
    return bitStr

class Packet():
    bitStream = b''
    seqNo = 0
    ackNo = 0
    receiveWindowSize = 0
    str1 = 0
    ACK = 0
    SYN = 0
    FIN = 0
    data = 0

    def make(self, dict):
        self.bitStream = getStreamFromDict(dict)
        self.seqNo = dict['seqNo']
        self.ackNo = dict['ackNo']
        self.receiveWindowSize = dict['receiveWindowSize']
        self.ACK = dict['ACK']
        self.SYN = dict['SYN']
        self.FIN = dict['FIN']
        if 'data' in dict:
            self.data = dict['data']

    def decode(self, byte1):
        #self.bitStream = Hex2Bit(byte1[:12])+byte1[12:]
        self.bitStream = byte1
        #print(self.bitStream)
        self.seqNo = int(self.bitStream[0:32], 2)
        self.ackNo = int(self.bitStream[32:64], 2)
        self.receiveWindowSize = int(self.bitStream[64:80], 2)
        self.str1 = str(self.bitStream[0:83], encoding='utf-8')
        if self.str1[80] == '1':
            self.ACK = 1
        else:
            self.ACK = 0
        if self.str1[81] == '1':
            self.SYN = 1
        else:
            self.SYN = 0
        if self.str1[82] == '1':
            self.FIN = 1
        else:
            self.FIN = 0
        """
        self.ACK = bytes(str(self.bitStream[80] - '0'),encoding='utf-8')
        self.SYN = bytes(str(self.bitStream[81] - '0'),encoding='utf-8')
        self.FIN = bytes(str(self.bitStream[82] - '0'),encoding='utf-8')
        if self.ACK:
            self.ACK = 1
        else:
            self.ACK = 0
        if self.SYN:
            self.SYN = 1
        else:
            self.SYN = 0
        if self.FIN:
            self.FIN = 1
        else:
            self.FIN = 0
        """
        self.data = self.bitStream[83:]
