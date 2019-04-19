# Copyright (c) 2018 by Software.com

from datetime import datetime
from threading import Thread, Timer, Event
import time
import json
import math
import os
import sublime_plugin, sublime
from .SoftwareHttp import *
from .SoftwareUtil import *

# Constants
DASHBOARD_KEYMAP_MSG = "⚠️Code Time ctrl+alt+o"
ONE_MINUTE_IN_SEC = 60
SECONDS_PER_HOUR = 60 * 60
LONG_THRESHOLD_HOURS = 12
SHORT_THRESHOLD_HOURS = 4
NO_TOKEN_THRESHOLD_HOURS = 2
LOGIN_LABEL = "Log in"

# store the payload offline
def storePayload(payload):
    # append payload to software data store file
    dataStoreFile = getSoftwareDataStoreFile()

    with open(dataStoreFile, "a") as dsFile:
        dsFile.write(payload + "\n")

# send the data that has been saved offline
def sendOfflineData():
    existingJwt = getItem("jwt")

    # no need to try to send the offline data if we don't have an auth token
    if (existingJwt is None):
        return

    # send the offline data
    dataStoreFile = getSoftwareDataStoreFile()

    if (os.path.exists(dataStoreFile)):
        payloads = []

        try:
            with open(dataStoreFile) as fp:
                for line in fp:
                    if (line and line.strip()):
                        line = line.rstrip()
                        # convert to object
                        json_obj = json.loads(line)
                        # convert to json to send
                        payloads.append(json_obj)
        except Exception:
            log("Unable to read offline data file %s" % dataStoreFile)

        if (payloads):
            response = requestIt("POST", "/data/batch", json.dumps(payloads), getItem("jwt"))

            if (isResponsOk(response)):
                os.remove(dataStoreFile)

def showLoginPrompt():
    serverAvailable = checkOnline()

    if (serverAvailable):
        # set the last update time so we don't try to ask too frequently
        infoMsg = "To see your coding data in Code Time, please log in to your account."
        clickAction = sublime.ok_cancel_dialog(infoMsg, LOGIN_LABEL)
        if (clickAction):
            # launch the login view
            launchLoginUrl()

def handlKpmClickedEvent():
    launchCodeTimeMetrics()

#
# Fetch and display the daily KPM info
#
def fetchDailyKpmSessionInfo():
    # send in the start of the day in seconds
    today = datetime.now()
    today = today.replace(hour=0, minute=0, second=0, microsecond=0)
    fromSeconds = round(today.timestamp())

    # api to fetch the session kpm info
    api = '/sessions?summary=true'
    response = requestIt("GET", api, None, getItem("jwt"))

    if (response is not None and isResponsOk(response)):
        sessions = json.loads(response.read().decode('utf-8'))

        # i.e.
        # {'sessionMinAvg': 0, 'inFlow': False, 'currentSessionMinutes': 23.983333333333334, 'lastKpm': 0, 'currentSessionGoalPercent': None}
        # but should be...
        # {'sessionMinAvg': 0, 'inFlow': False, 'currentSessionMinutes': 23.983333333333334, 'lastKpm': 0, 'currentSessionGoalPercent': 0.44}

        avgKpmStr = "0"
        try:
            avgKpmStr = '{:1.0f}'.format(sessions.get("lastKpm", 0))
        except Exception:
            avgKpmStr = "0"

        currentSessionMinutes = 0
        try:
            currentSessionMinutes = int(sessions.get("currentSessionMinutes", 0))
        except Exception:
            currentSessionMinutes = 0

        sessionMinGoalPercent = 0.0
        try:
            if (sessions.get("currentSessionGoalPercent") is not None):
                sessionMinGoalPercent = float(sessions.get("currentSessionGoalPercent", 0.0))
        except Exception:
            sessionMinGoalPercent = 0.0

        currentDayMinutes = 0
        try:
            currentDayMinutes = int(sessions.get("currentDayMinutes", 0))
        except Exception:
            currentDayMinutes = 0
        averageDailyMinutes = 0
        try:
            averageDailyMinutes = int(sessions.get("averageDailyMinutes", 0))
        except Exception:
            averageDailyMinutes = 0
        
        currentSessionTime = humanizeMinutes(currentSessionMinutes)
        currentDayTime = humanizeMinutes(currentDayMinutes)
        averageDailyTime = humanizeMinutes(averageDailyMinutes)

        inFlowIcon = ""
        if (currentDayMinutes > averageDailyMinutes):
            inFlowIcon = "🚀"

        statusMsg = inFlowIcon + "" + currentDayTime
        if (averageDailyMinutes > 0):
            statusMsg += " | Avg:" + averageDailyTime

        showStatus(statusMsg)
        fetchCodeTimeMetrics()

    fetchDailyKpmTimer = Timer(60, fetchDailyKpmSessionInfo)
    fetchDailyKpmTimer.start()

def humanizeMinutes(minutes):
    minutes = int(minutes)
    humanizedStr = ""
    if (minutes == 60):
        humanizedStr = "1 hr"
    elif (minutes > 60):
        floatMin = (minutes / 60)
        if (floatMin % 1 == 0):
            # don't show zeros after the decimal
            humanizedStr = '{:4.0f}'.format(floatMin) + " hrs"
        else:
            # at least 4 chars (including the dot) with 2 after the dec point
            humanizedStr = '{:4.1f}'.format(round(floatMin, 1)) + " hrs"
    elif (minutes == 1):
        humanizedStr = "1 min"
    else:
        humanizedStr = '{:1.0f}'.format(minutes) + " min"

    return humanizedStr



