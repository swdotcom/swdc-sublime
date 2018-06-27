# Copyright (c) 2018 by Software.com

from datetime import datetime, timezone, timedelta
from threading import Thread, Timer, Event
from queue import Queue
import webbrowser
import uuid
import time
import math
import http
import json
import os
import urllib
import subprocess
import zipfile
import re
import sublime_plugin, sublime

VERSION = '0.1.4'
PM_URL = 'localhost:19234'
USER_AGENT = 'Software.com Sublime Plugin v' + VERSION
LOGGING = True
DEFAULT_DURATION = 60
was_new_version_shown = False
updates_running = False
downloadingPM = False
fetchingUserFromToken = False

PM_BUCKET = "https://s3-us-west-1.amazonaws.com/swdc-plugin-manager/"
PLUGIN_YML_URL = "https://s3-us-west-1.amazonaws.com/swdc-plugins/plugins.yml"
PM_NAME = "software"
NO_PM_FOUND_MSG = "We are having trouble sending data to Software.com. The Software Desktop may not be installed. Would you like to download it now?"
PLUGIN_TO_PM_ERROR_MSG = "We are having trouble sending data to Software.com. Please make sure the Software Desktop is running and signed on."
PLUGIN_UPDATE_AVAILABLE_MSG = "A new version of the Software plugin (%s) for Sublime Text is now available. Update now?"
PLUGIN_ZIP_NAME = "swdc-sublime.zip"
PLUGIN_ZIP_URL = "https://s3-us-west-1.amazonaws.com/swdc-plugins/%s" % PLUGIN_ZIP_NAME
LOGIN_LABEL = "Log in"

MILLIS_PER_DAY = 1000 * 60 * 60 * 24
MILLIS_PER_HOUR = 1000 * 60 * 60
SECONDS_PER_HOUR = 60 * 60
SECONDS_PER_HALF_HOUR = 60 * 30
LONG_THRESHOLD_HOURS = 12
SHORT_THRESHOLD_HOURS = 4
DASHBOARD_KEYMAP_MSG = "Software.com [ctrl+alt+o]"
PROD_API_ENDPOINT = "api.software.com"
PROD_URL = "https://alpha.software.com"
TEST_API_ENDPOINT = "localhost:5000"
TEST_URL = "http://localhost:3000"

# set the api endpoint to use
api_endpoint = PROD_API_ENDPOINT
# set the launch url to use
launch_url = PROD_URL

# log the message
def log(message):
    if not LOGGING:
        return

    print(message)

def secondsNow():
    return datetime.utcnow()

def trueSecondsNow():
    return time.mktime(secondsNow().timetuple())

#
# post the json data
#
def post_json(json_data):
    # send offline data
    sendOfflineData()

    response = requestIt("POST", "/data", json_data)

    if (response is None):
        # save the data to the offline data file
        storePayload(json_data)
        # check if we need to ask to login
        chekUserAuthenticationStatus()

    PluginData.reset_source_data()

class BackgroundWorker():
    def __init__(self, threads_count, target_func):
        self.queue = Queue(maxsize=0)
        self.target_func = target_func
        self.threads = []

        for i in range(threads_count):
            thread = Thread(target=self.worker, daemon=True)
            thread.start()
            self.threads.append(thread)

    def worker(self):
        while True:
            self.target_func(self.queue.get())
            self.queue.task_done()

class DownloadPM(Thread):

    # download the PM and install it....
    def run(self):
        downloadingPM = True
        saveAs = getDownloadFilePathName()
        url = getFileUrl()
        downloadPath = getDownloadPath()

        showStatus("Downlaoding Software Desktop")

        try:
            urllib.urlretrieve(url, saveAs)
        except AttributeError:
            urllib.request.urlretrieve(url, saveAs)

        showStatus("Completed downloading Software Desktop")

        showStatus("Installing Software Desktop")
        if (isMac()):
            # open the .dmg
            subprocess.Popen(['open', saveAs], stdout=subprocess.PIPE)
        else:
            # open the .deb or .exe
            subprocess.Popen([saveAs], stdout=subprocess.PIPE)

