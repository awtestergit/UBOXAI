"""
    server start
    Author: awtestergit
"""

import logging
import json
from argparse import ArgumentParser
import uvicorn
from ubox_server_fastapi import create_app

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-p", "--port", dest="port", type=int, default=5000, help="UBOX AI server port.")
    parser.add_argument("-ip", "--host", dest="ip", type=str, default="0.0.0.0", help="UBOX AI server host IP.")
    parser.add_argument("-cp", "--client-port", dest="cp", type=int, default=5050, help="UBOX Webserver host port.")
    parser.add_argument("-cip", "--client-host", dest="cip", type=str, default="127.0.0.1", help="UBOX Webserver host IP.")
    parser.add_argument("-log", "--log-file", dest="logfile", type=str, default="ubox_server.log", help="UBOX AI server log file.")
    parser.add_argument("-l", "--log", dest="logging", type=str, default="./ubox_server.log", help="UBOX Server logging file.")
    parser.add_argument("-k", "--openai-key", dest="openai_key", type=str, default='', help="set your openai key here to use OpenAI model.")
    args = parser.parse_args()
    logging_file = args.logging

    logging.basicConfig(filename=logging_file,filemode='a', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
    #logging.basicConfig(filename=logging_file,filemode='a', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
    logging.info("Starting...")

    local_addr = args.ip
    local_port = args.port
    client_addr = args.cip
    client_port = args.cp
    openai_key = args.openai_key

    config = {}
    with open('config.json', 'r') as f:
        config = json.load(f)
        config['local_ip'] = local_addr
        config['local_port'] = local_port
        config['client_ip'] = client_addr
        config['client_port'] = client_port
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=4)


    app = create_app(openai_key=openai_key)
    uvicorn.run(app, log_level='debug', host="0.0.0.0", port=local_port)
