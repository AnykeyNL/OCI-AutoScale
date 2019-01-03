# OCI - Auto start / stop of Compute Instances based on time
# Written by: Richard Garsthagen - richard@oc-blog.com
# Version 1.0 - Janruary 3rd 2019
#
# A pre-defined tag namespace "Schedule" needs to be used.
# The following tags in that namespace can be used:
# - AnyDay
# - Weekend
# - Weekday
# - Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday
#
# Each tag must consist of 24 numbers seperated by a komma, representing the hours of the day.
# a 0 stands for OFF and a 1 stands for ON
#
# If no schedule tage is present the instance is ignored.
#
# More info see: www.oc-blog.com
#

import oci
import json
import datetime
import time
import sys
import logging

#logging.basicConfig(filename="autoonoff.log", format='%(asctime)s %(message)s', level=logging.INFO)
logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)

# Specify your config file with access to the OCI API credentials
configfile = "c:\oci\config"
action = 0

for arg in sys.argv:
  if arg == "on": 
    logging.info ("Check for auto ON events ONLY")
    action = 1
  if arg == "off":
    logging.info ("Check for auto OFF events ONLY")
    action = 2

def CheckInstances(instances, compartmentName, regionname):
  for instance in instances:   
    namespaces = instance.defined_tags
    schedule = ""
    if "Schedule" in namespaces:
        logging.info ("Instance [{}] has a schedule".format(instance.display_name))
        
        # Lower priority - AnyDay
        if "AnyDay" in namespaces["Schedule"]:
            schedule = namespaces["Schedule"]["AnyDay"]
                
        # 2nd prioriry - Weekend or Weekday
        if Day == "Saturday" or Day == "Sunday":
            if "Weekend" in namespaces["Schedule"]: schedule = namespaces["Schedule"]["Weekend"]
        else:
            if "Weekday" in namespaces["Schedule"]: schedule = namespaces["Schedule"]["Weekday"]

        #1st priority - specific day
        if Day in namespaces["Schedule"]: schedule = namespaces["Schedule"][Day]

        schedulehours = schedule.split(",")
        if len(schedulehours) == 24:
            logging.info ("Current State: [{}]  -   Desired state: [{}]".format(instance.lifecycle_state, schedulehours[CurrentHour-1]))
            if instance.lifecycle_state == "STOPPED" and schedulehours[CurrentHour-1] == "1" and (action == 0 or action== 1):
                logging.info("Starting the instance")
                response = ComputeClient.instance_action(instance_id=instance.id, action="START")
            if instance.lifecycle_state == "RUNNING" and schedulehours[CurrentHour-1] == "0" and (action == 0 or action== 2):
                logging.info("Stopping the instance")
                response = ComputeClient.instance_action(instance_id=instance.id, action="SOFTSTOP")
                
        else:
            logging.info ("Instance [{}] has incorrect specified schedule".format(instance.display_name))
            
        

logging.debug("Action: {}".format(action))

DayOfWeekString = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

config = oci.config.from_file(configfile)

identity = oci.identity.IdentityClient(config)
user = identity.get_user(config["user"]).data
RootCompartmentID = user.compartment_id

logging.info ("Logged in as: {} @ {}".format(user.description, config["region"]))

response = identity.list_region_subscriptions(config["tenancy"])
regions = response.data

for region in regions:
  if region.is_home_region:
    home = "Home region"
  else:
    home = ""
  logging.info("- {} ({}) {}".format(region.region_name, region.status, home))


ComputeClient = oci.core.ComputeClient(config)

DayOfWeek = datetime.datetime.today().weekday()
Day = DayOfWeekString[DayOfWeek]
CurrentHour = datetime.datetime.now().hour
logging.info ("Day of week: {} - Current hour: {}".format(Day,CurrentHour))

for region in regions:
  config = oci.config.from_file(configfile)
  config["region"] = region.region_name

  identity = oci.identity.IdentityClient(config)
  user = identity.get_user(config["user"]).data
  RootCompartmentID = user.compartment_id
 
  ComputeClient = oci.core.ComputeClient(config)
  
  # Check instances for all the underlaying Compartments   
  response = oci.pagination.list_call_get_all_results(identity.list_compartments,RootCompartmentID,compartment_id_in_subtree=True)
  compartments = response.data

  # Insert (on top) the root compartment
  RootCompartment = oci.identity.models.Compartment()
  RootCompartment.id = RootCompartmentID
  RootCompartment.name = "root"
  RootCompartment.lifecycle_state = "ACTIVE"
  compartments.insert(0, RootCompartment)

  for compartment in compartments:
    compartmentName = compartment.name
    if compartment.lifecycle_state == "ACTIVE":
      logging.info("process Compartment:" + compartmentName)
      response = oci.pagination.list_call_get_all_results(ComputeClient.list_instances,compartment_id=compartment.id)  
      if len(response.data) > 0:
        CheckInstances(response.data, compartmentName, region.region_name)

logging.info("Done.")



      



