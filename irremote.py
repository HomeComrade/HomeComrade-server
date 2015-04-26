import os

#local imports
import config

class IRRemote:
	POWER = 'KEY_POWER'
	VOLUME_UP = 'KEY_VOLUMEUP'
	VOLUME_DOWN = 'KEY_VOLUMEDOWN'
	MUTE = 'KEY_MUTE'
	SOURCE = 'KEY_SOURCE'
	
	@staticmethod
	def sendCommand(command):
		os.system('irsend SEND_ONCE '+config.IR_REMOTE_NAME+' '+command)
