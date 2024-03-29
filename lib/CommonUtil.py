import time as timeModule
import platform
import json
import os
import re, uuid
from .Constants import *
from .SoftwareSettings import *
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

def getOsUsername():
    homedir = os.path.expanduser('~')
    username = os.path.basename(homedir)

    if (username is None or username == ""):
        username = os.environ.get("USER")

    return username

def getHostname():
    try:
        return socket.gethostname()
    except Exception:
        return os.uname().nodename

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

def getPluginType():
    return "codetime"

def getPluginId():
	return PLUGIN_ID

def getPluginName():
    pluginName = __name__.split('.')[0]
    return pluginName

def getJwt():
    jwt = getItem("jwt")

    if jwt is None or ' ' not in jwt:
        return jwt
    else:
        return jwt.strip().split(' ')[1]


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

def getPluginUuid():
    jsonObj = getDeviceAsJson()
    plugin_uuid = jsonObj.get("plugin_uuid", None)
    if (plugin_uuid is None):
        plugin_uuid = str(uuid.uuid4())
        jsonObj["plugin_uuid"] = plugin_uuid
        content = json.dumps(jsonObj)

        deviceFile = getDeviceFile()
        with open(deviceFile, 'w') as f:
            f.write(content)

    return plugin_uuid

def getAuthCallbackState(auto_create=True):
    jsonObj = getDeviceAsJson()
    auth_callback_state = jsonObj.get("auth_callback_state", None)
    if (auth_callback_state is None and auto_create is True):
        auth_callback_state = str(uuid.uuid4())
        jsonObj["auth_callback_state"] = auth_callback_state
        content = json.dumps(jsonObj)

        deviceFile = getDeviceFile()
        with open(deviceFile, 'w') as f:
            f.write(content)

    return auth_callback_state

def setAuthCallbackState(value):
    jsonObj = getDeviceAsJson()
    jsonObj["auth_callback_state"] = value

    content = json.dumps(jsonObj)

    deviceFile = getDeviceFile()
    with open(deviceFile, 'w') as f:
        f.write(content)

def getSoftwareSessionAsJson():
    try:
        with open(getSoftwareSessionFile(), encoding='utf-8') as sessionFile:
            return json.load(sessionFile)
    except Exception as ex:
        return {}

def getSoftwareSessionFile():
    file = getSoftwareDir(True)
    return os.path.join(file, 'session.json')

def getDeviceAsJson():
    try:
        with open(getDeviceFile(), encoding='utf-8') as deviceFile:
            return json.load(deviceFile)
    except Exception:
        return {}

def getDeviceFile():
    file = getSoftwareDir(True)
    return os.path.join(file, 'device.json')

def getSoftwareDir(autoCreate):
    softwareDataDir = os.path.expanduser('~')
    softwareDataDir = os.path.join(softwareDataDir, getSoftwareDirName())
    if (autoCreate is True):
        os.makedirs(softwareDataDir, exist_ok=True)
    return softwareDataDir

def getSoftwareDirName():
    return getValue("software_dir", ".software")

def sublime_variables(view):
    view.window().extract_variables()

def getWebUrl():
    return getValue("software_dashboard_url", "https://app.software.com")

def getApiEndpoint():
    return getValue("software_api_endpoint", "api.software.com")

def getAppEndpoint():
    return getValue("software_app_endpoint", "app.software.com")

def getPercentOfReferenceAvg(curr, ref, refDisplay):
    if (curr is None):
        curr = 0
    quotient = 1
    if (ref is not None):
        quotient = curr / ref
        if (curr > 0 and quotient < 0.01):
            quotient = 0.01

    return round((quotient * 100), 2) + " of " + refDisplay
