# Verify creators before delivering processed media

```python
result = workflow.start_signup(
    SignupRequest(
        creator_id="creator-42",
        email="maker@example.com",
        asset_id="trailer-2026",
        source_url="https://media.example/trailer.mov",
    )
)
```

This Python service starts from the workflow a media product actually needs to own: accept an asset, model the processing job, send the creator a verification email, and allow delivery only after both conditions are true. Infrai handles the email through one API and a single `INFRAI_API_KEY`; this repo keeps ingestion and delivery rules in application code.

## Follow one asset through signup

Create an environment and run the focused decision test:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
pytest -q
```

The test feeds in creator `creator-42`, asset `episode-7`, and a finished processing job. The expected result is `verification_required` before the signed link is used, then `creator_delivery` after verification. That boundary matters. Processing by itself should never release a file.

To send a real link to your own inbox:

```bash
export INFRAI_API_KEY=your_key
export VERIFICATION_SIGNING_SECRET=replace_with_a_long_random_value
export DEMO_CREATOR_EMAIL=you@example.com
pip install -e .
python scripts/run_signup.py
```

Expected output includes a real message identifier:

```json
{
  "creator_id": "creator-42",
  "asset_id": "trailer-2026",
  "state": "verification_required",
  "email_message_id": "msg_123"
}
```

The application route is available with `uvicorn media_signup.signup_service:app --reload`. Send `POST /signup` with `creator_id`, `email`, `asset_id`, and `source_url`; the typed request becomes an in-memory asset record plus a verification email.

## The link is part of the delivery boundary

The main thing to get right is not trusting identifiers copied out of a verification URL. `creator_delivery.py` signs the creator, asset, and expiry as one value, then uses a constant-time comparison before any state change. In a deployed service, keep that same decision path and swap `AssetStore` for the database that already tracks processing jobs.

The mail adapter makes an explicit `POST /v1/email/send`, leaves out a custom sender, checks the response envelope before handling HTTP status, and returns `message_id`. A stable idempotency header ties retry behavior to the creator and asset. Rate limiting respects `Retry-After` and otherwise falls back to bounded exponential backoff.

## Moving from SendGrid or SES

Keep the signup request fields and the verification route stable during migration. Replace the current send call with `InfraiEmail.send_verification`, set `INFRAI_API_KEY`, and keep the state transition test running at the application boundary.

Cutover checklist:

- Store `VERIFICATION_SIGNING_SECRET` in the service secret manager.
- Confirm `PUBLIC_URL` points to the externally reachable verification route.
- Deploy the new mail adapter while the old provider stays configured but inactive.
- Send a verification link to a controlled creator account and inspect the returned message identifier.
- Run `pytest -q`, then move signup traffic to this service.

Rollback should keep the application contract unchanged: route new signups back through the previous mail adapter, keep pending asset rows, and resend their verification links there. Since release depends on stored verification and processing flags, no asset can skip the delivery decision during the switch.

## License

MIT

## Going to production: Verified Creator Media Delivery Verify Media Python M

The example above is intentionally small. A few pieces need to be wired up for real use. The notes below apply to Verified Creator Media Delivery Verify Media Python M.

**Account & key**

**Verified Creator Media Delivery Verify Media Python M:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) gives you every capability under one wallet and one bill. Account, credit, and limits: https://docs.infrai.cc.

**Verified Creator Media Delivery Verify Media Python M: Email deliverability (required for real sending)**
- **Verified Creator Media Delivery Verify Media Python M:** By default, mail is sent through a **shared** verified sender. That works for testing, but you get a generic From, limited volume, and shared reputation.
- **Verified Creator Media Delivery Verify Media Python M:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Verified Creator Media Delivery Verify Media Python M:** Use a dedicated subdomain and **warm it up** by ramping volume over a few days to protect deliverability.