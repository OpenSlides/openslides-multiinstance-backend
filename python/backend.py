from optparse import OptionParser

from flask import Flask

import jsonapi.flask
from backendutils import checkRequiredArguments
from jsonapi.base.schema import Schema
from multiinstance.models import Instance, OsVersion
from multiinstance.models import OsDomain
from multiinstance.session import Session
from multiinstance.upload import add_routes
from multiinstance.listing import DomainListing
from multiinstance.models import OsDomain
from multiinstance.utils import generate_username
from backendutils import checkRequiredArguments

parser = OptionParser()
parser.add_option("-i", "--instance-meta-dir", dest="instance_meta_dir",
                  help="[REQUIRED] directory containing instance meta files", metavar="INSTANCE_META_DIR")
parser.add_option("--versions-meta-dir", dest="versions_meta_dir",
                  help="[REQUIRED] directory containing version meta files",
                  metavar="VERSIONS_META_DIR")
parser.add_option("-d", "--instances-dir", dest="instances_dir",
                  help="[REQUIRED] directory containing instance data", metavar="INSTANCES_DIR")
parser.add_option("-a", "--python-ansible", dest="python_ansible",
                  help="[REQUIRED] python binary of ansible virtual environment", metavar="PYTHON_ANSIBLE")
parser.add_option("-u", "--multiinstance-url", dest="multiinstance_url",
                  help="[REQUIRED] URL of the multiinstance api (https://instances.openslides.de/api)",
                  metavar="MULTIINSTANCE_URL")
parser.add_option("-l", "--upload-dir", dest="upload_dir",
                  help="[REQUIRED] directory for uploads",
                  metavar="MULTIINSTANCE_URL")

(options, args) = parser.parse_args()

checkRequiredArguments(options, parser)
instance_meta_dir = options.instance_meta_dir
versions_meta_dir = options.versions_meta_dir


class Database(jsonapi.base.database.Database):
    def session(self):
        return Session(self.api,
                       multiinstance_url=options.multiinstance_url,
                       instance_meta_dir=instance_meta_dir,
                       versions_meta_dir=versions_meta_dir,
                       instances_dir=options.instances_dir,
                       python_ansible=options.python_ansible,
                       upload_dir=options.upload_dir)


UPLOAD_FOLDER = '/tmp'

app = Flask(__name__)


class ReverseProxied(object):
    '''Wrap the application in this middleware and configure the
    front-end server to add these headers, to let you quietly bind
    this to a URL other than / and to an HTTP scheme that is
    different than what is used locally.

    In nginx:
    location /myprefix {
        proxy_pass http://192.168.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Scheme $scheme;
        proxy_set_header X-Script-Name /myprefix;
        }

    :param app: the WSGI application
    '''

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        print('WSGI REQUEST')
        print(environ)
        script_name = environ.get('HTTP_X_SCRIPT_NAME', '')
        if script_name:
            environ['SCRIPT_NAME'] = script_name
            path_info = environ['PATH_INFO']
            if path_info.startswith(script_name):
                environ['PATH_INFO'] = path_info[len(script_name):]

        scheme = environ.get('HTTP_X_FORWARDED_PROTO', '')
        server = environ.get('HTTP_X_FORWARDED_SERVER', '')
        if scheme:
            environ['wsgi.url_scheme'] = scheme
        if server:
            environ['HTTP_HOST'] = server
        return self.app(environ, start_response)

app.wsgi_app = ReverseProxied(app.wsgi_app)

application = app.wsgi_app

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = 'adfndsfadsfnasdfdsaf'

api = jsonapi.flask.FlaskAPI("/api", db=Database(), flask_app=app)

add_routes(app)

api.add_type(Schema(Instance, typename='instances'))
api.add_type(Schema(OsVersion, typename='osversions'))
api.add_type(Schema(OsDomain, typename='osdomains'))

if __name__ == "__main__":
    app.run()
