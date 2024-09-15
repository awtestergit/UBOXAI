from qdrant_client import QdrantClient
from qdrant_client.http import models

collection_name = "vdb_ubox"
host = "host.docker.internal"
#host = '0.0.0.0'
#host = '127.0.0.1'
#host = "localhost"
#host = "192.168.1.2"
url = f"http://{host}:6333"
print(url)
client = QdrantClient(url=url)

# response = client.get_collections()
# names = [desc.name for desc in response.collections]
# if collection_name not in names:#create
#     client.create_collection(collection_name, vectors_config=models.VectorParams(size=1024,distance=models.Distance.COSINE))


#host = "http://host.docker.internal:11434"
#host = "http//0.0.0.0:11434"
#host = "http://192.168.1.2:11434"
host = "http://127.0.0.1:11434"
#host = "http://localhost:11434"
#emb = OllamaEmbeddingModel(host=host)
#e = ollama.embeddings(model='local_llm', prompt='The sky is blue because of rayleigh scattering')
p = 'The sky is blue because of rayleigh scattering'
#e = emb.encode(p)
# llm = OllamaModel(host=host)
# r = llm.generate(p)
# print(r)

import sys
sys.path.append('./server')


import numpy as np

# Function to calculate cosine similarity
def cosine_similarity(vec1, vec2):
    dot_product = np.dot(vec1, vec2)
    norm_vec1 = np.linalg.norm(vec1)
    norm_vec2 = np.linalg.norm(vec2)
    return dot_product / (norm_vec1 * norm_vec2)

from models.embed import OllamaNomicEmbeddingModel
emb = OllamaNomicEmbeddingModel()
#e = ollama.embeddings(model='local_llm', prompt='The sky is blue because of rayleigh scattering')
p = 'how many chips'
r = "how many chips are required"
ep = emb.encode(p, to_list=True)
er = emb.encode(r, to_list=True)

ss = cosine_similarity(ep, er)

ss