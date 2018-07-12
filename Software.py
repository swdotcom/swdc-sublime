# Copyright (c) 2018 by Software.com

from datetime import datetime, timezone, timedelta
from threading import Thread, Timer, Event
from queue import Queue
import json
import sublime_plugin, sublime
from .lib.SoftwareSession import *
from .lib.SoftwareHttp import *
from .lib.SoftwareUtil import *

DEFAULT_DURATION = 60
SETTINGS_FILE = 'Software.sublime-settings'
SETTINGS = {}

# update the kpm info.
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
    __slots__ = ('source', 'type', 'data', 'start', 'end', 'send_timer', 'project', 'pluginId', 'version')
    convert_to_seconds = ('start', 'end')
    json_ignore = ('send_timer',)
    background_worker = BackgroundWorker(1, post_json)
    active_datas = {}

    def __init__(self, project):
        self.source = {}
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

    # send the kpm info
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
                keystrokeCountObj.source = {}
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
            fileInfoData = {}
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

class GoToSoftwareCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        launchDashboard()

# Command to pause kpm updates
class PauseKpmUpdatesCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        log("software kpm updates paused")
        SETTINGS.set("software_telemetry_on", False)

    def is_enabled(self):
        return (SETTINGS.get("software_telemetry_on", True) is True)

# Command to re-enable kpm updates
class EnableKpmUpdatesCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        log("software kpm updates enabled")
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
        # try:
        # rowcol(point) Calculates the 0-based line and column numbers of the point
        lines = view.rowcol(fileSize)[0]

        prevLines = fileInfoData['lines']
        fileInfoData['lines'] = lines

        lineDiff = lines - prevLines
        if (lineDiff > 0):
            fileInfoData['linesAdded'] = fileInfoData['linesAdded'] + lineDiff
            log('Software.com: lines added incremented')
        elif (lineDiff < 0):
            fileInfoData['linesRemoved'] = fileInfoData['linesRemoved'] + lineDiff
            log('Software.com: lines removed incremented')
        
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

    global SETTINGS
    SETTINGS = sublime.load_settings(SETTINGS_FILE)

    sendOfflineDataTimer = Timer(20, sendOfflineData)
    sendOfflineDataTimer.start()

    sendOfflineDataTimer = Timer(30, fetchDailyKpmSessionInfo)
    sendOfflineDataTimer.start()

def plugin_unloaded():
    PluginData.send_all_datas()
    PluginData.background_worker.queue.join()



















