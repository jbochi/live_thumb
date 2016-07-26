from threading import Thread
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from multiprocessing.pool import Pool
import multiprocessing
import datetime
import base64
import logging
import os
import re
import redis
import requests
import signal
import sys
import time
import uuid
import multiprocessing

FRAMES_PATH = os.getenv("FRAMES_PATH", 'frames')

HTTP_HOST_LIST_URL = os.getenv("HTTP_HOST_LIST_URL", None)
HTTP_HOST = os.getenv("HTTP_HOST", "localhost")
HTTP_PORT = int(os.getenv("HTTP_PORT", 9080))
HTTP_PUBLISH_URL_TEMPLATE = os.getenv("HTTP_PUBLISH_URLS_TEMPLATE", 'http://{host}:{port}/pub?id={channel}')
HTTP_FILTER_CHANNEL = os.getenv("HTTP_FILTER_CHANNEL", None) # Regex to filter channels
http_hosts = requests.get(HTTP_HOST_LIST_URL).json() if HTTP_HOST_LIST_URL else [HTTP_HOST]

HTTP_REGEX = re.compile(HTTP_FILTER_CHANNEL) if HTTP_FILTER_CHANNEL else None

REDIS_HOST_LIST_URL = os.getenv("REDIS_HOST_LIST_URL", None)
REDIS_HOST = os.getenv("REDIS_HOST", "")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
REDIS_TTL = int(os.getenv("REDIS_TTL", 60))
REDIS_SAMPLE_RATE = int(os.getenv("REDIS_SAMPLE_RATE", 8)) # 1/8 images will be post to redis
REDIS_FILTER_CHANNEL = os.getenv("REDIS_FILTER_CHANNEL", None) # Regex to filter channels
REDIS_REGEX = re.compile(REDIS_FILTER_CHANNEL) if REDIS_FILTER_CHANNEL else None

redis_hosts = requests.get(REDIS_HOST_LIST_URL).json() if REDIS_HOST_LIST_URL else [REDIS_HOST]

WORKERS = int(os.getenv("WORKERS", multiprocessing.cpu_count()))
EVENT_QUEUE_MAX_SIZE = int(os.getenv("EVENT_QUEUE_MAX_SIZE", WORKERS * 2))
MAX_TASKS_PER_WORKER = int(os.getenv("MAX_TASKS_PER_WORKER", 10))
BASE64_ENCODE = "BASE64_ENCODE" in os.environ
LOG_FILE = os.getenv("LOG_FILE", None)
LOG_LEVEL = getattr(logging, os.getenv("LOG_LEVEL", "debug").upper())
logger = logging.getLogger("broadcaster")


