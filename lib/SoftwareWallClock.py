import sublime, sublime_plugin
from .SoftwareUtil import *
from .SoftwareOffline import *
from .SoftwareStatusManager import *

SECONDS_INCREMENT = 30

_wctime = 0

def wallClockMgrInit():
    global _wctime
    _wctime = getItem('wctime') or 0
    setInterval(updateTimeWrapper, SECONDS_INCREMENT)
    log('------- Intializing Wallclock ----------')
    updateStatusBarWithSummaryData()


def updateTimeWrapper():
    if isFocused():
        updateWcTime()
    dispatchStatusViewUpdate()


def updateWcTime():
    global _wctime
    _wctime = getItem('wctime') or 0
    _wctime += SECONDS_INCREMENT
    setItem('wctime', _wctime)
    updateTimeData(SECONDS_INCREMENT)

def dispatchStatusViewUpdate():
    updateStatusBarWithSummaryData()
    refreshTreeView()

def clearWcTime():
    setWcTime(0)

def getHumanizedWcTime():
    global _wctime
    return humanizeMinutes(_wctime / 60).strip()

def getWcTimeInSeconds():
    global _wctime
    return _wctime

def setWcTime(seconds):
    setItem('wctime', seconds)
    updateWcTime()

def updateTimeData(seconds):
    global _wctime
    updateEditorSeconds(seconds)

def updateBasedOnSessionSeconds(session_seconds):
    editor_seconds = getWcTimeInSeconds()

    if editor_seconds < session_seconds:
        editor_seconds = session_seconds + 1
        setWcTime(editor_seconds)

    updateStatusBarWithSummaryData()