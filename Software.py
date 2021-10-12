from threading import Thread, Timer, Event
from package_control import events
from queue import Queue
import webbrowser
import os
import json
import sublime_plugin
import sublime
from datetime import *
from .lib.SoftwareHttp import *
from .lib.SoftwareUtil import *
from .lib.SoftwareRepo import *
from .lib.SoftwareOffline import *
from .lib.SoftwareSettings import *
from .lib.SoftwareWallClock import *
from .lib.SoftwareUserStatus import *
from .lib.SoftwareModels import *
from .lib.SoftwareSessionApp import *
from .lib.SoftwareReportManager import *
from .lib.KpmManager import *
from .lib.Constants import *
from .lib.TrackerManager import *
from .lib.TreePanel import *
from .lib.ui_interactions import UI_INTERACTIONS
from .lib.SlackManager import *
from .lib.OsaScriptUtil import *
from .lib.Logger import *

DEFAULT_DURATION = 60

SETTINGS = {}
retry_counter = 0
activated = False
editor_focused = False
last_focus_event_sent = None

class GoToSoftware(sublime_plugin.TextCommand):
    def run(self, edit):
        launchWebDashboardUrl()
        track_ui_event('view-web-dashboard')

    def is_enabled(self):
        return True

class SwitchAccount(sublime_plugin.TextCommand):
    def run(self, edit):
        switchAccount()

    def is_enabled(self):
        return True

class SoftwareTopForty(sublime_plugin.TextCommand):
    def run(self, edit):
        webbrowser.open("https://api.software.com/music/top40")

    def is_enabled(self):
        return True

class ToggleStatusBarMetrics(sublime_plugin.TextCommand):
    def run(self, edit):
        logIt("toggling status bar metrics")
        toggleStatus()
        track_ui_event('toggle-status-bar-metrics')

class GenerateContributorSummary(sublime_plugin.WindowCommand):
    def run(self):
        projectDir = getProjectDirectory()
        generateContributorSummary(projectDir)

class PauseKpmUpdatesCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        logIt("software kpm metrics paused")
        showStatus("Paused")
        track_ui_event('pause-telemetry')
        # set value must be below track_ui_event, otherwise we will not catch the event!
        setValue("software_telemetry_on", False)

    def is_enabled(self):
        return (getValue("software_telemetry_on", True) is True)

# Command to re-enable kpm metrics
class EnableKpmUpdatesCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        logIt("software kpm metrics enabled")
        showStatus("Code Time")
        setValue("software_telemetry_on", True)
        track_ui_event('enable-telemetry')

    def is_enabled(self):
        return (getValue("software_telemetry_on", True) is False)

class DisconnectSlackCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        disconnectSlackWorkspace()

    def is_enabled(self):
        return True

class ConnectSlackCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        connectSlackWorkspace()

    def is_enabled(self):
        return True

class PauseSlackNotificationsCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        pauseSlackNotifications()

    def is_enabled(self):
        return True

class EnableSlackNotificationsCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        enableSlackNotifications()

    def is_enabled(self):
        return True

class EnterFlowModeActionCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        enableFlowMode()
 
    def is_enabled(self):
        return True

class ExitFlowModeActionCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        exitFlowMode()

    def is_enabled(self):
        return True

class ToggleDarkModeCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        toggleDarkMode()

    def is_enabled(self):
        return True

class ToggleDockCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        toggleDock()

    def is_enabled(self):
        return True

class UpdateSlackStatusMsgCommand(sublime_plugin.TextCommand):
    def run(self, view):
        is_registered = checkRegistration(True)
        if (is_registered is False):
            return

        is_connected = checkSlackConnection(True)
        if (is_connected is False):
            return

        # show the selection to clear or update
        options = ['Clear status', 'Update status']
        self.view.window().show_quick_panel(options, self.on_select_receiver)

    def on_select_receiver(self, index):
        if index == -1:
            return
        if index == 0:
            # clear
            clearSlackStatusText()
        else:
            # update
            self.on_update_request()

    def on_update_request(self):
        self.view.window().show_input_panel("Slack status message", "", self.on_done, None, None)

    def on_done(self, message):
        if not message:
            return
        updateSlackStatusText(message)

