#!/usr/bin/env python3
"""
Plot 2m temperature (t2) over CONUS from a NetCDF file, with CONUS and
state boundaries overlaid.

File structure (from `ncdump -h`):
    dimensions: time(91), member(1), lat(135), lon(272)
    t2(time, member, lat, lon)  -- "2m temperature", units = "K"
    lat: 53.75 .. 20.25 (descending)
    lon: 232 .. ~299.75 (0-360 convention -> subtract 360 for degrees East)

Usage:
    python plot_t2_conus.py                       # first time step, member 0
    python plot_t2_conus.py --time 10 --units F   # 11th step in Fahrenheit
    python plot_t2_conus.py --time 0 --units C --out t2_map.png
"""

import argparse

import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER


def kelvin_to(units, data_k):
    """Convert a Kelvin array to the requested units (K, C, or F)."""
    units = units.upper()
    if units == "K":
        return data_k, "K"
    if units == "C":
        return data_k - 273.15, "°C"
    if units == "F":
        return (data_k - 273.15) * 9.0 / 5.0 + 32.0, "°F"
    raise ValueError(f"Unknown units: {units!r} (use K, C, or F)")


def main():
    p = argparse.ArgumentParser(description="Plot t2 over CONUS.")
    p.add_argument("--file", default="t2_20200627T18_mem49_CONUS.nc",
                   help="Path to the NetCDF file.")
    p.add_argument("--time", type=int, default=0,
                   help="Time index to plot (0-based). Default 0.")
    p.add_argument("--member", type=int, default=0,
                   help="Member index to plot (0-based). Default 0.")
    p.add_argument("--units", default="C", choices=["K", "C", "F", "k", "c", "f"],
                   help="Output temperature units. Default C.")
    p.add_argument("--cmap", default="RdYlBu_r", help="Matplotlib colormap.")
    p.add_argument("--out", default="t2_conus.png",
                   help="Output image filename.")
    p.add_argument("--dpi", type=int, default=150, help="Output DPI.")
    args = p.parse_args()

    # ---- Load data --------------------------------------------------------
    ds = xr.open_dataset(args.file)

    # Select one time step and one ensemble member -> 2D (lat, lon) field.
    t2 = ds["t2"].isel(time=args.time, member=args.member)

    # Use the coordinates exactly as stored in the file -- no shifting or
    # reprojection of the data. Longitudes stay in the 0-360 convention and
    # the cartopy boundary features are aligned to them via the map
    # projection's central longitude (see below).
    lat = ds["lat"].values
    lon = ds["lon"].values

    field, unit_label = kelvin_to(args.units, t2.values)

    # Variable label for the title.
    var_label = f"temperature in {unit_label} at 2m from the ground"

    # Human-readable time for the title.
    try:
        time_str = str(ds["time"].isel(time=args.time).values)
    except Exception:
        time_str = f"index {args.time}"

    # ---- Plot -------------------------------------------------------------
    # The data longitudes are in the 0-360 convention. We DO NOT alter them.
    # Instead the map is drawn with a central longitude of 180 so that
    # cartopy reprojects its built-in boundary features into the same frame
    # as the data; the data themselves are passed through unchanged with a
    # plain PlateCarree() transform (which understands 0-360 values).
    data_crs = ccrs.PlateCarree()
    map_proj = ccrs.PlateCarree(central_longitude=180)

    fig = plt.figure(figsize=(11, 7))
    ax = plt.axes(projection=map_proj)

    # Limit the view to CONUS based on the (unmodified) data extent.
    ax.set_extent([lon.min(), lon.max(), lat.min(), lat.max()], crs=data_crs)

    # Filled temperature field -- coordinates passed exactly as stored.
    mesh = ax.pcolormesh(
        lon, lat, field,
        cmap=args.cmap,
        shading="auto",
        transform=data_crs,
    )

    # ---- Boundaries -------------------------------------------------------
    ax.add_feature(cfeature.STATES.with_scale("50m"),
                   edgecolor="black", linewidth=0.5)
    ax.add_feature(cfeature.BORDERS.with_scale("50m"),
                   edgecolor="black", linewidth=0.8)
    ax.add_feature(cfeature.COASTLINE.with_scale("50m"),
                   edgecolor="black", linewidth=0.8)
    ax.add_feature(cfeature.LAKES.with_scale("50m"),
                   edgecolor="black", facecolor="none", linewidth=0.4)

    # ---- Gridlines / labels ----------------------------------------------
    gl = ax.gridlines(crs=data_crs, draw_labels=True, linewidth=0.3,
                      color="gray", alpha=0.5, linestyle="--")
    gl.top_labels = False
    gl.right_labels = False
    gl.xformatter = LONGITUDE_FORMATTER
    gl.yformatter = LATITUDE_FORMATTER
    gl.xlocator = mticker.MultipleLocator(10)
    gl.ylocator = mticker.MultipleLocator(5)

    # ---- Colorbar + title -------------------------------------------------
    cbar = fig.colorbar(mesh, ax=ax, orientation="vertical",
                        pad=0.02, shrink=0.85)
    cbar.set_label(f"2 m temperature ({unit_label})")

    ax.set_title(
        f"{var_label} over CONUS\n{time_str}  "
        f"(member {args.member})",
        fontsize=18,
    )

    # NOTE: do not use bbox_inches="tight" here -- combined with cartopy
    # gridliner labels and a colorbar it can collapse the GeoAxes.
    fig.savefig(args.out, dpi=args.dpi)
    print(f"Saved figure to {args.out}")
    plt.show()


if __name__ == "__main__":
    main()
