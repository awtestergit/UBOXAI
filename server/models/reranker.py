# -*- coding: utf-8 -*-
"""
    Reranker using Ollama
    Author: awtestergit
"""

import logging
import traceback
from interface.interface_model import IRerankerModel
    
class OllamaReRankerModel(IRerankerModel):
    def __init__(self, model:str='local_llm', threshod:float = 0.5, seq_size=4096):
        """
        wait till Ollama supports reranker
        """
        pass

    def rerank_score(self, inputA: str, inputB: list, top_n=-1, return_documents=False)->tuple[bool, float]:
        """
        wait till Ollama supports reranker
        return False for now indicating failed.
        """
        return False, 0.0