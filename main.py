from flask import Flask, request, redirect, render_template, url_for
import sqlite3 as sql
from stravalib import Client, unithelper
import pandas as pd
import numpy as np
from bokeh.plotting import figure, output_file, show
from bokeh.embed import components
import math
from datetime import date, datetime
import time

app_lulu = Flask(__name__)

app_lulu.vars = {}

client = Client()
url = client.authorization_url(client_id = 10117, \
	redirect_uri = 'http://127.0.0.1:5000/authorization')



app_lulu.client_secret = strava_secret_key
app_lulu.client_id = strava_client_id

#DATABASE = '/Users/paulsavala/strava_v1/database.db'
DATABASE = 'database.db'

# ==================- Database functions -==================

# This assumes that segment contains an id, name, hill_score and var_score
def insert_segment(segment):
	with sql.connect(DATABASE) as con:
		cur = con.cursor()
		try:
			cur.execute('INSERT INTO segments (segment_id, segment_name, hill_score, \
				var_score) VALUES (?,?,?,?)', (segment.id, segment.name, segment.hill_score, \
				segment.var_score))
			con.commit()
		except sql.IntegrityError:
			return render_template('error.html', error = str(segment.id))
	pass
				
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
	var_score = sum(abs(grad_series.diff().fillna(0)))
	return 1000*var_score # multiplying by 1000 is scaling
# GETTING NEGATIVE VARIABILITY SCORES. SHOULD THERE BE AN ABSOLUTE VALUE HERE?
	
# Grades a hill according to how uphill / downhill it is
# "Large" positive values been long, steep climbs
# "Large" negative values mean long, steep descents
def get_hill_score(grad_series, dist_series):
	# We assume that grad_series is a pandas series holding the gradients
	# at each measurement, and that dist_series is the same for distances 
	# (measured at the same time)
	dist_diff = dist_series.diff().drop(0).replace(np.nan, 0).replace(np.inf, 0)
	grad_series = grad_series.drop(0).replace(np.nan, 0).replace(np.inf, 0)
	
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

# Returns a dict, where each key is the activity id, and the value is a list of segments
def get_segments_from_activities(activities):
	segments = {}
	for activity in activities:
		activity_segments = []
		activity = client.get_activity(activity.id) # For some reason you _have_ to get the activity again, otherwise the efforts are NoneType
		activity_efforts = activity.segment_efforts
		for effort in activity_efforts:
			activity_segments.append(effort.segment)
		segments[activity.id] = activity_segments
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

# Takes in a collection (list, or BatchedResultsIterator) of segments and checks to
# see if they're already in the db. If so it fetches them, if not it calculates the
# score and writes them into the db.
def check_db_for_segments(segments):
	for segment in segments:
		db_segment = retrieve_segment(segment.id)
		if db_segment is None: # if the segment is not yet in the db...
			segment.hill_score, segment.var_score = grade_segment(segment.id)
			insert_segment(segment)
			segment.athlete_rank, segment.leaderboard_size = get_leaderboard_rank(segment.id)
			segment.ranking_score = compute_ranking_score(segment.athlete_rank, segment.leaderboard_size)
		else: # ...else the segment is already in the db, so grab it
			segment_dict = retrieve_segment(segment.id)
			segment.hill_score = round(segment_dict['hill_score'], 2)
			segment.var_score = round(segment_dict['var_score'], 2)
			segment.athlete_rank, segment.leaderboard_size = get_leaderboard_rank(segment.id)
			segment.ranking_score = compute_ranking_score(segment.athlete_rank, segment.leaderboard_size)
	return segments # This returned collection now has hill and var scores attached to each segment
			
# Gets all the attributes attached to an object
def get_object_attrs(object):
	attribs = ' '
	for item in dir(object):
		attribs += item + ' '
	return attribs
	
def get_leaderboard_rank(segment_id, top_results_limit=100):
	leaderboard = client.get_segment_leaderboard(segment_id, top_results_limit = top_results_limit)
	for entry in leaderboard:
		if entry.athlete_id == app_lulu.curr_athlete.id:
			return entry.rank, leaderboard.entry_count
	return 0, 0 # This occurs when the athlete is not found in the top_results_limit
	
def compute_ranking_score(position, leaderboard_size):
	ranking_score = 2 ** (float(1-position) / float(leaderboard_size - 1) + 1) - 1
	return ranking_score
# ==================- Flask functions -=====================

# Have user connect with Strava
@app_lulu.route('/connect')
def connect():
	return render_template('connect.html', connect_url = url)

# Authentication and token exchange
@app_lulu.route('/authorization')
def authorization():
	my_client_id = app_lulu.client_id
	my_client_secret = app_lulu.client_secret
	
	code = request.args.get('code')
	
	access_token = client.exchange_code_for_token(client_id = my_client_id, \
		client_secret = my_client_secret, code = code)
	app_lulu.vars['access_token'] = access_token
	app_lulu.curr_athlete = client.get_athlete()
	
	return render_template('menu.html', athlete = app_lulu.curr_athlete)

# Build the power profile page by grabbing recent activities and segments and populating the graph
@app_lulu.route('/power_profile', defaults = {'after_date': '', 'before_date': ''})
@app_lulu.route('/power_profile/<after_date>/<before_date>')
def power_profile(after_date, before_date):
	if after_date == '' or before_date == '':
		recent_activities = client.get_activities(limit = 3)
	else:
		after = datetime.strptime(after_date, '%m-%d-%Y')
		before = datetime.strptime(before_date, '%m-%d-%Y')
		limit = 50
		recent_activities = client.get_activities(before = before, after = after, limit = limit)
	
	segments = get_segments_from_activities(recent_activities)
	
	start = time.time()
	for activity in recent_activities:
		segments[activity.id] = check_db_for_segments(segments[activity.id])
	end = time.time()
	elapsed_time = end - start

	script, div = placeholder_graph()
	return render_template('layout.html', athlete = app_lulu.curr_athlete, \
		recent_activities = recent_activities, activity_segments = segments, \
		script = script, div = div, debug = str(elapsed_time))
	
@app_lulu.route('/update_recent_rides', methods = ['POST'])
def update_rides():
	before_date = str(request.form['datepicker_before']).replace('/','-')
	after_date = str(request.form['datepicker_after']).replace('/','-')
	return redirect(url_for('power_profile', after_date = after_date, before_date = before_date))
	
# Gets rank on a particular segment
@app_lulu.route('/segment_rank')
def insert_segment_to_db():
	segment_df = get_segment_df(5543676)
	dist_diff = segment_df['distance'].diff().drop(0)
	grad_series = segment_df['gradient'].drop(0).replace(np.inf, 0).replace(np.nan, 0)
	
	return str(grad_series[grad_series.isnull()])

# ======================- Jinja filters -========================= 


# ======================- Housekeeping functions -================

# Settings for local Flask deployment (for testing)
if __name__ == "__main__":
	app_lulu.run(debug=True)
	
# =======================- Old work -==============================

# def get_segments_from_activities(activities):
# 	segments = []
# 	for activity in activities:
# 		activity = client.get_activity(activity.id) # For some reason you _have_ to get the activity again, otherwise the efforts are NoneType
# 		activity_efforts = activity.segment_efforts
# 		for effort in activity_efforts:
# 			segments.append(effort.segment)
# 	return segments