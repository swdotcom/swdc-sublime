import sublime_plugin, sublime
from threading import Thread, Timer, Event
import json
import os.path
import time
import datetime
import math
import copy
from .SoftwareUtil import *
from .SoftwareFileDataManager import *
from .SoftwareModels import SessionSummary, KeystrokeAggregate
from .SoftwareWallClock import *
from .SoftwareDashboard import *

# Constants
SERVICE_NOT_AVAIL = "Our service is temporarily unavailable.\n\nPlease try again later.\n"
ONE_MINUTE_IN_SEC = 60
SECONDS_PER_HOUR = 60 * 60
DEFAULT_SESSION_THRESHOLD_SECONDS = 60 * 15
LONG_THRESHOLD_HOURS = 12
SHORT_THRESHOLD_HOURS = 4
NO_TOKEN_THRESHOLD_HOURS = 2
LOGIN_LABEL = "Log in"
NO_PROJ_NAME = 'Unnamed'


def getSummaryInfoFile():
    file = getSoftwareDir(True)
    return os.path.join(file, 'SummaryInfo.txt')

def incrementSessionSummaryData(aggregates):
    data = getSessionSummaryData()
    incrementMinutes = getMinutesSinceLastPayload()

    data['currentDayMinutes'] += incrementMinutes
    data['currentDayKeystrokes'] += aggregates['keystrokes']
    data['currentDayLinesAdded'] += aggregates['linesAdded']
    data['currentDayLinesRemoved'] += aggregates['linesRemoved']

    saveSessionSummaryToDisk(data)

    timeData = getTodayTimeDataSummary()
    timeData['file_seconds'] += 60
    fileSeconds = timeData['file_seconds']

    sessionSeconds = data['currentDayMinutes'] * 60
    updateBasedOnSessionSeconds(sessionSeconds)
    editorSeconds = getWcTimeInSeconds()

    updateTimeSummaryData(editorSeconds, sessionSeconds, fileSeconds)

def getCurrentDayTime(sessionSummaryData):
    currentDayMinutes = 0
    try:
        currentDayMinutes = int(sessionSummaryData.get("currentDayMinutes", 0))
    except Exception as ex:
        currentDayMinutes = 0
        log("Code Time: Current Day exception: %s" % ex)
    
    return {"data": currentDayMinutes, "formatted": humanizeMinutes(currentDayMinutes)}

def getAverageDailyTime(sessionSummaryData):
    averageDailyMinutes = 0
    try:
        averageDailyMinutes = int(sessionSummaryData.get("averageDailyMinutes", 0))
    except Exception as ex:
        averageDailyMinutes = 0
        log("Code Time: Average Daily Minutes exception: %s" % ex)
    
    return {"data": averageDailyMinutes, "formatted": humanizeMinutes(averageDailyMinutes)}


def getSessionThresholdSeconds():
    thresholdSeconds = getItem('sessionThresholdInSec') or DEFAULT_SESSION_THRESHOLD_SECONDS
    return thresholdSeconds

def clearSessionSummaryDataData():
    log('--- clearing session summary data ---')
    emptyData = SessionSummary()
    saveSessionSummaryToDisk(emptyData)


def setSessionSummaryLiveshareMinutes(minutes):
    data = getSessionSummaryData()
    data['liveshareMinutes'] = minutes
    saveSessionSummaryToDisk(data)

def getMinutesSinceLastPayload():
    minutesSinceLastPayload = 1
    lastPayloadEnd = getItem('latestPayloadTimestampEndUtc')
    if lastPayloadEnd is not None:
        nowTimes = getNowTimes()
        nowInSec = nowTimes['nowInSec']
        # diff from the previous end time
        diffInSec = nowInSec - lastPayloadEnd

        if diffInSec > 0 and diffInSec < getSessionThresholdSeconds():
            minutesSinceLastPayload = diffInSec / 60
    else:
        refreshSessionSummaryTimer = Timer(1.0, getSessionSummaryStatus)
        refreshSessionSummaryTimer.start()

    return minutesSinceLastPayload

