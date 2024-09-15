/*
    Author: awtestergit
*/

import { Grid } from "@mui/material";
import LeftPanel from "./leftside";
import {BasePanel} from "../common";
import RightPanel from "./rightside";
import AnbJsonStreamCoder from '../../interface/interface_stream';
import { Buffer } from "buffer";

class DoctractMainPanel extends BasePanel{
    constructor(props){
        super(props);
        this.state = {
            //
            fileKeyName: 'fileTract', // file key
            fileName: '', // filename
            file: null, // file
            isScan: false, // if isscan, ocr is needed
            // progress
            progressStatus: '', //show progress, a string status
            showProgress: false, // flag
            // elements
            elements: '', //
            // result message
            responseMessage:[], // response messages, [{'element': xx, 'detail': yy, 'sources': zz}, {}...]
            // sources
            sources: [], //
            // error message
            errorMessage: '',
            // file processed
            fileProcessed: false, // 
            // send /cancel button
            showSend: true, // default show send, if false show 'cancel'
            disableSend : true, // default disable send button
            // stop controller
            stopController: null,
            // buttons
            buttons: ['Open template','Save template'], // buttons
            // read_by
            read_by: 2, // default by paragraph
            readOption: ['Page','Document', 'Paragraph'], // default
            readOptionsAll: ['Page','Document', 'Paragraph'],
            readOptionScan: ['Page', 'Dococument'],

        }
        this.handleFileChange = this.handleFileChange.bind(this);
        this.handleCheckScan = this.handleCheckScan.bind(this);
        this.handleQuery = this.handleQuery.bind(this);
        this.uploadFile = this.uploadFile.bind(this);
        this.handleSend = this.handleSend.bind(this);
        this.handleCancel = this.handleCancel.bind(this);
        this.handleStop = this.handleStop.bind(this);
        this.handleTemplate = this.handleTemplate.bind(this);
        this.handleElementChange=this.handleElementChange.bind(this);
        this.handleReadOption=this.handleReadOption.bind(this);
    }

    handleReadOption(event){
        const option = event.target.value;
        const index = this.state.readOption.indexOf(option);
        const disableSend = this.state.file ? false : true;
        this.setState(
            {
                read_by : index,
                fileProcessed: false, // reset
                disableSend: disableSend, // if file exists, do not disable
            }
        );
    }
    
