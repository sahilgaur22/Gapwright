from app.services.parsing.cleaner import (
    clean_text,
    fix_line_hyphenation,
    normalize_bullets,
    normalize_whitespace,
    remove_headers_footers,
)


def test_normalize_whitespace() -> None:
    raw = "Hello   world!\r\nThis is\t\ta  test.\u00a0\n\n\n\nNew paragraph."
    expected = "Hello world!\nThis is a test.\n\nNew paragraph."
    assert normalize_whitespace(raw) == expected


def test_fix_line_hyphenation() -> None:
    raw = "Under- \nstanding the funda-\nmentals of soft-\nware engineering."
    cleaned = fix_line_hyphenation(raw)
    assert "fundamentals" in cleaned
    assert "software" in cleaned
    assert "Understanding" in cleaned


def test_normalize_bullets() -> None:
    raw = (
        "• Machine Learning\n"
        "  ◦ Deep Learning\n"
        "▪ Natural Language Processing\n"
        "* Computer Vision\n"
        "– Reinforcement Learning"
    )
    cleaned = normalize_bullets(raw)
    for line in cleaned.split("\n"):
        assert line.strip().startswith("- ")


def test_remove_headers_footers() -> None:
    raw = (
        "Course Syllabus: CS 101\n"
        "Page 1 of 5\n"
        "Week 1 Overview\n"
        "--- Page 2 ---\n"
        "Week 2 Overview\n"
        "- 3 -\n"
        "[Page 4]\n"
        "Final Exam"
    )
    cleaned = remove_headers_footers(raw)
    assert "Page 1 of 5" not in cleaned
    assert "--- Page 2 ---" not in cleaned
    assert "- 3 -" not in cleaned
    assert "[Page 4]" not in cleaned
    assert "Course Syllabus: CS 101" in cleaned
    assert "Week 1 Overview" in cleaned
    assert "Final Exam" in cleaned


def test_clean_text_full_pipeline() -> None:
    raw = (
        "  Distributed   Systems Syllabus\r\n\r\n"
        "Page 1 of 10\r\n"
        "• Mod-\nule 1: Algo-\nrithms\r\n"
        "\n\n\n"
        "▪ Mod-\nule 2: Concurrency\r\n"
        "   - 2 -   \r\n"
    )
    result = clean_text(raw)
    assert "Distributed Systems Syllabus" in result
    assert "Page 1 of 10" not in result
    assert "- 2 -" not in result
    assert "- Module 1: Algorithms" in result
    assert "- Module 2: Concurrency" in result
    # Ensure no excessive consecutive blank lines
    assert "\n\n\n" not in result


def test_clean_text_empty_and_whitespace() -> None:
    assert clean_text("") == ""
    assert clean_text("   \n\t   \n  ") == ""
