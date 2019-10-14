import os
import pprint
from argparse import ArgumentParser
from apiclient.discovery import build
from google.cloud import bigquery
from oauth2client.service_account import ServiceAccountCredentials

SCOPES = ['https://www.googleapis.com/auth/analytics.readonly']
KEY_FILE_LOCATION = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

pp = pprint.PrettyPrinter(indent=2)
bq = bigquery.Client()

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

def generateInserts(clientId, activities):
  inserts = []
  for activity in activities:
    inserts.append(f"""(
    "{clientId}",
    "{activity['activityTime']}",
    "{activity['activityType']}",
    "{activity['campaign']}",
    "{activity['channelGrouping']}",
    "{activity['hostname']}",
    "{activity['keyword']}",
    "{activity['landingPagePath']}",
    "{activity['medium']}",
    ["{activity['pageview']['pagePath']}"],
    "{activity['source']}")
    """)
  return inserts

def createTable(table):
  query = f"""CREATE TABLE `{table}` (
  client_id STRING NOT NULL,
  activity_time STRING,
  activity_type STRING,
  campaign STRING,
  channel_grouping STRING,
  hostname STRING,
  keyword STRING,
  landing_page STRING,
  medium STRING,
  page_view ARRAY<STRING>,
  source STRING)
  """
  r = bq.query(query)
  print(r.result())

def main(viewId, table, dateRange):
  analytics = initializeAnalyticsReporting()
  sessions = getSessionsByClientId(analytics, viewId, dateRange)
  clientIds = extractClientIds(sessions)

  print(f"Creating table {table}")
  createTable(table)

  inserts = []
  for clientId in clientIds:
    activities = extractActivities(getUserActivity(analytics, viewId, clientId, dateRange))
    print("Client: " + clientId)
    print("-------------------")
    pp.pprint(activities)
    inserts.extend(generateInserts(clientId, activities))
  print("Inserting data into BigQuery")
  queryJob = bq.query("INSERT INTO `" + table + "` values " + ",".join(inserts))
  results = queryJob.result()

if __name__ == '__main__':
  parser = ArgumentParser()
  parser.add_argument("-v", "--view", dest="viewId", help="Get analytics from view ID", required=True)
  parser.add_argument("-t", "--table", dest="table", help="The destination table in which to save the analytics data, using a fully-qualified path of the form <organisation>.<dataset>.<table-name>. This table will be created and should not already exist", required=True)
  args = parser.parse_args()
  main(args.viewId, args.table, {'startDate': '7daysAgo', 'endDate': 'today'})
