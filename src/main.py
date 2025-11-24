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

import src.solver
import src.instance
from src.config import *
np.random.seed(42)

G, U = src.instance.graph()
stops, stops_ref_to_node = src.instance.stops(U)
W, st_pairs = src.instance.cover_and_st_pairs(U, stops=stops)
L, L_st, C = src.instance.candidate_lines(G, U, st_pairs, stops_ref_to_node)
T = src.instance.transfer_candidates(L)
rho = {(s, t): max(G.nodes[s]['rho'], G.nodes[t]['rho']) for s, t in st_pairs}

# L_size = 250
# C_size = 10

# L = dict()
# L_st = {(s, t): set() for s, t in st_pairs}
# C = set()
#
# for ell in range(L_size):
#
#     p, q = np.random.choice(list(stops), size=2, replace=False)
#     h = H[np.random.randint(0, len(H))]
#
#     p_q_length, p_q_path = nx.single_source_dijkstra(G, source=p, target=q, weight='length')
#     q_p_length, q_p_path = nx.single_source_dijkstra(G, source=q, target=p, weight='length')
#     p_q_stops = set(p_q_path).intersection(stops)
#     p_q_coverage = set(nx.multi_source_dijkstra_path_length(U, p_q_stops, weight='length', cutoff=WALKING_DST).keys())
#     q_p_stops = set(q_p_path).intersection(stops)
#     q_p_coverage = set(nx.multi_source_dijkstra_path_length(U, q_p_stops, weight='length', cutoff=WALKING_DST).keys())
#
#     ell_length = p_q_length + q_p_length
#     ell_path = p_q_path + q_p_path[1:]
#     ell_stops = p_q_stops.union(q_p_stops)
#     ell_coverage = p_q_coverage.intersection(q_p_coverage)
#     ell_transfer_stops = ell_stops.intersection(ell_coverage)
#
#     L[ell] = {
#         'length': ell_length,
#         'path': ell_path,
#         'stops': ell_stops,
#         'coverage': ell_coverage,
#         'transfer_stops': ell_transfer_stops
#     }
#
#     for s, t in st_pairs:
#         if s in ell_coverage and t in ell_coverage:
#             L_st[(s, t)].add(ell)
#
#     if ell <= C_size:
#         C.add((ell, h))


print('     Some statistics ... ')
print('         - number of nodes: {0}'.format(len(W)))
print('         - number of s-t pairs: {0}'.format(len(st_pairs)))
print('         - number of headway options: {0}'.format(len(H)))
print('         - number of candidate lines: {0}'.format(len(L)))
print('         - number of transfer candidates: {0}'.format(len(T)))

P_u, P_y = src.solver.service_plans(st_pairs, L, L_st, C, T, rho=rho)

folium_map = folium.Map(location=CENTER, zoom_start=ZOOM, tiles=None)
folium.TileLayer('OpenStreetMap', opacity=OPACITY).add_to(folium_map)
for s in W:
    folium.CircleMarker(
        location=(G.nodes[s]['y'], G.nodes[s]['x']), color=HEXBLACK, radius=1, weight=0,
        fill=True, fill_opacity=1, tooltip=s
    ).add_to(folium_map)
for ell, h in C:
    ell_coords = [(G.nodes[stop]['y'], G.nodes[stop]['x']) for stop in L[ell]['path']]
    HEXCOLOR = HEXCOLORS[L[ell]['idx'] % len(HEXCOLORS)]
    folium.PolyLine(
            ell_coords, color=HEXCOLOR, weight=1/h*max(H), opacity=1, tooltip=ell
    ).add_to(folium_map)
folium_map.save('./results/frames/html/current_plan.html')


folium_map = folium.Map(location=CENTER, zoom_start=ZOOM, tiles=None)
folium.TileLayer('OpenStreetMap', opacity=OPACITY).add_to(folium_map)
for s in W:
    folium.CircleMarker(
        location=(G.nodes[s]['y'], G.nodes[s]['x']), color=HEXBLACK, radius=1, weight=0,
        fill=True, fill_opacity=1, tooltip=s
    ).add_to(folium_map)
for ell in L.keys():
    ell_coords = [(G.nodes[stop]['y'], G.nodes[stop]['x']) for stop in L[ell]['path']]
    HEXCOLOR = HEXCOLORS[L[ell]['idx'] % len(HEXCOLORS)]
    folium.PolyLine(
            ell_coords, color=HEXCOLOR, weight=4, opacity=1, tooltip=ell
    ).add_to(folium_map)
folium_map.save('./results/frames/html/candidate_lines.html')

folium_map = folium.Map(location=CENTER, zoom_start=ZOOM, tiles=None)
folium.TileLayer('OpenStreetMap', opacity=OPACITY).add_to(folium_map)
for s in W:
    folium.CircleMarker(
        location=(G.nodes[s]['y'], G.nodes[s]['x']), color=HEXBLACK, radius=1, weight=0,
        fill=True, fill_opacity=1, tooltip=s
    ).add_to(folium_map)
for ell, h in P_u:
    ell_coords = [(G.nodes[stop]['y'], G.nodes[stop]['x']) for stop in L[ell]['path']]
    HEXCOLOR = HEXCOLORS[L[ell]['idx'] % len(HEXCOLORS)]
    folium.PolyLine(
            ell_coords, color=HEXCOLOR, weight=1/h*max(H), opacity=1, tooltip=ell
    ).add_to(folium_map)
folium_map.save('./results/frames/html/ridership_plan.html')

folium_map = folium.Map(location=CENTER, zoom_start=ZOOM, tiles=None)
folium.TileLayer('OpenStreetMap', opacity=OPACITY).add_to(folium_map)
for s in W:
    folium.CircleMarker(
        location=(G.nodes[s]['y'], G.nodes[s]['x']), color=HEXBLACK, radius=1, weight=0,
        fill=True, fill_opacity=1, tooltip=s
    ).add_to(folium_map)
for ell, h in P_y:
    ell_coords = [(G.nodes[stop]['y'], G.nodes[stop]['x']) for stop in L[ell]['path']]
    HEXCOLOR = HEXCOLORS[L[ell]['idx'] % len(HEXCOLORS)]
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

