
# Copyright (c) 2018 by Software.com

import http
import json
import sublime_plugin, sublime

USER_AGENT = 'Code Time Sublime Plugin'

def httpLog(message):

    software_settings = sublime.load_settings("Software.sublime_settings")
    if (software_settings.get("software_logging_on", True)):
        print(message)

# update the status bar message
def showStatus(msg):
    try:
        active_window = sublime.active_window()
        if active_window:
            for view in active_window.views():
                view.set_status('software.com', msg)
    except RuntimeError:
        httpLog(msg)

def isResponsOk(response):
    if (response is not None and int(response.status) < 300):
        return True
    return False

def isUnauthenticated(response):
    if (response is not None and int(response.status) == 401):
        return True
    return False

# send the request.
def requestIt(method, api, payload, jwt):

    software_settings = sublime.load_settings("Software.sublime_settings")
    api_endpoint = software_settings.get("software_api_endpoint", "api.software.com")

    if (software_settings.get("software_telemetry_on", True) is False):
        # httpLog("Code Time: telemetry is currently paused. To see your coding data in Software.com, enable software telemetry.")
        return None

    # try to update kpm data.
    try:
        connection = None
        # create the connection
        if ('localhost' in api_endpoint):
            connection = http.client.HTTPConnection(api_endpoint)
        else:
            connection = http.client.HTTPSConnection(api_endpoint)

        headers = {'Content-Type': 'application/json', 'User-Agent': USER_AGENT}
            
        if (jwt is not None):
            headers['Authorization'] = jwt
        elif (method is 'POST' and jwt is None):
            httpLog("Code Time: no auth token available to post kpm data: %s" % payload)
            return None

        # make the request
        if (payload is None):
            payload = {}
            httpLog("Code Time: Requesting [" + method + ": " + api_endpoint + "" + api + "]")
        else:
            httpLog("Code Time: Sending [" + method + ": " + api_endpoint + "" + api + ", headers: " + json.dumps(headers) + "] payload: %s" % payload)
        

        # send the request
        connection.request(method, api, payload, headers)

        # httpLog("Code Time: completed api request: %s" % connection);

        response = connection.getresponse()
        # httpLog("Code Time: " + api_endpoint + "" + api + " Response (%d)" % response.status)
        return response
    except Exception as ex:
        print("Code Time: " + api + " Network error: %s" % ex)
        return None

