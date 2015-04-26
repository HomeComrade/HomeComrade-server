from subprocess import Popen, call, STDOUT, PIPE
import os, time, threading

#local imports
import config
from playlist import Playlist, TotemPlaylist, OmxplayerPlaylist
from logger import Logger

DEVNULL = open(os.devnull, 'wb')

#Exceptions
class CommandNotSupported(Exception):
	pass

class InvalidPlayer(Exception):
	pass

#Base class
class Player:
	PLAY = 'play'
	ENQUEUE = 'enqueue'
	
	def __init__(self, serverType, command, responseHandler):
		self.serverType = serverType
		self.command = command
		self.responseHandler = responseHandler
	
	def playlistUpdated(self):
		pass
	
	def enqueueFiles(self, filePaths):
		pass
	
	@staticmethod
	def startThreads():
		if config.MEDIA_PLAYER == Omxplayer.SERVER_TYPE:
			Omxplayer.nextFileThread()
	
	def getServerType(self):
		return self.serverType
	
	@staticmethod
	def getPlayer(serverType, section, responseHandler):
		if serverType == Totem.SERVER_TYPE:
			return Totem(Totem.SERVER_TYPE, section, responseHandler)
		elif serverType == Omxplayer.SERVER_TYPE:
			return Omxplayer(Omxplayer.SERVER_TYPE, section, responseHandler)
		else:
			raise InvalidPlayer('Unknown player: '+serverType)

class Totem(Player):
	SERVER_TYPE = 'totem'
	
	CMD_PLAY = '--play'
	CMD_ENQUEUE = '--enqueue'
	CMD_PLAY_PAUSE = '--play-pause'
	CMD_NEXT = '--next'
	CMD_PREVIOUS = '--previous'
	CMD_SEEK_FORWARD = '--seek-fwd'
	CMD_SEEK_BACKWARD = '--seek-bwd'
	CMD_VOLUME_UP = '--volume-up'
	CMD_VOLUME_DOWN = '--volume-down'
	CMD_FULLSCREEN = '--fullscreen'
	CMD_TOGGLE_CONTROLS = '--toggle-controls'
	CMD_REPLACE = '--replace'
	
	def __playerCommand(self, command=None):
		if not command:
			Logger(Logger.DEBUG, 'sending command: totem')
			
			Popen(['totem'], shell=True, stdin=None, stdout=DEVNULL, stderr=STDOUT, close_fds=True)
		else:
			Logger(Logger.DEBUG, 'sending command: totem '+command)
			
			Popen(['totem '+command], shell=True, stdin=None, stdout=DEVNULL, stderr=STDOUT, close_fds=True)
	
	def getPlaylist(self):
		if not hasattr(self, 'playlist'):
			self.playlist = TotemPlaylist()
		
		return self.playlist
	
	def playPause(self):
		self.__playerCommand(Totem.CMD_PLAY_PAUSE)
	
	def next(self):
		self.__playerCommand(Totem.CMD_NEXT)
	
	def previous(self):
		self.__playerCommand(Totem.CMD_PREVIOUS)
	
	def seekForward(self):
		self.__playerCommand(Totem.CMD_SEEK_FORWARD)
	
	def seekBackward(self):
		self.__playerCommand(Totem.CMD_SEEK_BACKWARD)
	
	def skipTitleSequence(self):
		self.__playerCommand(Totem.CMD_SEEK_FORWARD)
		self.__playerCommand(Totem.CMD_SEEK_BACKWARD)
		self.__playerCommand(Totem.CMD_SEEK_BACKWARD)
	
	def volumeUp(self):
		self.__playerCommand(Totem.CMD_VOLUME_UP)
	
	def volumeDown(self):
		self.__playerCommand(Totem.CMD_VOLUME_DOWN)
	
	def fullScreen(self):
		self.__playerCommand(Totem.CMD_FULLSCREEN)
	
	def toggleControls(self):
		self.__playerCommand(Totem.CMD_TOGGLE_CONTROLS)
	
	def playPlaylist(self):
		self.__playerCommand(Totem.CMD_PLAY+' '+self.getPlaylist().getFilePath())
	
	def enqueueFiles(self, filePaths):
		for filePath in filePaths:
			self.__playerCommand(Totem.CMD_ENQUEUE+' '+Playlist.escapeFilePath(filePath, True))#was filePath.replace(' ', '\ ')
	
	def playlistUpdated(self):
		self.__playerCommand(Totem.CMD_REPLACE+' '+self.getPlaylist().getFilePath())
	
	def playAt(self, position):
		currentPlaylist = self.getPlaylist().getFilePaths()
		
		if len(currentPlaylist) < position:
			self.responseHandler.setSuccess(False)
			return
		
		#reload our playlist from the beginning
		self.playlistUpdated()
		time.sleep(1)
		
		for index in range(0, position):
			if index == position:
				break
			
			next(self)
			time.sleep(1)

