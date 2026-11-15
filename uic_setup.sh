# source this from the checkout: setup with uic_law.cfg and the output store shared between checkouts
source setup.sh dev
export LAW_CONFIG_FILE="$MTT_BASE/uic_law.cfg"
export CF_STORE_LOCAL="$(dirname "$MTT_BASE")/mtt_store"
