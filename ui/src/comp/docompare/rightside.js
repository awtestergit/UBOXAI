/*
    awtestergit
    right panel for docompare
*/

import { Component } from "react";
import Grid from '@mui/material/Grid';
import Box from '@mui/material/Box';
import { Pagination } from "@mui/material";
import LinearProgress from '@mui/material/LinearProgress';
import { BlockItem } from "../common";


class RightPanel extends Component{
    //
    constructor(props){
        super(props);
    }

    render(){
        // calculate pagination
        const left_items = this.props.leftItems;
        const left_length = left_items.length;
        const right_items = this.props.rightItems;
        const right_length = right_items.length;
        const length_per_page = this.props.pageLength ? this.props.pageLength : 1000; // default 1000 words per page
        let pages = []; // holder for each page, [[leftItems, rightItems], [leftItems, rigthItems]...]
        // calculate page count
        const length = (left_length > right_length) ? right_length : left_length;
        let temp_length = 0;
        let current_index = 0; // track current index while looping
        for(var i=0; i<length; ++i){
            const l_len = left_items[i].length;
            const r_len = right_items[i].length;
            const larger = (l_len > r_len) ? l_len : r_len;
            temp_length += larger;
            if (temp_length >= length_per_page){
                let lefts = [];
                let rights = [];
                if (current_index == i){
                    //if the length of i is over length already
                    lefts = [left_items[i]]; // a list
                    rights = [right_items[i]];
                    current_index += 1;
                }
                else{ // else
                    lefts = left_items.slice(current_index, i); // the i-th index is not included
                    rights = right_items.slice(current_index, i);    
                    current_index = i; // track currrent index
                }
                pages.push([lefts, rights]);
                temp_length = 0; // reset
            }
        }
        // the current_index item has not been added yet
        if (current_index < length){ // if so
            const lefts = left_items.slice(current_index);
            const rights = right_items.slice(current_index);
            pages.push([lefts, rights]);
        }
        // any left overs
        temp_length = 0; // reset
        if (left_length > right_length){
            // left has more items
            for (var i=current_index; i<left_length; ++i){
                const l_len = left_items[i].length;
                temp_length += l_len;
                if (temp_length >= length_per_page){
                    let lefts = [];
                    if (current_index == i){
                        lefts = [left_items[i]]; // a list
                        current_index += 1;
                    }
                    else{
                        lefts = left_items.slice(current_index, i); // the i-th index is not included
                        current_index = i; // track currrent index
                    }
                    pages.push([lefts, []]); // right empty
                    temp_length = 0; // reset
                }
            }
            // the current_index item has not been added yet
            if (current_index < left_length){
                const lefts = left_items.slice(current_index);
                pages.push([lefts, []]);
            }   
        }

        if (right_length > left_length){
            // right has more items
            for (var i=current_index; i<right_length; ++i){
                const r_len = right_items[i].length;
                temp_length += r_len;
                if (temp_length >= length_per_page){
                    let rights = [];
                    if (current_index == i){
                        rights = [right_items[i]]; // a list
                        current_index += 1;
                    }
                    else{
                        rights = right_items.slice(current_index, i); // the i-th index is not included
                        current_index = i; // track currrent index
                    }
                    pages.push([[], rights]); // right empty
                    temp_length = 0; // reset
                }
            }
            // the current_index item has not been added yet
            if (current_index < right_length){
                const rights = right_items.slice(current_index);
                pages.push([[], rights]);
            }
        }
        const page_count = pages.length;
        const current_page = this.props.currentPage -1; // make the page index
        const left_items_to_display = page_count > 0 ? pages[current_page][0] : [];
        const right_items_to_display = page_count > 0 ? pages[current_page][1] : [];

        return (
            //
            <Box sx={{ display:'flex', flexDirection:'column', height: '100%', width:'100%', border:'1px solid #ccc'}} >
                <Box sx={{width:'100%', height:'auto'}}>
                    {
                        this.props.compareStatus && <label style={{display: "block", textAlign: 'center', color:'red', fontSize:this.props.fontSizeMD}}>{this.props.compareStatus}</label>
                    }
                    {
                        (this.props.compareProgress) && <div style={{display: "flex", width:'100%', justifyContent: 'center', alignItems:'center'}}><LinearProgress sx={{width:'20%'}}/></div>
                    }
                    <Grid container direction='row' spacing={1} sx={{width:'100%'}} >
                        <Grid item py={1} xs={6}>
                            <Grid item xs={12}>
                                <label style={{display: "block", textAlign: 'center', fontSize:this.props.fontSizeMD}}>{this.props.filenameA}</label>
                            </Grid>
                        </Grid>
                        <Grid item py={1} xs={6}>
                            <Grid item xs={12}>
                                <label style={{display: "block", textAlign: 'center', fontSize:this.props.fontSizeMD}}>{this.props.filenameB}</label>
                            </Grid>
                        </Grid>
                    </Grid>
                </Box>
                <Box flexGrow={1} sx={{width:'100%', overflowY:'auto', border:0}} >
                    <Grid container direction='row' spacing={1} sx={{width:'100%'}} >
                        <Grid item xs={6}>
                            <Grid item xs={12} p={0} border={0}>
                                <BlockItem name='left' items={left_items_to_display}></BlockItem>
                            </Grid>
                        </Grid>
                        <Grid item xs={6}>
                            <Grid item xs={12}>
                                <BlockItem name='right' items={right_items_to_display}></BlockItem>
                            </Grid>
                        </Grid>
                    </Grid>
                </Box>
                <Box sx={{display:'flex', width:'100%', height:'auto'}} alignItems='center' justifyContent='center' p={0.5} border={0} >
                    { (page_count > 1) &&
                        <Pagination count={page_count} 
                        page={this.props.currentPage} 
                        onChange={this.props.onPageChange} 
                        variant="outlined" shape="rounded" color="primary" size="small" 
                        showFirstButton showLastButton />
                    }
                </Box>
            </Box>
        );
    }
}

export default RightPanel;