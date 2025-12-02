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
        simplify=False,
        retain_all=False,
        custom_filter=CUSTOM_FILTER
    )
    G = nx.subgraph(G, max(nx.strongly_connected_components(G), key=len))
    U = G.to_undirected()

    for s in U.nodes():

        U.nodes[s]['walk_cover'] = set(
            nx.single_source_dijkstra_path_length(U, s, cutoff=WALK_COVER_FACTOR * WALK_DST, weight='length').keys()
        )
        G.nodes[s]['walk_cover'] = U.nodes[s]['walk_cover']

        U.nodes[s]['rho'] = len(U.nodes[s]['walk_cover'])
        G.nodes[s]['rho'] = U.nodes[s]['rho']

    return G, U


def stops(U):

    stops_df = ox.features_from_place(PLACE, STOPS_TAGS).droplevel('element')
    stops_df = stops_df[stops_df['geometry'].geom_type == 'Point']
    stops_df['node'] = stops_df.apply(lambda stop: ox.nearest_nodes(U, stop.geometry.x, stop.geometry.y), axis=1)

    stops_ref_to_node = stops_df['node'].to_dict()
    stops = set(stops_ref_to_node.values())

    return stops, stops_ref_to_node


def new_stops(U):

    stops_df = pd.read_csv('./data/tcat-ny-us/stops.txt', delimiter=',').set_index('stop_id')
    stops_df['node'] = stops_df.apply(lambda stop: ox.nearest_nodes(U, stop.stop_lon, stop.stop_lat), axis=1)
    stops_ref_to_node = stops_df['node'].to_dict()
    stops = set(stops_ref_to_node.values())

    return stops, stops_ref_to_node


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
                U, s, cutoff=WALK_TRIP_FACTOR * WALK_DST, weight='length'
            ).keys()
        ).intersection(W)
    st_pairs = []
    for s, t in it.combinations(W, 2):
        if t not in walk_trips[s] and s not in walk_trips[t]:
            st_pairs.append(tuple(sorted((s, t))))

    return W, st_pairs


def candidate_lines(G, U, stops, stops_ref_to_node, W, st_pairs):

    L, L_st = dict(), {(s, t): set() for s, t in st_pairs}
    C = set()
    idx = 0

    current_query = """
    [out:json];
    area["name"="{0}"]["admin_level"="{1}"]->.searchArea;
    (
      relation["type"="route"]["route"="bus"](area.searchArea);
    );
    out body;
    """.format(PLACE, ADMIN_LEVEL)
    current_response = requests.get('http://overpass-api.de/api/interpreter', params={'data': current_query}).json()

    for element in current_response['elements']:
        ell = element['tags']['name']
        if not all(tag in ell for tag in REQUIRED_LINE_TAGS) or any(tag in ell for tag in FORBIDDEN_LINE_TAGS):
            continue
        if ell == 'TCAT 21 Trumansburg - Commons':
            break
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
            ell_stops = set(ell_stop_seq).intersection(W)
            ell_coverage = set(
                nx.multi_source_dijkstra_path_length(U, ell_stops, weight='length', cutoff=WALK_DST).keys()
            ).intersection(W)
            ell_transfer_stops = ell_stops.intersection(ell_coverage)

            L[ell] = {
                'idx': idx,
                'length': ell_length,
                'path': ell_path,
                'stops': ell_stops,
                'coverage': ell_coverage,
                'transfer_stops': ell_transfer_stops
            }
            idx += 1

            for s, t in st_pairs:
                if s in ell_coverage and t in ell_coverage:
                    L_st[(s, t)].add(ell)

            if ell in C_FREQ:
                if C_FREQ[ell] is not None:
                    C.add((ell, C_FREQ[ell]))

    for i in range(NO_RANDOM_LINES):

        ell = 'r-{0}'.format(i)
        p, q = np.random.choice(list(W), size=2, replace=False)

        p_q_length, p_q_path = nx.single_source_dijkstra(G, source=p, target=q, weight='length')
        q_p_length, q_p_path = nx.single_source_dijkstra(G, source=q, target=p, weight='length')

        p_q_stops = set(p_q_path).intersection(W)  # could also be .intersection(stops)
        p_q_coverage = set(
            nx.multi_source_dijkstra_path_length(U, p_q_stops, weight='length', cutoff=WALK_DST).keys()
        ).intersection(W)
        q_p_stops = set(q_p_path).intersection(W)  # could also be .intersection(stops)
        q_p_coverage = set(
            nx.multi_source_dijkstra_path_length(U, q_p_stops, weight='length', cutoff=WALK_DST).keys()
        ).intersection(W)

        ell_length = p_q_length + q_p_length
        ell_path = p_q_path + q_p_path[1:]
        ell_stops = p_q_stops.union(q_p_stops)
        ell_coverage = p_q_coverage.intersection(q_p_coverage)
        ell_transfer_stops = ell_stops.intersection(ell_coverage)

        L[ell] = {
            'idx': idx,
            'length': ell_length,
            'path': ell_path,
            'stops': ell_stops,
            'coverage': ell_coverage,
            'transfer_stops': ell_transfer_stops
        }
        idx += 1

        for s, t in st_pairs:
            if s in ell_coverage and t in ell_coverage:
                L_st[(s, t)].add(idx)

    return L, L_st, C


