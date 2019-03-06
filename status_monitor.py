"""A little script to monitor the GW detector statuses."""

import json
from datetime import datetime
from time import sleep
from urllib.request import urlopen

from astropy.time import Time

STATUS_PAGE = 'https://ldas-jobs.ligo.caltech.edu/~gwistat/gwistat/gwistat.json'


def get_gw_status():
    """Fetch and parse the GW status page."""
    # Fetch the JSON
    request = urlopen(STATUS_PAGE)
    contents = request.read()
    data = json.loads(contents.decode())

    # Need to parse the timestamp, doesn't include the year!
    current_year = datetime.now().year
    timestamp = str(current_year) + data['UTC']
    timestamp = datetime.strptime(timestamp, '%Y%b %d, %H:%M UTC')
    timestamp = Time(timestamp)  # Newer astropys gives Time.strptime

    # Create the status dict
    status_dict = {detector['site']: detector['status'] for detector in data['detectors']}

    # Return both
    return timestamp, status_dict


def format_status(time, status_dict):
    """Format the status dict."""
    string = 'Status at {}:\n'.format(time.iso)
    for detector in sorted(status_dict):
        string += '\t{: <{i}}: "{}"\n'.format(detector, status_dict[detector],
                                              i=max([len(d) for d in status_dict]) + 1)
    return string


def listen():
    """Listen to the status page and pick up any changes."""
    time, status_dict = get_gw_status()
    print(format_status(time, status_dict))

    while True:
        # Sleep first, so we don't bombard the site
        sleep(120)

        # Compare to see if anything has changed
        old_status_dict = status_dict.copy()
        time, status_dict = get_gw_status()
        changed = [detector for detector in status_dict
                   if status_dict[detector] != old_status_dict[detector]]

        # If so, then print out
        if changed:
            for detector in changed:
                print('{} status has changed: "{}" -> "{}"'.format(detector,
                                                                   old_status_dict[detector],
                                                                   status_dict[detector],
                                                                   ))
            print(format_status(time, status_dict))


if __name__ == '__main__':
    listen()
