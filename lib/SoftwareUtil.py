# Copyright (c) 2018 by Software.com

from datetime import datetime, timedelta
import os
import json
import time
import sublime_plugin, sublime

VERSION = '0.1.6'

# get the number of seconds from epoch.
def trueSecondsNow():
    return time.mktime(datetime.utcnow().timetuple())

# get the utc time
def secondsNow():
    return datetime.utcnow()

# log the message
def log(message):
    sublime_settings = sublime.load_settings("Software.sublime-settings")
    if (sublime_settings.get("software_logging_on", True)):
        print(message)

# fetch a value from the .software/sesion.json file
def getItem(key):
    jsonObj = getSoftwareSessionAsJson()

    # return a default of None if key isn't found
    val = jsonObj.get(key, None)

    return val

# get an item from the session json file
def setItem(key, value):
    jsonObj = getSoftwareSessionAsJson()
    jsonObj[key] = value

    content = json.dumps(jsonObj)

    sessionFile = getSoftwareSessionFile()
    with open(sessionFile, 'w') as f:
        f.write(content)

# store the payload offline
def storePayload(payload):
    # append payload to software data store file
    dataStoreFile = getSoftwareDataStoreFile()

    with open(dataStoreFile, "a") as dsFile:
        dsFile.write(payload + "\n")

def getSoftwareSessionAsJson():
    try:
        with open(getSoftwareSessionFile()) as sessionFile:
            return json.load(sessionFile)
    except FileNotFoundError:
        return {}

def getSoftwareSessionFile():
    file = getSoftwareDir()
    return os.path.join(file, 'session.json')

def getSoftwareDataStoreFile():
    file = getSoftwareDir()
    return os.path.join(file, 'data.json')

def getSoftwareDir():
    softwareDataDir = os.path.expanduser('~')
    softwareDataDir = os.path.join(softwareDataDir, '.software')
    os.makedirs(softwareDataDir, exist_ok=True)

    return softwareDataDir


