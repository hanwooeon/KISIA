from pathlib import Path
from docling.document_converter import DocumentConverter

SUPPORTED_EXTENSIONS = {
    ".pdf", ".docx", ".pptx", ".xlsx",
    ".png", ".jpg", ".jpeg", ".tiff",
}


def parse_file(file_path: str) -> str:
    path = Path(file_path)
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"지원하지 않는 파일 형식: {path.suffix}")

    converter = DocumentConverter()
    result = converter.convert(str(path))
    return result.document.export_to_markdown()
