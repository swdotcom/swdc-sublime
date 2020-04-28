from threading import Thread, Timer, Event, Lock, current_thread
import os
import json
import time as timeModule
import socket
import sublime_plugin, sublime
import sys
import uuid
import platform
import re, uuid
import webbrowser
import locale
import math
locale.setlocale(locale.LC_ALL, '')
from datetime import *
from subprocess import Popen, PIPE, check_output, CalledProcessError
from .SoftwareHttp import *
from .SoftwareSettings import *
from .SoftwareModels import Project
from .Constants import *

# the plugin version
VERSION = '2.2.0'

DASHBOARD_LABEL_WIDTH = 25
DASHBOARD_VALUE_WIDTH = 25
MARKER_WIDTH = 4

sessionMap = {}

buildTreeLock = Lock()

PROJECT_DIR = None

NUMBER_IN_EMAIL_REGEX = r'^\d+\+'

'''
In the future consider a TTL cache, but as of right now Python 3.3 (Sublime's version) does not 
have easy TTL cache options available
'''
# TODO: implement a TTL cache
myCache = {}

runningResourceCmd = False
loggedInCacheState = False

def updateOnlineStatus():
    online = serverIsAvailable()
    if (online is True):
        setValue("online", True)
        # print(getValue("online", True))
    else:
        setValue("online", False)
        # print(getValue("online", True))

# log the message
def log(message):
    if (getValue("software_logging_on", True)):
        print(message)

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
    myTimezone = None 
    try:
        myTimezone = datetime.now(timezone.utc).astimezone().tzname()
    except Exception:
        pass
    return myTimezone

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

def getHostname():
    try:
        return socket.gethostname()
    except Exception:
        return os.uname().nodename

def getActiveWindowId():
    try:
        return sublime.active_window().id()
    except Exception as ex:
        print("Code Time: unable to retrieve active window: %s" % ex)
        return None

# fetch a value from the .software/session.json file
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

def refreshTreeView():
    buildTreeLock.acquire()
    # print('thread {} refreshing'.format(current_thread().ident))
    sublime.active_window().run_command('open_tree_view')
    buildTreeLock.release()

def getOpenProjects():
    folders = None 
    if sublime.active_window().project_data():
        folders = sublime.active_window().project_data()['folders']
    if folders is None:
        return []
    openProjectNames = list(map(lambda x: x['path'], folders))
    return openProjectNames

def getFirstOpenProject():
    openProjects = getOpenProjects()
    if len(openProjects) > 0:
        return openProjects[0]
    return '' 

def getProjectDirectory():
    global PROJECT_DIR 
    if PROJECT_DIR is not None:
        return PROJECT_DIR 
    else:
        return getFirstOpenProject()

def getActiveProject():
    rootPath = getFirstOpenProject()
    project = Project()
    if not rootPath:
        project['directory'] = UNTITLED
        global NO_PROJ_NAME
        project['name'] = NO_PROJ_NAME
        return project 
    
    projectName = os.path.basename(rootPath)
    project['name'] = projectName if projectName else rootPath 
    project['directory'] = rootPath

    resourceInfo = getResourceInfo(rootPath)
    if resourceInfo and resourceInfo['identifier']:
        project['identifier'] = resourceInfo['identifier']
        project['resource'] = resourceInfo
    return project 

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

def getFileDataAsJson(file):
    data = None 
    if os.path.isfile(file):
        with open(file) as f:
            try:
                data = json.load(f)
            except Exception as ex:
                # log('Unable to read session info: %s' % ex)
                # os.remove(file)
                print('unable to read: %s' % ex)
    return data 

def getFileDataArray(file):
    payloads = []
    if os.path.isfile(file):
        with open(file) as f:
            try:
                contents = json.load(f)
                if (isinstance(contents, list)):    
                    payloads = contents 
                else:
                    payloads.append(contents)
            except Exception as ex:
                log('Error reading file array data: %s' % ex)
                os.remove(file)
    return payloads 

def getFileDataPayloadsAsJson(file):
    payloads = []
    if os.path.isfile(file):
        try:
            with open(file) as f:
                for line in f:
                    if (line and line.strip()):
                        line = line.rstrip()
                        # convert to object
                        json_obj = json.loads(line)
                        # convert to json to send
                        payloads.append(json_obj)
        except Exception as ex:
            log('Unable to read file data payload: %s' % ex)
            return []
    return payloads 

def getSoftwareSessionFile():
    file = getSoftwareDir(True)
    return os.path.join(file, 'session.json')

def getSoftwareDataStoreFile():
    file = getSoftwareDir(True)
    return os.path.join(file, 'data.json')

def getPluginEventsFile():
    file = getSoftwareDir(True)
    return os.path.join(file, 'events.json')

def getFileChangeSummaryFile():
    file = getSoftwareDir(True)
    return os.path.join(file, 'fileChangeSummary.json')

def getDashboardFile():
    file = getSoftwareDir(True)
    return os.path.join(file, 'CodeTime.txt')

def getTimeDataSummaryFile():
    file = getSoftwareDir(True)
    return os.path.join(file, 'projectTimeData.json')

def getSessionThresholdSeconds():
    thresholdSeconds = getItem('sessionThresholdInSec') or DEFAULT_SESSION_THRESHOLD_SECONDS
    return thresholdSeconds

def getSoftwareDir(autoCreate):
    softwareDataDir = os.path.expanduser('~')
    softwareDataDir = os.path.join(softwareDataDir, '.software')
    if (autoCreate is True):
        os.makedirs(softwareDataDir, exist_ok=True)
    return softwareDataDir

def getCustomDashboardFile():
    file = getSoftwareDir(True)
    return os.path.join(file, 'CustomDashboard.txt')

