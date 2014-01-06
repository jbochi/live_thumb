from threading import Thread
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
import base64
import os
import requests
import time

FRAMES_PATH = os.getenv("FRAMES_PATH", 'frames')
PUBLISH_URL = os.getenv("PUBLISH_URL", 'http://localhost:9080/pub?id={channel}')
BASE64_ENCODE = "BASE64_ENCODE" in os.environ


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
            print 'Pushed {}'.format(path)
        else:
            print r
    os.remove(path)


def run():
    event_handler = EventHandler()
    observer = Observer()
    observer.schedule(event_handler, path=FRAMES_PATH, recursive=True)
    observer.start()
    print 'started'

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    run()
