#!/usr/bin/env bash

#
# plot the distribution of the ttbar mass
# 
#

# common arguments for all tasks
args=(
    --version jets_v2
    --categories incl,0t__2j,1t__2j,0t__3j,1t__3j,0t__chi2pass,0t__chi2fail,1t__chi2pass,1t__chi2fail
    --config run3_mtt_2024_nano_v15_limited_new
    #--hist-producer all_weights
    #--skip-ratio
    #--workers 5
    #--workflow htcondor
    #--local-scheduler False
    #--shape-norm
    #--skip-ratio
    #--remove-output 0,a,y
    #--selector-steps Jet,BJet
    #--per-plot steps BUGGED
    --cms-label pw
    --file-types png
    --process-settings "tt,unstack,color=#e41a1c:st,unstack,label=Single Top"
)

# lotta jet stuffs
law run cf.PlotCutflow \
    --processes \
        data,tt,st,w_lnu \
    --datasets \
        data_mu_c,tt_sl_powheg,st_twchannel_t_sl_powheg,st_twchannel_tbar_sl_powheg,w_lnu_1j_madgraph,w_lnu_2j_madgraph,w_lnu_3j_madgraph,w_lnu_4j_madgraph \
    "${args[@]}"
