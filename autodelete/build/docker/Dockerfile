# -----------------------------------------------------------------------------
#%% Base setup

# Start with ubuntu-python base
FROM pacefactory/scv2_ubuntupython_base:1.0.0


# -----------------------------------------------------------------------------
#%% Set environment variables

# Create a 'home' folder path to avoid storing everything in the root fs
ENV HOME                            /home/scv2

# Set variables for accessing the database server
ENV DBSERVER_HOST                   localhost
ENV DBSERVER_PORT                   8050

# Set variables for deletion
ENV DAYS_TO_KEEP                    5
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

# Run the autodeletion script! This is a blocking call...
CMD ["python3", "-u", "autodelete.py"]


# -----------------------------------------------------------------------------
# To use manually:

# From outside autodelete project directory:
# sudo docker build -t autodelete_image -f ./autodelete/build/docker/Dockerfile ./autodelete
# sudo docker run -d --network="host" --name autodelete_container autodelete_image

