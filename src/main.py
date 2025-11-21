import asyncio
import osmnx as ox
import folium
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
np.random.seed(1)

t0 = time.time()
g = ox.graph_from_place(
    PLACE,
    network_type='drive',
    simplify=True,
    retain_all=False,
    custom_filter=CUSTOM_FILTER
)
# g = ox.graph_from_point(
#     center_point=CENTER,
#     dist=1000,
#     network_type='drive',
#     simplify=True,
#     retain_all=False,
#     custom_filter=CUSTOM_FILTER
# )

g = nx.subgraph(g, max(nx.strongly_connected_components(g), key=len))

forbidden = dict()
for s in g.nodes():
    forbidden[s] = set(nx.single_source_dijkstra_path_length(g, s, cutoff=3 * WALKING, weight='length').keys())

C_size = 25
C = set()

L_size = 250
L = dict()
L_st = {(s, t): set() for s in g.nodes() for t in g.nodes() if t not in forbidden[s]}

for ell in range(L_size):

    s, t = np.random.choice(g.nodes(), size=2, replace=False)
    h = np.random.choice(H)
    s, t, h = int(s), int(t), int(h)

    s_t_length, s_t_path = nx.single_source_dijkstra(g, source=s, target=t, weight='length')
    t_s_length, t_s_path = nx.single_source_dijkstra(g, source=t, target=s, weight='length')

    length = s_t_length + t_s_length
    path = s_t_path + t_s_path[1:]
    stops = set(path)
    coverage = set(nx.multi_source_dijkstra_path_length(g, stops, weight='length', cutoff=WALKING).keys())

    L[ell] = {
        'path': path,
        'length': length,
        'coverage': coverage
    }
    for s in coverage:
        for t in coverage:
            if t in forbidden[s]:
                continue
            L_st[(s, t)].add(ell)

    if ell <= C_size:
        C.add((ell, h))


C_cost = sum(L[ell]['length'] * 1 / h for ell, h in C)

print('     Some statistics ... ')
print('         - number of nodes: {0}'.format(g.number_of_nodes()))
print('         - number of candidate lines: {0}'.format(len(L)))
print('         - current cost: {0}'.format(C_cost))
t1 = time.time()
print('     ... elapsed time: {0:.2f} sec'.format(t1 - t0))


m = gp.Model()
m.ModelSense = gp.GRB.MAXIMIZE

print('     Started writing variables ... ')
m._x = m.addVars(((ell, h) for ell in L.keys() for h in H), vtype=gp.GRB.BINARY, name='x')
m._y, m._u = dict(), dict()
for s in g.nodes():
    for t in g.nodes():
        if t in forbidden[s]:
            continue
        m._y[(s, t)] = m.addVar(vtype=gp.GRB.BINARY, name='y')
        m._u[(s, t)] = m.addVar(vtype=gp.GRB.CONTINUOUS, lb=0, ub=1/min(H), name='u')
t1 = time.time()
print('     ... done writing variables!')
print('     ... elapsed time: {0:.2f} sec'.format(t1 - t0))

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

print('         Started writing quality of service constraints ...')
for (s, t), var in m._u.items():
    qs_lhs = min(sum(1/h for ell, h in C if ell in L_st[(s,t)]), 1/min(H)) * IC_FACTOR
    qs_rhs = 0
    cvrg_lhs = m._y[(s, t)]
    cvrg_rhs = 0
    for ell in L_st[(s, t)]:
        for h in H:
            qs_rhs += 1 / h * m._x[(ell, h)]
            cvrg_rhs += m._x[(ell, h)]
    m.addConstr(qs_lhs <= var)
    m.addConstr(var <= qs_rhs)
    m.addConstr(cvrg_lhs <= cvrg_rhs)
t1 = time.time()
print('         ... done writing quality of service constraints!')
print('         ... elapsed time: {0:.2f} sec'.format(t1 - t0))

print('     ... done writing constraints!')
t1 = time.time()
print('     ... elapsed time: {0:.2f} sec'.format(t1 - t0))

