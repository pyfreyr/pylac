FROM ubuntu:16.04

ENV LANG=C.UTF-8 LC_ALL=C.UTF-8
ENV TZ=Asia/Shanghai
ENV LD_LIBRARY_PATH /usr/local/lac/lib:$LD_LIBRARY_PATH

RUN apt-get update && \
    apt-get install -y python python-pip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /web

ADD . .

RUN mkdir -p /usr/local/lac && tar -zxvf data/lib.tar.gz -C /usr/local/lac && \
    tar -zxvf data/conf.tar.gz && \
    rm -rf data

RUN pip install -r requirements.txt && \
    rm -rf requirements.txt


ENTRYPOINT ["/bin/bash", "-c"]

EXPOSE 8888

CMD ["python lac_server.py"]