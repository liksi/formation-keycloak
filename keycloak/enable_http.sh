#!/usr/bin/env bash
docker exec -it keycloak \
   /opt/keycloak/bin/kcadm.sh \
   update --server http://localhost:8080/auth \
   --realm master --user admin --password admin \
   realms/master -s sslRequired=NONE
