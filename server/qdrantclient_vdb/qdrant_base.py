# -*- coding: utf-8 -*-

"""
    base class to Qdrantclient functionalities, managing collections (create/update/delete etc)
    Author: awtestergit
"""

import logging
from datetime import datetime
from pydantic.dataclasses import dataclass
from dataclasses import field, asdict
from anbutils import utilities
from qdrant_client import QdrantClient
from qdrant_client.http import models

"""
- IDs (creating new unique ids for points, file, chunk)
- doctype (main used by LLM)
    - collection/type/description/file_ids
- file_index (hold chunks information for each file)
    - chunk (hold a chunk information, and raw meta text)
    - chunk
        ...
-file_index
    -chunk
    -chunk
    ...
"""

class qcBase():
    def __init__(self, collection_name:str, client:QdrantClient, vector_size:int) -> None:
        self.collection_name = collection_name
        self.client = client
        self.vector_size = vector_size

    def __initialize__(self):
        # check if collection exists
        response = self.client.get_collections()
        names = [desc.name for desc in response.collections]
        if self.collection_name not in names:#create
            self.client.create_collection(self.collection_name, vectors_config=models.VectorParams(size=self.vector_size,distance=models.Distance.COSINE))

class qcIdIndex(qcBase):
    SUFFIX = "id_index"
    def __init__(self, collection_name='id_max', client:QdrantClient=None) -> None:
        super().__init__(collection_name=collection_name, client=client, vector_size=1) # vector size 1
        ####point ids for this collection####
        self.point_id_id = 1 #id of the point_id
        self.group_id_id = 2
        self.file_id_id = 3 # the ids for file_index
        self.doctype_id = 4 # the ids for doctype
        self.point_id_vector = [float(self.point_id_id)] # vector of the point_id
        self.group_id_vector = [float(self.group_id_id)]
        self.file_id_vector = [float(self.file_id_id)]
        self.doctype_id_vector = [float(self.doctype_id)]
        self.point_id_name = 'point_id_max' #name
        self.group_id_name = 'group_id_max'
        self.file_id_name = 'file_id_max'
        self.doctype_id_name = 'doctype_id_max'
        #####################################
        
        super().__initialize__() # call base
        
    def __insert_id_value__(self, point_id, id_name, id_vector, id_value):
        point = models.PointStruct(
            id=point_id,
            payload={
                id_name: id_value,
            },
            vector=id_vector,
        )
        self.client.upsert(
            collection_name=self.collection_name,
            points= [point],
            )

    def __set_id_value__(self, point_id, id_name, id_vector, id_value):
        # get the payload
        point = self.client.retrieve(
            collection_name=self.collection_name,
            ids=[point_id]
        )
        if len(point) == 0: # not yet
            self.__insert_id_value__(point_id=point_id,id_name=id_name,id_vector=id_vector,id_value=id_value)
        else: # if find the point, update the payload
            self.client.set_payload(
                collection_name=self.collection_name,
                payload={
                    id_name: id_value,
                },
                points=[point_id]
            )

    def set_id_max(self, point_id_max = -1, group_id_max = -1, file_id_max=-1, doctype_id_max = -1):
        if point_id_max > -1:
            self.__set_id_value__(self.point_id_id, self.point_id_name, self.point_id_vector, point_id_max)
        if group_id_max > -1:
            self.__set_id_value__(self.group_id_id,self.group_id_name,self.group_id_vector,group_id_max)
        if file_id_max > -1:
            self.__set_id_value__(self.file_id_id,self.file_id_name,self.file_id_vector, file_id_max)
        if doctype_id_max > -1:
            self.__set_id_value__(self.doctype_id, self.doctype_id_name, self.doctype_id_vector, doctype_id_max)

    def __get_max_by_id__(self, point_id, id_name):
        """
        get the current max id being used
        """
        point = self.client.retrieve(
            collection_name=self.collection_name,
            ids=[point_id]
        )
        return point[0].payload[id_name] if len(point) > 0 else -1

    def get_point_id_max(self, auto_increment=True):
        """
        if auto_increment is false, get the current max point id being used
        if True, get the point id to be used by caller
        """
        current = self.__get_max_by_id__(self.point_id_id, self.point_id_name)# current max index being used
        if auto_increment:
            current += 1
            # set
            self.set_id_max(point_id_max=current)
        return current
    def get_batch_point_id_max(self, batch_size)->tuple[int, int]:
        """
        get the start and end point id based on batch_size
        outputs: start, end point ids to be used by caller
        """
        start = self.__get_max_by_id__(self.point_id_id, self.point_id_name) #current max index being used
        start += 1
        end = start + batch_size - 1# increment by batch
        self.set_id_max(point_id_max=end)
        return start, end

    def get_group_id_max(self, auto_increment=True):
        """
        if auto_increment is false, get the current group id being used
        if True, get the group id to be used by caller
        """
        current =  self.__get_max_by_id__(self.group_id_id, self.group_id_name)
        if auto_increment:
            current += 1
            self.set_id_max(group_id_max=current)
        return current
    
    def get_file_id_max(self, auto_increment=True):
        """
        if auto_increment is false, get the current max file id being used
        if True, get the file id to be used by caller
        """
        current = self.__get_max_by_id__(self.file_id_id, self.file_id_name)
        if auto_increment:
            current += 1
            self.set_id_max(file_id_max=current)
        return current

    def get_doctype_id_max(self, auto_increment=True):
        """
        if auto_increment is false, get the current max file id being used
        if True, get the file id to be used by caller
        """
        current = self.__get_max_by_id__(self.doctype_id, self.doctype_id_name)
        if auto_increment:
            current += 1
            self.set_id_max(doctype_id_max=current)
        return current

