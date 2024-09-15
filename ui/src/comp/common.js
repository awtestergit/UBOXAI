/*
    awtestergit
    common functions
*/
import { Component, createContext, useContext, useState} from 'react';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import Card from '@mui/material/Card';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import ButtonGroup from '@mui/material/ButtonGroup';
import CardContent from '@mui/material/CardContent';
import Paper from '@mui/material/Paper';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemText from '@mui/material/ListItemText';
import Box from '@mui/material/Box';
import Container from '@mui/material/Container';
import Divider from '@mui/material/Divider';

import '../css/styles.css';

function FileUpload({fontSize, name, fileName, fileValue, fileType, onFileChange, checkName, isScan, onCheckScan, padding=1}){  
    let displayName = fileName.length > 0 ? fileName + " uploaded." : 'Only PDF/DOCX files.';
    
    // console.log("file upload check name, %s, checked: %s", checkName, checked.toString());

    return (
      <>
        <Card spacing={2} sx={{paddingTop: 2, paddingBottom:2, minHeight: '80px', '@media (min-width:600px)': { minHeight: '100px' }}}>
          <Grid container rowSpacing={{xs:1, sm:2}}>
            <Grid item xs={12} p={padding}>
              <Button
              component="label"
              variant="contained"
              startIcon={<CloudUploadIcon />}
              sx={{width: '100%', minHeight:'50px'}}
            >
              <Typography variant="caption" sx={{fontSize:fontSize}}>Upload file</Typography>
              <input type="file" accept={fileType} name={name} value={fileValue} onChange={onFileChange} style={{display : 'none'}} />
            </Button>
            </Grid>
            <Grid item xs={12}>
              <label style={{display: "block", textAlign: 'center', fontSize:fontSize}}>{displayName}</label>
            </Grid>
          </Grid>
        </Card>
      </>
    );
}
function MultipleFileUpload({fontSize, name, fileNames, fileType, onFileChange, checkName, onCheckScan, padding=1}){  

  return (
    <>
      <Card spacing={2} sx={{paddingTop: 2, paddingBottom:2, width:'100%', minHeight: '80px', '@media (min-width:600px)': { minHeight: '100px' }}}>
        <Grid container rowSpacing={{xs:1, sm:2}} sx={{width:'100%'}}>
          <Grid item xs={12} px={padding}>
            <Button
            component="label"
            variant="contained"
            startIcon={<CloudUploadIcon />}
            sx={{width: '100%', minHeight:'50px'}}
          >
            <Typography variant="caption" sx={{fontSize:fontSize}}>Upload file</Typography>
            <input type="file" multiple accept={fileType} name={name} onChange={onFileChange} style={{display : 'none'}} />
          </Button>
          </Grid>
          <Grid item xs={12}>
            <div style={{display:'flex', flexDirection:'column', alignItems: 'center', justifyContent:'center'}} >
            { (fileNames.length>0) &&
              <>
              <div style={{width:'100%', fontSize:fontSize, padding:'0px 0px 8px 32px'}}><label>Files uploaded:</label></div>
              <div style={{display:'flex', maxHeight:'200px', overflowY:'auto', alignItems: 'center', justifyContent:'center'}} >
              <List sx={{width:'100%'}} spacing={1} >
              {fileNames.map((source, index) => (
                  <ListItem key={'multiple_'+index.toString()} alignItems="flex-start" sx={{width:'100%', paddingTop:'0px', paddingBottom:'0px'}} >
                        <ListItemText 
                        primary={source} 
                        primaryTypographyProps={{paddingRight:'5px', fontSize:fontSize}}
                        />
                  </ListItem>
                )
              )}
              </List>
              </div>
              </>
            }
            {
              fileNames.length == 0 && 'Only PDF/DOCX files.'
            }
            </div>
          </Grid>
        </Grid>
      </Card>
    </>
  );
}

class BasePanel extends Component{
    constructor(props){
        super(props);
        this.state = {
            // font
            fontSizeXXS: 8, // 
            fontSizeXS: 10, // default xs font size
            fontSizeSM: 12, // default small font size
            fontSizeMD: 16, // default middle font size
            fontSizeLG: 18, // default large font size
            fontSizeXL: 24, // default xlarge font size
            // file
            fileType: '.docx, .doc, .pdf', // accepted file types
            fileMaxSize: 10, // 10MB
        };
        
        this.superState = this.state; // seems derived class cannot get the state from render(), so use this instead

        this.handleFontSize = this.handleFontSize.bind(this);
    }