# download the plugin and unzip it to the packages folder.
class DownloadPlugin(Thread):
    def run(self):
        # delete existing zip files
        packagesDir = sublime.packages_path()
        for file in os.listdir(packagesDir):
            if (file.startswith("swdc") and file.find(".zip") != -1):
                zipToRemove = os.path.join(getPluginPathWithSlash(), file)
                os.remove(zipToRemove)

        showStatus("Downloading Software package")

        saveAs = getPluginDataPathFileName()

        try:
            urllib.urlretrieve(PLUGIN_ZIP_URL, saveAs)
        except AttributeError:
            urllib.request.urlretrieve(PLUGIN_ZIP_URL, saveAs)

        # unzip it now
        showStatus("Extracting Software package")

        with zipfile.ZipFile(saveAs, "r") as zip_ref:
            zip_ref.extractall(sublime.packages_path())

        showStatus("Completed package installation")

        try:
            os.remove(saveAs)
        except:
            pass


# fetch the plugins.yml to find out if there's a new plugin version to download
class CheckForUpdates(Thread):

    def run(self):
        global was_new_version_shown
        global updates_running

        updates_running = True
        
        with urllib.request.urlopen(PLUGIN_YML_URL) as response:
            ymldata = response.read().decode("utf-8")

            if (ymldata is not None):
                ymllines = ymldata.splitlines()
                # look for "sublime-version"
                if (ymllines and len(ymllines) > 0):
                    for versionline in ymllines:
                        if (versionline.startswith("sublime-version")):
                            versionparts = versionline.split()
                            availableversion = versionparts[1].strip()
                            if (len(versionparts) == 2 and VERSION != availableversion):
                                # alert the user that there's a new version
                                was_new_version_shown = True

                                version_available_msg = PLUGIN_UPDATE_AVAILABLE_MSG % availableversion

                                clickAction = sublime.ok_cancel_dialog(version_available_msg, "Download")
                                if (clickAction == True):
                                    thread = DownloadPlugin()
                                    thread.start()
                                return
                                
                            # break out, we found the sublime version line
                            break

        updates_running = False