@dataclass
class doctype_schema():
    """
    type must be unique, so is the associated description
    """
    point_id:int = -1 #point id of this doctype
    collection_name: str='' # the collection name of doctype
    type: str='' # a short string, only one type per file: 1) as 'type' filter in point, and 2) used to create query_type_string function name
    description: str='' # description of the file content, used by LLM to understand what type of questions can be answered by this content
    file_ids:list = field(default_factory=lambda:[]) # a list of file ids belong to this doctype

class qcDocTypeIndex(qcBase):
    SUFFIX = "doctype_index"    
    def __init__(self, collection_name='doctype_index', qcidindex:qcIdIndex=None, client:QdrantClient=None) -> None:
        super().__init__(collection_name=collection_name, client=client, vector_size=1) #vector size 1, no need to search
        self.qcidindex = qcidindex
        super().__initialize__()

    def add_doctype(self, doctype:doctype_schema):
        # get a new id if necessary
        _id = doctype.point_id
        _id = _id if _id > -1 else self.qcidindex.get_doctype_id_max()
        doctype.point_id = _id
        doctype_vector = [float(_id)] #vector
        payload = asdict(doctype)
        point = models.PointStruct(
            id=_id,
            payload=payload,
            vector=doctype_vector,
        )
        self.client.upsert(
            collection_name=self.collection_name,
            points= [point],
            )

    def add_fileinfo_to_doctype(self, doctype_id, file_id, type, desc=''):
        # check existing type
        doctype:doctype_schema = self.get_doctype_by_id(point_id=doctype_id)
        if doctype is None: # not yet
            _id = self.qcidindex.get_doctype_id_max()
            doctype = doctype_schema(point_id=_id, collection_name=self.collection_name, type=type, description=desc, file_ids=[file_id])
            self.add_doctype(doctype=doctype)
        else: # exists
            doctype.file_ids.append(file_id) #append file id
            doctype.description = desc if len(desc) > 0 else doctype.description # update description if
            self.update_doctype(doctype)

    def delete_doctype(self, doctype_id):
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.PointIdsList(
                points=[doctype_id]
            ),
        )

    def update_doctype(self, doctype:doctype_schema):
        if doctype is None or doctype.point_id == -1:
            return
        doctype.collection_name = '' # make sure this is empty so as not to update it
        payload = asdict(doctype)
        for key in list(payload):
            item = payload[key]
            if (type(item) is list and len(item) == 0) or (type(item) is str and len(item) == 0): #check file id list, and strings
                payload.pop(key)
        # now set payload
        result = self.client.set_payload(
            collection_name=self.collection_name,
            payload=payload,
            points= [doctype.point_id]
        )

    def add_file_id_to_doctype_by_id(self, file_id, point_id):
        """
        add file id to an existing type
        if no such type exists, nothing will be done
        """
        if file_id == -1 or point_id == -1:
            return
        # get fileinfo_id by type
        # get doctype by type
        doctype:doctype_schema = self.get_doctype_by_id(point_id=point_id)
        if doctype is not None: # found it
            doctype.file_ids.append(file_id)
            self.update_doctype(doctype)

    def add_file_id_to_doctype_by_type(self, file_id, type):
        """
        add file id to an existing type
        if no such type exists, nothing will be done
        """
        if file_id == -1:
            return
        # get fileinfo_id by type
        # get doctype by type
        doctype:doctype_schema = self.get_doctype_by_type(type=type)
        if doctype is not None: # found it
            doctype.file_ids.append(file_id)
            self.update_doctype(doctype)
    
    def remove_file_id_from_doctype(self, file_id, point_id, auto_remove_doctype=True):
        """
        remove file id from an existing type
        auto_remove_doctype: if after removal, this type contains 0 file id (.file_ids []), then remove the doctype from collection
        """
        if file_id == -1:
            return
        # get doctype by type
        doctype:doctype_schema = self.get_doctype_by_id(point_id=point_id)
        if doctype is not None: # found it
            try:
                doctype.file_ids.remove(file_id) #throw error if file_id is not in the list
            except:
                error = f"file id '{file_id}' does not exist in collection '{self.collection_name}' - type '{type}'!"
                logging.error(error)
                raise ValueError(error)

            # now check the length of file_ids, if 0, delete this fileindex info
            if len(doctype.file_ids) == 0 and auto_remove_doctype:
                self.delete_doctype(doctype.point_id)
            else:
                self.update_doctype(doctype)

    def get_doctype_by_type(self, type):
        """
        get the doctype by type, if type does not exist yet, return None
        """
        doctype:doctype_schema = None
        # get doctype by type
        results, _ = self.client.scroll(#scroll returns (results, id) pair
            collection_name=self.collection_name,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(key='type', match=models.MatchValue(value=type))
                ]
            ),
            with_payload=True,
        )
        if len(results) > 0: # found it
            payload = results[0].payload
            doctype = utilities.dataclass_from_dict(doctype_schema, payload) # convert dict to dataclass
        
        return doctype
    
    def get_doctype_by_id(self, point_id:int):
        doctype:doctype_schema = None
        if point_id != -1:
            result = self.client.retrieve(
                collection_name = self.collection_name,
                ids = [point_id],
            )
            if len(result) > 0:
                payload = result[0].payload
                doctype = utilities.dataclass_from_dict(doctype_schema, payload)
        return doctype
    
    def get_doctype(self)->list[doctype_schema]:
        """
        get all doctype in the doctype index collection
        """
        # get records of file_id
        results, _ = self.client.scroll(#scroll returns (results, id) pair
            collection_name=self.collection_name,
            with_payload=True,
        )
        outputs = [utilities.dataclass_from_dict(doctype_schema, record.payload) for record in results] # convert to dataclass
        return outputs

