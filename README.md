### 📝 `README.md`

# 🗺️ WHW Map Generator

This project generates a high-quality, vector-based map of the **West Highland Way** in Scotland, using OpenStreetMap data, elevation (DEM), and custom stylization in Python. Fully offline, customizable and exportable to PDF.

## 📷 Example Output

![WHW Map Preview](example/map_preview.png)

## 🚀 Features

- ✅ Elevation-based hillshade (rasterio + matplotlib)
- ✅ Smoothed and simplified natural features (forest, grassland)
- ✅ High-quality route lines and points of interest
- ✅ Styled vector export (PDF)

## ⚙️ Requirements

Install dependencies using `conda` or `pip`:

```bash
conda install geopandas rasterio shapely matplotlib cartopy osmnx
```

Or:

```bash
pip install geopandas rasterio shapely matplotlib cartopy osmnx
```

## 📁 Folder Structure

```
.
├── res/                  # Input resources (KML, DEM, cached features)
│   ├── whw.kml
│   ├── whw.tif
│   ├── cached_nature.gpkg
│   ├── cached_lakes_scotland.gpkg
│   └── segments.csv / points.csv
│
├── output/               # Generated output files
│   ├── whw.pdf           # Final vector map (high-resolution)
│   └── map_preview.png   # PNG preview image
│
├── extract.py            # KML extraction logic
├── generate_map.py       # Main map generation script
└── README.md             # This file
```

## ▶️ How to Run

1. Place your input KML and DEM files in the `res/` folder.
2. Run the main script:

```bash
python generate_map.py
```

3. The final map will be saved to `output/whw.pdf`.

## 🖼️ Exporting a Preview Image

You can extract a PNG from the PDF to use as preview:

```bash
from pdf2image import convert_from_path

images = convert_from_path("output/whw.pdf", dpi=200)
images[0].save("output/map_preview.png", "PNG")
```

> Requires: `pip install pdf2image poppler-utils`

## 📌 Notes

- Works best with clean KML route data and high-resolution DEM.