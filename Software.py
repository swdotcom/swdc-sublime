# Copyright (c) 2018 by Software.com

from threading import Thread, Timer, Event
from package_control import events
from queue import Queue
import webbrowser
import time
import json
import os
import sublime_plugin, sublime
from .lib.SoftwareSession import *
from .lib.SoftwareHttp import *
from .lib.SoftwareUtil import *
from .lib.SoftwareMusic import *
from .lib.SoftwareRepo import *
from .lib.SoftwareSettings import *

DEFAULT_DURATION = 60

# SETTINGS_FILE = 'Software.sublime_settings'
# SETTINGS = {}

PROJECT_DIR = None

check_online_interval_sec = 60 * 10
retry_counter = 0

# update the kpm in
def post_json(json_data):
    # send offline data
    sendOfflineData()

    response = requestIt("POST", "/data", json_data, getItem("jwt"))

    # update status bar after data is sent
    fetchDailyKpmTimer = Timer(5, fetchDailyKpmSessionInfo)
    fetchDailyKpmTimer.start()

    if (isUnauthenticated(response)):
        # save the data to the offline data file
        storePayload(json_data)

    PluginData.reset_source_data()

#
# Background thread used to send data every minute
#
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

#
# kpm payload data structure
#
class PluginData():
    __slots__ = ('source', 'keystrokes', 'start', 'local_start', 'project', 'pluginId', 'version', 'os', 'timezone')
    background_worker = BackgroundWorker(1, post_json)
    active_datas = {}
    line_counts = {}
    send_timer = None

    def __init__(self, project):
        self.source = {}
        self.start = 0
        self.local_start = 0
        self.timezone = ''
        self.keystrokes = 0
        self.project = project
        self.pluginId = PLUGIN_ID
        self.version = VERSION
        now = round(time.time()) - 60
        self.start = now
        self.local_start = getLocalStart()
        self.timezone = getTimezone()
        self.os = getOs()

    def json(self):

        # if self.project['directory'] == 'Unnamed':
        #     self.project = None

        dict_data = {key: getattr(self, key, None)
                     for key in self.__slots__}

        return json.dumps(dict_data)

    # send the kpm info
    def send(self):
        if PluginData.background_worker and self.hasData():
            PluginData.background_worker.queue.put(self.json())

    # check if we have data
    def hasData(self):
        if (self.keystrokes > 0):
            return True
        for fileName in self.source:
            fileInfo = self.source[fileName]
            if (fileInfo['close'] > 0 or
                fileInfo['open'] > 0 or
                fileInfo['paste'] > 0 or
                fileInfo['delete'] > 0 or
                fileInfo['add'] > 0 or
                fileInfo['netkeys'] > 0):
                return True
        return False

    @staticmethod
    def reset_source_data():
        PluginData.send_timer = None

        for dir in PluginData.active_datas:
            keystrokeCountObj = PluginData.active_datas[dir]
            
            # get the lines so we can add that back
            for fileName in keystrokeCountObj.source:
                fileInfo = keystrokeCountObj.source[fileName]
                # add the lines for this file so we can re-use again
                PluginData.line_counts[fileName] = fileInfo["lines"]

            if keystrokeCountObj is not None:
                keystrokeCountObj.source = {}
                keystrokeCountObj.keystrokes = 0
                keystrokeCountObj.project['identifier'] = None
                now = round(time.time()) - 60
                keystrokeCountObj.start = now
                keystrokeCountObj.local_start = getLocalStart()
                keystrokeCountObj.timezone = getTimezone()

    @staticmethod
    def create_empty_payload(fileName, projectName):
        project = {}
        project['directory'] = projectName
        project['name'] = projectName
        return_data = PluginData(project)
        PluginData.active_datas[project['directory']] = return_data
        PluginData.get_file_info_and_initialize_if_none(return_data, fileName)
        return return_data

    @staticmethod
    def get_active_data(view):
        return_data = None
        if view is None or view.window() is None:
            return return_data

        fileName = view.file_name()
        if (fileName is None):
            fileName = "Untitled"

        sublime_variables = view.window().extract_variables()
        project = {}

        # set it to none as a default
        projectFolder = 'Unnamed'

        # set the project folder
        if 'folder' in sublime_variables:
            projectFolder = sublime_variables['folder']
        elif 'file_path' in sublime_variables:
            projectFolder = sublime_variables['file_path']

        # if we have a valid project folder, set the project name from it
        if projectFolder != 'Unnamed':
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
            project['directory'] = 'Unnamed'

        old_active_data = None
        if project['directory'] in PluginData.active_datas:
            old_active_data = PluginData.active_datas[project['directory']]
        
        if old_active_data is None:
            new_active_data = PluginData(project)

            PluginData.active_datas[project['directory']] = new_active_data
            return_data = new_active_data
        else:
            return_data = old_active_data

        fileInfoData = PluginData.get_file_info_and_initialize_if_none(return_data, fileName)

        # This activates the 60 second timer. The callback
        # in the Timer sends the data
        if (PluginData.send_timer is None):
            PluginData.send_timer = Timer(DEFAULT_DURATION, return_data.send)
            PluginData.send_timer.start()

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
            fileName = 'Untitled'
        
        # create the new FileInfo, which will contain a dictionary
        # of fileName and it's metrics
        fileInfoData = PluginData.get_existing_file_info(fileName)

        # "add" = additive keystrokes
        # "netkeys" = add - delete
        # "keys" = add + delete
        # "delete" = delete keystrokes
        if fileInfoData is None:
            fileInfoData = {}
            fileInfoData['paste'] = 0
            fileInfoData['open'] = 0
            fileInfoData['close'] = 0
            fileInfoData['length'] = 0
            fileInfoData['delete'] = 0
            fileInfoData['netkeys'] = 0
            fileInfoData['add'] = 0
            fileInfoData['lines'] = -1
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

    @staticmethod
    def send_initial_payload():
        fileName = "Untitled"
        active_data = PluginData.create_empty_payload(fileName, "Unnamed")
        PluginData.get_file_info_and_initialize_if_none(active_data, fileName)
        fileInfoData = PluginData.get_existing_file_info(fileName)
        fileInfoData['add'] = 1
        active_data.keystrokes = 1
        PluginData.send_all_datas()

class GoToSoftwareCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        launchWebDashboardUrl()

    def is_enabled(self):
        # global SETTINGS
        # return (SETTINGS.get("logged_on", True) is True)
        return (getValue("logged_on", True) is True)

# code_time_login command
class CodeTimeLogin(sublime_plugin.TextCommand):
    def run(self, edit):
        launchLoginUrl()

    def is_enabled(self):
        # global SETTINGS
        # return (SETTINGS.get("logged_on", True) is False)
        return (getValue("logged_on", True) is False)

# Command to launch the code time metrics "launch_code_time_metrics"
class LaunchCodeTimeMetrics(sublime_plugin.TextCommand):
    def run(self, edit):
        launchCodeTimeMetrics()

class SoftwareTopForty(sublime_plugin.TextCommand):
    def run(self, edit):
        webbrowser.open("https://api.software.com/music/top40")

class ToggleStatusBarMetrics(sublime_plugin.TextCommand):
    def run(self, edit):
        # global SETTINGS
        log("toggling status bar metrics")

        # showStatusVal = SETTINGS.get("show_code_time_status", True)
        showStatusVal = getValue("show_code_time_status", True)
        if (showStatusVal):
            # SETTINGS.set("show_code_time_status", False)
            setValue("show_code_time_status", False)
        else:
            # SETTINGS.set("show_code_time_status", True)
            setValue("show_code_time_status", True)


        toggleStatus()


# Command to pause kpm metrics
class PauseKpmUpdatesCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        # global SETTINGS
        log("software kpm metrics paused")
        showStatus("Paused")
        # SETTINGS.set("software_telemetry_on", False)
        setValue("software_telemetry_on", False)

    def is_enabled(self):
        # global SETTINGS
        # return (SETTINGS.get("software_telemetry_on", True) is True)
        return (getValue("software_telemetry_on", True) is True)

