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
DAY_CHECK_TIMER_INTERVAL = 1000 * 60

def dashboardMgrInit():
    global currentDay
    if currentDay is not None:
        return 
    
    currentDay = getItem('currentDay')
    setInterval(lambda _: newDayChecker(True), DAY_CHECK_TIMER_INTERVAL)
    getSessionSummaryStatus()


def newDayChecker(isInit=False):
    global currentDay
    pass 
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

        refreshTreeView()
        # Get summary status in a minute
        refreshSessionSummaryTimer = Timer(60.0, getSessionSummaryStatus)
        refreshSessionSummaryTimer.start()

    elif isInit:
        refreshTreeView()


# TODO: add updateSessionSummaryFromServer as per https://github.com/swdotcom/swdc-atom/commit/26f6e6c9d2ef637580f71cc3d54cbcf99ffc6d66


# Fetch and display the daily KPM info
#TODO: remove per https://github.com/swdotcom/swdc-atom/commit/eb7a659cbee1590e21f40206bfd318b7bde8728d
def getSessionSummaryStatus():
    summary = getSessionSummaryFileAsJson()
    jwt = getItem('jwt')
    serverOnline = serverIsAvailable()

    if serverOnline and jwt is not None:
        response = requestIt("GET", '/sessions/summary', None, jwt)
        if response is not None and isResponseOk(response):
            respData = json.loads(response.read().decode('utf-8'))

            dataMinutes = respData['currentDayMinutes']

            if dataMinutes == 0 or dataMinutes < summary['currentDayMinutes']:
                log('syncing current day minutesSinceLastPayload')
                respData['currentDayMinutes'] = summary['currentDayMinutes']
                respData['currentDayKeystrokes'] = summary['currentDayKeystrokes']
                respData['currentDayKpm'] = summary['currentDayKpm']
                respData['currentDayLinesAdded'] = summary['currentDayLinesAdded']
                respData['currentDayLinesRemoved'] = summary['currentDayLinesRemoved']

                # Everything is synced up now, save to disk
                summary = copy.deepcopy(respData)
                saveSessionSummaryToDisk(summary)

                currentTs = getItem('latestPayloadTimestampEndUtc')
                if currentTs is None or summary['latestPayloadTimestampEndUtc'] > currentTs:
                    setItem('latestPayloadTimestampEndUtc', summary['latestPayloadTimestampEndUtc'])
        else:
            log('Unable to get session summary response')

    sessionSeconds = summary['currentDayMinutes'] * 60
    updateBasedOnSessionSeconds(sessionSeconds)
    return summary 


def getDashboardFile():
    file = getSoftwareDir(True)
    return os.path.join(file, 'CodeTime.txt')
