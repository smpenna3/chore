from __future__ import print_function
import httplib2
import os
import logging

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

import datetime
import time


logger = logging.getLogger('mainlog')

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/calendar-python-quickstart.json

SCOPES = 'https://www.googleapis.com/auth/calendar'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Google Calendar API Python Quickstart'


def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'calendar-python-quickstart.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials


def insertEvent(title, weekday, email, location):
    # Get the account credentials from the JSON file
    try:
        credentials = get_credentials()
        http = credentials.authorize(httplib2.Http())
        service = discovery.build('calendar', 'v3', http=http)
    except:
        logger.error('ERROR: Could not find credentials')
        return 2
    
    # Determine the start and end dates from the weekday given
    # Need to look for the next date of that weekday
    if(weekday == 5):
        # Sun-Wed
        logger.info('Emailing new assignments for Sun-Wed')
        checkStart = 0
        checkEnd = 3
        
    elif(weekday == 2):
        # Thur-Sat
        logger.info('Emailing new assignments for Thu-Sat')
        checkStart = 4
        checkEnd = 0
    
    else:
        logger.error('Weekday not recognized: ' + str(weekday))
        
    # Find start date
    start = datetime.datetime.now()
    while start.strftime('%w') != str(checkStart):
        start += datetime.timedelta(1)
    startDate = start.strftime('%Y-%m-%d')
    logger.debug('Start Date ' + str(startDate))
    
    # Find end date
    end = datetime.datetime.now()
    while ((end.strftime('%w') != str(checkEnd)) or (start > end)):
        end += datetime.timedelta(1)
    endDate = end.strftime('%Y-%m-%d')
    logger.debug('End Date ' + str(endDate))
    
    logger.debug(start > end)
        
    event = {
      'summary': title,
      'location': location,
      'description': 'Time to do your chores!',
      'start': {
        'date': startDate,
        'timeZone': 'America/New_York',
      },
      'end': {
        'date': endDate,
        'timeZone': 'America/New_York',
      },
      'attendees': [
        {'email': email},
      ],
      'reminders': {
        'useDefault': False,
        'overrides': [
          {'method': 'popup', 'minutes': 30},
          {'method': 'popup', 'minutes': 60},
        ],
      },
    }
    try:
        event = service.events().insert(calendarId='primary', sendNotifications=True, body=event).execute()
    except Exception as e:
        logger.error('ERROR: Could not add calendar event: ' + str(e))
        return 3
    logger.info('Setup event and sent email')
    return 0