#!/opt/rh/python27/root/usr/bin/python
# OCI - Berametal Database Scaling Script
# Written by: Richard Garsthagen - richard@oc-blog.com
# Version 1.0 - September 6th 2018
#
# More info see: www.oc-blog.com
#

import instanceMetadata
import oci
import json
import datetime
import time
import sys
import logging

logging.basicConfig(filename="~/autoscale.log", format='%(asctime)s %(message)s', level=logging.INFO)

# Specify your config file with access to the OCI API credentials
configfile = "~/config"

action = 0

for arg in sys.argv:
  if arg == "up": 
    logging.info ("Check for Scaling up")
    action = 1
  if arg == "down":
    logging.info ("Check for Scaling down")
    action = 2

logging.debug("Action: {}".format(action))

DayOfWeekString = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

md = instanceMetadata.get_metadata()

systemID = md["displayName"]
Region = md["canonicalRegionName"]

config = oci.config.from_file(configfile)
config["region"] = Region

identity = oci.identity.IdentityClient(config)
user = identity.get_user(config["user"]).data
RootCompartmentID = user.compartment_id

logging.info ("Logged in as: {} @ {}".format(user.description, config["region"]))

databaseClient = oci.database.DatabaseClient(config)
DbSystem = oci.database.models.DbSystem()
response = databaseClient.get_db_system(db_system_id = md["displayName"])
DbSystem = response.data

DayOfWeek = datetime.datetime.today().weekday()
Day = DayOfWeekString[DayOfWeek]
logging.info ("Day of week: {}".format(Day))

Schedule = ""

for def_tags in DbSystem.defined_tags:
  if def_tags == "Schedule":
    schedTags = DbSystem.defined_tags["Schedule"]
    try:
      Schedule = schedTags["AnyDay"]
    except:
      logging.debug ("No anyday record")
    if (DayOfWeek < 5):  # Weekday
      try:
        Schedule = schedTags["WeekDay"]
      except:
        logging.debug ("No Weekday record")
    else:  # Weekend
      try:
        Schedule = schedTags["Weekend"]
      except:
        logging.debug ("No Weekend record")
    try:  # Check Day specific record
       Schedule = schedTags[Day]
    except:
       logging.debug ("No day specific record found")

try:
  HourCoreCount = Schedule.split(",")
except:
  HourCoreCount = ""

if (len(HourCoreCount) == 24):  # Check if schedule contains 24 hours.
  CurrentHour = datetime.datetime.now().hour
  logging.info ("Current hour: {}".format(CurrentHour))
  logging.info ("Current Core count:   {}".format(DbSystem.cpu_core_count))
  logging.info ("Scheduled Core count: {}".format(HourCoreCount[CurrentHour]))

  takeAction = False
  if (int(DbSystem.cpu_core_count) < int(HourCoreCount[CurrentHour]) and (action == 0 or action ==1)):
    takeAction = True
  if (int(DbSystem.cpu_core_count) > int(HourCoreCount[CurrentHour]) and (action == 0 or action ==2)):
    takeAction = True

  if (takeAction):
    logging.info ("System needs to rescaling")
    tries = 0
    while (tries < 5): 
      if (DbSystem.lifecycle_state == "AVAILABLE"):
        logging.info ("System is available for re-scaling")
        DbSystemDetails = oci.database.models.UpdateDbSystemDetails(cpu_core_count = int(HourCoreCount[CurrentHour]))
        response = databaseClient.update_db_system(db_system_id = systemID, update_db_system_details = DbSystemDetails)
        #logging.debug (response.data)
        logging.info ("System is re-scaling")
        break
      else:
        logging.debug ("System is not available for scaling... attempt: {}".format(tries))
        time.sleep(60)
        response = databaseClient.get_db_system(db_system_id = systemID)
        DbSystem = response.data
        tries = tries + 1
  else:
    logging.info ("No Action needed")





