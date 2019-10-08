import os
from argparse import ArgumentParser
from apiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

SCOPES = ['https://www.googleapis.com/auth/analytics.readonly']
KEY_FILE_LOCATION = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

def initializeAnalyticsReporting():
  credentials = ServiceAccountCredentials.from_json_keyfile_name(KEY_FILE_LOCATION, SCOPES)
  analytics = build('analyticsreporting', 'v4', credentials=credentials)
  return analytics

def getSessionsByClientId(analytics, viewId):
  return analytics.reports().batchGet(
      body={
        'reportRequests': [
        {
          'viewId': viewId,
          'dateRanges': [{'startDate': '7daysAgo', 'endDate': 'today'}],
          'metrics': [{'expression': 'ga:sessions'}],
          'dimensions': [{'name': 'ga:clientId'}]
        }]
      }
  ).execute()

def printReport(response):
  for report in response.get('reports', []):
    columnHeader = report.get('columnHeader', {})
    dimensionHeaders = columnHeader.get('dimensions', [])
    metricHeaders = columnHeader.get('metricHeader', {}).get('metricHeaderEntries', [])

    for row in report.get('data', {}).get('rows', []):
      dimensions = row.get('dimensions', [])
      dateRangeValues = row.get('metrics', [])

      for header, dimension in zip(dimensionHeaders, dimensions):
        print header + ': ' + dimension

      for i, values in enumerate(dateRangeValues):
        print 'Date range: ' + str(i)
        for metricHeader, value in zip(metricHeaders, values.get('values')):
          print metricHeader.get('name') + ': ' + value

def main(viewId):
  analytics = initializeAnalyticsReporting()
  response = getSessionsByClientId(analytics, viewId)
  printReport(response)

if __name__ == '__main__':
  parser = ArgumentParser()
  parser.add_argument("-v", "--view", dest="viewId", help="Get analytics from view ID", required=True)
  args = parser.parse_args()
  main(args.viewId)
