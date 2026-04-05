#!/bin/bash

# Build the Docker images
docker build -t eavedillo/django .

# push the containers
docker push eavedillo/django:latest