#!/usr/bin/env  python
import platform
import rpm
import commands
import re
import os

def __arch():
	"""Get architecture"""
	Arch = platform.architecture()[0]
	return Arch

def __release():
	"""Get system release"""		
	release_path = '/etc/klinux-release'
	if os.path.exists(release_path):
		file = open(release_path,'r')
		system = file.read().strip('\n')
		file.close()
	else:
		system = None
	return system

def __drivers():
	"""Get atca-drivers version"""
	ts = rpm.TransactionSet()
	mi = ts.dbMatch('name','atca-drivers')
	for h in mi:
    	# Do something with the header...
    		package = "%s-%s-%s" % (h['name'], h['version'], h['release'])
		return package
def __network():
	"""Get network adapter"""
	na_ = commands.getoutput('lspci | grep Eth | awk "END{print NR}"')
	if na_ == '0':
		print 'System does not discern network adapter.'
	else:
		na = int(na_)
		for i in range(na):
			id_ = commands.getoutput('/sbin/lspci |grep Eth |cut -d " " -f1').split('\n')[i]
			code_all = commands.getoutput('/sbin/lspci -n').split()
			code = [x for x in code_all if id_ in x][0]
			des = commands.getoutput('/sbin/lspci |grep Eth |cut -d : -f3').split('\n')[i]
			print "ADAPTER :",i
			print "DESCRIPTION :",des
			print "DEVICE ADDRESS :",code

		
		

if __name__ == '__main__':	
	system = __release()
	if system == None:
		system = 'unknown system'
		print('This system is not CGSL.')
	print 'SYSTEM : ',system ,__arch()
	package = __drivers()
	if package == None:
		print "No such atca-drivers package installed."
	else:
		print "DRIVER : ",package
	print ""
	__network()
