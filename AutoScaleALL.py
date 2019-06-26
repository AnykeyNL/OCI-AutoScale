import oci
import logging
import datetime
import threading
import time
import sys

# OCI - Scheduled Auto Scaling Script
# Written by: Richard Garsthagen - richard@oc-blog.com
# Version 1.0 - June 2019
#
# More info see: www.oc-blog.com
#

# You can modify / translate the tag names used by this script - case sensitive!!!
PredefinedTag = "Schedule"
AnyDay = "AnyDay"
Weekend = "Weekend"
WeekDay = "WeekDay"
Daysofweek = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# OCI Configuration
configfile = "~/.oci/config"
ComputeShutdownMethod = "SOFTSTOP"

# Configure logging output
#logging.basicConfig(filename="~/autoscale.log", format='%(asctime)s %(message)s', level=logging.INFO)
logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)

Action = "All"  # Default, do all up/on and down/off scaling actions

if len(sys.argv) == 2:
    if sys.argv[1].upper() == "UP":
        Action = "Up"
    if sys.argv[1].upper() == "DOWN":
        Action = "Down"

logging.info("Starting Auto Scaling script, executing {} actions".format(Action))

class AutonomousThread (threading.Thread):
    def __init__(self, threadID, ID, NAME, CPU):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.ID = ID
        self.NAME = NAME
        self.CPU = CPU
    def run(self):
        logging.info("Starting Autonomous DB {} and after that scaling to {} cpus".format(self.NAME, self.CPU) )
        response = database.start_autonomous_database(autonomous_database_id=self.ID).data
        while response.lifecycle_state != "AVAILABLE":
            response = database.get_autonomous_database(autonomous_database_id=self.ID).data
            time.sleep(5)
        logging.info("Autonomous DB {} started, re-scaling to {} cpus".format(self.NAME, self.CPU))
        dbupdate = oci.database.models.UpdateAutonomousDatabaseDetails()
        dbupdate.cpu_core_count = self.CPU
        response = database.update_autonomous_database(autonomous_database_id=self.ID, update_autonomous_database_details=dbupdate)

class PoolThread (threading.Thread):
    def __init__(self, threadID, ID, NAME, INSTANCES):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.ID = ID
        self.NAME = NAME
        self.INSTANCES = INSTANCES
    def run(self):
        logging.info("Starting Instance Pool {} and after that scaling to {} instances".format(self.NAME, self.INSTANCES) )
        response = pool.start_instance_pool(instance_pool_id=self.ID).data
        while response.lifecycle_state != "RUNNING":
            response = pool.get_instance_pool(instance_pool_id=self.ID).data
            time.sleep(5)
        logging.info("Instance pool {} started, re-scaling to {} instances".format(self.NAME, self.INSTANCES))
        pooldetails = oci.core.models.UpdateInstancePoolDetails()
        pooldetails.size = self.INSTANCES
        response = pool.update_instance_pool(instance_pool_id=self.ID, update_instance_pool_details=pooldetails).data

# Check credentials and enabled regions
config = oci.config.from_file(configfile)
identity = oci.identity.IdentityClient(config)
user = identity.get_user(config["user"]).data
RootCompartmentID = user.compartment_id
logging.info ("Logged in as: {} @ {}".format(user.description, config["region"]))

compute = oci.core.ComputeClient(config)
database = oci.database.DatabaseClient(config)
pool = oci.core.ComputeManagementClient(config)

regions = identity.list_region_subscriptions(config["tenancy"]).data
regionnames = ""
for region in regions:
    regionnames = regionnames + region.region_name + " "

logging.info ("Enabled regions: {}".format(regionnames))

threads = []  # Thread array for async AutonomousDB start and rescale
tcount = 0

# Get Current Day, time
DayOfWeek = datetime.datetime.today().weekday()   # Day of week as a number
Day = Daysofweek[DayOfWeek]                       # Day of week as string
CurrentHour = datetime.datetime.now().hour
logging.info ("Day of week: {} - Current hour: {}".format(Day,CurrentHour))

