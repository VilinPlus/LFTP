import threading
import time

timeEnd = 0

def count(self):
    global timeEnd
    while self.re_transmis:
        timeEnd = time.perf_counter()

timeStart = time.perf_counter()
thread_time = threading.Thread(target=count, args=())
thread_time.start()
