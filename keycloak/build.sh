#!/bin/bash

DOCKER_COMPOSE="docker-compose -f docker-compose.yml"


if [ "$1" == "run" ]; then
  ${DOCKER_COMPOSE} up -d
elif [ "$1" == "stop" ]; then
  ${DOCKER_COMPOSE} stop
else
  ${DOCKER_COMPOSE} build
fi
