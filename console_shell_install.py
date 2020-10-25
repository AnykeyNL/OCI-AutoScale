import oci
import requests

signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()

try:
    url = "http://169.254.169.254/opc/v1/instance/"
    data = requests.get(url).json()
except:
    MakeLog("This instance is not running on OCI")
    exit()

if "CloudShell" in data['definedTags']:
    print ("Confirmed I am running in cloudshell :-)")
else:
    print ("I am not running in a cloudshell instancw")
    exit()

userOCID = data['freeformTags']['user-ocid']
rootCompartmentID = data['freeformTags']['user-tenancy-ocid']

print ("user OCID: {}".format(userOCID))
print ("root ID: {}".format(rootCompartmentID))

identity = oci.identity.IdentityClient(config={}, signer=signer)

compartments = identity.list_compartments(compartment_id=rootCompartmentID, compartment_id_in_subtree=True).data
print (compartments)


# query = "query vcn resources where lifeCycleState = 'AVAILABLE'"
# search = oci.resource_search.ResourceSearchClient(config={}, signer=signer)
#
# sdetails = oci.resource_search.models.StructuredSearchDetails()
# sdetails.query = query
# sdetails.type = "Structured"
#
# result = search.search_resources(search_details=sdetails, limit=1000).data
#
# if len(result.items) == 0:
#     print ("No VCN found, please first create one")
#     exit()
# counter = 0
# for item in result.items:
#     print ("{} : {}".format(counter, item.display_name))
#     counter = counter + 1
# x = input("Select VCN you want the Automation instance to run in: ")








