#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Copyright (C) 2017  Alexander Sosna <alexander.sosna@credativ.de>

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
import os
import logging
import math
import sys
import time
import subprocess
from datetime import datetime
from statistics import median
from pint import UnitRegistry
# Global variables
__version__ = '0.6'
VERSION = __version__
SUPPORTED_VERSIONS = ['10', '9.6']
TOOLS = [[
    'This tool is needed to read and write PostgreSQL Settings',
    ['pg_conftool', '--help']
]]

LOG_LEVEL = logging.INFO

# SI unit usage
ureg = UnitRegistry()
Q_ = ureg.Quantity


def memory():
    """Get node total memory and memory usage"""
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
    """Round number up to the power of 2"""
    return int(math.pow(2, math.ceil(math.log(number, 2))))


def round_power_of_2_ceil_mb(mem):
    """Round memory up to the power of 2 and return in MB"""
    mem_mb = mem.to(ureg.megabyte).magnitude
    ceil_mb = int(math.pow(2, math.ceil(math.log(mem_mb, 2))))
    return ceil_mb * ureg.megabyte


def round_power_of_2_floor(number):
    """Round number down to the power of 2"""
    return int(math.pow(2, math.floor(math.log(number, 2))))


def round_power_of_2_floor_mb(mem):
    """Round memory down to the power of 2 and return in MB"""
    mem_mb = mem.to(ureg.megabyte).magnitude
    floor_mb = int(math.pow(2, math.floor(math.log(mem_mb, 2))))
    return floor_mb * ureg.megabyte


def shared_buffers(system):
    """Calculate the shared_buffers"""
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
    # Special case if shared_buffers would be > 16GB
    elif candidate > 16 * ureg.gigabyte:
        sb = 16 * ureg.gigabyte
    else:
        sb = candidate

    return round_power_of_2_floor_mb(sb)


def maintenance_work_mem(system):
    """Calculate the maintenance_work_mem"""
    # Get total available memory as MB
    total = system['memory']['total']

    # Get a candidate value
    candidate = total / 10

    # Special cases for high memory
    if candidate > 8 * ureg.gigabyte:
        mwm = 8 * ureg.gigabyte
    else:
        mwm = candidate
    return round_power_of_2_floor_mb(mwm)


def max_connections(pg_out, pg_in, system):
    """Calculate the max_connections"""
    # If max_connections are given we use it
    if pg_in['max_connections'] > 0:
        return pg_in['max_connections']

    # Possible max_connections based on cpu_count
    cpu_candidate = system['cpu_count'] * 12

    connection_ram = system['memory']['total'].to(ureg.megabyte).magnitude
    # keep some space for the OS fs cache
    connection_ram -= system['memory']['total'].to(
        ureg.megabyte).magnitude / 10
    connection_ram -= pg_out['shared_buffers'].to(ureg.megabyte).magnitude
    connection_ram -= pg_out['maintenance_work_mem'].to(
        ureg.megabyte).magnitude

    # Estimate possible workmem
    workmem_candidate = round_power_of_2_floor(connection_ram / cpu_candidate)

    # Calculate possible max_connections based on workmem only
    return int(round(connection_ram / workmem_candidate, -1))


def work_mem(pg_out, system):
    """Calculate the work_mem"""
    connection_ram = system['memory']['total']
    connection_ram -= pg_out['shared_buffers']
    connection_ram -= pg_out['maintenance_work_mem']
    return round_power_of_2_floor_mb(
        connection_ram / pg_out['max_connections'])


def effective_cache_size(pg_out, pg_in, system):
    """Calculate the effective_cache_size"""
    usage_factor = 0.6
    cache_ram = system['memory']['total']
    cache_ram -= pg_out['shared_buffers']
    cache_ram -= pg_out['maintenance_work_mem']
    cache_ram -= pg_out['work_mem'] * pg_out['max_connections'] * usage_factor

    # If we are running on fast SSDs we can assume a larger cash
    # to push PostgreSQL to do less sequential scans
    if pg_in['disk_speed'] == "fast":
        cache_ram *= 2

    return round_power_of_2_floor_mb(cache_ram)


def superuser_reserved_connections(pg_out):
    """Calculate the superuser_reserved_connections"""
    src = 7
    if pg_out['max_connections'] <= (src * 30):
        src = 5
    elif pg_out['max_connections'] >= (src * 100):
        src = 10
    return src


def autovacuum_max_workers(system):
    """Calculate the autovacuum_max_workers"""
    cc = system['cpu_count']
    avmw = 3
    if cc >= 16:
        avmw = 5
    if cc > 64:
        avmw = 7
    return int(avmw)


def vacuum_cost_limit(pg_in):
    """Calculate the vacuum_cost_limit"""
    if pg_in['disk_speed'] == "fast":
        return 800
    elif pg_in['disk_speed'] == "medium":
        return 600
    elif pg_in['disk_speed'] == "slow":
        return 200


