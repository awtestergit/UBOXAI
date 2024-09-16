# -*- coding: utf-8 -*-

"""
    AIGC ubox server, serving users with AI
    Author: awtestergit
"""
import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, Request, Form
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from werkzeug.utils import secure_filename
import socketio
from urllib.parse import parse_qs
from dataclasses import asdict, dataclass
from pydantic import BaseModel
import traceback
import json
import shutil
from qdrant_client import QdrantClient
from file_management.file_manager import server_file_mgr, server_file_item
from file_management.chat_manager import chat_history_mgr
from interface.interface_stream import AnbJsonStreamCoder
from frontend.frontend_server import webui_handlers
from frontend.session import session_manager
from interface.interface_model import llm_continue, ContinueExit
from qdrantclient_vdb.qdrant_manager import qcVdbManager
from models.llm import OllamaModel, GPTModel
from models.embed import OllamaNomicEmbeddingModel, GPTEmbeddingModel
from models.reranker import OllamaReRankerModel

import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"

def create_app(openai_key=''):
    """
    default is to use Ollama for LLM and embedding
    if openai_key is provided, LLM and embedding will use OpenAI
    """
    config_file = "config.json"

    g_config = {}
    with open(config_file) as f:
        g_config = json.load(f)

    base_folder = os.path.join('.','tmp')
    chat_folder = os.path.join('.', 'history')
    # add rest config
    g_config["BASEFOLDER"] = base_folder
    g_config["SQLITE_FOLDER"] = base_folder
    g_config["SQLITE_NAME"] = "ubox.db"
    g_config["SQLITE_CHATFOLDER"] = chat_folder
    g_config["SQLITE_CHATDB"] = "chat_history.db"
    g_config["UPLOAD_FOLDER"] = os.path.join(base_folder, 'tmpfiles')
    g_config['TREE_FILE'] = 'root.pickle' # tree root pickled file

    #print(g_config)

    client_ip = ''
    client_port = -1
    local_port = -1
    local_ip = ''
    # load client ip from config.json
    try:
        client_ip = g_config['client_ip']
        client_port = g_config['client_port']
        local_ip = g_config['local_ip']
        local_port = g_config['local_port']
    except:
        raise ValueError("server config.json does not have client_ip/client_port/local_port setting. make sure these are set.")

    # clean up all temps
    if os.path.exists(g_config['SQLITE_FOLDER']):
        try:
            shutil.rmtree(g_config['SQLITE_FOLDER'])
        except:
            pass
    if os.path.exists(g_config['SQLITE_CHATFOLDER']):
        try:
            shutil.rmtree(g_config['SQLITE_CHATFOLDER'])
        except:
            pass

    file_mgr = server_file_mgr(db_path=g_config['SQLITE_FOLDER'], db_name=g_config['SQLITE_NAME'], file_path=g_config['UPLOAD_FOLDER'])
    g_config['FILEMGR'] = file_mgr
    chat_mgr = chat_history_mgr(db_path=g_config['SQLITE_CHATFOLDER'], db_name=g_config['SQLITE_CHATDB'])
    g_config['CHATMGR'] = chat_mgr

    # session
    expires_in_minutes = int(g_config['SESSION_EXPIRATION']) if 'SESSION_EXPIRATION' in g_config else 30 # default 30 minutes
    session = session_manager(file_mgr=file_mgr, chat_mgr=chat_mgr, expiration=expires_in_minutes)

    def server_preprocess():
        run_in_docker = g_config["RUN_IN_DOCKER"] == 1 # if running in a docker
        localhost = "127.0.0.1"
        max_embedding_dim = g_config['MAX_EMBEDDING_DIM']
        llm, embed = None, None
        if len(openai_key) > 0:
            llm = GPTModel(openai_key)
            embed = GPTEmbeddingModel(openai_key, max_embedding_dim=max_embedding_dim)
        else:
            ollama_host = g_config["OLLAMA_HOST"] if run_in_docker else f"http://{localhost}:11434"
            ollama_model_name = g_config["OLLAMA_MODEL_NAME"]
            ollama_embed_name = g_config["OLLAMA_EMBED_NAME"]
            model_seq_length = g_config["MODEL_SEQ_LENGTH"]
            llm = OllamaModel(host=ollama_host, model=ollama_model_name, max_context_length=model_seq_length)
            embed = OllamaNomicEmbeddingModel(host=ollama_host, model=ollama_embed_name, max_context_length=model_seq_length, max_embedding_dim=max_embedding_dim)

        # for reranker, skip it for now
        reranker = OllamaReRankerModel() # not yet supported by Ollama

        #vdb
        vdb_ip = g_config['VDBIP'] if run_in_docker else localhost
        vdb_port = g_config['VDBPORT']
        collection_name = g_config['VDBNAME']
        client = QdrantClient(vdb_ip, port=vdb_port)
        vdbmanager = qcVdbManager(model=embed,collection_name=collection_name,client=client)
        # get tools from vdb
        doctypes = vdbmanager.get_doctype()
        tools = {} #{tool_name: tool desc}
        for doctype in doctypes:
            tool_name = doctype.type
            tool_desc = doctype.description
            tools[f"knowledge_{tool_name}"] = tool_desc # tool name: knowledge_AI

        g_config['TOOLS'] = tools

        ocr_model = None

        web_handler = webui_handlers(llm=llm, emb_model=embed, reranker_model=reranker, ocr=ocr_model, vdb_mgr=vdbmanager)
        g_config['WEBHANDLER'] = web_handler

    def server_shutdown():
        # clean up all temps
        if os.path.exists(g_config['SQLITE_FOLDER']):
            try:
                shutil.rmtree(g_config['SQLITE_FOLDER'])
            except:
                pass
        if os.path.exists(g_config['SQLITE_CHATFOLDER']):
            try:
                shutil.rmtree(g_config['SQLITE_CHATFOLDER'])
            except:
                pass

    async def periodic_cleanup():
        schedule = 60 * g_config["CLEANUP_SCHEDULE"] if "CLEANUP_SCHEDULE" in g_config else 60 # default 60 seconds
        schedule = int(schedule)
        try:
            while True:
                await asyncio.sleep(schedule)  # Clean up expired sessions every minute
                
                #print(f"........cleanup before: {session.session}")
                session.cleanup_expired_sessions()
                #print(f"........cleanup after: {session.session}")
        except (asyncio.CancelledError, GeneratorExit):
            pass
        except:
            e = traceback.format_exc()
            #print(e)
            logging.error(e)

    @dataclass
    class dc_response_header():
        status:str = '' # status string
        reason:str = '' # status reason string
        download_url:str = '' # file download url
        id:int = -1 # id of this header
    @dataclass
    class dc_response_object():
        A:str = '' # a string
        B:str = '' # bstring

    def yield_response_bytes(r): # client use reader().read, so yield
        yield r

    def get_reset_continue_flag(uid:str):
        # create continueflag session
        if not session.get_session_key(uid, session.CONTINUE_KEY):
            cf = llm_continue()
            session.set_session(uid, session.CONTINUE_KEY, cf) # set

        # reset continue flag
        continue_flag:llm_continue = session.get_session_key(uid, session.CONTINUE_KEY)
        if continue_flag:
            continue_flag.reset_stop_flag()

        return continue_flag

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        #preprocess
        server_preprocess()
        # Schedule session cleanup periodically
        asyncio.create_task(periodic_cleanup())
        # print out client connection
        client_conn = f"https://{client_ip}:{client_port}"
        print("************************************************")
        print("************************************************")
        print("***Users can connect to UBOX-AI via address:***")
        print(f"***{client_conn}***")
        print("************************************************")
        print("************************************************")
        yield
        # Clean up 
        server_shutdown()

    def cors_allowed():
        ips = ['localhost', '127.0.0.1', client_ip]
        local_ip = '' # need to get
        try:
            local_ip = g_config['local_ip']
            if local_ip != client_ip:
                ips.append(local_ip)
        except:
            pass
        cors = []
        for ip in ips:
            cors.append(f"http://{ip}")
            cors.append(f"https://{ip}")
            cors.append(f"http://{ip}:{client_port}")
            cors.append(f"https://{ip}:{client_port}")
            cors.append(f"http://{ip}:{local_port}")
            cors.append(f"https://{ip}:{local_port}")
        return cors
    origins = cors_allowed()

    #print(f"..........cors allowed: {origins}")
    logging.debug(f"..........cors allowed: {origins}")

    app = FastAPI(lifespan=lifespan, debug=True)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    #print("....app .")
    sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins=[], logger=True, engineio_logger=True) # this cors should be [] to be disabled, can not be '*'
    app.mount('/socket.io/', socketio.ASGIApp(sio))
    #socket_app = socketio.ASGIApp(sio, app, socketio_path='socket.io')
    #print(".....socketio...")

    @app.get('/')
    def init():
        return 'success'

    @app.post('/doc_upload')
    async def doc_upload(file: UploadFile, uid:str = Form(...), ocr:int = Form(...), read_by:int = Form(...)):

        #print(f"......{file.filename}, {uid}, {ocr}, {read_by}")
        logging.debug(f"......{file.filename}, {uid}, {ocr}, {read_by}")

        is_same_uid = session.cross_check_uid_in_session(uid)
        if not is_same_uid:
            r = dc_response_header()
            r.status = 'fail'
            r.reason = 'can not get client session ID! Try to refresh the page.'
            response_json = asdict(r)
            return response_json
        
        if file.filename == '':
            r = dc_response_header()
            r.status = 'fail'
            r.reason = 'No files uploaded!'
            response_json = asdict(r)
            return response_json
        
        filename = secure_filename(file.filename)
        # set session id
        session.set_session(uid, session.UID_KEY, uid) # set the UID_KEY for this client @ uid

        is_ocr = int(ocr) != 0 # either '0' or '1'

        read_by = int(read_by) if read_by else 0 # default read by page

        #print(f"client file info: {filename}, {uid}, {is_ocr}")
        logging.debug(f"client file info: {filename}, {uid}, {is_ocr}")

        # get and reset continue flag
        continue_flag:llm_continue = get_reset_continue_flag(uid)

        try:
            # save files
            mgr:server_file_mgr = g_config['FILEMGR']
            item = server_file_item(file_obj=file, file_path=filename)
            # need to manually save UploadFile
            saved_filepaths = mgr.track_file_add_path_to_db(uuid=uid, file_items=[item], save=False) # do not save
            with open(saved_filepaths[0], "wb") as f: # manually save
                contents = await file.read()
                f.write(contents)

            # get web handler
            web_handler:webui_handlers = g_config['WEBHANDLER']
            # build index
            with open(saved_filepaths[0]) as f:
                index, texts = web_handler.doc_upload(f, is_ocr, read_by=read_by, continue_flag=continue_flag)
                # save to session
                session.set_session(uid, session.FAISS_KEY, index)
                session.set_session(uid, session.FAISS_TEXTS, texts)

            #print(f"..........server session: {session[FAISS_KEY]}, texts: {session[FAISS_TEXTS]}")

            # respond success
            r = dc_response_header()
            r.status = 'success'
            response_json = asdict(r)
            
            #print(response_json)
            
            # do not use Response, without properly set headers
            return response_json
        except (ContinueExit, GeneratorExit):
            # log
            #print('..............dochat_upload received stop signal.')
            logging.debug('..............dochat_upload received stop signal.')
            return {}
        except:
            e = traceback.format_exc()
            r = dc_response_header()
            r.status = 'fail'
            r.reason = str(e)
            return r
        finally:
            await file.close() # close

    @app.get('/dochat_chat')
    async def dochat_chat(uid:str, q:str, words:int):
        """
        """
        faiss_index=None
        texts = []
        query = q

        is_same_uid = session.cross_check_uid_in_session(uid)
        if not is_same_uid:
            r = dc_response_header()
            r.status = 'fail'
            r.reason = 'can not get client session ID! Try to refresh the page.'
            response_header = asdict(r)
            response_json = {}
            response_bytes = AnbJsonStreamCoder.encode(response_header, response_json)
            return StreamingResponse(yield_response_bytes(response_bytes), media_type='application/octet-stream')

        try:
            faiss_index = session.get_session_key(uid, session.FAISS_KEY)
            texts = session.get_session_key(uid,session.FAISS_TEXTS)
            words = int(words)
            #print(f"..........dochat get query {query}, words: {words}")
        except (ContinueExit, GeneratorExit):
            # log
            #print('..............dochat_chat @ 1 received stop signal.')
            logging.debug('..............dochat_chat @ 1 received stop signal.')
            return
        except:
            
            #print(f"dochat_chat failed. {traceback.format_exc()}")
            logging.error(f"dochat_chat failed. {traceback.format_exc()}")

            r = dc_response_header()
            r.status = 'fail'
            r.reason = "Session has expired. please refresh your page."
            r_header = asdict(r)
            r_obj = {}
            r_bytes = AnbJsonStreamCoder.encode(r_header, r_obj)
            return StreamingResponse(yield_response_bytes(r_bytes), media_type='application/octet-stream')

        # get and reset continue flag
        continue_flag:llm_continue = get_reset_continue_flag(uid)

        # get web handler
        web_handler:webui_handlers = g_config['WEBHANDLER']
        reranker_conf = g_config['RERANKCONF']
        reranker_min_score = g_config['RERANKMINSCORE']
        ###
        # use asyncio.to thread to await for all web_handler long executions
        # this await will enable stop event to be executed in between long executions
        results = await asyncio.to_thread(web_handler.doc_question, query=query, words=words, faiss_index=faiss_index, texts=texts, rerank_threshold=reranker_conf, rerank_min_score=reranker_min_score, continue_flag=continue_flag)
        
        async def convert_results_to_stream(results):
            error = None # exception
            try:
                for output in results:
                    status  = output['status']
                    r = dc_response_header()
                    if status == 0: # success
                        r.status = 'success'
                        r_header = asdict(r)
                        r_obj = {
                            'text': output['text'],
                            'sources': output['sources'],
                        }
                        r_bytes = AnbJsonStreamCoder.encode(r_header,r_obj)
                        yield r_bytes
                    elif status == 1: # warning
                        r.status = 'success'
                        r_header = asdict(r)
                        text = f"{output['error']}::{output['text']}"
                        r_obj = {
                            'text': text,
                        }
                        r_bytes = AnbJsonStreamCoder.encode(r_header,r_obj)
                        yield r_bytes
                    elif status == -1: # failure
                        r.status = 'fail'
                        r.reason = output['error']
                        r_header = asdict(r)
                        r_obj = {}
                        r_bytes = AnbJsonStreamCoder.encode(r_header, r_obj)
                        yield r_bytes
            except (ContinueExit, GeneratorExit):
                # log
                #print('..............dochat_chat @ streaming received stop signal.')
                return
            except Exception as e:
                # error
            #    print(f"...........exception: {e}")
                #logging.error(f"Caught an exception: {e}. Type: {type(e).__name__}, Args: {e.args}")
                error = traceback.format_exc()
                #print(f"exception error: {error}; e is: {e}")
                logging.error(f"exception error: {error}")

            # if error
            if error is not None:
                r = dc_response_header()
                r.status = 'fail'
                r.reason = f"an error happened. technical details: {error}"
                r_header = asdict(r)
                r_obj = {}
                r_bytes = AnbJsonStreamCoder.encode(r_header, r_obj)
                #print(f".........in exception r bytes: {r_bytes}")
                yield r_bytes

            # send 'end'
            r = dc_response_header()
            r.status = 'end'
            r_header = asdict(r)
            r_obj = {}
            r_bytes = AnbJsonStreamCoder.encode(r_header, r_obj)
            #print(f".........in end r bytes: {r_bytes}")
            yield r_bytes
            # end

        rs = convert_results_to_stream(results)
        # use application/octet-stream mimetype
        return StreamingResponse(rs, media_type='application/octet-stream')

    class elements_in(BaseModel):
        #elements:list = lambda: []
        elements:str = ''
        uid:str

    @app.post('/doctract')
    async def doctract(params: elements_in):
        """
        """
        results = None
        elements = params.elements
        uid = params.uid

        is_same_uid = session.cross_check_uid_in_session(uid)
        if not is_same_uid:
            r = dc_response_header()
            r.status = 'fail'
            r.reason = 'can not get client session ID! Try to refresh the page.'
            response_header = asdict(r)
            response_json = {}
            response_bytes = AnbJsonStreamCoder.encode(response_header, response_json)
            return StreamingResponse(yield_response_bytes(response_bytes), media_type='application/octet-stream')

        faiss_index = session.get_session_key(uid, session.FAISS_KEY)
        texts = session.get_session_key(uid, session.FAISS_TEXTS)
        if faiss_index is None or texts is None:
            r = dc_response_header()
            r.status = 'fail'
            r.reason = "Session has expired. please refresh your page."
            r_header = asdict(r)
            r_obj = {}
            r_bytes = AnbJsonStreamCoder.encode(r_header, r_obj)
            #print(f".........in exception r bytes: {r_bytes}")
            logging.warning(f".........in doctract: {r_bytes}")
            return StreamingResponse(yield_response_bytes(r_bytes),media_type='application/octet-stream')

        # get and reset continue flag
        continue_flag = get_reset_continue_flag(uid)

        try:
            # get web handler
            web_handler:webui_handlers = g_config['WEBHANDLER']
            rerank_threshold = g_config['RERANKCONF']
            rerank_min_score = g_config['RERANKMINSCORE']
            results = await asyncio.to_thread(web_handler.doc_extract, elements, faiss_index=faiss_index, texts=texts, rerank_threshold=rerank_threshold, rerank_min_score=rerank_min_score, continue_flag=continue_flag)
        except (ContinueExit, GeneratorExit):
            # log
            #print('..............doctract @ 1 received stop signal.')
            logging.debug('..............doctract @ 1 received stop signal.')
            return
        except Exception as e:
            err = traceback.format_exc()
            r = dc_response_header()
            r.status = 'fail'
            r.reason = err
            r_header = asdict(r)
            r_obj = {}
            r_bytes = AnbJsonStreamCoder.encode(r_header, r_obj)
            #print(f".........in exception r bytes: {r_bytes}")
            logging.error(f".........doctract in exception r bytes: {r_bytes}")
            return StreamingResponse(yield_response_bytes(r_bytes),media_type='application/octet-stream')

        def convert_results_to_stream(results):
            error = None # exception
            try:
                for output in results:
                    status  = output['status']
                    r = dc_response_header()
                    if status == 0 or status == 1: # success or warning
                        r.status = 'success'
                        r_header = asdict(r)
                        r_obj = {
                            'element': output['element'],
                            'detail': output['detail'],
                            'sources': output['sources'],
                            'source_id': output['source_id'],
                        }
                        r_bytes = AnbJsonStreamCoder.encode(r_header,r_obj)
                        yield r_bytes
                    elif status == -1: # failure
                        r.status = 'fail'
                        r.reason = output['error']
                        r_header = asdict(r)
                        r_obj = {}
                        r_bytes = AnbJsonStreamCoder.encode(r_header, r_obj)
                        yield r_bytes
            except (ContinueExit, GeneratorExit):
                # log
                #print('..............doctract @ streaming received stop signal.')
                logging.debug('..............doctract @ streaming received stop signal.')
                return
            except Exception as e:
                # error
            #    print(f"...........exception: {e}")
                #logging.error(f"Caught an exception: {e}. Type: {type(e).__name__}, Args: {e.args}")
                error = traceback.format_exc()
                #print(f"exception error: {error}; e is: {e}")
                logging.error(f"doctract exception error: {error}")

            # if error
            if error is not None:
                r = dc_response_header()
                r.status = 'fail'
                r.reason = f"an error happened. technical details: {error}"
                r_header = asdict(r)
                r_obj = {}
                r_bytes = AnbJsonStreamCoder.encode(r_header, r_obj)
                #print(f".........in exception r bytes: {r_bytes}")
                yield r_bytes

            # send 'end'
            r = dc_response_header()
            r.status = 'end'
            r_header = asdict(r)
            r_obj = {}
            r_bytes = AnbJsonStreamCoder.encode(r_header, r_obj)
            #print(f".........in end r bytes: {r_bytes}")
            yield r_bytes
            # end

        rs = convert_results_to_stream(results)
        # use application/octet-stream mimetype
        return StreamingResponse(rs,media_type='application/octet-stream')

    @app.post('/docompare')
    #async def docompare(A:UploadFile, B:UploadFile, uid:str, compare:str, a_ocr:str, b_ocr:str):
    async def docompare(request: Request):
        #// request format
        #// {
        #//    'A': fileA,
        #//    'B': fileB,
        #//    'compare': 'Page',
        #//    'uid': 12345,
        #//}

        # response header json format
        # {
        #   'status': success / warning / fail / or end
        #   'reason': ''
        #   'download_url': url to download,
        #   'id': id 
        # }
        # response object json
        # {
        #   'A': xxxx,
        #   'B': xxxx,
        # }
        params = await request.form()
        a_file = params.get('A')
        b_file = params.get('B')
        uid = params.get('uid')
        compare = params.get('compare')
        a_ocr = params.get('a_ocr')
        b_ocr = params.get('b_ocr')
        # files format {'A': [fileA, isScanned], 'B':[fileB, isScanned]}
        a_scanned = int(a_ocr) != 0 # either '0' or '1'
        b_scanned = int(b_ocr) != 0

        a_key = "A"
        b_key = "B"
        a_filename = secure_filename(a_file.filename)
        b_filename = secure_filename(b_file.filename)

        compare_by = int(compare) # convert to int, 0 - page, 1 - document, 2 - paragraph

        is_same_uid = session.cross_check_uid_in_session(uid)
        if not is_same_uid:
            r = dc_response_header()
            r.status = 'fail'
            r.reason = 'can not get client session ID! Try to refresh the page.'
            response_header = asdict(r)
            response_json = {}
            response_bytes = AnbJsonStreamCoder.encode(response_header, response_json)
            return StreamingResponse(yield_response_bytes(response_bytes), media_type='application/octet-stream')


        #print(f"client file info: {a_filename}, {b_filename}, {uid}, {compare_by}")
        logging.debug(f"client file info: {a_filename}, {b_filename}, {uid}, {compare_by}")

        # get and reset continue flag
        continue_flag:llm_continue = get_reset_continue_flag(uid)

        # save to file manager
        mgr:server_file_mgr = g_config['FILEMGR']
        item = server_file_item(file_obj=a_file, file_path=a_filename)
        # need to manually save UploadFile
        saved_filepaths = mgr.track_file_add_path_to_db(uuid=uid, file_items=[item], save=False) # do not save
        a_filename = saved_filepaths[0]
        with open(saved_filepaths[0], "wb") as f: # manually save
            contents = await a_file.read()
            f.write(contents)
        item = server_file_item(file_obj=b_file, file_path=b_filename)
        saved_filepaths = mgr.track_file_add_path_to_db(uuid=uid, file_items=[item], save=False) # do not save
        b_filename = saved_filepaths[0]
        with open(saved_filepaths[0], "wb") as f: # manually save
            contents = await b_file.read()
            f.write(contents)

        # get web handler
        web_handler:webui_handlers = g_config['WEBHANDLER']

        # processing
        def compare_proc():
            error = None
            try:
                outputs = web_handler.compare_files(a_filename, b_filename,compare_by=compare_by, a_ocr=a_scanned, b_ocr=b_scanned, streaming=True, continue_flag=continue_flag)
                for idx, output in enumerate(outputs):
                    status = output['status']
                    a = output['A']
                    b = output['B']
                    if status == 0: # success
                        r = dc_response_header()
                        r.status = 'success'
                        r.id = idx
                        response_header = asdict(r)
                        response_json = {
                            a_key: a,
                            b_key:b
                        }
                        response_bytes = AnbJsonStreamCoder.encode(response_header, response_json)
                        yield response_bytes
                    elif status == 1: # warning
                        r = dc_response_header()
                        r.status = 'warning'
                        r.reason = output['error']
                        r.id = idx
                        response_header = asdict(r)
                        response_json = {}
                        response_bytes = AnbJsonStreamCoder.encode(response_header, response_json)
                        yield response_bytes
                    else: # error
                        r = dc_response_header()
                        r.status = 'fail'
                        r.reason = output['error']
                        r.id = idx
                        response_header = asdict(r)
                        response_json = {}
                        response_bytes = AnbJsonStreamCoder.encode(response_header, response_json)
                        yield response_bytes

            except (ContinueExit, GeneratorExit): # yield will raise GeneratorExit if client aborts
                # log
                #print("....route docompare:: stop signal received, exit...")
                logging.debug("....route docompare:: stop signal received, exit...")
                return # return
            except Exception:
                error = traceback.format_exc()
                #log error
                #print("......route docompare:: " + error)
                logging.error("......route docompare:: " + error)

            if error is not None:
                r = dc_response_header()
                r.status = 'fail'
                r.reason = f"Error, technical details: {error}"
                response_header = asdict(r)
                response_json = {}
                response_bytes = AnbJsonStreamCoder.encode(response_header, response_json)
                yield response_bytes

            # send 'end'
            r = dc_response_header()
            r.status = 'end'
            response_header = asdict(r)
            response_json = {}

            response_bytes = AnbJsonStreamCoder.encode(response_header, response_json)
            yield response_bytes
            # end
            return

        return StreamingResponse(compare_proc(), media_type='application/octet-stream')


    @app.get('/docknow_clear_history')
    async def docknow_clear_history(uid:str, recent:str=''):
        is_same_uid = session.cross_check_uid_in_session(uid)
        if not is_same_uid:
            r = dc_response_header()
            r.status = 'fail'
            r.reason = 'can not get client session ID! Try to refresh the page.'
            response_json = asdict(r)
            return response_json

        error = None
        try:
            recent = int(recent) if len(recent)>0 else -1
            chat_mgr:chat_history_mgr = g_config['CHATMGR']
            chat_mgr.delete_chat_history(uuid=uid, keep_recent=recent)
        except:
            error = traceback.format_exc()
        status = 'success' if error is None else 'fail'
        r = {
            'status': status,
            'error': error if error else '',
        }
        return r

    @app.post('/docknow')
    async def docknow(request: Request):
        """
        """
        params = await request.form()
        uid = params.get('uid')
        query = params.get('query')
        words = params.get('words')
        history = params.get('history')
        bot = params.get('bot')
        temperature = params.get('temperature')
        top_p = params.get('top_p')
        top_k = params.get('top_k')
        repetition_penalty = params.get('repetition_penalty')
        faq_conf = params.get('faq_conf')
        vdb_conf = params.get('vdb_conf')

        is_same_uid = session.cross_check_uid_in_session(uid)
        if not is_same_uid:
            r = dc_response_header()
            r.status = 'fail'
            r.reason = 'can not get client session ID! Try to refresh the page.'
            response_header = asdict(r)
            response_json = {}
            response_bytes = AnbJsonStreamCoder.encode(response_header, response_json)
            return StreamingResponse(yield_response_bytes(response_bytes), media_type='application/octet-stream')

        d_words = 300 # default
        d_recent_history = 100 # recent history
        d_bot_name = 'ubox' # default name
        d_faq_conf = 0.94 # default faq confidence
        d_vdb_conf = 0.6

        try:
            words = int(words) if words else d_words
            recent_history = int(history) if history else d_recent_history
            bot_name = bot if bot else d_bot_name
            temperature = float(temperature) if temperature else 0.3
            top_p = float(top_p) if top_p else 0.95
            top_k = int(top_k) if top_k else 3
            repetition_penalty = float(repetition_penalty) if repetition_penalty else 1.1
            faq_conf = float(faq_conf) if faq_conf else d_faq_conf
            vdb_conf = float(vdb_conf) if vdb_conf else d_vdb_conf
            kwargs = {
                'temperature': temperature,
                'max_new_tokens': words,
                'top_k': top_k,
                'top_p': top_p,
                'repetition_penalty': repetition_penalty,
            }
            #print(f"..........docknow get query {query}, words: {words}, history: {recent_history}, faq conf: {faq_conf}")

        except (ContinueExit, GeneratorExit):
            # log
            #print('..............docknow @ 1 received stop signal.')
            logging.debug('..............docknow @ 1 received stop signal.')
            return
        except Exception as e:
            r = dc_response_header()
            r.status = 'fail'
            r.reason = "Cannot process empty query."
            r_header = asdict(r)
            r_obj = {}
            r_bytes = AnbJsonStreamCoder.encode(r_header, r_obj)
            #print(f".........in exception r bytes: {r_bytes}")
            logging.error(f".........docknow in exception r bytes: {r_bytes}")
            return StreamingResponse(yield_response_bytes(r_bytes), media_type='application/octet-stream')


        # get web handler
        web_handler:webui_handlers = g_config['WEBHANDLER']
        reranker_conf = g_config['RERANKCONF']
        reranker_min_score = g_config['RERANKMINSCORE']
        # chat history
        chat_history = []
        try:
            chat_mgr:chat_history_mgr = g_config['CHATMGR']
            chat_history = chat_mgr.get_chat_history(uuid=uid, recent=recent_history)
            chat_history = [(history[0], history[1]) for history in reversed(chat_history)] # chat_history was [query, answer, time], get rid of time
        except (ContinueExit, GeneratorExit):
            # log
            #print('..............docknow @ 2 received stop signal.')
            logging.debug('..............docknow @ 2 received stop signal.')
            return
        except:
            error = traceback.format_exc()
            #print(f"docknow failed to get history. uid: {uid}, error: {error}")
            logging.error(f"docknow failed to get history. uid: {uid}, error: {error}")
        
        #print(f"chat history: {chat_history}")

        tools = g_config['TOOLS']
        streaming_delta = True # only delta
        # get and reset continue flag
        continue_flag:llm_continue = get_reset_continue_flag(uid)
        results = await asyncio.to_thread(web_handler.doc_know, query=query, tools=tools, history=chat_history, faq_conf=faq_conf, vdb_conf=vdb_conf, rerank_threshold=reranker_conf, rerank_min_score=reranker_min_score, bot_name=bot_name, streaming=True, streaming_delta=streaming_delta, continue_flag=continue_flag, **kwargs)
        def convert_results_to_stream(results):
            error = None # exception
            full_answer = ''
            # results: [iterator, sources]
            sources = results[1]
            answers = results[0]
            try:
                for answer in answers:
                    full_answer += answer
                    r = dc_response_header()
                    r.status = 'success'
                    r_header = asdict(r)
                    r_obj = {
                        'answer': answer,
                        'sources': '',
                    }
                    r_bytes = AnbJsonStreamCoder.encode(r_header,r_obj)
                    yield r_bytes
                # now send 'sources'
                for source in sources:
                    r = dc_response_header()
                    r.status = 'success'
                    r_header = asdict(r)
                    r_obj = {
                        'answer': '',
                        'sources': source,
                    }
                    r_bytes = AnbJsonStreamCoder.encode(r_header,r_obj)
                    yield r_bytes

            except (ContinueExit, GeneratorExit):
                # log
                #print('..............docknow @ streaming received stop signal.')
                logging.debug('..............docknow @ streaming received stop signal.')
                return
            except:
                # error
            #    print(f"...........exception: {e}")
                #logging.error(f"Caught an exception: {e}. Type: {type(e).__name__}, Args: {e.args}")
                error = traceback.format_exc()
                #print(f"exception error: {error}; e is: {error}")
                logging.error(f"exception error: {error}")

            try: # log history
                chat_mgr.add_chat(uuid=uid, query=query, answer=full_answer) if len(full_answer) > 0 else None
            except: # fail siliently but log it
                err = traceback.format_exc() # not use 'error'
                #print(f"doc_know failed to save history. {err}")
                logging.error(f"doc_know failed to save history. {err}")

            # if error
            if error is not None:
                r = dc_response_header()
                r.status = 'fail'
                r.reason = f"an error happened. technical details: {error}"
                r_header = asdict(r)
                r_obj = {}
                r_bytes = AnbJsonStreamCoder.encode(r_header, r_obj)
                yield r_bytes

            # send 'end'
            r = dc_response_header()
            r.status = 'end'
            r_header = asdict(r)
            r_obj = {}
            r_bytes = AnbJsonStreamCoder.encode(r_header, r_obj)
            yield r_bytes
            # end

        rs = convert_results_to_stream(results)
        # use application/octet-stream mimetype
        return StreamingResponse(rs, media_type='application/octet-stream')

    @app.get('/stop')
    async def stop_gen(uid:str):
        # get continue flag, best effort
        continue_flag:llm_continue = session.get_session_key(uid, session.CONTINUE_KEY)
        if continue_flag:
            #print(f"...........reset continue flag for uid: {uid}, {continue_flag}")
            logging.debug(f"...........reset continue flag for uid: {uid}, {continue_flag}")
            continue_flag.set_stop_flag()
        else:
            #print(f".........did not get the continue flag for uid: {uid}")
            logging.debug(f".........did not get the continue flag for uid: {uid}")
        return 'sent stop signal'

    @sio.on('connect')
    async def connect(sid:str, environ): # connect takes an environ variable
        #print(f"......Client connected: {sid}") #, environ: {environ}")
        logging.debug(f"......Client connected: {sid}")
        uid = None # get uid
        qs = environ.get('QUERY_STRING', None)
        error = "Cannot get UID from client" if qs is None else None
        if not error :
            ps = parse_qs(qs)
            uid = ps.get('uid', [None])[0]
            error = "Cannot get UID from client" if uid is None else None
        if not error:
            session.set_session_sid(sid, uid) # set sid and uid, these two can cross reference, uid contains all relevant key/value

        #print(f"....connect: session all: {session.session}")

        if error:
            #print(f"........error: {error}")
            logging.error(f"........connect error: {error}")
            await sio.emit('connect_error_data', data={"error": error}, to=sid)

    @sio.on('message')
    async def handle_message(sid, data):
        #print(f'.........handle message: Received message, sid: {sid}, data: {data}')
        logging.debug(f'.........handle message: Received message, sid: {sid}, data: {data}')
        try:
            uid = session.get_session_key(uid=sid, key=session.UID_KEY) # get uid
            loggedIn, userId, userName = data.values()
            if uid:
                session.set_session(uid, session.LOGGEDIN, loggedIn)
                session.set_session(uid, session.USERNAME, userName)
                session.set_session(uid, session.USERID, userId)
            #socketio.emit('message', {'response': 'Server received your message'}, room=request.sid)
        except:
            e = traceback.format_exc()
            #print(f"client handle message exception: {e}")
            logging.error(f"client handle message exception: {e}")

    @sio.on('disconnect')
    async def disconnect(sid:str): # disconnect does not
        #print(f"......Client disconnected: {sid}")
        logging.debug(f"......Client disconnected: {sid}")
        try:
            uid = session.get_session_key(uid=sid, key=session.UID_KEY) # get uid
            # clear all key/value
            session.remove_session_sid(sid)
            session.remove_session(uid) # remove uid k/v, should have been removed at remove_session_sid, but in case...
            # clear files
            if uid:
                mgr:server_file_mgr = g_config['FILEMGR']
                mgr.delete_file_remove_path_from_db(uuid=uid)
                # clear history
                chat_mgr:chat_history_mgr = g_config['CHATMGR']
                chat_mgr.delete_chat_history(uuid=uid)
        except Exception:
            e = traceback.format_exc()
            #print(f"client disconnect exception: {e}")
            logging.error(f"client disconnect exception: {e}")
        #print(f"....disconnect: session all: {session.session}")

    return app
