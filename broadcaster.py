from threading import Thread
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
import os
import requests
import time

FRAMES_PATH = 'frames'
PUBLISH_URL = 'http://localhost:9080/pub?id={channel}'


class EventHandler(FileSystemEventHandler):
    def on_created(self, event):
        Thread(target=post, args=(event.src_path,)).start()


def post(path):
    channel = os.path.basename(os.path.dirname(path))
    with open(path, 'rb') as content:
        r = requests.post(PUBLISH_URL.format(channel=channel), data=content.read())
        if r.status_code == 200:
            print 'Pushed {}'.format(path)
        else:
            print r
    os.remove(path)


if __name__ == "__main__":
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
