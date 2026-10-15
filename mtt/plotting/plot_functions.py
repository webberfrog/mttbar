# coding: utf-8

"""
Custom plot functions producing summary plots of derived, non-histogram quantities.
"""

from __future__ import annotations

__all__ = []

from columnflow.util import maybe_import
from columnflow.hist_util import sum_hists
from columnflow.plotting.plot_util import remove_residual_axis

np = maybe_import("numpy")
hist = maybe_import("hist")


def _hist_moments(h) -> tuple[float, float, float, float, float]:
    """
    Return `(S, M, varS, varM, covMS)` for a 1D or 2D histogram `h`, where, writing `x` for the
    bin center (1D) or the product of the two axes' bin centers (2D):

      * `S`     -- sum of bin contents (excl. flow)
      * `M`     -- sum of `x * content`
      * `varS`  -- variance of `S` (sum of per-bin variances)
      * `varM`  -- variance of `M` (sum of `x**2 * per-bin variance`)
      * `covMS` -- covariance(M, S) (sum of `x * per-bin variance`)

    These are the building blocks both for the weighted mean `<x> = M / S` (and its variance)
    and for combining several histograms' `M`/`S` contributions via independent error
    propagation (see `_combine`).
    """
    values = h.values()
    variances = h.variances()

    if len(h.axes) == 1:
        x = h.axes[0].centers
    elif len(h.axes) == 2:
        cx = h.axes[0].centers
        cy = h.axes[1].centers
        x = cx[:, None] * cy[None, :]
    else:
        raise ValueError(f"expected a 1D or 2D histogram, got {len(h.axes)} axes")

    S = float(values.sum())
    M = float((x * values).sum())
    varS = float(variances.sum())
    varM = float((x ** 2 * variances).sum())
    covMS = float((x * variances).sum())
    return S, M, varS, varM, covMS


def _combine(
    mom_a: tuple[float, float, float, float, float],
    kappa_a: float,
    mom_b: tuple[float, float, float, float, float],
    kappa_b: float,
    scale: float,
) -> tuple[float, float]:
    """
    Combine the contributions of two histograms -- built from disjoint, and therefore
    statistically independent, event sub-samples, each with its own spin-analyzing power
    `kappa_a`/`kappa_b` -- into a single expectation-value estimate

        value = scale * (M_a / kappa_a + M_b / kappa_b) / (S_a + S_b)

    and its propagated variance, via standard (delta-method) error propagation.
    """
    s_a, m_a, var_s_a, var_m_a, cov_ms_a = mom_a
    s_b, m_b, var_s_b, var_m_b, cov_ms_b = mom_b

    s = s_a + s_b
    ratio = (m_a / kappa_a + m_b / kappa_b) / s
    value = scale * ratio

    var_a = (var_m_a / kappa_a ** 2 - 2 * ratio * cov_ms_a / kappa_a + ratio ** 2 * var_s_a) / s ** 2
    var_b = (var_m_b / kappa_b ** 2 - 2 * ratio * cov_ms_b / kappa_b + ratio ** 2 * var_s_b) / s ** 2
    variance = scale ** 2 * (var_a + var_b)

    return value, variance


def _mean_and_var(mom: tuple[float, float, float, float, float]) -> tuple[float, float]:
    """
    Return the weighted mean `<x> = M / S` and its variance, via delta-method error propagation
    (as in `_combine`), from the `_hist_moments` output `mom`.
    """
    s, m, var_s, var_m, cov_ms = mom
    mean = m / s
    variance = (var_m - 2 * mean * cov_ms + mean ** 2 * var_s) / s ** 2
    return mean, variance


def _cms_label(ax, config_inst, cms_label: str) -> None:
    """
    Draw the CMS label and luminosity/energy on `ax`, unless `cms_label` is "skip".
    """
    import mplhep

    if cms_label == "skip":
        return

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
    mplhep.cms.label(
        ax=ax,
        llabel=label_options.get(cms_label, cms_label),
        fontsize=18,
        data=False,
        lumi=round(0.001 * config_inst.x.luminosity.get("nominal"), 1),
        com=config_inst.campaign.ecm,
    )


