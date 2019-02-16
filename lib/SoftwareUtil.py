# Copyright (c) 2018 by Software.com

import os
import json
import time
import sublime_plugin, sublime
import sys
from subprocess import Popen, PIPE
import re

VERSION = '0.6.0'
PLUGIN_ID = 1

runningResourceCmd = False

# log the message
def log(message):

    software_settings = sublime.load_settings("Software.sublime_settings")
    if (software_settings.get("software_logging_on", True)):
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
    except Exception:
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

def getDashboardFile():
    file = getSoftwareDir()
    return os.path.join(file, 'CodeTime.txt')

# execute the applescript command
def runTrackCmd(cmd, args):
    p = Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate(cmd)
    return stdout.decode('utf-8').strip()

def getItunesTrackState():
    script = '''
        tell application "iTunes" to get player state
        '''
    try:
        cmd = script.encode('latin-1')
        result = runTrackCmd(cmd, ['osascript', '-'])
        return result
    except Exception as e:
        log("exception getting track state: %s " % e)
        # no music found playing
        return "stopped"

def getSpotifyTrackState():
    script = '''
        tell application "Spotify" to get player state
        '''
    try:
        cmd = script.encode('latin-1')
        result = runTrackCmd(cmd, ['osascript', '-'])
        return result
    except Exception as e:
        log("exception getting track state: %s " % e)
        # no music found playing
        return "stopped"


# get the current track playing (spotify or itunes)
def getTrackInfo():
    if sys.platform == "darwin":
        return getMacTrackInfo()
    elif sys.platform == "win32":
        # not supported on other platforms yet
        return getWinTrackInfo()
    else:
        # linux not supported yet
        return {}

# windows
def getWinTrackInfo():
    # not supported on other platforms yet
    return {}

# OS X
def getMacTrackInfo():
    script = '''
        on buildItunesRecord(appState)
            tell application "iTunes"
                set track_artist to artist of current track
                set track_name to name of current track
                set track_genre to genre of current track
                set track_id to database ID of current track
                set track_duration to duration of current track
                set json to "type='itunes';genre='" & track_genre & "';artist='" & track_artist & "';id='" & track_id & "';name='" & track_name & "';state='playing';duration='" & track_duration & "'"
            end tell
            return json
        end buildItunesRecord

        on buildSpotifyRecord(appState)
            tell application "Spotify"
                set track_artist to artist of current track
                set track_name to name of current track
                set track_duration to duration of current track
                set track_id to id of current track
                set track_duration to duration of current track
                set json to "type='spotify';genre='';artist='" & track_artist & "';id='" & track_id & "';name='" & track_name & "';state='playing';duration='" & track_duration & "'"
            end tell
            return json
        end buildSpotifyRecord

        try
            if application "Spotify" is running and application "iTunes" is not running then
                tell application "Spotify" to set spotifyState to (player state as text)
                -- spotify is running and itunes is not
                if (spotifyState is "paused" or spotifyState is "playing") then
                    set jsonRecord to buildSpotifyRecord(spotifyState)
                else
                    set jsonRecord to {}
                end if
            else if application "Spotify" is running and application "iTunes" is running then
                tell application "Spotify" to set spotifyState to (player state as text)
                tell application "iTunes" to set itunesState to (player state as text)
                -- both are running but use spotify as a higher priority
                if spotifyState is "playing" then
                    set jsonRecord to buildSpotifyRecord(spotifyState)
                else if itunesState is "playing" then
                    set jsonRecord to buildItunesRecord(itunesState)
                else if spotifyState is "paused" then
                    set jsonRecord to buildSpotifyRecord(spotifyState)
                else
                    set jsonRecord to {}
                end if
            else if application "iTunes" is running and application "Spotify" is not running then
                tell application "iTunes" to set itunesState to (player state as text)
                set jsonRecord to buildItunesRecord(itunesState)
            else
                set jsonRecord to {}
            end if
            return jsonRecord
        on error
            return {}
        end try
    '''
    try:
        cmd = script.encode('latin-1')
        result = runTrackCmd(cmd, ['osascript', '-'])
        result = result.strip('\r\n')
        result = result.replace('"', '')
        result = result.replace('\'', '')

        if (result):
            trackInfo = dict(item.strip().split("=") for item in result.strip().split(";"))
            return trackInfo
        else:
            return {}
    except Exception as e:
        log("exception getting track: %s " % e)
        # no music found playing
        return {}

def runResourceCmd(cmdArgs, rootDir):
    if sys.platform == "darwin": # OS X
        runningResourceCmd = True
        p = Popen(cmdArgs, cwd = rootDir, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate()
        stdout = stdout.decode('utf-8').strip()
        if (stdout):
            stdout = stdout.strip('\r\n')
            return stdout
        else:
            return ""
    else:
        return ""


def getResourceInfo(rootDir):
    try:
        resourceInfo = {}
        tag = runResourceCmd(['git', 'describe', '--all'], rootDir)

        if (tag):
            resourceInfo['tag'] = tag
        identifier = runResourceCmd(['git', 'config', '--get', 'remote.origin.url'], rootDir)

        if (identifier):
            resourceInfo['identifier'] = identifier
        branch = runResourceCmd(['git', 'symbolic-ref', '--short', 'HEAD'], rootDir)

        if (branch):
            resourceInfo['branch'] = branch
        email = runResourceCmd(['git', 'config', 'user.email'], rootDir)

        if (email):
            resourceInfo['email'] = email
            
        if (resourceInfo.get("identifier") is not None):
            return resourceInfo
        else:
            return {}
    except Exception as e:
        log("Unable to locate git repo info: %s" % e)
        return {}



