/*
    Author: awtestergit
*/

import { Component, createRef } from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Slider from '@mui/material/Slider';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemAvatar from '@mui/material/ListItemAvatar';
import Avatar from '@mui/material/Avatar';
import ListItemText from '@mui/material/ListItemText';
import Grid from '@mui/material/Grid';
import ArrowForwardIosIcon from '@mui/icons-material/ArrowForwardIos';
import ArrowBackIosIcon from '@mui/icons-material/ArrowBackIos';
import IconButton  from '@mui/material/IconButton';
import CircularProgress from '@mui/material/CircularProgress';
import Stack from '@mui/material/Stack';
import ReactDOM from 'react-dom';
import SendIcon from '@mui/icons-material/Send';
import StopCircleIcon from '@mui/icons-material/StopCircle';
import userImg from '../../images/user.png';
import botImg from '../../images/bot.png';
import { Divider } from '@mui/material';

class RightPanel extends Component{
    constructor(props){
        super(props);
        this.state = {
            maxWords: 1000, // max
            // right box
            rSplit: '25%', // right
            lSplit: '75%', // left
            minRSplit: '5%', // minimize split
            minLSplit: '95%',
            maxRSplit: '25%',
            maxLSplit: '75%',
            show: true,
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
      const newRSplit = this.state.show ? this.state.minRSplit : this.state.maxRSplit;
      const newLSplit = this.state.show ? this.state.minLSplit : this.state.maxLSplit;
      
      console.log("right box to be set as: %s, %s, %s", newShow, newRSplit, newLSplit);
      
      this.setState({
        show: newShow,
        rSplit: newRSplit,
        lSplit : newLSplit,
      });
    }


    render(){
      const toShow = this.state.show || this.props.isMobile;
      const msgRightBox = !toShow ? [] : this.props.sourceText; // blockitem items is an array
      const buttonToShow = this.props.showSend ? <Button variant="contained" sx={{height:'100%', width:'100%', fontSize:this.props.fontSizeSM}} onClick={this.props.onSendButton} endIcon={<SendIcon />}>Send</Button> : <Button variant="contained" sx={{height:'100%', width:'100%', fontSize:this.props.fontSizeSM}} onClick={this.props.onCancelButton} endIcon={<StopCircleIcon />}>Stop</Button>;
      const buttomBoxOverflow = this.props.isMobile ? 'none' : 'auto';
      const lSplit = this.props.isMobile ? '100%' : this.state.lSplit;
      const rSplit = this.props.isMobile ? '100%' : this.state.rSplit;
      return (
        <>
          {(this.props.showProgress && this.props.progressStatus.length>0) && ReactDOM.createPortal(<div style={{position: 'fixed', top: 0, right:'5%', width: '100%', height: '30%', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 9999}}><Stack direction='column' spacing={1}> {this.props.progressStatus}<CircularProgress sx={{width:'20%'}}/></Stack></div>, document.body)}
          <Box
            sx={{
              display: 'flex',
              flexDirection: this.props.isMobile ? 'column' : 'row',
              overflowY: this.props.isMobile ? 'auto' : 'none',
              width: '100%',
              height: this.props.isMobile ? 'auto' : '100%',
              border: '1px solid #ccc',
              borderRadius: '4px',
            }}
          >              
              <Box height='100%' sx={{ display: 'flex', flexDirection: 'column', width: lSplit}}>
                <Box
                  sx={{
                    flexGrow: 1,
                    overflowY: 'auto',
                    padding: '1px',
                    minHeight: '100px',
                  }}
                  border={0}
                  ref={this.refBox}
                >
                  <List spacing={1} >
                    {this.props.chatMessages.map((message, index) => (
                        (message.side=='bot') ?
                            <ListItem key={'bot_'+index.toString()} alignItems="flex-start" style={{paddingTop:'0px', paddingBottom:'0px'}} >
                              <ListItemAvatar>
                                <Avatar alt='AI' src={botImg} />
                              </ListItemAvatar>
                              <ListItemText 
                              primary={message.text} 
                              primaryTypographyProps={{paddingRight:'50px'}}
                              secondary={message.timestamp.toLocaleTimeString()} 
                              />
                            </ListItem>
                          :
                            (message.side=='user') &&
                            <ListItem key={'user_'+index.toString()} style={{padding:'0px'}}>
                              <ListItemText 
                              primary={message.text}
                              primaryTypographyProps={{align:'right', paddingRight:'5px'}}
                              secondary={message.timestamp.toLocaleTimeString()}
                              secondaryTypographyProps={{align:'right', paddingRight:'5px'}}
                              />
                              <ListItemAvatar>
                                <Avatar alt='XW' src={userImg} />
                              </ListItemAvatar>
                            </ListItem>
                       )
                    )}
                  </List>
                </Box>
                <Box
                  sx={{
                    position: 'sticky',
                    bottom: 0,
                    padding: '4px',
                    borderTop: '1px solid #ccc',
                  }}
                >
                  <Grid container sx={{width: '100%', boxSizing: 'border-box'}} border={0}>
                    <Grid item xs={12} sx={{boxSizing: 'border-box'}} border={0}>
                      <Grid container direction='row' width='100%' border={0}>
                        <Grid item sm={8.5} xs={12} pr={2} py={0.2} border={0}>
                          <input type='text' 
                            placeholder="Type your message..."
                            onKeyDown={this.props.onKeyDown}
                            onChange={this.props.onTextChange}
                            style={{ width:'100%', height:'100%', paddingLeft:'10px', border: '1px solid lightgray', borderRadius: '5px', fontsize: this.props.fontSizeMD}}
                            value={this.props.newMessage}
                          />  
                        </Grid>
                        {
                          this.props.isMobile && <Grid item>&nbsp;</Grid>
                        }
                        <Grid item display='flex' justifyContent='center' sm={1.5} xs={12} py={0.2} border={0} sx={{boxSizing: 'border-box'}} >
                        {buttonToShow}
                        </Grid>
                        <Grid item border={0} display='flex' sm={2} xs={12} fontSize={this.props.fontSizeXS} py={0} px={1} justifyContent='center'>
                          <Stack direction='column' flexGrow={1}>
                          <span style={{ marginRight:'3px', textAlign:'center', fontSize:this.props.fontSizeXS}}>Words: {this.props.numWords}</span>
                          <Slider
                              sx={{width:'100%', height:'2px'}}
                              defaultValue={this.props.numWords}
                              getAriaValueText= {() =>{return this.props.numWords;}}
                              valueLabelDisplay="auto"
                              marks
                              step={1}
                              min={50}
                              max={this.props.maxWords}
                              onChange={this.props.onWordNumber}
                          />
                          </Stack>
                        </Grid>
                      </Grid>
                    </Grid>
                  </Grid>
                </Box>
              </Box>
              <Box sx={{display: 'flex', flexDirection: 'column', height: this.props.isMobile ? 'auto' : '100%', overflowY: 'none',  fontSize:this.props.fontSizeXS, width: rSplit, borderLeft:'1px solid #ccc'}}>
              {!this.props.isMobile &&
                <>
                <IconButton sx={()=>(this.state.show && {display:'none'})} onClick={this.handleShowRightBox}>
                  <ArrowBackIosIcon />
                </IconButton>
                <IconButton sx={()=>(!this.state.show && {display:'none'})} onClick={this.handleShowRightBox}>
                  <ArrowForwardIosIcon />
                </IconButton>
                </>
                }
                <Box display='flex' flexGrow={1} sx={{height: this.props.isMobile ? 'auto' : '100%', overflowY: buttomBoxOverflow}}>
                  <Grid container sx={{width: '100%', p:0}}>
                    <Grid item xs={12}>
                    { (toShow && msgRightBox.length>0) &&
                      <List sx={{width:'100%'}} spacing={1} >
                      {msgRightBox.map((source, index) => (
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
//<Box display='flex' flexGrow={1} sx={{overflowY:'auto'}}>
//<BlockItem items={msgRightBox} name='msgRightBox' />
//</Box>

