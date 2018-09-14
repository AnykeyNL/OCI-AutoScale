#!/opt/rh/python27/root/usr/bin/python
# OCI - ADW and ATP Scheduled Auto Scaling
# Written by: Richard Garsthagen - richard@oc-blog.com
# Version 1.0 - September 14th 2018
#
# More info see: www.oc-blog.com
#
import oci
import json
import logging
import datetime
import time
import sys

# Script configuation ###################################################################################

configfile = "c:\\oci\\config"  # Define config file to be used. 

# #######################################################################################################

def ScaleInstances(instances):
  Schedule = ""
  for instance in instances:
    logging.debug(instance)
    for def_tags in instance.defined_tags:
      logging.debug(def_tags)
      if (def_tags == "Schedule"):
        logging.debug ("Schedule tags found for instance " + instance.display_name)
        schedTags = instance.defined_tags["Schedule"]
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

        logging.debug ("Schedule is: " + Schedule)

        try:
          HourCoreCount = Schedule.split(",")
        except:
          HourCoreCount = ""

        if (len(HourCoreCount) == 24):  # Check if schedule contains 24 hours.
          CurrentHour = datetime.datetime.now().hour
          logging.info ("Current hour: {}".format(CurrentHour))
          logging.info ("Current Core count:   {}".format(instance.cpu_core_count))
          logging.info ("Scheduled Core count: {}".format(HourCoreCount[CurrentHour]))

          takeAction = False
          if (int(instance.cpu_core_count) < int(HourCoreCount[CurrentHour]) and (action == 0 or action ==1)):
            takeAction = True
          if (int(instance.cpu_core_count) > int(HourCoreCount[CurrentHour]) and (action == 0 or action ==2)):
            takeAction = True

          if (takeAction):
            logging.info ("System needs to rescaling")
            tries = 0
            while (tries < 5): 
              if (instance.lifecycle_state == "AVAILABLE"):
                logging.info ("System is available for re-scaling")
                DbSystemDetails = oci.database.models.UpdateDbSystemDetails(cpu_core_count = int(HourCoreCount[CurrentHour]))
                response = databaseClient.update_db_system(db_system_id = instance.id, update_db_system_details = DbSystemDetails)
                logging.debug (response.data)
                logging.info ("System is re-scaling")
                break
              else:
                logging.debug ("System is not available for scaling... attempt: {}".format(tries))
                time.sleep(60)
                response = databaseClient.get_db_system(db_system_id = instance.id)
                instance = response.data
                tries = tries + 1
          else:
            logging.info ("No Action needed")

 
logging.basicConfig(format='%(asctime)s %(message)s', level=logging.DEBUG)

DayOfWeekString = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DayOfWeek = datetime.datetime.today().weekday()
Day = DayOfWeekString[DayOfWeek]
logging.info ("Day of week: {}".format(Day))

action = 0
for arg in sys.argv:
  if arg == "up": 
    logging.info ("Check for Scaling up")
    action = 1
  if arg == "down":
    logging.info ("Check for Scaling down")
    action = 2

config = oci.config.from_file(configfile)

identity = oci.identity.IdentityClient(config)
user = identity.get_user(config["user"]).data
RootCompartmentID = user.compartment_id
  
logging.info ("Logged in as: {} @ {}".format(user.description, config["region"]))

databaseClient = oci.database.DatabaseClient(config)

# Get list of all Compartments   
response = identity.list_compartments(RootCompartmentID)
compartments = response.data

# Insert (on top) the root compartment
RootCompartment = oci.identity.models.Compartment()
RootCompartment.id = RootCompartmentID
RootCompartment.name = "root"
compartments.insert(0, RootCompartment)

for compartment in compartments:
  compartmentName = compartment.name
  compartmentID = compartment.id
  
  #try:
  response = databaseClient.list_autonomous_data_warehouses(compartment_id=compartmentID)
  ScaleInstances(response.data)
  #except:
  #  logging.debug ("No ADW instances")
  
  #try:
  response = databaseClient.list_autonomous_databases(compartment_id=compartmentID)
  ScaleInstances(response.data)
  #except:
  #  logging.debug ("No ATP instances")




    
