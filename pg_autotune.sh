#!/bin/bash
# Alexander Sosna <alexander.sosna@credativ.de>
#
# This is to automatic tune cloud images for first use, nothing more!

set -e

# Settings
grubcfg="grub"
pgconf="./postgresql.conf"
pgversion="9.5"
pgclustername="main"


# Autoconf
cpucount=$(nproc)
totalram_kB=$(cat /proc/meminfo | grep MemTotal | awk '{ print $2 }')
totalram_MB=$(($totalram_kB/1000))

# set_option_in_file changes lines in a file in order to change configuration options.
# It takes 3 arguments:
#    $1: path to configuration file
#    $2: identifier string that identifies the target option
#    $3: full option line as it should appear in the config file
function set_option_in_file()
{
    file=$1
    identifier=$2
    option=$3

    if grep -q "$option" $file; then
        echo "$file: Found option: $option, nothing to do."
    elif grep -q "$identifier" $file; then
        echo "$file: Found identifier: $identifier, going to replace with option: $option"
        sed -i -e "/$identifier/ c $option" $file
    else
        echo "$file: Put option at end of file: $option"
        echo "$option" >> $file
    fi
}

# Change grub configuration
function configure_grub()
{
    set_option_in_file "$grubcfg" "$1" "$2"
}

# Change PostgreSQL configuration
function configure_postgresql()
{
    if command -v pg_conftool2 >/dev/null 2>&1; then
        pg_conftool "$pgconf" set "$1" "$2"
    else
        set_option_in_file "$pgconf" "\b${1} =" "$1 = $2"
    fi
}

echo "Set deadline scheduler for all devices"
configure_grub "elevator=" 'GRUB_CMDLINE_LINUX="elevator=deadline"'

# echo "Update grub configuration"
#update-grub2

echo "Generate PostgreSQL parameters"
shared_buffers_MB=$(($totalram_MB / 4))
if (( $shared_buffers_MB > 12000 ))
then
    shared_buffers_MB=12000
fi


echo "Tune postgresql.conf"
# CONNECTIONS AND AUTHENTICATION
configure_postgresql "port" "5432"
configure_postgresql "max_connections" "50"
configure_postgresql "superuser_reserved_connections" "5"

# RESOURCE USAGE (except WAL)
configure_postgresql "shared_buffers" "${shared_buffers_MB}MB"
configure_postgresql "work_mem" "16MB"
configure_postgresql "maintenance_work_mem" "512MB"
configure_postgresql "shared_preload_libraries" "'pg_stat_statements'"

# WRITE AHEAD LOG
configure_postgresql "wal_level" "minimal"
configure_postgresql "wal_buffers" "16MB"
configure_postgresql "wal_compression" "off"
configure_postgresql "checkpoint_timeout" "5min"
configure_postgresql "max_wal_size" "2GB"
configure_postgresql "min_wal_size" "80MB"
configure_postgresql "checkpoint_completion_target" "0.7"

# AUTOVACUUM PARAMETERS
configure_postgresql "autovacuum" "on"
configure_postgresql "autovacuum_max_workers" "4"

# QUERY TUNING
configure_postgresql "random_page_cost" "4.0"
configure_postgresql "effective_cache_size" "4GB"
