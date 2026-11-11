# Top-quark width measurement: progress

Status as of 2026-11-11, branch `top_width`. The method follows ATLAS, Eur. Phys. J. C 78 (2018) 129
([ATLAS_top_width_measurement_2018.pdf](ATLAS_top_width_measurement_2018.pdf)).

**Current state:** the two fit observables are implemented and produced on `tt_sl_powheg`. The m_lb
shape looks right, but the jet paired with the lepton is probably often not the b. That should be
quantified before templates are built. No width templates or fit exist yet.

## Method in short

1. Reconstruct two observables: **m_lb** (lepton + b-jet of the leptonic top) and **ΔR_min(j_b, j_l)**
   (hadronic b-jet to the closest light jet of the hadronic top).
2. Build one tt̄ template per Γt hypothesis by reweighting a single MC sample with the per-event ratio
   of Breit–Wigner functions, using the gen masses of the top and antitop.
3. Fit the templates to data with a binned likelihood, in regions split by lepton flavour, b-tag
   multiplicity and jet |η|. The signal normalisation floats; the backgrounds float within constraints.
4. Scan Γt and take the minimum of a parabola through −2 ln L.

## What is implemented

Everything works under `uic_law.cfg` only; `law.cfg` does not load these modules.

| File | Change |
|---|---|
| [uic/production/reco_jets.py](uic/production/reco_jets.py) | New shared `reco_jets()`: the jet list used by the reconstruction. |
| [uic/production/top_width_observables.py](uic/production/top_width_observables.py) | New producer `top_width_observables`, writing `TopWidth.mlb`, `TopWidth.lep_jet_is_b`, `TopWidth.dr_min_bl`. |
| [uic/production/ttbar_reco_uic.py](uic/production/ttbar_reco_uic.py) | Jet selection now calls `reco_jets()`. |
| [uic/production/default.py](uic/production/default.py) | Imports `uic` from `uic/` instead of `mtt/`; runs `top_width_observables` after `uic`. |
| [uic/config/run3/uic_config.py](uic/config/run3/uic_config.py) | New setting `ttbar_reco_settings.jet_topjet_min_dr = 1.2`. |
| [uic/config/variables.py](uic/config/variables.py) | New variables `mlb` (40 bins, 0–200 GeV) and `dr_min_bl` (28 bins, 0.4–3.2). |

Definitions, with `EMPTY_FLOAT` where undefined:

- `TopWidth.mlb`: filled only when `TTbar.n_jet_lep == 1`. It is purely reco-level.
- `TopWidth.lep_jet_is_b`: whether that jet matches a jet in `BJet`.
- `TopWidth.dr_min_bl`: filled only with `TTbar.n_bjet_had >= 1` and at least one other hadronic jet.
  The "light" jets are all other hadronic jets, not specifically the W jets as in ATLAS.

`TTbar.jet_idxs_lep` and `TTbar.jet_idxs_had` are positions in the `reco_jets()` list, not in
`events.Jet`, so they only make sense with a list obtained from that function.

### Checks done

- The new `reco_jets()` is bit-identical to the old inline selection on 239,742 real events (102
  reduced-event files, data and QCD, including 973 boosted events). The old and new `uic` producer were
  not compared end to end.
- `mlb` and `dr_min_bl` match hand-computed values on three toy events.

## First result

`cf.PlotVariables1D`, `--version tw_v1`, config `run3_mtt_2024_nano_v15_limited_new`, dataset
`tt_sl_powheg`, category `incl`. m_lb is a smooth peak at about 100 GeV, similar to ATLAS Fig. 4a.
The `dr_min_bl` plot was produced but has not been reviewed.

Numbers from the `ProduceColumns` output (63,097 events, unweighted):

| Quantity | Value |
|---|---|
| `mlb` defined | 98.4 % |
| `mlb` median / mean | 100.8 / 105.8 GeV |
| Above the ~153 GeV kinematic limit | 10.0 % (b-tagged jet 6.7 %, untagged 13.3 %) |
| Outside the plotted range (< 30 / > 180 GeV) | 0.8 % / 5.2 % |
| Leptonic jet b-tagged | 50.8 % |
| `dr_min_bl` defined | 62.1 % |

## Open issues

1. **Assignment purity (most important).** Only 50.8 % of the jets paired with the lepton are b-tagged,
   while a mostly correct assignment should approach the b-tagging efficiency. The chi2 uses masses only,
   no b-tagging. ATLAS used b-tagging in the assignment and got the leptonic b right 65–75 % of the time.
   This is indirect evidence: the purity has not been measured against gen.
2. **`dr_min_bl` loses 38 % of events**, mostly events with no b-tagged jet on the hadronic side. This is
   probably the same assignment problem.
3. **Gen-level precision is unchecked.** The reweighting needs `GenPart.mass` of the tops to be resolved
   well below 1 GeV in NanoAOD. The sample's true m_t and Γ₀ must also be read from the generator settings.

## Next steps

1. Measure the assignment purity: how often the chosen jet matches the gen b of the leptonic top.
2. Depending on that result, either require `TopWidth.lep_jet_is_b` in a category (costs about half the
   events), or add b-tagging to the assignment as a separate option. The latter must not change the
   default combinatorics, because Alex's observables depend on it.
3. Write the width-weight producer: one Breit–Wigner reweighting column per Γt, normalised before selection.
4. Add the categories: e/μ × 1b/≥2b (`1b`/`2b` are commented out in `uic/config/categories.py`) × jet |η|.
5. Fit: first a standalone Python fit on the histograms, later combine with profiled systematics.
6. Validate with reweighting closure, pull and linearity toys, and an alternative-width sample if one exists.

Physics caveats from the paper: Γt is degenerate with m_t (a 0.5 GeV shift in m_t moves Γt by up to about
0.2 GeV), and off-shell and tt̄/Wt interference effects are not modelled (ATLAS cross-checked with
m_lb < 150 GeV).
