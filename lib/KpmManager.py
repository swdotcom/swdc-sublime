from threading import Thread, Timer, Event
from queue import Queue
import sublime_plugin, sublime
from .SoftwareOffline import *
from .SoftwarePayload import *
from .SoftwareUtil import *
from .TimeSummaryData import *

DEFAULT_DURATION = 60

# payload trigger to store it for later.
def post_json(json_data):
    # save the data to the offline data file
    storePayload(json.loads(json_data))

    PluginData.reset_source_data()

#
# Background thread used to send data every minute.
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
    __slots__ = ('source', 'keystrokes', 'start', 'local_start', 'project', 'pluginId', 'version', 'os', 'timezone', 'cumulative_editor_seconds', 'cumulative_session_seconds', 'elapsed_seconds')
    background_worker = BackgroundWorker(1, post_json)
    active_datas = {} # active projects, where each entry is a project directory
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
        self.timezone = getTimezone()
        self.os = getOs()
        self.cumulative_editor_seconds = 0
        self.cumulative_session_seconds = 0
        self.elapsed_seconds = 0

    def json(self):

        # make sure all file end times are set

        dict_data = {key: getattr(self, key, None)
                     for key in self.__slots__}

        return json.dumps(dict_data)

    # send the kpm info
    def send(self):
        # check if it has data
        if PluginData.background_worker and self.hasData():
            PluginData.endUnendedFileEndTimes()
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
    def hasKeystrokeData():
        for dir in PluginData.active_datas:
            keystrokeCountObj = PluginData.active_datas[dir]
            if keystrokeCountObj is not None and keystrokeCountObj.source is not None:
                # check if the source object is empty
                if bool(keystrokeCountObj.source):
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
                PluginData.line_counts[fileName] = fileInfo.get("lines", 0)

            if keystrokeCountObj is not None:
                keystrokeCountObj.source = {}
                keystrokeCountObj.keystrokes = 0
                keystrokeCountObj.project['identifier'] = None
                keystrokeCountObj.timezone = getTimezone()

    @staticmethod
    def create_empty_payload(fileName, projectName):
        project = Project()
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
            fileName = UNTITLED

        sublime_variables = view.window().extract_variables()
        project = Project()

        # set it to none as a default
        projectFolder = NO_PROJ_NAME

        # set the project folder
        if 'folder' in sublime_variables:
            projectFolder = sublime_variables['folder']
        elif 'file_path' in sublime_variables:
            projectFolder = sublime_variables['file_path']

        # if we have a valid project folder, set the project name from it
        if projectFolder != NO_PROJ_NAME:
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
            project['directory'] = NO_PROJ_NAME
            project['name'] = UNTITLED

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

    # ...
    @staticmethod
    def get_existing_file_info(fileName):
        fileInfoData = None

        # Get the FileInfo object within the KeystrokesCount object
        # based on the specified fileName.
        for dir in PluginData.active_datas:
            keystrokeCountObj = PluginData.active_datas[dir]
            if keystrokeCountObj is not None:
                hasExistingKeystrokeObj = True
                # we have a keystroke count object, get the fileInfo
                if keystrokeCountObj.source is not None and fileName in keystrokeCountObj.source:
                    # set the fileInfoData we'll return the calling def
                    fileInfoData = keystrokeCountObj.source[fileName]
                else:
                    # end the other files end times
                    for fileName in keystrokeCountObj.source:
                        fileInfo = keystrokeCountObj.source[fileName]
                        nowTimes = getNowTimes()
                        fileInfo["end"] = nowTimes['nowInSec']
                        fileInfo["local_end"] = nowTimes['localNowInSec']

        return fileInfoData

    @staticmethod
    def endUnendedFileEndTimes():
        for dir in PluginData.active_datas:
            keystrokeCountObj = PluginData.active_datas[dir]
            if keystrokeCountObj is not None and keystrokeCountObj.source is not None:
                for fileName in keystrokeCountObj.source:
                    fileInfo = keystrokeCountObj.source[fileName]
                    if (fileInfo.get("end", 0) == 0):
                        td = getTodayTimeDataSummary(keystrokeCountObj.project)
                        editorSeconds = max(td['editor_seconds'], td['session_seconds']) if td else 60

                        nowTimes = getNowTimes()
                        fileInfo["end"] = nowTimes['nowInSec']
                        fileInfo["local_end"] = nowTimes['localNowInSec']

    @staticmethod
    def send_all_datas():
        for dir in PluginData.active_datas:
            PluginData.active_datas[dir].send()

    #.........
    @staticmethod
    def initialize_file_info(keystrokeCount, fileName):
        if keystrokeCount is None:
            return

        if fileName is None or fileName == '':
            fileName = UNTITLED
        
        # create the new FileInfo, which will contain a dictionary
        # of fileName and it's metrics
        fileInfoData = PluginData.get_existing_file_info(fileName)

        nowTimes = getNowTimes()

        if keystrokeCount.start == 0:
            keystrokeCount.start = nowTimes['nowInSec']
            keystrokeCount.local_start = nowTimes['localNowInSec']
            keystrokeCount.timezone = getTimezone()

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
            fileInfoData['keystrokes'] = 0
            fileInfoData['add'] = 0
            fileInfoData['lines'] = -1
            fileInfoData['linesAdded'] = 0
            fileInfoData['linesRemoved'] = 0
            fileInfoData['syntax'] = ""
            fileInfoData['start'] = nowTimes['nowInSec']
            fileInfoData['local_start'] = nowTimes['localNowInSec']
            fileInfoData['end'] = 0
            fileInfoData['local_end'] = 0
            keystrokeCount.source[fileName] = fileInfoData
        else:
            # update the end and local_end to zero since the file is still getting modified
            fileInfoData['end'] = 0
            fileInfoData['local_end'] = 0

    @staticmethod
    def get_file_info_and_initialize_if_none(keystrokeCount, fileName):
        fileInfoData = PluginData.get_existing_file_info(fileName)
        if fileInfoData is None:
            PluginData.initialize_file_info(keystrokeCount, fileName)
            fileInfoData = PluginData.get_existing_file_info(fileName)

        return fileInfoData

    @staticmethod 
    def send_initial_payload():
        fileName = UNTITLED
        active_data = PluginData.create_empty_payload(fileName, NO_PROJ_NAME)
        active_data.keystrokes = 1
        nowTimes = getNowTimes()
        start = nowTimes['nowInSec'] - 60
        local_start = nowTimes['localNowInSec'] - 60
        active_data.start = start 
        active_data.local_start = local_start 
        fileInfo = {
            "add": 1,
            "keystrokes": 1,
            "start": start,
            "local_start": local_start, 
            "paste": 0,
            "open": 0,
            "close": 0,
            "length": 0,
            "delete": 0,
            "netkeys": 0,
            "lines": -1,
            "linesAdded": 0,
            "linesRemoved": 0,
            "syntax": "",
            "end": 0,
            "local_end": 0
        }
        active_data.source[fileName] = fileInfo 

        dict_data = {key: getattr(active_data, key, None)
                     for key in active_data.__slots__}
        postBootstrapPayload(dict_data)
