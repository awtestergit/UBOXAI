/*
    awtestergit
    left panel for docompare
*/

import { Component } from "react";
import { Button } from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import StopIcon from '@mui/icons-material/Stop';
import Grid from '@mui/material/Grid';
import { FileUpload, DisplayButtons, ButtonSelect } from "../common";


class LeftPanel extends Component {

  render() {
    const buttonToShow = this.props.showSend ? <Button fullWidth onClick={this.props.onFilesSubmit} variant="contained" endIcon={<SendIcon />}>Submit</Button> : <Button fullWidth onClick={this.props.onStop} variant="contained" endIcon={<StopIcon />}>Stop</Button>;
    return (
      <form>
          <Grid container direction='column' columns={1} sx={{height: '100%', border:0}} >
            <Grid container columnSpacing={{sm:1}} sx={{width: '100%', overflow:'hidden'}} >
              <Grid item xs={12} py={2} sx={{fontSize:this.props.fontSizeMD}}>Upload file:</Grid>
              <Grid item xs={6} p={0}>
                <FileUpload 
                fontSize={this.props.fontSizeSM} 
                name={this.props.aTargetName} 
                fileName={this.props.fileAName}
                fileValue={this.props.fileValue}
                fileType={this.props.fileType} 
                onFileChange={this.props.onHandleFileChange}
                checkName={'left'}
                isScan={this.props.isScanA}
                onCheckScan={this.props.onCheckScan} 
                padding={1}/>
              </Grid>
              <Grid item xs={6} p={0}>
                <FileUpload 
                fontSize={this.props.fontSizeSM} 
                name={this.props.bTargetName} 
                fileName={this.props.fileBName} 
                fileValue={this.props.fileValue}
                fileType={this.props.fileType} 
                onFileChange={this.props.onHandleFileChange} 
                checkName={'right'} 
                isScan={this.props.isScanB}
                onCheckScan={this.props.onCheckScan} 
                padding={1}/>
              </Grid>
            </Grid>
            <Grid container  width='100%' rowSpacing={0} >
              <Grid item xs={12} py={2} sx={{fontSize:this.props.fontSizeMD}}>Compare by：</Grid>
              <Grid item xs={12} ><DisplayButtons fontSize={this.props.fontSizeXS} buttons={this.props.buttons} buttonId={this.props.buttonId} variant='contained' onClick={this.props.onHandleOptionChange} /></Grid>
            </Grid>
            <Grid item pt={3} xs={12} >{buttonToShow}</Grid>
          </Grid>
    </form>
    );
  }
}

export default LeftPanel;
