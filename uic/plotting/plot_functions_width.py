# coding: utf-8

"""
Plot functions for the top-quark width template method (ATLAS, EPJC 78 (2018) 129).

One tt MC sample, generated with a top mass m_t and width Gamma_0, is reweighted to a hypothesis Gamma
with the ratio of Breit-Wigner densities of the gen top and antitop masses,

    w(Gamma) = BW(m_t; Gamma) BW(m_tbar; Gamma) / (BW(m_t; Gamma_0) BW(m_tbar; Gamma_0)).

Since w depends only on the two gen masses, the templates are built from a histogram that has the two gen
masses as axes next to the reco observable, in the same way as the A_C templates of
`uic.plotting.plot_functions_asymmetry` are built from a (gen X, reco X) histogram: every gen bin is
scaled by its weight, then the gen axes are summed over. The input is a 3D histogram, e.g.

    --variables gen_mt-gen_mtbar-mlb_btagged     or     gen_mt-gen_mtbar-dr_min_bl_btagged

The two gen axes are identified by their names starting with ``gen_``, the remaining axis is the reco observable.

Weights are the expected value of the density ratio over a gen bin, not its value at the bin centre
(so the templates stay right for small widths, where the Breit-Wigner is narrower than a gen bin). Events with a
gen mass outside the axis range, or with no gen top found (EMPTY_FLOAT), sit in the flow bins and keep weight 1; the
fraction of the signal yield there is quoted in the legend, since for large widths the Breit-Wigner tails matter.
The yield is not renormalised: the signal normalisation floats in the fit, the shape change is what is checked.
"""

from __future__ import annotations

__all__ = []

from collections import OrderedDict

import law

from columnflow.util import maybe_import
from columnflow.plotting.plot_util import remove_residual_axis, prepare_style_config

from uic.plotting.plot_functions_asymmetry import _values_variances, _with_contents, _split_hists

np = maybe_import("numpy")

# sub-points per gen bin used to average the Breit-Wigner densities
N_SUB = 16


#
# pure helpers
#

def _bw_density(m, mass, width, relativistic: bool = True):
    """
    Normalised Breit-Wigner density of the top mass `m` (all in GeV), for pole mass `mass` and width `width`.
    The relativistic form is a function of m^2 and is converted to a density in m.
    """
    m = np.asarray(m, dtype=float)
    if relativistic:
        return 2.0 * m * (mass * width / np.pi) / ((m ** 2 - mass ** 2) ** 2 + (mass * width) ** 2)
    return (width / (2.0 * np.pi)) / ((m - mass) ** 2 + 0.25 * width ** 2)


def _bin_weights(axis, mass: float, width: float, width_0: float, relativistic: bool = True):
    """
    Per-bin weights (length `len(axis)`, no flow bins) of one gen mass axis: the expected ratio
    BW(m; width) / BW(m; width_0) over a bin, for masses distributed as BW(m; width_0), i.e. the ratio of the bin
    integrals of the two densities (evaluated with `N_SUB` sub-points per bin).
    """
    edges = axis.edges
    lo, hi = edges[:-1], edges[1:]
    frac = (np.arange(N_SUB) + 0.5) / N_SUB
    m = lo[:, None] + (hi - lo)[:, None] * frac[None, :]  # (n_bins, N_SUB)
    num = _bw_density(m, mass, width, relativistic).sum(axis=1)
    den = _bw_density(m, mass, width_0, relativistic).sum(axis=1)
    return num / den


def _axes_by_level(h) -> tuple[int, int, int]:
    """
    Return `(gen_1, gen_2, reco)` axis indices of a 3D histogram. The gen axes are those with a name starting with
    ``gen_`` (in the order given), the reco axis is the remaining one.
    """
    names = list(h.axes.name)
    gen = [i for i, name in enumerate(names) if name.startswith("gen_")]
    if len(names) != 3 or len(gen) != 2:
        raise ValueError(
            "expected a 3D histogram with exactly two gen axes (names starting with 'gen_') and one reco axis, "
            f"e.g. --variables gen_mt-gen_mtbar-mlb_btagged; got axes {names}",
        )
    reco = next(i for i in range(3) if i not in gen)
    return gen[0], gen[1], reco


def _flow_fraction(h) -> float:
    """
    Fraction of the yield of the 3D histogram `h` that lies in a flow bin of either gen axis.
    """
    values = h.values(flow=True)
    total = values.sum()
    slicer = [slice(None)] * 3
    for g in _axes_by_level(h)[:2]:
        traits = h.axes[g].traits
        slicer[g] = slice(int(traits.underflow), values.shape[g] - int(traits.overflow))
    return float(1.0 - values[tuple(slicer)].sum() / total) if total else 0.0


def _build_width_templates(h, gammas, mass: float, width_0: float, relativistic: bool = True) -> dict:
    """
    Build `{gamma: template}` reco histograms: every gen-mass bin pair of the 3D histogram `h` is scaled by
    w_i(gamma) w_j(gamma) (flow bins by 1), then the gen axes are summed over, flow included. Variances scale with w^2.
    """
    g1, g2, reco = _axes_by_level(h)
    values, variances = _values_variances(h, flow=True)
    values = np.moveaxis(values, (g1, g2, reco), (0, 1, 2))
    variances = np.moveaxis(variances, (g1, g2, reco), (0, 1, 2))
    h_reco = h.project(reco)

    def full_weights(axis, gamma):
        w = _bin_weights(axis, mass, gamma, width_0, relativistic)
        traits = axis.traits
        return np.concatenate([[1.0] * traits.underflow, w, [1.0] * traits.overflow])

    templates = {}
    for gamma in gammas:
        w1 = full_weights(h.axes[g1], gamma)
        w2 = full_weights(h.axes[g2], gamma)
        w = w1[:, None] * w2[None, :]
        t_values = np.einsum("ij,ijk->k", w, values)
        t_variances = np.einsum("ij,ijk->k", w ** 2, variances)
        templates[gamma] = _with_contents(h_reco, t_values, t_variances, flow=True)
    return templates


