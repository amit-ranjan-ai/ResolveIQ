import uuid
from types import SimpleNamespace

import pytest

from app.models.category import Category
from app.models.organisation import Organisation
from app.models.organisation_membership import OrganisationMembership
from app.models.team import Team
from app.models.team_membership import TeamMembership
from app.models.user import User
from app.services.ai.classification_service import (
    classify_ticket,
    suggest_team,
)
from app.services.ai.confidence import (
    calculate_category_confidence,
    calculate_field_confidence,
    get_confidence_level,
)
from app.services.ai.rule_based_classifier import (
    keyword_matches,
    suggest_category,
    suggest_impact,
    suggest_urgency,
)

pytest_plugins = ("tests.test_notifications",)


def make_category(name):
    return SimpleNamespace(
        id=uuid.uuid4(),
        name=name,
        is_active=True,
    )


def test_network_keywords_suggest_network_category():
    network = make_category("Network")

    result = suggest_category(
        subject="Office Wi-Fi is unavailable",
        description="The internet connection keeps timing out.",
        categories=[network],
    )

    assert result["category_id"] == network.id
    assert result["category_name"] == "Network"
    assert "wi-fi" in result["matched_keywords"]
    assert "internet" in result["matched_keywords"]
    assert result["confidence"] > 0


def test_category_matching_is_case_insensitive():
    network = make_category("Network")

    result = suggest_category(
        subject="VPN CONNECTION FAILURE",
        description="The NETWORK is unavailable.",
        categories=[network],
    )

    assert result["category_name"] == "Network"
    assert "vpn" in result["matched_keywords"]
    assert "network" in result["matched_keywords"]


def test_ambiguous_category_match_returns_low_confidence():
    network = make_category("Network")
    software = make_category("Software")

    result = suggest_category(
        subject="Network and application issue",
        description="Please investigate this problem.",
        categories=[network, software],
    )

    assert result["category_id"] == network.id
    assert result["confidence"] == 45
    assert result["matched_keywords"]


def test_ambiguous_category_selection_is_independent_of_input_order():
    network = make_category("Network")
    software = make_category("Software")

    first_result = suggest_category(
        subject="Network and application issue",
        description="Please investigate this problem.",
        categories=[network, software],
    )

    second_result = suggest_category(
        subject="Network and application issue",
        description="Please investigate this problem.",
        categories=[software, network],
    )

    assert first_result["category_name"] == "Network"
    assert second_result["category_name"] == "Network"
    assert first_result["confidence"] == second_result["confidence"]


def test_keyword_matching_uses_whole_words():
    matches = keyword_matches(
        "the internet connection is working",
        ["internet", "net"],
    )

    assert matches == ["internet"]


def test_partial_keyword_does_not_trigger_category_match():
    network = make_category("Network")

    result = suggest_category(
        subject="Networking discussion",
        description="Please review the networking configuration.",
        categories=[network],
    )

    assert result["category_id"] is None
    assert result["category_name"] is None
    assert result["confidence"] == 0
    assert result["matched_keywords"] == []


def test_security_category_wins_over_account_access_for_phishing():
    security = make_category("Security")
    account = make_category("Account & Access")

    result = suggest_category(
        subject="Suspicious phishing email received",
        description=(
            "I received a suspicious email asking me to verify "
            "my company password through an unknown link. "
            "I suspect it may be a phishing attempt."
        ),
        categories=[account, security],
    )

    assert result["category_id"] == security.id
    assert result["category_name"] == "Security"
    assert result["confidence"] == 75
    assert "phishing" in result["matched_keywords"]


def test_other_category_is_used_as_fallback():
    other = make_category("Other")

    result = suggest_category(
        subject="Unusual support request",
        description="Please investigate this issue.",
        categories=[other],
    )

    assert result["category_id"] == other.id
    assert result["category_name"] == "Other"
    assert result["confidence"] == 25
    assert result["matched_keywords"] == []


def test_no_matching_category_returns_empty_suggestion():
    result = suggest_category(
        subject="Unusual support request",
        description="Please investigate this issue.",
        categories=[],
    )

    assert result["category_id"] is None
    assert result["category_name"] is None
    assert result["confidence"] == 0


def test_empty_ticket_text_is_rejected():
    with pytest.raises(ValueError):
        suggest_category(
            subject="",
            description="",
            categories=[],
        )


def test_high_impact_is_detected():
    result = suggest_impact(
        subject="Production down",
        description="All users are unable to access the critical system.",
    )

    assert result["value"] == "HIGH"
    assert result["confidence"] == 80
    assert result["matched_keywords"]


