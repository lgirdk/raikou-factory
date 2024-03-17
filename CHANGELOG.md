## v1.1.0 (2024-03-17)

### Feat

- **factory**: update to v25.0.4 alpine 3.19
- **factory**: add API to update files in containers

### Fix

- **supervisor**: fix process kill error

## v1.0.0 (2024-03-17)

### Feat

- **app/docker_orchestrator.py**: perform docker network prune before deployment
- **examples**: sample deployment
- **docker_orchestrator.py**: specify context for all docker and docker-compose invocations
- dump docker-compose based on syntax
- **factory**: add a bosa board example
- **factory**: fix SSH reuse conn issues
- **factory**: added docker factory implementation

### Fix

- **Dockerfile**: update openssh version
- **factory**: update Dockerfile libraries

### Refactor

- **raikou-factory**: update LICENSE and documentation
- **raikou-factory**: move factory code to root project path
