FROM docker:25.0.4-alpine3.19

LABEL maintainer="ktewari@libertyglobal.com"
LABEL version="alpine3.18"

WORKDIR /root

COPY requirements.txt requirements.txt
COPY ./app app

RUN apk add -u --no-cache \
    python3=3.11.9-r0 \
    py3-pip=23.3.1-r0 \
    py3-cffi=1.16.0-r0 \
    bash=5.2.21-r0 \
    openrc=0.52.1-r2 \
    openssh=9.6_p1-r0 \
    sshpass=1.10-r0 \
    uuidgen=2.39.3-r0 \
    iproute2=6.6.0-r0 \
    supervisor=4.2.5-r4 && \
    \
    # Configure SSH key
    /usr/bin/ssh-keygen -t rsa -b 4096 -N '' -f /root/.ssh/id_rsa && \
    /usr/bin/ssh-keygen -t rsa -b 4096 -N '' -f /etc/ssh/ssh_host_rsa_key && \
    sed -i 's,#PermitRootLogin.*$,PermitRootLogin yes,1' /etc/ssh/sshd_config && \
    \
    # Install python dependencies
    # Handle PEP668
    python3 -m pip --no-cache-dir install --break-system-packages -U pip wheel && \
    python3 -m pip --no-cache-dir install --break-system-packages -r requirements.txt  && \
    chmod +x app/init



# Add supervisord configuration file
COPY ./config/supervisord.conf /etc/supervisord.conf

ENV PYTHONPATH "${PYTHONPATH}:/root/app/"

EXPOSE 8000

ENTRYPOINT [ "app/init" ]