def getCommandResultLine(cmd, projectDir):
    resultList = getCommandResultList(cmd, projectDir)

    resultLine = ''
    if resultList and len(resultList) > 0:
        for line in resultList:
            if line and len(line.strip()) > 0:
                resultLine = line.strip()
                break 
    
    return resultLine 

def getCommandResultList(cmd, projectDir):
    # print(cmd)
    # print(projectDir) 
    try:
        result = check_output(cmd, cwd=projectDir)
    except CalledProcessError as ex:
        # print('reusltlisterrorerror: {}'.format(ex.output))
        if ex.output != b'': # Suppress trivial error 
            log('Error running {}: {}'.format(cmd, ex.output))
        return []
    
    result = result.decode('UTF-8').strip().replace('\r\n', '\r').replace('\n', '\r')
    # Remove initial spaces
    result = re.sub(r'^\s+', '', result).split('\r')
    return result 
    

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

        if (rootDir is None or isGitProject(rootDir) is False):
            return {}

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

def serverIsAvailable():
    # non-authenticated ping, no need to set the Authorization header
    response = requestIt("GET", "/ping", None, getItem("jwt"))
    if (isResponseOk(response)):
        return True
    else:
        return False

def launchSubmitFeedback():
    webbrowser.open('mailto:cody@software.com')

def getLocalREADMEFile():
    return os.path.join(os.path.dirname(__file__), '..', 'README.md')

# TODO: figure out how to do markdown preview
def displayReadmeIfNotExists(): 
    readmeFile = getLocalREADMEFile()
    sublime.active_window().open_file(readmeFile)
    # fileUri = 'markdown-preview://{}'.format(readmeFile)
    # displayed = getItem('sublime_CtReadme')
    # if not displayed:
        # setItem('sublime_CtReadme', True)

def launchSpotifyLoginUrl():
    api_endpoint = getValue("software_api_endpoint", "api.software.com")
    jwt = getItem("jwt")
    spotify_url="https://api.software.com/auth/spotify?token="+jwt
    # spotify_url = "https://"+ api_endpoint + "/auth/spotify?token=" + jwt
    webbrowser.open(spotify_url)

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
        start = int(timeModule.mktime(datetime.strptime(startDate, "%m/%d/%Y").timetuple()))
        end = int(timeModule.mktime(datetime.strptime(endDate, "%m/%d/%Y").timetuple()))
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
    serverAvailable = serverIsAvailable()
    if (serverAvailable):
        now = round(timeModule.time())
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
            if (response is not None and isResponseOk(response)):
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
        if (isResponseOk(response)):
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

def normalizeGithubEmail(email, filterOutNonEmails=True):
    if email:
        if filterOutNonEmails and ('users.noreply' in email or email.endswith('github.com')):
            return None 
        else:
            found = re.match(NUMBER_IN_EMAIL_REGEX, email)
            if found and 'users.noreply' in email:
                return None
    return email 

def getLoggedInCacheState():
    return loggedInCacheState

def sendHeartbeat(reason):
    jwt = getItem("jwt")
    serverAvailable = serverIsAvailable()
    if (jwt is not None and serverAvailable):

        payload = {}
        payload["pluginId"] = PLUGIN_ID
        payload["os"] = getOs()
        payload["start"] = round(timeModule.time())
        payload["version"] = VERSION
        payload["hostname"] = getHostname()
        payload["trigger_annotaion"] = reason

        api = "/data/heartbeat"
        try:
            response = requestIt("POST", api, json.dumps(payload), jwt)

            if (response is not None and isResponseOk(response) is False):
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

def getIcons():
    try:
        dirname = os.path.dirname(__file__)
        icons_file = os.path.join(dirname, '../icons.json')
        with open(icons_file, 'r') as f:
            icons_dict = json.load(f)
            return icons_dict
    except Exception:
        return {}

def formatNumber(num):
    numberStr = ''
    try:
        num = float(num)
    except Exception as ex:
        num = 0

    if num >= 1000:
        numberStr = '{:n}'.format(num)
    elif num % 1 == 0:
        numberStr = '{:n}'.format(int(num))
    else:
        numberStr = '{:.5n}'.format(num)
    return numberStr
    

#TODO:  Ensure this has equivalent functionality as numeral().format('0 a') in JS
def formatNumWithK(num):
    if num == 0: 
        return '0'
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    return '{} {}'.format('{:.1f}'.format(num).rstrip('0').rstrip('.'), ['', 'K', 'M', 'B', 'T'][magnitude]).strip()

def setInterval(func, sec): 
    def func_wrapper():
        setInterval(func, sec) 
        func()  
    t = Timer(sec, func_wrapper)
    t.start()
    return t

# Returns a unixTimestamp as a unixTimestamp but at the end of the day (to the millisecond)
def endOfDayUnix(unixTimestamp):
    day = datetime.fromtimestamp(unixTimestamp)
    endOfDay = datetime(day.year, day.month, day.day) + timedelta(1) - timedelta(0, 0, 0, 1)
    return math.floor(endOfDay.timestamp())

def startOfDayUnix(unixTimestamp):
    day = datetime.fromtimestamp(unixTimestamp)
    return datetime(day.year, day.month, day.day).timestamp()

def isGitProject(projectDir):
    if (projectDir is None):
        return False
    elif (os.path.exists(os.path.join(projectDir, '.git')) is False):
        return False
    else:
        return True

def getFormattedDay(unixSeconds):
    # returns a format like '2020/04/19'
    return datetime.fromtimestamp(unixSeconds).strftime("%Y/%m/%d")

def getIsNewDay():
    day = getNowTimes()['day']
    currentDay = getItem('currentDay')
    if (currentDay != day):
        return True
    else: 
        return False