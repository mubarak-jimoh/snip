from snip.codes import ALPHABET, CODE_LENGTH, alias_problem, random_code


def test_random_code_has_the_right_length_and_characters():
    code = random_code()
    assert len(code) == CODE_LENGTH
    assert all(ch in ALPHABET for ch in code)


def test_random_codes_do_not_repeat():
    assert len({random_code() for _ in range(1000)}) == 1000


def test_good_alias_is_accepted():
    assert alias_problem("my-link_2026") is None


def test_alias_that_is_too_short_is_rejected():
    assert alias_problem("ab") is not None


def test_alias_with_a_slash_is_rejected():
    assert alias_problem("a/b/c") is not None


def test_reserved_alias_is_rejected_in_any_case():
    assert alias_problem("api") is not None
    assert alias_problem("Stats") is not None