class PluginData():
    __slots__ = ('source', 'type', 'data', 'start', 'end', 'send_timer', 'project', 'pluginId', 'version')
    convert_to_seconds = ('start', 'end')
    json_ignore = ('send_timer',)
    background_worker = BackgroundWorker(1, post_json)
    active_datas = dict()

    def __init__(self, project):
        self.source = dict()
        self.type = 'Events'
        self.data = 0
        self.start = secondsNow()
        self.end = self.start + timedelta(seconds=60)
        self.send_timer = None
        self.project = project
        self.pluginId = 1
        self.version = VERSION

    def json(self):

        if self.project['directory'] == 'None':
            self.project = None

        dict_data = {key: getattr(self, key, None)
                     for key in self.__slots__ if key not in self.json_ignore}

        for key in self.convert_to_seconds:
            dict_data[key] = int(round(dict_data[key]
                                       .replace(tzinfo=timezone.utc).timestamp()))

        return json.dumps(dict_data)

    def send(self):
        if PluginData.background_worker is not None and self.hasData():
            PluginData.background_worker.queue.put(self.json())

    # check if we have data
    def hasData(self):
        for fileName in self.source:
            fileInfo = self.source[fileName]
            if (fileInfo['close'] > 0 or
                fileInfo['open'] > 0 or
                fileInfo['paste'] > 0 or
                fileInfo['delete'] > 0 or
                fileInfo['add'] > 0):
                return True
        return False

    @staticmethod
    def reset_source_data():
        for dir in PluginData.active_datas:
            keystrokeCountObj = PluginData.active_datas[dir]
            if keystrokeCountObj is not None:
                keystrokeCountObj.source = dict()
                keystrokeCountObj.data = 0
                keystrokeCountObj.start = secondsNow()
                keystrokeCountObj.end = keystrokeCountObj.start + timedelta(seconds=60)

    @staticmethod
    def get_active_data(view):
        now = secondsNow()
        return_data = None
        if view is None or view.window() is None:
            return return_data

        fileName = view.file_name()
        if fileName is None:
            return return_data

        sublime_variables = view.window().extract_variables()
        project = dict()

        #
        projectFolder = 'None'

        # set the project folder
        if 'folder' in sublime_variables:
            projectFolder = sublime_variables['folder']
        elif 'file_path' in sublime_variables:
            projectFolder = sublime_variables['file_path']

        # if we have a valid project folder, set the project name from it
        if projectFolder != 'None':
            project['directory'] = projectFolder
            if 'project_name' in sublime_variables:
                project['name'] = sublime_variables['project_name']
            else:
                # use last file name in the folder as the project name
                projectNameIdx = projectFolder.rfind('/')
                if projectNameIdx > -1:
                    projectName = projectFolder[projectNameIdx + 1:]
                    project['name'] = projectName
        else:
            project['directory'] = 'None'

        old_active_data = None
        if project['directory'] in PluginData.active_datas:
            old_active_data = PluginData.active_datas[project['directory']]

        if old_active_data is None or now > old_active_data.end:
            new_active_data = PluginData(project)

            # This activates the 60 second timer. The callback
            # in the Timer sends the data
            new_active_data.send_timer = Timer(DEFAULT_DURATION,
                                               new_active_data.send)
            new_active_data.send_timer.start()

            PluginData.active_datas[project['directory']] = new_active_data
            return_data = new_active_data
        else:
            return_data = old_active_data

        fileInfoData = PluginData.get_file_info_and_initialize_if_none(return_data, fileName)

        return return_data

    @staticmethod
    def get_existing_file_info(fileName):

        # Get the FileInfo object within the KeystrokesCount object
        # based on the specified fileName.
        for dir in PluginData.active_datas:
            keystrokeCountObj = PluginData.active_datas[dir]
            if keystrokeCountObj is not None:
                hasExistingKeystrokeObj = True
                # we have a keystroke count object, get the fileInfo
                if keystrokeCountObj.source is not None and fileName in keystrokeCountObj.source:
                    return keystrokeCountObj.source[fileName]

        return None

    @staticmethod
    def send_all_datas():
        for dir in PluginData.active_datas:
            PluginData.active_datas[dir].send()

    @staticmethod
    def initialize_file_info(keystrokeCount, fileName):
        if keystrokeCount is None:
            return

        if fileName is None or fileName == '':
            fileName is 'None'
        
        # create the new FileInfo, which will contain a dictionary
        # of fileName and it's metrics
        fileInfoData = PluginData.get_existing_file_info(fileName)

        # "add" = additive keystrokes
        # "netkeys" = add - delete
        # "keys" = add + delete
        # "delete" = delete keystrokes
        if fileInfoData is None:
            fileInfoData = dict()
            fileInfoData['keys'] = 0
            fileInfoData['paste'] = 0
            fileInfoData['open'] = 0
            fileInfoData['close'] = 0
            fileInfoData['length'] = 0
            fileInfoData['delete'] = 0
            fileInfoData['netkeys'] = 0
            fileInfoData['add'] = 0
            fileInfoData['lines'] = 0
            fileInfoData['linesAdded'] = 0
            fileInfoData['linesRemoved'] = 0
            fileInfoData['syntax'] = ""
            keystrokeCount.source[fileName] = fileInfoData

    @staticmethod
    def get_file_info_and_initialize_if_none(keystrokeCount, fileName):
        fileInfoData = PluginData.get_existing_file_info(fileName)
        if fileInfoData is None:
            PluginData.initialize_file_info(keystrokeCount, fileName)
            fileInfoData = PluginData.get_existing_file_info(fileName)

        return fileInfoData

class DashboardView(sublime_plugin.TextCommand):
    def run(self, edit, **kwargs):
        launchDashboard()

# Runs once instance per view (i.e. tab, or single file window)
class EventListener(sublime_plugin.EventListener):
    def on_load(self, view):
        fileName = view.file_name()

        active_data = PluginData.get_active_data(view)

        # get the file info to increment the open metric
        fileInfoData = PluginData.get_file_info_and_initialize_if_none(active_data, fileName)
        if fileInfoData is None:
            return

        fileSize = view.size()
        fileInfoData['length'] = fileSize

        # we have the fileinfo, update the metric
        fileInfoData['open'] = fileInfoData['open'] + 1
        log('Software.com: opened file %s' % fileName)

    def on_close(self, view):
        fileName = view.file_name()

        active_data = PluginData.get_active_data(view)

        # get the file info to increment the close metric
        fileInfoData = PluginData.get_file_info_and_initialize_if_none(active_data, fileName)
        if fileInfoData is None:
            return

        fileSize = view.size()
        fileInfoData['length'] = fileSize

        # we have the fileInfo, update the metric
        fileInfoData['close'] = fileInfoData['close'] + 1
        log('Software.com: closed file %s' % fileName)

    def on_modified(self, view):
        # get active data will create the file info if it doesn't exist
        active_data = PluginData.get_active_data(view)
        if active_data is None:
            return

        # add the count for the file
        fileName = view.file_name()
        fileInfoData = PluginData.get_file_info_and_initialize_if_none(active_data, fileName)
        if fileInfoData is None:
            return

        fileSize = view.size()
        # subtract the current size of the file from what we had before
        # we'll know whether it's a delete, copy+paste, or kpm
        currLen = fileInfoData['length']

        charCountDiff = 0
        
        if currLen > 0:
            charCountDiff = fileSize - currLen
        
        fileInfoData['length'] = fileSize
        if charCountDiff > 1:
            fileInfoData['paste'] = fileInfoData['paste'] + charCountDiff
            log('Software.com: copy and pasted incremented')
        elif charCountDiff < 0:
            fileInfoData['delete'] = fileInfoData['delete'] + 1
            # increment the overall count
            active_data.data = active_data.data + 1
            log('Software.com: delete incremented')
        else:
            fileInfoData['add'] = fileInfoData['add'] + 1
            # increment the overall count
            active_data.data = active_data.data + 1
            log('Software.com: KPM incremented')

        # update the netkeys and the keys
        # "netkeys" = add - delete
        # "keys" = add + delete
        fileInfoData['netkeys'] = fileInfoData['add'] - fileInfoData['delete']
        fileInfoData['keys'] = fileInfoData['add'] + fileInfoData['delete']

