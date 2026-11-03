#!/usr/bin/env bash

#
# Testing new uic_law.cfg and attempting to validate our selection/reconstruction with a range of kinematic plots
#

# common arguments for all tasks
args=(
    --version uic_v5
    --categories incl,1m__chi2pass,1m
    --config run3_mtt_2024_nano_v15_limited_new
    --hist-producer all_weights
    #--plot-function uic.plotting.plot_functions_asymmetry.plot_tanh_y_gen_weights
    #--skip-ratio
    --workers 5
    --workflow htcondor
    #--local-scheduler False --bugged right now for me
    #--shape-norm
    #--skip-ratio
    --remove-output 0,a,y
    #--selector-steps Jet,BJet
    #--per-plot steps BUGGED
    --cms-label wip
    --file-types png
    #--branches 1
    #--process-settings "tt,unstack,color=#e41a1c:st,unstack,label=Single Top"
)

# all relevant kinematics with all backgrounds
law run cf.PlotVariables1D \
    --variables \
        jet1_pt,jet1_eta,jet1_phi,jet2_pt,jet2_eta,jet2_phi,fatjet1_pt,fatjet1_eta,fatjet1_phi,fatjet_tau32,fatjet_tau21,electron_pt,electron_eta,electron_phi,muon_pt,muon_eta,muon_phi,met_pt,met_phi,puppi_met_pt,puppi_met_phi,jet_lep_pt_rel,jet_lep_delta_r,chi2_lt100,ttbar_mass_1k \
    --processes \
        data,tt_sl,tt_dl,tt_fh,st,w_lnu,qcd,vv,dy \
    --datasets \
        data_mu_c,data_mu_d,data_mu_e,data_mu_f,data_mu_g,data_mu_h,data_mu_i,tt_sl_powheg,st_twchannel_t_sl_powheg,st_twchannel_tbar_sl_powheg,st_twchannel_t_dl_powheg,st_twchannel_tbar_dl_powheg,st_twchannel_t_fh_powheg,st_twchannel_tbar_fh_powheg,st_tchannel_tbar_had_4f_powheg,st_tchannel_t_lep_4f_powheg,st_tchannel_tbar_lep_4f_powheg,w_lnu_1j_madgraph,w_lnu_2j_madgraph,w_lnu_3j_madgraph,w_lnu_4j_madgraph,tt_dl_powheg,tt_fh_powheg,qcd_ht200to400_madgraph,qcd_ht400to600_madgraph,qcd_ht600to800_madgraph,qcd_ht800to1000_madgraph,qcd_ht1000to1200_madgraph,qcd_ht1200to1500_madgraph,qcd_ht1500to2000_madgraph,qcd_ht2000toinf_madgraph,ww_pythia,wz_pythia,zz_pythia,dy_4j_mumu_m50toinf_madgraph,dy_4j_ee_m50toinf_madgraph \
    --producers \
        category_ids,uic,features,weights,add_prod_cats \
    "${args[@]}"


#data_mu_c,data_mu_d,data_mu_e,data_mu_f,data_mu_g,data_mu_h,data_mu_i,tt_sl_powheg,st_twchannel_t_sl_powheg,st_twchannel_tbar_sl_powheg,st_twchannel_t_dl_powheg,st_twchannel_tbar_dl_powheg,st_twchannel_t_fh_powheg,st_twchannel_tbar_fh_powheg,st_tchannel_tbar_had_4f_powheg,st_tchannel_t_lep_4f_powheg,st_tchannel_tbar_lep_4f_powheg,w_lnu_1j_madgraph,w_lnu_2j_madgraph,w_lnu_3j_madgraph,w_lnu_4j_madgraph,tt_dl_powheg,tt_fh_powheg,qcd_ht200to400_madgraph,qcd_ht400to600_madgraph,qcd_ht600to800_madgraph,qcd_ht800to1000_madgraph,qcd_ht1000to1200_madgraph,qcd_ht1200to1500_madgraph,qcd_ht1500to2000_madgraph,qcd_ht2000toinf_madgraph,ww_pythia,wz_pythia,zz_pythia,dy_4j_mumu_m50toinf_madgraph,dy_4j_ee_m50toinf_madgraph \
