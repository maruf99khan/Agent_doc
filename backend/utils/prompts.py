DOCUMENT_CHECK_PROMPT = """You are a professional document editor and writing expert.
Review the following document for:
1. Grammar and spelling errors
2. Clarity and readability
3. Professional tone
4. Structure and organization

Provide:
- A list of issues found
- Corrections and suggestions
- An improved version of the document

Document to review:
{text}

Please provide a detailed analysis and improvement suggestions."""

SUMMARY_PROMPT = """You are a professional summarizer.
Create a comprehensive summary of the following document.

Provide:
1. Executive Summary (2-3 sentences)
2. Key Points (5-7 bullet points)
3. Important Takeaways (3-4 points)

Document to summarize:
{text}

Format your response clearly with these three sections."""

INFO_COLLECTION_PROMPT = """You are an information extraction and organization expert.
Analyze the following document and extract structured information.

Extract and organize:
1. Main Topics/Entities (important subjects)
2. Key Facts (important information)
3. Action Items (if any)
4. Categories (organize information by topic)
5. Important Numbers/Data (statistics, dates, etc.)

Document to analyze:
{text}

Provide a well-organized report of extracted information."""

TOPIC_RESEARCH_PROMPT = """You are a research assistant and information curator.
Provide comprehensive information about: {topic}

Include:
1. Definition and Overview
2. Key Concepts
3. Applications
4. Current Trends
5. Challenges and Limitations
6. Resources for Further Learning

Format your response in a clear, structured way."""
