Dependencies for backend.py
===========================

```
# sudo apt-get install libpq-dev python-dev libffi-dev python3-gi
```

- Create virtualenv with system-packages (e.g. mkvirtualenv backend --system-site-packages -p /usr/bin/python3). This is required for pydbus

```
# pip install  cached_property
# pip install -r requirements.txt
```

Dependencies for play.py
========================

```
# mkvirutalenv ansible -p /usr/bin/python2
# pip install -r requirements-ansible.txt
```

Host System Setup
=================

Install rkt
-----------

```
# sudo aptitude install postgresql nginx
# sudo mkdir /etc/nginx/openslides
```

Add admin user in postgresql
----------------------------

```
CREATE USER openslides_admin WITH PASSWORD 'asdf';
ALTER USER openslides_admin WITH SUPERUSER;
```

Add generated locations/vhosts to nginx
---------------------------------------

-> Add 'include /etc/nginx/openslides/*.locations;' in a vhost config of your choice
-> Add 'include /etc/nginx/openslides/*.conf;' in main nginx.conf

Configure redis and postgresql to listen to rkt network
-------------------------------------------------------

- in /etc/redis/redis.conf: bind 127.0.0.1 172.16.28.1
- in /etc/postgresql/.../postgresql.conf: listen_addresses = 'localhost,172.16.28.1'
- in /etc/postgresql/.../pg_hba.conf: host  all  all 172.16.28.0/24 md5

Add OpenSlides version
----------------------

1. get docker image: sudo rkt --insecure-options=image fetch docker://openslides/openslides
2. copy sha512 hash shown by rkt fetch
3. create file for version, e.g. /srv/openslides/versions/openslides_version_2_1.json
```
{
  "id": "2.1",
  "image": "sha512-<<HASH FOR STEP 2>>",
  "default": true|false
}
```

Check
-----

```
# cd python
# python backend.py --instance-meta-dir /srv/openslides/instances --versions-meta-dir /srv/openslides/versions --instances-dir /srv/openslides/instances --sudo-password <YOURPASSWORD> --python-ansible /home/$USER/.virtualenvs/ansible/bin/python
# curl -H 'Content-Type: application/vnd.api+json' http://127.0.0.1:5000/api/versions | json_pp
# curl -X POST --data-binary @example_instance.json -H 'Content-Type: application/vnd.api+json' http://127.0.0.1:5000/api/instances | json_pp
```
- add
```
127.0.0.1 konferenz.local
```
to /etc/hosts

- go to http://konferenz.local in your browser

MISC
====

- If rkt messed up your networking:

```
# sudo rkt gc --grace-period=0
```

Credits
=======

The ansible scripts are based on scripts made by @ostcar.
