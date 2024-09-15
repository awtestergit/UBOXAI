/*
    Author: awtestergit
*/

import io from 'socket.io-client';
import { BasePanel, ButtonSelectProvider, UboxAppMenu } from './comp/common';
import Container from '@mui/material/Container';
import Box from '@mui/material/Box';
import useTheme from '@mui/material/styles/useTheme';
import useMediaQuery from '@mui/material/useMediaQuery';
//import configData from './config.json';
import DocompareMainPanel from './comp/docompare/docomparePanel';
import DochatMainPanel from './comp/dochat/dochatPanel';
import DoctractMainPanel from './comp/docxtract/doctractPanel';
import DocknowMainPanel from './comp/docknow/docknowPanel';

import env from "react-dotenv";

// Create a Higher Order Component (HOC)
function withMediaQuery(Component) {
    return function WrappedComponent(props) {
      // Use the `useMediaQuery` hook inside the HOC
      const theme = useTheme();
      const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
      // Pass the `isMobile` as a prop to your component
      return <Component {...props} isMobile={isMobile} />;
    };
  }


class AppPanel extends BasePanel{
    constructor(props) {
        super(props);
        this.state = {
            errorMessage: '', // error message
            // constants
            host: '',
            // socket
            socket: null,
            // uid
            uid:123456,
            // session
            session: null,
            // button select
            buttonId: 0, // default
            buttons: ['dochat', 'doctract','docompare'],
            // file type allowed
            fileTypes: '.docx, .doc, .pdf',
            configType: '.cfg',
            // menu
            menuId: 0, // default
            //
            error: null,

            // handle Wix iframe
            loggedin: false,
            userId: '',
            userName: '',
        }

        this.handleErrorMessage = this.handleErrorMessage.bind(this);
        this.handleButtonSelect = this.handleButtonSelect.bind(this);
        this.handleAppMenu=this.handleAppMenu.bind(this);
    }

    handleAppMenu(event){
        const buttonId = parseInt(event.currentTarget.id); // currentTarget for Button, not target.id
        this.setState(
            {
                menuId: buttonId,
            }
        );
    }

    async componentDidMount() {
        //let serverIP;
        //let serverPort;
        //const serverIP = configData['server_ip'];
        //const serverPort = configData['server_port'];
        const serverIP = env.REACT_APP_UBOXAI_SERVER_IP; // get these from .env
        const serverPort = env.REACT_APP_UBOXAI_SERVER_PORT;
        //const serverIP = "127.0.0.1";
        //const serverPort = 5000;
        //console.log("server ip: %s, port: %s", serverIP, serverPort);
        const host = "http://" + serverIP + ":" + serverPort.toString();
        // server ip
        this.setState(()=> {
            return {host: host};
        });
        console.log("server ip: %s", host);
        // a psudo random uid
        let uid = new Date();
        uid = uid.getTime().toString();
        const random = Math.floor(Math.random() * (9999)) + 1000; // 4 digits
        uid += random.toString();
        const io_url = host + "?uid=" + uid;
        this.setState({uid: uid}); // set uid
        
        try{
            const socket = io(io_url, {secure:false}); // session to Socketio

            socket.on('error', (err)=>{
                const status = "Failed to connect server. " + err;
                console.log(status);
                this.setState(
                    {
                        errorMessage: status,
                    }
                );
            });
            // connect
            socket.on('connect', () =>{
                //
                console.log("socket connect");
            });

            socket.on('connect_error_data', (data) => {
                console.log('socket connect returns');
                const status = "Failed to connect server. " + data['error'];
                this.setState({
                    errorMessage: status,
                });
            });

            // message
            socket.on('message', (data)=>{
                console.log('socket message');
                console.log(data);
            }
            );
            // disconnect
            socket.on('disconnect', (data)=>{
                //
                console.log('socket disconnected');
                console.log(data);
            });

            // set state
            this.setState({
                socket: socket,
            });

            // test
            //const data = {'loggedIn': true, 'userId': 12345, 'userName': 'albert'}
            //socket.emit('message', data)

        } catch(error){
            const status = "Failed to connect server. " + error;
            
            console.log(status);
            
            this.setState(
                {
                    errorMessage: status,
                }
            );
        }
        
    }

    handleErrorMessage(msg){
        console.log(msg);
    }

