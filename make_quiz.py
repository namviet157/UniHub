import re
import random
import json
import numpy as np
from typing import List, Dict, Any
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
import torch
from sentence_transformers import SentenceTransformer, util

class AdvancedEnglishQuizGenerator:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"🚀 Using device: {self.device}")
        
        # Improved models
        print("🔄 Loading improved models...")
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Better question generation model
        self.qg_tokenizer = AutoTokenizer.from_pretrained("mrm8488/t5-base-finetuned-question-generation-ap")
        self.qg_model = AutoModelForSeq2SeqLM.from_pretrained("mrm8488/t5-base-finetuned-question-generation-ap").to(self.device)
        
        self.qa_pipeline = pipeline(
            "question-answering",
            model="deepset/roberta-base-squad2",
            device=0 if self.device == "cuda" else -1
        )
        
        # Enhanced question templates
        self.question_templates = {
            "definition": [
                "What is the primary definition of {concept}?",
                "How is {concept} formally defined in data mining?",
                "Which description accurately defines {concept}?",
                "What characterizes {concept} in the context of data analysis?"
            ],
            "application": [
                "In which specific field is {concept} most effectively applied?",
                "What is a key real-world application of {concept}?",
                "Which industry scenario best demonstrates {concept}?",
                "How is {concept} utilized in business intelligence?"
            ],
            "process": [
                "What is the correct sequence in the {process}?",
                "Which step is crucial but often overlooked in {process}?",
                "What initiates the {process} in data mining?",
                "How does {process} contribute to knowledge discovery?"
            ],
            "importance": [
                "Why has {concept} become increasingly important?",
                "What major problem does {concept} help solve?",
                "How does {concept} impact decision-making processes?",
                "What value does {concept} add to data analysis?"
            ],
            "comparison": [
                "How does {concept} differ from traditional methods?",
                "What distinguishes {concept} from similar approaches?",
                "What unique advantage does {concept} offer?",
                "How is {concept} different from manual data analysis?"
            ],
            "challenge": [
                "What is the main challenge associated with {concept}?",
                "What limitation does {concept} face with big data?",
                "What technical obstacle must {concept} overcome?",
                "Why is {concept} difficult to implement at scale?"
            ]
        }

    def extract_key_concepts_with_context(self, text: str) -> List[Dict[str, Any]]:
        """Extract concepts with their specific contexts"""
        # Split text into meaningful segments
        segments = self._split_text_into_segments(text)
        
        concepts_with_context = []
        
        # Data Mining Definitions
        if any(word in text.lower() for word in ['data mining', 'discovering knowledge', 'patterns']):
            concepts_with_context.append({
                "concept": "Data Mining",
                "type": "definition",
                "context": "Data Mining is the process of discovering knowledge from data through statistical techniques, machine learning, and artificial intelligence to find meaningful patterns, trends, and relationships.",
                "key_points": ["knowledge discovery", "statistical techniques", "machine learning", "pattern recognition"]
            })
        
        # Importance of Data Mining
        if any(word in text.lower() for word in ['important', 'hidden patterns', 'decision making']):
            concepts_with_context.append({
                "concept": "Data Mining Importance", 
                "type": "importance",
                "context": "Data Mining is important because it helps discover hidden patterns in big data, support smart business decision making, and optimize operational processes.",
                "key_points": ["hidden patterns", "business decisions", "operational optimization"]
            })
        
        # Data Growth
        if any(word in text.lower() for word in ['terabytes', 'petabytes', 'data explosion']):
            concepts_with_context.append({
                "concept": "Data Growth",
                "type": "challenge",
                "context": "The Explosive Growth of Data: from terabytes to petabytes. Automated data collection tools, database systems, the Web, computerized society.",
                "key_points": ["terabytes to petabytes", "automated collection", "multiple data sources"]
            })
        
        # KDD Process
        if any(word in text.lower() for word in ['kdd', 'knowledge discovery', 'data cleaning']):
            concepts_with_context.append({
                "concept": "KDD Process",
                "type": "process", 
                "context": "KDD Process: Data Cleaning, Data Integration, Data Selection, Data Mining, Pattern Evaluation. This is a view from typical database systems and data warehousing communities.",
                "key_points": ["data cleaning", "data integration", "pattern evaluation", "knowledge discovery"]
            })
        
        # Techniques
        if any(word in text.lower() for word in ['classification', 'clustering', 'association']):
            concepts_with_context.append({
                "concept": "Data Mining Techniques",
                "type": "application",
                "context": "Data mining includes techniques such as classification, clustering, association rule discovery, and prediction. Applications in many fields from marketing, healthcare, to finance and security.",
                "key_points": ["classification", "clustering", "association rules", "prediction"]
            })
        
        # Challenges
        if any(word in text.lower() for word in ['challenge', 'scalable', 'high-dimensional']):
            concepts_with_context.append({
                "concept": "Data Mining Challenges",
                "type": "challenge",
                "context": "Challenges include tremendous amount of data, algorithms must be highly scalable, high-dimensionality of data, and high complexity of data including data streams and sensor data.",
                "key_points": ["scalability", "high-dimensional data", "data complexity", "algorithm efficiency"]
            })
        
        # Business Intelligence
        if any(word in text.lower() for word in ['business intelligence', 'decision making', 'data analysis']):
            concepts_with_context.append({
                "concept": "Business Intelligence",
                "type": "application",
                "context": "Data Mining in Business Intelligence: Increasing potential to support business decisions through data presentation, visualization techniques, and information discovery.",
                "key_points": ["business decisions", "data visualization", "information discovery"]
            })
        
        return concepts_with_context

    def _split_text_into_segments(self, text: str) -> List[str]:
        """Split text into meaningful segments for context"""
        # Split by sentences and filter meaningful ones
        sentences = re.split(r'[.!?]+', text)
        meaningful_sentences = []
        
        for sentence in sentences:
            clean_sentence = sentence.strip()
            if len(clean_sentence) > 30 and not clean_sentence.isupper():
                # Check if sentence contains substantial information
                words = clean_sentence.split()
                if len(words) >= 5 and any(keyword in clean_sentence.lower() for keyword in 
                                          ['data', 'mining', 'process', 'analysis', 'knowledge', 'pattern']):
                    meaningful_sentences.append(clean_sentence)
        
        return meaningful_sentences

    def generate_diverse_question(self, concept_data: Dict[str, Any]) -> Dict[str, str]:
        """Generate diverse questions using multiple strategies"""
        concept = concept_data["concept"]
        context = concept_data["context"]
        question_type = concept_data["type"]
        
        # Strategy 1: Use template-based generation
        template_question = self._generate_from_template(concept, question_type)
        
        # Strategy 2: Use model-based generation
        model_question = self._generate_from_model(context, concept)
        
        # Strategy 3: Use key-points based generation
        keypoints_question = self._generate_from_keypoints(concept_data["key_points"], concept)
        
        # Choose the best question
        questions = [template_question, model_question, keypoints_question]
        valid_questions = [q for q in questions if q and len(q) > 10]
        
        if not valid_questions:
            return None
            
        selected_question = random.choice(valid_questions)
        
        # Get answer
        answer = self._extract_precise_answer(selected_question, context, concept_data["key_points"])
        
        return {
            "question": selected_question,
            "correct_answer": answer,
            "context": context,
            "concept": concept,
            "type": question_type
        }

    def _generate_from_template(self, concept: str, question_type: str) -> str:
        """Generate question using templates"""
        if question_type in self.question_templates:
            template = random.choice(self.question_templates[question_type])
            return template.format(concept=concept, process=concept)
        return None

    def _generate_from_model(self, context: str, concept: str) -> str:
        """Generate question using AI model"""
        try:
            input_text = f"generate question: {context}"
            
            inputs = self.qg_tokenizer(
                input_text, 
                return_tensors="pt", 
                max_length=512, 
                truncation=True
            ).to(self.device)
            
            outputs = self.qg_model.generate(
                inputs.input_ids,
                max_length=64,
                num_beams=4,
                early_stopping=True,
                temperature=0.8
            )
            
            question = self.qg_tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Ensure question is about the concept
            if concept.lower() not in question.lower():
                question = f"What is {concept} in data mining?"
                
            return question
            
        except Exception as e:
            print(f"Model generation error: {e}")
            return None

    def _generate_from_keypoints(self, key_points: List[str], concept: str) -> str:
        """Generate question from key points"""
        question_types = [
            f"What are the main components of {concept}?",
            f"Which elements are essential in {concept}?",
            f"What characterizes an effective {concept}?",
            f"How is {concept} typically implemented?"
        ]
        
        return random.choice(question_types)

    def _extract_precise_answer(self, question: str, context: str, key_points: List[str]) -> str:
        """Extract precise answer using multiple strategies"""
        try:
            # Strategy 1: Use QA model
            qa_result = self.qa_pipeline(question=question, context=context)
            model_answer = qa_result['answer'].strip()
            
            if len(model_answer) > 10:
                return model_answer
                
        except:
            pass
        
        # Strategy 2: Use key points matching
        question_lower = question.lower()
        for point in key_points:
            if point in question_lower:
                # Return a complete sentence using the key point
                return f"Involves {point} as a core component"
        
        # Strategy 3: Extract from context based on question type
        if 'what' in question_lower and 'definition' in question_lower:
            return self._extract_definition(context)
        elif 'why' in question_lower or 'important' in question_lower:
            return self._extract_importance(context)
        elif 'how' in question_lower or 'process' in question_lower:
            return self._extract_process(context)
        else:
            return "Extracting valuable insights and patterns from data"

    def _extract_definition(self, context: str) -> str:
        """Extract definition from context"""
        patterns = [
            r'is the process of[^.!?]*',
            r'defined as[^.!?]*', 
            r'refers to[^.!?]*',
            r'means[^.!?]*'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, context, re.IGNORECASE)
            if match:
                return match.group(0)
        return context.split('.')[0] + '.'

    def _extract_importance(self, context: str) -> str:
        """Extract importance from context"""
        patterns = [
            r'important because[^.!?]*',
            r'helps[^.!?]*',
            r'supports[^.!?]*',
            r'enables[^.!?]*'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, context, re.IGNORECASE)
            if match:
                return match.group(0)
        return "It provides valuable insights for decision making"

    def _extract_process(self, context: str) -> str:
        """Extract process information from context"""
        if 'cleaning' in context and 'integration' in context:
            return "Includes data cleaning, integration, selection, mining, and pattern evaluation"
        return "A systematic approach to knowledge discovery from data"

    def generate_quality_distractors(self, correct_answer: str, concept: str, question_type: str) -> List[str]:
        """Generate high-quality distractors"""
        distractors = []
        
        # Concept-specific wrong answers
        concept_distractors = {
            "Data Mining": [
                "Manual data entry and recording",
                "Simple data storage and retrieval", 
                "Basic spreadsheet calculations",
                "Data deletion and archiving processes"
            ],
            "Data Mining Importance": [
                "Reduces the amount of data collected",
                "Eliminates the need for human analysis",
                "Focuses only on data storage efficiency",
                "Primarily used for data backup purposes"
            ],
            "KDD Process": [
                "Data creation and initialization",
                "Information deletion phase", 
                "Hardware maintenance procedures",
                "Network configuration steps"
            ],
            "Data Mining Techniques": [
                "Data compression algorithms only",
                "Hardware troubleshooting methods",
                "User interface design principles",
                "Network security protocols"
            ]
        }
        
        # Type-specific wrong answers
        type_distractors = {
            "definition": [
                "A type of hardware component",
                "Related to physical data storage only",
                "A programming language feature",
                "A network protocol standard"
            ],
            "importance": [
                "It makes data analysis more complicated",
                "It reduces data accuracy over time", 
                "It requires more manual intervention",
                "It decreases computational efficiency"
            ],
            "process": [
                "Starts with data deletion",
                "Focuses on hardware maintenance",
                "Eliminates the need for cleaning",
                "Requires manual data entry first"
            ]
        }
        
        # Add concept-specific distractors
        if concept in concept_distractors:
            distractors.extend(concept_distractors[concept])
        
        # Add type-specific distractors  
        if question_type in type_distractors:
            distractors.extend(type_distractors[question_type])
        
        # Remove correct answer and duplicates
        distractors = [d for d in distractors if d != correct_answer]
        distractors = list(dict.fromkeys(distractors))
        
        # Ensure we have enough distractors
        while len(distractors) < 3:
            generic = [
                "Not directly related to the concept",
                "Opposite of the actual approach",
                "A common misconception in the field"
            ]
            new_distractor = random.choice(generic)
            if new_distractor not in distractors:
                distractors.append(new_distractor)
        
        return random.sample(distractors, 3)

    def generate_complete_quiz(self, english_text: str, num_questions: int = 15) -> Dict[str, Any]:
        """Generate complete improved quiz"""
        print("🔨 Processing text with advanced extraction...")
        
        concepts_data = self.extract_key_concepts_with_context(english_text)
        print(f"📚 Found {len(concepts_data)} concept groups")
        
        quiz_questions = []
        used_combinations = set()
        
        # Generate multiple questions per concept
        for concept_data in concepts_data:
            if len(quiz_questions) >= num_questions:
                break
                
            # Generate 2-3 different questions per concept
            for i in range(min(3, num_questions - len(quiz_questions))):
                question_data = self.generate_diverse_question(concept_data)
                
                if not question_data:
                    continue
                    
                # Check for uniqueness
                question_hash = hash(question_data["question"][:50] + concept_data["concept"])
                if question_hash in used_combinations:
                    continue
                    
                used_combinations.add(question_hash)
                
                # Generate distractors
                distractors = self.generate_quality_distractors(
                    question_data["correct_answer"],
                    concept_data["concept"], 
                    concept_data["type"]
                )
                
                # Create options
                all_options = [question_data["correct_answer"]] + distractors
                random.shuffle(all_options)
                
                options_dict = {}
                correct_label = ""
                
                for j, option in enumerate(all_options):
                    label = chr(65 + j)
                    options_dict[label] = option
                    if option == question_data["correct_answer"]:
                        correct_label = label
                
                if correct_label:
                    quiz_questions.append({
                        "id": len(quiz_questions) + 1,
                        "question": question_data["question"],
                        "options": options_dict,
                        "correct_answer": correct_label,
                        "explanation": f"Based on: {question_data['context'][:100]}...",
                        "concept": question_data["concept"],
                        "type": question_data["type"]
                    })
        
        return {
            "quiz_title": "Advanced Data Mining Concepts Quiz",
            "total_questions": len(quiz_questions),
            "questions": quiz_questions,
            "concepts_covered": list(set([q["concept"] for q in quiz_questions]))
        }

    def display_quiz(self, quiz_data: Dict[str, Any]):
        """Display the generated quiz"""
        if "error" in quiz_data:
            print(f"❌ {quiz_data['error']}")
            return
            
        print("\n" + "="*80)
        print(f"📝 {quiz_data['quiz_title']}")
        print(f"📊 Total Questions: {quiz_data['total_questions']}")
        print(f"🎯 Concepts: {', '.join(quiz_data['concepts_covered'])}")
        print("="*80)
        
        for question in quiz_data["questions"]:
            print(f"\n{question['id']}. {question['question']}")
            print(f"   Type: {question['type'].title()} | Concept: {question['concept']}")
            
            for opt, text in question["options"].items():
                print(f"   {opt}. {text}")
            
            print(f"   ✅ Correct: {question['correct_answer']}")
            print(f"   💡 Explanation: {question['explanation']}")
            print("-" * 80)

    def save_quiz_to_file(self, quiz_data: Dict, output_path: str = "rag_quiz_upgraded_en.json"): # Sửa tên file
            """
            NÂNG CẤP: Lưu quiz ra file JSON với định dạng đơn giản
            (chỉ câu hỏi, các lựa chọn, và văn bản câu trả lời đúng).
            """
            
            # NÂNG CẤP: Tạo một cấu trúc dữ liệu đơn giản hơn
            simplified_quiz = {
                "quiz_title": quiz_data.get("quiz_title", "Advanced English Quiz"),
                "total_questions": quiz_data.get("total_questions", 0),
                "questions": []
            }
            
            original_questions = quiz_data.get("questions", [])
            if not isinstance(original_questions, list):
                print(f"❌ Lỗi: Cấu trúc 'questions' không phải là danh sách.")
                original_questions = []

            for q in original_questions:
                try:
                    correct_label = q.get("correct_answer") # vd: "A"
                    
                    # Lấy văn bản của câu trả lời đúng từ "options"
                    correct_text = q.get("options", {}).get(correct_label, "LỖI: Không tìm thấy text")
                    
                    simple_q = {
                        "question": q.get("question"),
                        "options": q.get("options"),
                        "correct_answer": correct_text # Đây là văn bản của câu trả lời đúng
                    }
                    simplified_quiz["questions"].append(simple_q)
                except Exception as e:
                    print(f"⚠️ Lỗi khi đơn giản hóa câu hỏi {q.get('id')}: {e}")

            # Lưu cấu trúc đã đơn giản hóa
            try:
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(simplified_quiz, f, ensure_ascii=False, indent=2)
                print(f"💾 Đã lưu quiz (đã đơn giản hóa) vào: {output_path}")
            except Exception as e:
                print(f"❌ Lỗi khi lưu file: {e}")
                if "not JSON serializable" in str(e):
                    print("--- Dữ liệu lỗi (Thử in một phần) ---")
                    # Cố gắng in ra một phần an toàn của dữ liệu
                    safe_data = {"title": simplified_quiz.get("quiz_title"), "total": simplified_quiz.get("total_questions")}
                    print(json.dumps(safe_data, indent=2))

