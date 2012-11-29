#!/usr/bin/env bash

pybabel extract -F babel.cfg -o messages.pot .
pybabel update -i messages.pot -d botias/translations
pybabel compile -d botias/translations

