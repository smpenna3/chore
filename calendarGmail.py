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

def insertEvent(title, timeToRun, email):
    logger.info("Event received <Title: " + str(title) + ", Runtime: " + str(timeToRun) + ", Email: " + str(email) + ">")

    if(timeToRun == 'sunday'): 
        check = 0
    elif(timeToRun == 'monday'):
        check = 1   
    elif(timeToRun == 'tueday'):
        check = 2
    elif(timeToRun == 'wednesday'):
        check = 3
    elif(timeToRun == 'thursday'):
        check = 4
    elif(timeToRun == 'friday'):
        check = 5
    elif(timeToRun == 'saturday'):
        check = 6

    # Find the next date 
    d = datetime.datetime.now()
    while d.strftime('%w') != str(check):
        logger.debug(d.strftime('%w'))
        d+=datetime.timedelta(1)

    dateToRun = d.strftime('%Y-%m-%d')

    """Shows basic usage of the Google Calendar API.

    Creates a Google Calendar API service object and outputs a list of the next
    10 events on the user's calendar.
    """
    try:
        credentials = get_credentials()
        http = credentials.authorize(httplib2.Http())
        service = discovery.build('calendar', 'v3', http=http)
    except:
        return 2

    event = {
      'summary': title,
      'location': 'Team HQ',
      'description': 'Time to do your chores!',
      'start': {
        'date': dateToRun,
        'timeZone': 'America/New_York',
      },
      'end': {
        'date': dateToRun,
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
    except:
        return 3
    return 0