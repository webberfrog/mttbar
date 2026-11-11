# coding: utf-8

"""
AK4 jet list used for the ttbar reconstruction.

Shared by `uic.production.ttbar_reco_uic` (chi2 combinatorics) and
`uic.production.top_width_observables`, so that both work on the same jets independently of
the combinatorics code.

IMPORTANT: `TTbar.jet_idxs_lep` and `TTbar.jet_idxs_had` are positions in the list returned by
`reco_jets`, NOT in `events.Jet`. They only make sense when the jet list is obtained from this
function, with the same `ttbar_reco_settings` and the same `events.Jet` (same shift, nothing
re-sorting or filtering jets in between). Any code that resolves these indices, and any
reconstruction that replaces the combinatorics but keeps writing `TTbar.jet_idxs_*`, must call
`reco_jets` rather than build its own jet list; otherwise the indices silently point at the
wrong jets.
"""

from columnflow.util import maybe_import

from mtt.production.util import lv_mass

ak = maybe_import("awkward")

# columns needed by `reco_jets`; add them to the `uses` of every producer that calls it
RECO_JETS_USES = {
    "Jet.{pt,eta,phi,mass}",
    "FatJetTopTagDeltaRLepton.{pt,eta,phi,mass}",
}


def reco_jets(events: ak.Array, settings) -> ak.Array:
    """
    Return the jets available to the ttbar reconstruction: the first `n_jet_max` jets, without
    those within `jet_topjet_min_dr` (default 1.2 = AK8 + AK4 radius) of a top-tagged AK8 jet.
    In resolved events (no top-tagged AK8 jet) this is just the first `n_jet_max` jets.

    *settings* is the config's `ttbar_reco_settings`.

    The returned jets keep all fields and any behaviour of `events.Jet` (e.g. the b-tag score
    used by the `uic` producer); only the selection is computed on Lorentz-vector copies.
    See the module docstring for how `TTbar.jet_idxs_*` relate to this list.
    """
    jet_lv = lv_mass(events.Jet)
    keep = ak.local_index(jet_lv, axis=1) < settings["n_jet_max"]

    # well separated from top-tagged AK8 jets
    dr_jet_topjet = ak.min(jet_lv.metric_table(lv_mass(events.FatJetTopTagDeltaRLepton)), axis=2)
    keep = keep & ak.fill_none(dr_jet_topjet > settings.get("jet_topjet_min_dr", 1.2), True)

    return events.Jet[keep]
