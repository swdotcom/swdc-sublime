import sublime_plugin, sublime
from threading import Thread, Timer, Event
import json
import os.path
import time
import copy
from datetime import *
from .SoftwareUtil import *
from .SoftwareFileDataManager import *
from .SoftwareModels import SessionSummary, KeystrokeAggregate, TimeData, Project, CodeTimeSummary
from .SoftwareFileChangeInfoSummaryData import *
from .TimeSummaryData import *
from .Constants import *
from .CommonUtil import *

# This file is called SessionSummaryDataManager.js in Atom

# Constants
SERVICE_NOT_AVAIL = "Our service is temporarily unavailable.\n\nPlease try again later.\n"
ONE_MINUTE_IN_SEC = 60
SECONDS_PER_HOUR = 60 * 60
DEFAULT_SESSION_THRESHOLD_SECONDS = 60 * 15
LONG_THRESHOLD_HOURS = 12
SHORT_THRESHOLD_HOURS = 4
NO_TOKEN_THRESHOLD_HOURS = 2

lastSavedKeystrokeStats = None

def getSummaryInfoFile():
    file = getSoftwareDir(True)
    return os.path.join(file, 'SummaryInfo.txt')

def incrementSessionSummaryData(aggregates):
    data = getSessionSummaryData()
    timeBetweenLastPayload = getTimeBetweenLastPayload()
    sessionMinutes = timeBetweenLastPayload['sessionMinutes']

    data['currentDayMinutes'] += sessionMinutes
    data['currentDayKeystrokes'] += aggregates['keystrokes']
    data['currentDayLinesAdded'] += aggregates['linesAdded']
    data['currentDayLinesRemoved'] += aggregates['linesRemoved']

    saveSessionSummaryToDisk(data)

def getTimeBetweenLastPayload():
    # default to 1 minute
    sessionMinutes = 1
    elapsedSeconds = 60

    lastPayloadEnd = getItem("latestPayloadTimestampEndUtc") # will be 0 if new day

    # the last payload end time is reset within the new day checker
    if (lastPayloadEnd is not None and lastPayloadEnd > 0):
        nowTimes = getNowTimes()
        nowInSec = nowTimes['nowInSec']
        # diff from the prev end time
        elapsedSeconds = max(60, nowInSec - lastPayloadEnd)

        # if it's less than the threshold, add minutes to the session time
        if (elapsedSeconds > 0 and elapsedSeconds <= getSessionThresholdSeconds()):
            # if it's still the same session, add the gap time in minutes
            sessionMinutes = elapsedSeconds / 60
        
        sessionMinutes = max(1, sessionMinutes)

    return { 'sessionMinutes': sessionMinutes, 'elapsedSeconds': elapsedSeconds }

def updateSessionFromSummaryApi(currentDayMinutes):
    day = getNowTimes()['day']

    codeTimeSummary = getCodeTimeSummary()

    diffActiveCodeMinutesToAdd = 0
    if codeTimeSummary['activeCodeTimeMinutes'] < currentDayMinutes:
        diffActiveCodeMinutesToAdd = currentDayMinutes - codeTimeSummary['activeCodeTimeMinutes']
    
    project = getActiveProject()
    timeData = None 
    if project:
        timeData = getTodayTimeDataSummary(project)
    else:
        summaryFile = getTimeDataSummaryFile()
        payloads = getFileDataArray(summaryFile)
        filteredPayloads = [x for x in payloads if x['day'] == day]
        if filteredPayloads and len(filteredPayloads) > 0:
            timeData = filteredPayloads[0]
    
    if not timeData:
        project = Project()
        project['directory'] = NO_PROJ_NAME
        project['name'] = UNTITLED

        timeData = TimeData()
        timeData['day'] = day
        timeData['project'] = project
    
    secondsToAdd = diffActiveCodeMinutesToAdd * 60
    timeData['session_seconds'] += secondsToAdd
    timeData['editor_seconds'] += secondsToAdd

    saveTimeDataSummaryToDisk(timeData)

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
def processAndAggregateData(payload):
    nowTimes = getNowTimes()

    fileChangeInfoMap = getFileChangeSummaryAsJson()
    aggregate = KeystrokeAggregate()

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
    
    # add the elapsed and cumulative times to the payload
    timeBetweenLastPayload = getTimeBetweenLastPayload()
    payload['elapsed_seconds'] = timeBetweenLastPayload['elapsedSeconds']
    validateAndUpdateCumulativeData(payload, timeBetweenLastPayload['sessionMinutes'])

    # set the end time
    payload['end'] = nowTimes['nowInSec']
    payload['local_end'] = nowTimes['localNowInSec']

    # set the hostname and workspace
    payload['hostname'] = getHostname()
    payload['workspace_name'] = getActiveWindowId()

    incrementSessionSummaryData(aggregate)

    # push the stats to the file so other editor windows can have it
    saveFileChangeInfoToDisk(fileChangeInfoMap)

    # get the datastore file to save the payload
    dataStoreFile = getSoftwareDataStoreFile()

    log("Code Time: storing kpm metrics: %s" % payload)

    setItem('latestPayloadTimestampEndUtc', nowTimes['nowInSec'])

def getLastSavedKeystrokeStats():
    global lastSavedKeystrokeStats
    if lastSavedKeystrokeStats is None:
        updateLastSavedKeystrokeStats()
    return lastSavedKeystrokeStats

def updateLastSavedKeystrokeStats():
    global lastSavedKeystrokeStats
    dataStoreFile = getSoftwareDataStoreFile()
    try:
        with open(dataStoreFile, "a") as dsFile:
            currentPayloads = getFileDataPayloadsAsJson(dataStoreFile)
            if (currentPayloads is not None and len(currentPayloads) > 0):
                currentPayloads
                sortedPayloads = list(sorted(currentPayloads, key=lambda payload: payload['start'], reverse=True))
                lastSavedKeystrokeStats = sortedPayloads[0]
    except Exception as ex:
        log('Error sorting current payloads: %s' % ex)

def validateAndUpdateCumulativeData(payload, sessionMinutes):
    td = incrementSessionAndFileSeconds(payload['project'], sessionMinutes)

    lastPayload = getLastSavedKeystrokeStats()

    # if it's a new day, clear the last payload and time data
    isNewDay = getIsNewDay()
    if isNewDay:
        lastPayload = None
        if td:
            td = None
    
    # set new_day in the payload based on last timestamp in session.json
    lastPayloadEnd = getItem("latestPayloadTimestampEndUtc")
    if lastPayloadEnd == 0:
        newDay = 1
    else:
        newDay = 0

    payload['new_day'] = newDay

    # get editor seconds
    cumulative_editor_seconds = 60
    cumulative_session_seconds = 60
    if (td is not None):
        # use data from the timedata object
        cumulative_editor_seconds = td['editor_seconds']
        cumulative_session_seconds = td['session_seconds']
    elif lastPayload:
        # no time data; used the last recorded kpm data
        if (lastPayload['cumulative_editor_seconds'] is not None):
            cumulative_editor_seconds = lastPayload['cumulative_editor_seconds'] + 60
        else:
            log('Error: No editor seconds in last payload.')

        if (lastPayload['cumulative_session_seconds'] is not None):
            cumulative_session_seconds = lastPayload['cumulative_session_seconds'] + 60
        else:
            log('Error: No session seconds in last payload.')
    
    # update the cumulative editor seconds
    payload['cumulative_editor_seconds'] = cumulative_editor_seconds
    payload['cumulative_session_seconds'] = cumulative_session_seconds