def test_low_impact_is_detected():
    result = suggest_impact(
        subject="Minor issue",
        description="Only a single user is affected.",
    )

    assert result["value"] == "LOW"
    assert result["confidence"] > 0


def test_unknown_impact_returns_no_suggestion():
    result = suggest_impact(
        subject="Support request",
        description="Please check this when available.",
    )

    assert result["value"] is None
    assert result["confidence"] == 0


def test_conflicting_impact_indicators_return_low_confidence():
    result = suggest_impact(
        subject="Impact assessment",
        description="All users and a single user are affected.",
    )

    assert result["value"] == "HIGH"
    assert result["confidence"] == 40
    assert len(result["matched_keywords"]) == 1
    assert "Conflicting impact indicators" in result["explanation"]


def test_high_urgency_is_detected():
    result = suggest_urgency(
        subject="Production down",
        description="The business has stopped. Please resolve immediately.",
    )

    assert result["value"] == "HIGH"
    assert result["confidence"] == 75


def test_low_urgency_is_detected():
    result = suggest_urgency(
        subject="General question",
        description="Please provide information when possible.",
    )

    assert result["value"] == "LOW"
    assert result["confidence"] > 0


def test_unknown_urgency_returns_no_suggestion():
    result = suggest_urgency(
        subject="Support request",
        description="Please review this request.",
    )

    assert result["value"] is None
    assert result["confidence"] == 0


def test_conflicting_urgency_indicators_return_low_confidence():
    result = suggest_urgency(
        subject="Urgency assessment",
        description="Please resolve immediately, but when possible.",
    )

    assert result["value"] == "HIGH"
    assert result["confidence"] == 40
    assert len(result["matched_keywords"]) == 1
    assert "Conflicting urgency indicators" in result["explanation"]


def test_classification_does_not_calculate_priority_without_impact_or_urgency(
    db_session_factory,
):
    with db_session_factory() as db:
        organisation = Organisation(
            name="Insufficient Information Organisation",
            slug=f"insufficient-info-{uuid.uuid4().hex[:8]}",
            status="ACTIVE",
        )

        db.add(organisation)
        db.commit()

        result = classify_ticket(
            db=db,
            organisation_id=organisation.id,
            subject="Support request",
            description="Please review this request.",
        )

        assert result["impact"]["value"] is None
        assert result["urgency"]["value"] is None
        assert result["priority"] is None
        assert result["requires_human_review"] is True


def test_classification_uses_only_active_categories_from_organisation(
    db_session_factory,
):
    with db_session_factory() as db:
        organisation_one = Organisation(
            name="AI Test Organisation One",
            slug=f"ai-test-one-{uuid.uuid4().hex[:8]}",
            status="ACTIVE",
        )

        organisation_two = Organisation(
            name="AI Test Organisation Two",
            slug=f"ai-test-two-{uuid.uuid4().hex[:8]}",
            status="ACTIVE",
        )

        db.add_all([organisation_one, organisation_two])
        db.flush()

        network_category = Category(
            organisation_id=organisation_one.id,
            name="Network",
            is_active=True,
        )

        inactive_category = Category(
            organisation_id=organisation_one.id,
            name="Hardware",
            is_active=False,
        )

        other_organisation_category = Category(
            organisation_id=organisation_two.id,
            name="Software",
            is_active=True,
        )

        db.add_all(
            [
                network_category,
                inactive_category,
                other_organisation_category,
            ]
        )
        db.commit()

        result = classify_ticket(
            db=db,
            organisation_id=organisation_one.id,
            subject="Office Wi-Fi is unavailable",
            description="The internet connection is failing.",
        )

        assert result["category"]["category_id"] == network_category.id
        assert result["category"]["category_name"] == "Network"
        assert result["category"]["category_id"] != inactive_category.id
        assert result["category"]["category_id"] != other_organisation_category.id
        assert result["requires_human_review"] is True


def test_suggest_team_returns_only_eligible_active_team(
    db_session_factory,
):
    with db_session_factory() as db:
        organisation = Organisation(
            name="Team Recommendation Organisation",
            slug=f"team-ai-{uuid.uuid4().hex[:8]}",
            status="ACTIVE",
        )
        db.add(organisation)
        db.flush()

        user = User(
            full_name="AI Agent",
            email=f"ai-agent-{uuid.uuid4()}@example.com",
            password_hash="test-password-hash",
        )
        db.add(user)
        db.flush()

        membership = OrganisationMembership(
            organisation_id=organisation.id,
            user_id=user.id,
            role="AGENT",
            is_active=True,
        )
        db.add(membership)
        db.flush()

        team = Team(
            organisation_id=organisation.id,
            name="Network Support",
            is_active=True,
        )
        db.add(team)
        db.flush()

        team_membership = TeamMembership(
            organisation_id=organisation.id,
            team_id=team.id,
            organisation_membership_id=membership.id,
        )
        db.add(team_membership)
        db.commit()

        result = suggest_team(
            db=db,
            organisation_id=organisation.id,
        )

        assert result["team_id"] == team.id
        assert result["team_name"] == "Network Support"
        assert result["confidence"] == 60
        assert "only active team" in result["explanation"]


