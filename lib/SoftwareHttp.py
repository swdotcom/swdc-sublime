
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

# send the request
def requestIt(method, api, payload):
    sublime_settings = sublime.load_settings("Software.sublime-settings")
    api_endpoint = sublime_settings.get("software_api_endpoint", "api.software.com")

    if (sublime_settings.get("software_telemetry_on", True) is False):
        # log("Software.com: telemetry is currently paused. To see your coding data in Software.com, enable software telemetry.")
        return None

    # try to update kpm data
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

        log("Software.com: Request [" + method + ": " + api_endpoint + "" + api + ", headers: " + json.dumps(headers) + "] payload: %s" % payload)

        # send the request
        connection.request(method, api, payload, headers)

        response = connection.getresponse()
        # log("Software.com: " + api_endpoint + "" + api + " Response (%d)" % response.status)
        return response
    except Exception as ex:
        print("Software.com: " + api + " Network error: %s" % ex)
        return None

