# AI Assistance and Development Log

This log records AI assistance used during development and follow-up maintenance. AI output is treated as implementation assistance; the project owner is responsible for reviewing the final code and behavior.

## Tools Used

- **Cascade (Claude-powered assistant):** Used during the initial application build for implementation ideas, debugging, and interface work, as recorded in the original development notes.
- **Codex:** Used for follow-up review and changes to settings, dashboard summaries, Gmail account handling, dependency documentation, and this log.

## Initial Development

AI assistance contributed to the Flask and SQLite application, its Jinja templates, customer and transaction screens, dashboard, login flow, and Gmail integration. The project uses Flask-rendered templates and Tailwind CSS via CDN to keep local setup simple.

The owner chose SQLite for local data storage and Flask/Jinja templates rather than a separate JavaScript frontend framework.

## OAuth Debugging Notes

During local Gmail OAuth development, the authorization state and PKCE code verifier were not reliably available in the callback when the app was accessed through different local hostnames. Attempts to store or pickle the OAuth `Flow` object in the browser session failed; the object contains non-picklable state.

The local-development workaround stores each pending flow in a server-memory dictionary keyed by OAuth state, then retrieves it in the callback. This supports a single running app process. Restarting the process or routing the callback to a different worker loses the pending flow, so a deployed multi-worker app should use shared server-side state storage.

## Follow-up Changes

- Removed reminder threshold settings because no automatic reminder scheduler used them. Manual reminders sent from a customer page remain available.
- Changed dashboard credit and payment summaries from a rolling seven-day period to the current calendar month.
- Updated Gmail setup to show the connected Google account and let an app user switch accounts. OAuth tokens are stored per app user so one user's Gmail connection does not replace another's.
- Added `OAUTH_REDIRECT_URI` configuration for deployments that use a public HTTPS callback. The default remains the local development callback.
- Added a demo sender account and copy controls to the Gmail setup page for testing, at the owner's request. The demo credentials are intentionally not repeated in this log.
- Declared directly imported `google-auth` and Werkzeug dependencies in `requirements.txt` and corrected the documented minimum Python version to match Flask 3.
- Reorganized the Flask app into a package with an application factory, configuration, shared database/password helpers, feature-based blueprints, and package-local templates. Updated the seed script to use the shared database setup.
- Replaced new password hashes with Werkzeug's password-hashing helpers and added successful-login migration for existing SHA-256 hashes.
- Added a confirmed customer deletion action that also removes the customer's transaction history.

## Deployment and Review Notes

- Google Cloud controls which accounts may authorize Gmail. External audience alone does not make an app available to everyone: the OAuth app must be published, and public use of the sensitive `gmail.send` scope requires Google's verification. The project owner must complete these steps in Google Cloud Console.
- For deployment, set `OAUTH_REDIRECT_URI` to the public HTTPS callback and register the exact same URI in the Google OAuth client.
- The demo Gmail credentials are displayed in the Gmail setup page for testing. Use a disposable test account and rotate its password after review; do not use a personal or production account for this purpose.
- Dependency declarations were reviewed against Python imports. A clean-environment installation has not been performed as part of this log update.
