"""The buyer-tier rule shared by Orders, Sales leads and Marketing audiences: a tier is only
meaningful on a CSD or GeM record, and only one of its own values. Used as a backstop so a bad
tier/market combination can never be written, no matter which write path it comes through."""

CSD_TIERS_BY_MARKET = {
    "csd": {"retailer", "end"},
    "gem": {"vendor", "customer"},
}


def valid_csd_tier(market: str | None, csd_tier: str | None) -> bool:
    if csd_tier is None:
        return True
    return csd_tier in CSD_TIERS_BY_MARKET.get(market or "", set())
