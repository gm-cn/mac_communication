# -*- coding:utf-8 -*-
import sqlite3
from configparser import ConfigParser

cp = ConfigParser()
cp.read("bms.ini")

class Database_test():
    def __init__(self):
        self.nic_count = int(cp.get('network', 'count'))
        self.conn = sqlite3.connect("test.db", timeout=10)
        self.cursor = self.conn.cursor()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.commit()
        self.cursor.close()
        self.conn.close()

    # task execute
    def create(self):
        sql = "create table create_bms " \
              "(create_id varchar(50) primary key, ipmi_ip varchar(30), dhcp_ip varchar(30), " \
              "dhcp_mac varchar(20), poweroff_s varchar(20), poweron_s varchar(20), clone_s varchar(20)," \
              "init_s varchar(20), powerreset_s varchar(20))"
        self.cursor.execute(sql)

    def insert(self, uuid, ipmi_ip):
        sql = "insert into create_bms " \
              "(create_id, ipmi_ip, dhcp_ip, dhcp_mac, poweroff_s, poweron_s, clone_s, init_s, powerreset_s) " \
              "values ( '{}', '{}', 0, 0, 0, 0, 0, 0, 0)".format(uuid, ipmi_ip)
        self.cursor.execute(sql)

    # server hardinfo table
    def create_host(self):
        macs = ''
        for i in range(self.nic_count):
            mac = "mac%s varchar(20), " % (i + 1)
            macs += mac
        sql = "create table host (ipmi_ip varchar(30) primary key, " \
              + macs + "result varchar(10))"

        self.cursor.execute(sql)

    def insert_host(self, attr):
        macs = ''
        for i in range(self.nic_count + 1):
            mac = "?, "
            macs += mac
        sql = "insert into host values (" + macs + "?)"
        attr.append("0")
        self.cursor.execute(sql, tuple(attr))

    def select_host(self, attr):
        sql = "select count(*) from host where ipmi_ip='%s'" % attr
        self.cursor.execute(sql)
        value = self.cursor.fetchone()
        return value

    # dhcpIP table
    def create_dhcpinfo(self):
        sql = "create table dhcpinfo " \
              "(ipmi_ip varchar(20) primary key, dhcp_ip varchar(20), mac varchar(30))"
        self.cursor.execute(sql)

    def insert_dhcpinfo(self, ip, dhcp_ip, mac):
        sql = "insert into dhcpinfo " \
              "(ipmi_ip, dhcp_ip, mac) " \
              "values ( '{}', '{}', '{}')".format(ip, dhcp_ip, mac)
        self.cursor.execute(sql)

    # server table
    def create_host_conf(self):
        ips = ''
        for i in range(self.nic_count):
            ip = "ip%s varchar(20), " % (i + 1)
            ips += ip
        sql = "create table host_conf " \
              "(ipmi_ip varchar(20) primary key, " + ips + "hostname varchar(30))"
        self.cursor.execute(sql)

    def insert_host_conf(self, attr):
        ips = ''
        for i in range(self.nic_count + 1):
            ip = "?, "
            ips += ip
        sql = "insert into host_conf values (" + ips + "?)"
        attr.append("bms")
        self.cursor.execute(sql, tuple(attr))

    # update create_bms table
    def update_create_bms(self, attr, value, pk):
        sql = "update create_bms " \
              "set %s='%s' " \
              "where create_id='%s'" % \
              (attr, value, pk)
        self.cursor.execute(sql)

    def update_host(self, value, ip):
        sql = "update host " \
              "set result='%s' " \
              "where ipmi_ip='%s'" % \
              (value, ip)
        self.cursor.execute(sql)

    def select(self):
        sql = "select * from host where result!='success'"
        self.cursor.execute(sql)
        value = self.cursor.fetchall()
        return value

    def select_host_ip(self):
        sql = "select ipmi_ip from host"
        self.cursor.execute(sql)
        value = self.cursor.fetchall()
        return value

    def select_attr(self, attr, id):
        sql = "select {} from create_bms where create_id='{}'".format(attr, id)
        self.cursor.execute(sql)
        value = self.cursor.fetchone()
        return value[0]

    def select_dhcp_ipmi(self, ip):
        sql = "select ipmi_ip, dhcp_ip, mac from dhcpinfo where ipmi_ip='{}'".format(ip)
        self.cursor.execute(sql)
        value = self.cursor.fetchone()
        return value

    def select_createbms_info(self,attr, ip):
        sql = "select {} from create_bms where ipmi_ip='{}'".format(attr, ip)
        self.cursor.execute(sql)
        value = self.cursor.fetchone()
        return value

    def select_host_conf(self, ip):
        sql = "select * from host_conf " \
              "where ipmi_ip='{}'".format(ip)
        self.cursor.execute(sql)
        value = self.cursor.fetchone()
        return value

    def select_host_conf_count(self):
        sql = "select count(*) from host_conf "
        self.cursor.execute(sql)
        value = self.cursor.fetchone()
        return value

    def select_ipmi_ips(self):
        sql = "select ipmi_ip from host_conf"
        self.cursor.execute(sql)
        value = self.cursor.fetchall()
        return value

    def delete_create_bms(self, ip):
        sql = "delete from create_bms " \
              "where ipmi_ip='{}'".format(ip)
        self.cursor.execute(sql)

    def delete_dhcpinfo(self):
        sql = "delete from dhcpinfo"
        self.cursor.execute(sql)

    def gen_host_ip(self):
        sql = "select * from host_conf"
        self.cursor.execute(sql)
        value = self.cursor.fetchall()
        return value

    def gen_install_success(self):
        sql = "select * from host"
        self.cursor.execute(sql)
        value = self.cursor.fetchall()
        return value
