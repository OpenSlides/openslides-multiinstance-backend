import json
import mimetypes
import os

from flask import send_file, request, flash, redirect, jsonify

from utils import random_string

ALLOWED_EXTENSIONS = set(['png'])


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


def add_routes(app):
    @app.route('/api/blobs/<blob_id>', methods=['GET'])
    def get_file(blob_id):
        filename = os.path.join(app.config['UPLOAD_FOLDER'], blob_id)
        meta_file_content = open(filename + '.json').read()
        mime_type = mimetypes.guess_type(json.loads(meta_file_content)['filename'])
        return send_file(filename, mimetype=mime_type[0])

    @app.route('/api/blobs', methods=['POST'])
    def upload_file():
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            blob_id = random_string(20)
            file.save(blob_file_path(blob_id))
            meta_file = open(os.path.join(app.config['UPLOAD_FOLDER'], blob_id + '.json'), 'w')
            meta_file.write(json.dumps({
                "filename": file.filename
            }))
            meta_file.close()

            return jsonify({
                'blobId': blob_id
            })

    def blob_file_path(blob_id):
        return os.path.join(app.config['UPLOAD_FOLDER'], blob_id)
