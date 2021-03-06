# -*- coding: utf-8 -*-
import psycopg2
import osmapi
import json
import time


src_db = dict(database='import_mappodm', user='postgres', host='127.0.0.1', port='5432')
dest_db = dict(database='osm', user='postgres', host='127.0.0.1', port='5434')
default_tags = [('source', 'import:map_podm')]

def parse_tags(s):
    tags =  filter(None, (t.strip() for t in s.split(';')))
    tags = (t.split('=') for t in tags)
    tags = [(k.strip(), v.strip()) for k, v in tags]
    if not tags:
        raise Exception('No tags')
    return tags

def float_to_coord(x):
    return int(round(x * 10000000))
    
def way(sql, tags, label_tag=None):
    sql = 'SELECT ST_ASGEOJSON(t1.geom, 6), t1.label  FROM (%s) AS t1' % sql
    tags = default_tags + parse_tags(tags)
    cur = pg.cursor()
    cur.execute(sql)
    for geom, label in cur:
        geom = json.loads(geom)
        if geom['type'] != 'LineString':
            raise Exception('Got "%s" for way' % geom['type'])
        coords = geom['coordinates']
        coords = [(float_to_coord(x), float_to_coord(y)) for x, y in coords]
        way_tags = tags[:]
        if label_tag:
            if label:
                label = label.strip()
            if label:
                way_tags.append((label_tag, label))
        osm.add_way(coords, way_tags)

def area(sql, tags, label_tag=None):
    sql = 'SELECT ST_ASGEOJSON(t1.geom, 6), t1.label  FROM (%s) AS t1' % sql
    tags = default_tags + parse_tags(tags)
    cur = pg.cursor()
    cur.execute(sql)
    for geom, label in cur:
        geom = json.loads(geom)
        if geom['type'] != 'Polygon':
            raise Exception('Got a "%s"for area' % geom['type'])
        coords = geom['coordinates']
        coords = [[(float_to_coord(x), float_to_coord(y)) for x, y in linestring] for linestring in coords]
        area_tags = tags[:]
        if label_tag:
            if label:
                label = label.strip()
            if label:
                area_tags.append((label_tag, label))
        if len(coords) == 1:
            osm.add_way(coords[0], area_tags)
        else:
            osm.add_ways_relation(coords, area_tags)
    
def poi(sql, tags, label_tag=None, use_cache=False):
    sql = 'SELECT DISTINCT ST_ASGEOJSON(t1.geom, 6), t1.label FROM (%s) AS t1' % sql
    tags = default_tags + parse_tags(tags)
    cur = pg.cursor()
    cur.execute(sql)
    for geom, label in cur:
        geom = json.loads(geom)
        if geom['type'] != 'Point':
            raise Exception('Got "%s" for poi' % geom['type'])
        coords = geom['coordinates']
        coords = (float_to_coord(coords[0]), float_to_coord(coords[1]))
        poi_tags = tags[:]
        if label_tag:
            if label:
                label = label.strip()
            if label:
                poi_tags.append((label_tag, label))
        osm.add_poi(coords, poi_tags, use_cache)

    
def roads():
    ##0x100001 автомагистраль
    way("SELECT geom, label FROM lines WHERE type='0x100001'", 'road=highway', 'name')
    #0x10000b крупное шоссе
    way("SELECT geom, label FROM lines WHERE type='0x10000b'",  "road=major", 'name')
    #0x100002 шоссе
    way("SELECT geom, label FROM lines WHERE type='0x100002'",  "road=asphalt", 'name')
    #0x10001a просека широкая
    way("SELECT geom, label FROM lines WHERE type='0x10001c'",  "road=cutting_wide", 'name')
    for proh in 0, 2, 3, 4, 5:
        if proh == 0:
            proh_tag = ""
        else:
            proh_tag = ";passability=%s" % proh
        #0x100004 проезжий грейдер
        way("SELECT geom, label FROM proh%s_lines WHERE type='0x100004'" % proh,  "road=advanced; drive=yes%s" % proh_tag, 'name')
        #0x100007 непроезжий грейдер
        way("SELECT geom, label FROM proh%s_lines WHERE type='0x100007'" % proh,  "road=advanced%s" % proh_tag, 'name')
        #0x100006 проезжая грунтовка
        way("SELECT geom, label FROM proh%s_lines WHERE type='0x100006'" % proh,  "road=dirt; drive=yes%s" % proh_tag, 'name')   
        #0x10000a непроезжая грунтовка
        way("SELECT geom, label FROM proh%s_lines WHERE type='0x10000a'" % proh,  "road=dirt%s" % proh_tag, 'name')
        #0x100016 просека
        way("SELECT geom, label FROM proh%s_lines WHERE type='0x100016'" % proh,  "road=cutting%s" % proh_tag, 'name')
        #0x10002d заросшая дорога
        way("SELECT geom, label FROM proh%s_lines WHERE type='0x10002d'" % proh,  "road=abandoned%s" % proh_tag, 'name')
        #0x10002a тропа
        way("SELECT geom, label FROM proh%s_lines WHERE type='0x10002a'" % proh,  "road=path%s" % proh_tag, 'name')
        #0x10002b сухая канава
        way("SELECT geom, label FROM proh%s_lines WHERE type='0x10002b'" % proh,  "road=trench%s" % proh_tag, 'name')
        #0x10002c вал
        way("SELECT geom, label FROM proh%s_lines WHERE type='0x10002c'" % proh,  "road=wall%s" % proh_tag, 'name')
    #0x100027 железная дорога
    #0x10000d	мал.хребет -- используется для не магистральных железных дорог
    way("SELECT geom, label FROM lines WHERE type in ('0x100027', '0x10000d')",  "road=railway", 'name')
    #0x100028 газопровод
    way("SELECT geom, label FROM lines WHERE type='0x100028'",  "road=gasline", 'name')
    #0x100029 лэп
    way("SELECT geom, label FROM lines WHERE type='0x100029'",  "road=powerline_major", 'name')
    #0x10001a маленькая лэп
    way("SELECT geom, label FROM lines WHERE type='0x10001a'",  "road=powerline", 'name')    

