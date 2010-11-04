# After Cloning
Run (you are recommended to do this inside a virtualenv):

    $ pip install -r requirements.txt
    $ sudo yum -y install $(cat yum-packages.txt) # external deps
    $ cd cafesys
    $ python manage.py syncdb

# Running a Development Server
Run:

    $ cd cafesys
    $ python manage.py runserver 0.0.0.0:8000

# Virtualenv Crash Course
Here is a crash course on how to get started with virtualenv and
virtualenvwrapper in Fedora:

    $ sudo pip install virtualenv
    $ sudo pip install virtualenvwrapper
    $ cd ~
    $ mkdir -p envs
    $ echo 'export WORKON_HOME=$HOME/envs' >> .bashrc
    $ echo 'export PIP_RESPECT_VIRTUALENV=true' >> .bashrc
    $ echo 'source /usr/bin/virtualenvwrapper.sh' >> .bashrc
    $ source .bashrc
    $ cd envs
    $ git clone git@github.com:pilt/cafesys.git
    $ mkvirtualenv --no-site-packages cafesys
    (cafesys) $ cd cafesys
    (cafesys) $ sudo yum -y install $(cat yum-packages.txt) # external deps
    (cafesys) $ easy_install pip
    (cafesys) $ pip install -r requirements.txt

## On Windows
### Using VirtualBox (recommended)
Install the [latest Fedora release](http://fedoraproject.org/get-fedora) on a
[VirtualBox](http://www.virtualbox.org/) instance. If you want to work on the
Windows host, configure shared folders.

### Using Cygwin
Install [cygwin](http://www.cygwin.com/) and be sure to include the Python and
SQLite packages. This has not been tried to work; if you do it successfully,
please let someone know so that we can update this readme.

# External Dependencies
## Base dependencies
 * See `yum-packages.txt`. You can install them all by running 
   `yum -y install $(cat yum-packages.txt)`.

## Kiosk Mode
 * Opera browser

## Smartcard Tools
 * The `pcsc-lite-devel` and `ccid` packages should be installed (in yum). 
   When they have been, the ACR122 will be lighted and able to scan cards 
   when the pcscd daemon is running.

## LDAP
 * The `python-ldap` module needs (in yum): `openldap openldap-devel`

## RabbitMQ
 * For IPC. In yum: `rabbitmq-server`

## Linear Programming
 * For distributing work shifts. In yum: `glpk glpk-utils`
