import stravalib
from my_app import app, controller

class Activity(object):
	"""Class for strava activities"""
	def __init__(self, activity):
		super(Activity, self).__init__()
		
		# Parameters
		self.id = activity.id
		self.name = activity.name
		self.start_date = actvity.start_date
		self.distance = activity.distance
	
	def get_segments(self):
		return 'get_segments'
		
		