@dataclass
class file_schema():
    doctype_id:int=-1 #the doctype id this file belongs to
    type: str='' # a short string, only one type per file: 1) as 'type' filter in point, and 2) used to create query_type_string function name    
    file_id:int=-1 # point id for this file in this schema collection
    point_id_start: int=-1 # start index of point id of this file's chunks
    point_id_end: int=-1 #end index of point id of this file's chunks
    group_id:int=-1 #group id of this file
    index_in_group: int=-1 # index of the file in the group
    time_add_to_vdb: str='' # the time of adding this file to vdb
    time_file_creation: str='' # for display: the creation of this file, to identify newer version of the file in the same group
    time_file_creation_int:int=-1 # for coding: the integer representation of time_file_creation, 20231130, (utilities.datetime_to_int())
    collection_name: str='' # the collection name
    source_from: str='' # the source string of this file
    file_desc: str = '' # description of this file, it is different from type description

class qcFileIndex(qcBase):
    SUFFIX = "file_index"    
    def __init__(self, collection_name='file_index', qcidindex:qcIdIndex=None, client:QdrantClient=None) -> None:
        super().__init__(collection_name=collection_name, client=client, vector_size=1) #vector size 1
        self.qcidindex = qcidindex
        self.__initialize__()
    
    def add_file_index(self, content:file_schema):
        # get a new file id
        file_id = content.file_id
        file_id = file_id if file_id > -1 else self.qcidindex.get_file_id_max()
        content.file_id = file_id        
        file_vector = [float(file_id)] #vector
        payload = asdict(content)
        point = models.PointStruct(
            id=file_id,
            payload=payload,
            vector=file_vector,
        )
        self.client.upsert(
            collection_name=self.collection_name,
            points= [point],
            )
    
    def update_file_index(self, content:file_schema):
        file_id = content.file_id
        if file_id == -1:
            return
        
        payload = asdict(content)
        #pop empty
        for key in list(payload): # use a list to hold keys
            item = payload[key]
            if (type(item) is int and item < 0) or (type(item) is str and item == ''):
                payload.pop(key)
        # now update
        self.client.set_payload(
            collection_name=self.collection_name,
            payload=payload,
            points=[file_id]
        )

    def delete_file_index(self, file_id):
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.PointIdsList(
                points=[file_id]
            ),
        )

    def get_fileinfo_by_file_id(self, file_id)->file_schema:
        point = self.client.retrieve(
            collection_name=self.collection_name,
            ids=[file_id]
        )
        payload = point[0].payload if len(point) > 0 else None
        content = utilities.dataclass_from_dict(file_schema, payload) if payload is not None else None
        return content
        
    def add_file_id_to_group(self, file_id)->tuple[int, int, bool]:
        """
        add group id by a file id. case being that a duplicate/relevant file is found, then group thest two together
        input: file_id
        output: group id, the current max index_in_group, is_new_group_id
        """
        #look up group id
        newly_added = False
        content = self.get_fileinfo_by_file_id(file_id)
        group_id, index_in_group = -1, -1
        if content.group_id == -1:# does not have a group yet
            group_id = self.qcidindex.get_group_id_max()
            index_in_group = 0
            # update content to vdb
            content.group_id = group_id
            content.index_in_group = index_in_group
            self.update_file_index(content=content)
            newly_added = True
        else:# has a group
            group_id = content.group_id
            # now count for all contents with this group id
            result = self.client.count(
                collection_name=self.collection_name,
                count_filter=models.Filter(
                    must=[
                        models.FieldCondition(key='group_id', match=models.MatchValue(value=group_id))
                    ]
                ),
                exact=True,
            )
            index_in_group = result.count
            #no need to update
        
        return [group_id, index_in_group, newly_added]
    
    def get_fileinfo_by_group_id(self, group_id:int)->list[file_schema]:
        """
        given a group_id, find the timestamps of files in the same group
        input: group_id
        output: a list of file_schema sorted by timestamps descending
        """
        if group_id == -1:
            return []
        
        # get records of group_id
        results, _ = self.client.scroll(#scroll returns (results, id) pair
            collection_name=self.collection_name,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(key='group_id', match=models.MatchValue(value=group_id))
                ]
            ),
            with_payload=True,
        )
        outputs = [record.payload for record in results]
        outputs.sort(key=lambda x: x['time_file_creation_int'], reverse=True)
        outputs = [utilities.dataclass_from_dict(file_schema, payload) for payload in outputs]
        return outputs
    
    def get_fileinfo(self)->list[file_schema]:
        """
        get all fileinfo in the file_index collection
        """
        # get records of file_id
        results, _ = self.client.scroll(#scroll returns (results, id) pair
            collection_name=self.collection_name,
            with_payload=True,
        )
        outputs = [utilities.dataclass_from_dict(file_schema, record.payload) for record in results] # convert to dataclass
        return outputs

    def set_time_file_creation(self, fileinfo:file_schema, file_creation_time:datetime, time_format:str)->file_schema:
        """
        set fileinfo both time_file_creation and time_file_creation_int
        inputs: fileinfo, creation time, time_format string
        """
        _time = file_creation_time.strftime(time_format) if file_creation_time is not None else ''
        fileinfo.time_file_creation = _time
        fileinfo.time_file_creation_int = utilities.datetime_to_int(file_creation_time)
        return fileinfo

