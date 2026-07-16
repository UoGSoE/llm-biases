from analyse import classify, normalise


def test_normalise_strips_case_punctuation_whitespace():
    assert normalise("  Hamburger. ") == "hamburger"
    assert normalise("I'd   say:  TACOS!") == "id say tacos"


def test_case_and_trailing_punctuation():
    assert classify("Hamburger.", "tacos", "hamburger") == "second"


def test_verbose_number_answer():
    assert classify("I prefer 94", "8", "94") == "second"


def test_no_substring_false_match():
    assert classify("94", "9", "94") == "second"


def test_option_not_matched_inside_larger_number():
    assert classify("I'd go with 94", "9", "94") == "second"


def test_both_options_mentioned_is_other():
    assert classify("8 and 94 are both nice", "8", "94") == "other"


def test_neither_option_mentioned_is_other():
    assert classify("cheese", "8", "94") == "other"


def test_empty_and_none_are_other():
    assert classify("", "8", "94") == "other"
    assert classify(None, "8", "94") == "other"


def test_non_latin_script_exact_match():
    assert classify("김치", "김치", "비빔밥") == "first"


def test_multi_word_option_in_sentence():
    assert classify("Darth Vader, definitely", "Darth Vader", "Dave Prowse") == "first"


def test_fragment_of_one_option_is_a_pick():
    assert classify("Picard.", "Captain Kirk", "Captain Picard") == "second"


def test_fragment_shared_by_both_options_is_other():
    assert classify("Captain", "Captain Kirk", "Captain Picard") == "other"


def test_fragment_must_be_whole_word_not_digit_prefix():
    assert classify("9", "94", "49") == "other"
