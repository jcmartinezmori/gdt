import osmnx as ox
import geopandas as gpd
import itertools as it
import networkx as nx
import numpy as np
import pandas as pd
import pickle
import requests
from shapely.geometry import Point, MultiPoint
import src.solver
from src.config import *
np.random.seed(0)


def __from_polygon():

    shapes_df = pd.read_csv('./data/{0}/shapes.txt'.format(GTFS), sep=',')
    latlon_points = list(zip(shapes_df['shape_pt_lat'], shapes_df['shape_pt_lon']))

    gdf = gpd.GeoDataFrame(
        geometry=[Point(lon, lat) for lat, lon in latlon_points],
        crs='EPSG:4326'
    )
    utm_crs = ox.projection.project_gdf(gdf).crs
    gdf_proj = gdf.to_crs(utm_crs)
    hull_proj = MultiPoint(list(gdf_proj.geometry)).convex_hull
    hull_buffered_proj = hull_proj.buffer(WALK_TRIP_FACTOR * WALK_DIST)
    polygon = gpd.GeoSeries([hull_buffered_proj], crs=utm_crs).to_crs("EPSG:4326").iloc[0]

    return polygon


def get_graphs(from_polygon=True):

    print('     Running get_graphs(*) ... ')

    if from_polygon:
        polygon = __from_polygon()
        G = ox.graph_from_polygon(
            polygon,
            network_type='drive',
            simplify=SIMPLIFY,
            retain_all=RETAIN_ALL,
            custom_filter=CUSTOM_FILTER
        )
        features_df = ox.features_from_polygon(polygon, TAGS)
    else:
        G = ox.graph_from_place(
            PLACE,
            network_type='drive',
            simplify=SIMPLIFY,
            retain_all=RETAIN_ALL,
            custom_filter=CUSTOM_FILTER
        )
        features_df = ox.features_from_place(PLACE, TAGS)

    G = nx.subgraph(G, max(nx.strongly_connected_components(G), key=len))

    for _, data in G.nodes(data=True):
        data['lon'] = data['x']
        data['lat'] = data['y']
    G = ox.projection.project_graph(G)

    U = G.to_undirected()

    features_df = ox.projection.project_gdf(features_df)
    features_df['building:levels'] = pd.to_numeric(features_df['building:levels'], errors='coerce').fillna(1)

    for s in U.nodes():
        U.nodes[s]['feature_ct'] = 0
        G.nodes[s]['feature_ct'] = U.nodes[s]['feature_ct']

    for idx, s in enumerate(
            ox.distance.nearest_nodes(U, features_df['geometry'].centroid.x, features_df['geometry'].centroid.y)
    ):
        U.nodes[s]['feature_ct'] += features_df.iloc[idx]['building:levels']
        G.nodes[s]['feature_ct'] = U.nodes[s]['feature_ct']

    B = U.to_directed()

    return G, U, B


def get_stop_nodes(U):

    print('     Running get_stop_nodes(*) ... ')

    stops_df = pd.read_csv('./data/{0}/stops.txt'.format(GTFS), delimiter=',').set_index('stop_id')

    stops_gdf = gpd.GeoDataFrame(
        stops_df,
        geometry=gpd.points_from_xy(stops_df['stop_lon'], stops_df['stop_lat']),
        crs='EPSG:4326'
    )
    stops_gdf_proj = stops_gdf.to_crs(U.graph['crs'])

    stops_df['node'] = ox.distance.nearest_nodes(
        U, stops_gdf_proj.geometry.centroid.x, stops_gdf_proj.geometry.centroid.y
    )
    stop_nodes = stops_df['node'].to_dict()

    return stop_nodes


def get_rhos(U, stop_nodes):

    print('     Running get_rhos(*) ... ')

    rhos = {t: 0 for t in stop_nodes.values()}

    for s in U.nodes():
        neighborhood_distances = nx.single_source_dijkstra_path_length(
            U, s, cutoff=WALK_TRIP_FACTOR * WALK_DIST, weight='length'
        )
        neighborhood_stops = [t for t in stop_nodes.values() if t in neighborhood_distances.keys()]
        try:
            t = min(neighborhood_stops, key=lambda t: neighborhood_distances[t])
            rhos[t] += float(U.nodes[s]['feature_ct'])
        except ValueError:
            continue

    return rhos


def get_W_st_pairs_dists(U, rhos):

    print('     Running get_W_st_pairs_dists(*) ... ')

    W = {s for s, rho in rhos.items() if rho >= RHO_CUTOFF}

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


