"""Pure Secret Santa assignment logic (no I/O, fully testable).

A "pairing" is a dict giver_id -> receiver_id that is a derangement of the
participant set: everyone gives exactly once, receives exactly once, and
nobody draws themselves.

Extra rules are passed as ``forbidden``: giver_id -> set of receiver_ids that
giver must not draw (couples, last year's match). Self is always forbidden.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

Forbidden = dict[int, set[int]]

_REJECTION_TRIES = 20_000


class DrawError(ValueError):
    pass


IMPOSSIBLE = (
    "These rules make a draw impossible. Try removing an exclusion, or turn off "
    "'avoid last year's match' for this year."
)


def _allowed(g: int, r: int, forbidden: Forbidden) -> bool:
    return g != r and r not in forbidden.get(g, ())


def _backtrack(givers: list[int], pool: list[int], forbidden: Forbidden, rng: random.Random) -> dict[int, int] | None:
    """Randomised exhaustive search: finds a valid assignment iff one exists."""
    options = {g: [r for r in pool if _allowed(g, r, forbidden)] for g in givers}
    for opts in options.values():
        rng.shuffle(opts)
    order = sorted(givers, key=lambda g: len(options[g]))  # most constrained first
    used: set[int] = set()
    out: dict[int, int] = {}

    def go(i: int) -> bool:
        if i == len(order):
            return True
        g = order[i]
        for r in options[g]:
            if r not in used:
                used.add(r); out[g] = r
                if go(i + 1):
                    return True
                used.discard(r); del out[g]
        return False

    return dict(out) if go(0) else None


def _random_assignment(givers: list[int], pool: list[int], rng: random.Random,
                       forbidden: Forbidden | None = None) -> dict[int, int] | None:
    """Random bijection givers -> pool respecting the rules, or None if impossible.

    Rejection sampling first (uniform over all valid draws). For 10-15 people
    with a few couples and last year's matches the acceptance rate is roughly
    1-5%, so it almost always succeeds. If it doesn't, an exhaustive randomised
    search decides whether any valid draw exists at all.
    """
    forbidden = forbidden or {}
    if len(givers) != len(pool):
        raise DrawError("internal: giver/pool size mismatch")
    if not givers:
        return {}
    shuffled = list(pool)
    for _ in range(_REJECTION_TRIES):
        rng.shuffle(shuffled)
        if all(_allowed(g, r, forbidden) for g, r in zip(givers, shuffled)):
            return dict(zip(givers, shuffled))
    return _backtrack(givers, pool, forbidden, rng)


def full_draw(participants, rng: random.Random | None = None, forbidden: Forbidden | None = None) -> dict[int, int]:
    rng = rng or random.SystemRandom()
    people = sorted(set(participants))
    if len(people) < 2:
        raise DrawError("At least 2 participants are needed for a draw.")
    result = _random_assignment(people, people, rng, forbidden)
    if result is None:
        raise DrawError(IMPOSSIBLE)
    return result


@dataclass
class ReshufflePlan:
    pairing: dict[int, int]
    reshuffled: set[int]          # every giver whose assignment was redrawn
    new_members: set[int]         # forced: joined after the draw
    hidden_forced: set[int]       # forced: receiver left / now breaks a rule (not shown to the operator)
    auto_added: set[int] = field(default_factory=set)  # decoys + extras needed to make the draw solvable
    selected_visible: set[int] = field(default_factory=set)  # picked by the operator

    @property
    def hidden_count(self) -> int:
        """Reshuffled people the operator did not pick and who are not new.

        Only the count is ever reported, so the operator cannot infer who was
        giving to a removed member.
        """
        return len(self.reshuffled - self.selected_visible - self.new_members)


def partial_reshuffle(old: dict[int, int], participants, selected, rng: random.Random | None = None,
                      forbidden: Forbidden | None = None) -> ReshufflePlan:
    """Redraw only part of an existing pairing after the participant list changed.

    - Givers who left are dropped.
    - New members are always redrawn (they have no assignment yet).
    - Givers whose receiver left, or whose match now breaks a rule, are always
      redrawn (hidden from the operator).
    - The operator's ``selected`` givers are redrawn as well.
    - Everyone else keeps their receiver.
    If the redraw set is unsolvable, random extra givers are added until it is.
    """
    rng = rng or random.SystemRandom()
    forbidden = forbidden or {}
    people = set(participants)
    if len(people) < 2:
        raise DrawError("At least 2 participants are needed for a draw.")

    selected_visible = set(selected) & people
    new_members = people - set(old)
    hidden_forced = {g for g in people & set(old)
                     if old[g] not in people or not _allowed(g, old[g], forbidden)}
    redraw = selected_visible | new_members | hidden_forced
    auto_added: set[int] = set()

    # Secrecy padding. Whoever gets redrawn is later re-notified, which the
    # operator can see. Without padding, "redrawn but not selected" would be
    # exactly the people who gave to a removed member. So we add random decoys:
    # one per hidden-forced giver, plus a replacement for every hidden-forced
    # giver the operator happened to select (so the hidden count does not
    # depend on the selection). Each redrawn person is then a decoy with
    # probability ~1/2.
    if hidden_forced:
        needed = len(hidden_forced) + len(hidden_forced & selected_visible)
        candidates = sorted(people - redraw)
        rng.shuffle(candidates)
        decoys = set(candidates[:needed])
        auto_added |= decoys
        redraw |= decoys

    while True:
        kept = {g: old[g] for g in people - redraw}
        pool = sorted(people - set(kept.values()))
        assignment = _random_assignment(sorted(redraw), pool, rng, forbidden)
        if assignment is not None:
            break
        candidates = sorted(people - redraw)
        if not candidates:
            raise DrawError(IMPOSSIBLE)
        extra = rng.choice(candidates)
        auto_added.add(extra)
        redraw.add(extra)

    pairing = {**kept, **assignment}
    validate(pairing, people, forbidden)
    return ReshufflePlan(
        pairing=pairing,
        reshuffled=redraw,
        new_members=new_members,
        hidden_forced=hidden_forced,
        auto_added=auto_added,
        selected_visible=selected_visible,
    )


def validate(pairing: dict[int, int], participants: set[int], forbidden: Forbidden | None = None) -> None:
    if set(pairing) != participants:
        raise DrawError("internal: every participant must give exactly once")
    if sorted(pairing.values()) != sorted(participants):
        raise DrawError("internal: every participant must receive exactly once")
    if any(not _allowed(g, r, forbidden or {}) for g, r in pairing.items()):
        raise DrawError("internal: a rule was broken")
