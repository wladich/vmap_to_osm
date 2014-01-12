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

def convert(filenames, out_name):
    mif = open(out_name + '.mif', 'w')
    mif.write(mif_header)
    mid = open(out_name + '.mid', 'w')
    for fname in filenames:
        print fname
        for obj in vmap_iterator(open(fname)):
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


