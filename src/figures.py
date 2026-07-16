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
from pathlib import Path
import src.instance
from src.config import *


def hex_to_rgba(hex_color, alpha):
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


def __draw_stop(folium_map, s, G, rhos, F):

    radius = 1 + np.log10(float(rhos[s]))
    radius *= 5 if s in F else 1
    color = HEXVERMILLION if s in F else HEXBLACK
    if s in F:
        folium.RegularPolygonMarker(
            location=(float(G.nodes[s]['lat']), float(G.nodes[s]['lon'])), color=color, radius=radius, weight=0,
            fill=True, fill_opacity=1, tooltip=s,
            number_of_sides=5
        ).add_to(folium_map)
    else:
        folium.CircleMarker(
            location=(float(G.nodes[s]['lat']), float(G.nodes[s]['lon'])), color=color, radius=radius, weight=0,
            fill=True, fill_opacity=1, tooltip=s
        ).add_to(folium_map)


def __draw_line(folium_map, ell, h, G, L):
    ell_coords = [(float(G.nodes[stop]['lat']), float(G.nodes[stop]['lon'])) for stop in L[ell]['path_nodes']]
    HEXCOLOR = HEXCOLORS[ell % len(HEXCOLORS)]
    folium.PolyLine(
        ell_coords, color=HEXCOLOR, weight=max(H) / h, opacity=1,
        tooltip='Line: {0}, Service: {1:.2f} runs/hr'.format(L[ell]['route_id'], 60 / h)
    ).add_to(folium_map)


def current_map():

    G = src.instance.__load_G(PLACE)
    rhos = src.instance.__load_rhos(PLACE)
    W, T, F = src.instance.__load_W_T_F(PLACE)
    C = src.instance.__load_C(PLACE)
    L, _ = src.instance.__load_L_L_st(PLACE)

    # current service plan
    folium_map = folium.Map(location=CENTER, zoom_start=ZOOM, tiles=None)
    folium.TileLayer('OpenStreetMap', opacity=OPACITY).add_to(folium_map)
    for ell in C.keys():
        __draw_line(folium_map, ell, C[ell]['h'], G, L)
    for s in W:
        __draw_stop(folium_map, s, G, rhos, F)
    folium_map.save('./results/maps/html/current_service_plan_{0}.html'.format(PLACE))


def solution_maps(**kwargs):

    place = kwargs.get('place', PLACE)
    budget_factor = kwargs.get('budget_factor', BUDGET_FACTOR)
    ridership_factor = kwargs.get('ridership_factor', RIDERSHIP_FACTOR)
    solution_filename = place + '_' + 'BUDGET_FACTOR-{0}_RIDERSHIP_FACTOR-{1}'.format(budget_factor, ridership_factor)

    G = src.instance.__load_G(place)
    rhos = src.instance.__load_rhos(place)
    W, T, F = src.instance.__load_W_T_F(place)
    L, _ = src.instance.__load_L_L_st(place)

    with open('./results/solutions/P_u_{0}.pkl'.format(solution_filename), 'rb') as file:
        P_u = pickle.load(file)
    with open('./results/solutions/P_y_{0}.pkl'.format(solution_filename), 'rb') as file:
        P_y = pickle.load(file)

    # ridership service plan
    folium_map = folium.Map(location=CENTER, zoom_start=ZOOM, tiles=None)
    folium.TileLayer('OpenStreetMap', opacity=OPACITY).add_to(folium_map)
    for ell, h in P_u:
        __draw_line(folium_map, ell, h, G, L)
    for s in W:
        __draw_stop(folium_map, s, G, rhos, F)
    folium_map.save('./results/maps/html/ridership_service_plan_{0}.html'.format(solution_filename))

    # coverage service plan
    folium_map = folium.Map(location=CENTER, zoom_start=ZOOM, tiles=None)
    folium.TileLayer('OpenStreetMap', opacity=OPACITY).add_to(folium_map)
    for ell, h in P_y:
        __draw_line(folium_map, ell, h, G, L)
    for s in W:
        __draw_stop(folium_map, s, G, rhos, F)
    folium_map.save('./results/maps/html/coverage_service_plan_{0}.html'.format(solution_filename))


