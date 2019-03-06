"""A little script to monitor the GW detector statuses."""

from time import sleep
from urllib.request import urlopen

import bs4
from astropy.time import Time


STATUS_PAGE = 'https://ldas-jobs.ligo.caltech.edu/~gwistat/gwistat/gwistat.html'

DETECTORS = ['GEO 600',
             'LIGO Hanford',
             'LIGO Livingston',
             'Virgo',
             'KAGRA',
             ]


def parse_status_page(data):
    """Parse the GW status page using BeautifulSoup."""
    soup = bs4.BeautifulSoup(data, 'html.parser')
    rows = soup.find_all('td')
    data = [row.text.strip() for row in rows if row.text.strip()]
    status_dict = {detector: data[data.index(detector) + 1] for detector in DETECTORS}
    return status_dict


def get_gw_status():
    """Fetch and parse the GW status page."""
    request = urlopen(STATUS_PAGE)
    data = request.read()
    status_dict = parse_status_page(data)
    return status_dict


def format_status(status_dict):
    now = Time.now()
    string = 'Status at {}:\n'.format(now.iso)
    for detector in sorted(status_dict):
        string += '\t{}: "{}"\n'.format(detector, status_dict[detector])
    return string

def listen():
    """Listen to the status page and pick up any changes."""
    status_dict = get_gw_status()
    print(format_status(status_dict))
    while True:
        old_status_dict = status_dict.copy()
        status_dict = get_gw_status()
        changed = [detector for detector in status_dict
                   if status_dict[detector] != old_status_dict[detector]]
        if changed:
            print(format_status(status_dict))
        sleep(30)

if __name__ == '__main__':
    listen()
