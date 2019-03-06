"""A little script to monitor the GW detector statuses."""

import subprocess


STATUS_PAGE = 'https://ldas-jobs.ligo.caltech.edu/~gwistat/gwistat/gwistat.html'


def curl_data_from_url(url, wait_time=5, outfile=None):
    """Fetch data from a URL."""
    if not outfile:
        outfile = '/tmp/curlout'
    curl_command = 'curl -s -m {:.0f}'.format(wait_time)
    curl_command += ' -o {}'.format(outfile)
    curl_command += ' {}'.format(url)
    try:
        p = subprocess.Popen(curl_command, shell=True, close_fds=True)
        p.wait()
    except Exception:
        print('Error fetching URL "{}"'.format(url))

    with open(outfile, 'r') as f:
        data = f.read()

    return data