def log_on_error(func):
    def f(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception as err:
            logger.exception(err)
    return f

class EventHandler(FileSystemEventHandler):
    def __init__(self, queue):
        super(EventHandler, self).__init__()
        self.queue = queue
        self.last_event = datetime.datetime.now()

    def on_created(self, event):
        self.last_event = datetime.datetime.now()
        if os.path.isdir(event.src_path):
            return
        self.queue.put_nowait(event.src_path)


@log_on_error
def post(path):
    channel = os.path.basename(os.path.dirname(path))
    with open(path, 'rb') as content:
        data = content.read()
        http_data = base64.b64encode(data) if BASE64_ENCODE else data
        post_http(channel, http_data, path)
        post_redis(channel, data, path)
    os.remove(path)


@log_on_error
def post_http(channel, data, path):
    if HTTP_FILTER_CHANNEL and not HTTP_REGEX.match(channel):
        return
    for host in [h for h in http_hosts if h]:
        post_http_to_host(channel, data, path, host)


@log_on_error
def post_http_to_host(channel, data, path, host):
    url = HTTP_PUBLISH_URL_TEMPLATE.format(channel=channel, host=host, port=HTTP_PORT)
    r = requests.post(url, data=data, timeout=0.5)
    if r.status_code == 200:
        logger.debug('Pushed {} to {}'.format(path, url))
    else:
        logger.error(r)


@log_on_error
def post_redis(channel, data, path):
    if REDIS_FILTER_CHANNEL and not REDIS_REGEX.match(channel):
        return

    digits = re.findall("(\d+)", path)
    if digits:
        count = int(digits[-1]) % REDIS_SAMPLE_RATE
        if count != 0:
            logger.debug('Image {} not sampled ({}/{}).'.format(path, count, REDIS_SAMPLE_RATE))
            return
    for redis_host in [h for h in redis_hosts if h]:
        try:
            r = redis.StrictRedis(host=redis_host, port=REDIS_PORT, db=REDIS_DB, password=REDIS_PASSWORD)

            channel_ttl = r.get("thumb/" + channel + "/ttl")
            channel_ttl = int(channel_ttl) if channel_ttl else REDIS_TTL

            key = "thumb/" + channel
            blob_key = "blob/" + str(uuid.uuid4())
            timestamp = os.path.getmtime(path)
            utctimestamp = int(time.mktime(datetime.datetime.utcfromtimestamp(timestamp).timetuple()))
            r.zadd(key, utctimestamp, blob_key)
            r.setex(blob_key, channel_ttl, data)
            r.zremrangebyscore(key, "-inf", utctimestamp - channel_ttl)
            logger.debug('Pushed {} to {}. Key={}, utctimestamp={}'.format(path, redis_host, blob_key, utctimestamp))
        except Exception as err:
            logger.error(err)


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


def to_milliseconds(time_in_seconds):
    return int(time_in_seconds * 1000)


def delete_all_files(top):
    for root, dirs, files in os.walk(top, topdown=False):
        for name in files:
            path = os.path.join(root, name)
            logger.debug("Removing old file {}".format(path))
            os.remove(path)

def worker(queue):
    executed = 0
    worker_uuid = uuid.uuid4()
    try:
        logger.debug('[Worker:%s] started', worker_uuid)
        while executed < MAX_TASKS_PER_WORKER:
            executed += 1
            live_thumb_path = queue.get()
            try:
                logger.debug('[Worker:%s] picked up live_thumb: %s', worker_uuid, live_thumb_path)
                process_start = time.time()
                post(live_thumb_path)
                logger.info('[EVENT:live_thumb_processed] live_thumb_path=%s process_time_ms=%s',
                            live_thumb_path,
                            to_milliseconds(time.time() - process_start))
            except Exception as err:
                logger.exception(err)
    except Exception as err:
        logger.exception(err)
    sys.exit(0)


def signal_handler(signum, _):
    logger.warning("Interrupt signal %s. Shutting down.", signum)
    sys.exit(0)


def init_observer():
    try:
        from inotify_observer import InotifyObserver
        Observer = InotifyObserver
    except ImportError:
        logger.warning("pyinotify not found. Falling back to watchdog")
        from watchdog.observers.polling import PollingObserver
        Observer = PollingObserver

    observer = Observer(timeout=0.5)
    return observer

def run():
    setup_logger()
    logger.info('Started')
    queue = multiprocessing.Queue(maxsize=EVENT_QUEUE_MAX_SIZE)
    pool = Pool(processes=WORKERS,
            initializer=worker,
            initargs=(queue,))

    event_handler = EventHandler(queue)
    observer = init_observer()
    try:
        delete_all_files(FRAMES_PATH)
        observer.schedule(event_handler, path=FRAMES_PATH, recursive=True)
        signal.signal(signal.SIGINT, signal_handler)
        observer.start()

        while True:
            pool._maintain_pool() #restart workers if needed
            time.sleep(1)
            now = datetime.datetime.now()
            if now - event_handler.last_event > datetime.timedelta(minutes=1):
                logger.warning("No events received in the last minute.")
                # Sometimes watchdog stops receiving events.
                # We exit, so the process can be restarted.
                break
    except KeyboardInterrupt as err:
        logger.warning("Keyboard interruption")
    except Exception as err:
        logger.exception(err)
    finally:
        observer.stop()
    observer.join()
    pool.terminate()
    logger.warning("Bye")


if __name__ == "__main__":
    run()
