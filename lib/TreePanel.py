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
from .SoftwareDashboard import *
from .SoftwareUserStatus import *
from .SoftwareModels import *
from .SoftwareSessionApp import *
from .SoftwareReportManager import *
from .KpmManager import *
from .Constants import *
from .TrackerManager import *
from .SoftwareFileChangeInfoSummaryData import *
from .SlackManager import *
from .OsaScriptUtil import *

GOOGLE_SIGNUP_LABEL = 'Sign up with Google'
GITHBUB_SIGNUP_LABEL = 'Sign up with GitHub'
EMAIL_SIGNUP_LABEL = 'Sign up with Email'
HIDE_STATUS_LABEL = 'Hide status bar metrics'
SHOW_STATUS_LABEL = 'Show status bar metrics'
SWITCH_ACCOUNT_LABEL = 'Switch account'
SUBMIT_FEEDBACK_LABEL = 'Submit feedback'
LEARN_MORE_LABEL = 'Learn more'
SEE_ADVANCED_METRICS = 'More data at Software.com'
DASHBOARD_LABEL = 'Dashboard'
TURN_ON_NOTIFICATIONS_LABEL = 'Turn on notifications'
PAUSE_NOTIFICATIONS_LABEL = 'Pause notifications'
TODAY_VS_AVG_LABEL = 'Today vs.'
SET_PRESENCE_TO_AWAY_LABEL = 'Set presence to away'
SET_PRESENCE_TO_ACTIVE_LABEL = 'Set presence to active'
UPDATE_PROFILE_STATUS_LABEL = 'Update profile status'
TURN_OFF_DARK_MODE_LABEL = 'Turn off dark mode'
TURN_ON_DARK_MODE_LABEL = 'Turn on dark mode'
TOGGLE_DOCK_LABEL = 'Toggle dock'
SLACK_WORKSPACES_LABEL = 'Slack workspaces'
ADD_SLACK_WORKSPACE_LABEL = 'Add workspace'


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

    self.keys.append('-----------------------------------')

    self.keys.append('%s%s' % (zeroDepth, "FLOW"))

    # data = {profile: {avatar_hash, display_name, display_name_normalized, email, first_name, ...,status_text, status_emoji, skype, status_expireation, status_text_canonical, title } }
    slackStatus = getSlackStatus()
    statusLabel = UPDATE_PROFILE_STATUS_LABEL
    if (slackStatus is not None and slackStatus["profile"] is not None
        and slackStatus["profile"]["status_text"] is not None
        and slackStatus["profile"]["status_text"] != ''):
        statusLabel += " (" + slackStatus["profile"]["status_text"] + ")"

    self.keys.append('%s%s' % (firstChildDepth, statusLabel))

    # data = {'next_dnd_end_ts': 1610892000, 'ok': True, 'next_dnd_start_ts': 1610861400, 'dnd_enabled': True, 'snooze_enabled': False}
    slackDndInfo = getSlackDnDInfo()
    if (slackDndInfo is None or slackDndInfo["snooze_enabled"] is False):
        self.keys.append('%s%s' % (firstChildDepth, PAUSE_NOTIFICATIONS_LABEL))
    else:
        self.keys.append('%s%s' % (firstChildDepth, TURN_ON_NOTIFICATIONS_LABEL))

    # data = {'auto_away': False, 'ok': True, 'manual_away': False, 'connection_count': 1, 'presence': 'active', 'last_activity': 1610866316, 'online': True}
    slackPresence = getSlackPresence()
    if (slackPresence is None or slackPresence["presence"] == "active"):
        self.keys.append('%s%s' % (firstChildDepth, SET_PRESENCE_TO_AWAY_LABEL))
    else:
        self.keys.append('%s%s' % (firstChildDepth, SET_PRESENCE_TO_ACTIVE_LABEL))

    if (isMac()):
        darkMode = isDarkMode()
        if (darkMode is True):
            self.keys.append('%s%s' % (firstChildDepth, TURN_OFF_DARK_MODE_LABEL))
        else:
            self.keys.append('%s%s' % (firstChildDepth, TURN_ON_DARK_MODE_LABEL))

        self.keys.append('%s%s' % (firstChildDepth, TOGGLE_DOCK_LABEL))

    self.keys.append('-----------------------------------')

    self.keys.append('%s%s' % (zeroDepth, "STATS"))

    data = getSessionSummaryData()
    codeTimeSummary = getCodeTimeSummary()
    data.update(codeTimeSummary)

    refClass = getItem("reference-class")
    if (refClass is None):
        refClass = "user"

    if (refClass == "user"):
        self.keys.append('%s%s' % (firstChildDepth, TODAY_VS_AVG_LABEL + " your daily average"))
    else:
        self.keys.append('%s%s' % (firstChildDepth, TODAY_VS_AVG_LABEL + " the global daily average"))

    todayString = datetime.today().strftime('%a')
    
    # code time
    codeTimeStr = humanizeMinutes(data["codeTimeMinutes"]).strip()
    codeTimeAvg = data["averageDailyCodeTimeMinutes"] if refClass == "user" else data["globalAverageDailyCodeTimeMinutes"]
    codeTimeAvgStr = humanizeMinutes(codeTimeAvg).strip()
    self.keys.append('%s%s' % (firstChildDepth, "Code time: " + codeTimeStr + " (" + codeTimeAvgStr + ")"))

    # active code time
    activeCodeTimeStr = humanizeMinutes(data["activeCodeTimeMinutes"]).strip()
    activeCodeTimeAvg = data["averageDailyMinutes"] if refClass == "user" else data['globalAverageDailyMinutes']
    activeCodeTimeAvgStr = humanizeMinutes(activeCodeTimeAvg).strip()
    self.keys.append('%s%s' % (firstChildDepth, "Active code time: " + activeCodeTimeStr + " (" + activeCodeTimeAvgStr + ")"))

    # lines added
    currLinesAdded = self.currentKeystrokeStats['currentDayLinesAdded'] + data['currentDayLinesAdded']
    linesAddedStr = formatNumWithK(currLinesAdded)
    linesAddedAvg = data["averageLinesAdded"] if refClass == "user" else data['globalAverageLinesAdded']
    linesAddedAvgStr = formatNumWithK(linesAddedAvg)
    self.keys.append('%s%s' % (firstChildDepth, "Lines added: " + linesAddedStr + " (" + linesAddedAvgStr + ")"))

    # lines removed
    currLinesRemoved = self.currentKeystrokeStats['currentDayLinesRemoved'] + data['currentDayLinesRemoved']
    linesRemovedStr = formatNumWithK(currLinesRemoved)
    linesRemovedAvg = data["averageLinesRemoved"] if refClass == "user" else data['globalAverageLinesRemoved']
    linesRemovedAvgStr = formatNumWithK(linesRemovedAvg)
    self.keys.append('%s%s' % (firstChildDepth, "Lines removed: " + linesRemovedStr + " (" + linesRemovedAvgStr + ")"))


    # keystrokes
    currKeystrokes = self.currentKeystrokeStats['currentDayKeystrokes'] + data['currentDayKeystrokes']
    keystrokesStr = formatNumWithK(currKeystrokes)
    keystrokesAvg = data["averageDailyKeystrokes"] if refClass == "user" else data['globalAverageDailyKeystrokes']
    keystrokesAvgStr = formatNumWithK(keystrokesAvg)
    self.keys.append('%s%s' % (firstChildDepth, "Keystrokes: " + keystrokesStr + " (" + keystrokesAvgStr + ")"))

    self.keys.append('%s%s' % (firstChildDepth, DASHBOARD_LABEL))
    self.keys.append('%s%s' % (firstChildDepth, SEE_ADVANCED_METRICS))
    

  def buildTopFilesNode(self, fileChangeInfoMap):
    
    filesChanged = len(fileChangeInfoMap.keys()) if fileChangeInfoMap else 0

    if filesChanged > 0:
        return 'Today: {}'.format(filesChanged)
    else:
        return None

  def setCurrentKeystrokeStats(self, keystrokeStats):
    if not keystrokeStats:
        self.currentKeystrokeStats = SessionSummary()
    else:
        for key in keystrokeStats.source:
            # fileInfo is of type FileChangeInfo
            fileInfo = keystrokeStats.source[key] 
            self.currentKeystrokeStats.currentDayKeystrokes = fileInfo.keystrokes
            self.currentKeystrokeStats.currentDayLinesAdded = fileInfo.linesAdded
            self.currentKeystrokeStats.currentDayLinesRemoved = fileInfo.linesRemoved

  def topFilesMetricsNode(self, fileChangeInfos, sortBy, id):
    if not fileChangeInfos or len(fileChangeInfos) == 0:
        return None 

    sortedArr = []
    if sortBy == 'duration_seconds' or sortBy == 'kpm' or sortBy == 'keystrokes':
        sortedArr = list(sorted(fileChangeInfos, key=lambda info: info[sortBy], reverse=True))
    else:
        log('Sorting by invalid sortBy value: "{}"'.format(sortBy))

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
            if (key == DASHBOARD_LABEL):
                codetimemetricsthread = Thread(target=launchCodeTimeMetrics)
                codetimemetricsthread.start()
            elif key == SWITCH_ACCOUNT_LABEL:
                switchAccount()
            elif (key == HIDE_STATUS_LABEL or key == SHOW_STATUS_LABEL):
                toggleStatus()
            elif (key == LEARN_MORE_LABEL):
                displayReadmeIfNotExists(True)
            elif (key == SEE_ADVANCED_METRICS):
                launchWebDashboardUrl()
            elif (key == SUBMIT_FEEDBACK_LABEL):
                launchSubmitFeedback()
            elif (key == GOOGLE_SIGNUP_LABEL):
                launchLoginUrl('google')
            elif (key == GITHBUB_SIGNUP_LABEL):
                launchLoginUrl('github')
            elif (key == EMAIL_SIGNUP_LABEL):
                launchLoginUrl('software')
            elif (key == TURN_ON_NOTIFICATIONS_LABEL):
                enableSlackNotifications()
            elif (key == PAUSE_NOTIFICATIONS_LABEL):
                pauseSlackNotifications()
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
            elif (key.find(UPDATE_PROFILE_STATUS_LABEL) != -1):
                # update the profile status
                sublime.active_window().run_command('update_slack_status_msg')
            elif (key == SET_PRESENCE_TO_AWAY_LABEL):
                toggleSlackPresence("away")
            elif (key == SET_PRESENCE_TO_ACTIVE_LABEL):
                toggleSlackPresence("auto")
            elif (key == TURN_ON_DARK_MODE_LABEL or key == TURN_OFF_DARK_MODE_LABEL):
                toggleDarkMode()
            elif (key == TOGGLE_DOCK_LABEL):
                toggleDock()
            elif (key == ADD_SLACK_WORKSPACE_LABEL):
                connectSlackWorkspace()

#EOL
