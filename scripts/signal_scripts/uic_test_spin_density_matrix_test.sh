#!/usr/bin/env bash

#
# Extract the ttbar polarization vectors (P, P-bar) and spin correlation matrix (C) in the
# helicity (k, n, r) basis from expectation values of the lepton/b-jet decay-product angles,
# and plot them in the style of Fig. 17/19 of CMS-TOP-23-007 (arXiv:2409.11067), minus the
# simulation-comparison panel. See `mtt.plotting.plot_functions.plot_spin_density_matrix` for
# the method (a direct expectation-value extraction, not the paper's binned likelihood fit)
# and its caveats.
#
# only mu data implemented currently
#

# the 12 charge-corrected 1D observables (see mtt/production/ttbar_reco_uic.py)
vars_1d=(
    top_lepton_k top_lepton_n top_lepton_r
    top_bjet_k top_bjet_n top_bjet_r
    atop_lepton_k atop_lepton_n atop_lepton_r
    atop_bjet_k atop_bjet_n atop_bjet_r
)

# the 18 joint 2D observables needed for the 9 C_ij correlation coefficients
# (one histogram per charge sub-sample per (i, j) pair)
vars_2d=()
for i in k n r; do
    for j in k n r; do
        vars_2d+=("top_lepton_${i}-atop_bjet_${j}")
        vars_2d+=("top_bjet_${i}-atop_lepton_${j}")
    done
done

variables="$(IFS=,; echo "${vars_1d[*]},${vars_2d[*]}")"

# common arguments for all tasks
args=(
    --version uic_v3_7
    --categories incl,1m__0t,1m__1t,1m__chi2pass,1m__chi2fail
    --config run3_mtt_2024_nano_v15_limited_new
    --hist-producer all_weights
    --workers 5
    --workflow htcondor
    --remove-output 0,a,y
    --cms-label pw
    --file-types png
    # kappa_lep=1.0, kappa_bjet=0.4 are already the plot function's defaults;
    # override them here (or drop this line) if different values are needed, e.g.:
    # --general-settings kappa_lep=1.0,kappa_bjet=0.966
)

law run cf.PlotVariables1D \
    --multi-variable \
    --variables "${variables}" \
    --plot-function mtt.plotting.plot_functions.plot_spin_density_matrix \
    --processes \
        tt_dl \
    --datasets \
        tt_dl_powheg \
    --producers \
        category_ids,uic,features,weights,add_prod_cats \
    "${args[@]}"
