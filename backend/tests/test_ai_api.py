import uuid

from sqlalchemy import select

from app.core.jwt import create_access_token
from app.models.organisation_membership import OrganisationMembership
from app.models.team import Team
from app.models.team_membership import TeamMembership
from app.models.user import User

pytest_plugins = ("tests.test_teams",)

from tests.test_teams import authenticate_as_owner, create_organisation


def test_classify_ticket_requires_authentication(client):
    response = client.post(
        f"/api/v1/organisations/{uuid.uuid4()}/ai/classify-ticket",
        json={
            "subject": "Wi-Fi is unavailable",
            "description": "The office network is not working.",
        },
    )

    assert response.status_code == 401


def test_classify_ticket_returns_suggestions(client):
    organisation = create_organisation(client)

    categories_url = f"/api/v1/organisations/{organisation['id']}/categories"

    category_response = client.post(
        categories_url,
        json={
            "name": "Network",
            "description": "Network and connectivity issues.",
        },
    )

    assert category_response.status_code == 201

    response = client.post(
        f"/api/v1/organisations/{organisation['id']}/ai/classify-ticket",
        json={
            "subject": "Company-wide Wi-Fi outage",
            "description": (
                "All employees cannot connect to Wi-Fi. "
                "The network is completely unavailable."
            ),
        },
    )

    assert response.status_code == 200

    result = response.json()

    assert result["category"]["category_name"] == "Network"
    assert result["impact"]["value"] == "HIGH"
    assert result["urgency"]["value"] == "HIGH"
    assert result["priority"] == "P1"
    assert result["requires_human_review"] is True
    assert result["category"]["confidence_level"] == "MODERATE"
    assert result["impact"]["confidence_level"] == "HIGH"
    assert result["urgency"]["confidence_level"] == "MODERATE"
    assert result["team"]["confidence_level"] == "LOW"


def test_classify_ticket_rejects_invalid_request(client):
    organisation = create_organisation(client)

    response = client.post(
        f"/api/v1/organisations/{organisation['id']}/ai/classify-ticket",
        json={
            "subject": "Hi",
            "description": "Issue",
        },
    )

    assert response.status_code == 422


def test_classification_does_not_use_another_organisations_categories(client):
    first_organisation = create_organisation(
        client,
        "First Organisation",
    )

    second_organisation = create_organisation(
        client,
        "Second Organisation",
    )

    # Add a category only to the second organisation.
    authenticate_as_owner(client, second_organisation["id"])

    category_response = client.post(
        f"/api/v1/organisations/{second_organisation['id']}/categories",
        json={
            "name": "Network",
            "description": "Network and connectivity issues.",
        },
    )

    assert category_response.status_code == 201

    # Authenticate as the owner of the first organisation.
    authenticate_as_owner(client, first_organisation["id"])

    response = client.post(
        f"/api/v1/organisations/{first_organisation['id']}/ai/classify-ticket",
        json={
            "subject": "Wi-Fi is unavailable",
            "description": "The office network connection is not working.",
        },
    )

    assert response.status_code == 200

    result = response.json()

    assert result["category"]["category_id"] is None
    assert result["category"]["category_name"] is None


