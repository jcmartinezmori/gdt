
import osmnx as ox, geopandas as gpd
from shapely.geometry import Point
from rasterstats import zonal_stats
import rasterio


# 1. Grab a node in Tompkins County
G = ox.graph_from_place("Tompkins County, NY, USA", network_type="drive")
node = list(G.nodes())[0]
x, y = G.nodes[node]['x'], G.nodes[node]['y']
buffer = gpd.GeoSeries([Point(x, y).buffer(1000)], crs="EPSG:4326").to_crs(epsg=3857)

# 2. Use Census TIGER+ACS tracts for population
import tidycensus
tidycensus.set_api_key(KEY)
tracts = tidycensus.get_acs(geography="tract", variables="B01003_001",
                            state="36", county="109", geometry=True)

pop = tracts[tracts.intersects(buffer.unary_union)].geometry \
            .apply(lambda g: tracts.loc[tracts.geometry.intersects(g), 'estimate'].sum())

# 3. Compute density
area_km2 = buffer.area.iloc[0] / 1e6
density = pop.iloc[0] / area_km2


KEY = '3e424ebf64342bae345a0a764c6b687c3b9883ab'
