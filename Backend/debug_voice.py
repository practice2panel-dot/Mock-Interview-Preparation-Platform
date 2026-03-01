#!/usr/bin/env python3
"""
Debug voice delivery evaluation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from simple_evaluation import SimpleEvaluationSystem

def debug_voice_delivery():
    """Debug voice delivery evaluation."""
    print("Debugging Voice Delivery Evaluation")
    print("=" * 50)
    
    evaluator = SimpleEvaluationSystem()
    
    # Test case with fillers
    test_answer = "Um, machine learning is, uh, when computers, like, learn from data, you know"
    print(f"Test Answer: {test_answer}")
    
    # Manual analysis
    words = test_answer.lower().split()
    print(f"Words: {words}")
    print(f"Total words: {len(words)}")
    
    # Check filler words
    filler_words = ['um', 'uh', 'ah', 'er', 'like', 'you know', 'so', 'well', 'um,', 'uh,', 'like,', 'so,']
    filler_count = sum(1 for word in words if word in filler_words)
    filler_ratio = filler_count / len(words)
    print(f"Filler count: {filler_count}")
    print(f"Filler ratio: {filler_ratio:.2%}")
    
    # Check sentence length
    sentences = test_answer.split('.')
    avg_sentence_length = sum(len(sentence.split()) for sentence in sentences) / len(sentences) if sentences else 0
    print(f"Average sentence length: {avg_sentence_length:.1f}")
    
    # Check pauses
    pause_indicators = test_answer.count('  ') + test_answer.count('...') + test_answer.count('--')
    print(f"Pause indicators: {pause_indicators}")
    
    # Calculate score manually
    score = 1  # Start with poor
    
    if filler_ratio < 0.05:
        score += 2
    elif filler_ratio < 0.1:
        score += 1
    
    if avg_sentence_length < 15:
        score += 1
    elif avg_sentence_length < 20:
        score += 0.5
    
    if pause_indicators <= 1:
        score += 1
    elif pause_indicators <= 3:
        score += 0.5
    
    final_score = max(1, min(5, int(score)))
    print(f"Manual calculated score: {final_score}")
    
    # Test with evaluator
    rubric_result = evaluator.evaluate_rubric(test_answer, "What is machine learning?")
    if rubric_result['status'] == 'success':
        voice_score = rubric_result['dimensions']['voice_delivery']
        print(f"Evaluator score: {voice_score['score']}/5")

if __name__ == "__main__":
    debug_voice_delivery()
