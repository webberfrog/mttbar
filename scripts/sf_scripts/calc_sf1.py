# coding: utf-8
import hist
import matplotlib.pyplot as plt
import mplhep
import numpy as np
import order as od
import os
import pickle

from scipy.stats import norm, beta

from columnflow.plotting.plot_util import remove_residual_axis

from tgs.config.run3.analysis_tgs import analysis_tgs

#from hist import axis as Axis


def load_hist(fname: str):
    if not os.path.exists(fname):
        msg = (
            f"could not find histogram file: {fname}\n"
            "Please run `law run cf.MergeHistograms` with the "
            "corresponding settings to produce it."
        )
        raise FileNotFoundError(msg)
    with open(fname, "rb") as f:
        return pickle.load(f)


def get_hist_1d(hist_obj: hist.Hist, root_category: str, config_inst: od.Config):
    """
    Extract regular histogram from a multidimensional columnflow output
    histogram by reducing the `category`, `process` and `shift` axes.

    `hist_obj`:      histogram object from columnflow output
    `root_category`: name of a category, for which all leaf categories should be
                     added together
    `config_inst`:   configuration object containing category-specific information
    """
    cat_insts = config_inst.get_category(root_category).get_leaf_categories()
    return hist_obj[{
        "category": [
            hist.loc(c.id) for c in cat_insts
            if c.id in hist_obj.axes["category"]
        ],
    }][{
        "category": sum,
        "process": sum,
    }]


def calc_efficiency_and_uncertainties(
    n_passed: np.array,
    n_total: np.array,
    error_type: str = "clopper-pearson",
    confidence_level: float = 0.682689492137,
):
    """
    Calculate efficiency and its associated (asymmetric) uncertainty given the number
    of events passing the selection criteria (`n_passed`) and the total number of events `n_total.

    Returns efficiency_value, (error_dn, error_up)
    """
    n_passed = np.asarray(n_passed)
    n_total = np.asarray(n_total)
    eff_val = n_passed / n_total

    # factor used in computing the uncertainty
    alpha = (1.0 - confidence_level) / 2

    if error_type == "normal":
        # normal approximation
        # https://root.cern.ch/doc/v630/classTEfficiency.html#a822b6253fc799767f271c7de9ea30935
        sigma = np.sqrt(eff_val * (1 - eff_val) / n_total)
        delta = norm.ppf(1 - alpha, loc=0, scale=sigma)
        eff_dn, eff_up = eff_val - delta, eff_val + delta

    elif error_type == "clopper-pearson":
        # Clopper-Pearson interval
        # https://root.cern.ch/doc/v630/classTEfficiency.html#ae80c3189bac22b7ad15f57a1476ef75b
        eff_up = beta.ppf(1 - alpha, n_passed + 1, n_total - n_passed)
        eff_dn = beta.ppf(alpha, n_passed, n_total - n_passed + 1)

    else:
        raise ValueError(f"unknown 'error_type': {error_type}")
    
    # ensure up/down variation within interval [0, 1]
    eff_up = np.where(eff_up < 1.0, eff_up, 1.0)
    eff_dn = np.where(eff_dn > 0.0, eff_dn, 0.0)

    # return central value end error bars (down, up)
    return eff_val, (
        eff_val - eff_dn,
        eff_up - eff_val,
    )

def calc_sf_and_uncertainties(
    num: np.array,
    den: np.array,
    error_type: str = "clopper-pearson",
    confidence_level: float = 0.682689492137,
):
    """
    Calculate efficiency and its associated (asymmetric) uncertainty given the number
    of events passing the selection criteria (`n_passed`) and the total number of events `n_total.

    Returns efficiency_value, (error_dn, error_up)
    """
    n_passed = np.asarray(n_passed)
    n_total = np.asarray(n_total)
    eff_val = n_passed / n_total

    # factor used in computing the uncertainty
    alpha = (1.0 - confidence_level) / 2

    if error_type == "normal":
        # normal approximation
        # https://root.cern.ch/doc/v630/classTEfficiency.html#a822b6253fc799767f271c7de9ea30935
        sigma = np.sqrt(eff_val * (1 - eff_val) / n_total)
        delta = norm.ppf(1 - alpha, loc=0, scale=sigma)
        eff_dn, eff_up = eff_val - delta, eff_val + delta

    elif error_type == "clopper-pearson":
        # Clopper-Pearson interval
        # https://root.cern.ch/doc/v630/classTEfficiency.html#ae80c3189bac22b7ad15f57a1476ef75b
        eff_up = beta.ppf(1 - alpha, n_passed + 1, n_total - n_passed)
        eff_dn = beta.ppf(alpha, n_passed, n_total - n_passed + 1)

    else:
        raise ValueError(f"unknown 'error_type': {error_type}")

    # ensure up/down variation within interval [0, 1]
    eff_up = np.where(eff_up < 1.0, eff_up, 1.0)
    eff_dn = np.where(eff_dn > 0.0, eff_dn, 0.0)

    # return central value end error bars (down, up)
    return eff_val, (
        eff_val - eff_dn,
        eff_up - eff_val,
    )

