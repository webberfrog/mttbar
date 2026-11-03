# AGENTS.md — mttbar (shared repo of Alex and Lautaro, UIC / spin-correlation study)

HEP analysis (CMS, SM tt → semileptonic) built on **columnflow** (law + order). This repo is
`webberfrog/mttbar` (`git@github.com:webberfrog/mttbar.git`), a fork of Johanna Matthiesen's
`uhh-cms/mttbar`. Alex (Alexander Thielen) and Lautaro (`lsilberg`) now **work in this same
repo** (Lautaro no longer has a separate fork). Alex's addition is a study of the ttbar charge
asymmetry A_C and of spin correlation / entanglement (D, D̃, polarisation, C_ij); the code base
is called "UIC" here.

**This is Lautaro's active repo.** The older `../tt_semileptonic_2` is deprecated; what is still
useful from it is being brought over. The comparison is in [COALESCING.md](COALESCING.md) (written
2026-10-17: it predates Alex's `uic/` restructuring below and calls `uic/` a "dead duplicate").
Since the repo is shared, the sibling directories referenced below (`../tt_semileptonic_2`,
`../mttbar_johanna`, ...) exist only in Lautaro's `/data/dust/user/lsilberg/columnflow/`; coordinate
with Alex before pushing to `master` or removing shared code (e.g. `uic/`).

Checked against the code on 2026-11-03: branch `lauti` @ `03169e5`, `origin/master` @ `6612a18`.
Unless a line says otherwise, this file describes the `lauti` tree. Module loading was tested with
Python under both law configs; no `law run` was repeated, so the smoke chain's date below still
stands. If this file disagrees with the code, trust the code and fix this file.

---

## Where the repos are

| What | Path | Remote | State |
|---|---|---|---|
| This repo (shared) | `/data/dust/user/lsilberg/columnflow/mttbar` | `webberfrog/mttbar` | working branch `lauti`; `origin/master` @ `6612a18`; `origin/reco_study` @ `b9909f4` (= Johanna's `master`, **no commits of its own yet**: a clean base to start from) |
| Johanna's analysis | `../mttbar_johanna` | `uhh-cms/mttbar` | checked out `fix/btag_sf` @ `2bf2cb0`; `origin/master` = `b9909f4`; local branch `lauti` = my early work |
| Mine (deprecated) | `../tt_semileptonic_2` | `lautisilber/tt_semileptonic` | `master` @ `8780e06`, 1 commit ahead of its `origin/master`, **plus uncommitted work** (shadow-dataset QCD, charge-asymmetry plot, docs) |
| Also present | `../tt_semileptonic_old`, `../local_datasets` | | not examined |

Key fact: Alex branched from Johanna's **old `master`** (2026-02-16). Johanna's 64-commit rework
`fix/btag_sf` (new `ttbar_res_sel` selection, triggers config, TuneP, new JEC/JER/b-tag SF,
hist producers, 2025 support; targets columnflow v0.3.1-60) is in **neither** this repo nor
`tt_semileptonic_2`. `../tt_semileptonic_2/MTTBAR_UPDATES.md` analyses it and has a port plan.

### `lauti` is behind `master`

`lauti` = `402489c` plus one docs commit (`AGENTS.md`, `COALESCING.md`, which exist only on this
branch). `402489c` is where it forked from `master`, which has since gained three of Alex's
commits (`73f5fea`, `392e1dc`, `6612a18`, 2026-10-21 to 28), **not merged here**:

- `README.md` is now a real guide (setup, structure, scripts, tips, WIP/TODO list). Read it with
  `git show origin/master:README.md`; the copy on `lauti` is the old stub. It is the place for the
  task list, so that list is not repeated here.
- `uic/config/run3/analysis_mtt_uic.py` → `analysis_uic.py` and `uic_mtt_config.py` → `uic_config.py`;
  `uic_law.cfg` points at the new name, and the `uic_config.py` imports go to `uic.config.*` and
  `uic.plotting.hist_hooks`. So on `master`, the `uic/` config chain is real (see below).
- `uic/calibration/` and `uic/reduction/` are removed (`mtt/` is used for those).
- New `scripts/alex_testing/validation_limited.sh` (data + all MC kinematics, version `uic_v5`).

Whether the `master` tree runs here is **untested**. Expect one problem:
`uic/config/run3/uic_config.py` on `master` hardcodes
`/data/dust/user/athielen/mttbar_2024/mttbar/mtt/config/run3/jec_sources.yaml`. It is currently
readable from this account, but it is Alex's private copy (the repo's own is
`mtt/config/run3/jec_sources.yaml`), so it should go back to a repo path.

---

## Setup and running

**`law run` commands are run by the user, not by Claude.** They take minutes to hours, and
Claude's command timeout would kill them before they finish. Claude should write the exact
command (and say what it expects to see), hand it to the user, and wait for the output. Quick
read-only commands (`law index`, `law run ... --print-status`, `law run ... --print-deps`,
`law --help`) are fine to run directly. Never start a `law run` that does real work from a Claude
session, including in the background.

Set up in Lautaro's checkout (`.setups/dev.sh`). Submodules are populated and at their pins:
columnflow `611d4e6` = v0.3.0-207, cmsdb `3ad8545`, plus columnflow's own law and order. Alex's
plotting options (`--hist-hooks`, `--multi-variable`, `--cms-label`) all exist at this pin.

```bash
cd /data/dust/user/lsilberg/columnflow/mttbar
git config submodule.modules/cmsdb.url https://github.com/uhh-cms/cmsdb.git   # see note below
git submodule update --init
source setup.sh dev              # setup name is arbitrary, stored in .setups/dev.sh; needs a fresh shell
```

- **cmsdb URL:** `.gitmodules` uses the relative URL `../cmsdb.git`, which resolves to
  `webberfrog/cmsdb`, a repo that does not exist (confirmed: "Repository not found"; also on
  `master`). A fresh clone must override it locally with the `git config` line above (public repo,
  no key needed) until `.gitmodules` is changed to an absolute URL. The `git clone --recursive` in
  `master`'s README fails on this.
- **Harmless setup noise:** `source setup.sh` prints two `fatal: empty string is not a valid
  pathspec` lines. `setup.sh:141` calls `cf_init_submodule` with one argument instead of two (same
  in Johanna's repo); the submodules are already initialised, so nothing is lost.
- `LAW_CONFIG_FILE` defaults to `law.cfg` (uses `mtt.*`). **`uic_law.cfg` is the config for working
  in `uic/`** (uses `uic.*` for analysis/production/selection). Switch in a shell that has run
  `source setup.sh dev` with `export LAW_CONFIG_FILE=$MTT_BASE/uic_law.cfg`, or permanently in the
  gitignored `.setups/dev.sh`, then `law index --verbose` (re-run it after switching back to
  `law.cfg`). The smoke chain below ran under `uic_law.cfg` with `--version test_uic` on 2026-10-18,
  with no duplicate-name error.
- **Working package decision (Lautaro, branch `lauti`):** new work goes into `uic/` as an
  *overlay*; `mtt/` is left as it is so it stays close to Johanna's repo for future pulls (Z′ code
  is deliberately kept for the same reason). Alex's `master` moves the same way, but `uic/` is
  **not yet wired up as an overlay**: see the next section before editing anything there.
- Task namespace `cf`. Default analysis: `mtt.config.run3.analysis_mtt_uic.analysis_mtt_new`.
  Configs: `run3_mtt_2024_nano_v15_new` (full), `run3_mtt_2024_nano_v15_limited_new` (2 files per
  dataset, default), `run3_mtt_2024_nano_v15_medium_limited_new` (10 files). Default dataset
  `tt_sl_powheg`.
- All task outputs in `law.cfg` `[outputs]` are **`local`** (Alex switched Calibrate/Select/Reduce/
  ProduceColumns and others from `wlcg`; `master`'s README says `wlcg` is not supported for UIC
  users; the old value remains as a `#wlcg` comment). The store is `data/mtt_store/new_analysis_mtt/`.
- **Grid proxy:** `voms-proxy-init -voms cms -rfc -valid 192:00`, check with `voms-proxy-info --all`.
  Needed for remote input data and job submission. Cached steps can look fine with an expired proxy
  and a later task then fails with `voms-proxy-info failed` / sandbox exit code 40.
- **Input files come from the dCache mount first:** `lfn_sources` in `law.cfg` lists
  `local_desy_dcache` (`/pnfs/desy.de/cms/tier2`) first. This avoids a framework problem seen in
  `tt_semileptonic_2`: the columnar sandbox's XRootD client can deadlock at process exit after a
  `root://` read, so the work finishes and the output is written but the job never exits. An LFN
  not on the DESY Tier-2 disk falls through to the XRootD redirectors, and the hang can return for
  that branch.
- `--calibrator` (singular) up to `CalibrateEvents`, `--calibrators` (plural) from `SelectEvents`;
  `--producer` singular for `cf.ProduceColumns`, `--producers` plural from `cf.CreateHistograms` on.
- Alex's scripts mostly use `--workflow htcondor`; leave out `--workflow` and `--workers` to run
  locally. Remember: the user runs `law run`, see the top of this section.
- `kill_on_str` (Lautaro's tool, on `PATH`) stops a process as soon as a string appears in its
  output, and `:(` in columnflow output means something failed. Worth suggesting when handing over
  a long command: `law run ... 2>&1 | kill_on_str ":("` (luigi logs to stderr, hence `2>&1`).
- Interactive helper: `source confirm_and_run.sh`, then `confirm_and_run "law run ..."`.

### Forcing a rerun (`--remove-output depth,mode,run`)

Law caches by parameter combination and will not rerun a task whose output exists, even a stale or
broken one.

1. **depth**: how far up the requirement chain to also remove. An int (`0` = this task only) or a
   task family where recursion stops (`cf.CalibrateEvents` removes everything up to and including it).
2. **mode**: `i` (confirm each target, default), `a` (remove all without asking), `d` (dry run).
3. **run**: whether to run the task after removing. The default is no: it only deletes and exits.

`0,a,y` regenerates just this task and keeps upstream caches (the usual choice after a producer
change). Use a larger depth or a task family when the change is further back in the graph.

### Verified smoke-test chain (Lautaro, 2026-10-18, branch `lauti`, columnflow v0.3.0-207)

All four ran successfully on `tt_sl_powheg`, `--version test_sel`, in the 2-file limited config;
outputs for `test_sel` and `test_uic` are in the store. Not rerun since, so repeat it after merging
`master`. Defaults of the config are calibrator `skip_jecunc`, selector `default`, reducer `default`
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

How Alex runs things: `scripts/alex_testing/*.sh` (14 scripts here, each a working example, though
some are snapshots of older stages), e.g.

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

## Which code actually runs: `mtt/` or `uic/`

**Editing a file in `uic/` often has no effect.** Under `law.cfg` no `uic.*` module is loaded at
all. Under `uic_law.cfg`, this is what resolves (tested by loading the modules under each config):

| Name | `law.cfg` | `uic_law.cfg` |
|---|---|---|
| Analysis object | `mtt.config.run3.analysis_mtt_uic` | `uic.config.run3.analysis_mtt_uic` |
| Config builder (imported by the analysis) | `mtt.config.run3.uic_mtt_config` | **`mtt`** on `lauti`; `uic.config.run3.uic_config` on `master` |
| Producers `uic`, `add_prod_cats`, `ttbar` | `mtt.production.*` | **`mtt.production.*`** |
| Producers `default`, `features` by name | `mtt.production.*` | `uic.production.*` |
| Selector `default` | `mtt.selection.default` | `uic.selection.default` |

Consequences:

- On `lauti`, no `.py` file in `uic/` or `mtt/` imports `uic.*`, and all 63 `uic/` files are
  byte-identical to their `mtt/` counterparts. `uic/config/` and `uic/plotting/` are therefore
  unused (a `--plot-function uic.plotting...` given explicitly would be the exception).
- **`uic/production/ttbar_reco_uic.py` is imported by nothing, on `lauti` and on `master`.**
  `uic/production/default.py` does `from mtt.production.ttbar_reco_uic import uic`, and `uic_law.cfg`
  lists `uic.production.ttbar_reco`, which does not exist. To change the producer today, edit the
  `mtt/` file, or repoint these imports first.
- `uic.production.default` and `uic.selection.default` also import their parts from `mtt.*` by
  object. So `--producer default` runs `mtt`'s `features`, while `--producers features` resolves by
  name to `uic`'s. The two only stay the same while the files are identical.
- A name registered twice raises no error; the `uic` copy wins here.
- A module listed in a law config that does not exist is **skipped silently**: columnflow loads them
  with `maybe_import`, which returns a mock (`modules/columnflow/columnflow/util.py`). Both configs
  list one (`mtt.calibration.test`). A typo in `*_modules` therefore shows up later, as a missing
  producer or selector.

---

## Layout

| Path | What |
|---|---|
| `mtt/` | **the code that actually runs** (Johanna's `master` + Alex's additions) |
| `mtt/production/ttbar_reco.py` | chi2 ttbar reco, producer `ttbar` (Johanna's, unchanged) |
| `mtt/production/ttbar_reco_uic.py` | **Alex's** producer `uic`: chi2 reco + `delta_y`/`tanh_y` + helicity-basis spin observables (`cos_theta`, `cos_phi`, `cos_phi_tilde`, `{top,atop}_{lepton,bjet}_{k,n,r}`), gen-level `gen_tanh_y`; also producer `add_prod_cats` |
| `mtt/production/ttbar_reco_uic_spanet.py` | near-copy for a future SPANet comparison; **not registered**; same producer name `uic` (do not load both); has the old energy-based rapidity |
| `mtt/production/default.py` | chain: `ttbar, features, weights, category_ids, uic` (in execution order) |
| `mtt/production/util.py` | `lv_nrk` (helicity basis k, n, r) added by Alex |
| `mtt/plotting/` | `plot_functions.py` (spin density matrix, entanglement summary), `plot_functions_asymmetry.py` (A_C template method, CMS AN-26-039), `plot_functions_2d.py` (migration), `hist_hooks.py` (`calculate_asymmetry`, `stack_entanglement_regions`) |
| `mtt/config/run3/uic_mtt_config.py` | config builder for UIC (adds charge + subjet columns, hist hooks, `cfg.x.entanglement_regions`) |
| `mtt/config/run3/analysis_mtt_uic.py` | analysis object (the `default_analysis`) |
| `mtt/config/{categories,variables,datasets*}.py` | n-jet categories (`0j..3j`), entanglement-region categories, QIS variables, `tt_sl/dl/fh` split |
| `mtt/selection/`, `mtt/calibration/` | **Johanna's old `master`** (includes triggers, `data_trigger_veto`, JEC/JER, jet veto map, QCD spikes, 2D lepton-jet cut); Alex's only change is +47 lines in `selection/categories.py` |
| `mtt/ml/`, `mtt/inference/` | Johanna's ML / limit code, not part of the UIC work |
| `mtt/columnflow_patches.py` | patches to columnflow tasks, applied at import |
| `uic/` | intended home of UIC work, but **currently a partial copy of `mtt/`**: see the section above. No `ml/`, `inference/`, `production/ttbar_reco.py` or `*.yaml` |
| `scripts/alex_testing/` | Alex's run scripts; `scripts/selection_scripts/` jet/cutflow studies; `scripts/sf_scripts/` SF calculation |
| `workflow_scripts/` | Johanna's workflow templates (gitignored except what is tracked) |
| `examples/`, `bin/` | upstream example workflows; `mtt_inspect`, `mtt_diff` helpers |
| `law.cfg`, `uic_law.cfg`, `law.nocert.cfg` | law configs (see above) |

Producers are registered by import: `mtt.production.default` imports `ttbar_reco_uic`, which is
why `--producers ...,uic,...` works although `law.cfg` does not list that module.

---

## Known problems (do before / during the merge)

1. **`uic/` is not a working overlay yet** (section above). Decide which modules move, repoint the
   imports, and fix the `uic.production.ttbar_reco` entry in `uic_law.cfg` (also on `master`). Do
   this after merging `master`, because Alex's restructuring changes the same files.
2. `*_old` files in `mtt/` (`datasets_old.py`, `variables_old.py`, `run3/new_mtt_config_old.py`,
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
   producers, neutrino sanity tolerance 4e-3 (the 2e-3 in `mtt/production/neutrino.py:102` can crash
   on a data event), 2025 support. Details in `../tt_semileptonic_2/MTTBAR_UPDATES.md`.
7. Reported in `master`'s README, not checked here: `--local-scheduler False` does not work in the
   current setup; `--per-plot steps` does not work for cutflow plots.

---

## How this relates to `tt_semileptonic_2` (what to keep from where)

- **Only here**: spin-density-matrix / entanglement (D, D̃) / polarisation machinery, A_C
  template-method plots, migration plot, hist hooks, entanglement-region categories, `uic`
  producer, SPANet prep, trigger logic (inherited from Johanna's `master`).
- **Only in `tt_semileptonic_2`** (not committed in part, see COALESCING.md §3.1): dataclass-based
  selection params and cleaner selector split, weights chain with a real shape b-tag SF, QCD
  data-driven "shadow dataset" design (never run), simple A_C plot (`delta_abs_y`), `PlotCutflow`
  wrapper, `ReduceEvents` chunk-size override, extensive docs. Read its files as reference only: it
  runs on columnflow v0.3.1, not this repo's v0.3.0-207.
- **Overlap**: chi2 `ttbar_reco`, lepton charge in the `Lepton` column, the charge-asymmetry
  observable (two implementations; both use the m_T-based rapidity).

---

## Framework gotchas

Carried over from `tt_semileptonic_2`; they apply to any columnflow code here.

- `category_ids` runs the categorizer for *every* leaf category, so a categorizer reading a column
  that is not produced yet breaks `cf.SelectEvents`.
- New categories do not apply retroactively to a cached `cf.SelectEvents` output for the same
  `--version`: law reruns on changed task parameters, not on a changed config. They show up empty
  until you use a new `--version` or force a rerun.
- `Jet`/`Muon` collections need the full `{pt,eta,phi,mass}` in `uses`, even if you cut only on
  pt/eta (otherwise `array does not have azimuthal coordinates`).
- De-option per-event scalars before broadcasting against a jagged array. Comparing `N * ?int`
  (e.g. from `ak.firsts`) with a jet column makes the whole list nullable, which survives
  `ak.fill_none(x, False)` and ends in `SelectionResult event mask must be of type N * bool`.
  `ak.fill_none` the scalar to a sentinel first.
- `--processes` takes process names (`tt_sl`), not dataset names (`tt_sl_powheg`).
- A sandbox exit code of `-9` during `cf.ReduceEvents` or `cf.ProduceColumns` is out of memory; lower
  `--workers` or the chunk size.

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
- Lint with `flake8` (`.flake8`: line length 120, double quotes).
- Do not edit `../mttbar_johanna` or `../tt_semileptonic_2` while coalescing without being asked;
  both hold work (the latter uncommitted) that exists nowhere else.
