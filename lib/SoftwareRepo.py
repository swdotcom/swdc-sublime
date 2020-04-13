import sublime_plugin, sublime
import re
from datetime import *
from urllib.parse import quote_plus
from .SoftwareModels import CommitChangeStats, ContributorMember
from .SoftwareHttp import *
from .SoftwareUtil import *
from .SoftwareSettings import *

ONE_HOUR_IN_SEC = 60 * 60
ONE_DAY_SEC = ONE_HOUR_IN_SEC * 24
ONE_WEEK_SEC = ONE_DAY_SEC * 7

def accumulateStatChanges(results):
	stats = CommitChangeStats()
	if results:
		for line in results:
			if 'changed' in line and ('insertion' in line or 'deletion' in line):
				parts = line.strip().split(' ')
				fileCount = int(parts[0])
				stats['fileCount'] += fileCount 
				stats['commitCount'] += 1

				for x in range(1, len(parts)):
					part = parts[x]
					if 'insertion' in part:
						numInsertions = int(parts[x - 1])
						stats['insertions'] += numInsertions
					elif 'deletion' in part:
						numDeletions = int(parts[x - 1])
						stats['deletions'] += numDeletions
	return stats 


def getChangeStats(projectDir, cmd):
	changeStats = CommitChangeStats()

	if not projectDir:
		return changeStats 

	resultList = getCommandResultList(cmd, projectDir)

	# if cmd == ['git', 'log', '--stat', '--pretty="COMMIT:%H,%ct,%cI,%s"', '--since=1586070000.0', '--until=1586674800.0']:
	print(resultList)

	if not resultList:
		return changeStats    

	changeStats = accumulateStatChanges(resultList)

	return changeStats

def getUncommittedChanges(projectDir):
    cmd = ['git', 'diff', '--stat']
    return getChangeStats(projectDir, cmd)

def getHistoricalCommits(rootDir):
	if (rootDir is None or rootDir == ''):
		return

	resourceInfoDict = getResourceInfo(rootDir)
	identifier = resourceInfoDict.get("identifier")

	if (identifier is not None):
		tag = resourceInfoDict['tag']
		branch = resourceInfoDict['branch']

		key = buildRepoKey(identifier, branch, tag)

		latestCommit = getLastCommit(rootDir)
		
		sinceOption = ""
		cmdList = ['git', 'log', '--stat', '--pretty="COMMIT:%H,%ct,%cI,%s"']

		# add the email to filter against
		email = resourceInfoDict.get("email", None)
		if (email is not None):
			emailOption = "--author=%s" % email
			cmdList.append(emailOption)

		# add the since to fetch the latest
		if (latestCommit is not None):
			latestCommitTs = latestCommit.get("timestamp", None)
			if (latestCommitTs is not None):
				sinceOption = "--since=%s" % int(latestCommitTs)
				cmdList.append(sinceOption)
		else:
			cmdList.append("--max-count=100")

		latestCommitId = None
		if (latestCommit is not None):
			latestCommitId = latestCommit.get("commitId", None)

		result = runResourceCmd(cmdList, rootDir)

		commitList = result.replace('\r\n', '\r').replace('\n', '\r').replace('"', '').split('\r')

		if (commitList is not None and len(commitList) > 0):
			commit = None
			commits = []
			for i in range(len(commitList)):
				line = commitList[i]
				# trim the line..
				line = line.strip()

				if (line.find("COMMIT:") == 0):
					# 52d0ac19236ac69cae951b2a2a0b4700c0c525db, 1545507646, 2018-12-22T11:40:46-08:00, updated wlb to use local_start, xavluiz@gmail.com
					line = line[len("COMMIT:"):]
					if (commit is not None):
						# add to the commits list
						commits.append(commit)

					commitInfos = line.split(",")
					
					if (commitInfos is not None and len(commitInfos) > 3):
						commitId = commitInfos[0].strip()

						if (latestCommitId is not None and commitId == latestCommitId):
							commit = None
							continue

						timestamp = 0
						try:
							timestamp = int(commitInfos[1].strip())
						except Exception:
							# ValueError: invalid literal for int() with base 10:
							timestamp = 0
						
						date = commitInfos[2].strip()
						message = commitInfos[3].strip()

						totalsDict = {
							'insertions': 0,
							'deletions': 0
						}

						changesDict = {
							'__sftwTotal__': totalsDict
						}
						commit = {
							'commitId': commitId,
							'timestamp': timestamp,
							'message': message,
							'changes': changesDict
						}

				elif (line.find("|") > 0):
					line = re.sub(' +', ' ', line)
					#
					# example line: ActivityCommand.py => Software.py | 43 ++++-----------------------
					lineInfos = line.split("|")
					if (lineInfos is not None and len(lineInfos) > 1):
						file = lineInfos[0].strip()

						metricsLine = lineInfos[1].strip()
						metricsInfos = metricsLine.split(" ")

						if (len(metricsInfos) < 2):
							continue

						changes = 0
						try:
							changes = int(metricsInfos[0].strip())
						except Exception:
							changes = 0
						addAndDeletes = metricsInfos[1].strip()
						insertions = 0
						deletions = 0
						lastPlusIdx = -1
						try:
							lastPlusIdx = addAndDeletes.rindex("+")
						except Exception as ex:
							lastPlusIdx = -1
						if (lastPlusIdx != -1):
							insertions = lastPlusIdx + 1
							deletions = len(addAndDeletes) - insertions
						elif (len(addAndDeletes) > 0):
							deletions = len(addAndDeletes)

						if (commit is not None):
							changes = commit["changes"]
							changes[file] = {
								'insertions': insertions,
								'deletions': deletions
							}
							totalInsertions = changes["__sftwTotal__"]["insertions"]
							totalDeletions = changes["__sftwTotal__"]["deletions"]
							changes["__sftwTotal__"]["insertions"] = totalInsertions + insertions
							changes["__sftwTotal__"]["deletions"] = totalDeletions + deletions

			if (commit is not None):
				# add to the commits list
				commits.append(commit)

			if (commits is not None and len(commits) > 0):
				batchCommits = []
				index = 0
				for commit in commits:
					batchCommits.append(commit)
					if (index > 0 and index % 100 == 0):
						commitData = {
							'commits': batchCommits,
							'identifier': identifier,
							'tag': tag,
							'branch': branch
						}
						sendCommits(commitData)
					index += 1

				if (len(batchCommits) > 0):
					commitData = {
						'commits': batchCommits,
						'identifier': identifier,
						'tag': tag,
						'branch': branch
					}
					sendCommits(commitData)