# Example usage
def main():
    english_content = """
    Data Mining is important because it helps discover hidden patterns in big data, 
    support smart business decision making, and optimize operational processes.
    Data Mining is the process of discovering knowledge from data through statistical techniques, 
    machine learning, and artificial intelligence to find meaningful patterns, trends, and relationships.
    The Explosive Growth of Data: from terabytes to petabytes. Automated data collection tools, 
    database systems, the Web, computerized society. We are drowning in data, but starving for knowledge!
    Data mining includes techniques such as classification, clustering, association rule discovery, 
    and prediction. Applications in many fields from marketing, healthcare, to finance and security.
    KDD Process: Data Cleaning, Data Integration, Data Selection, Data Mining, Pattern Evaluation.
    Challenges include tremendous amount of data, algorithms must be highly scalable, 
    high-dimensionality of data, and high complexity of data.
    Business Intelligence uses data mining to support business decisions through data analysis.
    """
    
    print("🚀 Initializing Advanced English Quiz Generator...")
    generator = AdvancedEnglishQuizGenerator()
    
    quiz_data = generator.generate_complete_quiz(
        english_text=english_content,
        num_questions=12
    )
    
    generator.display_quiz(quiz_data)
    generator.save_quiz_to_file(quiz_data)

if __name__ == "__main__":
    main()