# TODO: this method hangs for a while (bc no cache now?)
def launchCodeTimeMetrics():
    fetchCodeTimeMetricsDashboard()
    print('hello?')
    file = getDashboardFile()
    sublime.active_window().open_file(file)


def fetchCodeTimeMetricsDashboard():
    serverOnline = serverIsAvailable()
    summaryInfoFile = getSummaryInfoFile()

    if serverOnline:
        # fetch the backend data
        islinux = "true"
        if isWindows() is True or isMac() is True:
            islinux = "false"

        # TODO: find sublime setting for showGitMEtrics and replace true with it
        showGitMetrics = True 
        api = '/dashboard?showGit=' + 'true' + '&linux=' + islinux + '&showToday=false'
        response = requestIt("GET", api, None, getItem("jwt"))

        summaryContent = ""
        try:
            summaryContent = response.read().decode('utf-8')
        except Exception as ex:
            summaryContent = SERVICE_NOT_AVAIL
            log("Code Time: Unable to read response data: %s" % ex)

        try:
            with open(summaryInfoFile, 'w', encoding='utf-8') as f:
                f.write(summaryContent)
        except Exception as ex:
            log("Code Time: Unable to write dashboard summary content: %s" % ex)

    # concat summary info with the dashboard file
    dashboardFile = getDashboardFile()
    dashboardContent = ""

    d = datetime.datetime.now()

    formattedDate = d.strftime("%a %b %d %I:%M %p")
    dashboardContent += "CODE TIME          (Last updated on %s)\n\n" % formattedDate

    formattedTodayDate = d.strftime("%a %b %d")
    todayHeader = "Today (%s)" % formattedTodayDate
    dashboardContent += getSectionHeader(todayHeader)

    summary = getSessionSummaryStatus()
    if (summary is not None):
        averageTime = getAverageDailyTime(summary)["formatted"]
        hoursCodedToday = getCurrentDayTime(summary)["formatted"]

        liveshareTime = None 
        if summary['liveshareMinutes']:
            liveshareTime = humanizeMinutes(summary['liveshareMinutes'])

        currentEditorMinutesStr = getHumanizedWcTime()
        dashboardContent += getDashboardRow('Editor time today', currentEditorMinutesStr)
        dashboardContent += getDashboardRow("Code time today", hoursCodedToday)
        dashboardContent += getDashboardRow("90-day avg", averageTime)
        if liveshareTime:
            dashboardContent += getDashboardRow('Live Share', liveshareTime)
        dashboardContent += "\n"

    if (os.path.exists(summaryInfoFile)):
        try:
            with open(summaryInfoFile, 'r', encoding="utf-8") as summaryInfoFileContent:
                dashboardContent += summaryInfoFileContent.read()
        except Exception as ex:
            log("Code Time: Unable to read summary info file content: %s" % ex)

    try:
        with open(dashboardFile, 'w', encoding='utf-8') as f:
            f.write(dashboardContent)
    except Exception as ex:
        log("Code Time: Unable to write local dashboard content: %s" % ex)

