import sublime_plugin, sublime
from .SoftwareUtil import *
from .SoftwareModels import CodeTimeSummary

def getCodeTimeSummary():
    summary = CodeTimeSummary()
    day = getEndDayTimes()['day']

    summaryFile = getTimeDataSummaryFile()
    payloads = getFileDataArray(summaryFile)
    filteredPayloads = list(filter(lambda x: x['day'] == day, payloads))

    if filteredPayloads and len(filteredPayloads) > 0:
        for payload in filteredPayloads:
            summary['activeCodeTimeMinutes'] += payload['session_seconds'] / 60
            summary['codeTimeMinutes'] += payload['editor_seconds'] / 60
            summary['fileTimeMinutes'] += payload['file_seconds'] / 60 
    
    return summary 
	