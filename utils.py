# -------------------------------------------------------------------- #
# Utility Functions
# -------------------------------------------------------------------- #
import geopandas as gpd
from shapely import MultiPolygon, unary_union


def filter_and_smooth_geometries(
    gdf,
    area_threshold_m2=10000,
    smooth_strength_m=10,
    simplify_factor=3,
    input_crs="EPSG:4326",
    working_crs="EPSG:3857",
):
    """
    Filters out small geometries and smooths the shape of polygons
    using buffering and simplification techniques.

    Parameters:
        gdf: The input geometries (in WGS 84 / EPSG:4326).
        area_threshold_m2: Minimum area (in m²) to retain a shape.
        smooth_strength_m: Strength of smoothing, via positive/negative
            buffer.
        simplify_factor: Geometry simplification factor (higher = more
            simplified).
        input_crs: CRS of the input data (typically EPSG:4326).
        working_crs: Metric CRS used for area/smoothing
            (e.g., EPSG:3857).

    Returns:
        GeoDataFrame: Cleaned and smoothed geometries, in the original
        CRS.
    """

    # Reproject to metric CRS for area calculation and buffering
    gdf_m = gdf.to_crs(working_crs)

    # Calculate geometry area in square meters
    gdf_m["area_m2"] = gdf_m.geometry.area

    # Filter out small geometries
    gdf_filtered = gdf_m[gdf_m["area_m2"] > area_threshold_m2].copy()

    # Smooth geometry using buffer-in/buffer-out trick
    gdf_filtered["geometry"] = gdf_filtered.geometry.buffer(
        smooth_strength_m
    ).buffer(-smooth_strength_m)

    # Simplify geometry to reduce complexity (preserving topology)
    gdf_filtered["geometry"] = gdf_filtered.geometry.simplify(
        simplify_factor, preserve_topology=True
    )

    # Reproject back to the original input CRS
    gdf_final = gdf_filtered.to_crs(input_crs)
    return gdf_final


def stylize_natural_geometries(
    gdf,
    area_threshold_m2=170000,
    proximity_threshold_m=10,
    smooth_strength_m=5,
    simplify_factor=2,
    input_crs="EPSG:4326",
    working_crs="EPSG:3857",
):
    """
    Processes and styles natural land cover data:
    - Filters small patches
    - Merges nearby features of the same category
    - Smooths and simplifies geometry
    - Returns final styled shapes grouped by 'category'

    Parameters:
        gdf: Input data with natural/landuse elements.
        area_threshold_m2: Minimum polygon area to keep.
        proximity_threshold_m: Buffer size to merge nearby features.
        smooth_strength_m: Smoothing via buffer (optional).
        simplify_factor: Simplification tolerance.
        input_crs: Original CRS of the data.
        working_crs: Projected CRS for calculations.

    Returns:
        GeoDataFrame: Styled polygons per land cover category in
        original CRS.
    """

    # Reproject to metric CRS for area and buffering
    gdf = gdf.to_crs(working_crs)

    # Calculate area and filter out small shapes
    gdf["area_m2"] = gdf.geometry.area
    gdf = gdf[gdf["area_m2"] > area_threshold_m2].copy()

    final_geoms = []

    # Process each category separately
    for cat, group in gdf.groupby("category"):
        if cat != "other":
            # Merge nearby shapes with buffering
            buffered = group.geometry.buffer(proximity_threshold_m)

            # Union all geometries into one
            fused = unary_union(buffered)

            # Optional: smooth the result with a buffer
            if smooth_strength_m > 0:
                fused = fused.buffer(smooth_strength_m)

            # Simplify the resulting shape
            simplified = fused.simplify(
                simplify_factor, preserve_topology=True
            )

            # Ensure output is MultiPolygon-compatible
            if isinstance(simplified, (MultiPolygon,)):
                for geom in simplified.geoms:
                    final_geoms.append({"category": cat, "geometry": geom})
            else:
                final_geoms.append({"category": cat, "geometry": simplified})

    # Return as GeoDataFrame in original CRS
    gdf_result = gpd.GeoDataFrame(final_geoms, crs=working_crs)
    return gdf_result.to_crs(input_crs)
