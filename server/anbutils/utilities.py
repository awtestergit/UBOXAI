"""
    Common utilities
    Author: awtestergit
"""

import json
from datetime import datetime
from dataclasses import make_dataclass
import numpy as np
from scipy.signal import resample

def extract_json_from_string(text: str) -> dict:
    """
    assuming a json string as: {"a": "value_a"}, with double quotes
    with an input that have portions of json string, 
        "a": "value_a, \n
        try to add { and }, then call json.loads
    Exceptions: if string after processing is not a json string, an exception will be thrown
    text: a json-like text string
    output: json dictionary or None if failed
    """
    if text is None or len(text) == 0:
        return {}
    
    #first strip the string
    text = text.strip(', \n')

    _length = len(text)
    # get the start {
    start = 0
    for i in range(0, _length):
        if text[i] == '{':
            start = i
            break
    if start == _length -1: # did not find '{'
        text = '{\n' + text # add '{'
        start = 0 # point to it

    # get the end }
    end = _length
    i = 0 # point to the start
    for i in range(_length-1, 0, -1):
        if text[i] == '}':
            end = i
            break
    _str = ''
    if end == _length: # did not find '}', add the '}'
        if text[-1] == '\"': #with quote
            _str = text[start:] + '\n}' # try add \n}
        else: #no quote
            _str = text[start:] + '\"\n}' # at least try... add \"\n}
    else:
        _str = text[start:end+1] # end + 1
    try:
        _jn = json.loads(_str)
    except:
        _jn = None
    return _jn

def text_list_strip(texts:list)->list:
    """
    remove empty items in the list
    """
    striped = list(filter(lambda x: x is not None and len(x.strip())>0, texts))
    return striped

def break_long_texts_into_chunks(texts:str, chuck_size:int, overlap:int) -> list[str]:
    """
    texts: a long string to be broken into chunks
    chunk_size: the size of each chunk
    overlap: the overlap of the second chunk to the first chunk, e.g., 'uperb!' is the overlap: [...here it is, superb!], [uperb! and a good way to ...]
    """
    length = len(texts)
    results = []
    start, end = 0, 0 # start and end index
    for idx in range(0, length, chuck_size):
        start = idx - overlap if idx > 0 else 0 # consider the overlap
        if idx > 0: # for the second chunks and so on
            end = idx + chuck_size - overlap if idx + chuck_size - overlap < length else length
        else:
            end = idx + chuck_size # the first loop when idx is 0
        start = int(start) # somehow start is not int?
        end = int(end) #
        text = texts[start:end]
        results.append(text)
    
    return results

def convert_text_list_to_chunks(texts:list, chunk_size:int, overlap:int, merge:False)->list[str]:
    """
    process a list of strings, break the list item if it is longer than chunk_size, or merge multiple items into a chuck if merge is true
    texts: a list of strings
    chunk_size: the chunk_size that every element of the list must be shorter than
    overlap: the overlap of the following element to the previous element
    merge: if true, will merge several elements till all length of the merged texts are about to longer than chunk_size
    output: the processed list
    """
    texts = text_list_strip(texts=texts)
    outputs = []
    _string = '' # temp string
    length = len(texts)
    for i in range(length):
        text = texts[i]
        if merge: # merge elements
            comb = _string + text + "\n"
            if len(comb) < chunk_size:
                _string = comb
                # check i
                if i == length-1: #the end
                    outputs.append(_string)
                continue
            else:# comb longer than chunk_size
                if len(_string) > 0: # if _string is not ''
                    outputs.append(_string)
                _string = ''
        
        # here, we need to add overlap, merge or no merge
        if len(outputs) > 0 and overlap > 0:
            previous = outputs[-1][-overlap:]
            _string = f"{previous}\n{text}"
        else:
            _string = text
        # if longer than chunk_size, break
        if len(_string) > chunk_size:
            chunks = break_long_texts_into_chunks(texts=_string, chuck_size=chunk_size, overlap=overlap)
            for chunk in chunks:
                outputs.append(chunk)
            # pop the last
            _string = outputs.pop()
        # now decide what to do
        # check i
        if i == length-1: #the end
            outputs.append(_string)
        elif not merge:# not merge
            outputs.append(_string)
        # continue
    
    return outputs

