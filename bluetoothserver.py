import serial, os, time, re, threading, queue

from logger import Logger
import busschedules.bus_station, busschedules.airport, busschedules.viru_keskus

UTC_OFFSET = 3

os.environ['TZ'] = 'Europe/Tallinn'
time.tzset()

class BluetoothServer:
	HARDWARE_BUTTON_PRESS = 'hardware-button-press'
	HARDWARE_BUTTON_PRESS_AND_HOLD = 'hardware-button-press-and-hold'
	
	QUEUE = queue.Queue()
	
	@staticmethod
	def startThreads():
		#restart this thread after 3 seconds
		#set as daemon so it will die when the main script dies
		try:
			thread = threading.Thread(target=mainLoop)
			thread.daemon = True
			thread.start()
		except KeyboardInterrupt:
			pass

class StopTimes:
	def __init__(self, busStop, nowDayOfWeek, nowHour, nowMinute):
		self.busStop = busStop#dictionary BUS_STATION, etc.
		
		self.startDayOfWeek = nowDayOfWeek
		self.startHour = nowHour
		self.startMinute = nowMinute
		
		self.nowDayOfWeek = nowDayOfWeek
		self.nowHour = nowHour
		self.nowMinute = nowMinute
		
		self.firstBusNumber = '99'
		self.firstBusTime = 99
		self.firstBusHoursIteration = 0#how many hours ahead we had to go from the initially supplied hour, for final minutes-from-now calculation
		
		self.secondBusNumber = '99'
		self.secondBusTime = 99
		self.secondBusHoursIteration = 0
	
	def moveFirstToSecondBusTime(self):
		self.secondBusNumber = self.firstBusNumber
		self.secondBusTime = self.firstBusTime
		self.secondBusHoursIteration = self.firstBusHoursIteration
	
	def hasUnsetTime(self, checkNumber = None):
		if None == checkNumber:
			if '99' == self.firstBusNumber or '99' == self.secondBusNumber:
				return True
		else:
			if '99' == checkNumber:
				return True
		
		return False
	
	def logTimes(self):
		Logger(Logger.VERBOSE, 'firstBusNumber: ' + self.firstBusNumber + ' time: ' + str(self.firstBusTime) + ' hours: ' + str(self.firstBusHoursIteration))
		Logger(Logger.VERBOSE, 'secondBusNumber: ' + self.secondBusNumber + ' time: ' + str(self.secondBusTime) + ' hours: ' + str(self.secondBusHoursIteration))

	def setNextBusses(self, hoursIteration = 0):
		dayKey = ''
		
		if 0 == self.nowDayOfWeek:#Sunday
			dayKey = 'sunday'
		elif 6 == self.nowDayOfWeek:#Saturday
			dayKey = 'saturday'
		else:#Work day
			dayKey = 'workDay'
		
		#do the bus stations
		hourTimes = self.busStop[dayKey][self.nowHour]
		Logger(Logger.DEBUG, str(hourTimes))
		for busNumber, minutes in hourTimes.items():
			for minute in minutes:
				#skip anything in the past
				if minute <= self.nowMinute:
					continue;
				
				combinedMinutes = minute + (60 * hoursIteration)
				combinedFirstBusTimeMinutes = self.firstBusTime + (60 * self.firstBusHoursIteration)
				combinedSecondBusTimeMinutes = self.secondBusTime + (60 * self.secondBusHoursIteration)
				
				if combinedMinutes < combinedFirstBusTimeMinutes:
					#push the first time to the 2nd slot since this is newer
					self.moveFirstToSecondBusTime()
				
					self.firstBusNumber = busNumber
					self.firstBusTime = minute
					self.firstBusHoursIteration = hoursIteration
				elif combinedMinutes < combinedSecondBusTimeMinutes:
					self.secondBusNumber = busNumber
					self.secondBusTime = minute
					self.secondBusHoursIteration = hoursIteration
		
		if self.hasUnsetTime():
			self.nowMinute = 0
			self.nowHour = self.nowHour + 1
			hoursIteration = hoursIteration + 1
			
			#if we have gone this far, we probably have some screwup. to avoid an infinite loop, just break out
			if hoursIteration > 23:
				return self
			
			if 24 == self.nowHour:
				self.nowHour = 0
				self.nowDayOfWeek = self.nowDayOfWeek + 1
				
				if self.nowDayOfWeek > 6:
					self.nowDayOfWeek = 0
			
			return self.setNextBusses(hoursIteration)
		
		self.logTimes()
		
		return self
	
	def getString(self):
		#BUS_NUMBER:MINUTES_TILL_DEPARTURE,BUS_NUMBER:MINUTES_TILL_DEPARTURE
		returnString = assert2Digits(self.firstBusNumber) + ':' + assert2Digits(self.timeToMinutesTill(self.firstBusTime, self.firstBusHoursIteration)) + ','
		returnString += assert2Digits(self.secondBusNumber) + ':' + assert2Digits(self.timeToMinutesTill(self.secondBusTime, self.secondBusHoursIteration))
		
		return returnString
	
	def timeToMinutesTill(self, busTime, hoursIteration):
		return str(busTime + (hoursIteration * 60) - self.startMinute)

