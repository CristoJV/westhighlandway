# %%
import ast
import os
import geopandas as gpd
import pandas as pd
from shapely import Point
from shapely.geometry import LineString
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.colors import LightSource
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import rasterio
import osmnx as ox

from extract import extract_kml_segments
from utils import filter_and_smooth_geometries, stylize_natural_geometries

RES_DIR = "res"
OUTPUT_DIR = "output"
KML_FILEPATH = f"{RES_DIR}/whw.kml"
SEGMENTS_CSV_FILEPATH = f"{RES_DIR}/segments.csv"
POINTS_CSV_FILEPATH = f"{RES_DIR}/points.csv"

ELEVATION_FILEPATH = f"{RES_DIR}/whw.tif"
NATURE_FILEPATH = f"{RES_DIR}/cached_nature.gpkg"
LAKES_FILEPATH = f"{RES_DIR}/cached_lakes_scotland.gpkg"
OUTPUT_FILEPATH = f"{OUTPUT_DIR}/whw.pdf"

SAVE_MAP = True
DPI = 500
BUFFER = 0.1

# ------------------------- Style Settings --------------------------- #
WATER_COLOR = "#8aa6a3"
ROUTE_COLOR = "#3b2f25"
STEP_COLOR = "#9e5741"
FOREST_COLOR = "#6a845e"
GRASS_COLOR = "#adb88f"
NATURE_ALPHA = 0.5

beige_cmap = mcolors.LinearSegmentedColormap.from_list(
    "beige",
    [
        "#7f6a53",  # Marrón tierra oscura para las sombras profundas
        "#a89070",  # Beige arena cálido para zonas bajas
        "#c8b28a",  # Amarillo arena suave para elevaciones medias
        "#e0cfac",  # Beige claro con toque cálido para zonas más altas
        "#f3e7d3",  # Beige pastel arena para las cumbres más elevadas
    ],
)
# -------------------------------------------------------------------- #
# Ensure required directories exist
# -------------------------------------------------------------------- #
for path in [RES_DIR, OUTPUT_DIR]:
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"📁 Created '{path}'")

# -------------------------------------------------------------------- #
# Load or extract route data
# -------------------------------------------------------------------- #
if not os.path.exists(SEGMENTS_CSV_FILEPATH) or not os.path.exists(
    POINTS_CSV_FILEPATH
):
    print("📡 Extracting segments and points from KML...")
    _, _ = extract_kml_segments(KML_FILEPATH, output_dir="res", save_csv=True)
else:
    print("✅ Loading existing CSV files for segments and points...")

segments_df = pd.read_csv(SEGMENTS_CSV_FILEPATH)
points_df = pd.read_csv(POINTS_CSV_FILEPATH)


gdf_combined = gpd.GeoDataFrame(
    {
        "name": segments_df["Name"],
        "geometry": [
            LineString(coords)
            for coords in segments_df["Coordinates"].apply(eval)
        ],
    },
    geometry="geometry",
    crs="EPSG:4326",
)

# Map extents
minx, miny, maxx, maxy = gdf_combined.total_bounds
center_x = (minx + maxx) / 2
center_y = (miny + maxy) / 2

# -------------------------------------------------------------------- #
# Create base map
# -------------------------------------------------------------------- #
fig, ax = plt.subplots(
    figsize=(16.5, 16.5 * 1.60),
    dpi=DPI,
    subplot_kw={"projection": ccrs.PlateCarree()},
)


# -------------------------------------------------------------------- #
# Load elevation and render hillshade
# -------------------------------------------------------------------- #
print("⛰️  Loading elevation data...")
with rasterio.open(ELEVATION_FILEPATH) as src:
    dem = src.read(1)
    extent = [
        src.bounds.left,
        src.bounds.right,
        src.bounds.bottom,
        src.bounds.top,
    ]

# # Upscale DEM data (e.g., 2x resolution for sharper raster)
# dem = zoom(dem, 2, order=3)

print("🌄 Generating hillshade...")
ls = LightSource(azdeg=315, altdeg=45)
hillshade = ls.hillshade(dem, vert_exag=1.5, dx=1, dy=1)

ax.imshow(
    hillshade,
    extent=extent,
    transform=ccrs.PlateCarree(),
    cmap=beige_cmap,
    alpha=1,
    zorder=2,
    rasterized=True,
)

# -------------------------------------------------------------------- #
# Load nature features (forests, grass, etc.)
# -------------------------------------------------------------------- #

if os.path.exists(NATURE_FILEPATH):
    print("🌲 Loading cached nature data...")
    gdf_nature = gpd.read_file(NATURE_FILEPATH)
