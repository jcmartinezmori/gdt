import osmnx as ox
import itertools as it
import networkx as nx
import numpy as np
import pandas as pd
import pickle
import requests
import src.solver
from src.config import *


def graphs():

    print('     Running graphs(*) ... ')

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
        U.nodes[s]['rho'] = 1 + sum(U.nodes[t]['feature_ct'] for t in nx.single_source_dijkstra_path_length(
            U, s, cutoff=WALK_DIST, weight='length').keys())
        G.nodes[s]['rho'] = U.nodes[s]['rho']

    B = U.to_directed()

    return G, U, B


def stop_nodes(U):

    print('     Running stop_nodes(*) ... ')

    stops_df = pd.read_csv('./data/{0}/stops.txt'.format(GTFS), delimiter=',').set_index('stop_id')
    stops_df['node'] = stops_df.apply(lambda stop: ox.nearest_nodes(U, stop.stop_lon, stop.stop_lat), axis=1)
    stop_nodes = stops_df['node'].to_dict()

    return stop_nodes


def walk_cover_st_pairs_and_dists(U, stop_nodes=None):

    print('     Running walk_cover_st_pairs_and_dists(*) ... ')

    W = src.solver.walk_cover(U, stop_nodes=stop_nodes)

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

    dists = {
        s: {t: length for t, length in nx.single_source_dijkstra_path_length(U, s, weight='length').items() if t in W}
        for s in W
    }

    return W, st_pairs, dists


def candidate_lines(G, U, B, stop_nodes, W, st_pairs, dists):

    print('     Running candidate_lines(*) ... ')

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
        ell_stop_seq = [stop_nodes[stop] for stop in ell_stop_seq]
        ell_stops = set(ell_stop_seq).intersection(W)
        ell_length = 0
        ell_path = []
        for stop1, stop2 in zip(ell_stop_seq[:-1], ell_stop_seq[1:]):
            ell_seg_length, ell_seg_path = nx.single_source_dijkstra(G, stop1, stop2, weight='length')
            ell_length += ell_seg_length
            ell_path.extend(ell_seg_path[:-1])
        ell_path.append(ell_stop_seq[-1])
        ell_walk = set(nx.multi_source_dijkstra_path_length(U, ell_stops, weight='length', cutoff=WALK_DIST).keys())
        ell_walk_cover = ell_walk.intersection(W)

        L[ell] = {
            'route_id': route_id,
            'stops': ell_stops,
            'length': ell_length,
            'path': ell_path,
            'walk': ell_walk,
            'walk_cover': ell_walk_cover
        }

        P = nx.compose(G.subgraph(set(ell_path)).copy(), B.subgraph(set(ell_walk)).copy())
        P_dists = {
            s: {t: length for t, length in
                nx.single_source_dijkstra_path_length(P, s, weight='length').items() if t in W}
            for s in W.intersection(P.nodes())
        }
        for s, t in st_pairs:
            if {s, t}.issubset(ell_walk_cover):
                if P_dists[s][t] <= DETOUR_FACTOR * dists[s][t]:
                    if P_dists[t][s] <= DETOUR_FACTOR * dists[t][s]:
                        L_st[(s, t)].add(ell)

        ell += 1
        print('         line count: {0}'.format(len(L)))

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
        p_q_walk = set(nx.multi_source_dijkstra_path_length(U, p_q_stops, weight='length', cutoff=WALK_DIST).keys())
        q_p_stops = set(q_p_path).intersection(W)  # could also be .intersection(stops)
        q_p_walk = set(nx.multi_source_dijkstra_path_length(U, q_p_stops, weight='length', cutoff=WALK_DIST).keys())

        ell_stops = p_q_stops.union(q_p_stops)
        ell_length = p_q_length + q_p_length
        ell_path = p_q_path + q_p_path[1:]
        ell_walk = p_q_walk.union(q_p_walk)
        ell_walk_cover = ell_walk.intersection(W)

        L[ell] = {
            'route_id': route_id,
            'stops': ell_stops,
            'length': ell_length,
            'path': ell_path,
            'walk': ell_walk,
            'walk_cover': ell_walk_cover,
        }

        P = nx.compose(G.subgraph(set(ell_path)).copy(), B.subgraph(set(ell_walk)).copy())
        P_dists = {
            s: {t: length for t, length in
                nx.single_source_dijkstra_path_length(P, s, weight='length').items() if t in W}
            for s in W.intersection(P.nodes())
        }
        for s, t in st_pairs:
            if {s, t}.issubset(ell_walk_cover):
                if P_dists[s][t] <= DETOUR_FACTOR * dists[s][t]:
                    if P_dists[t][s] <= DETOUR_FACTOR * dists[t][s]:
                        L_st[(s, t)].add(ell)

        ell += 1
        print('         line count: {0}'.format(len(L)))

    return L, L_st, C


