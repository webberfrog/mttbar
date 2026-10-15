# coding: utf-8

"""
Plot functions for the ttbar charge asymmetry A_C in the asymmetry-sensitive observable
X = tanh(Delta|y|) (`TTbar.tanh_y`, see `mtt.production.ttbar_reco_uic`), following the template
method of CMS AN-26-039 (Sec. 7):

  * the X distribution is split into a symmetric and an antisymmetric component,

        rho^+(X) = 1/2 [rho(X) + rho(-X)],    rho^-(X) = 1/2 [rho(X) - rho(-X)],

  * a family of asymmetry hypotheses is built by scaling only the antisymmetric part,

        rho(X; f) = rho^+(X) + (1 - f) rho^-(X),

    such that A_C(f) = (1 - f) A_C^nom (f = 0: nominal, f = 1: no asymmetry, f < 0: enhanced).

Two input modes are supported by all plot functions:

  * 1D reco histogram (e.g. ``--variables tanh_y_18bin``): templates are built directly on the
    reco X distribution, so `f` is a reco-level parameter (no detector dilution).
  * 2D (gen X, reco X) histogram (e.g. ``--variables gen_tanh_y-tanh_y_18bin``): paper-style.
    The weights w(X_gen; f) = (rho_gen^+ + (1 - f) rho_gen^-) / rho_gen (Eq. 24) are computed per
    gen bin and applied to the gen-reco response before projecting onto reco X, which is
    identical to weighting every event by its gen bin. `f` then maps to the gen-level asymmetry,
    A_C^gen(f) = (1 - f) A_C^gen,nom (Eq. 25). The gen axis is identified by its name starting
    with ``gen_``.

    Caveat: AN-26-039 derives rho_gen and A_C^gen,nom from all generated events, before
    selection. Here only selected events enter the histograms, so the gen shape (and the quoted
    A_C^gen,nom) is the post-selection one. The template construction itself is self-consistent.
"""

from __future__ import annotations

__all__ = []

from collections import OrderedDict

import law

from columnflow.util import maybe_import
from columnflow.hist_util import sum_hists
from columnflow.plotting.plot_util import remove_residual_axis, prepare_style_config

np = maybe_import("numpy")


