# -*- coding: utf-8 -*-
#
# @author awtestergit
# @description interface to encode/decode object into bytes for streaming between client and server
#

import json
import base64
#
#   format as:
#   TOTAL_LENGTH|HEADER_LENGTH|HEADER_BYTES|OBJECT_BYTES
#       where total length is 4 bytes, header length is 4 bytes
#
#
class anb_stream_coder():
    def encode(*args, **kwargs):
        raise NotImplementedError("anb_encoder not implemented")
    def decode(*args, **kwargs):
        raise NotImplementedError("anb_decoder not implemented")
    
class AnbJsonStreamCoder(anb_stream_coder):
    @classmethod
    def encode(cls, dict_header:dict, dict_obj:dict, byte_length=4, byte_order='little')->bytes:
        """
        encode dict into a byte sequence, format as:
            total_length|header_length|dict_header|dict_obj, where header is the object in bytes
        dict_header: a dict header describing this sequence of dict ojbect
        dict_obj: the object in dict
        byte_order: must be the same between client and server
        byte_length: both total_length and header_length are 4 bytes, 
            total_length includes total length of 'total_length|header_length|header|wav'
            header_length indicating the length of 'header_length|header' of the byte sequence
        the rest is the dict bytes
        output: the byte sequence in 'total_length|header_length|header|wav'
        """
        dict_header_data = json.dumps(dict_header).encode(errors='ignore') # dump to json bytes
        dict_header_data_size = len(dict_header_data) # len
        dict_header_data_size_bytes = dict_header_data_size.to_bytes(byte_length, byteorder=byte_order)
        dict_obj_data = json.dumps(dict_obj).encode(errors='ignore') # dump to json bytes
        dict_obj_data_size = len(dict_obj_data) # len
        #dict_obj_data_size_bytes = dict_obj_data_size.to_bytes(byte_length, byteorder=byte_order)

        # header
        header = dict_header_data_size_bytes + dict_header_data
        header_length = byte_length + dict_header_data_size # len(header)
        # total length
        total_length = byte_length + header_length + dict_obj_data_size # including the 4 byets, now the length is total of 'total_length|header_length|header|obj'
        total_length_bytes = total_length.to_bytes(byte_length, byteorder=byte_order)
        # output
        output = total_length_bytes + header + dict_obj_data #concat
        # base64
        #output64 = base64.b64encode(output)
        return output

    @classmethod
    def decode(cls, obj:bytes, byte_length=4, byte_order='little')->tuple[dict, bytes]:
        """
        input: bytes in the format of 'total_size|header_size|dict_header|dict_obj'
            decoder extract the header and dict_obj
        output: dict_header, dict_obj, the rest bytes if any
        """
        #obj = base64.b64decode(obj)
        total_size = obj[:byte_length]
        total_size = int.from_bytes(total_size, byteorder=byte_order)
        header_size = obj[byte_length:byte_length*2] #two byte_length
        header_size = int.from_bytes(header_size, byteorder=byte_order)# byteorder to consider
        header_size += byte_length*2 # the end of header in the byte sequence
        header = obj[byte_length*2:header_size] # bytes of header object, starting at byte_length, end at header_size
        header = header.decode() # decode into str
        header = json.loads(header) # to dict
        dict_obj = obj[header_size:total_size] #the rest to total_size is dict_obj
        dict_obj = dict_obj.decode()
        dict_obj = json.loads(dict_obj)
        obj_size = len(obj)
        rest_bytes = obj[total_size:] if obj_size > total_size else None
        return header, dict_obj, rest_bytes