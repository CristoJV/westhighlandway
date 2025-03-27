import xml.etree.ElementTree as ET
import pandas as pd


def extract_kml_segments(
    file_path: str,
    output_dir: str = "res",
    segment_slice: tuple = (3, 11),
    save_csv: bool = True,
):
    """
    Extracts segments and points from a KML file and saves them as CSV files.

    Parameters:
        file_path (str): Path to the input KML file.
        output_dir (str): Directory to save the output CSV files.
        segment_slice (tuple): Range to slice the segments DataFrame (start, end).
        save_csv (bool): Whether to save output files or just return them.

    Returns:
        tuple: (segments_df, points_df)
    """
    # Parse the KML
    tree = ET.parse(file_path)
    root = tree.getroot()
    namespace = {"kml": "http://www.opengis.net/kml/2.2"}

    # Extract all Placemark elements
    segments = []
    for placemark in root.findall(".//kml:Placemark", namespace):
        name = (
            placemark.find("kml:name", namespace).text
            if placemark.find("kml:name", namespace) is not None
            else "Unnamed"
        )
        coordinates = placemark.find(
            ".//kml:coordinates", namespace
        ).text.strip()

        coords_list = [
            tuple(map(float, coord.strip().split(",")))
            for coord in coordinates.split()
        ]

        segments.append({"Name": name, "Coordinates": coords_list})

    # Create DataFrame
    segments_df = pd.DataFrame(segments)

    # Split points and segments
    points_df = segments_df[
        segments_df["Coordinates"].apply(lambda x: len(x) == 1)
    ]
    segments_df = segments_df[
        segments_df["Coordinates"].apply(lambda x: len(x) > 1)
    ]

    # Slice desired segments
    segments_df = segments_df.iloc[segment_slice[0] : segment_slice[1]]

    if save_csv:
        points_df.to_csv(f"{output_dir}/points.csv", index=False)
        segments_df.to_csv(f"{output_dir}/segments.csv", index=False)
        print(f"✅ Saved points to '{output_dir}/points.csv'")
        print(f"✅ Saved segments to '{output_dir}/segments.csv'")

    return segments_df, points_df


# Example usage
# segments_df, points_df = extract_kml_segments("res/whw.kml")
