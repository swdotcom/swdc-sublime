import sublime
import os
from .SoftwareUtil import *
from .SoftwareFileDataManager import *
from .SoftwareHttp import *
from .SoftwareWallClock import *
from .SoftwareOffline import *
from .CommonUtil import *
from .Logger import *

DAY_CHECK_TIMER_INTERVAL = 60 * 5

in_flow = False

def sessionSummaryInit():
    # fetch flow sessions and current day stats every 5 minutes
    setInterval(lambda: updateSessionSummaryFromServer(), DAY_CHECK_TIMER_INTERVAL)

def inFlow():
    global in_flow
    return in_flow

def enableFlowMode():
    global in_flow
    in_flow = True if len(getFlowSessions()) > 0 else False

    jwt = getItem('jwt')
    if in_flow is False:
        params = {
            'automated': False
        }
        requestIt('POST', '/v1/flow_sessions', json.dumps(params), jwt)
        in_flow = True
        updateStatusBarWithSummaryData()

def exitFlowMode():
    global in_flow

    requestIt("DELETE", '/v1/flow_sessions', None, getItem('jwt'))
    in_flow = False
    updateStatusBarWithSummaryData()

def updateSessionSummaryFromServerAsync():
    setInterval(lambda: updateSessionSummaryFromServer(), 1)

def updateSessionSummaryFromServer():
    global in_flow
    jwt = getItem('jwt')

    if jwt is None:
        return
    
    response = requestIt("GET", '/sessions/summary', None, jwt)
    if response is not None and isResponseOk(response):
        # summary data: {'currentDayMinutes': 86, 'averageDailyMinutes': 230}
        respData = json.loads(response.read().decode('utf-8'))

        saveSessionSummaryToDisk(respData)

    in_flow = True if len(getFlowSessions()) > 0 else False

    updateStatusBarWithSummaryData()

def getFlowSessions():
    response = requestIt('GET', '/v1/flow_sessions', None, getItem('jwt'))
    if response is not None and isResponseOk(response):
        # flow sessions: {'flow_sessions': []}
        respData = json.loads(response.read().decode('utf-8'))
        
        return respData.get('flow_sessions')

    return []

def updateStatusBarWithSummaryData():
    sessionSummaryData = getSessionSummaryFileAsJson()

    currentDayMinutes = int(sessionSummaryData.get("currentDayMinutes", 0))
    averageDailyMinutes = int(sessionSummaryData.get("averageDailyMinutes", 0))

    timeIcon = "🕒"
    if (currentDayMinutes > averageDailyMinutes):
        timeIcon = "🚀"

    currentDayMinStr = humanizeMinutes(currentDayMinutes)

    inFlowMsg = "  ○ Flow"
    if inFlow():
        inFlowMsg = "  ⚪ Flow"

    statusMsg = timeIcon + " " + currentDayMinStr + inFlowMsg

    showStatus(statusMsg)