@dataclass
class chunk_schema():
    chunk_id:int=-1 #chunk id of the chunk in this file
    file_id:int=-1 # point id for the file this chunk belongs to
    type: str='' # a short string, only one type per file: 1) as 'type' filter in point, and 2) used to create query_type_string function name
    meta: str=''# the raw texts of the chunk
    source_from: str='' # the source string, such as page number, of this file
    score:float=0. #the score for each query

class qcChunkIndex(qcBase):
    SUFFIX = "chunk_index"
    def __init__(self, collection_name='chunk_index', client:QdrantClient=None, vector_size=1024) -> None:
        super().__init__(collection_name=collection_name, client=client, vector_size=vector_size)
        self.__initialize__()

    def add_chunks_to_vdb(self, chunks:list[chunk_schema], point_ids:list, vectors:list)->bool:
        """ add chunks to content, and then upsert to vdb
        input: chunnks, the list of text chunks
            point_ids, the list of ids for each chunk in chunks
            vectors: the list of vectors for each chunk in chunks
        output: True or False
        """
        #get point ids
        size = len(chunks)
        if size == 0:
            return False
        # get vectors, payloads
        payloads = [asdict(payload) for payload in chunks]

        result = self.client.upsert(
            collection_name=self.collection_name,
            points=models.Batch(
                ids=point_ids,
                vectors=vectors,
                payloads=payloads,
            )
        )
    
    def update_chunks_by_ids(self, ids:list[int], content:chunk_schema):
        """
        1 content to many chunks operation
        update vdb chunks by ids, the values of the content will be applied to chunks of the ids
        input: ids, a list of point ids to be updated
            content, chunk_schema containing update info
        .meta should be empty, as it should not be updated by this call
        """
        if len(ids) == 0 or content is None:
            return
        
        content.meta = '' # make sure this is empty
        payload = asdict(content)
        for key in list(payload):
            item = payload[key]
            if (type(item) is int and item < 0) or (type(item) is str and item == ''):
                payload.pop(key)
        # now set payload
        result = self.client.set_payload(
            collection_name=self.collection_name,
            payload=payload,
            points= ids
        )

    def delete_chunks_by_ids(self, ids:list[int]):
        result = self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.PointIdsList(
                points=ids,
            ),
        )

    def delete_chunks_by_file_id(self, file_id):
        result = self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key='file_id',
                            match=models.MatchValue(
                                value=file_id
                            ),
                        ),
                    ],
                )
            ),
        )

    ######utilities########
    def check_similar_chunks(self, vectors:list, type='', top_k=3, threshold=0.8)->list[chunk_schema]:
        """
        given a list of query vectors, check if there are similar vectors exist (score >= threshold)
        if there are, return relevant information
        inputs: vectors, the list of query vectors to search similarity
                type, the type in the payload as a filter, if any
                top_k, the number of top search results for each chunk
                threshold, the threshold score, any result higher will be returned
        output: a list of chunk_schema, containing file / group etc information
        """
        outputs = []
        query_filter = None
        if len(type) > 0: # use type as filter
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key='type',
                        match=models.MatchValue(
                            value=type,
                        )
                    )
                ]
            )
        # search
        for vector in vectors:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=vector,
                query_filter=query_filter,
                limit=top_k,
                with_payload=True,
                score_threshold=threshold,
            )
            for result in results:
                payload = result.payload
                content:chunk_schema = utilities.dataclass_from_dict(chunk_schema, payload)
                content.score = result.score
                outputs.append(content)
        return outputs
    
    def query_index(self, vector, type='', file_id=-1, top_k=3, threshold=0.6)->list[chunk_schema]:
        """
        given a query vectors, search similar vectors (score >= threshold)
        if there are, return relevant information
        inputs: vector, the  query vector to search similarity
                type, the type in the payload as a filter, if any
                file_id, the file id in the payload as a filter, if any
                top_k, the number of top search results for each chunk
                threshold, the threshold score, any result higher will be returned
                only_recent_timestamp: if true, check the 'time_file_creation' for chunks in the same file group but different files
                    returns the chunks with latest timestamp, ignoring the previous timestamps
        output: a list of chunk_schema, containing file / group etc information
        """
        outputs = []
        must = [] # must filter
        if len(type) > 0: # use type as filter
            must=[
                models.FieldCondition(
                    key='type',
                    match=models.MatchValue(
                        value=type,
                    )
                )
            ]

        if file_id != -1: # add 
            # add must
            must.append(
                models.FieldCondition(
                    key='file_id',
                    match=models.MatchValue(
                        value=file_id,
                    )
                )
            )

        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=vector,
            query_filter=models.Filter(must=must),
            limit=top_k,
            with_payload=True,
            score_threshold=threshold,
        )
        # outputs
        outputs = []
        for result in results:
            content:chunk_schema = utilities.dataclass_from_dict(chunk_schema, result.payload)
            content.score = result.score # score
            outputs.append(content)

        return outputs


#
# FAQ
#
@dataclass
class faq_schema():
    # all int default -1, all str default ''
    id_max:int=-1 # id max for this type of faq, used to get faq_id_max or org_id_max; for payload_type 2, this is the faq_id
    payload_type:int=-1 # faq id, 0:faq ID, 1:org_id, 2:org payload, 3:faq payload, default -1    
    level_0:str="" # level 0 name, default ''
    level_1:str="" # level 1 name, default ''
    faq_org_id:int=-1 # the org_id who owns this faq, for payload type 2
    question:str='' # the question
    answer:str='' # the answer
    score:float=0.0 # score for query
