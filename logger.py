import config

class Logger:
	VERBOSE = 0
	DEBUG = 1
	INFO = 2
	ERROR = 3
	
	def __init__(self, level, message):
		if config.DEBUG and level >= config.DEBUG_LEVEL:
			try:
				print(str(level)+') '+message)
			except UnicodeEncodeError:
				print('Unicode encode error when trying to print level '+str(level)+' message')
