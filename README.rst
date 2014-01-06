live\_thumb
===========

Live thumbnail using `MJPEG`_ and `nginx\_push\_stream`_.

Usage
-----

Compile Nginx with `nginx\_push\_stream`_ support and run it with sample
config:

::

    $ nginx -c $PWD/nginx.conf

Make a directory to store the thumbs

::

    $ mkdir -p frames/parts

Start ffmpeg to create thumbs for a channel (``parts`` in this example):

::

    $ ffmpeg -re -i rtmp://example.com/live/stream -vf "scale=159:-1" -r 3 frames/parts/thumb%9d.jpg

Run the broadcaster:

::

    $ python broadcaster.py

If you prefer, install the script using ``pip`` and run it:

::

    $ pip install live_thumb
    $ broadcaster

Watch the movie with the example html:

::

    $ open test.html

Or go to ``http://localhost:9080/sub/parts`` directly.

.. _MJPEG: http://en.wikipedia.org/wiki/Motion_JPEG
.. _nginx\_push\_stream: https://github.com/wandenberg/nginx-push-stream-module
