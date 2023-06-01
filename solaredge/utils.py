import json
import logging
import os
import shutil
import zipfile
from datetime import datetime
from os.path import exists as path_exists
from os.path import sep as native_slash
from pathlib import Path
from random import gauss, uniform
from time import sleep as original_sleep
import os
import colorlog
import sys
from selenium.common.exceptions import (NoSuchElementException,
                                        TimeoutException, WebDriverException)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
from webdriverdownloader import ChromeDriverDownloader, GeckoDriverDownloader
from logging import Handler, Logger, StreamHandler
from config import ASSETS_PATH, EXTENSION_PATH
import shutil
STDEV = 0.5
sleep_percentage = 1
sleep_percentage *= uniform(0.9, 1.1)


def make_dir(_dir: str) -> None:
    if not os.path.exists(_dir):
        os.mkdir(_dir)


def mkdirs(path, mode):
    """
    """
    try:
        o_umask = os.umask(0)
        os.makedirs(path, mode)
    except OSError:
        if not os.path.isdir(path):
            raise
    finally:
        os.umask(o_umask)


def randomize_time(mean):
    allowed_range = mean * STDEV
    stdev = allowed_range / 3  # 99.73% chance to be in the allowed range

    t = 0
    while abs(mean - t) > allowed_range:
        t = gauss(mean, stdev)

    return t


def set_sleep_percentage(percentage):
    global sleep_percentage
    sleep_percentage = percentage / 100
    sleep_percentage = sleep_percentage * uniform(0.9, 1.1)


def sleep(t, custom_percentage=None):
    if custom_percentage is None:
        custom_percentage = sleep_percentage
    time = randomize_time(t) * custom_percentage
    original_sleep(time)


def sleep_actual(t):
    original_sleep(t)


def get_time(labels):
    """ To get a use out of this helpful function
        catch in the same order of passed parameters """
    if not isinstance(labels, list):
        labels = [labels]

    results = []

    for label in labels:
        if label == "this_minute":
            results.append(datetime.now().strftime("%M"))

        if label == "this_hour":
            results.append(datetime.now().strftime("%H"))

        elif label == "today":
            results.append(datetime.now().strftime("%Y-%m-%d"))

    return results if len(results) > 1 else results[0]


def get_chrome_driver():
    home = os.path.expanduser('~')
    driverpath = os.path.join(home, 'browser-drivers')
    if not os.path.exists(driverpath):
        os.mkdir(driverpath)
        sys.path.insert(0, str(Path(driverpath).absolute()))
    else:
        for filename in os.listdir(driverpath):
            if filename == 'chromedriver.exe':
                return os.path.join(driverpath, filename)
    if chrome_path := shutil.which("chromedriver") or shutil.which(
        "chromedriver.exe"
    ):
        return chrome_path

    try:
        gdd = ChromeDriverDownloader(driverpath, driverpath)
        _, sym_path = gdd.download_and_install()
        return sym_path
    except OSError:
        return None


def get_geckodriver():
    if gecko_path := shutil.which("geckodriver") or shutil.which(
        "geckodriver.exe"
    ):
        return gecko_path
    gdd = GeckoDriverDownloader(ASSETS_PATH, ASSETS_PATH)
    _, sym_path = gdd.download_and_install()
    return sym_path


def create_firefox_extension():
    ext_path = os.path.abspath(os.path.join(
        EXTENSION_PATH, "firefox_extension"))
    ext_path = str(Path(ext_path).absolute())
    # save into assets folder
    zip_file = os.path.join(ASSETS_PATH, 'firefox')
    if not os.path.exists(zip_file):
        os.mkdir(zip_file)
    zip_file = os.path.join(zip_file, "extension.crf")
    zip_file = str(Path(zip_file).absolute())

    files = ["manifest.json", 'content.js', "background.js",
             "arrive.js", 'beasts-32.png', 'beasts-32-light.png', 'beasts-48.png']
    with zipfile.ZipFile(zip_file, "w", zipfile.ZIP_DEFLATED, False) as zipf:
        for file in files:
            zipf.write(ext_path + native_slash + file, file)

    return zip_file


