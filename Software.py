from threading import Thread, Timer, Event
from package_control import events
from queue import Queue
import webbrowser
import time as timeModule
import os
import json
import sublime_plugin
import sublime
from datetime import *
from .lib.SoftwareHttp import *
from .lib.SoftwareUtil import *
from .lib.SoftwareMusic import *
from .lib.SoftwareRepo import *
from .lib.SoftwareOffline import *
from .lib.SoftwareSettings import *
from .lib.SoftwareTree import *
from .lib.SoftwareWallClock import *
from .lib.SoftwareDashboard import *
from .lib.SoftwareUserStatus import *
from .lib.SoftwareModels import *
from .lib.SoftwareSessionApp import *
from .lib.SoftwareReportManager import *
from .lib.KpmManager import *
from .lib.Constants import *
from .lib.TrackerManager import *
from .lib.ui_interactions import UI_INTERACTIONS

DEFAULT_DURATION = 60

SETTINGS = {}
check_online_interval_sec = 60 * 10
retry_counter = 0
activated = False

class GoToSoftware(sublime_plugin.TextCommand):
    def run(self, edit):
        launchWebDashboardUrl()
        track_ui_event('view-web-dashboard')

    def is_enabled(self):
        return (getValue("logged_on", True) is True)

# Command to launch the code time metrics "launch_code_time_metrics"
class LaunchCodeTimeMetrics(sublime_plugin.TextCommand):
    def run(self, edit):
        codetimemetricsthread = Thread(target=launchCodeTimeMetrics)
        codetimemetricsthread.start()
        track_ui_event('view-dashboard')


class ShowTreeView(sublime_plugin.WindowCommand):
    def run(self):
        setShouldOpen(True)
        refreshTreeView()
        track_ui_event('show-tree-view')

class SoftwareTopForty(sublime_plugin.TextCommand):
    def run(self, edit):
        webbrowser.open("https://api.software.com/music/top40")

    def is_enabled(self):
        return (getValue("online", True) is True)


class ToggleStatusBarMetrics(sublime_plugin.TextCommand):
    def run(self, edit):
        log("toggling status bar metrics")
        toggleStatus()
        track_ui_event('toggle-status-bar-metrics')

class ForceUpdateSessionSummary(sublime_plugin.WindowCommand):
    def run(self, isNewDay):
        updateSessionSummaryFromServer(isNewDay)


class GenerateContributorSummary(sublime_plugin.WindowCommand):
    def run(self):
        projectDir = getProjectDirectory()
        generateContributorSummary(projectDir)

class PauseKpmUpdatesCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        log("software kpm metrics paused")
        showStatus("Paused")
        track_ui_event('pause-telemetry')
        # set value must be below track_ui_event, otherwise we will not catch the event!
        setValue("software_telemetry_on", False)

    def is_enabled(self):
        return (getValue("software_telemetry_on", True) is True)

# Command to re-enable kpm metrics
class EnableKpmUpdatesCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        log("software kpm metrics enabled")
        showStatus("Code Time")
        setValue("software_telemetry_on", True)
        track_ui_event('enable-telemetry')

    def is_enabled(self):
        return (getValue("software_telemetry_on", True) is False)


editor_focused = False
last_focus_event_sent = None

def check_and_send_unfocus_event(view):
    global editor_focused
    global last_focus_event_sent

    if(editor_focused is False and last_focus_event_sent is not 'unfocus'):
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
        log('Code Time: opened file %s' % full_file_path)

        track_editor_action(**editor_action_params(view, 'file', 'open'))

        # show last status message
        redisplayStatus()

    # TODO: if tree view is closed, all groups should move left once space
    def on_close(self, view):
        full_file_path = view.file_name()
        if (full_file_path is None):
            full_file_path = UNTITLED

        if view.name() == CODETIME_TREEVIEW_NAME:
            handleCloseTreeView()

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
        log('Code Time: closed file %s' % full_file_path)
        
        Thread(target=track_file_closed, args=(full_file_path, get_syntax(view), get_line_count(view), get_character_count(view))).start()

        # show last status message
        redisplayStatus()

    def on_modified_async(self, view):
        global PROJECT_DIR
        # get active data will create the file info if it doesn't exist
        active_data = PluginData.get_active_data(view)
        if active_data is None:
            return

        # add the count for the file
        full_file_path = view.file_name()

        fileInfoData = {}

        if (full_file_path is None):
            full_file_path = UNTITLED

        fileInfoData = PluginData.get_file_info_and_initialize_if_none(active_data, full_file_path)
        # project data
        fileInfoData['project_name'] = active_data.project['name']
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
            # log("Code Time: opened file untitled")
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
                log('Code Time: linesAdded incremented')
            elif (lineDiff < 0):
                fileInfoData['linesRemoved'] += abs(lineDiff)
                log('Code Time: linesRemoved incremented')

        if (lineDiff > 0):
            fileInfoData['linesAdded'] += lineDiff
            log('Code Time: linesAdded incremented')
        elif (lineDiff < 0):
            fileInfoData['linesRemoved'] += abs(lineDiff)
            log('Code Time: linesRemoved incremented')

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

        # update the netkeys and the keystrokes
        # "netkeys" = add - delete
        fileInfoData['netkeys'] = fileInfoData['add'] - fileInfoData['delete']
