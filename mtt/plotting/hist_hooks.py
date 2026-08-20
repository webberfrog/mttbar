# coding: utf-8

"""
Custom hist hooks (see columnflow's ``HistHookMixin``), invoked via ``--hist-hooks <name>`` right
before plotting to transform histograms in place.
"""

from __future__ import annotations

from columnflow.util import maybe_import

hist = maybe_import("hist")
np = maybe_import("numpy")


# axis names this hook knows how to asymmetrize, and the spin-analyzing-power prefactor
# to apply for each (5.0 for both the lepton and the b-jet, per the current analysis note)
_ASYMMETRY_AXES = {
    "cos_phi": 2.5,
    "cos_phi_tilde": 2.5,
}


def _asymmetrize_hist(h, sign_axis_name, prefactor, collapse):
    """
    Compute D (and its propagated variance) for a single histogram along `sign_axis_name`.
    See `calculate_asymmetry` for the definition of D.

    If `collapse` is False, returns a new histogram with the same axes/shape as `h`, with every
    bin along `sign_axis_name` (for a given combination of the other axes) filled with that
    combination's single D value -- used to keep the exact 2-axis heatmap shape of a plot like
    ``ttbar_mass-cos_phi``, where cos_phi is the only other axis besides the sign axis itself.

    If `collapse` is True, `sign_axis_name` is removed entirely from the output histogram's
    axes -- used when two (or more) other variable axes are being kept (e.g.
    ``ttbar_mass-cos_theta-cos_phi``), so that the result is a genuinely lower-dimensional
    histogram in the remaining axes, as expected by a 2D plot of D(var1, var2).
    """
    # positive- and negative-cos_phi sub-histograms, with the sign axis summed away
    h_pos = h[{sign_axis_name: slice(hist.loc(0), None, sum)}]
    h_neg = h[{sign_axis_name: slice(None, hist.loc(0), sum)}]

    n_pos = h_pos.values()
    n_neg = h_neg.values()
    denom = n_pos + n_neg

    # variances of each partition; fall back to a Poisson assumption (variance == value)
    # if the histogram's storage type doesn't track variances separately
    var_pos = h_pos.variances()
    var_neg = h_neg.variances()
    if var_pos is None:
        var_pos = n_pos
    if var_neg is None:
        var_neg = n_neg

    with np.errstate(divide="ignore", invalid="ignore"):
        # a bin is only meaningful if both partitions are non-negative; with weighted NLO MC
        # (negative generator weights), a sparse bin can have N_pos or N_neg come out negative
        # from weight-sign cancellation, which breaks the mathematical guarantee that
        # |N_pos - N_neg| <= N_pos + N_neg and lets D blow up far past [-prefactor, prefactor].
        # Treat such bins as invalid, the same as empty (denom <= 0) ones.
        valid = (denom > 0) & (n_pos >= 0) & (n_neg >= 0)

        d = np.where(valid, prefactor * (n_pos - n_neg) / denom, 0.0)
        # error propagation for D = prefactor * (a - b) / (a + b), with a, b independent:
        # var(D) = (2 * prefactor / (a + b)^2)^2 * (b^2 * var(a) + a^2 * var(b))
        d_var = np.where(
            valid,
            (2 * prefactor / denom ** 2) ** 2 * (n_neg ** 2 * var_pos + n_pos ** 2 * var_neg),
            0.0,
        )

    if collapse:
        # h_pos (equivalently h_neg) already has exactly the axes of `h` minus the collapsed
        # sign axis -- reuse it as a template for the output histogram
        h_out = h_pos.copy()
        view = h_out.view(flow=False)
        if view.dtype.names:
            view["value"][...] = d
            view["variance"][...] = d_var
        else:
            view[...] = d
        return h_out

    # broadcast the per-bin D value (and its variance) back across the (kept-shape) sign axis
    sign_axis_idx = h.axes.name.index(sign_axis_name)
    d_broadcast = np.expand_dims(d, axis=sign_axis_idx)
    d_var_broadcast = np.expand_dims(d_var, axis=sign_axis_idx)

    h_out = h.copy()
    view = h_out.view(flow=False)
    if view.dtype.names:
        # weighted storage (value, variance, ...)
        view["value"][...] = np.broadcast_to(d_broadcast, view["value"].shape)
        view["variance"][...] = np.broadcast_to(d_var_broadcast, view["variance"].shape)
    else:
        # plain storage has no separate slot for the variance; it cannot be retained here
        view[...] = np.broadcast_to(d_broadcast, view.shape)

    return h_out


