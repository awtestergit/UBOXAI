/*
    Author: awtestergit
*/

import { Dialog, Grid } from "@mui/material";
import LeftPanel from "./leftside";
import {BasePanel} from "../common";
import RightPanel from "./rightside";
import AnbJsonStreamCoder from '../../interface/interface_stream';
import { Buffer } from "buffer";

class DochatMainPanel extends BasePanel{
    constructor(props){
        super(props);
        this.state = {
            //
            fileKeyName: 'fileChat', // file key
            fileName: '', // filename
            file: null, // file
            isScan: false, // if isscan, ocr is needed
            // chat messages
            messages: [], //side is 'user' or 'bot', { 'side': 'user', 'text': this.state.newMessage, 'timestamp': new Date() }
            newMessage : '',
            sourceText: [], // list
            numWords: 150, // current set number of words to generate
            maxWords: 500, // max words
            // progress
            progressStatus: '', //show progress, a string status
            showProgress: false, // flag
            // button disable
            //sendButtonDisabled: false,
            // error message
            errorMessage: '',
            // file processed
            fileProcessed: false, // 
            // send /cancel button
            showSend : true, // default show send button
            // stop controller
            stopController: null,
            // read_by
            read_by: 2, // default by paragraph
            readOption: ['Page','Document', 'Paragraph'], // default
            readOptionsAll: ['Page','Document', 'Paragraph'],
            readOptionScan: ['Page', 'Dococument'],
            // alert
            alertMessage: '',
        }
        this.handleFileChange = this.handleFileChange.bind(this);
        this.handleCheckScan = this.handleCheckScan.bind(this);
        this.handleQuery = this.handleQuery.bind(this);
        this.handleKeyDown = this.handleKeyDown.bind(this);
        this.handleTextChange = this.handleTextChange.bind(this);
        this.handleSliderChange = this.handleSliderChange.bind(this);
        this.uploadFile = this.uploadFile.bind(this);
        this.handleSend = this.handleSend.bind(this);
        this.handleCancel = this.handleCancel.bind(this);
        this.handleStop = this.handleStop.bind(this);
        this.handleReadOption=this.handleReadOption.bind(this);
    }

