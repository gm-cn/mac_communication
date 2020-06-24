## 管理节点安装要求：具有公网，带外，私网三种IP，公网进行yum安装，私网进行PXE安装镜像
1. 安装管理节点所有yum rpm 包和服务，执行如下脚本
   ./deploy_controller.sh enp7s0f0 11.177.178.184/24 11.177.178.50 11.177.178.60

2. 安装baremetal-api服务
   ./install.sh



baremetal-api服务为裸金属机器提供初始化镜像（用户名密码配置，网络配置），配置交换机信息，生命周期管理等功能。

访问方式： http://ip:8989

其中: bms_api/tools/rest.py提供调用脚本，供测试参考。以下提供的api均为异步接口。

### 1. 初始化镜像
```
url: /baremetal/image/init
body:
{
        "uuid": str(uuid.uuid4()),                                  # 裸金属机器uuid
        "hostname": "baremetal",                                    # 主机名称
        "username": "root",                                         # 用户名
        "password": "cds-china",                                    # 用户名对应密码
        "root_volume": "/dev/disk/by-id/**********",                # 主机系统盘在管理节点的绝对路径
        "networks": {
            "interfaces": ["eth0", "eth1", "eth2", "eth3"],         # 机器网卡名称
            "port_groups": [
                {
                    "name": "bond0",                                # bond名称
                    "mode": "802.1ad",                              # bond模式
                    "bond": [                                       # bond的两个接口名称
                        "eth0",
                        "eth1"
                    ],
                    "ipaddr": "1.1.1.2",                            # bond ip地址
                    "netmask": "255.255.255.0",                     # bond 子网掩码
                    "gateway": "1.1.1.1"                            # bond 网关地址
                },
                {
                    "name": "bond1",
                    "mode": "802.1ad",
                    "bond": [
                        "eth2",
                        "eth3"
                    ],
                    "ipaddr": "2.2.2.2",
                    "netmask": "255.255.255.0"
                }
            ],
            "dns": [
                "114.114.114.114",                                  # dns 服务器地址
                "114.114.115.115"
            ]
        }
}
```
### 2. 为 bond 接口配置 VLAN
```
url: /baremetal/switch/vlan/set
body:
{
        "username": "admin123",                                     # 交换机用户名
        "password": "CDS-china1",                                   # 交换机密码
        "host": "10.177.178.241",                                   # 交换机 ip 地址
        "ports": [
                {
                    "trunk_number": "5",                            # bond 接口的 id 号
                    "vlan_id": "2222"                               # vlan id
                },
                {
                    "trunk_number": "6",
                    "vlan_id": "2223"
                }
            ]
}
```
### 3. 取消 bond接口的 vlan 配置
```
url: /baremetal/switch/vlan/unset
body:
{
        "username": "admin123",
        "password": "CDS-china1",
        "host": "10.177.178.241",
        "ports": ["5", "6"]                                         # 支持多个trunk port
}
```
### 4. 为 bond 接口配置限速
```
url: /baremetal/switch/limit/set
body:
{
        "username": "admin123",
        "password": "CDS-china1",
        "host": "10.177.178.241",
        "networks": [
            {
                "trunk_number": "5",
                "bandwidth": 20,
                "template_name": "public",
                "ports": ["10GE1/0/11", "10GE1/0/12"]
            },
            {
                "trunk_number": "4",
                "bandwidth": 100,
                "template_name": "private",
                "ports": ["10GE1/0/17", "10GE1/0/18"]
            }
        ]
    }
```
### 5. 取消 bond接口的限速配置
```
url: /baremetal/switch/limit/unset
body:
{
        "username": "admin123",
        "password": "CDS-china1",
        "host": "10.177.178.241",
        "trunk_ports": [5, 6],
        "physical_ports": ["10GE1/0/12", "10GE1/0/11", "10GE1/0/13", "10GE1/0/14"]
}
```

### 6. 创建限速模板
```
url: /baremetal/switch/limit/create
body:
{
        "username": "admin123",
        "password": "CDS-china1",
        "host": "10.177.178.241",
        "templates": [
            {
                "name": "public",
                "bandwidth": 20
            },
            {
                "name": "private",
                "bandwidth": 100
            }
        ]
}
```

### 7. 删除限速模板
```
url: /baremetal/switch/limit/delete
body:
{
        "username": "admin123",
        "password": "CDS-china1",
        "host": "10.177.178.241",
        "templates": ["public", "private"]             # 模板名称
}
```

### 8. 修改密码
```
url: /baremetal/changepasswd
body:
{
        "baremetal_id": "uuid",
        "root_volume": "/dev/disk/by-id/*",           # 机器系统盘在管理节点上的绝对路径
        "username": "root",
        "password": "1q2w3e4r!"
}
```
### 9. 修改ip
```
url: /baremetal/changeip
body:
{
        "baremetal_id": str(uuid.uuid4()),
        "root_volume": "/dev/disk/by-id/**********",
        "networks": {
            "interfaces": ["eth0", "eth1", "eth2", "eth3"],
            "port_groups": [
                {
                    "name": "bond2",
                    "mode": "4",
                    "bond": [
                        "eth0",
                        "eth1"
                    ],
                    "ipaddr": "1.1.1.2",
                    "netmask": "255.255.255.0",
                    "gateway": "1.1.1.1"
                },
                {
                    "name": "bond3",
                    "mode": "4",
                    "bond": [
                        "eth2",
                        "eth3"
                    ],
                    "ipaddr": "2.2.2.2",
                    "netmask": "255.255.255.0"
                }
            ],
            "dns": [
                "114.114.114.114",
                "114.114.115.115"
            ]
        }
}
```
