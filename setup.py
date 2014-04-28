from os.path import dirname, abspath, join
from setuptools import setup

with open(abspath(join(dirname(__file__), 'README.rst'))) as fileobj:
    README = fileobj.read().strip()

install_reqs = [req for req in open(abspath(join(dirname(__file__), 'requirements.txt')))]

setup(
    name='live_thumb',
    description='MJPEG broadcaster',
    long_description=README,
    author='Globo.com',
    version='0.0.12',
    include_package_data=True,
    install_requires=install_reqs,
    py_modules=[
        'broadcaster',
    ],
    entry_points={
        'console_scripts': [
            'broadcaster = broadcaster:run'
        ]
    }
)
