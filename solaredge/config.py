import os
from pathlib import Path

ROOT = os.path.dirname(os.path.realpath(__file__))

DATAPATH = os.path.join(ROOT, 'data')
if not os.path.exists(DATAPATH):
    os.mkdir(DATAPATH)

SCRAP_DATA = os.path.join(DATAPATH, 'scrap_data')
if not os.path.exists(SCRAP_DATA):
    os.mkdir(SCRAP_DATA)

BROWSER_DATA = os.path.join(DATAPATH, 'browser_data')
if not os.path.exists(BROWSER_DATA):
    os.mkdir(BROWSER_DATA)

LOG_PATH = os.path.join(ROOT, 'logs')
if not os.path.exists(LOG_PATH):
    os.mkdir(LOG_PATH)

ASSETS_PATH = os.path.join(ROOT, 'assets')
if not os.path.exists(ASSETS_PATH):
    os.mkdir(ASSETS_PATH)

EXTENSION_PATH = os.path.join(ROOT, 'extension')
LOG_FILE = os.path.join(LOG_PATH, 'browser.log')
