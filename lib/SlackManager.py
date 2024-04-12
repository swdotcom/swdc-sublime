import os
import sys
import json
import webbrowser
import sublime
import sublime_plugin
from threading import Thread, Timer, Event
from .SoftwareUtil import *
from .CommonUtil import *
from .SoftwareUserStatus import *
from .SlackHttp import *
try:
	#python2
	from urllib import urlencode
except ImportError:
	#python3
	from urllib.parse import urlencode

pendingCallback = None

def getSlackWorkspaces():
    currentUser = getUser(False)

    if (currentUser):
        integrations =  currentUser.get("integration_connections", [])

        workspaces = [x for x in integrations if (x['integration_type_id'] == 14 and x['status'].lower() == 'active')]
        return workspaces if workspaces is not None and len(workspaces) > 0 else []

    return []

def hasSlackWorkspaces():
	return True if len(getSlackWorkspaces()) > 0 else False

def disconnectSlackWorkspace():
	launchSlackSettings()

def connectSlackWorkspace():
	launchSlackSettings()

	t = Timer(10, refetchSlackConnectStatusLazily, [40])
	t.start()

def launchSlackSettings():
	url = getWebUrl() + "/data_sources/integration_types/slack"
	webbrowser.open(url)

#######################################################################################
# PRIVATE METHODS
#######################################################################################

def refetchSlackConnectStatusLazily(try_count=40):
	foundSlackAuth = getSlackAuth()
	if (foundSlackAuth is False):
		if (try_count > 0):
			try_count -= 1
			t = Timer(10, refetchSlackConnectStatusLazily, [try_count])
			t.start()
		else:
			setAuthCallbackState(None)
	else:
		setAuthCallbackState(None)
		sublime.message_dialog("Successfully connected to Slack")

def getSlackAuth():
	curentUser = getUser(True)

	return hasSlackWorkspaces()
