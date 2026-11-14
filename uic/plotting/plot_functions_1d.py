# coding: utf-8

"""
Custom one-dimensional plot functions.
"""

from __future__ import annotations

__all__ = []

from collections import OrderedDict

from columnflow.util import maybe_import
from columnflow.hist_util import sum_hists
from columnflow.plotting.plot_util import remove_residual_axis

np = maybe_import("numpy")
hist = maybe_import("hist")
plt = maybe_import("matplotlib.pyplot")
mplhep = maybe_import("mplhep")


# same names as the --cms-label choices of the plot tasks
_CMS_LABELS = {
    "wip": "Work in progress",
    "pre": "Preliminary",
    "pw": "Private Work",
    "sim": "Simulation",
    "simwip": "Simulation work in progress",
    "simpre": "Simulation preliminary",
    "simpw": "Simulation private work",
    "public": "",
}


def _stats_lines(h) -> list[tuple[str, str]]:
    """
    ROOT-like statistics box entries for the 1D weighted histogram `h`.

    Mean and std dev are computed from the in-range bins (bin centers weighted by bin contents),
    as ROOT does for the stat box by default. columnflow histograms only store the sum of weights
    and the sum of squared weights per bin, not the number of fills, so the raw "Entries" of ROOT
    is not available; the effective number of entries (sum w)^2 / sum w^2 is shown instead.
    """
    view = h.view(flow=True)
    values = view["value"] if view.dtype.names else view
    variances = view["variance"] if view.dtype.names else view

    in_range = values[1:-1]
    centers = h.axes[0].centers
    sum_w = in_range.sum()
    mean = (centers * in_range).sum() / sum_w
    std = np.sqrt(max((((centers - mean) ** 2) * in_range).sum() / sum_w, 0.0))

    sum_w_all = values.sum()
    sum_w2_all = variances.sum()
    n_eff = sum_w_all ** 2 / sum_w2_all if sum_w2_all > 0 else 0.0

    return [
        ("Eff. entries", f"{n_eff:.4g}"),
        ("Mean", f"{mean:.4g}"),
        ("Std dev", f"{std:.4g}"),
        ("Underflow", f"{values[0]:.3g}"),
        ("Overflow", f"{values[-1]:.3g}"),
    ]


def _draw_stats_box(ax, lines: list[tuple[str, str]], x0=0.64, x1=0.97, y1=0.97, dy=0.05, fontsize=15) -> None:
    """
    Draw `lines` as a two-column (name left, value right) box in the upper right of `ax`.
    """
    for i, (name, value) in enumerate(lines):
        y = y1 - (i + 0.8) * dy
        ax.text(x0 + 0.015, y, name, transform=ax.transAxes, ha="left", va="center", fontsize=fontsize)
        ax.text(x1 - 0.015, y, value, transform=ax.transAxes, ha="right", va="center", fontsize=fontsize)

    height = (len(lines) + 0.6) * dy
    ax.add_patch(plt.Rectangle(
        (x0, y1 - height), x1 - x0, height,
        transform=ax.transAxes, fill=False, edgecolor="black", linewidth=1.0, zorder=10,
    ))


def plot_root_style(
    hists: OrderedDict,
    config_inst,
    category_inst,
    variable_insts,
    shift_insts,
    cms_label: str | None = None,
    info_text: str | None = None,
    process_text: str | None = None,
    color: str = "red",
    stats: bool = True,
    ymax_scale: float = 1.6,
    **kwargs,
):
    """
    ROOT-like 1D plot: a single unfilled step histogram (all requested MC processes summed), a
    statistics box (effective entries, mean, std dev, underflow, overflow), and two lines of
    annotation text. Meant for gen-level distributions such as m(lb).

    Options can be passed through ``--general-settings``, e.g.

    .. code-block:: bash

        --general-settings "info_text=Generator level (Powheg-Pythia8),process_text=TTToSemiLeptonic"

    - `info_text`: first annotation line (default: category label)
    - `process_text`: second, smaller annotation line (default: process labels)
    - `color`: line color (default: red)
    - `stats`: draw the statistics box (default: True)
    - `ymax_scale`: upper y limit as a multiple of the highest bin (default: 1.6)
    """
    variable_inst = variable_insts[0]

    # nominal shift only
    if len(shift_insts) == 1:
        hists = remove_residual_axis(hists, "shift")
    else:
        hists = remove_residual_axis(hists, "shift", select_value="nominal")

    # sum all MC processes into one histogram
    mc_hists = {proc_inst: h for proc_inst, h in hists.items() if not proc_inst.is_data}
    if not mc_hists:
        raise ValueError("plot_root_style needs at least one MC process")
    h = sum_hists(list(mc_hists.values()))

    plt.style.use(mplhep.style.CMS)
    fig, ax = plt.subplots()

    mplhep.histplot(h, ax=ax, histtype="step", color=color, linewidth=1.5, flow="none", yerr=False)

    # axis labels: x as "title (unit)", y as "Events / <bin width> <unit>" for uniform binning
    unit = variable_inst.unit or ""
    widths = h.axes[0].widths
    ylabel = "Events"
    if np.allclose(widths, widths[0]):
        ylabel = f"Events / {widths[0]:g} {unit}".rstrip()
    ax.set_xlabel(variable_inst.get_full_x_title(unit_format="{title} ({unit})"), ha="right", x=1.0)
    # stop short of the top so the label does not run into the "x10^n" multiplier
    ax.set_ylabel(ylabel, ha="right", y=0.92)

    ax.set_xlim(h.axes[0].edges[0], h.axes[0].edges[-1])
    ax.set_ylim(0, ymax_scale * max(h.values().max(), 0) or 1)
    ax.ticklabel_format(axis="y", style="sci", scilimits=(-3, 3), useMathText=True)
    # put the "x10^n" multiplier above the tick labels, left of the CMS label (as in ROOT)
    offset_text = ax.yaxis.get_offset_text()
    offset_text.set_x(-0.01)
    offset_text.set_horizontalalignment("right")

    # annotation text
    if info_text is None:
        info_text = category_inst.label or ""
    if process_text is None:
        process_text = ", ".join(proc_inst.label for proc_inst in mc_hists)
    ax.text(0.04, 0.93, info_text, transform=ax.transAxes, ha="left", va="center", fontsize=16)
    ax.text(0.04, 0.87, process_text, transform=ax.transAxes, ha="left", va="center", fontsize=13)

    if stats:
        _draw_stats_box(ax, _stats_lines(h))

    # CMS label left, centre-of-mass energy right (no lumi: meant for gen-level shapes)
    if cms_label != "skip":
        mplhep.cms.label(
            ax=ax,
            llabel=_CMS_LABELS.get(cms_label or "pw", cms_label),
            data=True,
            rlabel=f"({config_inst.campaign.ecm:g} TeV)",
            fontsize=20,
        )

    fig.tight_layout()

    return fig, (ax,)