# Iniates the plugin tasks once the it's loaded into Sublime.
def plugin_loaded():
    initializeUser()
    fetch_user_hashed_values()
    track_editor_action(
        jwt=getJwt(),
        entity='editor',
        type='activate',
        plugin_id=getPluginId(),
        plugin_version=getVersion(),
        plugin_name=getPluginName()
    )

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
    serverAvailable = serverIsAvailable()
    fileExists = softwareSessionFileExists()
    jwt = getItem("jwt")

    if (fileExists is False or jwt is None):
        if (serverAvailable is False):
            if (retry_counter == 0):
                showOfflinePrompt()
            initializeUserTimer = Timer(
                check_online_interval_sec, initializeUser)
            initializeUserTimer.start()
        else:
            result = createAnonymousUser()
            if (result is None):
                if (retry_counter == 0):
                    showOfflinePrompt()
                initializeUserTimer = Timer(
                    check_online_interval_sec, initializeUser)
                initializeUserTimer.start()
            else:
                initializePlugin(True, serverAvailable)
    else:
        initializePlugin(False, serverAvailable)


def initializePlugin(initializedAnonUser, serverAvailable):
    name = getPluginName()
    version = getVersion()
    log('Code Time: Loaded v%s of package name: %s' % (version, name))
    showStatus("Code Time")

    setItem("sublime_lastUpdateTime", None)

    wallClockMgrInit()
    dashboardMgrInit()

    # this check is required before the commits timer is started
    initializeUserPreferences()

    # fire off timer tasks (seconds, task)

    setOnlineStatusTimer = Timer(5, setOnlineStatus)
    setOnlineStatusTimer.start()

    oneMin = 60

    setInterval(sendOfflineData, oneMin * 15)
    setInterval(lambda: sendHeartbeat('HOURLY'), oneMin * 60)
    setInterval(sendOfflineEvents, oneMin * 40)
    setInterval(getUsersOfFirstProject, oneMin * 50)

    # only send commit data if setting is enabled
    disable_git_data = getItem("disableGitData")
    if not disable_git_data:
        setInterval(getHistoricalCommitsOfFirstProject, oneMin * 45)
        getCommitsTimer = Timer(oneMin * 2, getHistoricalCommitsOfFirstProject)
        getCommitsTimer.start()

    updateStatusBarWithSummaryData()

    offlineTimer = Timer(oneMin, sendOfflineData)
    offlineTimer.start()

    getUsersTimer = Timer(oneMin * 3, getUsersOfFirstProject)
    getUsersTimer.start()

    sendEventsTimer = Timer(oneMin * 4, sendOfflineEvents)
    sendEventsTimer.start()

    updateOnlineStatusTimer = Timer(0.25, updateOnlineStatus)
    updateOnlineStatusTimer.start()

    initializeUserThread = Thread(
        target=initializeUserInfo, args=[initializedAnonUser])
    initializeUserThread.start()


def initializeUserInfo(initializedAnonUser):
    getUserStatus()

    initialized = getItem('sublime_CtInit')
    if not initialized:
        setItem('sublime_CtInit', True)
        updateSessionSummaryFromServer()
        refreshTreeView()
        PluginData.send_initial_payload()
        sendHeartbeat('INSTALLED')

def plugin_unloaded():
    # clean up the background worker
    PluginData.background_worker.queue.join()


def showOfflinePrompt():
    infoMsg = "Our service is temporarily unavailable. We will try to reconnect again in 10 minutes. Your status bar will not update at this time."
    sublime.message_dialog(infoMsg)


def setOnlineStatus():
    online = serverIsAvailable()
    # log("Code Time: Checking online status...")
    if (online is True):
        setValue("online", True)
        # log("Code Time: Online")
    else:
        setValue("online", False)
        # log("Code Time: Offline")

    # run the check in another 1 minute
    timer = Timer(60 * 10, setOnlineStatus)
    timer.start()


def getUsersOfFirstProject():
    getRepoUsers(getProjectDirectory())


def getHistoricalCommitsOfFirstProject():
    getHistoricalCommits(getProjectDirectory())

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
