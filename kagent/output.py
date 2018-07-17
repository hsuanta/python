#!/usr/bin/env python
# coding: utf-8

import time
import logging
import sysutils

class Logging(object):
	def GetTime(self):
		"""Return a string representing the current time in the form::

			Mon dd hh:mm:ss

		:return: a string representing the current time
		"""
		months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
					'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
		now = time.localtime(time.time())
		ret = months[int(time.strftime('%m', now)) - 1] + time.strftime(' %d %T', now)
		return ret

	def info(self, msg):
		time = self.GetTime()
		self.msg = '%s %s: %s' % (time, self.level[0], msg)
		sysutils.WriteToFile(self.file, self.msg)
		
	def warnning(self, msg):
		time = self.GetTime()
		self.msg = '%s %s: %s' % (time, self.level[1], msg)
		sysutils.WriteToFile(self.file, self.msg)
	
	def error(self, msg):
		time = self.GetTime()
		self.msg = '%s %s: %s' % (time, self.level[2], msg)
		sysutils.WriteToFile(self.file, self.msg)
	
	def __init__(self, file):
		self.level = [ 'INFO', 'WARNNING', 'ERROR' ]
		self.file = file
		sysutils.BackupFile(self.file)