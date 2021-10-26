from threading import Thread, Timer, Event
from package_control import events
from queue import Queue
import webbrowser
import time as timeModule
import os
import json
import sublime_plugin
import sublime
from datetime import *
from .SoftwareHttp import *
from .SoftwareUtil import *
from .SoftwareRepo import *
from .SoftwareOffline import *
from .SoftwareSettings import *
from .SoftwareWallClock import *
from .SoftwareUserStatus import *
from .SoftwareModels import *
from .SoftwareSessionApp import *
from .KpmManager import *
from .Constants import *
from .TrackerManager import *
from .SoftwareFileChangeInfoSummaryData import *
from .SlackManager import *
from .OsaScriptUtil import *
from .Logger import *

GOOGLE_SIGNUP_LABEL = 'Sign up with Google'
GITHBUB_SIGNUP_LABEL = 'Sign up with GitHub'
EMAIL_SIGNUP_LABEL = 'Sign up with Email'
REGISTER_OR_LOGIN_LABEL = 'Register or login'
HIDE_STATUS_LABEL = 'Hide status bar metrics'
SHOW_STATUS_LABEL = 'Show status bar metrics'
SWITCH_ACCOUNT_LABEL = 'Switch account'
SUBMIT_FEEDBACK_LABEL = 'Submit feedback'
UPDATE_PREFERENCES_LABEL = 'Settings'
LEARN_MORE_LABEL = 'Learn more'
VIEW_DASHBOARD_LABEL = 'View dashboard'
SEE_ADVANCED_METRICS = 'More data at Software.com'
TODAY_VS_AVG_LABEL = 'Today vs.'
SLACK_WORKSPACES_LABEL = 'Slack workspaces'
ADD_SLACK_WORKSPACE_LABEL = 'Add workspace'
ENABLE_FLOW_MODE = 'Enter Flow Mode'
EXIT_FLOW_MODE = 'Exit Flow Mode'

