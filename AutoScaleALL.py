#!/home/opc/py36env/bin/python
# OCI - Scheduled Auto Scaling Script
# Written by: Richard Garsthagen - richard@oc-blog.com
# Co-Developers: Joel Nation (https://github.com/Joelith)
# Version 2.2 - August 20200
#
# More info see: www.oc-blog.com
#
import oci
import datetime
import threading
import time
import sys
import requests


# You can modify / translate the tag names used by this script - case sensitive!!!
PredefinedTag = "Schedule"
AnyDay = "AnyDay"
Weekend = "Weekend"
WeekDay = "WeekDay"
Daysofweek = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# ============== CONFIGURE THIS SECTION ======================
# OCI Configuration
UseInstancePrinciple = False

#Location of config file
#configfile = "c:\\Users\\UserName\\.oci\\config"
configfile = "~/.oci/config"

ComputeShutdownMethod = "SOFTSTOP"
LogLevel = "ALL" #  Use ALL or ERRORS. When set to ERRORS only a notification will be published if error occurs
TopicID = ""  # Enter Topic OCID if you want the script to publish a message about the scaling actions

AlternativeWeekend = False # Set to True is your weekend is Friday/Saturday

RateLimitDelay = 2  # Time in seconds to wait before retry of operation
# ============================================================

ErrorsFound = False

# Configure logging output
def MakeLog(msg):
    print (msg)

Action = "All"  # Default, do all up/on and down/off scaling actions

if len(sys.argv) == 2:
    if sys.argv[1].upper() == "UP":
        Action = "Up"
    if sys.argv[1].upper() == "DOWN":
        Action = "Down"

if UseInstancePrinciple:
    signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
    MakeLog("Using Instance principle")
else:
    signer = None

MakeLog("Starting Auto Scaling script, executing {} actions".format(Action))

def isWeekDay(day):
    weekday = True
    if AlternativeWeekend:
        if day == 4 or day == 5:
            weekday = False
    else:
        if day == 5 or day == 6:
            weekday = False
    return weekday

class AutonomousThread (threading.Thread):
    def __init__(self, threadID, ID, NAME, CPU):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.ID = ID
        self.NAME = NAME
        self.CPU = CPU
    def run(self):
        MakeLog(" - Starting Autonomous DB {} and after that scaling to {} cpus".format(self.NAME, self.CPU) )
        Retry = True
        while Retry:
            try:
                response = database.start_autonomous_database(autonomous_database_id=self.ID)
                Retry = False
                success.append("Started Autonomous DB {}".format(self.NAME))
            except oci.exceptions.ServiceError as response:
                if response.status == 429:
                    MakeLog("Rate limit kicking in.. waiting {} seconds...".format(RateLimitDelay))
                    time.sleep(RateLimitDelay)
                else:
                    ErrorsFound = True
                    errors.append(" - Error ({}) Starting Autonomous DB {}".format(response.status, self.NAME))
                    Retry = False

        response = database.get_autonomous_database(autonomous_database_id=self.ID)
        time.sleep(10)
        while response.data.lifecycle_state != "AVAILABLE":
            response = database.get_autonomous_database(autonomous_database_id=self.ID)
            time.sleep(10)
        MakeLog("Autonomous DB {} started, re-scaling to {} cpus".format(self.NAME, self.CPU))
        dbupdate = oci.database.models.UpdateAutonomousDatabaseDetails()
        dbupdate.cpu_core_count = self.CPU
        Retry = True
        while Retry:
            try:
                response = database.update_autonomous_database(autonomous_database_id=self.ID, update_autonomous_database_details=dbupdate)
                Retry = False
                success.append("Autonomous DB {} started, re-scaling to {} cpus".format(self.NAME, self.CPU))
            except oci.exceptions.ServiceError as response:
                if response.status == 429:
                    MakeLog("Rate limit kicking in.. waiting {} seconds...".format(RateLimitDelay))
                    time.sleep(RateLimitDelay)
                else:
                    errors.append(" - Error ({}) re-scaling to {} cpus for {}".format(response.status, self.CPU, self.NAME))
                    Retry = False

class PoolThread (threading.Thread):
    def __init__(self, threadID, ID, NAME, INSTANCES):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.ID = ID
        self.NAME = NAME
        self.INSTANCES = INSTANCES
    def run(self):
        MakeLog(" - Starting Instance Pool {} and after that scaling to {} instances".format(self.NAME, self.INSTANCES) )
        Retry = True
        while Retry:
            try:
                response = pool.start_instance_pool(instance_pool_id=self.ID)
                Retry = False
                success.append(" - Starting Instance Pool {}".format(self.NAME))
            except oci.exceptions.ServiceError as response:
                if response.status == 429:
                    MakeLog("Rate limit kicking in.. waiting {} seconds...".format(RateLimitDelay))
                    time.sleep(RateLimitDelay)
                else:
                    errors.append(" - Error ({}) starting instance pool {}".format(response.status, self.NAME))
                    Retry = False

        response = pool.get_instance_pool(instance_pool_id=self.ID)
        time.sleep(10)
        while response.data.lifecycle_state != "RUNNING":
            response = pool.get_instance_pool(instance_pool_id=self.ID)
            time.sleep(10)
        MakeLog("Instance pool {} started, re-scaling to {} instances".format(self.NAME, self.INSTANCES))
        pooldetails = oci.core.models.UpdateInstancePoolDetails()
        pooldetails.size = self.INSTANCES
        Retry = True
        while Retry:
            try:
                response = pool.update_instance_pool(instance_pool_id=self.ID, update_instance_pool_details=pooldetails)
                Retry = False
                success.append("Rescaling Instance Pool {} to {} instances".format(self.NAME, self.INSTANCES))
            except oci.exceptions.ServiceError as response:
                if response.status == 429:
                    MakeLog("Rate limit kicking in.. waiting {} seconds...".format(RateLimitDelay))
                    time.sleep(RateLimitDelay)
                else:
                    ErrorsFound = True
                    errors.append(" - Error ({}) rescaling instance pool {}".format(response.status, self.NAME))
                    Retry = False

