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
from .CommonUtil import *

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

def getOpenProjects():
    folders = None
    if sublime.active_window().project_data():
        folders = sublime.active_window().project_data()['folders']
    if folders is None:
        return []
    openProjectNames = list([x['path'] for x in folders])
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

def storeHashedValues(user_hashed_values):
    file = getSoftwareHashedValuesFile()
    if user_hashed_values:
        try:
            with open(file, 'w') as f:
                json.dump(user_hashed_values, f, indent=4)
        except Exception as ex:
            log('Code time: Error writing hashed_values: %s' % ex)

def getHashedValues():
    return getFileDataAsJson(getSoftwareHashedValuesFile()) or {}

def getSoftwareHashedValuesFile():
    file = getSoftwareDir(True)
    return os.path.join(file, 'hashed_values.json')

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
            try:
                resourceInfo['repo_name'] = identifier.split("/")[-1].split(".git")[0]
            except Exception as ex:
                print("unable to extract repo_name from identifier: " + identifier)
                resourceInfo['repo_name'] = ''

            try:
                resourceInfo['repo_owner_id'] = identifier.split(":")[1].split("/")[0]
            except Exception as ex:
                print("unable to extract repo_owner_id from identifier: " + identifier)
                resourceInfo['repo_owner_id'] = ''

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
    response = requestIt("GET", "/ping", None, None)
    if (isResponseOk(response)):
        return True
    else:
        return False

def launchSubmitFeedback():
    webbrowser.open('mailto:cody@software.com')

def getLocalREADMEFile():
    return os.path.join(os.path.dirname(__file__), '..', 'README.txt')

# TODO: figure out how to do markdown preview
def displayReadmeIfNotExists(overrideInitCheck):
    displayed = getItem('sublime_CtReadme');
    if (displayed is None or overrideInitCheck is True):
        readmeFile = getLocalREADMEFile()
        sublime.active_window().open_file(readmeFile)
        setItem('sublime_CtReadme', True)

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

def createAnonymousUser():
    jwt = getItem("jwt")
    if (jwt is None):
        plugin_uuid = getPluginUuid()
        username = getOsUsername()
        timezone = getTimezone()
        hostname = getHostname()
        auth_callback_state = getAuthCallbackState()

        payload = {}
        payload["username"] = username
        payload["timezone"] = timezone
        payload["hostname"] = hostname
        payload["plugin_uuid"] = plugin_uuid
        payload["auth_callback_state"] = auth_callback_state

        api = "/plugins/onboard"
        try:
            response = requestIt("POST", api, json.dumps(payload))
            if (response is not None and isResponseOk(response)):
                try:
                    responseObj = json.loads(response.read().decode('utf-8'))
                    jwt = responseObj.get("jwt", None)
                    log("created anonymous user with jwt %s " % jwt)
                    setItem("jwt", jwt)
                    setItem("name", None)
                    setItem("switching_account", False)
                    setAuthCallbackState(None)
                    return jwt
                except Exception as ex:
                    log("Code Time: Unable to retrieve plugin accounts response: %s" % ex)
        except Exception as ex:
            log("Code Time: Unable to complete anonymous user creation: %s" % ex)
    return None

def getUser():
    jwt = getItem("jwt")
    if (jwt):
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

def initializeUserPreferences():
    session_threshold_in_sec = getSessionThresholdSeconds()

    user = getUser()
    if(user):
        session_threshold_in_sec =  user.get("preferences", {}).get("sessionThresholdInSec", getSessionThresholdSeconds())

    # update values config
    setItem("sessionThresholdInSec", session_threshold_in_sec)

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

def format_file_name(path, project_path = None):
    try:
        # path should be the full path
        # /Users/bojacobson/code/software/swdc-sublime/lib/SoftwareUtil.py
        if path == "Untitled" or path is None:
            return UNTITLED

        if project_path is None:
            project_data = sublime.active_window().project_data()
            project_path = project_data['folders'][0]['path']
        # => /lib/SoftwareUtil.py
        return path.split(project_path)[1]
    except Exception as ex:
        return path

def format_file_path(path):
    # prevent null from being passed in as the file path
    if(path == "Untitled" or path is None):
        return UNTITLED
    else:
        return path

def get_syntax(view):
    syntax = view.settings().get('syntax')
    # get the last occurance of the "/" then get the 1st occurance of the .sublime-syntax
    # [language].sublime-syntax
    # Packages/Python/Python.sublime-syntax
    if (syntax):
        return syntax[syntax.rfind('/') + 1:-len(".sublime-syntax")]
    else:
        # get it from the file name
        path = view.file_name()
        if path == "Untitled" or path is None:
            return ""

        split = path.split(".")

        if len(split) > 1:
            return split[-1]
        else:
            return ""

def get_character_count(view):
    return view.size()

def get_line_count(view):
    # rowcol gives 0-based line number, need to add one as on editor lines starts from 1
    character_count = get_character_count(view)
    return view.rowcol(character_count)[0] + 1

def analyzeDocumentChanges(file_info_data, view):
    change_info = {
        'lines_added': 0,
        'lines_deleted': 0,
        'characters_added': 0,
        'characters_deleted': 0,
        'change_type': ""
    }

    extract_change_counts(change_info, file_info_data, view)
    characterize_change(change_info, file_info_data, view)

    return change_info

def extract_change_counts(change_info, file_info_data, view):
    prev_line_count = file_info_data['lines']
    if (prev_line_count == 0):
        prev_line_count = 1
    prev_character_count = file_info_data['length']

    new_line_count = get_line_count(view)
    new_character_count = get_character_count(view)

    line_diff = new_line_count - prev_line_count
    if (line_diff > 0):
        change_info['lines_added'] = line_diff
    else:
        change_info['lines_deleted'] = abs(line_diff)

    character_diff = new_character_count - prev_character_count
    if (character_diff > 0):
        change_info['characters_added'] = character_diff - change_info['lines_added']
    else:
        change_info['characters_deleted'] = abs(character_diff) - change_info['lines_deleted']


def characterize_change(change_info, file_info_data, view):
    if(change_info['characters_deleted'] > 0 or change_info['lines_deleted'] > 0):
        if (change_info['characters_added'] > 0 or change_info['lines_added'] > 0):
            change_info['change_type'] = "replacement"
        else:
            if (change_info['characters_deleted'] > 1 or change_info['lines_deleted'] > 1):
                change_info['change_type'] = "multi_delete"
            elif (change_info['characters_deleted'] == 1 or change_info['lines_deleted'] == 1):
                change_info['change_type'] = "single_delete"
    elif (change_info['characters_added'] > 1 or change_info['lines_added'] > 1):
        change_info['change_type'] = "multi_add"
    elif (change_info['characters_added'] == 1 or change_info['lines_added'] == 1):
        change_info['change_type'] = "single_add"
    else:
        change_info['change_type'] = "net_zero_change"
