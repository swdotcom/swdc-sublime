import sublime_plugin, sublime

SETTINGS_FILE = 'Software.sublime_settings'
SETTINGS = sublime.load_settings(SETTINGS_FILE)

def getValue(key, defaultValue):
	SETTINGS = sublime.load_settings(SETTINGS_FILE)
	return SETTINGS.get(key, defaultValue)

def setValue(key, value):
	SETTINGS = sublime.load_settings(SETTINGS_FILE)
	return SETTINGS.set(key, value)