def get_C(G, stop_nodes):

    print('     Running get_C(*) ... ')

    routes_df = pd.read_csv('./data/{0}/routes.txt'.format(GTFS), delimiter=',')
    trips_df = pd.read_csv('./data/{0}/trips.txt'.format(GTFS), delimiter=',')
    stop_times_df = pd.read_csv('./data/{0}/stop_times.txt'.format(GTFS), delimiter=',')

    trips_df = trips_df[trips_df['service_id'] == 'WK']
    stop_times_df = stop_times_df[stop_times_df['trip_id'].isin(trips_df['trip_id'])]

    stop_times_df['departure_time'] = pd.to_timedelta(stop_times_df['departure_time'])

    headways = {route_id: {0: [], 1: []} for route_id in routes_df['route_id']}
    stop_id_sequences = {route_id: {0: [], 1: []} for route_id in routes_df['route_id']}

    for (route_id, direction_id), route_direction_trips_df in trips_df.groupby(['route_id', 'direction_id']):

        route_direction_stop_times_df = stop_times_df[
            stop_times_df['trip_id'].isin(route_direction_trips_df['trip_id'])
        ]

        outlier_stop_ids = set()
        for stop_id, route_direction_stop_id_stop_times_df in route_direction_stop_times_df.groupby('stop_id'):
            if route_direction_stop_id_stop_times_df.shape[0] <= 2:
                outlier_stop_ids.add(stop_id)
            else:
                dt1 = route_direction_stop_id_stop_times_df.sort_values('departure_time')['departure_time'].shift(-1)
                dt2 = route_direction_stop_id_stop_times_df.sort_values('departure_time')['departure_time']
                diff = dt1 - dt2
                diff = diff.dt.total_seconds() / 60
                headways[route_id][direction_id].extend(diff[:-1])

        if headways[route_id][direction_id]:
            headways[route_id][direction_id] = min(
                H, key=lambda h: abs(h - np.median(headways[route_id][direction_id]))
            )

        for trip_id, route_direction_trip_stop_times_df in route_direction_stop_times_df.groupby('trip_id'):
            stop_id_sequence = route_direction_trip_stop_times_df.sort_values(by='stop_sequence')['stop_id'].tolist()
            if not outlier_stop_ids.isdisjoint(stop_id_sequence):
                continue
            else:
                if len(stop_id_sequence) >= len(stop_id_sequences[route_id][direction_id]):
                    stop_id_sequences[route_id][direction_id] = stop_id_sequence

    C = {}
    for ell, route_id in enumerate(routes_df['route_id']):
        if (
                headways[route_id][0] and
                headways[route_id][1] and
                stop_id_sequences[route_id][0] and
                stop_id_sequences[route_id][1]
        ):
            C[ell] = dict()
            C[ell]['route_id'] = route_id
            C[ell]['headway'] = max(headways[route_id][0], headways[route_id][1])
            C[ell]['stop_id_sequence'] = stop_id_sequences[route_id][0] + stop_id_sequences[route_id][1]
            C[ell]['stop_node_sequence'] = [stop_nodes[s] for s in C[ell]['stop_id_sequence']]
            if C[ell]['stop_node_sequence'][-1] != C[ell]['stop_node_sequence'][0]:
                C[ell]['stop_id_sequence'].append(C[ell]['stop_id_sequence'][0])
                C[ell]['stop_node_sequence'].append(C[ell]['stop_node_sequence'][0])

            length = 0
            path_nodes = []
            for stop1, stop2 in zip(C[ell]['stop_node_sequence'][:-1], C[ell]['stop_node_sequence'][1:]):
                seg_length, seg_path_nodes = nx.single_source_dijkstra(G, stop1, stop2, weight='length')
                length += seg_length
                path_nodes.extend(seg_path_nodes[:-1])
            length += G.edges[path_nodes[-1], seg_path_nodes[-1], 0]['length']
            path_nodes.append(seg_path_nodes[-1])

            C[ell]['length'] = length
            C[ell]['path_nodes'] = path_nodes

    return C


def get_L_L_st(G, B, W, st_pairs, dists, C):

    print('     Running get_L_L_st(*) ... ')

    L = C.copy()
    L_st = {(s, t): set() for s, t in st_pairs}

    for ell in L.keys():

        ell_path_nodes = set(L[ell]['path_nodes'])
        ell_walk_nodes = set(
            nx.multi_source_dijkstra_path_length(
                B, set(L[ell]['stop_node_sequence']), weight='length', cutoff=WALK_COVER_FACTOR * WALK_DIST
            ).keys()
        )

        P = nx.compose(G.subgraph(ell_path_nodes).copy(), B.subgraph(set(ell_walk_nodes)).copy())

        P_dists = {
            s: {t: length for t, length in
                nx.single_source_dijkstra_path_length(P, s, weight='length').items() if t in W}
            for s in W.intersection(P.nodes())
        }

        for s, t in st_pairs:
            if {s, t}.issubset(P.nodes()):
                if P_dists[s][t] <= DETOUR_FACTOR * dists[s][t]:
                    if P_dists[t][s] <= DETOUR_FACTOR * dists[t][s]:
                        L_st[(s, t)].add(ell)

    return L, L_st


