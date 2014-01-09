from threading import Thread
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
import base64
import logging
import os
import requests
import signal
import sys
import time

FRAMES_PATH = os.getenv("FRAMES_PATH", 'frames')
PUBLISH_URLS = os.getenv("PUBLISH_URLS", 'http://localhost:9080/pub?id={channel}').split(",")
BASE64_ENCODE = "BASE64_ENCODE" in os.environ
LOG_FILE = os.getenv("LOG_FILE", None)
logger = logging.getLogger("broadcaster")


class EventHandler(FileSystemEventHandler):
    def on_created(self, event):
        if os.path.isdir(event.src_path):
            return
        Thread(target=post, args=(event.src_path,)).start()


def post(path):
    channel = os.path.basename(os.path.dirname(path))
    with open(path, 'rb') as content:
        data = content.read()
        if BASE64_ENCODE:
            data = base64.b64encode(data)
        for publish_url in PUBLISH_URLS:
            url = publish_url.format(channel=channel)
            r = requests.post(url, data=data)
            if r.status_code == 200:
                logger.debug('Pushed {} to {}'.format(path, url))
            else:
                logger.error(r)
    os.remove(path)


def setup_logger():
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    logger.setLevel(logging.DEBUG)
    if LOG_FILE:
        fh = logging.FileHandler(LOG_FILE)
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        logger.addHandler(fh)


def delete_all_files(top):
    for root, dirs, files in os.walk(top, topdown=False):
        for name in files:
            path = os.path.join(root, name)
            logger.info("Removing old file {}".format(path))
            os.remove(path)

def signal_handler(signal, frame):
    logger.warning("Interrupt. Shuting down.")
    sys.exit(0)

def run():
    setup_logger()
    logger.info('Started')
    event_handler = EventHandler()
    observer = Observer()
    delete_all_files(FRAMES_PATH)
    observer.schedule(event_handler, path=FRAMES_PATH, recursive=True)
    observer.start()
    signal.signal(signal.SIGINT, signal_handler)

    while True:
        time.sleep(1)
    observer.join()


if __name__ == "__main__":
    run()
