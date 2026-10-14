#!/usr/bin/env python3
"""Hide a published Facebook page post (reversible: is_hidden=true).
Usage: POST_ID=<page_post_id> python scripts/hide_post.py
To show it again, run with UNHIDE=1."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import publish_social as ps  # reuses graph() and page_token(), which keep the token out of logs

post_id = os.environ.get("POST_ID", "").strip()
if not post_id:
    sys.exit("POST_ID is required")
hide = os.environ.get("UNHIDE", "") not in ("1", "true")
try:
    res = ps.graph("POST", post_id, ps.page_token(), is_hidden="true" if hide else "false")
except Exception as e:  # graph() already scrubs tokens from the message
    print(f"::error::{ps.scrub(e)}")
    sys.exit(1)
print(f"::notice::{'hidden' if hide else 'unhidden'} {post_id} {res}")
