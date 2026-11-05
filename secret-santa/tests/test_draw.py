import random

import pytest

from app import draw


def check(p, people):
    draw.validate(p, set(people))


@pytest.mark.parametrize("n", [2, 3, 5, 12])
def test_full_draw_is_derangement(n):
    for seed in range(50):
        check(draw.full_draw(range(n), random.Random(seed)), range(n))


def test_full_draw_needs_two():
    with pytest.raises(draw.DrawError):
        draw.full_draw([1])


def test_add_member_keeps_unselected():
    old = draw.full_draw(range(6), random.Random(1))
    plan = draw.partial_reshuffle(old, set(range(7)), selected=set(), rng=random.Random(2))
    check(plan.pairing, range(7))
    assert 6 in plan.reshuffled
    # only the newcomer plus whoever must make room may change
    changed = {g for g in range(6) if plan.pairing[g] != old[g]}
    assert changed <= plan.reshuffled


def test_remove_member_hidden_and_padded():
    for seed in range(100):
        rng = random.Random(seed)
        old = draw.full_draw(range(8), rng)
        people = set(range(7))  # member 7 leaves
        plan = draw.partial_reshuffle(old, people, selected=set(), rng=rng)
        check(plan.pairing, people)
        giver_of_7 = next(g for g, r in old.items() if r == 7)
        if giver_of_7 != 7:
            assert giver_of_7 in plan.hidden_forced
            assert giver_of_7 in plan.reshuffled
        # decoys: hidden count is at least twice the forced set (enough people here)
        assert plan.hidden_count >= 2 * len(plan.hidden_forced)


def test_hidden_count_independent_of_selection():
    old = draw.full_draw(range(10), random.Random(3))
    people = set(range(9))
    giver_of_9 = next(g for g, r in old.items() if r == 9)
    a = draw.partial_reshuffle(old, people, selected=set(), rng=random.Random(4))
    b = draw.partial_reshuffle(old, people, selected={giver_of_9}, rng=random.Random(4))
    c = draw.partial_reshuffle(old, people, selected={(giver_of_9 + 1) % 9}, rng=random.Random(4))
    assert a.hidden_count == b.hidden_count == c.hidden_count


def test_two_cycle_removal_is_solvable():
    old = {0: 1, 1: 0, 2: 3, 3: 2}
    plan = draw.partial_reshuffle(old, {0, 2, 3}, selected=set(), rng=random.Random(0))
    check(plan.pairing, {0, 2, 3})


def test_everyone_selected_equals_full_redraw():
    old = draw.full_draw(range(5), random.Random(0))
    plan = draw.partial_reshuffle(old, set(range(5)), selected=set(range(5)), rng=random.Random(1))
    assert plan.reshuffled == set(range(5))
    check(plan.pairing, range(5))


def test_rules_respected_family_of_12():
    people = list(range(12))
    couples = [(0, 1), (2, 3), (4, 5), (6, 7), (8, 9)]
    forbidden = {}
    for a, b in couples:
        forbidden.setdefault(a, set()).add(b)
        forbidden.setdefault(b, set()).add(a)
    last = draw.full_draw(people, random.Random(0), forbidden)
    for g, r in last.items():
        forbidden.setdefault(g, set()).add(r)
    for seed in range(200):
        p = draw.full_draw(people, random.Random(seed), forbidden)
        draw.validate(p, set(people), forbidden)


def test_impossible_rules_raise():
    with pytest.raises(draw.DrawError):
        draw.full_draw([0, 1], forbidden={0: {1}})


def test_backtracking_finds_rare_solution():
    # only one valid derangement of 0..5 is allowed: i -> i+1 mod 6
    people = list(range(6))
    forbidden = {g: {r for r in people if r != (g + 1) % 6} for g in people}
    assert draw.full_draw(people, random.Random(1), forbidden) == {g: (g + 1) % 6 for g in people}
