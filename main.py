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

# Strava API values


client = Client()
url = client.authorization_url(client_id = strava_client_id, \
	redirect_uri = 'http://127.0.0.1:5000/authorization')

app_lulu.client_secret = strava_secret_key
app_lulu.client_id = strava_client_id

#DATABASE = '/Users/paulsavala/strava_v1/database.db'
DATABASE = 'database.db'

# ==================- Database functions -==================

# This assumes that segment contains an id, name, hill_score and var_score
def insert_segment(segment, cur, con):
	cur.execute('INSERT INTO segments (segment_id, segment_name, hill_score, \
		var_score) VALUES (?,?,?,?)', (segment.id, segment.name, segment.hill_score, \
		segment.var_score))
	con.commit()
	return segment.id
				
# A sqlite row_factory, which gives the results as a dict 
def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

# Gets segment from db by segment id (_not_ the db id)
def retrieve_segment(segment_id, cur):
	cur.execute('SELECT * FROM %s WHERE %s = %d' % ('segments', 'segment_id', segment_id))
	segment = cur.fetchone()
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
	var_score = sum(abs(grad_series.diff().fillna(0).replace(np.nan, 0).replace(np.inf, 0)))
	return 1000*var_score # multiplying by 1000 is scaling
	
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
	segment_grad_df = segment_stream_df.diff()['altitude'] / segment_stream_df.diff()['distance'].replace(0,segment_stream_df.diff()['distance'].mean())
	segment_stream_df['gradient'] = segment_grad_df.fillna(0)
	return segment_stream_df

# Returns all segment grades given an id
def grade_segment(id):
	segment_df = get_segment_df(id)
	hill_score = get_hill_score(segment_df['gradient'], segment_df['distance'])
	var_score = get_var_score(segment_df['gradient'])
	climb_val, roleur_val, sprint_val, tt_val = get_graph_scores(id, hill_score, var_score)
	return hill_score, var_score, climb_val, roleur_val, sprint_val, tt_val

def get_graph_scores(id, hill_score, var_score):
	segment = client.get_segment(id)
	climb_val = max(hill_score, 0) * 4 / 3;
	roleur_val = var_score / 500;
	sprint_val = max(abs(100 - (abs(float(segment.distance) - 200) + roleur_val)), 0);
	tt_val = 50 * (math.log(float(segment.distance)) / 1000) / (1 + roleur_val);
	return climb_val, roleur_val, sprint_val, tt_val;

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

# Takes in a collection (list, or BatchedResultsIterator) of segments and checks to
# see if they're already in the db. If so it fetches them, if not it calculates the
# score and writes them into the db.
def check_db_for_segments(segments, cur, con):
	inserted_segments = []
	for segment in segments:
		db_segment = retrieve_segment(segment.id, cur)
		if db_segment is None: # if the segment is not yet in the db...
			segment.hill_score, segment.var_score, segment.climb_val, \
				segment.roleur_val, segment.sprint_val, segment.tt_val = grade_segment(segment.id)
			this_id = insert_segment(segment, cur, con)
			inserted_segments.append(this_id)
			#segment.athlete_rank, segment.leaderboard_size = get_leaderboard_rank(segment.id)
			#segment.ranking_score = compute_ranking_score(segment.athlete_rank, segment.leaderboard_size)
		else: # ...else the segment is already in the db
			segment.hill_score = round(db_segment['hill_score'], 2)
			segment.var_score = round(db_segment['var_score'], 2)
			segment.climb_val, segment.roleur_val, segment.sprint_val, \
				segment.tt_val = get_graph_scores(segment.id, segment.hill_score, segment.var_score)
# 			#segment.athlete_rank, segment.leaderboard_size = get_leaderboard_rank(segment.id)
# 			#segment.ranking_score = compute_ranking_score(segment.athlete_rank, segment.leaderboard_size)
	return segments, inserted_segments # This returned collection now has hill and var scores attached to each segment
			
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
	start = time.time()
	if (after_date == '' or before_date == ''):
		recent_activities = client.get_activities(limit = 3)
	else:
		after = datetime.strptime(after_date, '%m-%d-%Y')
		before = datetime.strptime(before_date, '%m-%d-%Y')
		limit = 50
		recent_activities = client.get_activities(before = before, after = after, limit = limit)
	end = time.time()
	elapsed_time_get_activities = end - start
 	
	start = time.time()
	segments = get_segments_from_activities(recent_activities)
	end = time.time()
	elapsed_time_get_segments = end - start
	
	start = time.time()
	with sql.connect(DATABASE) as con:
		con.row_factory = dict_factory
		cur = con.cursor()
		segments_inserted = []
		for activity in recent_activities:
			segments[activity.id], this_activity_inserted = check_db_for_segments(segments[activity.id], cur, con)
			segments_inserted.append(this_activity_inserted)
	end = time.time()
	elapsed_time_check_db = end - start
 	
	elapsed_time = ['get_activities: %f' % elapsed_time_get_activities, \
 		'get_activities: %f' % elapsed_time_get_segments, \
 		'get_activities: %f' % elapsed_time_check_db]
	
	return render_template('layout.html', athlete = app_lulu.curr_athlete, \
		recent_activities = recent_activities, activity_segments = segments, \
		debug = str(elapsed_time))
	
@app_lulu.route('/update_recent_rides', methods = ['POST'])
def update_rides():
	before_date = str(request.form['datepicker_before']).replace('/','-')
	after_date = str(request.form['datepicker_after']).replace('/','-')
	return redirect(url_for('power_profile', after_date = after_date, before_date = before_date))
	
# Gets rank on a particular segment
@app_lulu.route('/segment_rank')
def insert_segment_to_db():
	activity = client.get_activity(497349462)
	activity_efforts = activity.segment_efforts
	kom_ranks = []
	# for effort in activity_efforts:
# 		kom_ranks.append(effort.kom_rank)
	return str(kom_ranks)

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