def format_for_pg_conf(si):
    """Format values to a string representation for the postgresql.conf"""
    if isinstance(si, int) or isinstance(si, str) or isinstance(si, float):
        # Seams to be a basic type so we just return the value as string
        return str(si)

    base = si.to_base_units()
    if base.units == "bit":
        si_mb = si.to(ureg.megabyte).magnitude
        return str(si_mb) + "MB"


def persist_conf(pg_out, pg_in, log):
    """Persit all not blacklisted settings form pg_out to the config file"""
    try:
        filehandle = open(pg_in['conf'], 'r+')
    except IOError:
        log.error(
            'Unable to open postgresql.conf for writing, ' + pg_in['conf'])
        sys.exit(1)
    filehandle.close()

    for key, value in sorted(pg_out.items()):
        if key in pg_in['blacklist']:
            log.info("blacklisted and will not be changed: %s", key)
        else:
            setting = format_for_pg_conf(value)
            log.info("set %s: %s", key, setting)
            ret = subprocess.call([
                "pg_conftool", pg_in['version'], pg_in['clustername'],
                pg_in['conf'], "set", key, setting
            ])
            if ret != 0:
                log.error(
                    "Error while setting: %s to: %s with return code: %s", key,
                    setting, ret)


def repeat_to_length(string_to_expand, length):
    """Repeat a string (partial) to a given length"""
    return (
        string_to_expand * int((length / len(string_to_expand)) + 1))[:length]


def chomp(x):
    """Removes the last character of a string if it is a newline"""
    if x.endswith("\r\n"):
        return x[:-2]
    if x.endswith("\n"):
        return x[:-1]
    return x


def get_setting(pg, key):
    """Gets a setting via pg_conftool"""
    ret = (subprocess.check_output([
        "pg_conftool", "--short", pg['version'], pg['clustername'], pg['conf'],
        "show", key
    ]))
    return chomp(ret.decode('UTF-8'))


def data_directory(pg):
    """Returns the data_directory"""
    return get_setting(pg, "data_directory")


def write_test(testfile, log):
    """Performs a test write of 5 times 16MB and returns the needed time"""
    testdata = repeat_to_length(
        """This is a test string and should be much more random
        !11!!!1!!!djefoirhnfonndojwpdojawpodjpajdpoajdpaojdpjadpojadoja""",
        (1024 * 1024 * 16))
    runtime = []
    for i in range(0, 5):
        startTime = datetime.now()
        try:
            fh = open(testfile, 'w+')
        except IOError:
            log.error('Iteration %d Unable to open test file for writing, %s',
                      i, testfile)
            sys.exit(1)
        fh.write(testdata)
        fh.flush()
        fh.close()
        delta = datetime.now() - startTime
        runtime.append(delta.microseconds)
    os.remove(testfile)
    return runtime


def write_bench(testfile, log):
    """Estimates the write performance (slow|medium|fast)"""
    # Do multiple test runs and wait some time
    # so the test is less likely to run in an anomaly
    results = write_test(testfile, log)
    time.sleep(0.5)
    results += write_test(testfile, log)
    time.sleep(0.5)
    results += write_test(testfile, log)

    for i in results:
        log.debug("test run took %dµs", i)
    med = int(median(results))
    mean = int(sum(results) / len(results))
    log.debug("median:\t%sµs", med)
    log.debug("mean:\t%sµs", mean)

    # Example disk (5400rpm RAID1)
    # DEBUG - median: 214289µs
    # DEBUG - mean:   153168µs
    # Example ssd (NVME Samsung SSD 960 EVO 500GB)
    # DEBUG - median:  24947µs
    # DEBUG - mean:    26861µs
    if med > 100000 or mean > 120000:
        return "slow"
    elif med > 40000 or mean > 50000:
        return "medium"
    else:
        return "fast"


def tune(pg_in, system, no_static, log):
    """Set multiple PostgreSQL settings according to the given input"""
    if not pg_in['version'] in SUPPORTED_VERSIONS:
        log.error("Version is not supported: %s", pg_in['version'])
        log.info("Supported versions: %s", SUPPORTED_VERSIONS)
        sys.exit(1)

    pg_out = {}
    # Static settings
    if not no_static:
        pg_out['wal_level'] = "replica"
        pg_out['checkpoint_timeout'] = "15min"
        pg_out['checkpoint_completion_target'] = 0.8
        pg_out['min_wal_size'] = "128MB"
        pg_out['max_wal_size'] = "4GB"

    # Dynamic setting
    pg_out['shared_buffers'] = shared_buffers(system)
    pg_out['maintenance_work_mem'] = maintenance_work_mem(system)
    pg_out['max_connections'] = max_connections(pg_out, pg_in, system)
    pg_out['work_mem'] = work_mem(pg_out, system)
    pg_out['effective_cache_size'] = effective_cache_size(
        pg_out, pg_in, system)
    pg_out['superuser_reserved_connections'] = superuser_reserved_connections(
        pg_out)
    pg_out['autovacuum_max_workers'] = autovacuum_max_workers(system)
    pg_out['vacuum_cost_limit'] = vacuum_cost_limit(pg_in)
    return pg_out


