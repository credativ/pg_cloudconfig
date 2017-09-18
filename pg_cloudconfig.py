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

def main():
    # Configure logging
    log = logging.getLogger('pg_cloudconfig')
    log.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    #formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    log.addHandler(ch)

    # Get system information
    cpu_count = psutil.cpu_count()
    mem = memory()

    # Get cmd arguments
    parser = argparse.ArgumentParser(description='Tool to set optimized defaults for PostgreSQL in cloud environments.')
    parser.add_argument('--pg_version', default="9.6", help='Version of the PostgreSQL cluster to tune.')
    parser.add_argument('--pg_clustername', default="main", help='Name of the PostgreSQL cluster to tune.')
    parser.add_argument('--pg_conf_dir', default="", help='Path to the dir holding the postgresql.conf (normally not necessary to set explicitly!).')
    args = parser.parse_args()

    # Settings - set defaults
    pg_version = args.pg_version
    pg_clustername = args.pg_clustername
    pg_conf_dir="/etc/postgresql/"+pg_version+"/"+pg_clustername

    # If --pg_conf_dir is set, use it insted of default
    if args.pg_conf_dir > "":
        pg_conf_dir = args.pg_conf_dir
    pg_conf=pg_conf_dir+"/postgresql.conf"

    # Debug information
    log.info("Variables")
    log.info("pg_version: "+pg_version)
    log.info("pg_clustername: "+pg_clustername)
    log.info("pg_conf_dir: "+pg_conf_dir)
    log.info("pg_conf: "+pg_conf)
    log.info("cpu_count: "+str(cpu_count))
    log.info("mem: "+str(mem))


if __name__ == "__main__":
    main()