# coding: utf-8

"""
Column production methods related to ttbar decay width observables (m_lb and DeltaR_min(j_l, j_b))

m_lb: the reconstructed invariant mass of the lepton and b quark of the leptonically decaying top
DeltaR_min(j_l, j_b): angular distance between the b-jet and the closest light jet (down, up or strange originated
    jet) from the hadronically decaying top

Both are built from the chi2 jet assignment of the `uic` producer (`TTbar.*` columns), so the
producers here must run in the same `cf.ProduceColumns` call as `uic`, after it. The jet indices
`TTbar.jet_idxs_{lep,had}` are resolved with `uic.production.reco_jets.reco_jets` (see there).
"""
from columnflow.production import Producer, producer
from columnflow.util import maybe_import
from columnflow.columnar_util import set_ak_column, EMPTY_FLOAT

from mtt.production.util import lv_mass  # PtEtaPhiM Lorentz vectors with coffea behaviour attached
from uic.production.reco_jets import reco_jets, RECO_JETS_USES

ak = maybe_import("awkward")
np = maybe_import("numpy")


@producer(
    uses=RECO_JETS_USES | {
        "TTbar.jet_idxs_lep",  # indices of the jets the chi2 assignment puts on the leptonic top
        "TTbar.n_jet_lep",  # number of jets on the leptonic side (1 or 2)
        "Lepton.{pt,eta,phi,mass}",  # the selected lepton (one record per event), from `choose_lepton`
        "BJet.{pt,eta,phi,mass}",  # b-tagged jets, to flag whether the leptonic jet is tagged
    },
    produces={"TopWidth.mlb", "TopWidth.lep_jet_is_b"},
)
def _m_lb(self: Producer, events: ak.Array, **kwargs) -> ak.Array:
    """
    m_lb = invariant mass of the lepton and the jet assigned to the leptonic top.

    Only defined when exactly one jet is assigned to the leptonic side; with two jets it is not
    known which one is the b (the chi2 does not use b-tagging). Otherwise EMPTY_FLOAT.
    `TopWidth.lep_jet_is_b` says whether that jet is b-tagged, to require it in a category.
    """
    jet = lv_mass(reco_jets(events, self.config_inst.x.ttbar_reco_settings))

    jets_lep = jet[events.TTbar.jet_idxs_lep]  # jagged: 1-2 jets per event
    b_lep = ak.firsts(jets_lep)  # None for events without leptonic jets
    lepton = lv_mass(events.Lepton)

    has_one_lep_jet = ak.fill_none(events.TTbar.n_jet_lep == 1, False)
    mlb = ak.where(has_one_lep_jet, (lepton + b_lep).mass, EMPTY_FLOAT)

    # b-tag flag via matching against the BJet collection (same trick as `uic`)
    dr_b_bjet = ak.min(lv_mass(events.BJet).delta_r(b_lep), axis=1)
    lep_jet_is_b = ak.fill_none(dr_b_bjet < 0.01, False) & has_one_lep_jet

    events = set_ak_column(events, "TopWidth.mlb", ak.fill_none(mlb, EMPTY_FLOAT))
    events = set_ak_column(events, "TopWidth.lep_jet_is_b", lep_jet_is_b)
    return events


@producer(
    uses=RECO_JETS_USES | {
        "TTbar.jet_idxs_had",  # indices of the jets the chi2 assignment puts on the hadronic top
        "TTbar.n_bjet_had",  # number of b-tagged jets among them (0 in boosted events)
        "TTbar.bjet_had_{pt,eta,phi,mass}",  # the b-jet assigned to the hadronic top
    },
    produces={"TopWidth.dr_min_bl"},
)
def _dr_min_bl(self: Producer, events: ak.Array, **kwargs) -> ak.Array:
    """
    DeltaR_min(j_b, j_l) = DeltaR between the hadronic b-jet and the closest other jet assigned to
    the hadronic top.

    Only defined in resolved events with a b-tagged hadronic jet (`TTbar.n_bjet_had >= 1`) and at
    least one other hadronic jet. Otherwise EMPTY_FLOAT. Note that the "light" jets are all other
    hadronic jets, not specifically the W jets as in the ATLAS analysis.
    """
    jet = lv_mass(reco_jets(events, self.config_inst.x.ttbar_reco_settings))

    jets_had = jet[events.TTbar.jet_idxs_had]  # jagged: 1-6 jets (resolved), empty (boosted)
    b_had = lv_mass(ak.zip({var: events.TTbar[f"bjet_had_{var}"] for var in ("pt", "eta", "phi", "mass")}))

    # find the b among the hadronic jets (`bjet_had_*` is a copy of its kinematics) and drop it
    dr_to_b = jets_had.delta_r(b_had)
    light_jets = jets_had[dr_to_b >= 0.01]

    dr_min = ak.min(light_jets.delta_r(b_had), axis=1)  # None if no light jets

    # `bjet_had_*` is also filled in boosted events (from a subjet, no b-tag requirement),
    # so require a tagged hadronic b explicitly
    has_b = events.TTbar.n_bjet_had >= 1
    dr_min = ak.where(has_b, ak.fill_none(dr_min, EMPTY_FLOAT), EMPTY_FLOAT)

    events = set_ak_column(events, "TopWidth.dr_min_bl", dr_min)
    return events


@producer(
    uses={_m_lb, _dr_min_bl},
    produces={_m_lb, _dr_min_bl},
)
def top_width_observables(self: Producer, events: ak.Array, **kwargs) -> ak.Array:
    """
    Observables for the top-width template fit. Needs the `TTbar.*` columns of the `uic`
    producer, so run it after `uic` in the same `cf.ProduceColumns` call.
    """
    events = self[_m_lb](events, **kwargs)
    events = self[_dr_min_bl](events, **kwargs)
    return events