_CMS_LABEL_OPTIONS = {
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


#
# pure histogram helpers
#

def _values_variances(h, flow=False):
    values = h.values(flow=flow)
    variances = h.variances(flow=flow)
    if variances is None:
        # unweighted storage: Poisson assumption
        variances = values.copy()
    return values, variances


def _check_symmetric(axis):
    edges = axis.edges
    if not np.allclose(edges, -edges[::-1]):
        raise ValueError(
            f"axis '{axis.name}' must have binning symmetric around 0 to decompose it into "
            f"symmetric and antisymmetric parts, got edges {edges}",
        )


def _with_contents(h, values, variances, flow=False):
    """
    Return a copy of `h` with its contents (including flow bins if `flow`) replaced.
    """
    h_out = h.copy()
    view = h_out.view(flow=flow)
    if view.dtype.names:
        view["value"][...] = values
        view["variance"][...] = variances
    else:
        view[...] = values
    return h_out


def _gen_reco_axes(h) -> tuple[int, int]:
    """
    Return `(gen_axis_index, reco_axis_index)` of a 2D (gen X, reco X) histogram. The gen axis
    is the one whose name starts with ``gen_``.
    """
    names = list(h.axes.name)
    gen = [i for i, name in enumerate(names) if name.startswith("gen_")]
    if len(names) != 2 or len(gen) != 1:
        raise ValueError(
            f"expected a 2D histogram with exactly one gen axis (name starting with 'gen_'), got "
            f"axes {names}",
        )
    return gen[0], 1 - gen[0]


def _is_gen_reco(h) -> bool:
    return len(h.axes) == 2


def _reco_projection(h):
    """
    Reco-X histogram: `h` itself if 1D, otherwise the projection of the 2D histogram onto its
    reco axis (summing over the gen axis including its flow bins, i.e. including events without
    gen information).
    """
    if not _is_gen_reco(h):
        return h
    return h.project(_gen_reco_axes(h)[1])


def _gen_projection(h):
    """
    Gen-X histogram: `h` itself if 1D (then assumed to be a gen histogram), otherwise the
    projection of the 2D histogram onto its gen axis.
    """
    if not _is_gen_reco(h):
        return h
    return h.project(_gen_reco_axes(h)[0])


def _decompose(h):
    """
    Split the 1D histogram `h` into `(rho, rho_plus, rho_minus)` histograms with
    rho^{+/-}(X) = 1/2 [h(X) +/- h(-X)].

    The variance assigned to rho^{+/-} is 1/4 [var(X) + var(-X)]. It is meant for display only:
    the X and -X bins of rho^{+/-} are built from the same two input bins and are therefore
    fully (anti-)correlated.
    """
    if len(h.axes) != 1:
        raise ValueError(f"expected a 1D histogram, got {len(h.axes)} axes")
    _check_symmetric(h.axes[0])

    values, variances = _values_variances(h)
    mirrored_values = values[::-1]
    mirrored_variances = variances[::-1]
    sym_var = 0.25 * (variances + mirrored_variances)

    rho_plus = _with_contents(h, 0.5 * (values + mirrored_values), sym_var)
    rho_minus = _with_contents(h, 0.5 * (values - mirrored_values), sym_var)
    return h.copy(), rho_plus, rho_minus


def _charge_asymmetry(h) -> tuple[float, float]:
    """
    A_C = (N(X > 0) - N(X < 0)) / (N(X > 0) + N(X < 0)) and its statistical uncertainty, for a
    1D histogram whose axis has a bin edge at 0 (guaranteed by the symmetric-binning check).
    """
    _check_symmetric(h.axes[0])
    values, variances = _values_variances(h)
    centers = h.axes[0].centers
    pos = centers > 0
    neg = centers < 0

    n_pos, n_neg = values[pos].sum(), values[neg].sum()
    var_pos, var_neg = variances[pos].sum(), variances[neg].sum()
    denom = n_pos + n_neg
    if denom <= 0:
        return np.nan, np.nan

    ac = (n_pos - n_neg) / denom
    # A = (a - b) / (a + b) with independent a, b:
    # var(A) = (2 / (a + b)^2)^2 * (b^2 var(a) + a^2 var(b))
    var = (2.0 / denom ** 2) ** 2 * (n_neg ** 2 * var_pos + n_pos ** 2 * var_neg)
    return float(ac), float(np.sqrt(var))


def _gen_weights(h, f: float, flow: bool = True):
    """
    Per-gen-bin weights w_j(f) = (rho^+_j + (1 - f) rho^-_j) / rho_j (AN-26-039, Eq. 24),
    computed from the gen projection of `h` (a 2D gen-reco or a 1D gen histogram). Bins with
    rho_j == 0 get weight 1. If `flow`, the gen under-/overflow bins (events without gen info,
    e.g. EMPTY_FLOAT) are included with weight 1.
    """
    h_gen = _gen_projection(h)
    _, rho_plus, rho_minus = _decompose(h_gen)
    vp, vm = rho_plus.values(), rho_minus.values()
    rho = vp + vm
    with np.errstate(divide="ignore", invalid="ignore"):
        w = np.where(rho != 0, (vp + (1.0 - f) * vm) / rho, 1.0)
    if flow:
        traits = h_gen.axes[0].traits
        w = np.concatenate([[1.0] * traits.underflow, w, [1.0] * traits.overflow])
    return w


def _build_templates(h, f_values) -> dict:
    """
    Build `{f: template}` reco-X histograms of the asymmetry hypotheses rho^+ + (1 - f) rho^-.

    * 1D input (reco X only): the decomposition is applied to the reco histogram itself. The
      total yield is preserved automatically since sum(rho^-) = 0.
    * 2D input (gen X, reco X): every gen bin j of the gen-reco response is scaled by
      w_j(f) (see `_gen_weights`), then projected onto reco X and rescaled to the nominal total
      yield (AN-26-039, Eq. 24 normalization).
    """
    templates = {}

    if len(h.axes) == 1:
        _, rho_plus, rho_minus = _decompose(h)
        vp, vm = rho_plus.values(), rho_minus.values()
        # variance: keep the nominal per-bin variance, rescaled with the template content
        nominal_values, nominal_variances = _values_variances(h)
        for f in f_values:
            values = vp + (1.0 - f) * vm
            with np.errstate(divide="ignore", invalid="ignore"):
                scale = np.where(nominal_values != 0, values / nominal_values, 1.0)
            templates[f] = _with_contents(h, values, nominal_variances * scale ** 2)
        return templates

    if len(h.axes) == 2:
        gen_ax, _ = _gen_reco_axes(h)
        values, variances = _values_variances(h, flow=True)
        values = np.moveaxis(values, gen_ax, 0)  # (n_gen (+flow), n_reco (+flow))
        variances = np.moveaxis(variances, gen_ax, 0)
        h_reco = _reco_projection(h)
        total = values.sum()
        for f in f_values:
            w = _gen_weights(h, f, flow=True)
            t_values = (w[:, None] * values).sum(axis=0)
            t_variances = (w[:, None] ** 2 * variances).sum(axis=0)
            scale = total / t_values.sum() if t_values.sum() != 0 else 1.0
            templates[f] = _with_contents(
                h_reco, t_values * scale, t_variances * scale ** 2, flow=True,
            )
        return templates

    raise ValueError(f"expected a 1D or 2D histogram, got {len(h.axes)} axes")


def _estimate_f(
    ac_obs: tuple[float, float],
    ac_f0: tuple[float, float],
    ac_f1: tuple[float, float],
) -> tuple[float, float]:
    """
    Estimate f from an observed reco asymmetry `ac_obs`, given the reco asymmetries of the
    (total MC) templates at f = 0 and f = 1. Since the templates are linear in f at fixed
    normalization, A^reco(f) is exactly linear too, so

        f = (A(0) - A_obs) / (A(0) - A(1)).

    Uncertainties of `ac_obs` and of A(0) are propagated (A(1) is built from the same events as
    A(0) and treated as fixed). For the 1D signal-only case A(1) = 0 and this reduces to
    f = 1 - A_obs / A(0).
    """
    (a_obs, s_obs), (a0, s0), (a1, _) = ac_obs, ac_f0, ac_f1
    slope = a0 - a1
    if slope == 0 or not np.isfinite(slope):
        return np.nan, np.nan
    f = (a0 - a_obs) / slope
    # df/dA_obs = -1 / slope,  df/dA(0) = (A_obs - A(1)) / slope^2
    sigma = np.sqrt((s_obs / slope) ** 2 + ((a_obs - a1) / slope ** 2 * s0) ** 2)
    return float(f), float(sigma)


#
# process handling
#

def _split_hists(hists, config_inst, signal_process):
    """
    Split the per-process `hists` (shift axis already removed) into summed data, signal (all
    processes belonging to `signal_process`) and background histograms (any may be None).

    `signal_process` may be a single process name or several separated by ";" (as passed via
    `--general-settings "signal_process=tt_sl;tt_dl"`). A plotted process counts as signal if it
    is one of these processes or one of their sub-processes.
    """
    signal_names = set(law.util.make_tuple(signal_process))
    signal_insts = [
        p for p in (config_inst.get_process(name, default=None) for name in signal_names)
        if p is not None
    ]

    def is_signal(proc_inst):
        return proc_inst.name in signal_names or any(
            s == proc_inst or s.has_process(proc_inst) for s in signal_insts
        )

    data, signal, background = [], [], []
    for proc_inst, h in hists.items():
        if proc_inst.is_data:
            data.append(h)
        elif is_signal(proc_inst):
            signal.append(h)
        else:
            background.append(h)

    def _sum(lst):
        return sum_hists(lst) if lst else None

    return _sum(data), _sum(signal), _sum(background)


def _parse_f_values(f_values) -> tuple[float, ...]:
    f_values = tuple(float(f) for f in law.util.make_tuple(f_values))
    # the nominal template is always needed as the ratio reference
    if 0.0 not in f_values:
        f_values = (0.0,) + f_values
    return tuple(sorted(f_values))


def _cms_label(ax, config_inst, cms_label, fontsize=18):
    import mplhep

    if cms_label == "skip":
        return
    mplhep.cms.label(
        ax=ax,
        llabel=_CMS_LABEL_OPTIONS.get(cms_label, cms_label),
        fontsize=fontsize,
        data=False,
        lumi=round(0.001 * config_inst.x.luminosity.get("nominal"), 1),
        com=config_inst.campaign.ecm,
    )


def _variable_insts_by_level(variable_insts) -> tuple:
    """
    Return `(gen_variable_inst, reco_variable_inst)`; either may be None.
    """
    gen = next((v for v in variable_insts if v.name.startswith("gen_")), None)
    reco = next((v for v in variable_insts if not v.name.startswith("gen_")), None)
    return gen, reco


def _prepare(hists, config_inst, signal_process, f_values):
    """
    Common preparation for all plot functions: split processes, build reco-X templates for the
    signal (reweighted) plus the backgrounds (nominal), and compute the asymmetries needed for
    the annotations.
    """
    hists = remove_residual_axis(hists, "shift")
    h_data, h_signal, h_background = _split_hists(hists, config_inst, signal_process)
    if h_signal is None:
        raise ValueError(
            f"no histograms for signal process(es) {signal_process!r} among the plotted processes "
            f"{[p.name for p in hists]}; pass e.g. --general-settings signal_process=<name>",
        )

    gen_mode = _is_gen_reco(h_signal)
    f_values = tuple(sorted(set(f_values) | {0.0, 1.0}))

    h_bkg_reco = _reco_projection(h_background) if h_background is not None else None
    sig_templates = _build_templates(h_signal, f_values)
    templates = {
        f: (h + h_bkg_reco if h_bkg_reco is not None else h)
        for f, h in sig_templates.items()
    }

    out = {
        "gen_mode": gen_mode,
        "h_signal": h_signal,
        "h_data_reco": _reco_projection(h_data) if h_data is not None else None,
        "h_bkg_reco": h_bkg_reco,
        "sig_templates": sig_templates,
        "templates": templates,
        "ac_reco_mc": _charge_asymmetry(templates[0.0]),
        "ac_reco_sig": _charge_asymmetry(sig_templates[0.0]),
        "ac_gen_nom": _charge_asymmetry(_gen_projection(h_signal)) if gen_mode else None,
        "ac_data": None,
        "f_hat": None,
        "ac_gen_hat": None,
    }

    if out["h_data_reco"] is not None:
        out["ac_data"] = _charge_asymmetry(out["h_data_reco"])
        out["f_hat"] = _estimate_f(
            out["ac_data"], out["ac_reco_mc"], _charge_asymmetry(templates[1.0]),
        )
        if gen_mode:
            # Eq. 29: A_C^gen = (1 - f) A_C^gen,nom
            (f_hat, s_f), (a_nom, s_nom) = out["f_hat"], out["ac_gen_nom"]
            out["ac_gen_hat"] = (
                (1.0 - f_hat) * a_nom,
                float(np.sqrt((s_f * a_nom) ** 2 + ((1.0 - f_hat) * s_nom) ** 2)),
            )

    return out


def _fmt_ac(name, ac):
    return rf"$A_C^{{{name}}} = {ac[0]:.5f} \pm {ac[1]:.5f}$"


#
# plot functions
#

def plot_tanh_y_decomposition(
    hists,
    config_inst,
    category_inst,
    variable_insts,
    shift_insts,
    style_config: dict | None = None,
    signal_process: str | tuple = "tt_sl",
    cms_label: str = "simwip",
    skip_legend: bool = False,
    **kwargs,
) -> tuple:
    """
    Plot the tanh(Delta|y|) distribution together with its symmetric (rho^+) and antisymmetric
    (rho^-) components in three panels (cf. Fig. 6 of AN-26-039). The asymmetries and the
    parameter f are quoted on the rho^- panel, which carries all of the asymmetry information.

    * 1D reco input: panels show the reco distribution of the total MC (and data, if present).
    * 2D gen-reco input: panels show the gen distribution of the signal (data has no gen
      information and is therefore only used for the quoted A_C^data, f and A_C^gen).

    Without data f is 0 by construction; with data the estimate of f from the observed reco
    asymmetry is shown (see `_estimate_f`).

    Exemplary task calls:

    .. code-block:: bash

        law run cf.PlotVariables1D --version v1 --processes tt_sl --variables tanh_y_18bin \\
            --plot-function mtt.plotting.plot_functions_asymmetry.plot_tanh_y_decomposition

        law run cf.PlotVariables2D --version v1 --processes tt_sl --variables gen_tanh_y-tanh_y_18bin \\
            --plot-function mtt.plotting.plot_functions_asymmetry.plot_tanh_y_decomposition
    """
    import matplotlib.pyplot as plt
    import mplhep

    prep = _prepare(hists, config_inst, signal_process, ())
    gen_var, reco_var = _variable_insts_by_level(variable_insts)

    if prep["gen_mode"]:
        h_panel_mc = _gen_projection(prep["h_signal"])
        h_panel_data = None
        mc_label = "Signal (gen)"
        x_title = gen_var.get_full_x_title()
    else:
        h_panel_mc = prep["templates"][0.0]
        h_panel_data = prep["h_data_reco"]
        mc_label = "MC"
        x_title = reco_var.get_full_x_title()

    mc_components = _decompose(h_panel_mc)
    data_components = _decompose(h_panel_data) if h_panel_data is not None else (None,) * 3

    plt.style.use(mplhep.style.CMS)
    fig, axs = plt.subplots(1, 3, figsize=(24, 8))

    titles = (r"$\rho(X)$", r"$\rho^{+}(X)$ (symmetric)", r"$\rho^{-}(X)$ (antisymmetric)")
    for ax, title, h_mc_comp, h_data_comp in zip(axs, titles, mc_components, data_components):
        _, mc_var = _values_variances(h_mc_comp)
        mplhep.histplot(h_mc_comp, ax=ax, yerr=np.sqrt(mc_var), color="tab:red", label=mc_label)
        if h_data_comp is not None:
            _, data_var = _values_variances(h_data_comp)
            mplhep.histplot(
                h_data_comp, ax=ax, yerr=np.sqrt(data_var), histtype="errorbar", color="black",
                label="Data",
            )
        ax.set_title(title, fontsize=18, pad=30)
        ax.set_xlabel(x_title)
        ax.set_ylabel("Events / bin")
        ax.set_xlim(-1, 1)
        _cms_label(ax, config_inst, cms_label, fontsize=14)

    # antisymmetric panel: asymmetry summary
    ax_minus = axs[2]
    ax_minus.axhline(0.0, color="gray", linestyle="--", linewidth=0.8, zorder=0)
    lines = []
    if prep["gen_mode"]:
        lines.append(_fmt_ac("gen,nom", prep["ac_gen_nom"]))
        lines.append(_fmt_ac("reco,sig", prep["ac_reco_sig"]))
    else:
        lines.append(_fmt_ac("MC", prep["ac_reco_mc"]))
        if prep["h_bkg_reco"] is not None:
            lines.append(_fmt_ac("sig", prep["ac_reco_sig"]))
    if prep["ac_data"] is not None:
        f_hat = prep["f_hat"]
        lines.append(_fmt_ac("data", prep["ac_data"]))
        lines.append(rf"$\hat{{f}} = {f_hat[0]:.3f} \pm {f_hat[1]:.3f}$")
        if prep["ac_gen_hat"] is not None:
            a, s_a = prep["ac_gen_hat"]
            lines.append(rf"$A_C^{{gen}}(\hat{{f}}) = {a:.5f} \pm {s_a:.5f}$")
    else:
        lines.append(r"$f = 0$ (nominal)")
    ax_minus.text(
        0.04, 0.96, "\n".join(lines),
        transform=ax_minus.transAxes, va="top", ha="left", fontsize=16,
        bbox={"facecolor": "white", "edgecolor": "gray", "alpha": 0.9},
    )

    axs[0].annotate(
        category_inst.label, xy=(0.04, 0.96), xycoords="axes fraction", va="top", ha="left",
        fontsize=16,
    )

    style_config = style_config or {}
    if "ax_cfg" in style_config:
        for ax in axs:
            ax.set(**style_config["ax_cfg"])

    if not skip_legend:
        for ax in axs[:2]:
            ax.legend(loc="lower right", fontsize=14)

    fig.tight_layout()
    return fig, tuple(axs)


def plot_tanh_y_f_templates(
    hists,
    config_inst,
    category_inst,
    variable_insts,
    shift_insts,
    style_config: dict | None = None,
    f_values: tuple | float = (-4.0, -1.0, 1.0, 4.0),
    signal_process: str | tuple = "tt_sl",
    yscale: str | None = None,
    **kwargs,
) -> tuple:
    """
    Overlay the reco tanh(Delta|y|) templates for several values of f, with a ratio panel to
    the nominal (f = 0) template (cf. Figs. 8 and 12 of AN-26-039). Only the `signal_process`
    contribution is reweighted; all other MC processes enter with their nominal shape
    (AN-26-039, l. 788).

    * 1D reco input: legend entries quote f and the signal A_C^reco(f) = (1 - f) A_C^reco,nom.
    * 2D gen-reco input: the reweighting is applied at gen level (Eq. 24); legend entries quote
      f and A_C^gen(f) = (1 - f) A_C^gen,nom, and the legend title the reco asymmetry and the
      dilution slope (A^reco_sig(0) - A^reco_sig(1)) / A_C^gen,nom (cf. Fig. 17).

    If data is among the processes it is overlaid (reco only) and the estimate of f (and, in 2D
    mode, A_C^gen) is added to the legend title.

    f values are set via `--general-settings "f_values=-4;-1;1;4"` (f = 0 is always included).

    Exemplary task calls:

    .. code-block:: bash

        law run cf.PlotVariables1D --version v1 --processes tt_sl,tt_dl,tt_fh,st,w_lnu \\
            --variables tanh_y_18bin \\
            --plot-function mtt.plotting.plot_functions_asymmetry.plot_tanh_y_f_templates

        law run cf.PlotVariables2D --version v1 --processes tt_sl --variables gen_tanh_y-tanh_y_18bin \\
            --plot-function mtt.plotting.plot_functions_asymmetry.plot_tanh_y_f_templates
    """
    import matplotlib.pyplot as plt
    from columnflow.plotting.plot_all import plot_all

    f_values = _parse_f_values(f_values)
    prep = _prepare(hists, config_inst, signal_process, f_values)
    templates = prep["templates"]
    nominal_values = templates[0.0].values()
    _, reco_var = _variable_insts_by_level(variable_insts)

    if prep["gen_mode"]:
        ac_ref, ac_level = prep["ac_gen_nom"][0], "gen"
    else:
        ac_ref, ac_level = prep["ac_reco_sig"][0], "reco"

    colors = plt.get_cmap("coolwarm")(np.linspace(0, 1, len(f_values)))
    plot_config = OrderedDict()
    for f, color in zip(f_values, colors):
        ac_f = (1.0 - f) * ac_ref
        is_nominal = f == 0.0
        line_style = {"color": "black" if is_nominal else color, "linestyle": "-" if is_nominal else "--"}
        plot_config[f"template_f{f:+g}"] = {
            "method": "draw_hist",
            "hist": templates[f],
            "kwargs": {
                "label": rf"$f = {f:+g}$, $A_C^{{{ac_level}}} = {ac_f:+.5f}$",
                "yerr": None,
                **line_style,
            },
            "ratio_kwargs": {"norm": nominal_values, "yerr": None, **line_style},
        }

    title_lines = []
    if prep["gen_mode"]:
        a_sig0 = prep["ac_reco_sig"][0]
        a_sig1 = _charge_asymmetry(prep["sig_templates"][1.0])[0]
        slope = (a_sig0 - a_sig1) / ac_ref if ac_ref else np.nan
        title_lines.append(rf"$A_C^{{reco}}(f=0) = {prep['ac_reco_mc'][0]:.5f}$, dilution $= {slope:.3f}$")

    if prep["h_data_reco"] is not None:
        f_hat = prep["f_hat"]
        title_lines.append(rf"$\hat{{f}} = {f_hat[0]:.3f} \pm {f_hat[1]:.3f}$")
        if prep["ac_gen_hat"] is not None:
            a, s = prep["ac_gen_hat"]
            title_lines.append(rf"$A_C^{{gen}}(\hat{{f}}) = {a:.5f} \pm {s:.5f}$")
        plot_config["data"] = {
            "method": "draw_errorbars",
            "hist": prep["h_data_reco"],
            "kwargs": {"label": "Data"},
            "ratio_kwargs": {"norm": nominal_values},
        }

    default_style_config = prepare_style_config(config_inst, category_inst, reco_var, yscale=yscale)
    default_style_config["ax_cfg"]["ylabel"] = "Events / bin"
    default_style_config["rax_cfg"]["ylabel"] = r"$f\ /\ f=0$"
    default_style_config["legend_cfg"]["ncols"] = 1
    if title_lines:
        default_style_config["legend_cfg"]["title"] = "\n".join(title_lines)
        default_style_config["legend_cfg"]["title_fontsize"] = "small"
    style_config = law.util.merge_dicts(default_style_config, style_config or {}, deep=True)

    return plot_all(plot_config, style_config, **kwargs)


def plot_tanh_y_gen_weights(
    hists,
    config_inst,
    category_inst,
    variable_insts,
    shift_insts,
    style_config: dict | None = None,
    f_values: tuple | float = (-4.0, -1.0, 1.0, 4.0),
    signal_process: str | tuple = "tt_sl",
    cms_label: str = "simwip",
    **kwargs,
) -> tuple:
    """
    Plot the gen-level event weight w(X_gen; f) (Eq. 24) as a function of the gen X bin for
    several values of f (cf. Fig. 7 of AN-26-039). Accepts a 1D gen histogram (``gen_tanh_y``)
    or a 2D gen-reco histogram, of which only the gen projection of the signal is used.

    The curves should be monotonic in X, cross 1 at X = 0 and deviate from 1 by a few percent
    for |f| <= 4.

    Exemplary task call:

    .. code-block:: bash

        law run cf.PlotVariables1D --version v1 --processes tt_sl --variables gen_tanh_y \\
            --plot-function mtt.plotting.plot_functions_asymmetry.plot_tanh_y_gen_weights
    """
    import matplotlib.pyplot as plt
    import mplhep

    f_values = _parse_f_values(f_values)
    hists = remove_residual_axis(hists, "shift")
    _, h_signal, _ = _split_hists(hists, config_inst, signal_process)
    if h_signal is None:
        raise ValueError(
            f"no histograms for signal process(es) {signal_process!r} among the plotted processes "
            f"{[p.name for p in hists]}; pass e.g. --general-settings signal_process=<name>",
        )
    h_gen = _gen_projection(h_signal)
    edges = h_gen.axes[0].edges
    gen_var, _ = _variable_insts_by_level(variable_insts)

    plt.style.use(mplhep.style.CMS)
    fig, ax = plt.subplots(figsize=(10, 8))
    colors = plt.get_cmap("coolwarm")(np.linspace(0, 1, len(f_values)))
    for f, color in zip(f_values, colors):
        is_nominal = f == 0.0
        mplhep.histplot(
            _gen_weights(h_gen, f, flow=False), bins=edges, ax=ax,
            color="black" if is_nominal else color, linestyle="-" if is_nominal else "--",
            label=f"f = {f:+g}" + (" (nominal)" if is_nominal else ""),
        )
    ax.set_xlim(edges[0], edges[-1])
    ax.set_xlabel((gen_var or variable_insts[0]).get_full_x_title())
    ax.set_ylabel("Event weight")
    ax.legend(loc="upper center", fontsize=14, ncols=2)
    _cms_label(ax, config_inst, cms_label, fontsize=16)

    style_config = style_config or {}
    if "ax_cfg" in style_config:
        ax.set(**style_config["ax_cfg"])

    fig.tight_layout()
    return fig, (ax,)
