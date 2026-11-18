"""Regression tests for the recovered Sports Tracker 2.0 Lambda.

Run from repository root:
    python -m unittest discover -s backend/tests -v
"""
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("TABLE_NAME", "sports-tracker-test")
import app


def event(method, path, sub="owner-1", body=None):
    context = {"http": {"method": method}}
    if sub is not None:
        context["authorizer"] = {"jwt": {"claims": {"sub": sub}}}
    result = {"requestContext": context, "rawPath": path}
    if body is not None:
        result["body"] = json.dumps(body)
    return result


def payload(response):
    return json.loads(response["body"])


class LambdaRegressionTests(unittest.TestCase):
    def setUp(self):
        self.db = MagicMock()
        self.table_patch = patch.object(app, "table", return_value=self.db)
        self.table_patch.start()
        self.addCleanup(self.table_patch.stop)
        self.league = {
            "PK": "LEAGUE#league-1", "SK": "META",
            "leagueId": "league-1", "ownerSub": "owner-1",
            "name": "Little League", "season": "Spring"
        }
        self.db.get_item.return_value = {"Item": self.league}
        self.db.query.return_value = {"Items": []}


    def test_owner_can_update_league_season(self):
        result = app.handler(event("PUT", "/v1/leagues/league-1", body={"name": "Youth League", "season": "Fall 2027"}), None)
        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(payload(result)["season"], "Fall 2027")
        self.db.update_item.assert_called_once()

    def test_non_owner_cannot_update_league(self):
        result = app.handler(event("PUT", "/v1/leagues/league-1", sub="other-user", body={"name": "Bad"}), None)
        self.assertEqual(result["statusCode"], 404)
        self.db.update_item.assert_not_called()

    def test_team_name_can_be_updated(self):
        self.db.get_item.side_effect = [{"Item": self.league}, {"Item": {"PK": "LEAGUE#league-1", "SK": "TEAM#team-1", "name": "Tigers"}}]
        result = app.handler(event("PUT", "/v1/leagues/league-1/teams/team-1", body={"name": "Bears"}), None)
        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(payload(result)["name"], "Bears")

    def test_parent_contacts_are_separate_from_player_record(self):
        player = {"PK": "TEAM#team-1", "SK": "PLAYER#player-1", "playerId": "player-1", "name": "Alex"}
        self.db.get_item.side_effect = [
            {"Item": self.league},
            {"Item": {"teamId": "team-1"}},
            {"Item": player}
        ]
        path = "/v1/leagues/league-1/teams/team-1/players/player-1/contacts"
        result = app.handler(event("PUT", path, body={"contacts": [{"name": "Parent", "email": "parent@example.com", "phone": "555-0100"}]}), None)
        self.assertEqual(result["statusCode"], 200)
        saved = self.db.put_item.call_args.kwargs["Item"]
        self.assertEqual(saved["PK"], "PLAYER#player-1")
        self.assertEqual(saved["SK"], "CONTACTS")
        self.assertNotIn("contacts", player)

    def test_non_owner_cannot_read_parent_contacts(self):
        path = "/v1/leagues/league-1/teams/team-1/players/player-1/contacts"
        result = app.handler(event("GET", path, sub="other-user"), None)
        self.assertEqual(result["statusCode"], 404)
        self.db.put_item.assert_not_called()

    def test_reject_contact_without_name(self):
        self.db.get_item.side_effect = [{"Item": self.league}, {"Item": {"teamId": "team-1"}}, {"Item": {"playerId": "player-1"}}]
        path = "/v1/leagues/league-1/teams/team-1/players/player-1/contacts"
        result = app.handler(event("PUT", path, body={"contacts": [{"email": "parent@example.com"}]}), None)
        self.assertEqual(result["statusCode"], 400)
        self.db.put_item.assert_not_called()


    def test_owner_adds_league_manager_contact(self):
        body = {"role": "league", "name": "Coach", "email": "coach@example.com", "phone": "555-0101"}
        result = app.handler(event("POST", "/v1/leagues/league-1/managers", body=body), None)
        self.assertEqual(result["statusCode"], 201)
        self.assertEqual(payload(result)["status"], "contact-only")
        self.assertEqual(self.db.put_item.call_args.kwargs["Item"]["email"], "coach@example.com")

    def test_team_manager_limit(self):
        self.db.get_item.side_effect = [{"Item": self.league}, {"Item": {"teamId": "team-1"}}]
        self.db.query.return_value = {"Items": [{"role": "team", "teamId": "team-1"} for _ in range(3)]}
        result = app.handler(event("POST", "/v1/leagues/league-1/managers",
            body={"role": "team", "teamId": "team-1", "name": "Fourth", "email": "fourth@example.com"}), None)
        self.assertEqual(result["statusCode"], 409)
        self.db.put_item.assert_not_called()

    def test_non_owner_cannot_list_manager_contacts(self):
        result = app.handler(event("GET", "/v1/leagues/league-1/managers", sub="stranger"), None)
        self.assertEqual(result["statusCode"], 404)

    def test_admin_group_can_read_any_league(self):
        e = event("GET", "/v1/leagues/league-1", sub="admin")
        e["requestContext"]["authorizer"]["jwt"]["claims"]["cognito:groups"] = ["SportsTrackerSuperAdmin"]
        result = app.handler(e, None)
        self.assertEqual(result["statusCode"], 200)

    def test_unprivileged_user_cannot_read_any_league(self):
        result = app.handler(event("GET", "/v1/leagues/league-1", sub="admin"), None)
        self.assertEqual(result["statusCode"], 404)
    def test_health_is_public(self):
        result = app.handler(event("GET", "/v1/health", sub=None), None)
        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(payload(result)["status"], "ok")
        self.db.get_item.assert_not_called()

    def test_leagues_require_authentication(self):
        result = app.handler(event("GET", "/v1/leagues", sub=None), None)
        self.assertEqual(result["statusCode"], 401)

    def test_owner_can_read_league(self):
        result = app.handler(event("GET", "/v1/leagues/league-1"), None)
        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(payload(result)["leagueId"], "league-1")

    def test_non_owner_cannot_read_league(self):
        result = app.handler(event("GET", "/v1/leagues/league-1", sub="other-user"), None)
        self.assertEqual(result["statusCode"], 404)

    def test_non_owner_cannot_create_team(self):
        result = app.handler(event("POST", "/v1/leagues/league-1/teams", sub="other-user", body={"name": "Tigers"}), None)
        self.assertEqual(result["statusCode"], 404)
        self.db.put_item.assert_not_called()

    def test_owner_can_create_team(self):
        result = app.handler(event("POST", "/v1/leagues/league-1/teams", body={"name": "Tigers"}), None)
        self.assertEqual(result["statusCode"], 201)
        self.assertEqual(payload(result)["name"], "Tigers")
        self.db.put_item.assert_called_once()

    def test_team_name_is_required(self):
        result = app.handler(event("POST", "/v1/leagues/league-1/teams", body={"name": " "}), None)
        self.assertEqual(result["statusCode"], 400)
        self.db.put_item.assert_not_called()

    def test_missing_team_cannot_have_players_added(self):
        self.db.get_item.side_effect = [
            {"Item": self.league},
            {}
        ]
        result = app.handler(event("POST", "/v1/leagues/league-1/teams/team-missing/players", body={"name": "Alex"}), None)
        self.assertEqual(result["statusCode"], 404)
        self.db.put_item.assert_not_called()

    def test_owner_can_create_player(self):
        self.db.get_item.side_effect = [
            {"Item": self.league},
            {"Item": {"PK": "LEAGUE#league-1", "SK": "TEAM#team-1", "name": "Tigers"}}
        ]
        result = app.handler(event("POST", "/v1/leagues/league-1/teams/team-1/players", body={"name": "Alex", "number": "7"}), None)
        self.assertEqual(result["statusCode"], 201)
        self.assertEqual(payload(result)["number"], "7")
        self.db.put_item.assert_called_once()

    def test_invalid_player_number_is_rejected(self):
        self.db.get_item.side_effect = [
            {"Item": self.league},
            {"Item": {"PK": "LEAGUE#league-1", "SK": "TEAM#team-1"}}
        ]
        result = app.handler(event("POST", "/v1/leagues/league-1/teams/team-1/players", body={"name": "Alex", "number": "123456"}), None)
        self.assertEqual(result["statusCode"], 400)
        self.db.put_item.assert_not_called()

    def test_league_creation_requires_season(self):
        result = app.handler(event("POST", "/v1/leagues", body={"name": "Summer League"}), None)
        self.assertEqual(result["statusCode"], 400)

    def test_owner_lists_only_owned_leagues(self):
        self.db.query.return_value = {"Items": [{"leagueId": "league-1"}, {"leagueId": "league-2"}]}
        self.db.get_item.side_effect = [
            {"Item": self.league},
            {"Item": {**self.league, "leagueId": "league-2", "ownerSub": "other-user"}}
        ]
        result = app.handler(event("GET", "/v1/leagues"), None)
        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(len(payload(result)["items"]), 1)


if __name__ == "__main__":
    unittest.main()
