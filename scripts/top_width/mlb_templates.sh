#!/usr/bin/env bash

#
# Top-width templates: reweight tt_sl_powheg to several top widths (Breit-Wigner ratio of the gen top masses)
# and overlay the m_lb and DeltaR_min(j_b, j_l) templates (b-tagged leptonic jet only).
#
# Needs `uic_law.cfg` (the gen_mt / mlb / dr_min_bl variables and the uic producers only exist there).
# `.setups/dev.sh` defaults to `law.cfg`, so the config is switched below. If you paste the commands into
# your own shell instead of running this script, run the export yourself, then `law index --verbose`.
# Run the steps one by one; the first one is slow and memory heavy.
#

: "${MTT_BASE:?run 'source setup.sh dev' first}"
export LAW_CONFIG_FILE="$MTT_BASE/uic_law.cfg"

common=(
    --version tw_v1
    --config run3_mtt_2024_nano_v15_limited_new
    --dataset tt_sl_powheg
    --calibrators skip_jecunc
    --selector default
    --reducer default
)

# 1. Regenerate the columns: the cached tw_v1 output predates TopWidth.gen_mt / gen_mtbar.
#    `0,a,y` removes only this task's output (no prompt) and reruns it, keeping selection and reduction.
# law run cf.ProduceColumns "${common[@]}" --producer default --remove-output 0,a,y

# 2. Templates. The 3D variables are (gen m_t, gen m_tbar, reco observable); the gen axes are summed over after
#    the per-bin Breit-Wigner weights are applied. Widths: --general-settings "gammas=0.7;1.0;2.0;3.0"
#    (the nominal width from ttbar_reco_settings.gen_top_width is always added).
law run cf.PlotVariables2D \
    --version tw_v1 \
    --config run3_mtt_2024_nano_v15_limited_new \
    --datasets tt_sl_powheg \
    --processes tt_sl \
    --categories incl,1e,1m \
    --calibrators skip_jecunc --selector default --reducer default \
    --producers default \
    --hist-producer all_weights \
    --variables gen_mt-gen_mtbar-mlb_btagged,gen_mt-gen_mtbar-dr_min_bl_btagged \
    --plot-function uic.plotting.plot_functions_width.plot_width_templates \
    --general-settings "gammas=0.7;3.0" \
    --cms-label wip \
    --file-types png
    # --remove-output 0,a,y \
