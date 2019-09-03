# Copyright (c) 2018 by Software.com
from threading import Thread, Timer, Event
import os
import json
import time
import datetime
import socket
import sublime_plugin, sublime
import sys
import uuid
import platform
import re, uuid
import webbrowser
from urllib.parse import quote_plus
from subprocess import Popen, PIPE
from .SoftwareHttp import *
from .SoftwareSettings import *

# the plugin version
VERSION = '0.9.4'
PLUGIN_ID = 1
DASHBOARD_LABEL_WIDTH = 25
DASHBOARD_VALUE_WIDTH = 25
MARKER_WIDTH = 4

sessionMap = {}

runningResourceCmd = False
loggedInCacheState = False
timezone=''

# log the message.
def log(message):
    if (getValue("software_logging_on", True)):
        print(message)

# .
def getUrlEndpoint():
    return getValue("software_dashboard_url", "https://app.software.com")

def getOsUsername():
    homedir = os.path.expanduser('~')
    username = os.path.basename(homedir)

    if (username is None or username == ""):
        username = os.environ.get("USER")
    
    return username

def getOs():
    system = platform.system()
    #release = platform.release()
    return system

def getTimezone():
    global timezone
    try:
        timezone = time.localtime().tm_zone
    except Exception:
        pass
#         keystrokeCountObj.timezone = ''
    return timezone

def getLocalStart():
    now = round(time.time())
    local_start = now - time.timezone
    try:
        #If current timezone is not in DST, value of tm_ist will be 0
        if time.localtime().tm_isdst == 0:
            pass
        else:
            # we're in DST, add 1
            local_start += (60 * 60)
    except Exception:
        pass
    return local_start

def getHostname():
    try:
        return socket.gethostname()
    except Exception:
        return os.uname().nodename

# fetch a value from the .software/sesion.json file
def getItem(key):
    val = sessionMap.get(key, None)
    if (val is not None):
        return val
    jsonObj = getSoftwareSessionAsJson()

    # return a default of None if key isn't found
    val = jsonObj.get(key, None)

    return val

# get an item from the session json file
def setItem(key, value):
    sessionMap[key] = value
    jsonObj = getSoftwareSessionAsJson()
    jsonObj[key] = value

    content = json.dumps(jsonObj)

    sessionFile = getSoftwareSessionFile()
    with open(sessionFile, 'w') as f:
        f.write(content)

def softwareSessionFileExists():
    file = getSoftwareDir(False)
    sessionFile = os.path.join(file, 'session.json')
    return os.path.isfile(sessionFile)

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

def getSoftwareDataStoreFile():
    file = getSoftwareDir(True)
    return os.path.join(file, 'data.json')

def getSoftwareDir(autoCreate):
    softwareDataDir = os.path.expanduser('~')
    softwareDataDir = os.path.join(softwareDataDir, '.software')
    if (autoCreate is True):
        os.makedirs(softwareDataDir, exist_ok=True)
    return softwareDataDir

def getDashboardFile():
    file = getSoftwareDir(True)
    return os.path.join(file, 'CodeTime.txt')

def getCustomDashboardFile():
    file = getSoftwareDir(True)
    return os.path.join(file, 'CustomDashboard.txt')

# execute the applescript command
def runCommand(cmd, args = []):
    p = Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate(cmd)
    return stdout.decode('utf-8').strip()

def getItunesTrackState():
    script = '''
        tell application "iTunes" to get player state
        '''
    try:
        cmd = script.encode('latin-1')
        result = runCommand(cmd, ['osascript', '-'])
        return result
    except Exception as e:
        log("Code Time: error getting track state: %s " % e)
        # no music found playing
        return "stopped"

def getSpotifyTrackState():
    script = '''
        tell application "Spotify" to get player state
        '''
    try:
        cmd = script.encode('latin-1')
        result = runCommand(cmd, ['osascript', '-'])
        return result
    except Exception as e:
        log("Code Time: error getting track state: %s " % e)
        # no music found playing
        return "stopped"


# get the current track playing (spotify or itunes)
def getTrackInfo():
    if sys.platform == "darwin":
        return getMacTrackInfo()
    elif sys.platform == "win32":
        # not supported on other platforms yet
        return getWinTrackInfo()
    else:
        # linux not supported yet
        return {}

# windows
def getWinTrackInfo():
    # not supported on other platforms yet
    return {}

