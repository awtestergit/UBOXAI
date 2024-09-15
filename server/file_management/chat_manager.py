# -*- coding: utf-8 -*-

"""
    chat manager - handles user's chat history
    Author: awtestergit
"""
import logging
import os
import shutil
import sqlite3
from threading import Lock

class chat_history_mgr():
    """
    """
    def __init__(self, db_path:str, db_name:str) -> None:
        """
        db_path: sqlite db path
        """
        self.db_path = db_path
        self.db_name = os.path.join(db_path, db_name) # join to get the full path
        self.db = None
        self.table_name = 'uid_chat_history'
        self.uuid_column = 'uuid'
        self.query_column = 'query'
        self.answer_column = 'answer'
        self.time_column = 'timestamp'
        self.sqlite_lock = Lock() # the  event for multi-threading
        self.__initialize__()

    def __initialize__(self):
        # table structure
        if not os.path.exists(self.db_path): # check db path
            os.makedirs(self.db_path)
        self.db = self.db if self.db else sqlite3.connect(self.db_name, check_same_thread=False)
        cur = self.db.cursor()
        # check table exists
        select_table = f"SELECT name from sqlite_master WHERE type='table' AND name='{self.table_name}'"
        cur.execute(select_table)
        result = cur.fetchone()
        if not result:
            create_table = f"CREATE TABLE {self.table_name} ({self.uuid_column}, {self.query_column} text, {self.answer_column} text, {self.time_column} TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
            cur.execute(create_table)
            self.db.commit()

    def get_db(self):
        self.db = self.db if self.db else sqlite3.connect(self.db_name, check_same_thread=False)
        return self.db
    
    def close_db(self):
        if self.db:
            self.db.close()
    
    def purge_all(self, close_db=True):
        # cleanse db
        drop_table = f"DROP TABLE IF EXISTS {self.table_name}"
        cur = self.db.cursor()
        cur.execute(drop_table)
        self.db.commit()
        if close_db:
            self.db.close()

    def add_chat(self, uuid:str='', query:str='', answer:str=''):
        """
        add chat to uuid
        """
        if len(uuid)==0 or len(query)==0: # allows answer is empty
            return
        
        if not self.db:
            raise ValueError("chat history manager: chat history db is not connected.")

        try:
            self.sqlite_lock.acquire()
            cur = self.db.cursor()
            insert_table = f"""INSERT INTO {self.table_name} ({self.uuid_column}, {self.query_column}, {self.answer_column}) VALUES ('{uuid}', "{query}", "{answer}")"""

            #print(insert_table)
            logging.debug(insert_table)

            cur.execute(insert_table) # save to db
            self.db.commit()
        finally:
            self.sqlite_lock.release()

    def get_chat_history(self, uuid:str, recent=-1)->list:
        """
        retrieve recent chat histories
        input: uid, 
            recent, if -1, get all
        output: [(query, answer)...]
        """
        # query table
        select_table = f"SELECT * FROM {self.table_name} WHERE {self.uuid_column}='{uuid}' ORDER BY {self.time_column} DESC"
        if recent > 0:
            select_table = f"SELECT * FROM {self.table_name} WHERE {self.uuid_column}='{uuid}' ORDER BY {self.time_column} DESC LIMIT {recent}"
        cur = self.db.cursor()
        cur.execute(select_table)
        rows = cur.fetchall()
        # rows is a list [(uid, query, answer, time),...]
        outputs = []
        for row in rows:
            query = row[1]
            answer = row[2]
            time = row[3]
            outputs.append((query, answer,time))
        return outputs
    
    def delete_chat_history(self, uuid:str, keep_recent=-1):
        """
        delete chat history, keep 'keep_recent' chat histories, e.g, keep recent 100
        keep_recent: if -1, delete all
        """
        delete_table = f"DELETE FROM {self.table_name} WHERE {self.uuid_column}='{uuid}'"        
        if keep_recent > 0:
            delete_table = f"DELETE FROM {self.table_name} WHERE {self.uuid_column}='{uuid}' AND ROWID NOT IN (SELECT ROWID FROM {self.table_name} WHERE {self.uuid_column}='{uuid}' ORDER BY {self.time_column} DESC LIMIT {keep_recent})"

        #print(delete_table)
        logging.debug(delete_table)

        try:
            self.sqlite_lock.acquire()
            cur = self.db.cursor()
            # delete from table
            cur.execute(delete_table)
            self.db.commit()
        finally:
            self.sqlite_lock.release()

    def __get_all_from_db__(self):
        """"""
        # query table
        select_table = f"SELECT * FROM {self.table_name}"
        cur = self.db.cursor()
        cur.execute(select_table)
        rows = cur.fetchall()
        output = ''
        for row in rows:
            for item in row:
                output += item
        return output
