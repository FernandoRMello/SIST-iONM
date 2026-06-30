import sqlite3

from fastapi.testclient import TestClient

from tests.conftest import LegacyTestState


def first_post_id(state: LegacyTestState) -> int:
    with sqlite3.connect(state.database_path) as connection:
        return int(connection.execute("SELECT id FROM feed_posts ORDER BY id LIMIT 1").fetchone()[0])


def reaction(state: LegacyTestState, post_id: int) -> str | None:
    with sqlite3.connect(state.database_path) as connection:
        row = connection.execute(
            """
            SELECT fr.reaction
            FROM feed_reactions fr
            JOIN users u ON u.id=fr.user_id
            WHERE fr.post_id=? AND u.username=?
            """,
            (post_id, state.admin_username),
        ).fetchone()
    return row[0] if row else None


def test_feed_reaction_switches_and_toggles_off(
    admin_client: TestClient,
    legacy_test_state: LegacyTestState,
) -> None:
    post_id = first_post_id(legacy_test_state)

    liked = admin_client.post(f"/feed/reaction/{post_id}/like", follow_redirects=False)
    assert liked.status_code == 303
    assert reaction(legacy_test_state, post_id) == "like"

    disliked = admin_client.post(f"/feed/reaction/{post_id}/dislike", follow_redirects=False)
    assert disliked.status_code == 303
    assert reaction(legacy_test_state, post_id) == "dislike"

    removed = admin_client.post(f"/feed/reaction/{post_id}/dislike", follow_redirects=False)
    assert removed.status_code == 303
    assert reaction(legacy_test_state, post_id) is None


def test_feed_reaction_validates_kind_and_post(
    admin_client: TestClient,
    legacy_test_state: LegacyTestState,
) -> None:
    post_id = first_post_id(legacy_test_state)

    assert admin_client.post(f"/feed/reaction/{post_id}/heart").status_code == 400
    assert admin_client.post("/feed/reaction/999999/like").status_code == 404


def test_feed_renders_reaction_states_and_author_photos(
    admin_client: TestClient,
    legacy_test_state: LegacyTestState,
) -> None:
    with sqlite3.connect(legacy_test_state.database_path) as connection:
        admin_id = connection.execute(
            "SELECT id FROM users WHERE username=?",
            (legacy_test_state.admin_username,),
        ).fetchone()[0]
        connection.execute(
            "UPDATE user_profiles SET avatar_path=? WHERE user_id=?",
            ("uploads/admin-avatar.jpg", admin_id),
        )
        connection.execute(
            "UPDATE user_profiles SET avatar_path=? WHERE user_id=?",
            ("uploads/comment-avatar.jpg", legacy_test_state.ids["settings_user_id"]),
        )

    response = admin_client.get("/feed")

    assert response.status_code == 200
    assert "&#128077;" in response.text
    assert "&#128078;" in response.text
    assert 'aria-pressed="' in response.text
    assert 'class="ui-feed-avatar" src="/uploads/admin-avatar.jpg"' in response.text
    assert 'class="ui-feed-comment-avatar" src="/uploads/comment-avatar.jpg"' in response.text
