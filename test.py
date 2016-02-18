import pandas as pd
import sqlite3 as sql
from datetime import date, datetime

date = '02/19/2016'
stripped_date = datetime.strptime(date, '%m/%d/%Y')
print(stripped_date)

# DATABASE = '/Users/paulsavala/strava_v1/database.db'
# 
# def dict_factory(cursor, row):
#     d = {}
#     for idx, col in enumerate(cursor.description):
#         d[col[0]] = row[idx]
#     return d
# 
# # Gets segment from db by segment id (_not_ the db id)
# def retrieve_segment(segment_id):
# 	with sql.connect(DATABASE) as con:
# 		con.row_factory = dict_factory
# 		cur = con.cursor()
# 		if cur.execute('SELECT * FROM %s WHERE %s = %d' % ('segments', 'segment_id', segment_id)):
# 			segment = cur.fetchone()
# 		else:
# 			segment = {}
# 	return segment
# 	
# segment = retrieve_segment(5147121)
# print(segment)


# ====================- Formatting datetimes -====================
# import datetime
# now = datetime.date.today()
# 
# def filter_datetime(date, fmt=None):
#     date = dateutil.parser.parse(date)
#     native = date.replace(tzinfo=None)
#     format='%b %d, %Y'
#     return native.strftime(format) 