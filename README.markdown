# After Cloning
Be sure to run the following commands after cloning for the first time,
to cut all ties with the system-wide Python:

    $ virtualenv --no-site-packages env
    $ source env/bin/activate

Now you are ready to bootstrap the system:

    $ python bootstrap.py

Finally, run the buildout, to get all dependencies (this will take a
long time):

    $ ./bin/buildout -v

Now you have all the dependencies needed to run the system. The `source
env/bin/activate` command is important, and must be ran in order to
tell the shell not to use the system-wide packages, but the packages
contained within the virtualenv.
