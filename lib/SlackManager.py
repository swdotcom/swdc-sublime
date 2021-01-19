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
	integrations = getIntegrations()
	workspaces = [x for x in integrations if (x['name'].lower() == 'slack' and x['status'].lower() == 'active')]
	return workspaces if workspaces is not None and len(workspaces) > 0 else []

def hasSlackWorkspaces():
	return True if len(getSlackWorkspaces()) > 0 else False

def disconnectSlackWorkspace():
	result = checkSlackConnection(False)
	if (result is False):
		# show a prompt there are no slack workspaces to disconnect
		sublime.message_dialog("No Slack workspaces found to disconnect")

	# set the pending callback
	global pendingCallback
	pendingCallback = disconnectSlackWorkspaceCallback
	showSlackWorkspaceSelection()

def disconnectSlackWorkspaceCallback(workspace):
	if (workspace is not None):
		removeSlackIntegration(workspace['authId'])
	else:
		clearPendingCallback()

def connectSlackWorkspace():
	is_registered = checkRegistration(True)
	if (is_registered is False):
		return

	params = {}
	params["plugin"] = getPluginType()
	params["plugin_uuid"] = getPluginUuid()
	params["pluginVersion"] = getVersion()
	params["plugin_id"] = getPluginId()
	params["auth_callback_state"] = getAuthCallbackState()

	url = getApi() + "/auth/slack?" + urlencode(params)
	webbrowser.open(url)

	t = Timer(10, refetchSlackConnectStatusLazily, [40])
	t.start()

def pauseSlackNotifications():
	is_registered = checkRegistration(True)
	if (is_registered is False):
		return

	is_connected = checkSlackConnection(True)
	if (is_connected is False):
		return

	updated = False
	workspaces = getSlackWorkspaces()
	for i in range(len(workspaces)):
		workspace = workspaces[i]
		resp = api_call('dnd.setSnooze', {'num_minutes': 120, 'token': workspace["access_token"]})
		if (resp['ok'] is True):
			updated = True

	if (updated is True):
		sublime.message_dialog("Slack notifications are paused for 2 hours")

def enableSlackNotifications():
	is_registered = checkRegistration(True)
	if (is_registered is False):
		return

	is_connected = checkSlackConnection(True)
	if (is_connected is False):
		return

	updated = False
	workspaces = getSlackWorkspaces()
	for i in range(len(workspaces)):
		workspace = workspaces[i]
		resp = api_call('dnd.endSnooze', {'token': workspace["access_token"]})
		if (resp['ok'] is True):
			updated = True

	if (updated is True):
		sublime.message_dialog("Slack notifications enabled")

def getSlackDnDInfo():
	workspaces = getSlackWorkspaces()
	for i in range(len(workspaces)):
		workspace = workspaces[i]
		resp = api_call('dnd.info', {'token': workspace["access_token"]})
		if (resp['ok'] is True):
			# return the 1st one
			return resp

	return None

def getSlackStatus():
	workspaces = getSlackWorkspaces()
	for i in range(len(workspaces)):
		workspace = workspaces[i]
		resp = api_call('users.profile.get', {'token': workspace["access_token"]})
		if (resp['ok'] is True):
			# return the 1st one
			return resp

	return None

def getSlackPresence():
	workspaces = getSlackWorkspaces()
	for i in range(len(workspaces)):
		workspace = workspaces[i]
		resp = api_call('users.getPresence', {'token': workspace["access_token"]})
		if (resp['ok'] is True):
			# return the 1st one
			return resp

	return None

# accepted states: "auto" or "away"
def toggleSlackPresence(state):
	is_registered = checkRegistration(True)
	if (is_registered is False):
		return

	is_connected = checkSlackConnection(True)
	if (is_connected is False):
		return

	updated = False
	workspaces = getSlackWorkspaces()
	for i in range(len(workspaces)):
		workspace = workspaces[i]
		resp = api_call('users.setPresence', {'token': workspace["access_token"], 'presence': state})
		if (resp['ok'] is True):
			updated = True

	if (updated is True):
		sublime.message_dialog("Slack presence updated")

