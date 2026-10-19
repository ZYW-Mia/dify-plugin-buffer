# Dify Content to Buffer

Import `buffer-social-copilot.yml` into Dify Cloud after installing and authorizing the
Buffer plugin. Configure the OpenAI model with your workspace credentials. The
example preserves the OpenAI model selected in the existing workflow.
If that model is unavailable, choose an OpenAI model available in your workspace.

This template references the Buffer plugin published under the **TenTen** author
namespace. Install and authorize the matching plugin before importing the template.

1. Choose **Original Content** or **AI Assistant**. Enter the content or brief and
   optionally attach one JPG, PNG, or WebP image.
2. For AI generation, choose **Purpose** and language. Optionally enter
   **Maximum characters**. Leave it blank for no preset drafting limit.
   A positive number sets the AI character target. Purpose automatically
   controls the editorial voice. OpenAI produces one content asset in one call.
   Original Content bypasses OpenAI and preserves your wording.
3. Buffer discovers connected accounts. One **Human Input** form lets you edit the
   content, choose an account, and select **Save Draft**, **Add to Queue**,
   **Schedule**, or **Publish Now**. There is no second AI rewrite or second review.
4. Leave **Scheduled publish time** blank for Publish Now, Save Draft, and Add to
   Queue. Those methods ignore it. **Only Schedule requires a time**: enter
   `YYYY-MM-DD HH:mm` in the selected account's displayed Buffer time zone, or an ISO
   timestamp with an explicit offset. Missing, invalid, past, ambiguous, and
   nonexistent scheduled local times are rejected before any write.
5. **Confirm & Send to Buffer** sends exactly the reviewed text and image using the
   chosen account and delivery method. Cancel or a three-day timeout creates no new
   post. Write retries are disabled; inspect Buffer before retrying an uncertain result.

Maximum characters is a drafting preference. It does not impose an artificial
platform cap or truncate human edits. Buffer validates the real network and account
limits, including special URL, Unicode, and subscription rules. Long posts can still
be rejected by Buffer if the selected account does not support them. See
[Buffer's character-limit guide](https://developers.buffer.com/guides/character-limits.html).

Human Input currently provides Paragraph, Select, File, and File List fields; it has
no native date/time picker or conditional field visibility. The time field therefore
stays visible with clear Schedule-only instructions. A calendar/time picker would
require a Chatflow interactive form or a custom client.

The tools use the Buffer authorization configured in this workflow. Public Web App
visitors do not automatically supply their own Buffer connection. A public product
with separate visitor connections needs a per-user authorization integration.

All connected, unlocked accounts appear in the overview. This template delivers to
X, Bluesky, and LinkedIn. One execution sends one post to one account. The optional
image is passed to Buffer without model analysis; Buffer must be able to fetch Dify's
HTTPS file URL. Self-hosted deployments need externally reachable file URLs.

The workflow has 16 functional nodes (including the account-lookup iteration's two
internal nodes), one OpenAI call on the AI branch, one Human Input review, and four
English explanatory notes. The product example is Dify. This template is distributed
separately from the plugin package.
