# This is an auto install script for Oracle Autonomous Linux 7.8
# It will configure to automatically run the autoscale script using Instance Principal permission
# So ensure you have configured a dynamic group for this instance and that that dynamic group
# has a policy to manage all resources in your tenancy.

# Set to your time zone for correct time
sudo timedatectl set-timezone Europe/Amsterdam

# Install needed components and configure crontab with correct schedule
sudo yum -y install git
sudo pip3 install oci oci-cli
git clone https://github.com/AnykeyNL/OCI-AutoScale.git
cd OCI-AutoScale/
sed -i 's/UseInstancePrinciple = False/UseInstancePrinciple = True/g' AutoScaleALL.py
crontab schedule.cron
