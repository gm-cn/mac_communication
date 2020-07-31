# bms_core容器化改造

### 一、Dockerfile构建
bms_core构建镜像的Dockerfile存放于项目的根目录下，内容如下：
bms_core/Dockerfile：
```dockerfile
FROM harbor.capitalonline.net/base/python:2.7-slim
RUN apt-get update && \
		apt-get install -y gcc nfs-common ipmitool iputils-ping && \
    cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    echo "Asia/shanghai" >> /etc/timezone
COPY requirements.txt /requirements.txt
RUN  pip install -r /requirements.txt --no-cache-dir
COPY . /app
WORKDIR /app
```
使用该Dockerfile构建镜像，上传到镜像仓库，如 `harbor.capitalonline.net/bms-test/bms_core`，之后会使用该镜像来部署到k8s集群。


### 二、k8s部署
#### 1. ConfigMap
bms_core的配置会存放到k8s集群的ConfigMap对象中，但是每个节点的配置不一样，所以我们会生成每个节点对应的ConfigMap配置。而且ConfigMap名称的格式要统一，到时候每个节点的bms_core会根据该格式拉取自己所属节点的配置。


当前bms_core定义的ConfigMap名称格式：`podXX-site-bmscore，如 pod45-wuxi2-bmscore`，请一定按照该格式创建每个节点对应的ConfigMap，否则bms_core服务创建拉取不到配置会出问题！！！

ConfigMap的yaml文件存放在bms_core项目下的k8s目录，如 pod45-wuxi2-bmscore的配置如下：
bms_core/k8s/pod45-wuxi2-bmscore.yaml：
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: pod45-wuxi2-bmscore
data:
  vip401: 10.128.192.21
  vip1800: 192.168.50.20
  config: |+
    [DEFAULT]
    server_port = 7081
    pidfile = /var/run/cdsstack/baremetal.pid
    max_retries = 10
    huawei_switch_max_connection = 20

    [hitachi]
    wwn_id = wwn-0x60060e801257cc00504057cc00000

    [pxe]
    nfs_server_ip = 192.168.50.20
    tftpboot_dir = /tftpboot
    pxelinux_dir = /tftpboot/pxelinux
    deploy_image_dir = /tftpboot/deploy_image_template
    user_image_dir = /tftpboot/user_images

    [center]
    scheduler_callback = http://192.168.50.20:17070/bms/v1/task/pxe/notify

    [sw_coordination]
    backend_url = kazoo://192.168.50.20:2181
    max_connections = 4
    acquire_lock_timeout = 300

    [sw_conn]
    conn_type = telnet
    device_type = huawei

    [shellinabox_console]
    pid_dir = /var/run/console
    host_ip = 10.177.178.184
    subprocess_timeout = 1

    [auto_test]
    bios_set = /root/bms_api
    nginx_ip = 10.128.121.40

```
vip401：表示pod45两台管理节点vlan401网络的虚ip；
vip1800：表示pod45两台管理节点vlan1800网络的虚ip；
config：表示bms_core服务的配置文件，其中
server_port：服务启动的端口；
nfs_server_ip：nfs服务的ip地址，两台管理节点都会启动nfs服务，注意取vlan1800的vip；
scheduler_callback：bms_control服务的回调url，除了ip其它都一样，注意ip取vlan1800的vip；
backend_url：zookeeper服务的地址，注意ip取vlan1800的vip；

#### 2. DaemonSet
bms_core通过DaemonSet方式部署到所有节点的管理节点，yaml文件存放于项目的k8s目录下。
**注意：该DaemonSet配置nodeSelector为node: ok，只会调度到有该标签的node上。**
bms_core/k8s/bms_core.yaml：

```yaml
# bms_core DaemonSet
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: bms-core
  namespace: default
  labels:
    app: bms-core
    name: bms-core
    version: v1
  annotations:
    service: bms-core
spec:
  minReadySeconds: 20
  updateStrategy:
    type: RollingUpdate
  selector:
    matchLabels:
      name: bms-core
  template:
    metadata:
      name: bms-core
      namespace: default
      labels:
        name: bms-core
    spec:
      containers:
      - name: bms-core
        image: harbor.capitalonline.net/bms-test/bms_core:lze-0714-2
        command: ["sh","-c","bash /app/start.sh"]
        imagePullPolicy: Always
        ports:
        - name: http
          containerPort: 7081
          hostPort: 7081
        securityContext:
          privileged: true
        volumeMounts:
        - name: baremetal-api
          mountPath: /etc/baremetal-api
        - name: env-config
          mountPath: /config
        - name: logs
          mountPath: /var/log/cdsstack
      initContainers:
      - name: config
        image: harbor.capitalonline.net/base/curl-jq
        command:
          - bash
          - -c
          - "
podName=`echo $NODE_NAME | cut -d '-' -f2`;
siteName=`echo $NODE_NAME | cut -d '-' -f3`;

configmap=`curl -k -H \"Authorization: Bearer $(cat /var/run/secrets/kubernetes.io/serviceaccount/token)\" -k  -H 'Accept: application/json' -H 'Content-Type: application/json' https://10.96.0.1/api/v1/namespaces/default/configmaps/${podName}-${siteName}-bmscore`;

