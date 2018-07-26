#!/usr/bin/env python
# coding: utf-8

import os
import sys
import commands
import re
import json

reload(sys)
sys.setdefaultencoding('utf8')

def EnsureDirExists(dir):
	if os.path.isdir(dir):
		return True
	try:
		os.makedirs(dir)
	except Exception, e:
		sys.stderr.write(e.message + '\n')
		return False
		
def RemoveDir(dir):
	path = os.path.abspath(dir)
	if path == '/tmp':
		return True
	if not os.path.exists(path):
		return True
	status, output = commands.getstatusoutput('rm -rf %s' %path)
	if status:
		sys.stderr.write("command [rm] failed\n")
		return False
	return True
		
def WriteToFile(file, content, mode='a'):
	if type(content) != str:
				reload(sys)
				sys.setdefaultencoding( "utf-8" )
				content = str(content)
	try:
		with open(file, mode) as f:
			f.writelines(content+'\n')
		return True
	except Exception, e:
		sys.stderr.write(e.message + '\n')
		return False
		
def EnsureFileExists(file):
	if os.path.isfile(file):
		return True
	else:
		return False
	# try:
		# with open(file, 'w') as f:
			# return True
	# except Exception, e:
		# sys.stderr.write(e.message + '\n')
		# return False
		
def IsExecutable(file):
	if not EnsureFileExists(file):
		return False
	if os.access(file, os.X_OK):
		return True
	else:
		return False

def RemoveFile(file):
	path = os.path.abspath(file)
	if not os.path.exists(path):
		return True
	status, output = commands.getstatusoutput('rm -rf %s' %path)
	if status:
		sys.stderr.write("command [rm] failed\n")
		return False
	return True

def BackupFile(file):
	if not EnsureFileExists(file):
		return False
	file_bak = file + '.bak'
	try:
		os.rename(file, file_bak)
		return True
	except Exception, e:
		sys.stderr.write(e.message + '\n')
		return False
		
def DownloadFile(url, local):
	import ssl
	import urllib
	# local = os.path.join(dir, url.split('/')[-1])
	ssl._create_default_https_context = ssl._create_unverified_context
	try:
		urllib.urlretrieve(url, local)
		return True
	except Exception, e:
		sys.stderr.write(e.message + '\n')
		return False
		
def Ungzip(gzfile, dir):
	import gzip
	import tarfile
	tfile = gzfile.replace(".gz","")
	try:
		g = gzip.GzipFile(gzfile)
		open(tfile, 'w+').write(g.read())
		g.close()
	except Exception, e:
		sys.stderr.write(e.message + '\n')
		return False
	try:
		t = tarfile.open(tfile)
		list = t.getnames()
		for f in list:
			t.extract(f, dir)
		t.close()
	except Exception, e:
		sys.stderr.write(e.message + '\n')
		return False
	RemoveFile(tfile)
	return True
	
def findfiles(path, pfile):
	import fnmatch
	try:
		for root, dirs, files in os.walk(path):
			for file in fnmatch.filter(files, pfile):
				return os.path.join(root, file)
	except Exception, e:
		sys.stderr.write(e.message + '\n')
		return False
		
def get_newest_file(dir, fextension):
	_dir = os.path.abspath(dir)
	list = os.listdir(_dir)
	_list = []
	for f in list:
		if f.endswith(fextension):
			if os.path.isdir(os.path.join(_dir, f)):
				continue
			_list.append(f)
	if not _list:
		return False
	else:
		_list.sort(key=lambda file: os.path.getmtime(os.path.join(_dir,file)), reverse=True)
		return os.path.join(_dir, _list[0])
	
def ServiceCtl(service, action):
	cmd = 'systemctl %s %s' % (action, service)
	status, output = commands.getstatusoutput(cmd)
	if status:
		sys.stderr.write('Failed to run [%s]\n' % cmd)
		return False
	return True

def runCMD(cmd):
	status, output = commands.getstatusoutput(cmd)
	if status:
		sys.stderr.write('Failed to run [%s] command.\n' % cmd)
		return False
	return output
	
def MatchPattern(pattern, str=None, file=None):

		def strPattern():
			try:
				result = re.search(pattern, str)
			except Exception, e:
				sys.stderr.write(e.message + '\n')
				return False
			return  result.group()

		def filePattern():
			try:
				 with open(file,'r') as f:
					for line in f.readlines(): 
						result = re.search(pattern, line)
						if result:
							return result.group()
			except Exception, e:
				sys.stderr.write(e.message + '\n')
			return False
			
		if not pattern:
			return False
		if str and file:
			return False
		if str:
			output = strPattern()
		elif os.path.exists(file):
			output = filePattern()
		else:
			return False
		return output

def getJsonItem(file, item):
	if not EnsureFileExists(file):
		return False
	try:
		with open(file, 'r') as f:
			j = json.load(f)
		value = j[item]
		if not value:
			return False
	except Exception, e:
		sys.stderr.write(e.message + '\n')
		return False
	return value
	
def getIP(ifname):
	import socket
	import fcntl
	import struct
	try:
		s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	except Exception, e:
		sys.stderr.write(e.message + '\n')
		return False
	return socket.inet_ntoa(fcntl.ioctl(
		s.fileno(),
		0x8915,  # SIOCGIFADDR
		struct.pack('256s', ifname[:15])
	)[20:24])
	
def setEnv():
	runCMD('sed -i \'s/^[^#].*swap.*/#&/\' /etc/fstab')
	runCMD('swapoff -a')
	runCMD('modprobe br_netfilter')
	sysctl_file = '/etc/sysctl.d/k8s.conf'
	sysctl_content = '''
	net.ipv4.ip_forward = 1
	net.bridge.bridge-nf-call-iptables = 1
	net.bridge.bridge-nf-call-ip6tables = 1
	'''
	WriteToFile(sysctl_file, sysctl_content, mode='w')
	runCMD('sysctl -p')
	
def POST(url, data, headers=None):
	if not headers:
		headers = {"Content-type": "application/json;charset=utf-8"}
	import requests
	try:
		response = requests.post(url, data=json.dumps(data), headers=headers)
	except Exception, e:
		sys.stderr.write(e.message + '\n')
		return False
	result = json.loads(response.text)
	# result = json.dumps(response.text,encoding="UTF-8", ensure_ascii=False)
	return result
	