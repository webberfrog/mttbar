# m(ttbar) analysis — UIC fork

Top-quark pair analysis (m(tt̄), charge asymmetry, spin-correlation / quantum-information observables) on Run 3.
Built on [columnflow](https://github.com/columnflow/columnflow), [law](https://github.com/riga/law) and [order](https://github.com/riga/order).

This is a fork of [uhh-cms/mttbar](https://github.com/uhh-cms/mttbar) (remote `origin`).
UIC developments live in [webberfrog/mttbar](https://github.com/webberfrog/mttbar) (remote `uic`) and mostly in the `uic/` package.


## Documentation

| Topic | Link |
| --- | --- |
| columnflow docs (start here) | https://columnflow.readthedocs.io/en/latest/ |
| columnflow task overview | https://columnflow.readthedocs.io/en/latest/task_overview/introduction.html |
| columnflow user guide | https://columnflow.readthedocs.io/en/latest/user_guide/index.html |
| columnflow API reference | https://columnflow.readthedocs.io/en/latest/api/index.html |
| columnflow source | https://github.com/columnflow/columnflow |
| law docs | https://law.readthedocs.io/en/latest/ |
| order docs | https://python-order.readthedocs.io/en/latest/ |
| cmsdb (datasets / processes) | https://github.com/uhh-cms/cmsdb |

Reference analysis note: `AN2023_120_v16`


## Setup

You need a valid VOMS proxy to read the input data.

```shell
# clone (with the columnflow + cmsdb submodules)
git clone --recursive git@github.com:webberfrog/mttbar.git
cd mttbar

# grid proxy
voms-proxy-init -voms cms -rfc -valid 196:00

# source the setup; decisions are stored in .setups/dev.sh (name is arbitrary)
source setup.sh dev

# index tasks once (and after changing the law config) for "law run" auto-completion
law index --verbose
```

### Choosing the law config

There are two law configs:

- `law.cfg`: the upstream `mtt` analysis (`mtt/` package)
- `uic_law.cfg`: the UIC analysis. It sets `default_analysis = uic.config.run3.analysis_mtt_uic.analysis_mtt_new` and `default_config = run3_mtt_2024_nano_v15_limited_new`, and loads UIC production and selection modules from `uic/`.

`.setups/dev.sh` sets `LAW_CONFIG_FILE`. To use the UIC analysis, change it there (the file is gitignored, so the change stays local):

```shell
export LAW_CONFIG_FILE="$MTT_BASE/uic_law.cfg"
```

Then run `source setup.sh dev && law index --verbose` again.


## Repository structure

```
mttbar/
├── mtt/                    # upstream analysis package
│   ├── config/             #   analysis + config objects (run2/, run3/), datasets, processes, variables, categories
│   ├── calibration/        #   calibrators (jets, ...)
│   ├── selection/          #   selectors
│   ├── production/         #   producers (features, ttbar reco, weights, ...)
│   ├── reduction/          #   reducers
│   ├── categorization/     #   categorizers
│   ├── ml/                 #   ML models (simple, derived/, ...)
│   ├── inference/          #   inference models for datacards (an_2019_197, simple)
│   ├── plotting/           #   custom plot functions + hist hooks
│   └── tasks/              #   analysis-specific law tasks
├── uic/                    # UIC versions of the above (config, selection, production, plotting, ...)
│   ├── config/run3/        #   analysis_mtt_uic.py, uic_mtt_config.py
│   ├── production/         #   ttbar_reco_uic*.py, ttbar_gen.py, features, weights, ...
│   └── plotting/           #   plot_functions_2d.py, plot_functions_asymmetry.py, hist_hooks.py
├── modules/                # git submodules: columnflow, cmsdb
├── scripts/                # run scripts (law run wrappers), see below
│   ├── alex_testing/       #   angular / spin-density / asymmetry plots
│   ├── selection_scripts/  #   jet selection studies, cutflows
│   └── sf_scripts/         #   scale-factor / efficiency calculation
├── examples/               # upstream example workflows (000_test, 004_dnn, ...)
├── workflow_scripts/       # older workflow scripts (gitignored)
├── bin/                    # mtt_inspect, mtt_diff helpers
├── sandboxes/              # extra venv sandbox definitions
├── law.cfg                 # law config: upstream mtt analysis
├── uic_law.cfg             # law config: UIC analysis
├── law.nocert.cfg          # law config without grid certificate
├── confirm_and_run.sh      # interactive confirm_and_run / no_confirm helpers
├── setup.sh                # environment setup
└── data/                   # local store, software, jobs (gitignored)
```


## Running the scripts

Each script in `scripts/` wraps a `law run` call. Arguments shared by all tasks go in an `args=(...)` array at the top, and the variables, processes, datasets and producers are given in the `law run` call itself.
Run them from the repo root after sourcing the setup:

```shell
source setup.sh dev        # with LAW_CONFIG_FILE pointing to uic_law.cfg

# --- scripts/alex_testing ---
bash scripts/alex_testing/uic_test_v3.sh                     # cf.PlotVariables2D: cos_theta-ttbar_mass-cos_phi(_tilde), htcondor
bash scripts/alex_testing/uic_test_migration.sh              # cf.PlotVariables2D: reco vs gen mtt migration matrix (tt_sl)
bash scripts/alex_testing/Ac_template_v1.sh                  # cf.PlotVariables2D: gen vs reco tanh(y) templates
bash scripts/alex_testing/Ac_weights_v1.sh
bash scripts/alex_testing/Ac_decomp_v1.sh
bash scripts/alex_testing/uic_test_spin_density_matrix.sh    # cf.PlotVariables1D: Plots full spin density matrix vars (currently observing polarization)
bash scripts/alex_testing/uic_test_2D_D.sh                   # 2D entanglement witness D

# --- scripts/selection_scripts ---
bash scripts/selection_scripts/cutflow_jets_v0.sh            # cf.PlotCutflow (limited config)
bash scripts/selection_scripts/jets_v1.sh                    # cf.PlotVariables1D, full 2024 mu data + all MC, htcondor
bash scripts/selection_scripts/n_jet_study.sh

# --- scripts/sf_scripts ---
# runs calc_sf2d.py inside the venv_columnar_dev sandbox; arguments are passed to it
bash scripts/sf_scripts/calc_sf.sh --config <config> --version <version> --variables <var1> <var2>
```

### Tips

- The scripts don't forward extra command-line arguments to `law run`. Edit the `args` array instead (many options are already there, commented out):
  - `--print-status 2,0`: show which outputs exist, without running anything
  - `--remove-output 0,a,y`: delete the existing plot outputs and rerun
  - `--workflow htcondor --workers 5`: submit to HTCondor. Leave both out to run locally.
  - `--branches 0`: run one branch only, for a quick test
  - `--version`: change it to keep outputs from different runs apart
- Interactive helper: `source confirm_and_run.sh`, then `confirm_and_run "law run ..."` asks before it runs the command and accepts the shortcuts `-ps` and `-ro`.
- `--config run3_mtt_2024_nano_v15_limited_new` runs over a reduced set of files and is fast. `run3_mtt_2024_nano_v15_new` runs over the full dataset.

### Caveats

- The scripts are snapshots taken at different stages of the analysis (see `workflow_scripts/README`), so some of them are out of date.
- `scripts/sf_scripts/calc_sf*.py` import `tgs.config.run3.analysis_tgs` and default to a run2 config. They need adapting before they work here.
- law.cfg wclg not supported for uic users, change all to local 


## Common columnflow tasks

| Task | Purpose |
| --- | --- |
| `cf.CalibrateEvents` | apply calibrators |
| `cf.SelectEvents` | apply selectors, store masks + cutflow |
| `cf.ReduceEvents` / `cf.MergeReducedEvents` | apply masks, write reduced columns |
| `cf.ProduceColumns` | run producers (`category_ids,uic,features,weights,add_prod_cats`) |
| `cf.CreateHistograms` / `cf.MergeHistograms` | fill histograms (`--hist-producer all_weights`) |
| `cf.PlotVariables1D` / `cf.PlotVariables2D` | plots (`--plot-function`, `--hist-hooks`) |
| `cf.PlotCutflow` | cutflow plots |
| `cf.CreateDatacards` | CMS datacards from an inference model |

Inspect a task tree: `law run <Task> ... --print-status 3,0`. For the full task graph, see the [task overview](https://columnflow.readthedocs.io/en/latest/task_overview/introduction.html).


## WIP / TODO

<!-- Fill in / tick off as work progresses. -->

### In progress
- [ ] QIS variables plot (bugged, see commit `0562b23`)
- [ ] Asymmetry hist hook `calculate_asymmetry` (`uic/plotting/hist_hooks.py`)
- [ ] SPANet-based ttbar reconstruction (`uic/production/ttbar_reco_uic_spanet.py`)
- [ ] Implement muon 2D cut (& verify whole selection)
- [ ] Determine is gen particles are first or last copy
- [ ] ...

### Known issues
- [ ] `--local-scheduler False` doesn't work in the current setup
- [ ] `--per-plot steps` doesn't work for cutflow plots
- [ ] `uic_law.cfg` `run3_analysis` points to `uic.config.run3.analysis_mtt`, which doesn't exist in `uic/config/run3/`
- [ ] ...

### Next steps
- [ ] Implement data/mc eras other than 2024
- [ ] Implement electron data
- [ ] Determine kinematics needed for EFT search
- [ ] Sketch EFT optimization project
- [ ] ...


## Development

- Upstream: [uhh-cms/mttbar](https://github.com/uhh-cms/mttbar) ([issues](https://github.com/uhh-cms/mttbar/issues))
- UIC fork: [webberfrog/mttbar](https://github.com/webberfrog/mttbar)