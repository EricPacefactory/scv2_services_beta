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

#### Docker Build:

From inside the autodelete folder:

`docker build -t services_autodelete_image -f ./build/docker/Dockerfile .`

This command will create a docker image (called `services_autodelete_image`) with all dependencies installed.

#### Docker Run:

From anywhere:

`docker run -d --network="host" --name services_autodelete services_autodelete_image`

This command will start up a container running the autodelete service. Note that the dbserver container should be running before starting the autodeletion container, as it will attempt to connect to the dbserver on startup (and close immediately if it fails!).

#### Environment variables:

`DBSERVER_PROTOCOL` = http

`DBSERVER_HOST` = localhost

`DBSERVER_PORT` = 8050

`DAYS_TO_KEEP` = 5

`DELETE_ON_STARTUP` = 0 (False)

`DELETE_ONCE` = 0 (False)

---

## gifwrapper

A script for generating GIF files. Provides a simple set of urls to specify GIF request.

Docker Build:

From inside the gifwrapper folder:

`docker build -t services_gifwrapper_image -f ./build/docker/Dockerfile .`

This command will create a docker image (called `services_gifwrapper_image`) with all dependencies installed.

#### Docker Run:

From anywhere:

`docker run -d --network="host" --name services_gifwrapper services_gifwrapper_image`

This command will start up a container running the gifwrapper service. Note that the dbserver container should be running before starting the gifwrapper container, as it will attempt to connect to the dbserver on startup (and close immediately if it fails!).

#### Environment variables:

`GIFSERVER_PROTOCOL` = http

`GIFSERVER_HOST` = 0.0.0.0

`GIFSERVER_PORT` = 7171

`DBSERVER_PROTOCOL` = http

`DBSERVER_HOST` = localhost

`DBSERVER_PORT` = 8050

`DEFAULT_DELAY_MS` = 150

`DEFAULT_MAX_FRAME_SIZE_PX` = 480

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
