# After Cloning
## System Dependencies
### OS X

    $ easy_install pip
    $ brew install postgresql node
    $ npm install -g uglify-js coffee-script

Start the server. Either manually or through launchd, see output from
Homebrew.

    $ createdb cafesys

## Python and Django
Run (you are recommended to do this inside a virtualenv):

    $ pip install -r requirements.txt
    $ cd cafesys
    $ python manage.py syncdb --noinput
    $ python manage.py migrate
    $ python manage.py createsuperuser
    $ python manage.py assets rebuild
    $ python manage.py runserver 

Visit [http://localhost:8000/](http://localhost:8000/). Assets are rebuilt
automatically.

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
