import sublime
import os 
from .SoftwareUtil import *
from .SoftwareFileDataManager import *
from .SoftwareHttp import *
from .SoftwareWallClock import *

def updateSessionSummaryFromServer():
    jwt = getItem('jwt')
    response = requestIt("GET", '/sessions/summary?refresh=true', None, jwt)
    if response is not None and isResponseOk(response):
        print('got session summary!')
        respData = json.loads(response.read().decode('utf-8'))
        summary = getSessionSummaryData()

        for item in respData.items():
            key = item[0]
            val = item[1]

            if val != None:
                summary[key] = val 
        
        updateBasedOnSessionSeconds(summary['currentDayMinutes'] * 60)

        log('summary data: {}'.format(summary))
        saveSessionSummaryToDisk(summary)
    else:
        print('failed getting session summary')