def points():
    #0x700 "город"
    poi("SELECT geom, label FROM points WHERE type='0x700'", 'poi=town', 'name')
    #0x800 "село"
    #0x900 "деревня"
    poi("SELECT geom, label FROM points WHERE type in ('0x800', '0x900')", 'poi=village', 'name')
    #0xd00 "отметка высоты" -- не делаем
    #0xf00 "триангуляционный знак"
    poi("SELECT geom, label FROM points WHERE type='0xf00'", 'poi=trig', 'elevation')
    #0x1000 "отметка уреза воды"  -- не делаем
    #0x1100 "отметка высоты"  -- не делаем
    #0x2800 "подпись лесного квартала, урочища"
    poi("SELECT distinct geom, label FROM points WHERE type='0x2800' AND label IS NOT NULL", 'poi=label', 'name')
    #0x2c04 "памятник"
    poi("SELECT geom, label FROM points WHERE type='0x2c04'", 'poi=memorial', 'name')
    #0x2c0b "церковь"
    poi("SELECT geom, label FROM points WHERE type='0x2c0b'", 'poi=church', 'name')
    #0x2e00 "магазин"
    poi("SELECT geom, label FROM points WHERE type='0x2e00'", 'poi=store', 'name')
    #0x2f08 "остановка автобуса"
    poi("SELECT geom, label FROM points WHERE type='0x2f08'", 'poi=bus_stop', 'name')
    #0x5905 "ж/д станция"
    poi("SELECT geom, label FROM points WHERE type='0x5905'", 'poi=railway_station', 'name', use_cache=True)
    #0x6402 "дом"
    poi("SELECT geom, label FROM points WHERE type='0x6402'", 'poi=building', 'name')
    #0x6403 "кладбище"
    poi("SELECT geom, label FROM points WHERE type='0x6403'", 'poi=cemetry', 'name')
    #0x6406 "перевал" -- нет на карте
    #0x640c "шахта" -- 4 шт на карте в одном месте, не делаем
    #0x6411 "башня"
    poi("SELECT geom, label FROM points WHERE type='0x6411'", 'poi=tower', 'name')
    #0x6414 "родник"
    poi("SELECT geom, label FROM points WHERE type='0x6414'", 'poi=spring', 'name')
    #0x6415 "развалины"
    poi("SELECT geom, label FROM points WHERE type='0x6415'", 'poi=ruins', 'name')
    #0x650e "порог" -- 15 шт. на карте, не делаем
    #0x6603 "яма" -- не понимаю, что это
    #0x6606 "охотничья вышка, кормушка и т.п."
    poi("SELECT geom, label FROM points WHERE type='0x6606'", 'poi=hunting', 'name')    
    #0x6613 "курган"
    poi("SELECT geom, label FROM points WHERE type='0x6613'", 'poi=mound', 'name')    
    #0x6616 "скала-останец" -- 8 шт. на карте, не делаем

# кривая надпись
# ? все объекты без подписей
#отдельные строения

def bridges():
    # 0x10001b	пешеходный тоннель -- превращаем в точечный
    poi("SELECT geom, label FROM points WHERE type='0x10001b'", 'poi=pedestrain_tunel', use_cache=True)
    #0x100008	мост-1 (пешеходный)
    way("SELECT geom, label FROM lines WHERE type='0x100008'", 'bridge=pedestrain')
    #0x100009	мост-2 (автомобильный)
    #0x10000e	мост-5 (на автомагистралях)
    way("SELECT geom, label FROM lines WHERE type in ('0x100009', '0x10000e')", 'bridge=automobile')

