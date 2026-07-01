"""Unit tests for the TTS text preprocessing pipeline.

Pure logic — no external services, no async. These run anywhere with just pytest.
"""

from app.utils import text_processor


def test_empty_and_whitespace():
    assert text_processor.process("") == ""
    assert text_processor.process("   ") == ""
    assert text_processor.process("\n\t  \n") == ""


def test_strips_bold_and_italic():
    assert text_processor.process("**Hello** world") == "Hello world"
    assert text_processor.process("*Hello* world") == "Hello world"
    assert text_processor.process("__Hello__ world") == "Hello world"


def test_strips_markdown_links_keeps_text():
    assert text_processor.process("Visit [our site](http://x.com) today") == "Visit our site today"


def test_strips_headers_and_bullets():
    assert text_processor.process("# Heading") == "Heading"
    assert text_processor.process("- Item one") == "Item one"
    assert text_processor.process("> quoted") == "quoted"


def test_strips_inline_code_and_blocks():
    assert text_processor.process("Run `pip install` now") == "Run pip install now"


def test_strips_html_tags():
    assert text_processor.process("<b>Bold</b> text") == "Bold text"
    assert text_processor.process("<p>Hello</p>") == "Hello"


def test_expands_abbreviations():
    assert text_processor.process("Dr. Smith is here") == "Doctor Smith is here"
    assert text_processor.process("Open Mon etc.") == "Open Mon et cetera"
    assert text_processor.process("e.g. this") == "for example this"


def test_currency_symbol_becomes_words():
    assert text_processor.process("It costs $42") == "It costs 42 dollars"
    assert text_processor.process("Total: $1,200") == "Total: 1,200 dollars"


def test_percent_becomes_words():
    assert text_processor.process("50% off") == "50 percent off"


def test_ampersand_and_at():
    assert text_processor.process("cats & dogs") == "cats and dogs"
    assert text_processor.process("meet @ noon") == "meet at noon"


def test_fixes_missing_space_after_punctuation():
    assert text_processor.process("Hello.World") == "Hello. World"


def test_removes_space_before_punctuation():
    assert text_processor.process("Hello , world .") == "Hello, world."


def test_collapses_whitespace():
    assert text_processor.process("too    many     spaces") == "too many spaces"


def test_realistic_llm_output():
    raw = "**We're open** Monday to Friday, 9am to 6pm. Call us @ the office for a $50 consult!"
    out = text_processor.process(raw)
    assert "*" not in out
    assert "50 dollars" in out
    assert " at " in out
    assert out.startswith("We're open")
