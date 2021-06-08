from .SoftwareUtil import *
from .SoftwareHttp import *
from .SoftwareFileDataManager import *
from .TimeSummaryData import *

def updateStatusBarWithSummaryData():
    codeTimeSummary = getCodeTimeSummary()
    sessionSummaryData = getSessionSummaryFileAsJson()

    currentDayMinutes = int(codeTimeSummary.get("activeCodeTimeMinutes", 0))
    averageDailyMinutes = int(sessionSummaryData.get("averageDailyMinutes", 0))

    inFlowIcon = "🕒"
    if (currentDayMinutes > averageDailyMinutes):
        inFlowIcon = "🚀"

    currentDayMinStr = humanizeMinutes(currentDayMinutes)
    statusMsg = inFlowIcon + " " + currentDayMinStr

    showStatus(statusMsg)
