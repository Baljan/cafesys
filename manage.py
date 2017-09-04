#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys


if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cafesys.settings.development')

    if os.getcwd() == '/vagrant':
        from django.core.management import execute_from_command_line

        execute_from_command_line(sys.argv)
    else:
        exit(os.system('vagrant ssh -c "cd /vagrant; source .venv/bin/activate && ./manage.py ' + ' '.join(sys.argv[1:]) + ';"'))

