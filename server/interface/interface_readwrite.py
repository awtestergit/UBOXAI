# -*- coding: utf-8 -*-

"""
    document read/write interfaces
    Author: awtestergit
"""


import os, io
from typing import Iterator
from interface.interface_model import llm_continue
from anbutils import utilities


"""
IDocReaderWriter
read/write pdf, docx, text files
"""
class IDocReaderWriter():
    TYPE = 'binary' # handle binary input; self.type is str|[list]
    def __init__(self) -> None:
        #document type, such as pdf, docx, txt
        self.type = 'txt' #default output type; self.type is str|[list]
        self.lang = 'zh' # default
        self.min_sentence_length = {
            'zh': 20,# 2/3 of line, in Chinese, about 30
            'en': 50,# about 80 in English
        }

    def __doc_type__(self, doc_path:str | bytes):
        doc_type = self.TYPE
        if type(doc_path) is str and len(doc_path) > 0:
            ext = doc_path.split(".")[-1]
            doc_type = ext.lower()

        return doc_type

    def __validate_doc_type__(self, doc_path:str | bytes) -> bool:
        doc_type = self.TYPE
        is_valid = True
        if type(doc_path) is str and os.path.exists(doc_path):
            doc_type = self.__doc_type__(doc_path=doc_path)
            is_valid = (doc_type == self.type) if type(self.type) is str else (doc_type in self.type if type(self.type) is list else False)
        
        return is_valid
    
    def __remove_newline_from_text__(self, text:str)->str:
        # remove the \n in the text
        texts = text.split('\n')
        text = ''
        for t in texts:
            text += t
        return text

    def construct_paragraph(self, texts:list, lang='en')->list:
        """
        texts: a list of texts
        lang: the text language
        """
        min_length = 20
        if lang in self.min_sentence_length:
            min_length = self.min_sentence_length[lang]

        # every paragraph is assumed to end with '.' or '。' (en or zh)
        result = []
        current = '' # buffer
        
        def is_end_of_paragraph(text):
            end = ['.', '。', ':', '：'] # must be multi-lingual
            return text[-1] in end
        
        for text in texts:
            # remove leading/trailing spaces
            text = text.strip()
            if len(text)>0:
                is_end = is_end_of_paragraph(text[-1])
                if not is_end:
                    current += text
                else:
                    current += text
                    result.append(current)
                    current = ''
                """
                if len(text) < min_length and not is_end: # if shorter than min but not end with '.', treat as a paragraph
                    if len(current) > 0: # who knows if some doc is weird
                        result.append(current)
                        current = ''
                    result.append(text)
                elif is_end:
                    current += text
                    result.append(current)
                    current = '' # reset
                else:
                    current += text
                """

        return result
    
    def read_doc_to_texts(self, doc_path:str|bytes, start_page:int=0, end_page:int=-1, remove_mark=[], reconstruct_paragraph_at_pagebreak=True, strip=True, read_by=0, streaming=False, continue_flag:llm_continue=None, lang='en')->Iterator:
        """
        doc_path: full path of the document to read
        remove_mark: the marks (texts) to be removed, note: the whole line will be removed at mark
        reconstruct_paragraph_at_pagebreak: to construct each paragraph at page break, if True
        strip: strip texts
        read_by: 0: page, 1: document, 2: paragraph
        streaming: if True, yield by paragraph (block), by page, or just yield one big doc
        output: a generator, regardless of streaming
            streaming text from document, by page/paragraph/document as a whole
        """
        if read_by == 0: # by page
            outputs = self.read_doc_to_texts_by_page(doc_path=doc_path, start_page=start_page, end_page=end_page, remove_mark=remove_mark, streaming=streaming, continue_flag=continue_flag)
        else:
            outputs = self.read_doc_to_texts_by_block(doc_path=doc_path, start_page=start_page, end_page=end_page, remove_mark=remove_mark, reconstruct_paragraph_at_pagebreak=reconstruct_paragraph_at_pagebreak, strip=strip, read_by=read_by, streaming=streaming, continue_flag=continue_flag)

        # outputs is a generator, regardless of 'streaming'
        def output_stream(outputs, streaming):
            # reconstruct paragraph
            if not streaming: #outputs: [['xxxx', 'page_'], ['yyyy', 'page_']...]
                outputs = [output[0] for output in outputs] # get rid of 'page_'
                if read_by==2: # if not streaming and read by paragraph
                    outputs = self.construct_paragraph(outputs, lang)
                    yield from outputs # yield the list
                elif read_by == 1: # read by document
                    all_outputs = ''.join(output for output in outputs)
                    yield from [all_outputs]
                else: # read by page
                    yield from outputs # yield the list
            else: # streaming
                if read_by == 1: # by document, the output is a list of list, [['text', 'page_']...]
                    all_outputs = ''.join(output[0] for output in outputs)
                    yield all_outputs
                else:
                    for output in outputs:
                        #       streaming by page or by paragraph, where output is ['text', 'page_']
                        yield output[0] # only the text, not the page number

        return output_stream(outputs, streaming=streaming)

    def read_doc_to_texts_with_source(self, doc_path:str|bytes, start_page:int=0, end_page:int=-1, remove_mark=[], reconstruct_paragraph_at_pagebreak=True, strip=True, read_by=0, continue_flag:llm_continue=None, lang='en')-> list[str, str]:
        """
        doc_path: full path of the document to read
        remove_mark: the marks (texts) to be removed, note: the whole line will be removed at mark
        reconstruct_paragraph_at_pagebreak: to construct each paragraph at page break, if True
        strip: strip texts
        read_by: 0: page, 1: document, 2: paragraph
        output: [(text, page_xx), ()...]
        """
        if read_by == 0: # by page
            outputs = self.read_doc_to_texts_by_page(doc_path=doc_path, start_page=start_page, end_page=end_page, remove_mark=remove_mark, streaming=False, continue_flag=continue_flag)
        else:
            outputs = self.read_doc_to_texts_by_block(doc_path=doc_path, start_page=start_page, end_page=end_page, remove_mark=remove_mark, reconstruct_paragraph_at_pagebreak=reconstruct_paragraph_at_pagebreak, strip=strip, read_by=read_by, streaming=False, continue_flag=continue_flag)

        # outputs is a generator, regardless of 'streaming'
        # reconstruct paragraph
        #outputs: [['xxxx', 'page_'], ['yyyy', 'page_']...]
        outputs = [output for output in outputs] # read from the generator
        if read_by==2: # if read by paragraph
            outputs = self.construct_paragraph(outputs, lang)

        return outputs
        
    def read_doc_to_texts_by_page(self, doc_path:str|bytes, start_page:int=0, end_page:int=-1, remove_mark=[], streaming=False, continue_flag:llm_continue=None):
        """
        read texts page by page
        doc_path: full path of the document to read
        remove_mark: the marks (texts) to be removed, note: the whole line will be removed at mark
        output: a generator regardless of streaming
            if streaming, yield to page by page
                if not streaming, yield to list of texts from the document, each entry is texts in a page
        """
        raise NotImplementedError("IDocReaderWriter base class: read_doc_to_texts_by_page")

    def read_doc_to_texts_by_block(self, doc_path:str|bytes, start_page:int=0, end_page:int=-1, remove_mark=[], reconstruct_paragraph_at_pagebreak=True, read_by=2, streaming=False, continue_flag:llm_continue=None):
        """
        'block' means paragraph - in word, it will be a paragraph, or a paragraph splitted by a soft pagebreak
                - in pdf, if a paragraph is splitted by a page, there is no way to recover it so far
        doc_path: full path of the document to read
        remove_mark: the marks (texts) to be removed, note: the whole line will be removed at mark
        reconstruct_paragraph: if True, will construct paragraph splitted by soft pagebreak in word, if False, the sub-paragraph splitted 
            by soft pagebreak will be treaded as a paragraph
            for pdf, it does nothing
        read_by: 0: page, 1: document, 2: paragraph
        output: a generator, regardless of streaming
            if streaming, yield to paragraph by paragraph
                if not streaming, yield to list of texts from the document, each entry is texts in a paragraph
        """
        raise NotImplementedError("IDocReaderWriter base class: read_doc_to_texts_by_block")

    def write_text_to_doc(self, texts: str|list[str]|list[list[str]], output_path:str, template_path:str=None, **kwargs) -> bool:
        """
        text: the text to write
        doc_path: the full path of output file
        template_path: if use a template, such as pptx, the full path to the template
        """
        raise NotImplementedError("IDocReaderWriter base class: write to doc")

    def __break_long_texts_into_chunks__(self, texts:str, chuck_size:int, overlap:int) -> list[str]:
        return utilities.break_long_texts_into_chunks(texts=texts, chuck_size=chuck_size, overlap=overlap)

