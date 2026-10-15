# coding: utf-8

"""
Custom 2D plot functions.
"""

from __future__ import annotations

__all__ = []

from collections import OrderedDict

import law
import order as od

from columnflow.util import maybe_import
from columnflow.hist_util import sum_hists
from columnflow.plotting.plot_util import (
    remove_residual_axis,
    apply_variable_settings,
    apply_process_settings,
    get_position,
    reduce_with,
)
from columnflow.types import TYPE_CHECKING

np = maybe_import("numpy")
if TYPE_CHECKING:
    plt = maybe_import("matplotlib.pyplot")


def _bin_range_labels(edges) -> list[str]:
    """
    Build per-bin range labels (e.g. ``"500-750"``) from an array of *edges*, except for the
    last bin, which is labeled as open-ended (e.g. ``"1500+"``) to match the convention of
    treating the final bin as an overflow-style catch-all.
    """
    n = len(edges) - 1
    labels = []
    for i in range(n):
        lo, hi = edges[i], edges[i + 1]
        if i == n - 1:
            labels.append(f"{lo:g}+")
        else:
            labels.append(f"{lo:g}-{hi:g}")
    return labels


def plot_2d_migration(
    hists: OrderedDict,
    config_inst: od.Config,
    category_inst: od.Category,
    variable_insts: list[od.Variable],
    shift_insts: list[od.Shift],
    style_config: dict | None = None,
    zlim: tuple | None = None,
    extremes: str | None = "",
    extreme_colors: tuple[str] | None = None,
    colormap: str | None = "",
    skip_legend: bool = False,
    cms_label: str = "wip",
    process_settings: dict | None = None,
    variable_settings: dict | None = None,
    **kwargs,
) -> plt.Figure:
    """
    Plot a migration matrix: for the 2D histogram of ``variable_insts[0]`` (x axis, e.g. a
    reconstructed quantity) vs. ``variable_insts[1]`` (y axis, e.g. the corresponding generator-level
    quantity), each bin's z-axis value is replaced by its share of its *row's* total, where "row"
    means "fixed y-axis bin" -- i.e. the bin value becomes

        value(x, y) = N(x, y) / sum_x' N(x', y)

    the fraction of events with a given y (e.g. gen-level) value that end up in each x (e.g.
    reco-level) bin, matching the standard "P(reco|gen)" migration-matrix convention. A y-bin with
    no entries at all (zero row sum) is left undefined (masked, rendered as background) rather than
    shown as 0, since 0/0 is not a meaningful fraction.

    Bins are drawn with equal width regardless of their underlying numeric range (labeled instead
    with their range, e.g. "500-750", and "1500+" for the open-ended last bin), since this function
    is intended for a small number of coarse, often very unevenly-sized bins (e.g. a 5-bin migration
    matrix), where drawing bins at their true relative width would make most cells illegibly thin.
    Rendered by hand via `ax.imshow` rather than `hist.Hist.plot2d`/mplhep's `hist2dplot`, since the
    latter always draws bins at their true numeric width.

    Adapted from `columnflow.plotting.plot_functions_2d.plot_2d`, dropping the options that don't
    make sense once bins have been row-normalized and equal-width-rendered (`density`, `shape_norm`,
    `zscale`, log axes), and adding per-bin percentage text labels reproducing the annotated-heatmap
    style commonly used for migration matrices (see e.g. Fig. 2 of arXiv:2409.11067). Intended to be
    used with ``cf.PlotVariables2D --plot-function mtt.plotting.plot_functions_2d.plot_2d_migration``.
    """
    import matplotlib as mpl
    import matplotlib.pyplot as plt
    import mplhep

    # remove shift axis from histograms
    hists = remove_residual_axis(hists, "shift")

    hists, process_style_config = apply_process_settings(hists, process_settings)
    hists, variable_style_config = apply_variable_settings(hists, variable_insts, variable_settings)

    # use CMS plotting style
    plt.style.use(mplhep.style.CMS)
    fig, ax = plt.subplots()

    # how to handle bin values outside plot range
    if not extremes:
        extremes = "color"

    # add all processes into 1 histogram
    h_sum = sum_hists(hists.values())

    # row-normalize: for each fixed y-axis (e.g. gen) bin, divide by the sum over the x-axis
    # (e.g. reco) bins in that same row, turning raw counts into a "fraction of this y-bin" value
    values = h_sum.values()
    row_sums = values.sum(axis=0, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        normalized = np.where(row_sums > 0, values / row_sums, np.nan)
    nx, ny = normalized.shape

    # `zlim` is a task-level CSVParameter that always arrives as a 2-tuple, never None -- its
    # own default is the literal ("min", "max"), the same specifier strings used to request
    # data-driven bounds explicitly. Since a data-driven default doesn't make sense here (bin
    # values are already bounded fractions), substitute our own default of the natural [0, 1]
    # range for exactly that un-overridden case; any other value (including a user-supplied
    # "min"/"max"/"maxabs"/"minabs", possibly negative-prefixed) is resolved as normal against
    # the now-normalized bin values.
    if tuple(zlim) == ("min", "max"):
        zlim = (0.0, 1.0)
    else:
        zlim = tuple(reduce_with(lim, normalized) for lim in zlim)

    # value range for deciding which ends of the colorbar need "extend" markers, computed before
    # any hide/clip adjustment below
    vmin, vmax = np.nanmin(normalized), np.nanmax(normalized)

    # a separate, possibly hidden/clipped copy used only for the color mapping; `normalized`
    # itself is kept untouched so the printed percentage labels always show the true value
    display_values = normalized.copy()
    if extremes == "hide":
        display_values = np.where(display_values < zlim[0], np.nan, display_values)
        display_values = np.where(display_values > zlim[1], np.nan, display_values)
    elif extremes == "clip":
        display_values = np.clip(display_values, zlim[0], zlim[1])

    # linear color scale
    cbar_norm = mpl.colors.Normalize(vmin=zlim[0], vmax=zlim[1])

    # obtain colormap
    cmap = plt.get_cmap(colormap or "viridis")

    # use dark and light gray to mark extreme values
    if extremes == "color":
        if not extreme_colors:
            extreme_colors = ["#444444", "#bbbbbb"]
            if sum(cmap(0.0)[:3]) > sum(cmap(1.0)[:3]):
                extreme_colors = extreme_colors[::-1]
        cmap = cmap.with_extremes(under=extreme_colors[0], over=extreme_colors[1])

    # build per-bin percentage text labels (blank for masked/undefined bins), matching the
    # annotated-heatmap convention of showing e.g. "78.5%" or "<0.1%" for very small nonzero values
    def format_label(value: float) -> str:
        if np.isnan(value):
            return ""
        if value == 0:
            return "0%"
        if value < 0.001:
            return "<0.1%"
        return f"{100 * value:.1f}%"

    labels = np.vectorize(format_label)(normalized)

    # unit format on axes (could be configurable)
    unit_format = "{title} [{unit}]"

    default_style_config = {
        "ax_cfg": {
            "xlabel": variable_insts[0].get_full_x_title(unit_format=unit_format),
            "ylabel": variable_insts[1].get_full_x_title(unit_format=unit_format),
        },
        "legend_cfg": {
            "title": "Process" if len(hists.keys()) == 1 else "Processes",
            "handles": [mpl.lines.Line2D([0], [0], lw=0) for proc_inst in hists.keys()],  # dummy handle
            "labels": [proc_inst.label for proc_inst in hists.keys()],
            "ncol": 1,
            "loc": "upper right",
        },
        "cms_label_cfg": {
            "lumi": round(0.001 * config_inst.x.luminosity.get("nominal"), 1),  # /pb -> /fb
            "com": config_inst.campaign.ecm,
        },
        "annotate_cfg": {
            "text": category_inst.label,
        },
    }
    style_config = law.util.merge_dicts(
        default_style_config,
        process_style_config,
        variable_style_config[variable_insts[0]],
        variable_style_config[variable_insts[1]],
        style_config,
        deep=True,
    )

    # draw the matrix as equal-width cells (indexed 0..nx-1 / 0..ny-1), independent of each bin's
    # true numeric width, with tick labels showing each bin's actual range
    im = ax.imshow(
        display_values.T,
        origin="lower",
        cmap=cmap,
        norm=cbar_norm,
        aspect="auto",
        interpolation="none",
    )

    x_labels = _bin_range_labels(h_sum.axes[0].edges)
    y_labels = _bin_range_labels(h_sum.axes[1].edges)
    ax.set_xticks(np.arange(nx))
    ax.set_xticklabels(x_labels)
    ax.set_yticks(np.arange(ny))
    ax.set_yticklabels(y_labels)
    ax.set_xlim(-0.5, nx - 0.5)
    ax.set_ylim(-0.5, ny - 0.5)
    ax.minorticks_off()

    # per-bin percentage text, colored for contrast against the cell's actual rendered color
    for xi in range(nx):
        for yi in range(ny):
            disp_val = display_values[xi, yi]
            if np.isnan(disp_val):
                continue
            rgba = cmap(cbar_norm(disp_val))
            luminance = 0.299 * rgba[0] + 0.587 * rgba[1] + 0.114 * rgba[2]
            text_color = "white" if luminance < 0.5 else "black"
            ax.text(xi, yi, labels[xi, yi], ha="center", va="center", color=text_color, fontsize=14)

    # apply style_config
    ax.set(**style_config["ax_cfg"])
    if not skip_legend:
        ax.legend(**style_config["legend_cfg"])

    # annotation of category label
    annotate_kwargs = {
        "text": "",
        "xy": (
            get_position(*ax.get_xlim(), factor=0.05, logscale=False),
            get_position(*ax.get_ylim(), factor=0.95, logscale=False),
        ),
        "xycoords": "data",
        "color": "black",
        "fontsize": 22,
        "horizontalalignment": "left",
        "verticalalignment": "top",
    }
    annotate_kwargs.update(default_style_config.get("annotate_cfg", {}))
    plt.annotate(**annotate_kwargs)

    # cms label
    if cms_label != "skip":
        label_options = {
            "wip": "Work in progress",
            "pre": "Preliminary",
            "pw": "Private work",
            "sim": "Simulation",
            "simwip": "Simulation work in progress",
            "simpre": "Simulation preliminary",
            "simpw": "Simulation private work",
            "od": "OpenData",
            "odwip": "OpenData work in progress",
            "odpw": "OpenData private work",
            "public": "",
        }
        cms_label_kwargs = {
            "ax": ax,
            "llabel": label_options.get(cms_label, cms_label),
            "fontsize": 22,
            "data": False,
        }
        cms_label_kwargs.update(style_config.get("cms_label_cfg", {}))
        mplhep.cms.label(**cms_label_kwargs)

    # decide at which ends of the colorbar to draw symbols indicating values outside the range;
    # since bins are fractions in [0, 1] and zlim defaults to exactly that range, this is
    # normally "neither", but stays meaningful if a custom zlim is passed
    if extremes == "hide":
        extend = "neither"
    elif vmax > zlim[1] and vmin < zlim[0]:
        extend = "both"
    elif vmin < zlim[0]:
        extend = "min"
    elif vmax > zlim[1]:
        extend = "max"
    else:
        extend = "neither"

    fig.colorbar(im, ax=ax, extend=extend)

    plt.tight_layout()

    return fig, (ax,)
