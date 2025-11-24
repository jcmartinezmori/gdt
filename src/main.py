import asyncio
import osmnx as ox
import folium
import itertools as it
import networkx as nx
import numpy as np
import random
import gurobipy as gp
import os
import shutil
import time
from playwright.async_api import async_playwright
from pathlib import Path
from src.config import *
np.random.seed(42)

t0 = time.time()
G = ox.graph_from_place(
    PLACE,
    network_type='drive',
    simplify=True,
    retain_all=False,
    custom_filter=CUSTOM_FILTER
)
# G = ox.graph_from_point(
#     center_point=CENTER,
#     dist=1000,
#     network_type='drive',
#     simplify=True,
#     retain_all=False,
#     custom_filter=CUSTOM_FILTER
# )
G = nx.subgraph(G, max(nx.strongly_connected_components(G), key=len))
U = G.to_undirected()
D = nx.dominating_set(U)
pr = nx.pagerank(U)

forbidden = dict()
for s in G.nodes():
    forbidden[s] = set(nx.single_source_dijkstra_path_length(U, s, cutoff=3 * WALKING_DST, weight='length').keys())
st_pairs = []
for s, t in it.combinations(D, 2):
    if t not in forbidden[s] and s not in forbidden[t]:
        st_pairs.append(tuple(sorted((s, t))))

L_size = 250
C_size = 10

L = dict()
L_st = {(s, t): set() for s, t in st_pairs}
C = set()

for ell in range(L_size):

    p, q = np.random.choice(G.nodes(), size=2, replace=False)
    h = H[np.random.randint(0, len(H))]

    p_q_length, p_q_path = nx.single_source_dijkstra(G, source=p, target=q, weight='length')
    q_p_length, q_p_path = nx.single_source_dijkstra(G, source=q, target=p, weight='length')
    p_q_stops = set(p_q_path)
    p_q_coverage = set(nx.multi_source_dijkstra_path_length(U, p_q_stops, weight='length', cutoff=WALKING_DST).keys())
    q_p_stops = set(q_p_path)
    q_p_coverage = set(nx.multi_source_dijkstra_path_length(U, q_p_stops, weight='length', cutoff=WALKING_DST).keys())

    length = p_q_length + q_p_length
    path = p_q_path + q_p_path[1:]
    stops = p_q_stops.union(q_p_stops)
    coverage = p_q_coverage.intersection(q_p_coverage)
    transfer_stops = stops.intersection(coverage)

    L[ell] = {
        'length': length,
        'path': path,
        'stops': stops,
        'coverage': coverage,
        'transfer_stops': transfer_stops
    }

    for s, t in st_pairs:
        if s in coverage and t in coverage:
            L_st[(s, t)].add(ell)

    if ell <= C_size:
        C.add((ell, h))

C_cost = sum(L[ell]['length'] * 1 / h for ell, h in C)

T = dict()

for ell1, ell2 in it.combinations(L.keys(), 2):
    if not L[ell1]['transfer_stops'].isdisjoint(L[ell2]['transfer_stops']):
        coverage1 = L[ell1]['coverage']
        coverage2 = L[ell2]['coverage']
        jac = len(coverage1.symmetric_difference(coverage2)) / len(coverage1.union(coverage2))
        if jac >= JAC_DST:
            T[tuple(sorted((ell1, ell2)))] = jac


print('     Some statistics ... ')
print('         - number of nodes: {0}'.format(G.number_of_nodes()))
print('         - number of s-t pairs: {0}'.format(len(st_pairs)))
print('         - headway options: {0}'.format(H))
print('         - number of candidate lines: {0}'.format(len(L)))
print('         - current cost: {0}'.format(C_cost))
t1 = time.time()
print('     ... elapsed time: {0:.2f} sec'.format(t1 - t0))

m = gp.Model()
m.ModelSense = gp.GRB.MAXIMIZE
m.Params.MIPFocus = 3

print('     Started writing variables ... ')
m._x = m.addVars(((ell, h) for ell in L.keys() for h in H), vtype=gp.GRB.BINARY, name='x')
m._y, m._u = dict(), dict()
for s, t in st_pairs:
    m._y[(s, t)] = m.addVar(vtype=gp.GRB.BINARY, name='y')
    m._u[(s, t)] = m.addVar(vtype=gp.GRB.CONTINUOUS, lb=0, ub=1/min(H), name='u')