class AnalyticsThread (threading.Thread):
    def __init__(self, threadID, ID, NAME, CPU):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.ID = ID
        self.NAME = NAME
        self.CPU = CPU
    def run(self):
        MakeLog(" - Starting Analytics Service {} and after that scaling to {} cpus".format(self.NAME, self.CPU) )
        Retry = True
        while Retry:
            try:
                response = analytics.start_analytics_instance(analytics_instance_id=self.ID)
                Retry = False
                success.append("Started Analytics Service {}".format(self.NAME))
            except oci.exceptions.ServiceError as response:
                if response.status == 429:
                    MakeLog("Rate limit kicking in.. waiting {} seconds...".format(RateLimitDelay))
                    time.sleep(RateLimitDelay)
                else:
                    ErrorsFound = True
                    errors.append(" - Error ({}) Starting Analytics Service {}".format(response.status, self.NAME))
                    Retry = False

        response = analytics.get_analytics_instance(analytics_instance_id=self.ID)
        time.sleep(10)
        while response.data.lifecycle_state != "ACTIVE":
            response = analytics.get_analytics_instance(analytics_instance_id=self.ID)
            time.sleep(10)
        MakeLog("Analytics Service {} started, re-scaling to {} cpus".format(self.NAME, self.CPU))
        capacity = oci.analytics.models.capacity.Capacity()
        capacity.capacity_value = self.CPU
        capacity.capacity_type = capacity.CAPACITY_TYPE_OLPU_COUNT
        details = oci.analytics.models.ScaleAnalyticsInstanceDetails()
        details.capacity = capacity
        Retry = True
        while Retry:
            try:
                response = analytics.scale_analytics_instance(analytics_instance_id=self.ID,scale_analytics_instance_details=details)
                Retry = False
                success.append("Analytics Service {} started, re-scaling to {} cpus".format(self.NAME, self.CPU))
            except oci.exceptions.ServiceError as response:
                if response.status == 429:
                    MakeLog("Rate limit kicking in.. waiting {} seconds...".format(RateLimitDelay))
                    time.sleep(RateLimitDelay)
                else:
                    errors.append("Error ({}) re-scaling Analytics to {} cpus for {}".format(response.status, self.CPU, self.NAME))
                    Retry = False

def isDeleted(state):
    deleted = False
    try:
        if state == "TERMINATED" or state == "TERMINATING":
            deleted = True
        if state == "DELETED" or state == "DELETING":
            deleted = True
    except:
        deleted = True
        MakeLog("No lifecyclestate found, ignoring resource")
        MakeLog(state)


    return deleted


if UseInstancePrinciple:
    userName = "Instance Principle"
    try:
        url = "http://169.254.169.254/opc/v1/instance/"
        data = requests.get(url).json()
    except:
        MakeLog("This instance is not running on OCI or does not have Instance Principle permissions")
        exit()
    region = data['region']
    compID = data['compartmentId']
    if compID[:14] == "ocid1.tenancy.":
       RootCompartmentID = compID
       SearchRootID = False
    else:
       SearchRootID = True
    SearchCompID = compID

    identity = oci.identity.IdentityClient(config={}, signer=signer)
    compute = oci.core.ComputeClient(config={}, signer=signer)
    database = oci.database.DatabaseClient(config={}, signer=signer)
    pool = oci.core.ComputeManagementClient(config={}, signer=signer)
    search = oci.resource_search.ResourceSearchClient(config={}, signer=signer)
    ns = oci.ons.NotificationDataPlaneClient(config={}, signer=signer)
    oda= oci.oda.OdaClient(config={}, signer=signer)
    analytics = oci.analytics.AnalyticsClient(config={}, signer=signer)
    integration = oci.integration.IntegrationInstanceClient(config={}, signer=signer)
    loadbalancer = oci.load_balancer.LoadBalancerClient(config={}, signer=signer)
    mysql = oci.mysql.MysqlaasClient(config={}, signer=signer)

    while SearchRootID:
        compartment = identity.get_compartment(compartment_id=SearchCompID).data
        if compartment.compartment_id[:14] == "ocid1.tenancy.":
            RootCompartmentID = compartment.compartment_id
            SearchRootID = False
        else:
            SearchCompID = compartment.compartment_id


else:
    config = oci.config.from_file(configfile)
    identity = oci.identity.IdentityClient(config)
    compute = oci.core.ComputeClient(config)
    database = oci.database.DatabaseClient(config)
    pool = oci.core.ComputeManagementClient(config)
    search = oci.resource_search.ResourceSearchClient(config)
    ns = oci.ons.NotificationDataPlaneClient(config)
    oda = oci.oda.OdaClient(config)
    analytics = oci.analytics.AnalyticsClient(config)
    integration = oci.integration.IntegrationInstanceClient(config)
    loadbalancer = oci.load_balancer.LoadBalancerClient(config)
    mysql = oci.mysql.MysqlaasClient(config)
    user = identity.get_user(config["user"]).data
    userName = user.description
    RootCompartmentID = config["tenancy"]
    region = config["region"]

# Check credentials and enabled regions
Tenancy = identity.get_tenancy(tenancy_id=RootCompartmentID).data

MakeLog ("Logged in as: {}/{} @ {}".format(userName, Tenancy.name, region))


threads = []  # Thread array for async AutonomousDB start and rescale
tcount = 0

# Get Current Day, time
DayOfWeek = datetime.datetime.today().weekday()   # Day of week as a number
Day = Daysofweek[DayOfWeek]                       # Day of week as string
CurrentHour = datetime.datetime.now().hour

if AlternativeWeekend:
    MakeLog("Using Alternative weekend (Friday and Saturday as weekend")

MakeLog ("Day of week: {} - Weekday: {} - Current hour: {}".format(Day,isWeekDay(DayOfWeek), CurrentHour))

#Array start with 0 so decrease CurrentHour with 1
CurrentHour = CurrentHour -1


# Find all resources with a Schedule Tag
query = "query all resources where (definedTags.namespace = '{}')".format(PredefinedTag)

sdetails = oci.resource_search.models.StructuredSearchDetails()
sdetails.query = query

result = search.search_resources(search_details=sdetails, limit=1000).data

