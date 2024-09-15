/*
    Author: awtestergit
*/

import { Grid } from "@mui/material";
import {BasePanel} from "../common";
import RightPanel from "./rightside";
import AnbJsonStreamCoder from '../../interface/interface_stream';
import { Buffer } from "buffer";

class DocknowMainPanel extends BasePanel{
    constructor(props){
        super(props);
        this.state = {
            // chat messages
            messages: [], //side is 'user' or 'bot', { 'side': 'user', 'text': this.state.newMessage, 'timestamp': new Date() }
            newMessage : '',
            sourceText: [], // sources
            numWords: 300, // current set number of words to generate
            maxWords: 1000, // max words
            // progress
            progressStatus: '', //show progress, a string status
            showProgress: false, // flag
            // button disable
            //sendButtonDisabled: false,
            // error message
            errorMessage: '',
            // send /cancel button
            showSend : true, // default show send button
            // stop controller
            stopController: null,
        }
        this.handleCheckScan = this.handleCheckScan.bind(this);
        this.handleQuery = this.handleQuery.bind(this);
        this.handleKeyDown = this.handleKeyDown.bind(this);
        this.handleTextChange = this.handleTextChange.bind(this);
        this.handleSliderChange = this.handleSliderChange.bind(this);
        this.handleSend = this.handleSend.bind(this);
        this.handleCancel = this.handleCancel.bind(this);
        this.handleStop = this.handleStop.bind(this);
    }

    handleStop(event){
        event.preventDefault();
        if (this.state.stopController){
            this.state.stopController.abort();
            const stopUrl = this.props.serverIP + '/stop?uid=' + this.props.uid;
            fetch(stopUrl)
            .then(async (response) =>{
                const text = await response.text();
                console.log('server stop response: %s', text);
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

        console.log("handle send to set showSend to false. value is: %s", this.state.showSend);

        this.handleQuery(event);
    }

    handleCancel(e){
        this.setState(()=>{
            return {showSend : true};
        });

        console.log("handle cancel to set showSend to false. value is: %s", this.state.showSend);

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
                    sourceText: [], // reset
                    newMessage: '', // reset
                }
            }
        );
        let trackError = null;
        // 127.0.0.1:8822?q=xx&words=nn
        const chatUrl = this.props.serverIP + '/docknow';
        let formData = new FormData();
        const uid = this.props.uid;
        formData.append('uid', uid);
        formData.append('query', query);
        formData.append('words', this.state.numWords);
        formData.append('history', 100); // default 100 histories
        formData.append('bot', 'ubox');
        formData.append('faq_conf', 0.91);
        formData.append('vdb_conf', 0.3);

        await fetch(chatUrl,
            {
                method: 'POST',
                body: formData,
                credentials: 'include',
                mode: 'cors',
                signal: controller.signal,
            },
        )
        .then( response => response.body.getReader())
        .then((async (reader) =>{
            let leftover = null; // track any leftover
            let allAnswer = '';
            let allSources = ['Sources:'];
            let showProgress = true;
            let progressStatus = progress;
            let result;
            while(!(result = await reader.read()).done){
                console.log('while loop start...');
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
                            const newText = object_json['answer']; // text generated
                            const sources = object_json['sources'];// sources
                            if (newText && newText.length>0){
                                const messages = this.state.messages.slice(0, -1);
                                allAnswer += newText;
                                const botMsg = {'side': 'bot', 'text': allAnswer, 'timestamp': new Date()};
                                const newMessages = [...messages, botMsg];
                                this.setState(()=>{ return {
                                        messages: newMessages,
                                    }
                                });                                        
                            }
                            if (sources && sources.length>0){
                                const newSource = sources;
                                allSources = [...allSources, newSource];
                                this.setState(()=>{ return {
                                    sourceText: allSources,
                                    }
                                });                                        
                            }
                            this.setState(()=>{ return {
                                    progressStatus: '',
                                    showProgress: false,
                                }
                            });
                        } else{
                            showProgress = false; // stop progress
                            if (status === 'end'){ // server sends 'end' regardless of any status
                                if(progressStatus === progress){ // reset if no failure
                                    progressStatus = '';
                                }
                                console.log("received 'end', status: %s", progressStatus);
                                break; // break loop
                            } else if(status ==='warning'){
                                progressStatus = status + '!! ' + header_json['reason'];
                                trackError = header_json['reason'];
                                console.log("warning: %s", header_json['reason']);
                            } else {
                                // if failed
                                progressStatus = status + '!! ' + header_json['reason'];
                                trackError = header_json['reason'];
                                console.log("not success, status: %s, reason: %s", status, header_json['reason']);
                            }
                        }//
                    } // end for
                    console.log('exit for status: %s, progress: %s. current state: %s', progressStatus, showProgress, this.state.progressStatus);
                } // end else
                console.log('next while loop status: %s, progress: %s. current state: %s', progressStatus, showProgress, this.state.progressStatus);
            } // end while
            console.log("i am done...");
        }))
        .catch((error) => {
            if (error.name === 'AbortError'){
                //
                console.log('....Aborted....');
            }
            else {
                trackError = "Error: " + error;
                console.log(".....error:")
                console.error(error);
            }
        });

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

        if( !this.state.newMessage){
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
        
        console.log("query is %s", query);

        const trackError = await this.queryServer(event, query, stopController);
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
            <Grid container display='flex' flexDirection='row' width='100%' height='100%' sx={{ boxSizing: 'border-box', border: 0}}>
                <Grid item xs={12} py={1} p={1} height='100%' border='0px'>
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

export default DocknowMainPanel;