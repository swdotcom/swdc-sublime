# Copyright (c) 2018 by Software.com

from datetime import datetime, timezone, timedelta
from threading import Thread, Timer, Event
from queue import Queue
import webbrowser
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


VERSION = '0.1.1'
PM_URL = 'localhost:19234'
USER_AGENT = 'Software.com Sublime Plugin v' + VERSION
LOGGING = True
DEFAULT_DURATION = 60
was_message_shown = False
was_pm_message_shown = False
was_new_version_shown = False
updates_running = False
downloadingPM = False
PM_BUCKET = "https://s3-us-west-1.amazonaws.com/swdc-plugin-manager/"
PLUGIN_YML_URL = "https://s3-us-west-1.amazonaws.com/swdc-plugins/plugins.yml"
PM_NAME = "software"
NO_PM_FOUND_MSG = "We are having trouble sending data to Software.com. The Plugin Manager may not be installed. Would you like to download it now?"
PLUGIN_TO_PM_ERROR_MSG = "We are having trouble sending data to Software.com. Please make sure the Plugin Manager is running and logged on."
PLUGIN_UPDATE_AVAILABLE_MSG = "A new version of the Software plugin (%s) for Sublime Text is now available. Update now?"
PLUGIN_ZIP_NAME = "swdc-sublime.zip"
PLUGIN_ZIP_URL = "https://s3-us-west-1.amazonaws.com/swdc-plugins/%s" % PLUGIN_ZIP_NAME

MILLIS_PER_DAY = 1000 * 60 * 60 * 24
MILLIS_PER_HOUR = 1000 * 60 * 60
SECONDS_PER_HOUR = 60 * 60
SECONDS_PER_HALF_HOUR = 60 * 30
LONG_THRESHOLD_HOURS = 12
SHORT_THRESHOLD_HOURS = 1
PROD_API_ENDPOINT = "api.software.com"
PROD_URL = "alpha.software.com"
TEST_API_ENDPOINT = "localhost:5000"
TEST_URL = "localhost:3000"


# log the message
def log(message):
    if LOGGING is False:
        return

    print(message)

def secondsNow():
    return datetime.utcnow()

# post the json data
def post_json(json_data):
    global was_message_shown
    global was_pm_message_shown
    global was_new_version_shown
    global updates_running

    error_message_shown = False

    # check to see if there's a new plugin version or now.
    if (not was_new_version_shown):
        updateThread = CheckForUpdates()
        updateThread.start()

    response = requestIt("POST", "/api/v1/data", json_data)
    if (response is None):
        # save the data to the offline data file
        storePayload(json_data)

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

        log('Software.com: background worker initiated')

    def worker(self):
        while True:
            self.target_func(self.queue.get())
            self.queue.task_done()

class PerpetualTimer():

    def __init__(self, t, hFunction):
        self.t = t
        self.hFunction = hFunction
        self.thread = Timer(self.t, self.handle_function)

    def handle_function(self):
        self.hFunction()
        self.thread = Timer(self.t, self.handle_function)
        self.thread.start()

    def start(self):
        self.thread.start()

    def cancel(self):
        self.thread.cancel()

class DownloadPM(Thread):

    # download the PM and install it....
    def run(self):
        downloadingPM = True
        saveAs = getDownloadFilePathName()
        url = getFileUrl()
        downloadPath = getDownloadPath()

        sublime.status_message("Downlaoding Software Desktop")

        try:
            urllib.urlretrieve(url, saveAs)
        except AttributeError:
            urllib.request.urlretrieve(url, saveAs)

        sublime.status_message("Completed downloading Software Desktop")

        sublime.status_message("Installing Software Desktop")
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

        sublime.status_message("Downloading Software Plugin...")

        saveAs = getPluginDataPathFileName()

        log("will save as %s and downloading from url %s" % (saveAs, PLUGIN_ZIP_URL))

        try:
            urllib.urlretrieve(PLUGIN_ZIP_URL, saveAs)
        except AttributeError:
            urllib.request.urlretrieve(PLUGIN_ZIP_URL, saveAs)

        # unzip it now
        sublime.status_message("Extracting Software Plugin...")

        with zipfile.ZipFile(saveAs, "r") as zip_ref:
            zip_ref.extractall(sublime.packages_path())

        sublime.status_message("Completed plugin installation")

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
                fileInfo['keys'] > 0):
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

        if fileInfoData is None:
            fileInfoData = dict()
            fileInfoData['keys'] = 0
            fileInfoData['paste'] = 0
            fileInfoData['open'] = 0
            fileInfoData['close'] = 0
            fileInfoData['length'] = 0
            fileInfoData['delete'] = 0
            keystrokeCount.source[fileName] = fileInfoData

    @staticmethod
    def get_file_info_and_initialize_if_none(keystrokeCount, fileName):
        fileInfoData = PluginData.get_existing_file_info(fileName)
        if fileInfoData is None:
            PluginData.initialize_file_info(keystrokeCount, fileName)
            fileInfoData = PluginData.get_existing_file_info(fileName)

        return fileInfoData

# Runs once instance per view (i.e. tab, or single file window)window..
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
            log('Software.com: delete incremented')
        else:
            fileInfoData['keys'] = fileInfoData['keys'] + 1
            active_data.data = active_data.data + 1
            log('Software.com: KPM incremented')


