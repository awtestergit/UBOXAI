# -*- coding: utf-8 -*-

"""
    provide qdrant server functionalities
    Author: awtestergit
"""

import logging

from interface.interface_constants import IConstants
from interface.interface_comm import  IServiceCommClass, ISystemDescPydantic, IpdOutputItem
from qdrantclient_vdb.qdrant_manager import qcVdbManager

class QdrantVDBServer(ISystemDescPydantic):
    def __init__(self, vdbs:list[qcVdbManager], service_comm:IServiceCommClass, vdb_name:str="", vdb_desc:str="") -> None:
        """
        vdbs: a list of vdb managers, each of which manage a collection set [id, doctype, file, chunk index]
        address/port, local http://ip/port this server is listening to
        """
        #####name, desc#####
        self.vdb_name = vdb_name if len(vdb_name) > 0 else "知识库查询系统"
        self.vdb_desc = vdb_desc if len(vdb_desc) > 0 else "查询公司知识库"

        self.vdbs = vdbs # vdb manager
        self.service_comm = service_comm
        # communication
        self.local_addr = service_comm.local_addr
        self.local_port = service_comm.local_port
        self.action = IConstants.ServiceComm.QUERY #all requests from server to client systems are to this: ip:port/query?json=...
        # split character
        self.system_split = '_system_' # to construct the system name, seperated by this character
        self.type_split = 'query_' # to construct the method name using vdb's type name

        # all ready, now initialize ISystemDescPydantic
        ISystemDescPydantic.__init__(self)

        # register, convert to dict
        systems = super().get_systems()
        #dicts = [asdict(system) for system in systems] # make the dict to send over request
        self.service_comm.register(systems=systems)
        # shut down
        self.down = False

    def __del__(self) -> None:
        self.shutdown()
    
    def shutdown(self):
        # unregister
        # register, convert to dict
        try:
            if not self.down:
                systems = super().get_systems()
                self.service_comm.unregister(systems=systems)
                self.down = True
        except Exception as e:
            logging.error(f"Qdrantclient db server shutdown failed. this may or may not be a problem, check error information: {e}")

    """
    ISystemDescPydantic
    """
    def __create_systems__(self):
        """
        lists of (type, description) for each collection in db
        "collection1": [type, description],
        "collection2": [type, description],
        """        
        self.systems = [] # clear any existing

        # for each collection in db, treat the collection as a system
        system_name = self.vdb_name #"知识库查询系统"
        system_desc = f"{self.vdb_desc}。包含" #"查询公司知识库，包含"
        # loop vdbs to get collection, type, description
        systems = []
        for vdb in self.vdbs:
            doctypes = vdb.get_doctype()
            collection_name = vdb.collection_name
            system = {collection_name: []} # a dict
            for doctype in doctypes:
                system[collection_name].append([doctype.type, doctype.description]) # type, desc
            systems.append(system)

        for system in systems:
            # export system description
            for k, v in system.items(): # name: [list]
                collection_name = k
                type_desc = v
            name = f"{system_name}{self.system_split}{collection_name}" # '_system_' to split. 知识库查询系统_system_collection name
            description = system_desc # add all descriptions of each type, the information will be added in the method loop below
            address = self.local_addr
            port = self.local_port
            action = self.action #

            # export methods
            for type, method_desc in type_desc: # loop the list
                method_name = f"{self.type_split}{type}" # use 'query_' to split, method name: query_type
                description = f"{description} ['{method_desc}']," # add to system description
                outputs = [IpdOutputItem(name='result',type='list')] # list of IpdOutputItem
                params = [] # no parameter
                self.add_method(system_name=name, name=method_name, desc=method_desc, outputs=outputs, params=params)
            # now we can add system
            self.add_system(system_name=name, desc=description, address=address, port=port, action=action)

    def query(self, system:str, function:str, query:str, top_k=3, threshold=0.6, only_recent_timestamp=True) -> list[IpdOutputItem]:
        """
        system string is: 知识库查询系统_system_collection name -> split to get collection name
        function string is: query_type, split 'query_' to get type
        query is query string to vdb
        """
        system = system.split(self.system_split) # '_system_' split
        assert len(system) == 2
        collection_name = system[1] # collection
        db_type = function.split(self.type_split)[-1] # 'query_' split
        error = f"system: {system}; function:{function}; query: {query}"
        
        logging.debug(error)
        
        # get the vdb
        manager:qcVdbManager = None
        for vdb in self.vdbs:
            if vdb.collection_name == collection_name:
                manager = vdb
                break
        if manager is None:
            error = f"QdrantVDBServer::query cannot find vdb manager by collection name '{collection_name}'." + error
            logging.error(error)
            raise ValueError(error)

        # prepare for query
        #vector = manager.model.encode_numpy(query) # use numpy
        db_type = '' # no type for now
        results = manager.query(query=query,type=db_type,top_k=top_k,threshold=threshold,only_recent_timestamp=only_recent_timestamp)
        # only output result.meta len > 0
        outputs = [IpdOutputItem(value=result.meta, type=db_type, source=result.source_from) for result in results if len(result.meta) > 0]
        return outputs

    def query_faq(self, system:str, query:str, level_0:str='', level_1:str='', top_k=3, threshold=0.9) -> list[IpdOutputItem]:
        """
        system string is: 知识库查询系统_system_collection name -> split to get collection name
        query is query string to vdb
        level_0/level_1, org names
        top_k, top k results
        threshold,
        """
        system = system.split(self.system_split) # '_system_' split
        assert len(system) == 2
        collection_name = system[1] # collection

        error = f"system: {system}; query: {query}; orgs:{level_0}/{level_1}"
        
        logging.debug(error)
        
        # get the vdb
        manager:qcVdbManager = None
        for vdb in self.vdbs:
            if vdb.collection_name == collection_name:
                manager = vdb
                break
        if manager is None:
            error = f"QdrantVDBServer::query_faq cannot find vdb manager by collection name '{collection_name}'." + error
            logging.error(error)
            raise ValueError(error)

        # prepare for query
        vector = manager.model.encode_numpy(query) # use numpy
        results = manager.faq_query(query_vector=vector, level_0=level_0, level_1=level_1, top=top_k, threshold=threshold)

        # only output result.meta len > 0
        outputs = [IpdOutputItem(value=result.answer, source=f"FAQ_{result.level_0}_{result.level_1}") for result in results if len(result.answer) > 0]
        return outputs

