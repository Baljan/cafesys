# After Cloning
## System Dependencies
### OS X

    $ brew install postgresql node
    $ npm install -g uglify-js coffee-script

Start the server. Either manually or through launchd, see output from
Homebrew.

    $ createdb cafesys

## Python and Django
Run (you are recommended to do this inside a virtualenv):

    $ pip install -r requirements.txt
    $ sudo yum -y install $(cat yum-packages.txt) # external deps
    $ cd cafesys
    $ python manage.py syncdb --noinput
    $ python manage.py migrate
    $ python manage.py createsuperuser
    $ python manage.py runserver 

Visit http://localhost:8000/.

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

# External Dependencies
## Base dependencies
 * See `yum-packages.txt`. You can install them all by running 
   `yum -y install $(cat yum-packages.txt)`.

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
