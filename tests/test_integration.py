from base64 import b64encode
from geventhttpclient import HTTPClient, URL
from multiprocessing.pool import ThreadPool
import datetime
import os
import redis
import subprocess
import tempfile
import time


def get_async():
    pool = ThreadPool(processes=1)
    async_result = pool.apply_async(get)
    return async_result

def get(path="/sub/channel"):
    url = URL("http://%s/%s" % (os.getenv("HTTP_HOST", 'localhost'), path))
    http = HTTPClient.from_url(url)
    response = http.get(path)
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
    if not os.path.exists(image_dir):
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
    p = run_broadcaster(tempdir, envs={"BASE64_ENCODE": "1"})
    r = get_async()
    create_image(tempdir, "channel", "JPEG IMAGE")
    p.terminate()
    buffer_size = 45
    data = r.get(timeout=2).read(buffer_size)
    assert "JPEG IMAGE" not in data
    assert b64encode("JPEG IMAGE") in data

def test_image_is_posted_to_redis_with_utctimestamp():
    tempdir = tempfile.mkdtemp()
    r = redis.StrictRedis(host=os.getenv("REDIS_HOST", 'localhost'), port=int(os.getenv("REDIS_PORT", 7000)), db=0)
    r.delete("thumb/channel")
    now = int(time.mktime(datetime.datetime.utcnow().timetuple()))
    p = run_broadcaster(tempdir, envs={"REDIS_SAMPLE_RATE": "1"})
    create_image(tempdir, "channel", "JPEG IMAGE")
    p.terminate()
    keys = r.zrangebyscore("thumb/channel", min=str(now - 1), max=str(now + 1), start=0, num=1)
    assert len(keys) == 1
    assert r.get(keys[0]) == "JPEG IMAGE"

def test_image_can_be_get_from_nginx():
    tempdir = tempfile.mkdtemp()
    r = redis.StrictRedis(host=os.getenv("REDIS_HOST", 'localhost'), port=int(os.getenv("REDIS_PORT", 7000)), db=0)
    r.delete("thumb/channel")
    now = time.time()
    p = run_broadcaster(tempdir, envs={"REDIS_SAMPLE_RATE": "1"})
    create_image(tempdir, "channel", "JPEG IMAGE")
    create_image(tempdir, "channel", "NEW JPEG IMAGE")
    p.terminate()
    assert get("/snapshot/channel?timestamp=%d" % (now - 1)).read() == "JPEG IMAGE"
    assert get("/snapshot/channel").read() == "NEW JPEG IMAGE"

def test_image_can_be_get_from_nginx_with_utctimestamp():
    tempdir = tempfile.mkdtemp()
    r = redis.StrictRedis(host=os.getenv("REDIS_HOST", 'localhost'), port=int(os.getenv("REDIS_PORT", 7000)), db=0)
    r.delete("thumb/channel")
    utcnow = int(time.mktime(datetime.datetime.utcnow().timetuple()))
    p = run_broadcaster(tempdir, envs={"REDIS_SAMPLE_RATE": "1"})
    create_image(tempdir, "channel", "JPEG IMAGE")
    create_image(tempdir, "channel", "NEW JPEG IMAGE")
    p.terminate()
    assert get("/snapshot/channel?utc=%d" % (utcnow - 1)).read() == "JPEG IMAGE"
    assert get("/snapshot/channel").read() == "NEW JPEG IMAGE"
