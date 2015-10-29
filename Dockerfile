FROM ubuntu:15.10

ENV DEBIAN_FRONTEND noninteractive

# create /app folder and set it as workdir
RUN mkdir /app
WORKDIR /app

# update and upgrade packages
RUN apt-get update && apt-get upgrade -y && apt-get clean && apt-get install -y \
  build-essential \
  git \
  python \
  python-dev \
  wget

RUN wget https://bootstrap.pypa.io/get-pip.py && python get-pip.py && rm get-pip.py

ADD requirements-dev.txt requirements.txt /app/

# install app requirements
RUN pip install -r requirements-dev.txt --index-url=https://artifactory.globoi.com/artifactory/api/pypi/pypi-all/simple/

# add soucecode to /app
ADD . /app
