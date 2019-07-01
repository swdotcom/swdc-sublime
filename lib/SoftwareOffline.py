import sublime_plugin, sublime
import json
import os.path
from .SoftwareUtil import *

sessionSummaryData = None
lastDashboardFetchTime = 0
SERVICE_NOT_AVAIL = "Our service is temporarily unavailable.\n\nPlease try again later.\n"

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
        print("Code Time: Current Day exception: %s" % ex)
    
    return {"data": currentDayMinutes, "formatted": humanizeMinutes(currentDayMinutes)}

def getAverageDailyTime(sessionSummaryData):
    averageDailyMinutes = 0
    try:
        averageDailyMinutes = int(sessionSummaryData.get("averageDailyMinutes", 0))
    except Exception as ex:
        averageDailyMinutes = 0
        print("Code Time: Average Daily Minutes exception: %s" % ex)
    
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
    global lastDashboardFetchTime

    summaryInfoFile = getSummaryInfoFile()

    now = round(time.time()) - 60
    diff = now - lastDashboardFetchTime
    day_in_sec = 60 * 60 * 24
    if (lastDashboardFetchTime == 0 or diff >= day_in_sec):
        lastDashboardFetchTime = now

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
    formattedDate = d.strftime("%a, %b %-d %-I:%M%p")
    dashboardContent += "CODE TIME          (Last updated on %s)\n\n" % formattedDate

    formattedTodayDate = d.strftime("%a, %b %-d")
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
            with open(summaryInfoFile) as summaryInfoFileContent:
                dashboardContent += summaryInfoFileContent
        except Exception as ex:
            log("Code Time: Unable to read summary info file content: %s" % ex)

    try:
        with open(dashboardFile, 'w', encoding='utf-8') as f:
            f.write(dashboardContent)
    except Exception as ex:
        log("Code Time: Unable to write local dashboard content: %s" % ex)


