# -----------------------------------------------------------------------------
#%% Base setup

# Start with ubuntu-python base
FROM pacefactory/scv2_ubuntupython_base:1.0.0


# -----------------------------------------------------------------------------
#%% Install system requirements

# Update repo records & install GIF making utility
RUN apt-get update && \
    apt-get install --quiet --assume-yes --no-install-recommends \
    imagemagick


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

# Set variables for default gif making behavior
ENV DEFAULT_DELAY_MS                150
ENV DEFAULT_MAX_FRAME_SIZE_PX       480


# -----------------------------------------------------------------------------
#%% Setup python

# Work with files outside of the root fs
WORKDIR $HOME/gifwrapper

# Install python requirements
COPY requirements.txt $HOME/gifwrapper
RUN pip3 install -r $HOME/gifwrapper/requirements.txt


# -----------------------------------------------------------------------------
#%% Launch!

# Move system files into the image
COPY . .

# Run the gif making server script! This is a blocking call...
ENTRYPOINT ["sh", "docker_entrypoint.sh"]


# -----------------------------------------------------------------------------
# To use manually:

# From the gifwrapper project root directory:
# sudo docker build -t services_gifwrapper_image -f ./build/docker/Dockerfile .
# sudo docker run -d --network="host" --name services_gifwrapper services_gifwrapper_image