#
# Iniates the plugin tasks once the it's loaded into Sublime
#
def plugin_loaded():
    log('Software.com: Loaded v%s' % VERSION)
    showStatus("Software.com")

    authStatusTimer = Timer(10, chekUserAuthenticationStatus)
    authStatusTimer.start()

    kpmFetchTimer = Timer(30, fetchDailyKpmSessionInfo)
    kpmFetchTimer.start()

    sendOfflineDataTimer = Timer(20, sendOfflineData)
    sendOfflineDataTimer.start()

def plugin_unloaded():
    PluginData.send_all_datas()
    PluginData.background_worker.queue.join()

def isWindows():
    if (os.name == 'nt'):
        return True

    return False

def isMac():
    if (os.name == 'posix'):
        return True

    return False

# get the url + PM name to download the PM.
def getFileUrl():
    fileUrl = PM_BUCKET + PM_NAME + getPmExtension()
    return fileUrl

def getHomeDir():
    return os.environ['HOME']

# get the path to download the PM to
def getDownloadPath():
    downloadPath = getHomeDir()
    if (isWindows()):
        downloadPath += "\\Desktop\\"
    else:
        downloadPath += "/Desktop/"

    return downloadPath

def getPmExtension():
    if (isWindows()):
        return ".exe"
    elif (isMac()):
        return ".dmg"
    else:
        return ".deb"

def getPluginPathWithSlash():
    pluginPathWithExtension = sublime.packages_path()

    if (isWindows()):
        return pluginPathWithExtension + "\\"
    else:
        return pluginPathWithExtension + "/"

    return pluginPathWithExtension

# For Sublime 3, the locations are the following
# Windows: %APPDATA%\Sublime Text 3\Packages
# OS X: ~/Library/Application Support/Sublime Text 3/Packages
# Linux: ~/.config/sublime-text-3/packages
def getPluginDataPathFileName():
    # i.e. sublime path: /Users/xavierluiz/Library/Application Support/Sublime Text 3/Packages
    pluginPathFileName = sublime.packages_path()

    if (isWindows()):
        return pluginPathFileName + "\\" + PLUGIN_ZIP_NAME
    else:
        return pluginPathFileName + "/" + PLUGIN_ZIP_NAME

# get the filename we're going to use for the PM download
def getDownloadFilePathName():
    downloadFilePathName = getDownloadPath() + PM_NAME + getPmExtension()
    return downloadFilePathName
     
# get the directory path where the PM should be installed
def getPmInstallDirectoryPath():
    if (isWindows()):
        return getHomeDir() + "\\AppData\\Local\\Programs"
    elif (isMac()):
        return "/Applications"
    else:
        return "/user/lib"

# check if the PM was installed or not
def hasPluginInstalled():
    installDir = getPmInstallDirectoryPath()

    for file in os.listdir(installDir):
        pathname = os.path.join(installDir, file)
        lcfile = file.lower()
        # file found: Software.com Plugin Manager.app
        if (lcfile.startswith("software")):
            return True

    return False

def getSoftwareDir():
    softwareDataDir = getHomeDir()
    if (isWindows()):
        softwareDataDir += "\\.software"
    else:
        softwareDataDir += "/.software"

    if not os.path.exists(softwareDataDir):
        os.makedirs(softwareDataDir)

    return softwareDataDir

