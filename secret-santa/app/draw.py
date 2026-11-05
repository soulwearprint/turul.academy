"""Pure Secret Santa assignment logic (no I/O, fully testable).

A "pairing" is a dict giver_id -> receiver_id that is a derangement of the
participant set: everyone gives exactly once, receives exactly once, and
nobody draws themselves.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

_MAX_TRIES = 10_000


class DrawError(ValueError):
    pass


def _random_assignment(givers: list[int], pool: list[int], rng: random.Random) -> dict[int, int] | None:
    """Uniformly random bijection givers -> pool with no giver mapped to itself.

    Rejection sampling: for the self-exclusion-only constraint the acceptance
    probability is >= ~1/e, so this terminates fast for family-sized groups.
    """
    if len(givers) != len(pool):
        raise DrawError("internal: giver/pool size mismatch")
    if len(givers) == 1 and givers[0] == pool[0]:
        return None
    pool = list(pool)
    for _ in range(_MAX_TRIES):
        rng.shuffle(pool)
        if all(g != r for g, r in zip(givers, pool)):
            return dict(zip(givers, pool))
    return None


def full_draw(participants: list[int] | set[int], rng: random.Random | None = None) -> dict[int, int]:
    rng = rng or random.SystemRandom()
    people = sorted(set(participants))
    if len(people) < 2:
        raise DrawError("At least 2 participants are needed for a draw.")
    result = _random_assignment(people, people, rng)
    if result is None:  # pragma: no cover - impossible for n >= 2
        raise DrawError("Could not find a valid draw.")
    return result


@dataclass
class ReshufflePlan:
    pairing: dict[int, int]
    reshuffled: set[int]          # every giver whose assignment was redrawn
    new_members: set[int]         # forced: joined after the draw
    hidden_forced: set[int]       # forced: their receiver left (not shown to the operator)
    auto_added: set[int] = field(default_factory=set)  # added only to make the draw solvable
    selected_visible: set[int] = field(default_factory=set)  # picked by the operator

    @property
    def hidden_count(self) -> int:
        """Reshuffled people the operator did not pick and who are not new.

        Only the count is ever reported, so the operator cannot infer who was
        giving to a removed member.
        """
        return len(self.reshuffled - self.selected_visible - self.new_members)


def partial_reshuffle(
    old: dict[int, int],
    participants: list[int] | set[int],
    selected: list[int] | set[int],
    rng: random.Random | None = None,
) -> ReshufflePlan:
    """Redraw only part of an existing pairing after the participant list changed.

    - Givers who left are dropped.
    - New members are always redrawn (they have no assignment yet).
    - Givers whose receiver left are always redrawn (hidden from the operator).
    - The operator's ``selected`` givers are redrawn as well.
    - Everyone else keeps their receiver.
    If the redraw set is unsolvable (only possible when it has one person whose
    only free receiver is themselves) random extra givers are added.
    """
    rng = rng or random.SystemRandom()
    people = set(participants)
    if len(people) < 2:
        raise DrawError("At least 2 participants are needed for a draw.")

    selected_visible = set(selected) & people
    new_members = people - set(old)
    hidden_forced = {g for g in people & set(old) if old[g] not in people}
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
        givers = sorted(redraw)
        assignment = _random_assignment(givers, pool, rng) if givers else {}
        if assignment is not None:
            break
        candidates = sorted(people - redraw)
        if not candidates:  # pragma: no cover - only reachable with n < 2
            raise DrawError("Could not find a valid draw.")
        extra = rng.choice(candidates)
        auto_added.add(extra)
        redraw.add(extra)

    pairing = {**kept, **assignment}
    validate(pairing, people)
    return ReshufflePlan(
        pairing=pairing,
        reshuffled=redraw,
        new_members=new_members,
        hidden_forced=hidden_forced,
        auto_added=auto_added,
        selected_visible=selected_visible,
    )


def validate(pairing: dict[int, int], participants: set[int]) -> None:
    if set(pairing) != participants:
        raise DrawError("internal: every participant must give exactly once")
    if sorted(pairing.values()) != sorted(participants):
        raise DrawError("internal: every participant must receive exactly once")
    if any(g == r for g, r in pairing.items()):
        raise DrawError("internal: somebody drew themselves")
