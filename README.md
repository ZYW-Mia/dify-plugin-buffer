# Buffer for Dify

Community-maintained by **TenTen**.

A Dify Tool Plugin for turning approved content into social posts through Buffer's GraphQL API. Connect with Buffer OAuth 2.0 (PKCE S256) or a personal API key.

English · [Simplified Chinese](readme/README_zh_Hans.md) · [Japanese](readme/README_ja_JP.md)

Plugin labels, tool parameters, help text, and authorization fields support English, Simplified Chinese, and Japanese. Dify selects the interface language; tool identifiers and API values stay consistent across locales.

[Download v0.1.0](https://github.com/ZYW-Mia/dify-plugin-buffer/releases/tag/v0.1.0) · [Workflow template](https://github.com/ZYW-Mia/dify-plugin-buffer/blob/main/examples/buffer-social-copilot.yml) · [Template setup](https://github.com/ZYW-Mia/dify-plugin-buffer/blob/main/examples/README.md)

## Tools

| Tool | Purpose |
| --- | --- |
| `list_organizations` | Find the organizations available to the connected account. |
| `list_channels` | Find social accounts, their IDs, platform, timezone, and connection status. |
| `create_post` | Create a post; **defaults to an unpublished draft**. Supports queue, custom time, next slot, and immediate publishing. |
| `schedule_post` | Create a **new** scheduled post or add a new post to the queue. |
| `list_posts` | Query posts by organization, channel, lifecycle status, and date; supports cursor pagination. |
| `get_post` | Read one post, including publication status, URL, and publishing errors. |
| `update_post` | Edit a draft or scheduled post, or schedule an existing draft. Omitted fields preserve existing content and scheduling. |
| `delete_post` | Permanently delete a Buffer post or cancel its queued publication. |

Each write targets one channel. Use one invocation per platform/account when building a cross-platform workflow. Platform support, required media, and publishing permissions depend on Buffer and the connected account. Selecting `notification` requires a person to finish publishing after the reminder.

## Install

Requires Python 3.12 for development and Dify 1.9.0 or newer.

1. Download `buffer-0.1.0.difypkg` from [GitHub Releases](https://github.com/ZYW-Mia/dify-plugin-buffer/releases/tag/v0.1.0), then use Dify's **Plugins → Install from local package** flow. This development build is unsigned; installation depends on your instance's plugin verification policy.
2. Configure either OAuth or a personal API key in the Buffer tool provider.
3. Run `list_organizations`, then `list_channels`, to obtain IDs for your workflow.

This package uses the `TenTen/buffer` author namespace. When replacing an older
author namespace, install this package and reconnect Buffer before importing its
matching workflow template. Dify treats different author namespaces as separate plugins.

### OAuth setup

1. Open [Buffer Settings → API → App Clients](https://publish.buffer.com/settings/api) and create a **private/confidential** app client. This plugin uses a server-side client secret.
2. Enable `account:read`, `posts:read`, `posts:write`, and long-lived access (`offline_access`).
3. Open the Buffer plugin's OAuth client settings in Dify. Copy the **exact callback URL shown by Dify** into Buffer's registered redirect URIs. Buffer requires HTTPS, including for local development. Do not construct the callback path by hand.
4. Enter the Buffer `client_id` and `client_secret` in Dify's OAuth client settings, then choose **Authorize** and approve access in Buffer.

OAuth clients are configured per Dify instance; installing a package does not create a Buffer app or configure a shared Dify Cloud OAuth client. A publicly distributed Cloud integration needs its OAuth client configured by that service's administrator.

Buffer access tokens expire, and refresh tokens rotate after every successful refresh. The plugin returns the new token pair and an absolute expiry for Dify to persist. It coalesces concurrent refreshes of the same token within a plugin worker and briefly caches their result. It does not refresh inside tools or retry token requests. Separate processes or replicas still require shared refresh coordination in the hosting Dify deployment. Reconnect if a refresh is interrupted or the grant is revoked. See [OAuth implementation notes](docs/oauth.md).

### Personal API key

For your own account, create a key at [Buffer Settings → API](https://publish.buffer.com/settings/api) and enter it in the provider's **Personal API Key** field. A personal key is for personal workflows; use OAuth when other users connect their accounts.

## Workflow examples

### Import the reusable template

[Dify Content to Buffer](https://github.com/ZYW-Mia/dify-plugin-buffer/blob/main/examples/README.md) includes the importable [workflow DSL](https://github.com/ZYW-Mia/dify-plugin-buffer/blob/main/examples/buffer-social-copilot.yml). Choose Original Content or AI Assistant, optionally attach an image, then review the content and select a connected account and delivery method in one Human Input form. Maximum characters is optional; leaving it blank sets no drafting limit. The template supports drafts, queues, scheduling, and immediate publishing for X, Bluesky, and LinkedIn.

### Create a draft for review

```json
{
  "channel_id": "CHANNEL_ID_FROM_LIST_CHANNELS",
  "text": "Our new release is here!",
  "mode": "draft",
  "ai_assisted": true
}
```

`create_post` returns `post`, `post_id`, and `status`. Every tool emits a JSON result plus named Dify output variables. These are available directly to subsequent Workflow nodes.

### Schedule the approved draft

Use `update_post` to avoid creating a second copy:

```json
{
  "post_id": "POST_ID_FROM_CREATE_POST",
  "mode": "customScheduled",
  "due_at": "2026-11-01T18:00:00+08:00"
}
```

The timestamp must be in the future and include a timezone. The plugin converts it to `2026-11-01T10:00:00.000Z`. To create a new post directly at a scheduled time, use `schedule_post` with `channel_id`, `text`, `mode`, and `due_at`.

`addToQueue` uses the next available channel slot; `shareNext` puts the post at the front of the queue. Neither mode accepts `due_at`. `shareNow` is available in `create_post` and `update_post` and publishes immediately.

### Attach media

`assets_json` is a JSON-encoded string containing Buffer's asset array. For example, enter this as the field value:

```json
[{"image":{"url":"https://your-public-host.example/release.png","metadata":{"altText":"Release screenshot"}}}]
```

Media must already have a public HTTP(S) URL reachable by Buffer and the target network. The plugin does not upload Dify files or host media. Local paths, Dify file IDs, and private attachment URLs are not usable media sources. Videos use `{"video":{"url":"..."}}`; documents require `url`, `title`, and `thumbnailUrl`. Video thumbnails use `metadata.thumbnailOffset`, not `thumbnailUrl`.

`metadata_json` accepts the target service's `PostInputMetaData` object. For an Instagram feed image:

```json
{"instagram":{"type":"post","shouldShareToFeed":true}}
```

Use the [official reference](https://developers.buffer.com/reference.html) for each platform's options, including threads, first comments, reels, and Pinterest boards. A threaded post's top-level text must match its first thread item. Buffer validates platform-specific combinations. Link attachments and non-empty media assets are mutually exclusive.

### Edit without changing the schedule

Provide `post_id` and `text` to `update_post`. Leave `mode` at `keep`. Empty optional text is ignored; `clear_text=true` explicitly clears it. Omit `assets_json` and `tag_ids_json` to preserve them; `[]` explicitly clears them.

### Iterate over posts

Call `list_posts` with an `organization_id`, optional `channel_ids_json` (e.g. `["CHANNEL_ID"]`), `status`, and `first` (1–100, default 20). If `has_next_page` is true, pass `end_cursor` as `after` to the next call. Reset `after` when changing filters. `start_date` and `end_date` follow Buffer's created-at or due-at filtering semantics.

## Error behavior

HTTP errors, GraphQL `errors`, and typed mutation errors fail the Dify tool invocation so Workflow error handling can act on them. Rate-limit errors include `Retry-After` when available. The client does not automatically retry writes: a timeout can happen after a post has already been created. Inspect `list_posts` or `get_post` before retrying an ambiguous write.

`delete_post` removes the item from Buffer; it does not promise to remove content already published on the destination social network.

## Development and packaging

```sh
uv venv --python 3.12
uv pip install --python .venv/bin/python -r requirements-dev.txt
.venv/bin/python -m scripts.validate
.venv/bin/pytest -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python -m scripts.package
```

The local packaging script validates with the real Dify SDK and creates an unsigned ZIP in Dify's `.difypkg` format using a source allowlist. It excludes environments, secrets, caches, tests, and build scripts. The official CLI can also build it with `dify plugin package . -o dist/buffer-0.1.0.difypkg`.

For Dify remote debugging, copy `.env.example` to `.env`, fill in the host/port/debug key shown by Dify, and run `.venv/bin/python -m main`. OAuth client credentials belong in Dify's provider settings, not in source files.

For a read-only real API check, set `BUFFER_API_KEY` in your environment and run `.venv/bin/python -m scripts.smoke_test`. It lists organizations and channel counts without creating posts. This smoke script reads exported environment variables; it does not load `.env` itself.

## Verification status

The SDK loads all eight tools. Automated tests cover HTTP/GraphQL errors, safe draft defaults, edit preservation, pagination, timezone normalization, PKCE exchange, expiring/tampered state, token rotation, and a simulated tool lifecycle. Operations and generated inputs are checked against a focused snapshot of Buffer's official API contract retrieved on October 16, 2026.

Workflow previews have read real Buffer organizations and connected accounts in Dify Cloud. The current **TenTen 0.1.0** package still needs a fresh installation, OAuth reconnection, and end-to-end write verification under its new author namespace. See the remaining checks in the [manual integration checklist](docs/integration-checklist.md).

## Scope and Buffer Commit

Post analytics are intentionally outside this OAuth plugin's first release: [Buffer currently restricts metrics to personal API keys](https://developers.buffer.com/guides/post-metrics). There is no unsupported analytics tool or placeholder API call.

The included template uses the plugin as its tool layer: produce content → discover connected accounts → human review and delivery selection → execute the confirmed Buffer request.

[Buffer Commit](https://buffer.com/api/commit) runs October 28–November 13, 2026. Existing projects may enter, with work added during the contest window identified separately. The submission needs public availability, real Buffer API calls through OAuth, a demo, and the Buffer App Client ID. This repository does not register or submit a contest entry.

## License and privacy

MIT. See [LICENSE](LICENSE) and [PRIVACY.md](PRIVACY.md). This is an independent integration and is not an official Buffer product.

## Source and support

Source: [ZYW-Mia/dify-plugin-buffer](https://github.com/ZYW-Mia/dify-plugin-buffer). Report bugs or request help through [GitHub Issues](https://github.com/ZYW-Mia/dify-plugin-buffer/issues) or contact [yawen@dify.ai](mailto:yawen@dify.ai). Do not include tokens, client secrets, or private post content in public reports.
