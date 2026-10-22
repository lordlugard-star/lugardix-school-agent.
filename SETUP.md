# Setup and deployment notes

## Prerequisites

- A self-hosted n8n instance (published workflows, HTTPS URL).
- A Supabase project.
- A WhatsApp Business Cloud API app and number.
- An LLM API key for the n8n AI Agent node.
- An email credential (Gmail OAuth, or SMTP with an app password).
- A Telegram bot, used only for developer alerts.

## 1. Database

Run `database/schema.sql` in the Supabase SQL editor. Add a few synthetic rows to `admins`, `students`, `parents` and `student_parents`. Use inboxes you control for any rows you will send to.

## 2. Credentials (create in n8n)

| Credential | Used by |
|---|---|
| Supabase (service-role key) | admin check, lookups, message logging |
| WhatsApp Cloud API credentials the node asks for | WhatsApp Trigger and reply nodes |
| LLM provider | AI Agent chat model |
| Email (OAuth or SMTP) | send workflows |
| Telegram bot | developer alerts |

Never put secrets in prompts, expressions or workflow JSON.

## 3. Import and wire

1. Import each file from `workflows/`.
2. On every node, re-select the credential. Exports contain only placeholders.
3. In the agent's workflow-tool nodes, re-select the sub-workflows.
4. Re-check expressions that reference a node by name. Renaming a node breaks them.
5. Set the Error Workflow on each workflow under its settings.
6. Publish all workflows. Edits are drafts until published.

## 4. Test checklist

- Admin lookup returns the expected rows.
- A stranger's message gets the refusal and nothing else.
- Draft, YES, and an email arrives. The `messages` table gets one row with status `sent`.
- A deliberate failure (bad address) does not create a `sent` row.
- A tool failure produces a clean reply to the admin and an alert to the developer.
- A bulk draft, answered with NO, sends nothing.

## Known gotchas

- The Supabase ILIKE operator uses `*` as the wildcard, not `%`.
- A default value for an unset AI-filled field must be valid for the column type. A text placeholder fails on uuid columns.
- CHECK constraints are case-sensitive.
- Foreign-key columns need the referenced row's `id`, not another identifier.
- Telegram parses message text as Markdown. Characters such as `_` and `*` in alert text can cause the send to fail, so strip them.
- Test executions can send real messages. Use addresses you control.
