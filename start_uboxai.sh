#!/bin/bash

# Fetch the local IP address (assuming the first one is the desired one)
# IP=$(ipconfig getifaddr en0)
IP=$1
# OpenAI key
OPENAIKEY=$2

# Check if IP was successfully fetched
if [ -z "$IP" ]; then
    echo "Failed to determine the IP address."
    exit 1
fi

# ubox_server IP
AIP=$IP
# ubox webserver IP
WIP=$IP

# ubox server port
APORT=5000
# ubox webserver port
WPORT=5050
# write to webserver
cd ui
TEXT="
PORT=$WPORT
REACT_APP_UBOXAI_SERVER_IP=$AIP
REACT_APP_UBOXAI_SERVER_PORT=$APORT
"
FILE='.env'
# Check if the file exists, if not, create it
if [ ! -f "$FILE" ]; then
    touch "$FILE"
fi
# overwrite the .env file
echo -e "$TEXT" > "$FILE"
# make a copy to build
FILE='build/env.js'
TEXT="
window.env = {
  \"REACT_APP_UBOXAI_SERVER_IP\": \"$(printf '%s' "$AIP")\",
  \"REACT_APP_UBOXAI_SERVER_PORT\": \"$(printf '%s' "$APORT")\"
};
"
# Check if the file exists, if not, create it
if [ ! -f "$FILE" ]; then
    touch "$FILE"
fi
# overwrite the .env file
echo -e "$TEXT" > "$FILE"

# restart nginx
echo "restart nginx..."
service nginx restart

cd ..

echo "Starting UBOX AI Server..."
# kill tmux
# tmux kill-session
# tmux kill-session

# start venv
source /uboxai/bin/activate 
cd server
echo current dictory: $(pwd)
# echo python ubox_server.py --host $AIP --port $APORT --client-host $WIP --client-port $WPORT --openai-key $OPENAIKEY
python ubox_server.py --host $AIP --port $APORT --client-host $WIP --client-port $WPORT --openai-key $OPENAIKEY

# echo tmux new-session -d -s ai 
# tmux new-session -d -s ai

# echo tmux send-keys -t ai "source /uboxai/bin/activate" C-m
# tmux send-keys -t ai "source /uboxai/bin/activate" C-m

# echo tmux send-keys -t ai "python ubox_server.py --host $AIP --port $APORT --client-host $WIP --client-port $WPORT --openai-key ''" C-m
# tmux send-keys -t ai "python ubox_server.py --host $AIP --port $APORT --client-host $WIP --client-port $WPORT --openai-key ''" C-m

