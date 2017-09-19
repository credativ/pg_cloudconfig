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
from pint import UnitRegistry


# Global variables
SUPPORTED_VERSIONS = ['9.6']
ureg = UnitRegistry()
Q_ = ureg.Quantity

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
                mem['total'] = int(sline[1]) * ureg.kilobytes
            elif str(sline[0]) in ('MemFree:', 'Buffers:', 'Cached:'):
                free += int(sline[1]) * ureg.kilobytes
        mem['free'] = free
        mem['used'] = mem['total'] - mem['free']
    return mem

def round_power_of_2_ceil(number):
    return int(math.pow(2,math.ceil(math.log(number,2))))

def round_power_of_2_ceil_mb(mem):
    mem_mb = mem.to(ureg.megabyte).magnitude
    ceil_mb = int(math.pow(2,math.ceil(math.log(mem_mb,2))))
    return ceil_mb * ureg.megabyte

def round_power_of_2_floor(number):
    return int(math.pow(2,math.floor(math.log(number,2))))

def round_power_of_2_floor_mb(mem):
    mem_mb = mem.to(ureg.megabyte).magnitude
    floor_mb = int(math.pow(2,math.floor(math.log(mem_mb,2))))
    return floor_mb * ureg.megabyte


def shared_buffers(pg_in, system, log):
    # Get total available memory as MB
    total = system['memory']['total']

    # Get a candidate value
    candidate = total / 5

    # Special cases for small memory
    if total < 4096 * ureg.megabyte:
        sb = 256 * ureg.megabyte
        if total < 1024 * ureg.megabyte:
            sb = 128 * ureg.megabyte
        if total < 512 * ureg.megabyte:
            sb = 64 * ureg.megabyte
        if total < 256 * ureg.megabyte:
            sb = 16 * ureg.megabyte
        if total < 128 * ureg.megabyte:
            sb = 4 * ureg.megabyte
    elif candidate > 16 * ureg.gigabyte:
        sb = 16 * ureg.gigabyte
    else:
        sb = candidate

    return round_power_of_2_floor_mb(sb)

def maintenance_work_mem(pg_in, system, log):
    # Get total available memory as MB
    total = system['memory']['total']

    # Get a candidate value
    candidate = total / 10

    # Special cases for small memory
    if candidate > 16 * ureg.gigabyte:
        mwm = 16 * ureg.gigabyte
    else:
        mwm = candidate
    return round_power_of_2_floor_mb(mwm)

def max_connections(pg_out, pg_in, system, log):
    # If max_connections are given we use it
    if pg_in['max_connections'] > 0:
        return pg_in['max_connections']

    # Possible max_connections based on cpu_count
    cpu_candidate = system['cpu_count'] * 15

    connection_ram = system['memory']['total'].to(ureg.megabyte).magnitude
    connection_ram -= pg_out['shared_buffers'].to(ureg.megabyte).magnitude
    connection_ram -= pg_out['shared_buffers'].to(ureg.megabyte).magnitude # keep some space for the fs cache
    connection_ram -= pg_out['maintenance_work_mem'].to(ureg.megabyte).magnitude

    # Estimate possible workmem
    workmem_candidate = round_power_of_2_floor(connection_ram / cpu_candidate)

    # Calculate possible max_connections based on workmem only
    return int(round(connection_ram / workmem_candidate,-1))

def work_mem(pg_out, pg_in, system, log):
    connection_ram = system['memory']['total']
    connection_ram -= pg_out['shared_buffers']
    connection_ram -= pg_out['maintenance_work_mem']
    return round_power_of_2_floor_mb(connection_ram / pg_out['max_connections'])

def tune(pg_in, system, log):
    """
    Set multiple PostgreSQL settings according to the given input
    """
    if not pg_in['version'] in SUPPORTED_VERSIONS:
        log.error("Version is not supported, "+ pg_in['version'])

    pg_out = {}
    pg_out['shared_buffers'] = shared_buffers(pg_in, system, log)
    pg_out['maintenance_work_mem'] = maintenance_work_mem(pg_in, system, log)
    pg_out['max_connections'] = max_connections(pg_out, pg_in, system, log)
    pg_out['work_mem'] = work_mem(pg_out, pg_in, system, log)


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
    parser.add_argument('--max_connections', default="",
                        help='Set the max_connections explicitly if needed')
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

    if args.max_connections > "":
        pg['max_connections'] = args.max_connections
    else:
        pg['max_connections'] = -1

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
