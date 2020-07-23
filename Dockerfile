FROM harbor.capitalonline.net/base/python:2.7-slim
RUN apt-get update && apt-get install -y gcc nfs-common ipmitool iputils-ping rsync xinetd procps && \
    cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    echo "Asia/shanghai" >> /etc/timezone
COPY requirements.txt /requirements.txt
RUN  pip install setuptools -U && pip install -r /requirements.txt --no-cache-dir
COPY . /app
RUN tar -zxvf /app/DellEMC-iDRACTools-Web-LX-9.3.0-3379_A00.tar.gz -C /opt
WORKDIR /app
