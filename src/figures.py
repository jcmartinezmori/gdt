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
import src.instance
from src.config import *


def maps(filename, solver_params):

    instance_filename = filename
    solution_filename = filename + '_' + solver_params

    G, U, B, stop_nodes, W, st_pairs, dists, L, L_st, C, T, T_st = src.instance.load_instance(instance_filename)
    with open('./results/solutions/P_u_{0}.pkl'.format(solution_filename), 'rb') as file:
        P_u = pickle.load(file)
    with open('./results/solutions/P_y_{0}.pkl'.format(solution_filename), 'rb') as file:
        P_y = pickle.load(file)

    # current service plan
    folium_map = folium.Map(location=CENTER, zoom_start=ZOOM, tiles=None)
    folium.TileLayer('OpenStreetMap', opacity=OPACITY).add_to(folium_map)
    for s in W:
        folium.CircleMarker(
            location=(G.nodes[s]['y'], G.nodes[s]['x']), color=HEXBLACK, radius=2.5, weight=0,
            fill=True, fill_opacity=1, tooltip=s
        ).add_to(folium_map)
    for ell, h in C:
        ell_coords = [(G.nodes[stop]['y'], G.nodes[stop]['x']) for stop in L[ell]['path']]
        HEXCOLOR = HEXCOLORS[ell % len(HEXCOLORS)]
        folium.PolyLine(
                ell_coords, color=HEXCOLOR, weight=1/h*max(H), opacity=1, tooltip=L[ell]['route_id']
        ).add_to(folium_map)
    folium_map.save('./results/frames/html/current_service_plan_{0}.html'.format(solution_filename))

    # candidate lines
    folium_map = folium.Map(location=CENTER, zoom_start=ZOOM, tiles=None)
    folium.TileLayer('OpenStreetMap', opacity=OPACITY).add_to(folium_map)
    for s in W:
        folium.CircleMarker(
            location=(G.nodes[s]['y'], G.nodes[s]['x']), color=HEXBLACK, radius=2.5, weight=0,
            fill=True, fill_opacity=1, tooltip=s
        ).add_to(folium_map)
    for ell in L.keys():
        ell_coords = [(G.nodes[stop]['y'], G.nodes[stop]['x']) for stop in L[ell]['path']]
        HEXCOLOR = HEXCOLORS[ell % len(HEXCOLORS)]
        folium.PolyLine(
                ell_coords, color=HEXCOLOR, weight=4, opacity=1, tooltip=L[ell]['route_id']
        ).add_to(folium_map)
    folium_map.save('./results/frames/html/candidate_lines_{0}.html'.format(solution_filename))

    # ridership service plan
    folium_map = folium.Map(location=CENTER, zoom_start=ZOOM, tiles=None)
    folium.TileLayer('OpenStreetMap', opacity=OPACITY).add_to(folium_map)
    for s in W:
        folium.CircleMarker(
            location=(G.nodes[s]['y'], G.nodes[s]['x']), color=HEXBLACK, radius=2.5, weight=0,
            fill=True, fill_opacity=1, tooltip=s
        ).add_to(folium_map)
    for ell, h in P_u:
        ell_coords = [(G.nodes[stop]['y'], G.nodes[stop]['x']) for stop in L[ell]['path']]
        HEXCOLOR = HEXCOLORS[ell % len(HEXCOLORS)]
        folium.PolyLine(
                ell_coords, color=HEXCOLOR, weight=1/h*max(H), opacity=1, tooltip=L[ell]['route_id']
        ).add_to(folium_map)
    folium_map.save('./results/frames/html/ridership_service_plan_{0}.html'.format(solution_filename))

    # coverage service plan
    folium_map = folium.Map(location=CENTER, zoom_start=ZOOM, tiles=None)
    folium.TileLayer('OpenStreetMap', opacity=OPACITY).add_to(folium_map)
    for s in W:
        folium.CircleMarker(
            location=(G.nodes[s]['y'], G.nodes[s]['x']), color=HEXBLACK, radius=2.5, weight=0,
            fill=True, fill_opacity=1, tooltip=s
        ).add_to(folium_map)
    for ell, h in P_y:
        ell_coords = [(G.nodes[stop]['y'], G.nodes[stop]['x']) for stop in L[ell]['path']]
        HEXCOLOR = HEXCOLORS[ell % len(HEXCOLORS)]
        folium.PolyLine(
                ell_coords, color=HEXCOLOR, weight=1/h*max(H), opacity=1, tooltip=L[ell]['route_id']
        ).add_to(folium_map)
    folium_map.save('./results/frames/html/coverage_service_plan_{0}.html'.format(solution_filename))


