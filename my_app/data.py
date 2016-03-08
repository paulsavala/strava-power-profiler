"""
For interacting with the strava api
"""

from flask import render_template, redirect, request
from my_app import app
from my_app.model import Activity

from stravalib import Client

import numpy as np


class StravaClient(Client):
	def __init__(self):
		super(StravaClient, self).__init__(access_token=app.vars['access_token'], rate_limit_requests=True)

def get_activities(before = None, after = None, limit = 500):
	client = StravaClient()
	if (before != None) and (after != None):
		activities = client.get_activities(before = before, after = after, limit = limit)
	else:
		activities = client.get_activities(limit = limit)
	return activities

# Returns a dict indexed by activity.id
def get_segment_efforts_from_activities(activities):
	client = StravaClient()
	activity_id_list = [activity.id for activity in activities]
	activities = map(client.get_activity, activity_id_list)
	activities_segment_efforts = {activity.id: activity.segment_efforts for activity in activities}
	return activities_segment_efforts

# Returns a stravalib segment object given an effort	
def get_segment_from_effort(effort):
	if type(effort) == int:
		client = StravaClient()
		effort = client.get_segment_effort(effort)
		
	segment = effort.segment
	return segment
	
def get_segment_scores(effort):
	client = StravaClient()
	if type(effort) == int:
		segment = client.get_segment_effort(effort)

	stream = client.get_effort_streams(effort.id, resolution='high', types=['distance', 'grade_smooth'])
	gradient = np.array(stream['grade_smooth'].data) / 100 # Convert gradient to decimal
	dist = np.array(stream['distance'].data) / 1000 # Convert distance to km
	
	var_score = 10 * sum(abs(np.diff(gradient)))
	hill_score = sum(dist * gradient) / 10
	
	climb_val = max(hill_score, 0) * 4 / 3;
	puncheur_val = var_score;
	sprint_val = max(100 - abs(float(effort.distance) - 250)/5 - puncheur_val - hill_score, 0);
	tt_val = max(0, 25 * (np.log(float(effort.distance)/1000)) / np.sqrt(1 + puncheur_val));

	return int(var_score), int(hill_score), int(climb_val), int(puncheur_val), \
	 	int(sprint_val), int(tt_val)
	
def attach_scores_to_efforts(effort):
	if type(effort) == int:
		client = StravaClient()
		effort = client.get_segment_effort(effort)

	var_score, hill_score, climb_val, puncheur_val, sprint_val, tt_val = get_segment_scores(effort)
	effort.var_score = var_score
	effort.hill_score = hill_score
	effort.climb_val = climb_val
	effort.puncheur_val = puncheur_val
	effort.sprint_val = sprint_val
	effort.tt_val = tt_val
	
	return effort

def get_segments_from_activity(activity):
	segments = {activity.id: [effort.segment for effort in activity.segment_efforts] for activity in activities}
	return segments
	
def attach_scores_to_segment(segment):
	if type(segment) == int:
		client = StravaClient()
		segment = client.get_segment(segment)
		
