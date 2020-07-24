# -----------------------------------------------------------------------------
#%% Base setup

# Start with ubuntu-python base
FROM pacefactory/scv2_ubuntupython_base:1.0.1


# -----------------------------------------------------------------------------
#%% Set environment variables

# Create a 'home' folder path to avoid storing everything in the root fs
ENV HOME                            /home/scv2

# Set variables for accessing the database server
ENV DBSERVER_HOST                   localhost
ENV DBSERVER_PORT                   8050

# Set variables for deletion
ENV DAYS_TO_KEEP                    1
ENV DELETE_ON_STARTUP               0
ENV DELETE_ONCE                     0


# -----------------------------------------------------------------------------
#%% Setup python

# Work with files outside of the root fs
WORKDIR $HOME/autodelete

# Install python requirements
COPY requirements.txt $HOME/autodelete
RUN pip3 install -r $HOME/autodelete/requirements.txt


# -----------------------------------------------------------------------------
#%% Launch!

# Move system files into the image
COPY . .

# Make sure the entrypoint script is executable
RUN chmod +x docker_entrypoint.sh

# Run the autodeletion script! This is a blocking call...
ENTRYPOINT ["./docker_entrypoint.sh"]


# -----------------------------------------------------------------------------
# To use manually:

# From the autodelete root project directory:
# docker build -t services_autodelete_image -f ./build/docker/Dockerfile .
# docker run -d -e DAYS_TO_KEEP=1 --network="host" --name autodelete_container services_autodelete_image

