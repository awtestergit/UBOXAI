**UBOX-AI:** 

Plug-and-Play AI Document Processing & Knowledge Machine for Every Business with Full Data Privacy

## Index

* [Description](#description)
* [Architecture](#architecture)
* [Installation](#installation)
* [Notes & Model downloads](#notes)

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
- More AI applications to come.

## Architecture

All services are deployed on one single host machine.
- You can opt for hosting AI services in a docker (which is the easiest way to deploy).
- For LLM, Ollama is supported by setting up Ollama on the host machine.
  - If you do not want to set up Ollama, you can use OpenAI by providing your OpenAI key as well.

<img width="913" alt="Screenshot 2024-09-15 at 12 27 03" src="https://github.com/user-attachments/assets/315022da-4268-4ce8-ae70-200e5db77f86">
