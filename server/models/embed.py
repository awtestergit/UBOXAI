# -*- coding: utf-8 -*-

"""
    Embedding model using Ollama
    Author: awtestergit
"""


from ollama import Client
import numpy as np

from interface.interface_model import IEmbeddingModel

class OllamaNomicEmbeddingModel(IEmbeddingModel):
    def __init__(self, host:str="http://localhost:11434", model:str='nomic-embed-text', max_context_length=8192) -> None:
        # assuming the model is running at host:str="http://localhost:11434",
        token_ex = 0.7 # 1 token ~= 0.7 character
        # max length 5000 = 8192*0.7
        self.MAX_LENGTH = int(max_context_length * token_ex)
        self.model = model
        self.client = Client(host=host)
        e = self.client.embeddings(model=model, prompt="hello")
        embedding_size = len(e['embedding'])
        self.EMBED_SIZE = embedding_size # embedding dimension of nomic

    def encode(self, inputs:str, to_list=False):
        """
        inputs: string
        output: 2d shape (1, embed_size)
        """
        def normalize_l2(x):
            x = np.array(x)
            if x.ndim == 1:
                norm = np.linalg.norm(x)
                if norm == 0:
                    return x
                return x / norm
            else:
                norm = np.linalg.norm(x, 2, axis=1, keepdims=True)
                return np.where(norm == 0, x, x / norm)
        #response = ollama.embeddings(model=self.model, prompt=inputs)
        response = self.client.embeddings(model=self.model, prompt=inputs)
        cut_dim = response['embedding'][:self.EMBED_SIZE]
        norm_dim = normalize_l2(cut_dim)
        if not to_list:
            norm_dim = norm_dim.reshape(1, -1) # reshape to (1, EMBED_SIZE)
        return norm_dim

# support OpenAI    
from openai import OpenAI

class GPTEmbeddingModel(IEmbeddingModel):
    gpt_embedding = {
        'text-embedding-3-small': {
            'emb_length_model': 1536,
            'emb_length_use': 1024,
            'seq_length': 8192,
        },
        'text-embedding-3-large': {
            'emb_length_model': 3072,
            'emb_length_use': 512,
            'seq_length': 8192,
        },
        'text-embedding-ada-002': {
            'emb_length_model': 1536,
            'emb_length_use': 1536,
            'seq_length': 8192,
        }
    }
    def __init__(self, key:str, model='text-embedding-3-small'):
        self.EMBED_SIZE = self.gpt_embedding[model]['emb_length_use']
        token_ex = 0.7
        self.MAX_LENGTH = int(self.gpt_embedding[model]['seq_length'] * token_ex)
        self.model = model
        self.client = OpenAI(api_key=key)
        self.need_normalize = self.EMBED_SIZE != self.gpt_embedding[model]['emb_length_model']

    def encode(self, inputs:str, to_list=False):
        """
        inputs: string
        output: 2d shape (1, embed_size)
        """
        def normalize_l2(x):
            x = np.array(x)
            if x.ndim == 1:
                norm = np.linalg.norm(x)
                if norm == 0:
                    return x
                return x / norm
            else:
                norm = np.linalg.norm(x, 2, axis=1, keepdims=True)
                return np.where(norm == 0, x, x / norm)
        response = self.client.embeddings.create(model=self.model, input=inputs)
        cut_dim = response.data[0].embedding[:self.EMBED_SIZE]
        norm_dim = normalize_l2(cut_dim) if self.need_normalize else cut_dim
        if not to_list:
            norm_dim = norm_dim.reshape(1, -1) # reshape to (1, EMBED_SIZE)
        return norm_dim