def new_candidate_lines(G, U, stops, stops_ref_to_node, W, st_pairs):

    L, L_st = dict(), {(s, t): set() for s, t in st_pairs}
    C = set()
    idx = 0

    trips_df = pd.read_csv('./data/tcat-ny-us/trips.txt', delimiter=',')
    stop_times_df = pd.read_csv('./data/tcat-ny-us/stop_times.txt', delimiter=',')

    D = {}
    for (route_id, trip_id, direction_id), trip_df in trips_df.groupby(['route_id', 'trip_id', 'direction_id']):
        if route_id not in D:
            D[route_id] = {}
        if direction_id not in D[route_id]:
            D[route_id][direction_id] = tuple(stop_times_df[stop_times_df['trip_id'] == trip_id]['stop_id'])

    for ell in D.keys():

        ell_stop_seq = []
        for ell_direction_stop_seq in D[ell].values():
            ell_stop_seq.extend(ell_direction_stop_seq)
        ell_stop_seq = [stops_ref_to_node[stop] for stop in ell_stop_seq]
        ell_length = 0
        ell_path = []
        for stop1, stop2 in zip(ell_stop_seq[:-1], ell_stop_seq[1:]):
            seg_length, seg_path = nx.single_source_dijkstra(G, stop1, stop2, weight='length')
            ell_length += seg_length
            ell_path.extend(seg_path[:-1])
        ell_path.append(ell_stop_seq[-1])
        ell_stops = set(ell_stop_seq).intersection(W)
        ell_coverage = set(
            nx.multi_source_dijkstra_path_length(U, ell_stops, weight='length', cutoff=WALK_DST).keys()
        ).intersection(W)
        ell_transfer_stops = ell_stops.intersection(ell_coverage)

        L[idx] = {
            'name': ell,
            'length': ell_length,
            'path': ell_path,
            'stops': ell_stops,
            'coverage': ell_coverage,
            'transfer_stops': ell_transfer_stops
        }
        idx += 1

        for s, t in st_pairs:
            if s in ell_coverage and t in ell_coverage:
                L_st[(s, t)].add(ell)

    for ell in L.keys():
        ell_trips_df = trips_df[trips_df['route_id'] == ell]
        ell_stop_times_df = stop_times_df[stop_times_df['trip_id'].isin(ell_trips_df['trip_id'])]
        ell_headways = []
        for _, ell_stop_times in ell_stop_times_df.groupby('stop_id'):
            arrival_times = pd.to_timedelta(ell_stop_times['arrival_time']).drop_duplicates(keep='first').sort_values()
            headways = arrival_times.diff().dt.total_seconds().div(60).iloc[1:]
            ell_headways.extend(headways.to_list())
        h = min(H, key=lambda h: abs(h - np.mean(ell_headways)))
        C.add((ell, h))

    for i in range(NO_RANDOM_LINES):

        ell = 'r-{0}'.format(i)
        p, q = np.random.choice(list(W), size=2, replace=False)

        p_q_length, p_q_path = nx.single_source_dijkstra(G, source=p, target=q, weight='length')
        q_p_length, q_p_path = nx.single_source_dijkstra(G, source=q, target=p, weight='length')

        p_q_stops = set(p_q_path).intersection(W)  # could also be .intersection(stops)
        p_q_coverage = set(
            nx.multi_source_dijkstra_path_length(U, p_q_stops, weight='length', cutoff=WALK_DST).keys()
        ).intersection(W)
        q_p_stops = set(q_p_path).intersection(W)  # could also be .intersection(stops)
        q_p_coverage = set(
            nx.multi_source_dijkstra_path_length(U, q_p_stops, weight='length', cutoff=WALK_DST).keys()
        ).intersection(W)

        ell_length = p_q_length + q_p_length
        ell_path = p_q_path + q_p_path[1:]
        ell_stops = p_q_stops.union(q_p_stops)
        ell_coverage = p_q_coverage.intersection(q_p_coverage)
        ell_transfer_stops = ell_stops.intersection(ell_coverage)

        L[idx] = {
            'name': ell,
            'length': ell_length,
            'path': ell_path,
            'stops': ell_stops,
            'coverage': ell_coverage,
            'transfer_stops': ell_transfer_stops
        }
        idx += 1

        for s, t in st_pairs:
            if s in ell_coverage and t in ell_coverage:
                L_st[(s, t)].add(idx)

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