def test_suggest_team_rejects_inactive_agent_membership(
    db_session_factory,
):
    with db_session_factory() as db:
        organisation = Organisation(
            name="Inactive Agent Organisation",
            slug=f"inactive-agent-{uuid.uuid4().hex[:8]}",
            status="ACTIVE",
        )
        db.add(organisation)
        db.flush()

        user = User(
            full_name="Inactive AI Agent",
            email=f"inactive-agent-{uuid.uuid4()}@example.com",
            password_hash="test-password-hash",
        )
        db.add(user)
        db.flush()

        membership = OrganisationMembership(
            organisation_id=organisation.id,
            user_id=user.id,
            role="AGENT",
            is_active=False,
        )
        db.add(membership)
        db.flush()

        team = Team(
            organisation_id=organisation.id,
            name="Inactive Agent Team",
            is_active=True,
        )
        db.add(team)
        db.flush()

        db.add(
            TeamMembership(
                organisation_id=organisation.id,
                team_id=team.id,
                organisation_membership_id=membership.id,
            )
        )
        db.commit()

        result = suggest_team(
            db=db,
            organisation_id=organisation.id,
        )

        assert result["team_id"] is None
        assert result["team_name"] is None
        assert result["confidence"] == 0
        assert "No active team" in result["explanation"]


def test_suggest_team_rejects_inactive_team(db_session_factory):
    with db_session_factory() as db:
        organisation = Organisation(
            name="Inactive Team Organisation",
            slug=f"inactive-team-{uuid.uuid4().hex[:8]}",
            status="ACTIVE",
        )
        db.add(organisation)
        db.flush()

        user = User(
            full_name="Active AI Agent",
            email=f"active-agent-{uuid.uuid4()}@example.com",
            password_hash="test-password-hash",
        )
        db.add(user)
        db.flush()

        membership = OrganisationMembership(
            organisation_id=organisation.id,
            user_id=user.id,
            role="AGENT",
            is_active=True,
        )
        db.add(membership)
        db.flush()

        team = Team(
            organisation_id=organisation.id,
            name="Inactive Support Team",
            is_active=False,
        )
        db.add(team)
        db.flush()

        db.add(
            TeamMembership(
                organisation_id=organisation.id,
                team_id=team.id,
                organisation_membership_id=membership.id,
            )
        )
        db.commit()

        result = suggest_team(
            db=db,
            organisation_id=organisation.id,
        )

        assert result["team_id"] is None
        assert result["team_name"] is None
        assert result["confidence"] == 0
        assert "No active team" in result["explanation"]


def test_suggest_team_rejects_owner_membership(db_session_factory):
    with db_session_factory() as db:
        organisation = Organisation(
            name="Owner Eligibility Organisation",
            slug=f"owner-eligibility-{uuid.uuid4().hex[:8]}",
            status="ACTIVE",
        )
        db.add(organisation)
        db.flush()

        user = User(
            full_name="Organisation Owner",
            email=f"owner-{uuid.uuid4()}@example.com",
            password_hash="test-password-hash",
        )
        db.add(user)
        db.flush()

        membership = OrganisationMembership(
            organisation_id=organisation.id,
            user_id=user.id,
            role="OWNER",
            is_active=True,
        )
        db.add(membership)
        db.flush()

        team = Team(
            organisation_id=organisation.id,
            name="Owner Team",
            is_active=True,
        )
        db.add(team)
        db.flush()

        db.add(
            TeamMembership(
                organisation_id=organisation.id,
                team_id=team.id,
                organisation_membership_id=membership.id,
            )
        )
        db.commit()

        result = suggest_team(
            db=db,
            organisation_id=organisation.id,
        )

        assert result["team_id"] is None
        assert result["confidence"] == 0
        assert "No active team" in result["explanation"]


