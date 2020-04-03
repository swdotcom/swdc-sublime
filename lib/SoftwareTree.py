import sublime_plugin, sublime 
from copy import deepcopy
from threading import Thread, Timer, Event 
from .SoftwareOffline import getSessionSummaryData
from .SoftwareDashboard import launchCodeTimeMetrics
from .SoftwareUtil import *
from .SoftwareModels import SessionSummary
from .SoftwareWallClock import *
from .SoftwareFileChangeInfoSummaryData import *
from .SoftwareRepo import *
from .SoftwareUserStatus import *

icons = getIcons()
tree_view = None
orig_layout = None
NO_ID = 'NO_ID'
CODETIME_TREEVIEW_NAME = 'Code Time Tree View'
shouldOpen = True
mainSections = ['code-time-actions', 'activity-metrics', 'project-metrics']

def setShouldOpen(val):
    global shouldOpen
    shouldOpen = val

'''
Because we do frequent tree updates/refreshes, we don't want to redraw the tree in its unopened
state, especially if the user is in the middle of using it. This data struct keeps track of what
was opened so state can be maintained across draws.
'''
open_state = set()

# IDs for code time action buttons
CODE_TIME_ACTIONS = {'advanced-metrics', 'open-dashboard', 'toggle-status-metrics', 'learn-more', 'submit-feedback', 'google-signup', 'github-signup', 'email-signup'}

