# -*- coding: utf-8 -*-
from vmap_parser import vmap_iterator
mif_header = '''Version 300
Charset "UTF-8"
Delimiter ","
CoordSys Earth Projection 1, 104
Columns 4
  type char(12)
  label char(64)
  dir integer
  angle integer
DATA
'''

caps_names = {}
for line in open('caps.txt').readlines():
    quad, caps_name, name = line.split('\t')
    caps_names[(quad, caps_name)] = name.strip()
    
towns_to_vilages = set()
for line in open('towns_to_villages.txt').readlines():
    quad, code, name = line.split('\t')
    name = name.strip()
    towns_to_vilages.add((quad, code, name))

villages_to_towns = set()
for line in open('villages_to_towns.txt').readlines():
    quad, code, name = line.split('\t')
    name = name.strip()
    villages_to_towns.add((quad, code, name))

exclude_cottage_labels = set()
for line in open('dachi_exclude.txt').readlines():
    name = line.strip()
    exclude_cottage_labels.add(name)

def translate_obj(fname, obj):
    quad = fname.stem
    name = obj.get('label', '').strip()
    code = hex(obj['code'])
    if (quad, code, name) in villages_to_towns:
        obj['code'] = 0x700
    elif (quad, code, name) in towns_to_vilages:
        obj['code'] = 0x900
    if (quad, name) in caps_names:
        obj['label'] = caps_names[(quad, name)]
    if code == '0x20004e' and name in exclude_cottage_labels:
        del obj['label']
        
    
def convert(filenames, out_name):
    mif = open(out_name + '.mif', 'w')
    mif.write(mif_header)
    mid = open(out_name + '.mid', 'w')
    for fname in filenames:
        print fname
        for obj in vmap_iterator(open(fname)):
            translate_obj(fname, obj)
            for geom in obj['geom']:
                code = (obj['code'])
                if code >= 0x200000:
                    kind = 'REGION'
                elif code >= 0x100000:
                    kind = 'PLINE'
                else:
                    kind = 'POINT'
                if kind == 'POINT':
                    assert len(geom) == 1
                    mif.write('\nPOINT %s %s\n' % (geom[0]))
                else:
                    new_geom = [geom[0]]
                    prev_p = geom[0]
                    for p in geom[1:]:
                        if p != prev_p:
                            prev_p = p
                            new_geom.append(p)
                    geom = new_geom
                    if kind == 'PLINE':
                        if len(geom) < 2:
                            continue
                        mif.write('\nPLINE\n')    
                    else:
                        if geom[-1] != geom[0]:
                            geom.append(geom[0])
                        if len(geom) < 4:
                            continue
                        mif.write('\nREGION 1\n')
                    mif.write('  %d\n' % (len(geom)))
                    for x, y in geom:
                        mif.write('%s %s\n' % (x, y))
                mid.write('%s, "%s", %s, %s\n' % (hex(obj['code']), obj.get('label', ''), obj.get('dir', ''), obj.get('angle', '')))
        

    mif.close()
    mid.close()
    
if __name__ == '__main__':
    import sys
    import unipath
    if len(sys.argv) != 3:
        print 'Usage: vmap_to_mif.py VMAPS_DIR OUT_FILE_NAME_BASE'
        exit(1)
    src_dir, dest_filename = sys.argv[1:]
    fnames = unipath.Path(src_dir).listdir('*.vmap')
    convert(fnames, dest_filename)
#    fnames = '/home/w/projects/osm-slazav/map_podm/mp/n36-024.mp'