def test_suggest_team_abstains_when_multiple_teams_are_eligible(
    db_session_factory,
):
    with db_session_factory() as db:
        organisation = Organisation(
            name="Multiple Teams Organisation",
            slug=f"multiple-teams-{uuid.uuid4().hex[:8]}",
            status="ACTIVE",
        )
        db.add(organisation)
        db.flush()

        teams = []

        for index in range(2):
            user = User(
                full_name=f"AI Agent {index}",
                email=f"multi-agent-{uuid.uuid4()}@example.com",
                password_hash="test-password-hash",
            )
            db.add(user)
            db.flush()

            membership = OrganisationMembership(
                organisation_id=organisation.id,
                user_id=user.id,
                role="AGENT",
                is_active=True,
            )
            db.add(membership)
            db.flush()

            team = Team(
                organisation_id=organisation.id,
                name=f"Support Team {index}",
                is_active=True,
            )
            db.add(team)
            db.flush()

            db.add(
                TeamMembership(
                    organisation_id=organisation.id,
                    team_id=team.id,
                    organisation_membership_id=membership.id,
                )
            )

            teams.append(team)

        db.commit()

        result = suggest_team(
            db=db,
            organisation_id=organisation.id,
        )

        assert len(teams) == 2
        assert result["team_id"] is None
        assert result["team_name"] is None
        assert result["confidence"] == 0
        assert "Multiple eligible teams" in result["explanation"]


def test_suggest_team_recommends_team_matching_category_expertise(
    db_session_factory,
):
    with db_session_factory() as db:
        organisation = Organisation(
            name="Team Expertise Organisation",
            slug=f"team-expertise-{uuid.uuid4().hex[:8]}",
            status="ACTIVE",
        )
        db.add(organisation)
        db.flush()

        team_data = [
            (
                "Network Support",
                "Handles Wi-Fi, VPN, DNS and network connectivity issues.",
            ),
            (
                "Hardware Support",
                "Handles laptop, desktop, printer and hardware issues.",
            ),
        ]

        teams = []

        for index, (team_name, description) in enumerate(team_data):
            user = User(
                full_name=f"Expertise Agent {index}",
                email=f"expertise-agent-{uuid.uuid4()}@example.com",
                password_hash="test-password-hash",
            )
            db.add(user)
            db.flush()

            membership = OrganisationMembership(
                organisation_id=organisation.id,
                user_id=user.id,
                role="AGENT",
                is_active=True,
            )
            db.add(membership)
            db.flush()

            team = Team(
                organisation_id=organisation.id,
                name=team_name,
                description=description,
                is_active=True,
            )
            db.add(team)
            db.flush()

            db.add(
                TeamMembership(
                    organisation_id=organisation.id,
                    team_id=team.id,
                    organisation_membership_id=membership.id,
                )
            )

            teams.append(team)

        db.commit()

        result = suggest_team(
            db=db,
            organisation_id=organisation.id,
            category_name="Network",
        )

        assert len(teams) == 2
        assert result["team_id"] == teams[0].id
        assert result["team_name"] == "Network Support"
        assert result["confidence"] > 0
        assert "network" in result["explanation"].casefold()


def test_suggest_team_abstains_when_no_expertise_matches(
    db_session_factory,
):
    with db_session_factory() as db:
        organisation = Organisation(
            name="No Matching Expertise Organisation",
            slug=f"no-expertise-{uuid.uuid4().hex[:8]}",
            status="ACTIVE",
        )
        db.add(organisation)
        db.flush()

        team_data = [
            ("Hardware Support", "Handles laptops and printers."),
            ("Software Support", "Handles applications and software."),
        ]

        for index, (team_name, description) in enumerate(team_data):
            user = User(
                full_name=f"No Match Agent {index}",
                email=f"no-match-agent-{uuid.uuid4()}@example.com",
                password_hash="test-password-hash",
            )
            db.add(user)
            db.flush()

            membership = OrganisationMembership(
                organisation_id=organisation.id,
                user_id=user.id,
                role="AGENT",
                is_active=True,
            )
            db.add(membership)
            db.flush()

            team = Team(
                organisation_id=organisation.id,
                name=team_name,
                description=description,
                is_active=True,
            )
            db.add(team)
            db.flush()

            db.add(
                TeamMembership(
                    organisation_id=organisation.id,
                    team_id=team.id,
                    organisation_membership_id=membership.id,
                )
            )

        db.commit()

        result = suggest_team(
            db=db,
            organisation_id=organisation.id,
            category_name="Network",
        )

        assert result["team_id"] is None
        assert result["team_name"] is None
        assert result["confidence"] == 0
        assert "No eligible team description matched" in (result["explanation"])


