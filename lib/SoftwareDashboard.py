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

currentDay = None 
DAY_CHECK_TIMER_INTERVAL = 60

def dashboardMgrInit():
    global currentDay
    if currentDay is not None:
        return 
    
    currentDay = getItem('currentDay')
    setInterval(lambda: newDayChecker(True), DAY_CHECK_TIMER_INTERVAL)


def newDayChecker(isInit=False):
    # print('in new day checker')
    global currentDay
    nowTime = getNowTimes()
    if nowTime['day'] != currentDay:
        # Send offline data we have
        sendOfflineData()
        sendOfflineTimeData()

        # Clear all data
        clearWcTime()
        clearSessionSummaryData()
        clearTimeDataSummary()
        clearFileChangeInfoSummaryData()

        currentDay = nowTime['day']

        setItem('currentDay', currentDay)
        setItem('latestPayloadTimestampEndUtc', 0)

        print('Updating session summary from server')
        updateSessionSummaryFromServer()
        refreshTreeView()
        # refreshSessionSummaryTimer = Timer(60.0, updateSessionSummaryFromServer)
        # refreshSessionSummaryTimer.start()

    elif isInit:
        refreshTreeView()


# TODO: add updateSessionSummaryFromServer as per https://github.com/swdotcom/swdc-atom/commit/26f6e6c9d2ef637580f71cc3d54cbcf99ffc6d66
def updateSessionSummaryFromServer():
    jwt = getItem('jwt')
    response = requestIt("GET", '/sessions/summary', None, jwt)
    if response is not None and isResponseOk(response):
        respData = json.loads(response.read().decode('utf-8'))
        summary = getSessionSummaryData()
        updateCurrents = summary['currentDayMinutes'] < respData['currentDayMinutes']

        for item in respData.items():
            key = item[0]
            val = item[1]

            if updateCurrents and key.startswith('current'):
                summary[key] = val 
            elif not key.startswith('current'):
                summary[key] = val

        log('summary data: {}'.format(summary))
        saveSessionSummaryToDisk(summary)



def getDashboardFile():
    file = getSoftwareDir(True)
    return os.path.join(file, 'CodeTime.txt')

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

    d = datetime.datetime.now()

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

# Fetch and display the daily KPM info
#TODO: remove per https://github.com/swdotcom/swdc-atom/commit/eb7a659cbee1590e21f40206bfd318b7bde8728d
# def getSessionSummaryStatus():
#     summary = getSessionSummaryFileAsJson()
#     jwt = getItem('jwt')
#     serverOnline = serverIsAvailable()

#     if serverOnline and jwt is not None:
#         response = requestIt("GET", '/sessions/summary', None, jwt)
#         if response is not None and isResponseOk(response):
#             respData = json.loads(response.read().decode('utf-8'))

#             dataMinutes = respData['currentDayMinutes']

#             if dataMinutes == 0 or dataMinutes < summary['currentDayMinutes']:
#                 log('syncing current day minutesSinceLastPayload')
#                 respData['currentDayMinutes'] = summary['currentDayMinutes']
#                 respData['currentDayKeystrokes'] = summary['currentDayKeystrokes']
#                 respData['currentDayKpm'] = summary['currentDayKpm']
#                 respData['currentDayLinesAdded'] = summary['currentDayLinesAdded']
#                 respData['currentDayLinesRemoved'] = summary['currentDayLinesRemoved']

#                 # Everything is synced up now, save to disk
#                 summary = copy.deepcopy(respData)
#                 saveSessionSummaryToDisk(summary)

#                 currentTs = getItem('latestPayloadTimestampEndUtc')
#                 if currentTs is None or summary['latestPayloadTimestampEndUtc'] > currentTs:
#                     setItem('latestPayloadTimestampEndUtc', summary['latestPayloadTimestampEndUtc'])
#         else:
#             log('Unable to get session summary response')

#     sessionSeconds = summary['currentDayMinutes'] * 60
#     updateBasedOnSessionSeconds(sessionSeconds)
#     return summary 
