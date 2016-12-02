FROM fedora:24

LABEL   name="jcpowermac/flask-cap" \
        url="https://github.com/jcpowermac/flask-cap" \
        run="docker run -d -p 0.0.0.0:8000:8000 -p 0.0.0.0:9000:9000 --pid=host --privileged --name NAME flask-cap" 
    
ENV PKGS="procps python-devel gcc make redhat-rpm-config git glibc-langpack-en libcap-ng-python npm python-pip"
ENV REMOVE_PKG="npm python-devel gcc make docker-v1.10-migrator glibc-all-langpacks selinux-policy-minimum"

COPY requirements.txt /tmp/

RUN dnf -y update && dnf -y install --setopt=tsflags=nodocs ${PKGS} \
 && npm install -g bower \
 && mkdir -p /opt/flask-cap/static/ /opt/flask-cap/templates \
 && cd /opt/flask-cap/static \
 && bower install patternfly --save --allow-root \
 && pip install -r /tmp/requirements.txt \ 
 && dnf -y remove ${REMOVE_PKG} \
 && dnf -y autoremove \
 && dnf clean all
  
EXPOSE 8000 9000
WORKDIR /opt/flask-cap
ENTRYPOINT ["/usr/bin/gunicorn"]
CMD ["--bind", "0.0.0.0:8000", "--worker-class", "eventlet", "-w", "1", "app:app"]
COPY app.py /opt/flask-cap/ 
COPY templates/* /opt/flask-cap/templates/
