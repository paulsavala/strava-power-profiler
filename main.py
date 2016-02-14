from flask import Flask, request, redirect, render_template
from stravalib import Client, unithelper
import pandas as pd
from bokeh.plotting import figure, output_file, show
from bokeh.embed import components
import datetime

app_lulu = Flask(__name__)

app_lulu.vars = {}

client = Client()
url = client.authorization_url(client_id = 10117, \
	redirect_uri = 'http://127.0.0.1:5000/authorization')

# ==================- Helper functions -====================

# Convert a stream to a proper pandas df
def stream_to_df(stream):
	stream_dict = {}
	for type in stream.keys():
		stream_dict[type] = list(stream[type].data)
		
	stream_df = pd.DataFrame(stream_dict)
	
	return stream_df

# Compute the variability scores
def variability_scores(grad_series):
	# Separate into positive and negative gradients
	grad_pos = grad_series[grad_series >= 0]
	grad_neg = grad_series[grad_series < 0]

	# Compute the means
	grad_mean = grad_series.mean()
	grad_pos_mean = grad_pos.mean()
	grad_neg_mean = grad_neg.mean()

	# Get the lengths
	n = grad_series.shape[0]
	n_pos = grad_pos.shape[0]
	n_neg = grad_neg.shape[0]

	# Compute the positive and negative variability scores
	try:
		var_pos = math.sqrt(sum((grad_pos - grad_pos_mean) ** 2)) / n_pos
	except ZeroDivisionError:
		var_pos = 0

	try:
		var_neg = math.sqrt(sum((grad_neg - grad_neg_mean) ** 2)) / n_neg
	except ZeroDivisionError:
		var_neg = 0

	# Compute total variability
	var = var_pos + var_neg
	
	return var, var_pos, var_neg
	
# Grades a hill according to how uphill / downhill it is
# "Large" positive values been long, steep climbs
# "Large" negative values mean long, steep descents
def hill_score(grad_series, dist_series):
	# We assume that grad_series is a pandas series holding the gradients
	# at each measurement, and that dist_series is the same for distances 
	# (measured at the same time)
	dist_diff = dist_series.diff().drop(0)
	grad_series = grad_series.drop(0)
	
	hill_score = sum(dist_diff * grad_series)
	
	return hill_score

# Grab the most recent activities
def recent_activities(num_activities = 5):
	client = Client(access_token = app_lulu.vars['access_token'])
	athlete = client.get_athlete()
	
	activities = client.get_activities(limit = num_activities)
	
	return activities
# ==================- Flask functions -=====================

# Have user connect with Strava
@app_lulu.route('/connect')
def connect():
	return render_template('connect.html', connect_url = url)

# Authentication and token exchange
@app_lulu.route('/authorization')
def authorization():
	my_client_id = 10117
	my_client_secret = 'dceb245a0fe67bcebb54a7c1af1d8a1a58025157'
	
	code = request.args.get('code')
	
	access_token = client.exchange_code_for_token(client_id = my_client_id, \
		client_secret = my_client_secret, code = code)
	app_lulu.vars['access_token'] = access_token
	
	return redirect('/graph_profile')

# Get the stream for a SEGMENT
@app_lulu.route('/segment_stream')
def segment_stream(segment_id = 3944715):
	types = ['distance', 'altitude']
	stream = client.get_segment_streams(segment_id, types = types, resolution = 'high')

	stream_df = stream_to_df(stream)

	return ('Got the stream for segment with id %d' % segment_id)
	
# Render the power profile chart page. Right now the chart is static.
@app_lulu.route('/graph_profile')
def graph_profile():
	curr_athlete = client.get_athlete()
	
	# This is a temporary, static graph acting as a placeholder
	p = figure(plot_width = 450, plot_height = 450)
	p.logo = None
	p.toolbar_location = None
	p.patch([-3,0,2,0], [0,2,0,-1], line_width = 2, alpha = 0.5)
 	#p.axis.minor_tick_line_color = None
  	#p.xaxis.axis_label = ''
 	#p.yaxis.axis_label = ''
	
	script, div = components(p)
	
	# Next we grab the most recent rides
	recent_rides = recent_activities()
	
	return render_template('layout.html', script = script, div = div, recent_activities = recent_rides, athlete = curr_athlete)
	
# ======================- Jinja filters -========================= 
# @app_lulu.template_filter('strftime')
# def _jinja2_filter_date(d, fmt = None):
#     date = datetime.datetime.strptime(d, fmt)
#     native = date.replace(tzinfo = None)
#     format='%Y'
#     return native.strftime(format) 

# ======================- Housekeeping functions -================

# Settings for local Flask deployment (for testing)
if __name__ == "__main__":
	app_lulu.run(debug=True)