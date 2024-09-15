# -*- coding: utf-8 -*-
"""
    Qdrantclient vector db manager, for users to manage collections (create/update/delete etc)
    Author: awtestergit
"""

import logging
import pandas as pd
from dataclasses import asdict
from datetime import datetime
from dateutil.relativedelta import relativedelta
from qdrantclient_vdb.qdrant_manager import qcVdbManager
from qdrantclient_vdb.qdrant_base import file_schema

class VectorDBManager():
    def __init__(self, manager:qcVdbManager) -> None:
        self.manager = manager
        self.types:list[str] = [] # the file types and description [type, desc]
        self.descs:list[str] = []
        self.time_format = manager.time_format

    def add_type_desc(self, type, desc)->bool:
        #check type
        doctype = self.manager.get_doctype_by_type(type)
        result = False
        if doctype is None: # add
            self.manager.add_doctype(type=type,description=desc)
            result = True
        return result

    def check_duplicate(self, chunks:list[str], type:str='', check_all_types=True, num_samples=3, threshold=0.95)->(bool, list[str, str, int]):
        """
        given text inputs, check if these texts exist in the vector db
        if check duplicate, check it first
        type: the type
        check_all_types: if True, check all vectors, regardless of type. default True
        num_samples: how many samples of chunks to used to check duplicate
        threshold: the threshold, if greater than threshold, then it is believed to be duplicate
        chunks: list[raw test]
        output: bool, list[similar text in vdb, source of this text, file_id of the chunk]
        """
        #check all types
        is_dup, dups = self.manager.check_duplicate(chunks=chunks,type=type, check_all_types=check_all_types, num_samples_to_check_duplicate=num_samples, threshold=threshold)
        if is_dup: # duplicate
            dup_list = [[dup.meta, dup.source_from, dup.file_id] for dup in dups]
            return True, dup_list
        else:
            return False, []

    def delete_doctype_by_id(self, doctype_id):
        self.manager.delete_all_by_doctype(doctype_id=doctype_id)

    def delete_fileinfo_by_id(self, file_id):
        self.manager.delete(file_id=file_id)

    def get_doctype_by_id(self, doctype_id):
        doctype = self.manager.get_doctype_by_id(doctype_id=doctype_id)
        return doctype

    def get_doctype_by_type(self, _type):
        doctype = self.manager.get_doctype_by_type(_type)
        return doctype

    def get_fileinfo_by_id(self, file_id):
        return self.manager.get_fileinfo_by_id(file_id=file_id)

    def insert(self, type:str, type_desc:str, file_full_path:str='', group_id=-1, index_in_group=-1, file_creation_time:datetime=None, file_desc:str='', chunks:list[str, str]=[], check_duplicate=True, num_samples=3, threshold=0.95)->tuple[bool, list[str, str,int]]:
        """
        insert a new file
        if check duplicate, check it first
        num_samples: how many samples of chunks to used to check duplicate
        threshold: the threshold, if greater than threshold, then it is believed to be duplicate
        chunks: list[raw test, source of this raw test]
        output: bool, list[similar text in vdb, source of this text, file_id]
        """
        # duplicate
        if check_duplicate:
            is_dup, dups = self.check_duplicate(chunks=chunks[0], type=type, num_samples=num_samples,threshold=threshold)
            if is_dup: # duplicate
                return is_dup, dups
        # else, insert
        result, _ = self.manager.insert(type=type, type_desc=type_desc, file_full_path=file_full_path,group_id=group_id, index_in_group=index_in_group, file_creation_time=file_creation_time, file_desc=file_desc, chunks=chunks)
        return result, []

    def insert_duplicate(self, orig_file_id, file_full_path:str, file_creation_time:datetime, file_desc:str='', chunks:list[str, str]=[], adjust_file_time_in_group=True)->bool:
        """
        known duplicated files exist, insert a new file into vector db
        orig_file_id: the existing file_id that new file (chunks) is similar with
        file_full_path: new file path
        file_creation_time: the file creation time of this file
        adjust_file_time_in_group: if True, will check file_creation_file for each file in the group, if not set, then set it to be older than this file 'file_creation_time'
        chunks: list[raw test, source of this raw test]
        output: bool
        """
        assert file_creation_time is not None # cannot be none
        type = ''
        desc = ''
        # first, set group id to the existing file id, which returns the group id, current max index_in_group used
        group_id, index_in_group, _ = self.manager.add_file_id_to_group(file_id=orig_file_id)
        if adjust_file_time_in_group: # if make previous file time older
            # get file info in the group, and prepare to set file_creation_time
            fileinfos = self.manager.get_fileinfo_by_group(group_id=group_id)
            for fileinfo in fileinfos:
                if fileinfo.time_file_creation is None or len(fileinfo.time_file_creation) == 0:
                    delta = fileinfo.index_in_group - 100000 # 100,000 seconds, longer than one day 86,400 seconds. the smaller index, the older
                    file_time = file_creation_time + relativedelta(seconds=delta)
                    fileinfo = self.manager.set_fileinfo_creation_time(fileinfo=fileinfo, creation_time=file_time)
                    self.manager.update_fileinfo(fileinfo=fileinfo) # update the existing file info
        # this file's index_in_group is one + the current max index
        index_in_group += 1
        orig_file = self.manager.get_fileinfo_by_id(file_id=orig_file_id)
        doctype_id = orig_file.doctype_id
        doctype = self.manager.get_doctype_by_id(doctype_id=doctype_id)
        type = doctype.type
        desc = doctype.description
        # insert new file info
        result, _ = self.insert(type=type, type_desc=desc, file_full_path=file_full_path, group_id=group_id, index_in_group=index_in_group, file_creation_time=file_creation_time, file_desc=file_desc, chunks=chunks,check_duplicate=False)
        return result
    
    def read_doctype(self)->pd.DataFrame:
        # read doctype
        doctypes = self.manager.get_doctype()
        df = [asdict(doc) for doc in doctypes]
        df = pd.DataFrame(df) #dataframe
        self.types = [doc.type for doc in doctypes] # read type and desc
        self.descs = [doc.description for doc in doctypes] # read type and desc
        return df

    def read_fileinfo(self)->pd.DataFrame:
        #read files
        files = self.manager.get_fileinfo()
        df = [asdict(file) for file in files]
        df = pd.DataFrame(df)
        return df

    def update_doctype_desc(self, doctype_id, desc:str):
        # update doctype description by id
        self.manager.update_description(doctype_id=doctype_id, desc=desc)

    def update_fileinfo(self, file_id, file_full_path:str='', group_id=-1, file_creation_time:datetime=None, file_desc:str='', chunks:list[str, str]=[])->bool:
        # if chunks is [], then just update file_schema info, else
        # update file info (delete then insert)
        result = True
        if len(chunks) == 0:
            # without creation time
            fileinfo:file_schema = file_schema(file_id=file_id, source_from=file_full_path, group_id=group_id, file_desc=file_desc)
            # now add
            fileinfo = self.manager.set_fileinfo_creation_time(fileinfo, file_creation_time)
            self.manager.update_fileinfo(fileinfo=fileinfo)
        else:
            result, _ = self.manager.update(file_id=file_id, file_full_path=file_full_path, group_id=group_id, file_creation_time=file_creation_time, file_desc=file_desc, chunks=chunks)
        return result

    #
    # FAQ
    #

    def faq_add_qa(self, level_0:str, level_1:str, question:str, answer:str, org_id:int=-1)->bool:
        return self.manager.faq_add_one_faq(question=question, answer=answer, level_0=level_0, level_1=level_1)
    
    def faq_add_qa_batch(self, df:pd.DataFrame):
        """
        df: must contain these 4 columns: Question, Answer, Department, Team
        """
        grouped_dept_team = df.groupby(['Department', 'Team'])
        for (dept, team), qas in grouped_dept_team:
            qa_list = []
            for _, row in qas.iterrows():
                qa_list.append([row['Question'], row['Answer']])
            self.manager.faq_add_batch_faqs(qa_list, level_0=dept, level_1=team)

    def faq_get_all(self)->pd.DataFrame:
        """
        return a dataframe: Question, Answer, Department, Team
        """
        # {level_0: [(id, team1,) (id, team2)...], level_0:[(id, team1), (id, team2)...]}
        df = pd.DataFrame(columns=['ID', 'Question', 'Answer', 'Department', 'Team'])
        org_dict = self.manager.faq_get_org_structure()
        for dept, id_teams in org_dict.items():
            for _, team in id_teams:
                id_qas = self.manager.faq_get_org_faqs(dept, team)
                # [(id, q,a), ...]
                for _id, q, a in id_qas:
                    qa = pd.DataFrame.from_dict({'ID':_id, 'Question':[q], 'Answer':[a], 'Department':[dept], 'Team':[team]})
                    df = pd.concat([df, qa], ignore_index=True)
        return df
    
    def faq_get_orgs(self)->dict:
        """
        {level_0: [(id, team1,) (id, team2)...], level_0:[(id, team1), (id, team2)...]}
        """
        return self.manager.faq_get_org_structure()

    def faq_delete_by_id(self, _id):
        return self.manager.faq_delete_faq_by_ids(_id)
    
    def faq_delete_by_level0(self, level_0):
        return self.manager.faq_delete_org_level_0(level_0)

    def faq_get_org_faqs(self, level_0:str, level_1:str):
        """
        return list of id/q/a [(id, q, a), [(id, q, a)]]
        """
        return self.manager.faq_get_org_faqs(level_0, level_1)