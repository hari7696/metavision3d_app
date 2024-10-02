# reference https://fanchenbao.medium.com/python3-logging-with-multiprocessing-f51f460b8778
import logging
from logging import handlers
from time import sleep
import datetime


def listener_configurer(log_dir):
    root = logging.getLogger()
    current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    file_location = f'{log_dir}/vision_{current_time}.log'
    file_handler = handlers.RotatingFileHandler(file_location, 'w')
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(processName)-10s %(name)s %(levelname)-8s %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    root.addHandler(file_handler)
    root.addHandler(console_handler)
    root.setLevel(logging.INFO)
    root.propagate = True

def worker_configurer(queue):
    h = logging.handlers.QueueHandler(queue)  # Just the one handler needed
    root = logging.getLogger()
    root.addHandler(h)
    # send all messages, for demo; no other level or filter logic applied.
    root.setLevel(logging.INFO)


def listener_process(queue, log_dir):
    listener_configurer(log_dir)
    while True:
        while not queue.empty():
            record = queue.get()
            logger = logging.getLogger(record.name)
            logger.handle(record)
        sleep(1)