def getSoftwareSessionFile():
    file = getSoftwareDir()
    if (isWindows()):
        file += "\\session.json"
    else:
        file += "/session.json"
    return file

def getSoftwareDataStoreFile():
    file = getSoftwareDir()
    if (isWindows()):
        file += "\\data.json"
    else:
        file += "/data.json"
    return file

def storePayload(payload):
    # append payload to software data store file
    dataStoreFile = getSoftwareDataStoreFile()

    with open(dataStoreFile, "a") as dsFile:
        dsFile.write(payload + "\n")

def setItem(key, value):
    jsonObj = getSoftwareSessionAsJson()
    jsonObj[key] = value

    content = json.dumps(jsonObj)

    sessionFile = getSoftwareSessionFile()
    with open(sessionFile, 'w') as f:
        f.write(content)

def getItem(key):
    jsonObj = getSoftwareSessionAsJson()

    # return a default of None if key isn't found
    val = jsonObj.get(key, None)

    return val

def getSoftwareSessionAsJson():
    data = None

    sessionFile = getSoftwareSessionFile()
    if (os.path.isfile(sessionFile)):
        content = open(sessionFile).read()

        if (content is not None):
            # json parse the content
            data = json.loads(content)

    if (data is not None):
        return data

    return dict()

def isPastTimeThreshold():
    existingJwt = getItem("jwt")

    thresholdHoursBeforeCheckingAgain = LONG_THRESHOLD_HOURS
    if (existingJwt is None):
        thresholdHoursBeforeCheckingAgain = SHORT_THRESHOLD_HOURS

    lastUpdateTime = getItem("sublime_lastUpdateTime")
    if (lastUpdateTime is None):
        lastUpdateTime = 0

    timeDiffSinceUpdate = trueSecondsNow() - lastUpdateTime

    threshold = SECONDS_PER_HOUR * thresholdHoursBeforeCheckingAgain

    if (timeDiffSinceUpdate < threshold):
        return False

    return True

def isAuthenticated():
    tokenVal = getItem('token')
    jwtVal = getItem('jwt')

    if (tokenVal is None or jwtVal is None):
        showStatus(DASHBOARD_KEYMAP_MSG)
        return False

    response = requestIt("GET", "/users/ping", None)

    if (response is not None):
        return True
    else:
        showStatus(DASHBOARD_KEYMAP_MSG)
        return False

def checkOnline():
    # non-authenticated ping, no need to set the Authorization header
    response = requestIt("GET", "/ping", None)
    if (response is not None):
        return True
    else:
        return False

def sendOfflineData():
    # send the offline data
    dataStoreFile = getSoftwareDataStoreFile()

    payloads = []

    if (os.path.isfile(dataStoreFile)):
        with open(dataStoreFile) as fp:
            for line in fp:
                if (line and line.strip()):
                    line = line.rstrip()
                    # convert to object
                    json_obj = json.loads(line)
                    # convert to json to send
                    payloads.append(json_obj)

    if (payloads):
        response = requestIt("POST", "/data/batch", json.dumps(payloads))

        if (response is not None):
            deleteFile(dataStoreFile)

def deleteFile(file):
    os.remove(file)

def chekUserAuthenticationStatus():
    serverAvailable = checkOnline()
    authenticated = isAuthenticated()
    pastThresholdTime = isPastTimeThreshold()
    existingJwt = getItem("jwt")

    initiateCheckTokenAvailability = True

    if (serverAvailable and
            not authenticated and
            pastThresholdTime):

        # set the last update time so we don't try to ask too frequently
        setItem("sublime_lastUpdateTime", int(trueSecondsNow()))
        confirmWindowOpen = True
        infoMsg = "To see your coding data in Software.com, please log in to your account."
        if (existingJwt):
            # show the Software.com message
            showStatus(DASHBOARD_KEYMAP_MSG)
        else:
            clickAction = sublime.ok_cancel_dialog(infoMsg, LOGIN_LABEL)
            if (clickAction):
                # launch the login view
                launchDashboard()
    elif (not authenticated):
        # show the Software.com message
        showStatus(DASHBOARD_KEYMAP_MSG)
        log("Software.com: user auth check status [online: %s, authenticated: %s, pastThresholdTime: %s]" % (serverAvailable, authenticated, pastThresholdTime))
    else:
        initiateCheckTokenAvailability = False


    if (initiateCheckTokenAvailability):
        # start the token availability timer
        tokenAvailabilityTimer = Timer(60, checkTokenAvailability)
        tokenAvailabilityTimer.start()

