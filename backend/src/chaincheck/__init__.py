"""ChainCheck backend.

Sierra chain controls, closures, incidents, pass forecasts, and resort snow,
unified behind one client-agnostic API. Road data comes from the ``ca_roads``
feed layer (shared with ca-roads-mcp); everything here adds the snow-trip
view: corridors, passes, forecasts, tier-change watching, and push.
"""

__version__ = "0.1.0"

USER_AGENT = "chaincheck/0.1 (+https://github.com/nicglazkov/chaincheck)"
