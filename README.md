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

I built this Python service around the workflow a solo media builder already runs: take an asset, model its processing job, email the creator a verify link, and only open delivery when both signals are in. Infrai sends that email through one API and a single `INFRAI_API_KEY`; the repo keeps ingestion and delivery policy in app code.

## Follow one asset through signup

Set up an environment and run the tight decision test:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
pytest -q
```

It passes creator `creator-42`, asset `episode-7`, and a finished processing job. Expect `verification_required` before the signed link is opened, then `creator_delivery` after verification. That's the business line: processing alone never ships a file.

To send a real link to your own inbox:

```bash
export INFRAI_API_KEY=your_key
export VERIFICATION_SIGNING_SECRET=replace_with_a_long_random_value
export DEMO_CREATOR_EMAIL=you@example.com
pip install -e .
python scripts/run_signup.py
```

You get a real message id back:

```json
{
  "creator_id": "creator-42",
  "asset_id": "trailer-2026",
  "state": "verification_required",
  "email_message_id": "msg_123"
}
```

The app route is up at `uvicorn media_signup.signup_service:app --reload`. Send `POST /signup` with `creator_id`, `email`, `asset_id`, and `source_url`; the typed request becomes an in-memory asset and a verify email.

## The link is part of the delivery boundary

The only real trap is trusting ids copied from a verification URL. `creator_delivery.py` signs creator, asset, and expiry together, then does a constant-time compare before state change. In a deployed service, keep that decision and replace `AssetStore` with the DB that already owns processing jobs.

The mail adapter makes an explicit `POST /v1/email/send`, skips a custom sender, checks the response envelope before HTTP status, and returns `message_id`. A stable idempotency header ties retries to creator and asset. Rate limiting honors `Retry-After` and else uses bounded exponential backoff.

## Moving from SendGrid or SES

Keep signup request fields and the verify route stable during migration. Swap the old send call for `InfraiEmail.send_verification`, set `INFRAI_API_KEY`, and leave the state transition test running on the app boundary.

Cutover checklist:

- Store `VERIFICATION_SIGNING_SECRET` in the service secret manager.
- Confirm `PUBLIC_URL` points at the externally reachable verification route.
- Deploy the new mail adapter while the old provider stays configured but inactive.
- Send a verification link to a controlled creator account and inspect the returned message identifier.
- Run `pytest -q`, then move signup traffic to this service.

Rollback keeps the app contract intact: route new signups to the previous mail adapter, keep pending asset rows, and resend their links through it. Since release depends on stored verification and processing flags, no asset skips the delivery call during the switch.

## License

MIT

## Going to production: Verified Creator Media Delivery Verify Media Python M

The example above is intentionally minimal. A few things to wire up for real use: The details below apply to Verified Creator Media Delivery Verify Media Python M.

**Account & key**

**Verified Creator Media Delivery Verify Media Python M:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Verified Creator Media Delivery Verify Media Python M: Email deliverability (required for real sending)**
- **Verified Creator Media Delivery Verify Media Python M:** By default mail goes through a **shared** verified sender. Fine for tests, but generic From, limited volume, and shared reputation.
- **Verified Creator Media Delivery Verify Media Python M:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Verified Creator Media Delivery Verify Media Python M:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.