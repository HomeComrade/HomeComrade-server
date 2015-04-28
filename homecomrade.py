#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, HTTPServer
from socket import error as SocketError

import cgi
from subprocess import call

#prevent .pyc files from being generated
import sys, json, os, time, urllib.parse, urllib.request
sys.dont_write_bytecode = True

#local imports
try:
	import config
except ImportError:
	print('Config module was not found. You can copy the config.py.dist to config.py to fix this error. Please make sure you setup your server in the config file before starting HomeComrade. Exiting.')
	sys.exit()

from database import Database, DatabaseError, SyncDatabase
from player import Player, CommandNotSupported, InvalidPlayer
from logger import Logger
from irremote import IRRemote
from lights import Lights
from shows import Shows

if config.IS_BLUETOOTH_SERVER:
	from bluetoothserver import BluetoothServer

class HomeComradeServer(BaseHTTPRequestHandler):
	def do_GET(self):
		self.getRequestResponse({})
	def do_POST(self):
		postVars = {}
		
		form = cgi.FieldStorage(
			fp = self.rfile,
			headers = self.headers,
			environ = {'REQUEST_METHOD': 'POST'}
		)
		
		for item in form.list:
			postVars[item.name] = item.value
		
		self.getRequestResponse(postVars)
	
	def getRequestResponse(self, postVars):
		Logger(Logger.DEBUG, 'received: '+str(postVars))
		
		try:
			self.__reply(RequestHandler(self.path, postVars).getRequestResponse())
		except InvalidPlayer:
			self.__reply({'success' : False, 'errors' : ['Request path was not understood.']})
		except InvalidRequest:
			self.__reply({'success' : False, 'errors' : ['The request path was not understood.']})
		except CommandNotSupported:
			self.__reply({'success' : False, 'errors' : ['Supplied command is not suported on this server.']})
		#except AttributeError:
		#	self.__reply({'success' : False, 'errors' : ['The supplied command is not suported on this server.']})
	
	def __reply(self, response):
		response = bytes(json.dumps(response), 'utf-8')
		
		try:
			self.send_response(200)
			self.send_header('Content-type', 'application/json')
			self.send_header("Content-Length", str(len(response)))
			self.end_headers()
			
			self.wfile.write(response)
		except SocketError:
			Logger(Logger.DEBUG, 'HTTP socket error');
	
	def log_message(self, format, *args):
		Logger(Logger.VERBOSE, 'HTTP server response: '+' '.join(args))

#Exceptions
class InvalidRequest(Exception):
	pass