def test_classify_ticket_rejects_inactive_organisation(client):
    organisation = create_organisation(
        client,
        "Suspended Organisation",
        status="SUSPENDED",
    )

    authenticate_as_owner(client, organisation["id"])

    response = client.post(
        f"/api/v1/organisations/{organisation['id']}/ai/classify-ticket",
        json={
            "subject": "Wi-Fi is unavailable",
            "description": "The office network is not working.",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "AI classification is unavailable for an inactive or suspended organisation."
    )


def test_classify_ticket_rejects_user_from_another_organisation(client):
    first_organisation = create_organisation(
        client,
        "First Organisation",
    )

    second_organisation = create_organisation(
        client,
        "Second Organisation",
    )

    # Authenticate as the owner of the first organisation.
    authenticate_as_owner(client, first_organisation["id"])

    # Attempt to access the second organisation's AI endpoint.
    response = client.post(
        f"/api/v1/organisations/{second_organisation['id']}/ai/classify-ticket",
        json={
            "subject": "Wi-Fi is unavailable",
            "description": "The office network is not working.",
        },
    )

    assert response.status_code == 403


def test_classify_ticket_rejects_inactive_membership(client):
    organisation = create_organisation(client)

    # Deactivate the owner's organisation membership.
    db = client.testing_session_local()

    try:
        membership = db.scalar(
            select(OrganisationMembership).where(
                OrganisationMembership.organisation_id == uuid.UUID(organisation["id"]),
                OrganisationMembership.role == "OWNER",
            )
        )

        assert membership is not None

        membership.is_active = False
        db.commit()
    finally:
        db.close()

    # Attempt AI classification with the now-inactive membership.
    response = client.post(
        f"/api/v1/organisations/{organisation['id']}/ai/classify-ticket",
        json={
            "subject": "Wi-Fi is unavailable",
            "description": "The office network is not working.",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "You do not have an active membership in this organisation."
    )


def authenticate_as_requester(client, organisation_id):
    db = client.testing_session_local()

    try:
        user = User(
            full_name="Test Requester",
            email=f"requester-{uuid.uuid4()}@example.com",
            password_hash="test-password-hash",
        )

        db.add(user)
        db.flush()

        membership = OrganisationMembership(
            organisation_id=uuid.UUID(organisation_id),
            user_id=user.id,
            role="REQUESTER",
            is_active=True,
        )

        db.add(membership)
        db.commit()

        token = create_access_token(str(user.id))

        client.headers.update({"Authorization": f"Bearer {token}"})

    finally:
        db.close()


def test_requester_can_use_ai_classification(client):
    organisation = create_organisation(client)

    authenticate_as_requester(client, organisation["id"])

    response = client.post(
        f"/api/v1/organisations/{organisation['id']}/ai/classify-ticket",
        json={
            "subject": "Wi-Fi is unavailable",
            "description": "The office network is not working.",
        },
    )

    assert response.status_code == 200
    assert response.json()["requires_human_review"] is True


def authenticate_as_agent(client, organisation_id):
    db = client.testing_session_local()

    try:
        user = User(
            full_name="Test Agent",
            email=f"agent-{uuid.uuid4()}@example.com",
            password_hash="test-password-hash",
        )

        db.add(user)
        db.flush()

        membership = OrganisationMembership(
            organisation_id=uuid.UUID(organisation_id),
            user_id=user.id,
            role="AGENT",
            is_active=True,
        )

        db.add(membership)
        db.commit()

        token = create_access_token(str(user.id))

        client.headers.update({"Authorization": f"Bearer {token}"})

    finally:
        db.close()


def test_agent_can_use_ai_classification(client):
    organisation = create_organisation(client)

    authenticate_as_agent(client, organisation["id"])

    response = client.post(
        f"/api/v1/organisations/{organisation['id']}/ai/classify-ticket",
        json={
            "subject": "Company-wide Wi-Fi outage",
            "description": (
                "All employees cannot connect to Wi-Fi. "
                "The network is completely unavailable."
            ),
        },
    )

    assert response.status_code == 200
    assert response.json()["requires_human_review"] is True


def authenticate_as_admin(client, organisation_id):
    db = client.testing_session_local()

    try:
        user = User(
            full_name="Test Admin",
            email=f"admin-{uuid.uuid4()}@example.com",
            password_hash="test-password-hash",
        )

        db.add(user)
        db.flush()

        membership = OrganisationMembership(
            organisation_id=uuid.UUID(organisation_id),
            user_id=user.id,
            role="ADMIN",
            is_active=True,
        )

        db.add(membership)
        db.commit()

        token = create_access_token(str(user.id))

        client.headers.update({"Authorization": f"Bearer {token}"})

    finally:
        db.close()


def test_admin_can_use_ai_classification(client):
    organisation = create_organisation(client)

    authenticate_as_admin(client, organisation["id"])

    response = client.post(
        f"/api/v1/organisations/{organisation['id']}/ai/classify-ticket",
        json={
            "subject": "Company-wide Wi-Fi outage",
            "description": (
                "All employees cannot connect to Wi-Fi. "
                "The network is completely unavailable."
            ),
        },
    )

    assert response.status_code == 200
    assert response.json()["requires_human_review"] is True


def test_classify_ticket_api_recommends_team_using_category_expertise(
    client,
):
    organisation = create_organisation(client)
    authenticate_as_owner(client, organisation["id"])

    categories_url = f"/api/v1/organisations/{organisation['id']}/categories"

    category_response = client.post(
        categories_url,
        json={
            "name": "Network",
            "description": "Network and connectivity issues.",
        },
    )

    assert category_response.status_code == 201

    db = client.testing_session_local()

    try:
        user = User(
            full_name="Network Expertise Agent",
            email=f"network-expertise-{uuid.uuid4()}@example.com",
            password_hash="test-password-hash",
        )
        db.add(user)
        db.flush()

        membership = OrganisationMembership(
            organisation_id=uuid.UUID(organisation["id"]),
            user_id=user.id,
            role="AGENT",
            is_active=True,
        )
        db.add(membership)
        db.flush()

        team = Team(
            organisation_id=uuid.UUID(organisation["id"]),
            name="Network Expertise Team",
            description="Handles Wi-Fi, VPN, DNS and network connectivity issues.",
            is_active=True,
        )
        db.add(team)
        db.flush()

        db.add(
            TeamMembership(
                organisation_id=uuid.UUID(organisation["id"]),
                team_id=team.id,
                organisation_membership_id=membership.id,
            )
        )

        db.commit()

    finally:
        db.close()

    response = client.post(
        f"/api/v1/organisations/{organisation['id']}/ai/classify-ticket",
        json={
            "subject": "Office Wi-Fi outage",
            "description": (
                "The office Wi-Fi and network connection are completely unavailable."
            ),
        },
    )

    assert response.status_code == 200

    result = response.json()

    assert result["category"]["category_name"] == "Network"
    assert result["team"]["team_name"] == "Network Expertise Team"
    assert result["team"]["confidence"] > 0
    assert result["requires_human_review"] is True
    assert result["category"]["confidence_level"] == "MODERATE"
    assert result["impact"]["confidence_level"] == "LOW"
    assert result["urgency"]["confidence_level"] == "MODERATE"
