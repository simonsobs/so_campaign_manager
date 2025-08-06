"""Tests for the SO LAT mission banner functionality."""

import io
import sys
from unittest.mock import patch

import pytest


def display_banner() -> None:
    """Display the SO LAT mission launched banner with 20-line ASCII galaxy design."""
    banner_lines = [
        "                  .     *       :        .    *       :        .     *                  ",
        "            *           :   .        +       .   :        +        :   .           *            ",
        "       .         +    :     .   *         .     :     .         *   .     :    +         .       ",
        "    :     .  *      ~    ^   .     +   .  SO LAT MISSION LAUNCHED  .   +     .   ^    ~      *  .     :    ",
        " .    +      *   :    .   ^    ~     +-------------------------------------+     ~    ^   .    :   *      +    . ",
        "   .     :    +    ^  .    :   *     |           Welcome to SO Campaign           |     *   :    .  ^    +    :     .   ",
        " +    *    .   :    ~   ^    .   +   |             Manager (socm)                 |   +   .    ^   ~    :   .    *    + ",
        "   :     +   *    .    :   ^   ~     |         Simmons Observatory                |     ~   ^   :    .    *   +     :   ",
        " *   .    +     ^   .   :   *   .    |      Large Aperture Telescope              |    .   *   :   .   ^     +    .   * ",
        "^   +    .   *    :    ^   +   .   * |            Ready for launch!               | *   .   +   ^    :    *   .    +   ^",
        "  :   .   *   ^     .   +   :   ^    +-------------------------------------+    ^   :   +   .     ^   *   .   :  ",
        ".   *    +    :   ^    .   *    +  :     .   +   :   ^   *   .   :   +   .     :  +    *   .    ^   :    +    *   .",
        " :   +   .   *    ^    :   +   .   *    .   :   +   ^   .   *   :   +   .   *    .   +   :    ^    *   .   +   : ",
        "  .   :    +    ^   .   *   +   :   ^   .   +   :   *   ^   +   .   :   ^   +   :   +   *   .   ^    +    :   .  ",
        "+    .   *    :   ^    +   .   :   *   ^   +   .   :   *   .   ^   +   *   :   .   +   ^   :   .   +    ^   :    +",
        "  ^   +    *    :   .   ^   +   *   :   .   +   ^   *   +   .   :   *   ^   +   .   :   *   +   ^   .   :    *   ",
        ":   .   +   *   ^    :   .   +   *   ^   :   +   .   *   :   ^   +   .   *   :   ^   +   .   :   ^   *   +   .   :",
        "  *    :   .   +   ^   *    :   .   +   ^   *   :   +   .   ^   *   +   .   :   *   ^   +   .   :    ^   +   .   ",
        ".   :   *   +   .   :   ^   *   +   .   :   *   ^   +   *   :   .   ^   +   *   :   .   +   ^   *   :   .   +   .",
        "   *      :      +      .      ^      *     Campaign management for cutting-edge astronomy     *      ^      "
    ]
    
    print()
    for line in banner_lines:
        print(line)
    print()


def test_display_banner():
    """Test that the banner displays correctly."""
    # Capture stdout to verify banner content
    captured_output = io.StringIO()
    sys.stdout = captured_output
    
    display_banner()
    
    # Reset stdout
    sys.stdout = sys.__stdout__
    
    # Get the output
    output = captured_output.getvalue()
    
    # Verify the banner contains the required text
    assert "SO LAT MISSION LAUNCHED" in output
    assert "Welcome to SO Campaign" in output
    assert "Manager (socm)" in output
    assert "Simmons Observatory" in output
    assert "Large Aperture Telescope" in output
    assert "Ready for launch!" in output
    assert "Campaign management for cutting-edge astronomy" in output
    
    # Verify ASCII symbols are present
    assert "*" in output
    assert "." in output
    assert "+" in output
    assert "~" in output
    assert ":" in output
    
    # Count lines (should be 20 lines plus empty lines before and after)
    lines = output.strip().split('\n')
    assert len(lines) == 20, f"Expected 20 lines, got {len(lines)}"
    
    # Verify no line exceeds 120 characters
    for i, line in enumerate(lines, 1):
        assert len(line) <= 120, f"Line {i} exceeds 120 characters: {len(line)} chars"


def test_banner_line_requirements():
    """Test specific banner requirements."""
    # Capture output
    captured_output = io.StringIO()
    sys.stdout = captured_output
    display_banner()
    sys.stdout = sys.__stdout__
    
    output = captured_output.getvalue()
    lines = output.strip().split('\n')
    
    # Test that we have exactly 20 content lines (requirement: up to 20 lines)
    assert len(lines) == 20
    
    # Test that all lines are within 120 character limit
    for line in lines:
        assert len(line) <= 120
    
    # Test that it includes ASCII symbols
    ascii_symbols = ["*", ".", "+", "~", ":", "#", "^", "=", "o"]
    assert any(symbol in output for symbol in ascii_symbols)
    
    # Test that it says "SO LAT mission launched" (case insensitive check)
    assert "SO LAT MISSION LAUNCHED" in output.upper()