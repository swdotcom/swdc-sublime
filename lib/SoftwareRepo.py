import sublime_plugin, sublime
import re
from datetime import *
from urllib.parse import quote_plus
from .SoftwareModels import CommitChangeStats, ContributorMember
from .SoftwareHttp import *
from .SoftwareUtil import *
from .SoftwareSettings import *
from .CommonUtil import *

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

	if not resultList:
		return changeStats

	changeStats = accumulateStatChanges(resultList)

	return changeStats

def getUncommittedChanges(projectDir):
    cmd = ['git', 'diff', '--stat']
    return getChangeStats(projectDir, cmd)


def buildRepoKey(identifier, branch, tag):
	return "%s_%s_%s" % (identifier, branch, tag)

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
