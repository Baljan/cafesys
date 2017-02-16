#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys


if __name__ == '__main__':
    # Add the cafesys package to the PYTHONPATH so we can reference the baljan
    # package as just baljan (instead of cafesys.baljan)
    sys.path.append(os.path.abspath(os.path.dirname(__file__)) + '/cafesys')

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cafesys.settings.development')

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