configStr=`echo $configmap | jq '.data.config'`;
configStrLen=${#configStr};
config=${configStr:1:(( $configStrLen - 2 ))};

echo -e $config;

echo -e $config >> /etc/baremetal-api/baremetal-api.ini;

vip1800Str=`echo $configmap | jq '.data.vip1800'`;
vip1800StrLen=${#vip1800Str};
vip1800=${vip1800Str:1:(( $vip1800StrLen - 2 ))};
echo $vip1800;
echo \"vip1800=$vip1800\" >> /config/env;
          "
        imagePullPolicy: Always
        securityContext:
          privileged: true
        volumeMounts:
        - mountPath: /config
          name: env-config
        - mountPath: /etc/baremetal-api
          name: baremetal-api
        env:
        - name: NODE_NAME
          valueFrom:
            fieldRef:
              fieldPath: spec.nodeName
      imagePullSecrets:
      - name: login-registry
      volumes:
      - name: env-config
        emptyDir: {}
      - name: baremetal-api
        emptyDir: {}
      - name: logs
        hostPath:
          path: /logs/bmscore
      hostNetwork: true
      restartPolicy: Always
      nodeSelector:
        node: ok
      serviceAccountName: bms-admin
      serviceAccount: bms-admin
```
上述DaemonSet会启动两个容器，一个是config initContainer，一个是bms-core Container。

----

**部署bms_ core依赖服务zookeeper服务**

bms_core/k8s/zookeeper.yaml：

~~~yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: zookeeper
  namespace: default
  labels:
    app: zookeeper
    name: zookeeper
    version: v1
  annotations:
    service: zookeeper
spec:
  minReadySeconds: 20
  updateStrategy:
    type: RollingUpdate
  selector:
    matchLabels:
      name: zookeeper
  template:
    metadata:
      name: zookeeper
      namespace: default
      labels:
        name: zookeeper
    spec:
      containers:
      - name: zookeeper
        image: zookeeper
        imagePullPolicy: Always
        ports:
        - name: http
          containerPort: 2181
        securityContext:
          privileged: true
        volumeMounts:
        - name: workdir
          mountPath: "/work-dir"
      hostNetwork: true
      restartPolicy: Always
      volumes:
      - name: workdir
        emptyDir: {}
~~~


#### 3. initContainer
在上述的DaemonSet的config initContainer中，会运行一个bash脚本，主要用来读取配置传给bms-core容器。
具体步骤如下：

1. 读取环境变量中的node名称，解析出当前节点的podXX及site；
1. 根据podXX及site拼接对应节点的ConfigMap名称，调用kubernetes接口获取ConfigMap配置；
1. 使用jq工具获取ConfigMap的config配置，该配置是bms-core服务的配置文件；
1. 将配置写入/etc/baremetal-api/baremetal-api.ini文件，其中/etc/baremetal-api目录是两个容器共享的;
1. 使用jq工具获取ConfigMap的vip1800配置，通过该ip挂载NFS /tftpboot目录到容器内；
1. 将vip1800写入到/config/env文件，其中/config目录是两个容器共享的。



脚本如下：
```shell
podName=`echo $NODE_NAME | cut -d '-' -f2`;
siteName=`echo $NODE_NAME | cut -d '-' -f3`;

# 获取kubernetes该节点的ConfigMap配置
configmap=`curl -k -H \"Authorization: Bearer $(cat /var/run/secrets/kubernetes.io/serviceaccount/token)\" -k  -H 'Accept: application/json' -H 'Content-Type: application/json' https://10.96.0.1/api/v1/namespaces/default/configmaps/${podName}-${siteName}-bmscore`;

# json解析获取config配置
configStr=`echo $configmap | jq '.data.config'`;
configStrLen=${#configStr};
config=${configStr:1:(( $configStrLen - 2 ))};

echo -e $config;

# 将config写入共享文件，提供给bms-core容器使用
echo -e $config >> /etc/baremetal-api/baremetal-api.ini;

# json解析获取vip1800配置
vip1800Str=`echo $configmap | jq '.data.vip1800'`;
vip1800StrLen=${#vip1800Str};
vip1800=${vip1800Str:1:(( $vip1800StrLen - 2 ))};
echo $vip1800;
# 将vip1800写入共享文件
echo \"vip1800=$vip1800\" >> /config/env;
```


#### 4. start.sh
bms-core容器会启动项目中start.sh脚本，该脚本会挂载NFS目录，并启动bms-core服务。
bms_core/start.sh：
```shell
#!/bin/bash

source /config/env
echo "vip of vlan 1800: ${vip1800}"
if [[ ${vip1800} == '' ]]; then
    echo "not found vip of vlan 1800"
    exit 1
fi

# 挂载NFS /tftpboot目录，该目录主要用来处理自定义模板及pxe启动镜像相关
mkdir /tftpboot && mount -t nfs -o nolock,vers=3 ${vip1800}:/tftpboot /tftpboot

if [[ $? != 0 ]]; then
  echo "mount ${vip1800}:/tftpboot nfs error"
  exit 1
fi

# 启动bms-core服务
PYTHONPATH=${PYTHONPATH}:/app && python -c "from baremetal import bdaemon; bdaemon.main()"
```
