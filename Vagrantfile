# -*- mode: ruby -*-
# vi: set ft=ruby :
Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/xenial64"
  config.vm.network "forwarded_port", guest: 8000, host: 8000, host_ip: '127.0.0.1'

  config.vm.provision "docker" do |d|
    d.run "postgres", args: "-p 5432:5432 --env-file /vagrant/.env.docker.tmpl"
    d.run "redis", args: "-p 6379:6379 --env-file /vagrant/.env.docker.tmpl"
  end

  config.vm.provision "shell", inline: <<-SHELL
    add-apt-repository -y ppa:jonathonf/python-3.6
    apt-get update
    apt-get install -y python3.6 python3.6-dev python3-pip libpq-dev build-essential libssl-dev g++ libffi-dev python3-dev pypy
    cd /vagrant
    cp -n .env.tmpl .env
  SHELL

  config.vm.provision "shell", run: 'always', inline: <<-SHELL
    cd /vagrant
    python3.6 -m pip install -r requirements.txt
  SHELL
end
