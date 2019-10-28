FROM python:3

ADD . /mnt
WORKDIR /mnt

RUN pip3 install -r /mnt/requirements.txt
