from threading import Thread, Timer, Event
from package_control import events
from queue import Queue
import webbrowser
import time as timeModule
from datetime import *
import json
import os
import sublime_plugin, sublime
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

DEFAULT_DURATION = 60

SETTINGS = {}

check_online_interval_sec = 60 * 10
retry_counter = 0
activated = False 

class GoToSoftware(sublime_plugin.TextCommand):
    def run(self, edit):
        launchWebDashboardUrl()

    def is_enabled(self):
        return (getValue("logged_on", True) is True)

# Command to launch the code time metrics "launch_code_time_metrics"
class LaunchCodeTimeMetrics(sublime_plugin.TextCommand):
    def run(self, edit):
        codetimemetricsthread = Thread(target=launchCodeTimeMetrics)
        codetimemetricsthread.start()

class LaunchCustomDashboard(sublime_plugin.WindowCommand):
    def run(self):
        d = datetime.now()
        current_time = d.strftime("%m/%d/%Y")
        t = d - timedelta(days=7)
        time_ago = t.strftime("%m/%d/%Y")
        # default range: last 7 days
        default_range = str(time_ago) + ", " + str(current_time)
        self.window.show_input_panel("Enter a start and end date (format: MM/DD/YYYY):", default_range, self.on_done, None, None)

    def on_done(self, result):
        setValue("date_range", result)
        launchCustomDashboard()

# connect spotify menu
class ConnectSpotify(sublime_plugin.TextCommand):
    def run(self, edit):
        launchSpotifyLoginUrl()

    # def is_enabled(self):
    #     loggedOn = getValue("logged_on", True)
    #     online = getValue("online", True)
    #     if (loggedOn is False and online is True):
    #         return True
    #     else:
    #         return False


class ShowTreeView(sublime_plugin.WindowCommand):
    def run(self):
        setShouldOpen(True)
        refreshTreeView()

class SoftwareTopForty(sublime_plugin.TextCommand):
    def run(self, edit):
        webbrowser.open("https://api.software.com/music/top40")

    def is_enabled(self):
        return (getValue("online", True) is True)



class ToggleStatusBarMetrics(sublime_plugin.TextCommand):
    def run(self, edit):
        log("toggling status bar metrics")
        toggleStatus()

# Testing function
class ForceUpdateSessionSummary(sublime_plugin.WindowCommand):
    def run(self, isNewDay):
        updateSessionSummaryFromServer(isNewDay)

class GenerateContributorSummary(sublime_plugin.WindowCommand):
    def run(self):
        projectDir = getProjectDirectory()
        generateContributorSummary(projectDir)

# Mute Console message
class HideConsoleMessage(sublime_plugin.TextCommand):
    def run(self, edit):
        log("Code Time: Console Messages Disabled !")
        # showStatus("Paused")
        setValue("software_logging_on", False)

    def is_enabled(self):
        return (getValue("software_logging_on", True) is True)

# Command to re-enable Console message
class ShowConsoleMessage(sublime_plugin.TextCommand):
    def run(self, edit):
        log("Code Time: Console Messages Enabled !")
        # showStatus("Code Time")
        setValue("software_logging_on", True)

    def is_enabled(self):
        return (getValue("software_logging_on", True) is False)
    
# Command to pause kpm metrics
class PauseKpmUpdatesCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        log("software kpm metrics paused")
        showStatus("Paused")
        setValue("software_telemetry_on", False)

    def is_enabled(self):
        return (getValue("software_telemetry_on", True) is True)

# Command to re-enable kpm metrics
class EnableKpmUpdatesCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        log("software kpm metrics enabled")
        showStatus("Code Time")
        setValue("software_telemetry_on", True)

    def is_enabled(self):
        return (getValue("software_telemetry_on", True) is False)