def sendCommits(commitData):
	online = getValue("online", True)
	if (online):
		response = requestIt("POST", "/commits", json.dumps(commitData), getItem("jwt"))
		if (response is not None):
			responseObjStr = response.read().decode('utf-8')
			try:
				responseObj = json.loads(responseObjStr)
				log("Code Time: %s" % responseObj.get("message", "Repo commits update complete"))
			except Exception as ex:
				log("Code Time: Unable to complete repo commits metric update: %s" % ex)
	else:
		return None

def buildRepoKey(identifier, branch, tag):
	return "%s_%s_%s" % (identifier, branch, tag)

def getLastCommit(rootDir):
	
	# get the repo info to get the last commit from the app
	if (rootDir is None):
		return None

    # get the repo url, branch, and tag
	resourceInfoDict = getResourceInfo(rootDir)
	identifier = resourceInfoDict.get("identifier")

	latestCommit = None

	if (identifier is not None):
		tag = resourceInfoDict['tag']
		branch = resourceInfoDict['branch']

		key = buildRepoKey(identifier, branch, tag)

    	# fetch the latest commit from the app
		encodedIdentifier = quote_plus(identifier) 
		encodedTag = quote_plus(tag)
		encodedBranch = quote_plus(branch)

		qryStr = "identifier=%s&tag=%s&branch=%s" % (encodedIdentifier, encodedTag, encodedBranch)
		api = "/commits/latest?%s" % qryStr

		response = requestIt("GET", api, None, getItem("jwt"))

		if (response is not None):
			responseObjStr = response.read().decode('utf-8')
			try:
				responseObj = json.loads(responseObjStr)
				status = responseObj.get("status", None)
				if (status is not None and status == "success"):
					# set the last commit data
					latestCommit = responseObj.get("commit", None)
				log("Code Time: %s" % responseObj.get("message", "Commit fetch complete"))
			except Exception as ex:
				log("Code Time: Unable to complete repo member metric update: %s" % ex)

	return latestCommit


