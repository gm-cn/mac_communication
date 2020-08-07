from oslo_config import cfg


default_opts = [
    cfg.IntOpt('server_port',
               default=8989,
               help="baremetal api server port"),
    cfg.StrOpt('pidfile',
               default="/var/run/cdsstack/baremetal.pid",
               help="baremetal api pid file path."),
    cfg.IntOpt('max_retries',
               default=10,
               help="get volume path retry times"),
    cfg.IntOpt('huawei_switch_max_connection',
               default=4,
               help="huawei switch max connection.")
]

hitachi_opts = [
    cfg.StrOpt('wwn_id',
               help="hitachi storage system wwn number."
    )
]

pxe_opts = [
    cfg.StrOpt("tftpboot_dir",
               default="/tftpboot",
               help="tftpboot directory."),
    cfg.StrOpt("nfs_server_ip",
               help="internal nfs server ip."),
    cfg.StrOpt("deploy_image_dir",
               help="deploy image root directory."),
    cfg.StrOpt("user_image_dir",
               help="user images directory."),
    cfg.StrOpt("pxelinux_dir",
               help="pxelinux config directory.")
]

center_opts = [
    cfg.StrOpt("scheduler_callback",
               help="BMS scheduler callback.")
]

switch_opts = [
    cfg.StrOpt('conn_type',
               default='ssh',
               help='the method of logining switch, eg.  ssh/telnet'),
cfg.StrOpt('device_type',
               default='huawei',
               help='the method of logining switch, eg.  ssh/telnet')
]

coordination_opts = [
    cfg.StrOpt('backend_url',
               help='The backend URL to use for distributed coordination.'),
    cfg.IntOpt('max_connections',
               help='switch max connections.'),
    cfg.IntOpt('acquire_lock_timeout',
               min=0,
               default=60,
               help='Timeout in seconds after which an attempt to grab a lock '
                    'is failed. Value of 0 is forever.'),
]

serial_opts = [
    cfg.StrOpt('pid_dir',
               default='/var/run/console',
               help='serial console pid file path'),
    cfg.StrOpt('host_ip',
               help='management node ip'),
    cfg.StrOpt('subprocess_timeout',
               default=1,
               help='Timeout in seconds which a attempt to get subprocess command returncode')
]
bios_opts = [
    cfg.StrOpt('bios_set',
               default='/root/bms_api/ipmi',
               help='bios set script file path'),
    cfg.StrOpt('nginx_ip',
               help='bios set script file path'),
]

k8s_opts = [
    cfg.StrOpt('token',
               help='kubernetes admin-user token'),
    cfg.StrOpt('host',
               help='kubernetes apiserver host'),
    cfg.StrOpt('image_registry',
               help='kubernetes image registry'),
    cfg.StrOpt('image_secret',
               help='kubernetes image registry secret')
]

def list_opts():
    return [
        (None, default_opts),
        ('hitachi', hitachi_opts),
        ('pxe', pxe_opts),
        ('center', center_opts),
        ('sw_coordination', coordination_opts),
        ('shellinabox_console', serial_opts),
        ('sw_conn', switch_opts),
        ('auto_test', bios_opts),
        ('k8sInfo', k8s_opts)
    ]

CONF = cfg.CONF


def register_all_options():
    """Register all options for storage
    """
    for option in list_opts():
        CONF.register_opts(opts=option[1], group=option[0])


def prepare():
    CONF(default_config_files=['/etc/baremetal-api/baremetal-api.ini'])