def check_and_send_unfocus_event(view):
    global editor_focused
    global last_focus_event_sent

    if (editor_focused is False):
        # set the 'isFocused' value within the SoftwareWallClock to False
        blurWindow()
        if (last_focus_event_sent is not 'unfocus'):
            # this will send off codetime events
            PluginData.send_all_datas()
            track_editor_action(**editor_action_params(view, 'editor', 'unfocus'))
            last_focus_event_sent = 'unfocus'

# Runs once instance per view (i.e. tab, or single file window)
class EventListener(sublime_plugin.EventListener):
    def on_activated_async(self, view):
        focusWindow()
        global editor_focused
        global last_focus_event_sent
        editor_focused = True

        if last_focus_event_sent is not 'focus':
            track_editor_action(**editor_action_params(view, 'editor', 'focus'))
            last_focus_event_sent = 'focus'

        full_file_path = view.file_name()
        if (full_file_path is None):
            full_file_path = UNTITLED

        active_data = PluginData.get_active_data(view)

        # get the file info to increment the open metric
        fileInfoData = PluginData.get_file_info_and_initialize_if_none(
            active_data, full_file_path)
        if fileInfoData is None:
            return

        fileInfoData['length'] = get_character_count(view)
        fileInfoData['lines'] = get_line_count(view)

    # this is called when the plugin initializes and
    # when it's deactivated (put into the background)
    def on_deactivated_async(self, view):
        blurWindow()
        global editor_focused
        editor_focused = False
        Timer(5, check_and_send_unfocus_event, [view]).start()

    def on_load_async(self, view):
        full_file_path = view.file_name()
        if (full_file_path is None):
            full_file_path = UNTITLED

        active_data = PluginData.get_active_data(view)

        # get the file info to increment the open metric
        fileInfoData = PluginData.get_file_info_and_initialize_if_none(
            active_data, full_file_path)
        if fileInfoData is None:
            return

        fileInfoData['length'] = get_character_count(view)

        # get the number of lines
        fileInfoData['lines'] = get_line_count(view)

        # we have the fileinfo, update the metric
        fileInfoData['open'] += 1
        logIt('Code Time: opened file %s' % full_file_path)

        track_editor_action(**editor_action_params(view, 'file', 'open'))

        updateStatusBarWithSummaryData()

    def on_close(self, view):

        full_file_path = view.file_name()
        if (full_file_path is None):
            full_file_path = UNTITLED

        active_data = PluginData.get_active_data(view)

        # get the file info to increment the close metric
        fileInfoData = PluginData.get_file_info_and_initialize_if_none(
            active_data, full_file_path)
        if fileInfoData is None:
            return

        fileInfoData['length'] = get_character_count(view)

        # get the number of lines
        fileInfoData['lines'] = get_line_count(view)

        # we have the fileInfo, update the metric
        fileInfoData['close'] += 1
        logIt('Code Time: closed file %s' % full_file_path)

        Thread(target=track_file_closed, args=(full_file_path, get_syntax(view), get_line_count(view), get_character_count(view))).start()

        updateStatusBarWithSummaryData()

    def on_modified_async(self, view):
        global PROJECT_DIR
        # get active data will create the file info if it doesn't exist
        active_data = PluginData.get_active_data(view)
        if active_data is None or active_data.project is None:
            return

        # add the count for the file
        full_file_path = view.file_name()

        fileInfoData = {}

        if (full_file_path is None):
            full_file_path = UNTITLED

        fileInfoData = PluginData.get_file_info_and_initialize_if_none(active_data, full_file_path)
        if fileInfoData is None:
            return
            
        # project data
        fileInfoData['project_name'] = active_data.project['name'] or NO_PROJ_NAME
        fileInfoData['project_directory'] = active_data.project['directory']

        # file data
        fileInfoData['file_name'] = format_file_name(full_file_path, active_data.project['directory'])
        fileInfoData['file_path'] = format_file_path(full_file_path)

        resource_info = active_data.project.get('resource', {})
        # repo data
        fileInfoData['repo_identifier'] = resource_info.get('identifier', '')
        fileInfoData['repo_name'] = resource_info.get('repo_name', '')
        fileInfoData['repo_owner_id'] = resource_info.get('repo_owner_id', '')
        fileInfoData['git_branch'] = resource_info.get('branch', '')
        fileInfoData['git_tag'] = resource_info.get('tag', '')

        # plugin data
        fileInfoData['plugin_id'] = getPluginId()
        fileInfoData['plugin_version'] = getVersion()
        fileInfoData['plugin_name'] = getPluginName()

        # If file is untitled then log that msg and set file open metrics to 1
        if full_file_path == UNTITLED:
            # logIt("Code Time: opened file untitled")
            fileInfoData['open'] = 1
        else:
            pass

        if fileInfoData is None:
            return

        fileSize = get_character_count(view)
        lines = get_line_count(view)

        fileInfoData['keystrokes'] += 1

        prevLines = fileInfoData['lines']
        if (prevLines == 0):
            if (PluginData.line_counts.get(full_file_path) is None):
                PluginData.line_counts[full_file_path] = prevLines
            prevLines = PluginData.line_counts[full_file_path]

        document_change_counts_and_type = analyzeDocumentChanges(fileInfoData, view)

        if(fileInfoData.get('document_change_info', None) is None):
            fileInfoData['document_change_info'] = {
                'lines_added': document_change_counts_and_type['lines_added'],
                'lines_deleted': document_change_counts_and_type['lines_deleted'],
                'characters_added':  document_change_counts_and_type['characters_added'],
                'characters_deleted': document_change_counts_and_type['characters_deleted'],
                'single_deletes': 0,
                'is_net_change': False,
                'multi_deletes': 0,
                'single_adds': 0,
                'multi_adds': 0,
                'auto_indents': 0,
                'replacements': 0,
            }
        else:
            fileInfoData['document_change_info']['lines_added'] += document_change_counts_and_type['lines_added']
            fileInfoData['document_change_info']['lines_deleted'] += document_change_counts_and_type['lines_deleted']
            fileInfoData['document_change_info']['characters_added'] += document_change_counts_and_type['characters_added']
            fileInfoData['document_change_info']['characters_deleted'] += document_change_counts_and_type['characters_deleted']

        change_type = document_change_counts_and_type['change_type']
        if (change_type == "single_delete"):
            fileInfoData['document_change_info']['single_deletes'] +=1
        if (change_type == "multi_delete"):
            fileInfoData['document_change_info']['is_net_change'] = True
            fileInfoData['document_change_info']['multi_deletes'] += 1
        if (change_type == "single_add"):
            fileInfoData['document_change_info']['single_adds'] += 1
        if (change_type == "multi_add"):
            fileInfoData['document_change_info']['is_net_change'] = True
            fileInfoData['document_change_info']['multi_adds'] += 1
        if (change_type == "auto_indent"):
            fileInfoData['document_change_info']['auto_indents'] += 1
        if (change_type == "replacement"):
            fileInfoData['document_change_info']['replacements'] += 1
        if (change_type == "net_zero_change"):
            fileInfoData['document_change_info']['is_net_change'] = True

        lineDiff = 0
        if (prevLines > 0):
            lineDiff = lines - prevLines
            if (lineDiff > 0):
                fileInfoData['linesAdded'] += lineDiff
                logIt('Code Time: linesAdded incremented')
            elif (lineDiff < 0):
                fileInfoData['linesRemoved'] += abs(lineDiff)
                logIt('Code Time: linesRemoved incremented')

        if (lineDiff > 0):
            fileInfoData['linesAdded'] += lineDiff
            logIt('Code Time: linesAdded incremented')
        elif (lineDiff < 0):
            fileInfoData['linesRemoved'] += abs(lineDiff)
            logIt('Code Time: linesRemoved incremented')

        fileInfoData['lines'] = lines

        # subtract the current size of the file from what we had before

        currLen = fileInfoData['length']

        charCountDiff = 0

        if currLen > 0 or currLen == 0:
            # currLen > 0 only worked for existing file, currlen==0 will work for new file
            charCountDiff = fileSize - currLen

        if (not fileInfoData["syntax"]):
            fileInfoData["syntax"] = get_syntax(view)

        PROJECT_DIR = active_data.project['directory']

        # getResourceInfo is a SoftwareUtil function
        if (active_data.project.get("identifier") is None):
            resourceInfoDict = getResourceInfo(PROJECT_DIR)
            if (resourceInfoDict.get("identifier") is not None):
                active_data.project['identifier'] = resourceInfoDict['identifier']
                active_data.project['resource'] = resourceInfoDict

        fileInfoData['length'] = fileSize

        if lineDiff == 0 and charCountDiff > 8:
            fileInfoData['chars_pasted'] += charCountDiff
            fileInfoData['paste'] += 1
            logIt('Code Time: pasted incremented')
        elif lineDiff == 0 and charCountDiff == -1:
            fileInfoData['delete'] += 1
            logIt('Code Time: delete incremented')
        elif lineDiff == 0 and charCountDiff == 1:
            fileInfoData['add'] += 1
            logIt('Code Time: KPM incremented')

        # increment the overall count
        if (charCountDiff != 0 or lineDiff != 0):
            active_data.keystrokes += 1

        # update the netkeys and the keystrokes
        # "netkeys" = add - delete
        fileInfoData['netkeys'] = fileInfoData['add'] - fileInfoData['delete']

        updateStatusBarWithSummaryData()

