from flask import Flask, render_template, request, abort, jsonify, url_for, redirect
from flask_socketio import SocketIO
import os, time, json, traceback
import logging, logging.handlers
import random as random
from apscheduler.schedulers.background import BackgroundScheduler
import datetime as dt
import numpy as np
from calendarGmail import *

############## PARAMETERS ###################
# Set if debugging is active
debugSet = True

# Set if the website runs on local network
external = False

# Should emails be sent?
emailFlag = True

# Location for event
eventLocation = '45 Westland Ave'
#############################################
#############################################

# Setup logging
formatter = logging.Formatter('%(asctime)s - [%(levelname)7s]. - %(message)s')
logger = logging.getLogger('mainlog')
logger.setLevel(logging.DEBUG)
fh = logging.handlers.RotatingFileHandler('log.log', maxBytes=5*1024*1024, backupCount=10)
fh.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.addHandler(fh)

# Get flask logger
flaskLogger = logging.getLogger('werkzeug')
flaskLogger.setLevel(logging.WARNING)
flaskLogger.addHandler(fh)

# Setup Flask
app = Flask(__name__)
socketio = SocketIO(app, async_mode='threading')

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
# SETUP THE CHORE FUNCTION CALLS
# Define a function to set the chores 
# Each user is the key to a dictionary
# Each value is a list with their chores
global assignment 
global choreCompletion
choreCompletion = {}

assignmentFileName = 'assignment.npy'
if os.path.isfile(assignmentFileName): 
	assignment = np.load(assignmentFileName).item()
	logger.warning('Using existing assignments file')
	logger.debug(assignment)
	# Reset completion chart
	for key,value in assignment.items():
		choreCompletion[key] = False
	logger.info('Reset completion')
else:
	assignment = {}
	np.save(assignmentFileName, assignment)
	logger.warning('Creating blank assignments file')
	   
def initialAssign():
	global users, chores, assignment, choreCompletion  # Get the global users and chores lists
	assignment = {} # Reset since it is being written from scratch
	numUsers = len(users) # Find how many users there are
	numChores = len(chores) # Find how many chores there are
	
	if(numUsers > 0 and numChores > 0):
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

		#logger.debug(assignment)
		np.save(assignmentFileName, assignment)
	else:
		logger.warning('Empty chore list or user list')
		
	# Reset completion chart
	for key,value in assignment.items():
		choreCompletion[key] = False
	logger.info('Reset completion')

global emails
emailsFileName = 'emails.npy'
if os.path.isfile(emailsFileName): 
	emails = np.load(emailsFileName).item()
	logger.warning('Using existing emails file')
	logger.debug(emails)
else:
	emails = {}
	np.save(emailsFileName, np.array(emails))
	logger.warning('Creating blank emails file')
	
def emailAssignments():  
	if(emailFlag):
		global assignment, users, chores, emails # Get global variables
		# Get the current weekday
		# Monday is 0, Sunday is 6
		weekday = dt.datetime.today().weekday()

		# Loop through the assignments dictionary and email each person with their chores
		for key, value in assignment.items():
			try:
				userEmail = emails[key]
				logger.debug('key ' + str(key))
				logger.debug('value ' + str(value))
				insertEvent(str(value), weekday, userEmail, eventLocation)
			except Exception as e:
				logger.warning('No email for user ' + str(key))
	
		logger.info('Updated assignments: ' + str(assignment))
		
		
def rotateAssign():
	global assignment, users, chores, choreCompletion # Get the global assignment, user list, and chores list
	numUsers = len(users) # Find how many users there are
	
	if(assignment != {}):
		# Make a temp list of lists of chores for each user
		tmplist = []
		for user in users:
			tmplist.append(assignment[user])

		# Push to the next user in the list
		i = 1
		for user in users:
			assignment[user] = tmplist[i]
			i = i + 1
			if(i >= numUsers):
				i = 0
	
	else:
		# If the assignment dictionary is empty we need to do an initial assign
		initialAssign()
		logger.warning('Assignments not set yet, setting initial assignments')
	
	# Send out the assignments to everyone with an email
	emailAssignments()
	
	# Save assignments to file in case of program crash
	np.save(assignmentFileName, assignment)
	
	# Reset completion chart
	for key,value in assignment.items():
		choreCompletion[key] = False
	logger.info('Reset completion')
	
	
