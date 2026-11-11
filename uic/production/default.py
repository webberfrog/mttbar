# coding: utf-8

"""
Wrappers for some default sets of producers.
"""

from columnflow.production import Producer, producer
from columnflow.production.categories import category_ids
from columnflow.util import maybe_import

from mtt.production.features import features
from mtt.production.weights import weights
from mtt.production.ttbar_reco import ttbar
from uic.production.ttbar_reco_uic import uic
from uic.production.top_width_observables import top_width_observables

ak = maybe_import("awkward")


@producer(
    uses={
        features, category_ids, weights, ttbar, uic, top_width_observables,
    },
    produces={
        features, category_ids, weights, ttbar, uic, top_width_observables,
    },
)
def default(self: Producer, events: ak.Array, **kwargs) -> ak.Array:

    # ttbar reconstruction
    events = self[ttbar](events, **kwargs)

    # features
    events = self[features](events, **kwargs)

    # weights
    events = self[weights](events, **kwargs)

    # category ids
    events = self[category_ids](events, **kwargs)

    # uic entanglement and asymmetry
    events = self[uic](events, **kwargs)

    # top-width observables (m_lb, DeltaR_min); need the TTbar.* columns of `uic`
    events = self[top_width_observables](events, **kwargs)

    return events
