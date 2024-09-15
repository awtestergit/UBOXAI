"""
    LLM using Ollama
    Author: awtestergit
"""

from interface.interface_model import ILanguageModel
from ollama import Client

class OllamaModel(ILanguageModel):
    def __init__(self, host:str="http://localhost:11434", model:str='local_llm', max_context_length=8192, seed=20240907) -> None:
        token_ex = 0.7 # 1 token ~= 0.7 character
        # max length 5000 = 8192*0.7
        max_context_length = int(max_context_length * token_ex)
        super().__init__(max_context_length, token_ex, seed)
        self.stop = []
        self.model = model
        self.client = Client(host=host)
        self.MAX_NEW_TOKENS = 4096 # max tokens to be genreated by model

    def generate(self, inputs, splitter='', stop=None, replace_stop=True, **kwargs):
        stop = stop if stop is not None else []
        if not replace_stop:
            stop.extend(self.stop)

        # system_prompt='', assistant_prompt=''
        key = 'system_prompt'
        if key in kwargs.keys():
            kwargs.pop(key)
        key = 'assistant_prompt'
        if key in kwargs.keys():
            kwargs.pop(key)

        return self.chat(inputs=inputs,model=self.model, splitter=splitter, stop=stop, replace_stop=replace_stop, **kwargs)

    def stream_generate(self, inputs, splitter='', stop=None, replace_stop=True, output_delta=False, **kwargs):
        stop = stop if stop is not None else []
        if not replace_stop:
            stop.extend(self.stop)

        # system_prompt='', assistant_prompt=''
        key = 'system_prompt'
        if key in kwargs.keys():
            kwargs.pop(key)
        key = 'assistant_prompt'
        if key in kwargs.keys():
            kwargs.pop(key)

        return self.stream_chat(inputs, self.model, splitter=splitter, stop=stop, replace_stop=replace_stop, output_delta=output_delta, **kwargs)

    def chat(self, inputs, system_prompt='', assistant_prompt='', history=[], splitter='', stop=None, replace_stop=True, **kwargs):
        stop = stop if stop is not None else []
        if not replace_stop:
            stop.extend(self.stop)
        seed = self.seed if self.seed > 0 else None
        # consruct message
        messages = self.__construct_chat_message__(inputs, system_prompt, assistant_prompt, history)
        kwargs = self.__kwargs_compatible__(messages, kwargs)
        kwargs['stop'] = stop
        kwargs['seed'] = seed
        response = self.client.chat(model=self.model, messages=messages, options=kwargs)
        answer = response['message']['content']
        answer = answer if answer is not None else ''
        answer = answer if len(splitter)==0 else answer.split(splitter)[-1]
        return answer

    def stream_chat(self, inputs, system_prompt='', assistant_prompt='', history=[], splitter='', stop=None, replace_stop=True, output_delta=False, **kwargs):
        stop = stop if stop is not None else []
        if not replace_stop:
            stop.extend(self.stop)
        # consruct message
        messages = self.__construct_chat_message__(inputs, system_prompt, assistant_prompt, history)
        kwargs = self.__kwargs_compatible__(messages, kwargs)
        #seed
        seed = self.seed if self.seed > 0 else None
        kwargs['stop'] = stop
        kwargs['seed'] = seed

        response = self.client.chat(model=self.model, messages=messages, stream=True, options=kwargs)
        texts = ''
        for chunk in response:
            t = chunk['message']['content']
            t = t if t is not None else ''
            if output_delta: # output delta only
                texts = t
            else:
                texts += t
                texts = texts.split(splitter)[-1] if len(splitter)>0 else texts # split by splitter, if any
            yield texts

    def __kwargs_compatible__(self, messages:list, kwargs):
        # get keys
        key = 'max_new_tokens'
        num_predict = self.MAX_NEW_TOKENS
        if key in kwargs.keys():
            #messages_tokens = self.num_tokens_from_messages(messages)
            num_predict = kwargs.pop(key)# + messages_tokens
        kwargs['num_predict'] = num_predict
        key = 'repetition_penalty'
        repeat_penalty = 1.1
        if key in kwargs.keys():
            repeat_penalty = kwargs.pop(key)
        kwargs['repeat_penalty'] =  repeat_penalty
        key = 'do_sample' # remove do_sample key
        if key in kwargs.keys():
            kwargs.pop(key)
        key = 'num_ctx'
        if key not in kwargs.keys():
            ctx_length = self.MAX_LENGTH - num_predict
            kwargs['num_ctx'] = ctx_length

        return kwargs

# support OpenAI
from openai import OpenAI
import tiktoken