###########################################################
# SETUP THE SCHEDULER
# Should run every 
# Setup scheduler
s = BackgroundScheduler(coalescing=True, misfire_grace_time=5, max_instances=1, timezone='America/New_York')
s.start()
logger.info('Scheduler setup')  

# Run the rotation on Wed and Sat night at 11:55PM
s.add_job(rotateAssign, 'cron', id='rotation', day_of_week='wed,sat', hour='23', minute='0')

	
##########################################################
# SETUP THE WEB SERVER
# A landing page serves the usual use cases
# The setup page is just for adding chores and users
# Socketio call for when chore is complete

# Define a landing page
@app.route('/', methods=['POST', 'GET'])
def home():
	global assignment, users, chores, choreCompletion # Get all global variables
	warnings = ''
	
	# Find which day the current assignments are due
	weekday = dt.datetime.today().weekday()
	if(weekday < 2):
		endDate = 'Wednesday'
	else:
		endDate = 'Sunday'
	
	# Check if chores have been assigned
	if(assignment == {}):
		logger.warning('No chores have been assigned yet')
		warnings = 'No chores have been assigned, contact Seth'
		return render_template('index.html', tableValues=assignment, warnings=warnings, endDate=endDate)
	
	# Return the table
	return render_template('index.html', tableValues=assignment, warnings=warnings, endDate=endDate, completion=choreCompletion)

	
# When the user completes a chore
@socketio.on('chorecomplete', namespace='/chore')
def choreComplete(chore):
	global choreCompletion
	try:
		choreCompletion[chore] = True
		logger.info('Chore ' + str(chore) + ' complete!')
		socketio.emit('update', namespace='/chore')
	except:
		logger.error("Couldn't complete chore " + str(chore))
		logger.error(traceback.print_exc())
	
	
# Load a simple page on 404 error which directs user back to safety at home page
@app.errorhandler(404)
def errorHandle(e):
	if('socket.io' not in request.url and 'favicon' not in request.url):
		logger.warning('User attempted to navigate to ' + str(request.url))
	return render_template('404.html')

	
# Define a maintenance/setup page
@app.route('/setup', methods=['POST', 'GET'])
def setup():
	global chores, users, assignment, emails # Get global chores list and users list
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
			emailValue = request.form['userEmail']
			if(addValue != '' and addValue not in users):
				logger.warning('Adding user: ' + str(addValue))
				users.append(addValue)
				emails[addValue] = str(emailValue)
				np.save(emailsFileName, emails)
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
			logger.info('Initialization requested')
			initialAssign()
			
		elif 'rotate' in request.form:
			logger.info('Rotate requested')
			rotateAssign()
			#logger.debug(assignment)
			
		elif 'email' in request.form:
			logger.info('Email reuqested')
			emailAssignments()
			
		elif 'clear' in request.form:
			if(request.form['clearConfirm'] == 'clear'):
				users = []
				chores = []
				assignment = {}
				emails = {}
				np.save(usersFileName, np.array(users))
				np.save(choresFileName, np.array(chores))
				np.save(assignmentFileName, assignment)
				np.save(emailsFileName, emails)
				logger.warning('All data cleared')
			else:
				logger.warning('Type "clear" to confirm and repress')
			
		if(changeFlag):
			random.shuffle(chores)
			#logger.debug(chores)
			initialAssign() # If any change has been made the chores need to be re-assigned
				
	try:
		nextrun = s.get_jobs()[0].next_run_time
	except Exception as e:
		nextrun = "Couldn't get next runtime " + e
	
	return render_template('setup.html', chores=chores, message=message, users=users, assignment=assignment, nextrun=nextrun, emails=emails)


# Run the application
if __name__ == '__main__':
	if(not external):
		socketio.run(app, debug=debugSet)
	else:
		socketio.run(app, debug=debugSet, host='0.0.0.0') 