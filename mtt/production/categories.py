# coding: utf-8

"""
Categorizers related to defining category masks following the production step.
"""
from functools import partial

from columnflow.columnar_util import Route
from columnflow.util import maybe_import
from columnflow.categorization import Categorizer, categorizer

from mtt.categorization.util import make_categorizer_and, make_categorizer_not, make_categorizer_range

np = maybe_import("numpy")
ak = maybe_import("awkward")


# -- basic categorizers for event categorization

# pass/fail chi2 criterion
@categorizer(uses={"TTbar.chi2"})
def sel_chi2pass(
    self: Categorizer,
    events: ak.Array,
    **kwargs,
) -> ak.Array:
    """Select only events with a chi2 lower than a configured threshold."""
    chi2_max = self.config_inst.x.categorization.chi2_max
    mask = Route("TTbar.chi2").apply(events) < chi2_max
    return events, mask


sel_chi2fail = make_categorizer_not("sel_chi2fail", sel_chi2pass)


# |cos(theta*)| regions
make_categorizer_range_acts = partial(
    make_categorizer_range,
    route="TTbar.cos_theta_star",
    route_func=abs,
    uses={"TTbar.cos_theta_star"},
)
# TODO: make configurable
acts_bins = [0.0, 0.5, 0.7, 0.9, 1.0]
acts_names = ["0_5", "5_7", "7_9", "9_1"]
sels_acts = tuple(
    make_categorizer_range_acts(
        name=f"sel_acts_{acts_name}",
        min_val=min_val,
        max_val=max_val,
    )
    for min_val, max_val, acts_name in zip(acts_bins[:-1], acts_bins[1:], acts_names)
)


# entanglement regions of Fig. 131 of AN2023_120 (see `mtt.config.categories.add_categories_entanglement`);
# these overlap with each other by design. Reconstruction failures (EMPTY_FLOAT) fall outside every range.
_sel_ent_mtt_gt800 = make_categorizer_range(
    "_sel_ent_mtt_gt800", route="TTbar.mass", min_val=800.0, max_val=np.inf, uses={"TTbar.mass"},
)
_sel_ent_mtt_gt1000 = make_categorizer_range(
    "_sel_ent_mtt_gt1000", route="TTbar.mass", min_val=1000.0, max_val=np.inf, uses={"TTbar.mass"},
)
_sel_ent_acts_lt0p4 = make_categorizer_range_acts(name="_sel_ent_acts_lt0p4", min_val=0.0, max_val=0.4)

sel_ent_pt_lt50 = make_categorizer_range(
    "sel_ent_pt_lt50", route="TTbar.top_pt", min_val=0.0, max_val=50.0, uses={"TTbar.top_pt"},
)
sel_ent_mtt_lt400 = make_categorizer_range(
    "sel_ent_mtt_lt400", route="TTbar.mass", min_val=0.0, max_val=400.0, uses={"TTbar.mass"},
)
sel_ent_mtt_gt800_acts_lt0p4 = make_categorizer_and(
    "sel_ent_mtt_gt800_acts_lt0p4", {_sel_ent_mtt_gt800, _sel_ent_acts_lt0p4},
)
sel_ent_mtt_gt1000_acts_lt0p4 = make_categorizer_and(
    "sel_ent_mtt_gt1000_acts_lt0p4", {_sel_ent_mtt_gt1000, _sel_ent_acts_lt0p4},
)

