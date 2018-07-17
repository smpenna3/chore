from flask import *
import os
import logging
import time
import random as random
from apscheduler.schedulers.background import BackgroundScheduler
import json
import datetime as dt
import traceback
import numpy as np

############## PARAMETERS ###################
# Set if debugging is active
debugSet = False

# Set if the website runs on local network
external = False
#############################################
#############################################

# Setup logging
formatter = ('%(asctime)s - [%(levelname)7s]. - %(message)s')
logger = logging.getLogger('mainlog')
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(logging.StreamHandler())

# Setup scheduler
s = BackgroundScheduler(coalescing=True, misfire_grace_time=5, max_instances=1, timezone='America/New_York')
s.start()
logger.info('Scheduler setup')

# Setup Flask
app = Flask(__name__)

# Setup global variable to hold chores and users
global chores
global users
usersFileName = 'users.npy'
choresFileName = 'chores.npy'
if os.path.isfile(choresFileName): 
    chores = list(np.load(choresFileName))
    logger.warning('Using existing chores file')
else:
    chores = []
    np.save(choresFileName, np.array(chores))
    logger.warning('Creating blank chores file')
    
if os.path.isfile(usersFileName): 
    users = list(np.load(usersFileName))
    logger.warning('Using existing users file')
else:
    users = []
    np.save(usersFileName, np.array(users))
    logger.warning('Creating blank users file')

    
#####################################################
# Define a function to set the chores 
# Each user is the key to a dictionary
# Each value is a list with their chores
global choresDict 

assignmentFileName = 'assignment.npy'
if os.path.isfile(assignmentFileName): 
    assignment = np.load(assignmentFileName).item()
    logger.warning('Using existing assignments file')
else:
    assignment = {}
    np.save(assignmentFileName, np.array(assignment))
    logger.warning('Creating blank assignments file')
       
def initialAssign():
    global users, chores, assignment # Get the global users and chores lists
    assignment = {} # Reset since it is being written from scratch
    numUsers = len(users) # Find how many users there are
    
    # Create an array for each user in the assignments dictionary
    for user in users:
        assignment[user] = []
    
    # Fill the arrays with the chores
    i = 0
    for chore in chores:
        assignment[users[i]].append(chore)
        i = i + 1
        if(i >= numUsers):
            i = 0
            
    logger.debug(assignment)
    return assignment

def rotateAssign():
    global assignment, users, chores # Get the global assignment, user list, and chores list
    
    
    
    return assignment
    
    
    
##########################################################
# Setup the web server
# A landing page serves the usual use cases
# The setup page is just for adding chores and users

# Define a landing page
@app.route('/', methods=['POST', 'GET'])
def home():
    global assignment, users, chores # Get all global variables
    warnings = ''
    
    if(assignment == {}):
        logger.warning('No chores have been assigned yet')
        warnings = 'No chores have been assigned, contact Admin'
    
    # Return the table
    return render_template('index.html', tableValues=assignment, warnings=warnings)

# Define a maintenance/setup page
@app.route('/setup', methods=['POST', 'GET'])
def setup():
    global chores, users, assignment # Get global chores list and users list
    message = '' # Reset message field
    changeFlag = 0
    if request.method == 'POST':
        logger.debug('Data received: ' + str(request.data))
        if 'addChore' in request.form:
            changeFlag = 1
            addValue = request.form['addvalue']
            if(addValue != '' and addValue not in chores):
                logger.warning('Adding chore: ' + str(addValue))
                chores.append(addValue)
                np.save(choresFileName, np.array(chores))
                message = 'Added ' + str(addValue) + ' to list'
            
        elif 'removeChore' in request.form:
            changeFlag = 1
            removeValue = request.form['removevalue']
            logger.warning('Removing chore: ' + str(removeValue))
            try:
                chores.remove(removeValue)
                np.save(choresFileName, np.array(chores))
                message = 'Removed ' + str(removeValue) + ' from list'
            except:
                logger.error('Could not remove chore, does not exist')
                message = 'WARNING: Could not remove item, item does not exist'
                
        elif 'addUser' in request.form:
            changeFlag = 1
            addValue = request.form['addUserValue']
            if(addValue != '' and addValue not in users):
                logger.warning('Adding user: ' + str(addValue))
                users.append(addValue)
                np.save(usersFileName, np.array(users))
                message = 'Added ' + str(addValue) + ' from list'
                
        elif 'removeUser' in request.form:
            changeFlag = 1
            removeValue = request.form['removeUserValue']
            logger.warning('Removing user: ' + str(removeValue))
            try:
                users.remove(removeValue)
                np.save(usersFileName, np.array(users))
                message = 'Removed ' + str(removeValue) + ' from list'
            except:
                logger.error('Could not remove user, does not exist')
                message = 'WARNING: Could not remove item, item does not exist'
                
        elif 'assign' in request.form:
            initialAssign()
            
        if(changeFlag):
            random.shuffle(chores)
            #logger.debug(chores)
            initialAssign() # If any change has been made the chores need to be re-assigned
                
    
    return render_template('setup.html', chores=chores, message=message, users=users, assignment=assignment)


# Run the application
if __name__ == '__main__':
    if(not external):
        app.run(debug=debugSet)
    else:
        app.run(debug=debugSet, host='0.0.0.0') 