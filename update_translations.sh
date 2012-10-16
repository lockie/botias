#!/usr/bin/env bash

pybabel extract -F babel.cfg -o messages.pot .
pybabel update -i messages.pot -d translations
pybabel compile -d translations
/etc/init.d/lighttpd restart
