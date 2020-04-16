import sublime_plugin, sublime
import copy
from .SoftwareUtil import *
from .SoftwareModels import CodeTimeSummary, TimeData

def saveTimeDataSummaryToDisk(data):
    if not data:
        return 

    # write new payloads to disk
    file = getTimeDataSummaryFile()

    payloads = getFileDataArray(file)
    index = -1
    if len(payloads) > 0:
        for i in range(len(payloads)):
            if payloads[i]['day'] == data['day'] and payloads[i]['project']['directory'] == data['project']['directory']:
                index = i
                break

        if index != -1:
            payloads[index] = data 
        else:
            payloads.append(data) 
    else:
        payloads = [data]
    
    try:
        with open(file, 'w') as f:
            json.dump(payloads, f, indent=4)
        log('Code time: updated time summary data to disk')
    except Exception as ex:
        log('Code time: Error writing time summary data:%s' % ex)

    # refresh the tree view with new data
    refreshTreeView()

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

def getNewTimeDataSummary(project):
    endDayTimes = getEndDayTimes()

    timeData = TimeData()
    timeData['day'] = endDayTimes['day']
    timeData['project'] = project 
    timeData['timestamp_local'] = endDayTimes['localEndOfDay']
    timeData['timestamp'] = endDayTimes['utcEndOfDay']
    return timeData

def findTimeDataSummary(project):
    if not project or not project['directory']:
        return None
    
    endDayTimes = getEndDayTimes()
    day = endDayTimes['day']

    timeData = None
    file = getTimeDataSummaryFile()
    payloads = getFileDataArray(file)
    if len(payloads) > 0:
        try:
            # same day and same project directory
            timeData = next(load for load in payloads if load['day'] == day and load['project']['directory'] == project['directory'])
        except Exception:
            pass
    return timeData


def getTodayTimeDataSummary(project):
    timeData = findTimeDataSummary(project)
    # not found, create one since we passed the non-null project and dir
    if not timeData:
        timeData = getNewTimeDataSummary(project)
        saveTimeDataSummaryToDisk(timeData)  
    return timeData


def incrementEditorSeconds(editor_seconds):
    activeProject = getActiveProject()

    timeData = getTodayTimeDataSummary(activeProject)
    if timeData:
        timeData['editor_seconds'] += editor_seconds
        # ensure that session seconds never exceeds editor seconds
        timeData['editor_seconds'] = max(timeData['editor_seconds'], timeData['session_seconds'])
        saveTimeDataSummaryToDisk(timeData)

def getCurrentTimeSummaryProject(project):
    if not project:
        project = copy.deepcopy(getActiveProject())
    
    if project['directory']:
        resource = getResourceInfo(project['directory'])
        if resource:
            project['resource'] = resource 
            project['identifier'] = resource['identifier']
    else:
        project['directory'] = NO_PROJ_NAME
        project['name'] = UNTITLED

    return project

def clearTimeDataSummary():
    payloads = []
    summaryFile = getTimeDataSummaryFile()
    content = json.dumps(payloads, indent=4)

    with open(summaryFile, 'w') as f:
        f.write(content)

def incrementSessionAndFileSeconds(project):
    minutes_since_payload = getMinutesSinceLastPayload()
    timeData = getTodayTimeDataSummary(project)

    if minutes_since_payload > 0:
        session_seconds = minutes_since_payload * 60
        timeData['session_seconds'] += session_seconds

    timeData['editor_seconds'] = max(timeData['editor_seconds'], timeData['session_seconds'])
    timeData['file_seconds'] += 60
    timeData['file_seconds'] = min(timeData['file_seconds'], timeData['session_seconds'])

    saveTimeDataSummaryToDisk(timeData)
	