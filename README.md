live_thumb
==========

Live thumbnail using [MJPEG](http://en.wikipedia.org/wiki/Motion_JPEG) and [nginx_push_stream](https://github.com/wandenberg/nginx-push-stream-module).


Usage
-----

Compile Nginx with [nginx_push_stream](https://github.com/wandenberg/nginx-push-stream-module) support and run it with sample config:

    $ sudo /usr/local/nginx/sbin/nginx -c $PWD/nginx.conf

Make a directory to store the thumbs

    $ mkdir -p frames/parts

Start ffmpeg to create thumbs for a channel (`parts` in this example):

    $ ffmpeg -re -i rtmp://example.com/live/stream -vf "scale=159:-1" -r 3 frames/parts/thumb%9d.jpg

Run the broadcaster:

    $ python broadcaster.py

Watch the movie with the example html:

    $ open test.html

Or go to `http://localhost:9080/sub/parts` directly.
