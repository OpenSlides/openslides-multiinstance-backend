# Multi instance backend for OpenSlides

## Setup instructions for Debian Jessie

### Initial system preparation

#### Install dependencies from Debian

    apt-get install libpq-dev python-dev libffi-dev python3-gi postgresql nginx \
    redis-server python-psycopg2 python-flask python-pip python3-pip \
    git sudo

Furthermore, we will need software from Backports:

    echo "deb http://ftp.debian.org/debian jessie-backports main" \
        >> /etc/apt/sources.list
    apt-get update

Kernel:

    apt-get install -t jessie-backports linux-image-amd64

Ansible version 2.1 or later:

    apt-get install -t jessie-backports ansible

#### Install Rocket

https://github.com/coreos/rkt/blob/master/Documentation/distributions.md#deb-based

You will probably need to change URLs and file names.

    gpg --recv-key 18AD5014C99EF7E3BA5F6CE950BDD3E0FC8A365E \
        --keyserver pgp.zdv.uni-mainz.de
    mkdir rocket && cd rocket
    wget https://github.com/coreos/rkt/releases/download/v1.16.0/rkt_1.16.0-1_amd64.deb
    wget https://github.com/coreos/rkt/releases/download/v1.16.0/rkt_1.16.0-1_amd64.deb.asc
    gpg --verify rkt_1.16.0-1_amd64.deb.asc
    dpkg -i rkt_1.16.0-1_amd64.deb

Fix installation if necessary:

    apt-get install -f:
    Inst libdbus-1-3 (1.8.20-0+deb8u1 Debian:8.6/stable [amd64]) [rkt:amd64 ]
    Inst dbus (1.8.20-0+deb8u1 Debian:8.6/stable [amd64])

#### Create user and clone repository

    useradd -m -s /bin/bash openslides
    su - -c 'git clone https://github.com/OpenSlides/openslides-multiinstance-backend.git' openslides

#### Install Pip dependencies

    pip3 install cached_property
    pip3 install -r ~openslides/openslides-multiinstance-backend/requirements.txt

### Configuration

#### PostgreSQL setup

    su - postgres
    psql
        CREATE USER openslides_admin WITH PASSWORD '<DBPASSWORD>';
        ALTER USER openslides_admin WITH SUPERUSER;
        \q
    logout

#### Configure Redis and PostgreSQL to listen on the rkt network

`/etc/redis/redis.conf`:

    # bind 127.0.0.1
    bind 127.0.0.1 172.16.28.1

`/etc/postgresql/9.4/main/postgresql.conf`:

    listen_addresses = 'localhost,172.16.28.1'

`/etc/postgresql/9.4/main/pg_hba.conf`:

    # Openslides/Rocket
    host    all             all             172.16.28.0/24          md5

#### Nginx setup