def checkTokenAvailability():
    global fetchingUserFromToken

    tokenVal = getItem("token")
    fetchingUserFromToken = True

    foundJwt = False
    if (tokenVal is not None):
        api = '/users/plugin/confirm?token=' + tokenVal
        response = requestIt("GET", api, None)

        if (response is not None):

            json_obj = json.loads(response.read().decode('utf-8'))

            jwt = json_obj.get("jwt", None)
            user = json_obj.get("user", None)
            if (jwt is not None):
                setItem("jwt", jwt)
                setItem("user", user)
                setItem("sublime_lastUpdateTime", int(trueSecondsNow()))
                fetchingUserFromToken = False
                foundJwt = True
            else:
                # check if there's a message
                message = json_obj.get("message", None)
                if (message is not None):
                    log("Software.com: Failed to retrieve session token, reason: \"%s\"" % message)

    if (not foundJwt):
        # start the token availability timer
        tokenAvailabilityTimer = Timer(120, checkTokenAvailability)
        tokenAvailabilityTimer.start()
        showStatus(DASHBOARD_KEYMAP_MSG)


def fetchDailyKpmSessionInfo():
    if (isAuthenticated()):
        api = '/sessions?from=' + str(int(trueSecondsNow())) + '&summary=true'
        response = requestIt("GET", api, None)

        if (response is not None):
            sessions = json.loads(response.read().decode('utf-8'))

            avgKpm = sessions.get("kpm", 0)
            totalMin = sessions.get("minutesTotal", 0)
            sessionTime = ""
            inFlow = sessions.get("inFlow", False)

            if (totalMin == 60):
                sessionTime = "1 hr"
            elif (totalMin > 60):
                # todo: make sure we use a precision of 2
                sessionTime = (totalMin / 60) + " hrs"
            elif (totalMin == 1):
                sessionTime = "1 min"
            else:
                sessionTime = str(totalMin) + " min"

            statusMsg = avgKpm + " KPM, " + sessionTime

            if (totalMin > 0 or avgKpm > 0):
                if (inFlow):
                    # set the status bar message
                    showStatus("<s> " + statusMsg + " ^")
                else:
                    showStatus("<s> " + statusMsg)
            else:
                showStatus(DASHBOARD_KEYMAP_MSG)
    else:
        log("Software.com: Currently not authenticated to fetch daily kpm session info")
        showStatus(DASHBOARD_KEYMAP_MSG)

    # fetch the daily kpm session info in 1 minute
    kpmReFetchTimer = Timer(60, fetchDailyKpmSessionInfo)
    kpmReFetchTimer.start()

def createToken():
    # return os.urandom(16).encode('hex')
    uid = uuid.uuid4()
    return uid.hex

def handlKpmClickedEvent():
    launchDashboard()

def requestIt(method, api, payload):

    log("Software.com: Sending request -- [" + method + ": " + api_endpoint + "" + api + "] payload: %s" % payload)
    
    try:
        connection = None
        if (api_endpoint is TEST_API_ENDPOINT):
            connection = http.client.HTTPConnection(api_endpoint)
        else:
            connection = http.client.HTTPSConnection(api_endpoint)

        headers = {'Content-type': 'application/json', 'User-Agent': USER_AGENT}

        jwt = getItem("jwt")
        if (jwt is not None):
            headers['Authorization'] = jwt

        # make the request
        if (payload is None):
            payload = {}

        connection.request(method, api, payload, headers)

        response = connection.getresponse()
        log("Software.com: " + api + " Response (%d)" % response.status)
        return response
    except (http.client.HTTPException, http.client.CannotSendHeader, ConnectionError, Exception) as ex:
        log("Software.com: " + api + " Network error: %s" % ex)
        return None

def launchDashboard():
    webUrl = launch_url

    existingJwt = getItem("jwt")
    if (existingJwt is None):
        tokenVal = createToken()
        # update the .software data with the token we've just created
        setItem("token", tokenVal)
        webUrl += "/onboarding?token=" + tokenVal

    webbrowser.open(webUrl)

def showStatus(msg):
    """Updates the status bar"""
    try:
        active_window = sublime.active_window()
        if active_window:
            for view in active_window.views():
                view.set_status('software.com', msg)
    except RuntimeError:
        log(msg)













