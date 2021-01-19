import os
import sublime_plugin
import sublime
from threading import Thread, Timer, Event
from subprocess import Popen, PIPE
from .CommonUtil import *

def toggleDarkMode():
	cmd = '''
	osascript -e '
		tell application "System Events"
			tell appearance preferences
				set dark mode to not dark mode
			end tell
		end tell'
	'''
	os.system(cmd)
	# set that this has been executed
	setItem("checked_sublime_sys_events", True)

def isDarkMode():
	checked = getItem("checked_sublime_sys_events")
	if (checked is True):
		script = '''
			try
				tell application "System Events"
					tell appearance preferences
						set t_info to dark mode
					end tell
				end tell
			on error
				return false
			end try
		'''
		try:
			cmd = script.encode('latin-1')
			result = runCommand(cmd, ['osascript', '-'])

			if (result is None or result == 'false'):
				return False
			return True
		except Exception as e:
			print("Code Time: error getting dark mode state: %s " % e)
			# no music found playing
			return False

def toggleDock():
	cmd = '''
		osascript -e '
		tell application "System Events"
			tell dock preferences
				set x to autohide
				if x is false then
					set properties to {autohide:true}
				else 
					set properties to {autohide:false}
				end if
			end tell
		end tell'
	'''
	os.system(cmd)
	# set that this has been executed
	setItem("checked_sublime_sys_events", True)

def runCommand(cmd, args=[]):
	p = Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE)
	stdout, stderr = p.communicate(cmd)
	return stdout.decode('utf-8').strip()
