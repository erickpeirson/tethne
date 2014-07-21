"""
Methods for analyzing :class:`.GraphCollection`\s.
"""

import networkx as nx
import types
import graph

def algorithm(C, method, **kwargs):
    """
    Apply NetworkX method to each ``Graph`` in :class:`.GraphCollection`\.

    Passes kwargs to specified NetworkX method for each Graph, and returns
    a dictionary of results indexed by element (node or edge) and graph index
    (e.g. ``date``).

    Parameters
    ----------
    C : :class:`.GraphCollection`
        The :class:`.GraphCollection` to analyze. The specified method will be
        applied to each :class:`.Graph` in **C**.
    method : string
        Name of a method in NetworkX to execute on graph collection.
    **kwargs
        A list of keyword arguments that should correspond to the parameters
        of the specified method.

    Returns
    -------
    results : dict
        A nested dictionary of results: results/elem(node or edge)/graph
        index.

    Raises
    ------
    ValueError
        If name is not in networkx, or if no such method exists.

    Examples
    --------

    *Betweenness centrality:*

    .. code-block:: python

       >>> import tethne.analyze as az
       >>> BC = az.collection.algorithm(C, 'betweenness_centrality')
       >>> print BC[0]
       {1999: 0.010101651117889644,
       2000: 0.0008689093723107329,
       2001: 0.010504898852426189,
       2002: 0.009338654511194512,
       2003: 0.007519105636349891}

    """

    results = {}

    if not method in nx.__dict__:
        raise(ValueError("No such name in networkx."))
    else:
        if type(nx.__dict__[method]) is not types.FunctionType:
            raise(ValueError("No such method in networkx."))
        else:
            for k, G in C.graphs.iteritems():
                r = nx.__dict__[method](G, **kwargs)
                for elem, value in r.iteritems():
                    try:
                        results[elem][k] = value
                    except KeyError:
                        results[elem] = { k: value }
                nx.set_node_attributes(G, method, r)    # [#61510128]
    return results

def delta(G, attribute):
    """
    Updates a :class:`.GraphCollection` with deltas of a node attribute.
    
    Parameters
    ----------
    G : :class:`.GraphCollection`
    attribute : str
        Name of a node attribute in ``G``.
    """
    import copy

    keys = sorted(G.graphs.keys())
    all_nodes =  G.nodes()
    deltas = { k:{} for k in keys }
    #n:{} for n in all_nodes }
    last = { n:None for n in all_nodes }
    
    for k in keys:
        graph = G[k]
        asdict = { v[0]:v[1] for v in graph.nodes(data=True) }
    
        for n in all_nodes:
            try:
                curr = float(asdict[n][attribute])
                if last[n] is not None and curr is not None:
                    delta = float(curr) - float(last[n])
                    last[n] = float(curr)
                elif last[n] is None and curr is not None:
                    delta = float(curr)
                    last[n] = float(curr)
                else:
                    delta = 0.
                deltas[k][n] = float(delta)
            except KeyError:
                pass
        nx.set_node_attributes(G[k], attribute+'_delta', deltas[k])

    return deltas

def connected(C, method, **kwargs):
    """
    Performs analysis methods from networkx.connected on each graph in the
    collection.

    Parameters
    ----------
    C : :class:`.GraphCollection`
        The :class:`.GraphCollection` to analyze. The specified method will be
        applied to each :class:`.Graph` in **C**.
    method : string
        Name of method in networkx.connected.
    **kwargs : kwargs
        Keyword arguments, passed directly to method.

    Returns
    -------
    results : dictionary
        Keys are graph indices, values are output of method for that graph.

    Raises
    ------
    ValueError
        If name is not in networkx.connected, or if no such method exists.

    Examples
    --------

    .. code-block:: python

        >>> import tethne.data as ds
        >>> import tethne.analyze as az
        >>> import networkx as nx
        >>> C = ds.GraphCollection()
        >>> # Generate some random graphs
        >>> for graph_index in xrange(1999, 2004):
        >>>     g = nx.random_regular_graph(4, 100)
        >>>     C[graph_index] = g
        >>> results = az.collection.connected(C, 'connected', k=None)
        >>> print results
        {1999: False,
        2000: False,
        2001: False,
        2002: False,
        2003: False }

    """

    results = {}

    if not method in nx.connected.__dict__:
        raise(ValueError("No such name in networkx.connected."))
    else:
        if type(nx.connected.__dict__[method]) is not types.FunctionType:
            raise(ValueError("No such method in networkx.connected."))
        else:
            for k, G in C.graphs.iteritems():
                results[k] = nx.connected.__dict__[method](G, **kwargs)
    return results

def node_global_closeness_centrality(C, node):
    """
    Calculates global closeness centrality for node in each graph in
    :class:`.GraphCollection` C.

    """

    results = {}
    for key, g in C.graphs.iteritems():
        results[key] = graph.node_global_closeness_centrality(g, node)

    return results
    
def attachment_probability(C):
    """
    Calculates the observed attachment probability for each node at each
    time-step.
    
    
    Attachment probability is calculated based on the observed new edges in the
    next time-step. So if a node acquires new edges at time t, this will accrue
    to the node's attachment probability at time t-1. Thus at a given time,
    one can ask whether degree and attachment probability are related.

    Parameters
    ----------
    C : :class:`.GraphCollection`
        Must be sliced by 'date'. See :func:`.GraphCollection.slice`\.
    
    Returns
    -------
    probs : dict
        Keyed by index in C.graphs, and then by node.
    """
    
    probs = {}
    G_ = None
    k_ = None
    for k,G in C.graphs.iteritems():
        new_edges = {}
        if G_ is not None: 
            for n in G.nodes():
                try:
                    old_neighbors = set(G_[n].keys())
                    if len(old_neighbors) > 0:
                        new_neighbors = set(G[n].keys()) - old_neighbors
                        new_edges[n] = float(len(new_neighbors))
                    else:
                        new_edges[n] = 0.
                except KeyError:
                    pass
    
            N = sum( new_edges.values() )
            probs[k_] = { n:0. for n in G_.nodes() }
            if N > 0.:
                for n in C.nodes():
                    try:
                        probs[k_][n] = new_edges[n]/N
                    except KeyError:
                        pass

            if probs[k_] is not None:
                nx.set_node_attributes(C.graphs[k_], 'attachment_probability', probs[k_])
    
        G_ = G
        k_ = k

    # Handle last graph (no values).
    key = C.graphs.keys()[-1]
    zprobs = { n:0. for n in C.graphs[key].nodes() }
    nx.set_node_attributes(C.graphs[key], 'attachment_probability', zprobs)

    return probs