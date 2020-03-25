#!/usr/bin/env bash

OUTPUT="/tmp/topology.json"


DB_ADDR_JSON_PATH=".keycloak.postgres_host"
DB_PORT_JSON_PATH=".keycloak.postgres_port"
DB_USER_JSON_PATH=".keycloak.postgres_keycloakUser"
DB_PASSWORD_JSON_PATH=".keycloak.postgres_keycloakPwd"
DB_DATABASE_JSON_PATH=".keycloak.postgres_keycloakDatabase"

KEYCLOAK_USER_PATH=".keycloak.defaultAdminUser"
KEYCLOAK_PASSWORD_PATH=".keycloak.defaultAdminPwd"

BACK_ECT_ADMIN_PATH=".backEctAdmin.url"


if [ -f $OUTPUT ]; then
  rm $OUTPUT
fi

if [ -z "${TOPOLOGY_HOST}" ]; then
  echo "TOPOLOGY_HOST env var must be set"
  exit 1
fi


function get_topology() {
  local output=$1
  local topology=$2
  local http_code=$(curl -s -o $output -w "%{http_code}" -X GET "${topology}"/api/configuration/topology)
  if [ "$http_code" != "200" ]; then
    echo "Cannot reach topology (received http code $http_code)"
    exit 1
  fi
}

function extractValue() {
  local output=$1
  local json_path=$2
  cat $output | jq $json_path
}

function check_key() {
  local key=$1
  local path=$2
  local value=$3
  if [ -z "$value" -o "$value" == "null" ]; then
    echo "No value read in topology at path $path for var $key"
    exit 1
  fi
}

function define_var() {
  local key=$1
  local path=$2
  local value=$3
  local output=$4
  local secret=$5
  if [ -z "${value}" ]; then
    value=$(extractValue $output $path)
    check_key "$key" "$path" "$value"
  fi
  if [ ! -z "$secret" ]; then
    echo "$key=*****"
  else
    echo "$key=$value"
  fi
  export $key=$(echo $value | tr -d '"')
}

function override_ect_admin_url() {
  local output=$1
  local json_path=$2
  local js_script_path=$3
  value=$(extractValue $output $json_path)
  sed  -i "s%ECT_ADMIN_HOST=.*%ECT_ADMIN_HOST=$value%" $js_script_path
}

echo "Fetching configuration from topology at $TOPOLOGY_HOST"
get_topology $OUTPUT $TOPOLOGY_HOST

define_var "DB_ADDR" "$DB_ADDR_JSON_PATH" "$DB_ADDR" "$OUTPUT"
define_var "DB_PORT" "$DB_PORT_JSON_PATH" "$DB_PORT" "$OUTPUT"
define_var "DB_USER" "$DB_USER_JSON_PATH" "$DB_USER" "$OUTPUT"
define_var "DB_PASSWORD" "$DB_PASSWORD_JSON_PATH" "$DB_PASSWORD" "$OUTPUT" "secret"
define_var "DB_DATABASE" "$DB_DATABASE_JSON_PATH" "$DB_DATABASE" "$OUTPUT"

define_var "KEYCLOAK_USER" "$KEYCLOAK_USER_PATH" "$KEYCLOAK_USER" "$OUTPUT"
define_var "KEYCLOAK_PASSWORD" "$KEYCLOAK_PASSWORD_PATH" "$KEYCLOAK_PASSWORD" "$OUTPUT" "secret"

override_ect_admin_url "$OUTPUT" "$BACK_ECT_ADMIN_PATH" "/opt/jboss/keycloak/themes/seiitra/login/resources/js/script.js"

exec /opt/jboss/tools/docker-entrypoint.sh $@
exit $?
