import sublime_plugin, sublime

class OpenTreeView(sublime_plugin.TextCommand):

    def run(self, edit):
        tree_view = None
        window = self.view.window()
        orig_view = window.active_view()
        if not tree_view:
            window.set_sidebar_visible(False)
            layout = window.get_layout()
            if len(layout['cols']) < 3:
                layout['cols'] = [0, 0.2, 1]
                layout['cells'] = [[0, 0, 1, len(layout['rows']) - 1]] + [
                    [cell[0] + 1, cell[1], cell[2] + 1, cell[3]] for cell in layout['cells']
                ]
                window.set_layout(layout)
                for view in window.views():
                    (group, index) = window.get_view_index(view)
                    window.set_view_index(view, group + 1, index)
            elif layout['cols'][1] > 0.3:
                layout['cols'] = [0, min(0.2, layout['cols'][1] / 2.0)] + layout['cols'][1:]
                layout['cells'] = [[0, 0, 1, len(layout['rows']) - 1]] + [
                    [cell[0] + 1, cell[1], cell[2] + 1, cell[3]] for cell in layout['cells']
                ]
                window.set_layout(layout)
                for view in window.views():
                    (group, index) = window.get_view_index(view)
                    window.set_view_index(view, group + 1, index)

            tree_view = window.new_file()
            tree_view.settings().set('line_numbers', False)
            tree_view.settings().set('gutter', False)
            tree_view.settings().set('rulers', [])
            tree_view.set_read_only(True)
            tree_view.set_name('Code Time Tree View')
            tree_view.set_scratch(True)
            if window.num_groups() > 1: 
                (group, index) = window.get_view_index(orig_view)
                if group != 0:
                    group = 0
                    window.set_view_index(tree_view, group, 0)
                    window.focus_view(orig_view) # Um... Seems like a bug
        else:
        	tree_view.erase_phantoms('remote_tree')

        self.view = tree_view
        self.phantom_set = sublime.PhantomSet(tree_view, 'remote_tree')

        # trees.append(self) 

        self.tree = { 
        	'index': 0,
        	'depth': 0,
        	'path': '',
        	'name': '',
        	'dir': True,
        	'expanded': False,
        	'childs': [
                {
                    'index': 1,
                    'depth': 1,
                    'name': 'CODE TIME',
                    'dir': True,
                    'expanded': False,
                    'childs': [
                        {
                            'index': 2,
                            'depth': 2,
                            'icon': 'paw',
                            'name': 'See advanced metrics',
                            'dir': False,
                            'expanded': False,
                            'childs': None
                        },
                        {
                            'index': 3,
                            'depth': 2,
                            'icon': 'dashboard',
                            'name': 'Generate dashboard',
                            'dir': False,
                            'expanded': False,
                            'childs': None
                        },
                        {
                            'index': 4,
                            'depth': 2,
                            'icon': 'visible',
                            'name': 'Hide status bar metrics', #TODO: make this a switch with Show status bar metrics
                            'dir': False,
                            'expanded': False,
                            'childs': None
                        },
                        {
                            'index': 5,
                            'depth': 2,
                            'icon': 'readme',
                            'name': 'Learn more',
                            'dir': False,
                            'expanded': False,
                            'childs': None
                        },
                        {
                            'index': 6,
                            'depth': 2,
                            'icon': 'message',
                            'name': 'Submit feedback',
                            'dir': False,
                            'expanded': False,
                            'childs': None
                        }
                    ]
                },
                {
                    'index': 7,
                    'depth': 1,
                    'name': 'ACTIVITY METRICS',
                    'dir': True,
                    'expanded': False,
                    'childs': [
                        {
                            'index': 8,
                            'depth': 2,
                            'name': 'Editor time',
                            'dir': True,
                            'expanded': False,
                            'childs': [
                                {
                                    'index': 9,
                                    'depth': 3,
                                    'name': 'Today: 0 min', #TODO: hardcoded right now
                                    'dir': False,
                                    'expanded': False,
                                    'childs': None
                                }
                            ]
                        },
                        {
                            'index': 9,
                            'depth': 2,
                            'name': 'Code time',
                            'dir': True,
                            'expanded': False,
                            'childs': [
                                {
                                    'index': 10,
                                    'depth': 3,
                                    'name': 'Today: 0 min', #TODO: hardcoded right now
                                    'dir': False,
                                    'expanded': False,
                                    'childs': None
                                },
                                {
                                    'index': 11,
                                    'depth': 3,
                                    'name': 'Your average: 0 min', #TODO: hardcoded right now
                                    'dir': False,
                                    'expanded': False,
                                    'childs': None
                                },
                                {
                                    'index': 12,
                                    'depth': 3,
                                    'name': 'Global average: 0 min', #TODO: hardcoded right now
                                    'dir': False,
                                    'expanded': False,
                                    'childs': None
                                }
                            ]
                        },
                        {
                            'index': 13,
                            'depth': 2,
                            'name': 'Lines added',
                            'dir': True,
                            'expanded': False,
                            'childs': [
                                {
                                    'index': 14,
                                    'depth': 3,
                                    'name': 'Today: 0 min', #TODO: hardcoded right now
                                    'dir': False,
                                    'expanded': False,
                                    'childs': None
                                },
                                {
                                    'index': 15,
                                    'depth': 3,
                                    'name': 'Your average: 0 min', #TODO: hardcoded right now
                                    'dir': False,
                                    'expanded': False,
                                    'childs': None
                                },
                                {
                                    'index': 16,
                                    'depth': 3,
                                    'name': 'Global average: 0 min', #TODO: hardcoded right now
                                    'dir': False,
                                    'expanded': False,
                                    'childs': None
                                }
                            ]
                        },
                            {
                            'index': 17,
                            'depth': 2,
                            'name': 'Lines removed',
                            'dir': True,
                            'expanded': False,
                            'childs': [
                                {
                                    'index': 18,
                                    'depth': 3,
                                    'name': 'Today: 0 min', #TODO: hardcoded right now
                                    'dir': False,
                                    'expanded': False,
                                    'childs': None
                                },
                                {
                                    'index': 19,
                                    'depth': 3,
                                    'name': 'Your average: 0 min', #TODO: hardcoded right now
                                    'dir': False,
                                    'expanded': False,
                                    'childs': None
                                },
                                {
                                    'index': 20,
                                    'depth': 3,
                                    'name': 'Global average: 0 min', #TODO: hardcoded right now
                                    'dir': False,
                                    'expanded': False,
                                    'childs': None
                                }
                            ]
                        }
                    ]
                },
                {
                    'index': 21,
                    'depth': 1,
                    'name': 'PROJECT METRICS',
                    'dir': True,
                    'expanded': False,
                    'childs': [
                        {
                            'index': 22,
                            'depth': 2,
                            'name': 'Open changes',
                            'dir': True,
                            'expanded': False,
                            'childs': None
                        },
                        {
                            'index': 23,
                            'depth': 2,
                            'name': 'Committed today',
                            'dir': True,
                            'expanded': False,
                            'childs': None
                        }
                    ]
                }
                
            ]
        }
        self.list = [self.tree]
        self.opened = None
        self.expand(0)


    def expand(self, index):
        item = self.list[index]
        item['expanded'] = not item['expanded']
        if item['expanded']: # and item['childs'] == None -- caching
            if item['childs']:
                for child in item['childs']:
                    child['index'] = len(self.list)
                    self.list.append(child)
            self.rebuild_phantom()
        else:
            self.rebuild_phantom()

    def open(self, index):  
        item = self.list[index]
        self.opened = item
        self.rebuild_phantom()

    def on_click(self, url):
        comps = url.split('/')
        if comps[0] == 'open':
            self.open(int(comps[1]))
        else:
            self.expand(int(comps[1]))

    def rebuild_phantom(self):
        result = self.render_subtree(self.tree, [])
        # print(result)
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
            .file.active {
            background-color: color(var(--background) blend(var(--foreground) 80%));
            border-radius: 3px;
            }
            .file span {
            font-size: 7px; 
            }
            .file a {
            text-decoration: none;
            padding-bottom: 5px;
            color: var(--foreground);
            }
        </style>''' + ''.join(result) + '</body>'
        self.phantom = sublime.Phantom(sublime.Region(0), html, sublime.LAYOUT_BLOCK, on_navigate=self.on_click)
        self.phantom_set.update([self.phantom])


    # TODO: modify render_subtree
    def render_subtree(self, item, result):
        # if file
        # if not item['dir']:
        #     result.append('<div class="file{active}" style="margin-left: {margin}px"><a href=open/{index}><span>📄&nbsp;</span>{name}</a></div>'.format(
        #         active=' active' if item == self.opened else '',
        #         margin=(item['depth'] * 20) - 10,
        #         index=item['index'],
        #         name=item['name']))
        #     return result
        
        if not item['dir']:
            if 'icon' in item:
                result.append('<div class="file{active}" style="margin-left: {margin}px;"><a href=open/{index}><img height="16" width="16" alt="" src="{icon}">{name}</a></div>'.format(
                    active=' active' if item == self.opened else '',
                    margin=(item['depth'] * 20) - 10,
                    index=item['index'],
                    name=item['name'],
                    icon=icons[item['icon']]))
                return result
            else:
                result.append('<div class="file{active}" style="margin-left: {margin}px"><a href=open/{index}><span>📄&nbsp;</span>{name}</a></div>'.format(
                    active=' active' if item == self.opened else '',
                    margin=(item['depth'] * 20) - 10,
                    index=item['index'],
                    name=item['name']))
                return result


        # if in a directory
        if item['depth'] > 0:
            result.append('<div class="dir" style="margin-left: {margin}px"><a href=expand/{index}>{sign}&nbsp;{name}</a></div>'.format(
                margin=(item['depth'] * 20) - 10,
                index=item['index'],
                name=item['name'],
                sign='▼' if item['expanded'] else '▶'))

        # if directory with things
        if item['childs'] != None and item['expanded']:
            for child in item['childs']:
                self.render_subtree(child, result)

        return result
