/*
    awtestergit
    main panel for docompare
*/

import axios from 'axios';
import LeftPanel from "./leftside";
import RightPanel from "./rightside";
import {Grid} from '@mui/material';
import AnbJsonStreamCoder from '../../interface/interface_stream';
import { Buffer } from "buffer";
import {BasePanel} from "../common";

class DocompareMainPanel extends BasePanel{
    //
    constructor(props){
        super(props);
        this.state = {
            ...this.state, // inherit base state
            // left panel
            fileA: null, // file A
            fileAName: '', // file A name
            aTargetName: 'A', // key name
            fileB: null,
            fileBName: '',
            bTargetName: 'B',
            // if is scanned file, if any
            isScanA: false, // if is scanned, the buttons is ['Page', 'Document']
            isScanB: false, // if is scanned

            // fileType: '.docx, .doc, .pdf', // accepted file types
            displayOption: 0, // compare by, 0 - page, 1 - document, 2 - paragraph, 
            buttonsAll: ['Page', 'Document', 'Paragraph'], // buttons for comparing all types, page/document should be in the first 2
            buttonsScan: ['Page', 'Document'], // if is scanned file, only page or document types
            //buttonsAll: ['页面', '全文', '段落'], // buttons for comparing all types, page/document should be in the first 2
            //buttonsScan: ['页面', '全文'], // if is scanned file, only page or document types

            //
            leftItems: [], // compare - left file
            rightItems: [],// compare - rigth file
            compareStatus: '', // compare - status
            compareProgress: false, // progress bar while comparing
            // pagination for right panel
            currentPage: 1, // first page
            pageCount: 0, // total page
            // status
            status: '',
            // stop controller
            stopController: null,
            // show send button, or show cancel
            showSend : true, // default show send button
        };

        this.handleFileChange = this.handleFileChange.bind(this);
        this.handleOptionChange = this.handleOptionChange.bind(this);
        this.onCompareFilesSubmit = this.onCompareFilesSubmit.bind(this);
        this.handlePageChange = this.handlePageChange.bind(this);
        this.handleCheckScan = this.handleCheckScan.bind(this);
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
                //console.log('server stop response: %s', text);
            })
            this.setState({stopController: null}); // reset
        }
        this.setState({
            showSend: true, // reset
        });
    }

    handleCheckScan(event){
        const targetName = event.target.name;
        const isChecked = event.target.checked;

        if (targetName==='left'){
            this.setState({isScanA: isChecked});
        }
        else if(targetName==='right'){
            this.setState({isScanB: isChecked});
        }
    }

    handleFileChange(event) {
        let targetName = '';
        try{ // user might click 'cancel'
            targetName = event.target.name;
            let targetFile = event.target.files[0];
            // check file size
            const origSize = targetFile.size / 1024 / 1024;
            const size = Math.ceil(origSize); //mb
            let oversize = false;
            const maxSize = this.state.fileMaxSize;
            
            if (size > maxSize){
                // modal
                oversize = true;
                const msg = "File size cannot exceed " + maxSize + "MB. Current file size is " + origSize.toFixed(2) + "MB."
                alert(msg);
            }

            //console.log("name: %s; filename: %s; filesize: %s; max size: %s; oversize: %s", targetName, targetFile.name, size, maxSize, oversize);

            if (targetName === 'A'){
                if (oversize){
                    this.setState({fileA: null, fileAName: ''});
                }
                else {
                    this.setState({ 
                        fileA: targetFile, 
                        fileAName: targetFile.name,
                        isScanA: false,
                    });
                }
            } else{
                if (oversize){
                    this.setState({fileB: null, fileBName: ''});
                }
                else {
                    this.setState({
                        fileB: targetFile,
                        fileBName: targetFile.name,
                        isScanB: false,
                    });
                }
            }
            // reset
            this.setState(
                {
                    leftItems: [], // compare - left file
                    rightItems: [],// compare - rigth file
                    compareStatus: '', // compare - status
                    compareProgress: false, // progress bar while comparing
                    // pagination for right panel
                    currentPage: 1, // first page
                    pageCount: 0, // total page
                    // status
                    status: '',        
                }
            )

        }
        catch(error){
            // ignore
            console.log(error);
        }
    }

    handlePageChange(event, value){
        this.setState(
            {
                currentPage: value,
            }
        );
    }
    
    handleOptionChange(event, optionIndex) {
        //  0 - page, 1 - document, 2 - paragraph. page/document should be in the first two
        //console.log("button value: %s", optionIndex);

        this.setState({ 
            displayOption: optionIndex,
            leftItems: [], // reset, otherwise can cause because of Pagination of page count out of range
            rightItems:[], // reset
            pageCount: 0, // reset
            currentPage: 1, //reset
         });
    }

    async onCompareFilesSubmit(event){
        event.preventDefault();

        // files
        if (!this.state.fileA || !this.state.fileB){
            this.setState(
                {
                    compareStatus: "Need two files to compare."
                }
            );
            return;
        }

        //const response = fetch(sip, {method:'POST'});
        let formData = new FormData();
        // ['A', [fileA, isScanned]]
        formData.append(this.state.aTargetName, this.state.fileA);
        formData.append(this.state.bTargetName, this.state.fileB);
        formData.append('a_ocr', this.state.isScanA ? 1 : 0);
        formData.append('b_ocr', this.state.isScanB ? 1 : 0);
        formData.append('compare', this.state.displayOption);
        const uid = this.props.uid;
        formData.append('uid', uid);
        const fetch_url = this.props.serverIP + '/docompare';

        //console.log("uid: %s", uid);

        const stopController = new AbortController();
        // set progressing
        this.setState({
            compareStatus: 'progessing',
            compareProgress: true,
            leftItems: [],
            rightItems: [],
            stopController: stopController, // controller
            showSend: false, // show cancel
        });

        let compareStatus = ''; // compare status
        let compareProgress = false; // progress bar
        
        //console.log('before fetch status: %s, progress: %s.', this.state.compareStatus, this.state.compareProgress);
        
        const processing = 'processing...'; // processing status
        // call await fetch to guarantee fetch finishes before parallel to the rest code
        await fetch(fetch_url,
            {
                method: 'POST',
                // headers:{'Content-Type': 'multipart/form-data',}, do NOT set this content type header, flask gets f**ked cannot resolve content properly if so
                body: formData,
                credentials: 'include',
                //mode: 'cors',
                signal: stopController.signal,
            },
        )
        .then( (response) => {
                //console.log("response:");
                //console.log(response);
                if (! response) {
                    throw new Error("docompare fetch network error");
                }
                const reader = response.body.getReader();
                if (! reader){
                    throw new Error("fetch reader error");
                }
                return reader;
            })
            .then(( async (reader) =>{
                //let decoder = new TextDecoder();
                let leftover = null;
                let left = []; // holder for left items to be setState
                let right = [];// holder for right items      
                let result;      
                while(!(result = await reader.read()).done){
                    //console.log("while true...");
                    const done = result.done;
                    const data = result.value;
                    //const {done, value} = await reader.read();
                    //console.log('more reading...');
                    //let s = decoder.decode(value);
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

                                // console.log(object_json);

                                const left_chunk = object_json[this.state.aTargetName]; // get A part
                                const right_chunk = object_json[this.state.bTargetName];// get B part

                                left = (left.length>0) ? [...left, left_chunk] : [left_chunk];
                                right = (right.length>0) ? [...right, right_chunk]: [right_chunk];

                                // compare Status
                                compareStatus = processing;
                                compareProgress = true;
                                
                            } else{
                                compareProgress = false; // stop progress
                                if (status === 'end'){ // server sends 'end' regardless of any status
                                    if(compareStatus === processing){ // reset if no failure
                                        compareStatus = '';
                                    }
                                    break; // break loop
                                } else if(status ==='warning'){
                                    //compareStatus = status + '!! ' + header_json['reason'];
                                    compareStatus = status + '!! ' + "check log for the warning."
                                    console.log("warning: %s", header_json['reason']);
                                    // throw Error(compareStatus);
                                } else {
                                    // if failed
                                    //compareStatus = status + '!! ' + header_json['reason'];
                                    compareStatus = status + '!! ' + "check log for the error."
                                    console.log("not success, status: %s, reason: %s", status, header_json['reason']);
                                    throw Error(compareStatus);
                                }
                            }//
                        } // end for
                        //console.log(left);
                        this.setState( (prevState, props) => {
                            return {
                                leftItems: left,
                                rightItems: right,
                                compareStatus: compareStatus,
                                compareProgress: compareProgress,
                            };
                        });
                        //console.log('exit for status: %s, progress: %s. current state: %s', compareStatus, compareProgress, this.state.compareProgress);
                    }
                    //console.log('next while loop status: %s, progress: %s. current state: %s', compareStatus, compareProgress, this.state.compareProgress);
                }
                //console.log("i am done..");
            }))
            .catch((error) =>{
                let status = null;
                if (error.name === 'AbortError'){
                    //
                    console.log('....Aborted....');
                }
                else {
                    // error
                    console.error("onCompareFilesSubmit error:");
                    console.error(error);
                    status = "Error: " + error;
                }

                if (status){
                    status = "Error, check log for details.";
                }
                // reset
                this.setState(
                    {
                        compareStatus: status,
                        compareProgress: false,
                    }
                );
            })
            .then( ()=>{
                //console.log('after fetch status: %s, progress: %s. current state: %s', compareStatus, compareProgress, this.state.compareProgress);
            }
        );

        this.setState({
            showSend: true, // reset
        });
        //console.log("finished sip");
    }

    render(){
        // if file scanned, then only 'page' and 'document'
        const buttons = (this.state.isScanA || this.state.isScanB) ? this.state.buttonsScan : this.state.buttonsAll;
        //console.log("at render, compare progress: %s", this.state.compareProgress);
        //<Grid container display='flex' direction='row' height='100%' width='100%' sx={{ boxSizing: 'border-box', overflow: 'hidden'}}>
        return (
            <>
                <Grid container display='flex' flexDirection='row' height='100%' width='100%' sx={{boxSizing: 'border-box', overflow:'visible'}} border={0}>                
                    <Grid item  xs={12} md={3} p={1} height='100%' sx={{border:0}}>
                        <LeftPanel 
                            fontSizeSM={this.superState.fontSizeSM}
                            fontSizeMD={this.superState.fontSizeMD}
                            fontSizeXS={this.superState.fontSizeXS}
                            buttons={buttons} 
                            fileAName={this.state.fileAName}
                            aTargetName={this.state.aTargetName}
                            fileAValue={this.state.fileA}
                            fileBName={this.state.fileBName}
                            isScanA={this.state.isScanA}
                            isScanB={this.state.isScanB}
                            bTargetName={this.state.bTargetName}
                            fileBValue={this.state.fileB}
                            fileType={this.props.fileTypes}
                            buttonId={this.state.displayOption}
                            showSend={this.state.showSend}
                            onHandleFileChange={this.handleFileChange}
                            onHandleOptionChange={this.handleOptionChange}
                            onFilesSubmit={this.onCompareFilesSubmit}
                            onCheckScan={this.handleCheckScan}
                            onStop={this.handleStop}
                        />
                    </Grid>
                    <Grid item xs={12} md={9} padding={1} height='100%' >
                        <RightPanel 
                        fontSizeSM={this.superState.fontSizeSM}
                        fontSizeMD={this.superState.fontSizeMD}
                        fontSizeXS={this.superState.fontSizeXS}
                        leftItems={this.state.leftItems} 
                        rightItems={this.state.rightItems} 
                        compareStatus={this.state.compareStatus}
                        compareProgress={this.state.compareProgress}
                        filenameA={this.state.fileAName}
                        filenameB={this.state.fileBName}
                        pageLength={1000} 
                        pageCount={this.state.pageCount} 
                        currentPage={this.state.currentPage} 
                        onPageChange={this.handlePageChange}
                        /></Grid>
                </Grid>
            </>
        );
    }
}

export default DocompareMainPanel;