    handleButtonSelect(event, id){
        console.log("app button to set id as: %d", id);
        this.setState({buttonId: id});
    }

    render(){
        if (this.state.errorMessage.length > 0 ){
            return (
                <>
                <label style={{display: "block", textAlign: 'center', color:'red', fontSize:this.superState.fontSizeXL}}>{this.state.errorMessage}</label>
                </>
            );
        }

        let display;
        if (this.state.menuId == 0){
            display = <DochatMainPanel uid={this.state.uid} serverIP={this.state.host} stopController={this.state.stopController} isMobile={this.props.isMobile} fileTypes={this.state.fileTypes} configType={this.state.configType} onStopController={this.state.handleStop} onError={this.handleErrorMessage}/>;
        } else if (this.state.menuId == 1){
            display = <DoctractMainPanel uid={this.state.uid} serverIP={this.state.host} stopController={this.state.stopController} isMobile={this.props.isMobile} fileTypes={this.state.fileTypes} configType={this.state.configType} onStopController={this.state.handleStop} onError={this.handleErrorMessage}/>;
        } else if (this.state.menuId == 2){
            display = <DocompareMainPanel uid={this.state.uid} serverIP={this.state.host} stopController={this.state.stopController} isMobile={this.props.isMobile} fileTypes={this.state.fileTypes} configType={this.state.configType} onStopController={this.state.handleStop} onError={this.handleErrorMessage}/>;
        } else if (this.state.menuId == 3){
            display = <DocknowMainPanel uid={this.state.uid} serverIP={this.state.host} stopController={this.state.stopController} isMobile={this.props.isMobile} fileTypes={this.state.fileTypes} configType={this.state.configType} onStopController={this.state.handleStop} onError={this.handleErrorMessage}/>;
        }
        //display = <DocwriteMainPanel uid={this.state.uid} serverIP={this.state.host} stopController={this.state.stopController} isMobile={this.props.isMobile} fileTypes={this.state.fileTypes} configType={this.state.configType} onStopController={this.state.handleStop} onError={this.handleErrorMessage}/>;
        //display = <DocknowMainPanel uid={this.state.uid} serverIP={this.state.host} stopController={this.state.stopController} isMobile={this.props.isMobile} fileTypes={this.state.fileTypes} configType={this.state.configType} onStopController={this.state.handleStop} onError={this.handleErrorMessage}/>;
        const height = this.props.isMobile ? 'auto' : '90vh';
        const width = this.props.isMobile ? '95vw' : '90vw';
        return (
                <ButtonSelectProvider buttons={this.state.buttons} 
                buttonId={this.state.buttonId} 
                fontSizeXS={this.superState.fontSizeXS}
                fontSizeSM={this.superState.fontSizeSM}
                fontSizeMD={this.superState.fontSizeMD}
                fontSizeLG={this.superState.fontSizeLG}
                fontSize={this.superState.fontSizeXS}
                onClick={this.handleButtonSelect} >
                <Container id='app-main' disableGutters
                    sx={{width: width, 
                        height: height, 
                        bgcolor: 'grey.100', 
                        alignItems: 'center', 
                        justifyContent: 'center',
                        border: "2px solid #a0aec0",
                        marginTop: '2%'}}
                >
                {this.props.isMobile &&
                <Box display={'flex'} flexDirection={'column'} sx={{width: '100%', height:'100%'}} >
                    <Box width={'100%'}>
                        <UboxAppMenu isMobile={this.props.isMobile} onMenuClick={this.handleAppMenu} selectedIndex={this.state.menuId} />
                    </Box>
                    <Box width={'100%'} flexGrow={1}>
                        {
                            display
                        }
                    </Box>
                </Box>        
                }
                {!this.props.isMobile &&
                <Box display={'flex'} flexDirection={'row'} sx={{width: '100%', height:'100%'}} >
                    <Box width={'12%'} height={'100%'}>
                        <UboxAppMenu onMenuClick={this.handleAppMenu} selectedIndex={this.state.menuId} />
                    </Box>
                    <Box width={'88%'} height={'100%'}>
                        {
                            display
                        }
                    </Box>
                </Box>
                }
                </Container>
                </ButtonSelectProvider>
        );
    }
}

export default withMediaQuery(AppPanel);
