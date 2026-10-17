# Coalescing `tt_semileptonic_2` into the shared repo (Alex's work): where things stand

Analysis date: 2026-10-17. **Read-only survey**: nothing was run, built, merged, fetched or
checked out in any of the three repos while writing this. Everything comes from `git log`,
`git diff`, `diff` and reading code, so every "should" below is a proposal, not a tested change.
Items marked *(unverified)* were inferred from reading, not confirmed.

## 1. The four code lines and how they relate

```
uhh-cms/mttbar  (Johanna Matthiesen's analysis, "mttbar_johanna")
 │
 ├─ origin/master  b9909f4  (2026-02-16)  <-- common ancestor of everything below
 │    │
 │    ├─ shared repo   webberfrog/mttbar   master 402489c   13 commits, Alexander Thielen
 │    │                (Alex and Lautaro now both work here; branch reco_study = b9909f4, no own commits)
 │    │                (this directory, /data/dust/user/lsilberg/columnflow/mttbar)
 │    │
 │    └─ tt_semileptonic_2  (my rewrite; started from a July 2026 clone of master, NOT a git descendant)
 │
 └─ origin/fix/btag_sf  2bf2cb0 (2026-10-13)  64 commits on top of master, all Johanna
      NEITHER the shared repo NOR tt_semileptonic_2 contains any of this.
```