def diff_gain_solution_maps(solver_params):

    solution_filename = PLACE + '_' + solver_params

    G = src.instance.__load_G(PLACE)
    rhos = src.instance.__load_rhos(PLACE)
    W, _, _ = src.instance.__load_W_T_F(PLACE)
    C = src.instance.__load_C(PLACE)
    L, _ = src.instance.__load_L_L_st(PLACE)

    with open('./results/solutions/P_u_{0}.pkl'.format(solution_filename), 'rb') as file:
        P_u = pickle.load(file)
    with open('./results/solutions/P_y_{0}.pkl'.format(solution_filename), 'rb') as file:
        P_y = pickle.load(file)

    # ridership service plan
    folium_map = folium.Map(location=CENTER, zoom_start=ZOOM, tiles=None)
    folium.TileLayer('OpenStreetMap', opacity=OPACITY).add_to(folium_map)
    for ell, h in P_u:
        C_ell = C.get(ell)
        if C_ell is None or C_ell['h'] / h > 1:
            f_diff = 1/h if C_ell is None else 1/h - 1/C_ell['h']
            ell_coords = [
                (float(G.nodes[stop]['lat']), float(G.nodes[stop]['lon'])) for stop in L[ell]['path_nodes']
            ]
            HEXCOLOR = HEXCOLORS[ell % len(HEXCOLORS)]
            folium.PolyLine(
                ell_coords, color=HEXCOLOR, weight=max(H) * f_diff, opacity=1,
                tooltip='Line: {0}, Service Gain: {1:.2f} runs/hr'.format(L[ell]['route_id'], f_diff * 60)
            ).add_to(folium_map)
    for s in W:
        __draw_stop(folium_map, s, G, rhos, F)
    folium_map.save('./results/maps/html/diff_gain_ridership_service_plan_{0}.html'.format(solution_filename))

    # coverage service plan
    folium_map = folium.Map(location=CENTER, zoom_start=ZOOM, tiles=None)
    folium.TileLayer('OpenStreetMap', opacity=OPACITY).add_to(folium_map)
    for ell, h in P_y:
        C_ell = C.get(ell)
        if C_ell is None or C_ell['h'] / h > 1:
            f_diff = 1/h if C_ell is None else 1/h - 1/C_ell['h']
            ell_coords = [
                (float(G.nodes[stop]['lat']), float(G.nodes[stop]['lon'])) for stop in L[ell]['path_nodes']
            ]
            HEXCOLOR = HEXCOLORS[ell % len(HEXCOLORS)]
            folium.PolyLine(
                ell_coords, color=HEXCOLOR, weight=max(H) * f_diff, opacity=1,
                tooltip='Line: {0}, Service Gain: {1:.2f} runs/hr'.format(L[ell]['route_id'], f_diff * 60)
            ).add_to(folium_map)
    for s in W:
        __draw_stop(folium_map, s, G, rhos, F)
    folium_map.save('./results/maps/html/diff_gain_coverage_service_plan_{0}.html'.format(solution_filename))


def diff_loss_solution_maps(solver_params):

    solution_filename = PLACE + '_' + solver_params

    G = src.instance.__load_G(PLACE)
    rhos = src.instance.__load_rhos(PLACE)
    W, _, _ = src.instance.__load_W_T_F(PLACE)
    C = src.instance.__load_C(PLACE)
    L, _ = src.instance.__load_L_L_st(PLACE)

    with open('./results/solutions/P_u_{0}.pkl'.format(solution_filename), 'rb') as file:
        P_u = pickle.load(file)
    with open('./results/solutions/P_y_{0}.pkl'.format(solution_filename), 'rb') as file:
        P_y = pickle.load(file)

    # ridership service plan
    folium_map = folium.Map(location=CENTER, zoom_start=ZOOM, tiles=None)
    folium.TileLayer('OpenStreetMap', opacity=OPACITY).add_to(folium_map)
    P_u = {ell: h for ell, h in P_u}
    for ell in C.keys():
        P_u_ell_h = P_u.get(ell)
        if P_u_ell_h is None or P_u_ell_h / C[ell]['h'] > 1:
            f_diff = 1 / C[ell]['h'] if P_u_ell_h is None else 1/C[ell]['h'] - 1/P_u_ell_h
            ell_coords = [
                (float(G.nodes[stop]['lat']), float(G.nodes[stop]['lon'])) for stop in L[ell]['path_nodes']
            ]
            HEXCOLOR = HEXCOLORS[ell % len(HEXCOLORS)]
            folium.PolyLine(
                ell_coords, color=HEXCOLOR, weight=max(H) * f_diff, opacity=1,
                tooltip='Line: {0}, Service Loss: {1:.2f} runs/hr'.format(L[ell]['route_id'], f_diff * 60)
            ).add_to(folium_map)
    for s in W:
        __draw_stop(folium_map, s, G, rhos, F)
    folium_map.save('./results/maps/html/diff_loss_ridership_service_plan_{0}.html'.format(solution_filename))

    # coverage service plan
    folium_map = folium.Map(location=CENTER, zoom_start=ZOOM, tiles=None)
    folium.TileLayer('OpenStreetMap', opacity=OPACITY).add_to(folium_map)
    P_y = {ell: h for ell, h in P_y}
    for ell in C.keys():
        P_y_ell_h = P_y.get(ell)
        if P_y_ell_h is None or P_y_ell_h / C[ell]['h'] > 1:
            f_diff = 1 / C[ell]['h'] if P_y_ell_h is None else 1/C[ell]['h'] - 1/P_y_ell_h
            ell_coords = [
                (float(G.nodes[stop]['lat']), float(G.nodes[stop]['lon'])) for stop in L[ell]['path_nodes']
            ]
            HEXCOLOR = HEXCOLORS[ell % len(HEXCOLORS)]
            folium.PolyLine(
                ell_coords, color=HEXCOLOR, weight=max(H) * f_diff, opacity=1,
                tooltip='Line: {0}, Service Loss: {1:.2f} runs/hr'.format(L[ell]['route_id'], f_diff * 60)
            ).add_to(folium_map)
    for s in W:
        __draw_stop(folium_map, s, G, rhos, F)
    folium_map.save('./results/maps/html/diff_loss_coverage_service_plan_{0}.html'.format(solution_filename))


