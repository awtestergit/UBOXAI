# -*- coding: utf-8 -*-

"""
    AIGC front end server, enabling users to interact with AI
    Author: awtestergit
"""
import logging
import os
from typing import Iterator
from interface.interface_readwrite import IDocReaderWriter, TextReaderWriter
from readwrite.pdf_readwrite import PDFReaderWriter
from readwrite.word_readwrite import WordReaderWriter
import faiss # faiss index
import datetime
import traceback
import math
import numpy as np
from anbutils import utilities
from interface.interface_model import ILanguageModel, IEmbeddingModel, llm_continue, ContinueExit
from qdrantclient_vdb.qdrant_manager import qcVdbManager

class webui_handlers():
    def __init__(self, llm:ILanguageModel, emb_model:IEmbeddingModel, reranker_model, ocr:IDocReaderWriter, vdb_mgr, **kwargs) -> None:
        self.ocr = ocr
        self.llm = llm
        self.emb_model=emb_model
        self.reranker = reranker_model
        self.vdb_mgr=vdb_mgr

    def __get_reader_by_filename__(self, filename:str, is_ocr=False)->IDocReaderWriter:
        if len(filename) == 0:
            return None

        if is_ocr:
            return self.ocr

        _type = filename.split('.')[-1].lower()
        reader: IDocReaderWriter
        if _type == 'txt': #text
            reader = TextReaderWriter()
        elif _type == 'pdf':
            reader = PDFReaderWriter()
        elif _type == "docx":
            reader = WordReaderWriter()
        else:
            reader = None # no rtf, for example
        
        return reader

    # file diff button click
    def compare_files(self, filenameA='', filenameB='', compare_by=0, a_ocr=False, b_ocr=False, streaming=True, continue_flag:llm_continue=None)->dict|Iterator:
        """
        compare files to illustrate differences
        inputs:
            fileA/B: two files
            compare_by: # 0: page, 1: document, 2: paragraph
            a/b_ocr: if the input file A/B is ocr scanned file
            streaming: True, to return generators instead of whold output strings
        output: a dict, or a generator of, depending on streaming
            {
                status: 0 - success, 1 - warning, -1 error,
                error: error text,
                A: a text,
                A_NAME: a filename
                B: b text,
                B_NAME: b filename
            }
        any exception will raise back to caller
        """
        output = {
            'status': 0,
            'error': '',
            'A': '',
            'B': '',
        }

        if len(filenameA)==0 or len(filenameB)==0:
            output['status'] = -1
            output['error'] = 'compare_files: input files can not be empty'
            return output
        
        """
        if compare_by.lower() == 'paragraph':
            compare_by = 0
        elif compare_by.lower() == 'page':
            compare_by = 1
        else:
            compare_by = 2
        """
        genA, genB = None, None
        error = None

        try:
            # if ocr, only by page or by document is allowed
            reconstruct_paragraph_at_pagebreak = True if compare_by==0 else False # for docx, if by page, reconstruct, else if by paragraph, do not construct paragraph at page break, of Word docs
            readerA = self.__get_reader_by_filename__(filenameA, a_ocr)
            genA = readerA.read_doc_to_texts(doc_path=filenameA, reconstruct_paragraph_at_pagebreak=reconstruct_paragraph_at_pagebreak, read_by=compare_by, streaming=streaming, continue_flag=continue_flag)
            readerB = self.__get_reader_by_filename__(filenameB, b_ocr)
            genB = readerB.read_doc_to_texts(doc_path=filenameB, reconstruct_paragraph_at_pagebreak=reconstruct_paragraph_at_pagebreak, read_by=compare_by, streaming=streaming, continue_flag=continue_flag)
            filenameA = filenameA.split('/')[-1] # get the filename, not full path
            filenameB = filenameB.split('/')[-1]
        except ContinueExit as ce:
            raise # re-raise so that http route can handle it
        except Exception:
            error = traceback.format_exc()
            # debug log
            #print(error)
            logging.error(f"....compare files exception: {error}")
        finally:
            pass

        if error:
            output['status'] = -1
            output['error'] = "Reading files failed."
            output['A'] = ''
            output['A_NAME'] = filenameA
            output['B'] = ''
            output['B_NAME'] = filenameB
            yield output
            return

        a_total, b_total = 0, 0 # total paragraph/pages of each

        a_font = """<span style='background-color:#ffa500'>"""
        b_font = """<span style='background-color:#87cefa'>"""
        font_end = "</span>"

        ####
        #helpers
        # loop through t1 and t2
        def get_ab_texts(a_gen, b_gen)->tuple[str, str, bool, bool]:
            # return a str, b str, a_end:True/False, b_end:True/False
            #a_list, b_list = [], []
            a_str, b_str = '',''
            a_end, b_end = False, False
            try:
                a_str = next(a_gen)
            except StopIteration:
                a_str = ''
                a_end = True
            try:
                b_str = next(b_gen)
            except StopIteration:
                b_str = ''
                b_end = True
            #return a_list, b_list, a_end, b_end
            return a_str, b_str, a_end, b_end

        def compare_two(a_str:str, b_str:str, replace_words_file='./compare_words.txt')->tuple[str, str]:
            # output: two list containing compared words highlighted difference using <span>...

            # read compare words
            # replace look-alike but different words (different unicode)
            wf = replace_words_file
            replace_words = []
            if os.path.exists(wf):
                with open(wf, 'r') as f:
                    r = f.readlines()
                    for text in r:
                        if text[0] == '#':
                            continue
                        ts = text.split(',')
                        a = ts[0].strip()
                        b = ts[1].strip()
                        replace_words.append((a,b))
            else:
                # log
                #print(f"compare word file '{wf}' does not exists.")
                logging.debug(f"compare word file '{wf}' does not exists.")

            #a_str = ''.join(a_list) if len(a_list)>0 else None
            #b_str = ''.join(b_list) if len(b_list)>0 else None

            # normalize
            from unicodedata import normalize
            string1 = normalize('NFKD', a_str)
            string2 = normalize('NFKD', b_str)
            
            #replace_words = [('民', '⺠'),('见','⻅'),] # replace look-alike but different words (different unicode)
            for rw1, rw2 in replace_words:
                string1 = string1.replace(rw2, rw1)
                string2 = string2.replace(rw2, rw1)

            from difflib import Differ
            d = Differ(charjunk=lambda x: x==' ') # char ' ' considered as junk
            diff = d.compare(string1, string2)
            result = list(diff)

            def is_ignored_word(wb:str): # if ignored, do not show at all
                ignore_list = [' ',',','，',':','：','(',')','{','}','【','】','.','。',';','；']
                #wb = w.encode()
                if wb in ignore_list:
                    return True
                return False

            s = [] # doc a
            ss = [] # doc b
            for r in result:
                to_ignore = is_ignored_word(r[-1])
                if r[:2] == '- ':
                    if not to_ignore: # doc a
                        if len(s) > 0 and  s[-1] == font_end: # remove </font> and add it after r[-1]
                            s[-1] = r[-1] #remove the </font>
                            s.append(font_end) #add the </font>
                        else: # add <font>...</font>
                            s.append(a_font)
                            s.append(r[-1])
                            s.append(font_end)
                    else: # ignored word, add back
                        s.append(r[-1])
                elif r[:2] == '+ ':
                    if  not to_ignore: #doc b
                        if len(ss) > 0 and ss[-1] == font_end:
                            ss[-1] = r[-1]
                            ss.append(font_end)
                        else:
                            ss.append(b_font)
                            ss.append(r[-1])
                            ss.append(font_end)
                    else: #add word as is
                        ss.append(r[-1])
                else: #not to_ignore: # if ignore, do not add at all
                    s.append(r[-1])
                    ss.append(r[-1])

            a = ''.join(s)
            b = ''.join(ss)
            a = a.replace('\n',"<p>") # replace newline \n with html <p>
            b = b.replace('\n', "<p>")

            return a, b

        try:
            # back to function
            a_str, b_str = '','' # output a, b strings
            a_str, b_str, a_end, b_end = get_ab_texts(genA, genB)
            while((not a_end) and (not b_end)):
                #
                #a_list = list(filter(lambda x: x.strip() != '', a_list)) # strip items
                #b_list = list(filter(lambda x: x.strip() != '', b_list))
                #a_total += len(a_list) # add to totals
                #b_total += len(b_list)
                a_total += 1
                b_total += 1

                # compare
                a_str, b_str = compare_two(a_str, b_str)
                
                # yield
                output['status'] = 0
                output['error'] = ''
                output['A'] = a_str
                output['A_NAME'] = filenameA
                output['B'] = b_str
                output['B_NAME'] = filenameB
                yield output

                # continue
                a_str, b_str, a_end, b_end = get_ab_texts(genA, genB)
            
            # check leftovers
            if not a_end: # a has more
                s = []
                s.append(a_font)
                for items in genA:
                    s.append(items)
                    a_total += 1
                s.append(font_end)
                sa = ''.join(s)
                a_str += sa

            if not b_end: # b has mor
                s = []
                s.append(b_font)
                for items in genB:
                    s.append(items)
                    b_total += 1
                s.append(font_end)
                sb = ''.join(s)
                b_str += sb

            if not a_end or not b_end:
                # yield
                output['status'] = 0
                output['error'] = ''
                output['A'] = a_str
                output['A_NAME'] = filenameA
                output['B'] = b_str
                output['B_NAME'] = filenameB
                yield output

            # check if any warning
            if a_total != b_total:
                warning = f"Warning! The number of paragraphs of {filenameA} is {a_total}, {filenameB} is {b_total}"
                # yield
                output['status'] = 1
                output['error'] = warning
                output['A'] = ''
                output['A_NAME'] = filenameA
                output['B'] = ''
                output['B_NAME'] = filenameB
                yield output
        except (ContinueExit, GeneratorExit): # yield will raise GeneratorExit if client aborts
            # log
            #print("....doc_compare:: stop signal received, exit...")
            logging.debug("....doc_compare:: stop signal received, exit...")
            raise # re raise
        except Exception:
            error = traceback.format_exc()

            # debug log
            #print(".......doc_compare:: " + error)
            logging.error(".......doc_compare:: " + error)

        if error:
            output['status'] = -1
            output['error'] = "Reading files failed."
            output['A'] = ''
            output['A_NAME'] = filenameA
            output['B'] = ''
            output['B_NAME'] = filenameB
            yield output
            return

    def doc_upload(self, file, is_ocr=False, read_by=0, continue_flag:llm_continue=None):
        # read_by default by page. 0 - page, 1 - document, 2 - paragraph
        FAISSINDEX = None
        texts = []

        try:
            if file is not None:
                MAX = self.emb_model.MAX_LENGTH
                overlap = 20 # overlap
                overlap = 0
                reader:IDocReaderWriter = self.__get_reader_by_filename__(file.name, is_ocr=is_ocr)
                t1 = reader.read_doc_to_texts(doc_path=file.name, read_by=read_by, continue_flag=continue_flag)
                # t1 is an iterator
                for t in t1:
                    texts.append(t)
                # break into chunks
                texts = utilities.convert_text_list_to_chunks(texts=texts, chunk_size=MAX, overlap=overlap, merge=False)#no merge
                # texts holds all document chunks
                # build faiss index
                DIM = self.emb_model.EMBED_SIZE
                FAISSINDEX = faiss.IndexFlatL2(DIM) # indexflat
                for t in texts:
                    v = self.emb_model.encode(t) # make shape [1, DIM], move to cpu
                    FAISSINDEX.add(v)
            return FAISSINDEX, texts
        except ContinueExit:
            # log
            #print(".........doc_upload received stop signal and exits...")
            logging.debug(".........doc_upload received stop signal and exits...")
            raise # reraise
        except:
            error = traceback.format_exc()
            #log
            #print(f".........doc_upload exception: {error}...")
            logging.error(f".........doc_upload exception: {error}...")
 
        return FAISSINDEX, texts
    
    def doc_question(self, query, words=100, faiss_index=None, texts=[], rerank_threshold=0.9, rerank_min_score=0.1, continue_flag:llm_continue=None)->Iterator:
        """
        input:
        query, user's query
        words, max new tokens to generate
        faiss_index, the search index
        texts, the original texts list
        rerank threshold: to find contexts > this threshold
            min_score: if rerank score below this score, do not return context
        output:
        {
            status: 0 - success, 1 - warning, -1 error,
            error: error text,
            text: newly generated text
            sources: source
        }
        exception: this will raise ContinueExit from llm generate/chats, caller needs to handle ContinueExit
        """
        def __answer_question__():
            status = 0
            error = ''
            sources = []
            context = []

            output = {
                'status': 0,
                'error': '',
                'text': '',
                'sources': [],
            }
            if faiss_index is None:
                output['status'] = -1
                output['error'] = "Error! Index for file is empty."
                yield output
                return
            # else

            max_score = 0.
            # get k neighbors from index
            # max length of each text in texts is self.emb.MAX
            maxK = math.floor(self.llm.MAX_LENGTH/self.emb_model.MAX_LENGTH)
            maxK = 10 if maxK > 10 else maxK
            k = len(texts)
            k = k if k < maxK else maxK
            k = 2 if k < 2 else k
            #print(f"........k is: {k}")
            logging.debug(f"........k is: {k}")

            xq = self.emb_model.encode(query)
            _, INDEX = faiss_index.search(xq, k) # INDEX array shape [1, k]
            # a list of 3 to choose
            score_context = []
            score_texts = []
            for idx in INDEX[0]: # loop each index in array
                if idx == -1:
                    
                    #print(f"webui_handler::doc_question faiss index is -1")
                    logging.warning(f"webui_handler::doc_question faiss index is -1")
                    
                    break
                score_texts.append(texts[idx])
            if len(score_texts) > 0:
                success, index_score = self.reranker.rerank_score(query, score_texts) # rerank element against text indexed at INDEX[0] array
                if success:
                    for idx, score in index_score:
                        score_context.append([score, score_texts[idx]]) # save to list
                else: # reranker failed, possibly cohere no credit or exceed quota
                    score = 0.5
                    # fake a score, using the score_text descending order
                    score_context = [[(score - 0.01*i), text] for i, text in enumerate(score_texts)]

            #print(f".......score_context: {score_context}")
            logging.debug(f".......score_context: {score_context}")

            if len(score_context)>0:
                score_context.sort(key=lambda x: x[0], reverse=True) # sort by score, descending
                max_score = score_context[0][0]
                if max_score > rerank_min_score: # if rank score too low, discard
                    threshold = rerank_threshold #
                    if max_score > threshold: # use the top score
                        context = [score_context[0][1]] # make it iterable
                    else: # use the top 3
                        top = 3
                        context = [text[1] for text in score_context[:top]] #iterable
                    #source
                    max_score = "{:.2%}".format(max_score)
                    #sources += f"审核问题：\n{query}\n来源：\n得分{max_score}\n{context}\n\n"
            if len(context)==0: # did not find any relevant info, most likely an error
                #sources += "Can not find relevant contexts, possible an error. Check server log for details."
                #status = 1 # warning
                sources = ["Can not find relevent contexts from the document. The following is a generic answer."] # iterable
            else:
                sources = context

            # current time
            current_time = datetime.datetime.now()
            current_time = current_time.strftime('%Y-%m-%d, %H:%M:%S')
            current_day = datetime.datetime.today().strftime('%A')
            current_time = f"{current_time}, {current_day}"

            sys_prompt = """"You are an AI, your name is {name}. The current time is {current}.
You are to answer user's question based on the provided background information.

Background Information:
{context}

Use the above background information to respond to user's inquery, do not make up your answer.
You must answer in English.
"""
            user_prompt = """{query}"""
            assistant_prompt = ''
            name = 'Bot'
            # query
            sys_prompt = sys_prompt.format(name=name, current=current_time, context=context)
            user_prompt = user_prompt.format(query=query)
            assistant_prompt = assistant_prompt.format(name=name)
            #inputs = prompt.format(name=name, context=context, query=query)

            #print(f"system: {sys_prompt}\nuser: {user_prompt}\nassistant: {assistant_prompt}")
            
            # tight
            kwargs = {
                'temperature': 0.3,
                'max_new_tokens': words,
                'top_k': 3,
                'top_p': 0.95,
                'repetition_penalty': 1.1,
            }
            stop = ['[['] # extend self.stop with this
            response = self.llm.stream_chat(inputs=user_prompt, system_prompt=sys_prompt, assistant_prompt=assistant_prompt, stop=stop, replace_stop=False, **kwargs)
            for text in response:
                text = text.strip()
                
                #print(f".........{text}")

                output['status'] = status
                output['error'] = error
                output['text'] = text
                output['sources'] = []
                yield output
            # send sources
            for source in sources:
                output['status'] = status
                output['error'] = error
                output['text'] = ''
                output['sources'] = source
                yield output
        
        out_streamer = __answer_question__() # assign the generator to out_streamer
        yield from out_streamer

    # file element extraction button click
    def doc_extract(self, elements:list=[], faiss_index=None, texts=[], rerank_threshold=0.9, rerank_min_score=0.1, continue_flag:llm_continue=None):
        """
        input: 
            elements: a list of elements as the information to be extracted, if provided
            faiss index, texts - the index and texts
            reranker threshold and min score
        output:
        {
            status: 0 - success, 1 - warning, -1 error,
            error: error text,
            element: information extracted
            detail: the element detail 
            sources: source of this element
            source_id: id of this source
        }
        exception: this will raise ContinueExit from llm generate/chats, caller needs to handle ContinueExit
        """
        model = self.llm
        #
        sources = ''
        output = {
            'status': 0,
            'error': '',
            'element': '',
            'detail': '',
            'sources': '',
            'source_id': -1,
        }
        # LLM splitter
        splitter = 'AI:'
        max_new_tokens = 100 #
        kwargs = {
            'temperature': 0.5,
            'top_k': 10,
            'top_p': 0.8,
            'max_new_tokens': max_new_tokens, # answer max length
        }
        if elements is None or len(elements) == 0: #extract all elements
            prompt = """You are an AI, a language expert. You need to extract relevant details from the background information.

Background Information:
[
{context}
]

Output should follow this format:
<Key Information Point>|<Relevant Details or 'None'>

REMEMBER: You need to identify key information points and extract relevant details from the background information. do not make up your answers.
You must answer in English.

Answer should start immediately with <Key Information Point>|<Relevant Details or 'None'>.

{splitter}
"""
            def extract_element(output, start=0, is_leftover=False):
                next_start = start
                text = output[start:]
                sep = '\n'
                split = '|'
                first = ''
                element, detail = '', ''
                
                if is_leftover:
                    first = output[start:]
                elif text.find(sep) > 0:
                    items = text.split(sep)
                    first = items[0]
                    next_start += len(first) + 1
                
                #print(first)
                
                if len(first) >0:
                    first = first.strip(split) # in case of '\element\detail\', strip the '\'
                    ss = first.split(split)
                    if len(ss) == 2:
                        (element, detail) = ss

                return element, detail, next_start

            for idx, context in enumerate(texts):
                output = {
                    'status': 0,
                    'error': '',
                    'element': '',
                    'detail': '',
                    'sources': '',
                    'source_id': idx,
                }
                title = f"The {idx+1} paragraph: "
                sources = title + texts[idx]
                query = prompt.format(context=context, splitter=splitter)
                #print(query)
                stop = ['\n\n']
                results = model.stream_generate(query, splitter=splitter, stop=stop, **kwargs)# max_new_tokens=max_new_tokens)#, repetition_penalty=1.2)
                start, next_start = 0,0
                for result in results:
                    (e, d, next_start) = extract_element(result, start)
                    if len(e) > 0:
                        # yield output
                        output['element'] = e
                        output['detail'] = d
                        output['sources'] = sources
                        print(f"e: {e}, d:{d}")
                        yield output

                    start = next_start

                (e, d, next_start) = extract_element(result, start, is_leftover=True)
                # yield output
                output['element'] = e
                output['detail'] = d
                output['sources'] = sources
                yield output

        else: # extract one by one
            if faiss_index is None:
                output['status'] = -1
                output['error'] = "Error! Index for file is empty."
                yield output
                return
            # else

            max_new_tokens = 100
            kwargs = {
                'temperature': 0.1,
                'top_k': 3,
                'top_p': 0.95,
                'max_new_tokens': max_new_tokens, # answer max length
            }

            prompt = """You are an AI, a language expert. you need to extract relevant details from the background information.

Background Information:
[
{context}
]

The above background information contains details about [{extract}], you need to identify and extract the specific details related to '{extract}'.
You must answer in English.
Output in JSON format:
{{
    "name": "{extract}", // key information
    "value": "string", // details regarding to '{extract}' or "None"
}}
Your output should provide only the "name" and "value" for '{extract}', and refrain from fabricating any other answers.

Output should start immediately with
```json

"""
            # get the elements
            elements = elements.split('\n')
            elements = list(filter(lambda x: len(x.strip())>0, elements))
            # for each element, get the max scored context
            for idx, element in enumerate(elements):
                output = {
                    'status': 0,
                    'error': '',
                    'element': element,
                    'detail': '',
                    'sources': '',
                    'source_id': idx,
                }

                max_score = 0.
                # get k neighbors from index
                # max length of each text in texts is self.emb.MAX
                maxK = math.floor(self.llm.MAX_LENGTH/self.emb_model.MAX_LENGTH)
                maxK = 10 if maxK > 10 else maxK
                maxK = 3 if maxK < 3 else maxK
                k = len(texts)
                k = k if k < maxK else maxK
                #print(f"........k is: {k}")
                xq = self.emb_model.encode(element)
                _, INDEX = faiss_index.search(xq, k) # INDEX array shape [1, k]
                # a list of 3 to choose
                score_context = []
                score_texts = []
                for idx in INDEX[0]: # loop each index in array
                    if idx == -1:
                        
                        #print(f"aigc_webui::doc_tract faiss index is -1")
                        logging.warning(f"aigc_webui::doc_tract faiss index is -1")
                        
                        break
                    score_texts.append(texts[idx])
                if len(score_texts) > 0:
                    success, index_score = self.reranker.rerank_score(element, score_texts) # rerank element against text indexed at INDEX[0] array
                    if success:
                        for idx, score in index_score:
                            score_context.append([score, score_texts[idx]]) # save to list
                    else: # reranker failed, possibly cohere no credit or exceed quota
                        score = 0.5
                        # fake a score, using the score_text descending order
                        score_context = [[(score - 0.01*i), text] for i, text in enumerate(score_texts)]

                if len(score_context)>0:
                    score_context.sort(key=lambda x: x[0], reverse=True) # sort by score, descending
                    max_score = score_context[0][0]
                    if max_score > rerank_min_score: # if rank score too low, discard
                        threshold = rerank_threshold #
                        if max_score > threshold: # use the top score
                            context = score_context[0][1]
                        else: # use the top 3
                            top = 3
                            context = [text[1] for text in score_context[:top]]
                        #source
                        max_score = "{:.2%}".format(max_score)
                        sources = f"Key:\n{element}\nSource:\nScore: {max_score}\n{context}\n\n"
                        # query
                        query = prompt.format(context=context, extract=element, splitter=splitter)
                        # print(query)
                        # json format output
                        stop = ['\n\n']
                        outputs = model.generate(query, splitter=splitter, stop=stop, replace_stop=False, **kwargs)
                        # print(outputs)
                        _json = utilities.extract_json_from_string(outputs)
                        if _json:
                            _element, _value = _json['name'], _json['value']
                            output['detail'] = _value
                        output['sources'] = sources
                else: # did not find any relevant info, most likely an error
                    output['detail'] = "Can not find relevant contexts."
                    output['status'] = 1 # warning
                    output['error'] = "Can not find relevant contexts, possible an error. Check server log for details."
                # yield output
                yield output

    def __extract_summary__(self, model:ILanguageModel, text:str, length:int, stream=False, continue_flag:llm_continue=None):
        """
        read texts and make a summary
        exception: this will raise ContinueExit from llm generate/chats, caller needs to handle ContinueExit
        """    
        splitter = "SUMMARY:"
        prompt = """You are AI, a language expert. Given a block of text content, your task is to generate a summary of that content.

Text Content:
[
{context}
]

Remember: Your summary should be approximately {length} words long.
You must answer in English.

{splitter}
"""
        kwargs = {
            'temperature': 0.5,
            'top_p': 0.90,
            'top_k': 5,
            'do_sample': True,
            'max_new_tokens':length,
        }

        inputs = prompt.format(context=text, length=length, splitter=splitter)
        #print(f"Length: {len(inputs)}; Max: {length}; prompt:\n{inputs}")

        if stream:
            return model.stream_generate(inputs=inputs, splitter=splitter, **kwargs)
        else:
            stop = ['\n\n']
            _summary = model.generate(inputs=inputs, splitter=splitter, stop=stop, replace_stop=False, **kwargs)
            #print(f"extract summary length {len(_summary)}: {_summary}")
            return _summary

    def doc_know(self, query: str, tools, history=None, splitter='', stop=[], replace_stop=False, streaming=True, streaming_delta=True, top=3, faq_conf=0.95, vdb_conf=0.6, rerank_threshold=0.9, rerank_min_score=0.1, bot_name='ubox', continue_flag:llm_continue=None,  **kwargs) -> tuple[bool, str|Iterator]:
        """
        inputs: 
            query: the ask
            tools: the list of tools for LLM to use
            history: chat history if provided
            splitter: split the LLM answer, the last one, -1, will be returned as answer
            stop: stop words
            replace_stop, if True, will replace LLM's own stop words, else, will append to the internal stop words
            streaming: if answer is streaming
            streaming_delta: if true, only delta sent to client
            faq_conf: when match query with FAQ questions, if >= conf, indicating a match
            top: the top number of answers with match conf >= conf, default top 1
            rerank_threshold: if reranker score > this threshold, meaning a top hit
            rerank_min_score: if score below this, meaning the context is irrelevant
        1. check FAQ, if the answer to question (inputs) has a confidence over conf (0.95), use return the answer without using LLM
        2. if LLM, check if streaming is set
        output: a generator of (answers, sources), where both answers and sources are iterable
        exception: this will raise ContinueExit from llm generate/chats, caller needs to handle ContinueExit
        """
        answers = None
        tools = tools if tools is not None else []
        history = history if history is not None else [] # taking care of a list as function param

        # check top, if llm max length 8000, leave about 2000 for new tokens; emb max either 512 or 1024 or 2048
        max_top = math.floor((self.llm.MAX_LENGTH - 2000) / self.emb_model.MAX_LENGTH)
        max_top = max_top if max_top > 1 else 3 # minimum is 3
        top = top if top < max_top else max_top

        #print(f"top is set as: {top}")

        sources = ''
        #
        # query to the VDB to see if the question has a matching FAQ
        #
        contexts = self.__query_faq__(query, conf=faq_conf, top=top)
        #print(f"faq returns: {contexts}")

        if len(contexts)>0: # a match            
            context = contexts[0] #the top 1
            answers = [context['answer']] # make it a list for caller to loop
            sources = ["I found answer from FAQ."]
            return answers, sources # FAQ has not source but itself

        # if not found in faq, continue
        system_prompt_context = """You are AI, name is {name}. It is now {current}. You need to answer user's question based on the provided background information.

Background Information:
[
{context}
]

Remember: It is essential to identify key information in the background information that pertains to user's question to provide more accurate responses.
Remember: Your responses must not contradict the facts presented in the background information.
Answer in English.
"""
        system_prompt_no_context = """You are AI, name is {name}. It is now {current}. Please answer user's question friendly.
Answer in English.
"""
        #
        # check if LLM can self answer without quarying knowledge, e.g, 'what time is it?'
        #
        #result = self.__llm_check_tools__(query=query, external_tools=tools, name=bot_name, continue_flag=continue_flag)
        # current time
        current_time = datetime.datetime.now()
        current_time = current_time.strftime('%Y-%m-%d %H:%M:%S')
        current_day = datetime.datetime.today().strftime('%A')
        current_time = f"{current_time}, {current_day}"

        result = 'tool' # bypass self check for now
        if result == 'self': #LLM can self-answer
            prompt = system_prompt_no_context.format(name=bot_name, current=current_time)

            #print(prompt)
            #print()

            if streaming:
                answers = self.llm.stream_chat(inputs=query,system_prompt=prompt, history=history, splitter=splitter, stop=stop, replace_stop=replace_stop, output_delta=streaming_delta, **kwargs)
            else:
                answers = self.llm.chat(inputs=query,system_prompt=prompt, history=history, splitter=splitter, stop=stop, replace_stop=replace_stop, **kwargs)
                answers = [answers] # make it a list for caller to loop
            sources = ["I can answer this without searching knowledge base."] # make a list
            return answers, sources # self answer, no sources
        # ignore 'none' case, let reranker to filter
        #else: continue to query knowledge base, and consulting with LLM for an answer
        contexts = self.__query_vdb__(query, conf=vdb_conf, top=top)
        # a list of 3 to choose
        score_context = []
        score_texts = []
        for ctx in contexts:
            meta = ctx['meta'] # only meta part
            score_texts.append(meta)

        if len(score_texts) > 0:
            success, index_score = self.reranker.rerank_score(query, score_texts) # rerank element against text indexed at INDEX[0] array
            if success:
                for idx, score in index_score:
                    context = contexts[idx] # 
                    score_context.append([score, context]) # save to list
            else: # reranker failed, possibly cohere no credit or exceed quota
                score = 0.5
                # fake a score, using the score_text descending order
                score_context = [[(score - 0.01*i), context] for i, context in enumerate(contexts)]

        contexts = [] # empty it
        if len(score_context)>0:
            score_context.sort(key=lambda x: x[0], reverse=True) # sort by score, descending
            max_score = score_context[0][0]
            if max_score > rerank_min_score: # if rank score too low, discard
                contexts = [ctx[1] for ctx in score_context[:top] if ctx[0] > rerank_min_score]

        # system prompt
        # construct prompt
        #prefix = '您好，' #prefix to the LLM answer
        if len(contexts)==0:# cannot find an answer with confidence from vdb
            #self.prefix = "我未能在公司知识体系找到相关答案，以下是我的理解："
            sources = ["I can not find relevent contexts from knowledge base. The following is a generic answer."]
            prompt = system_prompt_no_context.format(name=bot_name, current=current_time)
        else: #with context
            # context is a list, [{meta:xx, source_from:yy ,..}, {}...]
            sources = [f"""{ctx['meta']} [Source: {ctx['source_from']}""" for ctx in contexts]
            # context only meta
            contexts = [f"{ctx['meta']}" for ctx in contexts]
            prompt = system_prompt_context.format(name=bot_name, current=current_time, context=contexts)

        #print(prompt)
        #print()

        if streaming:
            answers = self.llm.stream_chat(inputs=query,system_prompt=prompt, history=history, splitter=splitter, stop=stop, replace_stop=replace_stop, output_delta=streaming_delta, **kwargs)
        else:
            answers = self.llm.chat(inputs=query,system_prompt=prompt, history=history, splitter=splitter, stop=stop, replace_stop=replace_stop, **kwargs)
            answers = [answers]

        return answers, sources

    def __query_faq__(self, query:str, level_0:str='', level_1:str='', conf=0.95, top=1)->dict:
        """
        query FAQ in vdb, if the query matches FAQ's questions with confidence >= conf, then return the top answer
        output: a list of dict: [{'question': xxx, 'answer':xxx, 'score': 0.x}]
        """
        answer = self.vdb_mgr.faq_query(query=query, level_0=level_0, level_1=level_1, top=top, threshold=conf)
        return answer

    def __query_vdb__(self, query:str, db_type='', conf=0.95, top=1, only_recent_timestamp=True)->dict:
        """
        query vdb, return the top answer with confidence >= conf
        output: a list of dict, [{meta:'xxx', type:'xxx', source_from:'xxx', score:0.0}...]
        """
        answer = self.vdb_mgr.query_vdb(query=query,type=db_type, top_k=top, threshold=conf, only_recent_timestamp=only_recent_timestamp)
        return answer

    def __llm_check_tools__(self, query:str, external_tools, name, continue_flag:llm_continue=None)->str:
        """
        use LLM to check if the model needs to use tools to answer user's query
        input: query
        external_tools: a list of tools - which are documents in vdb
        name: bot name
        output: str, 'tool name', or 'self', or 'none'
        or
            None if failed to get the answer
        """
        # current time
        current_time = datetime.datetime.now()
        current_time = current_time.strftime('%Y/%m/%d, %H:%M:%S')
        current_day = datetime.datetime.today().strftime('%A')
        current_time = f"{current_time}, {current_day}"
        external_tools = external_tools if external_tools is not None else [] # taking care of list as input param
        # tools, [doc_search: 用于搜索银行理财产品相关信息]
        # tool_names, ['doc_search']
        # tools_self_none, ['doc_search', 'self', 'none']
        tools = ""
        tool_names = "["
        tools_self_none = "["
        is_start = True
        for tool, desc in external_tools.items():
            if not is_start:
                tools += "\n" #add newline
                tool_names += ", "#add comma
                tools_self_none += ", "#add comma
            is_start = False
            tools += f"{tool}: {desc}"
            tool_names += f"'{tool}'"
            tools_self_none += f"'{tool}'"
        tool_names += "]"
        tools_self_none += ", 'self', 'none']"

        prompt = """You are {name}, a helpful AI assistant to answer user's question. Today's date is '{current}'. \
You have access to the follow tools in the format of 'tool: description of the tool'
{tools}

Given the user's input, you need to think what tools to use, and output your decision, which should be one of {tool_names} \
if you believe these tools can help you better answer the question, or \
['self'] if these tools are not relevant but you can answer the question yourself, \
or ['none'] if you do not have sufficient information to answer the question, do NOT make up your answer.

Your output shuld be the following JSON format:
{{
    "tool": "your decision", //must be one of {tools_self_none}
}}

Begin!

{question}
```json
{{
"""
        query = prompt.format(name=name, current=current_time, tools=tools, tool_names=tool_names, tools_self_none=tools_self_none, question=query)

        #print(query)
        #print()

        kwargs = {
            'temperature': 0.3,
            'max_new_tokens': 100,
            'top_k': 3,
            'top_p': 0.95,
            'repetition_penalty': 1.1,
        }   
        result = self.llm.generate(inputs=query, stop=['```', '\n\n'], **kwargs)
        result = result.strip()
        #print(result)
        #print()

        output = None
        try:
            result = '{' + result # add { 
            result_json = utilities.extract_json_from_string(result)
            output = result_json['tool'] if result_json is not None else None
        except:
            #print(f"failed to extract json. raw text: {result}")
            logging.debug(f"failed to extract json. raw text: {result}")
        return output
