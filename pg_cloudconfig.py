#!/usr/bin/python3
"""
Copyright (C) 2017  Alexander Sosna

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import argparse
import psutil
import logging
import math

# Global variables
SUPPORTED_VERSIONS = ['9.6']

def memory():
    """
    Get node total memory and memory usage
    """
    with open('/proc/meminfo', 'r') as meminfo:
        mem = {}
        free = 0
        for i in meminfo:
            sline = i.split()
            if str(sline[0]) == 'MemTotal:':
                mem['total'] = int(sline[1])
            elif str(sline[0]) in ('MemFree:', 'Buffers:', 'Cached:'):
                free += int(sline[1])
        mem['free'] = free
        mem['used'] = int(mem['total']) - int(mem['free'])
    return mem

def round_power_of_2_ceil(number):
    return int(math.pow(2,math.ceil(math.log(number,2))))

def round_power_of_2_floor(number):
    return int(math.pow(2,math.floor(math.log(number,2))))

def shared_buffers(pg_in, system, log):
    # Get total available memory as MB
    total = system['memory']['total'] / 1024

    # Get a candidate value
    candidate = total / 4

    # Special cases for small memory
    if total < 4096:
        sb = 256
        if total < 1024:
            sb = 128
        if total < 512:
            sb = 64
        if total < 256:
            sb = 16
        if total < 128:
            sb = 4
    elif candidate > 16384:
        sb = 16384
    else:
        sb = candidate

    sb = round_power_of_2_floor(sb)
    return str(sb)+"MB"

def tune(pg_in, system, log):
    """
    Set multiple PostgreSQL settings according to the given input
    """
    if not pg_in['version'] in SUPPORTED_VERSIONS:
        log.error("Version is not supported, "+ pg_in['version'])

    pg_out = {}
    pg_out['shared_buffers'] = shared_buffers(pg_in, system, log)


    return pg_out

def main():
    # Configure logging
    log = logging.getLogger('pg_cloudconfig')
    log.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    # formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s -
    # %(message)s')
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    log.addHandler(ch)

    # Get system information
    system = {}
    system['cpu_count'] = psutil.cpu_count()
    system['memory'] = memory()

    # Get cmd arguments
    parser = argparse.ArgumentParser(
        description='Tool to set optimized defaults for PostgreSQL in cloud environments.')
    parser.add_argument('--pg_version', default="9.6",
                        help='Version of the PostgreSQL cluster to tune.')
    parser.add_argument('--pg_clustername', default="main",
                        help='Name of the PostgreSQL cluster to tune.')
    parser.add_argument('--pg_conf_dir', default="",
                        help='Path to the dir holding the postgresql.conf (normally not necessary to set explicitly!).')
    args = parser.parse_args()

    # Settings - set defaults
    pg ={}
    pg['version'] = args.pg_version
    pg['clustername'] = args.pg_clustername
    pg['conf_dir'] = "/etc/postgresql/" + pg['version'] + "/" + pg['clustername']

    # If --pg_conf_dir is set, use it insted of default
    if args.pg_conf_dir > "":
        pg_conf_dir = args.pg_conf_dir
    pg['conf'] = pg['conf_dir'] + "/postgresql.conf"

    # Show information
    log.info("Variables")
    log.info("pg_version: " + pg['version'])
    log.info("pg_clustername: " + pg['clustername'])
    log.info("pg_conf_dir: " + pg['conf_dir'])
    log.info("pg_conf: " + pg['conf'])
    log.info("cpu_count: " + str(system['cpu_count']))
    log.info("mem: " + str(system['memory']))

    pg_out = tune(pg,system,log)

    log.info("Result")
    log.info(pg_out)

if __name__ == "__main__":
    main()