def convert_text_with_source_list_to_chunks(text_source:list[str, str], doc_path:str, chunk_size:int, overlap:int, merge:False)->list[str,str]:
    """
    process a list of strings, break the list item if it is longer than chunk_size, or merge multiple items into a chuck if merge is true
    text_source: a list of [str, str], text and its source
    doc_path: the document path. combine doc_path+source is the chunk's source_from string
    chunk_size: the chunk_size that every element of the list must be shorter than
    overlap: the overlap of the following element to the previous element
    merge: if true, will merge several elements till all length of the merged texts are about to longer than chunk_size
    output: the processed list
    """
    
    texts = []
    #preprocess the list to make sure all texts are less than chunk_size
    for text, source in text_source:
        # if not merge, append doc path to source
        source = source if merge else f"{doc_path}_{source}"
        if len(text) <= chunk_size:
            texts.append([text, source])
        else:#break into chunks
            _texts = break_long_texts_into_chunks(text, chuck_size=chunk_size, overlap=overlap)
            for _text in _texts:
                texts.append([_text, source])

    if merge: # reassamble the short texts to chunk_size 
        chunks = texts
        texts = []
        text = ''
        source_start = ''
        for idx, chunk in enumerate(chunks):
            current_text, current_source = chunk
            source_start = current_source if source_start == '' else source_start
            if (len(text+current_text) <= chunk_size):# if less than max
                text += "\n" + current_text
                #check if idx is the end of list
                if idx < len(chunks)-1:
                    continue
            #else: #longer than max
            source = f"{doc_path}_{source_start}_{current_source}"
            texts.append([text, source])
            text = current_text #set
            #check if idx is the end of list
            if idx == len(chunks)-1: # the end
                source = f"{doc_path}_{current_source}_{current_source}"
                texts.append([text, source])
                break
            # else, continue
            source_start = '' #reset
    return texts

def datetime_to_int(dt:datetime=None):
    """
    2023-11-30 -> 20231130
    """
    if dt is None:
        return -1
    dt_int = dt.year * 10000 + dt.month * 100 + dt.day
    return int(dt_int)

def dataclass_from_dict(_class_, dict):
    return make_dataclass(cls_name=_class_.__name__, fields=[(k, type(v)) for k, v in dict.items()])(**dict)

###audios
def resample_wav(wav, target_rate:int=16000)->tuple[int,any]:
    """
    input: a wav format (sample_rate, data)
    output: wav format (16000, data)
    """
    rate, data = wav
    return resample_data(rate=rate, data=data, target_rate=target_rate)

def resample_data(rate, data, target_rate:int=16000):
    
    # if stereo
    if len(data.shape)== 2: #(samples, 2)
        data = data.T[0] #get mono

    if rate != target_rate: # resample
        new_rate = target_rate
        data = resample(data, int(len(data)*new_rate/rate))
        rate = new_rate

    data = data.astype(np.float32) # convert to float32
    data /= np.max(np.abs(data))

    return rate, data

def convert_audio_int_bytes_to_numpy(data, sample_rate, bit_depth:int)->dict:
    """
    given a raw audio data of int bytes, convert to ndarray of float
    output: dict of {'sampling_rate': sample_rate, 'raw': data_np}
    """
    dtype = 0
    if bit_depth == 16:
        dtype = np.int16
    elif bit_depth == 32:
        dtype = np.int32
    else:
        raise ValueError(f"convert audio int bytes: bit depth must be either 16 or 32, input as: {bit_depth}")
    sample_width = int(bit_depth/8)
    data_np = np.frombuffer(data, dtype=dtype, count=len(data)//sample_width, offset=0) #
    data_np = data_np * (0.5**15) # to float
    data_np = data_np.astype(np.float32)
    return {
        'sampling_rate': sample_rate, 
        'raw': data_np
    }

def convert_audio_numpy_int_to_float(data:np.ndarray, sample_rate)->dict:
    """
    given a numpy data array, convert to ndarray of float
    output: dict of {'sampling_rate': sample_rate, 'raw': data_np}
    """
    if len(data)==0:
        return {}

    dtype = 0
    if not isinstance(data, np.ndarray):
        raise ValueError(f"convert audio numpy to float: data is not ndarray, but is {type(data)}")
    if 'int' not in str(type(data[0])).lower():
        raise ValueError(f"convert audio numpy int to float: data is not numpy int")
    
    data_np = data * (0.5**15) # to float, or / 32767
    data_np = data_np.astype(np.float32)
    return {
        'sampling_rate': sample_rate, 
        'raw': data_np
    }

def convert_audio_float32_to_int16(data:np.ndarray, to_bytes:bool=False)->np.ndarray|bytes:
    """
    convert np array of floats to np array of int, or bytes if to_bytes
    """
    if len(data)==0:
        return None
    #dtype = np.int32 if bit_depth==32 else np.int16
    dtype = np.int16
    data_type = str(type(data[0])).lower()
    if 'float' in data_type:
        data = data.clip(min=-1, max=1) # clip to -1 and 1
        data[data<0.0] *= 32768.0 # if negative
        data[data>0.0] *= 32767.0 # if positive
        data = np.floor(data).astype(dtype=dtype) # floor, to int
    elif 'int' in data_type:
        data = data.astype(dtype=dtype)
    else:
        raise ValueError(f"convert audio to int: data type should be either float or int, instead is: {data_type}")
    
    data = data if not to_bytes else data.tobytes()

    return data