# Command to re-enable kpm metrics
class EnableKpmUpdatesCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        # global SETTINGS
        log("software kpm metrics enabled")
        showStatus("Code Time")
        # SETTINGS.set("software_telemetry_on", True)
        setValue("software_telemetry_on", True)

    def is_enabled(self):
        # global SETTINGS
        # return (SETTINGS.get("software_telemetry_on", True) is False)
        return (getValue("software_telemetry_on", True) is False)

# Runs once instance per view (i.e. tab, or single file window)
class EventListener(sublime_plugin.EventListener):
    def on_load_async(self, view):
        fileName = view.file_name()
        if (fileName is None):
            fileName = "Untitled"

        active_data = PluginData.get_active_data(view)

        # get the file info to increment the open metric
        fileInfoData = PluginData.get_file_info_and_initialize_if_none(active_data, fileName)
        if fileInfoData is None:
            return

        fileSize = view.size()
        fileInfoData['length'] = fileSize

        # get the number of lines
        lines = view.rowcol(fileSize)[0]
        fileInfoData['lines'] = lines

        # we have the fileinfo, update the metric
        fileInfoData['open'] += 1
        log('Code Time: opened file %s' % fileName)

        # show last status message
        toggleStatus() 

    def on_close(self, view):
        fileName = view.file_name()
        if (fileName is None):
            fileName = "Untitled"

        active_data = PluginData.get_active_data(view)

        # get the file info to increment the close metric
        fileInfoData = PluginData.get_file_info_and_initialize_if_none(active_data, fileName)
        if fileInfoData is None:
            return

        fileSize = view.size()
        fileInfoData['length'] = fileSize

        # get the number of lines
        lines = view.rowcol(fileSize)[0]
        fileInfoData['lines'] = lines

        # we have the fileInfo, update the metric
        fileInfoData['close'] += 1
        log('Code Time: closed file %s' % fileName)
        
        # show last status message
        toggleStatus() 

    def on_modified_async(self, view):
        global PROJECT_DIR
        # get active data will create the file info if it doesn't exist
        active_data = PluginData.get_active_data(view)
        if active_data is None:
            return

        # add the count for the file
        fileName = view.file_name()
        if (fileName is None):
            fileName = "Untitled"
        fileInfoData = PluginData.get_file_info_and_initialize_if_none(active_data, fileName)
        if fileInfoData is None:
            return

        fileSize = view.size()

        lines = 0
        # try
        # rowcol(point) Calculates the 0-based line and column numbers of the point
        lines = view.rowcol(fileSize)[0]

        prevLines = fileInfoData['lines']
        if (prevLines == 0):

            if (not PluginData.line_counts):
                PluginData.line_counts[fileName] = prevLines

            prevLines = PluginData.line_counts[fileName]
            if (prevLines > 0):
                fileInfoData['lines'] = prevLines

        lineDiff = 0
        if (prevLines > 0):
            lineDiff = lines - prevLines
            if (lineDiff > 0):
                fileInfoData['linesAdded'] += lineDiff
                log('Code Time: linesAdded incremented')
            elif (lineDiff < 0):
                fileInfoData['linesRemoved'] += abs(lineDiff)
                log('Code Time: linesRemoved incremented')

        fileInfoData['lines'] = lines
        
        # subtract the current size of the file from what we had before
        # we'll know whether it's a delete, copy+paste, or kpm.
        currLen = fileInfoData['length']

        charCountDiff = 0
        
        if currLen > 0:
            charCountDiff = fileSize - currLen

        if (not fileInfoData["syntax"]):
            syntax = view.settings().get('syntax')
            # get the last occurance of the "/" then get the 1st occurance of the .sublime-syntax
            # [language].sublime-syntax
            # Packages/Python/Python.sublime-syntax
            syntax = syntax[syntax.rfind('/') + 1:-len(".sublime-syntax")]
            if (syntax):
                fileInfoData["syntax"] = syntax

        PROJECT_DIR = active_data.project['directory']

        # getResourceInfo is a SoftwareUtil function
        if (active_data.project.get("identifier") is None):
            resourceInfoDict = getResourceInfo(PROJECT_DIR)
            if (resourceInfoDict.get("identifier") is not None):
                active_data.project['identifier'] = resourceInfoDict['identifier']
                active_data.project['resource'] = resourceInfoDict

        
        fileInfoData['length'] = fileSize

        if lineDiff == 0 and charCountDiff > 8:
            fileInfoData['paste'] += 1
            log('Code Time: pasted incremented')
        elif lineDiff == 0 and charCountDiff == -1:
            fileInfoData['delete'] += 1
            log('Code Time: delete incremented')
        elif lineDiff == 0 and charCountDiff == 1:
            fileInfoData['add'] += 1
            log('Code Time: KPM incremented')

        # increment the overall count
        if (charCountDiff != 0 or lineDiff != 0):
            active_data.keystrokes += 1

        # update the netkeys and the keys
        # "netkeys" = add - delete
        fileInfoData['netkeys'] = fileInfoData['add'] - fileInfoData['delete']

