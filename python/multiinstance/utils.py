import json
import os


def get_json_data(directory, prefix):
    for dirname, dirnames, filenames in os.walk(directory):
        for filename in filenames:
            if not filename.startswith(prefix) or not filename.endswith('.json'):
                continue
            print("loading " + filename)
            yield json.load(open(os.path.join(dirname, filename), 'r'), encoding='utf-8')


def generate_username(first_name, last_name):
    """
    Generates a username from first name and last name.
    """
    first_name = first_name.strip()
    last_name = last_name.strip()

    if first_name and last_name:
        base_name = ' '.join((first_name, last_name))
    else:
        base_name = first_name or last_name
        if not base_name:
            raise ValueError("Either 'first_name' or 'last_name' must not be "
                             "empty.")

    return base_name
