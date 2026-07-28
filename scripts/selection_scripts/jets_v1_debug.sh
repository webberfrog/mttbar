#!/usr/bin/env bash

#
# plot the distribution of the ttbar mass
# only mu data implemented currently
#

# common arguments for all tasks
args=(
    --version jets_v3
    --categories incl,1m__0t__2j,1m__1t__2j,1m__0t__3j,1m__1t__3j,1m__0t__chi2pass,1m__1t__chi2pass,1m__0t__chi2fail,1m__1t__chi2fail,1m__0t,1m__1t,1m__chi2pass,1m
    --config run3_mtt_2024_nano_v15_new
    --hist-producer all_weights
    #--skip-ratio
    --workers 5
    --workflow htcondor
    --local-scheduler False
    #--shape-norm
    #--skip-ratio
    --remove-output 8,i
    #--selector-steps Jet,BJet
    #--per-plot steps BUGGED
    --cms-label pw
    --file-types png
    #--process-settings "tt,unstack,color=#e41a1c:st,unstack,label=Single Top"
)

# lotta jet stuffs
law run cf.PlotVariables1D \
    --variables \
        ttbar_mass \
    --processes \
        data,tt_sl,tt_dl,tt_fh,st,w_lnu,qcd,vv,dy \
    --datasets \
       qcd_ht1200to1500_madgraph \
    --producers \
        category_ids,ttbar,add_prod_cats,features,weights \
    "${args[@]}"