class GPTModel(ILanguageModel):
    gpt_max_tokens = {
        "gpt-4o": 128000, # gpt-4o
        "gpt-4-turbo": 128000,
        "gpt-4": 8192,
        "gpt-3.5-turbo": 16000
    }
    def __init__(self, key:str, model:str='gpt-4o', seed=20240614) -> None:
        token_ex = 0.7 # 1 token ~= 0.7 character
        # max length 5000 = 8192*0.7
        max_context_length = self.gpt_max_tokens[model]
        max_context_length = int(max_context_length * token_ex)
        max_context_length = 5000
        super().__init__(max_context_length, token_ex, seed)
        self.stop = []
        self.client = OpenAI(api_key=key)
        self.model = model
        self.MAX_NEW_TOKENS = 4096 # max tokens to be genreated by model

    def generate(self, inputs, splitter='', stop=None, replace_stop=True, **kwargs):
        stop = stop if stop is not None else []
        if not replace_stop:
            stop.extend(self.stop)

        # system_prompt='', assistant_prompt=''
        key = 'system_prompt'
        if key in kwargs.keys():
            kwargs.pop(key)
        key = 'assistant_prompt'
        if key in kwargs.keys():
            kwargs.pop(key)

        return self.chat(inputs=inputs,model=self.model, splitter=splitter, stop=stop, replace_stop=replace_stop, **kwargs)

    def stream_generate(self, inputs, splitter='', stop=None, replace_stop=True, output_delta=False, **kwargs):
        stop = stop if stop is not None else []
        if not replace_stop:
            stop.extend(self.stop)

        # system_prompt='', assistant_prompt=''
        key = 'system_prompt'
        if key in kwargs.keys():
            kwargs.pop(key)
        key = 'assistant_prompt'
        if key in kwargs.keys():
            kwargs.pop(key)

        return self.stream_chat(inputs, self.model, splitter=splitter, stop=stop, replace_stop=replace_stop, output_delta=output_delta, **kwargs)

    def chat(self, inputs, system_prompt='', assistant_prompt='', history=[], splitter='', stop=None, replace_stop=True, **kwargs):
        stop = stop if stop is not None else []
        if not replace_stop:
            stop.extend(self.stop)
        seed = self.seed if self.seed > 0 else None
        # consruct message
        messages = self.__construct_chat_message__(inputs, system_prompt, assistant_prompt, history)
        kwargs = self.__kwargs_compatible__(messages, kwargs)
        response = self.client.chat.completions.create(model=self.model, messages=messages, stop=stop, seed=seed, **kwargs)
        answer = response.choices[0].message.content
        answer = answer if answer is not None else ''
        answer = answer if len(splitter)==0 else answer.split(splitter)[-1]
        return answer

    def stream_chat(self, inputs, system_prompt='', assistant_prompt='', history=[], splitter='', stop=None, replace_stop=True, output_delta=False, **kwargs):
        stop = stop if stop is not None else []
        if not replace_stop:
            stop.extend(self.stop)
        # consruct message
        messages = self.__construct_chat_message__(inputs, system_prompt, assistant_prompt, history)
        kwargs = self.__kwargs_compatible__(messages, kwargs)
        #seed
        seed = self.seed if self.seed > 0 else None

        response = self.client.chat.completions.create(model=self.model, messages=messages, stop=stop, seed=seed, stream=True, **kwargs)
        texts = ''
        for chunk in response:
            t = chunk.choices[0].delta.content
            t = t if t is not None else ''
            if output_delta: # output delta only
                texts = t
            else:
                texts += t
                texts = texts.split(splitter)[-1] if len(splitter)>0 else texts # split by splitter, if any
            yield texts

    def __kwargs_compatible__(self, messages:list, kwargs):
        # get keys
        key = 'max_new_tokens'
        max_tokens = -1
        if key in kwargs.keys():
            #messages_tokens = self.num_tokens_from_messages(messages)
            max_tokens = kwargs.pop(key)# + messages_tokens
        key = 'max_tokens' # continue to check max_tokens for different bindings
        if key in kwargs.keys():
            max_tokens = kwargs.pop(key)
        key = 'repetition_penalty'
        frequency_penalty = 1.1
        if key in kwargs.keys():
            frequency_penalty = kwargs.pop(key)
        key = 'repeat_penalty' # continue to check 
        if key in kwargs.keys():
            frequency_penalty = kwargs.pop(key)
        key = 'do_sample' # remove do_sample key
        if key in kwargs.keys():
            kwargs.pop(key)
        key = 'top_p'
        top_p = 1
        if key in kwargs.keys():
            top_p = kwargs.pop(key)
        key = 'temperature'
        temperature = 0.5
        if key in kwargs.keys():
            temperature = kwargs.pop(key)
        kwargs = {
            'frequency_penalty': frequency_penalty,
            'top_p': top_p,
            'temperature': temperature,
        }
        # check max_tokens, add to kwargs, else no
        if max_tokens < self.MAX_NEW_TOKENS:
            kwargs['max_tokens'] = max_tokens
        return kwargs

    def num_tokens_from_messages(self, messages):
        """Return the number of tokens used by a list of messages."""
        try:
            encoding = tiktoken.encoding_for_model(self.model)
        except KeyError:
            #print("Warning: model not found. Using cl100k_base encoding.")
            encoding = tiktoken.get_encoding("cl100k_base")
        if any('gpt-4' in model for model in self.gpt_max_tokens.keys()) or any('gpt-3' in model for model in self.gpt_max_tokens.keys()):
            tokens_per_message = 3
            tokens_per_name = 1
        else:
            raise NotImplementedError(
                f"""num_tokens_from_messages() is not implemented for model {model}. See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens."""
            )
        num_tokens = 0
        for message in messages:
            num_tokens += tokens_per_message
            for key, value in message.items():
                num_tokens += len(encoding.encode(value))
                if key == "name":
                    num_tokens += tokens_per_name
        num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
        return num_tokens