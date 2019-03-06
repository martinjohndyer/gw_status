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
    data['timestamp'] = timestamp

    return data


def format_status(data):
    """Format the status dict."""
    string = 'Status at {}:\n'.format(data['timestamp'].iso)
    max_len = max([len(d['site']) for d in data['detectors']]) + 1
    for detector in data['detectors']:
        string += '\t{: <{i}}: "{}"\n'.format(detector['site'], detector['status'],
                                              i=max_len)
    return string


def listen():
    """Listen to the status page and pick up any changes."""
    data = get_gw_status()
    print(format_status(data))
    status_dict = {detector['site']: detector['status'] for detector in data['detectors']}

    while True:
        # Sleep first, so we don't bombard the site
        sleep(120)

        # Store old dict, and fetch new one
        old_status_dict = status_dict.copy()
        data = get_gw_status()

        # We're only interested in the status if it's not an error
        status_dict = {detector['site']: detector['status'] for detector in data['detectors']
                       if 'error' not in detector['status'].lower()}

        # See if any changed
        changed = [detector for detector in status_dict
                   if status_dict[detector] != old_status_dict[detector]]

        # If so, then print out
        if changed:
            for detector in changed:
                print('{} status has changed: "{}" -> "{}"'.format(detector,
                                                                   old_status_dict[detector],
                                                                   status_dict[detector],
                                                                   ))
            print(format_status(data))


if __name__ == '__main__':
    listen()
