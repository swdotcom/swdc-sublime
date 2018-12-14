# Copyright (c) 2018 by Software.com

from threading import Thread, Timer, Event
from queue import Queue
import time
import json
import sublime_plugin, sublime
from .lib.SoftwareSession import *
from .lib.SoftwareHttp import *
from .lib.SoftwareUtil import *
from .lib.SoftwareMusic import *

DEFAULT_DURATION = 60

SETTINGS_FILE = 'Software.sublime_settings'
SETTINGS = {}

# update the kpm info
def post_json(json_data):
    # send offline data
    sendOfflineData()

    response = requestIt("POST", "/data", json_data)

    if (response is None or int(response.status) >= 400):
        # save the data to the offline data file
        storePayload(json_data)
        # check if we need to ask to login
        chekUserAuthenticationStatus()

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
    __slots__ = ('source', 'type', 'keystrokes', 'start', 'local_start', 'project', 'pluginId', 'version', 'timezone')
    background_worker = BackgroundWorker(1, post_json)
    active_datas = {}
    line_counts = {}
    send_timer = None

    def __init__(self, project):
        self.source = {}
        self.type = 'Events'
        self.start = 0
        self.local_start = 0
        self.timezone = ''
        self.keystrokes = 0
        self.project = project
        self.pluginId = 1
        self.version = VERSION
        # set the start and local_start
        now = round(time.time()) - 60
        self.start = now
        # update the local_start using the time.timezone (i.e. 8 hour offset will be 28800)
        self.local_start = now - time.timezone

        try:
            # get the offset and timezone from the time value
            self.timezone = time.strftime('%Z')
        except Exception:
            # unable to get it from the time string, use the tzname[0] (1st tuple)
            self.timezone = time.tzname[0]

    def json(self):

        if self.project['directory'] == 'None':
            self.project = None

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
                keystrokeCountObj.local_start = now - time.timezone


                try:
                    # get the offset and timezone from the time value
                    keystrokeCountObj.timezone = time.strftime('%Z')
                except Exception:
                    # failed getting timezone and offset from time, use tzname
                    try:
                        if time.tzname[1] is None or time.tzname[0] == time.tzname[1]:
                            keystrokeCountObj.timezone = time.tzname[0]
                        else:
                            keystrokeCountObj.timezone = time.tzname[1]
                            # add an hour to the local_start since we're in DST
                            keystrokeCountObj.local_start += (60 * 60)
                    except Exception:
                        keystrokeCountObj.timezone = ''

    @staticmethod
    def get_active_data(view):
        return_data = None
        if view is None or view.window() is None:
            return return_data

        fileName = view.file_name()
        if fileName is None:
            return return_data

        sublime_variables = view.window().extract_variables()
        project = {}

        # set it to none as a default
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
            fileName is 'None'
        
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

class GoToSoftwareCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        launchDashboard()

# Command to pause kpm metrics
class PauseKpmUpdatesCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        log("software kpm metrics paused")
        showStatus("Paused")
        SETTINGS.set("software_telemetry_on", False)

    def is_enabled(self):
        return (SETTINGS.get("software_telemetry_on", True) is True)

# Command to re-enable kpm metrics
class EnableKpmUpdatesCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        log("software kpm metrics enabled")
        showStatus("Software.com")
        SETTINGS.set("software_telemetry_on", True)

    def is_enabled(self):
        return (SETTINGS.get("software_telemetry_on", True) is False)

# Runs once instance per view (i.e. tab, or single file window)
class EventListener(sublime_plugin.EventListener):
    def on_load_async(self, view):
        fileName = view.file_name()

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

        # get the number of lines
        lines = view.rowcol(fileSize)[0]
        fileInfoData['lines'] = lines

        # we have the fileInfo, update the metric
        fileInfoData['close'] += 1
        log('Software.com: closed file %s' % fileName)

    def on_modified_async(self, view):
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
                log('Software.com: linesAdded incremented')
            elif (lineDiff < 0):
                fileInfoData['linesRemoved'] += abs(lineDiff)
                log('Software.com: linesRemoved incremented')

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

        # getResourceInfo is a SoftwareUtil function
        if (active_data.project.get("identifier") is None):
            resourceInfoDict = getResourceInfo(active_data.project['directory'])
            if (resourceInfoDict.get("identifier") is not None):
                active_data.project['identifier'] = resourceInfoDict['identifier']
                active_data.project['resource'] = resourceInfoDict

        
        fileInfoData['length'] = fileSize

        if lineDiff == 0 and charCountDiff > 8:
            fileInfoData['paste'] += 1
            log('Software.com: pasted incremented')
        elif lineDiff == 0 and charCountDiff == -1:
            fileInfoData['delete'] += 1
            log('Software.com: delete incremented')
        elif lineDiff == 0 and charCountDiff == 1:
            fileInfoData['add'] += 1
            log('Software.com: KPM incremented')

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
    log('Software.com: Loaded v%s' % VERSION)
    showStatus("Software.com")

    global SETTINGS
    SETTINGS = sublime.load_settings(SETTINGS_FILE)

    setItem("sublime_lastUpdateTime", None)

    sendOfflineDataTimer = Timer(20, sendOfflineData)
    sendOfflineDataTimer.start()

    fetchDailyKpmTimer = Timer(5, fetchDailyKpmSessionInfo)
    fetchDailyKpmTimer.start()

    gatherMusicTimer = Timer(6, gatherMusicInfo)
    gatherMusicTimer.start()

def plugin_unloaded():
    PluginData.send_all_datas()
    PluginData.background_worker.queue.join()



















