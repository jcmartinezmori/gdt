import asyncio
import folium
import os
import shutil
from playwright.async_api import async_playwright
from pathlib import Path
import pickle

filename = 'ithaca'

G = ox.load_graphml('./results/instances/G_{0}.graphml'.format(filename))
U = ox.load_graphml('./results/instances/U_{0}.graphml'.format(filename))
with open('./results/instances/instance_{0}.pkl'.format(filename), 'rb') as file:
    instance = pickle.load(file)
    W, st_pairs, L, L_st, C, T = instance
with open('./results/output/P_u_{0}.pkl'.format(filename), 'rb') as file:
    P_u = pickle.load(file)
with open('./results/output/P_y_{0}.pkl'.format(filename), 'rb') as file:
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