# Iniates the plugin tasks once the it's loaded into Sublime.
def plugin_loaded():
    initializeUser()

def plugin_unloaded():
	track_editor_action(
        jwt=getJwt(),
        entity='editor',
        type='deactivate',
        plugin_id=getPluginId(),
        plugin_version=getVersion(),
        plugin_name=getPluginName()
    )

def initializeUser():
    # check if the session file is there
    jwt = getItem("jwt")

    if (jwt is None):
        result = createAnonymousUser()
        # init
        initializePlugin(True)

    # init
    initializePlugin(False)

    track_editor_action(
        jwt=getJwt(),
        entity='editor',
        type='activate',
        plugin_id=getPluginId(),
        plugin_version=getVersion(),
        plugin_name=getPluginName()
    )

def initializePlugin(initializedAnonUser):
    name = getPluginName()
    version = getVersion()
    logIt('Code Time: Loaded v%s of package name: %s' % (version, name))
    showStatus("Code Time")

    setItem("sublime_lastUpdateTime", None)

    displayReadmeIfNotExists(False)

    wallClockMgrInit()

    # this check is required before the commits timer is started
    initializeUserPreferencesAsync()

    initialized = getItem('sublime_CtInit')
    if not initialized:
        setItem('sublime_CtInit', True)

    updateSessionSummaryFromServerAsync()