# store the payload offline...
def storePayload(payload):

    fileChangeInfoMap = getFileChangeSummaryAsJson()
    aggregate = KeystrokeAggregate()
    print(payload)

    if payload['project']:
        aggregate['directory'] = payload['project']['directory'] or NO_PROJ_NAME
    else:
        aggregate['directory'] = NO_PROJ_NAME
    
    for key in payload['source'].keys():
        fileInfo = payload['source'][key]
        baseName = os.path.basename(key)

        fileInfo['name'] = baseName
        fileInfo['fsPath'] = key
        fileInfo['projectDir'] = payload['project']['directory']
        fileInfo['duration_seconds'] = fileInfo['end'] - fileInfo['start']

        aggregate['add'] += fileInfo['add']
        aggregate['close'] += fileInfo['close']
        aggregate['delete'] += fileInfo['delete']
        aggregate['keystrokes'] += fileInfo['keystrokes']
        aggregate['linesAdded'] += fileInfo['linesAdded']
        aggregate['linesRemoved'] += fileInfo['linesRemoved']
        aggregate['open'] += fileInfo['open']
        aggregate['paste'] += fileInfo['paste']

        existingFileInfo = fileChangeInfoMap.get(key)
        if existingFileInfo is None:
            fileInfo['update_count'] = 1
            fileInfo['kpm'] = aggregate['keystrokes']
            fileChangeInfoMap[key] = fileInfo
        else:
            existingFileInfo['update_count'] += 1
            existingFileInfo['keystrokes'] += fileInfo['keystrokes']
            existingFileInfo['kpm'] = existingFileInfo['keystrokes'] / existingFileInfo['update_count']
            existingFileInfo['add'] += fileInfo['add']
            existingFileInfo['close'] += fileInfo['close']
            existingFileInfo['delete'] += fileInfo['delete']
            existingFileInfo['keystrokes'] += fileInfo['keystrokes']
            existingFileInfo['linesAdded'] += fileInfo['linesAdded']
            existingFileInfo['linesRemoved'] += fileInfo['linesRemoved']
            existingFileInfo['open'] += fileInfo['open']
            existingFileInfo['paste'] += fileInfo['paste']
            existingFileInfo['duration_seconds'] += fileInfo['duration_seconds']

            # non aggregates, just set
            existingFileInfo['lines'] = fileInfo['lines']
            existingFileInfo['length'] = fileInfo['length']


    incrementSessionSummaryData(aggregate)

    # push the stats to the file so other editor windows can have it
    saveFileChangeInfoToDisk(fileChangeInfoMap)

    # refresh tree
    refreshTreeTimer = Timer(1.0, refreshTreeView)
    refreshTreeTimer.start()

    # get the datastore file to save the payload
    dataStoreFile = getSoftwareDataStoreFile()

    log("Code Time: storing kpm metrics: %s" % payload)

    try:
        with open(dataStoreFile, "a") as dsFile:
            dsFile.write(json.dumps(payload) + "\n")
    except Exception as ex:
        log('Error appending to the Software data store file: %s' % ex)

# send the data that has been saved offline
def sendOfflineData():
    batchSendData('/data/batch', getSoftwareDataStoreFile())

def sendOfflineEvents():
    batchSendData('/data/event', getPluginEventsFile())

def sendOfflineTimeData():
    batchSendData('/data/time', getTimeDataSummaryFile(), isArray=True)


def batchSendData(api, file, isArray=False):
    isOnline = serverIsAvailable()
    if not isOnline:
        return 

    try:
        # print('batch sending {}'.format(file))
        if os.path.exists(file):
            payloads = None 
            if isArray:
                payloads = getFileDataArray(file)
            else:
                payloads = getFileDataPayloadsAsJson(file)
            batchSendPayloadData(api, file, payloads)
    except Exception as ex:
        log('Error batch sending payloads: %s' % ex)

            

def batchSendPayloadData(api, file, payloads):
    if (payloads is not None and len(payloads) > 0):
        log('sending batch payloads')

        # go through the payloads array 50 at a time
        batch = []
        length = len(payloads)
        for i in range(length):
            payload = payloads[i]
            if (len(batch) >= 50):
                requestIt("POST", "/data/batch", json.dumps(batch), getItem("jwt"))
                # send batch
                batch = []
            batch.append(payload)

        # send remaining batch
        if (len(batch) > 0):
            requestIt("POST", "/data/batch", json.dumps(batch), getItem("jwt"))
        
        os.remove(file)



def showLoginPrompt():
    serverAvailable = serverIsAvailable()

    if (serverAvailable):
        # set the last update time so we don't try to ask too frequently
        infoMsg = "To see your coding data in Code Time, please log in to your account."
        clickAction = sublime.ok_cancel_dialog(infoMsg, LOGIN_LABEL)
        if (clickAction):
            # launch the login view
            launchLoginUrl()