def get_candidate_transfers(G, B, W, st_pairs, dists, L, L_st):

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

    G = __load_G(instance_filename)
    U = __load_U(instance_filename)
    B = __load_B(instance_filename)

    with open('./results/instances/stop_nodes_{0}.pkl'.format(instance_filename), 'rb') as file:
        stop_nodes = pickle.load(file)

    with open('./results/instances/rhos_{0}.pkl'.format(instance_filename), 'rb') as file:
        rhos = pickle.load(file)

    W = __load_W(instance_filename)
    st_pairs = __load_st_pairs(instance_filename)
    with open('./results/instances/dists_{0}.pkl'.format(instance_filename), 'rb') as file:
        dists = pickle.load(file)

    L, L_st, C = __load_L_L_st_C(instance_filename)
    T, T_st = __load_T_T_st(instance_filename)

    return G, U, B, stop_nodes, rhos, W, st_pairs, dists, L, L_st, C, T, T_st


def __load_G(instance_filename):

    G = ox.load_graphml('./results/instances/G_{0}.graphml'.format(instance_filename))

    return G


def __load_U(instance_filename):

    U = ox.load_graphml('./results/instances/U_{0}.graphml'.format(instance_filename))

    return U


def __load_B(instance_filename):

    B = ox.load_graphml('./results/instances/B_{0}.graphml'.format(instance_filename))

    return B


def __load_W(instance_filename):

    with open('./results/instances/W_{0}.pkl'.format(instance_filename), 'rb') as file:
        W = pickle.load(file)

    return W


def __load_st_pairs(instance_filename):

    with open('./results/instances/st_pairs_{0}.pkl'.format(instance_filename), 'rb') as file:
        st_pairs = pickle.load(file)

    return st_pairs


def __load_L_L_st_C(instance_filename):

    with open('./results/instances/L_{0}.pkl'.format(instance_filename), 'rb') as file:
        L = pickle.load(file)
    with open('./results/instances/L_st_{0}.pkl'.format(instance_filename), 'rb') as file:
        L_st = pickle.load(file)
    with open('./results/instances/C_{0}.pkl'.format(instance_filename), 'rb') as file:
        C = pickle.load(file)

    return L, L_st, C


def __load_T_T_st(instance_filename):

    with open('./results/instances/T_{0}.pkl'.format(instance_filename), 'rb') as file:
        T = pickle.load(file)
    with open('./results/instances/T_st_{0}.pkl'.format(instance_filename), 'rb') as file:
        T_st = pickle.load(file)

    return T, T_st


