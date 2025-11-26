import asyncio
import folium
import os
import osmnx as ox
import pandas as pd
import pickle
import shutil
from playwright.async_api import async_playwright
import plotly.graph_objects as go
from pathlib import Path
from src.config import *


def main(filename, solver_params):

    G = ox.load_graphml('./results/instances/graph_{0}.graphml'.format(instance_filename))
    with open('./results/instances/instance_{0}.pkl'.format(instance_filename), 'rb') as file:
        instance = pickle.load(file)
        W, st_pairs, L, L_st, C, T = instance
    with open('./results/output/P_u_{0}.pkl'.format(filename + solver_params), 'rb') as file:
        P_u = pickle.load(file)
    with open('./results/output/P_y_{0}.pkl'.format(filename + solver_params), 'rb') as file:
        P_y = pickle.load(file)

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
    folium_map.save('./results/frames/html/current_plan_{0}.html'.format(filename + solver_params))

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
    folium_map.save('./results/frames/html/candidate_lines_{0}.html'.format(filename + solver_params))

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
    folium_map.save('./results/frames/html/ridership_plan_{0}.html'.format(filename + solver_params))

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
    folium_map.save('./results/frames/html/coverage_plan_{0}.html'.format(filename + solver_params))


def frequencies(filename, solver_params):

    instance_filename = city
    solution_filename = city + '_' + solver_params
    
    G = ox.load_graphml('./results/instances/graph_{0}.graphml'.format(instance_filename))
    with open('./results/instances/instance_{0}.pkl'.format(instance_filename), 'rb') as file:
        instance = pickle.load(file)
        W, st_pairs, L, L_st, C, T = instance
    with open('./results/solutions/P_u_{0}.pkl'.format(solution_filename), 'rb') as file:
        P_u = pickle.load(file)
    with open('./results/solutions/P_y_{0}.pkl'.format(solution_filename), 'rb') as file:
        P_y = pickle.load(file)

    freq_C = {(s, t): 0 for s, t in st_pairs}
    ell_C = {ell for (ell, _) in C}
    for idx, (s, t) in enumerate(st_pairs):
        for ell, h in C:
            if ell in L_st[(s, t)]:
                freq_C[(s, t)] += 1/h
        for (ell1, ell2), data in T.items():
            if {ell1, ell2} in ell_C:


    freq_P_u = {(s, t): 0 for s, t in st_pairs}
    for idx, (s, t) in enumerate(st_pairs):
        for ell, h in P_u:
            if ell in L_st[(s, t)]:
                freq_P_u[(s, t)] += 1/h

    freq_P_y = {(s, t): 0 for s, t in st_pairs}
    for idx, (s, t) in enumerate(st_pairs):
        for ell, h in P_y:
            if ell in L_st[(s, t)]:
                freq_P_y[(s, t)] += 1/h

    freq_df = pd.DataFrame([freq_C, freq_P_u, freq_P_y]).T
    freq_df.columns = ['freq_C', 'freq_P_u', 'freq_P_y']

    fig = go.Figure()

    for col in freq_df.columns:
        x = list(range(len(freq_df[col])))
        y = np.sort(freq_df[col].values)
        fig.add_trace(go.Scatter(
            x=x,
            y=y,
            mode='lines',
            name=f"Lorenz – {col}"
        ))
    fig.show()


# async def convert_html_to_images(html_dir, pdf_dir):
#
#     if os.path.exists(pdf_dir):
#         shutil.rmtree(pdf_dir)
#     os.makedirs(pdf_dir)
#
#     html_files = sorted(Path(html_dir).glob('*.html'), key=lambda f: f.stat().st_ctime)
#
#     async with async_playwright() as p:
#
#         browser = await p.chromium.launch()
#         page = await browser.new_page()
#
#         for i, html_file in enumerate(html_files):
#
#             file_url = html_file.resolve().as_uri()
#             pdf_out = Path(pdf_dir)/f'frame_{i:04d}.pdf'
#
#             await page.goto(file_url)
#             await page.set_viewport_size({'width': 1920, 'height': 1080})
#             await page.wait_for_load_state('networkidle')
#             await page.pdf(path=pdf_out, width='1920', height='1080', print_background=False)
#
#         await browser.close()
#
# html_dir = './results/frames/html'
# pdf_dir = './results/frames/pdf'
# asyncio.run(convert_html_to_images(html_dir, pdf_dir))

if __name__ == '__main__':
    filename = 'ithaca'
    solver_params = '_QS-FACTOR-{0}'.format(QS_FACTOR)
    # main(filename, solver_params)
    frequencies(filename, solver_params)