m._z = m.addVars(((ell1, ell2) for ell1, ell2 in T.keys()), vtype=gp.GRB.BINARY, name='z')
t1 = time.time()
print('         ... done writing variables!')
print('         ... elapsed time: {0:.2f} sec'.format(t1 - t0))

print('     Started writing constraints ... ')
print('         Started writing selection constraints ...')
for ell in L.keys():
    lhs = gp.quicksum(m._x[(ell, h)] for h in H)
    rhs = 1
    m.addConstr(lhs <= rhs)
t1 = time.time()
print('             ... done writing selection constraints!')
print('             ... elapsed time: {0:.2f} sec'.format(t1 - t0))

print('         Started writing budget constraint ...')
lhs = gp.quicksum(L[ell]['length'] / h * var for (ell, h), var in m._x.items())
rhs = C_cost * BDGT_FACTOR
m.addConstr(lhs <= rhs)
t1 = time.time()
print('             ... done writing budget constraint!')
print('             ... elapsed time: {0:.2f} sec'.format(t1 - t0))

print('         Started writing coverage constraints ...')
for (s, t), var in m._y.items():
    rhs = 0
    for ell in L_st[(s, t)]:
        for h in H:
            rhs += m._x[(ell, h)]
    m.addConstr(var <= rhs)
t1 = time.time()
print('             ... done writing coverage constraints!')
print('             ... elapsed time: {0:.2f} sec'.format(t1 - t0))

print('         Started writing quality of service constraints ...')
for (s, t), var in m._u.items():
    lb = min(sum(1/h for ell, h in C if ell in L_st[(s,t)]), 1/min(H)) * QS_FACTOR
    ub = 0
    for ell in L_st[(s, t)]:
        for h in H:
            ub += 1 / h * m._x[(ell, h)]
    m.addConstr(lb <= var)
    m.addConstr(var <= ub)
t1 = time.time()
print('             ... done writing quality of service constraints!')
print('             ... elapsed time: {0:.2f} sec'.format(t1 - t0))

print('         Started writing transfer constraints ...')
for (ell1, ell2), var in m._z.items():
    m.addConstr(var <= m._x[(ell1, min(H))])
    m.addConstr(var <= m._x[(ell2, min(H))])
t1 = time.time()
print('             ... done writing transfer constraints!')
print('             ... elapsed time: {0:.2f} sec'.format(t1 - t0))

print('         ... done writing constraints!')
t1 = time.time()
print('         ... elapsed time: {0:.2f} sec'.format(t1 - t0))

print('     Started writing warm start ...')
for (ell, h), var in m._x.items():
    if (ell, h) in C:
        var.Start = 1
    else:
        var.Start = 0
print('         ... done writing warm start!')
t1 = time.time()
print('         ... elapsed time: {0:.2f} sec'.format(t1 - t0))

u_obj = gp.quicksum(max(pr[s], pr[t]) * var for (s, t), var in m._u.items())
y_obj = gp.quicksum(m._y.values())
z_obj = gp.quicksum(T[(ell1, ell2)] * var for (ell1, ell2), var in m._z.items())

m.setObjectiveN(u_obj, index=0, priority=3, reltol=REL_TOL)
m.setObjectiveN(z_obj, index=1, priority=2, reltol=REL_TOL)
m.setObjectiveN(y_obj, index=2, priority=1, reltol=REL_TOL)
m.optimize()
P_u = {(ell, h) for (ell, h), var in m._x.items() if var.X > 0}

m.setObjectiveN(y_obj, index=0, priority=3, reltol=REL_TOL)
m.setObjectiveN(u_obj, index=1, priority=2, reltol=REL_TOL)
m.setObjectiveN(z_obj, index=2, priority=1, reltol=REL_TOL)
m.optimize()
P_y = {(ell, h) for (ell, h), var in m._x.items() if var.X > 0}

folium_map = folium.Map(location=CENTER, zoom_start=ZOOM, tiles=None)
folium.TileLayer('OpenStreetMap', opacity=OPACITY).add_to(folium_map)
for s, data in G.nodes(data=True):
    folium.CircleMarker(
        location=(data['y'], data['x']), color=HEXBLACK, radius=3, weight=0,
        fill=True, fill_opacity=1, tooltip=s
    ).add_to(folium_map)