def calculate_asymmetry(task, hists, category_name=None, variable_name=None, **kwargs):
    """
    Hist hook that replaces the ``cos_phi``/``cos_phi_tilde`` axis of a histogram with the
    spin-correlation asymmetry

        D = prefactor * (N(cos_phi > 0) - N(cos_phi < 0)) / (N(cos_phi > 0) + N(cos_phi < 0))

    computed independently for every bin of the histogram's other axes (e.g. ``ttbar_mass``,
    ``category``, ``shift``).

    Two output shapes are supported, chosen automatically based on how many other variables are
    being plotted alongside the sign axis:

    - Exactly one other variable (e.g. ``ttbar_mass-cos_phi``): the output histogram keeps the
      exact same axes as the input, including the cos_phi(_tilde) axis itself, with every bin
      along that axis in a given "column" filled with that column's single D value. This
      preserves the original 2-axis heatmap shape for plotting with e.g. ``cf.PlotVariables2D``.

    - Two other variables (e.g. ``ttbar_mass-cos_theta-cos_phi``): the sign axis is dropped
      entirely from the output histogram, leaving a genuinely 2D histogram of D as a function of
      the two remaining variables -- suitable for a true D(var1, var2) 2D plot.

    The statistical uncertainty on D is propagated from the (independent, since built from
    disjoint sets of events) variances of N(cos_phi > 0) and N(cos_phi < 0) via standard error
    propagation, and stored in the output histogram's variance field. It is not visualized by
    the default 2D plot, but is retained in the underlying histogram data.

    D is computed once from the combined counts summed across all requested processes (not
    separately per process), since it is not an additive quantity -- summing already-computed
    per-process D values, as the default plot function does for raw counts, would be wrong. The
    result is carried under a single representative process key; the plot's legend will
    therefore only show that one process's label.

    If none of the variables being plotted is ``cos_phi``/``cos_phi_tilde``, the histograms are
    returned unchanged.

    Exemplary task calls:

    .. code-block:: bash

        law run cf.PlotVariables2D --version v1 --processes tt_fh \\
            --variables ttbar_mass-cos_phi --hist-hooks calculate_asymmetry

        law run cf.PlotVariables2D --version v1 --processes tt_fh \\
            --variables ttbar_mass-cos_theta-cos_phi --hist-hooks calculate_asymmetry
    """
    # figure out which of the plotted variables is the asymmetry axis, if any
    plotted_vars = variable_name.split("-") if variable_name else []
    sign_axis_name = next((name for name in plotted_vars if name in _ASYMMETRY_AXES), None)
    if sign_axis_name is None:
        return hists

    prefactor = _ASYMMETRY_AXES[sign_axis_name]
    n_other_vars = len(plotted_vars) - 1
    collapse = n_other_vars >= 2

    # `hists` is nested as dict[od.Config, dict[od.Process, hist.Hist]]
    new_hists = {}
    for config_inst, config_hists in hists.items():
        process_insts = list(config_hists.keys())
        example_h = config_hists[process_insts[0]]
        if sign_axis_name not in example_h.axes.name:
            new_hists[config_inst] = config_hists
            continue

        # D is not additive across processes -- plot_2d sums per-process histograms together
        # downstream (`sum_hists(hists.values())`), so computing D separately per process and
        # letting those already-derived values be summed afterwards would be wrong (e.g. two
        # processes each near D = +5 would sum to +10). Instead, sum the raw (still-additive)
        # counts across all requested processes first, and compute D once on the combination.
        h_total = config_hists[process_insts[0]].copy()
        for process_inst in process_insts[1:]:
            h_total = h_total + config_hists[process_inst]

        h_out = _asymmetrize_hist(h_total, sign_axis_name, prefactor, collapse)

        # carry the single combined result under one representative process key, since the
        # per-process breakdown is no longer meaningful for a derived quantity like D; note
        # this means the legend will only show that one process's label/color -- pass
        # --skip-legend if that's undesirable
        new_hists[config_inst] = {process_insts[0]: h_out}

    return new_hists


# registry consumed by `config_inst.x.hist_hooks`
hist_hooks = {
    "calculate_asymmetry": calculate_asymmetry,
}
