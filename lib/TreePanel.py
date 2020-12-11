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

GOOGLE_SIGNUP_LABEL = 'Sign up with Google'
GITHBUB_SIGNUP_LABEL = 'Sign up with GitHub'
EMAIL_SIGNUP_LABEL = 'Sign up with Email'
HIDE_STATUS_LABEL = 'Hide status bar metrics'
SHOW_STATUS_LABEL = 'Show status bar metrics'
SWITCH_ACCOUNT_LABEL = 'Switch account'
SUBMIT_FEEDBACK_LABEL = 'Submit feedback'
LEARN_MORE_LABEL = 'Learn more'
SEE_ADVANCED_METRICS = 'See advanced metrics'
VIEW_SUMMARY_LABEL = 'View summary'


class ShowTreeView(sublime_plugin.TextCommand):
  def run(self, edit):
    self.currentKeystrokeStats = SessionSummary()
    self.keys = []
    self.create_tree()
    sublime.active_window().show_quick_panel(self.keys, self.itemSelectionHandler)

  def create_tree(self):
    zeroDepth = ' '
    firstChildDepth = ' ' * 8
    secondChildDepth = ' ' * 16
    if not getItem('name'):
        self.keys.append('%s%s' % (zeroDepth, GOOGLE_SIGNUP_LABEL))
        self.keys.append('%s%s' % (zeroDepth, GITHBUB_SIGNUP_LABEL))
        self.keys.append('%s%s' % (zeroDepth, EMAIL_SIGNUP_LABEL))
    else:
        self.keys.append('%s%s(%s)' % (zeroDepth, "Logged in as ", getItem('name')))
        self.keys.append('%s%s' % (firstChildDepth, SWITCH_ACCOUNT_LABEL))

    statusBarMessage = HIDE_STATUS_LABEL if getValue("show_code_time_status", True) else SHOW_STATUS_LABEL
    self.keys.append('%s%s' % (zeroDepth, statusBarMessage))
    self.keys.append('%s%s' % (zeroDepth, SUBMIT_FEEDBACK_LABEL))
    self.keys.append('%s%s' % (zeroDepth, LEARN_MORE_LABEL))

    self.keys.append('-----------------------------------')
    
    self.keys.append('%s%s' % (zeroDepth, SEE_ADVANCED_METRICS))
    self.keys.append('%s%s' % (zeroDepth, VIEW_SUMMARY_LABEL))

    data = getSessionSummaryData()
    codeTimeSummary = getCodeTimeSummary()
    data.update(codeTimeSummary)

    self.keys.append('-----------------------------------')

    todayString = datetime.today().strftime('%a')
    
    # code time
    self.keys.append('%s%s' % (zeroDepth, "- Code Time"))
    editorMinutes = humanizeMinutes(data['codeTimeMinutes']).strip()
    self.keys.append('%s%s' % (firstChildDepth, 'Today: {}'.format(editorMinutes)))

    # active code time
    self.keys.append('%s%s' % (zeroDepth, "- Active Code Time"))
    activeCodeTimeMinutes = humanizeMinutes(data['activeCodeTimeMinutes']).strip()
    avgDailyMinutes = humanizeMinutes(data['averageDailyMinutes']).strip()
    globalAvgMinutes = humanizeMinutes(data['globalAverageSeconds'] / 60).strip()
    self.keys.append('%s%s' % (firstChildDepth, 'Today: {}'.format(activeCodeTimeMinutes)))
    self.keys.append('%s%s' % (firstChildDepth, 'Your average ({}): {}'.format(todayString, avgDailyMinutes)))
    self.keys.append('%s%s' % (firstChildDepth, 'Global average ({}): {}'.format(todayString, globalAvgMinutes)))

    # lines added
    self.keys.append('%s%s' % (zeroDepth, "- Lines added"))
    currLinesAdded = self.currentKeystrokeStats['currentDayLinesAdded'] + data['currentDayLinesAdded']
    linesAdded = formatNumWithK(currLinesAdded)
    avgLinesAdded = formatNumWithK(data['averageLinesAdded'])
    globalLinesAdded = formatNumWithK(data['globalAverageLinesAdded'])
    self.keys.append('%s%s' % (firstChildDepth, 'Today: {}'.format(linesAdded)))
    self.keys.append('%s%s' % (firstChildDepth, 'Your average ({}): {}'.format(todayString, avgLinesAdded)))
    self.keys.append('%s%s' % (firstChildDepth, 'Global average ({}): {}'.format(todayString, globalLinesAdded)))

    # lines removed
    self.keys.append('%s%s' % (zeroDepth, "- Lines removed"))
    currLinesRemoved = self.currentKeystrokeStats['currentDayLinesRemoved'] + data['currentDayLinesRemoved']
    linesRemoved = formatNumWithK(currLinesRemoved)
    avgLinesRemoved = formatNumWithK(data['averageLinesRemoved'])
    globalLinesRemoved = formatNumWithK(data['globalAverageLinesRemoved'])
    self.keys.append('%s%s' % (firstChildDepth, 'Today: {}'.format(linesRemoved)))
    self.keys.append('%s%s' % (firstChildDepth, 'Your average ({}): {}'.format(todayString, avgLinesRemoved)))
    self.keys.append('%s%s' % (firstChildDepth, 'Global average ({}): {}'.format(todayString, globalLinesRemoved)))

    # keystrokes
    self.keys.append('%s%s' % (zeroDepth, "- Keystrokes"))
    currKeystrokes = self.currentKeystrokeStats['currentDayKeystrokes'] + data['currentDayKeystrokes']
    keystrokes = formatNumWithK(currKeystrokes)
    avgKeystrokes = formatNumWithK(data['averageDailyKeystrokes'])
    globalKeystrokes = formatNumWithK(data['globalAverageDailyKeystrokes'])
    self.keys.append('%s%s' % (firstChildDepth, 'Today: {}'.format(keystrokes)))
    self.keys.append('%s%s' % (firstChildDepth, 'Your average ({}): {}'.format(todayString, avgKeystrokes)))
    self.keys.append('%s%s' % (firstChildDepth, 'Global average ({}): {}'.format(todayString, globalKeystrokes)))
    
    # file changed metrics
    fileChangeInfoMap = getFileChangeSummaryAsJson()
    if (fileChangeInfoMap is not None):
        self.keys.append('%s%s' % (zeroDepth, "- File changed"))
        filesChangedNode = self.buildTopFilesNode(fileChangeInfoMap)
        self.keys.append('%s%s' % (firstChildDepth, filesChangedNode))

        fileChangeInfos = fileChangeInfoMap.values()

        topKpmFileNodes = self.topFilesMetricsNode(fileChangeInfos, 'kpm', 'top-kpm-files')
        self.keys.append('%s%s' % (zeroDepth, "- Top files by KPM"))
        if topKpmFileNodes is not None:
            for node in topKpmFileNodes:
                self.keys.append('%s%s' % (firstChildDepth, node))

        topKeystrokeFileNodes = self.topFilesMetricsNode(fileChangeInfos, 'keystrokes', 'top-keystrokes-files')
        self.keys.append('%s%s' % (zeroDepth, "- Top files by keystrokes"))
        if topKeystrokeFileNodes is not None:
            for node in topKeystrokeFileNodes:
                self.keys.append('%s%s' % (firstChildDepth, node))

        topCodetimeFileNodes = self.topFilesMetricsNode(fileChangeInfos, 'duration_seconds', 'top-codetime-files')
        self.keys.append('%s%s' % (zeroDepth, "- Top files by code time"))
        if topCodetimeFileNodes is not None:
            for node in topCodetimeFileNodes:
                self.keys.append('%s%s' % (firstChildDepth, node))

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
            if (key == VIEW_SUMMARY_LABEL):
                codetimemetricsthread = Thread(target=launchCodeTimeMetrics)
                codetimemetricsthread.start()
            elif key == SWITCH_ACCOUNT_LABEL:
                self.switchAccount()
            elif (key == HIDE_STATUS_LABEL or key == SHOW_STATUS_LABEL):
                toggleStatus()
            elif key == LEARN_MORE_LABEL:
                displayReadmeIfNotExists(True)
            elif key == SEE_ADVANCED_METRICS:
                launchWebDashboardUrl()
            elif key == SUBMIT_FEEDBACK_LABEL:
                launchSubmitFeedback()
            elif key == GOOGLE_SIGNUP_LABEL:
                launchLoginUrl('google')
            elif key == GITHBUB_SIGNUP_LABEL:
                launchLoginUrl('github')
            elif key == EMAIL_SIGNUP_LABEL:
                launchLoginUrl('software')

  def switchAccount(self):
    self.keys = ['Google', 'GitHub', 'Email']
    sublime.active_window().show_quick_panel(self.keys, self.switchAccountHandler)

  def switchAccountHandler(self, idx):
    if (idx is not None and idx >= 0):
        setItem("switching_account", True);
        if (idx == 0):
            launchLoginUrl('google')
        elif (idx == 1):
            launchLoginUrl('github')
        else:
            launchLoginUrl('software')

#EOL
