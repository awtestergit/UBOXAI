# -*- coding: utf-8 -*-

"""
    Model interfaces
    Author: awtestergit
"""

import json
import numpy
from typing import Iterator

"""
IBaseModel, interface to wrap model
"""
class IBaseModel():
    ### embedding model
    EMBED_SIZE = 1024 # embedding size of the model
    MAX_LENGTH = 8000 # max seq length, e.g, openai 8192

"""
IRerankerModel, interface to wrap model
"""
class IRerankerModel(IBaseModel):
    ### embedding model
    MAX_LENGTH = 4000 # max seq length, e.g., Cohere 4096
    def __init__(self, threshod:float = 0.5) -> None:
        self.threshold = threshod

    def rerank_score(self, inputA:str, inputB:list)->tuple[bool, float]:
        raise NotImplementedError("IRerankerModel rerank score not implemented")

"""IEmbeddingModel
"""
class IEmbeddingModel(IBaseModel):
    ### embedding model
    EMBED_SIZE = 1024 # embedding size of the model
    MAX_LENGTH = 8000 # max seq length, openai 8192
    def encode(self, inputs, to_list:bool=False, *args):
        raise NotImplementedError("ILanguageModel base class encode")

"""
ILanguageModel, interface to wrap model
"""
class ILanguageModel(IBaseModel):
    def __init__(self, max_context_length, token_ex, seed) -> None:
        self.MAX_LENGTH = max_context_length # max token lengths
        self.TOKEN_EX = token_ex # 
        self.seed = seed

    def generate(self, inputs, splitter='', stop=[], replace_stop=True, **kwargs):
        raise NotImplementedError("ILanguageModel base class generate")

    def chat(self, inputs, history=[], splitter='', stop=[], replace_stop=True, **kwargs):
        raise NotImplementedError("ILanguageModel base class generate")

    def stream_generate(self, inputs, splitter='', stop=[], replace_stop=True, output_delta=False, **kwargs):
        raise NotImplementedError("ILanguageModel base class stream generate")

    def stream_chat(self, inputs, history=[], splitter='', stop=[], replace_stop=True, output_delta=False, **kwargs):
        raise NotImplementedError("ILanguageModel base class stream chat")

    def __construct_chat_message__(self, inputs:str, system_prompt:str, assistant_prompt:str, history:list)->list:
        # 1. construct system prompt
        # 2. construct history
        # 3. construct input
        # 4. construct assistant prompt, ignored
        messages = []
        if len(system_prompt)>0:
            system = {
                'role': 'system',
                'content': system_prompt
            }
            messages.append(system)
        if len(history)>0:
            for user, bot in history:
                user = {
                    'role': 'user',
                    'content': user
                }
                messages.append(user)
                bot = {
                    'role': 'assistant',
                    'content': bot
                }
                messages.append(bot)
        user = {
            'role': 'user',
            'content': inputs
        }
        messages.append(user)
        return messages
    
    def __extract_json_from_answer__(self, answer_str: str) -> dict:
        _length = len(answer_str)
        # get the start {
        start = 0
        for i in range(0, _length):
            if answer_str[i] == '{':
                start = i
                break
        if start == _length -1: # did not find '{'
            answer_str = '{\n' + answer_str # add '{'
            start = 0 # point to it

        # get the end }
        end = _length
        i = 0 # point to the start
        for i in range(_length-1, 0, -1):
            if answer_str[i] == '}':
                end = i
                break
        _str = ''
        if end == _length: # did not find '}', add the '}'
            if answer_str[-1] == '\"': #with quote
                _str = answer_str[start:] + '\n}' # try add \n}
            else: #no quote
                _str = answer_str[start:] + '\"\n}' # at least try... add \"\n}
        else:
            _str = answer_str[start:end+1] # end + 1
        
        #print(f"end is: {end}; _str is: {_str}")
        
        _jn = json.loads(_str.strip())
        return _jn


"""ITTSModel
    tts model wrapper
"""
class ITTSModel(IBaseModel):
    def __init__(self) -> None:
        pass

    def text_to_data(self, input:str | Iterator, streaming=False, **kwargs) -> tuple[int, numpy.array]:
        raise NotImplementedError("ITTSModel base class, text_to_data")



"""IASRModel
    ASR model wrapper
"""
class IASRModel(IBaseModel):
    def __init__(self) -> None:
        pass

    def voice_to_text(self, data, rate, language, bit_depth, **kwargs) -> str:
        raise NotImplementedError("IASRModel base, voice to text")

#
# global continue flag for generating
#
from threading import Event, Lock
class llm_continue():
    def __init__(self) -> None:
        self.__exit_event__ = Event()
        self.__exit_event__.set() # any wait will pass
        self.__continue_lock__ = Lock()
    
    def check_continue_flag(self, timeout=0.5):# default non-blocking lock, wait for 0.5sec
        """
        in danger of deadlock - make sure to set exit event if cannot acquire the lock
        """
        try:
            flag = self.__continue_lock__.acquire(blocking=False)
            if not flag: # if cannot acquire the lock, indicating main thread is hold lock to set continue flag
                return False # return false
            # if lock acquired
            flag = self.__exit_event__.wait(timeout)
            if not flag:
                return False
        finally:
            self.__continue_lock__.release() # release
        # if here    
        return True

    def set_stop_flag(self):
        """
        check_continue_flag is the only place the event is clear() to make other threads wait
        so must set this flag when any function calling 'check_continue_flag' exits the routine
        """
        self.__exit_event__.clear() # any wait will block

    def reset_stop_flag(self):
        self.__exit_event__.set() # any wait will pass

class ContinueExit(Exception):
    pass