def plugin_loaded():
    log('Software.com: Loaded v%s' % VERSION)

    t = Timer(10, fetchDailyKpmSessionInfo)
    t.start()

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

    log("setting item into json content: %s" % content)

    sessionFile = getSoftwareSessionFile()
    with open(sessionFile, 'w') as f:
        f.write(content)

def getItem(key):
    jsonObj = getSoftwareSessionAsJson()

    return jsonObj[key]

def getSoftwareSessionAsJson():
    data = None

    sessionFile = getSoftwareSessionFile()
    if (os.path.isfile(sessionFile)):
        content = open(sessionFile).read()
        if (content):
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
    timeDiffSinceUpdate = datetime.now() - lastUpdateTime
    threshold = SECONDS_PER_HOUR * thresholdHoursBeforeCheckingAgain

    if (lastUpdateTime and timeDiffSinceUpdate < threshold):
        return False

    return True

def isAuthenticated():
    log("isAuthenticated: checking if the user is authenticated or not")
    tokenVal = getItem("token")
    jwtVal = getItem("jwt")

    log("isAuthenticated: token val: %s" % tokenVal)

    if (tokenVal is None or jwtVal is None):
        log("isAuthenticated: no token val or jwt, the user is not authenticated")
        return False

    response = requestIt("GET", "/users/ping", None)
    log("isAuthenticated: ping response: %s" % response)
    if (response is not None):
        return True
    else:
        return False

def checkOnline():
    # non-authenticated ping, no need to set the Authorization header
    response = requestIt("GET", "/ping", None)
    if (response is not None):
        return True
    else:
        return False

def chekUserAuthenticationStatus():
    serverAvailable = serverIsAvailable()
    isAuthenticated = isAuthenticated()
    pastThresholdTime = isPastTimeThreshold()
    existingJwt = getItem("jwt")

    log("serverAvailable, isAuthenticated, pastThresholdTime %s %s %s" % (serverAvailable, isAuthenticated, pastThresholdTime))

    if (serverAvailable is not None and
            isAuthenticated is None and
            pastThresholdTime is not None):

        # set the last update time so we don't try to ask too frequently
        setItem("submlime_lastUpdateTime", secondsNow())
        confirmWindowOpen = True
        infoMsg = "To see insights into how you code, please sign in to Software.com."
        if (existingJwt):
            # they have an existing jwt, show the re-login message
            infoMsg = "We are having trouble sending data to Software.com, please sign in to see insights into how you code."

        clickAction = sublime.ok_cancel_dialog(infoMsg, LOGIN_LABEL)
        if (clickAction == True):
            # launch the login view
            tokenVal = createToken()
            setItem("token", tokenVal)
            launchWebUrl(TEST_URL + "/login?token=" + tokenVal)


def checkTokenAvailability():
    api = '/users/plugin/confirm?token=' + tokenVal
    response = requestIt("GET", api, None)

    if (response is not None):
        setItem("jwt", response.data.jwt)
        setItem("user", response.data.user)
        setItem("vscode_lastUpdateTime", secondsNow())
    else:
        # check again in a minute
        tokenAvailTimer = Timer(60, checkTokenAvailability)
        tokenAvailTimer.start()


def launchWebUrl(url):
    log("launchWebUrl: launching " + url)
    # launch the browser with the specifie URL
    webbrowser.open(url)


def fetchDailyKpmSessionInfo():
    if (isAuthenticated() is False):
        log("Software.com: not authenticated to fetch daily kpm session info, trying again later")
        t = Timer(60, fetchDailyKpmSessionInfo)
        t.start()
        return

    api = '/sessions?from=' + secondsNow() + '&summary=true'
    response = requestIt("GET", api, None)
    log("fetchDailyKpmSessionInfo: sessions response: %s" % response)
    t = Timer(60, fetchDailyKpmSessionInfo)
    t.start()

def createToken():
    return os.urandom(16).encode('hex')


def handleKpmClickedEvent():
    # check if we've successfully logged in as this user yet
    existingJwt = getItem("jwt")

    webUrl = TEST_URL
    if (existingJwt is None):
        tokenVal = createToken()
        # update the .software data with the token we've just created
        setItem("token", tokenVal)
        webUrl = TEST_URL + "/login?token=" + tokenVal

    launchWebUrl(webUrl)


def requestIt(method, api, payload):
    log("Software.com: Sending to " + api + " : %s" % payload)
    try:
        connection = http.client.HTTPConnection(TEST_API_ENDPOINT)
        connection.putheader("User-Agent", USER_AGENT)
        connection.putheader("Content-type", 'application/json')

        jwt = getItem("jwt")
        if (jwt is not None):
            connection.putheader("Authorization", jwt)

        if (payload is not None):
            connection.request(method, api, payload)

        if (connection is None):
            log("Software.com: major error, connection was not initialized for api " + api)
            return None

        response = connection.getresponse()
        log("Software.com: " + api + " Response (%d): %s" % (response.status, response.read().decode('utf-8')))
        return response
    except (http.client.HTTPException, ConnectionError) as ex:
        log("Software.com: " + api + " Network error: %s" % ex)
        return None













