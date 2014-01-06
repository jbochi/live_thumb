import os
import subprocess
import tempfile
import time

def run_broadcaster(frames_path):
    env = os.environ.copy()
    env["FRAMES_PATH"] = frames_path
    p = subprocess.Popen(["python", "broadcaster.py"], env=env)
    time.sleep(1)
    return p

def create_image(tempdir, content):
    image = tempfile.NamedTemporaryFile(dir=tempdir, delete=False)
    image.write(content)
    image.close()
    time.sleep(1)
    return image

def test_when_file_is_created_its_contents_are_posted():
    tempdir = tempfile.mkdtemp()
    p = run_broadcaster(tempdir)
    image = create_image(tempdir, "JPEG IMAGE")
    p.terminate()
    assert os.path.exists(image.name) is False
