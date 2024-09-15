# -*- coding: utf-8 -*-

"""
    file manager - handles user's upload/download, as well as cleanup after request
    Author: awtestergit
"""
import logging
import os
import shutil
import sqlite3
from threading import Lock

class server_file_item():
    def __init__(self, file_obj, file_path:str) -> None:
        """
        file_obj: a class must have save() method
        """
        self.file_obj = file_obj
        self.file_path = file_path

class server_file_mgr():
    """
    """
    def __init__(self, db_path:str, db_name:str, file_path:str) -> None:
        """
        db_path: sqlite db path
        file_path: local file path to save all files
        """
        self.db_path = db_path
        self.db_name = os.path.join(db_path, db_name) # join to get the full path
        self.file_path = file_path
        self.db = None
        self.table_name = 'uuid_files'
        self.uuid_column = 'uuid'
        self.path_column = 'path'
        self.type_column = 'type'
        self.sqlite_lock = Lock() # the sqlite event for multithreading
        self.__initialize__()

    def __initialize__(self):
        # table structure
        # uuid | path | type, where type is 'auto' or 'manual'; if manual, need to delete these files manually
        if not os.path.exists(self.db_path): # check db path
            os.makedirs(self.db_path)
        self.db = self.db if self.db else sqlite3.connect(self.db_name, check_same_thread=False)
        cur = self.db.cursor()
        # close all first, leave db open
        self.close_all(close_db=False)
        # check table exists
        select_table = f"SELECT name from sqlite_master WHERE type='table' AND name='{self.table_name}'"
        cur.execute(select_table)
        result = cur.fetchone()
        if not result:
            create_table = f"CREATE TABLE {self.table_name} ({self.uuid_column} text, {self.path_column} text, {self.type_column} text)"
            cur.execute(create_table)
            self.db.commit()


    def get_db(self):
        self.db = self.db if self.db else sqlite3.connect(self.db_name, check_same_thread=False)
        return self.db
    
    def close_db(self):
        if self.db:
            self.db.close()
    
    def close_all(self, close_db=True):
        # remove folder
        if os.path.exists(self.file_path):
            shutil.rmtree(self.file_path)
        # cleanse db
        drop_table = f"DROP TABLE IF EXISTS {self.table_name}"
        cur = self.db.cursor()
        cur.execute(drop_table)
        self.db.commit()
        if close_db:
            self.db.close()

    def construct_file_folder(self, uuid:str, create_if_not_exist=True)->str:
        """
            create root_path/uuid/file_path
        """
        # create uuid folder if not exists
        folder = os.path.join(self.file_path, uuid)
        if not os.path.exists(folder):
            if create_if_not_exist:
                os.makedirs(folder)
            else: # set empty
                folder = '' # empty
        return folder

    def track_files_only(self, uuid:str, filenames:list[str]):
        """
        use mgr to track files along with other files - when client disconnects, all these files will be deleted from server
        """
        # save files to local dir and save paths to db
        try:
            self.sqlite_lock.acquire()
            cur = self.db.cursor()
            for file_path in filenames:
                # manual type
                insert_table = f"INSERT INTO {self.table_name} ({self.uuid_column}, {self.path_column}, {self.type_column}) VALUES ('{uuid}', '{file_path}', 'manual')"
                
                #print(insert_table)
                logging.debug(insert_table)

                cur.execute(insert_table) # save to db
            self.db.commit()
        finally:
            self.sqlite_lock.release()

    def track_file_add_path_to_db(self, uuid:str, file_items:list[server_file_item], save=True)->list[str]:
        """
        track/save file_path to uuid, if save is True, save the file
        output:
            filenames saved
        """
        if not uuid or len(uuid) == 0:
            raise ValueError("server file manager: save file uuid is empty.")
        
        if not self.db:
            raise ValueError("server file manager: save_file db is not connected.")

        output_filenames = []
        folder = self.construct_file_folder(uuid=uuid) # construct uuid/file

        # save files to local dir and save paths to db
        try:
            self.sqlite_lock.acquire()
            cur = self.db.cursor()
            for item in file_items:
                file_obj = item.file_obj
                file_path = item.file_path
                file_path = os.path.join(folder, file_path) # save path
                if save:
                    file_obj.save(file_path) # save to folder
                    output_filenames.append(file_path)
                    insert_table = f"INSERT INTO {self.table_name} ({self.uuid_column}, {self.path_column}, {self.type_column}) VALUES ('{uuid}', '{file_path}', 'auto')"
                else: # manual type
                    output_filenames.append(file_path)
                    insert_table = f"INSERT INTO {self.table_name} ({self.uuid_column}, {self.path_column}, {self.type_column}) VALUES ('{uuid}', '{file_path}', 'manual')"

                #print(insert_table)
                logging.debug(insert_table)
                
                cur.execute(insert_table) # save to db
            self.db.commit()
        finally:
            self.sqlite_lock.release()

        return output_filenames
    
    def delete_file_remove_path_from_db(self, uuid:str, file_paths:list=[]):
        """
        delete file paths from db, if file_paths is empty, delete all entries of uuid
        """
        if not uuid or len(uuid) == 0:
            raise ValueError("server file manager: save file uuid is empty.")

        if not self.db:
            raise ValueError("server file manager: delete_file db is not connected.")
        
        folder = self.construct_file_folder(uuid=uuid, create_if_not_exist=False) # construct uuid/file

        try:
            self.sqlite_lock.acquire() # block, as multiple disconnect events from client
            cur = self.db.cursor()
            if len(file_paths)==0: # all uuids
                # remove all files under uuid
                if len(folder) > 0 and os.path.exists(folder): # if the folder not empty and exists
                    #print(f'rmtree: {folder}')
                    logging.debug(f'rmtree: {folder}')
                    shutil.rmtree(folder)
                # query table to see any 'manual' type to be removed
                select_table = f"SELECT * FROM {self.table_name} WHERE {self.uuid_column}='{uuid}' AND {self.type_column}='manual'"
                cur.execute(select_table)
                rows = cur.fetchall()
                # rows is a list [(uid, filepath, 'manual'),(uid, filepath, 'manual'),...]
                for row in rows:
                    path = row[1] # file path
                    if os.path.isfile(path): # remove file from local dir
                        os.remove(path)

                # delete from db
                delete_table = f"DELETE FROM {self.table_name} WHERE {self.uuid_column}='{uuid}'"
                cur.execute(delete_table)
            else:
                for file_path in file_paths:
                    file_path = os.path.join(folder, file_path)
                    if os.path.exists(file_path): # remove file from local dir
                        os.remove(file_path)
                    # delete from table
                    delete_table = f"DELETE FROM {self.table_name} WHERE {self.uuid_column}='{uuid}' AND {self.path_column}='{file_path}"
                    cur.execute(delete_table)
            self.db.commit()
        finally:
            self.sqlite_lock.release() # release

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

class file_item():
    def __init__(self, file_mgr:server_file_mgr, uuid:str, file_path:str, mode:str='w') -> None:
        """
        file_path
        """
        self.mgr = file_mgr
        folder = file_mgr.construct_file_folder(uuid)
        self.file_path = os.path.join(folder, file_path)
        self.file_obj = open(self.file_path, mode)

    def write(self, content:str):
        self.file_obj.write(content)
        self.file_obj.flush()
    
    def save(self, filepath=''):
        self.file_obj.flush()
    
    def close(self):
        self.file_obj.close()