def _parse_gammas(gammas, width_0: float) -> tuple[float, ...]:
    gammas = tuple(float(g) for g in law.util.make_tuple(gammas))
    # the nominal width is always needed as the ratio reference
    if not any(np.isclose(g, width_0) for g in gammas):
        gammas = gammas + (width_0,)
    return tuple(sorted(gammas))


#
# plot functions
#

def plot_width_templates(
    hists,
    config_inst,
    category_inst,
    variable_insts,
    shift_insts,
    style_config: dict | None = None,
    gammas: tuple | float = (0.7, 1.0, 2.0, 3.0),
    signal_process: str | tuple = "tt_sl",
    relativistic: bool | str = True,
    yscale: str | None = None,
    **kwargs,
) -> tuple:
    """
    Overlay the reco templates of the width hypotheses `gammas` (GeV), with a ratio panel to the nominal width
    of the sample (`ttbar_reco_settings.gen_top_width`, which is always included). Only the `signal_process`
    contribution is reweighted, all other MC processes enter with their nominal shape. The top mass and nominal
    width are read from `ttbar_reco_settings.{gen_top_mass,gen_top_width}`.

    Widths are set via `--general-settings "gammas=0.7;1.0;2.0;3.0"`, the Breit-Wigner form with
    `--general-settings "relativistic=False"`.

    Exemplary task call:

    .. code-block:: bash

        law run cf.PlotVariables2D --version v1 --processes tt_sl --categories incl \\
            --variables gen_mt-gen_mtbar-mlb_btagged \\
            --plot-function uic.plotting.plot_functions_width.plot_width_templates
    """
    import matplotlib.pyplot as plt
    from columnflow.plotting.plot_all import plot_all

    settings = config_inst.x.ttbar_reco_settings
    mass, width_0 = float(settings.gen_top_mass), float(settings.gen_top_width)
    if isinstance(relativistic, str):
        relativistic = relativistic.lower() not in ("false", "0", "no")
    gammas = _parse_gammas(gammas, width_0)

    hists = remove_residual_axis(hists, "shift")
    h_data, h_signal, h_background = _split_hists(hists, config_inst, signal_process)
    if h_signal is None:
        raise ValueError(
            f"no histograms for signal process(es) {signal_process!r} among the plotted processes "
            f"{[p.name for p in hists]}; pass e.g. --general-settings signal_process=<name>",
        )

    templates = _build_width_templates(h_signal, gammas, mass, width_0, relativistic)
    if h_background is not None:
        h_bkg_reco = h_background.project(_axes_by_level(h_background)[2])
        templates = {g: h + h_bkg_reco for g, h in templates.items()}
    nominal = next(g for g in gammas if np.isclose(g, width_0))
    nominal_values = templates[nominal].values()
    reco_var = next(v for v in variable_insts if not v.name.startswith("gen_"))

    colors = plt.get_cmap("plasma")(np.linspace(0.0, 0.9, len(gammas)))
    plot_config = OrderedDict()
    for gamma, color in zip(gammas, colors):
        is_nominal = gamma == nominal
        line_style = {"color": "black" if is_nominal else color, "linestyle": "-" if is_nominal else (0, (1, 1))} # linestyle = (0, (1, 1)) means densely dotted
        plot_config[f"template_g{gamma:g}"] = {
            "method": "draw_hist",
            "hist": templates[gamma],
            "kwargs": {
                "label": rf"$\Gamma_t = {gamma:g}$ GeV" + (" (nominal)" if is_nominal else ""),
                "yerr": None,
                **line_style,
            },
            "ratio_kwargs": {"norm": nominal_values, "yerr": None, **line_style},
        }

    if h_data is not None:
        plot_config["data"] = {
            "method": "draw_errorbars",
            "hist": h_data.project(_axes_by_level(h_data)[2]),
            "kwargs": {"label": "Data"},
            "ratio_kwargs": {"norm": nominal_values},
        }

    default_style_config = prepare_style_config(config_inst, category_inst, reco_var, yscale=yscale)
    default_style_config["ax_cfg"]["ylabel"] = "Events / bin"
    default_style_config["rax_cfg"]["ylabel"] = r"$\Gamma_t\ /\ \Gamma_t^{nom}$"
    default_style_config["legend_cfg"]["ncols"] = 1
    # two short lines: a long single line widens the legend and runs over the category label at the top left
    default_style_config["legend_cfg"]["title"] = (
        rf"$m_t = {mass:g}$ GeV" + "\n" + rf"outside gen-mass axes: {100 * _flow_fraction(h_signal):.1f}%"
    )
    default_style_config["legend_cfg"]["title_fontsize"] = "small"
    style_config = law.util.merge_dicts(default_style_config, style_config or {}, deep=True)

    return plot_all(plot_config, style_config, **kwargs)
