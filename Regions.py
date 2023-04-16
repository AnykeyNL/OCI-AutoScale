# OCI Regions according to:
# https://docs.oracle.com/en-us/iaas/Content/General/Concepts/regions.htm
# update 2023-04-16

import pytz
import datetime

# set timezone per region
timezones = {
    'ap-chuncheon-1': 'Asia/Seoul',
    'ap-hyderabad-1': 'Asia/Kolkata',
    'ap-melbourne-1': 'Australia/Melbourne',
    'ap-mumbai-1': 'Asia/Kolkata',
    'ap-osaka-1': 'Asia/Tokyo',
    'me-abudhabi-1': 'Asia/Dubai',
    'ap-seoul-1': 'Asia/Seoul',
    'eu-madrid-1': 'Europe/Madrid',
    'eu-stockholm-1': 'Europe/Stockholm',
    'ap-singapore-1': 'Asia/Singapore',
    'us-sanjose-1': 'America/Los_Angeles',
    'ap-sydney-1': 'Australia/Sydney',
    'ap-tokyo-1': 'Asia/Tokyo',
    'ca-montreal-1': 'America/Montreal',
    'ca-toronto-1': 'America/Toronto',
    'eu-amsterdam-1': 'Europe/Amsterdam',
    'eu-frankfurt-1': 'Europe/Berlin',
    'eu-zurich-1': 'Europe/Zurich',
    'me-dubai-1': 'Asia/Dubai',
    'me-jeddah-1': 'Asia/Riyadh',
    'sa-santiago-1': 'America/Santiago',
    'sa-saopaulo-1': 'America/Sao_Paulo',
    'uk-cardiff-1': 'Europe/London',
    'uk-london-1': 'Europe/London',
    'us-ashburn-1': 'America/New_York',
    'us-chicago-1': 'America/Chicago',
    'us-phoenix-1': 'America/Phoenix',
    'eu-milan-1': 'Europe/Rome',
    'eu-paris-1': 'Europe/Paris',
    'eu-marseille-1': 'Europe/Paris',
    'sa-vinhedo-1': 'America/Sao_Paulo',
    'il-jerusalem-1': 'Asia/Jerusalem',
    'mx-queretaro-1': 'America/Mexico_City',
    'af-johannesburg-1': 'Africa/Johannesburg',
    'us-langley-1': 'America/New_York',
    'us-luke-1': 'America/Phoenix',
    'us-gov-ashburn-1': 'America/New_York',
    'us-gov-chicago-1': 'America/Chicago',    
    'us-gov-phoenix-1': 'America/Phoenix',
    'uk-gov-london-1': 'Europe/London',
    'uk-gov-cardiff-1': 'Europe/London'
}

RegionTime = []

# Dynamically retrieve offset time to support regions using 'Daylight Saving Time'
for region, timezone in timezones.items():
    # set timezone
    tz = pytz.timezone(timezone)

    # Get the current time in the specified timezone
    now = datetime.datetime.now(tz)

    # Get UTC offset for the current time in the specified timezone
    offset = now.utcoffset()

    # Region timezone is later to UTC
    if offset.days == 0 :       
        hours, minutes, seconds = map(int, str(offset).split(':'))
        decimal_time = hours + minutes / 60 + seconds / 3600

        # if offset is an integer (e.g. Franckfurt 2)
        if decimal_time % 1 == 0:
            RegionTime.append([region, int(decimal_time)])

        # if offset is a float (e.g. Mumbai 5.5)
        else:
            RegionTime.append([region, decimal_time])
    
    # Region timezone is prior to UTC
    else:
        days, hours, minutes = offset.days, offset.seconds // 3600, offset.seconds // 60 % 60
        decimal_time = hours - 24
        RegionTime.append([region, decimal_time])