`/etc/nginx/sites-available/openslides`:

    # OpenSlides multi instance management interface

    server {
        listen 80;
        listen [::]:80;
        server_name openslides.example.com;

        location / {
            rewrite ^ https://$server_name$request_uri ;
        }
    }

    server {
        listen 443 ssl spdy;
        listen [::]:443 ssl spdy;
        server_name openslides.example.com;
        client_max_body_size 100m;

        ssl on;
        ssl_protocols TLSv1.2 TLSv1.1 TLSv1;
        ssl_ciphers EECDH+AESGCM:EDH+AESGCM:EECDH:EDH:!MD5:!RC4:!LOW:!MEDIUM:!CAMELLIA:!ECDSA:!DES:!DSS:!3DES:!NULL;
        ssl_prefer_server_ciphers on;
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload";
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 10m;
        ssl_certificate      /etc/ssl/certs/ssl-cert-snakeoil.pem;
        ssl_certificate_key  /etc/ssl/private/ssl-cert-snakeoil.key;
        root   /usr/share/nginx/html;
        index  index.html index.htm;

        include /etc/nginx/openslides/*.locations;

        location /api/ {
            proxy_pass http://localhost:5000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto "https";
        }
        location / {
            proxy_pass http://localhost:4200;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto "https";
        }
    }

Modify the path of your ssl certificate (for `ssl_certificate` and `ssl_certificate_key`)
 * nginx configuration of management interface: see `/etc/nginx/sites-available/openslides`
 * generic nginx configuration of OpenSlides instances: see `openslides-multiinstance-backend/roles/openslides-add-instance/templates/nginx_instance_subdomain.conf.j2`


Enable the new Nginx config:

    ln -s /etc/nginx/sites-available/openslides /etc/nginx/sites-enabled/openslides
    rm -vi /etc/nginx/sites-enabled/default

`/etc/nginx/nginx.conf`:

    include /etc/nginx/openslides/*.conf;

Create directory for OpenSlides:

    mkdir -p /etc/nginx/openslides

#### Configure HTTP Auth

see also http://nginx.org/en/docs/http/ngx_http_auth_basic_module.html

Install required Debian utils:

    apt-get install apache2-utils

Create account:

    htpasswd -c /etc/nginx/conf.d/htpasswd admin

`/etc/nginx/sites-available/openslides` :

    location /api/ {
            proxy_pass http://localhost:5000;

            auth_basic           "closed site";
            auth_basic_user_file conf.d/htpasswd;
    }

    location / {
            proxy_pass http://localhost:4200;

            auth_basic           "closed site";
            auth_basic_user_file conf.d/htpasswd;
    }

#### Setup sudo

Set `openslides` user password:

    passwd openslides

Grant sudo permissions:

    visudo
        openslides ALL=(ALL) NOPASSWD:ALL


### Set up the OpenSlides multi instance backend

#### Retrieve Docker images

    rkt --insecure-options=image fetch docker://openslides/openslides:master

Take note of the SHA512 sum, e.g., `sha512-6a229c6187cb6168eaac1d11ce85b14c`.

#### Configure OpenSlides backend directories and configuration files

    mkdir -p /srv/openslides/versions/
    mkdir -p /srv/openslides/instances/

Create the following two files.  Add the above checksum.

`/srv/openslides/versions/openslides_versions.json`:

    [
      {
          "id": "2.1-master (20170106)",
          "image": "sha512-<<HASH RETURNED BY rkt>>",
      }
    ]

`/srv/openslides/versions/domains.json`:

    [
      {
          "id" : "1",
          "domain" : "openslides.example.com"
      }
    ]

#### Configure Ansible playbook

Look for `postgres_password` in `python/play.py` and configure with DB password
from above:

    'postgres_password': '<DBPASSWORD>'

#### Fix permissions

    chown -R openslides: /srv/openslides/*

### Test

#### Run in foreground

    su - openslides
    cd openslides-multiinstance-backend/python
    python3 backend.py --instance-meta-dir /srv/openslides/instances \
        --versions-meta-dir /srv/openslides/versions --instances-dir \
        /srv/openslides/instances --sudo-password SUDOPASSWORD \
        --python-ansible /usr/bin/python --multiinstance-url \
        instances.openslides.de --upload-dir /tmp

#### Manual queries to backend

##### Request information

    curl -H 'Content-Type: application/vnd.api+json' \
        http://127.0.0.1:5000/api/osversions | json_pp
    curl -H 'Content-Type: application/vnd.api+json' \
        http://127.0.0.1:5000/api/osdomains | json_pp

##### Create an instance

    cd ~pythonopenslides/openslides-multiinstance-backend
    curl -X POST --data-binary @example_instance.json \
        -H 'Content-Type: application/vnd.api+json' \
        http://127.0.0.1:5000/api/instances | json_pp

### Systemd service file example

`/etc/systemd/system/openslides-backend.service`:

    [Unit]
    Description=OpenSlides multi instance backend
    Wants=network.target

    [Service]
    ExecStart=/usr/bin/python3 \
        /home/openslides/openslides-multiinstance-backend/python/backend.py \
        --instance-meta-dir /srv/openslides/instances \
        --versions-meta-dir /srv/openslides/versions --instances-dir \
        /srv/openslides/instances --sudo-password SUDOPASSWORD \
        --python-ansible /usr/bin/python --multiinstance-url \
        instances.openslides.de --upload-dir /tmp
    User=openslides

    [Install]
    WantedBy=multi-user.target

## TODO

* Explain usage of Rocket; warn about security updates of long-running
  instances?
* Which minimal kernel version is required?
* Explain reason for root privileges
* Explain need for `NOPASSWD` in `/etc/sudoers` *and* `--sudo-password` for backend.py
* Provide a sudoers entry with minimal privileges
* Alternatives to sudo?
* Tracked files should not be config files
* Add configuration file option to avoid hard-coding parameters in service files

# MISC

- If rkt messed up your networking:

```
# sudo rkt gc --grace-period=0
```

# SSL TODOs

- adjust roles/openslides-add-instance/templates/nginx_instance_subdomain.conf.j2


# Credits

The ansible scripts are based on scripts made by @ostcar.
