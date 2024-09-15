/*
    Author: awtestergit
*/

import { Component, Fragment, createRef } from 'react';
import Box from '@mui/material/Box';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemText from '@mui/material/ListItemText';
import Grid from '@mui/material/Grid';
import ArrowForwardIosIcon from '@mui/icons-material/ArrowForwardIos';
import ArrowBackIosIcon from '@mui/icons-material/ArrowBackIos';
import IconButton  from '@mui/material/IconButton';
import CircularProgress from '@mui/material/CircularProgress';
import Stack from '@mui/material/Stack';
import ReactDOM from 'react-dom';
import Divider from '@mui/material/Divider';

class RightPanel extends Component{
    constructor(props){
        super(props);
        this.state = {
            // right box
            rSplit: '5%', // right
            lSplit: '95%', // left
            rSplitNoShow: '5%', // if show button is not clicked - no show source
            lSplitNoShow: '95%',
            rSplitShow: '40%', // if show button is clicked - show source
            lSplitShow: '60%',
            show: false,
          };


        this.refBox = createRef(); // auto scroll
        this.handleShowRightBox = this.handleShowRightBox.bind(this);    
    }

    componentDidUpdate(){
      const node = this.refBox.current;
      if (node){
        node.scrollTop = node.scrollHeight;
      }
    }

    handleShowRightBox(e){
      const newShow = !this.state.show;
      const newRSplit = this.state.show ? this.state.rSplitNoShow : this.state.rSplitShow;
      const newLSplit = this.state.show ? this.state.lSplitNoShow : this.state.lSplitShow;
        
      this.setState({
        show: newShow,
        rSplit: newRSplit,
        lSplit: newLSplit,
      });
    }


    render(){
      return (
        <>
          {(this.props.errorMessage && this.props.errorMessage.length >0) && <label style={{display: "block", textAlign: 'center', color:'red', fontSize:this.props.fontSizeMD}}>{this.props.errorMessage}</label>}
          {(this.props.showProgress && this.props.progressStatus.length>0) && ReactDOM.createPortal(<div style={{position: 'fixed', top: 0, left: '10%', width: '100%', height: '30%', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 9999}}><Stack direction='column' spacing={1}> {this.props.progressStatus}<CircularProgress sx={{width:'20%'}}/></Stack></div>, document.body)}
          <Box
            id='outer box'
            sx={{
              display: 'flex',
              flexDirection: 'row',
              width: '100%',
              height: '100%',
              border: '1px solid #ccc',
              borderRadius: '4px',
              padding: '1px',
            }}
          >              
              <Box ref={this.refBox} sx={{width:this.state.lSplit, height:'100%', maxHeight:'100%', overflowY:'auto'}} border={0}>
                <List sx={{width:'100%'}} spacing={1} >
                  {this.props.responseMessage.map((message, index) => (
                      <ListItem key={'bot_'+index.toString()} alignItems="flex-start" sx={{width:'100%', paddingTop:'0px', paddingBottom:'0px'}} >
                        <Grid container sx={{width: '100%', p:0}}>
                          { message.element.length > 0 &&
                          <>
                          <Grid item xs={4}>
                            <ListItemText 
                            primary={message.element} 
                            primaryTypographyProps={{paddingRight:'5px'}}
                            />
                          </Grid>
                          <Grid item xs={8}>
                            <ListItemText 
                              primary={message.detail} 
                              primaryTypographyProps={{paddingRight:'5px'}}
                              />
                          </Grid>
                          </>
                          }
                          {
                            message.element.length === 0 &&
                            <>
                            <Divider />
                            </>
                          }
                        </Grid>
                      </ListItem>
                    )
                  )}
                </List>
              </Box>
              <Box display='flex' flexDirection='column' sx={{width: this.state.rSplit, borderLeft:'1px solid #ccc', height:'100%'}}>
                <IconButton sx={()=>(this.state.show && {display:'none'})}  onClick={this.handleShowRightBox}>
                  <ArrowBackIosIcon />
                </IconButton>
                <IconButton sx={()=>(!this.state.show && {display:'none'})} onClick={this.handleShowRightBox}>
                  <ArrowForwardIosIcon />
                </IconButton>
                <Box display='flex' flexGrow={1} sx={{overflowY:'auto'}}>
                  <Grid container sx={{width: '100%', p:0}}>
                    <Grid item xs={12}>
                    { (this.state.show && this.props.sources.length>0) &&
                      <List sx={{width:'100%'}} spacing={1} >
                      {this.props.sources.map((source, index) => (
                          <ListItem key={'source_'+index.toString()} alignItems="flex-start" sx={{width:'100%', paddingTop:'0px', paddingBottom:'0px'}} >
                                <ListItemText 
                                primary={source} 
                                primaryTypographyProps={{paddingRight:'5px', fontSize:this.props.fontSizeSM}}
                                />
                              <Divider />
                          </ListItem>
                        )
                      )}
                      </List>
                    }
                    </Grid>
                  </Grid>
                </Box>
              </Box>
          </Box>
        </>
      );
    }      
}

export default RightPanel;

// create an AI chat dialog, contains a dialog box, a text input, a send button, a slider to set number of words. the dialog box shows AI chat on the left with avatar, with timestamp on each message, user chat on the right with avatar, with timestamp on each message

