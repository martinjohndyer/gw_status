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
MAX_LEN = max([len(name) for name in DETECTORS])

OBSERVING_DICT = {detector: False for detector in DETECTORS}
OBSERVING_STATUSES = ['Observing', 'Science']


def get_gw_data():
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

    # Create a simple nested dict for each detector, with the site as the key
    # Only for the sites we care about (in DETECTORS)
    status_dict = {detector_dict['site']: detector_dict
                   for detector_dict in data['detectors']
                   if detector_dict['site'] in DETECTORS}

    # Add a boolean observing and error flags
    for detector in status_dict:
        status_dict[detector]['observing'] = status_dict[detector]['status'] in OBSERVING_STATUSES
        status_dict[detector]['error'] = 'error' in status_dict[detector]['status']

    # Need to parse the timestamp, it doesn't include the year!
    current_year = datetime.now().year
    timestamp = str(current_year) + data['UTC']
    timestamp = datetime.strptime(timestamp, '%Y%b %d, %H:%M UTC')
    timestamp = Time(timestamp)  # Newer astropys gives Time.strptime

    return status_dict, timestamp


def listen(channel, token):
    """Listen to the status page and pick up any changes."""
    # Blank observing dict to start
    observing_dict = {detector: None for detector in DETECTORS}

    while True:
        # Store old dict
        old_observing_dict = observing_dict.copy()

        # Get the current detector data from the site
        status_dict, timestamp = get_gw_data()

        # Build the new observing dict
        # Note we don't change if the error flag is true
        observing_dict = {detector:
                          status_dict[detector]['observing']
                          if not status_dict[detector]['error']
                          else old_observing_dict[detector]
                          for detector in status_dict}

        # Count the number observing
        num_observing = sum([observing_dict[detector] for detector in observing_dict])

        # See if any changed observing status
        changed = [detector for detector in observing_dict
                   if (observing_dict[detector] != old_observing_dict[detector] and
                       'error' not in status_dict[detector]['status'])]

        # If the status chenged then alert people!
        if any(changed):
            print('~~~~~~~~~~~~~~~~~~~~~~~~~~~')

            # Print the number of detectors observing
            string = 'Status at {}:\n  {}/{} detectors are observing'
            print(string.format(timestamp.iso[:-7],
                                num_observing,
                                len(observing_dict)))

            # Print all detector statuses
            for detector in sorted(status_dict):
                string = '  {: <{i}}: {} ("{}")'
                print(string.format(detector,
                                    '1' if status_dict[detector]['observing'] else '0',
                                    status_dict[detector]['status'],
                                    i=MAX_LEN + 1))

            # Send the Slack message
            if channel and token:
                # Create Slack client
                client = SlackClient(token)

                # Create message with link to page
                string = '<{}|GW detector status update>: {}/{} observing'
                msg = string.format(STATUS_PAGE,
                                    num_observing,
                                    len(observing_dict))

                # Report which detectors changed
                for detector in sorted(changed):
                    if old_observing_dict[detector] is None:
                        # First time
                        pass
                    elif observing_dict[detector]:
                        msg += '\n({} changed to Observing)'.format(detector)
                    else:
                        msg += '\n({} changed to Down)'.format(detector)

                # Create attachment for each detector
                attachments = []
                for detector in sorted(status_dict):
                    # Format each detector status
                    if status_dict[detector]['observing']:
                        text = 'Observing'
                        color = '#00ff00'
                    else:
                        text = 'Down'
                        color = '#ff4040'

                    attachment = {'title': detector,
                                  'text': text,
                                  'fallback': '{}: {}'.format(detector, text),
                                  'color': color,
                                  }
                    attachments.append(attachment)

                # Send the message
                client.api_call('chat.postMessage',
                                text=msg,
                                attachments=attachments,
                                channel=channel)

        # Sleep so we don't bombard the site
        sleep(120)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-c', '--channel', help='Slack channel name')
    parser.add_argument('-t', '--token', help='Slack Bot Token')
    args = parser.parse_args()

    listen(args.channel, args.token)
