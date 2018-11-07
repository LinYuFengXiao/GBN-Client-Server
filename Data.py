class Data(object):
    """
    要发送的数据包
    msg为报文内容 字节序列
    type表示类型，0为数据报文，1为ack报文
    seq表示序列号
    state只在发送端使用，不发送到接收端 state为0表是带发送，为1表示以发送， 为2表示以发送且已收到ACK
    """
    def __init__(self, msg, type, seq=0, state=0):
        self.msg = msg.decode()
        self.type = str(type)
        self.state = state
        self.seq = str(seq)

    def __str__(self):
        return self.seq + self.type + self.msg
