#!/bin/bash
cd uboxai
# OpenAI Key
OPENAIKEY=$1
# Check if IP was successfully fetched
if [ -z "$OPENAIKEY" ]; then
    OPENAIKEY=''    
fi

# echo source start_uboxai.sh 127.0.0.1 $OPENAIKEY
source start_uboxai.sh 127.0.0.1 $OPENAIKEY

