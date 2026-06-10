"""Builds the match-result email from scoresheet data and entered results.

The format follows the club's submission conventions (see example_emails.md):
a title line with the final score, then one block per round (or per board for
Standard matches) with a result line for every pairing, plus round score,
cumulative score, and a final score after the last round.

Defaults ("D") render as their point value with "(absent)" written beside the
defaulting player: a present player beats an absent one 1 - 0, while a double
default is scored as a 0.5 - 0.5 draw. Unentered results render as "_ - _"
so the captain can fill them in before sending.
"""

# Selectable results, home score first. "D" = default (absent player).
RESULT_OPTIONS = ["", "1 - 0", "0.5 - 0.5", "0 - 1", "1 - D", "D - 1", "D - D"]

_POINTS = {
    "1 - 0": (1.0, 0.0),
    "0.5 - 0.5": (0.5, 0.5),
    "0 - 1": (0.0, 1.0),
    "1 - D": (1.0, 0.0),   # away defaulted: the present player wins
    "D - 1": (0.0, 1.0),   # home defaulted
    "D - D": (0.5, 0.5),   # double default is scored as a draw
}

_HOME_DEFAULTS = ("D - 1", "D - D")
_AWAY_DEFAULTS = ("1 - D", "D - D")


def format_points(value):
    """3.0 -> '3', 2.5 -> '2.5'."""
    return str(int(value)) if float(value).is_integer() else f"{value:g}"


def _player_text(player, defaulted, colour=""):
    """'Forename Surname [pnum] (rating) (B)', '(ung)' when unrated.

    Unnamed players (blank rows / short side) render as '(absent)' when
    defaulted, otherwise as a blank line for the captain to fill in.
    Defaulted players played no game, so their colour is omitted.
    """
    name = ((player or {}).get('name') or '').strip()
    if not name:
        return "(absent)" if defaulted else "______"
    parts = [name]
    if (player or {}).get('pnum'):
        parts.append(f"[{player['pnum']}]")
    rating = ((player or {}).get('rating') or '').strip()
    parts.append(f"({rating})" if rating else "(ung)")
    if defaulted:
        parts.append("(absent)")
    elif colour:
        parts.append(f"({colour})")
    return " ".join(parts)


def compute_totals(rounds):
    """Return (per_round, (home_total, away_total), n_missing).

    per_round is a list of (home_pts, away_pts, n_missing_in_round).
    Boards without an entered result contribute nothing to the totals.
    """
    per_round = []
    total_h = total_a = 0.0
    missing = 0
    for rnd in rounds:
        h = a = 0.0
        rnd_missing = 0
        for pair in rnd['pairs']:
            pts = _POINTS.get(pair.get('result', ''))
            if pts is None:
                rnd_missing += 1
            else:
                h += pts[0]
                a += pts[1]
        per_round.append((h, a, rnd_missing))
        total_h += h
        total_a += a
        missing += rnd_missing
    return per_round, (total_h, total_a), missing


def _pair_line(pair):
    result = pair.get('result', '')
    pts = _POINTS.get(result)
    home_txt = _player_text(pair.get('home'), result in _HOME_DEFAULTS,
                            pair.get('home_colour', ''))
    away_txt = _player_text(pair.get('away'), result in _AWAY_DEFAULTS,
                            pair.get('away_colour', ''))
    if pts is None:
        score = "_ - _"
    else:
        score = f"{format_points(pts[0])} - {format_points(pts[1])}"
    return f"{home_txt} {score} {away_txt}"


def build_match_email(home_team, away_team, date_str, rounds,
                      is_all_play_all, final_score=None):
    """Build the email text.

    rounds: [{'colours': 'B/W' or None, 'pairs': [{'home': player or None,
    'away': player or None, 'result': str, 'home_colour': 'W'/'B'/'',
    'away_colour': 'W'/'B'/''}]}] where player dicts carry 'name', 'pnum',
    'rating'. Round-level 'colours' suits All Play All (whole-team draws);
    per-pair colours suit Standard boards.

    final_score: (home, away) override for the final score. When None it is
    autofilled from the entered results, or left blank if results are missing.
    """
    per_round, computed, missing = compute_totals(rounds)

    final = final_score
    if final is None and missing == 0:
        final = computed

    if final is not None:
        title = (f"{home_team} (home) {format_points(final[0])} - "
                 f"{format_points(final[1])} {away_team} (away), {date_str}.")
    else:
        title = f"{home_team} (home) vs {away_team} (away), {date_str}."

    lines = [title, ""]

    if is_all_play_all:
        cum_h = cum_a = 0.0
        cum_known = True
        for i, rnd in enumerate(rounds):
            colours = rnd.get('colours')
            lines.append(f"Round {i + 1} {colours}:" if colours
                         else f"Round {i + 1}:")
            for pair in rnd['pairs']:
                lines.append(_pair_line(pair))

            h, a, rnd_missing = per_round[i]
            cum_h += h
            cum_a += a
            if rnd_missing:
                cum_known = False
                lines.append(f"Round {i + 1} score: _ - _")
            else:
                lines.append(f"Round {i + 1} score: "
                             f"{format_points(h)} - {format_points(a)}")

            if i == len(rounds) - 1:
                if final is not None:
                    lines.append(f"Final score: {format_points(final[0])} - "
                                 f"{format_points(final[1])}")
                else:
                    lines.append("Final score: _ - _")
            elif cum_known:
                lines.append(f"Cumulative score: "
                             f"{format_points(cum_h)} - {format_points(cum_a)}")
            else:
                lines.append("Cumulative score: _ - _")
            lines.append("")
    else:
        for b, pair in enumerate(rounds[0]['pairs']):
            lines.append(f"Board {b + 1}:")
            lines.append(_pair_line(pair))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