def level_of_service(filename, solver_params):

    instance_filename = filename
    solution_filename = filename + '_' + solver_params

    st_pairs = src.instance.__load_st_pairs(instance_filename)
    L, L_st, C = src.instance.__load_L_L_st_C(instance_filename)
    T, T_st = src.instance.__load_T_T_st(instance_filename)

    with open('./results/solutions/P_u_{0}.pkl'.format(solution_filename), 'rb') as file:
        P_u = pickle.load(file)
    with open('./results/solutions/P_y_{0}.pkl'.format(solution_filename), 'rb') as file:
        P_y = pickle.load(file)

    C_dict = {ell: h for ell, h in C}
    P_u_dict = {ell: h for ell, h in P_u}
    P_y_dict = {ell: h for ell, h in P_y}

    freq_C = {(s, t): 0 for s, t in st_pairs}
    freq_P_u = {(s, t): 0 for s, t in st_pairs}
    freq_P_y = {(s, t): 0 for s, t in st_pairs}
    for s, t in st_pairs:
        for ell in L_st[(s, t)]:
            if ell in C_dict.keys():
                freq_C[(s, t)] += 1/C_dict[ell]
            if ell in P_u_dict.keys():
                freq_P_u[(s, t)] += 1/P_u_dict[ell]
            if ell in P_y_dict.keys():
                freq_P_y[(s, t)] += 1/P_y_dict[ell]

    freq_df = pd.DataFrame([freq_C, freq_P_u, freq_P_y]).T
    freq_df.columns = ['Current Service Plan', 'Ridership Service Plan', 'Coverage Service Plan']
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=(
            'Distribution of Level of Service with No Transfers ({0:.1f}-Incentive Compatibility)'.format(IC_FACTOR),
            'Distribution of Level of Service with One Transfer ({0:.1f}-Incentive Compatibility)'.format(IC_FACTOR)
        ),
        vertical_spacing=0.175
    )

    colors = [HEXORANGE, HEXBLUE, HEXVERMILLION]
    for i, col in enumerate(freq_df.columns):
        x = list(range(len(freq_df[col])))
        y = np.sort(freq_df[col].values)
        fig.add_trace(go.Scatter(
            x=x,
            y=y,
            mode='lines',
            name=f"{col}",
            line=dict(color=colors[i], width=2),
            showlegend=True
        ), row=1, col=1)
    fig.update_yaxes(
        row=1, col=1,
        title_text=r'$\large \textrm{Service Frequency } [\mathtt{min}^{-1}]$',
        title_font={'size': 20},
        range=[0 - 0.025, 0.6]
    )
    fig.update_xaxes(
        row=1, col=1,
        title_text=r'$\large \textrm{Origin-Destination Pairs (sorted by Service Frequency)}$',
        title_font={'size': 20},
        range=[125000, 200000]
    )

    for s, t in st_pairs:
        for ell1, ell2 in T_st[(s, t)]:
            if ell1 in C_dict.keys() and ell2 in C_dict.keys():
                if C_dict[ell1] <= TRANSFER_MIN_H or C_dict[ell2] <= TRANSFER_MIN_H:
                    freq_C[(s, t)] += 1/max(C_dict[ell1], C_dict[ell2])
            if ell1 in P_u_dict.keys() and ell2 in P_u_dict.keys():
                if P_u_dict[ell1] <= TRANSFER_MIN_H or P_u_dict[ell2] <= TRANSFER_MIN_H:
                    freq_P_u[(s, t)] += 1/max(P_u_dict[ell1], P_u_dict[ell2])
            if ell1 in P_y_dict.keys() and ell2 in P_y_dict.keys():
                if P_y_dict[ell1] <= TRANSFER_MIN_H or P_y_dict[ell2] <= TRANSFER_MIN_H:
                    freq_P_y[(s, t)] += 1/max(P_y_dict[ell1], P_y_dict[ell2])

    freq_df = pd.DataFrame([freq_C, freq_P_u, freq_P_y]).T
    freq_df.columns = ['Current Service Plan', 'Ridership Service Plan', 'Coverage Service Plan']

    for i, col in enumerate(freq_df.columns):
        x = list(range(len(freq_df[col])))
        y = np.sort(freq_df[col].values)
        fig.add_trace(go.Scatter(
            x=x,
            y=y,
            mode='lines',
            name=f"{col}",
            line=dict(color=colors[i], width=2),
            showlegend=False
        ), row=2, col=1)
    fig.update_yaxes(
        row=2, col=1,
        title_text=r'$\large \textrm{Service Frequency } [\mathtt{min}^{-1}]$',
        title_font={'size': 20},
        range=[0 - 0.025, 0.6]
    )
    fig.update_xaxes(
        row=2, col=1,
        title_text=r'$\large \textrm{Origin-Destination Pairs (sorted by Service Frequency)}$',
        title_font={'size': 20},
        range=[125000, 200000]
    )

    for annotation in fig['layout']['annotations']:
        annotation['font'] = {'size': 24}
        # annotation['y'] = 1.0125
    fig.update_layout(
        legend={
            'orientation': 'v', 'entrywidth': 250, 'yanchor': 'top', 'y': 1-0.125/4, 'xanchor': 'left', 'x': 0.125/4,
            'font': {'size': 20}
        }
    )
    fig.write_image(
        './results/figures/los_{0}.pdf'.format(solution_filename),
        width=1200, height=800
    )
    # fig.show()


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
    solver_params = 'IC-FACTOR-{0}'.format(IC_FACTOR)
    # maps(filename, solver_params)
    level_of_service(filename, solver_params)
