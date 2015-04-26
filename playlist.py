import os, urllib.request, urllib.parse, urllib.error

#local imports
import config
from logger import Logger

PLAYLIST_FOLDER = 'playlists'

class Playlist:
	def playlistExists(self):
		return os.path.exists(self.path)
	
	def getFilePath(self):
		return self.path
	
	def getFormattedShows(self):
		formattedShows = []
		
		for filePath in self.getFilePaths():
			pathParts = filePath.split('/')
			
			episode = pathParts[-1]
			show = 'Season'
			i = -2
			
			while 'Season' in show:
				show = pathParts[i]
				i -= 1
			
			formattedShows.append(show+' - '+episode)
		
		return formattedShows
	
	def getFilePaths(self):
		shows = []
		
		if self.playlistExists():
			playlistContents = open(self.path, 'r')
			
			for line in playlistContents:
				line = line.strip()
				
				if line[:4] == 'File':
					lineParts = line.split('=')
					
					filePath = urllib.parse.unquote(lineParts[1].replace(Playlist.escapeFilePath(''), ''))
					shows.append(filePath)
			
			playlistContents.close()
		
		return shows
	
	def getFilePathAtPosition(self, position):
		for key, val in enumerate(self.getFilePaths()):
			if key == position:
				return val
		
		return None
	
	def addFilesAtPosition(self, newFilePaths, position):
		playlistFiles = self.getFilePaths()
		newPlaylistFiles = [];
		
		for index, playlistFile in enumerate(playlistFiles):
			if index == position:
				for newFilePath in newFilePaths:
					newPlaylistFiles.append(newFilePath)
			
			newPlaylistFiles.append(playlistFile)
		
		if position >= len(playlistFiles):
			for newFilePath in newFilePaths:
				newPlaylistFiles.append(newFilePath)
		
		self.save(newPlaylistFiles)
	
	def save(self, filePaths):
		playlistContents = '[playlist]\n'
		playlistContents += 'NumberOfEntries='+str(len(filePaths))+'\n'
		
		for i in range(len(filePaths)):
			playlistContents += 'File'+str((i + 1))+'='+Playlist.escapeFilePath(filePaths[i])+'\n'
		
		fileHandler = open(self.path, 'w')
		fileHandler.write(playlistContents)
		fileHandler.close()
	
	def append(self, newFilePaths):
		filePaths = self.getFilePaths()
		
		for newFilePath in newFilePaths:
			filePaths.append(newFilePath)
		
		self.save(filePaths)
	
	@staticmethod
	def escapeFilePath(filePath, replaceSpaces=False):
		if 'ssh' == config.CONNECTION_TYPE:
			filePath = 'sftp://'+config.CONNECTION_USERNAME+'@'+config.CONNECTION_SERVER+urllib.parse.quote(filePath)
		elif replaceSpaces:
			filePath = filePath.replace(' ', '\ ')
		
		return filePath

class TotemPlaylist(Playlist):
	FILE_NAME = 'totem.pls'
	
	def __init__(self):
		self.path = os.path.dirname(os.path.realpath(__file__))+'/'+PLAYLIST_FOLDER+'/'+TotemPlaylist.FILE_NAME

class OmxplayerPlaylist(Playlist):
	FILE_NAME = 'omxplayer.pls'
	
	currentPosition = 0
	
	def __init__(self):
		self.path = os.path.dirname(os.path.realpath(__file__))+'/'+PLAYLIST_FOLDER+'/'+OmxplayerPlaylist.FILE_NAME
	
	def setPosition(self, position):
		OmxplayerPlaylist.currentPosition = position
		
		Logger(Logger.DEBUG, 'Set playlist position: '+str(OmxplayerPlaylist.currentPosition))
	
	def incrementToPosition(self, moveToPosition):
		#if we dont have a playlist, set position to 0 and run away
		if not self.playlistExists():
			OmxplayerPlaylist.currentPosition = 0
			return None
		
		OmxplayerPlaylist.currentPosition += moveToPosition
		
		if OmxplayerPlaylist.currentPosition < 0:
			#put position on first file and return none since its not a valid situation
			OmxplayerPlaylist.currentPosition = 0
			
			return None
		
		playlistFiles = self.getFilePaths()
		totalPlaylistFiles = len(playlistFiles)
		
		if (OmxplayerPlaylist.currentPosition + 1) > totalPlaylistFiles:
			#put position on last file and return none since its not a valid situation
			OmxplayerPlaylist.currentPosition = (totalPlaylistFiles - 1)
		
			return None
		
		Logger(Logger.DEBUG, 'Incremented playlist position to: '+str(OmxplayerPlaylist.currentPosition))
		
		return self.getFilePathAtPosition(OmxplayerPlaylist.currentPosition)
