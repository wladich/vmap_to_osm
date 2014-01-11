----------- Pedestrain tunels
DO $$
for tunel in plpy.execute("SELECT *, ST_LineInterpolatePoint(geom, 0.5) AS point FROM lines WHERE type='0x10001b'"):
    road = plpy.execute("""
        SELECT * from lines 
        WHERE type IN ('0x100001', '0x10000b', '0x100002') 
        AND st_dwithin(geom::geography, '{0}'::geography, 20) 
        ORDER BY ST_Distance(geom, '{0}') ASC  LIMIT 1""".format(tunel['point']))
    if road:
        road = road[0]
        pos = plpy.execute("SELECT ST_LineLocatePoint('{0}', '{1}') as pos". format(road['geom'], tunel['point']))[0]['pos']
        plpy.execute("UPDATE map_podm SET geom=ST_LineInterpolatePoint('{road}', {pos}) WHERE id={id}".format(road=road['geom'], pos=pos, id=tunel['id']))
        plpy.execute("UPDATE map_podm SET geom=ST_LineMerge(ST_Union(ST_LineSubstring('{road}', 0, {pos}), ST_LineSubstring('{road}', {pos}, 1))) WHERE id={id}".format(road=road['geom'], id=road['id'], pos=pos))
$$
LANGUAGE 'plpythonu';

----------- Railway stations
DO $$
for station in plpy.execute("SELECT * FROM points WHERE type='0x5905'"):
    road = plpy.execute("""
        SELECT * from lines 
        WHERE type IN ('0x100027', '0x10000d') 
        AND st_dwithin(geom::geography, '{0}'::geography, 20) 
        ORDER BY ST_Distance(geom, '{0}') ASC  LIMIT 1""".format(station['geom']))
    if road:
        road = road[0]
        pos = plpy.execute("SELECT ST_LineLocatePoint('{0}', '{1}') as pos". format(road['geom'], station['geom']))[0]['pos']
        plpy.execute("UPDATE map_podm SET geom=ST_LineInterpolatePoint('{road}', {pos}) WHERE id={id}".format(road=road['geom'], pos=pos, id=station['id']))
        plpy.execute("UPDATE map_podm SET geom=ST_LineMerge(ST_Union(ST_LineSubstring('{road}', 0, {pos}), ST_LineSubstring('{road}', {pos}, 1))) WHERE id={id}".format(road=road['geom'], id=road['id'], pos=pos))
$$
LANGUAGE 'plpythonu';