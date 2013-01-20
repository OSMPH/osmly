#!/usr/bin/env python

import sqlite3
from flask import Flask, render_template, request
import json
from shapely.geometry import mapping, Polygon
import shapely.wkt
import time
import random
import math

app = Flask(__name__)

sqlite = {
    'db': 'laparks.sqlite',
    'table': 'parks',  # need to standardize table naming
    'columns': ['OGC_FID', 'GEOMETRY'],
    'where': 'shape_area < 27000000'
}
    # columns[1] is always OGC_FID
    # columns[2] is always GEOMETRY
    # other columns are optional and get used as tags

# adds a tag to everything
    #   'area': 'yes',
    #   'leisure': 'park',
    #   'source': 'TIGER 2012'
# tags will override columns that are named the same
add_tag = {}

# 'error' is an identifier
# 'display' is the actual ui message
error = {
    'error': '',
    'display': ''
}

# in meters, to limit clientside query size
# todo: redo ogr2ogr script and define srs +units=m
AREA_LIMIT = 1000


@app.route('/', methods=['GET', 'POST'])
def slash():
    if request.method == 'POST':
        # log: uploaded, skipped, or reported
        done(request.form['id'], request.form['action'])
        status = {
            'status': 'ok',
            'id': request.form['id']
        }
        return json.dumps(status)

    elif request.method == 'GET':

        if 'next' in request.args:
            get_set_params(request.args)
            polygon = prep(next())
            return json.dumps(polygon)
        else:
            # plain jane visit
            return render_template('index.html')


def get_set_params(args):
    # args is immutable
    # todo: if empty? ''
    # todo: if whitespace? columns = 'name, source'
    if 'db' in args:
        if ',' in args['db']:
            db = args['db'].split(',')
            db = [x.strip() for x in db]
            db = random.choice(db)
        else:
            db = args['db'].strip()

        sqlite['db'] = db + ".sqlite"

    # just return all columns? sort it out clientside?
    if 'columns' in args:
        if ',' in args['columns']:
            columns = args['columns'].split(',')
        else:
            columns = [args['columns']]

        columns = [x.strip() for x in columns]
        sqlite['columns'].extend(columns)

    # sqlite['where'] += ' AND unixtime < strftime("%s","now")'
    sqlite['where'] += ' AND OGC_FID = 1057'
    # sqlite['where'] += ' AND OGC_FID = 56'


def next():
    conn = sqlite3.connect(sqlite['db'])
    conn.row_factory = sqlite3.Row
    columns = ', '.join(sqlite['columns'])
    # no placeholders on columns or table: http://stackoverflow.com/q/8841488
    row = conn.execute(
        'SELECT %s FROM %s WHERE %s ORDER BY RANDOM() LIMIT 1'
        % (columns, sqlite['table'], sqlite['where'])
    )
    row = row.fetchone()
    # tried doing unixtime in sqlite (strftime("%s","now")), python was taking %s literally :/
    conn.execute(
        'UPDATE %s SET unixtime = %s WHERE OGC_FID = %d'
        % (sqlite['table'], int(time.time()) + 300, row[0])
    )
    # this SELECT then UPDATE is the best I could figure out, mostly because of 'ORDER BY RANDOM()'
    # better idea?
    conn.commit()
    conn.close()

    geo = shapely.wkb.loads(str(row[1]))
    if geo.geom_type == 'MultiPolygon':
        # external of multipolygon
        # leaflet can't edit the inner of multipolygons
        p_list = []
        for p in geo:
            p_list += list(p.exterior.coords)

        geo = Polygon(simple_hull(p_list, p_list, 0.5))
        # print simple_hull(p_list, 0.5)

    geo = geo.simplify(0.00005, False)  # 0.0001 is pretty solid
    envelope = map(str, geo.buffer(0.002).bounds)
    bbox = '[bbox=' + envelope[0] + ',' + envelope[1] + ',' + envelope[2] + ',' + envelope[3] + ']'
        # do it clientside later

    polygon = {
        'id': row[0],
        'bbox': bbox,
        'db': sqlite['db'].split('.')[0],
        'geo': geo,
        'tags': {}
    }

    row = dict(row)
    del row['OGC_FID']
    del row['GEOMETRY']

    # tags from source
    for k, v in row.iteritems():
        polygon['tags'][k] = v

    # additional specified tags
    for k, v in add_tag.iteritems():
        polygon['tags'][k] = v

    return polygon


def simple_hull(coords, coords2, tolerance):
    # tolerance, float 0 -> 1
    # this is pretty inefficient, reconsidering
    hull = []
    for i, c in enumerate(coords):
        near = {
            'id': 0,
            'distance': 0,
            'coords': False
        }
        for i2, rd in enumerate(coords2):
            dist = distance(c, rd)
            if i2 is 0 or i is len(coords):
                near['distance'] = distance(c, rd) + 1
            if dist < near['distance'] and i2 != i:
                # tolerance check around here
                near['id'] = i2
                near['distance'] = dist
                near['coords'] = rd

        hull.append(near['coords'])
        del coords2[near['id']]
        print str(i) + ': ' + str(near['id'])

    print len(hull)
    return hull


def distance(one, two):
    return (one[0] - two[0])**2 + (one[1] - two[1])**2


def prep(polygon):
    polygon['geo'] = mapping(polygon['geo'])
    polygon['geo']['coordinates'] = listit(polygon['geo']['coordinates'])
        # listit() is for converting tuples to a list so it can be modified
    if (len(polygon['geo']['coordinates']) > 1):
        # multipolygon, just the first one
        polygon['geo']['type'] = 'MultiPolygon'
    else:
        del polygon['geo']['coordinates'][0][-1]
    # removes the start/end polygon connecting point
    return polygon


def done(id, result):
    # a few columns have been added to the original table
    # ALTER TABLE parks ADD skip_count NUMERIC NOT NULL DEFAULT 0
    # ALTER TABLE parks ADD unixtime NUMERIC NOT NULL DEFAULT 0
    # ALTER TABLE parks ADD result TEXT
    unix = int(time.time())
    try:
        conn = sqlite3.connect('merged.sqlite')
        if result == 'skip':
            conn.execute(
                'UPDATE merged SET skip_count = skip_count + ?, unixtime = ? WHERE OGC_FID = ?',
                (1, unix, id)
            )
        elif result == 'new':
            conn.execute(
                'UPDATE merged SET result = ?, unixtime = ? WHERE OGC_FID = ?',
                (result, unix, id)
            )
        else:
            conn.execute(
                'UPDATE merged SET result = ?, unixtime = ? WHERE OGC_FID = ?',
                (result, unix, id)
            )
        conn.commit()
        conn.close()
    except sqlite3.OperationalError:
        # add the new columns, can it done in a single statement?
        return 'ok'


def listit(t):
    # http://stackoverflow.com/q/1014352
    return list(map(listit, t)) if isinstance(t, (list, tuple)) else t


if __name__ == '__main__':
    app.run(debug=True)