# OS X
def getMacTrackInfo():
    script = '''
        on buildItunesRecord(appState)
            tell application "iTunes"
                set track_artist to artist of current track
                set track_name to name of current track
                set track_genre to genre of current track
                set track_id to database ID of current track
                set track_duration to duration of current track
                set json to "type='itunes';genre='" & track_genre & "';artist='" & track_artist & "';id='" & track_id & "';name='" & track_name & "';state='playing';duration='" & track_duration & "'"
            end tell
            return json
        end buildItunesRecord

        on buildSpotifyRecord(appState)
            tell application "Spotify"
                set track_artist to artist of current track
                set track_name to name of current track
                set track_duration to duration of current track
                set track_id to id of current track
                set track_duration to duration of current track
                set json to "type='spotify';genre='';artist='" & track_artist & "';id='" & track_id & "';name='" & track_name & "';state='playing';duration='" & track_duration & "'"
            end tell
            return json
        end buildSpotifyRecord

        try
            if application "Spotify" is running and application "iTunes" is not running then
                tell application "Spotify" to set spotifyState to (player state as text)
                -- spotify is running and itunes is not
                if (spotifyState is "paused" or spotifyState is "playing") then
                    set jsonRecord to buildSpotifyRecord(spotifyState)
                else
                    set jsonRecord to {}
                end if
            else if application "Spotify" is running and application "iTunes" is running then
                tell application "Spotify" to set spotifyState to (player state as text)
                tell application "iTunes" to set itunesState to (player state as text)
                -- both are running but use spotify as a higher priority
                if spotifyState is "playing" then
                    set jsonRecord to buildSpotifyRecord(spotifyState)
                else if itunesState is "playing" then
                    set jsonRecord to buildItunesRecord(itunesState)
                else if spotifyState is "paused" then
                    set jsonRecord to buildSpotifyRecord(spotifyState)
                else
                    set jsonRecord to {}
                end if
            else if application "iTunes" is running and application "Spotify" is not running then
                tell application "iTunes" to set itunesState to (player state as text)
                set jsonRecord to buildItunesRecord(itunesState)
            else
                set jsonRecord to {}
            end if
            return jsonRecord
        on error
            return {}
        end try
    '''
    try:
        cmd = script.encode('latin-1')
        result = runCommand(cmd, ['osascript', '-'])
        result = result.strip('\r\n')
        result = result.replace('"', '')
        result = result.replace('\'', '')

        if (result):
            trackInfo = dict(item.strip().split("=") for item in result.strip().split(";"))
            return trackInfo
        else:
            return {}
    except Exception as e:
        log("Code Time: error getting track: %s " % e)
        # no music found playing
        return {}

