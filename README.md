# Intro pg_cloudconfig
Tool to set optimized defaults for PostgreSQL in virtual environments (changes settings without asking for confirmation).


Should be run as the same user as PostgreSQL.
`pg_version` and `pg_clustername` are used to choose a cluster.
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
sudo apt-get install postgresql python3-psutil python3-pint
sudo cp pg_cloudconfig /usr/local/bin
```

# Test
```bash
vagrant up
vagrant ssh
sudo su postgres
pg_cloudconfig 9.6 main
```

# Usage
```
usage: pg_cloudconfig [-h] [--max_connections MAX_CONNECTIONS]
                      [--pg_conf_dir PG_CONF_DIR] [--dynamic_only]
                      [--blacklist SETTING [SETTING ...]] [--debug] [-q]
                      [--version]
                      pg_version pg_clustername

Tool to set optimized defaults for PostgreSQL in virtual environments (changes
settings without asking for confirmation).

positional arguments:
  pg_version            version of the PostgreSQL cluster to tune
  pg_clustername        name of the PostgreSQL cluster to tune

optional arguments:
  -h, --help            show this help message and exit
  --max_connections MAX_CONNECTIONS
                        set the max_connections explicitly if needed
  --pg_conf_dir PG_CONF_DIR
                        path to dir holding the postgresql.conf (to override
                        default)
  --dynamic_only        do not set static optimized defaults
  --blacklist SETTING [SETTING ...]
                        settings not to touch
  --debug               show debug messages
  -q, --quiet           disable output
  --version             show program's version number and exit

Should be run as the same user as PostgreSQL. pg_version and pg_clustername
are used to choose a cluster. It is assumed that the Debian / postgresql-
common naming and configuration schema is used. If this is not the case
--pg_conf_dir needs to be set. pg_conftool is used to get/set settings and is
required! This does not tune PostgreSQL for any specific workload but only
tries to set some optimized defaults based on a few input variables and simple
rules.
```
