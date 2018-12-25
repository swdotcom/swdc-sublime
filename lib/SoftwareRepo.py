import sublime_plugin, sublime
import time
from .SoftwareHttp import *
from .SoftwareUtil import *

def gatherRepoMembers(rootDir):
	resourceInfoDict = getResourceInfo(rootDir)
	identifier = resourceInfoDict.get("identifier")

	if (identifier is not None):
		tag = resourceInfoDict['tag']
		branch = resourceInfoDict['branch']

		# get the list of the repo members....
		result = runResourceCmd(['git', 'log', '--pretty="%an,%ae"'], rootDir)

		devList = result.replace('\r\n', '\r').replace('\n', '\r').replace('"', '').split('\r')

		# create a unique list
		devListMap = {}
		members = []
		repoData = {
			'members': [],
			'identifier': identifier,
			'tag': tag,
			'branch': branch
		}
		for devInfo in devList:
			devInfoParts = devInfo.split(",");
			if (devInfoParts is not None and len(devInfoParts) > 1):
				name = devInfoParts[0]
				email = devInfoParts[1]
				if (devListMap.get(email) is None):
					devListMap[email] = name
					
					members.append({'name': name.strip(), 'email': email.strip()})


		# members: [{'email': 'xavluiz@gmail.com', 'name': 'Xavier'}, {'email': 'brettmstevens7@gmail.com', 'name': 'brettmstevens7'}, {'email': '39741693+o4sw@users.noreply.github.com', 'name': 'o4sw'}]
        # sending: {"members": [{"email": "xavluiz@gmail.com", "name": "Xavier"}, {"email": "brettmstevens7@gmail.com", "name": "brettmstevens7"}, {"email": "39741693+o4sw@users.noreply.github.com", "name": "o4sw"}], "identifier": "https://github.com/swdotcom/swdc-sublime.git", "tag": "tags/0.4.7", "branch": "master"}
		if (len(members) > 0):
			repoData['members'] = members;

			response = requestIt("POST", "/repo/members", json.dumps(repoData))
			# ....
			if (response is not None):
				responseObjStr = response.read().decode('utf-8')
				try:
					responseObj = json.loads(responseObjStr)
					log("Software.com: %s" % responseObj['message'])
				except Exception as ex:
					log("Software.com: Unable to complete repo member metric update: %s" % ex)