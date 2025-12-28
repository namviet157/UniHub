import fitz
import re
import os
import time
import torch
import nltk
from nltk.tokenize import sent_tokenize
from transformers import T5Tokenizer, T5ForConditionalGeneration
from deep_translator import GoogleTranslator

nltk.download('punkt', quiet=True)
nltk.download('punkt_tab', quiet=True)

def translate_text(text, src="en", dest="vi"):
    return GoogleTranslator(source=src, target=dest).translate(text)

class ExtendedLectureSummarizer:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.expansion_tokenizer = T5Tokenizer.from_pretrained("t5-base")
        self.expansion_model = T5ForConditionalGeneration.from_pretrained("t5-base").to(self.device)

    def extract_text_from_pdf(self, file_path):
        try:
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text.strip()
        except Exception:
            return ""

    def expand_with_t5(self, text):
        try:
            prompt = "Elaborate on this text and provide more details: " + text[:500]
            inputs = self.expansion_tokenizer.encode(prompt, return_tensors="pt", max_length=512, truncation=True).to(self.device)
            outputs = self.expansion_model.generate(
                inputs, max_length=280, min_length=100, num_beams=4, early_stopping=True, no_repeat_ngram_size=3
            )
            return self.expansion_tokenizer.decode(outputs[0], skip_special_tokens=True)
        except Exception:
            return text

    def analyze_content_structure(self, text):
        sentences = sent_tokenize(text)
        questions = [s for s in sentences if '?' in s][:5]
        definitions = [s for s in sentences if any(k in s.lower() for k in ['là ', 'gọi là', 'định nghĩa', 'means', 'refers to'])][:5]
        statements = [s for s in sentences if s not in questions and s not in definitions][:10]
        return {'questions': questions, 'definitions': definitions, 'statements': statements}

    def create_detailed_explanation(self, text):
        a = self.analyze_content_structure(text)
        parts = []

        if a['questions']:
            parts.append("KEY QUESTIONS:")
            for i, q in enumerate(a['questions'], 1):
                parts.append(f"{i}. {q}")
                parts.append(f"   → [Will be explained in detail]")

        if a['definitions']:
            parts.append("\nKEY CONCEPTS:")
            for i, d in enumerate(a['definitions'], 1):
                parts.append(f"{i}. {d}")
                parts.append(f"   → [Expanded below]")

        if a['statements']:
            parts.append("\nBACKGROUND INFO:")
            for s in a['statements']:
                parts.append(f"• {s}")

        return "\n".join(parts)

    def comprehensive_expansion(self, text):
        detailed = self.create_detailed_explanation(text)
        expanded_t5 = self.expand_with_t5(text)

        return f"""DETAILED SUMMARY

{detailed}

AI EXPANSION:
{expanded_t5}

CONCLUSION:
This document covers essential concepts with practical applications in multiple domains. Further analysis can enhance understanding and implementation."""

    @staticmethod
    def split_text_into_chunks(text, max_chunk_size=4000):
        chunks = []
        paragraphs = text.split('\n')
        current_chunk = ""
        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) > max_chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
            current_chunk += paragraph + "\n"
        if current_chunk:
            chunks.append(current_chunk.strip())
        return chunks

    def translate_vietnamese_to_english(self, text):
        try:
            chunks = self.split_text_into_chunks(text)
            translated_chunks = []
            for chunk in chunks:
                translated = translate_text(chunk, src="vi", dest="en")
                translated_chunks.append(translated)
                time.sleep(1)
            return " ".join(translated_chunks)
        except Exception:
            return None

    def process(self, file_path):
        text = self.extract_text_from_pdf(file_path)
        if not text or len(text) < 50:
            return None

        text = re.sub(r'\s+', ' ', text).strip()
        vn_summary = self.comprehensive_expansion(text)
        en_summary = self.translate_vietnamese_to_english(vn_summary) or vn_summary

        return {
            'english': en_summary,
            'original_chars': len(text),
            'summary_chars': len(en_summary)
        }

    def save_english_summary(self, data, input_path):
        base = os.path.splitext(os.path.basename(input_path))[0]
        os.makedirs("summaries", exist_ok=True)
        output_file = f"summaries/{base}_summary_EN.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(data['english'])

    def get_summary_text(self, file_path):
        result = self.process(file_path)
        return result['english'] if result else None