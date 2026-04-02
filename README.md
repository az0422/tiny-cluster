# Tiny Cluster Framework
## How to Install and Setup
### System Requirements 
* OS: Ubuntu 22.04 LTS or Later
* docker-ce and recommended packages
* nvidia-container-toolkit
* nvidia-driver
* python3-venv

### Master Node
* Install the master controller. Follow command as:
```
git clone https://github.com/az0422/tiny-cluster
cd tiny-cluster/master
./installer
```
* Install the update:
```
cd tiny-cluster
git pull
cd master
./installer
```
* The `tiny` command will be installed on `$HOME/.local` path
* If you want to see detail, command to `tiny -h`

### Worker Node
* Configure worker node container. Follow command as:
```
git clone https://github.com/az0422/tiny-cluster
cd tiny-cluster/worker
./configure
```
* And then enter to `container name` path to build container image and create container
```
cd <container name>
docker compose up -d --build
```
* If install the update:
```
cd <container name>
docker compose down
docker compose up -d --build
```

## How to Use
### Job YAML format
* Format
```
name: <job_name>
env: 
  <environment_key>: "<environment_value>"
venv: <python3 venv path>
path: <project or run directory (default: $HOME)>
exec: <main command>
args: ['<args1>', '<args2>', ...]
```
* Example

Make virtual environment
```
name: create-venv
env: 
venv:
path: $HOME/projects/projectA
exec: python3
args: ['-m', 'venv', '.venv']
```

Train a model
```
name: resnet18
env:
  CUDA_VISIBLE_DEVICES: "0"
venv: $HOME/projects/projectA/.venv
path: $HOME/projects/projectA/
exec: python3
args: ['train.py', 'option=train/resnet18.yaml']
```

### Command in Master Node
* Submit a job: `tiny submit <WORKER IP> job.yaml`
* Show list of jobs: `tiny list <WORKER IP>`
* Show logs of a job: `tiny logs <WORKER IP> job_name`
* Stop a job: `tiny logs <WORKER IP> job_name`
* Prune stopped jobs and logs: `tiny prune <WORKER IP>`
* Restart worker node: `ssh <USER>@<WORKER IP> docker restart <container name>`