def getRepoContributors(projectDir, filterOutNonEmails=False):
	contributors = []
	if not projectDir:
		return contributors
	
	repoContributorInfo = getRepoUsers(projectDir, filterOutNonEmails)

	if repoContributorInfo and repoContributorInfo['members']:
		for member in repoContributorInfo['members']:
			contributor = ContributorMember()
			contributor['name'] = member['name']
			contributor['email'] = member['email']
			contributor['identifier'] = repoContributorInfo['identifier']
			contributors.append(contributor)
	
	return contributors 

def processRepoContributors(projectDir):
	if not projectDir:
		return 

	repoContributorInfo = getRepoUsers(projectDir)

	if repoContributorInfo:
		response = requestIt("POST", '/repo/contributors', repoContributorInfo, getItem('jwt'))

		if response and isResponseOk(response):
			log('Code Time: repo contributor updated')

def getRepoUsers(rootDir, filterOutNonEmails=False):
	if (rootDir is None or rootDir == ''):
		return

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
		if devList is not None and len(devList) > 0:
			for devInfo in devList:
				devInfoParts = devInfo.split(",")
				if (devInfoParts is not None and len(devInfoParts) > 1):
					name = devInfoParts[0]
					email = devInfoParts[1]

					validEmail = normalizeGithubEmail(email, filterOutNonEmails)
					if validEmail:
						if (devListMap.get(email) is None):
							members.append({'name': name.strip(), 'email': email.strip()})
						devListMap[email] = name
			repoData['members'] = members
			return repoData 
	return None 

def getTodaysCommits(projectDir, useAuthor=True):
	today = getToday()
	return getCommitsInRange(projectDir, today['start'], today['end'], useAuthor)

def getYesterdaysCommits(projectDir, useAuthor=True):
	yesterday = getYesterday()
	return getCommitsInRange(projectDir, yesterday['start'], yesterday['end'], useAuthor)

def getThisWeeksCommits(projectDir, useAuthor=True):
	thisWeek = getThisWeek()
	return getCommitsInRange(projectDir, thisWeek['start'], thisWeek['end'], useAuthor)

def getCommitsInRange(projectDir, start, end, useAuthor=True):
	resourceInfo = getResourceInfo(projectDir)
	authorOption = '--author={}'.format(resourceInfo['email']) if useAuthor and resourceInfo and resourceInfo['email'] else ''
	cmd = ['git', 'log', '--stat', '--pretty="COMMIT:%H,%ct,%cI,%s"', '--since={}'.format(start), '--until={}'.format(end)]
	if authorOption:
		cmd.append(authorOption)
	# print(' '.join(cmd))
	return getChangeStats(projectDir, cmd)

def getLastCommitId(projectDir, email):
	cmd = ['git', 'log',  '--pretty="%H,%s"', '--max-count=1']
	if email:
		cmd.append('--author={}'.format(email))
	resultList = getCommandResultList(cmd, projectDir)
	if resultList and len(resultList) > 0:
		lastCommit = resultList[0]
		# Get rid of surrounding quotations
		if lastCommit[0] == '"':
			lastCommit = lastCommit[1:]
		if lastCommit[len(lastCommit) - 1] == '"':
			lastCommit = lastCommit[:-1]		
		parts = lastCommit.split(',')
		if parts and len(parts) == 2:
			return {
				"commitId": parts[0],
				"comment": parts[1]
			}
	return {}

def getRepoConfigUserEmail(projectDir):
	cmd = ['git', 'config', '--get', '--global', 'user.email']
	return getCommandResultLine(cmd, projectDir)

def getRepoUrlLink(projectDir):
	cmd = ['git', 'config', '--get', 'remote.origin.url']
	link = getCommandResultLine(cmd, projectDir)

	if link and link.endswith('.git'):
		link = link[0:link.rindex('.git')]
	return link 

def getToday():
	day = datetime.fromtimestamp(round(timeModule.time()))
	today = datetime(day.year, day.month, day.day)
	start = today.timestamp()
	end = start + ONE_DAY_SEC
	return { "start": int(start), "end": int(end) } 

def getYesterday():
	day = datetime.fromtimestamp(round(timeModule.time()))
	today = datetime(day.year, day.month, day.day) - timedelta(days=1)
	start = today.timestamp()
	end = start + ONE_DAY_SEC
	return { "start": int(start), "end": int(end) } 

def getThisWeek():
	day = datetime.fromtimestamp(round(timeModule.time()))
	today = datetime(day.year, day.month, day.day) - timedelta(days=(day.weekday() + 1))
	start = today.timestamp()
	end = start + ONE_WEEK_SEC
	return { "start": int(start), "end": int(end) }