# Demo Notes

## Repository Notes

1. Clone **docker-recipes** repo
    ```
    git clone http://10.64.38.13:8080/gerrit/c/lgi/docker-recipes/
    ```


2. Cherry-pick/checkout the following change if not merged already
    ```
    git fetch ssh://ktewari.contractor@10.64.38.13:29418/lgi/docker-recipes refs/changes/99/1499/3 && git checkout FETCH_HEAD
    ```

## Initial checks

1. Ensure docker is installed on you system.

2. Pull the pre-pushed docker factory image
    ```
    docker pull 10.64.38.13:5000/bf-docker-factory:alpine3.18-dind-ovs_2.17
    ```

3. In case the image pull fails, build the image locally using the following
commands:
    ```
    source VERSION
    docker build -t $registry/$name:$version .
    ```

4. Prepare the contexts.csv file under the **docker-recipes/factory** directory
    ```
    cd docker-recipes/factory
    echo "nuc1,10.71.10.117,22,boardfarm,BF_prod_ams" > contexts.csv
    ```

5. If you have provided a demo of local docker compose deployment.
Ensure to perform a ```docker compose down``` before deploying via factory.

    In case docker compose down does not work, just execute the following 2 commands on the NUC:
    ```
    docker stop $(docker ps -aq)
    docker rm $(docker ps -aq)
    ```

## Deploy Docker Factory

```
docker run --name factory --rm -it \
    -d -v $(pwd)/contexts.csv:/root/contexts.csv \
    -p 8000:8000 10.64.38.13:5000/bf-docker-factory:alpine3.18-dind-ovs_2.17
```

Run ```docker logs factory``` to ensure that context is created:
```
...
+ docker context create nuc1 --docker host=ssh://boardfarm@10.71.10.117:22
nuc1
Successfully created context "nuc1"
...
```

## Run Python Client to deploy virtual boards.

### Pre-Requisites
1. Prepare a python venv with httpx installed.

2. Ensure that you execute the python client from
**docker-recipes/factory/example/virtual_board/** directory

### Execution

Run the python client
```
python client.py
```

Expect an output similar to this:
```
Printing Docker Compose API output..
Please wait..
...
...
...
...
 Container acs  Started
 Container bng  Started
 Container orchestrator  Starting
 Container orchestrator  Started


Collecting docker container stats...
Please wait...
Container_name: /acs, Status: running
Container_name: /bng, Status: running
...
...
Dumping stats in /tmp/container.json
```

## Run Python Client to deploy infra for a physical board.

### Pre-Requisites
1. Prepare a python venv with httpx installed.

2. Ensure that you execute the python client from
**docker-recipes/factory/example/physical_board/** directory

### Execution

Run the python client
```
python client.py
```

Expect an output similar to this:
```
Printing Docker Compose API output..
Please wait..
...
...
...
...
 Container acs  Started
 Container bng  Started
 Container orchestrator  Starting
 Container orchestrator  Started


Collecting docker container stats...
Please wait...
Container_name: /acs, Status: running
Container_name: /bng, Status: running
...
...
Dumping stats in /tmp/container.json
```

### Key points to highlight here before running boardfarm3

1. [docker-compose.yaml](./example/physical_board/docker-compose.yaml) does not contain the board container as it is now a physical entity.

2. If we look at the [config.json](./example/physical_board/config.json), the
OVS bridges have parent interfaces attached, as they now speak to the real world.
    ```
    {
    "bridge": {
        ...

        "cpe-to-olt": {
            "parent": "enx6c5ab06c1349",
            "trunk": "10,121",
            "untagged": "1081"
        },

        "lan1-to-cpe": {
            "parent": "lan1_parent"
        },

        "lan2-to-cpe": {
            "parent": "lan2_parent"
        },

        ...
    },
    ```
 > Note: We can understand from above snippet that the WAN port of board
 > is connected to the NUC via iface ```enx6c5ab06c1349``` and expects
 > to forward VLAN packets tagged with VLAN ID 10/121/untagged.
 > In case of untagged packets we want them to be part of native vlan 1081.

 This showcases how we support VLAN hunting feature for the Mv3 Ethernet CPE.

### Run Boardfarm

```
boardfarm --board-name F5685LGE-5-17 \
    --inventory-config ~/workspace/boardfarm_repos/docker-recipes/factory/example/physical_board/inventory.json  \
    --env-config ../boardfarm_repos/boardfarm-lgi/json_payload/F5685LGE/weekly/env-default_dual-nowifi.json \
    --ldap-credentials "ktewari.contractor;ba7ad2b4" \
    --jenkins-url http://10.64.38.13:8081/jenkins \
    --jenkins-credentials "ktewari.contractor;11abfe5ab831ce332a4b0f1381ff610bd7" \
    --skip-boot
```

> Note: Ensure that the inventory.json path is the one
> from the **docker-recipes/factory/example/physical_board/** directory


### What to ensure if we're dynamically adding a new LAN/WAN container

Since we've already added LAN3, sharing an example if we wanted to
add another WAN container.


1. First add the service in [docker-compose.yaml](./example/physical_board/docker-compose.yaml)
    ```
      wan2:
        container_name: wan2
        image: "10.64.38.13:5000/bf-wan:bullseye-3.11.1-lwds_lite_1.0"
        ports:
            - "4009:22"
            - "10109:8080"
        environment:
            DNS_UPSTREAM: "10.64.36.53"
            LEGACY: "no"
        privileged: true
        hostname: "wan2"
    ```
    Ensure that the ports are not in conflict with the rest of the services.
    Also the **container_name**, and **hostname** are updated.

2. Then showcase the network addition in OVS configuration file
[config.json](./example/physical_board/config.json)
    ```
    {
    "bridge": {
        "bng-to-uplink1": {},

        ...
    },
    "container": {
        ...

         "wan2": [
            {
                "bridge": "bng-to-uplink1",
                "gateway": "172.25.1.1",
                "gateway6": "2001:dead:beef:2::1",
                "iface": "eth1",
                "ip6address": "2001:dead:beef:2::102/64",
                "ipaddress": "172.25.1.102/24"
            }
        ]
    ```
    Ensure that the IP address is not in conflict with the rest of the services.

3. Re-run the python client

4. Update the [INVENTORY.JSON](./example/physical_board/inventory.json)
    ```
    {
    "F5685LGE-5-17": {
        "devices": [
            ...

            {
                "color": "cyan",
                "connection_type": "authenticated_ssh",
                "http_proxy": "10.71.10.117:10109",
                "ipaddr": "10.71.10.117",
                "name": "wan2",
                "options": "wan-no-dhcp-server, tftpd-server, mgmt_dns: 10.64.36.53, wan-static-ip:172.25.1.102/24, wan-static-ipv6:2001:dead:beef:2::102/64, static-route:0.0.0.0/0-172.25.1.1, dante",
                "port": 4009,
                "type": "debian_wan"
            },
    ```
    Ensuring here that the ports and ip addresses match with the OVS
    config.json

5. Run boardfarm3 and showcase interact
