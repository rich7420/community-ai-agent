import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
from ai.prompts import CommunityPrompts
from ai.grok_llm import GrokLLM

def test_min_prompt_llm_integration_no_network():
    qa_prompt = CommunityPrompts.get_qa_prompt()
    messages = qa_prompt.format_messages(context="test context", question="What is this community?")
    llm = GrokLLM.from_environment()
    # Do not call llm; just ensure object exists and messages are built
    assert len(messages) > 0

