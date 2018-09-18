# OCI - ADW and ATP Scheduled Auto Scaling
# Written by: Richard Garsthagen - richard@oc-blog.com
# Version 1.1 - September 18th 2018
#
# More info see: www.oc-blog.com
#
import oci
import json
import logging
import datetime
import time
import sys
from threading import Thread


# Script configuation ##################################################################################

configfile = "c:\\oci\\config"  # Define config file to be used. 

########################################################################################################

def ScaleInstance(instance, dbtype):
    Schedule = ""
    logging.debug(instance)
    for def_tags in instance.defined_tags:
      logging.debug(def_tags)
      if (def_tags == "Schedule"):
        logging.info ("Schedule tags found for instance " + instance.display_name)
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
          logging.info ("Instance: " + instance.display_name)
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
            while (tries < 7): 
              if (instance.lifecycle_state == "AVAILABLE"):
                logging.debug ("System is available for re-scaling")
                # Let's rescale the services!
                if dbtype == "ADW":
                  if int(HourCoreCount[CurrentHour]) == 0:
                    response = databaseClient.stop_autonomous_data_warehouse(autonomous_data_warehouse_id = instance.id)
                    logging.info("Stopping ADW as requested CPU count is 0")
                  else:
                    DbSystemDetails = oci.database.models.UpdateAutonomousDataWarehouseDetails(cpu_core_count = int(HourCoreCount[CurrentHour]))
                    response = databaseClient.update_autonomous_data_warehouse(autonomous_data_warehouse_id = instance.id, update_autonomous_data_warehouse_details = DbSystemDetails)
                if dbtype == "ATP":
                  if int(HourCoreCount[CurrentHour]) == 0:
                    response = databaseClient.stop_autonomous_database(autonomous_database_id = instance.id)
                    logging.info("Stopping ATP as requested CPU count is 0")
                  else:
                    DbSystemDetails = oci.database.models.UpdateAutonomousDatabaseDetails(cpu_core_count = int(HourCoreCount[CurrentHour]))
                    response = databaseClient.update_autonomous_database(autonomous_database_id = instance.id, update_autonomous_database_details = DbSystemDetails)
                logging.debug (response.data)
                logging.info ("System is re-scaling")
                break

              elif (instance.lifecycle_state == "STOPPED"):
                logging.debug("System is stopped!")
                if dbtype == "ADW":
                  if int(HourCoreCount[CurrentHour]) != 0:
                    logging.info("Need to power on ADW instance first")
                    response = databaseClient.start_autonomous_data_warehouse(autonomous_data_warehouse_id = instance.id)
                    if (int(instance.cpu_core_count) < int(HourCoreCount[CurrentHour])):
                      while (instance.lifecycle_state != "AVAILABLE"):
                        logging.debug("Waiting for instance to become available")
                        response = databaseClient.get_autonomous_data_warehouse(autonomous_data_warehouse_id = instance.id)
                        instance = response.data
                        time.sleep(5)
                      DbSystemDetails = oci.database.models.UpdateAutonomousDataWarehouseDetails(cpu_core_count = int(HourCoreCount[CurrentHour]))
                      response = databaseClient.update_autonomous_data_warehouse(autonomous_data_warehouse_id = instance.id, update_autonomous_data_warehouse_details = DbSystemDetails)
                if dbtype == "ATP":
                  if int(HourCoreCount[CurrentHour]) != 0:
                    logging.info("Need to power on ATP instance first")
                    response = databaseClient.start_autonomous_database(autonomous_database_id = instance.id)
                    if (int(instance.cpu_core_count) < int(HourCoreCount[CurrentHour])):
                      while (instance.lifecycle_state != "AVAILABLE"):
                        logging.debug("Waiting for instance to become available")
                        response = databaseClient.get_autonomous_database(autonomous_database_id = instance.id)
                        instance = response.data
                        time.sleep(5)
                      DbSystemDetails = oci.database.models.UpdateAutonomousDatabaseDetails(cpu_core_count = int(HourCoreCount[CurrentHour]))
                      response = databaseClient.update_autonomous_database(autonomous_database_id = instance.id, update_autonomous_database_details = DbSystemDetails)
                break

              else:
                logging.debug ("System is not available for scaling... attempt: {}".format(tries))
                time.sleep(20)
                if (dbtype == "ADW"):
                  response = databaseClient.get_autonomous_data_warehouse(autonomous_data_warehouse_id = instance.id)
                if (dbtype == "ATP"):
                  response = databaseClient.get_autonomous_database(autonomous_database_id = instance.id)
                instance = response.data
                tries = tries + 1
        
          else:
            logging.info ("No Action needed")

 
logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)

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

threads = []

for compartment in compartments:
  compartmentName = compartment.name
  compartmentID = compartment.id
  
  try:
    response = databaseClient.list_autonomous_data_warehouses(compartment_id=compartmentID)
    instances = response.data
    for instance in instances:
      t = Thread( target=ScaleInstance, args=(instance, "ADW") )
      threads.append(t)
  except:
    logging.debug ("No ADW instances")
  
  try:
    response = databaseClient.list_autonomous_databases(compartment_id=compartmentID)
    instances = response.data
    for instance in instances:
      t = Thread( target=ScaleInstance, args =(instance, "ATP") )
      threads.append(t)
  except:
    logging.debug ("No ATP instances")

logging.debug("Start scaling threads")
for s in threads:
  s.start()

logging.debug("Waiting for completion of all threads")
for s in threads:
  s.join()

logging.info("Completed")







    
