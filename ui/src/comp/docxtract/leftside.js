/*
    awtestergit
    left panel for docompare
*/
import { Component } from "react";
import { TextField, Grid, Button, Box, Stack } from "@mui/material";
import SendIcon from '@mui/icons-material/Send';
import StopIcon from '@mui/icons-material/Stop';
import Accordion from '@mui/material/Accordion';
import AccordionSummary from '@mui/material/AccordionSummary';
import AccordionDetails from '@mui/material/AccordionDetails';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import Typography from '@mui/material/Typography';
import { FileUpload, ButtonSelect } from "../common";

class LeftPanel extends Component{    
    render(){
        const buttonToShow = this.props.showSend ? <Button fullWidth disabled={this.props.disableSend} onClick={this.props.onSend} variant="contained" endIcon={<SendIcon />}>Extract</Button> : <Button fullWidth onClick={this.props.onCancel} variant="contained" endIcon={<StopIcon />}>Stop</Button>;
        return(
            <>
            <Box display='flex' flexDirection='column' sx={{width:'100%', height:'100%'}} border={0}>
                <Grid container columnSpacing={{sm:1}} border={0} sx={{width: '100%', paddingTop: 0, paddingBottom:2}} >
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
                                <select value={this.props.readOption[this.props.readBy]} onChange={this.props.onReadOption} style={{fontSize: this.props.fontSizeSM}}>
                                {this.props.readOption.map((option, index) => (
                                    <option key={'read_' + index.toString()} id={index} value={option}>
                                    {option}
                                    </option>
                                ))}
                                </select>
                            </Box>
                        </Grid>
                    </Grid>
                </Grid>
                <Stack direction={'column'} flexGrow={1}sx={{width:'100%', overflowY:'auto'}} >
                <Box sx={{width:'100%'}} >
                    <Accordion width='100%'>
                        <AccordionSummary
                        expandIcon={<ExpandMoreIcon />}
                        aria-controls="panel1a-content"
                        id="panel1a-header"
                        sx={{minHeight: 8}}
                        >
                        Extract by elements:
                        </AccordionSummary>
                        <AccordionDetails p={0} width='100%' sx={{padding:'2px'}} >
                        <Grid container display='flex' flexDirection='column' width='100%' p={0} sx={{border:0, boxSizing:'border-box'}}>
                            <Grid container width='100%' >
                                <Grid item p={0} xs={6}>
                                    <Button key='template_0' fullWidth component="label" variant={'text'}>
                                        <Typography variant="caption" sx={{fontSize:this.props.fontSizeXS}}>{this.props.buttons[0]}</Typography>
                                        <input type="file" accept={this.props.configType} onChange={(event) => {this.props.onTemplate(event, 0)}} style={{display : 'none'}} />
                                    </Button>
                                </Grid>
                                <Grid item p={0} xs={6}>
                                    <Button key='template_1' fullWidth component="label" variant={'text'} onClick={(event) => {this.props.onTemplate(event, 1)}}>
                                        <Typography variant="caption" sx={{fontSize:this.props.fontSizeXS}}>{this.props.buttons[1]}</Typography>
                                    </Button>
                                </Grid>
                            </Grid>
                            <Grid item display='flex' flexDirection='row' xs={12} p={0} pt='2px' sx={{boxSizing: 'border-box'}}>
                                <TextField multiline fullWidth border={0} rows={6} value={this.props.elements} onChange={this.props.onElementChange} ></TextField>
                            </Grid>
                        </Grid>
                        </AccordionDetails>
                    </Accordion>
                </Box>
                <Box sx={{width:'100%', bottom:0, position:'sticky'}} pt={2}>
                    {buttonToShow}
                </Box>
            </Stack>
            </Box>
            </>
        );
    }
}

export default LeftPanel;