"""
Test script to demonstrate multi-step query decomposition improvements
Run this after ingesting your course catalog to see the difference
"""
from chatbot_service import chatbot_service
import sys

def test_query(question: str, use_multi_step: bool = True):
    """Test a query with or without multi-step decomposition"""
    print(f"\n{'='*80}")
    print(f"Question: {question}")
    print(f"Multi-step: {'ENABLED' if use_multi_step else 'DISABLED'}")
    print('='*80)
    
    answer, citations = chatbot_service.get_answer(
        question=question,
        conversation_history=[],
        use_multi_step=use_multi_step
    )
    
    print(f"\nAnswer:\n{answer}")
    print(f"\nCitations found: {len(citations)}")
    for i, cite in enumerate(citations[:3], 1):  # Show first 3
        print(f"  {i}. {cite['source']}, p. {cite['page']}")
    
    return answer, citations


def main():
    """Run comparison tests"""
    print("\n" + "="*80)
    print("MULTI-STEP QUERY TRANSFORMATION TEST")
    print("="*80)
    
    # Test queries that benefit from decomposition
    test_queries = [
        "Tell me about EAST 203",
        "What prerequisites do I need for upper-level Computer Science courses and what courses can I take after completing them?",
        "If I want to major in Psychology, what are the requirements and what courses should I take in my first year?",
        "What's the difference between a BA and BS in Economics?",
    ]
    
    for query in test_queries:
        print("\n" + "#"*80)
        print("# WITH MULTI-STEP DECOMPOSITION")
        print("#"*80)
        answer_multi, citations_multi = test_query(query, use_multi_step=True)
        
        print("\n" + "#"*80)
        print("# WITHOUT MULTI-STEP DECOMPOSITION")
        print("#"*80)
        answer_single, citations_single = test_query(query, use_multi_step=False)
        
        print(f"\n📊 COMPARISON:")
        print(f"  Multi-step citations: {len(citations_multi)}")
        print(f"  Single-step citations: {len(citations_single)}")
        print(f"  Multi-step answer length: {len(answer_multi)} chars")
        print(f"  Single-step answer length: {len(answer_single)} chars")
        
        # Pause between queries
        if query != test_queries[-1]:
            input("\n⏸️  Press Enter to continue to next test...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Test interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
