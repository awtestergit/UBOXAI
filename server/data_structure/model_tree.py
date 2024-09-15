# -*- coding: utf-8 -*-

"""
    use tree structure for long contexts, e.g, multiple files, or very long contents
    Paper: "WALKING DOWN THE MEMORY MAZE: BEYOND CONTEXT LIMIT THROUGH INTERACTIVE READING"
    R-tree/KNN: use cosine to create similarity at  each layer, so that relevant contexts are close and more likely to be selected by LLM
    
    Author: awtestergit
"""

import logging

class tree_node():
    def __init__(self, parent=None, children=[], item='', encoding=None, node_type=1, leaf='') -> None:
        self.parent = parent # parent
        self.add_children(children=children) # children and assign parent
        self.item = item # summary
        self.encoding = encoding #the encoding of item (summary)
        self.node_type = node_type # root: 0, leaf: -1, node: 1
        self.leaf = leaf # leaf string
        self.index = -1 # as a child, which index in the parent's children list
        ### for auxiliary usage ###
        self.pos = 0 # for example, sorting use, search use etc

    def add_children(self, children=[]):
        """
        add children to self,
        and assign self to children' parent
        """
        if len(children) > 0:
            self.children = children
            # the parent of children
            for idx, child in enumerate(children):
                child.parent = self # parent
                child.index = idx #index
        else:
            self.children = []


class model_tree():
    def __init__(self, fn_summary, fn_encode, fn_distance, fn_eval, k:int=3, MAX:int=512) -> None:
        self.root = tree_node(node_type=0) # root 0
        self.k = k # number of children per parent
        self.MAX = MAX # max length of the leaf string
        self.fn_summary = fn_summary # summary function of LLM
        self.fn_encode = fn_encode # encoding function
        self.fn_distance = fn_distance # calculate distance, e.g, cosine - must work with the fn_encode
        self.fn_eval = fn_eval # evaluate function

    def create_psudo_tree(self, text:str)->tree_node:
        """
        given a text, create a psude tree,
        in case of short file, no need to create a tree
        """
        child = tree_node(parent=self.root, node_type=-1, item=text, encoding=self.fn_encode(text), leaf=text)
        self.root.add_children(children=[child])
        return self.root

    def create_tree(self, inputs:list)->tree_node:
        """
        bottom up to generate each layer of nodes, till fewer than k nodes left where to use root to points to these few nodes and done
        """
        if len(inputs) == 0:
            return None
        
        current_layer = [] # to hold current layer of nodes, [[n1, n2, n3],[n4, n5, n6],[n7, n8]]
        # create leaves, quite expensive operation because of the summary call
        summaries = []
        summaries = [self.fn_summary(_input) for _input in inputs]
        encodings = [self.fn_encode(_input) for _input in inputs]
        current_layer = [tree_node(node_type=-1, item=summaries[idx], encoding=encodings[idx], leaf=input) for idx, input in enumerate(inputs)] # leaf -1
        logging.debug(f"create_tree, the number of leaf nodes is: {len(summaries)}")

        while (True):
            node_list = self.get_knn(inputs=current_layer, k = self.k) #  is a list of node list (current_layer) that are sorted by knn, [[n1, n2, n3],[n4, n5, n6],[n7, n8]]
            current_layer = []
            for nodes in node_list: # create a new layer
                input = '\n\n'.join(node.item for node in nodes) # concat the summaries
                summary = self.fn_summary(input) # summarize, expensive
                new_node = tree_node(item=summary, encoding=self.fn_encode(summary), children=nodes) # create new node, add children & assign node to be parent of children
                current_layer.append(new_node) # hold the new nodes

            if len(current_layer) <= self.k: # reach the first layer of children
                self.root.add_children(children = current_layer) # add children & assign node to be parent of children
                break # done, break the loop
            # else, continue

        return self.root

    def get_knn(self, inputs:list, k:int=3, descend=True)->list:
        """
        inputs: a list of tree nodes, to be sorted by distance
        the k, the k number of items in one cluster
        """
        results = []
        
        if len(inputs) == 0:
            return []
        
        # base
        if len(inputs) <= k:
            output = [item for item in inputs] # item
            results.append(output) #result append [[a,b,c]]
            return results

        left_knn, mid_knn, right_knn = [], [], []

        # sort the list by distance to the item @ index, new list is [item, 1-nearest, 2nd, 3rd ...], index -1 is the furthest
        # remember the sorted index, so that order can be restored after the furthest node's sorting
        inputs = self.sort_by_distance_to_item(inputs, index=0, remember_pos=True, descend=descend) # get the furthest item, and the list sorted by distance to the first item
        # get the k items close to left_most
        left_knn, inputs = self.get_nearest_and_pop(inputs, k) # get left_knn and two neighbors, and pop them from the inputs

        if len(inputs) > 0:
            # now sort the list by distance to the item @ index -1
            new_inputs = []
            new_inputs = self.sort_by_distance_to_item(inputs, index=-1, descend=descend)
            right_knn, new_inputs = self.get_nearest_and_pop(new_inputs, k) # get right_knn and two neighbors, and pop them from the inputs
            
            # restore the new_inputs by the sorted original inputs's remembered position, so that next round's left_knn is still close to this left_knn
            if len(new_inputs) > 0:
                new_inputs.sort(key=lambda x: x.pos) # restore the order to 'inputs'

                # recursive call to get the middle
                mid_knn = self.get_knn(new_inputs, k)

        if len(left_knn) > 0:
            results.append(left_knn)
        if len(mid_knn) > 0:
            results.extend(mid_knn) #note: extend, not append, as mid_knn is a list as well
        if len(right_knn) > 0:
            results.append(right_knn)

        return results

    def sort_by_distance_to_item(self, inputs:list, index:int, descend=True, remember_pos=False)->list:
        """
        sort the node list by distance to node @ index
        descending order by default
        remember_pos: whether to use node.pos to track the sorted position (index)
        """
        if len(inputs) == 0:
            return []

        output = []
        node = inputs[index]
        inputs.pop(index) # remove from the inputs
        node_encoded = self.fn_encode(node.item) if node.encoding is None else node.encoding # get the encode of node item
        max = 999999999 # if cosine, the 1 means similar, 0 means not
        output.append([max, node]) #the 0: distance, -1: item
        for node in inputs: # create new list by distance
            _encode = self.fn_encode(node.item) if node.encoding is None else node.encoding # encode
            distance = self.fn_distance(node_encoded, _encode) # calculate distance
            output.append([distance, node])
        # sort by distance, descending order
        output.sort(key=lambda k : k[0], reverse=descend)
        # return node list
        _output = []
        for idx, item in enumerate(output):
            if remember_pos: # remember the index
                item[-1].pos = idx # [-1] is the node itself
            _output.append(item[-1])
        return _output
    
    def get_nearest_and_pop(self, inputs:list, k:int)->tuple[object, list]:
        """
        inputs: sorted list
        item: to find nearest k-1 items
        k: k 
        output: list of k items, inputs w/ these k items poped
        """
        if len(inputs) == 0:
            return (None, [])

        items = []
        output = []
        
        if len(inputs) > k:
            for i in range(0,k):
                items.append(inputs.pop(0)) # the first k items
            output = inputs # the leftover
        else: # no need to do anything else
            items = inputs
            # output = []
        
        return items, output
    
    def __reset_tree__(self, node:tree_node):
        """
        to reset all node's auxiliary value
        """
        if node == None:
            return
        
        default = -100
        # in-order
        node.pos = default
        for n in node.children:
            self.__reset_tree__(n)

    def reset_tree(self):
        return self.__reset_tree__(self.root)

    def get_top_k(self, query, k:int, original_text=False, fuzz=False)->list:
        """
        traverse the tree from self.root, evaluate the current node and decide where to go next
        fn_eval: call back function, 
                input: [str1, str2, ...]
                    query: query tensor
                output:must return an index as the best evaluated children's index, or -1 to parent
        k: k results to return to, 
        original_text: if True, evaluate against the original_text instead of summary at leaf
        fuzz: if True, if a leaf is selected after evaluation, all other siblings will be selected without further processing
        output: as in [(str, encoding), (str, encoding)...]
        """
        results = []
        self.__reset_tree__(self.root) # reset the pos value

        self.__top_k__(query=query, node=self.root, fn_eval=self.fn_eval, k=k, results=results, original_text=original_text, fuzz=fuzz)
        return results

    def __top_k__(self, query, node:tree_node, fn_eval, k:int, results:list, original_text=False, fuzz=False):
        """
        node: tree node
        fn_eval: 
                input: list of index, str: [[index, str1, Tensor], [index, str2, Tensor], ...]
                    query tensor
                output:return child index, or -1 to indicate back to parent
        k, k results
        results: the list holding the top k results, as in [(str, encoding), (str, encoding)...]
        original_text: if False, only evaluate on summary of the leaf node (self.item), if True, evaulate on the original leaf context (self.leaf)
        fuzz: if True, if a leaf is selected after evaluation, all other siblings will be selected without further processing
        """
        if node is None:
            return
        if len(results) == k: # found k results
            return
        """
        color the node: the self.pos value
            -100: default value
            0: visiting
            1: done, do not eval anymore
            2: rejected, do not eval anymore
        """
        # color: 0
        node.pos = 0

        # call each child
        # input strings, if summary_only, use self.leaf
        available_children = list(filter(lambda x : x.pos <= 0, node.children)) # only children with color <=0
        inputs = []
        index = -1 # which node LLM thinks relevant
        if len(available_children) > 0:
            for nd in available_children:
                if fuzz: # index, item, not care of leaf, the original text
                    inputs.append([nd.index, nd.item, nd.encoding])
                else: # if not fuzz, self.leaf if leaf & original_text
                    inputs.append([nd.index, nd.leaf if (nd.node_type == -1 and original_text) else nd.item, nd.encoding]) # self.leaf if leaf & original_text
                nd.pos = 0 # color
            # evaluate the children' summary/context
            # inputs: [[index, str1, Tensor], [index, str2, Tensor]...]
            index = fn_eval(inputs, query)
        else: # no available children anymore
            node.pos = 1 # color done
            index = -1 # move to parent
        
        # assign node according to index value
        if index == -1: # if evaluate says -1, meaning this node is rejected, and return to parent
            node.pos = 2 if node.pos <= 0  else node.pos # rejected or done
            node = node.parent # move to parent (1)
        elif index >= 0: # found a good match
            assert index < len(node.children)
            assert node.pos <= 0 # not colored done yet

            child:tree_node = node.children[index] # the child @ index is a match
            if child.node_type == -1: # leaf
                if len(results) < k: # if not k yet
                    results.append((child.leaf, child.encoding)) # the original text, encoding
                # color the child
                child.pos = 1 # done
                # if fuzz, add all siblings
                if fuzz:
                    for idx, child in enumerate(node.children): # add all siblings
                        if idx != index:
                            if len(results) < k: # if not k yet
                                results.append((child.leaf, child.encoding))
                    node.pos = 1 # color the node, done
                    node = node.parent # move to parent (2)
                #else:
                    # node = node # move to self (2)
            else:
                node = child # move on to this child (3)

        # if here, recursively call, node is node self, or parent, or child
        return self.__top_k__(query=query, node=node, fn_eval=fn_eval, k=k, results=results, original_text=original_text, fuzz=fuzz)

    def __print_tree__(self, node:tree_node, level:int):
        """
        debug print
        """
        print(f"current level: {level}\n")
        spaces = "***"
        for i in range(level):
            spaces += "***"
        spaces += "\n"
        
        children = node.children
        s, c = '', ''
        for idx, child in enumerate(children):
            s += f"child node: {idx}; {child.item} {spaces}"
            if child.node_type == -1: #leaf
                c += f"child node leaf: {idx}; {child.leaf} {spaces}"
        if len(s) > 0:
            print(f"{s}\n")
        if len(c) > 0:
            print(f"{c}\n")

        level += 1
        for child in children:
            self.__print_tree__(child, level=level)
