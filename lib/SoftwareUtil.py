# Copyright (c) 2018 by Software.com

from datetime import datetime, timedelta
import os
import json
import time
import sublime_plugin, sublime
import sys
from subprocess import Popen, PIPE
import re

VERSION = '0.2.7'

# get the number of seconds from epoch
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

# execute the applescript command.
def runTrackCmd(cmd, args):
    p = Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate(cmd)
    return stdout.decode('utf-8').strip()

# get the current track playing (spotify or itunes)
def getCurrentMusicTrack():
    if sys.platform == "darwin": # OS X
        script = '''
            on buildItunesRecord(appState)
                tell application "iTunes"
                    set track_artist to artist of current track
                    set track_name to name of current track
                    set track_genre to genre of current track
                    set track_id to database ID of current track
                    set json to "genre='" & track_genre & "';artist='" & track_artist & "';id='" & track_id & "';name='" & track_name & "';state='playing'"
                end tell
                return json
            end buildItunesRecord

            on buildSpotifyRecord(appState)
                tell application "Spotify"
                    set track_artist to artist of current track
                    set track_name to name of current track
                    set track_duration to duration of current track
                    set track_id to id of current track
                    set json to "genre='';artist='" & track_artist & "';id='" & track_id & "';name='" & track_name & "';state='playing'"
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

            trackInfo = dict(item.strip().split("=") for item in result.strip().split(";"))
            return trackInfo
        except Exception as e:
            log("Unable to parse music track info: %s" % e)
            return {}
    else:
        # not supported on other platforms yet
        return {}

def runResourceCmd(cmdArgs, rootDir):
    p = Popen(cmdArgs, cwd = rootDir, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()
    stdout = stdout.decode('utf-8').strip()
    if (stdout):
        stdout = stdout.strip('\r\n')
        return stdout
    else:
        return ""


def getResourceInfo(rootDir):
    resourceInfo = {}
    try:
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
        return resourceInfo



