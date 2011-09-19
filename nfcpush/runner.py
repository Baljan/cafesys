# coding=utf-8
import sys
import os
import ConfigParser
import subprocess
import struct
import re

import requests

__author__ = 'Simon Pantzare'

_s = struct.Struct('I')
_reg = re.compile(r'^< ([A-F0-9 ]+) : Normal processing.*$')

def process(response):
    lines = response.splitlines()
    result = _reg.match(lines[-1])
    if result is None:
        raise ValueError("bad data")
    id_bytes = result.group(1).split()[:-2]
    buf = "".join([chr(int(b, 16)) for b in id_bytes])
    card_id = unicode(_s.unpack(buf)[0])
    return card_id

config = ConfigParser.RawConfigParser()
config.read('settings.ini')

commands_file = config.get('nfcpush', 'commands_file')
if not os.path.isfile(commands_file):
    sys.exit('bad commands file: %s' % commands_file)

url = config.get('nfcpush', 'url')

def handle_inserted():
    sys.stderr.write("card inserted\n")
    sys.stderr.flush()
    scriptor_proc = subprocess.Popen(
        ['scriptor', commands_file],
        stdout=subprocess.PIPE,
    )
    out, err = scriptor_proc.communicate()
    if scriptor_proc.returncode == 0:
        processed = process(out)
        r = requests.post(url, data={'card': str(processed)})
        if r.status_code == requests.codes.ok:
            sys.stderr.write("POST success:\n%r\n" % r.content)
        else:
            sys.stderr.write("POST failed:\n%r\n" % r.content)
        sys.stderr.flush()
    else:
        sys.stderr.write('scriptor failed')
        sys.stderr.flush()

def handle_removed():
    sys.stderr.write("card removed\n")
    sys.stderr.flush()

if __name__ == '__main__':
    scan_proc = subprocess.Popen(
        ['pcsc_scan', '-n'], 
        shell=True,
        stdout=subprocess.PIPE,
    )
    state_line = 'Card state: \x1b[31mCard %s, \x1b[0m'

    while True:
        line = scan_proc.stdout.readline()
        if not line:
            break
        for state, handler in [
                ('inserted', handle_inserted),
                ('removed', handle_removed),
                ]:
            if line.find(state_line % state) != -1:
                handler()
                break
