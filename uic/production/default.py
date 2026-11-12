# coding: utf-8

"""
Wrappers for some default sets of producers.
"""

from columnflow.production import Producer, producer
from columnflow.production.categories import category_ids
from columnflow.util import maybe_import

from mtt.production.features import features
from mtt.production.weights import weights
from uic.production.ttbar_reco_uic import uic
from uic.production.top_width_observables import top_width_observables

ak = maybe_import("awkward")


@producer(
    uses={
        features, category_ids, weights, uic, top_width_observables,
    },
    produces={
        features, category_ids, weights, uic, top_width_observables,
    },
)
def default(self: Producer, events: ak.Array, **kwargs) -> ak.Array:

    # ttbar reconstruction + uic entanglement and asymmetry, in a single pass: `uic` contains the same
    # chi2 combinatorics as the `ttbar` producer and writes a superset of its TTbar.* columns, so running
    # both only repeated the (expensive) combinatorics. It runs first so that `category_ids` sees TTbar.*
    events = self[uic](events, **kwargs)

    # features
    events = self[features](events, **kwargs)

    # weights
    events = self[weights](events, **kwargs)

    # category ids
    events = self[category_ids](events, **kwargs)

    # top-width observables (m_lb, DeltaR_min); need the TTbar.* columns of `uic`
    events = self[top_width_observables](events, **kwargs)

    return events
