from threading import Thread, Timer, Event
from queue import Queue
import sublime_plugin, sublime
from .SoftwareOffline import *
from .SoftwareUtil import *
from .SoftwareHttp import *
from .Constants import *
from .CommonUtil import *
from .TrackerManager import *

DEFAULT_DURATION = 60

# payload trigger to store it for later.
def post_json(json_data):
    # save the data to the offline data file
    processAndAggregateData(json.loads(json_data))

    jwt = getJwt()
    for filepath, payload in json.loads(json_data)['source'].items():
        track_codetime_event(
            jwt=jwt,
            keystrokes=payload['keystrokes'],
            lines_added=payload.get('document_change_info', {}).get('lines_added', 0),
            lines_deleted=payload.get('document_change_info', {}).get('lines_deleted', 0),
            characters_added=payload.get('document_change_info', {}).get('characters_added', 0),
            characters_deleted=payload.get('document_change_info', {}).get('characters_deleted', 0),
            single_deletes=payload.get('document_change_info', {}).get('single_deletes', 0),
            multi_deletes=payload.get('document_change_info', {}).get('multi_deletes', 0),
            single_adds=payload.get('document_change_info', {}).get('single_adds', 0),
            multi_adds=payload.get('document_change_info', {}).get('multi_adds', 0),
            auto_indents=payload.get('document_change_info', {}).get('auto_indents', 0),
            replacements=payload.get('document_change_info', {}).get('replacements', 0),
            is_net_change=payload.get('document_change_info', {}).get('is_net_change', False),
            start_time=payload['local_start'],
            end_time=payload['local_end'],
            file_path=payload['file_path'],
            file_name=payload['file_name'],
            syntax=payload['syntax'],
            line_count=payload['lines'],
            character_count=payload['length'],
            project_name=payload['project_name'],
            project_directory=payload['project_directory'],
            plugin_id=payload['plugin_id'],
            plugin_version=payload['plugin_version'],
            plugin_name=payload['plugin_name'],
            repo_identifier=payload['repo_identifier'],
            repo_name=payload['repo_name'],
            owner_id=payload.get('repo_owner_id', None),
            git_branch=payload['git_branch'],
            git_tag=payload['git_tag']
        )


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
    __slots__ = ('source', 'keystrokes', 'start', 'local_start', 'project', 'pluginId', 'version', 'os', 'timezone', 'elapsed_seconds')
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
        self.version = getVersion()
        self.timezone = getTimezone()
        self.os = getOs()
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

    # Return True if a keystroke payload has keystrokes
    @staticmethod
    def hasKeystrokeData():
        for dir in PluginData.active_datas:
            keystrokeCountObj = PluginData.active_datas[dir]
            if keystrokeCountObj is not None and keystrokeCountObj.keystrokes is not None:
                if keystrokeCountObj.keystrokes > 0:
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
            if 'project_name' in sublime_variables and sublime_variables['project_name']:
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
            fileInfoData['lines'] = 0
            fileInfoData['linesAdded'] = 0
            fileInfoData['linesRemoved'] = 0
            fileInfoData['syntax'] = ""
            fileInfoData['start'] = nowTimes['nowInSec']
            fileInfoData['local_start'] = nowTimes['localNowInSec']
            fileInfoData['end'] = 0
            fileInfoData['local_end'] = 0
            fileInfoData['chars_pasted'] = 0
            fileInfoData['project_name'] = NO_PROJ_NAME
            fileInfoData['project_directory'] = ''
            fileInfoData['file_name'] = ''
            fileInfoData['file_path'] = ''
            fileInfoData['plugin_id'] = getPluginId()
            fileInfoData['plugin_version'] = getVersion()
            fileInfoData['plugin_name'] = getPluginName()
            fileInfoData['repo_identifier'] = ''
            fileInfoData['repo_name'] = ''
            fileInfoData['repo_owner_id'] = ''
            fileInfoData['git_branch'] = ''
            fileInfoData['git_tag'] = ''
            fileInfoData['document_change_info'] = {}
            fileInfoData['document_change_info']['lines_added'] = 0
            fileInfoData['document_change_info']['lines_deleted'] = 0
            fileInfoData['document_change_info']['characters_added'] = 0
            fileInfoData['document_change_info']['characters_deleted'] = 0
            fileInfoData['document_change_info']['single_deletes'] = 0
            fileInfoData['document_change_info']['multi_deletes'] = 0
            fileInfoData['document_change_info']['single_adds'] = 0
            fileInfoData['document_change_info']['multi_adds'] = 0
            fileInfoData['document_change_info']['auto_indents'] = 0
            fileInfoData['document_change_info']['replacements'] = 0
            fileInfoData['document_change_info']['is_net_change'] = False
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
