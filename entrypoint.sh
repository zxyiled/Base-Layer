#!/bin/sh
set -eu

echo "Applying database migrations..."
flask --app wsgi db upgrade

echo "Starting the application..."
exec "$@"