# TODO: rare bug where tree isn't clickable (possibly slow wifi)
class OpenTreeView(sublime_plugin.WindowCommand):

    def run(self):
        if not shouldOpen:
            return

        global tree_view 
        global orig_layout
        self.currentKeystrokeStats = SessionSummary()
        window = self.window

        orig_view = window.active_view()
        
        # Create tree view if it doesn't exist yet
        if tree_view is None:
            layout = window.get_layout()
            layout['cols'] = [0, 1]
            layout['rows'] = [0, 1]
            layout['cells'] = [[0,0,1,1]]
            window.set_layout(layout)
            self.build_tree_layout()

        self.phantom_set = sublime.PhantomSet(tree_view, 'software_tree')

        if len(window.views()) == 1:
            window.focus_group(1)

        statusBarMessage = 'Hide status bar metrics' if getValue("show_code_time_status", True) else 'Show status bar metrics'

        self.tree = { 
        	'index': 0,
        	'depth': 0,
        	'path': '',
        	'name': '',
            'id': '',
        	'dir': True,
        	'expanded': False,
        	'childs': [
                {
                    'depth': 1,
                    'id': 'code-time-actions',
                    'name': 'CODE TIME',
                    'dir': True,
                    'expanded': True,
                    'childs': [
                        {
                            'depth': 2,
                            'id': 'advanced-metrics',
                            'icon': 'paw',
                            'name': 'See advanced metrics',
                            'dir': False,
                            'expanded': False,
                            'childs': None
                        },
                        { 
                            'depth': 2,
                            'id': 'toggle-status-metrics',
                            'icon': 'visible',
                            'name': statusBarMessage,
                            'dir': False,
                            'expanded': False,
                            'childs': None
                        },
                        { 
                            'depth': 2,
                            'id': 'learn-more',
                            'icon': 'readme',
                            'name': 'Learn more',
                            'dir': False,
                            'expanded': False,
                            'childs': None
                        },
                        {
                            'depth': 2,
                            'id': 'submit-feedback',
                            'icon': 'message',
                            'name': 'Submit feedback',
                            'dir': False,
                            'expanded': False,
                            'childs': None
                        },
                        { 
                            'depth': 2,
                            'id': 'open-dashboard',
                            'icon': 'dashboard',
                            'name': 'View summary',
                            'dir': False,
                            'expanded': False,
                            'childs': None
                        }
                    ]
                }
            ]
        }

        # Build tree nodes
        data = getSessionSummaryData()

        self.addConnectionStatusIcons()
        self.buildMetricsNodes(data)
        self.buildCommitTreeNodes()
        self.expand(self.tree, '')

    def build_tree_layout(self):
        global tree_view 
        global orig_layout 
        window = self.window 
        window.set_sidebar_visible(False)
        layout = window.get_layout()
        orig_layout = deepcopy(layout)
        if len(layout['cols']) < 3:
            layout['cols'] = [0, 0.25, 1]
        elif layout['cols'][1] > 0.3:
            # Evenly space the original views
            tree_view_width = min(0.25, layout['cols'][1] / 2.0)
            new_orig_views = list(map(lambda x: x + (1 - x) * tree_view_width, layout['cols'][1:-1])) 
            layout['cols'] = [0, tree_view_width] + new_orig_views + [layout['cols'][-1]]

        layout['cells'] = [[0, 0, 1, len(layout['rows']) - 1]] + [
            [cell[0] + 1, cell[1], cell[2] + 1, cell[3]] for cell in layout['cells']
        ]
        window.set_layout(layout)

        tree_view = window.new_file()
        tree_view.settings().set('line_numbers', False)
        tree_view.settings().set('gutter', False)
        tree_view.settings().set('rulers', [])
        tree_view.set_read_only(True)
        tree_view.set_name(CODETIME_TREEVIEW_NAME)
        tree_view.set_scratch(True)
        if window.num_groups() > 1:
            for view in window.views():
                (group, index) = window.get_view_index(view)
                window.set_view_index(view, group + 1, 0)
            window.set_view_index(tree_view, 0, 0)


    def expand(self, tree, id):
        if 'id' in tree and tree['id'] == id:
            tree['expanded'] = not tree['expanded']
            if tree['expanded'] is True:
                open_state.add(tree['id'])
            else:
                open_state.remove(tree['id'])
            self.rebuild_phantom()
            return True
        else:
            if tree['childs'] is None:
                return False
            else:
                for child in tree['childs']:
                    if self.expand(child, id):
                        return True

    def performCodeTimeAction(self, command):
        if command == 'open-dashboard':
            codetimemetricsthread = Thread(target=launchCodeTimeMetrics)
            codetimemetricsthread.start()
        elif command == 'toggle-status-metrics':
            toggleStatus()
            refreshTreeView()
        elif command == 'learn-more':
            displayReadmeIfNotExists()
        elif command == 'advanced-metrics':
            launchWebDashboardUrl()
        elif command == 'submit-feedback':
            launchSubmitFeedback()
        elif command == 'google-signup':
            launchLoginUrl('google')
        elif command == 'github-signup':
            launchLoginUrl('github')
        elif command == 'email-signup':
            launchLoginUrl('software')

    def getAuthTypeLabelAndIcon(self):
        authType = getItem('authType')

        if (authType == 'google'):
            return { "label": 'Connected using Google', "icon": 'google-icon' }
        elif (authType == 'github'):
            return { "label": 'Connected using GitHub', "icon": 'github-icon' }
        elif (authType == 'software'):
            return { "label": 'Connected using email', "icon": 'envelope-icon' }
        return { "label": 'Connected', "icon": 'envelope-icon' } 

    def on_click(self, url):
        comps = url.split('/')

        # Don't close or open this
        if comps[1] in mainSections:
            return

        if comps[1] in CODE_TIME_ACTIONS:
            self.performCodeTimeAction(comps[1])
            return 

        if comps[0] == 'expand':
            self.expand(self.tree, comps[1])

    '''
    TODO: lots of styles changes to look more like Atom/VSCode, though 
          Sublime's "minihtml" engine has some large restrictions
    '''
    def rebuild_phantom(self):
        result = self.render_subtree(self.tree, [])
        html = '''<body id="tree">
            <style>
            body {
            font-size: 12px;
            line-height: 16px;
            }
            .file a, .dir a {
            display: block;
            padding-left: 4px;
            }
            .dir a {
            padding-top: 1px;
            padding-bottom: 2px;
            text-decoration: none;
            }
            .file span {
            font-size: 7px; 
            }
            .file a {
            text-decoration: none;
            padding-bottom: 5px;
            color: var(--foreground);
            }
            .file p {
            position: relative;
            bottom: 2px;
            display: inline;
            }
        </style>''' + ''.join(result) + '</body>'
        self.phantom = sublime.Phantom(sublime.Region(0), html, sublime.LAYOUT_BLOCK, on_navigate=self.on_click)
        self.phantom_set.update([self.phantom])

    def render_subtree(self, item, result):
        if 'id' in item and item['id'] in open_state:
            item['expanded'] = True

        global icons
        if not item['dir']:
            if 'icon' in item:
                result.append('<div class="file" style="margin-left: {margin}px;"><a href=open/{index}><img height="16" width="16" alt="" src="{icon}"><p> {name}</p></a></div>'.format(
                    margin=(item['depth'] * 20) - 10,
                    index=item['id'] if 'id' in item else NO_ID,
                    name=item['name'],
                    icon=icons[item['icon']]))
                    # icon='🚀'))
                return result
            else:
                result.append('<div class="file" style="margin-left: {margin}px"><a href=open/{index}>{name}</a></div>'.format(
                    margin=(item['depth'] * 20) - 10,
                    index=item['id'] if 'id' in item else NO_ID,
                    name=item['name']))
                return result

        # if in a directory
        if item['depth'] > 0:
            result.append('<div id="{id}" class="dir" style="margin-left: {margin}px"><a href=expand/{index}>{sign}&nbsp;{name}</a></div>'.format(
                id=item['id'] if 'id' in item else NO_ID,
                margin=(item['depth'] * 20) - 10,
                index=item['id'] if 'id' in item else NO_ID,
                name=item['name'],
                sign='' if ('id' in item and item['id'] in mainSections) else ('▼' if (item['expanded']) else '▶')))

        # if directory with things
        if item['childs'] != None and item['expanded']:
            for child in item['childs']:
                self.render_subtree(child, result)

        return result

    def setCurrentKeystrokeStats(self, keystrokeStats):
        if not keystrokeStats:
            self.currentKeystrokeStats = SessionSummary()
        else:
            for key in keystrokeStats.source:
                # fileInfo is of type FileChangeInfo
                fileInfo = keystrokeStats.source[key] 
                self.currentKeystrokeStats.currentDayKeystrokes = fileInfo.keystrokes
                self.currentKeystrokeStats.currentDayLinesAdded = fileInfo.linesAdded
                self.currentKeystrokeStats.currentDayLinesRemoved = fileInfo.linesRemoved

    def addConnectionStatusIcons(self):
        if not getItem('name'):
            self.addSignupButtons()
        else:
            authObj = self.getAuthTypeLabelAndIcon()
            connectedNode = {
                'depth': 2,
                'id': 'connected-type-button',
                'icon': authObj['icon'],
                'name': authObj['label'],
                'dir': False,
                'expanded': False,
                'childs': None
            }
            self.tree['childs'][0]['childs'].insert(0, connectedNode)

    def addSignupButtons(self):
        googleSignup = {
            'depth': 2,
            'id': 'google-signup',
            'icon': 'google-icon',
            'name': 'Sign up with Google',
            'dir': False,
            'expanded': False,
            'childs': None
        }
        githubSignup = {
            'depth': 2,
            'id': 'github-signup',
            'icon': 'github-icon',
            'name': 'Sign up with GitHub',
            'dir': False,
            'expanded': False,
            'childs': None
        }
        emailSignup = {
            'depth': 2,
            'id': 'email-signup',
            'icon': 'envelope-icon',
            'name': 'Sign up with email',
            'dir': False,
            'expanded': False,
            'childs': None
        }
        self.tree['childs'][0]['childs'] = [googleSignup, githubSignup, emailSignup] + self.tree['childs'][0]['childs']

    # data is an object of shape returned by SessionSummary()
    def buildMetricsNodes(self, data):
        # delete the current (ACTIVITY METRICS) from tree['childs']
        self.tree['childs'] = list(filter(lambda x: x['name'] != 'ACTIVITY METRICS', self.tree['childs']))

        newActivityMetrics = {
            'index': 2,
            'depth': 1,
            'id': 'activity-metrics',
            'name': 'ACTIVITY METRICS',
            'dir': True,
            'expanded': True,
            'childs': []
        }

        # EDITOR-TIME stuff
        editorMinutes = getHumanizedWcTime()
        newActivityMetrics['childs'].append(self.buildCodeTimeMetricsItem('editor-time', 'Editor time', editorMinutes))

        # CODE-TIME stuff
        codeTimeMinutes = humanizeMinutes(data['currentDayMinutes']).strip()
        avgDailyMinutes = humanizeMinutes(data['averageDailyMinutes']).strip()
        globalAvgMinutes = humanizeMinutes(data['globalAverageSeconds'] / 60).strip()
        boltIcon = 'bolt' if data['currentDayMinutes'] > data['averageDailyMinutes'] else 'bolt-grey'
        newActivityMetrics['childs'].append(self.buildCodeTimeMetricsItem('code-time', 'Code time', codeTimeMinutes, avgDailyMinutes, globalAvgMinutes, boltIcon))

        currLinesAdded = self.currentKeystrokeStats['currentDayLinesAdded'] + data['currentDayLinesAdded']
        linesAdded = formatNumWithK(currLinesAdded)
        avgLinesAdded = formatNumWithK(data['averageLinesAdded'])
        globalLinesAdded = formatNumWithK(data['globalAverageLinesAdded'])
        boltIcon = 'bolt' if data['currentDayLinesAdded'] > data['averageLinesAdded'] else 'bolt-grey'
        newActivityMetrics['childs'].append(self.buildCodeTimeMetricsItem('lines-added', 'Lines added', linesAdded, avgLinesAdded, globalLinesAdded, boltIcon))

        currLinesRemoved = self.currentKeystrokeStats['currentDayLinesRemoved'] + data['currentDayLinesRemoved']
        linesRemoved = formatNumWithK(currLinesRemoved)
        avgLinesRemoved = formatNumWithK(data['averageLinesRemoved'])
        globalLinesRemoved = formatNumWithK(data['globalAverageLinesRemoved'])
        boltIcon = 'bolt' if data['currentDayLinesRemoved'] > data['averageLinesRemoved'] else 'bolt-grey'
        newActivityMetrics['childs'].append(self.buildCodeTimeMetricsItem('lines-removed', 'Lines removed', linesRemoved, avgLinesRemoved, globalLinesRemoved, boltIcon))

        currKeystrokes = self.currentKeystrokeStats['currentDayKeystrokes'] + data['currentDayKeystrokes']
        keystrokes = formatNumWithK(currKeystrokes)
        avgKeystrokes = formatNumWithK(data['averageDailyKeystrokes'])
        globalKeystrokes = formatNumWithK(data['globalAverageDailyKeystrokes'])
        boltIcon = 'bolt' if data['currentDayKeystrokes'] > data['averageDailyKeystrokes'] else 'bolt-grey'
        newActivityMetrics['childs'].append(self.buildCodeTimeMetricsItem('keystrokes', 'Keystrokes', keystrokes, avgKeystrokes, globalKeystrokes, boltIcon))
        
        
        # Num files changed
        fileChangeInfoMap = getFileChangeSummaryAsJson()
        topFilesNode = self.buildTopFilesNode(fileChangeInfoMap)
        if topFilesNode:
            newActivityMetrics['childs'].append(topFilesNode)

        # More file metrics nodes
        fileChangeInfos = fileChangeInfoMap.values()

        topKpmFileNodes = self.topFilesMetricsNode(fileChangeInfos, 'Top files by KPM', 'kpm', 'top-kpm-files')
        if topKpmFileNodes:
            newActivityMetrics['childs'].append(topKpmFileNodes)

        topKeystrokeFileNodes = self.topFilesMetricsNode(fileChangeInfos, 'Top files by keystrokes', 'keystrokes', 'top-keystrokes-files')
        if topKeystrokeFileNodes:
            newActivityMetrics['childs'].append(topKeystrokeFileNodes)

        topCodetimeFileNodes = self.topFilesMetricsNode(fileChangeInfos, 'Top files by code time', 'duration_seconds', 'top-codetime-files')
        if topCodetimeFileNodes:
            newActivityMetrics['childs'].append(topCodetimeFileNodes)

        # Insert newActivityMetrics into second position of tree['childs']
        self.tree['childs'].insert(1, newActivityMetrics)


    def buildCodeTimeMetricsItem(self, id, label, todayValue, avgValue=None, globalAvgValue=None, avgIcon=None):
        todayString = datetime.today().strftime('%a')
        item = {
            'depth': 2,
            'id': id,
            'name': label,
            'dir': True,
            'expanded': False,
            'childs': [
                {
                    'depth': 3,
                    'icon': 'rocket',
                    'name': 'Today: {}'.format(todayValue),
                    'dir': False,
                    'expanded': False,
                    'childs': None
                }
            ]
        }

        if avgValue and globalAvgValue:
            item['childs'].append({
                    'depth': 3,
                    'icon': avgIcon,
                    'name': 'Your average ({}): {}'.format(todayString, avgValue),
                    'dir': False,
                    'expanded': False,
                    'childs': None
                })
            item['childs'].append({
                    'depth': 3,
                    'icon': 'global-grey',
                    'name': 'Global average ({}): {}'.format(todayString, globalAvgValue),
                    'dir': False,
                    'expanded': False,
                    'childs': None
                })

        return item 

    def buildTopFilesNode(self, fileChangeInfoMap):
        topFileTreeNodes = {
            'depth': 2,
            'id': 'files-changed',
            'name': 'Files changed today',
            'dir': True,
            'expanded': False,
            'childs': [
                {
                    'depth': 3,
                    'name': '',
                    'dir': False,
                    'expanded': False,
                    'childs': None
                }
            ]
        }
        filesChanged = len(fileChangeInfoMap.keys()) if fileChangeInfoMap else 0

        if filesChanged > 0:
            topFileTreeNodes['childs'][0]['name'] = 'Today: {}'.format(filesChanged)
            return topFileTreeNodes
        else:
            return {}

    def buildOpenChangesDirNodeItem(self, dirName, id, insertions, deletions, commitCount=None, fileCount=None):
        newNode = {
            'depth': 3,
            'id': id,
            'name': dirName,
            'dir': True,
            'expanded': False,
            'childs': []
        }

        newNode['childs'].append({
            'depth': 4,
            'icon': 'insertion',
            'name': 'Insertion(s): {}'.format(insertions),
            'dir': False,
            'expanded': False,
            'childs': None 
        })
        newNode['childs'].append({
            'depth': 4,
            'icon': 'deletion',
            'name': 'Deletions(s): {}'.format(deletions),
            'dir': False,
            'expanded': False,
            'childs': None 
        })

        if commitCount:
            newNode['childs'].append({
                'depth': 4,
                'icon': 'commit',
                'name': 'Commit(s): {}'.format(commitCount),
                'dir': False,
                'expanded': False,
                'childs': None 
            })  
            newNode['childs'].append({
                'depth': 4,
                'icon': 'files',
                'name': 'Files changed: {}'.format(fileCount),
                'dir': False,
                'expanded': False,
                'childs': None 
            })

        return newNode


    def topFilesMetricsNode(self, fileChangeInfos, name, sortBy, id):
        if not fileChangeInfos or len(fileChangeInfos) == 0:
            return None 

        node = {
            'depth': 2,
            'id': id,
            'name': name,
            'dir': True,
            'expanded': False,
            'childs': []
        }

        sortedArr = []
        if sortBy == 'duration_seconds' or sortBy == 'kpm' or sortBy == 'keystrokes':
            sortedArr = list(sorted(fileChangeInfos, key=lambda info: info[sortBy], reverse=True))
        else:
            log('Sorting by invalid sortBy value: "{}"'.format(sortBy))

        childrenNodes = []
        length = min(3, len(sortedArr))
        for i in range(0, length):
            sortedObj = sortedArr[i]
            fileName = sortedObj['name']

            val = 0
            if sortBy == 'kpm' or sortBy == 'keystrokes':
                val = formatNumWithK(sortedObj['kpm'] or 0)
            elif sortBy == 'duration_seconds':
                minutes = sortedObj.get('duration_seconds', 0) / 60
                val = humanizeMinutes(minutes)

            fsPath = sortedObj['fsPath']
            label = '{} | {}'.format(fileName, val)

            valItem = {
                'depth': 3,
                'name': label,
                'dir': False,
                'expanded': False,
                'childs': None 
            }

            node['childs'].append(valItem)
        
        return node 

    def buildCommitTreeNodes(self):
        self.tree['childs'] = list(filter(lambda x: x['name'] != 'PROJECT METRICS', self.tree['childs']))

        newProjectMetrics = {
            'depth': 1,
            'id': 'project-metrics',
            'name': 'PROJECT METRICS',
            'dir': True,
            'expanded': True,
            'childs': []
        }

        folders = getOpenProjects()
        
        openChangesNode = {
            'depth': 2,
            'id': 'open-changes',
            'name': 'Open changes',
            'dir': True,
            'expanded': False,
            'childs': []
        }
        committedTodayNode = {
            'depth': 2,
            'id': 'committed-today',
            'name': 'Committed today',
            'dir': True,
            'expanded': False,
            'childs': []
        }
        
        if len(folders) > 0:
            for i in range(len(folders)):
                directory = folders[i]
                basename = os.path.basename(directory)

                # Add uncommitted changes
                currentChangesSummary = getUncommittedChanges(directory)
                uncommittedNode = self.buildOpenChangesDirNodeItem(basename, 'uncommitted-{}'.format(i), currentChangesSummary['insertions'], currentChangesSummary['deletions'])
                openChangesNode['childs'].append(uncommittedNode)

                # Add committed changes
                todaysChangeSummary = getTodaysCommits(directory)
                committedNode = self.buildOpenChangesDirNodeItem(basename, 'committed-{}'.format(i), todaysChangeSummary['insertions'], todaysChangeSummary['deletions'], todaysChangeSummary['commitCount'], todaysChangeSummary['fileCount'])
                committedTodayNode['childs'].append(committedNode)

        newProjectMetrics['childs'].append(openChangesNode)
        newProjectMetrics['childs'].append(committedTodayNode)

        self.tree['childs'].insert(2, newProjectMetrics)


# If the tree view is closed, collapse its view and set the layout back to its original.
# TODO: improvements for this method needed b/c the tree view is itself part of the user's 
#       view layout and it's difficult to return to that state 
def handleCloseTreeView():
    global shouldOpen
    global tree_view
    shouldOpen = False
    tree_view = None
    # global orig_layout
    
    # groups = set()
    # window = sublime.active_window()
    # for view in window.views():
    #     (group, _) = window.get_view_index(view)
    #     groups.add(group)
    # for group in groups:
    #     views = window.views_in_group(group)
    #     for view in reversed(views):
    #         # Shift the views back
    #         window.set_view_index(view, group - 1, 0)

    # window.set_layout(orig_layout)
    # orig_layout = None