def main():
    """Main function ;)"""
    system = {}
    system['cpu_count'] = os.cpu_count()
    system['memory'] = memory()

    # Get cmd arguments
    parser = argparse.ArgumentParser(
        description="""Tool to set optimized defaults for PostgreSQL
        in virtual environments
        (changes settings without asking for confirmation).""",
        epilog="""Should be run as the same user as PostgreSQL.
        pg_version and pg_clustername are used to choose a cluster.
         It is assumed that the Debian / postgresql-common naming and
         configuration schema is used.
         If this is not the case --pg_conf_dir needs to be set.
         pg_conftool is used to get/set settings and is required!
         This does not tune PostgreSQL for any specific workload but only
         tries to set some optimized defaults based on a few input variables
         and simple rules.""")
    parser.add_argument(
        'pg_version',
        nargs=1,
        help='version of the PostgreSQL cluster to tune')
    parser.add_argument(
        'pg_clustername',
        nargs=1,
        help='name of the PostgreSQL cluster to tune')
    parser.add_argument(
        '--max_connections',
        default="",
        help='set the max_connections explicitly if needed')
    parser.add_argument(
        '--pg_conf_dir',
        default="",
        help='path to dir holding the postgresql.conf (to override default)')
    parser.add_argument(
        '--dynamic_only',
        action='store_true',
        help='do not set static optimized defaults')
    parser.add_argument(
        '--blacklist',
        nargs='+',
        default=[],
        metavar='SETTING',
        help='settings not to touch')
    parser.add_argument(
        '--debug', action='store_true', help='show debug messages')
    parser.add_argument(
        '-q', '--quiet', action='store_true', help='disable output')
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s {version}'.format(version=VERSION))
    args = parser.parse_args()

    # Configure logging
    if args.debug:
        log_level = logging.DEBUG
    elif args.quiet:
        log_level = logging.FATAL
    else:
        log_level = LOG_LEVEL

    log = logging.getLogger('pg_cloudconfig')
    log.setLevel(log_level)
    ch = logging.StreamHandler()
    ch.setLevel(log_level)
    # formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s -
    # %(message)s')
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    log.addHandler(ch)

    # Settings
    pg = {}
    pg['version'] = args.pg_version[0]
    pg['clustername'] = args.pg_clustername[0]
    pg['blacklist'] = args.blacklist

    # If --pg_conf_dir is set, use it insted of default
    if args.pg_conf_dir > "":
        pg['conf_dir'] = os.path.join(args.pg_conf_dir, pg['conf'],
                                      pg['conf_dir'], "postgresql.conf")
    else:
        pg['conf_dir'] = os.path.join("/etc/postgresql", pg['version'],
                                      pg['clustername'])
    pg['conf'] = os.path.join(pg['conf_dir'], "postgresql.conf")

    if args.max_connections > "":
        pg['max_connections'] = args.max_connections
    else:
        pg['max_connections'] = -1

    log.info("Cluster to tune:\t %s/%s", pg['version'], pg['clustername'])
    log.info("conf_dir:\t %s", pg['conf_dir'])

    if not os.path.isdir(pg['conf_dir']):
        log.error("conf_dir (%s) is not a directory or does not exist",
                  pg['conf_dir'])
        log.info("Hint: Does the cluster %s/%s exists?" +
                 "Try 'pg_createcluster %s %s' if not.", pg['version'],
                 pg['clustername'], pg['version'], pg['clustername'])
        sys.exit(1)

    pg['data_directory'] = data_directory(pg)
    log.info("data_directory:\t %s", pg['data_directory'])

    # Check if needed tools are available
    log.debug("Checking tools")
    tool_fails = 0
    DEVNULL = open(os.devnull, 'w')
    for tool in TOOLS:
        helptext = tool[0]
        command = tool[1]
        name = command[0]
        try:
            ret = subprocess.call(command, stdout=DEVNULL)
        except FileNotFoundError:
            ret = -1
        if ret != 0:
            tool_fails += 1
            log.error("It seems the tool '%s' is not working correctly." +
                      " Is it installed and in the path?", name)
            log.info("Why '%s' is needed: %s", name, helptext)
        if tool_fails != 0:
            sys.exit(1)

    log.info("Start write_bench...")
    pg['disk_speed'] = write_bench(
        os.path.join(pg['data_directory'], "~write_test.dat"), log)
    log.info("Disk was benched as: %s (slow|medium|fast)", pg['disk_speed'])

    log.info("Calculate settings...")
    no_static = args.dynamic_only
    pg_out = tune(pg, system, no_static, log)
    log.debug("Result")
    log.debug(pg_out)

    log.info("Persist settings using pg_conftool...")
    persist_conf(pg_out, pg, log)


if __name__ == "__main__":
    main()
