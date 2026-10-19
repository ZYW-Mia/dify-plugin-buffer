# Privacy policy

This independent Buffer integration sends the parameters supplied to its tools to Buffer at `https://api.buffer.com`. OAuth authorization and token exchange use `https://auth.buffer.com`. Buffer and the destination social networks process content under their own terms and privacy policies.

The plugin accesses organization/channel information and post information as requested. Write operations transmit post text, public media URLs, scheduling choices, tags, and platform metadata to Buffer. Buffer and the destination network fetch media from the URLs supplied by the user; the plugin does not host or upload media.

Dify stores the configured personal API key, OAuth client credentials, and user OAuth token pair using the hosting instance's credential management. The plugin uses these credentials for API requests and returns refreshed tokens to Dify. A bounded in-memory cache retains refresh results for up to ten minutes to prevent concurrent use of a consumed refresh token within one worker; its keys are token fingerprints. It does not add a separate credential database, telemetry, analytics, or third-party logging service. Tool inputs and outputs may be retained in Dify execution histories under the instance operator's policies.

OAuth requests use `account:read`, `posts:read`, `posts:write`, and `offline_access`. OAuth state contains a timestamp, nonce, and integrity signature; no access token, refresh token, client secret, or PKCE verifier is put in the authorization URL.

Users can revoke the app in Buffer account settings and remove credentials from Dify. Deleting a post in Buffer does not guarantee removal of content already published on a social network. Contact the operator of your Dify instance for questions about its credential storage, execution history retention, and deletion procedures.
