import osmnx as ox
import pandas as pd
import requests
from src.config import *


def current_service_plan(G):




    lines = []
    for element in lines_response['elements']:
        stops = []
        for member in element['members']:
            if member['type'] == 'node':
                if member['ref'] in stops_df.index:
                    stop = stops_df.loc[member['ref']].node
                    if not stops or stops[-1] != stop:
                        stops.append(stop)
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
