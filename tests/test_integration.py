from geventhttpclient import HTTPClient, URL
from multiprocessing.pool import ThreadPool
from base64 import b64encode
import os
import subprocess
import tempfile
import time


def get_async():
    pool = ThreadPool(processes=1)
    async_result = pool.apply_async(get)
    return async_result

def get():
    url = URL("http://localhost:9080/sub/channel")
    http = HTTPClient.from_url(url)
    response = http.get(url.path)
    return response

def run_broadcaster(frames_path, envs={}):
    env = os.environ.copy()
    env["FRAMES_PATH"] = frames_path
    env.update(envs)
    p = subprocess.Popen(["python", "broadcaster.py"], env=env)
    time.sleep(1)
    return p

def create_image(tempdir, channel, content):
    image_dir = os.path.join(tempdir, channel)
    os.mkdir(image_dir)
    image = tempfile.NamedTemporaryFile(dir=image_dir, delete=False)
    image.write(content)
    image.close()
    time.sleep(1)
    return image

def test_when_file_is_created_its_contents_are_posted():
    tempdir = tempfile.mkdtemp()
    p = run_broadcaster(tempdir)
    r = get_async()
    create_image(tempdir, "channel", "JPEG IMAGE")
    p.terminate()
    buffer_size = 45
    assert "JPEG IMAGE" in r.get(timeout=2).read(buffer_size)

def test_file_is_deleted_after_post():
    tempdir = tempfile.mkdtemp()
    p = run_broadcaster(tempdir)
    image = create_image(tempdir, "channel", "JPEG IMAGE\n")
    p.terminate()
    assert os.path.exists(image.name) is False

def test_contents_are_encoded():
    tempdir = tempfile.mkdtemp()
    p = run_broadcaster(tempdir, envs={"HTTP_BASE64_ENCODE": "1"})
    r = get_async()
    create_image(tempdir, "channel", "JPEG IMAGE")
    p.terminate()
    buffer_size = 45
    data = r.get(timeout=2).read(buffer_size)
    assert "JPEG IMAGE" not in data
    assert b64encode("JPEG IMAGE") in data
