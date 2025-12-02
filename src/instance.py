import osmnx as ox
import itertools as it
import networkx as nx
import numpy as np
import pandas as pd
import requests
import src.solver
from src.config import *


def graph():

    G = ox.graph_from_place(
        PLACE,
        network_type='drive',
        simplify=SIMPLIFY,
        retain_all=RETAIN_ALL,
        custom_filter=CUSTOM_FILTER
    )
    G = nx.subgraph(G, max(nx.strongly_connected_components(G), key=len))
    U = G.to_undirected()

    for s in U.nodes():

        U.nodes[s]['feature_ct'] = 0
        G.nodes[s]['feature_ct'] = U.nodes[s]['feature_ct']

        U.nodes[s]['walk_cover'] = set(
            nx.single_source_dijkstra_path_length(U, s, cutoff=WALK_COVER_FACTOR * WALK_DIST, weight='length').keys()
        )
        G.nodes[s]['walk_cover'] = U.nodes[s]['walk_cover']

    features_df = ox.features_from_place(PLACE, TAGS)
    for _, feature in features_df.iterrows():
        s = ox.nearest_nodes(U, feature.geometry.centroid.x, feature.geometry.centroid.y)
        U.nodes[s]['feature_ct'] += 1
        G.nodes[s]['feature_ct'] = U.nodes[s]['feature_ct']

    for s in U.nodes():

        U.nodes[s]['rho'] = 1 + sum(U.nodes[t]['feature_ct'] for t in nx.single_source_dijkstra_path_length(U, s, cutoff=WALK_TRIP_FACTOR * WALK_DIST, weight='length').keys())
        G.nodes[s]['rho'] = U.nodes[s]['rho']

    return G, U


def stops(U):

    stops_df = pd.read_csv('./data/{0}/stops.txt'.format(GTFS), delimiter=',').set_index('stop_id')
    stops_df['node'] = stops_df.apply(lambda stop: ox.nearest_nodes(U, stop.stop_lon, stop.stop_lat), axis=1)
    stops_id_to_node = stops_df['node'].to_dict()
    stops = set(stops_id_to_node.values())

    return stops, stops_id_to_node


def walk_cover_and_st_pairs(U, **kwargs):

    if 'stops' in kwargs:
        stops = kwargs['stops']
    else:
        stops = None

    W = src.solver.walk_cover(U, stops=stops)

    walk_trips = dict()
    for s in W:
        walk_trips[s] = set(
            nx.single_source_dijkstra_path_length(
                U, s, cutoff=WALK_TRIP_FACTOR * WALK_DIST, weight='length'
            ).keys()
        ).intersection(W)
    st_pairs = []
    for s, t in it.combinations(W, 2):
        if t not in walk_trips[s] and s not in walk_trips[t]:
            st_pairs.append(tuple(sorted((s, t))))

    return W, st_pairs