class RequestHandler:
	HEARTBEAT = 'heartbeat'
	PLAY_PAUSE = 'play-pause'
	NEXT = 'next'
	PREVIOUS = 'previous'
	SEEK_FORWARD = 'seek-fwd'
	SEEK_BACKWARD = 'seek-bwd'
	SKIP_TITLE_SEQUENCE = 'skip-title-sequence'
	VOLUME_UP = 'volume-up'
	VOLUME_DOWN = 'volume-down'
	FULLSCREEN = 'fullscreen'
	TOGGLE_CONTROLS = 'toggle-controls'
	RANDOM_SETTINGS = 'random-settings'
	ALL_SHOWS = 'all-shows'
	LAST_PLAYLIST = 'last-playlist'
	CURRENT_PLAYLIST = 'current-playlist'
	CURRENT_PLAYLIST_SELECTION = 'current-playlist-selection'
	RANDOM = 'random'
	FOREIGN_RANDOM = 'foreign-random'
	BROWSE = 'browse'
	PLAY = 'play'
	ENQUEUE = 'enqueue'
	INSERT_AT = 'insert-at'
	FOREIGN_UPDATE_PLAY_TIME = 'foreign-update-play-time'
	PLAY_AT = 'play-at'
	QUIT = 'quit'
	
	HARDWARE_BUTTON_PRESS = 'hardware-button-press'
	HARDWARE_BUTTON_PRESS_AND_HOLD = 'hardware-button-press-and-hold'
	LIGHTS_RGB = 'lights-rgb'
	
	TV_VOLUME_UP = 'volume-up-tv'
	TV_VOLUME_DOWN = 'volume-down-tv'
	TV_MUTE = 'mute-tv'
	TV_POWER = 'power-tv'
	TV_SOURCE = 'source-tv'
	
	def __init__(self, path, postVars):
		self.mountPoint = None#default to none
		
		""" We must first make sure that any SSH mount points needed exist, otherwise our player wont be able to find our files """
		if 'ssh' == config.CONNECTION_TYPE:
			mountPoint = '/run/user/'+str(os.getuid())+'/gvfs/sftp:host='+config.CONNECTION_SERVER+',user='+config.CONNECTION_USERNAME
			
			if not os.path.isdir(mountPoint):
				Logger(Logger.INFO, 'sftp mount point not mounted, attempting to mount.')
				
				command = 'gvfs-mount sftp://'+config.CONNECTION_USERNAME+'@'+config.CONNECTION_SERVER
				
				call([command], shell=True, stdin=None, stdout=None, stderr=None, close_fds=True)
				
				Logger(Logger.INFO, 'sftp mount mounted or mounting')
				
				sleepAttempts = 0
				maxSleepAttempts = 10
				while not os.path.isdir(mountPoint):
					Logger(Logger.INFO, 'sleep attempt until mount finished: '+str(sleepAttempts + 1))
					
					time.sleep(1)
					sleepAttempts += 1
					
					if maxSleepAttempts <= sleepAttempts:
						break;
			
			self.mountPoint = mountPoint
		
		self.success = True#default to true
		self.data = None
		self.command = path.replace('/', '')
		self.postVars = postVars
		self.player = Player.getPlayer(config.MEDIA_PLAYER, self.command, self)
	
	def setSuccess(self, success):
		self.success = success
	
	def setData(self, data):
		self.data = data
	
	def getRequestResponse(self):
		if self.command == RequestHandler.HEARTBEAT:
			self.setData({'serverType' : self.player.getServerType(), 'irRemote' : config.USES_IR_REMOTE})
		elif self.command == RequestHandler.PLAY_PAUSE:
			self.player.playPause()
		elif self.command == RequestHandler.NEXT:
			self.player.next()
		elif self.command == RequestHandler.PREVIOUS:
			self.player.previous()
		elif self.command == RequestHandler.SEEK_FORWARD:
			self.player.seekForward()
		elif self.command == RequestHandler.SEEK_BACKWARD:
			self.player.seekBackward()
		elif self.command == RequestHandler.SKIP_TITLE_SEQUENCE:
			self.player.skipTitleSequence()
		elif self.command == RequestHandler.VOLUME_UP:
			self.player.volumeUp()
		elif self.command == RequestHandler.VOLUME_DOWN:
			self.player.volumeDown()
		elif self.command == RequestHandler.FULLSCREEN:
			self.player.fullScreen()
		elif self.command == RequestHandler.TOGGLE_CONTROLS:
			self.player.toggleControls()
		elif self.command == RequestHandler.RANDOM_SETTINGS:
			self.setData(Shows(self.mountPoint).getShowCategories())
		elif self.command == RequestHandler.ALL_SHOWS:
			self.setData(Shows(self.mountPoint).getAllShows())
		elif self.command == RequestHandler.LAST_PLAYLIST:
			playlist = self.player.getPlaylist()
			
			playlistExists = playlist.playlistExists()
			
			if playlistExists:
				self.player.playPlaylist()
			
			self.setSuccess(playlistExists)
			self.setData(playlist.getFormattedShows())
		elif self.command == RequestHandler.CURRENT_PLAYLIST or self.command == RequestHandler.CURRENT_PLAYLIST_SELECTION:
			playlist = self.player.getPlaylist()
			self.setSuccess(playlist.playlistExists())
			self.setData(playlist.getFormattedShows())
		elif self.command == RequestHandler.RANDOM:
			filePaths = self.getRandom()
			
			if self.success and filePaths:
				self.playRandom(filePaths)
		elif self.command == RequestHandler.FOREIGN_RANDOM:
			if 'localhost' == config.CONNECTION_TYPE:
				filePaths = self.getRandom()
				
				if self.success and filePaths:
					self.setData(filePaths)
			else:
				self.setSuccess(False)
		elif self.command == RequestHandler.BROWSE:
			self.browse()
		elif self.command == RequestHandler.PLAY:
			self.play(Player.PLAY)
		elif self.command == RequestHandler.ENQUEUE:
			self.play(Player.ENQUEUE)
		elif self.command == RequestHandler.INSERT_AT:
			self.insertAt()
		elif self.command == RequestHandler.PLAY_AT:
			self.playAt()
		elif self.command == RequestHandler.FOREIGN_UPDATE_PLAY_TIME:
			if 'localhost' == config.CONNECTION_TYPE:
				self.__checkAndUpdateFilePaths()
			else:
				self.setSuccess(False)
		elif self.command == RequestHandler.QUIT:
			self.player.quit()
		
		#TV commands, handled seperatly
		elif self.command == RequestHandler.TV_VOLUME_UP:
			if not config.USES_IR_REMOTE:
				raise CommandNotSupported('No support for IR commands on this server')
			
			IRRemote.sendCommand(IRRemote.VOLUME_UP)
		elif self.command == RequestHandler.TV_VOLUME_DOWN:
			if not config.USES_IR_REMOTE:
				raise CommandNotSupported('No support for IR commands on this server')
			
			IRRemote.sendCommand(IRRemote.VOLUME_DOWN)
		elif self.command == RequestHandler.TV_MUTE:
			if not config.USES_IR_REMOTE:
				raise CommandNotSupported('No support for IR commands on this server')
			
			IRRemote.sendCommand(IRRemote.MUTE)
		elif self.command == RequestHandler.TV_POWER:
			if not config.USES_IR_REMOTE:
				raise CommandNotSupported('No support for IR commands on this server')
			
			IRRemote.sendCommand(IRRemote.POWER)
		elif self.command == RequestHandler.TV_SOURCE:
			if not config.USES_IR_REMOTE:
				raise CommandNotSupported('No support for IR commands on this server')
			
			IRRemote.sendCommand(IRRemote.SOURCE)
		
		#BT commads, handled seperatly
		elif self.command == RequestHandler.HARDWARE_BUTTON_PRESS:
			if not config.IS_BLUETOOTH_SERVER:
				raise CommandNotSupported('Cannot send Bluetooth commands on a non Bluetooth server')
			
			BluetoothServer.QUEUE.put(BluetoothServer.HARDWARE_BUTTON_PRESS)
		elif self.command == RequestHandler.HARDWARE_BUTTON_PRESS_AND_HOLD:
			if not config.IS_BLUETOOTH_SERVER:
				raise CommandNotSupported('Cannot send Bluetooth commands on a non Bluetooth server')
			
			BluetoothServer.QUEUE.put(BluetoothServer.HARDWARE_BUTTON_PRESS_AND_HOLD)
		elif self.command == RequestHandler.LIGHTS_RGB:
			if not config.IS_BLUETOOTH_SERVER:
				raise CommandNotSupported('Cannot send Bluetooth commands on a non Bluetooth server')
			
			lights = Lights(self.postVars.get('red', 0), self.postVars.get('green', 0), self.postVars.get('blue', 0))
			command = lights.buildString()
			
			if not command:
				raise CommandNotSupported('All colors must be between 255 and 0')
						
			queueCommand = BluetoothServer.LIGHTS_RGB+command
			BluetoothServer.QUEUE.put(queueCommand)
			
		#If we have made it this far, we don't know how to handle this command as we should just raise our exception
		else:
			raise InvalidRequest('Unknown request command')
		
		return self.respond()
	
	def respond(self):
		response = {
			'success' : self.success,
			'type' : self.command,
		}
		
		if self.data:
			response['data'] = self.data
		
		Logger(Logger.DEBUG, 'response: '+str(response))
		
		return response
	
	def getRandom(self):
		playlistSize = self.postVars.get('playlistSize', 5)
		allowedShows = self.__postStrToList('allowedShows')
		
		if type(playlistSize) is list:
			playlistSize = int(playlistSize[0])
		else:
			playlistSize = int(playlistSize)
		
		if playlistSize > config.MAX_RANDOM_PLAYLIST_SIZE:
			playlistSize = config.MAX_RANDOM_PLAYLIST_SIZE
		
		filePaths = []
		
		if config.CONNECTION_TYPE == 'localhost':
			filePaths = Shows(self.mountPoint).getRandomShows(playlistSize, allowedShows)
			
			if not filePaths:
				self.setSuccess(False)
				return
		else:
			values = {'playlistSize' : playlistSize, 'allowedShows' : json.dumps(allowedShows)}
			response = self.__loadForeignUrl(values, RequestHandler.FOREIGN_RANDOM)
			
			success = response.get('success', False)
			filePaths = response.get('data', None)
			
			self.setSuccess(success)
			
			if not filePaths:
				self.setSuccess(False)
				return
		
		return filePaths
	
	def playRandom(self, filePaths):
		playMethod = self.postVars.get('playMethod', Player.PLAY)
		
		if type(playMethod) is list:
			playMethod = playMethod[0]
		
		if not playMethod == Player.PLAY and not playMethod == Player.ENQUEUE:
			playMethod = Player.PLAY
		
		playlist = self.player.getPlaylist()
		
		if playMethod == Player.PLAY:
			playlist.save(filePaths)
			self.player.playPlaylist()
		elif playMethod == Player.ENQUEUE:
			playlist.append(filePaths)
			self.player.enqueueFiles(filePaths)
		else:
			self.setSuccess(False)
		
		self.setData(playlist.getFormattedShows())
	
	def browse(self):
		dirToBrowse = self.postVars.get('dir', '/media')
		
		if type(dirToBrowse) is list:
			dirToBrowse = dirToBrowse[0]
		
		if not dirToBrowse:
			dirToBrowse = '/media'
		
		dirList = Shows(self.mountPoint).getDirContents(dirToBrowse)
		
		self.setData({'dirList' : dirList, 'dir' : dirToBrowse})
	
	def play(self, playMethod):
		filePaths = self.__checkAndUpdateFilePaths()
		
		if not self.success:
			return
		
		playlist = self.player.getPlaylist()
		
		if playMethod == Player.PLAY:
			playlist.save(filePaths)
			self.player.playPlaylist()
		elif playMethod == Player.ENQUEUE:
			playlist.append(filePaths)
			self.player.enqueueFiles(filePaths)
		else:
			self.setSuccess(False)
	
	def insertAt(self):
		filePaths = self.__checkAndUpdateFilePaths()
		
		if not self.success:
			return
		
		position = self.postVars.get('position')
		
		if type(position) is list:
			position = position[0]
		
		if not position.isdigit():
			self.setSuccess(False)
			return
		
		self.player.getPlaylist().addFilesAtPosition(filePaths, int(position))
		self.player.playlistUpdated()
	
	def playAt(self):
		position = self.postVars.get('position')
		
		if type(position) is list:
			position = position[0]
		
		if not position.isdigit():
			self.setSuccess(False)
			return
		
		self.player.playAt(int(position))
	
	def __postStrToList(self, var):
		returned = self.postVars.get(var)
		
		if type(returned) is list:
			returned = returned[0]
		
		try:
			returned = json.loads(returned)
		except TypeError:
			return None
		except ValueError:
			return None
		
		if type(returned) is not list:
			return None
		
		return returned
	
	def __checkAndUpdateFilePaths(self):
		filePaths = self.__postStrToList('filePaths')
		
		if not filePaths:
			self.setSuccess(False)
			return
		
		shows = Shows(self.mountPoint)
		
		for filePath in filePaths:
			if not shows.isPlayableFile(filePath):
				self.setSuccess(False)
				return#break out completly, no need to check others
		
		if 'localhost' == config.CONNECTION_TYPE:
			for filePath in filePaths:
				shows.updateLastPlayedTime(filePath)
		else:
			values = {'filePaths' : json.dumps(filePaths)}
			response = self.__loadForeignUrl(values, RequestHandler.FOREIGN_UPDATE_PLAY_TIME)
			
			self.setSuccess(response.get('success', False))
		
		return filePaths
	
	def __loadForeignUrl(self, values, command):
		url = 'http://'+config.CONNECTION_SERVER+':'+str(config.SERVER_PORT)+'/'+command+'/'
		encodedValues = urllib.parse.urlencode(values)
		
		request = urllib.request.Request(url, encodedValues.encode('utf-8'))
		return json.loads(urllib.request.urlopen(request).read().decode('utf-8'))

if __name__ == '__main__':
	if config.CONNECTION_TYPE == 'localhost':
		try:
			Database.setup()
		except DatabaseError as e:
			Logger(Logger.ERROR, e)
			print('The database could not be loaded. Please make sure your database file exists and restart HomeComrade. Exiting...')
			sys.exit()
		
		syncDatabase = SyncDatabase()
		syncDatabase.setDaemon(True)
		syncDatabase.start()
	
	server = HTTPServer(('', config.SERVER_PORT), HomeComradeServer)
	Logger(Logger.INFO, 'Started httpserver on port: '+str(config.SERVER_PORT))
	
	Player.startThreads()
	
	if config.IS_BLUETOOTH_SERVER:
		BluetoothServer.startThreads()
	
	try:
		server.serve_forever()
	except KeyboardInterrupt:
		Logger(Logger.INFO, '^C received')
	
	Logger(Logger.INFO, 'shutting down the web server')
	
	if config.CONNECTION_TYPE == 'localhost':
		Database.close()
	
	server.server_close()
