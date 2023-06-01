from typing import Optional

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver import Remote
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options as Firefox_Options

from config import BROWSER_DATA, DATAPATH
from utils import (create_firefox_extension, get_chrome_driver,
                   get_geckodriver, sleep)


def create_proxied_browser_instance(proxy=None, use_proxy=False, headless=False, use_data_dir=False) -> webdriver.Chrome:
    chrome_options = webdriver.ChromeOptions()
    capabilities = webdriver.DesiredCapabilities.CHROME
    prefs = {'disk-cache-size': 4096}
    if headless:
        chrome_options.headless = True
        prefs["profile.managed_default_content_settings.images"] = 2
    chrome_options.add_experimental_option('prefs', prefs)
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("log-level=3")
    chrome_options.add_argument("ignore-certificate-errors")
    if use_data_dir:
        chrome_options.add_argument('user-data-dir={D}'.format(D=BROWSER_DATA))

    try:
        extension = create_firefox_extension()
    except Exception as a:
        print(a)
        extension = None
    if extension:
        chrome_options.add_extension(extension)

    driver_path = get_chrome_driver()
    if not driver_path:
        raise Exception("Chrome driver not found")
    driver: webdriver.Chrome = webdriver.Chrome(
        executable_path=driver_path,
        options=chrome_options,
        desired_capabilities=capabilities
    )

    return driver


def set_selenium_local_session(
        logfile,
        proxy_address: Optional[str] = None,
        proxy_port: Optional[str] = None,
        proxy_username: Optional[str] = None,
        proxy_password: Optional[str] = None,
        headless_browser: Optional[bool] = False,
        browser_profile_path: Optional[str] = None,
        disable_image_load: Optional[bool] = False,
        page_delay: Optional[int] = 25
) -> webdriver.Firefox:
    """Starts local session for a selenium server."""

    firefox_options = Firefox_Options()
    if headless_browser:
        firefox_options.add_argument("-headless")
    if browser_profile_path is not None:
        firefox_profile = webdriver.FirefoxProfile(
            profile_directory=browser_profile_path)
    else:
        firefox_profile = webdriver.FirefoxProfile()
    firefox_profile.set_preference("intl.accept_languages", "en-US")
    #firefox_profile.set_preference("general.useragent.override", user_agent)
    if disable_image_load:
        firefox_profile.set_preference("permissions.default.image", 2)

    if proxy_address and proxy_port:
        firefox_profile.set_preference("network.proxy.type", 1)
        firefox_profile.set_preference("network.proxy.http", proxy_address)
        firefox_profile.set_preference(
            "network.proxy.http_port", int(proxy_port))
        firefox_profile.set_preference("network.proxy.ssl", proxy_address)
        firefox_profile.set_preference(
            "network.proxy.ssl_port", int(proxy_port))

    firefox_profile.set_preference("media.volume_scale", "0.0")
    driver_path = get_geckodriver()
    browser = webdriver.Firefox(
        firefox_profile=firefox_profile,
        executable_path=driver_path,
        options=firefox_options,
        service_log_path=logfile
    )
    try:
        extension = create_firefox_extension()
    except Exception as a:
        print(a)
        extension = None
    if extension:
        browser.install_addon(extension, temporary=True)
    if proxy_username and proxy_password:
        proxy_authentication(browser, proxy_username, proxy_password)
    browser.implicitly_wait(page_delay)
    browser.set_window_size(1280, 1024)
    browser.minimize_window()
    return browser


def proxy_authentication(browser, proxy_username, proxy_password) -> bool:
    """ Authenticate proxy using popup alert window """
    try:
        sleep(2)
        alert_popup = browser.switch_to_alert()
        alert_popup.send_keys(
            "{username}{tab}{password}{tab}".format(
                username=proxy_username, tab=Keys.TAB, password=proxy_password
            )
        )
        alert_popup.accept()
        return True
    except WebDriverException as e:
        print(e)
        return False


def retry(max_retry_count=3, start_page=None):
    """
        Decorator which refreshes the _page and tries to execute the function again.
        Use it like that: @retry() => the '()' are important because its a decorator
        with params.
    """

    def real_decorator(org_func):
        def wrapper(*args, **kwargs):
            browser = None
            _start_page = start_page

            # try to find instance of a browser in the arguments
            # all webdriver classes (chrome, firefox, ...) inherit from Remote class
            for arg in args:
                if not isinstance(arg, Remote):
                    continue

                browser = arg
                break

            else:
                for _, value in kwargs.items():
                    if not isinstance(value, Remote):
                        continue

                    browser = value
                    break

            if not browser:
                print("not able to find browser in parameters!")
                return org_func(*args, **kwargs)

            if max_retry_count == 0:
                print("max retry count is set to 0, this function is useless right now")
                return org_func(*args, **kwargs)

            # get current _page if none is given
            if not start_page:
                _start_page = browser.current_url

            rv = None
            retry_count = 0
            while True:
                try:
                    rv = org_func(*args, **kwargs)
                    break
                except Exception as e:
                    # TODO: maybe handle only certain exceptions here
                    retry_count += 1

                    # if above max retries => throw original exception
                    if retry_count > max_retry_count:
                        raise e

                    rv = None

                    # refresh _page
                    browser.get(_start_page)

            return rv

        return wrapper

    return real_decorator
