# -*- coding: utf-8 -*-
import unipath
from vmap_parser import vmap_iterator

src_dir = unipath.Path('./tmp/map_podm/vmap')
dest_dir = unipath.Path('.')

quads_town_to_village = ['o37-126', 
                         'o37-114', 
                         'n37-003', 
                         'o37-133']


def get_objects_by_type(fname, codes):
    if not hasattr(codes, '__iter__'):
        codes = [codes]
    for obj in vmap_iterator(open(fname)):
        if obj['code'] in codes:
            yield obj
        
#def make_lists(src_dir, dest_dir):
#    fnames = unipath.Path(src_dir).listdir('*.vmap')
    
def has_locase(s):
    for c in s:
        if c in u'абгдеёжзиклмнопртуфхцчшщъыьэюя':
            return True
    return False

town_to_village = {}

with open(dest_dir.child('towns_to_villages.txt'), 'w') as f:
    for quad in quads_town_to_village:
        fn = src_dir.child(quad + '.vmap')
        for obj in get_objects_by_type(fn, 0x700):
            name = obj['label'].strip()
            print >> f, '\t'.join([quad, hex(obj['code']), name])

with open(dest_dir.child('caps.txt'), 'w') as f:
    for fn in src_dir.listdir('*.vmap'):
        quad = fn.stem
        for obj in get_objects_by_type(fn, [0x700, 0x800, 0x900]):
            name = obj['label'].strip().decode('utf-8')
            if not has_locase(name):
                print >> f, '\t'.join(
                    [quad, 
                    name.encode('utf-8'), 
                    name.capitalize().encode('utf-8')])

with open(dest_dir.child('villages_to_towns.txt'), 'w') as f:
    for quad in quads_town_to_village:
        fn = src_dir.child(quad + '.vmap')
        for obj in get_objects_by_type(fn, 0x900):
            name = obj['label'].strip()
            print >> f, '\t'.join([quad, hex(obj['code']), name])