class ShowTreeView(sublime_plugin.TextCommand):
  def run(self, edit):
    self.showTree()

  def showTree(self):
    self.currentKeystrokeStats = SessionSummary()
    self.keys = []
    self.create_tree()
    sublime.active_window().show_quick_panel(self.keys, self.itemSelectionHandler)

  def create_tree(self):
    zeroDepth = ' '
    firstChildDepth = ' ' * 8
    secondChildDepth = ' ' * 16

    self.keys.append('%s%s' % (zeroDepth, "FLOW"))
    if getItem('name') is not None:
        self.keys.append('%s%s' % (firstChildDepth, ENABLE_FLOW_MODE))
        self.keys.append('%s%s' % (firstChildDepth, EXIT_FLOW_MODE))
    else:
        self.keys.append('%s%s' % (firstChildDepth, REGISTER_OR_LOGIN_LABEL))

    self.keys.append('-----------------------------------')

    self.keys.append('%s%s' % (zeroDepth, "STATS"))

    self.keys.append('%s%s' % (firstChildDepth, UPDATE_PREFERENCES_LABEL))
    self.keys.append('%s%s' % (firstChildDepth, VIEW_DASHBOARD_LABEL))
    self.keys.append('%s%s' % (firstChildDepth, SEE_ADVANCED_METRICS))

    data = getSessionSummaryData()

    # active code time
    activeCodeTimeStr = humanizeMinutes(data["currentDayMinutes"]).strip()
    activeCodeTimeAvg = data["averageDailyMinutes"]
    activeCodeTimeAvgStr = humanizeMinutes(activeCodeTimeAvg).strip()
    self.keys.append('%s%s' % (firstChildDepth, "Active code time: " + activeCodeTimeStr))

    self.keys.append('-----------------------------------')
    self.keys.append('%s%s' % (zeroDepth, "ACCOUNT"))

    if not getItem('name'):
        self.keys.append('%s%s' % (firstChildDepth, GOOGLE_SIGNUP_LABEL))
        self.keys.append('%s%s' % (firstChildDepth, GITHBUB_SIGNUP_LABEL))
        self.keys.append('%s%s' % (firstChildDepth, EMAIL_SIGNUP_LABEL))
    else:
        self.keys.append('%s%s(%s)' % (firstChildDepth, "Logged in as ", getItem('name')))
        self.keys.append('%s%s' % (firstChildDepth, SWITCH_ACCOUNT_LABEL))

    statusBarMessage = HIDE_STATUS_LABEL if getValue("show_code_time_status", True) else SHOW_STATUS_LABEL
    self.keys.append('%s%s' % (firstChildDepth, statusBarMessage))
    self.keys.append('%s%s' % (firstChildDepth, SUBMIT_FEEDBACK_LABEL))
    self.keys.append('%s%s' % (firstChildDepth, LEARN_MORE_LABEL))

    self.keys.append('%s%s' % (firstChildDepth, SLACK_WORKSPACES_LABEL))
    # get the workspaces and list them
    workspaces = getSlackWorkspaces()
    if (len(workspaces) > 0):
        for i in range(len(workspaces)):
            workspace = workspaces[i]
            self.keys.append('%s%s' % (secondChildDepth, workspace['team_domain'] + " (" + workspace['team_name'] + ")"))
    else:
        self.keys.append('%s%s' % (secondChildDepth, '<No workspaces found>'))

    self.keys.append('%s%s' % (secondChildDepth, ADD_SLACK_WORKSPACE_LABEL))

  def buildTopFilesNode(self, fileChangeInfoMap):
    
    filesChanged = len(fileChangeInfoMap.keys()) if fileChangeInfoMap else 0

    if filesChanged > 0:
        return 'Today: {}'.format(filesChanged)
    else:
        return None

  def topFilesMetricsNode(self, fileChangeInfos, sortBy, id):
    if not fileChangeInfos or len(fileChangeInfos) == 0:
        return None 

    sortedArr = []
    if sortBy == 'duration_seconds' or sortBy == 'kpm' or sortBy == 'keystrokes':
        sortedArr = list(sorted(fileChangeInfos, key=lambda info: info[sortBy], reverse=True))
    else:
        logIt('Sorting by invalid sortBy value: "{}"'.format(sortBy))

    childrenNodes = []
    length = min(3, len(sortedArr))
    for i in range(0, length):
        sortedObj = sortedArr[i]
        fileName = sortedObj['name']

        val = 0
        if sortBy == 'kpm' or sortBy == 'keystrokes':
            val = formatNumWithK(sortedObj['kpm'] or 0)
        elif sortBy == 'duration_seconds':
            minutes = sortedObj.get('duration_seconds', 0) / 60
            val = humanizeMinutes(minutes)

        fsPath = sortedObj['fsPath']
        label = '{} | {}'.format(fileName, val)

        childrenNodes.append(label)
    
    return childrenNodes 

  def itemSelectionHandler(self, idx):
    if (idx is not None and idx >= 0):
        key = self.keys[idx]

        if (key is not None):
            key = key.strip()
            if key == SWITCH_ACCOUNT_LABEL or key == REGISTER_OR_LOGIN_LABEL:
                switchAccount()
            elif (key == HIDE_STATUS_LABEL or key == SHOW_STATUS_LABEL):
                toggleStatus()
            elif (key == LEARN_MORE_LABEL):
                displayReadmeIfNotExists(True)
            elif (key == VIEW_DASHBOARD_LABEL):
                launchCodeTimeDashboard()
            elif (key == UPDATE_PREFERENCES_LABEL):
                launchUpdatePreferences()
            elif (key == SEE_ADVANCED_METRICS):
                launchWebDashboardUrl()
            elif (key == ENABLE_FLOW_MODE):
                enableFlowMode()
            elif (key == EXIT_FLOW_MODE):
                exitFlowMode()
            elif (key == SUBMIT_FEEDBACK_LABEL):
                launchSubmitFeedback()
            elif (key == GOOGLE_SIGNUP_LABEL):
                launchLoginUrl('google', False)
            elif (key == GITHBUB_SIGNUP_LABEL):
                launchLoginUrl('github', False)
            elif (key == EMAIL_SIGNUP_LABEL):
                launchLoginUrl('software', False)
            elif (key.find(TODAY_VS_AVG_LABEL) != -1):
                # today vs average label click, swap the avg comparison
                refClass = getItem("reference-class")
                if (refClass is None or refClass == "user"):
                    refClass = "global"
                else:
                    refClass = "user"
                setItem("reference-class", refClass)
                # show the tree view again to show the changes
                self.showTree()
            elif (key == ADD_SLACK_WORKSPACE_LABEL):
                connectSlackWorkspace()

#EOL