    handleTemplate(event, id){
        if (id === 0){
            // open template
            const file = event.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (readerEvent) => {
                    const result = readerEvent.target.result;
                    //console.log("reader result: %s", result);

                    this.setState({
                        elements: result,
                        disableSend: result.length > 0 ? false : true,
                    })
                };
                reader.readAsText(file);
            }
        }
        if (id === 1){
            // save template
            // Create a blob from the file content
            const blob = new Blob([this.state.elements], { type: 'text/plain;charset=utf-8' });

            // Create a temporary link element
            const link = document.createElement('a');
            link.href = window.URL.createObjectURL(blob);
            link.download = 'untitled.cfg'; // Set the suggested filename here
            link.style.display = 'none';

            // Append the link to the body and trigger the download
            document.body.appendChild(link);
            link.click();

            // Clean up
            window.URL.revokeObjectURL(link.href);
            document.body.removeChild(link);            
            /*
            window.showSaveFilePicker({
                suggestedName: 'untitled.cfg',
                types: [
                    {
                    description: 'Text file',
                    accept: { 'text/plain': ['.cfg'] },
                    },
                ],                    
            })
            .then(fileHandle => {
                return fileHandle.createWritable();
            })
            .then(writable=>{
                return writable.write(this.state.elements);
            })
            .catch(error =>{
                console.error("Error: ", error);
            });
            */
        }
    }

    handleElementChange(event){        
        this.setState({
            elements: event.target.value,
            disableSend: false, // enable send button
        });
    }

    handleStop(event){
        event.preventDefault();
        if (this.state.stopController){
            this.state.stopController.abort();
            const stopUrl = this.props.serverIP + '/stop?uid=' + this.props.uid;
            fetch(stopUrl)
            .then(async (response) =>{
                const text = await response.text();
                //console.log('server stop response: %s', text);
            })
            this.setState({stopController: null}); // reset
        }
    }

    handleSend(event){
        this.setState(()=>{
            return {showSend : false};
        }); // send is clicked, set it to false so that cancel can be shown

        //console.log("handle send to set showSend to false. value is: %s", this.state.showSend);

        this.handleQuery(event);
    }

    handleCancel(e){
        this.setState(()=>{
            return {showSend : true};
        });

        //console.log("handle cancel to set showSend to false. value is: %s", this.state.showSend);

        this.handleStop(e);
    }

    handleCheckScan(event){
        const isChecked = event.target.checked;
        this.setState({isScan: isChecked});
    }

    handleFileChange(event){
        //
        let targetName = '';
        targetName = event.target.name;
        let targetFile = event.target.files[0];
        //console.log("name: %s; filename: %s", targetName, targetFile.name);
        this.setState({
            file: targetFile,
            fileName: targetFile.name,
            fileProcessed: false, // reset this flag
            disableSend: false, // enable send button
        });
    }

    async uploadFile(event, controller){
        event.preventDefault();

        // disable button, clean error message, clear text input
        this.setState(
            ()=>{
                return {
                    errorMessage: '', // reset
                    //sendButtonDisabled: true,
                }
            }
        );
        let progress = "Analyzing file...";
        let trackError = null; // track error

        if (!this.state.fileProcessed){
            // upload file and create index
            this.setState(
                ()=>{
                    return {
                        progressStatus: progress,
                        showProgress: true,
                    }
                }
            );

            const chatUrl = this.props.serverIP + '/doc_upload';
            let formData = new FormData();
            formData.append('file', this.state.file);
            const uid = this.props.uid;
            formData.append('uid', uid);
            formData.append('ocr', this.state.isScan ? 1 : 0); // is ocr or not
            formData.append('read_by', this.state.read_by); // read doc by paragraph, if not ocr; 0 - page, 1 - document, 2 - paragraph

            //console.log("read by: %d", this.state.read_by);

            await fetch(chatUrl, {
                method:'POST',
                body: formData,
                credentials: 'include',
                mode: 'cors',
                signal: controller.signal,
            })
            .then(async (response)=>{
                const data = await response.json();
                //console.log('response data');
                //console.log(data);

                const status = data['status']; //
                if (status !== 'success'){
                    trackError = data['reason'];
                    throw new Error(trackError); // get out of the function
                }
                else{
                    this.setState(
                        {
                            fileProcessed: true,
                        }
                    );
                }
            })
            .catch((error) =>{
                if (error.name === 'AbortError'){
                    //
                    console.log('....Aborted....');
                }
                else {
                    trackError = error;
                    console.error(error);
                }
            });

            if (trackError){
                trackError = "Error, Check log for details.";
            }
            // reset
            this.setState(
                {
                    progressStatus: '', // reset
                    showProgress: false, // reset
                    //sendButtonDisabled: false, // reset
                    errorMessage: trackError, // error track
                }
            );
        }// end file processed

        return trackError;
    }

    async queryServer(event, controller){
        event.preventDefault();

        // now, send query over for AI to answer
        // upload file and create index
        let progress = "Prepare answer...";
        this.setState(
            ()=>{
                return {
                    progressStatus: progress,
                    showProgress: true,
                    //sendButtonDisabled: true, // set disable
                    errorMessage: '', // reset
                }
            }
        );
        let trackError = null;
        try{
            // 127.0.0.1:8822
            const chatUrl = this.props.serverIP + '/doctract';
            
            const elementJson = JSON.stringify({elements: this.state.elements, uid: this.props.uid});
            //console.log("element json is: %s", elementJson);

            await fetch(chatUrl,
                {
                    method: 'POST',
                    headers:{
                        'Accept': 'application/octet-stream',
                        'Content-Type': 'application/json',
                    },
                    body: elementJson,
                    credentials: 'include',
                    //mode: 'cors',
                    signal: controller.signal,
                },
            )
            .then( response => response.body.getReader())
            .then((async (reader) =>{
                let leftover = null; // track any leftover
                let element = '';
                let detail = '';
                let sources = '';
                let showProgress = true;
                let progressStatus = progress;
                let result;
                let source_id = -1; // track source id
                let currentMessages = [];
                let currentSources = [];
                while(!(result = await reader.read()).done){
                    //console.log('while loop start...');
                    const data = result.value;

                    let v = data;
                    if (leftover != null){ // if leftover from previous processing, concat together
                        v = Buffer.concat([leftover, v]);
                    }
                    let s = AnbJsonStreamCoder.decode(v);
                    if (s == null){ // decode returns null if this v contains only part of jsons, need more from next read()
                        leftover = v;
                    } else{
                        const head_objects = s[0];
                        leftover = s[1];
                        for (let i=0; i<head_objects.length;++i){
                            let ho = head_objects[i]; //header and objects
                            const header_json = ho[0]; // header
                            const status = header_json['status'];
                            if (status === 'success'){
                                const object_json = ho[1]; // object json
                                
                                element = object_json['element']; // element generated
                                detail = object_json['detail']; // element detail
                                sources = object_json['sources'];// sources
                                const _id = parseInt(object_json['source_id']);
                                
                                //console.log("rece'ed: %s, %s, %d ", element, detail, _id);

                                if (_id === source_id){
                                    sources = ''; // only if new source id
                                } else {
                                    // a new source
                                    const msg = {'element': '', 'detail':''}; // add an empty, so that UI display a divider
                                    //const newResponseMessages = [...this.state.responseMessage, msg];
                                    currentMessages = [...currentMessages, msg];
                                    const newResponseMessages = currentMessages
                                    this.setState(()=>{ return {
                                            responseMessage: newResponseMessages,
                                        }
                                    });
                                }
                                source_id = _id; // track
                                //const newSources = [...this.state.sources, sources];
                                currentSources = [...currentSources, sources];
                                const newSources = currentSources;

                                const msg = {'element': element, 'detail': detail};
                                
                                //console.log("construct msg:");
                                //console.log(msg);
                                
                                //const newResponseMessages = [...this.state.responseMessage, msg];
                                currentMessages = [...currentMessages, msg];
                                const newResponseMessages = currentMessages;

                                //console.log(newResponseMessages);

                                this.setState(()=>{ return {
                                        responseMessage: newResponseMessages,
                                        sources: newSources,
                                        // progressStatus: '',
                                        //showProgress: false,
                                    }
                                });
                            } else{
                                showProgress = false; // stop progress
                                if (status === 'end'){ // server sends 'end' regardless of any status
                                    if(progressStatus === progress){ // reset if no failure
                                        progressStatus = '';
                                    }
                                    //console.log("received 'end', status: %s", progressStatus);
                                    break; // break loop
                                } else if(status ==='warning'){
                                    progressStatus = status + '!! ' + header_json['reason'];
                                    trackError = header_json['reason'];
                                    console.log("warning: %s", header_json['reason']);
                                    throw Error(trackError);
                                } else {
                                    // if failed
                                    progressStatus = status + '!! ' + header_json['reason'];
                                    trackError = header_json['reason'];
                                    console.log("not success, status: %s, reason: %s", status, header_json['reason']);
                                    throw Error(trackError);
                                }
                            }//
                        } // end for
                        //console.log('exit for status: %s, progress: %s. current state: %s', progressStatus, showProgress, this.state.progressStatus);
                    } // end else
                    //console.log('next while loop status: %s, progress: %s. current state: %s', progressStatus, showProgress, this.state.progressStatus);
                } // end while
                //console.log("i am done...");
            }));
        }
        catch(error){
            if (error.name === 'AbortError'){
                //
                console.log('....Aborted....');
            }
            else {
                trackError = "Error: " + error;
                console.error(error);
            }
        }

        this.setState(
            {
                progressStatus: '', // reset
                showProgress: false, // reset
                showSend: true, // reset
            }
        );

        return trackError;
    }

    async handleQuery(event){
        event.preventDefault();

        if(!this.state.file){
            this.setState(
                {
                    showSend: true, // reset, this is set at handleSend before this query
                    disableSend: true, // reset, disabled
                }
            );
            return;
        }

        const stopController = new AbortController();

        // set state to prepare dialog
        this.setState(() =>{
            return {
                responseMessage: [], // reset
                stopController : stopController,
                sources: [], // reset
            }
          });

        let trackError = await this.uploadFile(event, stopController);
        if (trackError){
            console.log("track error: %s", trackError);
        } else{
            trackError = await this.queryServer(event, stopController);
        }
        // if error,let bot to answer the error
        if (trackError){
            trackError = "Error, check log for details.";
            this.setState(()=>{
                return {
                    errorMessage: trackError,
                }
            });
        }
        // reset
        this.setState(
            {
                showSend: true,
                disableSend: this.state.elements.length>0 ? false : true,
            }
        );
    }

    render(){
        return(
            <>
            <Grid container display='flex' direction='row' width='100%' height='100%' pr={0} sx={{ boxSizing: 'border-box', overflow:'visible', border: 0}}>
                <Grid item xs={12} md={3} p={1} sx={{border: 0, height:'100%'}} >
                    <LeftPanel
                    fontSizeXXS={this.superState.fontSizeXXS}
                    fontSizeXS={this.superState.fontSizeXS}
                    fontSizeSM={this.superState.fontSizeSM}
                    fontSizeMD={this.superState.fontSizeMD}
                    fontSizeLG={this.superState.fontSizeLG}
                    showSend={this.state.showSend}
                    disableSend={this.state.disableSend}
                    name={this.state.fileKeyName}
                    fileName={this.state.fileName}
                    fileType={this.props.fileTypes}
                    configType={this.props.configType}
                    buttons={this.state.buttons}
                    onSend={this.handleSend}
                    onCancel={this.handleCancel}
                    onFileChange={this.handleFileChange}
                    onCheckScan={this.handleCheckScan}
                    onTemplate={this.handleTemplate}
                    onElementChange={this.handleElementChange}
                    elements={this.state.elements}
                    readBy={this.state.read_by}
                    readOption={this.state.readOption}
                    onReadOption={this.handleReadOption}
                    />
                </Grid>
                <Grid item id='doctract_right' xs={12} md={9} py={1} pr={1} height='100%' border='0px'>
                    <RightPanel 
                    fontSizeXS={this.superState.fontSizeXS}
                    fontSizeSM={this.superState.fontSizeSM}
                    fontSizeMD={this.superState.fontSizeMD}
                    fontSizeLG={this.superState.fontSizeLG}
                    responseMessage={this.state.responseMessage}
                    sources={this.state.sources}
                    progressStatus={this.state.progressStatus}
                    showProgress={this.state.showProgress}
                    errorMessage={this.state.errorMessage}
                    />
                </Grid>
            </Grid>
            </>
        );
    }
}

export default DoctractMainPanel;