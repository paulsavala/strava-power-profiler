import pandas as pd
import numpy as np
from bokeh.plotting import figure, output_file, show
from bokeh.embed import components
import math
import sqlite3

# ===============- Variability score -=======================
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
	
	return var_pos, var_neg, var

# ====================- Hill score -===========================
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
	

# ===================- Data -==================================
short_df = pd.DataFrame.from_csv('stream.csv')
short_grad_df = short_df.diff().altitude / short_df.diff().distance
short_df['gradient'] = short_grad_df.replace(np.nan, 0)

long_df = pd.DataFrame.from_csv('stream2.csv')
long_grad_df = long_df.diff().altitude / long_df.diff().distance
long_df['gradient'] = long_grad_df.replace(np.nan, 0)



var_pos, var_neg, var = variability_scores(short_df['gradient'])
print('Var+ = %f' % var_pos)
print('Var- = %f' % var_neg)
print('Var = %f' % var)
print('Hill score = %f' % hill_score(short_df['gradient'], short_df['distance']))
print('=' * 20)

var_pos, var_neg, var = variability_scores(long_df['gradient'])
print('Var+ = %f' % var_pos)
print('Var- = %f' % var_neg)
print('Var = %f' % var)
print('Hill score = %f' % hill_score(long_df['gradient'], long_df['distance']))


# ====================- Formatting datetimes -====================
# import datetime
# now = datetime.date.today()
# 
# def filter_datetime(date, fmt=None):
#     date = dateutil.parser.parse(date)
#     native = date.replace(tzinfo=None)
#     format='%b %d, %Y'
#     return native.strftime(format) 
    
print(filter_datetime(now))