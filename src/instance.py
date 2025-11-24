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
        simplify=True,
        retain_all=False,
        custom_filter=CUSTOM_FILTER
    )
    G = nx.subgraph(G, max(nx.strongly_connected_components(G), key=len))
    for u, rho in nx.pagerank(G).items():
        G.nodes[u]['rho'] = rho

    U = G.to_undirected()

    return G, U


def st_pairs(U):

    W = src.solver.walkable_cover(U)

    forbidden = dict()
    for s in U.nodes():
        forbidden[s] = set(nx.single_source_dijkstra_path_length(U, s, cutoff=3 * WALKING_DST, weight='length').keys())
    st_pairs = []
    for s, t in it.combinations(W, 2):
        if t not in forbidden[s] and s not in forbidden[t]:
            st_pairs.append(tuple(sorted((s, t))))

    return st_pairs


def stops(U):

    stops_df = ox.features_from_place(PLACE, STOPS_TAGS).droplevel('element')
    stops_df = stops_df[stops_df['geometry'].geom_type == 'Point']
    stops_df['node'] = stops_df.apply(lambda stop: ox.nearest_nodes(U, stop.geometry.x, stop.geometry.y), axis=1)

    stops_ref_to_node = stops_df['node'].to_dict()
    stops = set(stops_dict.values())

    return stops, stops_ref_to_node


def current_service_plan(st_pairs, stops_ref_to_node):

    current_query = """
    [out:json];
    area["name"="{0}"]["admin_level"="{1}"]->.searchArea;
    (
      relation["type"="route"]["route"="bus"](area.searchArea);
    );
    out body;
    """.format(PLACE, ADMIN_LEVEL)
    current_response = requests.get('http://overpass-api.de/api/interpreter', params={'data': lines_query}).json()

    C, C_st = dict(), {(s, t): set() for s, t in st_pairs}
    for element in current_response['elements']:
        ell_stop_seq = []
        for member in element['members']:
            if member['type'] == 'node':
                if member['ref'] in stops_ref_to_node.keys():
                    stop = stops_ref_to_node[member['ref']]
                    if not ell_stop_seq or ell_stop_seq[-1] != ell_stop_seq:
                        ell_stop_seq.append(stop)
        seen = set()
        stops = tuple(stop for stop in stops if not (stop in seen or seen.add(stop)))
        if len(stops) >= 6:
            length = 0
            route = []
            for s, t in zip(stops[:-1], stops[1:]):
                if s != t:
                    segment_length, segment_route = nx.bidirectional_dijkstra(g, s, t, weight='length')
                    length += segment_length
                    route.extend(segment_route[:-1])
            route.append(stops[-1])
            route = tuple(route)
            coords = tuple((g.nodes[node]['y'], g.nodes[node]['x']) for node in route)
            hexcolor = HEXCOLORS[len(lines) % len(HEXCOLORS)]
            line = [element['id'], element['tags'], stops, length, route, coords, hexcolor]
            lines.append(line)
    lines_df = pd.DataFrame(lines, columns=['id', 'tags', 'stops', 'length', 'route', 'coords', 'hexcolor'])
    lines_df['length'] /= 1000  # kilometers
    lines_df['dist'] = lines_df.apply(
        lambda line: nx.multi_source_dijkstra_path_length(g, line.stops, weight='length', cutoff=WALKING_DST),
        axis=1
    )
    lines_df.set_index('id', inplace=True)
    lines_df.drop_duplicates(subset=['length'], inplace=True)

    return C, C_st
