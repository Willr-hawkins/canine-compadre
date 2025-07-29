#!/usr/bin/env bash
# exit on error
set -o errexit

# Install requirements
pip install -r requirements.txt

# Collect static files
python manange.py collectstatic --no-input

# Run migrations
python manage.py migrate