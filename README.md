# Safety-cv-2: Services

(Only tested on: Linux Mint 19.1 Tessa, Python 3.6.7)

## Purpose

This repo contains code for running the *gifwrapper* service, which when running, provides a server that can generate animation files for download.

## Requirements

To manually install python requirements, use:

`pip3 install -r requirements.txt`

This should be called from the root porject folder (where the requirements file is located).

Note that this is done automatically when building/running for deployment with docker, but may be useful if running the service 'natively' (i.e. outside of docker).

## Deployment

This service is expected to be run as a docker container (alongside other safety-cv-2 containers). The instructions below explain how to (manually) build and run the container.

##### Build image

To build the docker image, use the **build_image.sh** script, which can be found in the folder (relative to the root project folder):

`build/docker/build_image.sh`

This script will prompt to perform a 'git pull' operation. If agreed to, this has the effect of building the image using the newest available source code.

Note that the git pull operation only works if an internet connection is available! The rest of the build script may also require an internet connection if prerequiste image data isn't already available.

#### Run container

To run the docker image (built using the steps above), use the **run_container.sh** script, which can be found in the folder (relative to the root project folder):

`build/docker/run_container.sh`

This script will prompt to enable auto-restart on the container. This should only be declined if running the container in a development environment.

Note that this script does not require an internet connection, assuming the image has already been successfully built.

Also note that environment variables can be overridden by providing them as additional arguments to the run script. For example, the server port can be changed to 1234 by using the run script as follows:

`build/docker/run_container.sh GIFSERVER_PORT=1234`

---

### TODOs

- re-implement gif formatted outputs