#
# Iniates the plugin tasks once the it's loaded into Sublime.
#
def plugin_loaded():
    initializeUser()

def initializeUser():
    # check if the session file is there
    serverAvailable = checkOnline()
    fileExists = softwareSessionFileExists()
    if (fileExists is False):
        if (serverAvailable is False):
            if (retry_counter == 0):
                showOfflinePrompt()
            initializeUserTimer = Timer(check_online_interval_sec, initializeUser)
            initializeUserTimer.start()
        else:
            result = createAnonymousUser(serverAvailable)
            if (result is None):
                if (retry_counter == 0):
                    showOfflinePrompt()
                initializeUserTimer = Timer(check_online_interval_sec, initializeUser)
                initializeUserTimer.start()
            else:
                initializePlugin(True)
    else:
        initializePlugin(False)

def initializePlugin(initializedAnonUser):
    PACKAGE_NAME = __name__.split('.')[0]
    log('Code Time: Loaded v%s of package name: %s' % (VERSION, PACKAGE_NAME))
    showStatus("Code Time")

    # global SETTINGS

    # SETTINGS = sublime.load_settings(SETTINGS_FILE)

    setItem("sublime_lastUpdateTime", None)

    # fire off timer tasks (seconds, task)

    sendOfflineDataTimer = Timer(20, sendOfflineData)
    sendOfflineDataTimer.start()

    fetchDailyKpmTimer = Timer(6, fetchDailyKpmSessionInfo)
    fetchDailyKpmTimer.start()

    gatherMusicTimer = Timer(30, gatherMusicInfo)
    gatherMusicTimer.start()

    hourlyTimer = Timer(45, hourlyTimerHandler)
    hourlyTimer.start()

    initializeUserInfo(initializedAnonUser)

def initializeUserInfo(initializedAnonUser):
    getUserStatus()

    if (initializedAnonUser is True):
        showLoginPrompt()
        PluginData.send_initial_payload()

    sendHeartbeat("INITIALIZED")

    # re-fetch user info in another 90 seconds
    checkUserAuthTimer = Timer(90, userStatusHandler)
    checkUserAuthTimer.start()

def userStatusHandler():
    getUserStatus()
    
    # re-fetch user info in another 90 seconds
    checkUserAuthTimer = Timer(90, userStatusHandler)
    checkUserAuthTimer.start()

def plugin_unloaded():
    # clean up the background worker
    PluginData.background_worker.queue.join()

# gather the git commits, repo members, heatbeat ping
def hourlyTimerHandler():
    global PROJECT_DIR

    sendHeartbeat("HOURLY")

    processCommitsTimer = Timer(60, processCommits)
    processCommitsTimer.start()

    # run the handler in another hour
    hourlyTimer = Timer(60 * 60, hourlyTimerHandler)
    hourlyTimer.start()

def processCommits():
    global PROJECT_DIR
    gatherCommits(PROJECT_DIR)

def showOfflinePrompt():
    infoMsg = "Our service is temporarily unavailable. We will try to reconnect again in 10 minutes. Your status bar will not update at this time."
    sublime.message_dialog(infoMsg)



















