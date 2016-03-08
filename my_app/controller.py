from my_app import app
import sqlite3 as sql

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