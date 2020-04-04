import http
import json
import sublime_plugin, sublime
from .SoftwareSettings import *

USER_AGENT = 'Code Time Sublime Plugin'
lastMsg = None
windowView = None

def httpLog(message):
    if (getValue("software_logging_on", True)):
        print(message)

def redisplayStatus():
    global lastMsg
    showStatus(lastMsg)

def toggleStatus():
    global lastMsg
    showStatusVal = getValue("show_code_time_status", True)
    setValue("show_code_time_status", not showStatusVal)

    # Change the setting before displaying the new one
    if (not showStatusVal is True):
        showStatus(lastMsg)
    else:
        # show clock icon unicode
        showStatus("⏱")
    sublime.active_window().run_command('open_tree_view')

# update the status bar message
def showStatus(msg):
    global lastMsg
    try:
        active_window = sublime.active_window()

        showStatusVal = getValue("show_code_time_status", True)

        if (showStatusVal is False):
            msg = "⏱"
        else:
            lastMsg = msg
        
        if (active_window is not None):
            for view in active_window.views():
                if (view is not None):
                    view.set_status('software.com', msg)
    except RuntimeError:
        httpLog(msg)

def isResponseOk(response):
    if (response is not None and int(response.status) < 300):
        return True
    return False

def isUnauthenticated(response):
    if (response is not None and int(response.status) == 401):
        return True
    return False

# send the request.
def requestIt(method, api, payload, jwt):

    api_endpoint = getValue("software_api_endpoint", "api.software.com")
    telemetry = getValue("software_telemetry_on", True)

    if (telemetry is False):
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

        response = connection.getresponse()
        # httpLog("Code Time: " + api_endpoint + "" + api + " Response (%d)" % response.status)
        return response
    except Exception as ex:
        print("Code Time: " + api + " Network error: %s" % ex)
        return None

