from urllib.parse import parse_qs, urlparse

from media_signup.creator_delivery import AssetState, AssetStore, CreatorDeliveryWorkflow, SignupRequest


class RecordingEmail:
    def __init__(self) -> None:
        self.verification_url = ""

    def send_verification(self, *, to: str, verification_url: str, idempotency_key: str) -> str:
        self.verification_url = verification_url
        return "msg_123"


def test_processed_asset_waits_for_verified_creator_then_enters_delivery() -> None:
    email = RecordingEmail()
    workflow = CreatorDeliveryWorkflow(AssetStore(), email, "https://studio.example", "test-secret")  # type: ignore[arg-type]
    result = workflow.start_signup(
        SignupRequest(
            creator_id="creator-42",
            email="maker@example.com",
            asset_id="episode-7",
            source_url="https://media.example/episode-7.mov",
        )
    )

    assert result.state == "verification_required"
    assert workflow.complete_processing("episode-7").state is AssetState.VERIFICATION_REQUIRED

    query = parse_qs(urlparse(email.verification_url).query)
    delivered = workflow.verify_email(
        query["creator_id"][0],
        query["asset_id"][0],
        int(query["expires"][0]),
        query["signature"][0],
    )
    assert delivered.state is AssetState.CREATOR_DELIVERY

