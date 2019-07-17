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
from .SoftwareSettings import *
from .SoftwareOffline import *

# Constants
ONE_MINUTE_IN_SEC = 60
SECONDS_PER_HOUR = 60 * 60
LONG_THRESHOLD_HOURS = 12
SHORT_THRESHOLD_HOURS = 4
NO_TOKEN_THRESHOLD_HOURS = 2
LOGIN_LABEL = "Log in"


# send the data that has been saved offline
def sendOfflineData():
    existingJwt = getItem("jwt")

    # no need to try to send the offline data if we don't have an auth token
    if (existingJwt is None):
        return

    serverAvailable = checkOnline()
    if (serverAvailable):
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
                os.remove(dataStoreFile)

                # go through the payloads array 50 at a time
                batch = []
                length = len(payloads)
                for i in range(length):
                    payload = payloads[i]
                    if (len(batch) >= 50):
                        requestIt("POST", "/data/batch", json.dumps(batch), getItem("jwt"))
                        # send batch
                        batch = []
                    batch.append(payload)

                # send remaining batch
                if (len(batch) > 0):
                    requestIt("POST", "/data/batch", json.dumps(batch), getItem("jwt"))

    # update the statusbar
    fetchDailyKpmSessionInfo(True)

    # send the next batch in 30 minutes
    sendOfflineDataTimer = Timer(60 * 30, sendOfflineData)
    sendOfflineDataTimer.start()

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
def fetchDailyKpmSessionInfo(forceRefresh):
    sessionSummaryData = getSessionSummaryFileAsJson()
    currentDayMinutes = sessionSummaryData.get("currentDayMinutes", 0)
    if (currentDayMinutes == 0 or forceRefresh is True):
        online = getValue("online", True)
        if (online is False):
            # update the status bar with offline data
            updateStatusBarWithSummaryData()
            return { "data": sessionSummaryData, "status": "CONN_ERR" }

        # api to fetch the session kpm info
        api = '/sessions/summary'
        response = requestIt("GET", api, None, getItem("jwt"))

        if (response is not None and isResponsOk(response)):
            sessionSummaryData = json.loads(response.read().decode('utf-8'))

            # update the file
            saveSessionSummaryToDisk(sessionSummaryData)

            # update the status bar
            updateStatusBarWithSummaryData()

            # stitch the dashboard together
            fetchCodeTimeMetricsDashboard(sessionSummaryData)

            return { "data": sessionSummaryData, "status": "OK" }
    else:
        # update the status bar with offline data
        updateStatusBarWithSummaryData()
        return { "data": sessionSummaryData, "status": "OK" }

# store the payload offline...
def storePayload(payload):

    # calculate it and call add to the minutes
    # convert it to json
    payloadData = json.loads(payload)

    keystrokes = payloadData.get("keystrokes", 0)

    incrementSessionSummaryData(1, keystrokes)

    # push the stats to the file so other editor windows can have it
    saveSessionSummaryToDisk(getSessionSummaryData())

    # update the statusbar
    fetchDailyKpmSessionInfo(False)

    # get the datastore file to save the payload
    dataStoreFile = getSoftwareDataStoreFile()

    log("Code Time: storing kpm metrics: %s" % payload)

    with open(dataStoreFile, "a") as dsFile:
        dsFile.write(payload + "\n")




