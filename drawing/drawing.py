#!/usr/bin/env python
import sys,os
NUM_ = raw_input("please enter number between (5 to 9) : ")
try:
	NUM = int(NUM_)
except ValueError:
	print "please try again and enter number."
if  NUM <= 5 or NUM >=  9:
	print "please enter number between (5 to 9)."
	sys.exit(1)
else:
	os.system('clear')
	for i in range(1,NUM+1):
		for t in range(NUM,i-1,-1):
			print " ",
		for s in range(1,i+1):
			print  " . ",
		print ""

	for i in range(1,NUM+1):
		for t in range (1,i+2):
			print " ",
		for s in range(NUM,i,-1):
			print " . ",
		print ""	
print "\n\t\t this is my demo."
sys.exit(0)