def updateSlackStatusText(message):
	updated = False
	workspaces = getSlackWorkspaces()
	for i in range(len(workspaces)):
		workspace = workspaces[i]
		resp = api_call('users.profile.set', {'token': workspace["access_token"], 'profile': {'status_text': message, 'status_emoji': "", 'status_expiration': 0}})
		if (resp['ok'] is True):
			updated = True

	if (updated is True):
		sublime.message_dialog("Slack status message updated")

def clearSlackStatusText():
	updated = False
	workspaces = getSlackWorkspaces()
	for i in range(len(workspaces)):
		workspace = workspaces[i]
		resp = api_call('users.profile.set', {'token': workspace["access_token"], 'profile': {'status_text': "", 'status_emoji': ""}})
		if (resp['ok'] is True):
			updated = True

	if (updated is True):
		sublime.message_dialog("Slack status message cleared")

#######################################################################################
# PRIVATE METHODS
#######################################################################################

# done
def showSlackWorkspaceSelection():
	workspaces = getSlackWorkspaces()
	# create the options
	options = []
	for i in range(len(workspaces)):
		workspace = workspaces[i]
		options.append(workspace['team_domain'] + " (" + workspace['team_name'] + ")")

	# show a prompt of which workspace to get the access token from
	sublime.active_window().show_quick_panel(options, showSlackWorkspaceSelectionHandler)

# done
def showSlackWorkspaceSelectionHandler(result_idx):
	# -1 means nothing was selected
	if (result_idx == -1):
		global pendingCallback
		pendingCallback = None
		return

	workspaces = getSlackWorkspaces()
	if (len(workspaces) > result_idx):
		# perform the waiting callback
		pendingCallback(workspaces[result_idx])
	else:
		clearPendingCallback()

# done
def checkSlackConnection(show_connect=True):
	if (hasSlackWorkspaces() is False):
		clearPendingCallback()
		if (show_connect is True):
			# show the prompt
			options = ['Connect a Slack workspace to continue', 'Not now']
			sublime.active_window().show_quick_panel(options, connectSlackPromptHandler)
		return False
	else:
		return True

# done
def connectSlackPromptHandler(result_idx):
	# zero means they've selected to connect slack
	if (result_idx != 0):
		clearPendingCallback()
	else:
		# connect
		connectSlackWorkspace()

# done
def removeSlackIntegration(auth_id):
	new_workspaces = [x for x in getSlackWorkspaces() if (x['authId'] != auth_id)]
	syncIntegrations(new_workspaces)
	clearPendingCallback()

def clearPendingCallback():
	global pendingCallback
	pendingCallback = None

def checkRegistration(show_signup=True):
	name = getItem("name")
	if (name is None):
		clearPendingCallback()
		if (show_signup is True):
			# show the signup confirm
			options = ['Connecting Slack requires a registered account. Sign up or log in to continue.', 'Not now']
			sublime.active_window().show_quick_panel(options, signupPromptHandler)
		return False
	
	return True

def signupPromptHandler(result_idx):
	# zero means they've selected to sign up
	if (result_idx == 0):
		# show the sign up flow
		signupOptions = ['Google', 'GitHub', 'Email']
		sublime.active_window().show_quick_panel(signupOptions, authSelectionHandler)

def authSelectionHandler(result_idx):
	if (result_idx == 0):
		launchLoginUrl('google')
	elif (result_idx == 1):
		launchLoginUrl('github')
	elif (result_idx == 2):
		launchLoginUrl('software')

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
	foundNewIntegration = False
	userState = getUserRegistrationState(True)

	if (userState["user"] is not None and userState["user"]["integrations"] is not None):
		integrations = userState["user"]["integrations"]

		existingIntegrations = getIntegrations()
		for i in range(len(integrations)):
			integration = integrations[i]
			if (integration["name"].lower() == 'slack' and integration["status"].lower() == 'active'):

				first = next(filter(lambda x: x.authId == integration["authId"], existingIntegrations), None)

				if (first is None):
					resp = api_call('users.identity', {'token': integration["access_token"]})
					if (resp['ok'] is True):
						integration["team_domain"] = resp["team"]["domain"]
						integration["team_name"] = resp["team"]["name"]
						foundNewIntegration = True
						existingIntegrations.append(integration)
						syncIntegrations(existingIntegrations)
				break

	return foundNewIntegration

