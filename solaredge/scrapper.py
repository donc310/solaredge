from __future__ import absolute_import

import os
import queue
import signal
import sys
import threading
from abc import ABCMeta, abstractmethod
from csv import DictWriter
from datetime import datetime
from time import sleep
from typing import Any, Dict, List, NamedTuple

from selenium import webdriver
from selenium.common.exceptions import (JavascriptException,
                                        NoSuchElementException,
                                        TimeoutException, WebDriverException)

import logging
from config import LOG_FILE, SCRAP_DATA
from local_browser import (create_proxied_browser_instance,
                           set_selenium_local_session)
from utils import is_page_available, web_address_navigator

logger = logging.getLogger()
lock = threading.Lock()
EXIT_SIG = 0
browser: webdriver.Chrome = create_proxied_browser_instance()
_url_ = "https://monitoringpublic.solaredge.com/solaredge-web/p/site/public?name=myerssolargrumbles#/layout"


class ScrapMessage(NamedTuple):
    datetime: datetime
    data: List[Dict]


class AbstractThreadWorker(metaclass=ABCMeta):
    @abstractmethod
    def put_message(self):
        """"""
        raise NotImplementedError()


class ScrappingThread(threading.Thread):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._interested_threads: List[AbstractThreadWorker] = []

    def load_page(self):
        try:
            browser.get(_url_)
        except TimeoutException as e:
            logger.error(e)

    def run(self):
        self.load_page()
        while not EXIT_SIG:
            sleep(1*60)
            try:
                data = browser.execute_script('return __get_data()')
                if data and len(data['data']):
                    message = ScrapMessage(
                        datetime=datetime.now(), data=data['data'])
                    self.dispatch_message(message)
                browser.execute_script('__scrap_data()')
                print('scraping data')
                sleep(1*60)
                data = browser.execute_script('return __get_data()')
                if data and len(data['data']):
                    message = ScrapMessage(
                        datetime=datetime.now(), data=data['data'])
                    self.dispatch_message(message)
            except JavascriptException as js_error:
                print(js_error)

    def register_interest(self, thread: AbstractThreadWorker):
        self._interested_threads.append(thread)

    def dispatch_message(self, message: ScrapMessage):
        for thread in self._interested_threads:
            thread.put_message(message)


class WorkerThread(AbstractThreadWorker, threading.Thread):
    def __init__(self, role: str, *args, **kwargs):
        threading.Thread.__init__(self, *args, **kwargs)
        self.queue = queue.Queue()
        self.role = role

    def run(self):
        dispatcher_thread.register_interest(self)
        while not EXIT_SIG:
            sleep(1*60)
            message = self.queue.get()
            if isinstance(message, ScrapMessage):
                self.process_message(message)

    def write_csv(self, data: List[Dict], path: str):
        field_names = data[0].keys()
        with open(path, 'a+', newline='') as write_obj:
            dict_writer = DictWriter(write_obj, fieldnames=field_names)
            for row in data:
                dict_writer.writerow(row)

    def get_write_path(self, datetime: datetime):
        today = datetime.date()
        root = os.path.join(SCRAP_DATA, str(today))
        if not os.path.exists(root):
            os.mkdir(root)
        csv_path = os.path.join(root, 'processed.csv')
        dump = os.path.join(root, 'dump')
        if not os.path.exists(dump):
            os.mkdir(dump)
        return csv_path, os.path.join(dump, str(datetime))

    def dump_json(self, data: Dict, path: str):
        pass

    def process_message(self, message: ScrapMessage):
        if self.role == 'DATA_PROCESSOR':
            processed: List[Dict] = []
            for scrap_response in message.data:
                data = scrap_response['res']
                if data and isinstance(data, dict):
                    for x, y in data.items():
                        i = {}
                        i['panel'] = x
                        i['energy'] = y['energy']
                        i['units'] = y['units']
                        i['unscaledEnergy'] = y['unscaledEnergy']
                        i['moduleEnergy'] = y['moduleEnergy']
                        i['relayState'] = y['relayState']
                        i['date'] = message.datetime
                        processed.append(i)
            if len(processed):
                csv_path, json_path = self.get_write_path(message.datetime)
                self.write_csv(processed, csv_path)
                self.dump_json(message.data[0]['res'], json_path)

    def put_message(self, message: Any):
        self.queue.put(message)


class RefreshThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def run(self):
        while not EXIT_SIG:
            sleep(10*60)
            print("Acquiring lock")
            with lock:
                print("Lock Acquired")
                if browser:
                    browser.refresh()


def terminateProcess(signalNumber, frame):
    global EXIT_SIG
    print('(SIGTERM)recieved terminating the process gracefully')
    EXIT_SIG = 1
    exist_gracefully()


def exist_gracefully():
    global browser
    if browser:
        browser.quit()
    sys.exit(0)


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, terminateProcess)
    signal.signal(signal.SIGINT, terminateProcess)
    dispatcher_thread = ScrappingThread(name='scrapper')
    dispatcher_thread.start()
    worker_threads = []
    roles = ['DATA_PROCESSOR']
    for role in roles:
        worker_thread = WorkerThread(role, name=role)
        worker_thread.start()
        worker_threads.append(worker_thread)
    refresher = RefreshThread(name='refresher').start()
    dispatcher_thread.join()
