"""A little script to monitor the GW detector statuses."""

import argparse
import json
import urllib
from datetime import datetime
from time import sleep

from astropy.time import Time

from slackclient import SlackClient

STATUS_PAGE = 'https://ldas-jobs.ligo.caltech.edu/~gwistat/gwistat/gwistat.html'
STATUS_JSON = 'https://ldas-jobs.ligo.caltech.edu/~gwistat/gwistat/gwistat.json'

DETECTORS = ['LIGO Hanford', 'LIGO Livingston', 'Virgo']


def get_gw_status():
    """Fetch and parse the GW status page."""
    data = None
    while not data:
        try:
            # Fetch the JSON
            request = urllib.request.urlopen(STATUS_JSON)
            contents = request.read()
            data = json.loads(contents.decode())
        except urllib.error.HTTPError:
            print('Got 403, retrying...')
            sleep(10)
        except Exception:
            raise

    # Need to parse the timestamp, doesn't include the year!
    current_year = datetime.now().year
    timestamp = str(current_year) + data['UTC']
    timestamp = datetime.strptime(timestamp, '%Y%b %d, %H:%M UTC')
    timestamp = Time(timestamp)  # Newer astropys gives Time.strptime
    data['timestamp'] = timestamp

    # Filter to only the ones we care about
    data['detectors'] = [d for d in data['detectors'] if d['site'] in DETECTORS]

    return data


def format_status(data):
    """Format the status dict."""
    string = 'Status at {}:\n'.format(data['timestamp'].iso[:-7])
    max_len = max([len(d['site']) for d in data['detectors']]) + 1
    for detector in data['detectors']:
        string += '\t{: <{i}}: "{}"\n'.format(detector['site'], detector['status'],
                                              i=max_len)
    return string


def send_slack_message(data, channel, token):
    """Send a status report to Slack."""
    client = SlackClient(token)

    msg = '<{}|GW detector status update>:'.format(STATUS_PAGE)
    attachments = []
    for detector in data['detectors']:
        attachment = {'title': detector['site'],
                      'text': detector['status'],
                      'fallback': '{}: {}'.format(detector['site'], detector['status']),
                      'color': detector['color'],
                      }
        attachments.append(attachment)

    client.api_call('chat.postMessage', text=msg, attachments=attachments, channel=channel)


def listen(channel, token):
    """Listen to the status page and pick up any changes."""
    data = get_gw_status()
    print(format_status(data))
    send_slack_message(data, channel, token)
    status_dict = {detector['site']: detector['status'] for detector in data['detectors']}

    while True:
        # Sleep first, so we don't bombard the site
        sleep(120)

        # Store old dict, and fetch new one
        old_status_dict = status_dict.copy()
        data = get_gw_status()

        # We're only interested in the status if it's not an error
        status_dict = {detector['site']: detector['status'] for detector in data['detectors']}

        # See if any changed
        changed = [detector for detector in status_dict
                   if status_dict[detector] != old_status_dict[detector]]

        # Processes changes
        for detector in changed:
            # Ignore errors
            if 'error' in status_dict[detector] or 'error' in old_status_dict[detector]:
                continue

            print('{} status has changed: "{}" -> "{}"'.format(detector,
                                                               old_status_dict[detector],
                                                               status_dict[detector],
                                                               ))
            print(format_status(data))
            send_slack_message(data, channel, token)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-c', '--channel', help='Slack channel name')
    parser.add_argument('-t', '--token', help='Slack Bot Token')
    args = parser.parse_args()

    listen(args.channel, args.token)