def get_current_url(browser):
    """ Get URL of the loaded webpage """
    try:
        current_url = browser.execute_script("return window.location.href")

    except WebDriverException:
        try:
            current_url = browser.current_url

        except WebDriverException:
            current_url = None

    return current_url


def web_address_navigator(browser, link):
    """Checks and compares current URL of web _page and the URL to be
    navigated and if it is different, it does navigate"""
    current_url = get_current_url(browser)
    page_type = None  # file or directory

    # remove slashes at the end to compare efficiently
    if current_url is not None and current_url.endswith("/"):
        current_url = current_url[:-1]

    if link.endswith("/"):
        link = link[:-1]
        page_type = "dir"  # slash at the end is a directory

    new_navigation = current_url != link

    if current_url is None or new_navigation:
        link = f"{link}/" if page_type == "dir" else link
        total_timeouts = 0
        # navigate faster

        while True:
            try:
                browser.get(link)
                sleep(2)
                break
            except TimeoutException as exc:
                if total_timeouts >= 7:
                    raise TimeoutException(
                        f"""Retried {total_timeouts} times to GET '{str(link).encode("utf-8")}' webpage but failed out of a timeout!\n\t{str(exc).encode("utf-8")}"""
                    )
                total_timeouts += 1
                sleep(2)


def reload_webpage(browser):
    """ Reload the current webpage """
    browser.execute_script("location.reload()")
    sleep(2)

    return True


def explicit_wait(browser, track, ec_params, logger, timeout=35, notify=True):
    """
    Explicitly wait until expected condition validates

    :param notify:
    :param timeout:
    :param browser: webdriver instance
    :param track: short name of the expected condition
    :param ec_params: expected condition specific parameters - [param1, param2]
    :param logger: the logger instance
    """

    if not isinstance(ec_params, list):
        ec_params = [ec_params]

    # find condition according to the tracks
    if track == "VOEL":
        elem_address, find_method = ec_params
        ec_name = "visibility of element located"

        find_by = (
            By.XPATH
            if find_method == "XPath"
            else By.CSS_SELECTOR
            if find_method == "CSS"
            else By.CLASS_NAME
        )
        locator = (find_by, elem_address)
        condition = ec.visibility_of_element_located(locator)

    elif track == "TC":
        expect_in_title = ec_params[0]
        ec_name = "title contains '{}' string".format(expect_in_title)

        condition = ec.title_contains(expect_in_title)

    elif track == "PFL":
        ec_name = "_page fully loaded"

        def condition(browser): return browser.execute_script(
            "return document.readyState"
        ) in ["complete" or "loaded"]

    elif track == "SO":
        ec_name = "staleness of"
        element = ec_params[0]

        condition = ec.staleness_of(element)
    else:
        def fail(driver):
            return False

        condition = fail
    try:
        wait = WebDriverWait(browser, timeout)
        result = wait.until(condition)
    except TimeoutException:
        if notify is True:
            logger.info(
                "Timed out with failure while explicitly waiting until {}!\n".format(
                    ec_name
                )
            )
        return False

    return result


def get_page_title(browser, logger):
    """ Get the title of the webpage """
    # wait for the current _page fully load to get the correct _page's title
    explicit_wait(browser, "PFL", [], logger, 10)

    try:
        page_title = browser.title

    except WebDriverException:
        try:
            page_title = browser.execute_script("return document.title")

        except WebDriverException:
            try:
                page_title = browser.execute_script(
                    "return document.getElementsByTagName('title')[0].text"
                )

            except WebDriverException:
                logger.info("Unable to find the title of the _page :(")
                return None

    return page_title


