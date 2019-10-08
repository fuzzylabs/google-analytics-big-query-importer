import os
import pprint
from argparse import ArgumentParser
from apiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

SCOPES = ['https://www.googleapis.com/auth/analytics.readonly']
KEY_FILE_LOCATION = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

pp = pprint.PrettyPrinter(indent=2)

def initializeAnalyticsReporting():
  credentials = ServiceAccountCredentials.from_json_keyfile_name(KEY_FILE_LOCATION, SCOPES)
  analytics = build('analyticsreporting', 'v4', credentials=credentials)
  return analytics

def getSessionsByClientId(analytics, viewId, dateRange):
  return analytics.reports().batchGet(
      body={
        'reportRequests': [
        {
          'viewId': viewId,
          'dateRanges': [dateRange],
          'metrics': [{'expression': 'ga:sessions'}],
          'dimensions': [{'name': 'ga:clientId'}]
        }]
      }
  ).execute()

def getUserActivity(analytics, viewId, userId, dateRange):
  return analytics.userActivity().search(
    body={
      "dateRange": dateRange,
      "viewId": viewId,
      "user": {'type': 'CLIENT_ID', 'userId': userId}
    }
  ).execute()

def extractClientIds(response):
  clientIds = []
  for report in response.get('reports', []):
    columnHeader = report.get('columnHeader', {})
    dimensionHeaders = columnHeader.get('dimensions', [])
    metricHeaders = columnHeader.get('metricHeader', {}).get('metricHeaderEntries', [])
    for row in report.get('data', {}).get('rows', []):
      dimensions = row.get('dimensions', [])
      for header, dimension in zip(dimensionHeaders, dimensions):
        if header == 'ga:clientId':
          clientIds.append(dimension)
  return clientIds

def extractActivities(response):
  activities = []

  for session in response.get('sessions', []):
    for activity in session.get('activities', []):
      activities.append(activity)
  return activities

def main(viewId, dateRange):
  analytics = initializeAnalyticsReporting()
  sessions = getSessionsByClientId(analytics, viewId, dateRange)
  clientIds = extractClientIds(sessions)

  for clientId in clientIds:
    activity = getUserActivity(analytics, viewId, clientId, dateRange)
    print("Client: " + clientId)
    print("-------------------")
    pp.pprint(extractActivities(activity))

if __name__ == '__main__':
  parser = ArgumentParser()
  parser.add_argument("-v", "--view", dest="viewId", help="Get analytics from view ID", required=True)
  args = parser.parse_args()
  main(args.viewId, {'startDate': '7daysAgo', 'endDate': 'today'})
