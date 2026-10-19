# OAuth implementation

Official protocol reference: https://developers.buffer.com/guides/authentication

The provider supports private/confidential Buffer app clients. A client ID and secret must be configured in Dify's OAuth client settings. Secrets are never returned as user credentials.

## PKCE and state

Dify's ToolProvider OAuth interface does not expose persistent session storage. A private client allows a stateless PKCE implementation that survives plugin process restarts and multiple workers:

1. Generate a cryptographically random 256-bit nonce and a Unix timestamp.
2. Sign timestamp, nonce, client ID, and the exact redirect URI using HMAC-SHA256 keyed by the server-side client secret, with a `state` purpose prefix and length-delimited components.
3. Derive a separate 256-bit code verifier using HMAC-SHA256 over the state, client ID, and redirect URI with a `pkce` purpose prefix.
4. Send only the base64url SHA256 hash of that verifier as the S256 challenge. Neither the client secret nor the verifier appears in the authorization URL.
5. On callback, verify the state signature and ten-minute lifetime, then reconstruct the verifier for token exchange. A small clock-skew allowance is permitted for timestamps ahead of the receiving worker.

The signature verifies integrity and binds the state to the client and redirect URI. It is not an independent browser session. The plugin relies on Dify's HttpOnly callback context cookie and single-use server context for browser/session handling, and on Buffer's single-use authorization code for exchange replay prevention. Do not expose this provider's callback methods as standalone HTTP endpoints outside Dify. This design has automated protocol tests; it has not received an independent security audit or live account validation.

## Token lifecycle

Token requests go to `https://auth.buffer.com/token` with form-encoded parameters. The access token, rotated refresh token, and absolute expiration (with a small safety margin) are returned to Dify. The plugin requires `offline_access` and rejects incomplete token responses instead of retaining an already consumed refresh token.

Buffer invalidates the previous refresh token after successful refresh and can revoke the grant if an old token is reused. No token request is automatically retried. The plugin merges concurrent refresh requests with the same token fingerprint within one worker and caches the resulting pair (or safe error) for ten minutes in memory, bounded to 512 entries. The fingerprint is HMAC-derived and contains no raw token. Separate processes and replicas do not share this cache. Dify is responsible for persisting returned credentials and coordinating refresh across those processes; verify this behavior on the target Dify deployment before concurrent production use. Tools never initiate refresh themselves. If a refresh response is lost or interrupted, reconnect the account.

## Sources

- https://developers.buffer.com/guides/authentication
- https://developers.buffer.com/guides/building-apps
- https://docs.dify.ai/en/develop-plugin/dev-guides-and-walkthroughs/tool-oauth
