FROM docker:24.0.2-dind-alpine3.18

WORKDIR /root

COPY requirements.txt requirements.txt

RUN apk add -u --no-cache \
    python3=3.11.4-r0 \
    py3-pip=23.1.2-r0 \
    bash=5.2.15-r5 \
    openrc=0.48-r0 \
    openssh=9.3_p2-r0 \
    sshpass=1.10-r0 \
    uuidgen=2.38.1-r8 \
    iproute2=6.3.0-r0 \
    supervisor=4.2.5-r2 && \
    \
    # Configure SSH key
    /usr/bin/ssh-keygen -t rsa -b 4096 -N '' -f /root/.ssh/id_rsa && \
    /usr/bin/ssh-keygen -t rsa -b 4096 -N '' -f /etc/ssh/ssh_host_rsa_key && \
    sed -i 's,#PermitRootLogin.*$,PermitRootLogin yes,1' /etc/ssh/sshd_config && \
    \
    # Install python dependencies
    python3 -m pip --no-cache-dir install -U pip wheel && \
    python3 -m pip --no-cache-dir install -r requirements.txt

COPY init init
COPY ./app app

# Add supervisord configuration file
COPY ./config/supervisord.conf /etc/supervisord.conf

ENV PYTHONPATH "${PYTHONPATH}:/root/app/"

EXPOSE 8000

ENTRYPOINT [ "/root/init" ]