def diff_neutral_solution_maps(solver_params):

    solution_filename = PLACE + '_' + solver_params

    G = src.instance.__load_G(PLACE)
    rhos = src.instance.__load_rhos(PLACE)
    W, _, _ = src.instance.__load_W_T_F(PLACE)
    C = src.instance.__load_C(PLACE)
    L, _ = src.instance.__load_L_L_st(PLACE)

    with open('./results/solutions/P_u_{0}.pkl'.format(solution_filename), 'rb') as file:
        P_u = pickle.load(file)
    with open('./results/solutions/P_y_{0}.pkl'.format(solution_filename), 'rb') as file:
        P_y = pickle.load(file)

    # ridership service plan
    folium_map = folium.Map(location=CENTER, zoom_start=ZOOM, tiles=None)
    folium.TileLayer('OpenStreetMap', opacity=OPACITY).add_to(folium_map)
    for ell, h in P_u:
        C_ell = C.get(ell)
        if C_ell is not None and C_ell['h'] / h == 1:
            ell_coords = [
                (float(G.nodes[stop]['lat']), float(G.nodes[stop]['lon'])) for stop in L[ell]['path_nodes']
            ]
            HEXCOLOR = HEXCOLORS[ell % len(HEXCOLORS)]
            folium.PolyLine(
                ell_coords, color=HEXCOLOR, weight=max(H) / h, opacity=1,
                tooltip='Line: {0}, Service: {1:.2f} runs/hr'.format(L[ell]['route_id'], 1 / h * 60)
            ).add_to(folium_map)
    for s in W:
        __draw_stop(folium_map, s, G, rhos, F)
    folium_map.save('./results/maps/html/diff_neutral_ridership_service_plan_{0}.html'.format(solution_filename))

    # coverage service plan
    folium_map = folium.Map(location=CENTER, zoom_start=ZOOM, tiles=None)
    folium.TileLayer('OpenStreetMap', opacity=OPACITY).add_to(folium_map)
    for ell, h in P_y:
        C_ell = C.get(ell)
        if C_ell is not None and C_ell['h'] / h == 1:
            ell_coords = [
                (float(G.nodes[stop]['lat']), float(G.nodes[stop]['lon'])) for stop in L[ell]['path_nodes']
            ]
            HEXCOLOR = HEXCOLORS[ell % len(HEXCOLORS)]
            folium.PolyLine(
                ell_coords, color=HEXCOLOR, weight=max(H) / h, opacity=1,
                tooltip='Line: {0}, Service: {1:.2f} runs/hr'.format(C[ell]['route_id'], 1 / h * 60)
            ).add_to(folium_map)
    for s in W:
        __draw_stop(folium_map, s, G, rhos, F)
    folium_map.save('./results/maps/html/diff_neutral_coverage_service_plan_{0}.html'.format(solution_filename))


