import logging
import array
import collections
import uuid
import bson.binary
from datetime import datetime
from io import StringIO
from pymongo import MongoClient
from configparser import ConfigParser
from flask import Flask
from flask import Response, request, url_for
from werkzeug.contrib.fixers import ProxyFix


CONF_FILE = '/etc/fare.conf'


logging.getLogger('werkzeug').setLevel(logging.ERROR)


def read_config(path):
    p = ConfigParser()

    with open(path) as f:
        s = StringIO('[main]\n' + f.read())
        p.readfp(s)

    return p['main']


config = read_config(CONF_FILE)
client = MongoClient(config['db.host'], int(config['db.port']))
db = client[config['db.name']]
files = db.files
app = Flask('Fare')
# Fix X-Forwarded-Proto Flask ignoring issue.
app.wsgi_app = ProxyFix(app.wsgi_app)


MAX_FILE_SIZE = int(config['upload.maxsize'])


class TooLargeError(Exception):
    pass


File = collections.namedtuple('File', ['data', 'name', 'mime'])


def get_file(request):
    if 'file' in request.files:
        f = request.files['file']
        d = f.stream.read(MAX_FILE_SIZE + 1)
        if len(d) > MAX_FILE_SIZE:
            raise TooLargeError('File size limit is {} bytes'.format(MAX_FILE_SIZE))
        mime = f.content_type or config['upload.default-mime']
        return File(d, f.filename, mime)
    if request.mimetype == 'multipart/form-data' and 'file' in request.form:
        return File(request.form['file'].encode('utf-8'),
                    request.form.get('filename', ''),
                    request.form.get('content_type', config['upload.default-mime']))

    return File(request.data, request.headers.get('X-Filename', ''),
                request.content_type)


def save(f):
    id = str(uuid.uuid4())
    files.insert_one({'_id': id,
                      'time': datetime.utcnow(),
                      'name': f.name,
                      'mime': f.mime,
                      'data': bson.binary.Binary(f.data,
                                                 bson.binary.BINARY_SUBTYPE)})

    return id


def find(id):
    f = files.find_one({'_id': id})
    if not f:
        return None

    return File(f['data'], f['name'], f['mime'])


@app.route('/favicon.ico')
def favicon():
    return 'Not found', 404


@app.route('/', methods=['POST'])
def upload():
    try:
        f = get_file(request)
        id = save(f)
        url = url_for('download', id=id, _external=True)

        return Response(url, 200, {'Content-Type': 'text/plain', 'Location': url})
    except TooLargeError as e:
        return str(e), 413


@app.route('/', methods=['GET'])
def blank():
    return '', 200


@app.route('/<string:id>', methods=['GET'])
def download(id):
    f = find(id)
    if not f:
        return 'Not found', 404

    r = Response(f.data, 200, {'Content-Type': f.mime})
    if f.name:
        r.headers['Content-Disposition'] = 'inline; filename="{}"'.format(f.name)

    return r


if __name__ == '__main__':
    app.run(config['http.address'], int(config['http.port']), debug=False)