def is_page_available(browser, logger):
    """ Check if the _page is available and valid """
    expected_keywords = ["Page Not Found", "Content Unavailable"]
    page_title = get_page_title(browser, logger)
    if any(keyword in page_title for keyword in expected_keywords):
        reload_webpage(browser)
        page_title = get_page_title(browser, logger)
        if any(keyword in page_title for keyword in expected_keywords):
            if "Page Not Found" in page_title:
                logger.warning(
                    "The _page isn't available!\t~the link may be broken, "
                    "or the _page may have been removed..."
                )

            elif "Content Unavailable" in page_title:
                logger.warning(
                    "The _page isn't available!\t~the user may have blocked " "you..."
                )

            return False

    return True


def set_log_context(logger, value):
    """
    Walks the tree of loggers and tries to set the context for each handler
    :param logger: logger
    :param value: value to set
    """
    _logger = logger
    while _logger:
        for handler in _logger.handlers:
            try:
                handler.set_context(value)
            except AttributeError:
                # Not all handlers need to have context passed in so we ignore
                # the error when handlers do not have set_context defined.
                pass
        _logger = _logger.parent if _logger.propagate is True else None


class LoggingMixin:
    """Convenience super-class to have a logger
        configured with the class name
    """

    def __init__(self, context=None):
        self._set_context(context)

    @property
    def log(self) -> Logger:
        """
        Returns a logger.
        """
        try:
            return self._log
        except AttributeError:
            self._log = logging.getLogger(
                f'{self.__class__.__module__}.{self.__class__.__name__}'
            )
            return self._log

    def _set_context(self, context):
        if context is not None:
            set_log_context(self.log, context)


class BotRuntimeHandler(logging.Handler):
    """ Creates New log entries for each bot run"""

    def __init__(self, base_log_folder: str):
        super().__init__()
        self.local_base = base_log_folder
        self.handler = None
        local_loc = self._init_file()
        self.handler = logging.FileHandler(local_loc, encoding='utf-8')
        if self.formatter:
            self.handler.setFormatter(self.formatter)
        self.handler.setLevel(self.level)

    def emit(self, record):
        if self.handler:
            self.handler.emit(record)

    def flush(self):
        if self.handler:
            self.handler.flush()

    def close(self):
        if self.handler:
            self.handler.close()

    def _init_file(self):
        """
        """
        try:
            relative_path = f"{str(datetime.now().date())}/runtime.log"
            full_path = os.path.join(self.local_base, relative_path)
            directory = os.path.dirname(full_path)
            if not os.path.exists(directory):
                mkdirs(directory, 0o777)

            if not os.path.exists(full_path):
                open(full_path, "a").close()
                os.chmod(full_path, 0o666)

            return full_path
        except Exception as e:
            print(e)


def create_logger(name: str, level: int = logging.DEBUG) -> None:
    """Create a configured instance of logger.

    :param int level:
        Describe the severity level of the logs to handle.
    """
    from config import LOG_PATH

    logger = logging.getLogger(name)

    date_fmt = '%Y-%m-%d %H:%M:%S'
    fmt = '[%(asctime)s,%(msecs)-d][%(threadName)-1s][%(levelname)-1s]: %(message)s'

    formatter = logging.Formatter(fmt, datefmt=date_fmt)
    colored_formater = colorlog.ColoredFormatter(
        "[%(blue)s%(asctime)s,%(msecs)-d%(reset)s][%(log_color)s%(threadName)-1s%(reset)s][%(log_color)s%(levelname)-1s%(reset)s] %(log_color)s%(message)s",
        datefmt=date_fmt,
        reset=True,
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        },
        secondary_log_colors={
            'message': {
                'ERROR': 'red',
                'CRITICAL': 'red',
                'INFO': 'blue',

            }
        },
        style='%'
    )

    console = colorlog.StreamHandler()
    console.setFormatter(colored_formater)
    bot_handler = BotRuntimeHandler(LOG_PATH)
    bot_handler.setFormatter(formatter)
    logger.addHandler(console)
    logger.addHandler(bot_handler)
    logger.setLevel(level)

    return None
