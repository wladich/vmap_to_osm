#!/bin/bash
set -e
set -x
basedir="`dirname $0`"
temp_dir="$basedir/tmp"
mkdir -p "$temp_dir"
gitdir=$temp_dir/map_podm
mif_base=$temp_dir/map_podm

if [ -e "$gitdir" ]; then
    pushd "$gitdir"
    git pull
    popd
else
    mkdir -p "$gitdir"
    git clone "https://github.com/slazav/map_podm.git" "$gitdir"
fi

dbname=import_mappodm
pg="psql --user postgres --host 127.0.0.1 --port 5432 -v ON_ERROR_STOP=1 "

python vmap_to_mif.py "$gitdir/vmap" "$mif_base"
$pg -c "DROP DATABASE IF EXISTS $dbname;"
$pg -c "CREATE DATABASE $dbname WITH ENCODING='UTF8';"
pg="$pg -d $dbname "
$pg -c "CREATE EXTENSION postgis;"

ogr2ogr  -s_srs EPSG:4326  -f PostgreSQL  PG:dbname="import_mappodm user=postgres host=127.0.0.1 port=5432" -lco FID=id -lco GEOMETRY_NAME=geom "$mif_base.mif"

$pg -f "$basedir/basic.sql" > /dev/null
$pg -f "$basedir/funcs.sql" > /dev/null
$pg -f "$basedir/proh.sql" > /dev/null
$pg -f "$basedir/landcover.sql" > /dev/null
$pg -f "$basedir/swamps.sql" > /dev/null
$pg -f "$basedir/simplify_lines.sql" > /dev/null
$pg -f "$basedir/points_on_lines.sql" > /dev/null
python $basedir/pg2osm.py
