import sublime_plugin, sublime
from threading import Thread, Timer, Event
import json
import os.path
import time
import datetime
import math
from .SoftwareUtil import *

# Constants
sessionSummaryData = None
lastDayOfMonth = 0
SERVICE_NOT_AVAIL = "Our service is temporarily unavailable.\n\nPlease try again later.\n"
ONE_MINUTE_IN_SEC = 60
SECONDS_PER_HOUR = 60 * 60
LONG_THRESHOLD_HOURS = 12
SHORT_THRESHOLD_HOURS = 4
NO_TOKEN_THRESHOLD_HOURS = 2
LOGIN_LABEL = "Log in"

# init the session summary data
def initSessionSumaryData():
    global sessionSummaryData
    sessionSummaryData = {
        "currentDayMinutes": 0,
        "averageDailyMinutes": 0,
        "averageDailyKeystrokes": 0,
        "currentDayKeystrokes": 0,
        "liveshareMinutes": None
    }

# get the session summary data
def getSessionSummaryData():
    global sessionSummaryData
    if (sessionSummaryData is None):
        sessionSummaryData = getSessionSummaryFileAsJson()
    return sessionSummaryData

# get the session summary file
def getSessionSummaryFile():
    file = getSoftwareDir(True)
    return os.path.join(file, 'sessionSummary.json')

def getSummaryInfoFile():
    file = getSoftwareDir(True)
    return os.path.join(file, 'SummaryInfo.txt')

def incrementSessionSummaryData(minutes, keystrokes):
    global sessionSummaryData
    if (sessionSummaryData is None):
        sessionSummaryData = getSessionSummaryFileAsJson()
    sessionSummaryData["currentDayMinutes"] += minutes
    sessionSummaryData["currentDayKeystrokes"] += keystrokes

#
def updateStatusBarWithSummaryData():
    global sessionSummaryData
    sessionSummaryData = getSessionSummaryFileAsJson()

    currentDayInfo = getCurrentDayTime(sessionSummaryData)
    averageDailyInfo = getAverageDailyTime(sessionSummaryData)

    inFlowIcon = ""
    if (currentDayInfo.get("data", 0) > averageDailyInfo.get("data", 0)):
        inFlowIcon = "🚀"

    statusMsg = inFlowIcon + "" + currentDayInfo["formatted"]
    if (averageDailyInfo.get("data", 0) > 0):
        statusMsg += " | " + averageDailyInfo["formatted"]

    showStatus(statusMsg)

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


def saveSessionSummaryToDisk(sessionSummaryData):
    content = json.dumps(sessionSummaryData)

    sessionFile = getSessionSummaryFile()
    with open(sessionFile, 'w') as f:
        f.write(content)

#
def getSessionSummaryFileAsJson():
    global sessionSummaryData
    try:
        with open(getSessionSummaryFile()) as sessionSummaryFile:
            sessionSummaryData = json.load(sessionSummaryFile)
    except Exception as ex:
        initSessionSumaryData()
        log("Code Time: Session summary file fetch error: %s" % ex)
    return sessionSummaryData

def launchCodeTimeMetrics():
    global sessionSummaryData
    online = getValue("online", True)
    sessionSummaryData = getSessionSummaryData()
    if (sessionSummaryData.get("currentDayMinutes", 0) == 0):
        if (online):
            result = fetchDailyKpmSessionInfo(True)
            sessionSummaryData = result["data"]
        else:
            log("Code Time: Connection error, using cached dashboard results")
            result = fetchDailyKpmSessionInfo(False)
            sessionSummaryData = result["data"]

    fetchCodeTimeMetricsDashboard(sessionSummaryData)
    file = getDashboardFile()
    sublime.active_window().open_file(file)

