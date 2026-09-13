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
        mplhep.cms.label(
            ax=ax,
            llabel=label_options.get(cms_label, cms_label),
            fontsize=18,
            data=False,
            lumi=round(0.001 * config_inst.x.luminosity.get("nominal"), 1),
            com=config_inst.campaign.ecm,
        )

    plt.tight_layout()

    return fig, (ax,)
