#!/bin/bash

usage () {
    echo "USAGE: $0 <password> <node1_ip> [node2_ip] [node3_ip]..."
    echo ""
    echo "!!!!! Note: Ensure that all specified ips are connected."
    echo ""
    echo "Examples:"
    echo ""
    echo "  password,  all zookeeper server login password."
    echo ""
    echo "  node1_ip,  zookeeper node1 ip. current node ip."
    echo ""
    echo "  node2_ip, zookeeper node2 ip. It's optional."
    echo ""
    echo "  node3_ip,  zookeeper node3 ip. It's optional."
    echo ""
    echo "  ..., others zookeeper node ip. It's optional."
    echo ""
    exit
}

if [[ $# -lt 2 ]];then
    usage
fi

sshpass_ssh_prefix="sshpass -p $1 ssh -o StrictHostKeyChecking=no"
sshpass_scp_prefix="sshpass -p $1 scp -o StrictHostKeyChecking=no"
zoo_cfg_file=/opt/apache-zookeeper-3.5.7-bin/conf/zoo.cfg
log_cfg_file=/opt/apache-zookeeper-3.5.7-bin/conf/log4j.properties
bin_cfg_dir=/opt/apache-zookeeper-3.5.7-bin/bin


function install_zookeeper_on_master()
{
    if [[ ! -d /opt/apache-zookeeper-3.5.7-bin ]];then
        cd /opt
        wget https://repos.capitalonline.net/wangyuwei/diskimage-builder/raw/master/apache-zookeeper-3.5.7-bin.tar.gz
        tar -zxf apache-zookeeper-3.5.7-bin.tar.gz
    fi

    cat > /root/install_zookeeper.sh << EOF
#!/bin/bash

rpm -qa | grep java-1.8.0-openjdk-1.8.0
if [[ \$? != 0 ]]; then
    echo "starting install java-1.8.0..."
    yum install java-1.8.0-openjdk -y 1>/dev/null 2>&1
else
    echo "java-1.8.0 package is installed."
fi

java_version=\`java -version 2>&1 | grep "openjdk version"\`
if [[ -z "\$java_version" ]]; then
    echo "install java failed."
    exit 1
else
    echo "install java-1.8.0-openjdk successfully."
fi

if [ -f $zoo_cfg_file ];then
    rm -rf $zoo_cfg_file
fi

cp /opt/apache-zookeeper-3.5.7-bin/conf/zoo_sample.cfg $zoo_cfg_file

if [[ ! -d "/var/lib/zookeeper" ]]; then
    mkdir /var/lib/zookeeper
fi

if [[ ! -d "/var/log/zookeeper" ]]; then
    mkdir /var/log/zookeeper
fi

sed -i 's/dataDir=\/tmp\/zookeeper/dataDir=\/var\/lib\/zookeeper/g' $zoo_cfg_file
sed -i 's/#maxClientCnxns=60/maxClientCnxns=500/g' $zoo_cfg_file

sed -i 's/zookeeper.root.logger=INFO, CONSOLE/zookeeper.root.logger=INFO, ROLLINGFILE/g' $log_cfg_file
sed -i 's/zookeeper.log.dir=./zookeeper.log.dir=\/var\/log\/zookeeper/g' $log_cfg_file
sed -i 's/zookeeper.log.maxfilesize=256MB/zookeeper.log.maxfilesize=100MB/g' $log_cfg_file
sed -i 's/zookeeper.log.maxbackupindex=20/zookeeper.log.maxbackupindex=6/g' $log_cfg_file

sed -i 's/ZOO_LOG4J_PROP="INFO,CONSOLE"/ZOO_LOG4J_PROP="INFO,ROLLINGFILE"/g' $bin_cfg_dir/zkEnv.sh
sed -i 's/ZOO_LOG_DIR="\$ZOOKEEPER_PREFIX\/logs"/ZOO_LOG_DIR="\/var\/log\/zookeeper"/g' $bin_cfg_dir/zkEnv.sh


echo "export ZOOKEEPER_HOME=/opt/apache-zookeeper-3.5.7-bin" >> /root/.bash_profile
echo export PATH="\\\$PATH":"\\\$ZOOKEEPER_HOME"/bin >> /root/.bash_profile
source /root/.bash_profile
rm -rf /opt/apache-zookeeper-3.5.7-bin.tar.gz

EOF
    chmod +x /root/install_zookeeper.sh
    sh /root/install_zookeeper.sh
}



function install_zookeeper_all_node()
{

    install_zookeeper_on_master
    let num=1
    for ip in $@
    do
        echo "server.$num=$ip:2888:3888" >> $zoo_cfg_file
        let num++
    done

    let num=1

    for ip in $@
    do
        if [[ $num == 1 ]];then
            echo $num > /var/lib/zookeeper/myid
        else
            $sshpass_scp_prefix /opt/apache-zookeeper-3.5.7-bin root@$ip:/opt
            $sshpass_scp_prefix /root/install_zookeeper.sh root@$ip:/root
            $sshpass_ssh_prefix $ip "sh /root/install_zookeeper.sh > /root/install_zookeeper.log && \
            echo $num > /var/lib/zookeeper/myid && echo success || echo failed"
            $sshpass_scp_prefix $zoo_cfg_file root@$ip:$zoo_cfg_file
        fi
        let num++
    done
}

function start_zookeeper_all_node()
{
    for ip in $@
    do
        $sshpass_ssh_prefix $ip "$bin_cfg_dir/zkServer.sh start"
        $sshpass_ssh_prefix $ip "$bin_cfg_dir/zkServer.sh status"
    done
}

install_zookeeper_all_node ${@:2:$#-1}

start_zookeeper_all_node ${@:2:$#-1}