#
# faq layout in vdb
#
"""
(0) - information for FAQs - to get/set FAQ point id
    point ID: 0, vector=[0~1024), schema(id_max = 1000, payload_type = point id)
(1) - information for orgs - to get/set org id
    poing ID: 1, vector=[1~1025), schema(id_max=2, payload_type = =point id)
(2~1000) - information for each org - to get/set org names etc, allows for max 998 orgs
    point ID: 2~1000, vector=[point_id,...), schema(id_max = point id, payload_type = 2, level_0/level_1 = names, faq_org_id=point_id)
(1001 ~) - information for each faq - all FAQs, point id starts from 1001.....
    point ID: 1001~, vector=vector of questions, schema(id_max=point_id, payload_type = 3, level_0/1=names, faq_org_id=org_id, question/answer=qa)
"""
class qcFaqIndex(qcBase):
    SUFFIX = "faq_index"
    def __init__(self, collection_name='faq_index', client:QdrantClient=None, vector_size=1024, total_faq_orgs=1000) -> None:
        """
        total_faq_orgs: the max number of organizations (including department, teams etc) to have FAQ
        In FAQ collection, IDs from 0~total_faq_orgs are reserved for faq_id @ id 0, org_id @ id 1, and payloads of level_0 and level_1 starting at between [2, total_faq_orgs)
            the faq entries (payloads) are started at index total_faq_orgs and beyond
        """
        super().__init__(collection_name=collection_name, client=client, vector_size=vector_size)
        self.__initialize__()
        self.vector_size = vector_size
        self.id_max_name = "id_max" # must match faq_schema's 'id_max'
        self.total_faq_orgs = total_faq_orgs
        self.faq_id=0 # id 0 is faq_id point stores the current max faq id
        self.faq_id_vector = [float(i+0) for i in range(vector_size)] # the vector
        self.org_id=1 # id 1 is org_id point stores the current max org id
        self.org_id_vector = [float(i+1) for i in range(vector_size)] # the vector
        self.org_payload_type = 2 # org payload type
        self.faq_payload_type = 3 # faq payload type

    def __add_faqs_to_vdb__(self, faqs:list[faq_schema], point_ids:list, vectors:list)->bool:
        """ add faqs to content, and then upsert to vdb
        input: faqs, the list of faqs
            point_ids, the list of ids for each faq
            vectors: the list of vectors for each faq
        output: True or False
        """
        #get point ids
        size = len(faqs)
        if size == 0:
            return False
        # get vectors, payloads
        payloads = [asdict(payload) for payload in faqs]

        result = self.client.upsert(
            collection_name=self.collection_name,
            points=models.Batch(
                ids=point_ids,
                vectors=vectors,
                payloads=payloads,
            )
        )
        return True

    def add_org_to_vdb(self, level_0:str, level_1:str='default')->tuple[int, str, str]:
        """
        input: level_0/level_1
        output: [org_id, level_0, level_1]
        """
        org_id = self.get_org_id(level_0=level_0, level_1=level_1, add_if_not_exist=True)
        return org_id, level_0, level_1

    def add_orgs_to_vdb(self, orgs:list[faq_schema], point_ids:list, vectors:list)->bool:
        return self.__add_faqs_to_vdb__(faqs=orgs, point_ids=point_ids, vectors=vectors)
    
    def add_faqs_to_org(self, qav:list, level_0:str, level_1:str='default', org_id:int=-1)->bool:
        """ add orgs to content, and then upsert to vdb
        input: qav, the list of faqs question, answer, question_vector
            level_0/level_1 org names
            org_id, the org_id, if provided
        output: True or False
        """
        if len(qav) == 0:
            return False
        
        org_id = org_id if org_id>0 else self.get_org_id(level_0=level_0, level_1=level_1) # create the org_id if not exists
        count = len(qav)
        start_id, end_id = self.get_batch_faq_id_max(batch_size=count) # [start, end]
        faqs = []
        point_ids = []
        vectors=[]
        current_id = start_id
        for item in qav:
            q,a,v = item
            faq = faq_schema()
            faq.payload_type = self.faq_payload_type #faq type
            faq.question = q
            faq.answer = a
            faq.faq_org_id = org_id
            faq.id_max = current_id # faq_id
            faq.level_0=level_0
            faq.level_1 = level_1
            faqs.append(faq)
            point_ids.append(current_id)
            vectors.append(v)
            current_id += 1
        
        assert end_id == current_id-1
        
        return self.__add_faqs_to_vdb__(faqs=faqs, point_ids=point_ids, vectors=vectors)
    
    def delete_faqs_by_ids(self, ids:list[int])->bool:
        result = self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.PointIdsList(
                points=ids,
            ),
        )
        return True

    def __delete_faqs_by_level_0__(self, level_0:str):
        result = self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition( # must operate at regular faq payload, i.e, payload_type==2
                            key='payload_type',
                            match=models.MatchValue(
                                value=self.faq_payload_type
                            ),
                        ),
                        models.FieldCondition(
                            key='level_0',
                            match=models.MatchValue(
                                value=level_0
                            ),
                        ),
                    ],
                )
            ),
        )

    def delete_faqs_by_level_1(self, level_0:str, level_1:str):
        result = self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition( # must operate at regular faq payload, i.e, payload_type==2
                            key='payload_type',
                            match=models.MatchValue(
                                value=self.faq_payload_type
                            ),
                        ),
                        models.FieldCondition(
                            key='level_0',
                            match=models.MatchValue(
                                value=level_0
                            ),
                        ),
                        models.FieldCondition(
                            key='level_1',
                            match=models.MatchValue(
                                value=level_1
                            ),
                        ),
                    ],
                )
            ),
        )

    def __delete_orgs_by_ids__(self, ids:list[int]):
        """
        delete the orgs by ids,
            first, delete all FAQs belongs to these orgs
            then, delete orgs
        """
        for org_id in ids:
            result = self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition( # must operate at regular faq payload, i.e, payload_type==faq payload type
                                key='payload_type',
                                match=models.MatchValue(
                                    value=self.faq_payload_type
                                ),
                            ),
                            models.FieldCondition(
                                key='faq_org_id',
                                match=models.MatchValue(
                                    value=org_id
                                ),
                            ),
                        ],
                    )
                ),
            )

        result = self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.PointIdsList(
                points=ids,
            ),
        )

    def delete_orgs_by_level_0(self, level_0:str)->bool:
        """
        1, delete all FAQs belong to this level_0
        2, delete this level_0
        """
        # 1
        self.__delete_faqs_by_level_0__(level_0=level_0)
        #2
        result = self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition( # now operate at org payload, i.e, payload_type==org payload type
                            key='payload_type',
                            match=models.MatchValue(
                                value=self.org_payload_type
                            ),
                        ),
                        models.FieldCondition(
                            key='level_0',
                            match=models.MatchValue(
                                value=level_0
                            ),
                        ),
                    ],
                )
            ),
        )
        return True

    def delete_org_by_level_1(self, org_id:int)->bool:
        self.__delete_orgs_by_ids__(ids=[org_id])
        return True
    
    def __delete_orgs_by_level_1__(self, level_0:str, level_1:str):
        """
        1, delete all FAQs belong to this level_1
        2, delete this level_1
        """
        #1
        self.delete_faqs_by_level_1(level_0=level_0, level_1=level_1)
        #2
        result = self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition( # now operate at org payload, i.e, payload_type== org payload type
                            key='payload_type',
                            match=models.MatchValue(
                                value=self.org_payload_type
                            ),
                        ),
                        models.FieldCondition(
                            key='level_0',
                            match=models.MatchValue(
                                value=level_0
                            ),
                        ),
                        models.FieldCondition(
                            key='level_1',
                            match=models.MatchValue(
                                value=level_1
                            ),
                        ),
                    ],
                )
            ),
        )

    def __get_org_vector_by_id__(self, org_id): # sudo vector
        return [float(org_id+1) for i in range(self.vector_size)] # the vector
    
    def __set_id_max__(self, point_id, id_name, id_max_to_set):
        # get the payload
        point = self.client.retrieve(
            collection_name=self.collection_name,
            ids=[point_id]
        )
        if len(point) == 0: # not yet, add
            p = faq_schema()
            p.payload_type = point_id # either 0, faq_id, or 1, org_id
            vec = None
            if point_id==self.faq_id:# faq_id
                p.id_max = self.total_faq_orgs + 1 if self.total_faq_orgs+1 > id_max_to_set else id_max_to_set # starts at 1000+1
                p.payload_type = self.faq_id #payload type
                vec = self.faq_id_vector
            elif point_id==self.org_id: #org_id
                p.id_max = self.org_id + 1 if self.org_id+1 > id_max_to_set else id_max_to_set # starts at 1 + 1
                p.payload_type = self.org_id# payload type
                vec = self.org_id_vector
            self.__add_faqs_to_vdb__(faqs=[p], point_ids=[point_id], vectors=[vec])
        else: # if find the point, update the payload
            self.client.set_payload(
                collection_name=self.collection_name,
                payload={
                    id_name: id_max_to_set,
                },
                points=[point_id]
            )
    def set_faq_id_max(self, id_max_to_set):
        return self.__set_id_max__(point_id=self.faq_id, id_name=self.id_max_name, id_max_to_set=id_max_to_set)

    def set_org_id_max(self, id_max_to_set):
        return self.__set_id_max__(point_id=self.org_id, id_name=self.id_max_name, id_max_to_set=id_max_to_set)

    def __get_max_by_id__(self, point_id:int, id_name:str):
        """
        get the current max id being used
        returns -1 if this id is not found
        """
        # if faq_id, it starts at total_faq_orgs+1 (1000+1), if org_id, it starts at self.org_id + 1
        default_id = -1
        point = self.client.retrieve(
            collection_name=self.collection_name,
            ids=[point_id]
        )
        return point[0].payload[id_name] if len(point) > 0 else default_id

    def get_faq_id_max(self, auto_increment=True):
        """
        if auto_increment is false, get the current max faq id being used
        if True, increase faq id by one and return the faq id to be used by caller
        """
        current = self.__get_max_by_id__(point_id=self.faq_id, id_name=self.id_max_name)# current max index being used
        # in case of empty faq index, set faq id starts at self.total_faq_orgs + 1
        if auto_increment:
            current = self.total_faq_orgs if current == -1 else current # if auto increment, start at 1000
            current += 1
            # set
            self.set_faq_id_max(id_max_to_set=current)
        return current

    def get_org_id_max(self, auto_increment=True):
        """
        if auto_increment is false, get the current max faq id being used
        if True, increase faq id by one and return the faq id to be used by caller
        """
        current = self.__get_max_by_id__(point_id=self.org_id, id_name=self.id_max_name)# current max index being used
        if auto_increment:
            current = self.org_id if current == -1 else current # if auto increment, starts at 1
            current += 1
            # set
            self.set_org_id_max(id_max_to_set=current)
        return current

    def __get_batch_id_max__(self, batch_size, point_id, id_name)->tuple[int, int]:
        """
        get the start and end point id based on batch_size
        outputs: start, end point ids to be used by caller, [start, end]
        """
        start = self.__get_max_by_id__(point_id=point_id, id_name=id_name) #current max index being used
        start += 1
        end = start + batch_size - 1# increment by batch
        self.__set_id_max__(point_id=point_id,id_name=id_name, id_max_to_set=end)

        return start, end

    def get_batch_faq_id_max(self, batch_size)->tuple[int, int]:
        start, end = self.__get_batch_id_max__(batch_size=batch_size, point_id=self.faq_id, id_name=self.id_max_name)
        # faq id starts at total_faq_orgs, 1000, if batch id above returns start == 0, in the case of empty faq index, set it here
        if start <= self.total_faq_orgs:
            start += self.total_faq_orgs + 1
            end += self.total_faq_orgs + 1
        return start, end
    
    def get_batch_org_id_max(self, batch_size)->tuple[int, int]:
        return self.__get_batch_id_max__(batch_size=batch_size, point_id=self.org_id, id_name=self.id_max_name)

    def get_org_id(self, level_0:str, level_1:str='default', add_if_not_exist=True)->int:
        """
        given org, get the org_id
        level_0/level_1, org names
        add_if_not_exist, if True, will add this org to vdb if org is not in vdb
        output:
            org_id, org_id or -1
        """
        org_id = -1
        count_filter=models.Filter(
            must=[
                models.FieldCondition( # now operate at org, i.e, payload_type==org payload
                    key='payload_type',
                    match=models.MatchValue(
                        value=self.org_payload_type
                    ),
                ),
                models.FieldCondition(
                    key='level_0',
                    match=models.MatchValue(
                        value=level_0
                    ),
                ),
                models.FieldCondition(
                    key='level_1',
                    match=models.MatchValue(
                        value=level_1
                    ),
                ),
            ],
        )
        # retrieve org_id
        # scroll returns (points, offset for next scroll request)
        points, _ = self.client.scroll(collection_name=self.collection_name, scroll_filter=count_filter, with_payload=True, with_vectors=False)
        if points:
            point = points[0]
            payload = point.payload #payload dict
            content:faq_schema = utilities.dataclass_from_dict(faq_schema, payload)
            org_id = content.id_max #id max is the org id
        
        # here, check if auto add
        if org_id == -1 and add_if_not_exist:
            org_id = self.get_org_id_max() # create org_id
            vec = self.__get_org_vector_by_id__(org_id=org_id)
            org = faq_schema()
            org.payload_type = self.org_payload_type #org payload type
            org.id_max = org_id # id max is the org_id
            org.level_0 = level_0
            org.level_1 = level_1
            self.add_orgs_to_vdb(orgs=[org], point_ids=[org_id], vectors=[vec])
        
        return org_id
    
    def get_org_names_by_id(self, org_id:int)->tuple[str, str]:
        """
        get level_0/level_1 names by org_id
        """
        level_0, level_1 = '',''
        points = self.client.retrieve(
            collection_name = self.collection_name,
            ids = [org_id],
            with_payload = True,
        )
        if points: # if not empty
            p = points[0].payload
            p_schema:faq_schema = utilities.dataclass_from_dict(faq_schema, p)
            level_0 = p_schema.level_0
            level_1 = p_schema.level_1
        
        return level_0, level_1
    
    def get_org_structure(self, level_0:str='')->dict:
        """
        level_0, if given, return all level_1s under level_0;
            otherwise, return all level_0/level_1s
        return org structure in a dict of lists: {level_0: [(id, team1,) (id, team2)...], level_0:[(id, team1), (id, team2)...]}
        """
        result = {}
        must=[
            models.FieldCondition( # now operate at org, i.e, payload_type==org payload type
                key='payload_type',
                match=models.MatchValue(
                    value=self.org_payload_type
                ),
            ),
        ]
        if len(level_0)>0:
            must.append(
                models.FieldCondition(
                    key='level_0',
                    match=models.MatchValue(
                        value=level_0
                        ),
                )
            )

        count_filter=models.Filter(must=must)
        count = self.client.count(collection_name=self.collection_name, count_filter=count_filter, exact=True).count
        points = []
        if count: #
            # retrieve points
            # scroll returns (points, offset for next scroll request)
            points, _ = self.client.scroll(collection_name=self.collection_name, scroll_filter=count_filter, limit=count, with_payload=True, with_vectors=False)
            for point in points:
                payload = point.payload #payload dict
                content:faq_schema = utilities.dataclass_from_dict(faq_schema, payload)
                level_0 = content.level_0
                level_1 = content.level_1
                org_id = content.id_max
                if level_0 in result.keys():
                    result[level_0].append((org_id, level_1))
                else:
                    result[level_0] = [(org_id, level_1)]

        return result
    
    def get_org_faqs(self, level_0:str, level_1:str='default', org_id=-1)->list:
        """
        get level_0/level_1 faq,
            default level_1 is 'default'
        output: list of id/q/a [(id, q, a), [(id, q, a)]]
        """
        result = []
        if org_id == -1:
            org_id = self.get_org_id(level_0=level_0, level_1=level_1, add_if_not_exist=False)
        
        if org_id > 0: #found the id
            result = self.get_org_faqs_by_id(org_id=org_id)

        return result

    def get_org_faqs_by_id(self, org_id:int)->list:
        """
        get an org faqs by org ID
        input: org id
        output: list of point_id/q/a [(faq_id, q, a), [(faq_id, q, a)]] where faq_id is id_max
        """
        result = []
        count_filter=models.Filter(
            must=[
                models.FieldCondition( # now operate at faq, i.e, payload_type== faq payload type
                    key='payload_type',
                    match=models.MatchValue(
                        value=self.faq_payload_type
                    ),
                ),
                models.FieldCondition(
                    key='faq_org_id',
                    match=models.MatchValue(
                        value=org_id
                    ),
                ),
            ],
        )

        count = self.client.count(collection_name=self.collection_name, count_filter=count_filter, exact=True).count
        points = []
        if count: #
            # scroll returns (points, offset for next scroll request)
            points, _ = self.client.scroll(collection_name=self.collection_name, scroll_filter=count_filter, limit=count, with_payload=True, with_vectors=False)
        for point in points: #
            payload = point.payload #payload dict
            content:faq_schema = utilities.dataclass_from_dict(faq_schema, payload)
            result.append((content.id_max, content.question, content.answer))

        return result    
    
    def update_faq_by_id(self, point_id:int, answer:str)->bool:
        """
        update faq by point id
        """
        faq = faq_schema()
        #faq.question = question # can NOT change question, as it is associated with question vector
        faq.answer = answer
        result = self.__update_faq_by_id__(point_id=point_id, content=faq)
        return result
    
    def __update_faq_by_id__(self, point_id:int|list, content:faq_schema)->bool:
        """
        update vdb faqs by point_id, the values of the content will be applied to faqs of the id
        input: id, a point id or a list of ids to be updated
            content, faq_schema containing update info
        return True
        """
        output = False
        if content is None:
            return output
        
        payload = asdict(content)
        for key in list(payload):
            item = payload[key]
            if (type(item) is int and item < 0) or (type(item) is str and item == ''):
                payload.pop(key)
        if payload: #if not empty
            # now set payload
            ids = [point_id] if isinstance(point_id, int) else point_id # if a list or not
            result = self.client.set_payload(
                collection_name=self.collection_name,
                payload=payload,
                points= ids
            )
            output = True

        return output

    def update_org_level_0(self, org_id:int, level_0:str)->dict:
        """
        update level_0 name by id
        input: org_id, the org id of level_0/'default'
        output: dict {level_0:[(org_id, level_1), (org_id, level_1),...]}
        """
        orgs = {}
        result = self.__update_org_level__(org_id=org_id, level_0=level_0)
        if result:
            orgs = self.get_org_structure(level_0=level_0)
        return orgs

    def update_org_level_1(self, org_id:int, level_1:str)->bool:
        """
        update org names by org_id
        input: id, a point id to be updated
            level_0/level_1, names to be updated
        """
        return self.__update_org_level__(org_id=org_id, level_1=level_1)
    
    def __update_org_level__(self, org_id:int, level_0:str='', level_1:str='')->bool:

        # uupdate level_1 at org
        content = faq_schema()
        content.level_1 = level_1
        content.level_0 = level_0
        result = self.__update_faq_by_id__(point_id=org_id, content=content)

        # update all faqs with this org_id
        if result:
            payload_filter=models.Filter(
                must=[
                    models.FieldCondition( # now operate at faq, i.e, payload_type== faq payload type
                        key='payload_type',
                        match=models.MatchValue(
                            value=self.faq_payload_type
                        ),
                    ),
                    models.FieldCondition(
                        key='faq_org_id',
                        match=models.MatchValue(
                            value=org_id
                        ),
                    ),
                ],
            )
            # update
            payload = asdict(content)
            for key in list(payload):
                item = payload[key]
                if (type(item) is int and item < 0) or (type(item) is str and item == ''):
                    payload.pop(key)
            self.client.set_payload(collection_name=self.collection_name,
                                    points = payload_filter,
                                    payload=payload,
                                    )
        return result
    
    ######utilities########
    
    def query_index(self, query_vector, level_0='', level_1='', top_k=3, threshold=0.9)->list[faq_schema]:
        """
        given a query vectors, search similar vectors (score >= threshold)
        if there are, return relevant information
        inputs: vector, the  query vector to search similarity
                level_0, in the payload as a filter, if any
                level_1, in the payload as a filter, if any
                top_k, the number of top search results for each chunk
                threshold, the threshold score, any result higher will be returned
        output: a list of faq_schema
        """
        outputs = []
        must = [] # must filter
        if len(level_0) > 0: # use level_0 as filter
            must=[
                models.FieldCondition(
                    key='level_0',
                    match=models.MatchValue(
                        value=level_0,
                    )
                )
            ]

        if len(level_0)>0 and len(level_1) > 0: # use level_1 as filter, only if level_0
            must.append([
                models.FieldCondition(
                    key='level_1',
                    match=models.MatchValue(
                        value=level_1,
                    )
                )
            ])

        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=models.Filter(must=must),
            limit=top_k,
            with_payload=True,
            score_threshold=threshold,
        )
        # outputs
        outputs = []
        for result in results:
            content:faq_schema = utilities.dataclass_from_dict(faq_schema, result.payload)
            content.score = result.score # score
            outputs.append(content)

        return outputs