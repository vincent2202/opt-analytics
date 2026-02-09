#!/bin/bash

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
while ! nc -z analytics_db 5432; do
  sleep 0.1
done
echo "PostgreSQL started"

# Run migrations
#echo "Running database migrations..."
#python manage.py migrate --noinput

# Execute the main command
exec "$@"