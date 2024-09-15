# -*- coding: utf-8 -*-

"""
    provide Qdrantclient functionalities management, managing collections (create/update/delete etc), query etc
    Author: awtestergit
"""
import logging

from dataclasses import asdict
from datetime import datetime
from interface.interface_model import ILanguageModel
from qdrantclient_vdb.qdrant_base import qcIdIndex, qcDocTypeIndex, qcFileIndex, qcChunkIndex, doctype_schema, file_schema, chunk_schema, qcFaqIndex, faq_schema

class qcIndex():
    qcidindex:qcIdIndex=None
    qcdoctypeindex:qcDocTypeIndex = None
    qcfileindex:qcFileIndex=None
    qcchunkindex:qcChunkIndex=None
    qcfaqindex:qcFaqIndex = None

class qcVdbManager():
    """
    each vdb manager holds 4 indexes: id, doctype, file, chunk
        + 1 FAQ
    """
    def __init__(self, model:ILanguageModel, collection_name="", client=None, total_faq_orgs:int=1000) -> None:
        """
        total_faq_orgs: the max number of organizations (including department, teams etc) to have FAQ
        faq_conf, the confidence of comparing the question to the stored question, similarity
        vdb_conf, the same as above, but for vdb query
        """
        self.model = model#embedding model
        self.collection_name = collection_name #only use as prefix_name for id, file, chunk index
        self.client = client
        self.total_faq_orgs = total_faq_orgs
        self.qcindex:qcIndex = self.__initialize_index__() #initialize 4 indices
        self.time_format = "%Y-%m-%d"

    def __initialize_index__(self):
        qcindex = qcIndex()
        # id index
        name = f"{self.collection_name}_{qcIdIndex.SUFFIX}"
        qcindex.qcidindex = qcIdIndex(collection_name=name, client=self.client)
        # doctype index
        name = f"{self.collection_name}_{qcDocTypeIndex.SUFFIX}"
        qcindex.qcdoctypeindex = qcDocTypeIndex(collection_name=name,qcidindex=qcindex.qcidindex, client=self.client)
        # file index
        name = f"{self.collection_name}_{qcFileIndex.SUFFIX}"
        qcindex.qcfileindex = qcFileIndex(collection_name=name, qcidindex=qcindex.qcidindex, client=self.client)
        # chunk index
        name = f"{self.collection_name}_{qcChunkIndex.SUFFIX}"
        qcindex.qcchunkindex = qcChunkIndex(collection_name=name, client=self.client, vector_size=self.model.EMBED_SIZE)
        # faq index
        name = f"{self.collection_name}_{qcFaqIndex.SUFFIX}"
        qcindex.qcfaqindex = qcFaqIndex(collection_name=name, client=self.client, vector_size=self.model.EMBED_SIZE, total_faq_orgs=self.total_faq_orgs)
        return qcindex

    def add_doctype(self, type, description):
        collection_name = self.qcindex.qcdoctypeindex.collection_name
        doctype:doctype_schema = doctype_schema(collection_name=collection_name, type=type, description=description)
        return self.qcindex.qcdoctypeindex.add_doctype(doctype=doctype)

    def add_file_id_to_group(self, file_id)->tuple[int, int, bool]:
        """
        add group id by a file id. case being that a duplicate/relevant file is found, then group thest two together
        input: file_id
        output: group id, the current max index_in_group index, is_new_group_id
        """
        return self.qcindex.qcfileindex.add_file_id_to_group(file_id=file_id)

    def check_duplicate(self, chunks:list[str], type:str='', num_samples_to_check_duplicate=3, threshold=0.95, check_all_types=True)->(bool, list[chunk_schema]):
        """
        chunks to be sampled and checked
        num_sample_to_check_duplicate: how many samples from chunks to check duplicate
        outputs:
            str: the reason of the failure
            list: list of chunk_schemas
        """
        # sample n texts
        n = num_samples_to_check_duplicate if num_samples_to_check_duplicate > 0 else 3
        steps = int(len(chunks) / n)
        texts = [chunks[i] for i in range(0,len(chunks),steps)] if steps >= 1 else chunks
        text_vectors = [self.model.encode(text, to_list=True) for text in texts]
        #threshold = 0.9# a high similarity score
        type = '' if check_all_types else type
        results = self.qcindex.qcchunkindex.check_similar_chunks(text_vectors, type=type, threshold=threshold)
        duplicate = (len(results) > 0)

        return duplicate, results

    def delete(self, file_id, auto_remove=True):
        fileinfo:file_schema = self.qcindex.qcfileindex.get_fileinfo_by_file_id(file_id=file_id)
        if fileinfo is not None:
            doctype_id = fileinfo.doctype_id
            #delete from chunk index
            self.qcindex.qcchunkindex.delete_chunks_by_file_id(file_id=file_id)
            #delete from file index
            self.qcindex.qcfileindex.delete_file_index(file_id=file_id)
            # delete from doctype index
            self.qcindex.qcdoctypeindex.remove_file_id_from_doctype(file_id=file_id, point_id=doctype_id, auto_remove_doctype=auto_remove)

    def delete_all_by_doctype(self, doctype_id:int):
        if doctype_id != -1:
            # get all file ids
            doctype:doctype_schema = self.qcindex.qcdoctypeindex.get_doctype_by_id(point_id=doctype_id)
            if doctype is not None:
                file_ids = doctype.file_ids
                for file_id in file_ids:
                    #delete from chunk index
                    self.qcindex.qcchunkindex.delete_chunks_by_file_id(file_id=file_id)
                    #delete from file index
                    self.qcindex.qcfileindex.delete_file_index(file_id=file_id)
                # delete doctype
                self.qcindex.qcdoctypeindex.delete_doctype(doctype_id=doctype_id)
    
    def get_fileinfo(self)->list[file_schema]:
        """
        get all fileinfo in the file_index collection
        """
        return self.qcindex.qcfileindex.get_fileinfo()

    def get_fileinfo_by_id(self, file_id)->file_schema:
        """
        get  fileinfo in the file_index collection by id
        """
        return self.qcindex.qcfileindex.get_fileinfo_by_file_id(file_id=file_id)

    def get_fileinfo_by_group(self, group_id)->list[file_schema]:
        return self.qcindex.qcfileindex.get_fileinfo_by_group_id(group_id=group_id)

    def get_doctype(self)->list[doctype_schema]:
        """
        get all doc type in doctype index
        """
        return self.qcindex.qcdoctypeindex.get_doctype()

    def get_doctype_by_id(self, doctype_id)->doctype_schema:
        """
        get  doc type in doctype index by id
        """
        return self.qcindex.qcdoctypeindex.get_doctype_by_id(point_id=doctype_id)

    def get_doctype_by_type(self, _type)->doctype_schema:
        """
        get  doc type in doctype index by type
        """
        return self.qcindex.qcdoctypeindex.get_doctype_by_type(type=_type)
        
    def insert(self, type:str, type_desc:str, file_id=-1, file_full_path:str='', group_id=-1, index_in_group=-1, file_creation_time:datetime=None, file_desc:str='', chunks:list[str, str]=[])->tuple[bool, str]:
        """
        insert text chunks associated with a file to vdb
        the insertion will touch all 4 indices (add, update etc)
        inputs:
            type: the type, type_desc, the description of type
            file_id: if -1, will generate a new file_id, otherwise, reuse this file_id (in the case of update file operation)
            file_full_path: the full path of the file, used as 'source_from'
            group_id: the group_id this file belongs to
            index_in_group: the index in group of this file
            type: the type of this file content
            type_desc: the description of the type
            chunks: a list of (meta, source_from) pair, where meta is the raw chunk text, source_from is the chunk's origin, e.g, file_path_page_2
        outputs:
            bool: if True, success, if False, the insert failed
            str: reason
        """
        reason = ''
        if file_full_path is None or len(file_full_path)==0 or chunks is None or len(chunks)==0:
            reason = 'either file path is empty or chunks is empty'
            return False, reason

        #else, insert
        ######doctype index######
        # check if doctype exists
        doctype:doctype_schema = self.qcindex.qcdoctypeindex.get_doctype_by_type(type=type)
        doctype_id = -1
        if doctype is not None:
            doctype_id = doctype.point_id # existing id
        else:
            doctype_id = self.qcindex.qcidindex.get_doctype_id_max() #new id

        ###### file index ######
        # create file content to be inserted into file index
        file_content = file_schema()
        file_content.file_id =file_id if file_id != -1 else self.qcindex.qcidindex.get_file_id_max() # get the file id for this file
        file_content.group_id = group_id # if any
        file_content.index_in_group = index_in_group # if any
        file_content.type = type
        _time = datetime.now().strftime(self.time_format)
        file_content.time_add_to_vdb = _time
        file_content.collection_name = self.qcindex.qcfileindex.collection_name
        file_content.source_from = file_full_path
        file_content.doctype_id = doctype_id # assign the doctype id
        file_content.file_desc = file_desc # file description
        # creation time
        file_content = self.set_fileinfo_creation_time(fileinfo=file_content, creation_time=file_creation_time)


        ######chunks######
        # get the max point id
        size = len(chunks)
        point_id_start, point_id_end = self.qcindex.qcidindex.get_batch_point_id_max(size) # start and end index
        file_content.point_id_start = point_id_start
        file_content.point_id_end = point_id_end
        # insert chunk to chunk index
        point_ids = [i for i in range(point_id_start, point_id_end+1)] #[point_id_start, point_id_end] is the point ids
        #vectors = [self.model.encode_numpy(text) for text, _ in chunks]
        vectors = [self.model.encode(text, to_list=True) for text, _ in chunks]
        contents = []
        for idx, chunk in enumerate(chunks):
            content = chunk_schema(chunk_id=idx, file_id=file_content.file_id, type=type, meta=chunk[0], source_from=chunk[1])
            contents.append(content)
        result = self.qcindex.qcchunkindex.add_chunks_to_vdb(contents, point_ids=point_ids, vectors=vectors)
        
        # insert file index
        self.qcindex.qcfileindex.add_file_index(file_content)
        
        ######doctype index continue######
        if doctype is None:#create new
            doctype = doctype_schema(point_id=doctype_id, collection_name=self.qcindex.qcdoctypeindex.collection_name, type=type, description=type_desc, file_ids=[file_content.file_id])
        else:#append to existing
            doctype.file_ids.append(file_content.file_id)
        # insert doctype index
        self.qcindex.qcdoctypeindex.add_doctype(doctype=doctype)

        return True, 'success'

    def update(self, file_id, file_full_path:str='', group_id=-1, file_creation_time:datetime=None, file_desc:str='', chunks:list[str, str]=[])->tuple[bool, str]:
        """
        update: delete then insert
        inputs:
            file_id: to be deleted from both chunk index and file index
            file_full_path: the full path of the file, used as 'source_from'
            group_id: the group_id this file belongs to
            chunks: a list of (meta, source_from) pair, where meta is the raw chunk text, source_from is the chunk's origin, e.g, file_path_page_2
        outputs:
            bool: if True, success, if False, the insert failed
            str: reason
        """
        # get the file info by id
        content:file_schema = self.qcindex.qcfileindex.get_fileinfo_by_file_id(file_id=file_id) # get the existing info
        if content is None:
            error = f"qcVdbManager::update failed to get content. fileid: {file_id}"
            print(error)
            logging.debug(error)
            return False, 'failed'
        type = content.type
        doctype:doctype_schema = self.qcindex.qcdoctypeindex.get_doctype_by_type(type=type) # get the existing info
        if doctype is None:
            error = f"qcVdbManager::update failed to get doctype. fileid: {file_id}, type: {content.type}"
            print(error)
            logging.debug(error)
            return False, 'failed'

        group_id = group_id if group_id > 0 else content.group_id # use existing group if not inputed
        type_desc = doctype.description # desc

        if file_creation_time is None: # check if content's file creation time exists
            if len(content.time_file_creation) > 0:
                file_creation_time = datetime.strptime(content.time_file_creation, self.time_format)
        #delete
        self.delete(file_id=file_id, auto_remove=False) # do not auto remove even if file ids is empty
        # insert, reuse file_id
        self.insert(file_id=file_id, file_full_path=file_full_path, group_id=group_id, type=type, type_desc=type_desc, file_creation_time=file_creation_time, file_desc=file_desc, chunks=chunks)
        return True, 'success'
    
    def update_description(self, doctype_id:int, desc:str):
        doctype:doctype_schema = doctype_schema(
            point_id=doctype_id, 
            collection_name=self.qcindex.qcdoctypeindex.collection_name,
            description=desc
        )
        self.qcindex.qcdoctypeindex.update_doctype(doctype=doctype)
            
    def update_fileinfo(self, fileinfo:file_schema):
        return self.qcindex.qcfileindex.update_file_index(content=fileinfo)

    def set_fileinfo_creation_time(self, fileinfo:file_schema, creation_time:datetime)->file_schema:
        return self.qcindex.qcfileindex.set_time_file_creation(fileinfo=fileinfo, file_creation_time=creation_time, time_format=self.time_format)

    #utilities
    def query(self, query:str, type='', top_k=3, threshold=0.6, only_recent_timestamp=True)->list[chunk_schema]:
        """
        given a query to be made into vectors, search similar vectors (score >= threshold)
        if there are, return relevant information
        inputs: vector, the  query vector to search similarity
                type, the type in the payload as a filter, if any
                top_k, the number of top search results
                threshold, the threshold score, any result higher will be returned
                only_recent_timestamp: if true, check the 'time_file_creation' for chunks in the same file group but different files
                    returns the chunks with latest timestamp, ignoring the previous timestamps
        output: a list of chunk_schema, containing raw text, file / group etc information
        """
        if len(query)==0:
            return []
        
        vector = self.model.encode(query, to_list=True)
        results = self.qcindex.qcchunkindex.query_index(vector=vector,type=type, top_k=top_k,threshold=threshold)
        outputs = results
         # now, if only_recent_timestamp is true, need further processing
        if only_recent_timestamp:
            dict_list = {} # dict holder of list for each group
            outputs = [] # reset
            for result in results: # loop each result, and make a map: group_id:list[content]
                file_id = result.file_id
                group_id = self.qcindex.qcfileindex.get_fileinfo_by_file_id(file_id=file_id).group_id#get group id by file_id
                item = dict_list[group_id] if group_id in dict_list.keys() else [] #if group_id in dict or not
                item.append(result)
                dict_list[group_id] = item
            #loop the dict
            for k, v in dict_list.items():
                if k == -1: #group_id is -1, no group
                    outputs.extend(v) # add all items
                else:# this chunk's file has group_id
                    group_id = k
                    file_index = self.qcindex.qcfileindex.get_fileinfo_by_group_id(group_id=group_id)# return file_schema sorted by timestamp
                    if len(file_index) == 0:# something wrong
                        error = f"qcVdbManager::query, inconsistency! In collection {self.collection_name}, group_id {group_id} does not exist in qcFileIndex"
                        logging.error(error)
                        raise ValueError(error)
                    latest_timestamp = file_index[0].time_file_creation_int
                    latest_file_id = file_index[0].file_id # already sorted

                    ######## if to keep the older version that contains unique texts that new version does not have ########
                    no_new = True # if the texts are all from older version, none from the latest version
                    for item in v: #loop each item in this group id
                        if latest_file_id == item.file_id:
                            # found one from the latest version
                            no_new = False
                            break
                    if no_new: # does not find any query results from latest version, keep the older version
                        results = v
                    ######## keep older version #########
                    else: # requery only the latest version
                        results = self.qcindex.qcchunkindex.query_index(vector=vector,type=type,file_id=latest_file_id, top_k=top_k,threshold=threshold)
                    outputs.extend(results)

            # now sort by score
            if len(outputs) > 0:
                outputs.sort(key=lambda x: x.score, reverse=True)
                outputs = outputs[:top_k] # pick top_k
        #end if only_recent_timestamp:
        return outputs
    
    def query_vdb(self, query, type='', top_k=3, threshold=0.6, only_recent_timestamp=True)->list[dict]:
        """
        given a query to be make into vectors, search similar vectors (score >= threshold)
        if there are, return relevant information
        inputs: vector, the  query vector to search similarity
                type, the type in the payload as a filter, if any
                top_k, the number of top search results
                threshold, the threshold score, any result higher will be returned, default use self.vdb_conf
                only_recent_timestamp: if true, check the 'time_file_creation' for chunks in the same file group but different files
                    returns the chunks with latest timestamp, ignoring the previous timestamps
        output: a list of dict, [{meta:'xxx', type:'xxx', source_from:'xxx', score:0.0}...]
        """
        output = []
        if len(query)>0:
            results = self.query(query=query,type=type, top_k=top_k, threshold=threshold,only_recent_timestamp=only_recent_timestamp)
            for result in results: #loop through chunk schema
                r = {
                    'meta': result.meta,
                    'type': result.type,
                    'source_from': result.source_from,
                    'score': result.score,
                }
                output.append(r)
        
        return output
    #
    #FAQ
    #
    def faq_add_one_faq(self,question:str, answer:str, org_id:int=-1, level_0:str='', level_1:str='')->bool:
        """
        question, answer
        org_id and (level_0, level_1) can NOT be at default value at the same time; either org_id is valid, or (level_0/1) are valid
        """
        if len(level_0)==0 or len(level_1)==0:
            # get org names
            level_0, level_1 = self.qcindex.qcfaqindex.get_org_names_by_id(org_id=org_id)
        
        return self.faq_add_batch_faqs(qa=[(question, answer)], level_0=level_0, level_1=level_1, org_id=org_id)

    def faq_add_batch_faqs(self, qa:list[tuple], level_0:str, level_1:str='default', org_id:int=-1)->bool:
        """
        insert FAQ in batch
        inputs: qa, a list of q,a, (question, answer)
            level_0/level_1, org names
            if org_id is provided, use it
        """
        qav = []
        for item in qa:# get qav vectors, making list of (question, answer, question_vector)
            q,a = item
            v = self.model.encode(inputs=q, to_list=True)
            qav.append((q,a,v))
        return self.qcindex.qcfaqindex.add_faqs_to_org(qav=qav, level_0=level_0, level_1=level_1, org_id=org_id)

    def faq_add_org_level_0(self, level_0:str)->tuple[int, str, str]:
        """
        add level_0 to org
        """
        return self.qcindex.qcfaqindex.add_org_to_vdb(level_0=level_0)
    
    def faq_add_org_level_1(self, level_0:str, level_1:str)->tuple[int, str, str]:
        """
        add level_1 to level_0 org
        returns [org_id, level_0, level_1]
        """
        return self.qcindex.qcfaqindex.add_org_to_vdb(level_0=level_0, level_1=level_1)

    def faq_delete_org_level_0(self, level_0:str)->bool:
        """
        delete level_0 org, along with all faqs under level_0/level_1s
        """
        return self.qcindex.qcfaqindex.delete_orgs_by_level_0(level_0=level_0)

    def faq_delete_org_level_1(self, org_id:int)->bool:
        """
        delete level_1 @ org_id
        """
        return self.qcindex.qcfaqindex.delete_org_by_level_1(org_id=org_id)

    def faq_delete_faq_by_ids(self, faq_ids:int|list[int])->bool:
        """
        delete faqs by ids
        faq_ids: int or list[int]
        """
        faq_ids = [faq_ids] if isinstance(faq_ids, int) else faq_ids
        return self.qcindex.qcfaqindex.delete_faqs_by_ids(ids=faq_ids)

    def faq_get_org_structure(self, level_0:str='')->dict:
        """
        retrieve org structure
        output: a dict of {level_0: [(id, team1,) (id, team2)...], level_0:[(id, team1), (id, team2)...]}
        """
        return self.qcindex.qcfaqindex.get_org_structure(level_0=level_0)
    
    def faq_get_org_faqs(self, level_0:str, level_1:str='default')->list:
        """
        get faqs of a level_0/level_1
        return list of id/q/a [(id, q, a), [(id, q, a)]]
        """
        return self.qcindex.qcfaqindex.get_org_faqs(level_0=level_0, level_1=level_1)

    def faq_get_org_faqs_by_id(self, org_id:int)->list:
        """
        get faqs of an org by org_id
        returns [(org_id, question, answer), (id, q, a),...]
        """
        return self.qcindex.qcfaqindex.get_org_faqs_by_id(org_id=org_id)

    def faq_update_faq_by_id(self, faq_id, answer:str)->bool:
        """
        update faq by faq_id
        """
        return self.qcindex.qcfaqindex.update_faq_by_id(point_id=faq_id, answer=answer)
    
    def faq_update_org_level0(self, org_id:int, level_0:str)->dict:
        """
        update level_0 org name
        inputs:
        org_id, level_0/'default' org_id
        level_0, new level_0 name
        outputs:
            dict, {'level_0':
                [
                    (org_id, level_1),
                    (org_id, level_1),
                    ...
                ]
            }
        """
        return self.qcindex.qcfaqindex.update_org_level_0(org_id=org_id, level_0=level_0)
    
    def faq_update_org_level_1(self, org_id:int, level_1:str)->bool:
        """
        update level_1 org name
        """
        return self.qcindex.qcfaqindex.update_org_level_1(org_id=org_id, level_1=level_1)

    ### utilities
    def faq_query(self, query:str, level_0:str='', level_1:str='', top:int=1, threshold=0.9)->list[dict]:
        """
        query to match faq's question
        inputs:
            query, the inquiry string
            level_0, level_1, if provided, search only in these orgs
            top: return top number of results
            threshold: the threshold for the search, default use self.faq_conf
        output:
            a list of dict: [{'question': xxx, 'answer':xxx, 'score': 0.x}]
        """
        output = []
        if len(query)>0:
            query_vector = self.model.encode(inputs=query, to_list=True)
            results = self.qcindex.qcfaqindex.query_index(query_vector=query_vector, level_0=level_0, level_1=level_1, top_k=top, threshold=threshold)
            for r in results: # faq_schema convert to dict
                result = {
                    'question': r.question,
                    'answer': r.answer,
                    'score': r.score,
                }
                output.append(result)
        
        return output