def plot_spin_density_matrix(
    hists,
    config_inst,
    category_inst,
    variable_insts,
    shift_insts,
    style_config: dict | None = None,
    kappa_lep: float = 1.0,
    kappa_bjet: float = 1.0,
    cms_label: str = "wip",
    skip_legend: bool = False,
    **kwargs,
) -> tuple:
    """
    Extract the ttbar polarization vectors (P for the top, P-bar for the antitop) and the spin
    correlation matrix C, in the helicity (k, n, r) basis, from the expectation values of the
    charge-corrected decay-product observables produced by `mtt.production.ttbar_reco_uic.uic`
    (see `TTbar.top_lepton_*`, `TTbar.top_bjet_*`, `TTbar.atop_lepton_*`, `TTbar.atop_bjet_*`),
    and plot them in the style of Fig. 17/19 of CMS-TOP-23-007 (arXiv:2409.11067) -- but without
    a simulation-comparison panel, since this method has no associated prediction to compare to.

    This uses the direct "expectation value" method

        P_i    = 3 * <Omega_i> / kappa,
        C_ij   = -9 * <Omega_i * Omega-bar_j> / (kappa_lep * kappa_bjet),

    (see e.g. Bernreuther, Heisler & Si, JHEP 12 (2015) 026) rather than the paper's binned
    maximum-likelihood template fit, and is therefore a lightweight cross-check, not a
    reproduction of the paper's headline result.

    Since the lepton and the b-jet have different spin-analyzing power, and which one is the
    physical top's decay product (vs. the antitop's) flips event by event with the lepton
    charge, each expectation value is computed by combining the two (disjoint, and thus
    independent) charge sub-samples separately, each with its own `kappa`, via `_combine`.

    The off-diagonal combinations `C_ij +/- C_ji` are formed assuming `C_ij` and `C_ji` are
    statistically independent for the purpose of error propagation; in reality they are built
    from the same events (just paired differently) and are correlated, so the quoted
    uncertainties on these combinations are an approximation.

    Expects `hists` to contain, for the requested category, one histogram for each of:

      * 1D: ``{role}_{{lepton,bjet}}_{{k,n,r}}`` for `role` in `top`, `atop` (12 total)
      * 2D: ``top_lepton_{i}-atop_bjet_{j}`` and ``top_bjet_{i}-atop_lepton_{j}``
        for `i`, `j` in `k`, `n`, `r` (18 total)

    i.e. this plot function is meant to be used with ``cf.PlotVariables1D --multi-variable``
    and a ``--variables`` list containing all 30 of the above.
    """
    import matplotlib.pyplot as plt
    import mplhep

    # drop the residual shift axis left over from the (already category-reduced) input hists
    hists = {
        var_name: remove_residual_axis(var_hists, "shift")
        for var_name, var_hists in hists.items()
    }

    # sum all requested processes together for each variable, then compute moments
    moments = {
        var_name: _hist_moments(sum_hists(list(var_hists.values())))
        for var_name, var_hists in hists.items()
    }

    def moments_for(name):
        if name not in moments:
            raise KeyError(
                f"histogram for variable '{name}' not found among the requested variables; make "
                "sure it is included in --variables (see plot_spin_density_matrix docstring)",
            )
        return moments[name]

    # -- polarization vectors P (top) and P-bar (antitop)

    polarizations = {}
    for role in ("top", "atop"):
        for component in ("k", "n", "r"):
            mom_lep = moments_for(f"{role}_lepton_{component}")
            mom_bjet = moments_for(f"{role}_bjet_{component}")
            polarizations[(role, component)] = _combine(mom_lep, kappa_lep, mom_bjet, kappa_bjet, scale=3.0)

    # -- spin correlation matrix C

    kappa_prod = kappa_lep * kappa_bjet
    correlations = {}
    for i in ("k", "n", "r"):
        for j in ("k", "n", "r"):
            mom_plus = moments_for(f"top_lepton_{i}-atop_bjet_{j}")
            mom_minus = moments_for(f"top_bjet_{i}-atop_lepton_{j}")
            correlations[(i, j)] = _combine(mom_plus, kappa_prod, mom_minus, kappa_prod, scale=-9.0)

    def c_plus_minus(i, j, sign):
        val_ij, var_ij = correlations[(i, j)]
        val_ji, var_ji = correlations[(j, i)]
        # treats C_ij and C_ji as independent (see docstring)
        return val_ij + sign * val_ji, var_ij + var_ji

    # -- assemble rows in the order used by Fig. 17/19 of CMS-TOP-23-007 (minus the "c-1" row,
    # which belongs to the overall-normalization parameter of the binned fit and has no
    # counterpart in the expectation-value method)

    rows = []
    for component, label in (("r", "P_{r}"), ("n", "P_{n}"), ("k", "P_{k}")):
        rows.append((label, *polarizations[("top", component)]))
    for component, label in (("r", r"\bar{P}_{r}"), ("n", r"\bar{P}_{n}"), ("k", r"\bar{P}_{k}")):
        rows.append((label, *polarizations[("atop", component)]))
    for component, label in (("r", "C_{rr}"), ("n", "C_{nn}"), ("k", "C_{kk}")):
        rows.append((label, *correlations[(component, component)]))
    for (i, j), label in ((("n", "r"), "C^{+}_{nr}"), (("r", "k"), "C^{+}_{rk}"), (("n", "k"), "C^{+}_{nk}")):
        rows.append((label, *c_plus_minus(i, j, +1)))
    for (i, j), label in ((("n", "r"), "C^{-}_{nr}"), (("r", "k"), "C^{-}_{rk}"), (("n", "k"), "C^{-}_{nk}")):
        rows.append((label, *c_plus_minus(i, j, -1)))

    # -- plot

    plt.style.use(mplhep.style.CMS)

    n_rows = len(rows)
    fig, ax = plt.subplots(figsize=(8, 0.55 * n_rows + 2))

    y_pos = np.arange(n_rows)[::-1]
    values = np.array([row[1] for row in rows])
    errors = np.sqrt(np.clip(np.array([row[2] for row in rows]), 0.0, None))

    ax.errorbar(
        values, y_pos,
        xerr=errors,
        fmt="o",
        color="black",
        markersize=6,
        capsize=3,
        label="Data",
    )
    ax.axvline(0.0, color="gray", linewidth=0.8, linestyle="--", zorder=0)

    tick_labels = [
        rf"${row[0]}$" + "\n" + rf"${row[1]:.3f} \pm {np.sqrt(max(row[2], 0.0)):.3f}$"
        for row in rows
    ]
    ax.set_yticks(y_pos)
    ax.set_yticklabels(tick_labels, fontsize=13)
    ax.set_ylim(-1, n_rows)
    ax.set_xlabel("Coefficient value")

    style_config = style_config or {}
    if "ax_cfg" in style_config:
        ax.set(**style_config["ax_cfg"])

    if not skip_legend:
        ax.legend(loc="upper right", fontsize=14)

    ax.annotate(
        category_inst.label,
        xy=(0.02, 0.98),
        xycoords="axes fraction",
        va="top",
        ha="left",
        fontsize=16,
    )

    _cms_label(ax, config_inst, cms_label)

    plt.tight_layout()

    return fig, (ax,)