def candidate_transfers(G, B, W, st_pairs, dists, L, L_st):

    print('     Running candidate_transfers(*) ... ')

    T, T_st = dict(), {(s, t): set() for s, t in st_pairs}

    for ell1, ell2 in it.combinations(L.keys(), 2):

        if not L[ell1]['stops'].isdisjoint(L[ell2]['stops']):

            ell1_walk_cover = L[ell1]['walk_cover']
            ell2_walk_cover = L[ell2]['walk_cover']
            ell1_and_ell2_walk_cover = ell1_walk_cover.intersection(ell2_walk_cover)

            ell1_ell2_walk_cover_overlap = len(ell1_and_ell2_walk_cover) / min(len(ell1_walk_cover), len(ell2_walk_cover))

            if ell1_ell2_walk_cover_overlap <= OVERLAP_THRESHOLD:

                ell1_or_ell2_walk_cover = ell1_walk_cover.union(ell2_walk_cover)

                P1 = nx.compose(G.subgraph(L[ell1]['path']).copy(), B.subgraph(L[ell1]['walk']).copy())
                P2 = nx.compose(G.subgraph(L[ell2]['path']).copy(), B.subgraph(L[ell2]['walk']).copy())
                P = nx.compose(P1, P2)

                P_dists = {
                    s: {t: length for t, length in
                        nx.single_source_dijkstra_path_length(P, s, weight='length').items() if t in W}
                    for s in W.intersection(P.nodes())
                }

                T[tuple(sorted((ell1, ell2)))] = {
                    'st_coverage': set()
                }
                for s, t in st_pairs:
                    if {s, t}.issubset(ell1_or_ell2_walk_cover):
                        if ell1 not in L_st[(s, t)] and ell2 not in L_st[(s, t)]:
                            if P_dists[s][t] <= DETOUR_FACTOR * dists[s][t]:
                                if P_dists[t][s] <= DETOUR_FACTOR * dists[t][s]:
                                    T[tuple(sorted((ell1, ell2)))]['st_coverage'].add((s, t))
                                    T_st[(s, t)].add(tuple(sorted((ell1, ell2))))

                print('         transfer count: {0}'.format(len(T)))

    return T, T_st


def load_instance(instance_filename):

    G = ox.load_graphml('./results/instances/G_{0}.graphml'.format(instance_filename))
    U = ox.load_graphml('./results/instances/U_{0}.graphml'.format(instance_filename))
    B = ox.load_graphml('./results/instances/B_{0}.graphml'.format(instance_filename))

    with open('./results/instances/stop_nodes_{0}.pkl'.format(instance_filename), 'rb') as file:
        stop_nodes = pickle.load(file)

    with open('./results/instances/W_{0}.pkl'.format(instance_filename), 'rb') as file:
        W = pickle.load(file)
    with open('./results/instances/st_pairs_{0}.pkl'.format(instance_filename), 'rb') as file:
        st_pairs = pickle.load(file)
    with open('./results/instances/dists_{0}.pkl'.format(instance_filename), 'rb') as file:
        dists = pickle.load(file)

    with open('./results/instances/L_{0}.pkl'.format(instance_filename), 'rb') as file:
        L = pickle.load(file)
    with open('./results/instances/L_st_{0}.pkl'.format(instance_filename), 'rb') as file:
        L_st = pickle.load(file)
    with open('./results/instances/C_{0}.pkl'.format(instance_filename), 'rb') as file:
        C = pickle.load(file)

    with open('./results/instances/T_{0}.pkl'.format(instance_filename), 'rb') as file:
        T = pickle.load(file)
    with open('./results/instances/T_st_{0}.pkl'.format(instance_filename), 'rb') as file:
        T_st = pickle.load(file)

    return G, U, B, stop_nodes, W, st_pairs, dists, L, L_st, C, T, T_st

