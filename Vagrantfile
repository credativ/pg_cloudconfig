# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  # The most common configuration options are documented and commented below.
  # For a complete reference, please see the online documentation at
  # https://docs.vagrantup.com.

  config.vm.box = "debian/buster64"
  config.vm.synced_folder ".", "/vagrant", type: "rsync", rsync__exclude: ".git/"
  config.vm.provision "shell", inline: <<-SHELL
    sudo su

    locale-gen en_US.UTF-8 de_DE.UTF-8
    localedef -i en_US -f UTF-8 en_US.UTF-8
    localedef -i de_DE -f UTF-8 de_DE.UTF-8

    # Install tools
    apt-get update
    apt-get install -y curl ca-certificates apt-transport-https gnupg2

    # Use official PostgreSQL repo, apt.postgresql.org
    echo "deb http://apt.postgresql.org/pub/repos/apt/ $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list
    curl https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -

    apt-get update
    apt-get install -y postgresql-12 python3-psutil python3-pint
    ln -s /vagrant/pg_cloudconfig/pg_cloudconfig.py /usr/bin/pg_cloudconfig
  SHELL
end
