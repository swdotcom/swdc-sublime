import sublime_plugin, sublime
from threading import Thread, Timer, Event
import json
import os.path
import time
import math
import copy
from datetime import *
from .SoftwareUtil import *
from .SoftwareFileDataManager import *
from .SoftwareModels import SessionSummary, KeystrokeAggregate, TimeData, Project
from .SoftwareFileChangeInfoSummaryData import *

# Constants
SERVICE_NOT_AVAIL = "Our service is temporarily unavailable.\n\nPlease try again later.\n"
ONE_MINUTE_IN_SEC = 60
SECONDS_PER_HOUR = 60 * 60
DEFAULT_SESSION_THRESHOLD_SECONDS = 60 * 15
LONG_THRESHOLD_HOURS = 12
SHORT_THRESHOLD_HOURS = 4
NO_TOKEN_THRESHOLD_HOURS = 2


def getSummaryInfoFile():
    file = getSoftwareDir(True)
    return os.path.join(file, 'SummaryInfo.txt')

def incrementSessionSummaryData(aggregates):
    data = getSessionSummaryData()
    incrementMinutes = getMinutesSinceLastPayload()

    data['currentDayMinutes'] += incrementMinutes
    data['currentDayKeystrokes'] += aggregates['keystrokes']
    data['currentDayLinesAdded'] += aggregates['linesAdded']
    data['currentDayLinesRemoved'] += aggregates['linesRemoved']

    saveSessionSummaryToDisk(data)
    incrementSessionAndFileSeconds()


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
        project['directory'] = NO_PROJ_NAME
        project['name'] = UNTITLED

    return project 


def clearTimeDataSummary():
    data = TimeData()
    saveTimeDataSummaryToDisk(data)

def updateEditorSeconds(editor_seconds):
    timeData = getTodayTimeDataSummary()
    timeData['editor_seconds'] += editor_seconds
    saveTimeDataSummaryToDisk(timeData)

def incrementSessionAndFileSeconds():
    minutes_since_payload = getMinutesSinceLastPayload()
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


def getCurrentDayTime(sessionSummaryData):
    currentDayMinutes = 0
    try:
        currentDayMinutes = int(sessionSummaryData.get("currentDayMinutes", 0))
    except Exception as ex:
        currentDayMinutes = 0
        log("Code Time: Current Day exception: %s" % ex)
    
    return {"data": currentDayMinutes, "formatted": humanizeMinutes(currentDayMinutes)}

def getAverageDailyTime(sessionSummaryData):
    averageDailyMinutes = 0
    try:
        averageDailyMinutes = int(sessionSummaryData.get("averageDailyMinutes", 0))
    except Exception as ex:
        averageDailyMinutes = 0
        log("Code Time: Average Daily Minutes exception: %s" % ex)
    
    return {"data": averageDailyMinutes, "formatted": humanizeMinutes(averageDailyMinutes)}

def clearSessionSummaryData():
    emptyData = SessionSummary()
    saveSessionSummaryToDisk(emptyData)


def setSessionSummaryLiveshareMinutes(minutes):
    data = getSessionSummaryData()
    data['liveshareMinutes'] = minutes
    saveSessionSummaryToDisk(data)

# store the payload offline...
def storePayload(payload):

    fileChangeInfoMap = getFileChangeSummaryAsJson()
    aggregate = KeystrokeAggregate()
    # print(payload)

    if payload['project']:
        aggregate['directory'] = payload['project']['directory'] or NO_PROJ_NAME
    else:
        aggregate['directory'] = NO_PROJ_NAME
    
    for key in payload['source'].keys():
        fileInfo = payload['source'][key]
        baseName = os.path.basename(key)

        fileInfo['name'] = baseName
        fileInfo['fsPath'] = key
        fileInfo['projectDir'] = payload['project']['directory']
        fileInfo['duration_seconds'] = fileInfo['end'] - fileInfo['start']

        aggregate['add'] += fileInfo['add']
        aggregate['close'] += fileInfo['close']
        aggregate['delete'] += fileInfo['delete']
        aggregate['keystrokes'] += fileInfo['keystrokes']
        aggregate['linesAdded'] += fileInfo['linesAdded']
        aggregate['linesRemoved'] += fileInfo['linesRemoved']
        aggregate['open'] += fileInfo['open']
        aggregate['paste'] += fileInfo['paste']

        existingFileInfo = fileChangeInfoMap.get(key)
        if existingFileInfo is None:
            fileInfo['update_count'] = 1
            fileInfo['kpm'] = aggregate['keystrokes']
            fileChangeInfoMap[key] = fileInfo
        else:
            existingFileInfo['update_count'] += 1
            existingFileInfo['keystrokes'] += fileInfo['keystrokes']
            existingFileInfo['kpm'] = existingFileInfo['keystrokes'] / existingFileInfo['update_count']
            existingFileInfo['add'] += fileInfo['add']
            existingFileInfo['close'] += fileInfo['close']
            existingFileInfo['delete'] += fileInfo['delete']
            existingFileInfo['keystrokes'] += fileInfo['keystrokes']
            existingFileInfo['linesAdded'] += fileInfo['linesAdded']
            existingFileInfo['linesRemoved'] += fileInfo['linesRemoved']
            existingFileInfo['open'] += fileInfo['open']
            existingFileInfo['paste'] += fileInfo['paste']
            existingFileInfo['duration_seconds'] += fileInfo['duration_seconds']

            # non aggregates, just set
            existingFileInfo['lines'] = fileInfo['lines']
            existingFileInfo['length'] = fileInfo['length']


    incrementSessionSummaryData(aggregate)

    # push the stats to the file so other editor windows can have it
    saveFileChangeInfoToDisk(fileChangeInfoMap)

    # refresh tree
    refreshTreeTimer = Timer(1.0, refreshTreeView)
    refreshTreeTimer.start()

    # get the datastore file to save the payload
    dataStoreFile = getSoftwareDataStoreFile()

    log("Code Time: storing kpm metrics: %s" % payload)

    try:
        with open(dataStoreFile, "a") as dsFile:
            dsFile.write(json.dumps(payload) + "\n")
    except Exception as ex:
        log('Error appending to the Software data store file: %s' % ex)


