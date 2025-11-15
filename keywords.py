import os
import re

VIETNAMESE_STOPWORDS = {
    'và', 'của', 'là', 'có', 'được', 'trong', 'với', 'cho', 'tại', 'để', 'về', 'các', 'một',
    'cũng', 'như', 'khi', 'sẽ', 'đã', 'này', 'nếu', 'vẫn', 'theo', 'đến', 'từ', 'lại',
    'đang', 'bởi', 'những', 'nên', 'trên', 'dưới', 'sau', 'trước', 'giữa', 'vào', 'ra',
    'làm', 'học', 'hiểu', 'biết', 'thấy', 'nghĩ', 'nói', 'viết', 'đọc', 'xem', 'dùng',
    'cần', 'phải', 'muốn', 'có thể', 'để', 'làm', 'và', 'hoặc', 'nhưng', 'mà'
}

class KeywordExtractor:
    def __init__(self, model_name='paraphrase-multilingual-MiniLM-L12-v2', stop_words=None):
        self.model_name = model_name
        self.stop_words = stop_words or VIETNAMESE_STOPWORDS
        self._model = None

    def _init_model(self):
        if self._model is None:
            from keybert import KeyBERT
            self._model = KeyBERT(self.model_name)

    @staticmethod
    def clean_text(text: str) -> str:
        if not text or not isinstance(text, str):
            return ""
        return re.sub(r'\s+', ' ', text).strip()

    def extract_from_text(self, text: str, top_n=5, ngram_range=(1,3), min_length=2):
        cleaned = self.clean_text(text)
        if not cleaned:
            return []
        self._init_model()
        keywords_with_scores = self._model.extract_keywords(
            cleaned,
            keyphrase_ngram_range=ngram_range,
            stop_words=list(self.stop_words),
            top_n=top_n * 3,
            use_mmr=True,
            diversity=0.5
        )
        filtered, seen = [], set()
        for kw, score in keywords_with_scores:
            kw = kw.strip().lower()
            if len(kw) >= min_length and kw not in seen and kw not in self.stop_words:
                filtered.append(kw)
                seen.add(kw)
            if len(filtered) >= top_n:
                break
        return filtered

    def extract_from_summary_file(self, original_filename: str, top_n=5, ngram_range=(1,3), min_length=2):
        base = os.path.splitext(os.path.basename(original_filename))[0]
        path = f"summaries/{base}_summary_EN.txt"
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        return self.extract_from_text(text, top_n=top_n, ngram_range=ngram_range, min_length=min_length)