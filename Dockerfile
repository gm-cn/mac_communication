FROM harbor.capitalonline.net/base/centos:7.6.1810
RUN yum install -y gcc nfs-utils ipmitool rsync xinetd wget perl dmidecode python-devel
RUN wget -q -O - http://linux.dell.com/repo/hardware/latest/bootstrap.cgi | bash && \
    yum -y install srvadmin-idrac && \
    cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    echo "Asia/shanghai" >> /etc/timezone
COPY requirements.txt /requirements.txt
RUN wget -q -O - https://bootstrap.pypa.io/get-pip.py | python && \
    pip install -r /requirements.txt --no-cache-dir
COPY . /app
WORKDIR /app
