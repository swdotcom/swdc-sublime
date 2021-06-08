import json 
from .SoftwareUtil import *
from .Logger import *

def clearFileChangeInfoSummaryData():
    saveFileChangeInfoToDisk({})

def getFileChangeSummaryAsJson():
    file = getFileChangeSummaryFile()
    fileChangeInfoMap = getFileDataAsJson(file)
    if not fileChangeInfoMap:
        fileChangeInfoMap = {}
    return fileChangeInfoMap

def saveFileChangeInfoToDisk(fileChangeInfoData):
    file = getFileChangeSummaryFile()
    if fileChangeInfoData:
        try:
            with open(file, 'w') as f:
                json.dump(fileChangeInfoData, f, indent=4)
        except Exception as ex:
            logIt('Code time: Error writing file change data: %s' % ex)
