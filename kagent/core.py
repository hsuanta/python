#!/usr/bin/env python
# coding: utf-8

import sys
import os
import uuid
import time
import sysutils
import output


config_dir = '/etc/fog-agent'
node = 'localhost'
pkgs = ['kubernetes-node-linux-arm.tar.gz',
			'kubernetes-node-linux-arm64.tar.gz',
			'kubernetes-node-linux-amd64.tar.gz']
pauses = ['pause-arm.tar', 'pause-arm64.tar', 'pause-amd64.tar']

# k8s_url = 'https://dl.k8s.io/v1.10.5/'
# pause_url = None
save_dir = '/tmp'
repository = 'k8s.gcr.io'
log_path = '/tmp/k8s_install.log'


kubelet_path = '/usr/bin/kubelet'
kube_proxy_path = '/usr/bin/kube-proxy'
kubectl_path = '/usr/bin/kubectl'

kubelet_config = '/etc/kubernetes/kubelet.conf'
kube_proxy_config = '/etc/kubernetes/kube-proxy.conf'

polling_time = 10

class core(object):
	
	def __init__(self, arch, ifname, server, data=None):
	
		self.arch = arch
		if self.arch == 'armv7l':
			self.pkg = pkgs[0]
			self.pause = pauses[0]
		elif self.arch == 'aarch64':
			self.pkg = pkgs[1]
			self.pause = pauses[1]
		elif self.arch == 'x86_64': 
			self.pkg = pkgs[2]
			self.pause = pauses[2]
		self.k8s_installed = False
		self.ifname = ifname
		self.server = server
		self.server_port = 8050
		self.local_ip = sysutils.getIP(self.ifname)
		self.node = node
		mac = uuid.UUID(int = uuid.getnode()).hex[-12:]	
		self.mac = ":".join([mac[e:e+2] for e in range(0,11,2)])
	
	def createDir(self):

		sysutils.EnsureDirExists('/etc/docker')
		sysutils.EnsureDirExists('/var/lib/kubelet')
		sysutils.EnsureDirExists('/var/lib/kube-proxy')
		sysutils.EnsureDirExists('/etc/kubernetes/pki')
		sysutils.EnsureDirExists('/etc/cni/net.d')
		
	def downloadPKG(self):
		
		pkg_url = self.metadata[u'result'][u'clientsUrl']
		pause_url = self.metadata[u'result'][u'containersUrl']
		
		self.pkg_path = os.path.join(save_dir, self.pkg)
		self.pause_path = os.path.join(save_dir, self.pause)
		
		pkg_dl=sysutils.DownloadFile(pkg_url, self.pkg_path)
		pause_dl=sysutils.DownloadFile(pause_url, self.pause_path)
		
		if pkg_dl and pause_dl:
			self.log.info("Download packages successfully.")
		else:
			self.log.error("Failed to download packages.")
			sys.exit(1)
		
		
	def decompressPKG(self):
		
		if os.path.exists(self.pkg_path):
			if not sysutils.Ungzip(self.pkg_path, save_dir):
				self.log.error("Failed to decompress %s package." %self.pkg)
				sys.exit(1)
		
	def cleanPKG(self):
	
		if os.path.exists(self.pkg_path):
			sysutils.RemoveFile(self.pkg_path)
		extract_dir=os.path.join(save_dir,'kubernetes')
		if os.path.exists(extract_dir):
			sysutils.RemoveDir(extract_dir)
			
	def cpFile(self):
	
		kubelet = sysutils.findfiles(save_dir, 'kubelet')
		kube_proxy = sysutils.findfiles(save_dir, 'kube-proxy')
		kubectl = sysutils.findfiles(save_dir, 'kubectl')
		
		if kubelet and kube_proxy and kubectl:
			sysutils.runCMD('cp %s %s' % (kubelet, kubelet_path))
			sysutils.runCMD('cp %s %s' % (kube_proxy, kube_proxy_path))
			sysutils.runCMD('cp %s %s' % (kubectl, kubectl_path))
		else:
			self.log.error("Failed to find file in cpFile().")
			sys.exit(1)
	
	def uploadImage(self):
		
		if not sysutils.ServiceCtl('docker', 'status'):
			sysutils.ServiceCtl('docker', 'enable')
			sysutils.ServiceCtl('docker', 'restart')
		op = sysutils.runCMD('docker images --format={{.Repository}}')
		self.infra = os.path.join(repository, self.pause).replace(".tar", "")
		if op.find(self.infra) != -1:
			self.log.warnning("%s image has been exists in docker repository." % self.infra)
			self.infra_version = sysutils.runCMD('docker images %s --format={{.Tag}}' % self.infra)
			return 
		self.log.info("Try to upload container image to docker repository.")
		op = sysutils.runCMD('docker load -i %s' % self.pause_path)
		if not op:
			self.log.error("Failed to upload container image.")
			sys.exit(1)
		self.log.info("Upload container image successfully.")
		self.infra_version = sysutils.runCMD('docker images %s --format={{.Tag}}' % self.infra)
		
	def configDocker(self):

		daemon_json = '/etc/docker/daemon.json'
		list = sysutils.getJsonItem(daemon_json,  u'insecure-registries')
		if list:
			registry = list[0].split(':')[0]
			if registry == self.master_ip:
				self.log.info("INFO: REGISTRY has been set.")
				return True
			daemon_conntent = '''{ "insecure-registries":["%s:5000"] }''' % self.master_ip
			sysutils.WriteToFile(daemon_json, daemon_conntent, mode='w')
			
			sysutils.runCMD('systemctl daemon-reload')
			sysutils.ServiceCtl('docker', 'enable')
			if not sysutils.ServiceCtl('docker', 'restart'):
				self.log.error("Failed to restart docker service.")
				return True
			else:
				self.log.info("Restarted docker service successfully.")
				return False
		
	def configKubelet(self):

		config_file = '/etc/kubernetes/config'
		config_content = '''
KUBE_LOGTOSTDERR="--logtostderr=true"
KUBE_LOG_LEVEL="--v=0"
KUBE_ALLOW_PRIV="--allow-privileged=true"
'''
		sysutils.WriteToFile(config_file, config_content.strip(), mode='w')
		
		kubelet_file = '/etc/kubernetes/kubelet'
		kubelet_content = '''
KUBELET_ADDRESS="--address=%s"
KUBELET_HOSTNAME="--hostname-override=%s"
KUBELET_POD_INFRA_CONTAINER="--pod-infra-container-image=%s:%s"
KUBELET_ARGS="--kubeconfig=%s"
''' % (self.local_ip, self.node, self.infra, self.infra_version, kubelet_config)
		sysutils.WriteToFile(kubelet_file, kubelet_content.strip(), mode='w')
		
		kubelet_config_content = '''
apiVersion: v1
clusters:
- cluster:
    insecure-skip-tls-verify: true
    server: http://%s:%s
  name: kubernetes
contexts:
- context:
    cluster: kubernetes
    user: ""
  name: system:node:%s
current-context: system:node:%s
kind: Config
preferences: {}
users: []
''' % (self.master_ip, self.master_port, self.node, self.node)
		sysutils.WriteToFile(kubelet_config, kubelet_config_content.strip(), mode='w')
		
		service_file = '/etc/systemd/system/kubelet.service'
		service_content = '''
[Unit]
Description=Kubernetes Kubelet Server
Documentation=https://github.com/GoogleCloudPlatform/kubernetes
After=docker.service
Requires=docker.service

[Service]
WorkingDirectory=/var/lib/kubelet
EnvironmentFile=-/etc/kubernetes/config
EnvironmentFile=-/etc/kubernetes/kubelet
ExecStart=/usr/bin/kubelet \\
            $KUBE_LOGTOSTDERR \\
            $KUBE_LOG_LEVEL \\
            $KUBELET_API_SERVER \\
            $KUBELET_ADDRESS \\
            $KUBELET_PORT \\
            $KUBELET_HOSTNAME \\
            $KUBE_ALLOW_PRIV \\
            $KUBELET_POD_INFRA_CONTAINER \\
            $KUBELET_ARGS
Restart=on-failure

[Install]
WantedBy=multi-user.target
'''
		sysutils.WriteToFile(service_file, service_content.strip(), mode='w')
		
		sysutils.runCMD('systemctl daemon-reload')
		sysutils.ServiceCtl('kubelet', 'enable')
		if not sysutils.ServiceCtl('kubelet', 'restart'):
			self.log.error("Failed to start kubelet service.")
		else:
			self.log.info("Started kubelet service successfully.")
			self.k8s_installed = True
			
	def configKubeproxy(self):
		
		proxy_file = '/etc/kubernetes/proxy'
		proxy_content = '''
KUBE_PROXY_ARGS="--hostname-override=%s --kubeconfig=%s"
''' % (self.node, kube_proxy_config)
		sysutils.WriteToFile(proxy_file, proxy_content.strip(), mode='w')
		
		kube_proxy_config_content = '''
apiVersion: v1
clusters:
- cluster:
    server: http://%s:%s
  name: kubernetes
contexts:
- context:
    cluster: kubernetes
  name: default
current-context: default
kind: Config
preferences: {}
users: []
''' % (self.master_ip, self.master_port)
		sysutils.WriteToFile(kube_proxy_config, kube_proxy_config_content.strip(), mode='w')
		
		service_file = '/etc/systemd/system/kube-proxy.service'
		service_content = '''
[Unit]
Description=Kubernetes Kube-Proxy Server
Documentation=https://github.com/GoogleCloudPlatform/kubernetes
After=network.target

[Service]
EnvironmentFile=-/etc/kubernetes/config
EnvironmentFile=-/etc/kubernetes/proxy
ExecStart=/usr/bin/kube-proxy \\
            $KUBE_LOGTOSTDERR \\
            $KUBE_LOG_LEVEL \\
            $KUBE_MASTER \\
            $KUBE_PROXY_ARGS
Restart=on-failure
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
'''
		sysutils.WriteToFile(service_file, service_content.strip(), mode='w')
		
		sysutils.runCMD('systemctl daemon-reload')
		sysutils.ServiceCtl('kube-proxy', 'enable')
		if not sysutils.ServiceCtl('kube-proxy', 'restart'):
			self.log.error("Failed to start kube-proxy service.")
		else:
			self.log.info("Started kube-proxy service successfully.")
		
	def joinCluster(self):
	
		sysutils.setEnv()
		self.createDir()
		if not self.k8s_installed:
			self.downloadPKG()
			self.decompressPKG()
			self.cpFile()
			self.uploadImage()
		self.configDocker()
		self.configKubelet()
		self.configKubeproxy()
		self.cleanPKG()
			
	def leaveCluster(self):
		
		if sysutils.EnsureFileExists(kubelet_config):
			if self.k8s_conf_node != None:
				sysutils.runCMD("kubectl delete node %s -s http://%s:%s" % (self.k8s_conf_node, self.k8s_conf_master, self.k8s_conf_port))
			
			sysutils.ServiceCtl('kubelet', 'stop')
			sysutils.ServiceCtl('kube-proxy', 'stop')
			sysutils.RemoveFile(kubelet_config)
			sysutils.RemoveFile(kube_proxy_config)
		
	def requestToServer(self):
		
		json = sysutils.get_newest_file(config_dir, ".json")
		if not json:
			self.log.error("Unable to find json file: no such file.")
			sys.exit(1)
		pub_key_id = sysutils.getJsonItem(json, 'keyId')
		if not pub_key_id:
			self.log.error("Unable to get [keyId] in json file: no such content.")
			sys.exit(1)
		pub_key_content = sysutils.getJsonItem(json, 'publicKey')
		if not pub_key_content:
			self.log.error("Unable to get [publicKey] in json file: no such content.")
			sys.exit(1)
		
		self.pub_key = os.path.join(config_dir, 'pub.key')
		sysutils.WriteToFile(self.pub_key, pub_key_content, mode='w')
		
		if not sysutils.runCMD('openssl rsa -in %s -noout -text -pubin' % self.pub_key):
			self.log.error("Unable to load Public Key: invalidated Public Key.")
			sys.exit(1)
			
		mac_rsautil = sysutils.runCMD('echo -n %s | openssl rsautl -encrypt -inkey %s  -pubin | base64 -w0' % (self.mac, self.pub_key))
		url = 'http://%s:%d/uconnect/catalog/discovery' % (self.server, self.server_port)
		data = {"sign": mac_rsautil, "macAddr": self.mac, "archType": self.arch, "pubKeyId": pub_key_id}
		# dict type
		self.metadata = sysutils.POST(url, data)
		if not self.metadata:
			self.log.error("Failed to get membership from server: %s" % self.metadata[u'message'])
			return False
		if self.metadata[u'code'] != 200:
			self.log.error("Failed to get membership from server: %s" % self.metadata[u'message'])
			return False
		return True
		
	def getClusterInfo(self):
		
		if os.path.exists(kubelet_config):
			pattern = '(?<=server: http://).*'
			str = sysutils.MatchPattern(pattern, file=kubelet_config)
			self.k8s_conf_master = str.split(":")[0]
			self.k8s_conf_port = str.split(":")[1]
			pattern = '(?<=system:node:).*$'
			self.k8s_conf_node = sysutils.MatchPattern(pattern, file=kubelet_config)
		else:
			self.k8s_conf_master = None
			self.k8s_conf_port = None
			self.k8s_conf_node = None
		
	def checkClusterInfo(self):
		
		self.match = True
		self.master_ip = str(self.metadata[u'result'][u'ip'])
		self.master_port = str(self.metadata[u'result'][u'port'])
		self.node = str(self.metadata[u'result'][u'nodeName'])
		
		if self.k8s_conf_master != self.master_ip:
			self.match = False
			self.log.info("update found in KUBERNETES MASTER: oldVal [%s] newVal[%s]" % (self.k8s_conf_master, self.master_ip))
		if self.k8s_conf_port != self.master_port:
			self.match = False
			self.log.info("update found in KUBERNETES MASTER PORT: oldVal [%s] newVal[%s]" % (self.k8s_conf_port, self.master_port))
		if self.k8s_conf_node != self.node:
			self.match = False
			self.log.info("update found in KUBERNETES nodeName: oldVal [%s] newVal[%s]" % (self.k8s_conf_node, self.node))
					
	def run(self):
		
		self.log = output.Logging(log_path)
		self.log.info('program is running now.')
		
		if sysutils.IsExecutable(kubelet_path) and sysutils.IsExecutable(kube_proxy_path) and sysutils.IsExecutable(kubectl_path):
			self.k8s_installed = True
			self.log.info('kubernetes node has been installed')
		
		while True:
			if self.requestToServer():
				self.getClusterInfo()
				self.checkClusterInfo()
				if not self.match:
					self.leaveCluster()
					self.joinCluster()
				else:
					print("INFO: nothing to update.")
			time.sleep(polling_time)