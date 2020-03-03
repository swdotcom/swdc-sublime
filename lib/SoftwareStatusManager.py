from .SoftwareUtil import *
from .SoftwareHttp import *
from .SoftwareFileDataManager import *


def updateStatusBar():
    sessionSummaryData = getSessionSummaryFileAsJson()

    currentDayMinStr = humanizeMinutes(int(sessionSummaryData.get('currentDayMinutes', 0)))
    averageMinStr = humanizeMinutes(int(sessionSummaryData.get('averageDailyMinutes', 0)))

    inFlowIcon = ""
    if (sessionSummaryData.get("currentDayMinutes", 0) > sessionSummaryData.get("averageDailyMinutes", 0)):
        inFlowIcon = "🚀"

    statusMsg = inFlowIcon + "" + currentDayMinStr
    if (sessionSummaryData.get("averageDailyMinutes", 0) > 0):
        statusMsg += " | " + averageMinStr

    showStatus(statusMsg)
