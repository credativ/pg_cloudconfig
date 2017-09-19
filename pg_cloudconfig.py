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
import sys
from pint import UnitRegistry
from subprocess import call

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
    return int(math.pow(2, math.ceil(math.log(number, 2))))


def round_power_of_2_ceil_mb(mem):
    mem_mb = mem.to(ureg.megabyte).magnitude
    ceil_mb = int(math.pow(2, math.ceil(math.log(mem_mb, 2))))
    return ceil_mb * ureg.megabyte


def round_power_of_2_floor(number):
    return int(math.pow(2, math.floor(math.log(number, 2))))


def round_power_of_2_floor_mb(mem):
    mem_mb = mem.to(ureg.megabyte).magnitude
    floor_mb = int(math.pow(2, math.floor(math.log(mem_mb, 2))))
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
    if candidate > 8 * ureg.gigabyte:
        mwm = 8 * ureg.gigabyte
    else:
        mwm = candidate
    return round_power_of_2_floor_mb(mwm)


def max_connections(pg_out, pg_in, system, log):
    # If max_connections are given we use it
    if pg_in['max_connections'] > 0:
        return pg_in['max_connections']

    # Possible max_connections based on cpu_count
    cpu_candidate = system['cpu_count'] * 12

    connection_ram = system['memory']['total'].to(ureg.megabyte).magnitude
    # keep some space for the OS fs cache
    connection_ram -= system['memory'][
        'total'].to(ureg.megabyte).magnitude / 10
    connection_ram -= pg_out['shared_buffers'].to(ureg.megabyte).magnitude
    connection_ram -= pg_out[
        'maintenance_work_mem'].to(ureg.megabyte).magnitude

    # Estimate possible workmem
    workmem_candidate = round_power_of_2_floor(connection_ram / cpu_candidate)

    # Calculate possible max_connections based on workmem only
    return int(round(connection_ram / workmem_candidate, -1))


def work_mem(pg_out, pg_in, system, log):
    connection_ram = system['memory']['total']
    connection_ram -= pg_out['shared_buffers']
    connection_ram -= pg_out['maintenance_work_mem']
    return round_power_of_2_floor_mb(connection_ram / pg_out['max_connections'])


def effective_cache_size(pg_out, pg_in, system, log):
    usage_factor = 0.6
    connection_ram = system['memory']['total']
    connection_ram -= pg_out['shared_buffers']
    connection_ram -= pg_out['maintenance_work_mem']
    connection_ram -= pg_out['work_mem'] * pg_out[
        'max_connections'] * usage_factor
    return round_power_of_2_floor_mb(connection_ram)


def superuser_reserved_connections(pg_out, pg_in, system, log):
    src = 7
    if pg_out['max_connections'] <= (src * 30):
        src = 5
    elif pg_out['max_connections'] >= (src * 100):
        src = 10
    return src


def autovacuum_max_workers(pg_in, system, log):
    cc = system['cpu_count']
    amw = 4
    if cc <= 4:
        awm = 2
    if cc >= 16:
        awm = 5
    if cc >= 32:
        amw = 7
    if cc > 64:
        awm = int(cc * 0.20)
    return int(amw)


def tune(pg_in, system, log):
    """
    Set multiple PostgreSQL settings according to the given input
    """
    if not pg_in['version'] in SUPPORTED_VERSIONS:
        log.error("Version is not supported, " + pg_in['version'])

    pg_out = {}
    # Static settings
    pg_out['wal_level'] = "replica"
    pg_out['checkpoint_timeout'] = "15min"
    pg_out['checkpoint_completion_target'] = 0.8
    pg_out['min_wal_size'] = "128MB"
    pg_out['max_wal_size'] = "4GB"
    pg_out['vacuum_cost_limit'] = "400"

    # Dynamic setting
    pg_out['shared_buffers'] = shared_buffers(pg_in, system, log)
    pg_out['maintenance_work_mem'] = maintenance_work_mem(pg_in, system, log)
    pg_out['max_connections'] = max_connections(pg_out, pg_in, system, log)
    pg_out['work_mem'] = work_mem(pg_out, pg_in, system, log)
    pg_out['effective_cache_size'] = effective_cache_size(
        pg_out, pg_in, system, log)
    pg_out['superuser_reserved_connections'] = superuser_reserved_connections(
        pg_out, pg_in, system, log)
    pg_out['autovacuum_max_workers'] = autovacuum_max_workers(
        pg_in, system, log)

    return pg_out


def format_for_pg_conf(si):
    if isinstance(si, int) or isinstance(si, str) or isinstance(si, float):
        # Seams to be a basic type so we just return the value as string
        return str(si)

    base = si.to_base_units()
    if base.units == "bit":
        si_mb = si.to(ureg.megabyte).magnitude
        return str(si_mb) + "MB"


def persist_conf(pg_out, pg_in, log):
    try:
        filehandle = open(pg_in['conf'], 'r+')
    except IOError:
        log.error(
            'Unable to open postgresql.conf for writing, ' + pg_in['conf'])
        sys.exit(1)
    filehandle.close()

    for key, value in pg_out.items():
        setting = format_for_pg_conf(value)
        log.info("set " + key + ": " + str(setting))
        ret = call(
            ["pg_conftool", pg_in['version'], pg_in['clustername'], pg_in['conf'], "set", key, setting])
        if ret != 0:
            log.error("Error while setting: " + key +
                      " to: " + setting + " with return code: " + ret)


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
    pg = {}
    pg['version'] = args.pg_version
    pg['clustername'] = args.pg_clustername
    pg['conf_dir'] = "/etc/postgresql/" + \
        pg['version'] + "/" + pg['clustername']

    # If --pg_conf_dir is set, use it insted of default
    if args.pg_conf_dir > "":
        pg_conf_dir = args.pg_conf_dir
    pg['conf'] = pg['conf_dir'] + "/postgresql.conf"

    if args.max_connections > "":
        pg['max_connections'] = args.max_connections
    else:
        pg['max_connections'] = -1

    # Show information
    log.debug("Variables")
    log.debug("pg_version: " + pg['version'])
    log.debug("pg_clustername: " + pg['clustername'])
    log.debug("pg_conf_dir: " + pg['conf_dir'])
    log.debug("pg_conf: " + pg['conf'])
    log.debug("cpu_count: " + str(system['cpu_count']))
    log.debug("mem: " + str(system['memory']))

    pg_out = tune(pg, system, log)

    log.debug("Result")
    log.debug(pg_out)
    persist_conf(pg_out, pg, log)

if __name__ == "__main__":
    main()
