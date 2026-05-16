from sherlock.markdown_store import remove_approved_blocks


def test_remove_approved_blocks():
    markdown = """# Card

## Segment
Base

<!-- sherlock-approved:abc:start -->
- Approved
<!-- sherlock-approved:abc:end -->

## Sources
"""
    cleaned = remove_approved_blocks(markdown)

    assert "sherlock-approved" not in cleaned
    assert "Base" in cleaned
    assert "## Sources" in cleaned