print('     Started writing warm start ...')
for (ell, h), var in m._x.items():
    if (ell, h) in C:
        var.Start = 1
    else:
        var.Start = 0
print('     ... done writing warm start!')
t1 = time.time()
print('     ... elapsed time: {0:.2f} sec'.format(t1 - t0))

u_obj = gp.quicksum(m._u.values())
y_obj = gp.quicksum(m._y.values())

m.setObjective(u_obj)
m.optimize()
P_u = {(ell, h) for (ell, h), var in m._x.items() if var.X > 0}

m.setObjective(y_obj)
m.optimize()
P_y = {(ell, h) for (ell, h), var in m._x.items() if var.X > 0}

folium_map = folium.Map(location=CENTER, zoom_start=ZOOM, tiles=None)
folium.TileLayer('OpenStreetMap', opacity=OPACITY).add_to(folium_map)
for s, data in g.nodes(data=True):
    folium.CircleMarker(
        location=(data['y'], data['x']), color=HEXBLACK, radius=3, weight=0,
        fill=True, fill_opacity=1, tooltip=s
    ).add_to(folium_map)
for ell, h in C:
    ell_coords = [(g.nodes[stop]['y'], g.nodes[stop]['x']) for stop in L[ell]['path']]
    HEXCOLOR = HEXCOLORS[ell % len(HEXCOLORS)]
    folium.PolyLine(
            ell_coords, color=HEXCOLOR, weight=1/h*max(H), opacity=1, tooltip=ell
    ).add_to(folium_map)
folium_map.save('./results/frames/html/current_plan.html')


folium_map = folium.Map(location=CENTER, zoom_start=ZOOM, tiles=None)
folium.TileLayer('OpenStreetMap', opacity=OPACITY).add_to(folium_map)
for s, data in g.nodes(data=True):
    folium.CircleMarker(
        location=(data['y'], data['x']), color=HEXBLACK, radius=3, weight=0,
        fill=True, fill_opacity=1, tooltip=s
    ).add_to(folium_map)
for ell in L.keys():
    ell_coords = [(g.nodes[stop]['y'], g.nodes[stop]['x']) for stop in L[ell]['path']]
    HEXCOLOR = HEXCOLORS[ell % len(HEXCOLORS)]
    folium.PolyLine(
            ell_coords, color=HEXCOLOR, weight=4, opacity=1, tooltip=ell
    ).add_to(folium_map)
folium_map.save('./results/frames/html/candidate_lines.html')

folium_map = folium.Map(location=CENTER, zoom_start=ZOOM, tiles=None)
folium.TileLayer('OpenStreetMap', opacity=OPACITY).add_to(folium_map)
for s, data in g.nodes(data=True):
    folium.CircleMarker(
        location=(data['y'], data['x']), color=HEXBLACK, radius=3, weight=0,
        fill=True, fill_opacity=1, tooltip=s
    ).add_to(folium_map)
for ell, h in P_u:
    ell_coords = [(g.nodes[stop]['y'], g.nodes[stop]['x']) for stop in L[ell]['path']]
    HEXCOLOR = HEXCOLORS[ell % len(HEXCOLORS)]
    folium.PolyLine(
            ell_coords, color=HEXCOLOR, weight=1/h*max(H), opacity=1, tooltip=ell
    ).add_to(folium_map)
folium_map.save('./results/frames/html/ridership_plan.html')

folium_map = folium.Map(location=CENTER, zoom_start=ZOOM, tiles=None)
folium.TileLayer('OpenStreetMap', opacity=OPACITY).add_to(folium_map)
for s, data in g.nodes(data=True):
    folium.CircleMarker(
        location=(data['y'], data['x']), color=HEXBLACK, radius=3, weight=0,
        fill=True, fill_opacity=1, tooltip=s
    ).add_to(folium_map)
for ell, h in P_y:
    ell_coords = [(g.nodes[stop]['y'], g.nodes[stop]['x']) for stop in L[ell]['path']]
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

