from __future__ import annotations

_model = None


def _get_model():
    global _model
    if _model is None:
        from FlagEmbedding import BGEM3FlagModel
        _model = BGEM3FlagModel('BAAI/bge-m3', use_fp16=True)
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = _get_model()
    result = model.encode(texts, batch_size=12, max_length=512)
    return result['dense_vecs'].tolist()
