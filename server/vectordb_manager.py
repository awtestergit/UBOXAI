# -*- coding: utf-8 -*-
"""
    Qdrantclient vector db manager, for users to manage collections (create/update/delete etc)
    Author: awtestergit
"""

# Warning control
import warnings
warnings.filterwarnings('ignore')

from argparse import ArgumentParser
import logging
import uvicorn
from fastapi import FastAPI
import pandas as pd
import gradio as gr
import json
import sys
import traceback
from datetime import datetime
from qdrant_client import QdrantClient
from models.embed import OllamaNomicEmbeddingModel
from qdrantclient_vdb.qdrant_webui_manager import VectorDBManager
from qdrantclient_vdb.qdrant_manager import qcVdbManager
from qdrantclient_vdb.qdrant_base import doctype_schema, file_schema, chunk_schema
from interface.interface_readwrite import *
from readwrite.pdf_readwrite import PDFReaderWriter
from readwrite.word_readwrite import WordReaderWriter

def main(
        collection_name = 'vdb_ubox',
        encoder_path = 'http://127.0.0.1:11434',
        logging_file = "./vectordb_manager.log",
        vdb_ip = "localhost",
        vdb_port = 6333,
):
    #logger
    logging.basicConfig(filename=logging_file,filemode='a', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
    logging.info("Starting...")
    config = {}
    try:
        with open('config.json', 'rb') as f:
            _config = json.load(f)
            config['VDBNAME'] = _config['VDBNAME']
            config['OCR_DET'] = _config['OCR_DET']
            config['OCR_CLS'] = _config['OCR_CLS']
            config['OCR_REC'] = _config['OCR_REC']
    except:
        e = traceback.format_exc()
        logging.error(f"loading config.json failed. {e}")
        sys.exit(-1)

    client = QdrantClient(vdb_ip, port=vdb_port)
    print(encoder_path)
    model = OllamaNomicEmbeddingModel(host=encoder_path)
    vdbmanager = qcVdbManager(model=model,collection_name=collection_name,client=client)
    webui_manager = VectorDBManager(manager=vdbmanager)
    ocr = None

    def __get_reader_by_filename__(filename:str, is_ocr=False)->IDocReaderWriter:
        if len(filename) == 0:
            return None
        
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

    df_fileinfo, df_faq = None, None
    def load_df_faq():
        global df_faq
        df_faq = webui_manager.faq_get_all()
        return df_faq
    def load_df_fileinfo():
        global df_fileinfo
        df = webui_manager.read_fileinfo()
        #df_fileinfo = df[['doctype_id','file_id', 'group_id', 'type', 'source_from', 'time_file_creation', 'time_add_to_vdb']]
        #df_fileinfo = df_fileinfo.copy().rename(columns={'doctype_id':'TypeID', 'file_id':'DocID', 'group_id':'GroupID', 'type':'Knowledge Type', 'source_from':'Source', 'time_file_creation':'Document Version (Time)', 'time_add_to_vdb':'Date Added'})#, inplace=True)
        if len(df) > 0:
            df_fileinfo = df[['file_id', 'file_desc', 'source_from', 'time_file_creation', 'time_add_to_vdb']]
            df_fileinfo = df_fileinfo.copy().rename(columns={ 'file_id':'DocID', 'file_desc':'Description', 'source_from':'Source', 'time_file_creation':'Document Version (Time)', 'time_add_to_vdb':'Date Added'})#, inplace=True)
        else:
            df_fileinfo = pd.DataFrame(columns=['DocID', 'Description','Source', 'Document Version (Time)', 'Date Added'])
        return df_fileinfo
    
    df_fileinfo = load_df_fileinfo()
    df_faq = load_df_faq()

    def load_config():
        global json_config
        with open('config.json', 'rb') as f:
            json_config = json.load(f)
        return json_config
    def save_config(config_dict:dict):
        with open('config.json', 'w') as f:
            json.dump(config_dict, f, indent=4)

    app = FastAPI()

    # start webui
    with gr.Blocks(title='UBOX-AI Services Manager') as sa:
        #####UI#####
        gr.Markdown("""<h1><center> UBOX-AI Services Manager </center></h1>""")
        with gr.Tab("FAQ", id='faq_id'):
            with gr.Row():
                with gr.Column(scale=2):
                    gr.Markdown("""<h3>Add FAQ</h3>""")
                    with gr.Group():
                        with gr.Row():
                            gr.Markdown("""<center><h4>Add by one</h4></center>""")
                        with gr.Row():
                            _faq_add_question = gr.Textbox(placeholder="Question", label='')
                            _faq_add_answer = gr.Textbox(placeholder="Answer", label='')
                        with gr.Row():
                            _faq_add_org = gr.Textbox(placeholder="Department (optional)", label='')
                            _faq_add_dept = gr.Textbox(placeholder="Team (optional)", label='')
                        _faq_add_submit = gr.Button(value="Submit")
                    with gr.Group():
                        gr.Markdown("""<center><h4>Add by bulk</h4></center>""")
                        _faq_template_file = gr.File(visible=False)
                        with gr.Row():
                            _faq_download_template = gr.Button(value="Download FAQ template.")
                            _faq_bulk_load = gr.UploadButton(interactive=True, label="Upload FAQs (.csv)", type='filepath', file_types=['.csv'],file_count='single')
                with gr.Column(scale=4):
                    gr.Markdown("""<h3>Existing FAQs</h3>""")
                    with gr.Group():
                        with gr.Row():
                            gr.Markdown("""<center>Delete FAQ @ ID</center>""")
                            _faq_id_text = gr.Text(placeholder="Click FAQ list to get ID", label='', container=False)
                            _faq_id_delete = gr.Button("Delete", interactive=False)
                    _df_faq = gr.DataFrame(value=df_faq[['Question','Answer', 'Department', 'Team']], interactive=False)
        with gr.Tab("Knowledge Warehouse"):
            # add files
            with gr.Group(visible=True) as _add_files_group:
                with gr.Accordion(label='Add Knowledge To Warehouse', open=False):
                    gr.Textbox(value="Add files to knowledge warehouse", label='', container=None, interactive=False)
                    _add_files_button = gr.UploadButton(label="Upload Files (PDF/DOCX)", file_types=['.pdf','.txt','.docx'],file_count='multiple')
            # add files popup
            with gr.Group(visible=False) as _add_files_popup:
                _add_files_status = gr.Textbox(value='', label='Execution Status', interactive=False)
                _add_files_check_duplicate = gr.Checkbox(value=True, label="Check similarity. If there are highly similar files in knowledge warehouse, newly uploaded files will not be added. Use 'Add Similar Files' for this scenario.")
                _add_files_remove_marks = gr.Textbox(interactive=True, label="Remove watermark (best effort only). Use comma ',' or space to seperate multiple watermark words.")
                _df_add_files = gr.DataFrame(interactive=True, type='pandas', label="Source: editable, you can change it to more readable; Version (Time): editable, format:'YYYY-MM-DD'; Description: editable, description of this file")
                with gr.Row():
                    with gr.Column():
                        _add_files_confirm = gr.Button(value="Confirm")
                    with gr.Column():
                        _add_files_cancel = gr.Button(value="Cancel")
                _add_slider_dup = gr.Slider(minimum=0.8, maximum=1, label="Similarity", value=0.95)
            # duplicated files
            with gr.Group(visible=True) as _duplicate_group:
                with gr.Accordion("Add Similar Files by Document Version (Time)", open=False):
                    _add_duplicate_button = gr.UploadButton(label="Upload Files (PDF/DOCX)", file_types=['.pdf','.docx'],file_count='multiple')                
            # fileinfo
            with gr.Group() as _fileinfo_group:
                with gr.Group() as _fileinfo_group_body:
                    with gr.Row():
                        _df_fileinfo = gr.Dataframe(value=df_fileinfo, interactive=False)
                    with gr.Row() as _body_row:
                        with gr.Column(scale=4, min_width=1):
                            with gr.Row():
                                with gr.Column(scale=1, min_width=1):
                                    gr.Textbox(value="Click the row:", label='', interactive=False, container=None)
                                with gr.Column(scale=1,min_width=1):
                                    _fileinfo_index = gr.Textbox(value='', label='', interactive=False, container=None)
                                with gr.Column(scale=4,min_width=1):
                                    gr.Textbox(value="to delete this record or update knowledge document.", interactive=False, label='', container=None)
                        with gr.Group(visible=True) as _fileinfo_group_button:
                            with gr.Column(scale=1, min_width=1):
                                _fileinfo_delete_button = gr.Button(value="Delete", interactive=False)
                            with gr.Column(scale=1, min_width=1):
                                _fileinfo_update_button = gr.Button(value="Update", interactive=False)
                with gr.Group(visible=False) as _fileinfo_group_confirm:
                    _fileinfo_delete_status = gr.Textbox(value="The document will be permanently deleted!", label="!!!Caution!!!", visible=True)
                    _fileinfo_delete_real = gr.Button(value="Confirm", interactive=True)
                    _fileinfo_delete_cancel = gr.Button(value="Cancel")
            # fileinfo popup
            with gr.Group(visible=False) as _fileinfo_popup:
                with gr.Row():
                    _fileinfo_popup_status = gr.Textbox(value='', label='Execution Status', interactive=False)
                with gr.Row():
                    with gr.Column(scale=1):
                        _fileinfo_popup_id = gr.Textbox(interactive=False,label="Document ID, readonly")
                    with gr.Column(scale=2):
                        _fileinfo_popup_desc = gr.Textbox(interactive=True, label="Document Description, editable")
                with gr.Row():
                    _fileinfo_popup_add_time = gr.Textbox(interactive=False,label="Date Added")
                    _fileinfo_popup_time = gr.Textbox(interactive=True, label="Document Version (Time). Can be updated using 'YYYY-MM-DD' format")
                with gr.Row(variant='panel', equal_height=True):
                        with gr.Column(scale=4):
                            gr.Text(value="Document source. Can be changed by click on 'Update File':", label='', container=False, interactive=False)
                        with gr.Column(scale=5):
                            _fileinfo_popup_source = gr.Textbox(interactive=False,label="", container=False)
                        with gr.Column(scale=1):
                            _fileinfo_popup_update_button = gr.UploadButton(interactive=True, label="Update File", type='filepath', file_types=['.pdf','.txt','.docx'],file_count='single')                
                with gr.Row():
                    with gr.Column():
                        _fileinfo_popup_confirm = gr.Button(value="Confirm")
                    with gr.Column():
                        _fileinfo_popup_cancel = gr.Button(value="Cancel")

        #####event handlers#####

        # faq
        def faq_tab_selected():
            return gr.File("faq_template.csv", visible=True)
        _faq_download_template.click(fn=faq_tab_selected, outputs=[_faq_template_file])

        def faq_add(level_0:str, level_1:str, question:str, answer:str):
            # department / team
            if len(level_0) == 0:
                level_0 = 'Default'
            if len(level_1) == 0:
                level_1 = 'Default'            
            webui_manager.faq_add_qa(level_0=level_0, level_1=level_1, question=question, answer=answer)
        def faq_add_bulk(file):
            df = pd.read_csv(file)
            default_fill = {'Department': 'Default', 'Team': 'Default'}
            df.fillna(default_fill, inplace=True)
            print(df)
            webui_manager.faq_add_qa_batch(df)
        def faq_delete_by_id(index):
            global df_faq
            index = int(index)
            _id = df_faq.at[index, 'ID']
            print(f"selected ID: {_id}....df:")
            print(df_faq)
            webui_manager.faq_delete_by_id(_id)
        #faq select
        def faq_select_id(evt: gr.SelectData):
            index = evt.index[0]
            return index, gr.Button(interactive=True)
        _faq_add_submit.click(fn=faq_add, inputs=[_faq_add_org, _faq_add_dept, _faq_add_question, _faq_add_answer]).then(None, js="location.reload(true)")
        _faq_bulk_load.upload(fn=faq_add_bulk, inputs=[_faq_bulk_load]).then(None, js='location.reload(true)')
        _df_faq.select(fn=faq_select_id, outputs=[_faq_id_text, _faq_id_delete])
        _faq_id_delete.click(fn=faq_delete_by_id, inputs=[_faq_id_text]).then(None, js='location.reload(true)')

        # dataframe select
        def group_enable_button(evt: gr.SelectData):
            index = evt.index[0]
            return index, gr.Button(interactive=True), gr.Button(interactive=True)
        def popup_disable_button():
            return gr.Button(interactive=False), gr.Button(value="Back")
        def show_popup():
            return gr.Group(visible=False), gr.Group(visible=True)
        def hide_group():
            return gr.Group(visible=False)

        # file select
        def fileinfo_delete(row_index):
            global df_fileinfo
            status = "Deleted."
            try:
                row = int(row_index)
                file_id = df_fileinfo['DocID'][row].item() # df.item()
                webui_manager.delete_fileinfo_by_id(file_id=file_id)
                status = f"DocID:{file_id} {status}"
            except Exception as e:
                status = f"Deletion failed! Error: {e}"
            return status

        def fileinfo_fill_popup(row_index):
            global df_fileinfo
            row = int(row_index)
            file_id = df_fileinfo['DocID'][row].item() # df.item()
            fileinfo:file_schema = webui_manager.get_fileinfo_by_id(file_id=file_id)
            doctype_id = fileinfo.doctype_id
            doctype:doctype_schema = webui_manager.get_doctype_by_id(doctype_id=doctype_id)
            return fileinfo.file_id, fileinfo.file_desc, fileinfo.time_add_to_vdb, fileinfo.time_file_creation, fileinfo.source_from
        
        def fileinfo_update_file(new_file):
            return gr.Textbox(value=new_file, interactive=True, label="Document source. If a temporary file path is shown, you can change it to be more readable, easier to track the source.")
        
        def fileinfo_popup_confirm(file_id, file_desc, file_creation_time, source_from, file_obj):
            status = "Execution Success."
            try:
                file_id = int(file_id)
                creation_time = None if (file_creation_time is None or len(file_creation_time) ==0) else datetime.strptime(file_creation_time, webui_manager.time_format)
                text_source = []
                if file_obj is not None:# new file uploaded
                    reader:IDocReaderWriter = __get_reader_by_filename__(filename=file_obj)
                    text_source = reader.read_doc_to_texts_with_source(file_obj)
                    max_length = webui_manager.manager.model.MAX_LENGTH
                    overlap = int(max_length/20)
                    overlap = overlap if overlap <= 50 else 50
                    text_source = utilities.convert_text_with_source_list_to_chunks(text_source=text_source, doc_path=source_from, chunk_size=max_length, overlap=overlap, merge=True)
                webui_manager.update_fileinfo(file_id=file_id, file_desc=file_desc, file_full_path=source_from, file_creation_time=creation_time, chunks=text_source)
                status = f"DocID:{file_id} {status}"
            except Exception as e:
                status = f"DocID:{file_id} file update failed! Error: {e}"
            return status

        _df_fileinfo.select(fn=group_enable_button, outputs=[_fileinfo_index, _fileinfo_delete_button, _fileinfo_update_button])
        _fileinfo_delete_button.click(fn=show_popup, outputs=[_fileinfo_group_button, _fileinfo_group_confirm]).then(\
            fn=hide_group, outputs=[_add_files_group]).then(fn=hide_group, outputs=[_duplicate_group])
        _fileinfo_delete_cancel.click(None, js="location.reload(true)")
        _fileinfo_delete_real.click(fn=fileinfo_delete, inputs=[_fileinfo_index], outputs=[_fileinfo_delete_status]).then(\
                    fn=popup_disable_button, outputs=[_fileinfo_delete_real, _fileinfo_delete_cancel]).then(\
                        fn=hide_group, outputs=[_fileinfo_group_body]).then(fn=hide_group, outputs=[_duplicate_group])
        _fileinfo_update_button.click(fn=fileinfo_fill_popup, inputs=[_fileinfo_index], outputs=[_fileinfo_popup_id, _fileinfo_popup_desc, _fileinfo_popup_add_time, _fileinfo_popup_time, _fileinfo_popup_source]).then(\
            fn=show_popup, outputs=[_fileinfo_group, _fileinfo_popup]).then(\
            fn=hide_group, outputs=[_add_files_group]).then(fn=hide_group, outputs=[_duplicate_group])
        _fileinfo_popup_update_button.upload(fn=fileinfo_update_file, inputs=[_fileinfo_popup_update_button], outputs=[_fileinfo_popup_source])
        _fileinfo_popup_cancel.click(None, js="location.reload(true)")
        _fileinfo_popup_confirm.click(fn=fileinfo_popup_confirm, inputs=[_fileinfo_popup_id, _fileinfo_popup_desc, _fileinfo_popup_time, _fileinfo_popup_source, _fileinfo_popup_update_button],outputs=[_fileinfo_popup_status]).then(\
            fn=popup_disable_button, outputs=[_fileinfo_popup_confirm, _fileinfo_popup_cancel])

        # add files select
        def add_files_fill_popup(file_objs):
            df = pd.DataFrame()
            df['DocSource'] = [file for file in file_objs]
            value = ['' for f in file_objs]
            df["DocVersion"] = value
            df['DocDescription'] = value
            return df

        def add_files_confirm(check_duplicate, dup_threshold, df, file_objs, file_dup_objs, marks=''):
            remove_mark = marks.split(', ') if len(marks) > 0 else []
            if file_dup_objs is not None and len(file_dup_objs) > 0:
                return __add_duplicate_files__(df, file_dup_objs, remove_mark=remove_mark)
            else:
                return __add_files__(check_duplicate, dup_threshold, df, file_objs, remove_mark=remove_mark)
        
        def __add_duplicate_files__(df, file_dup_objs, remove_mark=[]):
            _type = "Default" # default for now
            status = ''
            added = []
            source_from = ''
            try:
                time_empty = []
                failed = []
                for idx, file_obj in enumerate(file_dup_objs):
                    file_time_creation = df['DocVersion'][idx]
                    source_from = df['DocSource'][idx]
                    file_desc = df['DocDescription'][idx]
                    if (file_time_creation is None or len(file_time_creation)==0): #make sure this is not empty anymore
                        time_empty.append(source_from)
                        continue # pass this
                    file_time_creation = datetime.strptime(file_time_creation, webui_manager.time_format)
                    reader:IDocReaderWriter = __get_reader_by_filename__(filename=file_obj)
                    texts = reader.read_doc_to_texts_with_source(file_obj, remove_mark=remove_mark)
                    max_length = webui_manager.manager.model.MAX_LENGTH
                    overlap = int(max_length/20)
                    overlap = overlap if overlap <= 50 else 50
                    texts = utilities.convert_text_with_source_list_to_chunks(text_source=texts, doc_path=source_from, chunk_size=max_length, overlap=overlap, merge=True)
                    doctype:doctype_schema = webui_manager.get_doctype_by_type(_type)
                    orig_file_id = doctype.file_ids[-1] # use the last id
                    result = webui_manager.insert_duplicate(orig_file_id=orig_file_id, file_full_path=source_from, file_creation_time=file_time_creation, file_desc=file_desc, chunks=texts)
                    if result: #success
                        added.append(source_from) #only source part
                    else:
                        failed.append(source_from)
                # status
                if len(added) > 0:
                    status = "The following files have been added:\n"
                    for text in added:
                        status += text + "\n"
                if len(time_empty)>0:
                    status += "\n\n!!!The document version time of highly similar files can not be empty!!! The following files need document version time:\n"
                    for text in time_empty:
                        status += text + "\n"
                if len(failed)>0:
                    status += "\n\n!!!Adding of the following files failed!!!:\n"
                    for text in failed:
                        status += text + "\n"
            except Exception as e:
                status = f"Adding file failed!!! File name: {source_from}, Error: {e}"
                if len(added) > 0: # some succedded
                    status += "\n\nThe following files have been added:\n"
                    for text in added:
                        status += text + "\n"
            return status

        def __add_files__(check_duplicate, dup_threshold, df, file_objs, remove_mark=[]):
            _type, _desc = "Default", "Default" # default for now
            status = ''
            added, dups, failed = [],[],[]
            source_from = ''
            try:
                threshold = float(dup_threshold)
                for idx, file_obj in enumerate(file_objs):
                    reader:IDocReaderWriter = __get_reader_by_filename__(filename=file_obj)
                    texts = reader.read_doc_to_texts_with_source(file_obj, remove_mark=remove_mark)
                    source_from = df['DocSource'][idx]
                    file_time_creation = df['DocVersion'][idx]
                    file_time_creation = None if (file_time_creation is None or len(file_time_creation)==0) else datetime.strptime(file_time_creation, webui_manager.time_format)
                    file_desc = df['DocDescription'][idx]
                    max_length = webui_manager.manager.model.MAX_LENGTH
                    overlap = int(max_length/20)
                    overlap = overlap if overlap <= 50 else 50
                    texts = utilities.convert_text_with_source_list_to_chunks(text_source=texts, doc_path=source_from, chunk_size=max_length, overlap=overlap, merge=True)
                    result, dup_chunks = webui_manager.insert(type=_type, type_desc=_desc, file_full_path=source_from, file_creation_time=file_time_creation, file_desc=file_desc, chunks=texts, check_duplicate=check_duplicate, threshold=threshold)
                    if len(dup_chunks)>0: # duplicated
                        dups.append(dup_chunks[0][1]) #only source part. dup_chunks: [chunk, source, duplicate_file_id]
                    elif result:#success
                        added.append(source_from)
                    else: #failed
                        failed.append(source_from)
                # status
                if len(added)>0:
                    status = "The following files have been added:\n"
                    for text in added:
                        status += text + "\n"
                if len(dups)>0:
                    status += "\n\nThe following files are similar to some files added to knowledge warehouse before, and are not added yet:\n"
                    for text in dups:
                        status += text + "\n"
                if len(failed)>0:
                    status += "\n\n!!!Adding of the following files failed!!!\n"
                    for text in failed:
                        status += text + "\n"
            except Exception as e:
                status = f"!!!Adding of the file failed!!! File name: {source_from}, Error: {e}"
                if len(added) > 0: # some succedded
                    status += "\n\nThe following files are added:\n"
                    for text in added:
                        status += text + "\n"
            return status

        def duplicate_upload(file_objs):
            df = add_files_fill_popup(file_objs=file_objs)
            return df, gr.Checkbox(visible=False), gr.Slider(visible=False)

        _add_files_button.upload(fn=add_files_fill_popup, inputs=[_add_files_button], outputs=[_df_add_files]).then(fn=show_popup, outputs=[_add_files_group, _add_files_popup]).then(\
            fn=hide_group, outputs=[_fileinfo_group]).then(fn=hide_group, outputs=[_duplicate_group])
        _add_files_cancel.click(None, js="location.reload(true)")
        _add_files_confirm.click(fn=add_files_confirm, inputs=[_add_files_check_duplicate, _add_slider_dup, _df_add_files, _add_files_button, _add_duplicate_button, _add_files_remove_marks],outputs=[_add_files_status]).then(\
            fn=popup_disable_button, outputs=[_add_files_confirm, _add_files_cancel])
        _add_duplicate_button.upload(fn=duplicate_upload, inputs=[_add_duplicate_button], outputs=[_df_add_files, _add_files_check_duplicate, _add_slider_dup]).then(fn=show_popup, outputs=[_add_files_group, _add_files_popup]).then(\
            fn=hide_group, outputs=[_fileinfo_group]).then(fn=hide_group, outputs=[_duplicate_group])

        def load_faq_df_to_display():
            global df_faq, df_fileinfo
            df_fileinfo = load_df_fileinfo()
            df_faq = load_df_faq()
            return df_fileinfo, df_faq[['Question', 'Answer', 'Department', 'Team']]
        
        sa.load(fn=load_faq_df_to_display, outputs=[_df_fileinfo, _df_faq]) # load df_doctype, df_fileinfo, types, faq

    sa.queue()
    #sa.launch(debug=True)
    webui_path = "/webui"
    app = gr.mount_gradio_app(app=app, blocks=sa, path=webui_path) # http://127.0.0.1:8880/webui
    return app

#app = main()

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("-p", "--port", dest="port", type=int, default=5010, help="VDB Manager server port.")
    parser.add_argument("-ip", "--host", dest="ip", type=str, default="0.0.0.0", help="VDB Manager server host IP.")
    parser.add_argument("-vp", "--vdb-port", dest="vp", type=int, default=6333, help="Vector DB host port.")
    parser.add_argument("-vip", "--vdb-host", dest="vip", type=str, default="host.docker.internal", help="Vector DB host IP.")
    parser.add_argument("-coll", "--coll-name", dest="coll", type=str, default="vdb_ubox", help="VDB collection name.")
    parser.add_argument("-encoder", "--encoder-path", dest="encoder", type=str, default="http://host.docker.internal:11434", help="Encoder model path.")
    parser.add_argument("-log", "--log-file", dest="logfile", type=str, default="vectordb_manager.log", help="VDB Manager log file.")

    args = parser.parse_args()

    local_addr = args.ip
    local_port = args.port
    vdb_port = args.vp
    vdb_ip = args.vip
    coll_name = args.coll
    encoder = args.encoder
    log = args.logfile
    
    app = main(collection_name=coll_name, encoder_path=encoder, logging_file=log, vdb_ip=vdb_ip, vdb_port=vdb_port)
    #uvicorn.run("vectordb_manager:app", host=local_addr, port=local_port, reload=True)
    uvicorn.run(app=app, host=local_addr, port=local_port)
    # end
    logging.info("End...")
    #main()