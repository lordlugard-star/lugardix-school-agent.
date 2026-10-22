# Workflows

Sanitized n8n exports. Credential ids and names, instance and webhook ids, pinned test data, emails, phone numbers, chat ids, WhatsApp phone number ids, tokens and project URLs have been removed or masked.

| File | Role |
|---|---|
| `main-workflow.json` | WhatsApp Trigger, read-receipt filter, admin check, AI Agent with tools, replies, error branches |
| `send-message.json` | sub-workflow: send one email, then log it to `messages` |
| `send-bulk-to-parents.json` | sub-workflow: one email per parent row |
| `error-alerts.json` | Error Trigger and developer alert |

Placeholders to fill after importing: `REPLACE_ME` (credential and workflow ids), `<PROJECT_REF>`, `<PHONE_OR_ID>`, `user@example.com`.
