
# Copyright (c) 2018 by Software.com

import http
import sublime_plugin, sublime
from .SoftwareUtil import *

USER_AGENT = 'Software.com Sublime Plugin v' + VERSION

# update the status bar message
def showStatus(msg):
    try:
        active_window = sublime.active_window()
        if active_window:
            for view in active_window.views():
                view.set_status('software.com', msg)
    except RuntimeError:
        log(msg)

def isResponsOk(response):
    if (response is not None and int(response.status) < 300):
        return True
    return False

def isUnauthenticated(response):
    if (response is None or (response is not None and int(response.status) == 401)):
        return True
    return False

def isUserDeactivated(response):
    if (isUnauthenticated(response)):
        # check if it has the DEACTIVATED "code" in a response body
        try:
            data = json.loads(response.read().decode('utf-8'))
            # data: {'message': 'User is deactivated', 'code': 'DEACTIVATED'}
            if (data is not None and data.get("code", "") == "DEACTIVATED"):
                return True
        except Exception as ex:
            log("exception reading unauthenticated response data: %s" % ex)
            return False

    return False

# send the request
def requestIt(method, api, payload):

    software_settings = sublime.load_settings("Software.sublime_settings")
    api_endpoint = software_settings.get("software_api_endpoint", "api.software.com")

    if (software_settings.get("software_telemetry_on", True) is False):
        # log("Software.com: telemetry is currently paused. To see your coding data in Software.com, enable software telemetry.")
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

        jwt = getItem("jwt")
        if (jwt is not None):
            headers['Authorization'] = jwt
        elif (method is 'POST' and jwt is None):
            log("Software.com: no auth token available to post kpm data")
            return None

        # make the request
        if (payload is None):
            payload = {}
            log("Software.com: Requesting [" + method + ": " + api_endpoint + "" + api + "]")
        else:
            log("Software.com: Sending [" + method + ": " + api_endpoint + "" + api + ", headers: " + json.dumps(headers) + "] payload: %s" % payload)
        

        # send the request
        connection.request(method, api, payload, headers)

        response = connection.getresponse()
        # log("Software.com: " + api_endpoint + "" + api + " Response (%d)" % response.status)
        return response
    except Exception as ex:
        print("Software.com: " + api + " Network error: %s" % ex)
        return None

