import sublime, sublime_plugin
from .SoftwareUtil import *
from .SoftwareOffline import *
from .SoftwareSessionApp import *
from .KpmManager import *
from .CommonUtil import *

SECONDS_INCREMENT = 30

_wctime = 0
isFocused = True

def wallClockMgrInit():
    global _wctime
    _wctime = getItem('wctime') or 0
    setInterval(updateTimeWrapper, SECONDS_INCREMENT)

def updateTimeWrapper():
    hasData = PluginData.hasKeystrokeData()
    if isFocused or hasData:
        updateWcTime()
    dispatchStatusViewUpdate()

def updateWcTime():
    global _wctime
    _wctime = getItem('wctime') or 0
    _wctime += SECONDS_INCREMENT
    setItem('wctime', _wctime)

def dispatchStatusViewUpdate():
    updateStatusBarWithSummaryData()

def clearWcTime():
    setWcTime(0)

def getWcTimeInSeconds():
    global _wctime
    return _wctime

def setWcTime(seconds):
    setItem('wctime', seconds)
    updateWcTime()

def focusWindow():
    global isFocused
    isFocused = True

def blurWindow():
    global isFocused
    isFocused = False

def isFocused():
    global isFocused
    return isFocused