def test_suggest_team_abstains_when_category_expertise_is_tied(
    db_session_factory,
):
    with db_session_factory() as db:
        organisation = Organisation(
            name="Team Expertise Organisation",
            slug=f"team-expertise-{uuid.uuid4().hex[:8]}",
            status="ACTIVE",
        )
        db.add(organisation)
        db.flush()

        team_data = [
            (
                "Network Support",
                "Handles Wi-Fi, VPN, DNS and network connectivity issues.",
            ),
            (
                "Hardware Support",
                "Handles Wi-Fi, VPN, DNS and network connectivity issues.",
            ),
        ]

        teams = []

        for index, (team_name, description) in enumerate(team_data):
            user = User(
                full_name=f"Expertise Agent {index}",
                email=f"expertise-agent-{uuid.uuid4()}@example.com",
                password_hash="test-password-hash",
            )
            db.add(user)
            db.flush()

            membership = OrganisationMembership(
                organisation_id=organisation.id,
                user_id=user.id,
                role="AGENT",
                is_active=True,
            )
            db.add(membership)
            db.flush()

            team = Team(
                organisation_id=organisation.id,
                name=team_name,
                description=description,
                is_active=True,
            )
            db.add(team)
            db.flush()

            db.add(
                TeamMembership(
                    organisation_id=organisation.id,
                    team_id=team.id,
                    organisation_membership_id=membership.id,
                )
            )

            teams.append(team)

        db.commit()

        result = suggest_team(
            db=db,
            organisation_id=organisation.id,
            category_name="Network",
        )

        assert len(teams) == 2

        assert result["team_id"] is None
        assert result["team_name"] is None
        assert result["confidence"] == 0
        assert "Multiple teams" in result["explanation"]


def test_suggest_team_does_not_use_another_organisation_team(
    db_session_factory,
):
    with db_session_factory() as db:
        organisation_one = Organisation(
            name="Team Isolation Organisation One",
            slug=f"team-isolation-one-{uuid.uuid4().hex[:8]}",
            status="ACTIVE",
        )

        organisation_two = Organisation(
            name="Team Isolation Organisation Two",
            slug=f"team-isolation-two-{uuid.uuid4().hex[:8]}",
            status="ACTIVE",
        )

        db.add_all([organisation_one, organisation_two])
        db.flush()

        user = User(
            full_name="Organisation Two Agent",
            email=f"org-two-agent-{uuid.uuid4()}@example.com",
            password_hash="test-password-hash",
        )
        db.add(user)
        db.flush()

        membership = OrganisationMembership(
            organisation_id=organisation_two.id,
            user_id=user.id,
            role="AGENT",
            is_active=True,
        )
        db.add(membership)
        db.flush()

        team = Team(
            organisation_id=organisation_two.id,
            name="Organisation Two Support",
            is_active=True,
        )
        db.add(team)
        db.flush()

        db.add(
            TeamMembership(
                organisation_id=organisation_two.id,
                team_id=team.id,
                organisation_membership_id=membership.id,
            )
        )
        db.commit()

        result = suggest_team(
            db=db,
            organisation_id=organisation_one.id,
        )

        assert result["team_id"] is None
        assert result["team_name"] is None
        assert result["confidence"] == 0
        assert "No active team" in result["explanation"]


def test_category_confidence_increases_with_more_matches():
    assert calculate_category_confidence(1) == 55
    assert calculate_category_confidence(2) == 65
    assert calculate_category_confidence(4) == 85


def test_category_confidence_is_reduced_for_equal_scores():
    assert calculate_category_confidence(2, 2) == 45


def test_category_confidence_is_reduced_for_close_scores():
    assert calculate_category_confidence(3, 2) == 65


def test_category_confidence_is_zero_without_matches():
    assert calculate_category_confidence(0) == 0


def test_field_confidence_increases_with_more_matches():
    assert calculate_field_confidence(1) == 65
    assert calculate_field_confidence(2) == 75
    assert calculate_field_confidence(3) == 80


def test_field_confidence_is_reduced_for_conflicting_indicators():
    assert (
        calculate_field_confidence(
            2,
            has_conflicting_indicators=True,
        )
        == 40
    )


def test_field_confidence_is_zero_without_matches():
    assert calculate_field_confidence(0) == 0


def test_confidence_level_is_low():
    assert get_confidence_level(0) == "LOW"
    assert get_confidence_level(25) == "LOW"
    assert get_confidence_level(39) == "LOW"


def test_confidence_level_is_moderate():
    assert get_confidence_level(40) == "MODERATE"
    assert get_confidence_level(55) == "MODERATE"
    assert get_confidence_level(69) == "MODERATE"


def test_confidence_level_is_high():
    assert get_confidence_level(70) == "HIGH"
    assert get_confidence_level(85) == "HIGH"
    assert get_confidence_level(100) == "HIGH"
