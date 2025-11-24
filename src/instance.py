import osmnx as ox
import itertools as it
import networkx as nx
import requests
import src.solver
from src.config import *


def graph():

    G = ox.graph_from_place(
        PLACE,
        network_type='drive',
        simplify=False,
        retain_all=False,
        custom_filter=CUSTOM_FILTER
    )
    G = nx.subgraph(G, max(nx.strongly_connected_components(G), key=len))
    for u, rho in nx.pagerank(G).items():
        G.nodes[u]['rho'] = rho

    U = G.to_undirected()

    return G, U


def stops(U):

    stops_df = ox.features_from_place(PLACE, STOPS_TAGS).droplevel('element')
    stops_df = stops_df[stops_df['geometry'].geom_type == 'Point']
    stops_df['node'] = stops_df.apply(lambda stop: ox.nearest_nodes(U, stop.geometry.x, stop.geometry.y), axis=1)

    stops_ref_to_node = stops_df['node'].to_dict()
    stops = set(stops_ref_to_node.values())

    return stops, stops_ref_to_node


def st_pairs(U, **kwargs):

    if 'stops' in kwargs:
        stops = kwargs['stops']
    else:
        stops = None

    W = src.solver.cover(U, stops=stops)

    forbidden = dict()
    for s in W:
        forbidden[s] = set(
            nx.single_source_dijkstra_path_length(U, s, cutoff=FORBIDDEN_DST, weight='length').keys()
        ).intersection(W)
    st_pairs = []
    for s, t in it.combinations(W, 2):
        if t not in forbidden[s] and s not in forbidden[t]:
            st_pairs.append(tuple(sorted((s, t))))

    return W, st_pairs


def candidate_lines(G, U, st_pairs, stops_ref_to_node):

    current_query = """
    [out:json];
    area["name"="{0}"]["admin_level"="{1}"]->.searchArea;
    (
      relation["type"="route"]["route"="bus"](area.searchArea);
    );
    out body;
    """.format(PLACE, ADMIN_LEVEL)
    current_response = requests.get('http://overpass-api.de/api/interpreter', params={'data': current_query}).json()

    L, L_st = dict(), {(s, t): set() for s, t in st_pairs}
    idx = 0
    for element in current_response['elements']:
        ell_stop_seq = []
        for member in element['members']:
            if member['type'] == 'node':
                if member['ref'] in stops_ref_to_node.keys():
                    stop = stops_ref_to_node[member['ref']]
                    if not ell_stop_seq or ell_stop_seq[-1] != ell_stop_seq:
                        ell_stop_seq.append(stop)
        if len(ell_stop_seq) >= 2:
            ell = element['tags']['name']
            if ell_stop_seq[0] != ell_stop_seq[-1]:
                ell_stop_seq += ell_stop_seq[-2::-1]
            ell_length = 0
            ell_path = []
            for stop1, stop2 in zip(ell_stop_seq[:-1], ell_stop_seq[1:]):
                seg_length, seg_path = nx.single_source_dijkstra(G, stop1, stop2, weight='length')
                ell_length += seg_length
                ell_path.extend(seg_path[:-1])
            ell_path.append(ell_stop_seq[-1])
            ell_stops = set(ell_stop_seq)
            ell_coverage = set(
                nx.multi_source_dijkstra_path_length(U, ell_stops, weight='length', cutoff=WALKING_DST).keys()
            )
            ell_transfer_stops = ell_stops.intersection(ell_coverage)

            L[ell] = {
                'idx': idx,
                'length': ell_length,
                'path': ell_path,
                'stops': ell_stops,
                'stop_seq': ell_stop_seq,
                'coverage': ell_coverage,
                'transfer_stops': ell_transfer_stops
            }
            idx += 1

            for s, t in st_pairs:
                if s in ell_coverage and t in ell_coverage:
                    L_st[(s, t)].add(ell)

    C = tuple((ell, max(H)) for ell in L.keys())

    return L, L_st, C


def transfer_candidates(L):

    T = dict()

    for ell1, ell2 in it.combinations(L.keys(), 2):
        if not L[ell1]['transfer_stops'].isdisjoint(L[ell2]['transfer_stops']):
            coverage1 = L[ell1]['coverage']
            coverage2 = L[ell2]['coverage']
            jac = len(coverage1.symmetric_difference(coverage2)) / len(coverage1.union(coverage2))
            if jac >= JAC_DST:
                T[tuple(sorted((ell1, ell2)))] = jac

    return T
