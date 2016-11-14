#
# Image configured with systemd and docker-in-docker.  Useful for
# simulating multinode deployments.
#
# The standard name for this image is openshift/dind
#
# Notes:
#
#  - disable SELinux on the docker host (not compatible with dind)
#
#  - to use the overlay graphdriver, ensure the overlay module is
#    installed on the docker host
#
#      $ modprobe overlay
#
#  - run with --privileged
#
#      $ docker run -d --privileged openshift/dind
#

FROM fedora:24

# Fix 'WARNING: terminal is not fully functional' when TERM=dumb
ENV TERM=xterm

## Configure systemd to run in a container

ENV container=docker

VOLUME ["/run", "/tmp"]

STOPSIGNAL SIGRTMIN+3

RUN systemctl mask\
 auditd.service\
 console-getty.service\
 dev-hugepages.mount\
 dnf-makecache.service\
 docker-storage-setup.service\
 getty.target\
 lvm2-lvmetad.service\
 sys-fs-fuse-connections.mount\
 systemd-logind.service\
 systemd-remount-fs.service\
 systemd-udev-hwdb-update.service\
 systemd-udev-trigger.service\
 systemd-udevd.service\
 systemd-vconsole-setup.service
RUN cp /usr/lib/systemd/system/dbus.service /etc/systemd/system/;\
 sed -i 's/OOMScoreAdjust=-900//' /etc/systemd/system/dbus.service

# Remove non-english translations for glibc to reduce image size by 100mb.
# docker-v1.10-migrator is unnecessary for a new docker installation
# selinux-policy-minimum is unnecessary since selinux won't be enabled
ENV PKGS="procps python-devel gcc make redhat-rpm-config git docker glibc-langpack-en iptables libcap-ng-python npm python-pip"
ENV REMOVE_PKG="npm python-devel gcc make docker-v1.10-migrator glibc-all-langpacks selinux-policy-minimum"

COPY requirements.txt /tmp/

RUN dnf -y update && dnf -y install --setopt=tsflags=nodocs ${PKGS} \
 && systemctl enable docker.service \
 && npm install -g bower \
 && mkdir -p /opt/flask-cap/static/ /opt/flask-cap/templates \
 && cd /opt/flask-cap/static \
 && bower install patternfly --save --allow-root \
 && pip install -r /tmp/requirements.txt \ 
 && dnf -y remove ${REMOVE_PKG} \
 && dnf -y autoremove \
 && dnf clean all
  

# Default storage to vfs.  overlay will be enabled at runtime if available.
RUN echo "DOCKER_STORAGE_OPTIONS=--storage-driver vfs" >\
 /etc/sysconfig/docker-storage

COPY dind-setup.sh /usr/local/bin
COPY dind-setup.service /etc/systemd/system/
COPY gunicorn.service /etc/systemd/system/
COPY gunicorn.socket /etc/systemd/system/
RUN systemctl enable dind-setup.service && \
    systemctl enable gunicorn.service

VOLUME ["/var/lib/docker"]

# Hardlink init to another name to avoid having oci-systemd-hooks
# detect containers using this image as requiring read-only cgroup
# mounts.  containers running docker need to be run with --privileged
# to ensure cgroups are mounted with read-write permissions.
RUN ln /usr/sbin/init /usr/sbin/dind_init
EXPOSE 8000 9000
CMD ["/usr/sbin/dind_init"]
COPY app.py /opt/flask-cap/ 
COPY templates/* /opt/flask-cap/templates/
