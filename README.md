HomeComrade-server -- Server for the HomeComrade suite
====================================================

The HomeComrade server allows you to use your computer as a media server with some extra features not available in other media server options.
HomeComrade stores your show paths in a database and gives you the ability to play random episodes of shows of your choice. The server works on
systems with either Totem (Gnome media player) or Omxplayer (Raspberry Pi media player). The server can be controlled from a website (https://github.com/HomeComrade/HomeComrade-website)
or from an Android app (https://github.com/HomeComrade/HomeComrade-android).

HomeComrade should not be started from rc.local if you use any unicode path names. On Gnome systems, it should be started as part of the Startup Applications.
On Raspberry Pi, it should be started from the command line when you log in.

## DOWNLOADING
	
	git clone https://github.com/HomeComrade/HomeComrade-server.git

## SYNOPSIS

Usage

	./homecomrade.py

## CONFIGURATION

Copy config.py.dist to config.py

	DEBUG				boolean, enable debug output
	DEBUG_LEVEL			int, 0 - 3, higher number = less debug output
	SERVER_PORT 		int, defaults to 8053
	MEDIA_PLAYER		string, 'omxplayer' or 'totem'
	CONNECTION_TYPE 	sttring, 'ssh' or 'localhost'. The localhost server controls the database while all other ssh servers will connect to the localhost server.
	CONNECTION_SERVER	ignored if connection type is localhost, otherwise should point to the domain / IP of the localhost server
	CONNECTION_USERNAME	Username to ssh into the localhost server, ignored if connection type is localhost
	CONNECTION_PASSWORD	Password to ssh into the localhost server, ignored if connection type is localhost
	USES_IR_REMOTE		boolean, True if the program "irsend" is configured on the same machine
	IR_REMOTE_NAME		only used if USES_IR_REMOTE is True. Must be the name of the remote in your "irsend" config
	showDirectories		list, a list of folder paths where shows are stored. The shows in these folders will be placed in the database for the random feature.

## RANDOM FEATURE

To enable the random settings, the folders listed in the configuration variable "showDirectories" must be in the proper format. This format is:

	Shows/
		Show Name -> ex "The Simpsons"
			Season Number -> ex Season 01
				Episode list...
