live\_thumb
===========

Live thumbnail using `MJPEG`_ and `nginx\_push\_stream`_.

Usage
-----

Compile Nginx with `nginx\_push\_stream`_ support. The example config also uses lua-nginx-module and lua-resty-redis to store and serve old snapshots from Redis, but this module is optional. The Nginx configuration should be something like this:

::

    $ LUAJIT_LIB=/usr/local/lib/ LUAJIT_INC=/usr/local/include/luajit-2.0 ./configure --add-module=../nginx-push-stream-module --add-module=../lua-nginx-module --with-pcre --with-ipv6 --with-ld-opt=-L/usr/local/lib

Now run Nginx with sample config:

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


To also store the snapshots on redis, you should run the broadcaster with an extra env variable:

::

    $ REDIS_HOST="localhost" REDIS_PORT=7000 python broadcaster.py


The snapshots will be served from ``http://localhost:9080/snapshot/parts``. You can also specify a timestamp: ``http://localhost:9080/snapshot/parts?timestamp=1396381230``


.. _MJPEG: http://en.wikipedia.org/wiki/Motion_JPEG
.. _nginx\_push\_stream: https://github.com/wandenberg/nginx-push-stream-module
