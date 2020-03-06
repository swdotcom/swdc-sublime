from .SoftwareUtil import *
from .SoftwareModels import TimeData
from datetime import *
import math 

def getTimeDataSummaryFile():
    file = getSoftwareDir(True)
    return os.path.join(file, 'timeDataSummary.json')

def clearTimeDataSummary():
    data = TimeData()
    saveTimeDataSummaryToDisk(data)

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

def getTodayTimeDataSummary():
    nowTimes = getNowTimes()
    day = nowTimes['day']

    timeData = myCache.get('timeDataSummary_{}'.format(day))
    if not timeData:
        file = getTimeDataSummaryFile()
        payloads = getFileDataArray(file)
        if len(payloads) > 0:
            try:
                timeData = next(load for load in payloads if load['day'] == day)
            except Exception as ex:
                timeData = TimeData()
                timeData['day'] = day 
                saveTimeDataSummaryToDisk(timeData)
        else:
            timeData = TimeData()
            timeData['day'] = day 
            saveTimeDataSummaryToDisk(timeData)
    return timeData


def saveTimeDataSummaryToDisk(data):
    if not data:
        return 

    nowTimes = getNowTimes()
    day = nowTimes['day']

    file = getTimeDataSummaryFile()
    payloads = getFileDataArray(file)

    newPayloads = []
    if len(payloads) > 0:
        # find the one for this day
        # existingTimeData = payloads.find(n => n.day === day);
        # create a new array and overwrite the file
        newPayloads = list(map(lambda item: data if item['day'] == day else item, payloads))
    else:
        newPayloads.append(data)

    # write new payloads to disk
    try:
        with open(file, 'w') as f:
            json.dump(newPayloads, f, indent=4)
        myCache['timeDataSummary_{}'.format(day)] = data 
    except Exception as ex:
        print('Deployer: Error writing time data:%s' % ex)



# Returns a unixTimestamp as a unixTimestamp but at the end of the day (to the millisecond)
def endOfDayUnix(unixTimestamp):
    endOfDay = datetime.fromtimestamp(unixTimestamp) + timedelta(1) - timedelta(0, 0, 0, 1)
    return math.floor(endOfDay.timestamp())