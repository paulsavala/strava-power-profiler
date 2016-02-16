from flask import Flask, request, redirect, render_template, session, g, url_for, \
	abort, flash
import sqlite3
from stravalib import Client, unithelper
import pandas as pd
import pandas as np
from bokeh.plotting import figure, output_file, show
from bokeh.embed import components
import math
import helpers as my # My own collection of helper functions

app_lulu = Flask(__name__)

app_lulu.vars = {}

client = Client()
url = client.authorization_url(client_id = 10117, \
	redirect_uri = 'http://127.0.0.1:5000/authorization')

# ==================- Flask functions -=====================

# Have user connect with Strava
@app_lulu.route('/connect')
def connect():
	return render_template('connect.html', connect_url = url)

# Authentication and token exchange
@app_lulu.route('/authorization')
def authorization():
	my_client_id = 10117
	my_client_secret = 'include my secret key'
	
	code = request.args.get('code')
	
	access_token = client.exchange_code_for_token(client_id = my_client_id, \
		client_secret = my_client_secret, code = code)
	app_lulu.vars['access_token'] = access_token
	app_lulu.curr_athlete = client.get_athlete()
	
	return render_template('menu.html', athlete = app_lulu.curr_athlete)

# Build the power profile page by grabbing recent activities and segments and populating the graph
@app_lulu.route('/power_profile')
def grade_segments():
	recent_activities = client.get_activities(limit=3)
	segments = get_segments_from_activities(recent_activities)
	script, div = placeholder_graph()
	return render_template('layout.html', \
		recent_segments = segments, athlete = app_lulu.curr_athlete, \
		recent_activities = recent_activities, script = script, div = div)


# ======================- Jinja filters -========================= 


# ======================- Housekeeping functions -================

# Settings for local Flask deployment (for testing)
if __name__ == "__main__":
	app_lulu.run(debug=True)
	
# =======================- Old work -==============================

## I don't think I need this, but I'm keeping it in case something breaks!		
# Get the stream for a SEGMENT
# @app_lulu.route('/grade_segments')
# def grade_segments():
# 	segments = []
# 	recent_activities = client.get_activities(limit=3)
# 	for activity in recent_activities:
# 		activity = client.get_activity(activity.id) # For some reason you _have_ to get the activity again, otherwise the efforts are NoneType
# 		activity_efforts = activity.segment_efforts
# 		for effort in activity_efforts:
# 			hill_score, var_score = grade_segment(effort.segment.id)
# 			effort.hill_score = round(hill_score, 2)
# 			effort.var_score = round(100*var_score, 2)
# 			segments.append(effort)
# 	return render_template('layout.html', \
# 		recent_segments = segments, athlete = app_lulu.curr_athlete)