from gradio_client import Client, handle_file
import json
import os


def ocr_image(image_path: str) -> str:
    client = Client("PaddlePaddle/PaddleOCR-VL-1.5_Online_Demo")
    result = client.predict(
        fp=handle_file(image_path),
        api_name="/run_spotting_wrapper"
    )
    return _extract_text(result)


def _extract_text(result) -> str:
    if result is None:
        return ""
    if isinstance(result, str):
        return _parse_text_value(result)
    if isinstance(result, (list, tuple)):
        texts = []
        for item in result:
            # 이미지 파일 경로는 건너뜀
            if isinstance(item, str) and _is_file_path(item):
                continue
            text = _extract_text(item)
            if text:
                texts.append(text)
        return "\n".join(texts)
    if isinstance(result, dict):
        if "text" in result:
            return result["text"]
        if "rec_texts" in result:
            return "\n".join(t for t in result["rec_texts"] if t)
    return str(result)


def _parse_text_value(s: str) -> str:
    try:
        data = json.loads(s)
        if isinstance(data, list):
            texts = [item.get("text", "") for item in data if isinstance(item, dict)]
            return "\n".join(t for t in texts if t)
        if isinstance(data, dict):
            return data.get("text", s)
    except (json.JSONDecodeError, TypeError):
        pass
    return s


def _is_file_path(s: str) -> bool:
    _, ext = os.path.splitext(s)
    return ext.lower() in {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"}
