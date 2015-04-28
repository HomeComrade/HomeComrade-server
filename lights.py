class Lights:
	def __init__(self, red, green, blue):
		self.red = int(red)
		self.green = int(green)
		self.blue = int(blue)
	
	def buildString(self):
		redString = ''
		greenString = ''
		blueString = ''
		
		if self.red > 255 or self.red < 0:
			return None
		else:
			redString = self.intToString(self.red)
		
		if self.green > 255 or self.green < 0:
			return None
		else:
			greenString = self.intToString(self.green)
		
		if self.blue > 255 or self.blue < 0:
			return None
		else:
			blueString = self.intToString(self.blue)
		
		return redString+','+greenString+','+blueString
	
	def intToString(self, num):
		if num < 10:
			return '00'+str(num)
		elif num < 100:
			return '0'+str(num)
		else:
			return str(num)
