# Intro pg_cloudconfig
Tool to set optimized defaults for PostgreSQL in virtual environments (changes settings without asking for confirmation).


Should be run as the same user as PostgreSQL.
`--pg_version` and `--pg_clustername` are used to choose a cluster.
It is assumed that the Debian / postgresql-common naming and
configuration schema is used.
If this is not the case `--pg_conf_dir` needs to be set.
pg_conftool is used to get/set settings and is required!
This does not tune PostgreSQL for any specific workload but only
tries to set some optimized defaults based on a few input variables
and simple rules.

# Installation
## Debian / Ubuntu
```bash
apt-get install postgresql python3-psutil python3-pint
```

# Test
```bash
vagrant up
vagrant ssh
sudo su postgres
pg_cloudconfig
```

# Usage
```
usage: pg_cloudconfig.py [-h] [--pg_version PG_VERSION]
                         [--pg_clustername PG_CLUSTERNAME]
                         [--max_connections MAX_CONNECTIONS]
                         [--pg_conf_dir PG_CONF_DIR] [--dynamic_only]
                         [--debug]

Tool to set optimized defaults for PostgreSQL in virtual environments (changes
settings without asking for confirmation).

optional arguments:
  -h, --help            show this help message and exit
  --pg_version PG_VERSION
                        version of the PostgreSQL cluster to tune
  --pg_clustername PG_CLUSTERNAME
                        name of the PostgreSQL cluster to tune
  --max_connections MAX_CONNECTIONS
                        set the max_connections explicitly if needed
  --pg_conf_dir PG_CONF_DIR
                        path to the dir holding the postgresql.conf (only to
                        override default)
  --dynamic_only        do not set static optimized defaults
  --debug               Show debug output

Should be run as the same user as PostgreSQL. --pg_version and
--pg_clustername are used to choose a cluster. It is assumed that the Debian /
postgresql-common naming and configuration schema is used. If this is not the
case --pg_conf_dir needs to be set. pg_conftool is used to get/set settings
and is required! This does not tune PostgreSQL for any specific workload but
only tries to set some optimized defaults based on a few input variables and
simple rules.
```