class Omxplayer(Player):
	SERVER_TYPE = 'omxplayer'
	
	MANAGER_FILE = 'omxplayer-manager.sh'
	NEXT_LOCK_FILE = 'omxplayer-next-lock'
	
	CMD_PLAY_PAUSE = ' '
	CMD_SEEK_FORWARD = '^[[C'
	CMD_SEEK_BACKWARD = '^[[D'
	CMD_VOLUME_UP = '+'
	CMD_VOLUME_DOWN = '-'
	CMD_QUIT = 'q'
	
	omxplayerProcess = None
	playerStarted = False
	volumeLevel = 0
	
	@staticmethod
	def playerManager(command=None):
		filePath = os.path.dirname(os.path.realpath(__file__))+'/'+Omxplayer.MANAGER_FILE
		
		if not command:
			p = Popen([filePath], stdout=PIPE, stderr=PIPE)
		else:
			p = Popen([filePath, command], stdout=PIPE, stderr=PIPE)
		
		out, err = p.communicate()
		
		return out.strip().decode('ascii')
	
	@staticmethod
	def isLockedPlayNext():
		filePath = os.path.dirname(os.path.realpath(__file__))+'/'+Omxplayer.NEXT_LOCK_FILE
		
		lockFile = open(filePath, 'a+')#create if it doesn't exist
		lockFile.seek(0)#a+ goes to the end of the file, so seek back to the beginning for reading
		lockTime = int(lockFile.read())
		lockFile.close()
		
		if not lockTime:
			return False
		else:
			currentTime = int(time.time())
			
			if (currentTime - lockTime) > 3:#if we are over 3 seconds past, we are no longer locked
				return False
		
		return True
	
	@staticmethod
	def updateNextLock():
		filePath = os.path.dirname(os.path.realpath(__file__))+'/'+Omxplayer.NEXT_LOCK_FILE
		
		lockFile = open(filePath, 'w+')#create if it doesn't exist and truncate
		lockFile.write(str(int(time.time())))
		lockFile.close()
	
	@staticmethod
	def playerCommand(command):
		Logger(Logger.DEBUG, 'attempting command: '+command)
		
		if not Omxplayer.omxplayerProcess:
			Logger(Logger.ERROR, 'omxplayerProcess variable empty')
		elif not 'y' == Omxplayer.playerManager():
			Logger(Logger.ERROR, 'no omxplayer process running')
		else:
			Omxplayer.omxplayerProcess.stdin.write(command.encode('ascii'))
			Omxplayer.omxplayerProcess.stdin.flush()
	
	@staticmethod
	def playFile(filePath):
		Omxplayer.playerStarted = True
		Omxplayer.updateNextLock()
		
		Logger(Logger.DEBUG, 'opening file: omxplayer '+filePath)
		
		Omxplayer.playerManager('kill')
		#-b sets the background to black
		Omxplayer.omxplayerProcess = Popen(['omxplayer', '-b', filePath], shell=False, stdin=PIPE, stdout=PIPE, stderr=PIPE, close_fds=True)
		
		#we have to sleep for 2 seconds to ensure that the file has started playing
		#otherwise, the volumn commands might not work
		time.sleep(3)
		
		if Omxplayer.volumeLevel != 0:
			Logger(Logger.DEBUG, 'Volume level must be reset to previous value: '+str(Omxplayer.volumeLevel))
		
		if Omxplayer.volumeLevel < 0:
			for i in range(Omxplayer.volumeLevel, 0):
				Omxplayer.playerCommand(Omxplayer.CMD_VOLUME_DOWN)
				time.sleep(0.5)
		elif Omxplayer.volumeLevel > 0:
			for i in range(0, Omxplayer.volumeLevel):
				Omxplayer.playerCommand(Omxplayer.CMD_VOLUME_UP)
				time.sleep(0.5)
	
	def getPlaylist(self):
		if not hasattr(self, 'playlist'):
			self.playlist = OmxplayerPlaylist()
		
		return self.playlist
	
	def playPause(self):
		Omxplayer.playerCommand(Omxplayer.CMD_PLAY_PAUSE)
	
	def next(self):
		if Omxplayer.playerStarted:
			filePath = self.getPlaylist().incrementToPosition(1)
			
			if filePath:
				Omxplayer.playFile(filePath)
	
	def previous(self):
		if Omxplayer.playerStarted:
			filePath = self.getPlaylist().incrementToPosition(-1)
			
			if filePath:
				Omxplayer.playFile(filePath)
	
	def seekForward(self):
		Omxplayer.playerCommand(Omxplayer.CMD_SEEK_FORWARD)
	
	def seekBackward(self):
		Omxplayer.playerCommand(Omxplayer.CMD_SEEK_BACKWARD)
	
	def volumeUp(self):
		Omxplayer.volumeLevel += 1
		Omxplayer.playerCommand(Omxplayer.CMD_VOLUME_UP)
	
	def volumeDown(self):
		Omxplayer.volumeLevel -= 1
		Omxplayer.playerCommand(Omxplayer.CMD_VOLUME_DOWN)
	
	def playPlaylist(self):
		self.playAt(0)
	
	def playAt(self, position):
		currentPlaylist = self.getPlaylist().getFilePaths()
		
		if len(currentPlaylist) < position:
			self.responseHandler.setSuccess(False)
			return
		
		filePath = self.getPlaylist().getFilePathAtPosition(position)
		
		if not filePath:
			self.responseHandler.setSuccess(False)
			return
		
		Omxplayer.playerStarted = True
		self.getPlaylist().setPosition(position)
		Omxplayer.playFile(filePath)
	
	def quit(self):
		Omxplayer.playerStarted = False
		Omxplayer.playerCommand(Omxplayer.CMD_QUIT)
	
	@staticmethod
	def nextFileThread():
		#restart this thread after 3 seconds
		#set as daemon so it will die when the main script dies
		try:
			thread = threading.Timer(3.0, Omxplayer.nextFileThread)
			thread.daemon = True
			thread.start()
		except KeyboardInterrupt:
			sys.exit(0)
		
		if Omxplayer.isLockedPlayNext():
			Logger(Logger.DEBUG, "Player 'next' is locked")
			return
		
		#if a connection hasn't started playing anything yet, just return
		if not Omxplayer.playerStarted:
			Logger(Logger.DEBUG, "Player has not been started yet")
			return
		
		#if it is running, do nothing
		if 'y' == Omxplayer.playerManager():
			return
		
		#if we have a next file, go for it
		filePath = OmxplayerPlaylist().incrementToPosition(1)
		
		if filePath:
			Logger(Logger.DEBUG, 'Next file found, playing.')
			
			Omxplayer.playFile(filePath)
