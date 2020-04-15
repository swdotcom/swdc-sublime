import sublime, sublime_plugin
import json 
import copy
import os 
from threading import Timer 
from .SoftwareUtil import *
from .SoftwareOffline import *
from .SoftwareHttp import *
from .SoftwareWallClock import *
from .SoftwareFileChangeInfoSummaryData import *
from .SoftwarePayload import *
from .TimeSummaryData import *

currentDay = None 
DAY_CHECK_TIMER_INTERVAL = 60

def dashboardMgrInit():
    global currentDay
    if currentDay is not None:
        return 
    
    currentDay = getItem('currentDay')
    setInterval(lambda: newDayChecker(False), DAY_CHECK_TIMER_INTERVAL)

    newDayTimer = Timer(1, newDayChecker, args=[True])
    newDayTimer.start()

def newDayChecker(isInit=False):
    global currentDay
    nowTime = getNowTimes()
    if nowTime['day'] != currentDay:
        clearSessionSummaryData()
        # Send offline data we have
        sendOfflineData(True)
        sendOfflineTimeData()

        # Clear all data
        clearWcTime()
        clearTimeDataSummary()
        clearFileChangeInfoSummaryData()

        currentDay = nowTime['day']

        setItem('currentDay', currentDay)
        setItem('latestPayloadTimestampEndUtc', 0)

        refreshTreeView()
    elif isInit:
        refreshTreeView()

def launchCodeTimeMetrics():
    fetchCodeTimeMetricsDashboard()
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

    d = datetime.now()

    formattedDate = d.strftime("%a %b %d %I:%M %p")
    dashboardContent += "CODE TIME          (Last updated on %s)\n\n" % formattedDate

    formattedTodayDate = d.strftime("%a %b %d")
    todayHeader = "Today (%s)" % formattedTodayDate
    dashboardContent += getSectionHeader(todayHeader)

    # summary = getSessionSummaryStatus()
    summary = getSessionSummaryData()
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
