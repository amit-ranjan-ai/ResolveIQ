import uuid

pytest_plugins = ("tests.test_teams",)

from tests.test_teams import create_organisation


def test_create_category(client):
    organisation = create_organisation(client)

    response = client.post(
        f"/api/v1/organisations/{organisation['id']}/categories",
        json={
            "name": "Network",
            "description": "Network and connectivity issues.",
        },
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Network"
    assert response.json()["organisation_id"] == organisation["id"]
    assert response.json()["is_active"] is True


def test_create_category_with_duplicate_name(client):
    organisation = create_organisation(client)

    url = f"/api/v1/organisations/{organisation['id']}/categories"
    category_data = {"name": "Network"}

    first_response = client.post(url, json=category_data)
    second_response = client.post(url, json=category_data)

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_create_category_for_inactive_organisation(client):
    organisation = create_organisation(
        client,
        status="INACTIVE",
    )

    response = client.post(
        f"/api/v1/organisations/{organisation['id']}/categories",
        json={"name": "Network"},
    )

    assert response.status_code == 400


def test_get_organisation_categories(client):
    organisation = create_organisation(client)
    url = f"/api/v1/organisations/{organisation['id']}/categories"

    client.post(url, json={"name": "Network"})
    client.post(url, json={"name": "Hardware"})

    response = client.get(url)

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_organisation_categories_includes_inactive_categories(client):
    organisation = create_organisation(client)
    url = f"/api/v1/organisations/{organisation['id']}/categories"

    category = client.post(
        url,
        json={"name": "Network"},
    ).json()

    client.patch(
        f"{url}/{category['id']}",
        json={"is_active": False},
    )

    response = client.get(url)

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["is_active"] is False


def test_patch_category(client):
    organisation = create_organisation(client)
    url = f"/api/v1/organisations/{organisation['id']}/categories"

    category = client.post(
        url,
        json={"name": "Network"},
    ).json()

    response = client.patch(
        f"{url}/{category['id']}",
        json={"name": "Networking"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Networking"


def test_patch_category_deactivate(client):
    organisation = create_organisation(client)
    url = f"/api/v1/organisations/{organisation['id']}/categories"

    category = client.post(
        url,
        json={"name": "Network"},
    ).json()

    response = client.patch(
        f"{url}/{category['id']}",
        json={"is_active": False},
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_patch_category_with_empty_data(client):
    organisation = create_organisation(client)
    url = f"/api/v1/organisations/{organisation['id']}/categories"

    category = client.post(
        url,
        json={"name": "Network"},
    ).json()

    response = client.patch(
        f"{url}/{category['id']}",
        json={},
    )

    assert response.status_code == 400


def test_patch_category_with_null_name(client):
    organisation = create_organisation(client)
    url = f"/api/v1/organisations/{organisation['id']}/categories"

    category = client.post(
        url,
        json={"name": "Network"},
    ).json()

    response = client.patch(
        f"{url}/{category['id']}",
        json={"name": None},
    )

    assert response.status_code == 422


def test_patch_category_from_another_organisation(client):
    first_organisation = create_organisation(client, "First Organisation")

    category = client.post(
        f"/api/v1/organisations/{first_organisation['id']}/categories",
        json={"name": "Network"},
    ).json()

    second_organisation = create_organisation(
        client,
        "Second Organisation",
    )

    response = client.patch(
        f"/api/v1/organisations/{second_organisation['id']}/categories/{category['id']}",
        json={"name": "Updated Network"},
    )

    assert response.status_code == 404


def test_get_categories_for_nonexistent_organisation(client):
    create_organisation(client)

    response = client.get(
        f"/api/v1/organisations/{uuid.uuid4()}/categories",
    )

    assert response.status_code == 403
