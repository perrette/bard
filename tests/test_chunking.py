from bard.chunking import split_text_into_chunks


def test_empty_string_returns_no_chunks():
    assert split_text_into_chunks("") == []


def test_whitespace_only_returns_no_chunks():
    assert split_text_into_chunks("   \n\t  ") == []


def test_single_short_sentence_is_one_chunk():
    assert split_text_into_chunks("Hello world.") == ["Hello world."]


def test_sentence_without_terminator_is_kept():
    # No trailing punctuation: still emitted as one chunk.
    assert split_text_into_chunks("Hello world") == ["Hello world"]


def test_multiple_sentences_fit_in_one_chunk():
    text = "One. Two? Three!"
    assert split_text_into_chunks(text, chunk_size=500) == ["One.Two?Three!"]


def test_splits_when_chunk_size_exceeded():
    # Each sentence is ~20 chars; chunk_size=25 forces a split after sentence 1.
    s1 = "A" * 20 + "."
    s2 = "B" * 20 + "."
    chunks = split_text_into_chunks(f"{s1} {s2}", chunk_size=25)
    assert chunks == [s1, s2]


def test_oversized_single_sentence_is_emitted_whole():
    # If a single sentence exceeds chunk_size on its own, the splitter does NOT
    # break mid-sentence — it emits the sentence as a single oversized chunk.
    huge = "x" * 1000 + "."
    assert split_text_into_chunks(huge, chunk_size=100) == [huge]


def test_punctuation_preserved_across_split_boundary():
    s1 = "First sentence is long enough to fill it."
    s2 = "Second one follows."
    chunks = split_text_into_chunks(f"{s1} {s2}", chunk_size=len(s1))
    assert chunks == [s1, s2]
    # Each chunk retains its terminal punctuation.
    assert all(c.endswith((".", "!", "?")) for c in chunks)


def test_question_and_exclamation_split_points():
    text = "Why? Because! Done."
    assert split_text_into_chunks(text, chunk_size=500) == ["Why?Because!Done."]


def test_leading_and_trailing_whitespace_stripped():
    assert split_text_into_chunks("   Hello world.   ") == ["Hello world."]


def test_default_chunk_size_is_500():
    # Build text that fits in 500 but not in 100, to confirm default isn't 100.
    sentences = " ".join(f"Sentence number {i}." for i in range(20))
    assert len(split_text_into_chunks(sentences)) == 1


def test_chunks_never_exceed_chunk_size_when_avoidable():
    sentences = " ".join(f"Sentence{i}." for i in range(50))
    chunks = split_text_into_chunks(sentences, chunk_size=50)
    # Every chunk that contains more than one sentence must fit within the budget.
    for chunk in chunks:
        n_sentences = chunk.count(".")
        if n_sentences > 1:
            assert len(chunk) <= 50
