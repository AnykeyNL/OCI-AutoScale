# OCI-AutoScale

Welcome to the Scheduled Auto Scaling Script for OCI (Oracle Cloud Infrastructure).

**NEW AutoScaleALL:** A single Auto Scaling script for all resources that support scaling and on/off operations.

# Supported services
- Compute VMs: On/Off
- Instance Pools: On/Off and Scaling (# of instances)
- Database VMs: On/Off
- Database Baremetal Servers: Scaling (# of CPUs)
- Autonomous Database: On/Off and Scaling (# of CPUs)

# How to use
To control what you want to scale or auto power on/off, you need to create a predefined tag called "Schedule". If you want to
localize this, that is possible in the script. For the predefined tag, you need entries for the days of the week, weekdays, weekends and anyday.

The value of the tag needs to contain 24 numbers, seperated by commas. If the value is a 0 it will power off the resource,
if that is supported. Any number higher then 0 will re-scale the resource to that number. If the resource is
powered off, it first will power-on the resource and then scale to the correct size.

![Scaling Example](https://www.oc-blog.com/wp-content/uploads/2018/09/atp_scale-1024x445.png)

The script supports 3 running methods: All, Up, Down

- All: This will execute any scaling and power on/off operation
- Down: This will execute only power off and scaling down operations
-Up: This will execute only power on and scaling up operations

The thinking behind this is that most OCI resources are charged per hour. So you likely want to run scale down / power off operations 
just before the end of the hour and run power on and scale up operations just after the hour.

To ensure the script runs as fast as possible, all blocking operations (power on, wait to be available and then re-scale) are executed in a seperate thread. I would recommend you run scaling down actions 1 or 2 minutes before the end of the hour and run scaling up actions just after the hour.

# Single service Autoscaling Scripts:
-**AutoscaleDBBM;** this script is designed to run inside the Baremetal instances running the Oracle Database Cloud Service.
-**Autoscale_AWD_ATP;** this script is designed to scale ALL ADW and ATP services that have a valid Schedule tag. You need to run this script somewere that has internet access so it can talk to the Oracle Cloud API. This can be in the cloud or on-premise. When 0 is specified the service will be turned off.
-**AutoOnOff_compute;** this script is designed to automatically power on / off compute instances based on the hour of the day. You need to run this script somewere that has internet access so it can talk to the Oracle Cloud API. This can be in the cloud or on-premise.


# More information
Please check www.oc-blog.com


## Disclaimer
This is a personal repository. Any code, views or opinions represented here are personal and belong solely to me and do not represent those of people, institutions or organizations that I may or may not be associated with in professional or personal capacity, unless explicitly stated.