# Runs once instance per view (i.e. tab, or single file window)
class EventListener(sublime_plugin.EventListener):
    def on_activated_async(self, view):
        focusWindow()

    def on_deactivated_async(self, view):
        blurWindow()

    def on_load_async(self, view):
        fileName = view.file_name()
        if (fileName is None):
            fileName = UNTITLED

        active_data = PluginData.get_active_data(view)

        # get the file info to increment the open metric
        fileInfoData = PluginData.get_file_info_and_initialize_if_none(active_data, fileName)
        if fileInfoData is None:
            return

        fileSize = view.size()
        fileInfoData['length'] = fileSize

        # get the number of lines
        lines = view.rowcol(fileSize)[0] + 1
        fileInfoData['lines'] = lines

        # we have the fileinfo, update the metric
        fileInfoData['open'] += 1
        log('Code Time: opened file %s' % fileName)

        # show last status message
        redisplayStatus() 

    # TODO: if tree view is closed, all groups should move left once space
    def on_close(self, view):
        fileName = view.file_name()
        if (fileName is None):
            fileName = UNTITLED

        if view.name() == CODETIME_TREEVIEW_NAME:
            handleCloseTreeView()

        active_data = PluginData.get_active_data(view)

        # get the file info to increment the close metric
        fileInfoData = PluginData.get_file_info_and_initialize_if_none(active_data, fileName)
        if fileInfoData is None:
            return

        fileSize = view.size()
        fileInfoData['length'] = fileSize

        # get the number of lines
        lines = view.rowcol(fileSize)[0] + 1
        fileInfoData['lines'] = lines

        # we have the fileInfo, update the metric
        fileInfoData['close'] += 1
        log('Code Time: closed file %s' % fileName)
        
        # show last status message
        redisplayStatus() 

    def on_modified_async(self, view):
        global PROJECT_DIR
        # get active data will create the file info if it doesn't exist
        active_data = PluginData.get_active_data(view)
        if active_data is None:
            return

        # add the count for the file
        fileName = view.file_name()
        
        fileInfoData = {}
        
        if (fileName is None):
            fileName = UNTITLED
            
        fileInfoData = PluginData.get_file_info_and_initialize_if_none(active_data, fileName)
        
        # If file is untitled then log that msg and set file open metrics to 1
        if fileName == UNTITLED:
            # log("Code Time: opened file untitled")
            fileInfoData['open'] = 1
        else:
            pass

        if fileInfoData is None:
            return

        fileSize = view.size()

        #lines = 0
        # rowcol gives 0-based line number, need to add one as on editor lines starts from 1 
        lines = view.rowcol(fileSize)[0] + 1
        
        prevLines = fileInfoData['lines']
        if (prevLines == 0):

            if (PluginData.line_counts.get(fileName) is None):
                PluginData.line_counts[fileName] = prevLines

            prevLines = PluginData.line_counts[fileName]
        elif (prevLines > 0):
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
        
        if currLen > 0 or currLen == 0:
        # currLen > 0 only worked for existing file, currlen==0 will work for new file
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

        # update the netkeys and the keystrokes
        # "netkeys" = add - delete
        fileInfoData['netkeys'] = fileInfoData['add'] - fileInfoData['delete']
        fileInfoData['keystrokes'] = fileInfoData['add'] + fileInfoData['delete'] + fileInfoData['paste'] + fileInfoData['linesAdded'] + fileInfoData['linesRemoved']

#
# Iniates the plugin tasks once the it's loaded into Sublime.
#
def plugin_loaded():
    initializeUser()

def initializeUser():
    # check if the session file is there
    serverAvailable = serverIsAvailable()
    fileExists = softwareSessionFileExists()
    jwt = getItem("jwt")
    log("JWT VAL: %s" % jwt)
    if (fileExists is False or jwt is None):
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
                initializePlugin(True, serverAvailable)
    else:
        initializePlugin(False, serverAvailable)

def initializePlugin(initializedAnonUser, serverAvailable):
    PACKAGE_NAME = __name__.split('.')[0]
    log('Code Time: Loaded v%s of package name: %s' % (VERSION, PACKAGE_NAME))
    showStatus("Code Time")

    setItem("sublime_lastUpdateTime", None)

    wallClockMgrInit()
    dashboardMgrInit()

    # fire off timer tasks (seconds, task)

    setOnlineStatusTimer = Timer(2, setOnlineStatus)
    setOnlineStatusTimer.start()

    oneMin = 60

    setInterval(sendOfflineData, oneMin * 15)
    setInterval(lambda: sendHeartbeat('HOURLY'), oneMin * 60)
    setInterval(sendOfflineEvents, oneMin * 40)
    setInterval(getHistoricalCommitsOfFirstProject, oneMin * 45)
    setInterval(getUsersOfFirstProject, oneMin * 50)

    updateStatusBarWithSummaryData()

    offlineTimer = Timer(oneMin, sendOfflineData)
    offlineTimer.start()

    getCommitsTimer = Timer(oneMin * 2, getHistoricalCommitsOfFirstProject)
    getCommitsTimer.start()

    getUsersTimer = Timer(oneMin * 3, getUsersOfFirstProject)
    getUsersTimer.start()

    sendEventsTimer = Timer(oneMin * 4, sendOfflineEvents)
    sendEventsTimer.start()

    updateOnlineStatusTimer = Timer(0.25, updateOnlineStatus)
    updateOnlineStatusTimer.start()
    # print("Online status timer initialized")

    # initializeUserInfo(initializedAnonUser)
    initializeUserThread = Thread(target=initializeUserInfo, args=[initializedAnonUser])
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

def userStatusHandler():
    getUserStatus()

    loggedOn = getValue("logged_on", True)
    if (loggedOn is True):
        # no need to fetch any longer
        return
    
    # re-fetch user info in another 10 minutes
    checkUserAuthTimer = Timer(60 * 10, userStatusHandler)
    checkUserAuthTimer.start()

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
    timer = Timer(60 * 1, setOnlineStatus)
    timer.start()

def getUsersOfFirstProject():
    getRepoUsers(getProjectDirectory())

def getHistoricalCommitsOfFirstProject():
    getHistoricalCommits(getProjectDirectory())
    