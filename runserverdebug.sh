#!/usr/bin/env bash

export PYTHONPATH=${PWD}:${PYTHONPATH}
export SPA_CONFIG=production_settings
export SPA_DEBUG_LOG=/tmp/debug.log

source ~/.virtualenvs/spring/bin/activate

cd /srv/spring/
python spa/server.py stop
python spa/server.py debug

