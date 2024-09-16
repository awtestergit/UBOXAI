**UBOX-AI:** 

Plug-and-Play AI Document Processing & Knowledge Machine for Every Business with Full Data Privacy

## Index

* [Description](#description)
* [Architecture](#architecture)
* [SLM in Power](#slminpower)
* [Installation](#installation)
* [Knowledge Warehouse](#knowledgewarehouse)

## Description

UBOX-AI is an AI-powered machine designed to revolutionize document processing, simplify repetitive tasks, and boost productivity for small businesses and home offices. With UBOX-AI, you can bring the latest in artificial intelligence directly into your workspace with ease and efficiency.

- We believe in **"AI democracy"** - making AI accessible to all businesses, regardless of size. UBOX-AI is a showcase of how even a Small Language Model (SLM) can deliver powerful results, automating tasks and streamlining workflows that were once time-consuming and complex.

- For businesses intrigued by AI but concerned about cost, UBOX-AI is a **budget-friendly** solution that leverages open-source technologies. It allows companies to experience AI firsthand, without high upfront investments - afterall, we optimized the whole AI system to run under one 4090 (or even lesser) GPU of a game machine, single-digit (not double-digit) of thousands.

- UBOX-AI is also a **plug-and-play** solution, meaning it’s incredibly easy to deploy. Simply connect UBOX-AI to your company’s intranet, and it immediately serves as a web-based AI server. Employees can access AI tools securely through a browser, without the need for complicated setups or specialized software.

- Your data **privacy and security** are the top priority. UBOX-AI operates as a private deployment, ensuring that all AI processes run locally, keeping your business data secure and confidential while delivering the benefits of cutting-edge AI technology.

Current features include:

- Dochat - chat with your document
- Doctract - extract key elements from your document
- Docompare - compare two documents to highlight differences
- DocKnow - chat with your knowledge warehouse (FAQ & documents)

Future work:

- Knowledge Warehouse Manager improvement.
- More AI applications to come.

## Architecture

All services are deployed on one single host machine.
- You can opt for hosting AI services in a docker (which is the easiest way to deploy).
- For LLM, Ollama is supported by setting up Ollama on the host machine.
  - If you do not want to set up Ollama, you can use OpenAI by providing your OpenAI key as well.

<img width="913" alt="Screenshot 2024-09-15 at 12 27 03" src="https://github.com/user-attachments/assets/315022da-4268-4ce8-ae70-200e5db77f86">

## SLM In Power

One key constraint of small LLM (SLM) is to control the context length - to make the SLM work in wonder, we need to make the context meaningfully short - the semantic search tree (SST) makes this possible. The tree is built upon long document(s), and the leaf nodes are clustered by their semantic meanings, and so does the parent nodes till root. To retrieve the context for a query, we search this tree for the top contextual results.

Reference:
- "WALKING DOWN THE MEMORY MAZE: BEYOND CONTEXT LIMIT THROUGH INTERACTIVE READING" https://arxiv.org/pdf/2310.05029
- R tree: https://www.bartoszsypytkowski.com/r-tree/

## Installation

- **Docker installation**
  - go to https://www.docker.com/ to install docker if you have not yet installed it.
- **Qdrant vector database installation**
  - https://qdrant.tech/documentation/quickstart/
    - ```bash
      docker pull qdrant/qdrant
      ```
    - ```bash
      docker run -p 6333:6333 -p 6334:6334 -v $(pwd)/qdrant_storage:/qdrant/storage:z qdrant/qdrant
      ```
- **Ollama & Models (If you plan to use OpenAI, skip this step)**
  - go to https://ollama.com/ to install ollama if you have not yet installed it.
  - pull Llama3.1 for LLM, https://ollama.com/library/llama3.1, you can pull 8B or larger depending on your host machine's GPU.
  - pull nomic-embed-text for embedding, https://ollama.com/library/nomic-embed-text
- **UBOXAI installation, you can either pull docker (the easiest way) or pull git, build and run**
  - **Docker way**
    - ```bash
      docker pull awtestergit/uboxai:latest
      ```
    - If you use Ollama shown above:
    - ```bash
      docker run --name uboxai -p 11434:11434 -p 5000:5000 -p 5010:5010 -p 5050:5050 -it -d --privileged -v ./:/orig -v $(pwd)/qdrant_storage:/qdrant/storage:z -v dind-certs:/certs -v /var/run/docker.sock:/var/run/docker.sock -e DOCKER_TLS_CERTDIR=/certs awtestergit/uboxai:latest ./entry_start.sh
      ```
    - If you use OpenAI:
    - ```bash
      docker run --name uboxai -p 11434:11434 -p 5000:5000 -p 5010:5010 -p 5050:5050 -it -d --privileged -v ./:/orig -v $(pwd)/qdrant_storage:/qdrant/storage:z -v dind-certs:/certs -v /var/run/docker.sock:/var/run/docker.sock -e DOCKER_TLS_CERTDIR=/certs awtestergit/uboxai:latest ./entry_start.sh your_openai_key
      ```
    - That is it! You can go to http://localhost:5050 on your host machine, or http://<host_machine_ip>:5050 from another machine on the same network, where host_machine_ip is the ip of your host machine, e.g, 192.168.x.xx.
    - The Dochat, Doctract, and Docompare work by now, and for Docknow, you need to populate the Knowledge Warehouse
      - See [Knowledge Warehouse](#knowledgewarehouse)
  - **Git pull way**
    - Prepare virtual environment (use your favorite virtual management tool), for example using conda:
      ```bash
      conda create -n uboxai python
      conda activate uboxai
      ```
    - Git pull:
      ```bash
      git clone https://github.com/awtestergit/UBOXAI.git
      cd UBOXAI/server
      pip install -r requirements.txt
      ```
    - Nginx installation
      - https://nginx.org/en/docs/install.html
      - configure sites: (shown as linux example, check nginx documents for other platforms)
        - copy 'uboxai' file under UBOXAI folder just created, which is the configuration for nginx, to /etc/nginx/sites-available (e.g, cp UBOXAI /etc/nginx/sites-available)
          - modify 'root /uboxai/ui/build;' in uboxai file, use your own ui/build path to replace '<your path to>/UBOXAI/ui/build' as necessary
        - ln -s /etc/nginx/sites-available/uboxai /etc/nginx/sites-enabled/ (probably you need to 'sudo ln ...'
      - restart nginx (in Linux: service nginx restart)
    - Start uboxai
      - at uboxai root, start ./entry_start.sh if using Ollama, or ./entry_start.sh <your_open_key> if using OpenAI
        - Note: if you need other machine under same subnet to access the UBOXAI, in entry_start.sh file replace 'source start_uboxai.sh 127.0.0.1' to 'source start_uboxai.sh <host_machine_ip>', where host_machine_ip is the ip of your host machine, e.g, 192.168.x.xx.
      - That is it! You can go to http://localhost:5050 on your host machine, or http://<host_machine_ip>:5050 from another machine on the same network
    - If you want to modify the UI and build by yourself, you need to install node, npm, etc, take a look at /ui/requirements.txt

## Knowledge Warehouse

Once you have the UBOXAI set up, you can populate the knowledge warehouse, which can store FAQs and your documents (supports PDF or DOCX formats).
**Note: There are plenty of works needed for the knowledge warehouse manager.**

- If you use **Docker way**, you can run this command to get to docker:
- ```bash
      docker run --name uboxai -p 11434:11434 -p 5000:5000 -p 5010:5010 -p 5050:5050 -it -d --privileged -v ./:/orig -v $(pwd)/qdrant_storage:/qdrant/storage:z -v dind-certs:/certs -v /var/run/docker.sock:/var/run/docker.sock -e DOCKER_TLS_CERTDIR=/certs awtestergit/uboxai:latest
      ```
- If you use **Git pull way**, activate the virtual environment, e.g, 'conda activate uboxai'
- go to folder /uboxai/server
- start venv by 'source /uboxai/bin/activate'
- start Knowledge Warehouse Manager by 'python vectordb_manager.py'
- use web browser on the host machine, http://localhost:5010, to populate the warehouse
  - for FAQ, you can bulk load by create the file using faq template. check faq template example.csv provided
  - for uploading documents, you can use the manager to upload file(s)

After the population, you can use Docknow to query - if the query hits FAQ, then the answer will be returned from FAQ; if not, the query will search from the documents uploaded to vector database and LLM will answer accordingly.
