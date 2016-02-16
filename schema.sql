drop table if exists segments;
create table segments (
id integer primary key autoincrement,
segment_id integer not null,
segment_name text not null,
hill_score real not null,
var_score real not null
);