#!/usr/bin/env python
# coding:utf-8 

import sys, os
import platform, argparse
from  helpformatter import SortingHelpFormatter

__VERSION__ = '1.0.0'


machies = ['armv7l', 'arm64', 'amd64']
_num = None

def InitArgs():

	parser = argparse.ArgumentParser(prog='kagent', description='Jion the kubernetes cluster as Node', formatter_class=SortingHelpFormatter)
	parser.add_argument('-i', '--interface', dest='interface', help='Set Node address to specified interface address', required='True')
	parser.add_argument('-s', '--server', dest='server', help='Connect to the management server on the given host', required='True')
	parser.add_argument('-v', '--version', help='output version information and exit', action='version', version='%(prog)s '+ __VERSION__)

	args = parser.parse_args()
	return  args

def CheckArgs(interface, server):

	nic_path = '/sys/class/net'
	retVal = 0
	interface_path = os.path.join(nic_path,interface)
	if not os.path.exists(interface_path):
		sys.stderr.write('ERROR: INTERFACE \'%s\' does not exist.\n' % interface)
		retVal = 1
	cmd = 'ping -c1 %s &>/dev/null' % server
	result = os.system(cmd)
	if result != 0:
		sys.stderr.write('ERROR: SERVER \'%s\' is unreachable.\n' % server)
		retVal = 1
	return retVal

def CheckEnv():

	if os.geteuid() != 0:
		sys.stderr.write('ERROR: Need to be root.\n')
		sys.exit(1)

	global arch_num
	_machine = platform.machine()
	if _machine == 'armv7l':
		_num = 0
	elif _machine == 'aarch64':
		_num = 1
	elif _machine == 'x86_64': 
		_num = 2
	else:
		sys.stderr.write('ERROR: Unsupport this %s machine architecture.\n' % _machine)
		sys.exit(1)

	cmd = 'systemctl status docker &>/dev/null'
	result = os.system(cmd)
	if result != 0:
		sys.stderr.write('ERROR: docker service is not running.\n')
		sys.exit(1)
	
	# disable files for paging and swapping in Raspbian
	swapfile_path = '/etc/dphys-swapfile'
	if os.path.isfile(swapfile_path):
		os.system('sed -i  \'s/^\(CONF_SWAPSIZE=\).*/\\10/\' %s' % swapfile_path)
		os.system('swapoff -a')
	
if __name__ == '__main__':
	args = InitArgs()
	CheckEnv()
	pre_code = CheckArgs(args.interface, args.server)
	if pre_code != 0:
		sys.exit(pre_code)
	if not arch_num:
		sys.exit(1)

	import core
	c = core.core(machines[_num], args.interface, args.server)
	c.run()
