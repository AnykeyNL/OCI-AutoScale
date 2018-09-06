# Get Instance Meta Data
# More info: https://docs.cloud.oracle.com/iaas/Content/Compute/Tasks/gettingmetadata.htm

try:
    # For Python 3.0 and later
    from urllib.request import urlopen
except ImportError:
    # Fall back to Python 2's urllib2
    from urllib2 import urlopen

import json

def get_jsonparsed_data(url):
    response = urlopen(url)
    data = response.read().decode("utf-8")
    return json.loads(data)

def get_metadata():
  url = "http://169.254.169.254/opc/v1/instance/"
  return get_jsonparsed_data(url)