def candidate_lines(G, U, stops, stops_id_to_node, W, st_pairs):

    trips_df = pd.read_csv('./data/{0}/trips.txt'.format(GTFS), delimiter=',')
    stop_times_df = pd.read_csv('./data/{0}/stop_times.txt'.format(GTFS), delimiter=',')

    R = dict()
    L, L_st, ell = dict(), {(s, t): set() for s, t in st_pairs}, 0
    C = set()

    for (route_id, trip_id, direction_id), trip_df in trips_df.groupby(['route_id', 'trip_id', 'direction_id']):
        if route_id not in R:
            R[route_id] = {}
        if direction_id not in R[route_id]:
            R[route_id][direction_id] = tuple(stop_times_df[stop_times_df['trip_id'] == trip_id]['stop_id'])

    for route_id in R.keys():

        ell_stop_seq = []
        for ell_direction_stop_seq in R[route_id].values():
            ell_stop_seq.extend(ell_direction_stop_seq)
        ell_stop_seq = [stops_id_to_node[stop] for stop in ell_stop_seq]
        ell_stops = set(ell_stop_seq).intersection(W)
        ell_length = 0
        ell_path = []
        for stop1, stop2 in zip(ell_stop_seq[:-1], ell_stop_seq[1:]):
            ell_seg_length, ell_seg_path = nx.single_source_dijkstra(G, stop1, stop2, weight='length')
            ell_length += ell_seg_length
            ell_path.extend(ell_seg_path[:-1])
        ell_path.append(ell_stop_seq[-1])
        ell_coverage = set(
            nx.multi_source_dijkstra_path_length(U, ell_stops, weight='length', cutoff=WALK_DIST).keys()
        ).intersection(W)
        ell_transfer_stops = ell_stops.intersection(ell_coverage)

        L[ell] = {
            'route_id': route_id,
            'stops': ell_stops,
            'length': ell_length,
            'path': ell_path,
            'coverage': ell_coverage,
            'transfer_stops': ell_transfer_stops
        }

        for s, t in st_pairs:
            if s in ell_coverage and t in ell_coverage:
                L_st[(s, t)].add(ell)

        ell += 1

    for ell in L.keys():

        ell_trips_df = trips_df[trips_df['route_id'] == L[ell]['route_id']]
        ell_stop_times_df = stop_times_df[stop_times_df['trip_id'].isin(ell_trips_df['trip_id'])]
        ell_headways = []
        for _, ell_stop_times in ell_stop_times_df.groupby('stop_id'):
            ell_stop_arrival_times = pd.to_timedelta(
                ell_stop_times['arrival_time']
            ).drop_duplicates(keep='first').sort_values()
            ell_stop_headways = ell_stop_arrival_times.diff().dt.total_seconds().div(60).iloc[1:]
            ell_headways.extend(ell_stop_headways.to_list())
        h = min(H, key=lambda h: abs(h - np.mean(ell_headways)))
        C.add((ell, h))

    ell = len(L)
    for idx in range(NO_RANDOM_LINES):

        route_id = 'RANDOM-{0}'.format(idx)
        p, q = np.random.choice(list(W), size=2, replace=False)

        p_q_length, p_q_path = nx.single_source_dijkstra(G, source=p, target=q, weight='length')
        q_p_length, q_p_path = nx.single_source_dijkstra(G, source=q, target=p, weight='length')

        p_q_stops = set(p_q_path).intersection(W)  # could also be .intersection(stops)
        p_q_coverage = set(
            nx.multi_source_dijkstra_path_length(U, p_q_stops, weight='length', cutoff=WALK_DIST).keys()
        ).intersection(W)
        q_p_stops = set(q_p_path).intersection(W)  # could also be .intersection(stops)
        q_p_coverage = set(
            nx.multi_source_dijkstra_path_length(U, q_p_stops, weight='length', cutoff=WALK_DIST).keys()
        ).intersection(W)

        ell_stops = p_q_stops.union(q_p_stops)
        ell_length = p_q_length + q_p_length
        ell_path = p_q_path + q_p_path[1:]
        ell_coverage = p_q_coverage.intersection(q_p_coverage)
        ell_transfer_stops = ell_stops.intersection(ell_coverage)

        L[ell] = {
            'route_id': route_id,
            'stops': ell_stops,
            'length': ell_length,
            'path': ell_path,
            'coverage': ell_coverage,
            'transfer_stops': ell_transfer_stops
        }

        for s, t in st_pairs:
            if s in ell_coverage and t in ell_coverage:
                L_st[(s, t)].add(ell)

        ell += 1

    return L, L_st, C


def candidate_transfers(L, st_pairs):

    T, T_st = dict(), {(s, t): set() for s, t in st_pairs}

    for ell1, ell2 in it.combinations(L.keys(), 2):
        if not L[ell1]['transfer_stops'].isdisjoint(L[ell2]['transfer_stops']):
            ell1_coverage = L[ell1]['coverage']
            ell2_coverage = L[ell2]['coverage']
            ell1_ell2_st_coverage = {
                tuple(sorted((s, t)))
                for s, t in it.product(ell1_coverage - ell2_coverage, ell2_coverage - ell1_coverage)
            }.intersection(st_pairs)
            if ell1_ell2_st_coverage:
                T[tuple(sorted((ell1, ell2)))] = {
                    'ell1_ell2_st_coverage': ell1_ell2_st_coverage
                }
                for s, t in ell1_ell2_st_coverage:
                    T_st[(s, t)].add(tuple(sorted((ell1, ell2))))

    return T, T_st
