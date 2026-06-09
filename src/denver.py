import pandas as pd
from src.config import *

routes_df = pd.read_csv('./data/{0}/routes.txt'.format(GTFS), delimiter=',')
trips_df = pd.read_csv('./data/{0}/trips.txt'.format(GTFS), delimiter=',')
stops_df = pd.read_csv('./data/{0}/stops.txt'.format(GTFS), delimiter=',')
stop_times_df = pd.read_csv('./data/{0}/stop_times.txt'.format(GTFS), delimiter=',')

trips_df = trips_df[trips_df['service_id'] == 'WK']
stop_times_df = stop_times_df[stop_times_df['trip_id'].isin(trips_df['trip_id'])]

parent_stations = stops_df.dropna(subset=['parent_station']).set_index('stop_id')['parent_station']
stop_times_df['stop_id'] = stop_times_df['stop_id'].map(parent_stations).fillna(stop_times_df['stop_id'])

stop_times_df['departure_time'] = pd.to_timedelta(stop_times_df['departure_time'])

headways = {route_id: {0: [], 1: []} for route_id in routes_df['route_id']}
stop_sequences = {route_id: {0: [], 1: []} for route_id in routes_df['route_id']}

for (route_id, direction_id), route_direction_trips_df in trips_df.groupby(['route_id', 'direction_id']):

    route_direction_stop_times_df = stop_times_df[stop_times_df['trip_id'].isin(route_direction_trips_df['trip_id'])]

    outlier_stop_ids = set()
    for stop_id, route_direction_stop_id_stop_times_df in route_direction_stop_times_df.groupby('stop_id'):
        if route_direction_stop_id_stop_times_df.shape[0] <= 2:
            outlier_stop_ids.add(stop_id)
        else:
            diff = (route_direction_stop_id_stop_times_df.sort_values('departure_time')['departure_time'].shift(-1)
                    - route_direction_stop_id_stop_times_df.sort_values('departure_time')['departure_time'])
            diff = diff.dt.total_seconds() / 60
            headways[route_id][direction_id].extend(diff[:-1])
    if headways[route_id][direction_id]:
        headways[route_id][direction_id] = min(H, key=lambda h: abs(h - np.median(headways[route_id][direction_id])))

    for trip_id, route_direction_trip_stop_times_df in route_direction_stop_times_df.groupby('trip_id'):
        stop_sequence = route_direction_trip_stop_times_df.sort_values(by='stop_sequence')['stop_id'].tolist()
        if not outlier_stop_ids.isdisjoint(stop_sequence):
            continue
        else:
            if len(stop_sequence) >= len(stop_sequences[route_id][direction_id]):
                stop_sequences[route_id][direction_id] = stop_sequence

final_headways = {
    route_id: max(headways[route_id][0], headways[route_id][1]) for route_id in routes_df['route_id']
    if headways[route_id][0] and headways[route_id][1] and stop_sequences[route_id][0] and stop_sequences[route_id][1]
}
final_stop_sequences = {
    route_id: stop_sequences[route_id][0] + stop_sequences[route_id][1] for route_id in routes_df['route_id']
    if headways[route_id][0] and headways[route_id][1] and stop_sequences[route_id][0] and stop_sequences[route_id][1]
}

# for key, value in final_stop_sequences.items():
#     if value[0] != value[-1]:
#         print(key)