def level_of_service(solver_params_list, **kwargs):

    place = kwargs.get('place', PLACE)

    rhos = src.instance.__load_rhos(place)
    st_pairs = src.instance.__load_st_pairs(place)
    C = src.instance.__load_C(place)
    L, L_st = src.instance.__load_L_L_st(place)

    data = []
    for solver_params in solver_params_list:

        budget_factor, ridership_factor = solver_params

        solver_params = 'BUDGET_FACTOR-{0}_RIDERSHIP_FACTOR-{1}'.format(budget_factor, ridership_factor)
        solution_filename = place + '_' + solver_params

        with open('./results/solutions/P_u_{0}.pkl'.format(solution_filename), 'rb') as file:
            P_u = pickle.load(file)

        P_u_dict = {ell: h for ell, h in P_u}
        freq_P_u = {(s, t): 0 for s, t in st_pairs}
        for ell, h in P_u_dict.items():
            for s, t in L[ell]['st_pairs']:
                freq_P_u[(s, t)] += 1 / h

        ridership = sum(np.sqrt(rhos[s] * rhos[t]) * np.sqrt(60 * freq) for (s, t), freq in freq_P_u.items())
        coverage = sum(1 for freq in freq_P_u.values() if freq >= 1/COVERAGE_H)
        html_filename = './results/maps/html/ridership_service_plan_{0}.html'.format(solution_filename)
        data.append(('Ridership', ridership, coverage, ridership_factor, budget_factor, HEXVERMILLION, html_filename))

        with open('./results/solutions/P_y_{0}.pkl'.format(solution_filename), 'rb') as file:
            P_y = pickle.load(file)
        P_y_dict = {ell: h for ell, h in P_y}
        freq_P_y = {(s, t): 0 for s, t in st_pairs}
        for ell, h in P_y_dict.items():
            for s, t in L[ell]['st_pairs']:
                freq_P_y[(s, t)] += 1 / h

        ridership = sum(np.sqrt(rhos[s] * rhos[t]) * np.sqrt(60 * freq) for (s, t), freq in freq_P_y.items())
        coverage = sum(1 for freq in freq_P_y.values() if freq >= 1/COVERAGE_H)
        html_filename = './results/maps/html/coverage_service_plan_{0}.html'.format(solution_filename)
        data.append(('Coverage', ridership, coverage, ridership_factor, budget_factor, HEXBLUE, html_filename))

    C_dict = {ell: C[ell]['h'] for ell in C.keys()}
    freq_C = {(s, t): 0 for s, t in st_pairs}
    for ell, h in C_dict.items():
        for s, t in L[ell]['st_pairs']:
            freq_C[(s, t)] += 1 / h

    ridership = sum(np.sqrt(rhos[s] * rhos[t]) * np.sqrt(60 * freq) for (s, t), freq in freq_C.items())
    coverage = sum(1 for freq in freq_C.values() if freq >= 1/COVERAGE_H)
    html_filename = './results/maps/html/current_service_plan_{0}.html'.format(place)

    df = pd.DataFrame(
        data, columns=['goal', 'ridership', 'coverage', 'ridership_factor', 'budget_factor', 'hexcolor', 'html_filename']
    )

    symbol_map = {
        1.0: 'circle',
        0.9: 'triangle-down',
        0.8: 'x'
    }

    df['color'] = df.apply(lambda row: hex_to_rgba(row['hexcolor'], row['ridership_factor']), axis=1)
    df['symbol'] = df['budget_factor'].map(symbol_map)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=[coverage],
            y=[ridership],
            mode='markers',
            marker=dict(
                color=[HEXBLACK],
                symbol='star',
                size=20,
                line=dict(color="black", width=2),
            ),
            customdata=[['Current Service Plan', ridership, coverage, None, None, html_filename]],
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                'Ridership: %{customdata[1]:.2f}<br>'
                'Coverage: %{customdata[2]}<br>'
                '<extra></extra>'
            ),
            showlegend=False
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df['coverage'],
            y=df['ridership'],
            mode="markers",
            marker=dict(
                symbol=df['symbol'],
                color=df['color'],
                size=25,
            ),
            customdata=df[['goal', 'ridership', 'coverage', 'ridership_factor', 'budget_factor', 'html_filename']],
            hovertemplate=(
                "<b>Goal: %{customdata[0]}</b><br>"
                'Ridership: %{customdata[1]:.2f}<br>'
                'Coverage: %{customdata[2]}<br>'
                'Ridership Factor: %{customdata[3]}<br>'
                'Budget Factor: %{customdata[4]}<br>'
                '<extra></extra>'
            ),
            showlegend=False
        )
    )

    fig.update_layout(
        xaxis=dict(
            title=r'$\Large \textrm{Coverage } [\mathtt{OD \ pairs}]$',
            title_font=dict(size=24),
            tickfont=dict(size=16)
        ),
        yaxis=dict(
            title=r'$\Large \textrm{Ridership } [\mathtt{amenities} \times \sqrt{\mathtt{runs/hr}}]$',
            title_font=dict(size=24),
            tickfont=dict(size=16)
        )
    )

    html = fig.to_html(
        include_plotlyjs='cdn',
        full_html=True,
        div_id='scatter',
        include_mathjax='cdn'
    )

    html += """
    <script>
    document.getElementById("scatter").on("plotly_click", function(data) {
        var filename = data.points[0].customdata[5];
        window.open("./../../" + filename, "_blank");
    });
    </script>
    """

    with open('./results/figures/level_of_service_{0}.html'.format(place), 'w', encoding="utf-8") as file:
        file.write(html)







