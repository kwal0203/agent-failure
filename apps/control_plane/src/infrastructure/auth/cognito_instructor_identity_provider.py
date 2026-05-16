from dataclasses import dataclass

from apps.control_plane.src.application.instructor_provisioning.ports import (
    InstructorIdentityProviderPort,
)
from apps.control_plane.src.application.instructor_provisioning.types import (
    InstructorIdentityResult,
)


@dataclass(frozen=True)
class CognitoInstructorIdentitySettings:
    enabled: bool
    user_pool_id: str
    region: str
    instructor_group_name: str


class NoopInstructorIdentityProvider(InstructorIdentityProviderPort):
    def ensure_instructor_group_membership(
        self, *, email: str, create_user_if_missing: bool
    ) -> InstructorIdentityResult:
        _ = email, create_user_if_missing
        raise ValueError("Instructor identity provider is not configured.")


class CognitoInstructorIdentityProvider(InstructorIdentityProviderPort):
    def __init__(self, settings: CognitoInstructorIdentitySettings) -> None:
        self._settings = settings

    def ensure_instructor_group_membership(
        self, *, email: str, create_user_if_missing: bool
    ) -> InstructorIdentityResult:
        import boto3  # type: ignore[import-untyped]
        from botocore.exceptions import ClientError  # type: ignore[import-untyped]

        client = boto3.client("cognito-idp", region_name=self._settings.region)

        user_created = False
        invite_sent = False
        user_id: str | None = None
        cognito_username: str | None = None
        try:
            existing = client.admin_get_user(
                UserPoolId=self._settings.user_pool_id,
                Username=email,
            )
            cognito_username = str(existing.get("Username") or email)
            user_id = cognito_username
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code != "UserNotFoundException":
                raise ValueError("Failed to query instructor account.") from exc
            list_result = client.list_users(
                UserPoolId=self._settings.user_pool_id,
                Filter=f'email = "{email}"',
                Limit=1,
            )
            users = list_result.get("Users") or []
            if users:
                cognito_username = str(users[0].get("Username") or email)
                user_id = cognito_username
            else:
                if not create_user_if_missing:
                    raise ValueError(
                        "Instructor account not found; create_user_if_missing=false."
                    ) from exc
                try:
                    created = client.admin_create_user(
                        UserPoolId=self._settings.user_pool_id,
                        Username=email,
                        DesiredDeliveryMediums=["EMAIL"],
                        UserAttributes=[
                            {"Name": "email", "Value": email},
                            {"Name": "email_verified", "Value": "true"},
                        ],
                    )
                    user_created = True
                    invite_sent = True
                    cognito_username = str(
                        created.get("User", {}).get("Username") or email
                    )
                    user_id = cognito_username
                except ClientError as create_exc:
                    raise ValueError(
                        "Failed to create instructor account."
                    ) from create_exc

        try:
            client.admin_add_user_to_group(
                UserPoolId=self._settings.user_pool_id,
                Username=cognito_username or email,
                GroupName=self._settings.instructor_group_name,
            )
        except ClientError as exc:
            raise ValueError("Failed to assign instructor group.") from exc

        return InstructorIdentityResult(
            email=email,
            user_created=user_created,
            invite_sent=invite_sent,
            group_assigned=True,
            user_id=user_id or email,
        )
