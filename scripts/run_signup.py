import os

from media_signup.creator_delivery import AssetStore, CreatorDeliveryWorkflow, SignupRequest
from media_signup.infrai_email import InfraiEmail


def main() -> None:
    recipient = os.environ.get("DEMO_CREATOR_EMAIL", "")
    secret = os.environ.get("VERIFICATION_SIGNING_SECRET", "")
    if not recipient or not secret:
        raise RuntimeError("DEMO_CREATOR_EMAIL and VERIFICATION_SIGNING_SECRET are required")
    workflow = CreatorDeliveryWorkflow(AssetStore(), InfraiEmail(), "http://localhost:8000", secret)
    result = workflow.start_signup(
        SignupRequest(
            creator_id="creator-42",
            email=recipient,
            asset_id="trailer-2026",
            source_url="https://media.example/trailer.mov",
        )
    )
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()

