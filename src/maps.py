import asyncio
import folium
import os
import itertools as it
import osmnx as ox
import pandas as pd
import pickle
import shutil
from playwright.async_api import async_playwright
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
from src.config import *


def main(filename, solver_params):

    instance_filename = filename
    solution_filename = filename + '_' + solver_params

    G = ox.load_graphml('./results/instances/graph_{0}.graphml'.format(instance_filename))
    with open('./results/instances/instance_{0}.pkl'.format(instance_filename), 'rb') as file:
        instance = pickle.load(file)
        W, st_pairs, L, L_st, C, T, T_st = instance
    with open('./results/solutions/P_u_{0}.pkl'.format(solution_filename), 'rb') as file:
        P_u = pickle.load(file)
    with open('./results/solutions/P_y_{0}.pkl'.format(solution_filename), 'rb') as file:
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
    folium_map.save('./results/frames/html/current_plan_{0}.html'.format(solution_filename))

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
    folium_map.save('./results/frames/html/candidate_lines_{0}.html'.format(solution_filename))

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
    folium_map.save('./results/frames/html/ridership_plan_{0}.html'.format(solution_filename))

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
    folium_map.save('./results/frames/html/coverage_plan_{0}.html'.format(solution_filename))


def frequencies(filename, solver_params):

    instance_filename = filename
    solution_filename = filename + '_' + solver_params

    G = ox.load_graphml('./results/instances/graph_{0}.graphml'.format(instance_filename))
    with open('./results/instances/instance_{0}.pkl'.format(instance_filename), 'rb') as file:
        instance = pickle.load(file)
        W, st_pairs, L, L_st, C, T, T_st = instance
    with open('./results/solutions/P_u_{0}.pkl'.format(solution_filename), 'rb') as file:
        P_u = pickle.load(file)
    with open('./results/solutions/P_y_{0}.pkl'.format(solution_filename), 'rb') as file:
        P_y = pickle.load(file)

    C_dict = {ell: h for ell, h in C}
    freq_C = {(s, t): 0 for s, t in st_pairs}
    for ell, h in C_dict.items():
        for s, t in it.combinations(L[ell]['coverage'], 2):
            try:
                freq_C[tuple(sorted((s, t)))] += 1/h
            except KeyError:
                continue
    for (ell1, h1), (ell2, h2) in it.combinations(C_dict.items(), 2):
        if h1 <= TRANSFER_H and h2 <= TRANSFER_H:
            if tuple(sorted((ell1, ell2))) in T:
                for s, t in T[tuple(sorted((ell1, ell2)))]['ell1_ell2_st_coverage']:
                    freq_C[tuple(sorted((s, t)))] += 1/max(h1, h2)

    P_u_dict = {ell: h for ell, h in P_u}
    freq_P_u = {(s, t): 0 for s, t in st_pairs}
    for ell, h in P_u_dict.items():
        for s, t in it.combinations(L[ell]['coverage'], 2):
            try:
                freq_P_u[tuple(sorted((s, t)))] += 1/h
            except KeyError:
                continue
    for (ell1, h1), (ell2, h2) in it.combinations(P_u_dict.items(), 2):
        if h1 <= TRANSFER_H and h2 <= TRANSFER_H:
            if tuple(sorted((ell1, ell2))) in T:
                for s, t in T[tuple(sorted((ell1, ell2)))]['ell1_ell2_st_coverage']:
                    freq_P_u[tuple(sorted((s, t)))] += 1/max(h1, h2)

    P_y_dict = {ell: h for ell, h in P_y}
    freq_P_y = {(s, t): 0 for s, t in st_pairs}
    for ell, h in P_y_dict.items():
        for s, t in it.combinations(L[ell]['coverage'], 2):
            try:
                freq_P_y[tuple(sorted((s, t)))] += 1/h
            except KeyError:
                continue
    for (ell1, h1), (ell2, h2) in it.combinations(P_y_dict.items(), 2):
        if h1 <= TRANSFER_H and h2 <= TRANSFER_H:
            if tuple(sorted((ell1, ell2))) in T:
                for s, t in T[tuple(sorted((ell1, ell2)))]['ell1_ell2_st_coverage']:
                    freq_P_y[tuple(sorted((s, t)))] += 1/max(h1, h2)

    freq_df = pd.DataFrame([freq_C, freq_P_u, freq_P_y]).T
    freq_df.columns = ['Current Service Plan', 'Ridership Service Plan', 'Coverage Service Plan']

    fig = make_subplots(
        rows=1, cols=1,
        subplot_titles=('Distribution of Level of Service (with {0:.1f}-Incentive Compatibility)'.format(LS_FACTOR),)
    )

    for col in freq_df.columns:
        x = list(range(len(freq_df[col])))
        y = np.sort(freq_df[col].values)
        fig.add_trace(go.Scatter(
            x=x,
            y=y,
            mode='lines',
            name=f"{col}"
        ))

    fig.update_yaxes(
        row=1, col=1,
        title_text=r'$\large \textrm{Effective Service Frequency}$',
        title_font={'size': 18},
        range=[0 - 0.025, 0.25 + 0.025]
    )
    fig.update_xaxes(
        row=1, col=1,
        title_text=r'$\large \textrm{Origin-Destination Pairs (sorted by Effective Service Frequency)}$',
        title_font={'size': 18},
        range=[0 - 0.025 * len(freq_df[col]), len(freq_df[col]) + 0.025 * len(freq_df[col])]
    )
    for annotation in fig['layout']['annotations']:
        annotation['font'] = {'size': 24}
        annotation['y'] = 1.0125
    fig.update_layout(
        legend={
            'orientation': 'v', 'entrywidth': 250, 'yanchor': 'top', 'y': 1-0.125/4, 'xanchor': 'left', 'x': 0.125/4,
            'font': {'size': 18}
        }
    )

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
    filename = 'ITHACA'
    solver_params = 'LS-FACTOR-{0}'.format(LS_FACTOR)
    # main(filename, solver_params)
    frequencies(filename, solver_params)
