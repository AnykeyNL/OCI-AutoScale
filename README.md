# OCI-AutoScale
There are 2 main Autoscaling Scripts here.

Autoscale; this script is designed to run inside the Baremetal instances running the Oracle Database Cloud Service.
Autoscale_AWD_ATP; this script is designed to scall ALL ADW and ATP services that have a valid Schedule tag. You need to run this script somewere that has internet access so it can talk to the Oracle Cloud API. This can be in the cloud or on-premise.

Using pre-defined tags, you can schedule automatic scale up and down event.

# How to use
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

# More information
Please check www.oc-blog.com

Demo video: https://youtu.be/5jsGgfClPAM
