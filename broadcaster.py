from threading import Thread
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
import base64
import logging
import os
import redis
import requests
import signal
import sys
import time
import uuid

FRAMES_PATH = os.getenv("FRAMES_PATH", 'frames')

HTTP_HOST_LIST_URL = os.getenv("HTTP_HOST_LIST_URL", None)
HTTP_HOST = os.getenv("HTTP_HOST", "localhost")
HTTP_PORT = int(os.getenv("HTTP_PORT", 9080))
HTTP_PUBLISH_URL_TEMPLATE = os.getenv("HTTP_PUBLISH_URLS_TEMPLATE", 'http://{host}:{port}/pub?id={channel}')
http_hosts = requests.get(HTTP_HOST_LIST_URL).json() if HTTP_HOST_LIST_URL else [HTTP_HOST]

REDIS_HOST_LIST_URL = os.getenv("REDIS_HOST_LIST_URL", None)
REDIS_HOST = os.getenv("REDIS_HOST", "")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_TTL = int(os.getenv("REDIS_TTL", 60))
redis_hosts = requests.get(REDIS_HOST_LIST_URL).json() if REDIS_HOST_LIST_URL else [REDIS_HOST]

BASE64_ENCODE = "BASE64_ENCODE" in os.environ
LOG_FILE = os.getenv("LOG_FILE", None)
LOG_LEVEL = getattr(logging, os.getenv("LOG_LEVEL", "debug").upper())
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
        for http_host in [h for h in http_hosts if h]:
            url = HTTP_PUBLISH_URL_TEMPLATE.format(channel=channel, host=http_host, port=HTTP_PORT)
            r = requests.post(url, data=data)
            if r.status_code == 200:
                logger.debug('Pushed {} to {}'.format(path, url))
            else:
                logger.error(r)
        for redis_host in [h for h in redis_hosts if h]:
            try:
                r = redis.StrictRedis(host=redis_host, port=REDIS_PORT, db=REDIS_DB)
                key = uuid.uuid4()
                timestamp = os.path.getmtime(path)
                r.zadd(channel, timestamp, key)
                r.setex(key, REDIS_TTL, data)
                r.zremrangebyscore(channel, "-inf", timestamp - REDIS_TTL)
                logger.debug('Pushed {} to {}. Key={}, timestamp={}'.format(path, redis_host, key, timestamp))
            except Exception as err:
                logger.error(err)
    os.remove(path)


def setup_logger():
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler = None
    if LOG_FILE:
        handler = logging.FileHandler(LOG_FILE)
    else:
        handler = logging.StreamHandler(sys.stdout)

    logger.setLevel(LOG_LEVEL)
    handler.setLevel(LOG_LEVEL)
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def delete_all_files(top):
    for root, dirs, files in os.walk(top, topdown=False):
        for name in files:
            path = os.path.join(root, name)
            logger.debug("Removing old file {}".format(path))
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
