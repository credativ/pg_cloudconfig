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
from . import *

def main():
    """Main function ;)"""
    system = {}
    system['cpu_count'] = os.cpu_count()
    system['memory'] = memory()

    # Get cmd arguments
    parser = argparse.ArgumentParser(
        description="""Tool to set optimized defaults for PostgreSQL in virtual environments
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
        log.error("conf_dir (%s) is not a directory or does not exist", pg['conf_dir'])
        log.info("Hint: Does the cluster %s/%s exists? Try 'pg_createcluster %s %s' if not.", pg['version'], pg['clustername'], pg['version'], pg['clustername'])
        sys.exit(1)

    pg['data_directory'] = data_directory(pg)
    log.info("data_directory:\t %s", pg['data_directory'])

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