class TextReaderWriter(IDocReaderWriter):
    def __init__(self) -> None:
        super().__init__()

    def read_doc_to_texts(self, doc_path: str|bytes, start_page:int=0, end_page:int=-1, remove_mark=[]) -> list[str]:
        """
        read full texts from document
        ignoring start and end page as there are no pages per se
        """
        output = []

        valid = self.__validate_doc_type__(doc_path=doc_path)
        if not valid:
            raise ValueError(f"DocReaderWriter read document failed. It does not exist! File: {doc_path}")
        else:
            # read file. if bytes, use stringIO with decode
            with io.StringIO(doc_path.decode()) if type(doc_path) is bytes else open(doc_path, 'r') as file:
                for line in file:
                    line = line.strip()
                    if len(line) > 0:
                        output.append(line)

        return output

    def read_doc_to_texts_with_source(self, doc_path: str | bytes, start_page: int = 0, end_page: int = -1, remove_mark=[]) -> list[str]:
        """
        read full texts from document
        ignoring start and end page as there are no pages per se
        """
        output = []

        valid = self.__validate_doc_type__(doc_path=doc_path)
        if not valid:
            raise ValueError(f"TextReaderWriter read document failed. It does not exist! File: {doc_path}")
        else:
            # read file. if bytes, use stringIO with decode
            with io.StringIO(doc_path.decode()) if type(doc_path) is bytes else open(doc_path, 'r') as file:
                for idx, line in enumerate(file):
                    line = line.strip()
                    if len(line) > 0:
                        output.append([line, f"line_{idx+1}"])

        return output

    def write_text_to_doc(self, texts: str|list[str], output_path: str, template_path: str = None, **kwargs) -> bool:
        with open(output_path, 'w') as file:
            if type(texts) is list:
                for text in texts:
                    file.write(f"{text}\n")
            else:
                file.write(texts)
        return True
