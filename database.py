import os, sqlite3, shutil, time
from threading import Thread

#local imports
import config
from logger import Logger

#Exceptions
class DatabaseError(Exception):
	pass

class Database:
	CONNECTION = None
	
	@staticmethod
	def setup():
		cwd = os.path.dirname(os.path.realpath(__file__))+'/'
		
		databasePath = cwd+config.SQLITE_DATABASE_NAME
		
		if not os.path.exists(databasePath):
			if os.path.isfile(cwd+config.SQLITE_DATABASE_NAME+'.dist'):
				shutil.copy(cwd+config.SQLITE_DATABASE_NAME+'.dist', cwd+config.SQLITE_DATABASE_NAME)
			else:
				raise DatabaseError('Could not find the database file');
		
		if os.path.exists(databasePath+'-journal'):
			raise DatabaseError('The database was not closed properly. Remove the journal file and restart.');
		
		Database.CONNECTION = sqlite3.connect(databasePath, check_same_thread=False,isolation_level=None)
	
	@staticmethod
	def close():
		Database.CONNECTION.close()
	
	@staticmethod
	def execute(sql, params = None):
		try:
			cursor = Database.CONNECTION.cursor()
			
			if not params:
				cursor.execute(sql)
			else:
				cursor.execute(sql, params)
		
			return cursor
		except sqlite3.Error as e:
			Logger(Logger.ERROR, 'Sqlite error: '+e.args[0])
			
			return None
	
	@staticmethod
	def getRows(sql, params = None):
		cursor = Database.execute(sql, params)
		
		if not cursor:
			return []
		
		return cursor.fetchall()

class SyncDatabase(Thread):
	def __init__(self):
		super(SyncDatabase, self).__init__()
	
	def run(self):
		while True:
			Logger(Logger.VERBOSE, 'sync database start')
			
			for showDir in config.showDirectories:
				dirList = os.listdir(showDir)
				
				for showTitle in dirList:
					if '.' == showTitle[0]:
						continue
					
					Logger(Logger.VERBOSE, 'checking show: '+showTitle)
					
					self.searchAndAddEpisodes(showTitle, os.path.join(showDir, showTitle))
			
			Logger(Logger.VERBOSE, 'checking for old shows')
			
			sql = """
				SELECT
					*
				FROM
					shows
			"""
			
			rows = Database.getRows(sql)
			
			for row in rows:
				path = row[2]
				
				if not os.path.exists(path):
					sql = """
						DELETE FROM
							shows
						WHERE
							showid = ?
					"""
					
					Logger(Logger.VERBOSE, 'removing show from database: '+path)
					
					Database.execute(sql, (row[0],))
			
			Logger(Logger.VERBOSE, 'Database sync complete, sleeping for 1 hour.')
			time.sleep(3600)#sleep for 1 hour in between checks, no need to go crazy
	
	def searchAndAddEpisodes(self, show, directory):
		dirList = os.listdir(directory)
		
		for entry in dirList:
			if '.' == entry[0]:
				continue
			
			fullPath = os.path.join(directory, entry)
			
			if not os.path.isdir(fullPath):
				fileName, fileExtension = os.path.splitext(fullPath)
				
				if fileExtension.lower() in config.VALID_MEDIA_FILE_EXTENSIONS:
					sql = """
						SELECT
							`showid`
						FROM
							`shows`
						WHERE
							`path` = ?
					"""
					
					results = len(Database.getRows(sql, (fullPath,)))
					
					if results < 1:
						sql = """
							INSERT INTO
								`shows`
									(`show`, `path`, `lastPlayTime`, `plays`)
							VALUES
									(?, ?, ?, 0)
						"""
						
						Logger(Logger.VERBOSE, 'adding show: '+fullPath)
						
						Database.execute(sql, [show, fullPath, int(os.stat(fullPath).st_atime)])
			else:#is a directory, recursive search
				self.searchAndAddEpisodes(show, fullPath)
