import pytest

from app.utils.chunking import chunk_pages, split_text_into_chunks


@pytest.mark.unit
class TestSplitTextIntoChunks:
    def test_returns_empty_list_for_empty_text(self):
        assert split_text_into_chunks("", chunk_size=100, chunk_overlap=20) == []

    def test_returns_empty_list_for_whitespace_only(self):
        assert split_text_into_chunks("   \n\t  ", chunk_size=100, chunk_overlap=20) == []

    def test_returns_single_chunk_when_text_shorter_than_chunk_size(self):
        text = "short text"
        result = split_text_into_chunks(text, chunk_size=100, chunk_overlap=20)
        assert result == ["short text"]

    def test_normalizes_whitespace_before_splitting(self):
        text = "word1   \n  word2\t\tword3"
        result = split_text_into_chunks(text, chunk_size=100, chunk_overlap=20)
        assert result == ["word1 word2 word3"]

    def test_splits_long_text_into_multiple_chunks_with_overlap(self):
        text = "a" * 100
        result = split_text_into_chunks(text, chunk_size=30, chunk_overlap=10)
        assert len(result) >= 3
        assert all(len(chunk) <= 30 for chunk in result)
        assert result[0] == text[:30]
        assert result[-1][-20:] == text[-20:]

    def test_overlap_reduces_boundary_gap(self):
        text = "x" * 80
        result = split_text_into_chunks(text, chunk_size=40, chunk_overlap=15)
        first_end = result[0][-15:]
        second_start = result[1][:15]
        assert first_end == second_start


@pytest.mark.unit
class TestChunkPages:
    def test_returns_empty_list_for_empty_pages(self):
        assert chunk_pages([], chunk_size=100, chunk_overlap=20) == []

    def test_chunks_single_page(self):
        pages = [(1, "hello world")]
        result = chunk_pages(pages, chunk_size=100, chunk_overlap=20)
        assert result == [(1, 0, "hello world")]

    def test_chunks_multiple_pages_with_page_and_index(self):
        pages = [(1, "short"), (2, "another short text")]
        result = chunk_pages(pages, chunk_size=100, chunk_overlap=20)
        assert result == [(1, 0, "short"), (2, 0, "another short text")]

    def test_splits_page_content_across_chunks(self):
        pages = [(1, "a" * 150)]
        result = chunk_pages(pages, chunk_size=50, chunk_overlap=10)
        assert len(result) >= 2
        assert all(t[0] == 1 for t in result)
        assert [t[1] for t in result] == list(range(len(result)))
