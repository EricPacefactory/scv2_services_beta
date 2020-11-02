# -----------------------------------------------------------------------------
#%% Base setup

# Start with Open-CV base
FROM pacefactory/scv2_opencv_base:1.0.1


# -----------------------------------------------------------------------------
#%% Setup python requirements

# Install python requirements
COPY requirements.txt /tmp/scv2/requirements.txt
RUN python3 -m pip install --upgrade pip && \
    python3 -m pip install -r /tmp/scv2/requirements.txt


# -----------------------------------------------------------------------------
#%% Set environment variables

# Create a 'home' folder path to avoid storing everything in the root fs
ENV HOME                            /home/scv2

# Set variables for setting up the gif making server
ENV GIFSERVER_HOST                  0.0.0.0
ENV GIFSERVER_PORT                  7171

# Set variables for accessing the database server
ENV DBSERVER_HOST                   localhost
ENV DBSERVER_PORT                   8050

# Set variables for default animation output
ENV DEFAULT_FPS                     8


# -----------------------------------------------------------------------------
#%% Launch!

# Work with files outside of the root fs
WORKDIR $HOME/gifwrapper

# Move system files into the image
COPY . .

# Make sure the entrypoint script is executable
RUN chmod +x docker_entrypoint.sh

# Run the gif making server script! This is a blocking call...
ENTRYPOINT ["./docker_entrypoint.sh"]


# -----------------------------------------------------------------------------
# To use manually:

# From the gifwrapper root project directory:
# docker build -t services_gifwrapper_image -f ./build/docker/Dockerfile .
# docker run -d --network="host" --name services_gifwrapper services_gifwrapper_image

