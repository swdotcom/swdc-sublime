from threading import Thread, Timer, Event
from package_control import events
from queue import Queue
import webbrowser
import time
import datetime
import json
import os
import sublime_plugin, sublime
from .lib.SoftwareHttp import *
from .lib.SoftwareUtil import *
from .lib.SoftwareMusic import *
from .lib.SoftwareRepo import *
from .lib.SoftwareOffline import *
from .lib.SoftwareSettings import *

music_time_menu = """[
    {
        "id": "tools",
        "children":
        [
            { "caption": "-", "id": "software" },
            {
                "caption": "Music Time",
                "children":
                [
                    { "command": "launch_music_time_metrics", "caption": "Music Time Dashboard" },
                    { "command": "software_top_forty", "caption": "Software Top 40" },
                    { "command": "connect_spotify", "caption": "Log in to see your coding data in Code Time" },
                    { "command": "toggle_status_bar_metrics", "caption": "Show/Hide Status Bar Metrics" },
                    { "command": "hide_console_message", "caption": "Hide Console Message" },
                    { "command": "show_console_message", "caption": "Show Console Message" },
                    
                ]
            },
        ]
    }
]"""

code_time_menu = '''[
    {
        "id": "tools",
        "children":
        [
            { "caption": "-", "id": "software" },
            {
                "caption": "Code Time",
                "children":
                [
                    { "command": "launch_code_time_metrics", "caption": "Code Time Dashboard" },
                    { "command": "launch_custom_dashboard", "caption": "Generate a Custom Dashboard" },
                    { "command": "software_top_forty", "caption": "Software Top 40" },
                    { "command": "go_to_software", "caption": "Web Dashboard" },
                    { "command": "code_time_login", "caption": "Log in to see your coding data in Code Time" },
                    { "command": "pause_kpm_updates", "caption": "Pause Code Time" },
                    { "command": "enable_kpm_updates", "caption": "Enable Code Time" },
                    { "command": "toggle_status_bar_metrics", "caption": "Show/Hide Status Bar Metrics" },
                    { "command": "hide_console_message", "caption": "Hide Console Message" },
                    { "command": "show_console_message", "caption": "Show Console Message" },
                    
                ]
            },
        ]
    }
]'''

default_code_time = '''[
    { "command": "launch_code_time_metrics", "caption": "Code Time: Dashboard" },
    { "command": "go_to_software", "caption": "Code Time: Go to software.com" },
    { "command": "software_top_forty", "caption": "Code Time: Software top 40" },
    { "command": "toggle_status_bar_metrics", "caption": "Code Time: Show/hide status bar metrics" },
]'''

default_music_time = '''[
    { "command": "launch_music_time_metrics", "caption": "Music Time Dashboard" },
    { "command": "software_top_forty", "caption": "Software Top 40" },
    { "command": "connect_spotify", "caption": "Connect to spotify account" },
    { "command": "toggle_status_bar_metrics", "caption": "Show/Hide Status Bar Metrics" },
]'''

plugin_name = 'music-time'

def setname():

    # plugin_name = getValue('name','code-time')
    print("\n`",plugin_name,"\n###############")
    if (plugin_name == 'code-time' ):
        '''  CODE TIME '''
        setValue('name','code-time')
        try:
            with open(r"Main.sublime-menu","r+") as menufile:
                menufile.write(code_time_menu)
                print(" code-time menu updated")
                menufile.seek(0)
                print(menufile.read())
                menufile.close()
                print("file closed")
        except Exception as e:
            print("MAIN MENU\n",e)

        try:
            write_menu(code_time_menu)
            print('Done')
        except Exception as e:
            print("write cache error")


        try:
            with open(r"Default.sublime-commands","r+") as defaultmenu:
                defaultmenu.write(default_code_time)
                print(" code-time  defaultmenu updated")
                defaultmenu.seek(0)
                print(defaultmenu.read())
                defaultmenu.close()
                print("file closed")
        except Exception as e:
            print("Default MENU\n",e)

        name = "Code Time"
    
    else:
    # elif (plugin_name == 'music-time'):
        ''' MUSIC TIME  '''
        # plugin_name = getValue('music-time',True)
        setValue('name','music-time')

        try:
            with open(r"Main.sublime-menu","w+") as menufile:
                menufile.write(music_time_menu)
                print(" music-time menu updated")
                menufile.seek(0)
                print(menufile.read())
                menufile.close()
                print("file closed")
        except Exception as e:
            print("MAIN MENU\n",e)

        try:
            write_menu(music_time_menu)
            print('Done')
        except Exception as e:
            print("write cache error")

        try:
            with open(r"Default.sublime-commands","w+") as defaultmenu:
                defaultmenu.write(default_music_time)
                print(" music-time  default menu updated")
                defaultmenu.seek(0)
                print(defaultmenu.read())
                defaultmenu.close()
        except Exception as e:
            print("Default MENU\n",e)

        name = "Music Time"
        
    return name