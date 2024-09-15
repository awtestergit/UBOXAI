# -*- coding: utf-8 -*-

"""
    PDF read / write
    Author: awtestergit
"""


import io
### pdf
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer
#import pdfplumber

from interface.interface_readwrite import IDocReaderWriter
from interface.interface_model import llm_continue, ContinueExit

class PDFReaderWriter(IDocReaderWriter):
    TYPE = "pdf"
    def __init__(self) -> None:
        super().__init__()
        self.type = self.TYPE

    def read_doc_to_texts_by_page(self, doc_path:str|bytes, start_page:int=0, end_page:int=-1, remove_mark=[], streaming=True, continue_flag:llm_continue=None):
        """
        read texts page by page
        doc_path: full path of the document to read
        remove_mark: the marks (texts) to be removed, note: the whole line will be removed at mark
        streaming: if to stream by yield a generator
        output: a generator regardless of streaming
            if streaming, yield to page by page
                if not streaming, yield to list of texts from the document, each entry is texts in a page
        """
        result = []
        valid = self.__validate_doc_type__(doc_path=doc_path)
        # if not valid
        if not valid: # either file does not exist, or file extension is not 'pdf'
            raise ValueError(f"PdfReaderWriter read document by block failed. either file is not {self.type}, or it does not exist! File: {doc_path}")
        else:
            #else, read pdf. if bytes, use bytesIO
            with io.BytesIO(doc_path) if type(doc_path) is bytes else open(doc_path, 'rb') as file:
                pages = extract_pages(file)
                page_list = list(pages)
                num_pages = len(page_list)
                # convert page number to index
                start_page = start_page - 1 if (start_page > 0 and start_page <= num_pages) else 0 # if start_page is too large
                end_page = num_pages if (end_page >= num_pages or end_page < 0) else end_page
                assert start_page <= end_page
                for idx in range(start_page, end_page):
                    # check continue
                    if continue_flag:
                        cf = continue_flag.check_continue_flag()
                        if not cf:
                            raise ContinueExit()

                    page = page_list[idx]
                    output = []
                    for element in page:
                        if isinstance(element, LTTextContainer):
                            #
                            # this get_text is a paragraph
                            #
                            text = element.get_text() # this gets a paragraph
                            text = text.strip(' ')
                            mark_removed = False
                            if len(remove_mark)>0:
                                for mark in remove_mark:
                                    if text.find(mark)>-1:
                                        mark_removed = True
                                        break
                            if mark_removed: # do not include mark string line
                                continue

                            # remove the \n in the text, effectively this reconstruct a paragraph
                            text = self.__remove_newline_from_text__(text)
                            text = text.strip()
                            output.append(text)
                    text = '\n'.join(t for t in output) # join every paragraph in the page, seperate by '\n'
                    result_item = [text, f"page_{idx}"]
                    result.append(result_item) # save page
                    if streaming:
                        yield result_item # if streaming, yield this page
        if not streaming:
            yield from result # if not streaming, yield from all pages instead
    
    def read_doc_to_texts_by_block(self, doc_path:str|bytes, start_page:int=0, end_page:int=-1, remove_mark=[], reconstruct_paragraph_at_pagebreak=True, strip=True, streaming=False, read_by=2, continue_flag:llm_continue=None):
        """
        'block' means paragraph - in word, it will be a paragraph, or a paragraph splitted by a soft pagebreak
                - in pdf, if a paragraph is splitted by a page, there is no way to recover it so far
        doc_path: full path of the document to read
        remove_mark: the marks (texts) to be removed, note: the whole line will be removed at mark
        reconstruct_paragraph_at_pagebreak: if True, will construct paragraph splitted by soft pagebreak in word, if False, the sub-paragraph splitted 
            by soft pagebreak will be treaded as a paragraph
            for pdf, it does nothing
        read_by: 0: page, 1: document, 2: paragraph, at this call, only 1 or 2
        output: a generator regardless of streaming
            if streaming, yield to paragraph by paragraph
                if not streaming, yield to list of texts from the document, each entry is texts in a paragraph
        """
        result = []
        valid = self.__validate_doc_type__(doc_path=doc_path)
        # if not valid
        if not valid: # either file does not exist, or file extension is not 'pdf'
            raise ValueError(f"PdfReaderWriter read document by block failed. either file is not {self.type}, or it does not exist! File: {doc_path}")
        else:
            #else, read pdf. if bytes, use bytesIO
            with io.BytesIO(doc_path) if type(doc_path) is bytes else open(doc_path, 'rb') as file:
                pages = extract_pages(file)
                page_list = list(pages)
                num_pages = len(page_list)
                # convert page number to index
                start_page = start_page - 1 if (start_page > 0 and start_page <= num_pages) else 0 # if start_page is too large
                end_page = num_pages if (end_page >= num_pages or end_page < 0) else end_page
                assert start_page <= end_page
                for idx in range(start_page, end_page):
                    # check continue
                    if continue_flag:
                        cf = continue_flag.check_continue_flag()
                        if not cf:
                            raise ContinueExit('pdf read exit.')

                    page = page_list[idx]
                    output = []
                    for element in page:
                        if isinstance(element, LTTextContainer):
                            #
                            # this get_text is a paragraph
                            #
                            text = element.get_text()
                            text = text.strip(' ') if strip else text
                            mark_removed = False
                            if len(remove_mark)>0:
                                for mark in remove_mark:
                                    if text.find(mark)>-1:
                                        mark_removed = True
                                        break
                            if mark_removed: # do not include mark string line
                                continue

                            # remove the \n in the text
                            text = self.__remove_newline_from_text__(text)
                            text = text.strip() if strip else text
                            output.append(text)

                            # if streaming and read by 'paragraph'
                            if streaming and read_by==2:
                                yield [text, f"page_{idx}"]
                    for text in output:
                        result.append([text, f"page_{idx}"])
        if not streaming or read_by==1:
            yield from result # if not streaming, or read by 'document'

    def write_text_to_doc(self, texts: str | list[str] | list[list[str]], output_path: str, template_path: str = None, **kwargs) -> bool:
        return super().write_text_to_doc(texts, output_path, template_path, **kwargs)