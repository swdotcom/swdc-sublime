import sublime
import os 
from .SoftwareUtil import *
from .SoftwareFileDataManager import *
from .SoftwareHttp import *
from .SoftwareWallClock import *
from .SoftwareOffline import *
from .CommonUtil import *

def updateSessionSummaryFromServer(isNewDay=False):
    jwt = getItem('jwt')
    response = requestIt("GET", '/sessions/summary?refresh=true', None, jwt)
    if response is not None and isResponseOk(response):
        respData = json.loads(response.read().decode('utf-8'))
        summary = getSessionSummaryData()

        for item in respData.items():
            key = item[0]
            val = item[1]

            if val != None:
                if key == 'currentDayMinutes' and not isNewDay:
                    try:
                        currDayMin = int(val)
                        summary['currentDayMinutes'] = min(summary['currentDayMinutes'], currDayMin)
                    except Exception:
                        pass 
                else:
                    summary[key] = val 
        
        updateSessionFromSummaryApi(summary['currentDayMinutes'])

        # log('summary data: {}'.format(summary))
        saveSessionSummaryToDisk(summary)

    updateStatusBarWithSummaryData()
