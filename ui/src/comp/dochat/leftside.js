/*
    awtestergit
    left panel for docompare
*/
import { Component } from "react";
import Grid from '@mui/material/Grid';
import Box from '@mui/material/Box';
import { FileUpload, ButtonSelect } from "../common";

class LeftPanel extends Component{
    render(){
        return(
            <>
            <form>
            <Grid container rowSpacing={{xs:1, sm:2}} sx={{height:'100%', boxSizing: 'border-box'}} border={0}>
                <Grid container columnSpacing={{sm:1}} sx={{width: '100%', pl:0, paddingTop: 2, paddingBottom:2}} >
                    <Grid item xs={12} py={2} sx={{fontSize:this.props.fontSizeMD}}>Upload files:</Grid>
                    <Grid item sx={{width: '100%', ml:1, pr:1, pt:1, border: '1px solid #ccc'}} >
                        <Grid item xs={12} border={0} sx={{pl:0, pr:0}}>
                            <FileUpload
                            fontSize={this.props.fontSizeSM}
                            name={this.props.fileKeyName} 
                            fileName={this.props.fileName}
                            fileType={this.props.fileType}
                            onFileChange={this.props.onFileChange}
                            padding={1}
                            onCheckScan={this.props.onCheckScan}
                            />
                        </Grid>
                        <Grid item xs={12} p={2} border={0}>
                            <Box display={'flex'} flexDirection={'row'} sx={{width:'100%', paddingTop:'4px', justifyContent:'center', border: '0px solid #ccc',borderRadius: '4px',}} >
                                <span style={{fontSize: this.props.fontSizeSM}}>Parsing file by:</span>
                                <select value={this.props.readOption[this.props.readBy]} onChange={this.props.onReadOption} style={{fontSize: this.props.fontSizeSM}} >
                                {this.props.readOption.map((option, index) => (
                                    <option key={'read_' + index.toString()} id={index} value={option} >
                                        {option}
                                    </option>
                                ))}
                                </select>
                            </Box>
                        </Grid>
                    </Grid>
                </Grid>
            </Grid>
            </form>
            </>
        );
    }
}

export default LeftPanel;