# def level_of_service(solver_params):
#
#     solution_filename = PLACE + '_' + solver_params
#
#     G = src.instance.__load_G(PLACE)
#     rhos = src.instance.__load_rhos(PLACE)
#     W, T, F = src.instance.__load_W_T_F(PLACE)
#     st_pairs = src.instance.__load_st_pairs(PLACE)
#     C = src.instance.__load_C(PLACE)
#     L, L_st = src.instance.__load_L_L_st(PLACE)
#
#     with open('./results/solutions/P_u_{0}.pkl'.format(solution_filename), 'rb') as file:
#         P_u = pickle.load(file)
#     with open('./results/solutions/P_y_{0}.pkl'.format(solution_filename), 'rb') as file:
#         P_y = pickle.load(file)
#
#     C_dict = {ell: C[ell]['h'] for ell in C.keys()}
#     P_u_dict = {ell: h for ell, h in P_u}
#     P_y_dict = {ell: h for ell, h in P_y}
#
#     freq_C = {(s, t): 0 for s, t in st_pairs}
#     freq_P_u = {(s, t): 0 for s, t in st_pairs}
#     freq_P_y = {(s, t): 0 for s, t in st_pairs}
#     for s, t in st_pairs:
#         for ell in L_st[(s, t)]:
#             if ell in C_dict.keys():
#                 freq_C[(s, t)] += 1/C_dict[ell]
#             if ell in P_u_dict.keys():
#                 freq_P_u[(s, t)] += 1/P_u_dict[ell]
#             if ell in P_y_dict.keys():
#                 freq_P_y[(s, t)] += 1/P_y_dict[ell]
#
#     freq_df = pd.DataFrame([freq_C, freq_P_u, freq_P_y]).T
#     freq_df.columns = ['Current Service Plan', 'Ridership Service Plan', 'Coverage Service Plan']
#
#     fig = go.Figure()
#
#     colors = [HEXORANGE, HEXBLUE, HEXVERMILLION]
#     for i, col in enumerate(freq_df.columns):
#         x = list(range(len(freq_df[col])))
#         y = np.sort(freq_df[col].values)
#         fig.add_trace(go.Scatter(
#             x=x,
#             y=y,
#             mode='lines',
#             name=f"{col}",
#             line=dict(color=colors[i], width=2),
#             showlegend=True
#         ))
#     fig.update_yaxes(
#         title_text=r'$\large \textrm{Service Frequency } [\mathtt{min}^{-1}]$',
#         title_font={'size': 20}
#     )
#     fig.update_xaxes(
#         title_text=r'$\large \textrm{Origin-Destination Pairs (sorted by Service Frequency)}$',
#         title_font={'size': 20}
#     )
#     fig.show()
#
#     for annotation in fig['layout']['annotations']:
#         annotation['font'] = {'size': 24}
#         # annotation['y'] = 1.0125
#     fig.update_layout(
#         legend={
#             'orientation': 'v', 'entrywidth': 250, 'yanchor': 'top', 'y': 1-0.125/4, 'xanchor': 'left', 'x': 0.125/4,
#             'font': {'size': 20}
#         }
#     )
#     fig.write_image(
#         './results/figures/los_{0}.pdf'.format(solution_filename),
#         width=1200, height=800
#     )
#     # fig.show()





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
            pdf_out = Path(pdf_dir)/'{0}.pdf'.format(html_file.name.strip('./html'))

            await page.goto(file_url)
            await page.set_viewport_size({'width': 1920, 'height': 1080})
            await page.wait_for_load_state('networkidle')
            await page.pdf(path=pdf_out, width='1920', height='1080', print_background=False)

        await browser.close()


if __name__ == '__main__':

    # current_map()

    # budget_factors = [1.0, 0.9, 0.8]
    # ridership_factors = [0.7, 0.65, 0.6, 0.55, 0.5]
    budget_factors = [1.0]
    ridership_factors = [0.7]
    for budget_factor in budget_factors:
        for ridership_factor in ridership_factors:
            kwargs = {
                'budget_factor': budget_factor,
                'ridership_factor': ridership_factor,
            }
            solution_maps(**kwargs)

    # diff_gain_solution_maps(solver_params)
    # diff_loss_solution_maps(solver_params)
    # diff_neutral_solution_maps(solver_params)

    # budget_factors = [1.0, 0.9, 0.8]
    # ridership_factors = [0.7, 0.65, 0.6, 0.55, 0.5]
    # solver_params_list = [
    #     (budget_factor, ridership_factor) for budget_factor in budget_factors for ridership_factor in ridership_factors
    # ]
    # level_of_service(solver_params_list)

    # html_dir = './results/maps/html'
    # pdf_dir = './results/maps/pdf'
    # asyncio.run(convert_html_to_images(html_dir, pdf_dir))
