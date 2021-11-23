#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys


if __name__ == '__main__':
    exit(os.system('vagrant ssh -c "cd /vagrant; source /venv/bin/activate && ./manage.py ' +
         ' '.join(sys.argv[1:]) + ';"'))
