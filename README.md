# Raikou-Factory (雷光工場)

<p align=center>
    <img src="docs/images/raikou-banner.jpg" width="500"/> <br>
    <img alt="GitHub" src="https://img.shields.io/github/license/lgirdk/raikou-factory">
    <img alt="GitHub commit activity (branch)"
    src="https://img.shields.io/github/commit-activity/t/lgirdk/raikou-factory">
    <img alt="GitHub last commit (branch)"
    src="https://img.shields.io/github/last-commit/lgirdk/raikou-factory">
    <img alt="Python Version" src="https://img.shields.io/badge/python-3.11+-blue">
    <a href="https://github.com/psf/black"><img alt="Code style: black"
    src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
    <a href="https://github.com/astral-sh/ruff"><img alt="Code style: black"
    src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json"></a>
</p> <hr>

## Introduction

Raikou is a FASTAPI web service that simplifies Docker container deployment.

Users access Raikou's Gateway API to deploy containers with a Docker Compose file
and designated Docker context name, offering user-friendly control.

### Key Technical Benefits

- **Client-Agnostic Docker Deployment**: Raikou removes the requirement of
having Docker installed on users' local machines, reducing client-side
dependencies and ensuring that Docker deployment is accessible to a wider user
base.

- **Enhanced Security through Isolation**: Raikou mitigates potential security
risks by preventing user access to target Docker daemons. It achieves this by
concealing the details of the Docker context that manages the node, allowing
users to share only the context name for deployment.

- **Seamless Integration with Automation Test Frameworks**: Raikou, with its
REST APIs, offers easy integration with any Python automation test
framework. This compatibility streamlines the incorporation of Raikou into
existing automation pipelines, enhancing the efficiency of testing processes.

## Motivation

Raikou is designed with a focus on lab administration, ensuring that lab
administrators have the necessary access to endpoint and security information
required for managing different Docker nodes via contexts.

During the deployment process, administrators can conveniently provide
this information to Raikou via a CSV file. <br>
Internally, Raikou automatically generates Docker contexts for the management
of each node within the list.

After deployment, users can access the list of contexts available for their
deployment activities via the ```GET /docker-contexts``` API. <br> This ensures
that they only have access to the contexts relevant to their role,
enhancing security and control.

## Getting Started

1. Ensure docker is installed on your system and clone the repository.

2. Build the image locally using the following commands:
    ```
    docker build -t raikou-factory:alpine3.18 .
    ```

3. Prepare a CSV file containing requirements for target docker context.

    > **_NOTE:_**  Raikou internally configures these target contexts.

    ```
    cat > contexts.csv << EOF
    <context_name>,<ip>,<ssh port>,<user>,<password>
    EOF
    ```

4. Deploy Raikou Factory

    ```
    docker run --name factory --rm -it \
        -d -v $(pwd)/contexts.csv:/root/contexts.csv \
        -p 8000:8000 \
        raikou-factory:alpine3.18
    ```

    Run ```docker logs factory``` to ensure that the requested
    contexts are created:
    ```
    ...
    docker context create <context_name> \
        --docker host=ssh://<user>@<password>:<ssh_port>

    Successfully created context "<context_name>"
    ...
    ```

5. Open the following link on your browser:

    ```http://localhost:8000/redoc```

    <img src="docs/images/API screenshot.png" width="800"/>

## Client-Side Usage

Please see the examples directory for details on how test users can access
Raikou-Factory to handle remote deployments of their docker containers.
