import json
from pathlib import Path
import re

class ResourcesQA:
    def __init__(self, index_path="manuals_index.json"):
        """Load the manuals index"""
        with open(index_path, 'r') as f:
            self.index = json.load(f)
        print(f"✅ Loaded {len(self.index)} manual pages")
    
    def search(self, question, max_results=5):
        """Simple keyword-based search that returns relevant pages with citations"""
        # Extract keywords from question
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                      'of', 'with', 'is', 'are', 'was', 'were', 'what', 'how', 'why', 'when',
                      'where', 'who', 'which', 'do', 'does', 'did', 'can', 'could', 'should'}
        
        question_lower = question.lower()
        keywords = [word for word in re.findall(r'\b\w+\b', question_lower) 
                   if word not in stop_words and len(word) > 2]
        
        if not keywords:
            return []
        
        # Score each page based on keyword matches
        results = []
        for page in self.index:
            text_lower = page['text'].lower()
            score = 0
            
            # Count keyword occurrences
            for keyword in keywords:
                score += text_lower.count(keyword)
            
            if score > 0:
                # Extract relevant snippet
                snippet = self._extract_relevant_snippet(page['text'], keywords)
                
                # Get contextual excerpt (better than full page)
                context = self._extract_context(page['text'], keywords)
                
                results.append({
                    'file': page['file'],
                    'page': page['page'],
                    'text': page['text'],
                    'snippet': snippet,
                    'context': context,
                    'keywords': keywords,
                    'score': score
                })
        
        # Sort by score and return top results
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:max_results]
    
    def _extract_relevant_snippet(self, text, keywords, max_words=80):
        """Extract a relevant snippet containing keywords"""
        sentences = re.split(r'[.!?]+', text)
        
        # Find sentences containing keywords
        scored_sentences = []
        for sent in sentences:
            sent_lower = sent.lower()
            score = sum(sent_lower.count(kw) for kw in keywords)
            if score > 0:
                scored_sentences.append((score, sent.strip()))
        
        if not scored_sentences:
            words = text.split()[:max_words]
            return ' '.join(words) + '...'
        
        # Get best sentence
        scored_sentences.sort(reverse=True)
        best_sentence = scored_sentences[0][1]
        
        # If sentence is too long, truncate
        words = best_sentence.split()
        if len(words) > max_words:
            return ' '.join(words[:max_words]) + '...'
        
        # Add more sentences if we have room
        snippet = best_sentence
        word_count = len(words)
        
        for i in range(1, min(3, len(scored_sentences))):
            next_sent = scored_sentences[i][1]
            next_words = len(next_sent.split())
            if word_count + next_words <= max_words:
                snippet += ' ' + next_sent
                word_count += next_words
            else:
                break
        
        return snippet
    
    def _extract_context(self, text, keywords, context_words=200):
        """Extract contextual excerpt around keywords (not full page)"""
        # Find first keyword position
        text_lower = text.lower()
        first_kw_pos = float('inf')
        
        for kw in keywords:
            pos = text_lower.find(kw)
            if pos != -1 and pos < first_kw_pos:
                first_kw_pos = pos
        
        if first_kw_pos == float('inf'):
            # No keywords found, return beginning
            words = text.split()[:context_words]
            return ' '.join(words) + '...'
        
        # Get words before and after
        words = text.split()
        word_positions = []
        current_pos = 0
        
        for i, word in enumerate(words):
            word_positions.append((i, current_pos))
            current_pos += len(word) + 1
        
        # Find word index at first keyword
        kw_word_idx = 0
        for i, pos in word_positions:
            if pos >= first_kw_pos:
                kw_word_idx = i
                break
        
        # Extract context window
        start_idx = max(0, kw_word_idx - 100)
        end_idx = min(len(words), kw_word_idx + 100)
        
        context = ' '.join(words[start_idx:end_idx])
        
        if start_idx > 0:
            context = '...' + context
        if end_idx < len(words):
            context = context + '...'
        
        return context
    
    def highlight_keywords(self, text, keywords):
        """Highlight keywords in text for better scanning"""
        highlighted = text
        for kw in keywords:
            # Case-insensitive replacement with markdown bold
            pattern = re.compile(re.escape(kw), re.IGNORECASE)
            highlighted = pattern.sub(lambda m: f"**{m.group(0)}**", highlighted)
        return highlighted
    
    def format_answer(self, question, results):
        """Format search results into a readable answer with citations"""
        if not results:
            return "I couldn't find relevant information in the manuals for that question."
        
        answer = f"**Answer based on {len(results)} relevant page(s):**\n\n"
        
        for i, result in enumerate(results, 1):
            manual_name = result['file'].replace('.pdf', '').replace('_', ' ')
            snippet = result.get('snippet', result['text'][:200])
            
            answer += f"**{i}. {manual_name} (Page {result['page']})**\n"
            answer += f"{snippet}\n\n"
        
        return answer

# Test the system
if __name__ == "__main__":
    qa = ResourcesQA()
    
    test_questions = [
        "What is TomKat used for?",
        "How do I interpret blood chemistry results?",
    ]
    
    print("\n" + "="*60)
    print("TESTING RESOURCES Q&A SYSTEM")
    print("="*60)
    
    for question in test_questions:
        print(f"\n❓ Question: {question}")
        results = qa.search(question, max_results=2)
        
        if results:
            print(f"\nFound {len(results)} results")
            for r in results:
                print(f"\n  Snippet: {r['snippet'][:100]}...")
                print(f"  Context length: {len(r['context'])} chars")
        print("-"*60)