def fetchCodeTimeMetricsDashboard(summary):
    global sessionSummaryData
    global lastDayOfMonth

    summaryInfoFile = getSummaryInfoFile()

    dayOfMonth = datetime.datetime.today().day

    if (lastDayOfMonth == 0 or dayOfMonth != lastDayOfMonth):
        lastDayOfMonth = dayOfMonth

        # fetch the backend data
        islinux = "true"
        if isWindows() is True or isMac() is True:
            islinux = "false"
        api = '/dashboard?linux=' + islinux + '&showToday=false'
        response = requestIt("GET", api, None, getItem("jwt"))

        summaryContent = ""
        try:
            summaryContent = response.read().decode('utf-8')
        except Exception as ex:
            summaryContent = SERVICE_NOT_AVAIL
            log("Code Time: Unable to read response data: %s" % ex)

        # save the 
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

    if (summary is not None):
        hoursCodedToday = getCurrentDayTime(sessionSummaryData)["formatted"]
        averageTime = getCurrentDayTime(sessionSummaryData)["formatted"]
        dashboardContent += getDashboardRow("Hours coded today", hoursCodedToday)
        dashboardContent += getDashboardRow("90-day avg", averageTime)
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

#
# Fetch and display the daily KPM info
#
def fetchDailyKpmSessionInfo(forceRefresh):
    sessionSummaryData = getSessionSummaryFileAsJson()
    currentDayMinutes = sessionSummaryData.get("currentDayMinutes", 0)
    if (currentDayMinutes == 0 or forceRefresh is True):
        online = getValue("online", True)
        if (online is False):
            # update the status bar with offline data
            updateStatusBarWithSummaryData()
            return { "data": sessionSummaryData, "status": "CONN_ERR" }

        # api to fetch the session kpm info
        api = '/sessions/summary'
        response = requestIt("GET", api, None, getItem("jwt"))

        if (response is not None and isResponsOk(response)):
            sessionSummaryData = json.loads(response.read().decode('utf-8'))

            # update the file
            saveSessionSummaryToDisk(sessionSummaryData)

            # update the status bar
            updateStatusBarWithSummaryData()

            # stitch the dashboard together
            fetchCodeTimeMetricsDashboard(sessionSummaryData)

            return { "data": sessionSummaryData, "status": "OK" }
    else:
        # update the status bar with offline data
        updateStatusBarWithSummaryData()
        return { "data": sessionSummaryData, "status": "OK" }

# store the payload offline...
def storePayload(payload):

    # calculate it and call add to the minutes
    # convert it to json
    payloadData = json.loads(payload)

    keystrokes = payloadData.get("keystrokes", 0)

    incrementSessionSummaryData(1, keystrokes)

    # push the stats to the file so other editor windows can have it
    saveSessionSummaryToDisk(getSessionSummaryData())

    # update the statusbar
    fetchDailyKpmSessionInfo(False)

    # get the datastore file to save the payload
    dataStoreFile = getSoftwareDataStoreFile()

    log("Code Time: storing kpm metrics: %s" % payload)

    with open(dataStoreFile, "a") as dsFile:
        dsFile.write(payload + "\n")

# send the data that has been saved offline
def sendOfflineData():
    existingJwt = getItem("jwt")

    # no need to try to send the offline data if we don't have an auth token
    if (existingJwt is None):
        return

    serverAvailable = checkOnline()
    if (serverAvailable):
        # send the offline data
        dataStoreFile = getSoftwareDataStoreFile()

        if (os.path.exists(dataStoreFile)):
            payloads = []

            try:
                with open(dataStoreFile) as fp:
                    for line in fp:
                        if (line and line.strip()):
                            line = line.rstrip()
                            # convert to object
                            json_obj = json.loads(line)
                            # convert to json to send
                            payloads.append(json_obj)
            except Exception:
                log("Unable to read offline data file %s" % dataStoreFile)

            if (payloads):
                os.remove(dataStoreFile)

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

    # update the statusbar
    fetchDailyKpmSessionInfo(True)

    # send the next batch in 30 minutes
    sendOfflineDataTimer = Timer(60 * 30, sendOfflineData)
    sendOfflineDataTimer.start()

def showLoginPrompt():
    serverAvailable = checkOnline()

    if (serverAvailable):
        # set the last update time so we don't try to ask too frequently
        infoMsg = "To see your coding data in Code Time, please log in to your account."
        clickAction = sublime.ok_cancel_dialog(infoMsg, LOGIN_LABEL)
        if (clickAction):
            # launch the login view
            launchLoginUrl()