    handleReadOption(event){
        const option = event.target.value;
        const index = this.state.readOption.indexOf(option);
        //console.log('parsing file option: %d', index);
        this.setState(
            {
                read_by : index,
                fileProcessed: false, // reset
            }
        );
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
            return {
                showSend : false,
            };
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
        const readOption = isChecked ? this.state.readOptionScan : this.state.readOptionsAll;
        this.setState({
            isScan: isChecked,
            readOption: readOption,
        });
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
        });
    }

    handleTextChange(e){
        this.setState({newMessage: e.target.value});
    }

    handleKeyDown(e){
      if (e.key === 'Enter' && (this.state.newMessage)){
        //console.log("enter key is pressed. message: %s", this.state.newMessage);
        this.handleSend(e);
      }
    }

    handleSliderChange(e, newValue){
        this.setState({numWords: newValue});
    }

    async uploadFile(event, controller){
        event.preventDefault();

        // disable button, clean error message, clear text input
        this.setState(
            ()=>{
                return {
                    newMessage: '',
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
            const uid = this.props.uid; //.toString();
            const ocr = this.state.isScan ? 1 : 0;
            const readBy = this.state.read_by;
            formData.append('uid', uid);
            formData.append('ocr', ocr); // is ocr or not
            formData.append('read_by', readBy); // read by

            //console.log("chatUrl is: %s", chatUrl);

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
                    trackError = error;
                }
                else {
                    trackError = error.toString();
                    console.error(error);
                }
            });
            if (trackError){
                trackError = "Uploading file failed."
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

    async queryServer(event, query, controller){
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
                    newMessage: '', // reset
                }
            }
        );
        let trackError = null;
        try{
            // 127.0.0.1:8822?q=xx&words=nn
            const uid = this.props.uid; //.toString();
            const chatUrl = this.props.serverIP + '/dochat_chat?uid=' + uid + "&q=" + query +"&words=" + this.state.numWords;            

            //console.log("chatUrl is: %s", chatUrl);

            await fetch(chatUrl,
                {
                    method: 'GET',
                    headers:{'Accept': 'application/octet-stream',},
                    credentials: 'include',
                    mode: 'cors',
                    signal: controller.signal,
                },
            )
            .then( response => response.body.getReader())
            .then((async (reader) =>{
                let leftover = null; // track any leftover
                let text = '';
                let allSources = ['Sources:'];
                let showProgress = true;
                let progressStatus = progress;
                let result;
                while(!(result = await reader.read()).done){
                    //console.log('while loop start...');
                    //let {done, value} = await reader.read(); value, not data! what the f**k?
                    const done = result.done;
                    const data = result.value;
                    //console.log("done: %s, data: %s", done, data);

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
                                text = object_json['text']; // text generated
                                const sources = object_json['sources'];// sources
                                if (text && text.length > 0){
                                    const messages = this.state.messages.slice(0, -1);
                                    const newText = text;
                                    const botMsg = {'side': 'bot', 'text': newText, 'timestamp': new Date()};
                                    const newMessages = [...messages, botMsg];
                                    this.setState(()=>{ return {
                                            messages: newMessages,
                                            progressStatus: '',
                                            showProgress: false,
                                        }
                                    });
                                }
                                if (sources && sources.length > 0){
                                    allSources = [...allSources, sources];
                                    this.setState(()=>{ return {
                                            sourceText: allSources,
                                            progressStatus: '',
                                            showProgress: false,
                                        }
                                    });
                                }
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
                                    //console.log("warning: %s", header_json['reason']);
                                } else {
                                    // if failed
                                    progressStatus = status + '!! ' + header_json['reason'];
                                    trackError = header_json['reason'];
                                    //console.log("not success, status: %s, reason: %s", status, header_json['reason']);
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
                //sendButtonDisabled: false, // reset
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
                    alertMessage: "No file selected!",
                }
            );
            return;
        }
        if(!this.state.newMessage){
            this.setState(
                {
                    showSend: true, // reset, this is set at handleSend before this query
                }
            );
            return;
        }

        const stopController = new AbortController();

        // set state to prepare dialog
        this.setState(() =>{
            return {
                messages: [...this.state.messages, 
                { 'side': 'user', 'text': this.state.newMessage, 'timestamp': new Date() },
                { 'side': 'bot', 'text': '', 'timestamp': new Date() },
                ],
                stopController : stopController,
            }
            //newMessage: '',
          });
  
        const query = this.state.newMessage;
        
        //console.log("query is %s", query);

        let trackError = await this.uploadFile(event, stopController);
        if (trackError){
            console.log("track error: %s", trackError);
        }
        else{ // if no error from upload file
            trackError = await this.queryServer(event, query, stopController);
        }
        // if error,let bot to answer the error
        if (trackError){
            const messages = this.state.messages.slice(0, -1);
            const botMsg = {'side': 'bot', 'text': trackError, 'timestamp': new Date()};
            const newMessages = [...messages, botMsg];

            this.setState(()=>{
                return {
                    messages: newMessages,
                }
            });
        }
        // reset
        this.setState(
            {showSend: true}
        );
    }
    render(){
        return(
            <>
            {
                this.state.alertMessage.length > 0 && 
                <Dialog open onClose={()=>{
                        this.setState({alertMessage: ''});
                    }} >
                    {this.state.alertMessage}
                </Dialog>
            }
            <Grid container display='flex' flexDirection='row' width='100%' height='100%' sx={{ boxSizing: 'border-box', border: 0, overflow: 'hidden'}}>
                <Grid item xs={12} md={3} p={1} height='100%' sx={{border: 0}} >
                    <LeftPanel
                    fontSizeSM={this.superState.fontSizeSM}
                    fontSizeMD={this.superState.fontSizeMD}
                    fontSizeLG={this.superState.fontSizeLG}
                    name={this.state.fileKeyName}
                    fileName={this.state.fileName}
                    fileType={this.props.fileTypes}
                    readBy={this.state.read_by}
                    readOption={this.state.readOption}
                    onReadOption={this.handleReadOption}
                    onFileChange={this.handleFileChange}
                    onCheckScan={this.handleCheckScan}
                    />
                </Grid>
                <Grid item xs={12} md={9} py={1} pr={1} height='100%' border='0px'>
                    <RightPanel 
                    fontSizeXS={this.superState.fontSizeXS}
                    fontSizeSM={this.superState.fontSizeSM}
                    fontSizeMD={this.superState.fontSizeMD}
                    fontSizeLG={this.superState.fontSizeLG}
                    showSend={this.state.showSend}
                    isMobile={this.props.isMobile}
                    onKeyDown={this.handleKeyDown}
                    onTextChange={this.handleTextChange}
                    onQuery={this.handleQuery}
                    onSendButton={this.handleSend}
                    onCancelButton={this.handleCancel}
                    onWordNumber={this.handleSliderChange}
                    newMessage={this.state.newMessage}
                    chatMessages={this.state.messages}
                    sourceText={this.state.sourceText}
                    progressStatus={this.state.progressStatus}
                    showProgress={this.state.showProgress}
                    sendButtonDisabled={this.state.sendButtonDisabled}
                    errorMessage={this.state.errorMessage}
                    numWords={this.state.numWords}
                    maxWords={this.state.maxWords}
                    />
                </Grid>
            </Grid>
            </>
        );
    }
}

export default DochatMainPanel;