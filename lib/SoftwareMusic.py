from threading import Thread, Timer, Event
import sublime_plugin, sublime
import copy
import time
from .SoftwareHttp import *
from .SoftwareUtil import *

currentTrackInfo = {}

def gatherMusicInfo():
	global currentTrackInfo


	# get the music track playing
	# the trackInfo should be a dictionary
	trackInfo = getTrackInfo()
	now = round(time.time())
	start = now
	local_start = now - time.timezone

	# state = "nice" if is_nice else "not nice"
	currentTrackId = currentTrackInfo.get("id", None)
	trackId = trackInfo.get("id", None)
	trackType = trackInfo.get("type", None)

	if (trackId is not None and trackType == "itunes"):
		itunesTrackState = getItunesTrackState()
		trackInfo["state"] = itunesTrackState
		try:
			# check if itunes is found, if not it'll raise a ValueError
			idx = trackId.index("itunes")
			if (idx == -1):
				trackId = "itunes:track:" + str(trackId)
				trackInfo["id"] = trackId
		except ValueError:
			# set the trackId to "itunes:track:"
			trackId = "itunes:track:" + str(trackId)
			trackInfo["id"] = trackId
	elif (trackId is not None and trackType == "spotify"):
		spotifyTrackState = getSpotifyTrackState()
		trackInfo["state"] = spotifyTrackState

	trackState = trackInfo.get("state", None)
	duration = trackInfo.get("duration", None)
	
	if (duration is not None):
		duration_val = float(duration)
		if (duration_val > 1000):
			trackInfo["duration"] = duration_val / 1000
		else:
			trackInfo["duration"] = duration_val

	# conditions
	# 1) if the currentTrackInfo doesn't have data and trackInfo does
	#    that means we should send it as a new song starting
	# 2) if the currentTrackInfo has data and the trackInfo does
	#    and has the same trackId, then don't send the payload
	# 3) if the currentTrackInfo has data and the trackInfo has data
	#    and doesn't have the same trackId then send a payload
	#    to close the old song and send a payload to start the new song

	if (trackId is not None):
		isPaused = False

		if (trackState != "playing"):
			isPaused = True

		if (currentTrackId is not None and (currentTrackId != trackId or isPaused is True)):
			# update the end time of the previous track and post it
			currentTrackInfo["end"] = start - 1
			response = requestIt("POST", "/data/music", json.dumps(currentTrackInfo))
			if (response is None):
				log("Code Time: error closing previous track")
			# re-initialize the current track info to an empty object
			currentTrackInfo = {}

		if (isPaused is False and (currentTrackId is None or currentTrackId != trackId)):
			# starting a new song
			trackInfo["start"] = start
			trackInfo["local_start"] = local_start
			trackInfo["end"] = 0
			response = requestIt("POST", "/data/music", json.dumps(trackInfo))
			if (response is None):
				log("Code Time: error sending new track")

			# clone the trackInfo to the currentTrackInfo
			for key, value in trackInfo.items():
				currentTrackInfo[key] = value
	else:
		if (currentTrackId is not None):
			# update the end time since there are no songs coming
			# in and the previous one is stil available
			currentTrackInfo["end"] = start - 1
			response = requestIt("POST", "/data/music", json.dumps(currentTrackInfo))
			if (response is None):
				log("Code Time: error closing previous track")

		# re-initialize the current track info to an empty object
		currentTrackInfo = {}

	# fetch the daily kpm session info in 15 seconds
	gatherMusicInfoTimer = Timer(15, gatherMusicInfo)
	gatherMusicInfoTimer.start()
