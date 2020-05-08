# Safety-cv-2: Services

(Only tested on: Linux Mint 19.1 Tessa, Python 3.6.7)

## Requirements

Each service has independent requirements. For python-based services, these can be installed using:

`pip3 install -r requirements.txt`

This should be called from within the folder of each of the services themselves.

## Modifying Environment Variables

Many services will have environment variables that can be used to alter the behaviour of the service. These can be overriden when running the container by adding either of the following formatted entries to the container run commands:

 `--env VARNAME='VALUE'` 

 `-e VARNAME='VALUE'` 

See each of the listed services and their corresponding environment variables for more info. Note that these entries can't just be added to the end of the run commands. A good place for them is after the `-d` flag, usually found in every run command.



---

## autodelete

A script for automatically deleting files off of the database on a regular (daily) interval.

#### Build:

From outside the autodelete folder (i.e. the same location as this README file):

`sudo docker build -t autodelete_image -f ./autodelete/build/docker/Dockerfile ./autodelete``

This command will create a docker image (called `autodelete_image`) with all dependencies installed. Note that this image requires the pybase image (currently located in the deployment repo!)

#### Run:

From anywhere:

`sudo docker run -d --network="host" --name autodelete_container autodelete_image`

This command will start up the autodeletion container. Note that the dbserver container should be running before starting the autodeletion container, as it will attempt to connect to the dbserver on startup (and close immediately if it fails!).

#### Environment variables:

`DBSERVER_HOST` = localhost

`DBSERVER_PORT` = 8050

`DAYS_TO_KEEP` = 5

`DELETE_ON_STARTUP` = 0 (False)

`DELETE_ONCE` = 0 (False)

---

## classifier

(to be completed)

---

## system_monitor

(to be completed)

---

## sample_capture

(to be completed)

---
