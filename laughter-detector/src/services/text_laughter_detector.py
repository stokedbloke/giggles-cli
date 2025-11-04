"""
Text-based laughter detection service.

This module analyzes text content from Limitless AI transcripts to detect laughter events.
"""

import re
from typing import List, Dict, Any
from datetime import datetime
import asyncio



class TextLaughterDetector:
    """Service for detecting laughter in text transcripts."""
    
    def __init__(self):
        """Initialize the text laughter detector."""
        # Laughter patterns in text
        self.laughter_patterns = [
            r'\b(ha|haha|hahaha|hehe|hehehe|lol|lmao|rofl)\b',
            r'\b(chuckling|giggling|laughing)\b',
            r'[😄😆😂🤣]',  # Laughter emojis
            r'[!]{2,}',  # Multiple exclamation marks (often laughter)
            r'\b(that\'s funny|hilarious|comedy)\b'
        ]
        
        # Compile regex patterns for efficiency
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.laughter_patterns]
        
        print(f"Text laughter detector initialized with {len(self.laughter_patterns)} patterns")
    
    async def detect_laughter_in_text(self, text_content: str, segment_id: str) -> List[Dict[str, Any]]:
        """
        Detect laughter events in text content.
        
        Args:
            text_content: Text content to analyze
            segment_id: ID of the text segment
            
        Returns:
            List of detected laughter events
        """
        try:
            laughter_events = []
            
            # Split text into sentences for better analysis
            sentences = self._split_into_sentences(text_content)
            
            for i, sentence in enumerate(sentences):
                # Check each sentence for laughter patterns
                laughter_score = self._calculate_laughter_score(sentence)
                
                if laughter_score > 0.3:  # Threshold for laughter detection
                    laughter_event = {
                        'id': f"{segment_id}_laughter_{i}",
                        'text': sentence.strip(),
                        'laughter_score': laughter_score,
                        'timestamp': datetime.now().isoformat(),
                        'confidence': min(laughter_score, 1.0)
                    }
                    laughter_events.append(laughter_event)
            
            print(f"Detected {len(laughter_events)} laughter events in text segment {segment_id}")
            return laughter_events
            
        except Exception as e:
            print(f"❌ Error detecting laughter in text: {str(e)}")
            return []
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _calculate_laughter_score(self, text: str) -> float:
        """Calculate laughter score for a piece of text."""
        score = 0.0
        
        for pattern in self.compiled_patterns:
            matches = pattern.findall(text)
            if matches:
                # Increase score based on number of matches and pattern type
                score += len(matches) * 0.2
                
                # Bonus for multiple laughter indicators
                if len(matches) > 1:
                    score += 0.3
                
                # Bonus for emojis
                if any(char in text for char in ['😄', '😆', '😂', '🤣']):
                    score += 0.4
        
        return min(score, 1.0)  # Cap at 1.0


# Global detector instance
text_laughter_detector = TextLaughterDetector()