#Array start with 0 so decrease CurrentHour with 1
CurrentHour = CurrentHour -1


# Find (almost) all resources with a Schedule Tag
search = oci.resource_search.ResourceSearchClient(config)
query = "query all resources where (definedTags.namespace = '{}')".format(PredefinedTag)

sdetails = oci.resource_search.models.StructuredSearchDetails()
sdetails.query = query

result = search.search_resources(search_details=sdetails, limit=1000).data

# Manually searching for Instance Pools as this is not indexed by the search function
compartments = oci.pagination.list_call_get_all_results(identity.list_compartments, compartment_id=RootCompartmentID ,compartment_id_in_subtree= True).data

pool = oci.core.ComputeManagementClient(config)

for c in compartments:
    if c.lifecycle_state == "ACTIVE":
        #pools = oci.pagination.list_call_get_all_results(pool.list_instance_pools, compartment_id=c.id).data
        pools = pool.list_instance_pools(compartment_id=c.id).data
        for p in pools:
            # If Schedule tag is found in the instance pool, add the pool to the search results.
            if PredefinedTag in p.defined_tags:
                pdetail = oci.resource_search.models.ResourceSummary()
                pdetail.identifier = p.id
                pdetail.resource_type = "instancePool"
                pdetail.defined_tags = p.defined_tags
                pdetail.display_name = p.display_name
                pdetail.lifecycle_state = p.lifecycle_state
                pdetail.time_created = p.time_created
                pdetail.compartment_id = p.compartment_id
                result.items.append(pdetail)


# All the items with a schedule are now collected.
# Let's go thru them and find / validate the correct schedule

for resource in result.items:
    schedule = resource.defined_tags[PredefinedTag]
    ActiveSchedule = ""
    if AnyDay in schedule:
        ActiveSchedule = schedule[AnyDay]
    if DayOfWeek < 6 : #check for weekday / weekend
        if WeekDay in schedule:
            ActiveSchedule = schedule[WeekDay]
    else:
        if Weekend in schedule:
            ActiveSchedule = schedule[Weekend]
    if Day in schedule: # Check for day specific tag (today)
        ActiveSchedule = schedule[Day]

    # Check is the active schedule contains exactly 24 numbers for each hour of the day
    try:
        schedulehours = ActiveSchedule.split(",")
        if len(schedulehours) != 24:
            logging.error("Error with schedule of {} - {}, not correct amount of hours".format(resource.display_name, ActiveSchedule))
            ActiveSchedule = ""
    except:
        ActiveSchedule = ""
        logging.error("Error with schedule of {}".format(resource.display_name))

    # if schedule validated, let see if we can apply the new schedule to the resource
    if ActiveSchedule != "":
        #print("Active schedule for {} : {}".format(resource.display_name, ActiveSchedule))

        # Execute On/Off operations for compute VMs
        if resource.resource_type == "Instance":
            if int(schedulehours[CurrentHour]) == 0 or int(schedulehours[CurrentHour]) == 1:
                resourceDetails = compute.get_instance(instance_id=resource.identifier).data

                # Only perform action if VM Instance, ignoring any BM instances.
                if resourceDetails.shape[:2] == "VM":
                    if resourceDetails.lifecycle_state == "RUNNING" and int(schedulehours[CurrentHour]) == 0:
                        if Action == "All" or Action == "Down":
                            logging.info("Initiate Compute VM shutdown for {}".format(resource.display_name))
                            response = compute.instance_action(instance_id=resource.identifier, action=ComputeShutdownMethod)
                    if resourceDetails.lifecycle_state == "STOPPED" and int(schedulehours[CurrentHour]) == 1:
                        if Action == "All" or Action == "Up":
                            logging.info("Initiate Compute VM startup for {}".format(resource.display_name))
                            response = compute.instance_action(instance_id=resource.identifier, action="START")


        if resource.resource_type == "DbSystem":
            resourceDetails = database.get_db_system(db_system_id=resource.identifier).data

            # Execute On/Off operations for Database VMs
            if resourceDetails.shape[:2] == "VM":
                dbnodedetails = database.list_db_nodes(compartment_id=resource.compartment_id, db_system_id=resource.identifier).data[0]
                if int(schedulehours[CurrentHour]) == 0 or int(schedulehours[CurrentHour]) == 1:
                    if dbnodedetails.lifecycle_state == "AVAILABLE" and int(schedulehours[CurrentHour]) == 0:
                        if Action == "All" or Action == "Down":
                            logging.info("Initiate DB VM shutdown for {}".format(resource.display_name))
                            response = database.db_node_action(db_node_id=dbnodedetails.id, action="STOP")
                    if dbnodedetails.lifecycle_state == "STOPPED" and int(schedulehours[CurrentHour]) == 1:
                        if Action == "All" or Action == "Up":
                            logging.info("Initiate DB VM startup for {}".format(resource.display_name))
                            response = database.db_node_action(db_node_id=dbnodedetails.id, action="START")

            # Execute CPU Scale Up/Down operations for Database BMs
            if resourceDetails.shape[:2] == "BM":
                if int(schedulehours[CurrentHour]) > 1 and int(schedulehours[CurrentHour]) < 53:
                    if resourceDetails.cpu_core_count > int(schedulehours[CurrentHour]):
                        if Action == "All" or Action == "Down":
                            logging.info("Initiate DB BM Scale Down to {} for {}".format(int(schedulehours[CurrentHour]),resource.display_name))
                            dbupdate = oci.database.models.UpdateDbSystemDetails()
                            dbupdate.cpu_core_count = int(schedulehours[CurrentHour])
                            response = database.update_db_system(db_system_id=resource.identifier, update_db_system_details=dbupdate)
                    if resourceDetails.cpu_core_count < int(schedulehours[CurrentHour]):
                        if Action == "All" or Action == "Up":
                            logging.info("Initiate DB BM Scale UP to {} for {}".format(int(schedulehours[CurrentHour]),resource.display_name))
                            dbupdate = oci.database.models.UpdateDbSystemDetails()
                            dbupdate.cpu_core_count = int(schedulehours[CurrentHour])
                            response = database.update_db_system(db_system_id=resource.identifier, update_db_system_details=dbupdate)


        # Execute CPU Scale Up/Down operations for Database BMs
        if resource.resource_type == "AutonomousDatabase":
            if int(schedulehours[CurrentHour]) >= 0 and int(schedulehours[CurrentHour]) < 129:
                resourceDetails = database.get_autonomous_database(autonomous_database_id=resource.identifier).data

                # Autonomous DB is running request is amount of CPU core change is needed
                if resourceDetails.lifecycle_state == "AVAILABLE" and int(schedulehours[CurrentHour]) > 0:
                    if resourceDetails.cpu_core_count > int(schedulehours[CurrentHour]):
                        if Action == "All" or Action == "Down":
                            logging.info("Initiate Autonomous DB Scale Down to {} for {}".format(int(schedulehours[CurrentHour]),
                                                                                         resource.display_name))
                            dbupdate = oci.database.models.UpdateAutonomousDatabaseDetails()
                            dbupdate.cpu_core_count = int(schedulehours[CurrentHour])
                            response = database.update_autonomous_database(autonomous_database_id=resource.identifier, update_autonomous_database_details=dbupdate)

                    if resourceDetails.cpu_core_count < int(schedulehours[CurrentHour]):
                        if Action == "All" or Action == "Up":
                            logging.info("Initiate Autonomous DB Scale Up to {} for {}".format(int(schedulehours[CurrentHour]),
                                                                                                 resource.display_name))
                            dbupdate = oci.database.models.UpdateAutonomousDatabaseDetails()
                            dbupdate.cpu_core_count = int(schedulehours[CurrentHour])
                            response = database.update_autonomous_database(autonomous_database_id=resource.identifier,
                                                                           update_autonomous_database_details=dbupdate)

                # Autonomous DB is running request is to stop the database
                if resourceDetails.lifecycle_state == "AVAILABLE" and int(schedulehours[CurrentHour]) == 0:
                    if Action == "All" or Action == "Down":
                        response= database.stop_autonomous_database(autonomous_database_id=resource.identifier)

                if resourceDetails.lifecycle_state == "STOPPED" and int(schedulehours[CurrentHour]) > 0:
                    if Action == "All" or Action == "Up":

                        # Autonomous DB is stopped and needs to be started with same amount of CPUs configured
                        if resourceDetails.cpu_core_count == int(schedulehours[CurrentHour]):
                            response = database.start_autonomous_database(autonomous_database_id=resource.identifier)

                        # Autonomous DB is stopped and needs to be started, after that it requires CPU change
                        if resourceDetails.cpu_core_count != int(schedulehours[CurrentHour]):
                            tcount = tcount + 1
                            thread = AutonomousThread(tcount, resource.identifier, resource.display_name , int(schedulehours[CurrentHour]))
                            thread.start()
                            threads.append(thread)

        if resource.resource_type == "instancePool":
            resourceDetails = pool.get_instance_pool(instance_pool_id=resource.identifier).data

            # Stop Resource pool action
            if resourceDetails.lifecycle_state == "RUNNING" and int(schedulehours[CurrentHour]) == 0:
                if Action == "All" or Action == "Down":
                    logging.info("Stopping instance pool {}".format(resource.display_name))
                    response = pool.stop_instance_pool(instance_pool_id=resource.identifier)

            # Scale up action on running instance pool
            elif resourceDetails.lifecycle_state == "RUNNING" and int(schedulehours[CurrentHour]) > resourceDetails.size:
                if Action == "All" or Action == "Up":
                    logging.info("Scaling up instance pool {} to {} instances".format(resource.display_name, int(schedulehours[CurrentHour]) ))
                    pooldetails = oci.core.models.UpdateInstancePoolDetails()
                    pooldetails.size = int(schedulehours[CurrentHour])
                    response = pool.update_instance_pool(instance_pool_id=resource.identifier, update_instance_pool_details=pooldetails).data

            # Scale down action on running instance pool
            elif resourceDetails.lifecycle_state == "RUNNING" and int(schedulehours[CurrentHour]) < resourceDetails.size:
                if Action == "All" or Action == "Down":
                    logging.info("Scaling down instance pool {} to {} instances".format(resource.display_name, int(schedulehours[CurrentHour]) ))
                    pooldetails = oci.core.models.UpdateInstancePoolDetails()
                    pooldetails.size = int(schedulehours[CurrentHour])
                    response = pool.update_instance_pool(instance_pool_id=resource.identifier, update_instance_pool_details=pooldetails).data

            elif resourceDetails.lifecycle_state == "STOPPED" and int(schedulehours[CurrentHour]) > 0:
                if Action == "All" or Action == "Up":
                    # Start instance pool with same amount of instances as configured
                    if resourceDetails.size == int(schedulehours[CurrentHour]):
                        logging.info("Starting instance pool {} from stopped state".format(resource.display_name))
                        response = pool.start_instance_pool(instance_pool_id=resource.identifier).data

                    # Start instance pool and after that resize the instance pool to desired state:
                    if resourceDetails.size != int(schedulehours[CurrentHour]):
                        tcount = tcount + 1
                        thread = PoolThread(tcount, resource.identifier, resource.display_name,int(schedulehours[CurrentHour]))
                        thread.start()
                        threads.append(thread)


# Wait for any AutonomousDB and Instance Pool Start and rescale tasks completed
for t in threads:
   t.join()

print ("All scaling tasks done")























