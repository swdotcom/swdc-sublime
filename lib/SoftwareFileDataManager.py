from threading import Lock
from .SoftwareUtil import *
from .SoftwareModels import SessionSummary
import os 
import json 

sessionSummaryLock = Lock()

# get the session summary data
def getSessionSummaryData():
    data = getSessionSummaryFileAsJson()
    data = coalesceMissingSessionSummaryAttributes(data)
    return data

# get the session summary file
def getSessionSummaryFile():
    file = getSoftwareDir(True)
    return os.path.join(file, 'sessionSummary.json')

# Corrects data object if missing keys
def coalesceMissingSessionSummaryAttributes(data):
    template = SessionSummary()
    for key in template.keys():
        if key not in data:
            if key == 'lastUpdatedToday' or key == 'inFlow':
                data[key] = False
            else: 
                data[key] = 0
    return data

def getSessionSummaryFileAsJson():
    sessionSummaryLock.acquire()
    try:
        with open(getSessionSummaryFile()) as sessionSummaryFile:
            sessionSummaryData = json.load(sessionSummaryFile)
    except Exception as ex:
        sessionSummaryData = SessionSummary()
        log("Code Time: Session summary file fetch error: %s" % ex)
    sessionSummaryData = coalesceMissingSessionSummaryAttributes(sessionSummaryData)
    sessionSummaryLock.release()
    return sessionSummaryData

def saveSessionSummaryToDisk(sessionSummaryData):
    content = json.dumps(sessionSummaryData, indent=4)

    sessionFile = getSessionSummaryFile()
    sessionSummaryLock.acquire()
    with open(sessionFile, 'w') as f:
        f.write(content)
    sessionSummaryLock.release()
