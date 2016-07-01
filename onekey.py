#!/usr/bin/env python
# coding=utf-8
# code by 92ez.com

import subprocess
import signal
import time
import sys
import os

DN = open(os.devnull, 'w')

def iwconfig():
	monitors = []
	proc = subprocess.Popen(['iwconfig'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	for line in proc.communicate()[0].split('\n'):
		if len(line) == 0: continue
		if line[0] != ' ':
			iface = line[:line.find(' ')]
			if 'Mode:Monitor' in line:
				monitors.append(iface)
	return monitors

def cleanup(signal, frame):
	os.system('echo 0 > /proc/sys/net/ipv4/ip_forward')
	os.system('iptables -F')
	os.system('iptables -X')
	os.system('iptables -t nat -F')
	os.system('iptables -t nat -X')
	os.system('pkill airbase-ng')
	os.system('pkill dhcpd')
	rm_mon()
	sys.exit('\n[+] Cleaned up')

def iptables(inet_iface):
	os.system('iptables -X')
	os.system('iptables -F')
	os.system('iptables -t nat -F')
	os.system('iptables -t nat -X')
	os.system('iptables -t nat -A POSTROUTING -o %s -j MASQUERADE' % inet_iface)
	os.system('echo 1 > /proc/sys/net/ipv4/ip_forward')

def rm_mon():
	monitors = iwconfig()
	for m in monitors:
		if 'mon' in m:
			subprocess.Popen(['airmon-ng', 'stop', m], stdout=DN, stderr=DN)
		else:
			subprocess.Popen(['ifconfig', m, 'down'], stdout=DN, stderr=DN)
			subprocess.Popen(['iw', 'dev', m, 'mode', 'managed'], stdout=DN, stderr=DN)
			subprocess.Popen(['ifconfig', m, 'up'], stdout=DN, stderr=DN)

def createAP(ap_iface,essid):
	print '[*] Create monitor...'
	proc = subprocess.Popen(['airmon-ng', 'start', ap_iface], stdout=subprocess.PIPE, stderr=DN)
	proc_lines = proc.communicate()[0].split('\n')

	for line in proc_lines:
		if "monitor mode vif enabled" in line:
			line = line.split()
			mon_iface = line[8].split(']')[1].split(')')[0]

	print '[*] Starting the fake access point...'
	subprocess.Popen(['airbase-ng', '-c', '7', '-e', essid, mon_iface], stdout=DN, stderr=DN)
	print '[*] Waiting for 6 seconds...'
	time.sleep(6)
	subprocess.Popen(['ifconfig', 'at0', 'up', '10.0.0.1', 'netmask', '255.255.255.0'], stdout=DN, stderr=DN)
	subprocess.Popen(['ifconfig', 'at0', 'mtu', '1400'], stdout=DN, stderr=DN)

def dhcp_conf(ipprefix):
	config = ('default-lease-time 300;\n'
			  'max-lease-time 360;\n'
			  'ddns-update-style none;\n'
			  'authoritative;\n'
			  'log-facility local7;\n'
			  'subnet %s netmask 255.255.255.0 {\n'
			  'range %s;\n'
			  'option routers %s;\n'
			  'option domain-name-servers %s;\n'
			  '}')
	if ipprefix == '19' or ipprefix == '17':
		with open('/tmp/dhcpd.conf', 'w') as dhcpconf:
			# subnet, range, router, dns
			dhcpconf.write(config % ('10.0.0.0', '10.0.0.2 10.0.0.100', '10.0.0.1', '114.114.114.114'))
	elif ipprefix == '10':
		with open('/tmp/dhcpd.conf', 'w') as dhcpconf:
			dhcpconf.write(config % ('172.16.0.0', '172.16.0.2 172.16.0.100', '172.16.0.1', '114.114.114.114'))
	return '/tmp/dhcpd.conf'

def dhcp(dhcpconf, ipprefix):
	os.system('echo > /var/lib/dhcp/dhcpd.leases')
	dhcp = subprocess.Popen(['dhcpd', '-cf', dhcpconf], stdout=subprocess.PIPE, stderr=DN)
	if ipprefix == '19' or ipprefix == '17':
		os.system('route add -net 10.0.0.0 netmask 255.255.255.0 gw 10.0.0.1')
	else:
		os.system('route add -net 172.16.0.0 netmask 255.255.255.0 gw 172.16.0.1')

if __name__ == '__main__':

	# isc-dhcp-server 
	# http://www.isc.org/downloads/dhcp/
	# tar xfvz dhcp-****.tar.gz
	# cd dhcp...
	# ./configure --prefix=/usr/local
	# make && make install

	if os.geteuid() != 0:
		sys.exit('[Error!!!] You must run this script as root')

	ap_interface = 'wlan0'
	inet_iface = 'eth0'
	essid = 'freewifi'
	ipprefix = '17'

	rm_mon()
	iptables(inet_iface)
	createAP(ap_interface,essid)
	dhcpconf = dhcp_conf(ipprefix)
	dhcp(dhcpconf, ipprefix)

	while 1:
		signal.signal(signal.SIGINT, cleanup)
		os.system('clear')
		proc = subprocess.Popen(['cat', '/var/lib/dhcp/dhcpd.leases'], stdout=subprocess.PIPE, stderr=DN)
		for line in proc.communicate()[0].split('\n'):
			print line 

		time.sleep(1)