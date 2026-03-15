from src.processing.file_readers import read_file_to_text


def test_read_plain_text_file(tmp_path):
    file_path = tmp_path / "note.txt"
    file_path.write_text("contenuto semplice", encoding="utf-8")
    result = read_file_to_text(file_path)
    assert result["text"] == "contenuto semplice"
    assert result["metadata"]["reader"] == "plain_text"
    assert result["tables"] == []
