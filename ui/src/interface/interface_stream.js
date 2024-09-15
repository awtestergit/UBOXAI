/*#
# @author awtestergit
# @description interface to encode/decode object into bytes for streaming between client and server
#
*/
import {Buffer} from 'buffer';

class AnbJsonStreamCoder{
    /*#
    #   format as:
    #   TOTAL_LENGTH|HEADER_LENGTH|HEADER_BYTES|OBJECT_BYTES
    #       where total length is 4 bytes, header length is 4 bytes
    */
    static encode(dict_header, dict_obj, byte_length=4, byte_order='little') {
        //const {Buffer} = require('buffer');

        const dict_header_data = JSON.stringify(dict_header);
        const dict_header_data_size = dict_header_data.length;
        let buf = Buffer.alloc(byte_length);
        if (byte_order === 'little'){
            buf.writeUInt32LE(dict_header_data_size,0);
        } else {
            buf.writeUInt32BE(dict_header_data_size,0);
        }
        const dict_header_data_size_bytes = buf;
        const dict_obj_data = JSON.stringify(dict_obj);
        const dict_obj_data_size = dict_obj_data.length;
        buf = Buffer.alloc(byte_length);
        if (byte_order === 'little'){
            buf.writeUInt32LE(dict_obj_data_size,0);
        } else{
            buf.writeUInt32BE(dict_obj_data_size,0);
        }
        const dict_obj_data_size_bytes = buf;

        const header = Buffer.concat([dict_header_data_size_bytes, Buffer.from(dict_header_data)]);
        const header_length = byte_length + dict_header_data_size;

        const total_length = byte_length + header_length + dict_obj_data_size;
        buf = Buffer.alloc(byte_length);
        if (byte_order === 'little'){
            buf.writeUInt32LE(total_length,0);
        } else{
            buf.writeUInt32BE(total_length,0);
        }
        const total_length_bytes = buf;

        const output = Buffer.concat([total_length_bytes, header, dict_obj_data_size_bytes, Buffer.from(dict_obj_data)]);
        //const output64 = output.toString('base64');
        return output;
    }

    static decode(obj, byte_length = 4, byte_order = 'little') {
        //
        //input: bytes in the format of 'total_size|header_size|dict_header|dict_obj'
        //    decoder extract the header and dict_obj
        //output:
        //      null, if total_size > obj size, else 
        //      [[dict_header, dict_obj], rest bytes] , the rest bytes if any
        //
        //const {Buffer} = require('buffer');
        if (obj == null){
            return null;
        }
        //const obj = Buffer.from(obj64, 'base64')
        let header_objects = []; // header and object list
        while (obj != null && obj.length>0){
            let total_size = obj.slice(0, byte_length);
            const obj_size = obj.length; // the object length

            // endian
            total_size = Buffer.from(total_size);
            total_size = (byte_order === 'little') ? total_size.readUInt32LE(0) : total_size.readUInt32BE(0);

            // return null if total size is larger than bytes length
            if (obj_size < total_size){
                break;
            }

            let header_size = obj.slice(byte_length, byte_length*2);
            header_size = Buffer.from(header_size);
            header_size = (byte_order === 'little') ? header_size.readUInt32LE(0) : header_size.readUInt32BE(0);
        
            header_size += byte_length*2; // The end of header in the byte sequence
        
            let header = obj.slice(byte_length*2, header_size);
            header = new TextDecoder().decode(header); // Decode into string
            header = JSON.parse(header); // Convert string to object
        
            let dict_obj = obj.slice(header_size, total_size);
            dict_obj = new TextDecoder().decode(dict_obj);
            dict_obj = JSON.parse(dict_obj);

            // header_objects
            header_objects = [...header_objects, [header, dict_obj]];

            // the rest bytes if any
            obj = (obj_size > total_size) ? obj.slice(total_size) : null;
        }

        // if no header objects,
        if (header_objects.length == 0){
            return null;
        } else{
            return [header_objects, obj];
        }
    }
}

export default AnbJsonStreamCoder;

/*
const h = {
    'header': 'abc',
    'seq': 0,
    'status': 'good',
};
const o = {
    'total': 2,
    'seq': 1,
    'data': {
        'A': {
            'text': 'text A',
        },
        'B': {
            'text': 'text A',
        },
    }
};

const tb = AnbJsonStreamCoder.encode(h, o);
const tbho = AnbJsonStreamCoder.decode(tb);
tbh = tbho[0];
tbo = tbho[1];
console.log("header");
console.log(tbh);
console.log('object');
console.log(tbo);
console.log("tbho");
console.log(tbho);
*/