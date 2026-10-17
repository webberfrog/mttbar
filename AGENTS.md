# AGENTS.md — mttbar (shared repo of Alex and Lautaro, UIC / spin-correlation study)

HEP analysis (CMS, SM tt → semileptonic) built on **columnflow** (law + order). This repo is
`webberfrog/mttbar` (`git@github.com:webberfrog/mttbar.git`), a fork of Johanna Matthiesen's
`uhh-cms/mttbar`. Alex (Alexander Thielen) and Lautaro (`lsilberg`) now **work in this same
repo** (Lautaro no longer has a separate fork). Alex's addition is a study of the ttbar charge
asymmetry A_C and of spin correlation / entanglement (D, D̃, polarisation, C_ij); the code base
is called "UIC" here.

**Purpose of this checkout:** Lautaro's older `../tt_semileptonic_2` (now deprecated) is being
coalesced into this repo. The full state comparison is in [COALESCING.md](COALESCING.md). Read it
before changing structure. Short version below. Since the repo is shared, the sibling
directories referenced below (`../tt_semileptonic_2`, `../mttbar_johanna`, ...) exist only in
Lautaro's `/data/dust/user/lsilberg/columnflow/`; coordinate with Alex before pushing to
`master` or removing shared code (e.g. `uic/`).

Written from the real code on 2026-10-17; nothing was run. If this file disagrees with the code,
trust the code and fix this file.

---

## Where the repos are

| What | Path | Remote | State |
|---|---|---|---|
| This repo (shared) | `/data/dust/user/lsilberg/columnflow/mttbar` | `webberfrog/mttbar` | `master` @ `402489c` = 13 commits by Alex on top of Johanna's `master` `b9909f4`; plus branch `origin/reco_study` @ `b9909f4` (= Johanna's `master`, **no commits of its own yet**: a clean base to start from) |
| Johanna's analysis | `../mttbar_johanna` | `uhh-cms/mttbar` | checked out `fix/btag_sf` @ `2bf2cb0`; `origin/master` = `b9909f4`; local branch `lauti` = my early work |
| Mine (deprecated) | `../tt_semileptonic_2` | `lautisilber/tt_semileptonic` | `master` @ `8780e06`, **plus uncommitted work** (shadow-dataset QCD, charge-asymmetry plot, docs) |
| Also present | `../tt_semileptonic_old`, `../local_datasets` | | not examined |

Key fact: Alex branched from Johanna's **old `master`** (2026-02-16). Johanna's 64-commit rework
`fix/btag_sf` (new `ttbar_res_sel` selection, triggers config, TuneP, new JEC/JER/b-tag SF,
hist producers, 2025 support; targets columnflow v0.3.1-60) is in **neither** this repo nor
`tt_semileptonic_2`. `../tt_semileptonic_2/MTTBAR_UPDATES.md` analyses it and has a port plan.

---

## Setup and running

**`law run` commands are run by the user, not by Claude.** They take minutes to hours, and
Claude's command timeout would kill them before they finish. Claude should write the exact
command (and say what it expects to see), hand it to the user, and wait for the output. Quick
read-only commands (`law index`, `law run ... --print-status`, `law run ... --print-deps`,
`law --help`) are fine to run directly. Never start a `law run` that does real work from a Claude
session, including in the background.

Set up in Lautaro's checkout (`.setups/dev.sh`; `source setup.sh dev` completed and
`law index --verbose` works, 2026-10-17). Submodules pinned at: columnflow `611d4e6` = v0.3.0-207,
cmsdb `3ad8545`, plus columnflow's own law and order.

```bash
cd /data/dust/user/lsilberg/columnflow/mttbar
git config submodule.modules/cmsdb.url https://github.com/uhh-cms/cmsdb.git   # see note below
git submodule update --init
source setup.sh dev              # setup name is arbitrary, stored in .setups/dev.sh; needs a fresh shell
```

- **cmsdb URL:** `.gitmodules` uses the relative URL `../cmsdb.git`, which resolves to
  `webberfrog/cmsdb`, a repo that does not exist. A fresh clone must override it locally with the
  `git config` line above (public repo, no key needed) until `.gitmodules` is changed to an
  absolute URL.
