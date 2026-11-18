"""Pure baseball game-state transitions; no AWS side effects."""
from copy import deepcopy

def new_game(league_id, home, away):
    if home == away:
        raise ValueError("Home and away teams must be different")
    return {
        "leagueId": league_id, "homeTeamId": home, "awayTeamId": away,
        "status": "scheduled", "inning": 1, "half": "top", "outs": 0,
        "runs": {"home": [0], "away": [0]},
        "battingOrders": {"home": [], "away": []},
        "batterIndex": {"home": 0, "away": 0},
        "history": [], "revision": 0
    }

def snapshot(game):
    return {k: deepcopy(game[k]) for k in (
        "status", "inning", "half", "outs", "runs", "battingOrders", "batterIndex"
    )}

def side(game):
    return "away" if game["half"] == "top" else "home"

def current_batters(game):
    order = game["battingOrders"][side(game)]
    if not order:
        return {"current": None, "onDeck": None}
    index = game["batterIndex"][side(game)] % len(order)
    return {"current": order[index], "onDeck": order[(index + 1) % len(order)]}

def apply(game, action, value=None):
    g = deepcopy(game)
    if action == "undo":
        if not g["history"]:
            raise ValueError("Nothing to undo")
        previous = g["history"].pop()
        g.update(previous)
        g["revision"] += 1
        return g
    if action == "reset":
        original = new_game(g["leagueId"], g["homeTeamId"], g["awayTeamId"])
        original.update({k: g[k] for k in ("PK", "SK", "gameId", "createdAt") if k in g})
        original["revision"] = g["revision"] + 1
        return original
    if g["status"] == "final":
        raise ValueError("Game is final")
    if action not in ("run", "out", "nextBatter", "start", "setBattingOrder"):
        raise ValueError("Unsupported scoring action")
    if len(g["history"]) >= 50:
        g["history"] = g["history"][-49:]
    g["history"].append(snapshot(g))
    if action == "start":
        if g["status"] != "scheduled":
            raise ValueError("Game already started")
        g["status"] = "live"
    elif action == "setBattingOrder":
        if not isinstance(value, dict) or value.get("side") not in ("home", "away"):
            raise ValueError("Specify a valid side")
        players = value.get("playerIds")
        if not isinstance(players, list) or len(players) > 30 or any(
            not isinstance(p, str) or not p.strip() for p in players
        ) or len(set(players)) != len(players):
            raise ValueError("Invalid batting order")
        g["battingOrders"][value["side"]] = players
        g["batterIndex"][value["side"]] = 0
    else:
        if g["status"] != "live":
            raise ValueError("Start the game before scoring")
        batting = side(g)
        if action == "run":
            if value is not None and value != 1:
                raise ValueError("One run per action")
            g["runs"][batting][-1] += 1
        elif action == "nextBatter":
            if not g["battingOrders"][batting]:
                raise ValueError("Set the batting order first")
            g["batterIndex"][batting] += 1
        elif action == "out":
            g["outs"] += 1
            if g["outs"] == 3:
                g["outs"] = 0
                if g["half"] == "top":
                    g["half"] = "bottom"
                else:
                    g["half"] = "top"
                    g["inning"] += 1
                    g["runs"]["home"].append(0)
                    g["runs"]["away"].append(0)
    g["revision"] += 1
    return g