# All the items with a schedule are now collected.
# Let's go thru them and find / validate the correct schedule
total_resources = len(result.items)
success=[]
errors=[]
for resource in result.items:
    # The search data is not always updated. Get the tags from the actual resource itself, not using the search data.
    resourceOk = False
    print ("Checking {} - {}...".format(resource.display_name, resource.resource_type))
    if resource.resource_type == "Instance":
        resourceDetails = compute.get_instance(instance_id=resource.identifier).data
        resourceOk = True
    if resource.resource_type == "DbSystem":
        resourceDetails = database.get_db_system(db_system_id=resource.identifier).data
        resourceOk = True
    if resource.resource_type == "VmCluster":
        resourceDetails = database.get_vm_cluster(vm_cluster_id=resource.identifier).data
        resourceOk = True
    if resource.resource_type == "AutonomousDatabase":
        resourceDetails = database.get_autonomous_database(autonomous_database_id=resource.identifier).data
        resourceOk = True
    if resource.resource_type == "InstancePool":
        resourceDetails = pool.get_instance_pool(instance_pool_id=resource.identifier).data
        resourceOk = True
    if resource.resource_type == "OdaInstance":
        resourceDetails = oda.get_oda_instance(oda_instance_id=resource.identifier).data
        resourceOk = True
    if resource.resource_type == "AnalyticsInstance":
        resourceDetails = analytics.get_analytics_instance(analytics_instance_id=resource.identifier).data
        resourceOk = True
    if resource.resource_type == "IntegrationInstance":
        resourceDetails = integration.get_integration_instance(integration_instance_id=resource.identifier).data
        resourceOk = True
    if resource.resource_type == "LoadBalancer":
        resourceDetails = loadbalancer.get_load_balancer(load_balancer_id=resource.identifier).data
        resourceOk = True

    if not isDeleted(resource.lifecycle_state) and resourceOk:
        MakeLog ("Checking: {} - {}".format(resource.display_name, resource.resource_type))
        schedule = resourceDetails.defined_tags[PredefinedTag]
        ActiveSchedule = ""
        if AnyDay in schedule:
            ActiveSchedule = schedule[AnyDay]
        if isWeekDay(DayOfWeek): #check for weekday / weekend
            if WeekDay in schedule:
                ActiveSchedule = schedule[WeekDay]
        else:
            if Weekend in schedule:
                ActiveSchedule = schedule[Weekend]

        if Day in schedule: # Check for day specific tag (today)
            ActiveSchedule = schedule[Day]

        # Check if the active schedule contains exactly 24 numbers for each hour of the day
        try:
            schedulehours = ActiveSchedule.split(",")
            if len(schedulehours) != 24:
                ErrorsFound = True
                errors.append(" - Error with schedule of {} - {}, not correct amount of hours, I count {}".format(resource.display_name, ActiveSchedule, len(schedulehours)))
                MakeLog(" - Error with schedule of {} - {}, not correct amount of hours, i count {}".format(resource.display_name, ActiveSchedule, len(schedulehours)))
                ActiveSchedule = ""
        except:
            ErrorsFound = True
            ActiveSchedule = ""
            errors.append(" - Error with schedule for {}".format(resource.display_name))
            MakeLog(" - Error with schedule of {}".format(resource.display_name))
            MakeLog(sys.exc_info()[0])

        # if schedule validated, let see if we can apply the new schedule to the resource
        if ActiveSchedule != "":
            DisplaySchedule = ""
            c = 0
            for h in schedulehours:
                if c == CurrentHour:
                    DisplaySchedule = DisplaySchedule + "[" + h + "],"
                else:
                    DisplaySchedule = DisplaySchedule + h + ","
                c = c + 1

            MakeLog(" - Active schedule for {} : {}".format(resource.display_name, DisplaySchedule))

            if schedulehours[CurrentHour] == "*":
                MakeLog(" - Ignoring this service for this hour")

            else:
                # Execute On/Off operations for compute VMs
                if resource.resource_type == "Instance":
                    if int(schedulehours[CurrentHour]) == 0 or int(schedulehours[CurrentHour]) == 1:
                        # Only perform action if VM Instance, ignoring any BM instances.
                        if resourceDetails.shape[:2] == "VM":
                            if resourceDetails.lifecycle_state == "RUNNING" and int(schedulehours[CurrentHour]) == 0:
                                if Action == "All" or Action == "Down":
                                    MakeLog(" - Initiate Compute VM shutdown for {}".format(resource.display_name))
                                    Retry = True
                                    while Retry:
                                        try:
                                            response = compute.instance_action(instance_id=resource.identifier, action=ComputeShutdownMethod)
                                            Retry = False
                                            success.append(" - Initiate Compute VM shutdown for {}".format(resource.display_name))
                                        except oci.exceptions.ServiceError as response:
                                            if response.status == 429:
                                                MakeLog("Rate limit kicking in.. waiting {} seconds...".format(RateLimitDelay))
                                                time.sleep(RateLimitDelay)
                                            else:
                                                ErrorsFound = True
                                                errors.append(" - Error ({}) Compute VM Shutdown for {} - {}".format(response.status, resource.display_name, response.message))
                                                MakeLog(" - Error ({}) Compute VM Shutdown for {} - {}".format(response.status, resource.display_name, response.message))
                                                Retry = False

                            if resourceDetails.lifecycle_state == "STOPPED" and int(schedulehours[CurrentHour]) == 1:
                                if Action == "All" or Action == "Up":
                                    MakeLog(" - Initiate Compute VM startup for {}".format(resource.display_name))
                                    Retry = True
                                    while Retry:
                                        try:
                                            response = compute.instance_action(instance_id=resource.identifier, action="START")
                                            Retry = False
                                            success.append(" - Initiate Compute VM startup for {}".format(resource.display_name))
                                        except oci.exceptions.ServiceError as response:
                                            if response.status == 429:
                                                MakeLog("Rate limit kicking in.. waiting {} seconds...".format(RateLimitDelay))
                                                time.sleep(RateLimitDelay)
                                            else:
                                                ErrorsFound = True
                                                errors.append(" - Error ({}) Compute VM startup for {} - {}".format(response.status, resource.display_name, response.message))
                                                Retry = False

                if resource.resource_type == "DbSystem":
                    # Execute On/Off operations for Database VMs
                    if resourceDetails.shape[:2] == "VM":
                        dbnodedetails = database.list_db_nodes(compartment_id=resource.compartment_id, db_system_id=resource.identifier).data[0]
                        if int(schedulehours[CurrentHour]) == 0 or int(schedulehours[CurrentHour]) == 1:
                            if dbnodedetails.lifecycle_state == "AVAILABLE" and int(schedulehours[CurrentHour]) == 0:
                                if Action == "All" or Action == "Down":
                                    MakeLog(" - Initiate DB VM shutdown for {}".format(resource.display_name))
                                    Retry = True
                                    while Retry:
                                        try:
                                            response = database.db_node_action(db_node_id=dbnodedetails.id, action="STOP")
                                            Retry = False
                                            success.append(" - Initiate DB VM shutdown for {}".format(resource.display_name))
                                        except oci.exceptions.ServiceError as response:
                                            if response.status == 429:
                                                MakeLog("Rate limit kicking in.. waiting {} seconds...".format(RateLimitDelay))
                                                time.sleep(RateLimitDelay)
                                            else:
                                                ErrorsFound = True
                                                errors.append(" - Error ({}) DB VM shutdown for {} - {}".format(response.status, resource.display_name, response.message))
                                                Retry = False
                            if dbnodedetails.lifecycle_state == "STOPPED" and int(schedulehours[CurrentHour]) == 1:
                                if Action == "All" or Action == "Up":
                                    MakeLog(" - Initiate DB VM startup for {}".format(resource.display_name))
                                    Retry = True
                                    while Retry:
                                        try:
                                            response = database.db_node_action(db_node_id=dbnodedetails.id, action="START")
                                            Retry = False
                                            success.append(" - Initiate DB VM startup for {}".format(resource.display_name))
                                        except oci.exceptions.ServiceError as response:
                                            if response.status == 429:
                                                MakeLog("Rate limit kicking in.. waiting {} seconds...".format(RateLimitDelay))
                                                time.sleep(RateLimitDelay)
                                            else:
                                                ErrorsFound = True
                                                errors.append(" - Error ({}) DB VM startup for {} - {}".format(response.status, resource.display_name, response.message))
                                                Retry = False

                    # Execute CPU Scale Up/Down operations for Database BMs
                    if resourceDetails.shape[:2] == "BM":
                        if int(schedulehours[CurrentHour]) > 1 and int(schedulehours[CurrentHour]) < 53:
                            if resourceDetails.cpu_core_count > int(schedulehours[CurrentHour]):
                                if Action == "All" or Action == "Down":
                                    MakeLog(" - Initiate DB BM Scale Down to {} for {}".format(int(schedulehours[CurrentHour]),resource.display_name))
                                    dbupdate = oci.database.models.UpdateDbSystemDetails()
                                    dbupdate.cpu_core_count = int(schedulehours[CurrentHour])
                                    Retry = True
                                    while Retry:
                                        try:
                                            response = database.update_db_system(db_system_id=resource.identifier, update_db_system_details=dbupdate)
                                            Retry = False
                                            success.append(" - Initiate DB BM Scale Down from {}to {} for {}".format(resourceDetails.cpu_core_count, (schedulehours[CurrentHour]),resource.display_name))
                                        except oci.exceptions.ServiceError as response:
                                            if response.status == 429:
                                                MakeLog("Rate limit kicking in.. waiting {} seconds...".format(RateLimitDelay))
                                                time.sleep(RateLimitDelay)
                                            else:
                                                ErrorsFound = True
                                                errors.append(" - Error ({}) DB BM Scale Down from {} to {} for {} - {}".format(response.status, resourceDetails.cpu_core_count, int(schedulehours[CurrentHour]),resource.display_name, response.message))
                                                MakeLog(" - Error ({}) DB BM Scale Down from {} to {} for {} - {}".format(response.status, resourceDetails.cpu_core_count, int(schedulehours[CurrentHour]),resource.display_name, response.message))
                                                Retry = False

                            if resourceDetails.cpu_core_count < int(schedulehours[CurrentHour]):
                                if Action == "All" or Action == "Up":
                                    MakeLog(" - Initiate DB BM Scale UP to {} for {}".format(int(schedulehours[CurrentHour]),resource.display_name))
                                    dbupdate = oci.database.models.UpdateDbSystemDetails()
                                    dbupdate.cpu_core_count = int(schedulehours[CurrentHour])
                                    Retry = True
                                    while Retry:
                                        try:
                                            response = database.update_db_system(db_system_id=resource.identifier, update_db_system_details=dbupdate)
                                            Retry = False
                                            success.append(" - Initiate DB BM Scale UP from {} to {} for {}".format(resourceDetails.cpu_core_count, int(schedulehours[CurrentHour]),resource.display_name))
                                        except oci.exceptions.ServiceError as response:
                                            if response.status == 429:
                                                MakeLog("Rate limit kicking in.. waiting {} seconds...".format(RateLimitDelay))
                                                time.sleep(RateLimitDelay)
                                            else:
                                                ErrorsFound = True
                                                errors.append(" - Error ({}) DB BM Scale UP from {} to {} for {} - {}".format(response.status, resourceDetails.cpu_core_count, int(schedulehours[CurrentHour]),resource.display_name, response.message))
                                                MakeLog(" - Error ({}) DB BM Scale UP from {} to {} for {} - {}".format(response.status, resourceDetails.cpu_core_count, int(schedulehours[CurrentHour]),resource.display_name, response.message))
                                                Retry = False

                    if resourceDetails.shape[:7] == "Exadata":
                        if resourceDetails.cpu_core_count > int(schedulehours[CurrentHour]):
                            if Action == "All" or Action == "Down":
                                MakeLog(" - Initiate Exadata CS Scale Down from {} to {} for {}".format(resourceDetails.cpu_core_count, int(schedulehours[CurrentHour]),resource.display_name))
                                dbupdate = oci.database.models.UpdateDbSystemDetails()
                                dbupdate.cpu_core_count = int(schedulehours[CurrentHour])
                                Retry = True
                                while Retry:
                                    try:
                                        response = database.update_db_system(db_system_id=resource.identifier, update_db_system_details=dbupdate)
                                        Retry = False
                                        success.append(" - Initiate Exadata DB Scale Down to {} for {}".format(resourceDetails.cpu_core_count, int(schedulehours[CurrentHour]),resource.display_name))
                                    except oci.exceptions.ServiceError as response:
                                        if response.status == 429:
                                            MakeLog("Rate limit kicking in.. waiting {} seconds...".format(RateLimitDelay))
                                            time.sleep(RateLimitDelay)
                                        else:
                                            ErrorsFound = True
                                            errors.append(" - Error ({}) Exadata DB Scale Down from {} to {} for {} - {}".format(response.status, resourceDetails.cpu_core_count, int(schedulehours[CurrentHour]),resource.display_name, response.message))
                                            MakeLog(" - Error ({}) Exadata DB Scale Down from {} to {} for {} - {}".format(response.status, resourceDetails.cpu_core_count, int(schedulehours[CurrentHour]),resource.display_name, response.message))
                                            Retry = False

                        if resourceDetails.cpu_core_count < int(schedulehours[CurrentHour]):
                            if Action == "All" or Action == "Up":
                                MakeLog(" - Initiate Exadata CS Scale UP from {} to {} for {}".format(resourceDetails.cpu_core_count,int(schedulehours[CurrentHour]),resource.display_name))
                                dbupdate = oci.database.models.UpdateDbSystemDetails()
                                dbupdate.cpu_core_count = int(schedulehours[CurrentHour])
                                Retry = True
                                while Retry:
                                    try:
                                        response = database.update_db_system(db_system_id=resource.identifier, update_db_system_details=dbupdate)
                                        Retry = False
                                        success.append(" - Initiate Exadata DB BM Scale UP from {} to {} for {}".format(resourceDetails.cpu_core_count,int(schedulehours[CurrentHour]),resource.display_name))
                                    except oci.exceptions.ServiceError as response:
                                        if response.status == 429:
                                            MakeLog("Rate limit kicking in.. waiting {} seconds...".format(RateLimitDelay))
                                            time.sleep(RateLimitDelay)
                                        else:
                                            ErrorsFound = True
                                            errors.append(" - Error ({}) Exadata DB Scale Up from {} to {} for {} - {}".format(response.status, resourceDetails.cpu_core_count,int(schedulehours[CurrentHour]), resource.display_name,response.message))
                                            MakeLog(" - Error ({}) Exadata DB Scale Up from {} to {} for {} - {}".format(response.status, resourceDetails.cpu_core_count,int(schedulehours[CurrentHour]), resource.display_name,response.message))
                                            Retry = False

                # Execute Scaling operations for Cloud@customer Exadata Cluster VM
                if resource.resource_type == "VmCluster":
                    if int(schedulehours[CurrentHour]) >= 0 and int(schedulehours[CurrentHour]) < 401:
                        # Cluster VM is running, request is amount of CPU core change is needed
                        if resourceDetails.lifecycle_state == "AVAILABLE" and int(schedulehours[CurrentHour]) > 0:
                            if resourceDetails.cpus_enabled > int(schedulehours[CurrentHour]):
                                if Action == "All" or Action == "Down":
                                    MakeLog(" - Initiate ExadataC@C VM Cluster Scale Down to {} for {}".format(int(schedulehours[CurrentHour]), resource.display_name))
                                    dbupdate = oci.database.models.UpdateVmClusterDetails()
                                    dbupdate.cpu_core_count = int(schedulehours[CurrentHour])
                                    Retry = True
                                    while Retry:
                                        try:
                                            response = database.update_vm_cluster(vm_cluster_id=resource.identifier, update_vm_cluster_details=dbupdate)
                                            Retry = False
                                            success.append(" - Initiate ExadataC&C Cluster VM Scale Down from {} to {} for {}".format(resourceDetails.cpus_enabled, int(schedulehours[CurrentHour]), resource.display_name))
                                        except oci.exceptions.ServiceError as response:
                                            if response.status == 429:
                                                MakeLog("Rate limit kicking in.. waiting {} seconds...".format(RateLimitDelay))
                                                time.sleep(RateLimitDelay)
                                            else:
                                                ErrorsFound = True
                                                errors.append(" - Error ({}) ExadataC&C Cluster VM Scale Down from {} to {} for {} - {}".format(response.status, resourceDetails.cpus_enabled, int(schedulehours[CurrentHour]),resource.display_name, response.message))
                                                MakeLog(" - Error ({}) ExadataC&C Cluster VM Scale Down from {} to {} for {} - {}".format(response.status, resourceDetails.cpus_enabled, int(schedulehours[CurrentHour]),resource.display_name, response.message))
                                                Retry = False

                            if resourceDetails.cpus_enabled < int(schedulehours[CurrentHour]):
                                if Action == "All" or Action == "Up":
                                    MakeLog(" - Initiate ExadataC@C VM Cluster Scale Up from {} to {} for {}".format(resourceDetails.cpus_enabled, int(schedulehours[CurrentHour]), resource.display_name))
                                    dbupdate = oci.database.models.UpdateVmClusterDetails()
                                    dbupdate.cpu_core_count = int(schedulehours[CurrentHour])
                                    Retry = True
                                    while Retry:
                                        try:
                                            response = database.update_vm_cluster(vm_cluster_id=resource.identifier, update_vm_cluster_details=dbupdate)
                                            Retry = False
                                            success.append(" - Initiate ExadataC&C Cluster VM Scale Up to {} for {}".format(int(schedulehours[CurrentHour]), resource.display_name))
                                        except oci.exceptions.ServiceError as response:
                                            if response.status == 429:
                                                MakeLog("Rate limit kicking in.. waiting {} seconds...".format(RateLimitDelay))
                                                time.sleep(RateLimitDelay)
                                            else:
                                                ErrorsFound = True
                                                errors.append(" - Error ({}) ExadataC&C Cluster VM Scale Up from {} to {} for {} - {}".format(response.status, resourceDetails.cpus_enabled, int(schedulehours[CurrentHour]), resource.display_name, response.message))
                                                MakeLog(" - Error ({}) ExadataC&C Cluster VM Scale Up from {} to {} for {} - {}".format(response.status, resourceDetails.cpus_enabled, int(schedulehours[CurrentHour]), resource.display_name, response.message))
                                                Retry = False

                # Execute CPU Scale Up/Down operations for Database BMs
                if resource.resource_type == "AutonomousDatabase":
                    if int(schedulehours[CurrentHour]) >= 0 and int(schedulehours[CurrentHour]) < 129:
                        # Autonomous DB is running request is amount of CPU core change is needed
                        if resourceDetails.lifecycle_state == "AVAILABLE" and int(schedulehours[CurrentHour]) > 0:
                            if resourceDetails.cpu_core_count > int(schedulehours[CurrentHour]):
                                if Action == "All" or Action == "Down":
                                    MakeLog(" - Initiate Autonomous DB Scale Down to {} for {}".format(int(schedulehours[CurrentHour]),
                                                                                                 resource.display_name))
                                    dbupdate = oci.database.models.UpdateAutonomousDatabaseDetails()
                                    dbupdate.cpu_core_count = int(schedulehours[CurrentHour])
                                    Retry = True
                                    while Retry:
                                        try:
                                            response = database.update_autonomous_database(autonomous_database_id=resource.identifier, update_autonomous_database_details=dbupdate)
                                            Retry = False
                                            success.append(" - Initiate Autonomous DB Scale Down from {} to {} for {}".format(resourceDetails.cpu_core_count, int(schedulehours[CurrentHour]), resource.display_name))
                                        except oci.exceptions.ServiceError as response:
                                            if response.status == 429:
                                                MakeLog("Rate limit kicking in.. waiting {} seconds...".format(RateLimitDelay))
                                                time.sleep(RateLimitDelay)
                                            else:
                                                ErrorsFound = True
                                                errors.append(" - Error ({}) Autonomous DB Scale Down from {} to {} for {} - {}".format(response.status, resourceDetails.cpu_core_count, int(schedulehours[CurrentHour]),resource.display_name, response.message))
                                                MakeLog(" - Error ({}) Autonomous DB Scale Down from {} to {} for {} - {}".format(response.status, resourceDetails.cpu_core_count, int(schedulehours[CurrentHour]),resource.display_name, response.message))
                                                Retry = False

                            if resourceDetails.cpu_core_count < int(schedulehours[CurrentHour]):
                                if Action == "All" or Action == "Up":
                                    MakeLog(" - Initiate Autonomous DB Scale Up from {} to {} for {}".format(resourceDetails.cpu_core_count, int(schedulehours[CurrentHour]),
                                                                                                         resource.display_name))
                                    dbupdate = oci.database.models.UpdateAutonomousDatabaseDetails()
                                    dbupdate.cpu_core_count = int(schedulehours[CurrentHour])
                                    Retry = True
                                    while Retry:
                                        try:
                                            response = database.update_autonomous_database(autonomous_database_id=resource.identifier,
                                                                                   update_autonomous_database_details=dbupdate)
                                            Retry = False
                                            success.append(" - Initiate Autonomous DB Scale Up to {} for {}".format(
                                                int(schedulehours[CurrentHour]), resource.display_name))
                                        except oci.exceptions.ServiceError as response:
                                            if response.status == 429:
                                                MakeLog("Rate limit kicking in.. waiting {} seconds...".format(RateLimitDelay))
                                                time.sleep(RateLimitDelay)
                                            else:
                                                ErrorsFound = True
                                                errors.append(" - Error ({}) Autonomous DB Scale Up from {} to {} for {} - {}".format(response.status, resourceDetails.cpu_core_count, int(schedulehours[CurrentHour]), resource.display_name, response.message))
                                                MakeLog(" - Error ({}) Autonomous DB Scale Up from {} to {} for {} - {}".format(response.status, resourceDetails.cpu_core_count,int(schedulehours[CurrentHour]), resource.display_name, response.message))
                                                Retry = False

                        # Autonomous DB is running request is to stop the database
                        if resourceDetails.lifecycle_state == "AVAILABLE" and int(schedulehours[CurrentHour]) == 0:
                            if Action == "All" or Action == "Down":
                                MakeLog(" - Stoping Autonomous DB {}".format(resource.display_name))
                                Retry = True
                                while Retry:
                                    try:
                                        response= database.stop_autonomous_database(autonomous_database_id=resource.identifier)
                                        Retry = False
                                        success.append(" - Initiate Autonomous DB Shutdown for {}".format(resource.display_name))
                                    except oci.exceptions.ServiceError as response:
                                        if response.status == 429:
                                            MakeLog("Rate limit kicking in.. waiting {} seconds...".format(RateLimitDelay))
                                            time.sleep(RateLimitDelay)
                                        else:
                                            ErrorsFound = True
                                            errors.append(" - Error ({}) Autonomous DB Shutdown for {} - {}".format(response.status, resource.display_name, response.message))
                                            MakeLog(" - Error ({}) Autonomous DB Shutdown for {} - {}".format(response.status, resource.display_name, response.message))
                                            Retry = False

                        if resourceDetails.lifecycle_state == "STOPPED" and int(schedulehours[CurrentHour]) > 0:
                            if Action == "All" or Action == "Up":
                                # Autonomous DB is stopped and needs to be started with same amount of CPUs configured
                                if resourceDetails.cpu_core_count == int(schedulehours[CurrentHour]):
                                    MakeLog(" - Starting Autonomous DB {}".format(resource.display_name))
                                    Retry = True
                                    while Retry:
                                        try:
                                            response = database.start_autonomous_database(autonomous_database_id=resource.identifier)
                                            Retry = False
                                            success.append(" - Initiate Autonomous DB Startup for {}".format(resource.display_name))
                                        except oci.exceptions.ServiceError as response:
                                            if response.status == 429:
                                                MakeLog("Rate limit kicking in.. waiting {} seconds...".format(RateLimitDelay))
                                                time.sleep(RateLimitDelay)
                                            else:
                                                ErrorsFound = True
                                                errors.append(" - Error ({}) Autonomous DB Startup for {} - {}".format(response.status,resource.display_name, response.message))
                                                MakeLog(" - Error ({}) Autonomous DB Startup for {} - {}".format(response.status,resource.display_name, response.message))
                                                Retry = False

                                # Autonomous DB is stopped and needs to be started, after that it requires CPU change
                                if resourceDetails.cpu_core_count != int(schedulehours[CurrentHour]):
                                    tcount = tcount + 1
                                    thread = AutonomousThread(tcount, resource.identifier, resource.display_name , int(schedulehours[CurrentHour]))
                                    thread.start()
                                    threads.append(thread)

                if resource.resource_type == "InstancePool":
                    # Stop Resource pool action
                    if resourceDetails.lifecycle_state == "RUNNING" and int(schedulehours[CurrentHour]) == 0:
                        if Action == "All" or Action == "Down":
                            success.append(" - Stopping instance pool {}".format(resource.display_name))
                            MakeLog(" - Stopping instance pool {}".format(resource.display_name))
                            Retry = True
                            while Retry:
                                try:
                                    response = pool.stop_instance_pool(instance_pool_id=resource.identifier)
                                    Retry = False
                                    success.append(" - Stopping instance pool {}".format(resource.display_name))
                                except oci.exceptions.ServiceError as response:
                                    if response.status == 429:
                                        MakeLog("Rate limit kicking in.. waiting {} seconds...".format(RateLimitDelay))
                                        time.sleep(RateLimitDelay)
                                    else:
                                        ErrorsFound = True
                                        errors.append(" - Error ({}) Stopping instance pool for {} - {}".format(response.status,resource.display_name, response.message))
                                        MakeLog(" - Error ({}) Stopping instance pool for {} - {}".format(response.status,resource.display_name, response.message))
                                        Retry = False

                    # Scale up action on running instance pool
                    elif resourceDetails.lifecycle_state == "RUNNING" and int(schedulehours[CurrentHour]) > resourceDetails.size:
                        if Action == "All" or Action == "Up":
                            MakeLog(" - Scaling up instance pool {} to {} instances".format(resource.display_name, int(schedulehours[CurrentHour])))
                            pooldetails = oci.core.models.UpdateInstancePoolDetails()
                            pooldetails.size = int(schedulehours[CurrentHour])
                            Retry = True
                            while Retry:
                                try:
                                    response = pool.update_instance_pool(instance_pool_id=resource.identifier, update_instance_pool_details=pooldetails)
                                    Retry = False
                                    success.append(" - Scaling up instance pool {} to {} instances".format(resource.display_name, int(schedulehours[CurrentHour])))
                                except oci.exceptions.ServiceError as response:
                                    if response.status == 429:
                                        MakeLog("Rate limit kicking in.. waiting {} seconds...".format(RateLimitDelay))
                                        time.sleep(RateLimitDelay)
                                    else:
                                        ErrorsFound = True
                                        errors.append(" - Error ({}) Scaling up instance pool {} to {} instances - {}".format(response.status, resource.display_name, int(schedulehours[CurrentHour]), response.message))
                                        Retry = False

                    # Scale down action on running instance pool
                    elif resourceDetails.lifecycle_state == "RUNNING" and int(schedulehours[CurrentHour]) < resourceDetails.size:
                        if Action == "All" or Action == "Down":
                            MakeLog(" - Scaling down instance pool {} to {} instances".format(resource.display_name, int(schedulehours[CurrentHour]) ))
                            pooldetails = oci.core.models.UpdateInstancePoolDetails()
                            pooldetails.size = int(schedulehours[CurrentHour])
                            Retry = True
                            while Retry:
                                try:
                                    response = pool.update_instance_pool(instance_pool_id=resource.identifier, update_instance_pool_details=pooldetails)
                                    Retry = False
                                    success.append(" - Scaling down instance pool {} to {} instances".format(resource.display_name, int(schedulehours[CurrentHour])))
                                except oci.exceptions.ServiceError as response:
                                    if response.status == 429:
                                        MakeLog("Rate limit kicking in.. waiting {} seconds...".format(RateLimitDelay))
                                        time.sleep(RateLimitDelay)
                                    else:
                                        ErrorsFound = True
                                        errors.append(" - Error ({}) Scaling down instance pool {} to {} instances - {}".format(response.status,resource.display_name,int(schedulehours[CurrentHour]), response.message))
                                        Retry = False

                    elif resourceDetails.lifecycle_state == "STOPPED" and int(schedulehours[CurrentHour]) > 0:
                        if Action == "All" or Action == "Up":
                            # Start instance pool with same amount of instances as configured
                            if resourceDetails.size == int(schedulehours[CurrentHour]):
                                success.append(" - Starting instance pool {} from stopped state".format(resource.display_name))
                                MakeLog(" - Starting instance pool {} from stopped state".format(resource.display_name))
                                Retry = True
                                while Retry:
                                    try:
                                        response = pool.start_instance_pool(instance_pool_id=resource.identifier)
                                        Retry = False
                                        success.append(" - Starting instance pool {} from stopped state".format(resource.display_name))
                                    except oci.exceptions.ServiceError as response:
                                        if response.status == 429:
                                            MakeLog("Rate limit kicking in.. waiting {} seconds...".format(RateLimitDelay))
                                            time.sleep(RateLimitDelay)
                                        else:
                                            ErrorsFound = True
                                            errors.append(" - Error ({}) Starting instance pool {} from stopped state - {}".format(response.status, resource.display_name, response.message))
                                            Retry = False

                            # Start instance pool and after that resize the instance pool to desired state:
                            if resourceDetails.size != int(schedulehours[CurrentHour]):
                                tcount = tcount + 1
                                thread = PoolThread(tcount, resource.identifier, resource.display_name,int(schedulehours[CurrentHour]))
                                thread.start()
                                threads.append(thread)
                if resource.resource_type == "OdaInstance":
                    if int(schedulehours[CurrentHour]) == 0 or int(schedulehours[CurrentHour]) == 1:
                        if resourceDetails.lifecycle_state == "ACTIVE" and int(schedulehours[CurrentHour]) == 0:
                            if Action == "All" or Action == "Down":
                                MakeLog(" - Initiate ODA shutdown for {}".format(resource.display_name))
                                Retry = True
                                while Retry:
                                    try:
                                        response = oda.stop_oda_instance(oda_instance_id=resource.identifier)
                                        Retry = False
                                        success.append(" - Initiate ODA shutdown for {}".format(resource.display_name))
                                    except oci.exceptions.ServiceError as response:
                                        if response.status == 429:
                                            MakeLog("Rate limit kicking in.. waiting {} seconds...".format(RateLimitDelay))
                                            time.sleep(RateLimitDelay)
                                        else:
                                            ErrorsFound = True
                                            errors.append(" - Error ({}) ODA Shutdown for {} - {}".format(response.status, resource.display_name, response.message))
                                            MakeLog(" - Error ({}) ODA Shutdown for {} - {}".format(response.status, resource.display_name, response.message))
                                            Retry = False

                        if resourceDetails.lifecycle_state == "INACTIVE" and int(schedulehours[CurrentHour]) == 1:
                            if Action == "All" or Action == "Up":
                                MakeLog(" - Initiate ODA startup for {}".format(resource.display_name))
                                Retry = True
                                while Retry:
                                    try:
                                        response = oda.start_oda_instance(oda_instance_id=resource.identifier)
                                        Retry = False
                                        success.append(" - Initiate ODA startup for {}".format(resource.display_name))
                                    except oci.exceptions.ServiceError as response:
                                        if response.status == 429:
                                            MakeLog("Rate limit kicking in.. waiting {} seconds...".format(RateLimitDelay))
                                            time.sleep(RateLimitDelay)
                                        else:
                                            ErrorsFound = True
                                            errors.append(" - Error ({}) ODA startup for {} - {}".format(response.status, resource.display_name, response.message))
                                            MakeLog(" - Error ({}) ODA startup for {} - {}".format(response.status, resource.display_name, response.message))
                                            Retry = False

                if resource.resource_type == "AnalyticsInstance":
                    # Execute Shutdown operations
                    if int(schedulehours[CurrentHour]) == 0 and resourceDetails.lifecycle_state == "ACTIVE":
                        if Action == "All" or Action == "Down":
                            MakeLog(" - Initiate Analytics shutdown for {}".format(resource.display_name))
                            Retry = True
                            while Retry:
                                try:
                                    response = analytics.stop_analytics_instance(analytics_instance_id=resource.identifier)
                                    Retry = False
                                    success.append(" - Initiate ODA shutdown for {}".format(resource.display_name))
                                except oci.exceptions.ServiceError as response:
                                    if response.status == 429:
                                        MakeLog("Rate limit kicking in.. waiting {} seconds...".format(RateLimitDelay))
                                        time.sleep(RateLimitDelay)
                                    else:
                                        ErrorsFound = True
                                        errors.append(" - Error ({}) Analytics Shutdown for {} - {}".format(response.status, resource.display_name, response.message))
                                        MakeLog(" - Error ({}) Analytics Shutdown for {} - {}".format(response.status, resource.display_name, response.message))
                                        Retry = False

                    # Execute Startup operations
                    if int(schedulehours[CurrentHour]) != 0 and resourceDetails.lifecycle_state == "INACTIVE":
                        if Action == "All" or Action == "Up":
                            if int(resourceDetails.capacity.capacity_value) == int(schedulehours[CurrentHour]):
                                MakeLog(" - Initiate Analytics Startup for {}".format(resource.display_name))
                                Retry = True
                                while Retry:
                                    try:
                                        response = analytics.start_analytics_instance(analytics_instance_id=resource.identifier)
                                        Retry = False
                                        success.append(" - Initiate Analytics Startup for {}".format(resource.display_name))
                                    except oci.exceptions.ServiceError as response:
                                        if response.status == 429:
                                            MakeLog("Rate limit kicking in.. waiting {} seconds...".format(RateLimitDelay))
                                            time.sleep(RateLimitDelay)
                                        else:
                                            ErrorsFound = True
                                            errors.append(" - Error ({}) Analytics Startup for {} - {}".format(response.status, resource.display_name, response.message))
                                            MakeLog(" - Error ({}) Analytics Startup for {} - {}".format(response.status, resource.display_name, response.message))
                                            Retry = False

                            # Execute Startup and scaling operations
                            else:
                                tcount = tcount + 1
                                thread = AnalyticsThread(tcount, resource.identifier, resource.display_name,int(schedulehours[CurrentHour]))
                                thread.start()
                                threads.append(thread)

                    # Execute scaling operations on running instance
                    if resourceDetails.lifecycle_state == "ACTIVE" and int(schedulehours[CurrentHour]) != int(resourceDetails.capacity.capacity_value):
                        if int(resourceDetails.capacity.capacity_value) == 1 or int(resourceDetails.capacity.capacity_value) > 12:
                            ErrorsFound = True
                            errors.append(
                                " - Error (Analytics instance with CPU count {} can not be scaled for instance: {}".format(int(resourceDetails.capacity.capacity_value), resource.display_name))
                            MakeLog(
                                " - Error (Analytics instance with CPU count {} can not be scaled for instance: {}".format(int(resourceDetails.capacity.capacity_value), resource.display_name))
                        goscale = False
                        if (int(schedulehours[CurrentHour]) >= 2 and int(schedulehours[CurrentHour]) <=8) and (int(resourceDetails.capacity.capacity_value) >=2 and int(resourceDetails.capacity.capacity_value) <=8):
                            capacity = oci.analytics.models.capacity.Capacity()
                            capacity.capacity_value = int(schedulehours[CurrentHour])
                            capacity.capacity_type = capacity.CAPACITY_TYPE_OLPU_COUNT
                            details = oci.analytics.models.ScaleAnalyticsInstanceDetails()
                            details.capacity = capacity
                            goscale = True

                        if (int(schedulehours[CurrentHour]) >= 10 and int(schedulehours[CurrentHour]) <= 12) and (
                                int(resourceDetails.capacity.capacity_value) >= 10 and int(
                                resourceDetails.capacity.capacity_value) <= 12):
                            capacity = oci.analytics.models.capacity.Capacity()
                            capacity.capacity_value = int(schedulehours[CurrentHour])
                            capacity.capacity_type = capacity.CAPACITY_TYPE_OLPU_COUNT
                            details = oci.analytics.models.ScaleAnalyticsInstanceDetails()
                            details.capacity = capacity
                            goscale = True

                        if goscale:
                            goscale = False
                            if Action == "All":
                                goscale = True
                            elif int(resourceDetails.capacity.capacity_value) < int(schedulehours[CurrentHour]) and Action == "Up":
                                goscale = True
                            elif int(resourceDetails.capacity.capacity_value) > int(schedulehours[CurrentHour]) and Action == "Down":
                                goscale = True

                            if goscale:
                                MakeLog(" - Initiate Analytics Scaling from {} to {}oCPU for {}".format(
                                    int(resourceDetails.capacity.capacity_value), int(schedulehours[CurrentHour]),
                                    resource.display_name))
                                Retry = True
                                while Retry:
                                    try:
                                        response = analytics.scale_analytics_instance(analytics_instance_id=resource.identifier,scale_analytics_instance_details=details)
                                        Retry = False
                                        success.append(" - Initiate Analytics Scaling from {} to {}oCPU for {}".format(int(resourceDetails.capacity.capacity_value), int(schedulehours[CurrentHour]), resource.display_name))
                                    except oci.exceptions.ServiceError as response:
                                        if response.status == 429:
                                            MakeLog("Rate limit kicking in.. waiting {} seconds...".format(RateLimitDelay))
                                            time.sleep(RateLimitDelay)
                                        else:
                                            ErrorsFound = True
                                            errors.append(
                                                " - Error ({}) Analytics scaling from {} to {}oCPU for {} - {}".format(response.status, int(resourceDetails.capacity.capacity_value), int(schedulehours[CurrentHour]),
                                                                                                resource.display_name, response.message))
                                            MakeLog(
                                                " - Error ({}) Analytics scaling from {} to {}oCPU for {} - {}".format(response.status, int(resourceDetails.capacity.capacity_value), int(schedulehours[CurrentHour]),
                                                                                                resource.display_name, response.message))
                                            Retry = False
                        else:
                            errors.append(
                                " - Error (Analytics scaling from {} to {}oCPU, invalid combination for {}".format(int(
                                    resourceDetails.capacity.capacity_value), int(schedulehours[CurrentHour]),
                                                                                                  resource.display_name))
                            MakeLog(
                                " - Error (Analytics scaling from {} to {}oCPU, invalid combination for {}".format(int(
                                    resourceDetails.capacity.capacity_value), int(schedulehours[CurrentHour]),
                                                                                                  resource.display_name))
                if resource.resource_type == "IntegrationInstance":
                    if int(schedulehours[CurrentHour]) == 0 or int(schedulehours[CurrentHour]) == 1:
                        resourceDetails = integration.get_integration_instance(integration_instance_id=resource.identifier).data

                        if resourceDetails.lifecycle_state == "ACTIVE" and int(schedulehours[CurrentHour]) == 0:
                            if Action == "All" or Action == "Down":
                                MakeLog(" - Initiate Integration Service shutdown for {}".format(resource.display_name))
                                Retry = True
                                while Retry:
                                    try:
                                        response = integration.stop_integration_instance(integration_instance_id=resource.identifier)
                                        Retry = False
                                        success.append(" - Initiate Integration Service shutdown for {}".format(resource.display_name))
                                    except oci.exceptions.ServiceError as response:
                                        if response.status == 429:
                                            MakeLog("Rate limit kicking in.. waiting {} seconds...".format(RateLimitDelay))
                                            time.sleep(RateLimitDelay)
                                        else:
                                            ErrorsFound = True
                                            errors.append(" - Error ({}) Integration Service Shutdown for {} - {}".format(response.status, resource.display_name, response.message))
                                            MakeLog(" - Error ({}) Integration Service Shutdown for {} - {}".format(response.status, resource.display_name, response.message))
                                            Retry = False

                        if resourceDetails.lifecycle_state == "INACTIVE" and int(schedulehours[CurrentHour]) == 1:
                            if Action == "All" or Action == "Up":
                                MakeLog(" - Initiate Integration Service startup for {}".format(resource.display_name))
                                Retry = True
                                while Retry:
                                    try:
                                        response = integration.start_integration_instance(integration_instance_id=resource.identifier)
                                        Retry = False
                                        success.append(" - Initiate Integration Service startup for {}".format(resource.display_name))
                                    except oci.exceptions.ServiceError as response:
                                        if response.status == 429:
                                            MakeLog("Rate limit kicking in.. waiting {} seconds...".format(RateLimitDelay))
                                            time.sleep(RateLimitDelay)
                                        else:
                                            ErrorsFound = True
                                            errors.append(" - Error ({}) Integration Service startup for {} - {}".format(response.message, resource.display_name, response.message))
                                            MakeLog(" - Error ({}) Integration Service startup for {} - {}".format(response.message, resource.display_name, response.message))
                                            Retry = False

                if resource.resource_type == "LoadBalancer":
                    requestedShape = int(schedulehours[CurrentHour])
                    shape = 0
                    if resourceDetails.shape_name == "10Mbps":
                        shape = 10
                    if resourceDetails.shape_name == "100Mbps":
                        shape = 100
                    if resourceDetails.shape_name == "400Mbps":
                        shape = 400
                    if resourceDetails.shape_name == "8000Mbps":
                        shape = 8000
                    if requestedShape == 10 or requestedShape == 100 or requestedShape == 400 or requestedShape == 8000:
                        if requestedShape < shape:
                            if Action == "All" or Action == "Down":
                                details = oci.load_balancer.models.UpdateLoadBalancerShapeDetails()
                                details.shape_name = "{}Mbps".format(requestedShape)
                                MakeLog(" - Downsizing loadbalancer from {} to {}".format(resourceDetails.shape_name, details.shape_name))
                                try:
                                    loadbalancer.update_load_balancer_shape(load_balancer_id=resource.identifier, update_load_balancer_shape_details=details)
                                except oci.exceptions.ServiceError as response:
                                    MakeLog (" - Error Downsizing: {}".format(response.message))
                                    errors.append(" - Error ({}) Integration Service startup for {}".format(response.message, resource.display_name))

                        if requestedShape > shape:
                            if Action == "All" or Action == "Up":
                                details = oci.load_balancer.models.UpdateLoadBalancerShapeDetails()
                                details.shape_name = "{}Mbps".format(requestedShape)
                                MakeLog(" - Upsizing loadbalancer from {} to {}".format(resourceDetails.shape_name, details.shape_name))
                                try:
                                    loadbalancer.update_load_balancer_shape(load_balancer_id=resource.identifier, update_load_balancer_shape_details=details)
                                except oci.exceptions.ServiceError as response:
                                    MakeLog (" - Error Upsizing: {} ".format(response.message))
                                    errors.append(" - Error ({}) Integration Service startup for {}".format(response.message, resource.display_name))

                    else:
                        MakeLog(" - Error {}: requested shape {} does not exists".format(resource.display_name, requestedShape))

# Wait for any AutonomousDB and Instance Pool Start and rescale tasks completed
for t in threads:
   t.join()

if len(TopicID) > 0:

    if LogLevel == "ALL" or (LogLevel == "ERRORS" and ErrorsFound):
        MakeLog("Publishing notification")
        body_message = "Scaling ({}) just completed. Found {} errors across {} scaleable instances (from a total of {} instances). \nError Details: {}\n\nSuccess Details: {}".format(Action, len(errors),len(success),total_resources,errors,success)
        Retry = True
        while Retry:
            try:
                response = ns.publish_message(TopicID, {"title": "Scaling Script ran across tenancy: {}".format(Tenancy.name),"body": body_message})
                Retry = False
            except oci.exceptions.ServiceError as response:
                if response.status == 429:
                    MakeLog("Rate limit kicking in.. waiting {} seconds...".format(RateLimitDelay))
                    time.sleep(RateLimitDelay)
                else:
                    MakeLog("Error ({}) publishing notification - {}".format(response.status, response.message))
                    Retry = False

MakeLog ("All scaling tasks done")

