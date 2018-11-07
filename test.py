import threading
import time

from GBN.GBN_Client import GBNClient
from GBN.GBN_Server import GBNServer
from GBN.SR_Client import SRClient
from GBN.SR_Server import SRServer

# s = SRServer()
# c = SRClient()
s = GBNServer()
c = GBNClient()

t1 = threading.Thread(target=s.start, args=())
t2 = threading.Thread(target=c.start, args=())
t1.start()
time.sleep(0.2)
t2.start()

