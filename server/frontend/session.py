# -*- coding: utf-8 -*-

"""
    session manager for fastapi/flask - to make the session used by both socket & http work
    Author: awtestergit
"""
from datetime import timedelta, datetime
from file_management.file_manager import server_file_mgr
from file_management.chat_manager import chat_history_mgr

class session_manager():
    def __init__(self, file_mgr:server_file_mgr, chat_mgr:chat_history_mgr, expiration=30) -> None:
        self.expiration = expiration # default session expires in 30 minutes
        self.expire_key = "SESSION_EXPIRATION"
        # session keys
        self.SID_KEY = "SID"
        self.UID_KEY = "UID"
        self.FAISS_KEY = 'FAISS' # faiss key
        self.FAISS_TEXTS = 'FAISSTEXTS' # faiss original texts
        self.CONTINUE_KEY = 'CONTINUEFLAG' # check if continue, i.e, if client send stop interruption
        self.TREE_KEY = 'TREEKEY' # content trees for search relevant content to write article
        self.HISTORY_KEY = 'HISTORYKEY' # history for doc_know
        self.TASK_KEY = "TASKKEY" # asyncio task key
        self.LOGGEDIN = "LOGGEDIN" # whether user is logged in, default user uid's loggedin is false
        self.USERID = "USERID" # user id
        self.USERNAME = "USERNAME" #user name
        self.session = {} # {'sid1: {'uid':uid1, EXPIRE:xx}, 'uid1': {sid:sid1, EXPIRE:xx}, 'uid2':{}...}
        self.file_mgr = file_mgr
        self.chat_mgr = chat_mgr

    def __renew_expiration__(self, uid):
        # Set session expiry
        expiry = timedelta(minutes=self.expiration)  # Sessions expire after 30 minutes
        expiry = datetime.now() + expiry

        if uid in self.session:
            session = self.session[uid]
            session[self.expire_key] = expiry # set self expiration
            # if this uid is sid
            if self.UID_KEY in session: # set the uid expiration
                uid = session[self.UID_KEY]
                if uid in self.session:
                    self.session[uid][self.expire_key] = expiry
            elif self.SID_KEY in session: # this uid is a uid, set sid expiration
                sid = session[self.SID_KEY]
                if sid in self.session:
                    self.session[sid][self.expire_key] = expiry

    def cleanup_expired_sessions(self):
        current_time = datetime.now()
        for k, v in list(self.session.items()): # k is id, v is {}, copy to a list to loop
            if self.expire_key in v and v[self.expire_key] < current_time:
                self.remove_session_sid(k) # use remove sid to remove, this can remove both sid and uid
                self.file_mgr.delete_file_remove_path_from_db(k)
                self.chat_mgr.delete_chat_history(k)

    def set_session_sid(self, sid:str, uid:str):
        # set sid, along with uid, so that these two can cross reference
        if not sid in self.session:
            self.session[sid] = {
                self.UID_KEY: uid,
            }
        if not uid in self.session:
            self.session[uid] = {
                self.SID_KEY: sid, # a copy of sid
                self.UID_KEY: uid, # a copy of self uid
            }
        self.__renew_expiration__(sid) # set exipration

    def remove_session_sid(self, sid:str):
        session = self.session[sid] if sid in self.session else None
        if session:
            if self.UID_KEY in session: # remove uid associated with this sid
                uid = session[self.UID_KEY]
                self.session.pop(uid, None)
            self.session.pop(sid, None) # remove this sid

    def remove_session(self, uid:str):
        self.session.pop(uid, None)

    def get_session_all(self, uid:str):
        session = None
        if uid in self.session:
            session = self.session[uid]
            self.__renew_expiration__(uid) # renew expiration
        return session
    def get_session_key(self, uid:str, key:str):
        session = None
        if uid in self.session and key in self.session[uid]:
            session = self.session[uid][key]
            self.__renew_expiration__(uid)
        return session

    def set_session(self, uid, key, value):
        if uid not in self.session:
            self.session[uid] = {
                self.UID_KEY: uid, # a copy of self always uid:{UID: uid...}
            }
        session = self.session[uid]
        session[key] = value
        self.__renew_expiration__(uid)

    def cross_check_uid_in_session(self, uid:str)->bool:
        is_same = False
        if uid in self.session:
            session = self.session[uid]                    
            if self.UID_KEY in session:
                if (uid == session[self.UID_KEY]): # uid match, now continue to check user login
                    is_same = True
        return is_same