for ell, h in C:
    ell_coords = [(G.nodes[stop]['y'], G.nodes[stop]['x']) for stop in L[ell]['path']]
    HEXCOLOR = HEXCOLORS[ell % len(HEXCOLORS)]
    folium.PolyLine(
            ell_coords, color=HEXCOLOR, weight=1/h*max(H), opacity=1, tooltip=ell
    ).add_to(folium_map)
folium_map.save('./results/frames/html/current_plan.html')


folium_map = folium.Map(location=CENTER, zoom_start=ZOOM, tiles=None)
folium.TileLayer('OpenStreetMap', opacity=OPACITY).add_to(folium_map)
for s, data in G.nodes(data=True):
    folium.CircleMarker(
        location=(data['y'], data['x']), color=HEXBLACK, radius=3, weight=0,
        fill=True, fill_opacity=1, tooltip=s
    ).add_to(folium_map)
for ell in L.keys():
    ell_coords = [(G.nodes[stop]['y'], G.nodes[stop]['x']) for stop in L[ell]['path']]
    HEXCOLOR = HEXCOLORS[ell % len(HEXCOLORS)]
    folium.PolyLine(
            ell_coords, color=HEXCOLOR, weight=4, opacity=1, tooltip=ell
    ).add_to(folium_map)
folium_map.save('./results/frames/html/candidate_lines.html')

folium_map = folium.Map(location=CENTER, zoom_start=ZOOM, tiles=None)
folium.TileLayer('OpenStreetMap', opacity=OPACITY).add_to(folium_map)
for s, data in G.nodes(data=True):
    folium.CircleMarker(
        location=(data['y'], data['x']), color=HEXBLACK, radius=3, weight=0,
        fill=True, fill_opacity=1, tooltip=s
    ).add_to(folium_map)
for ell, h in P_u:
    ell_coords = [(G.nodes[stop]['y'], G.nodes[stop]['x']) for stop in L[ell]['path']]
    HEXCOLOR = HEXCOLORS[ell % len(HEXCOLORS)]
    folium.PolyLine(
            ell_coords, color=HEXCOLOR, weight=1/h*max(H), opacity=1, tooltip=ell
    ).add_to(folium_map)
folium_map.save('./results/frames/html/ridership_plan.html')

folium_map = folium.Map(location=CENTER, zoom_start=ZOOM, tiles=None)
folium.TileLayer('OpenStreetMap', opacity=OPACITY).add_to(folium_map)
for s, data in G.nodes(data=True):
    folium.CircleMarker(
        location=(data['y'], data['x']), color=HEXBLACK, radius=3, weight=0,
        fill=True, fill_opacity=1, tooltip=s
    ).add_to(folium_map)
for ell, h in P_y:
    ell_coords = [(G.nodes[stop]['y'], G.nodes[stop]['x']) for stop in L[ell]['path']]
    HEXCOLOR = HEXCOLORS[ell % len(HEXCOLORS)]
    folium.PolyLine(
            ell_coords, color=HEXCOLOR, weight=1/h*max(H), opacity=1, tooltip=ell
    ).add_to(folium_map)
folium_map.save('./results/frames/html/coverage_plan.html')


async def convert_html_to_images(html_dir, pdf_dir):

    if os.path.exists(pdf_dir):
        shutil.rmtree(pdf_dir)
    os.makedirs(pdf_dir)

    html_files = sorted(Path(html_dir).glob('*.html'), key=lambda f: f.stat().st_ctime)

    async with async_playwright() as p:

        browser = await p.chromium.launch()
        page = await browser.new_page()

        for i, html_file in enumerate(html_files):

            file_url = html_file.resolve().as_uri()
            pdf_out = Path(pdf_dir)/f'frame_{i:04d}.pdf'

            await page.goto(file_url)
            await page.set_viewport_size({'width': 1920, 'height': 1080})
            await page.wait_for_load_state('networkidle')
            await page.pdf(path=pdf_out, width='1920', height='1080', print_background=False)

        await browser.close()

html_dir = './results/frames/html'
pdf_dir = './results/frames/pdf'
asyncio.run(convert_html_to_images(html_dir, pdf_dir))