# observables of the entanglement summary plot: y-axis label, separable-states boundary, and on
# which side of the boundary the separable states lie
_ENTANGLEMENT_OBSERVABLES = {
    "cos_phi": {
        "label": r"$D = -(C_{nn} + C_{rr} + C_{kk})/3$",
        "boundary": -1.0 / 3.0,
        "separable_side": "above",
    },
    "cos_phi_tilde": {
        "label": r"$\tilde{D} = (C_{nn} - C_{rr} - C_{kk})/3$",
        "boundary": 1.0 / 3.0,
        "separable_side": "below",
    },
}


def plot_entanglement_summary(
    hists,
    config_inst,
    category_inst,
    variable_insts,
    shift_insts,
    style_config: dict | None = None,
    kappa_lep: float = 1.0,
    kappa_bjet: float = 1.0,
    band_width: float = 0.015,
    cms_label: str = "wip",
    skip_legend: bool = False,
    **kwargs,
) -> tuple:
    """
    Entanglement summary plot in the style of Fig. 131 of AN2023_120: one panel per observable,
    D (from ``cos_phi``) and/or D-tilde (from ``cos_phi_tilde``), with one column per phase-space
    region showing the data point, the summed MC prediction as a line with a stat. band, the
    separable-states boundary (green band at -1/3 for D, +1/3 for D-tilde), and the
    observed (expected) significance of the deviation from that boundary.

    Both quantities are extracted directly from the mean of the respective opening-angle
    distribution,

        D = -3 * <cos phi> / (kappa_lep * kappa_bjet),
        D-tilde = -3 * <cos phi-tilde> / (kappa_lep * kappa_bjet),

    with the statistical uncertainty propagated from the histogram variances.

    Expects the histograms to carry a ``region`` axis as added by the
    ``stack_entanglement_regions`` hist hook (regions configured via
    ``config_inst.x.entanglement_regions``), i.e. to be used as

    .. code-block:: bash

        law run cf.PlotVariables1D --version v1 --processes data,tt --categories incl \\
            --variables cos_phi,cos_phi_tilde --multi-variable \\
            --hist-hooks stack_entanglement_regions \\
            --plot-function mtt.plotting.plot_functions.plot_entanglement_summary \\
            --general-settings kappa_lep=1.0,kappa_bjet=<value>

    Data processes give the points; all other processes are summed into the MC prediction. If no
    data process is requested, the MC prediction is used as pseudo-data (with MC stat. errors),
    so the plot can be produced while blinded.

    The observed significance is `(boundary - D_data) / sigma_data`, signed so that it is positive
    towards the entangled side; the expected one uses D_MC with the same uncertainty.

    Caveats -- this is a detector-level cross-check, not a reproduction of the AN result:

      * no unfolding or acceptance correction, and no systematic uncertainties (stat. only), so
        values are diluted with respect to the AN's parton-level numbers;
      * ``TTbar.top_pt`` is the lab-frame top pT, whereas the AN may define pT(t) differently;
      * the mean is computed from bin centers, so finer binning reduces the (small) binning bias.
    """
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import mplhep

    var_names = [name for name in hists if name in _ENTANGLEMENT_OBSERVABLES]
    if not var_names:
        raise ValueError(
            f"none of the requested variables {list(hists)} is a known entanglement observable "
            f"({list(_ENTANGLEMENT_OBSERVABLES)})",
        )

    kappa_prod = kappa_lep * kappa_bjet
    style_config = style_config or {}

    plt.style.use(mplhep.style.CMS)
    fig, axs = plt.subplots(1, len(var_names), figsize=(10 * len(var_names), 8), squeeze=False)
    axs = axs[0]

    for ax, var_name in zip(axs, var_names):
        obs = _ENTANGLEMENT_OBSERVABLES[var_name]
        boundary = obs["boundary"]
        # +1 if a value below the boundary is entangled, -1 otherwise
        sign = 1.0 if obs["separable_side"] == "above" else -1.0

        var_hists = remove_residual_axis(hists[var_name], "shift")
        if any("region" not in h.axes.name for h in var_hists.values()):
            raise ValueError(
                f"histograms of variable '{var_name}' have no 'region' axis; run with "
                "--hist-hooks stack_entanglement_regions",
            )

        data_hists = [h for proc, h in var_hists.items() if proc.is_data]
        mc_procs = [proc for proc in var_hists if not proc.is_data]
        mc_hists = [var_hists[proc] for proc in mc_procs]
        if not mc_hists:
            raise ValueError(f"no MC processes requested for variable '{var_name}'")
        h_mc = sum_hists(mc_hists)
        h_data = sum_hists(data_hists) if data_hists else None

        regions = list(h_mc.axes["region"])

        def extract(h, region):
            mean, var = _mean_and_var(_hist_moments(h[{"region": hist.loc(region)}]))
            return -3.0 * mean / kappa_prod, 3.0 * np.sqrt(max(var, 0.0)) / abs(kappa_prod)

        mc_results = [extract(h_mc, region) for region in regions]
        data_results = [extract(h_data, region) for region in regions] if h_data is not None else mc_results

        # MC prediction: line with stat. band per region
        mc_label = ", ".join(proc.label for proc in mc_procs)
        for i, (d_mc, err_mc) in enumerate(mc_results):
            ax.fill_between([i, i + 1], d_mc - err_mc, d_mc + err_mc, color="salmon", alpha=0.5, linewidth=0)
            ax.hlines(d_mc, i, i + 1, color="red", linewidth=1.5)

        # data (or pseudo-data) points
        x_centers = np.arange(len(regions)) + 0.5
        d_data = np.array([r[0] for r in data_results])
        err_data = np.array([r[1] for r in data_results])
        data_label = "Data" if h_data is not None else "Pseudo-data (MC)"
        ax.errorbar(x_centers, d_data, yerr=err_data, fmt="o", color="black", markersize=6, capsize=3)

        # y range: include all points, bands and the boundary, with headroom for legend/labels
        lo = min(np.min(d_data - err_data), min(d - e for d, e in mc_results), boundary)
        hi = max(np.max(d_data + err_data), max(d + e for d, e in mc_results), boundary)
        span = max(hi - lo, 0.05)
        ax.set_ylim(lo - 0.35 * span, hi + 0.6 * span)
        y_range = np.diff(ax.get_ylim())[0]

        # separable-states boundary band
        half_width = band_width * y_range
        ax.axhspan(boundary - half_width, boundary + half_width, color="#a8cfc0", zorder=0)
        arrow = r"$\uparrow$" if sign > 0 else r"$\downarrow$"
        ax.text(
            len(regions) / 2, boundary, f"{arrow} Separable states {arrow}",
            ha="center", va="center", fontsize=14, color="gray",
        )

        # significance per region, placed on the entangled side of the band
        text_offset = sign * (half_width + 0.03 * y_range)
        for i, ((d_obs, err_obs), (d_exp, _)) in enumerate(zip(data_results, mc_results)):
            if err_obs <= 0:
                continue
            sig_obs = sign * (boundary - d_obs) / err_obs
            sig_exp = sign * (boundary - d_exp) / err_obs
            ax.text(
                i + 0.5, boundary - text_offset, f"{sig_obs:.1f} ({sig_exp:.1f})$\\sigma$",
                ha="center", va="top" if sign > 0 else "bottom", fontsize=15,
            )

        # region columns
        for i in range(1, len(regions)):
            ax.axvline(i, color="gray", linewidth=0.8, linestyle="--")
        ax.set_xlim(0, len(regions))
        ax.set_xticks(x_centers)
        ax.set_xticklabels([config_inst.get_category(region).label for region in regions], fontsize=15)
        ax.tick_params(axis="x", which="both", top=False, bottom=False)
        ax.set_ylabel(obs["label"])

        if "ax_cfg" in style_config:
            ax.set(**style_config["ax_cfg"])
        if var_name in style_config and "ax_cfg" in style_config[var_name]:
            ax.set(**style_config[var_name]["ax_cfg"])

        if not skip_legend:
            handles = [
                ax.errorbar([], [], yerr=[], fmt="o", color="black", markersize=6, capsize=3),
                (mpatches.Patch(color="salmon", alpha=0.5), plt.Line2D([], [], color="red")),
            ]
            ax.legend(handles, [data_label, mc_label], loc="upper right", fontsize=14)

        ax.annotate(
            category_inst.label,
            xy=(0.02, 0.98),
            xycoords="axes fraction",
            va="top",
            ha="left",
            fontsize=16,
        )

        _cms_label(ax, config_inst, cms_label)

    plt.tight_layout()

    return fig, tuple(axs)