    handleFontSize(){
        const adjuster = Math.max(10, window.innerWidth/80);
        const xxs = Math.min(8, adjuster-4); // 
        const xs = Math.min(10, adjuster-2); // 
        const sm = Math.min(12, adjuster);
        const md = Math.min(16, adjuster+2);
        const lg = Math.min(18, adjuster+2);
        //console.log("adjuster size: %d, sm: %d, md: %d, xs: %d, xxs: %d", adjuster, sm, md, xs, xxs);
        this.setState(
            {
                fontSizeXXS: xxs,
                fontSizeXS: xs,
                fontSizeSM: sm,
                fontSizeMD: md,
                fontSizeLG: lg,
            }
        );
    }

    componentDidMount(){
        // resize
        window.addEventListener('resize', this.handleFontSize);
        this.handleFontSize(); // initial
    }

    componentDidUpdate(){
        //this.handleFontSize(); no setState in update, infinite loop
    }

    componentWillUnmount(){
        window.removeEventListener('resize', this.handleFontSize);
    }
}

class BlockBase extends Component{
  //<Typography variant="body2" component='div' dangerouslySetInnerHTML={{__html: this.props.children}} />
  render(){
      // console.log(this.props.children);
      return (
          <>            
          <Card square elevation={0} sx={{width:'100%'}}>
              <CardContent>
                  <div style={{width:'100%', wordWrap:'break-word'}} dangerouslySetInnerHTML={{__html: this.props.children}} />
              </CardContent>
          </Card>
          </>
      );
  }
}

class BlockItem extends Component{
  constructor(props){
      super(props);
  }

  render() {
      return (
          <>
          <Paper square elevation={0} sx={{width:'100%'}}>
              {
                  this.props.items.length >0 && this.props.items.map( (item, index) => (
                      <BlockBase key={this.props.name+index}>{item}</BlockBase>
                  ))
              }
          </Paper>
          </>
      )
  }
}
/*
class BlockItem extends Component{
  constructor(props){
      super(props);
  }

  render() {
      return (
          <>
              {
                  this.props.items.length >0 && this.props.items.map( (item, index) => (
                      <div style={{width:'100%'}} key={this.props.name+index} dangerouslySetInnerHTML={{__html: item}} /> 
                  ))
              }
          </>
      )
  }
}
*/
class DisplayButtons extends Component {
  //
  constructor(props){
    super(props);
    this.state = {
      id_button_clicked: 0,
    };

    this.handleButtonClick = this.handleButtonClick.bind(this);
  }

  handleButtonClick(event, id, name){

    //this.setState( () =>{
    //  return {id_button_clicked: id};
    //});
    // call back
    this.props.onClick(event, id);
  }

  render() {
    const buttonId = this.props.buttonId;
    const fontSize = this.props.fontSize;

    return (
      //
      <>
        <ButtonGroup fullWidth  variant="contained">
          {
            this.props.buttons.map((item, index) => (
              <Button key={item} fullWidth onClick= {(event) => {this.handleButtonClick(event, index, item)}} variant={this.props.buttonVariant ? this.props.buttonVariant : (buttonId === index ? 'contained' : 'outlined')}>
                <Typography variant="caption" sx={{fontSize:fontSize}}>{item}</Typography>
              </Button>
            ))
          }
        </ButtonGroup>
      </>
    );
  }
}

// button context
const ButtonSelect = createContext(
  {
    buttonSelect: null,
  }
)
class ButtonSelectProvider extends Component{
  render() {
    // Container disableGuttters to remove default padding
    const buttons = <Container disableGutters sx={{px:0, paddingTop:2, paddingBottom:2}}><DisplayButtons 
    buttons={this.props.buttons} 
    onClick={this.props.onClick}
    buttonId={this.props.buttonId}
    fontSizeXS={this.props.fontSizeXS}
    fontSizeSM={this.props.fontSizeSM}
    fontSizeMD={this.props.fontSizeMD}
    fontSizeLG={this.props.fontSizeLG}
    fontSize={this.props.fontSize}
    textButton
    /></Container>;

    return (
      <ButtonSelect.Provider value={{buttonSelect: buttons}}>
        {this.props.children}
      </ButtonSelect.Provider>
    );
  }
}


