import select
import socket
import sys
from random import random
from GBN.Data import Data

class SRServer:
    def __init__(self):
        self.nextseqnum = 1
        self.addr = ('127.0.0.1', 31500)
        self.client_addr = ('127.0.0.1', 12345)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(self.addr)
        self.max_time = 5 # 超时时间
        self.wait_time = 15  # 等待看是否还有数据发来的时间
        self.pkg_num = 0 # 要发送的包的数目
        self.N = 3 # 发送窗口大小
        self.M = 3 # 接收窗口大小
        self.buff_size = 1024
        self.send_windows = []
        self.receive_windows = []

    def send(self, buffer):
        # 计时和包序号初始化
        pkg_timer = [] # 发送报文的定时器
        self.pkg_num = len(buffer)
        # 记录上一个回执的ack的值
        last_ack = 0 # 上一次发送的ack值
        msg_timer = 0 # 接收报文的定时器

        while True:
            # 当超时后，将窗口内的数据更改为未发送状态
            for index, item in enumerate(pkg_timer):
                if item > self.max_time:  # 说明该分组超时:
                    if self.send_windows[index].state != 2:
                        self.send_windows[index].state = 0
                        print('Server: 发生超时，重传 ', self.send_windows[index].seq)

            # 窗口中数据小于最大容量时，尝试添加新数据
            while len(self.send_windows) < self.N:
                if (self.nextseqnum > self.pkg_num): # 若无数据则不发送
                    break
                # 将第nextseqnum-1个包加入窗口内，并封装成数据,type为0
                data = Data(buffer[self.nextseqnum - 1], 0, seq=self.nextseqnum)
                self.send_windows.append(data)
                pkg_timer.append(0)
                self.nextseqnum += 1

            # 没有数据要发送(pkg_timer为空), 且没有报文要接收(msg_timer超时)
            if not self.send_windows:
                if not pkg_timer and msg_timer > self.wait_time:
                    print('Server: 发送/接收完毕, 退出')
                    break

            # 遍历窗口内数据，如果存在未成功发送的则发送
            for index, data in enumerate(self.send_windows):
                if not data.state:
                    print('Server: 发送数据 ' + data.seq)
                    self.socket.sendto(str(data).encode(), self.client_addr)
                    data.state = 1 # 状态置为1， 0表示未发送， 1表示以发送，还未收到ack， 2表示已发送，且已收到ack
                    pkg_timer[index] = 0


            # 无阻塞socket连接监控
            readable, writeable, errors = select.select([self.socket, ], [], [], 1)

            if len(readable) > 0:
                message, address = self.socket.recvfrom(self.buff_size)
                msg = message.decode() # 转为字符串
                if msg[1] == '1':
                    ack_num = msg[0]
                    # 收到ACK， 重新计时
                    print('Server: 收到ACK ',msg[0])
                    if(len(self.send_windows) == 0):
                        continue
                    if int(ack_num) < int(self.send_windows[0].seq):
                        continue # 不是我们需要的ack，略过
                    pkg_timer[int(ack_num) - int(self.send_windows[0].seq)] = 0 # 对应pkg的timer置0
                    for i in range(len(self.send_windows)):
                        if ack_num == self.send_windows[i].seq:
                            self.send_windows[i].state = 2 # 对应的pkg的state置2，表示已成功发送
                            if i == 0: # 若该报文位于窗口第一个，则判断其后是否有连续的成功接收的报文
                                idx = 0
                                flag = 1
                                for idx in range(len(self.send_windows)):
                                    if self.send_windows[idx].state != 2:
                                        flag = 0
                                        break
                                idx += flag
                                self.send_windows = self.send_windows[idx:] # 窗口后移
                                pkg_timer = pkg_timer[idx:] # 计时器跟着后移
                            break
                else:
                    # 非ACK，说明是收到的数据，这是发送的每个pkg的timer+1
                    for index, item in enumerate(pkg_timer):
                        if self.send_windows[index].state != 2:
                            item += 1
                    print('Server: 收到MSG = ', msg[0])
                    ackNum = int(msg[0]) # 获得seq号
                    msg_timer = 0 # 接收报文的timer重新计时
                    # 连续接收数据则反馈当前ack
                    if last_ack == ackNum - 1:
                        # 模拟丢包和ack丢失
                        if random() < 0.1:
                            print('Server: 模拟发生丢包, 丢失的包的seq为', str(ackNum))
                            continue
                        if random() < 0.1:
                            print('Server: 模拟ACK丢失, 丢失ACK为 ', str(ackNum))
                            last_ack = ackNum
                            continue
                        # 检查接收窗口是否后移
                        toRemove = []
                        self.socket.sendto(str(Data(''.encode(), 1, ackNum)).encode(), address) # 返回ACK
                        print('Server: 发送ACK ', str(ackNum))
                        self.receive_windows.append(ackNum)
                        for i in range(self.M):
                            if (ackNum + i) not in self.receive_windows:
                                last_ack = ackNum + i - 1
                                break
                            else:
                                last_ack = ackNum + i
                                toRemove.append((ackNum + i))
                        for ele in toRemove:
                            self.receive_windows.remove(ele)
                    else: # 接收到的数据不是当前要的
                        # 若在接收窗口内，则缓存
                        if (ackNum) < (last_ack + 1 + self.M) and ackNum > last_ack and ackNum not in self.receive_windows:
                            self.receive_windows.append(ackNum)
                            print('Server: 缓存数据', ackNum)
                            self.socket.sendto(str(Data(''.encode(), 1, ackNum)).encode(), address)
                        # 是接收窗口之前的，发个ACK
                        elif ackNum <= last_ack:
                            self.socket.sendto(str(Data(''.encode(), 1, ackNum)).encode(), address)
                        else:
                            print('Server 扔弃', ackNum)
            else:
                # 未收到数据则计时器加一
                for index, item in enumerate(pkg_timer):
                    if self.send_windows[index].state != 2:
                        pkg_timer[index] = item + 1
                msg_timer += 1

    def start(self):
        # 读取文件
        buffer = []
        with open('server_send.txt', 'rb') as f:
            while True:
                seq = f.read(500)
                if len(seq) > 0:
                    buffer.append(seq)
                else:
                    break
        while True:
            # 无阻塞socket连接监控
            readable, writeable, errors = select.select([self.socket, ], [], [], 1)
            if (len(readable) > 0):
                message, address = self.socket.recvfrom(self.buff_size)
                if message.decode() == '-testgbn':
                    self.send(buffer)

s = SRServer()
s.start()