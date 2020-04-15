import sublime
import os
from .SoftwareUtil import *
from .SoftwareOffline import *
from .SoftwareHttp import *
from .TimeSummaryData import *

# send the data that has been saved offline
def sendOfflineData(isNewDay=False):
    batchSendData('/data/batch', getSoftwareDataStoreFile())
    timer = Timer(60, lambda: sublime.active_window().run_command('force_update_session_summary', {"isNewDay": isNewDay}))
    timer.start()
    

def sendOfflineEvents():
    batchSendData('/data/event', getPluginEventsFile())

def sendOfflineTimeData():
    batchSendData('/data/time', getTimeDataSummaryFile(), isArray=True)
    clearTimeDataSummary()

def batchSendData(api, file, isArray=False):
    isOnline = serverIsAvailable()
    if not isOnline:
        return 

    try:
        if os.path.exists(file):
            payloads = None 
            if isArray:
                payloads = getFileDataArray(file)
            else:
                payloads = getFileDataPayloadsAsJson(file)
            batchSendPayloadData(api, file, payloads)
    except Exception as ex:
        log('Error batch sending payloads: %s' % ex)

            

def batchSendPayloadData(api, file, payloads):
    if (payloads is not None and len(payloads) > 0):

        # go through the payloads array 50 at a time
        batch = []
        length = len(payloads)
        for i in range(length):
            payload = payloads[i]
            if (len(batch) >= 50):
                requestIt("POST", "/data/batch", json.dumps(batch), getItem("jwt"))
                # send batch
                batch = []
            batch.append(payload)

        # send remaining batch
        if (len(batch) > 0):
            requestIt("POST", "/data/batch", json.dumps(batch), getItem("jwt"))
        
        os.remove(file)

def postBootstrapPayload(payload):
    batch = [payload]
    requestIt("POST", "/data/batch", json.dumps(batch), getItem("jwt"))