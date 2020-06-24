# -*- coding:utf-8 -*-
from concurrent.futures import ThreadPoolExecutor
import time
import os
from database import Database_test
from get_excel_info import Excel, gen_log, checkout_excel
from service import  boot_deploy_image, pxe_set_vlan, other_set_vlan

from configparser import ConfigParser

cp = ConfigParser()
cp.read("bms.ini")


def get_host_ips():
    with Database_test() as data_t:
        res = data_t.select()
        for i in res:
            if i[-1] == "failed":
                data_t.delete_create_bms(i[0])
        return res


def get_ipmi_ips(ips):

    with Database_test() as data_t:
        data_t.delete_dhcpinfo()
        if len(ips) != data_t.select_host_conf_count()[0]:
            pxe_set_vlan()
            for ip in ips:
                try:
                    data_t.insert_host_conf(ip)
                except:
                    continue

    with Database_test() as data_t:
        tem1 = data_t.select_ipmi_ips()
        tem2 = data_t.select_host_ip()
        return [i[0] for i in tem1 if i not in tem2]

def boot_deploy_image_all(os_version):
    host_ips = get_ipmi_ips(os_version)

    print("start", time.ctime())
    with ThreadPoolExecutor(max_workers=50) as executor:
        for i in host_ips:
            time.sleep(1)
            executor.submit(boot_deploy_image, i)

    print("end", time.ctime())
    time.sleep(5)


if __name__ == '__main__':
    # set ipmi username password
    now_path = os.getcwd()
    pro_path = now_path.split('tools')[0]

    filepath1 = now_path + '/host_ip'

    if os.path.exists(filepath1):
        os.remove(filepath1)

    excel = Excel()
    ips = excel.get_ips()

    boot_deploy_image_all(ips)
    num = gen_log()
    other_set_vlan(num)
    checkout_excel()