# def get_candidate_lines(G, U, B, stop_nodes, W, st_pairs, dists):
#
#     print('     Running candidate_lines(*) ... ')
#
#     routes_df = pd.read_csv('./data/{0}/routes.txt'.format(GTFS), delimiter=',')
#     trips_df = pd.read_csv('./data/{0}/trips.txt'.format(GTFS), delimiter=',')
#     stops_df = pd.read_csv('./data/{0}/stops.txt'.format(GTFS), delimiter=',')
#     stop_times_df = pd.read_csv('./data/{0}/stop_times.txt'.format(GTFS), delimiter=',')
#
#     R = dict()
#     L, L_st, ell = dict(), {(s, t): set() for s, t in st_pairs}, 0
#     C = set()
#
#     for (route_id, trip_id, direction_id), trip_df in trips_df.groupby(['route_id', 'trip_id', 'direction_id']):
#         if route_id not in R:
#             R[route_id] = {}
#         if direction_id not in R[route_id]:
#             R[route_id][direction_id] = tuple()
#         if len(tuple(stop_times_df[stop_times_df['trip_id'] == trip_id]['stop_id'])) > len(R[route_id][direction_id]):
#             R[route_id][direction_id] = tuple(stop_times_df[stop_times_df['trip_id'] == trip_id]['stop_id'])
#
#     for route_id in R.keys():
#
#         ell_stop_seq = []
#         for ell_direction_stop_seq in R[route_id].values():
#             ell_stop_seq.extend(ell_direction_stop_seq)
#         ell_stop_seq = [stop_nodes[stop] for stop in ell_stop_seq]
#         if len(R[route_id].values()) == 1 and ell_stop_seq[0] != ell_stop_seq[-1]:
#             ell_stop_seq.extend(ell_stop_seq[::-1])
#
#         ell_path = []
#         for stop1, stop2 in zip(ell_stop_seq[:-1], ell_stop_seq[1:]):
#             _, ell_seg_path = nx.single_source_dijkstra(G, stop1, stop2, weight='length')
#             ell_path.extend(ell_seg_path[:-1])
#         ell_path.append(ell_stop_seq[-1])
#
#         P = G.subgraph(set(ell_path)).copy()
#         P = nx.subgraph(P, max(nx.strongly_connected_components(P), key=len))
#         ell_length = sum(data['length'] for _, _, data in P.edges(data=True))
#         ell_stops = set(P.nodes()).intersection(ell_stop_seq)
#
#         ell_walk = set(nx.multi_source_dijkstra_path_length(U, ell_stops, weight='length', cutoff=WALK_DIST).keys())
#         ell_walk_cover = ell_walk.intersection(W)
#
#         L[ell] = {
#             'route_id': route_id,
#             'stops': ell_stops,
#             'length': ell_length,
#             'path': ell_path,
#             'walk': ell_walk,
#             'walk_cover': ell_walk_cover
#         }
#
#         P = nx.compose(P, B.subgraph(set(ell_walk)).copy())
#         P_dists = {
#             s: {t: length for t, length in
#                 nx.single_source_dijkstra_path_length(P, s, weight='length').items() if t in W}
#             for s in W.intersection(P.nodes())
#         }
#         for s, t in st_pairs:
#             if {s, t}.issubset(ell_walk_cover):
#                 if P_dists[s][t] <= DETOUR_FACTOR * dists[s][t]:
#                     if P_dists[t][s] <= DETOUR_FACTOR * dists[t][s]:
#                         L_st[(s, t)].add(ell)
#
#         ell += 1
#         print('         line count: {0}'.format(len(L)))
#
#     for ell in L.keys():
#
#         ell_trips_df = trips_df[trips_df['route_id'] == L[ell]['route_id']]
#         ell_stop_times_df = stop_times_df[stop_times_df['trip_id'].isin(ell_trips_df['trip_id'])]
#         ell_headways = []
#         for _, ell_stop_times in ell_stop_times_df.groupby('stop_id'):
#             ell_stop_arrival_times = pd.to_timedelta(
#                 ell_stop_times['arrival_time']
#             ).drop_duplicates(keep='first').sort_values()
#             ell_stop_headways = ell_stop_arrival_times.diff().dt.total_seconds().div(60).iloc[1:]
#             ell_headways.extend(ell_stop_headways.to_list())
#         h = min(H, key=lambda h: abs(h - np.mean(ell_headways)))
#
#         C.add((ell, h))
#
#     ell = len(L)
#     for idx in range(NO_RANDOM_LINES):
#
#         route_id = 'RANDOM-{0}'.format(idx)
#         p, q = np.random.choice(list(W), size=2, replace=False)
#
#         p_q_length, p_q_path = nx.single_source_dijkstra(G, source=p, target=q, weight='length')
#         q_p_length, q_p_path = nx.single_source_dijkstra(G, source=q, target=p, weight='length')
#
#         p_q_stops = set(p_q_path).intersection(W)  # could also be .intersection(stops)
#         p_q_walk = set(nx.multi_source_dijkstra_path_length(U, p_q_stops, weight='length', cutoff=WALK_DIST).keys())
#         q_p_stops = set(q_p_path).intersection(W)  # could also be .intersection(stops)
#         q_p_walk = set(nx.multi_source_dijkstra_path_length(U, q_p_stops, weight='length', cutoff=WALK_DIST).keys())
#
#         ell_stops = p_q_stops.union(q_p_stops)
#         ell_length = p_q_length + q_p_length
#         ell_path = p_q_path + q_p_path[1:]
#         ell_walk = p_q_walk.union(q_p_walk)
#         ell_walk_cover = ell_walk.intersection(W)
#
#         L[ell] = {
#             'route_id': route_id,
#             'stops': ell_stops,
#             'length': ell_length,
#             'path': ell_path,
#             'walk': ell_walk,
#             'walk_cover': ell_walk_cover,
#         }
#
#         P = nx.compose(G.subgraph(set(ell_path)).copy(), B.subgraph(set(ell_walk)).copy())
#         P_dists = {
#             s: {t: length for t, length in
#                 nx.single_source_dijkstra_path_length(P, s, weight='length').items() if t in W}
#             for s in W.intersection(P.nodes())
#         }
#         for s, t in st_pairs:
#             if {s, t}.issubset(ell_walk_cover):
#                 if P_dists[s][t] <= DETOUR_FACTOR * dists[s][t]:
#                     if P_dists[t][s] <= DETOUR_FACTOR * dists[t][s]:
#                         L_st[(s, t)].add(ell)
#
#         ell += 1
#         print('         line count: {0}'.format(len(L)))
#
#     return L, L_st, C

