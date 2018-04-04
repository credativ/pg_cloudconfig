![pg_cloudconfig logo](images/pg_cloudconfig.png "pg_cloudconfig")

# Intro pg_cloudconfig
Tool to initially set optimized defaults for PostgreSQL in virtual
environments. Settings are changed without asking for confirmation.

This is used to change the static defaults of PostgreSQL to potentially more
useful alternatives calculated based on available resources or previous
settings.

pg_cloudconfig should be run as the same user as PostgreSQL. `pg_version` and
`pg_clustername` are used to choose a cluster. It is assumed that the Debian
(postgresql-common) naming and configuration schema is used. If this is not the
case `--pg_conf_dir` needs to be set. pg_conftool is used to get/set settings.

## Disclaimer
This does not tune PostgreSQL for any specific workload but only tries to set
some optimized defaults based on a few input variables and simple rules.
The intended use is to pre-configure automatically created cloud instances.
For high load and critical databases it should always be preferred to configure
and tune them for the specific use case.

# Installation
## Debian / Ubuntu
```bash
sudo apt-get install postgresql-common python3-pint python3-setuptools
python3 setup.py build
sudo python3 setup.py install
```

## Other
The following dependencies are required
* [postgresql-common](https://salsa.debian.org/postgresql/postgresql-common)
* python3
* python3-pint
* python3-setuptools

# Test
```bash
vagrant up
vagrant ssh
sudo su postgres
pg_cloudconfig 9.6 main
```

# Usage
```
usage: pg_cloudconfig.py [-h] [--max_connections MAX_CONNECTIONS]
                         [--pg_conf_dir PG_CONF_DIR] [--dynamic_only]
                         [--blacklist SETTING [SETTING ...]] [--debug] [-q]
                         [--version]
                         pg_version pg_clustername

Tool to initially set optimized defaults for PostgreSQL in virtualized
environments. Settings are changed without asking for confirmation.

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
  --dynamic_only        do not set static optimized defaults, only set values
                        dynamic calculated
  --blacklist SETTING [SETTING ...]
                        settings not to touch
  --debug               show debug messages
  -q, --quiet           disable output
  --version             show program's version number and exit

pg_cloudconfig should be run as the same user as PostgreSQL. pg_version and
pg_clustername are used to choose a cluster. It is assumed that the Debian /
postgresql-common naming and configuration schema is used. If this is not the
case --pg_conf_dir needs to be set. pg_conftool is used to get/set settings.
This does not tune PostgreSQL for any specific workload but only tries to set
some optimized defaults based on a few input variables and simple rules.
```

## Example

```bash
pg_cloudconfig 10 main
```