- **Harmless setup noise:** `source setup.sh` prints two `fatal: empty string is not a valid
  pathspec` lines. `setup.sh` calls `cf_init_submodule` with one argument instead of two (same in
  Johanna's repo); the submodules are already initialised, so nothing is lost.
- `LAW_CONFIG_FILE` defaults to `law.cfg` (uses `mtt.*`). **`uic_law.cfg` is the config for working
  in `uic/`** (uses `uic.*` for analysis/production/selection). Switch in a shell that has run
  `source setup.sh dev` with `export LAW_CONFIG_FILE=$MTT_BASE/uic_law.cfg`, then
  `law index --verbose` (re-run it after switching back to `law.cfg`). Verified 2026-10-18: the
  full smoke chain below runs under `uic_law.cfg` with `--version test_uic`, no duplicate-name clash.
- **Working package decision (Lautaro, branch `lauti`):** new work goes into `uic/` as an
  *overlay*; `mtt/` is left as it is so it stays close to Johanna's repo for future pulls (Z′ code
  is deliberately kept for the same reason). `uic/` files still `from mtt....` import what they do
  not override, so a change in `uic/` only takes effect where the config chain imports `uic.*`:
  `uic/config/run3/analysis_mtt_uic.py` and `uic/config/run3/uic_mtt_config.py` import
  `uic.config.run3.uic_mtt_config` / `uic.config.variables`; other `uic/` modules are still shadows
  of `mtt/` (see "Known problems" #1).
- Task namespace `cf`. Default analysis: `mtt.config.run3.analysis_mtt_uic.analysis_mtt_new`.
  Configs: `run3_mtt_2024_nano_v15_new` (full) and `run3_mtt_2024_nano_v15_limited_new`
  (file-limited, default). Default dataset `tt_sl_powheg`.
- Outputs for Calibrate/Select/Reduce/ProduceColumns are **`local`** in `law.cfg` (Alex switched
  them from `wlcg`).
- Needs a valid VOMS proxy for remote input data: `voms-proxy-init -voms cms -rfc -valid 192:00`.
- `--calibrator` (singular) up to `CalibrateEvents`, `--calibrators` (plural) from `SelectEvents`;
  `--producer` singular for `cf.ProduceColumns`, `--producers` plural from `cf.CreateHistograms` on.
- `--remove-output depth,mode,run` forces regeneration (`0,a,y` = this task only, all, run it);
  see `../tt_semileptonic_2/AGENTS.md` for the full explanation.
- Known framework issue (from my other repo): the columnar sandbox's XRootD client can hang at
  process exit after a `root://` read; `tt_semileptonic_2` avoids it by reading from the dCache
  mount first (`[outputs] lfn_sources`). Check whether this applies here if jobs never exit.
- Alex's scripts mostly use `--workflow htcondor`. Remember: the user runs `law run`, see the top of
  this section.

### Verified smoke-test chain (Lautaro, 2026-10-18, branch `lauti`, columnflow v0.3.0-207)

All four ran successfully on `tt_sl_powheg`, `--version test_sel`, in the 2-file limited config.
Defaults of the config are calibrator `skip_jecunc`, selector `default`, reducer `default`
(`mtt/config/defaults_and_groups.py:23-25`); they are spelled out here. The user runs these.

```bash
common="--version test_sel --config run3_mtt_2024_nano_v15_limited_new --dataset tt_sl_powheg"

law run cf.SelectEvents  $common --calibrators skip_jecunc --selector default --branch 0
law run cf.ReduceEvents  $common --calibrators skip_jecunc --selector default --reducer default --branch 0
law run cf.ProduceColumns $common --calibrators skip_jecunc --selector default --reducer default \
    --producer default --branch 0          # runs ttbar + uic (slow, memory heavy)

law run cf.PlotVariables1D --version test_sel --config run3_mtt_2024_nano_v15_limited_new \
    --datasets tt_sl_powheg --processes tt_sl --calibrators skip_jecunc --selector default \
    --reducer default --producers default --hist-producer all_weights --categories incl \
    --variables ttbar_mass,tanh_y --cms-label wip --file-types png
```

Notes: `--branch 0` still pulls in the second file as a dependency for the merged steps
(`ProduceColumns` needs all `SelectEvents` stats and merged reduced events). `--producers default`
reuses the cached `ProduceColumns` output; Alex's chain `category_ids,uic,features,weights,add_prod_cats`
runs the producers separately and is needed for categories such as `1m__0t__chi2pass`. Not yet
tested: the asymmetry / spin-density / entanglement plot functions below.

How Alex runs things: `scripts/alex_testing/*.sh` (14 scripts, each is a working example), e.g.

```bash
law run cf.PlotVariables2D --version uic_v4_1 --config run3_mtt_2024_nano_v15_limited_new \
    --datasets tt_sl_powheg --processes tt_sl --categories incl,1m__0t,1m__1t,1m__chi2pass \
    --producers category_ids,uic,features,weights,add_prod_cats --hist-producer all_weights \
    --variables gen_tanh_y-tanh_y_18bin \
    --plot-function mtt.plotting.plot_functions_asymmetry.plot_tanh_y_f_templates \
    --cms-label wip --file-types png
```

Scripts: `Ac_*` (A_C decomposition / templates / weights), `uic_test_v*` (reco variables),
`uic_test_2D_D` (D vs 2 variables), `uic_test_migration`, `uic_test_spin_density_matrix[_test]`.

---

## Layout

| Path | What |
|---|---|
| `mtt/` | **the code that actually runs** (Johanna's `master` + Alex's additions) |
| `mtt/production/ttbar_reco.py` | chi2 ttbar reco, producer `ttbar` (Johanna's, unchanged) |
| `mtt/production/ttbar_reco_uic.py` | **Alex's** producer `uic`: chi2 reco + `delta_y`/`tanh_y` + helicity-basis spin observables (`cos_theta`, `cos_phi`, `cos_phi_tilde`, `{top,atop}_{lepton,bjet}_{k,n,r}`), gen-level `gen_tanh_y` |
| `mtt/production/ttbar_reco_uic_spanet.py` | near-copy for a future SPANet comparison; **not registered**; same producer name `uic` (do not load both); has the old energy-based rapidity |
| `mtt/production/default.py` | chain: `features, category_ids, weights, ttbar, uic` |
| `mtt/production/util.py` | `lv_nrk` (helicity basis k, n, r) added by Alex |
| `mtt/plotting/` | `plot_functions.py` (spin density matrix, entanglement summary), `plot_functions_asymmetry.py` (A_C template method, CMS AN-26-039), `plot_functions_2d.py` (migration), `hist_hooks.py` (`calculate_asymmetry`, `stack_entanglement_regions`) |
| `mtt/config/run3/uic_mtt_config.py` | config builder for UIC (adds charge + subjet columns, hist hooks, `cfg.x.entanglement_regions`) |
| `mtt/config/run3/analysis_mtt_uic.py` | analysis object (the `default_analysis`) |
| `mtt/config/{categories,variables,datasets*}.py` | n-jet categories (`0j..3j`), entanglement-region categories, QIS variables, `tt_sl/dl/fh` split |
| `mtt/selection/`, `mtt/calibration/` | **Johanna's old `master`, unchanged** (includes triggers, `data_trigger_veto`, JEC/JER, jet veto map, QCD spikes, 2D lepton-jet cut) |
| `mtt/ml/`, `mtt/inference/` | Johanna's ML / limit code, not part of the UIC work |
| `uic/` | **dead duplicate of `mtt/`** (all 63 `.py` files byte-identical, all imports go to `mtt.*`) |
| `scripts/alex_testing/` | Alex's run scripts; `scripts/selection_scripts/` jet/cutflow studies; `scripts/sf_scripts/` SF calculation |
| `workflow_scripts/` | Johanna's workflow templates (gitignored except what is tracked) |
| `law.cfg`, `uic_law.cfg` | law configs (see above) |

Producers are registered by import: `mtt.production.default` imports `ttbar_reco_uic`, which is
why `--producers ...,uic,...` works although `law.cfg` does not list that module.

---

## Known problems (do before / during the merge)

1. **`uic/` duplicates `mtt/`**. `uic_law.cfg` loads `uic.production.*`/`uic.selection.*` *and*
   `mtt.*` modules, so same-named producers/selectors would be registered twice (unverified).
   Keep one package, delete the other.
2. `*_old` files in `mtt/` (`datasets_old.py`, `variables_old.py`, `new_mtt_config_old.py`,
   `production/default_old.py`, `selection/default_old.py`) are snapshots, not used.
3. `scripts/sf_scripts/*.py` import `tgs.config.run3.analysis_tgs`, which does not exist here.
4. Status words from Alex's own commits: "QIS variables plot (bugged)", "asymmetry hist_hook
   (WIP)", "first try". Commit `b8ce204` is co-authored with Claude. Physics code has not been
   independently reviewed.
5. Gen-level variables (`gen_tanh_y`, `mtt_gen_5bin`) and the migration / template plots need gen
   info at `cf.ProduceColumns` time; in `tt_semileptonic_2` `GenPart.hasFlags` was unavailable
   after `cf.ReduceEvents`. Alex's producer attaches `GenPart` behavior itself; whether that
   works on the reduced files is unverified.
6. Missing from this repo (exist only in Johanna's `fix/btag_sf`): trigger config update, TuneP,
   electron SC-eta veto, GloParT WP update, JEC V5 / JER JRV2, fixed-WP b-tag SF, custom hist
   producers, neutrino sanity tolerance 4e-3 (the 2e-3 in this tree can crash on a data event),
   2025 support. Details in `../tt_semileptonic_2/MTTBAR_UPDATES.md`.
7. The submodule worktrees are empty and the local `.git` has columnflow HEAD at `63e1a80`
   (v0.3.1-89) while the tree pins `611d4e6`. Make sure which columnflow version the code is meant
   for before running (Alex's plotting uses `--hist-hooks`, `--multi-variable`, `--cms-label`).

---

## How this relates to `tt_semileptonic_2` (what to keep from where)

- **Only here**: spin-density-matrix / entanglement (D, D̃) / polarisation machinery, A_C
  template-method plots, migration plot, hist hooks, entanglement-region categories, `uic`
  producer, SPANet prep, trigger logic (inherited from Johanna's `master`).
- **Only in `tt_semileptonic_2`** (not committed in part, see COALESCING.md §3.1): dataclass-based
  selection params and cleaner selector split, weights chain with a real shape b-tag SF, QCD
  data-driven "shadow dataset" design (never run), simple A_C plot (`delta_abs_y`), `PlotCutflow`
  wrapper, `ReduceEvents` chunk-size override, XRootD workaround, extensive docs.
- **Overlap**: chi2 `ttbar_reco`, lepton charge in the `Lepton` column, the charge-asymmetry
  observable (two implementations; both use the m_T-based rapidity).
- Working notes carried over from `tt_semileptonic_2` that apply to any columnflow code here:
  `category_ids` runs the categorizer for *every* leaf category (a categorizer reading a
  column that is not produced yet breaks `cf.SelectEvents`); new categories do not apply
  retroactively to a cached `cf.SelectEvents` output for the same `--version`; `Jet`/`Muon`
  collections need the full `{pt,eta,phi,mass}` in `uses`; `--processes` takes process names
  (`tt_sl`), not dataset names (`tt_sl_powheg`).

---

## Conventions

- **Change files only with the Edit and Write tools.** Never modify a file through Bash: no
  `python`/`python3` scripts or heredocs, `sed -i`, `awk`, `perl -i`, `cat > file`, `echo >`,
  `tee`, or `git apply`/`patch` on working files. Edit and Write show the user a reviewable diff;
  a script that rewrites a file silently does not, and the user cannot see what changed. Use Edit
  for changes to an existing file (Read it first), Write for new files or full rewrites. If an
  edit is large or repetitive (many files), still use Edit/Write per file and say what changes.
  Bash is for reading, searching and running commands, not for writing file contents.
- Reference code as `path:line`. Match the surrounding style; Alex's files use `#Alex add`
  comments and uneven blank lines, so do not "fix" style in unrelated hunks while merging.
- Anything in calibration/selection needs a fresh `--version` and a rerun from
  `cf.CalibrateEvents`/`cf.SelectEvents`; production-only changes need `cf.ProduceColumns` onward.
- Do not edit `../mttbar_johanna` or `../tt_semileptonic_2` while coalescing without being asked;
  both hold work (the latter uncommitted) that exists nowhere else.
