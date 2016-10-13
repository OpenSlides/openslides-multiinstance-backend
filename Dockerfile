FROM williamyeh/ansible:ubuntu16.04-onbuild

# ==> Specify requirements filename;  default = "requirements.yml"
#ENV REQUIREMENTS  requirements.yml

# ==> Specify playbook filename;      default = "playbook.yml"
#ENV PLAYBOOK      playbook.yml
ADD roles/instance /roles/instance
ADD playbook.yml /

# ==> Specify inventory filename;     default = "/etc/ansible/hosts"
#ENV INVENTORY     inventory.ini

# ==> Executing Ansible (with a simple wrapper)...
RUN ansible-playbook-wrapper

VOLUME /supervisord.conf
VOLUME /data

EXPOSE 5000

CMD ["/usr/bin/supervisord", "-n"]
