import datetime
from netmiko.huawei.huawei_ssh import HuaweiSSH
import threading


class HuaweiSwitch(HuaweiSSH):

    def __init__(self, ip, username, password):
        self.ip = ip
        self.config = {
            "device_type": "huawei",
            "ip": self.ip,
            "username": username,
            "password": password
        }
        super(HuaweiSwitch, self).__init__(**self.config)
        print "session opened."

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        print "session closed."

    def check_crc(self):

        self.session_preparation()
        self.config_mode()
        date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # output = self.send_config_set(["vlan batch"])
        # super(HuaweiSSH, self).save_config(cmd='save', confirm=True, confirm_response='Y')
        output = self.send_command("display interface | include CRC")
        file_name = "/home/switch-%s" % self.ip
        with open(file_name, 'a+') as f:
            f.writelines(date)
            f.writelines(output)


def check_crc(ip):
    username = "sshadmin"
    password = "ssh-P@$$w0rd"
    with HuaweiSwitch(ip, username, password) as client:
        client.check_crc()


if __name__ == '__main__':
    switch_ips = [
        "10.128.125.253",
        "10.128.125.251"
    ]

    thread_pool = []
    for ip in switch_ips:
        t = threading.Thread(target=check_crc, name=ip, args=(ip,))
        thread_pool.append(t)

    for th in thread_pool:
        th.start()

