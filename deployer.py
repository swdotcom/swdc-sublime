import sys
import json

# python deployer.py music-time

# High level steps:
# 1. update the plugin name in Software.sublime-settings
# 2. update the Main.sublime-menu file
# 3. udpate the Default.sublime-commands file

# First argument: plugin to be deployed
try:
    plugin_name = sys.argv[1]

    # update the plugin name in the sublime settings file
    sublime_settings = open("Software.sublime_settings")
    string = sublime_settings.read()
    json_data = json.loads(string)

    for key, value in json_data.items():
        if key == "plugin":
            del json_data["plugin"]
            json_data["plugin"] = plugin_name

    # print json_data.items()

    # overwrite the sublime settings file with the new plugin
    with open("Software.sublime_settings", "w") as outfile:
        json.dump(json_data, outfile, indent=4)

    if plugin_name == "code-time":
        display_name = "Code Time"
    else:
        display_name = "Music Time"

    # this will store the array that gets written into Main.sublime_menu
    main_menu = []

    main_obj = {"id": "tools", "children": []}
    author_obj = {"caption": "-", "id": "software"}
    main_obj["children"].append(author_obj)
    plugin_obj = {"caption": display_name, "children": []}
    main_obj["children"].append(plugin_obj)


    # music time only commands
    music_time_cmds = []
    music_time_cmds.append({ "command": "launch_music_time_metrics", "caption": "Music Time Dashboard" })
    music_time_cmds.append({ "command": "software_top_forty", "caption": "Software Top 40" })
    music_time_cmds.append({ "command": "connect_spotify", "caption": "Log in to Spotify" })

    # code time only commands
    code_time_cmds = []
    code_time_cmds.append({ "command": "launch_code_time_metrics", "caption": "Code Time Dashboard" })
    code_time_cmds.append({ "command": "launch_custom_dashboard", "caption": "Generate a Custom Dashboard" })
    code_time_cmds.append({ "command": "go_to_software", "caption": "Web Dashboard" })
    code_time_cmds.append({ "command": "code_time_login", "caption": "Log in to see your coding data in Code Time" })
    code_time_cmds.append({ "command": "pause_kpm_updates", "caption": "Pause Code Time" })
    code_time_cmds.append({ "command": "enable_kpm_updates", "caption": "Enable Code Time" })

    # shared commands for code time and music time
    shared_cmds = []
    shared_cmds.append({ "command": "toggle_status_bar_metrics", "caption": "Show/Hide Status Bar Metrics" })
    shared_cmds.append({ "command": "hide_console_message", "caption": "Hide Console Message" })
    shared_cmds.append({ "command": "show_console_message", "caption": "Show Console Message" })

    # add the appropriate commands 
    if plugin_name == "code-time":
        cmds = code_time_cmds + shared_cmds
        main_obj['children'][1]["children"]=cmds
        # plugin_obj["children"].append(cmds)
    else:
        cmds = music_time_cmds + shared_cmds
        main_obj['children'][1]["children"]=cmds
        # plugin_obj["children"].append(music_time_cmds)

    # main_obj["children"].append(plugin_obj)

    main_menu.append(main_obj)

    # write the main menu array to the menu file
    with open("Main.sublime-menu", "w") as main_menu_file:
        json.dump(main_menu, main_menu_file, indent=4)

    # write the commands array to the default commands file
    with open("Default.sublime-commands", "w") as default_cmds_file:
        json.dump(cmds, default_cmds_file, indent=4)
except Exception as E:
    pass
