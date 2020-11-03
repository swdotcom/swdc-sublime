from threading import Lock
from .SoftwareUtil import *
from .SoftwareModels import SessionSummary
import os 
import json 

sessionSummaryLock = Lock()

# get the session summary data
def getSessionSummaryData():
    data = getSessionSummaryFileAsJson()
    return data

# get the session summary file
def getSessionSummaryFile():
    file = getSoftwareDir(True)
    return os.path.join(file, 'sessionSummary.json')

def clearSessionSummaryFile():
    data = SessionSummary()
    saveSessionSummaryToDisk(data)

def getSessionSummaryFileAsJson():
    sessionSummaryLock.acquire()
    try:
        with open(getSessionSummaryFile()) as sessionSummaryFile:
            sessionSummaryData = json.load(sessionSummaryFile)
    except Exception as ex:
        sessionSummaryData = SessionSummary()
        log("Code Time: Session summary file fetch error: %s" % ex)
    sessionSummaryLock.release()
    return sessionSummaryData

def saveSessionSummaryToDisk(sessionSummaryData):
    content = json.dumps(sessionSummaryData, indent=4)

    sessionFile = getSessionSummaryFile()
    sessionSummaryLock.acquire()
    with open(sessionFile, 'w') as f:
        f.write(content)
    sessionSummaryLock.release()
