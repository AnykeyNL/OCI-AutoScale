#!/home/opc/py36env/bin/python
# OCI - Create Namespace and key tags for Auto Scaling Script
#
# Copyright (c) 2016, 2020, Oracle and/or its affiliates.  All rights reserved.
# This software is licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl
#
# Written by: Richard Garsthagen
# Contributors: Joel Nation
#
# This script is designed to run inside an OCI instance, assigned with the right permissions to manage the tenancy

import oci
import requests

signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()

UseInstancePrinciple = True

def MakeLog(msg):
    print (msg)

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

    while SearchRootID:
        compartment = identity.get_compartment(compartment_id=SearchCompID).data
        if compartment.compartment_id[:14] == "ocid1.tenancy.":
            RootCompartmentID = compartment.compartment_id
            SearchRootID = False
        else:
            SearchCompID = compartment.compartment_id

    Tenancy = identity.get_tenancy(tenancy_id=RootCompartmentID).data
    MakeLog("Logged in as: {}/{} @ {}".format(userName, Tenancy.name, region))

    details = oci.identity.models.CreateTagNamespaceDetails()

    details.compartment_id = RootCompartmentID
    details.name = "Schedule"
    details.description = "Namespace for schedule tags"

    print("Creating Namespace Schedule")
    response = identity.create_tag_namespace(create_tag_namespace_details=details).data
    namespaceID = response.id

    keys = ["AnyDay", "WeekDay", "Weekend", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    print("Creating keys Schedule")
    for key in keys:
        keydetails = oci.identity.models.CreateTagDetails()
        keydetails.name = key
        keydetails.description = "Schedule for {}".format(key)
        response = identity.create_tag(tag_namespace_id=namespaceID, create_tag_details=keydetails)

    print ("Namespace and keys for scheduling have been created")

else:
    print ("This script is designed to run inside OCI using Instance principal permissions")



