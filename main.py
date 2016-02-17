from flask import Flask, request, redirect, render_template, url_for
import sqlite3 as sql
from stravalib import Client, unithelper
import pandas as pd
from bokeh.plotting import figure, output_file, show
from bokeh.embed import components
import math
import helpers as my # My own collection of helper functions

app_lulu = Flask(__name__)

app_lulu.vars = {}

client = Client()
url = client.authorization_url(client_id = 10117, \
	redirect_uri = 'http://127.0.0.1:5000/authorization')

DATABASE = '/Users/paulsavala/strava_v1/database.db'
#DATABASE = '/database.db'

# ==================- Database functions -==================

# This assumes that segment contains an id, name, hill_score and var_score
def insert_segment(segment):
	try:
		with sql.connect(DATABASE) as con:
			cur = con.cursor()
			cur.execute('INSERT INTO segments (segment_id, segment_name, hill_score, \
				var_score) VALUES (?,?,?,?)', (segment.id, segment.name, segment.hill_score, \
				segment.var_score))
			con.commit()
		return 'Segment successfully inserted'
	except AttributeError:
		return 'Segment is lacking some attributes. Required attributes are id, name, \
				hill_score and var_score'
				
# A sqlite row_factory, which gives the results as a dict 
def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

# Gets segment from db by segment id (_not_ the db id)
def retrieve_segment(segment_id):
	with sql.connect(DATABASE) as con:
		con.row_factory = dict_factory
		cur = con.cursor()
		if cur.execute('SELECT * FROM %s WHERE %s = %d' % ('segments', 'segment_id', segment_id)):
			segment = cur.fetchone()
		else:
			segment = {}
	return segment
	

# ====================- Helper functions -==================
# Convert a stream to a proper pandas df
def stream_to_df(stream):
	stream_dict = {}
	for type in stream.keys():
		stream_dict[type] = list(stream[type].data)
		
	stream_df = pd.DataFrame(stream_dict)
	
	return stream_df

# Compute the variability score
def get_var_score(grad_series):
	var_score = sum(grad_series.diff().fillna(0))
	return var_score
	
# Grades a hill according to how uphill / downhill it is
# "Large" positive values been long, steep climbs
# "Large" negative values mean long, steep descents
def get_hill_score(grad_series, dist_series):
	# We assume that grad_series is a pandas series holding the gradients
	# at each measurement, and that dist_series is the same for distances 
	# (measured at the same time)
	dist_diff = dist_series.diff().drop(0)
	grad_series = grad_series.drop(0)
	
	hill_score = sum(dist_diff * grad_series)
	
	return hill_score

# Fetch a segment by id and convert to a df	
def get_segment_df(id):
	stream = client.get_segment_streams(id, types=['distance', 'altitude'], resolution='high')
	segment_stream_df = stream_to_df(stream)
	segment_grad_df = segment_stream_df.diff()['altitude'] / segment_stream_df.diff()['distance']
	segment_stream_df['gradient'] = segment_grad_df.fillna(0)
	return segment_stream_df

# Returns all segment grades given an id
def grade_segment(id):
	segment_df = get_segment_df(id)
	hill_score = get_hill_score(segment_df['gradient'], segment_df['distance'])
	var_score = get_var_score(segment_df['gradient'])
	return hill_score, var_score
	
def get_segments_from_activities(activities):
	segments = []
	for activity in activities:
		activity = client.get_activity(activity.id) # For some reason you _have_ to get the activity again, otherwise the efforts are NoneType
		activity_efforts = activity.segment_efforts
		for effort in activity_efforts:
			hill_score, var_score = grade_segment(effort.segment.id)
			effort.hill_score = round(hill_score, 2)
			effort.var_score = round(100*var_score, 2)
			segments.append(effort)
	return segments
	
# This is a temporary, static graph acting as a placeholder
def placeholder_graph():
	p = figure(plot_width = 450, plot_height = 450)
	p.logo = None
	p.toolbar_location = None
	p.patch([-3,0,2,0], [0,2,0,-1], line_width = 2, alpha = 0.5)
	p.axis.minor_tick_line_color = None
	p.xaxis.axis_label = ''
	p.yaxis.axis_label = ''
	
	script, div = components(p)
	return script, div

# ==================- Flask functions -=====================

# Have user connect with Strava
@app_lulu.route('/connect')
def connect():
	return render_template('connect.html', connect_url = url)

# Authentication and token exchange
@app_lulu.route('/authorization')
def authorization():
	my_client_id = 10117
	my_client_secret = 'secret_key'
	
	code = request.args.get('code')
	
	access_token = client.exchange_code_for_token(client_id = my_client_id, \
		client_secret = my_client_secret, code = code)
	app_lulu.vars['access_token'] = access_token
	app_lulu.curr_athlete = client.get_athlete()
	
	return render_template('menu.html', athlete = app_lulu.curr_athlete)

# Build the power profile page by grabbing recent activities and segments and populating the graph
@app_lulu.route('/power_profile')
def power_profile():
	recent_activities = client.get_activities(limit=3)
	segments = get_segments_from_activities(recent_activities)
	for segment in segments:
		db_segment = retrieve_segment(segment.id)
		if db_segment is None:
			insert_segment(segment)
	script, div = placeholder_graph()
	return render_template('layout.html', \
		recent_segments = segments, athlete = app_lulu.curr_athlete, \
		recent_activities = recent_activities, script = script, div = div)

# Testing work to write a segment into the db
@app_lulu.route('/insert_segment_to_db')
def insert_segment_to_db():
	segment = client.get_segment(5147121)
	segment.hill_score, segment.var_score = grade_segment(5147121)
	segment.hill_score = round(segment.hill_score, 0)
	segment.var_score = round(100*segment.var_score, 2)
	result = insert_segment(segment)
	return 'Done'
	

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