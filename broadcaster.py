from threading import Thread
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
import base64
import logging
import os
import requests
import time
import sys

FRAMES_PATH = os.getenv("FRAMES_PATH", 'frames')
PUBLISH_URL = os.getenv("PUBLISH_URL", 'http://localhost:9080/pub?id={channel}')
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
        r = requests.post(PUBLISH_URL.format(channel=channel), data=data)
        if r.status_code == 200:
            logger.debug('Pushed {}'.format(path))
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


def run():
    setup_logger()
    event_handler = EventHandler()
    observer = Observer()
    observer.schedule(event_handler, path=FRAMES_PATH, recursive=True)
    observer.start()
    logger.info('Started')

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    run()
