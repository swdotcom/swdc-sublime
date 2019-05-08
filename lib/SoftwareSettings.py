
import sublime_plugin, sublime

def getValue(key, defaultValue):
	SETTINGS = sublime.load_settings("Software.sublime_settings")
	# log("Got value!")
	return SETTINGS.get(key, defaultValue)

def setValue(key, value):
	SETTINGS = sublime.load_settings("Software.sublime_settings")
	# log("Set value!")
	return SETTINGS.set(key, value)