def runResourceCmd(cmdArgs, rootDir):
    if sys.platform == "darwin": # OS X
        runningResourceCmd = True
        p = Popen(cmdArgs, cwd = rootDir, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate()
        stdout = stdout.decode('utf-8').strip()
        if (stdout):
            stdout = stdout.strip('\r\n')
            return stdout
        else:
            return ""
    else:
        return ""


def getResourceInfo(rootDir):
    try:
        resourceInfo = {}
        tag = runResourceCmd(['git', 'describe', '--all'], rootDir)

        if (tag):
            resourceInfo['tag'] = tag
        identifier = runResourceCmd(['git', 'config', '--get', 'remote.origin.url'], rootDir)

        if (identifier):
            resourceInfo['identifier'] = identifier
        branch = runResourceCmd(['git', 'symbolic-ref', '--short', 'HEAD'], rootDir)

        if (branch):
            resourceInfo['branch'] = branch
        email = runResourceCmd(['git', 'config', 'user.email'], rootDir)

        if (email):
            resourceInfo['email'] = email
            
        if (resourceInfo.get("identifier") is not None):
            return resourceInfo
        else:
            return {}
    except Exception as e:
        return {}

def checkOnline():
    # non-authenticated ping, no need to set the Authorization header
    response = requestIt("GET", "/ping", None, getItem("jwt"))
    if (isResponsOk(response)):
        return True
    else:
        return False

def refetchUserStatusLazily(tryCountUntilFoundUser):
    currentUserStatus = getUserStatus()
    loggedInUser = currentUserStatus.get("loggedInUser", None)
    if (loggedInUser is not None or tryCountUntilFoundUser <= 0):
        return

    # start the time
    tryCountUntilFoundUser -= 1
    t = Timer(10, refetchUserStatusLazily, [tryCountUntilFoundUser])
    t.start()

def launchLoginUrl():
    webUrl = getUrlEndpoint()
    jwt = getItem("jwt")
    webUrl += "/onboarding?token=" + jwt
    webbrowser.open(webUrl)
    refetchUserStatusLazily(10)

def launchWebDashboardUrl():
    webUrl = getUrlEndpoint() + "/login"
    webbrowser.open(webUrl)

def isMac():
    if sys.platform == "darwin":
        return True
    return False

def isWindows():
    if sys.platform == "win32":
        return True
    return False

def fetchCustomDashboard(date_range):
    try:
        date_range_arr = [x.strip() for x in date_range.split(',')]
        startDate = date_range_arr[0] 
        endDate = date_range_arr[1] 
        start = int(time.mktime(datetime.datetime.strptime(startDate, "%m/%d/%Y").timetuple()))
        end = int(time.mktime(datetime.datetime.strptime(endDate, "%m/%d/%Y").timetuple()))
    except Exception:
        sublime.error_message(
            'Invalid date range'
            '\n\n'
            'Please enter a start and end date in the format, MM/DD/YYYY.'
            '\n\n'
            'Example: 04/24/2019, 05/01/2019')
        log("Code Time: invalid date range")

    try:
        api = '/dashboard?start=' + str(start) + '&end=' + str(end)
        response = requestIt("GET", api, None, getItem("jwt"))
        content = response.read().decode('utf-8')
        file = getCustomDashboardFile()
        with open(file, 'w', encoding='utf-8') as f:
            f.write(content)
    except Exception:
        log("Code Time: Unable to write custom dashboard")


def launchCustomDashboard():
    online = getValue("online", True)
    date_range = getValue("date_range", "04/24/2019, 05/01/2019")
    if (online):
        fetchCustomDashboard(date_range)
    else:
        log("Code Time: could not fetch custom dashboard")
    file = getCustomDashboardFile()
    sublime.active_window().open_file(file)

def getAppJwt():
    serverAvailable = checkOnline()
    if (serverAvailable):
        now = round(time.time())
        api = "/data/apptoken?token=" + str(now)
        response = requestIt("GET", api, None, None)
        if (response is not None):
            responseObjStr = response.read().decode('utf-8')
            try:
                responseObj = json.loads(responseObjStr)
                appJwt = responseObj.get("jwt", None)
                if (appJwt is not None):
                    return appJwt
            except Exception as ex:
                log("Code Time: Unable to retrieve app token: %s" % ex)
    return None

# crate a uuid token to establish a connection
def createToken():
    # return os.urandom(16).encode('hex')
    uid = uuid.uuid4()
    return uid.hex

def createAnonymousUser(serverAvailable):
    appJwt = getAppJwt()
    if (serverAvailable and appJwt):
        username = getOsUsername()
        timezone = getTimezone()
        hostname = getHostname()

        payload = {}
        payload["username"] = username
        payload["timezone"] = timezone
        payload["hostname"] = hostname
        payload["creation_annotation"] = "NO_SESSION_FILE"

        api = "/data/onboard"
        try:
            response = requestIt("POST", api, json.dumps(payload), appJwt)
            if (response is not None and isResponsOk(response)):
                try:
                    responseObj = json.loads(response.read().decode('utf-8'))
                    jwt = responseObj.get("jwt", None)
                    log("created anonymous user with jwt %s " % jwt)
                    setItem("jwt", jwt)
                    return jwt
                except Exception as ex:
                    log("Code Time: Unable to retrieve plugin accounts response: %s" % ex)
        except Exception as ex:
            log("Code Time: Unable to complete anonymous user creation: %s" % ex)
    return None

def getUser(serverAvailable):
    jwt = getItem("jwt")
    if (jwt and serverAvailable):
        api = "/users/me"
        response = requestIt("GET", api, None, jwt)
        if (isResponsOk(response)):
            try:
                responseObj = json.loads(response.read().decode('utf-8'))
                user = responseObj.get("data", None)
                return user
            except Exception as ex:
                log("Code Time: Unable to retrieve user: %s" % ex)
    return None

def validateEmail(email):
    match = re.findall('\S+@\S+', email)
    if match:
        return True
    return False

def isLoggedOn(serverAvailable):
    jwt = getItem("jwt")
    if (serverAvailable and jwt is not None):

        user = getUser(serverAvailable)
        if (user is not None and validateEmail(user.get("email", None))):
            setItem("name", user.get("email"))
            setItem("jwt", user.get("plugin_jwt"))
            return True

        api = "/users/plugin/state"
        response = requestIt("GET", api, None, jwt)

        responseOk = isResponsOk(response)
        if (responseOk is True):
            try:
                responseObj = json.loads(response.read().decode('utf-8'))
                
                state = responseObj.get("state", None)
                if (state is not None and state == "OK"):
                    email = responseObj.get("emai", None)
                    setItem("name", email)
                    pluginJwt = responseObj.get("jwt", None)
                    if (pluginJwt is not None and pluginJwt != jwt):
                        setItem("jwt", pluginJwt)

                    # state is ok, return True
                    return True
                elif (state is not None and state == "NOT_FOUND"):
                    setItem("jwt", None)

            except Exception as ex:
                log("Code Time: Unable to retrieve logged on response: %s" % ex)

    setItem("name", None)
    return False


def getUserStatus():
    global loggedInCacheState

    currentUserStatus = {}

    if (loggedInCacheState is True):
        currentUserStatus["loggedOn"] = loggedInCacheState
        return currentUserStatus

    getOsUsername()

    serverAvailable = checkOnline()

    # check if they're logged in or not
    loggedOn = isLoggedOn(serverAvailable)
    
    setValue("logged_on", loggedOn)
    currentUserStatus["loggedOn"] = loggedOn

    if (loggedOn is True and loggedInCacheState != loggedOn):
        log("Code Time: Logged on")
        sendHeartbeat("STATE_CHANGE:LOGGED_IN:true")

    loggedInCacheState = loggedOn

    return currentUserStatus

def sendHeartbeat(reason):
    jwt = getItem("jwt")
    serverAvailable = checkOnline()
    if (jwt is not None and serverAvailable):

        payload = {}
        payload["pluginId"] = PLUGIN_ID
        payload["os"] = getOs()
        payload["start"] = round(time.time())
        payload["version"] = VERSION
        payload["hostname"] = getHostname()
        payload["trigger_annotaion"] = reason

        api = "/data/heartbeat"
        try:
            response = requestIt("POST", api, json.dumps(payload), jwt)

            if (response is not None and isResponsOk(response) is False):
                log("Code Time: Unable to send heartbeat ping")
        except Exception as ex:
            log("Code Time: Unable to send heartbeat: %s" % ex)

def humanizeMinutes(minutes):
    minutes = int(minutes)
    humanizedStr = ""
    if (minutes == 60):
        humanizedStr = "1 hr"
    elif (minutes > 60):
        floatMin = (minutes / 60)
        if (floatMin % 1 == 0):
            # don't show zeros after the decimal
            humanizedStr = '{:4.0f}'.format(floatMin) + " hrs"
        else:
            # at least 4 chars (including the dot) with 2 after the dec point
            humanizedStr = '{:4.1f}'.format(round(floatMin, 1)) + " hrs"
    elif (minutes == 1):
        humanizedStr = "1 min"
    else:
        humanizedStr = '{:1.0f}'.format(minutes) + " min"

    return humanizedStr


def getDashboardRow(label, value):
    dashboardLabel = getDashboardLabel(label, DASHBOARD_LABEL_WIDTH)
    dashboardValue = getDashboardValue(value)
    content = "%s : %s\n" % (dashboardLabel, dashboardValue)
    return content

def getSectionHeader(label):
    content = "%s\n" % label
    # add 3 to account for the " : " between the columns
    dashLen = DASHBOARD_LABEL_WIDTH + DASHBOARD_VALUE_WIDTH + 15
    for i in range(dashLen):
        content += "-"
    content += "\n"
    return content

def getDashboardLabel(label, width):
    return getDashboardDataDisplay(width, label)

def getDashboardValue(value):
    valueContent = getDashboardDataDisplay(DASHBOARD_VALUE_WIDTH, value)
    paddedContent = ""
    for i in range(11):
        paddedContent += " "
    paddedContent = "%s%s" % (paddedContent, valueContent)
    return paddedContent

def getDashboardDataDisplay(widthLen, data):
    dataLen = len(data)

    stringLen = widthLen - len(data)

    content = ""
    for i in range(stringLen):
        content += " "
    return "%s%s" % (content, data)

