"""Constants for the Skylight API client library."""

BASE_URL = "https://app.ourskylight.com"
OAUTH_URL = "https://app.ourskylight.com/oauth/token"
OAUTH_AUTHORIZE_URL = "https://app.ourskylight.com/oauth/authorize"
# Skylight's OAuth server only allows one registered redirect URI, so it is
# always passed back as-is. The server never actually redirects there during
# a headless flow — the user copies the ?code=... value out of the address bar.
OAUTH_REDIRECT_URI = "https://ourskylight.com/welcome"
OAUTH_CLIENT_ID = "skylight-mobile"
OAUTH_SCOPE = "everything"
API_VERSION = "2026-05-01"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

# Chore status literals.
#
# Skylight spells a finished chore "complete". Note that list_items use
# "completed" — the two resources genuinely differ, so don't unify them.
CHORE_STATUS_COMPLETE = "complete"
CHORE_STATUS_PENDING = "pending"
# Statuses that count as done when *reading* the feed. Both spellings are
# accepted so an API-version change can't silently un-tick every chore.
CHORE_COMPLETE_STATUSES = frozenset({"complete", "completed"})

# Bound on the ETag response cache (see SkylightAPI._etags).
ETAG_CACHE_MAX_ENTRIES = 64
