import json
import os


def get_json_data(directory, prefix):
    for dirname, dirnames, filenames in os.walk(directory):
        for filename in filenames:
            if not filename.startswith(prefix) or not filename.endswith('.json'):
                continue
            print("loading " + filename)
            yield json.load(open(os.path.join(dirname, filename), 'r'), encoding='utf-8')