else:
    print("🛰️  Downloading nature data from OSM...")
    all_nature_tags = {
        "natural": [
            "wood",
            "grassland",
            "heath",
            "scrub",
            "wetland",
            "tundra",
        ],
        "landuse": ["forest", "meadow", "farmland", "grass", "orchard"],
        "landcover": ["grass", "crop"],
        "leisure": ["nature_reserve", "park"],
    }

    gdf_nature = ox.features_from_point(
        (center_y, center_x), dist=70000, tags=all_nature_tags
    )
    gdf_nature.to_file(NATURE_FILEPATH, driver="GPKG")
    print(f"💾 Saved to cache: {NATURE_FILEPATH}")


def classify(row):
    grass_tags = {
        "natural": ["heath"],
        "landuse": ["meadow", "farmland", "grass", "orchard"],
        "landcover": ["grass", "crop"],
    }

    forest_tags = {
        "landuse": ["forest"],
        "natural": ["wood", "tundra"],
    }

    if row.get("natural") in forest_tags["natural"]:
        return "forest"
    elif row.get("landuse") in forest_tags["landuse"]:
        return "forest"
    elif row.get("natural") in grass_tags["natural"]:
        return "grass"
    else:
        return "other"


gdf_nature["category"] = gdf_nature.apply(classify, axis=1)
gdf_nature = stylize_natural_geometries(gdf_nature, area_threshold_m2=170000)


nature_colors = {
    "forest": FOREST_COLOR,
    "grass": GRASS_COLOR,
}

print("🌳 Plotting nature features...")
for cat, group in gdf_nature.groupby("category"):
    if cat in nature_colors:
        color = nature_colors.get(cat, "#cccccc")
        group.plot(
            ax=ax,
            facecolor=color,
            edgecolor="none",
            alpha=NATURE_ALPHA,
            zorder=6,
            label=cat,
        )

# -------------------------------------------------------------------- #
# Load lakes
# -------------------------------------------------------------------- #

ax.add_feature(cfeature.OCEAN, facecolor=WATER_COLOR, zorder=20)
ax.add_feature(cfeature.RIVERS, linewidth=1, color=WATER_COLOR, zorder=5)

if os.path.exists(LAKES_FILEPATH):
    print("🏞️  Loading cached lake data...")
    gdf_lakes_osm = gpd.read_file(LAKES_FILEPATH)
else:
    print("📥 Downloading lakes from OSM...")
    gdf_lakes_osm = ox.features_from_point(
        (center_y, center_x),
        dist=70000,
        tags={
            "natural": ["water"],
            "water": [
                "lake",
                "reservoir",
                "river",
                "stream",
            ],
        },
    )
    gdf_lakes_osm.to_file(LAKES_FILEPATH, driver="GPKG")
    print(f"💾 Saved lakes to: {LAKES_FILEPATH}")

gdf_lakes_osm = filter_and_smooth_geometries(
    gdf_lakes_osm, area_threshold_m2=150000
)

gdf_lakes_osm.plot(
    ax=ax,
    color=WATER_COLOR,
    alpha=1,
    edgecolor="black",
    linewidth=0,
    zorder=10,
)

# -------------------------------------------------------------------- #
# Plot route and points of interest
# -------------------------------------------------------------------- #
points_df["geometry"] = points_df["Coordinates"].apply(
    lambda coord: Point(
        ast.literal_eval(coord)[0][0], ast.literal_eval(coord)[0][1]
    )
)

points_gdf = gpd.GeoDataFrame(points_df, geometry="geometry", crs="EPSG:4326")

points_gdf.plot(
    ax=ax,
    color=STEP_COLOR,
    markersize=130,
    marker="o",
    label="Points of Interest",
    zorder=20,
    edgecolor=ROUTE_COLOR,
    linewidth=3,
)

gdf_combined.plot(
    ax=ax, color=ROUTE_COLOR, linewidth=3, edgecolor=ROUTE_COLOR, zorder=12
)

# -------------------------------------------------------------------- #
# Set final map extent and save
# -------------------------------------------------------------------- #
map_height = maxy - miny
map_width = map_height * 1.57

ax.set_extent(
    [
        center_x - map_width / 2 - BUFFER,
        center_x + map_width / 2 + BUFFER,
        miny - BUFFER,
        maxy + BUFFER,
    ],
    crs=ccrs.PlateCarree(),
)


if SAVE_MAP:
    print(f"💾 Saving final vector map as PDF using {DPI} DPI")
    plt.savefig(OUTPUT_FILEPATH, format="pdf", bbox_inches="tight", dpi=DPI)

print(f"✅ Map successfully saved as '{OUTPUT_FILEPATH}'")

# %%
