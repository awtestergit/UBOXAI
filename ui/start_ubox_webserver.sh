#!/bin/bash
echo "UBOX Webserver starts at $(pwd)"

# write the config.json
# .sh aiserver_ip aiserver_port webserver_ip webserver_port
TEXT="{\"server_ip\":\"$(printf '%s' "$1")\", \"server_port\":\"$(printf '%s' "$2")\"}"
FILE='./src/config.json'
#overwrite
echo "$TEXT" > "$FILE"

# wait for AI server for a few seconds
sleep 5

# start
echo serve -s -l $4 build
serve -s -l $4 build
