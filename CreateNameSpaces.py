#!/home/opc/py36env/bin/python
# OCI - Create Namespace and key tags for Auto Scaling Script
#
# Copyright (c) 2016, 2022, Oracle and/or its affiliates.  All rights reserved.
# This software is licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl
#
# Written by: Richard Garsthagen
# Contributors: Joel Nation
#
# This script is designed to run inside an OCI instance, assigned with the right permissions to manage the tenancy

import oci
#import requests
import argparse
import OCIFunctions
import datetime

def MakeLog(msg):
    print (msg)


##########################################################################
# Main
##########################################################################
# Get Command Line Parser
parser = argparse.ArgumentParser()
parser.add_argument('-t', default="", dest='config_profile', help='Config file section to use (tenancy profile)')
parser.add_argument('-ip', action='store_true', default=False, dest='is_instance_principals', help='Use Instance Principals for Authentication')
parser.add_argument('-dt', action='store_true', default=False, dest='is_delegation_token', help='Use Delegation Token for Authentication')

cmd = parser.parse_args()

config, signer = OCIFunctions.create_signer(cmd.config_profile, cmd.is_instance_principals, cmd.is_delegation_token)

MakeLog("Starts at " + str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
MakeLog("\nConnecting to Identity Service...")
identity = oci.identity.IdentityClient(config, signer=signer)
tenancy = identity.get_tenancy(config["tenancy"]).data
regions = identity.list_region_subscriptions(tenancy.id).data

for reg in regions:
    if reg.is_home_region:
        tenancy_home_region = str(reg.region_name)

MakeLog("")
MakeLog("Tenant Name   : " + str(tenancy.name))
MakeLog("Tenant Id     : " + tenancy.id)
MakeLog("Home Region   : " + tenancy_home_region)

details = oci.identity.models.CreateTagNamespaceDetails()

details.compartment_id = tenancy.id
details.name = "Schedule"
details.description = "Namespace for schedule tags"

MakeLog("Creating Namespace Schedule")
response = identity.create_tag_namespace(create_tag_namespace_details=details).data
namespaceID = response.id

keys = ["AnyDay", "WeekDay", "Weekend", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", "DayOfMonth"]

MakeLog("Creating keys Schedule")
for key in keys:
    keydetails = oci.identity.models.CreateTagDetails()
    keydetails.name = key
    keydetails.description = "Schedule for {}".format(key)
    response = identity.create_tag(tag_namespace_id=namespaceID, create_tag_details=keydetails, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
    MakeLog("Key {} is created".format(key))

MakeLog("")
MakeLog ("Namespace and keys for scheduling have been created")



