# Manual integration checklist

The maintainer confirmed completion of real Dify installation, Buffer OAuth authorization, and real posting verification on October 20, 2026, and confirmed the Plugin Developer Agreement. These are maintainer-reported integration results; automated tests separately use HTTP mocks and an official documentation contract snapshot.

The release fix changes the internal author ID from `TenTen` to `tenten` to meet the daemon's lowercase identifier rules. The community author remains **TenTen**. Install and reconnect the matching package when migrating between author namespaces.

The following procedure is retained as a repeatable regression checklist. It is not a list of pending release gates. Use a test social channel for writes.

- Install the generated package into a running Dify instance and confirm all eight tools appear.
- Configure a private Buffer App Client and register the exact HTTPS callback URL displayed by Dify.
- Authorize in Dify; confirm organization and channel tools work through OAuth.
- Reject a separate consent request and verify a useful authorization error.
- Create a draft and verify its content in Buffer. Confirm it has not entered the publishing queue.
- Edit its text with `mode=keep`; verify the content changes without changing its scheduling state.
- Schedule that same draft with `update_post`, using a future timestamp with an explicit timezone. Confirm Buffer shows the intended local time and the same post ID.
- Create a separate post with `schedule_post(mode=addToQueue)` and verify its queue slot.
- Attach a public image and the target platform's required metadata. Inspect it in Buffer before publishing.
- Query more than one page with `list_posts` and use its returned cursor.
- Delete the test scheduled posts and verify they no longer appear in the queue.
- Allow a test OAuth token to expire; verify Dify persists the new refresh token and subsequent tool calls succeed. Verify simultaneous invocations do not reuse an old refresh token on the target deployment.
- Publish approved test content on a test social account and inspect `get_post` for `sent` and an external URL.
- Revoke access in Buffer and verify a reconnect error.

For Buffer Commit, retain evidence of real OAuth/API calls, make the integration publicly available during submission/judging, identify work completed during the October 28–November 13 build window, and supply the required app client ID and demo. Review current contest eligibility directly on the event page before submitting.
