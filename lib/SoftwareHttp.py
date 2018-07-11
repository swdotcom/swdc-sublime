
# Copyright (c) 2018 by Software.com

import http
import sublime_plugin, sublime
from .SoftwareUtil import *

# constants
PROD_API_ENDPOINT = "api.software.com"
TEST_API_ENDPOINT = "localhost:5000"

# set the api endpoint to use
api_endpoint = PROD_API_ENDPOINT

# toggle to turn on/off logging
LOGGING = True

# toggle to turn on/of telemetry
TELEMETRY_ON = True

def updateTelemetry(telemtryOnVal):
    global TELEMETRY_ON
    log("setting software telemetry to: %s " % telemtryOnVal)
    TELEMETRY_ON = telemtryOnVal

# log the message
def log(message):
    global LOGGING
    if not LOGGING:
        return
    print(message)

# update the status bar message
def showStatus(msg):
    try:
        active_window = sublime.active_window()
        if active_window:
            for view in active_window.views():
                view.set_status('software.com', msg)
    except RuntimeError:
        log(msg)

def requestIt(method, api, payload):
    global TELEMETRY_ON

    if (TELEMETRY_ON is False):
        log("Software.com: telemetry is currently paused. To see your coding data in Software.com, enable software telemetry.")
        return None

    log("Software.com: Sending request -- [" + method + ": " + api_endpoint + "" + api + "] payload: %s" % payload)
    
    try:
        connection = None
        if (api_endpoint is TEST_API_ENDPOINT):
            connection = http.client.HTTPConnection(api_endpoint)
        else:
            connection = http.client.HTTPSConnection(api_endpoint)

        headers = {'Content-type': 'application/json', 'User-Agent': USER_AGENT}

        jwt = getItem("jwt")
        if (jwt is not None):
            headers['Authorization'] = jwt

        # make the request
        if (payload is None):
            payload = {}

        connection.request(method, api, payload, headers)

        response = connection.getresponse()
        log("Software.com: " + api + " Response (%d)" % response.status)
        return response
    except (http.client.HTTPException, http.client.CannotSendHeader, ConnectionError, Exception) as ex:
        log("Software.com: " + api + " Network error: %s" % ex)
        return None

