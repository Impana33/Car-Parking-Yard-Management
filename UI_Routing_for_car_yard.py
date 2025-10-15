import tkinter as tk
from tkinter import ttk
import geopandas as gpd

def run_pathfinding():
    source = source_var.get()
    target = target_var.get()
    if not source or not target:
        status_label.config(text="❌ Please select both source and target slots.")
        return

    # Call your routing function here
    try:
        shortest_path(source, target)
        status_label.config(text=f"✅ Path found: {source} → {target}")
    except Exception as e:
        status_label.config(text=f"❌ Error: {str(e)}")

def shortest_path(source_slot_id, target_slot_id):
    from shapely.geometry import Point, LineString
    import networkx as nx
    from rtree import index
    import pandas as pd
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.lines import Line2D

    # Paths
    slot_path = r"C:\Users\impug\OneDrive\Documents\Car_paring_yard_management\SLOT_shp-20250716T085303Z-1-001\SLOT_shp\Parking_yard_dta\Slot.shp"
    road_path = r"D:\Impana\Car_paring_yard_management\edited_road\Roads_1.shp"

    slots = gpd.read_file(slot_path)
    roads = gpd.read_file(road_path)

    source_geom = slots.loc[slots['slot_id'] == source_slot_id, 'geometry'].values[0].centroid
    target_geom = slots.loc[slots['slot_id'] == target_slot_id, 'geometry'].values[0].centroid

    edges = []
    node_idx = index.Index()
    node_id_counter = 0
    node_lookup = {}

    def add_node(point, node_lookup):
        nonlocal node_id_counter
        key = (point.x, point.y)
        if key not in node_lookup:
            node_lookup[key] = node_id_counter
            node_idx.insert(node_id_counter, (point.x, point.y, point.x, point.y))
            node_id_counter += 1
        return node_lookup[key]

    for _, row in roads.iterrows():
        coords = list(row.geometry.coords)
        for i in range(len(coords) - 1):
            pt1 = Point(coords[i])
            pt2 = Point(coords[i + 1])
            n1 = add_node(pt1, node_lookup)
            n2 = add_node(pt2, node_lookup)
            distance = pt1.distance(pt2)
            edges.append((n1, n2, distance))

    G = nx.Graph()
    G.add_weighted_edges_from(edges)

    def get_nearest_node(pt: Point):
        nearest = list(node_idx.nearest((pt.x, pt.y, pt.x, pt.y), 1))
        return nearest[0]

    src_node = get_nearest_node(source_geom)
    dst_node = get_nearest_node(target_geom)
    node_reverse_lookup = {v: k for k, v in node_lookup.items()}
    src_point = Point(node_reverse_lookup[src_node])
    dst_point = Point(node_reverse_lookup[dst_node])

    snap_links = [
        LineString([source_geom, src_point]),
        LineString([target_geom, dst_point])
    ]
    snap_links_gdf = gpd.GeoDataFrame(pd.DataFrame({'type': ['source_link', 'target_link']}), geometry=snap_links, crs=roads.crs)
    snap_links_gdf.to_file("snapped_links.shp")

    snap_pts_gdf = gpd.GeoDataFrame(pd.DataFrame({'type': ['source', 'target']}), geometry=[src_point, dst_point], crs=roads.crs)
    snap_pts_gdf.to_file("nearest_points.shp")

    if not nx.has_path(G, src_node, dst_node):
        raise ValueError("No path found")

    path = nx.shortest_path(G, src_node, dst_node, weight='weight')
    path_coords = [node_reverse_lookup[n] for n in path]
    path_line = LineString(path_coords)
    path_gdf = gpd.GeoDataFrame(pd.DataFrame({'id': [1]}), geometry=[path_line], crs=roads.crs)
    path_gdf.to_file("shortest_path.shp")

    # Plot
    fig, ax = plt.subplots(figsize=(10, 10))
    roads.plot(ax=ax, color='gray', linewidth=0.5)
    slots.plot(ax=ax, color='lightblue', edgecolor='black', linewidth=0.3)
    path_gdf.plot(ax=ax, color='red', linewidth=2)
    snap_links_gdf.plot(ax=ax, color='orange', linewidth=1.5, linestyle='--')
    snap_pts_gdf[snap_pts_gdf['type'] == 'source'].plot(ax=ax, color='green', markersize=50)
    snap_pts_gdf[snap_pts_gdf['type'] == 'target'].plot(ax=ax, color='yellow', markersize=50)

    legend_elements = [
        mpatches.Patch(color='gray', label='Roads'),
        mpatches.Patch(color='lightblue', label='Slots'),
        Line2D([0], [0], color='red', lw=2, label='Shortest Path'),
        Line2D([0], [0], color='orange', lw=2, linestyle='--', label='Snap Links'),
        Line2D([0], [0], marker='o', color='w', label='Source', markerfacecolor='green', markersize=10),
        Line2D([0], [0], marker='o', color='w', label='Target', markerfacecolor='yellow', markersize=10),
    ]
    ax.legend(handles=legend_elements, loc='upper right')
    ax.set_title(f"Shortest Path: {source_slot_id} → {target_slot_id}")
    plt.tight_layout()
    plt.show()

# -----------------------------
# Tkinter UI Setup
# -----------------------------
slot_shp = r"C:\Users\impug\OneDrive\Documents\Car_paring_yard_management\SLOT_shp-20250716T085303Z-1-001\SLOT_shp\Parking_yard_dta\Slot.shp"
slot_gdf = gpd.read_file(slot_shp)
slot_ids = sorted(slot_gdf["slot_id"].dropna().unique().tolist())

root = tk.Tk()
root.title("Shortest Path Finder")

tk.Label(root, text="Select Source Slot:").grid(row=0, column=0, padx=10, pady=10)
source_var = tk.StringVar()
source_menu = ttk.Combobox(root, textvariable=source_var, values=slot_ids, state="readonly", width=15)
source_menu.grid(row=0, column=1)

tk.Label(root, text="Select Target Slot:").grid(row=1, column=0, padx=10, pady=10)
target_var = tk.StringVar()
target_menu = ttk.Combobox(root, textvariable=target_var, values=slot_ids, state="readonly", width=15)
target_menu.grid(row=1, column=1)

ttk.Button(root, text="Find Shortest Path", command=run_pathfinding).grid(row=2, columnspan=2, pady=10)
status_label = tk.Label(root, text="", fg="blue")
status_label.grid(row=3, columnspan=2)

root.mainloop()
