from flask import Flask, render_template, request, abort, jsonify, url_for, redirect
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
import os, time, json, traceback
import logging, logging.handlers
import random as random
from apscheduler.schedulers.background import BackgroundScheduler
import datetime as dt
import numpy as np
from calendarGmail import *

############## PARAMETERS ###################
# Set if debugging is active
debugSet = False

# Set if the website runs on local network
external = False

# Should emails be sent?
emailFlag = False

# Location for event
eventLocation = 'ADDRESS'
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

# Setup database
db_uri = 'sqlite:///{}'.format(os.path.join(os.path.dirname(__file__), 'chores.db'))
app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)



#### DATABASE CLASSES
# Parent Class
class User(db.Model):
	__tablename__ = 'user'
	id = db.Column(db.Integer, primary_key=True, autoincrement=True)
	name = db.Column(db.String(), unique=False)
	email = db.Column(db.String(), unique=True)
	chores = db.relationship('Chore')
	
# Child Class
class Chore(db.Model):
	__tablename__ = 'chore'
	id = db.Column(db.Integer, primary_key=True, autoincrement=True)
	name = db.Column(db.String(), unique=True)
	frequency = db.Column(db.Integer, unique=False)
	complete = db.Column(db.Boolean, unique=False)
	user_id = db.Column(db.Integer, ForeignKey('user.id'))

# Create all
db.create_all()


	
#####################################################
# SETUP THE CHORE FUNCTION CALLS
	  
def initialAssign():
	# Get length of lists
	usersLen = db.session.query(User).count()
	choreLen = db.session.query(Chore).count()
	
	# Make sure neither list is empty
	if(usersLen > 0 and choreLen > 0):
		# Go through each chore and assign a user to it
		i = 0
		for chore in db.session.query(Chore).all():
			chore.
		
	else:
		logger.warning('Empty chore list or user list')
		
	# Reset completion chart
	for chore in db.session.query(Chore).all():
		chore.complete = False
	db.session.commit()
	
	logger.info('Reset completion')
	
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
	global assignment # Get the global assignment, user list, and chores list
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
	global assignment # Get all global variables
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
	return render_template('index.html', tableValues=assignment, warnings=warnings, endDate=endDate)

	
# When the user completes a chore
@socketio.on('chorecomplete', namespace='/chore')
def choreComplete(chore):
	try:
		chore = db.session.query(Chore).filter(Chore.name == chore)
		chore.complete = True
	except:
		logger.error(traceback.print_exc())
	

### Server error handling	
# Load a simple page on 404 error which directs user back to safety at home page
@app.errorhandler(404)
def errorHandle(e):
	if('socket.io' not in request.url and 'favicon' not in request.url):
		logger.warning('User attempted to navigate to ' + str(request.url))
	return render_template('404.html')

@socketio.on_error()
def error_handler(e):
	logger.critical('Socket IO Error')
	logger.critical(traceback.print_exc())
	logger.critical(e)

@socketio.on_error_default
def default_error_handler(e):
	logger.critical('Socket IO Error')
	logger.critical(traceback.print_exc())
	logger.critical(e)
	
	
# Define a maintenance/setup page
@app.route('/setup', methods=['POST', 'GET'])
def setup():
	global assignment # Get global chores list and users list
	message = '' # Reset message field
	changeFlag = 0
	if request.method == 'POST':
		logger.debug('Data received: ' + str(request.data))
		if 'addChore' in request.form:
			changeFlag = 1
			addValue = request.form['addvalue']
			if(addValue != ''):
				logger.warning('Adding chore: ' + str(addValue))
				chore = Chore(name=addValue, frequency=0, complete=False)
				db.session.add(chore)
				db.session.commit()
				message = 'Added ' + str(addValue) + ' to list'
			
		elif 'removeChore' in request.form:
			changeFlag = 1
			removeValue = request.form['removevalue']
			logger.warning('Removing chore: ' + str(removeValue))
			try:
				db.session.query(Chore).filter(Chore.name == removeValue).remove()
				message = 'Removed ' + str(removeValue) + ' from list'
			except:
				logger.error('Could not remove chore, does not exist')
				message = 'WARNING: Could not remove item, item does not exist'
				
		elif 'addUser' in request.form:
			changeFlag = 1
			addValue = request.form['addUserValue']
			emailValue = request.form['userEmail']
			if(addValue != ''):
				logger.warning('Adding user: ' + str(addValue))
				user = User(name=addValue, email=emailValue)
				db.session.add(user)
				db.session.commit()
				message = 'Added ' + str(addValue) + ' from list'
				
		elif 'removeUser' in request.form:
			changeFlag = 1
			removeValue = request.form['removeUserValue']
			logger.warning('Removing user: ' + str(removeValue))
			try:
				db.session.query(User).filter(User.name == removeValue).remove()
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
				db.session.query(User).all().remove()
				db.session.query(Chore).all().remove()
				logger.warning('All data cleared')
			else:
				logger.warning('Type "clear" to confirm and repress')
			
		if(changeFlag):
			pass
			#random.shuffle()
			#initialAssign() # If any change has been made the chores need to be re-assigned
				
	try:
		nextrun = s.get_jobs()[0].next_run_time
	except Exception as e:
		nextrun = "Couldn't get next runtime " + e
	
	chores = db.session.query(Chore.name).all()
	users = db.session.query(User.name).all()
	emails = db.session.query(User.email).all()
	return render_template('setup.html', chores=chores, message=message, users=users, assignment=assignment, nextrun=nextrun, emails=emails)


# Run the application
if __name__ == '__main__':
	if(not external):
		socketio.run(app, debug=debugSet)
	else:
		socketio.run(app, debug=debugSet, host='0.0.0.0') 