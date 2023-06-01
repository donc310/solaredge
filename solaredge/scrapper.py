from __future__ import absolute_import

import logging
import os
import queue
import random
import signal
import sys
import threading
import time
from abc import ABCMeta, abstractmethod
from csv import DictWriter
from datetime import datetime
from typing import Any, Dict, List, NamedTuple
import json
from selenium import webdriver
from selenium.common.exceptions import (JavascriptException,
                                        NoSuchElementException,
                                        TimeoutException, WebDriverException)

from config import LOG_FILE, SCRAP_DATA
from local_browser import (create_proxied_browser_instance,
                           set_selenium_local_session)
from utils import create_logger, is_page_available, web_address_navigator

create_logger('solaredge')
logger = logging.getLogger('solaredge')
lock = threading.Lock()

EXIT_SIG = 0
try:
    browser: webdriver.Chrome = create_proxied_browser_instance()
except Exception as e:
    logger.error(e)
    sys.exit(-1)

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
        threading.Thread.__init__(self, *args, **kwargs)
        self._interested_threads: List[AbstractThreadWorker] = []

    def load_page(self):
        try:
            browser.get(_url_)
            self.ensure_extension_loaded()
            web_address_navigator(browser, _url_)
        except TimeoutException as e:
            logger.error(e)

    def get_random(self) -> int:
        return random.randint(60, (2*60))

    def ensure_extension_loaded(self):
        try:
            if engine := browser.execute_script(
                'return document.getElementById("_ENGINE_")'
            ):
                logger.info(
                    f"Scrap extension loaded , version:{engine.get_attribute('data-version')} ts:{engine.get_attribute('data-ts')}"
                )
                return
        except JavascriptException as err_r:
            logger.error(err_r)

    def run(self):
        self.load_page()
        while not EXIT_SIG:
            twait = self.get_random()
            logger.info(f"Waiting for {twait} seconds ")
            time.sleep(twait)
            try:
                data = browser.execute_script('return __get_data()')
                if data and len(data['data']):
                    message = ScrapMessage(
                        datetime=datetime.now(), data=data['data'])
                    self.dispatch_message(message)
                browser.execute_script('__scrap_data()')
                logger.info(f'scraping data {datetime.now()}')
                time.sleep(30)
                data = browser.execute_script('return __get_data()')
                if data and len(data['data']):
                    message = ScrapMessage(
                        datetime=datetime.now(), data=data['data'])
                    self.dispatch_message(message)
            except JavascriptException as js_error:
                logger.error(js_error)

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
            time.sleep(1*60)
            message = self.queue.get()
            if isinstance(message, ScrapMessage):
                self.process_message(message)

    def write_csv(self, data: List[Dict], path: str):
        logger.info(f"Writing new data to {path}")
        field_names = list(data[0].keys())
        try:
            write_obj = None
            if exits := os.path.exists(path):
                write_obj = open(path, 'a+', newline='')
                dict_writer = DictWriter(write_obj, fieldnames=field_names)
            else:
                write_obj = open(path, 'w', newline='')
                dict_writer = DictWriter(write_obj, fieldnames=field_names)
                dict_writer.writeheader()
            dict_writer.writerows(data)
        except Exception as error:
            logger.error(error)
        finally:
            if write_obj:
                write_obj.close()

    def get_write_path(self, datetime: datetime):
        today = datetime.date()
        root = os.path.join(SCRAP_DATA, str(today))
        if not os.path.exists(root):
            os.mkdir(root)
        csv_path = os.path.join(root, 'processed.csv')
        dump = os.path.join(root, 'dump')
        if not os.path.exists(dump):
            os.mkdir(dump)
        return csv_path, os.path.join(dump, str(datetime.timestamp()).replace('.', '_')+'.json')

    def dump_json(self, data: Dict, path: str):
        try:
            with open(path, 'w') as json_obj:
                logger.info(f"Dumping data to  {path}")
                json.dump(data, json_obj)
        except Exception as e:
            logger.error(e)

    def process_message(self, message: ScrapMessage):
        if self.role != 'DATA_PROCESSOR':
            return
        logger.info(f'Recieved new message {message.__class__.__name__}')
        processed: List[Dict] = []
        for scrap_response in message.data:
            data = scrap_response['res']
            if data and isinstance(data, dict):
                for x, y in data.items():
                    i = {
                        'panel': x,
                        'energy': y['energy'],
                        'units': y['units'],
                        'unscaledEnergy': y['unscaledEnergy'],
                        'moduleEnergy': y['moduleEnergy'],
                        'relayState': y['relayState'],
                        'date': message.datetime,
                    }
                    processed.append(i)
        if len(processed):
            csv_path, json_path = self.get_write_path(message.datetime)
            self.write_csv(processed, csv_path)
            self.dump_json(message.data[0]['res'], json_path)

    def put_message(self, message: Any):
        self.queue.put(message)


class RefreshThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self, *args, **kwargs)
        self._log = logging.getLogger('solaredge.bot')

    def run(self):
        while not EXIT_SIG:
            time.sleep(10*60)
            logger.info("Acquiring lock")
            with lock:
                logger.info("Lock Acquired")
                if browser:
                    try:
                        logger.info("Refreshing browser")
                        browser.refresh()
                        logger.info("Browser refreshed")
                        web_address_navigator(browser, _url_)
                    except Exception as e:
                        logger.error(f"Error refreshing browser, errpr:{e}")
            logger.info("Lock releashed")


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