def plugin_unloaded():
    # clean up the background worker
    PluginData.background_worker.queue.join()

def showOfflinePrompt():
    infoMsg = SERVICE_NOT_AVAIL
    sublime.message_dialog(infoMsg)

def track_ui_event(command_lookup_key):
    global UI_INTERACTIONS
    try:
        track_ui_interaction(
            jwt=getJwt(),
            plugin_id=getPluginId(),
            plugin_version=getVersion(),
            plugin_name=getPluginName(),
            **UI_INTERACTIONS[command_lookup_key]
        )
    except Exception as ex:
        print("Cannot track ui interaction for command: %s" % ex)

def track_file_closed(full_file_path, syntax, line_count, character_count):
    track_editor_action(**editor_action_params(
        None,
        'file',
        'close',
        full_file_path=full_file_path,
        syntax=syntax,
        line_count=line_count,
        character_count=character_count
    ))

def editor_action_params(view, entity, action_type, **kwargs):
    project_directory = getProjectDirectory()
    project_name = os.path.basename(project_directory)
    resource_info = getResourceInfo(project_directory)
    full_file_path = kwargs.get('full_file_path', "Untitled")
    syntax = kwargs.get('syntax', "")
    line_count = kwargs.get('line_count', 0)
    character_count = kwargs.get('character_count', 0)

    if(view):
        full_file_path = view.file_name()
        syntax = get_syntax(view)
        line_count = get_line_count(view)
        character_count = get_character_count(view)

    return {
        'jwt': getJwt(),
        'entity': entity,
        'type': action_type,
        'file_name': format_file_name(full_file_path, project_directory),
        'file_path': format_file_path(full_file_path),
        'syntax': syntax,
        'line_count': line_count,
        'character_count': character_count,
        'project_name': project_name,
        'project_directory': project_directory,
        'repo_identifier': resource_info.get('identifier', ''),
        'repo_name': resource_info.get('repo_name', ''),
        'owner_id': resource_info.get('repo_owner_id', ''),
        'git_branch': resource_info.get('branch', ''),
        'git_tag': resource_info.get('tag', ''),
        'plugin_id': getPluginId(),
        'plugin_version': getVersion(),
        'plugin_name': getPluginName()
    }