function UboxAppMenu({ isMobile=false, onMenuClick, selectedIndex=0, onModelChange, models=['Qwen'], selectedModel=0}) {
  const pages = ['DocChat', 'DocTract', 'Docompare', 'DocKnow'];
  const settings = ['Profile', 'Account', 'Dashboard', 'Logout'];
  
  return (
      <Box width='100%' height='100%' sx={{display:'flex', flexDirection:'column', border: 0, bgcolor:'grey.300'}} >
      {isMobile && 
        <>
        <Box p={2} sx={{ display:'flex', flexDirection:'column', backgroundColor:'grey.400', alignItems: 'center', justifyContent: 'center'}}>
          <span style={{ color: '#0080FF', fontSize: '18px', fontWeight: 'bold' }}>UBOX-AI</span>
          <span style={{ color: '#0080FF', fontSize: '8px', fontWeight: 'bold' }}>AI in your box</span>
        </Box>
        <Box pt={1} sx={{ display:'flex', flexDirection:'row', justifyContent:'center' }}>
          {pages.map((page, index) => {
            const color = (index == selectedIndex) ? '#fafafa' : '#0080FF';
              return (
              <Button id={index} key={page} onClick={onMenuClick}>
                <span style={{fontSize: '14px', fontWeight: 'bold', color: color }}>{page}</span>
              </Button>
              );
            })
          }
        </Box>
        <Box pt={0} pb={1} px={2} sx={{display:'flex', flexDirection:'column'}}>
        { false &&
          <>
          <Divider />
          <Box py={1} display={'flex'} flexDirection={'row'} justifyContent={'center'}>
          <span style={{paddingTop:'4px', color:'#0080FF', fontSize: '10px'}}>selected model:</span>
          <select value={models[selectedModel]} onChange={onModelChange} style={{ width:'50%', fontSize: '10px', color:'#0080FF',  backgroundColor:'#f2f2f2'}}>
          {models.map((option, index) => (
              <option key={'read_' + index.toString()} id={index} value={option}>
              {option}
              </option>
          ))}
          </select>
          </Box>
          </>
        }
        <span style={{ textAlign:'center', color:'#0080FF', fontWeight:'bold', fontSize: '8px'}}>UBOX-AI, ver: 1.0</span>
        </Box>
      </>
      }
      { !isMobile &&
        <>
        <Box p={2} sx={{ display:'flex', flexDirection:'column', backgroundColor:'grey.400', alignItems: 'center', justifyContent: 'center'}}>
          <span style={{ color: '#0080FF', fontSize: '18px', fontWeight: 'bold' }}>UBOX-AI</span>
          <span style={{ color: '#0080FF', fontSize: '8px', fontWeight: 'bold' }}>AI in your box</span>
        </Box>
        <Box pt={4} pl={1} sx={{ display:'flex', flexDirection:'column', flexGrow:1, alignItems:'flex-start' }}>
              {pages.map((page, index) => {
                const color = (index == selectedIndex) ? '#fafafa' : '#0080FF';
                return (
                <Button id={index} key={page} onClick={onMenuClick}>
                  <span style={{fontSize: '14px', fontWeight: 'bold', color: color }}>{page}</span>
                </Button>
              );
            })
            }
        </Box>
        <Box p={2} sx={{display:'flex', flexDirection:'column'}}>
        { false &&
          <>
          <span style={{paddingLeft:'2px', color:'#0080FF', fontSize: '10px'}}>selected model:</span>
          <select value={models[selectedModel]} onChange={onModelChange} style={{fontSize: '10px', color:'#0080FF',  backgroundColor:'#f2f2f2'}}>
          {models.map((option, index) => (
              <option key={'read_' + index.toString()} id={index} value={option}>
              {option}
              </option>
          ))}
          </select>
          </>
        }
        <span style={{ textAlign:'center', color:'#0080FF', fontWeight:'bold', fontSize: '8px'}}>UBOX-AI, ver: 0.9</span>
        </Box>
        </>
      }
      </Box>
  );
}

function parse_text_to_html(text){
  const parsedText = text
    .replace(/\n/g, '<br>')
    .replace(/`/g, "\\`")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/ /g, "&nbsp;")
    .replace(/\*/g, "&ast;")
    .replace(/_/g, "&lowbar;")
    .replace(/-/g, "&#45;")
    .replace(/\./g, "&#46;")
    .replace(/!/g, "&#33;")
    .replace(/\(/g, "&#40;")
    .replace(/\)/g, "&#41;")
    .replace(/\$/g, "&#36;");

    return parsedText;
}

export {FileUpload, MultipleFileUpload, parse_text_to_html, UboxAppMenu, BasePanel, BlockBase, BlockItem, DisplayButtons, ButtonSelect, ButtonSelectProvider};