def assert2Digits(num):
	num = int(re.sub('[^0-9]', '', num))
	
	if num < 10:
		return '0' + str(num)
	elif num > 99:
		num = 99
	
	return str(num)

def mainLoop():
	Logger(Logger.DEBUG, 'Starting main Bluetooth thread')
	
	bluetoothSerial = serial.Serial('/dev/rfcomm1', baudrate=9600)
	sendBusMessageSeconds = 5#every 5 seconds
	busMessageTimer = int(time.time()) - sendBusMessageSeconds#send first message right away
	
	while True:
		writeString = None
		currentTime = int(time.time())
		command = None
		
		if not BluetoothServer.QUEUE.empty():
			command = BluetoothServer.QUEUE.get()
		
		if command == BluetoothServer.HARDWARE_BUTTON_PRESS:
			writeString = '#1#'
			Logger(Logger.DEBUG, 'Hardware button press - '+writeString)
		elif command == BluetoothServer.HARDWARE_BUTTON_PRESS_AND_HOLD:
			writeString = '#2#'
			Logger(Logger.DEBUG, 'Hardware button press and hold - '+writeString)
		
		if (currentTime - busMessageTimer) > sendBusMessageSeconds:
			busMessageTimer = currentTime
			
			#print time.strftime('%d')#day
			#print time.strftime('%H')#hour
			#print time.strftime('%M')#minute
			#print time.strftime('%w')#day of week
			
			nowDayOfWeek = int(time.strftime('%w'))
			nowHour = int(time.strftime('%H'))
			nowMinute = int(time.strftime('%M'))
			
			#nowDayOfWeek = 0
			#nowHour = 19
			#nowMinute = 58
			
			busStationBusses = StopTimes(busschedules.bus_station.schedule, nowDayOfWeek, nowHour, nowMinute).setNextBusses().getString()
			airportBusses = StopTimes(busschedules.airport.schedule, nowDayOfWeek, nowHour, nowMinute).setNextBusses().getString()
			viruKeskusBusses = StopTimes(busschedules.viru_keskus.schedule, nowDayOfWeek, nowHour, nowMinute).setNextBusses().getString()
			
			writeString = '!'+busStationBusses+';'+airportBusses+';'+viruKeskusBusses+'!'
			#writeString = busStationBusses
			
			Logger(Logger.DEBUG, 'Prepared BT message - Week: '+str(nowDayOfWeek)+' '+str(nowHour)+':'+str(nowMinute)+' '+writeString)
		
		if writeString:
			try:
				bluetoothSerial.write(bytes(writeString, 'UTF-8'))
			except serial.serialutil.SerialException:
				bluetoothSerial = serial.Serial('/dev/rfcomm1', baudrate=9600)
