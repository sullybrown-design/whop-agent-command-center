# Deployment: Render blueprint

The repository includes a Dockerfile and Render Blueprint. **This does not deploy the app automatically.** Connect the GitHub repository in Render and apply the blueprint. Confirm billing and service settings before deploying.

1. Visit https://dashboard.render.com/blueprints and choose New Blueprint Instance.
2. Select `sullybrown-design/whop-agent-command-center`.
3. Review the proposed service and pricing. `render.yaml` specifies a paid starter instance; change the plan if needed.
4. Deploy and wait for the health check to pass.
5. The app uses HTTP Basic authentication for all routes except `/api/health`. Username is `admin`; password is the generated `ADMIN_TOKEN` environment variable. Find it securely in Render's environment settings. Never share or commit it.
6. Check `/api/health` and sign in to the dashboard.

**Storage:** SQLite jobs and review history now survive process restarts when DATABASE_PATH points to persistent storage. The default /app/data path is writable in the image, but Render container filesystems are ephemeral across redeployments. Provision a persistent disk through Render, set DATABASE_PATH to its writable mount (for example /var/data/jobs.sqlite3), and maintain backups before relying on saved jobs. Disk provisioning can add cost and is not included automatically in the blueprint. Use one app instance with SQLite. This does not persist LangGraph checkpoints or connect publishing/payout accounts.

## Next production requirements
- Production database operations, backups, run state and LangGraph checkpointing
- HTTPS and stronger identity/access controls
- Structured logs, alerting, backups and rate limiting
- API credentials in managed secrets only
- Rights verification and explicit review before publishing
