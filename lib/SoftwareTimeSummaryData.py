from .SoftwareUtil import *
from .SoftwareModels import TimeData, Project 
from datetime import *
import math 

def clearTimeDataSummary():
    data = TimeData()
    saveTimeDataSummaryToDisk(data)

def getNewTimeDataSummary():
    endDayTimes = getEndOfDayTimes()
    project = getCurrentTimeSummaryProject()

    timeData = TimeData()
    timeData['day'] = endDayTimes['day']
    timeData['project'] = project 
    timeData['timestamp_local'] = endDayTimes['localEndOfDay']
    timeData['timestamp'] = endDayTimes['utcEndOfDay']
    return timeData 

def getCurrentTimeSummaryProject():
    project = Project()
    projectNameAndDir = getProjectNameAndDirectory()

    if projectNameAndDir['directory']:
        project['directory'] = projectNameAndDir['directory']
        project['name'] = projectNameAndDir['name']

        resource = getResourceInfo(projectNameAndDir['directory'])
        if resource:
            project['resource'] = resource 
            project['identifier'] = resource['identifier']
    else:
        project['directory'] = 'Unnamed'
        project['name'] = 'Untitled'

    return project 

def updateEditorSeconds(editor_seconds):
    timeData = getTodayTimeDataSummary()
    timeData['editor_seconds'] += editor_seconds
    saveTimeDataSummaryToDisk(timeData)

def updateTimeSummaryData(editor_seconds, session_seconds, file_seconds):
    nowTimes = getNowTimes()
    utcEndOfDay = endOfDayUnix(nowTimes['nowInSec'])
    localEndOfDay = endOfDayUnix(nowTimes['localNowInSec'])

    timeData = getTodayTimeDataSummary()
    timeData['editor_seconds'] = editor_seconds
    timeData['session_seconds'] = session_seconds
    timeData['file_seconds'] = file_seconds
    timeData['timestamp'] = utcEndOfDay
    timeData['timestamp_local'] = localEndOfDay
    timeData['day'] = nowTimes['day']

    saveTimeDataSummaryToDisk(timeData)

def incrementSessionAndFileSeconds(minutes_since_payload):
    timeData = getTodayTimeDataSummary()
    sessionSeconds = minutes_since_payload * 60
    timeData['session_seconds'] += sessionSeconds
    timeData['file_seconds'] += 60

    saveTimeDataSummaryToDisk(timeData)

def getTodayTimeDataSummary():
    endOfDayTimes = getEndOfDayTimes()
    day = endOfDayTimes['day']

    projectNameAndDir = getProjectNameAndDirectory()

    timeData = None 
    file = getTimeDataSummaryFile()
    payloads = getFileDataArray(file)
    if len(payloads) > 0:
        try:
            timeData = next(load for load in payloads if load['day'] == day and load['project']['directory'] == projectNameAndDir['directory'])
        except Exception:
            print('unable to extract payloads')
    if not timeData:
        timeData = TimeData()
        timeData['day'] = day 
        saveTimeDataSummaryToDisk(timeData)  
    return timeData


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

def getEndOfDayTimes():
    nowTime = getNowTimes()
    utcEndOfDay = endOfDayUnix(nowTime['nowInSec'])
    localEndOfDay = endOfDayUnix(nowTime['localNowInSec'])
    return { 
        "utcEndOfDay": utcEndOfDay, 
        "localEndOfDay": localEndOfDay, 
        "day": nowTime['day'] }

# Returns a unixTimestamp as a unixTimestamp but at the end of the day (to the millisecond)
def endOfDayUnix(unixTimestamp):
    day = datetime.fromtimestamp(unixTimestamp)
    endOfDay = datetime(day.year, day.month, day.day) + timedelta(1) - timedelta(0, 0, 0, 1)
    return math.floor(endOfDay.timestamp())