def rivers():
    #0x100015 река-1
    way("SELECT * FROM lines WHERE type='0x100015'",  "river=stream", 'name')
    #0x100018 река-2
    way("SELECT * FROM lines WHERE type='0x100018'",  "river=kneedeep", 'name')
    #0x10001f река-3
    way("SELECT * FROM lines WHERE type='0x10001f'",  "river=wide", 'name')
    #0x100026 пунктирный ручей
    way("SELECT * FROM lines WHERE type='0x100026'",  "river=drying", 'name')

def relief():
    #0x100020 пунктирная горизонталь
    way("SELECT * FROM lines WHERE type='0x100020' AND ST_NPoints(geom)>2",  "relief=contour; deprecated:contour-width=minor", 'elevation')
    #0x100021 горизонтали, бергштрихи
    way("SELECT * FROM lines WHERE type='0x100021' AND ST_NPoints(geom)>2",  "relief=contour", 'elevation')
    #0x100022 жирная горизонталь
    way("SELECT * FROM lines WHERE type='0x100022' AND ST_NPoints(geom)>2",  "relief=contour; deprecated:contour-width=major", 'elevation')
    #### Бергштрихи    
    way("SELECT * FROM lines WHERE type='0x100021' AND ST_NPoints(geom)=2",  "relief=hatch")
    way("SELECT * FROM lines WHERE type='0x100022' AND ST_NPoints(geom)=2",  "relief=hatch; deprecated:contour-width=major")
    #0x10001e	низ обрыва -- не делаем
    #0x100003	верх обрыва
    way("SELECT geom, label FROM lines WHERE type='0x100003'",  "relief=cliff", 'height')
    #0x100025	овраг
    way("SELECT * FROM lines WHERE type='0x100025'",  "relief=ravine")
    #0x10000c	хребет -- используется локально для оврагов, корторые и так видны, не делаем
    

def borders():
    #граница областей 0x10001d -- ??
    #забор 0x100019
    way("SELECT * FROM lines WHERE type='0x100019'",  "border=fence", 'name')
    #контур леса 0x100023
    way("SELECT * FROM lines WHERE type='0x100023'",  "border=forest", 'name')
    
def swamps():
    #глубокое болото 0x20004c 
    area("SELECT geom, label FROM swamps2 WHERE kind='deep'", 'swamp=deep')
    #болото 0x200051 
    area("SELECT geom, label FROM swamps2 WHERE kind = 'swamp'", 'swamp=swamp')
    #болото 0x100024
    area("SELECT geom, label FROM swamps2 WHERE kind = 'lines'", 'swamp=swamp; converted_from_lines=yes')


def landcover():
    #0x200029 водоемы
    #0x20003b большие водоемы
    #0x200053 остров
    area("SELECT geom, label FROM polygons3 WHERE type in ('0x20003b', '0x200029')", 'landcover=water', 'name')
    #0x200001 городская застройка
    area("SELECT geom, label FROM polygons3 WHERE type = '0x200001'", 'landcover=urban')
    #0x20000e сельская застройка
    area("SELECT geom, label FROM polygons3 WHERE type = '0x20000e'", 'landcover=rural')
    #0x20004e дачи
    area("SELECT geom, label FROM polygons3 WHERE type = '0x20004e'", 'landcover=cottage', 'name')    
    #0x200004 закрытые территории
    area("SELECT geom, label FROM polygons3 WHERE type = '0x200004'", 'landcover=restricted', 'name')
    #0x20001a кладбище
    area("SELECT geom, label FROM polygons3 WHERE type = '0x20001a'", 'landcover=cemetry')
    #0x200016 лес
    #0x200015 остров леса
    #0x200052 поле
    area("SELECT geom, '' as label FROM forests", 'landcover=forest')
    #0x200014 редколесье
    area("SELECT geom, label FROM polygons3 WHERE type = '0x200014'", 'landcover=sparse')
    #0x20004f свежая вырубка
    area("SELECT geom, label FROM polygons3 WHERE type = '0x20004f'", 'landcover=felling')
    #0x200050 стар.вырубка
    area("SELECT geom, label FROM polygons3 WHERE type = '0x200050'", 'landcover=felling_overgrown')

osm = osmapi.OSMDB(**dest_db)
pg = psycopg2.connect(**src_db)
osm.truncate()

osm.set_current_user('importer')
changeset_id = osm.open_changeset([('created_by', 'https://github.com/wladich/vmap_to_osm'), ('comment', 'Import of slazav map')])
print 'Changeset %s' % changeset_id
t = time.time()
points()
roads()
bridges()
osm.drop_node_cache()
landcover()
swamps()
rivers()
osm.drop_node_cache()
borders()
osm.drop_node_cache()
relief()


print time.time() - t


osm.close()
