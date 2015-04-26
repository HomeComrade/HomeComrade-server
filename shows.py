import os, sqlite3, random, time, copy
from itertools import cycle

#local imports
import config
from database import Database
from logger import Logger

class Shows:
	def __init__(self, baseDirectory):
		self.baseDirectory = None
		self.baseDirectory = self.__combineDirs(baseDirectory)
	
	def __combineDirs(self, newDirectory, baseDirectory=None):
		if not baseDirectory:
			baseDirectory = self.baseDirectory
		
		#self.baseDirectory might also be None
		if not baseDirectory:
			baseDirectory = ''
		
		if not newDirectory:
			newDirectory = ''
		
		directory = '/'+baseDirectory+'/'+newDirectory
		
		directory = directory.replace('//', '/')
		
		return directory
	
	def isPlayableFile(self, filePath, combineDirs=True):
		if combineDirs:
			combinedFilePath = self.__combineDirs(filePath)
		else:
			combinedFilePath = filePath
		
		if not os.path.isfile(combinedFilePath):
			return False
		
		fileName, fileExtension = os.path.splitext(filePath)
		
		fileExtension = fileExtension.lower()
		
		if fileExtension in config.VALID_PLAYABLE_FILE_EXTENSIONS:
			return True
		
		return False
	
	def getDirContents(self, dirToBrowse):
		dirContents = []
		
		dirToBrowse = self.__combineDirs(dirToBrowse)
		
		if not os.path.isdir(dirToBrowse):
			return dirContents
		
		dirList = os.listdir(dirToBrowse)
		
		for entry in dirList:
			if '.' == entry[0]:
				continue
			
			fullPath = self.__combineDirs(entry, dirToBrowse)
			
			if os.path.isdir(fullPath):
				fileType = 'dir'
				isPlayable = False
			else:
				fileType = 'file'
				isPlayable = self.isPlayableFile(fullPath, False)
			
			dirContents.append({'name' : entry, 'type' : fileType, 'isPlayable' : isPlayable})
		
		return sorted(dirContents, key=lambda k: k['name']);
	
	def getShowCategories(self):
		categories = copy.deepcopy(config.BLANK_SHOW_CATEGORIES)
		
		for directory in config.showDirectories:
			dirList = os.listdir(self.__combineDirs(directory))
			
			for entry in dirList:
				if '.' == entry[0]:
					continue
				
				if False != config.knownShowCategories.get(entry, False):
					categories[config.knownShowCategories[entry]].append(entry)
				else:
					categories['Other'].append(entry)
		
		return categories;
	
	def getAllShows(self):
		allShows = []
		
		for directory in config.showDirectories:
			dirList = os.listdir(self.__combineDirs(directory))
			
			for entry in dirList:
				if '.' == entry[0]:
					continue
				
				allShows.append(entry)
		
		return allShows
	
	def getRandomShows(self, playlistSize, allowedShows):
		#if no show filters were given, just get random shows out
		if not type(allowedShows) is list or len(allowedShows) < 1:
			allowedShows = []
			
			missingShowsCount = str(playlistSize - len(allowedShows))
			
			sql = """
				SELECT
					DISTINCT `show`
				FROM
					shows
				ORDER BY RANDOM()
				LIMIT ?
			"""
			
			rows = Database.getRows(sql, (missingShowsCount,))
			
			for row in rows:
				allowedShows.append(row[0])
		#if we have less shows than our playlist size, enlarge our allowed shows list with duplicate shows
		elif len(allowedShows) < playlistSize:
			allowedShowsCycle = cycle(allowedShows)
			
			for x in range(len(allowedShows), playlistSize):
				allowedShows.append(next(allowedShowsCycle))
		#if we have more shows then our playlist size, get the number of shows as the playlist size
		elif len(allowedShows) > playlistSize:
			allowedShows = random.sample(allowedShows, playlistSize)
		
		filePaths = []
		usingShowids = []#store show ids already picked so we don't have repeats
		
		for allowedShow in allowedShows:
			#compile the where list so we don't get duplicate shows
			if len(usingShowids) == 0:
				where = '1'
			else:
				whereList = []
				
				for showid in usingShowids:
					whereList.append('showid != '+str(showid))
				
				where = ' AND '.join(whereList)
			
			sql = """
				SELECT
					`showid`,
					`path`
				FROM
					`shows`
				WHERE
					`show` = ?
				AND
					%(where)s
				ORDER BY
					lastPlayTime ASC
				LIMIT 5
			""" % {'where' : where}
			
			rows = Database.getRows(sql, (allowedShow,))
			tmpShows = {}
			
			for tmpShow in rows:
				tmpShows[tmpShow[0]] = tmpShow[1]
			
			if len(tmpShows) > 0:
				randomShowid = random.choice(list(tmpShows.keys()))
				usingShowids.append(randomShowid)
				
				filePaths.append(tmpShows[randomShowid])
		
		for filePath in filePaths:
			self.updateLastPlayedTime(filePath)
		
		if 0 == len(filePaths):
			Logger(Logger.DEBUG, 'No shows were found for the supplied random settings')
			return False
		
		return filePaths

	def updateLastPlayedTime(self, filePath):
		sql = """
			UPDATE
				shows
			SET
				plays = plays + 1,
				lastPlayTime = ?
			WHERE
				path = ?
		"""
				
		Database.execute(sql, (str(time.time()), filePath))
