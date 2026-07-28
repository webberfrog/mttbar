#!/usr/bin/env bash

#
# plot the distribution of the ttbar mass
# 
#

# common arguments for all tasks
args=(
    --version reco_improvement
    --categories incl
    --config run3_mtt_2024_nano_v15_limited_new
    #--skip-ratio
    #--workers 8
    #--workflow htcondor
    #--local-scheduler False
    #--shape-norm
    #--skip-ratio
    #--remove-output 0,a,y
    #--selector-steps Jet,BJet
    #--per-plot steps BUGGED
    --cms-label simpw
    #--process-settings "tt,unstack,color=#e41a1c:st,unstack,label=Single Top"
)

# two versions of the ttbar mass
law run cf.PlotVariables1D \
    --variables ttbar_mass,cf_n_jet,n_bjet \
    --processes \
        tt,st,w_lnu,dy,qcd \
    --datasets \
        data_mu_c,tt_sl_powheg,st_twchannel_t_sl_powheg,st_twchannel_tbar_sl_powheg,w_lnu_1j_madgraph,w_lnu_2j_madgraph,w_lnu_3j_madgraph,w_lnu_4j_madgraph \
    --producers \
        ttbar \
    --variables \
        cf_n_jet \
    "${args[@]}"