if __name__ == "__main__":

    from argparse import ArgumentParser

    ap = ArgumentParser()

    ap.add_argument("--config", default="run2_2017_nano_v9_limited", help="columnflow config name")
    ap.add_argument("--version", default="v0", help="columnflow version tag")
    ap.add_argument("--variable", default="electron_eta", help="columnflow variable name; efficiency will be calculated as a function of this variable")

    ap.add_argument("--output-filename", default="efficiency.png", help="name of the output plot")

    args = ap.parse_args()

    store_path = os.path.join(os.getenv("CF_STORE_LOCAL"), "analysis_tgs")

    # change as needed
    #config = "run2_2017_nano_v9_limited"  # config name
    #version = "v1"  # version tag
    #variable = "electron_eta"  # the quantity on the x axis

    # retrieve configuration instance
    config_inst = analysis_tgs.get_config(args.config)
    variable_inst = config_inst.get_variable(args.variable)

    # data/MC samples (add more here after running cf.MergeHistograms)
    mc_samples = [
        "tt_dl_powheg",
    ]
    data_samples = [
        "data_mu_e",
        #"data_mu_c",
        #"data_mu_d",
    ]
    
    # construct paths to histogram files 
    hist_files = {
        "mc": [
            f"{store_path}/cf.MergeHistograms/{args.config}/{sample}/nominal/calib__skip_jecunc/sel__default_tgs/prod__default_tgs/weight__all_weights/{args.version}/hist__var_{args.variable}.pickle"
            for sample in mc_samples
        ],
        "data": [
            f"{store_path}/cf.MergeHistograms/{args.config}/{sample}/nominal/calib__skip_jecunc/sel__default_tgs/prod__default_tgs/weight__all_weights/{args.version}/hist__var_{args.variable}.pickle"
            for sample in data_samples
        ],
    }

    #For rebinning
    #new_edges = np.array([-2.5, -1.5, -1.0, -0.5, 0, 0.5, 1.0, 1.5, 2.5])
    # new_edges = np.concatenate([
    # np.linspace(0, 120, 24, endpoint=False),
    # np.linspace(120, 240, 12, endpoint=False),
    # np.linspace(240, 360, 8, endpoint=False),
    # np.linspace(360, 400, 1, endpoint=False),
    # np.linspace(400, 600, 1),
    # ])
    # print(new_edges[-1])

    
    # load and add histograms
    hists = {}
    for key in ("data", "mc"):
        # skip empty samples
        if not hist_files[key]:
            continue
        hists[key] = sum(load_hist(fname) for fname in hist_files[key])

    # remove "shift" axis
    hists = remove_residual_axis(hists, "shift")

    # calculate the efficiencies for data and MC
    efficiencies = {}
    for key in ("data", "mc"):
        # skip nonexistent keys
        if key not in hists:
            continue

        # get the histograms of passed and failed events
        h_pass = get_hist_1d(hists[key], "ele_trigger_pass", config_inst)
        h_fail = get_hist_1d(hists[key], "ele_trigger_fail", config_inst)

        # if args.variable == "electron_pt":
        #     # get and rebin histograms
        #     h_pass_raw = get_hist_1d(hists[key], "ele_trigger_pass", config_inst)
        #     h_fail_raw = get_hist_1d(hists[key], "ele_trigger_fail", config_inst)

        #     # debugging
        #     orig_edges = h_pass_raw.axes[args.variable].edges
        #     print("Original bin edges:", orig_edges, orig_edges[-1])

        #     # Rebin pass and fail
        #     h_pass = h_pass_raw[args.variable: Axis.Variable(new_edges)]
        #     h_fail = h_fail_raw[args.variable: Axis.Variable(new_edges)]

        # else:
        #    # get the histograms of passed and failed events
        #    h_pass = get_hist_1d(hists[key], "ele_trigger_pass", config_inst)
        #    h_fail = get_hist_1d(hists[key], "ele_trigger_fail", config_inst)    

        # add the histograms to get the total
        h_total = h_pass + h_fail

        # calculate the efficiency and the associated uncertainty
        eff_val, (err_dn, err_up) = calc_efficiency_and_uncertainties(h_pass.values(), h_total.values())
        
        #efficiencies[key] = h_pass.values() / h_total.values()
        efficiencies[key] = {
            "n_passed": h_pass.values(),
            "n_total": h_total.values(),
            "hist": h_total,
            "efficiency": eff_val,
            "efficiency_err": (err_dn, err_up),
        }
    
    # Tried to get fancy, resorted to the basics
    # # calculate the SF
    # sf = {}
    # for key in ("data"):
    #     # skip nonexistent keys
    #     if key not in hists:
    #         continue
    #     # get the histograms of passed and failed events
    #     # propagate uncertainties
    #     eff_data = efficiencies[key]["efficiency"]
    #     eff_mc = efficiencies["mc"]["efficiency"]
    #     err_data_dn, err_data_up = efficiencies[key]["efficiency_err"]
    #     err_mc_dn, err_mc_up = efficiencies["mc"]["efficiency_err"]

    #     # propagate asymmetric errors (conservatively)
    #     sf_err_dn = sf_val * np.sqrt((err_data_dn / eff_data) ** 2 + (err_mc_up / eff_mc) ** 2)
    #     sf_err_up = sf_val * np.sqrt((err_data_up / eff_data) ** 2 + (err_mc_dn / eff_mc) ** 2)

    #     # calculate the sf
    #     sf_val = eff_data/eff_mc
        
    #     #sf[key] = num / den
    #     sf[key] = {
    #         "sf": sf_val,
    #         "sf_err": (sf_err_dn, sf_err_up),
    #     }

    # plot the efficiencies
    mplhep.style.use("CMS")
    ax = plt.gca()
    for key in ("data", "mc"):
        # skip nonexistent keys
        if key not in efficiencies:
            continue
        # retrieve the efficiency
        h = efficiencies[key]["hist"]
        eff_val = efficiencies[key]["efficiency"]

        # retrieve the errors and put into an (N, 2)-array
        # that histplot understands
        err_dn, err_up = efficiencies[key]["efficiency_err"]
        yerr = np.concatenate([[err_dn], [err_up]], axis=0)

        # do plotting using mplhep
        if key == "mc":
            mplhep.histplot(
                eff_val,
                bins=h.axes[args.variable].edges,
                histtype="step",
                label="MC",

            )
            ax.bar(
                label="MC stat. unc.",
                x=h.axes[args.variable].centers,
                width=h.axes[args.variable].edges[1:] - h.axes[args.variable].edges[:-1],
                bottom=eff_val - err_dn,
                height=err_dn + err_up,
                hatch="///",
                facecolor="none",
                linewidth=0,
                color="black",
                alpha=1.0,
            )
        else:
            #print("Histogram axes:")
            #for ax in h_pass_raw.axes:
            #   print(f" - {ax.name} ({type(ax)})")
            mplhep.histplot(
                eff_val,
                bins=h.axes[args.variable].edges,
                yerr=yerr,
                histtype="errorbar",
                color="black",
                label=r"Data $\pm$ stat. unc.",
            )
            #(sf_err_dn, sf_err_up) = sf[key]["sf_err"]
            #sf_yerr = np.stack((sf_err_dn, sf_err_up), axis=0)

    # set axis limits
    plt.ylim(0, 1.25)

    # set labels
    mplhep.cms.label(ax=plt.gca(), fontsize=22, llabel="Work in progress")
    plt.ylabel("Efficiency")
    plt.xlabel(variable_inst.x_title)

    # draw legend
    plt.legend(ncol=1, loc="upper right")

    # save plot
    plt.savefig(args.output_filename)

    #plot sf
    if "data" in efficiencies and "mc" in efficiencies:
        eff_data = efficiencies["data"]["efficiency"]
        eff_mc = efficiencies["mc"]["efficiency"]
        err_data_dn, err_data_up = efficiencies["data"]["efficiency_err"]
        err_mc_dn, err_mc_up = efficiencies["mc"]["efficiency_err"]

        # SF and error propagation
        sf_val = eff_data / eff_mc
        sf_err_dn = sf_val * np.sqrt((err_data_dn / eff_data) ** 2 + (err_mc_up / eff_mc) ** 2)
        sf_err_up = sf_val * np.sqrt((err_data_up / eff_data) ** 2 + (err_mc_dn / eff_mc) ** 2)
        sf_yerr = np.stack((sf_err_dn, sf_err_up), axis=0)

        h = efficiencies["data"]["hist"]
        bin_centers = h.axes[args.variable].centers
        bin_widths = h.axes[args.variable].edges[1:] - h.axes[args.variable].edges[:-1]

        # Create scale factor plot
        fig2, ax2 = plt.subplots(figsize=(8, 6))
        # Plot central value
        ax2.plot(
            bin_centers,
            sf_val,
            "o",
            color="black",
            label="Scale Factor (Data / MC)",
        )

        # Plot error boxes
        ax2.bar(
            bin_centers,
            height=sf_err_up + sf_err_dn,
            bottom=sf_val - sf_err_dn,
            width=bin_widths,
            color="red",
            alpha=0.3,
            align="center",
            label="SF stat. unc.",
            edgecolor="red",
            linewidth=0,
        )


        ax2.axhline(1.0, color="gray", linestyle="--", linewidth=1)
        ax2.set_ylim(0.0, 2.0)
        ax2.set_ylabel("Scale factor")
        ax2.set_xlabel(variable_inst.x_title)
        ax2.legend(loc="best", fontsize=9)
        ax2.grid(True, linestyle="--", alpha=0.4)

        # # set labels
        # mplhep.cms.label(ax=plt.gca(), fontsize=22, llabel="Work in progress")
        # plt.ylabel("Scale Factor")
        # plt.xlabel(variable_inst.x_title)

        # # draw legend
        # plt.legend(ncol=1, loc="upper right")

        sf_plot_file = args.output_filename.replace(".png", "_sf.png")
        fig2.savefig(sf_plot_file)
        print(f"Saved scale factor plot to {sf_plot_file}")
    else:
        print("Skipping scale factor plot: 'data' or 'mc' efficiency missing.")

