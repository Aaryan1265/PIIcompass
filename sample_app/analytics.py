"""SYNTHETIC analytics flow for the fictional MapleHealth portal.

Parsed, never executed. Streams online identifiers to a US analytics vendor.
"""


def track_pageview(request):
    """Send a page-view event to the analytics vendor (third country: US)."""
    mixpanel_client.track("page_view", {
        "ip": request.ip_address,
        "user_agent": request.user_agent,
        "device_id": request.device_id,
        "session_id": request.session_id,
        "geo_region": request.geo_region,
        "page_url": request.page_url,
    })