| | Path | Remote | Branch / head | Base | Columnflow pin |
|---|---|---|---|---|---|
| Johanna | `../mttbar_johanna` | `uhh-cms/mttbar` | checked out `fix/btag_sf` @ `2bf2cb0`; `origin/master` = `b9909f4`; local branch `lauti` = `a3b5c95` (mine, early) | n/a | master: v0.3.0-207 (`611d4e6`); fix/btag_sf: v0.3.1-60 (`4c3d443`) |
| Shared repo (Alex's work) | `.` (this dir) | `webberfrog/mttbar` (shared by Alex and Lautaro; earlier this checkout was `lautisilber/mttbar`, a fork of Alex's fork); branches: `master` and `reco_study` (`b9909f4`, identical to Johanna's `master`, nothing added yet) | `master` @ `402489c` | **`b9909f4` = Johanna's `master`** | `611d4e6` (v0.3.0-207) in the tree; submodule gitdir HEAD is `63e1a80` (v0.3.1-89), worktrees empty |
| Mine | `../tt_semileptonic_2` | `lautisilber/tt_semileptonic` | `master` @ `8780e06`, 31 commits, **dirty** | July 2026 snapshot of `mttbar` master, then rewritten | v0.3.1 (`f29ca6f`) |

(`tt_semileptonic_old` also exists in `columnflow/`; not examined.)

**The single most important fact:** Alex branched from Johanna's *old* `master`. Johanna's big
2026-02 → 2026-10 rework (`fix/btag_sf`) is in neither the shared repo nor my `tt_semileptonic_2`. Any coalesced code
therefore has to decide independently what to do about Johanna's new work (section 5).

## 2. What Alex's work (shared repo `master`) adds on top of Johanna's `master`

13 commits, 2026-07-28 → 2026-10-16, 112 files, +31288/-21 (but see the `uic/` duplicate below:
most of the line count is a copy). Commit `b8ce204` is co-authored with Claude; the later
commit messages say "WIP", "bugged", "first try", so treat the physics code as needing review.

His work is a quantum-information / spin-correlation / asymmetry study of the semileptonic ttbar
sample. All of it lives in `mtt/` (the real, imported code), not in `uic/`.

### 2.1 New producer: `mtt/production/ttbar_reco_uic.py` (1024 lines), producer name `uic`
A copy of the chi2 `ttbar` reconstruction, extended. Writes `TTbar.*` columns:
- chi2 reco: `chi2`, `chi2_had`, `chi2_lep`, `jet_idxs_{had,lep}`, `n_jet_{had,lep,sum}`,
  `n_bjet_had`, `top_{had,lep}_energy` (this is really m_T), `cos_theta_star`, `abs_cos_theta_star`
- **charge-asymmetry observable**: `delta_y` (|y_t| − |y_tbar|), `tanh_y` (= tanh(delta_y)); top vs
  antitop identified by lepton charge. Rapidity computed as asinh(p_z/m_T) (a "b-tag and rapidity
  fix", commit `9a1c0dd`). Gen-level `gen_delta_y` / `gen_tanh_y` are written when gen info is
  available.
- **helicity-basis spin observables**: `cos_theta`, `cos_phi`, `cos_phi_tilde`, and
  `lepton_{k,n,r}` / `bjet_{k,n,r}` components, charge-corrected into top-/antitop-side
  versions (`top_lepton_k`, `atop_bjet_r`, ... 12 one-dimensional variables). Uses the new helper
  `lv_nrk` in `mtt/production/util.py` (Bernreuther–Si basis).
- hadronic b-jet assignment for the angular variables (b-tag score ranking; boosted regime uses AK8
  subjets and needs `SubJet.btagUParTAK4B`).
- Also registers its own `add_prod_cats` producer (copy of the one in `ttbar_reco.py`).
- `mtt/production/default.py` now chains `features, category_ids, weights, ttbar, uic`.
- `mtt/production/ttbar_reco_uic_spanet.py` (1011 lines): near-copy of the above, header "Will
  eventually become the SPANet reconstruction to compare to chi^2". **Not registered in `law.cfg`
  and still has the old energy-based rapidity formula** (it lacks the `_rapidity` fix). It also
  defines a producer named `uic`, i.e. the same name as the main one: do not register both.

### 2.2 New plotting layer: `mtt/plotting/` (4 files, ~1850 lines)
| File | What | Use |
|---|---|---|
| `plot_functions.py` | `plot_spin_density_matrix` (P, P̄, C_ij in helicity basis, in the style of CMS-TOP-23-007 / arXiv:2409.11067 Fig. 17/19; direct expectation-value method, not the paper's template fit); `plot_entanglement_summary` (D and D̃ per phase-space region, AN2023_120 Fig. 131 style) | `cf.PlotVariables1D --multi-variable --plot-function ...` |
| `plot_functions_asymmetry.py` | A_C template method of CMS AN-26-039 Sec. 7: symmetric/antisymmetric decomposition of X = tanh(Δ\|y\|), f-template family, gen-weight reweighting; three functions `plot_tanh_y_decomposition`, `plot_tanh_y_f_templates`, `plot_tanh_y_gen_weights` | `cf.PlotVariables1D`/`2D` |
| `plot_functions_2d.py` | `plot_2d_migration` (gen-vs-reco migration matrix) | `cf.PlotVariables2D` |
| `hist_hooks.py` | hist hooks `calculate_asymmetry` (D / D̃ from cos φ sign split) and `stack_entanglement_regions` | `--hist-hooks` |

Wired in through `cfg.x.hist_hooks` / `ana.x.hist_hooks` and `cfg.x.entanglement_regions`
(`mtt/config/run3/uic_mtt_config.py`, `analysis_mtt_uic.py`).

### 2.3 Config changes
- `mtt/config/run3/uic_mtt_config.py` (new, `add_new_config`): `new_mtt_config.py` plus
  `Muon.charge`/`Electron.charge`, AK8 sub-jet columns in `keep_columns`, the hist hooks and
  entanglement regions; imports datasets from `datasets_uic.py`.
- `mtt/config/run3/analysis_mtt_uic.py` (new analysis object) is the `default_analysis` in `law.cfg`.
  Config name used by all his scripts: `run3_mtt_2024_nano_v15_new` (full) or
  `run3_mtt_2024_nano_v15_limited_new`.
- Datasets: `tt_datasets` split into `tt_sl_datasets` / `tt_dl_datasets` / `tt_fh_datasets` and
  matching processes/colours (`tt_sl`, `tt_dl`, `tt_fh`); `w_lnu_{1..4}j_madgraph` datasets
  added. `datasets_uic.py` (858 lines) and `datasets_old.py` are snapshots.
- Categories: `0j/1j/2j/3j` (n jets, group `n_jets`, cut via `cutflow.n_jet`) and four overlapping
  entanglement regions (`ent_pt_lt50`, `ent_mtt_lt400`, `ent_mtt_gt800_acts_lt0p4`,
  `ent_mtt_gt1000_acts_lt0p4`, ids 100_000_001+) in `mtt/config/categories.py` and
  `mtt/production/categories.py`.
- Variables (`mtt/config/variables.py`, +166): `ttbar_mass_1k`, `mtt_reco_5bin`/`mtt_gen_5bin`,
  `delta_y`, `tanh_y`, `tanh_y_18bin`, `gen_tanh_y`, `cos_phi`, `cos_phi_tilde`, `cos_theta`, the
  top/antitop lepton/b-jet helicity components, `n_bjet_had`. `production/features.py` adds `n_bjet`.
- `law.cfg`: `CalibrateEvents/SelectEvents/ReduceEvents/ProduceColumns/...` outputs switched from
  `wlcg` to `local` (the old `wlcg` lines are left as comments).

### 2.4 What he did NOT change
Selection, calibration, lepton/jet/MET logic, weights, triggers are **exactly Johanna's `master`**
(`mtt/selection/default.py` etc. byte-identical except `selection/categories.py` +47 lines for the
n-jet categorizers). Specifically his selection **includes** triggers and the data-stream
`data_trigger_veto`, jet veto map, QCD spikes, JEC/JER via `mtt/calibration`, i.e. all the things
`tt_semileptonic_2` has not ported (triggers) or ported in a restructured way.

### 2.5 Housekeeping problems in the shared repo (matter for the merge)
1. **`uic/` is a verbatim duplicate of `mtt/`.** All 63 `.py` files under `uic/` are byte-identical
   to their `mtt/` counterparts, and every import inside `uic/` is `from mtt....` (96 of them, none
   `from uic`). It is dead weight: `uic_law.cfg` registers `uic.production.*` / `uic.selection.*`
   modules *and* `mtt.*` ones, which would register same-named producers twice *(unverified: not
   run)*. Decide on one package and delete the other. `law.cfg` (the default) only uses `mtt.*`.
2. `uic_law.cfg` is a variant of `law.cfg` selected through `LAW_CONFIG_FILE` in
   `.setups/<name>.sh`; its `[modules]` lists `mtt.tasks` and `default_analysis` points at `uic.*`.
3. `*_old.py` / `*_old` snapshots are scattered through `mtt/` (`datasets_old.py`,
   `variables_old.py`, `new_mtt_config_old.py`, `production/default_old.py`, `selection/default_old.py`).
4. `scripts/sf_scripts/*.py` import `tgs.config.run3.analysis_tgs`, a module that does not exist
   here (copied from another analysis); they cannot run in this repo as they are.
5. `scripts/alex_testing/*.sh` (14 scripts) are the working record of how each plot is produced:
   `law run cf.PlotVariables1D|2D ... --producers category_ids,uic,features,weights,add_prod_cats
   --hist-producer all_weights --plot-function mtt.plotting.plot_functions[_asymmetry].<fn> ...`,
   mostly with `--workflow htcondor` and `--remove-output 0,a,y`.
6. Submodules: both pinned commits are Johanna's `master` ones; the checkout is not set up
   (`modules/*` empty, no `.setups/`). `.gitmodules` uses relative URLs (`../cmsdb.git`,
   `../../columnflow/columnflow.git`) which, on `webberfrog/mttbar`, resolve to
   `webberfrog/cmsdb` (the local git config sets cmsdb to that and columnflow to
   `columnflow/columnflow`) *(whether `webberfrog/cmsdb` exists, and whether it contains the pinned
   commit `3ad8545`, was not checked)*. The pinned cmsdb `3ad8545` is from `fix/data_2024`.
7. Some of his new `mtt/` files carry lint noise (missing blank lines, `#Alex add` comments).

## 3. What `tt_semileptonic_2` has that the shared repo does not

Package `tt_semileptonic/` (7.7k lines), ported selectively from `mtt` in July and then
restructured. State per `AGENTS.md`, `V1.md`, `CHANGES.md` there (read, not re-run). Working through
`cf.ProduceColumns` and `cf.PlotVariables1D/2D/Cutflow`; `cf.CreateHistograms` was "next".

- **Cleaner selection architecture**: selection parameters as `dataclasses`
  (`config/selection_params.py`), config-driven lepton definition as a producer
  (`production/lepton.py::lepton_definition`), small sub-selectors in `selection/{leptons,jets,
  fatjets,met,lepton_jet_2d}.py`, `cutflow_features`, `qcd_spikes`, golden JSON, jet veto map,
  tight jet/fat-jet ID via columnflow producers.
- **Calibration**: `jet_lepton_cleaner` + JEC/JER (nominal only), ported from `mtt/calibration/jets.py`.
- **Weights chain** (`production/{weights,btag,gen_top,default}.py`): electron/muon SF, pileup,
  normalization (all 29 MC datasets' cmsdb cross sections confirmed populated at 13.6 TeV), top-pt
  reweighting, and a **real 2024 UParTAK4_kinfit shape b-tag SF** (`upart_btag_weights`, not yet in
  `cfg.x.event_weights`). Uses `--hist-producer all_weights`.
- **Data-driven QCD study** (written, **never run**): "shadow" datasets `l2dfail_<data dataset>`
  (muon streams only) keep only events that *fail* the lepton-jet 2D cut, so they can serve as a
  QCD template (see `QCD_DATA_DRIVEN.md` there). Plus `pt_low`/`pt_high` regime categories and
  chi2/cos θ* categories (also wired but not yet run).
- **Charge asymmetry**: `TTbar.delta_abs_y` (= q_lep·(|y_lep| − |y_had|)) and `tanh_delta_y` in
  `production/ttbar_reco.py`; `plotting/charge_asymmetry.py::plot_charge_asymmetry` (A_C in five
  m(ttbar) bins from a 2D histogram). Confirmed running on `tt_sl_powheg`; **this overlaps with
  Alex's `delta_y`/`tanh_y` + `plot_functions_asymmetry.py`, which is more elaborate**.
- **Infrastructure fixes**: XRootD `atexit` hang worked around by reading from the DESY dCache
  mount (`ISSUES.md`), `cf.PlotCutflow` wrapper for the columnflow PR #783 regression
  (`plotting/cutflow.py`), `cf.ReduceEvents` chunk-size override to avoid OOM, `law.cfg` details.
- **Documentation**: `AGENTS.md`, `SELECTION.md`, `V1.md`, `CHANGES.md` (909 lines),
  `MTTBAR_UPDATES.md` (my own 2026-10-15 analysis of Johanna's `fix/btag_sf`, incl. a ranked port
  plan), `ISSUES.md`.
- **Not in it**: triggers (+ data-stream veto), MET-φ, muon TuneP, e/μ scale-and-smear, gen-level
  ttbar matching (`GenPart.hasFlags` is unavailable post-`ReduceEvents`), ML, inference,
  spin-correlation / entanglement variables.

### 3.1 Uncommitted work in `tt_semileptonic_2` (at risk, since the repo is "deprecated")
`git status` there: 11 modified tracked files (`AGENTS.md`, `CHANGES.md`, `categorization/default.py`,
`config/{categories,datasets,defaults_and_groups,variables}_helper.py`,
`config/run3/config_helper.py`, `production/{lepton,ttbar_reco}.py`, `selection/default.py`) and
untracked `MTTBAR_UPDATES.md`, `QCD_DATA_DRIVEN.md`, `V1.md`,
`tt_semileptonic/plotting/charge_asymmetry.py` (and a stray `typescript` file). **The shadow-dataset
QCD work, the charge-asymmetry plot and three doc files exist only in the working tree, never
committed or pushed.** Commit them before archiving that repo.

## 4. Side-by-side

| Area | Alex (`mtt/`, = Johanna master + UIC) | Mine (`tt_semileptonic/`) | Johanna `fix/btag_sf` |
|---|---|---|---|
| Package / structure | `mtt/` (+ dead duplicate `uic/`) | `tt_semileptonic/`, cleaner, dataclass params | `mtt/`, new `ttbar_res_sel` + cleanup/stats/hists modules |
| Columnflow | pin v0.3.0-207 | v0.3.1 | v0.3.1-60 |
| Selection | master `default` | own rewrite, no triggers | `ttbar_res_sel`, triggers, N-1 steps, JEC/JER shifts |
| Triggers + data stream veto | yes (master) | **no** | yes, Run-3 trigger config updated |
| Calibration | master | JEC/JER nominal port | rewritten: TuneP, subjet JEC/JER, msoftdrop recompute, 2024 JEC V5 / JER JRV2 |
| Electron eta | master (track eta) | `eta+deltaEtaSC` | SC eta |
| b-tag SF | master weights | real shape SF (unused in plots) | fixed-WP from merged file + normalized weights |
| Hist weights | `all_weights` | `all_weights` | custom hist producers |
| chi2 reco | `ttbar` + `uic` | ported `ttbar_reco` | unchanged algorithm |
| A_C | `tanh_y`, template-method plots | `delta_abs_y`, simple A_C plot | n/a |
| Spin / entanglement (D, D̃, C_ij, P) | **yes** | no | no |
| Gen-level migration / templates | yes (needs gen info) | no (`GenPart.hasFlags` issue) | n/a |
| QCD from 2D-fail data | no | designed, never run | no (N-1 `all_but_2d_iso` steps exist) |
| n-jet categories | `0j..3j` | no | `0j..6jp`, `0bj..` |
| Years | 2024 (config also lists older) | 2024 | 2024, 2025 |
| Docs for agents | none (this file is the first) | extensive | none |

## 5. Suggested path (proposals; decisions are yours)

1. **Freeze `tt_semileptonic_2` first.** Commit and push its uncommitted work (section 3.1).
2. **Pick the code base to keep.** The physics deliverable (spin density matrix, D/D̃, A_C
   templates, migration) is only in the shared repo and is largely self-contained *additive* code:
   `ttbar_reco_uic.py`, `lv_nrk` in `production/util.py`, `mtt/plotting/*`, the entanglement
   categories, variables, `cfg.x.entanglement_regions`. The structural and infrastructure work
   (selection rewrite, weights, QCD shadow datasets, docs, XRootD workaround) is only in mine.
   Either direction is feasible; porting Alex's additions into `tt_semileptonic/` looks like the
   smaller job and keeps the cleaner structure, but it means maintaining one more divergence from
   Johanna. Keeping Alex's tree means adopting `mtt/`'s older selection and then deciding on
   Johanna's `fix/btag_sf`.
3. **Porting `uic` into `tt_semileptonic` needs these (check each, *unverified*)**: it calls
   `choose_lepton` (mine builds `Lepton` in selection instead, see `production/lepton.py::
   lepton_producer`), expects the `BJet` and `FatJetTopTagDeltaRLepton` collections (both exist in
   mine), `SubJet.{pt,eta,phi,mass,btagUParTAK4B}` and `FatJetTopTagDeltaRLepton.{subJetIdx1,2}`
   (not in my `keep_columns`), `Muon.charge`/`Electron.charge` (mine carries `Lepton.charge`),
   `cfg.x.ttbar_reco_settings` incl. `max_chunk_size`, `cfg.x.jet_selection.ak4.btagger.column`
   (mine: dataclass `sel_params.btagger.column`), and `mtt.util.iter_chunks`,
   `mtt.profiling_tools.Profiler`.
4. **Decide on the A_C observable once**: unify `TTbar.delta_abs_y`/`tanh_delta_y` (mine) with
   `TTbar.delta_y`/`tanh_y` (Alex's, with the m_T rapidity fix). Mine already uses the m_T-based
   `rapidity()` too, so the two should agree numerically *(unverified)*.
5. **Johanna's `fix/btag_sf`**: independent of 2–4. `MTTBAR_UPDATES.md` (in `tt_semileptonic_2`)
   has an item-by-item port plan; the shared repo would need all of it (he has none), mine needs it
   minus the items already done there.
6. **Clean up Alex's tree before merging**: drop `uic/` (or `mtt/`), the `*_old` files, the
   `tgs`-importing scripts; fix the `uic_law.cfg` doubled modules; give `ttbar_reco_uic_spanet.py`
   a distinct producer name or leave it out of the cfg.
7. **Shared tooling to carry over**: `../tt_semileptonic_2/AGENTS.md` (`--remove-output` recipe,
   framework gotchas, XRootD note, `kill_on_str`) is mostly framework-generic and worth keeping.

## 6. What was not checked
- Whether Alex's code currently runs end to end (his own commits say "bugged"/"WIP"); whether
  `lautisilber/cmsdb` exists; whether Johanna's remote has moved since 2026-10-15 (no `git fetch`).
- Whether Alex's `uic` physics is correct (not reviewed, only read for structure; one commit is
  AI-assisted).
- Whether `tt_semileptonic_2` still runs on top of columnflow v0.3.1 unchanged.
- `tt_semileptonic_old` and the `local_datasets/` directory.
