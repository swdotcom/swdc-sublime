import time as timeModule
import platform
import json
import os
from .Constants import *
from datetime import *

def getUtcOffset():
    timestamp = timeModule.time()
    time_local = datetime.fromtimestamp(timestamp)
    time_utc = datetime.utcfromtimestamp(timestamp)
    offset_in_sec = round((time_local - time_utc).total_seconds())
    return offset_in_sec

def getNowTimes():
    nowInSec = round(timeModule.time())
    offsetInSec = getUtcOffset()
    localNowInSec = round(nowInSec + offsetInSec)
    day = datetime.now().date().isoformat()
    return {
        'nowInSec': nowInSec,
        'localNowInSec': localNowInSec,
        'offsetInSec': offsetInSec,
        'day': day
    }

def getIsNewDay():
    day = getNowTimes()['day']
    currentDay = getItem('currentDay')
    if (currentDay != day):
        return True
    else: 
        return False

def getOs():
    system = platform.system()
    return system

def getTimezone():
    myTimezone = None 
    try:
        myTimezone = datetime.now(timezone.utc).astimezone().tzname()
    except Exception:
        pass
    return myTimezone

def getPluginId():
	return PLUGIN_ID

def getPluginName():
	pluginName = __name__.split('.')[0]
	return pluginName

def getJwt(with_prefix = False):
    jwt = getItem("jwt")

    if(with_prefix or jwt is None):
        return jwt
    else:
        return jwt.split("JWT ")[1]


# fetch a value from the .software/session.json file
def getItem(key):
    jsonObj = getSoftwareSessionAsJson()

    # return a default of None if key isn't found
    val = jsonObj.get(key, None)

    return val

# get an item from the session json file
def setItem(key, value):
    jsonObj = getSoftwareSessionAsJson()
    jsonObj[key] = value

    content = json.dumps(jsonObj)

    sessionFile = getSoftwareSessionFile()
    with open(sessionFile, 'w') as f:
        f.write(content)

def getSoftwareSessionAsJson():
    try:
        with open(getSoftwareSessionFile()) as sessionFile:
            loadedSessionFile = json.load(sessionFile)
            return loadedSessionFile
    except Exception:
        return {}

def getSoftwareSessionFile():
    file = getSoftwareDir(True)
    return os.path.join(file, 'session.json')

def getSoftwareDir(autoCreate):
    softwareDataDir = os.path.expanduser('~')
    softwareDataDir = os.path.join(softwareDataDir, '.software')
    if (autoCreate is True):
        os.makedirs(softwareDataDir, exist_ok=True)
    return softwareDataDir

def sublime_variables(view):
    view.window().extract_variables()


