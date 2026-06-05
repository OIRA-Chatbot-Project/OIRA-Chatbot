Analyze the following question and determine if it needs to be decomposed into sub-questions for better retrieval.

Question: $question

Determine the question type and respond with valid JSON:

1. SIMPLE - Single focused question that can be answered with one retrieval
   Examples: "What is CSCI 204?", "What are the prerequisites for MATH 211?"
   Response: {"type": "simple"}

2. COMPLEX - Requires multiple retrievals to answer completely
   Examples:
   - Comparisons: "What are the differences between Computer Science and Computer Engineering?"
   - Multi-part: "What courses should I take for a CS major with a math minor?"
   - Multiple entities: "Tell me about CSCI 204, CSCI 206, and MATH 211"

   Break into 2-5 specific sub-questions that each target distinct information.
   Each sub-question should be:
   - Standalone and clear (no pronouns like "it" or "that")
   - Focused on a single piece of information
   - Suitable for independent retrieval

   Response: {"type": "complex", "sub_questions": ["question 1", "question 2", ...]}

3. TOO_BROAD - Question is too general to answer effectively
   Examples: "Tell me everything", "What should I study?", "Explain the entire catalog"

   Provide a helpful suggestion to narrow the question.
   Response: {"type": "too_broad", "suggestion": "Please narrow your question to a specific major, course, or requirement."}

Important:
- Return ONLY valid JSON, no additional text
- For simple questions, just return {"type": "simple"}
- Keep sub-questions under 5 (enforce strict limit)
- Make sub-questions self-contained (include context from original question)

JSON:
