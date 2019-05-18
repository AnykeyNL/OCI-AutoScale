# OCI-AutoScale
There are 3 main Autoscaling Scripts here.

**Autoscale;** this script is designed to run inside the Baremetal instances running the Oracle Database Cloud Service.

**Autoscale_AWD_ATP;** this script is designed to scall ALL ADW and ATP services that have a valid Schedule tag. You need to run this script somewere that has internet access so it can talk to the Oracle Cloud API. This can be in the cloud or on-premise.

**AutoOnOff_compute;** this script is designed to automatically power on / off compute instances based on the hour of the day. You need to run this script somewere that has internet access so it can talk to the Oracle Cloud API. This can be in the cloud or on-premise.

# Auto Start and Stop
As the ATP and ADW services also support turning an instance on and off (and reducing cost), the AWD_ATP script supports this now.
If you specify and 0 (zero) for the hour, it will stop the service. If the services is stopped and the hour requires more then 0 cpu
cores, it will automatically start the instance and then scale it to the appropriate size.

As the starting takes some time, I have updated the ADW_ATP script with support for multi threading, so that all scaling actions happen at the same time, and not sequencially.

# How to use
Using pre-defined tags, you can schedule automatic scale up and down event.

Created a Tag Namespace called "Schedule"
In that namespace create the following Tag Key Definitions:
- AnyDay
- WeekDay
- Weekend
- Monday
- Tuesday
- Wednesday
- Thursday
- Friday
- Saturday
- Sunday

After that you can add the takes to any database instance you want to Autoscale based on a schedule. The tag should contain 24 numbers, sperated by commas. Each number represents the amount of CPUs for that specific hour.

# Running the Scripts
The script can be run without a parameter or with the parameter "up/down" or "on/off". If the "up/on" parameter is specified the script will only execute scaling Up / Power on actions. If "down/off" is specified, it will only do scaling Down and power off actions. If nothing is specified, the script will do BOTH scaling and power actions.

I would recommend you run scaling down actions 1 or 2 minutes before the end of the hour and run scaling up actions just after the hour.

![Scaling Example](https://www.oc-blog.com/wp-content/uploads/2018/09/atp_scale-1024x445.png)

# More information
Please check www.oc-blog.com

Demo video: https://youtu.be/5jsGgfClPAM


## Disclaimer
This is a personal repositorie. Any code, views or opinions represented here are personal and belong solely to me and do not represent those of people, institutions or organizations that I may or may not be associated with in professional or personal capacity, unless explicitly stated.
