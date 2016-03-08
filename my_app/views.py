from flask import render_template, request, redirect, url_for
from my_app import app, data
from my_app.data import StravaClient
from stravalib import Client
import time
from datetime import date, datetime
		
# Set the route and accepted methods
@app.route('/connect')
def connect():
	client = Client()
	url = client.authorization_url(client_id = app.vars['client_id'], \
		redirect_uri = 'http://127.0.0.1:5000/authorization')
	return render_template('connect.html', connect_url = url)

# Authentication and token exchange
@app.route('/authorization')
def authorization():
	my_client_id = app.vars['client_id']
	my_client_secret = app.vars['client_secret']

	code = request.args.get('code')

	client = Client()
	access_token = client.exchange_code_for_token(client_id = my_client_id, \
		client_secret = my_client_secret, code = code)
	app.vars['access_token'] = access_token
	
	my_client = StravaClient()
	app.vars['athlete'] = my_client.get_athlete()
	
	return redirect('power_profile')

# Build the power profile page by grabbing recent activities and segments and populating the graph
@app.route('/power_profile', defaults = {'after_date': '', 'before_date': ''})
@app.route('/power_profile/<after_date>/<before_date>')
def power_profile(after_date, before_date):
	
	start = time.time()
	if (after_date == '' or before_date == ''):
		recent_activities = data.get_activities(limit = 3)
	else:
		after = datetime.strptime(after_date, '%m-%d-%Y')
		before = datetime.strptime(before_date, '%m-%d-%Y')
		limit = 50
		recent_activities = data.get_activities(before = before, after = after, limit = limit)
		
	activities_segment_efforts = data.get_segment_efforts_from_activities(recent_activities)
	
	# Testing
	for activity in recent_activities:
		effort_scored = [data.attach_scores_to_efforts(x) for x in activities_segment_efforts[activity.id]]
	seg = data.get_segment_from_effort(10066421)
	# End Testing
	
	# with sql.connect(DATABASE) as con:
# 		con.row_factory = dict_factory
# 		cur = con.cursor()
# 		segments_inserted = []
# 		for activity in recent_activities:
# 			segments[activity.id], this_activity_inserted = check_db_for_segments(segments[activity.id], cur, con)
# 			segments_inserted.append(this_activity_inserted)
	end = time.time()
	elapsed_time = end - start
 	
	elapsed_time = ['get_segments: %f' % elapsed_time]
	
	return render_template('layout.html', athlete = None, \
		recent_activities = recent_activities, activity_segments = activities_segment_efforts, \
		debug = str())
	
@app.route('/update_recent_rides', methods = ['POST'])
def update_rides():
	before_date = str(request.form['datepicker_before']).replace('/','-')
	after_date = str(request.form['datepicker_after']).replace('/','-')
	return redirect(url_for('power_profile', after_date = after_date, before_date = before_date))
	
# Gets rank on a particular segment
@app.route('/testing')
def testing():
	#activities = data.get_activities(before = '02/29/2016', after = '09/01/2015', limit = 3)
	#activity_segments = actClass.get_segments_from_activities(activities)

	stream = data.attach_segment_scores(10066421)

	pass