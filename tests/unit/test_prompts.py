import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
from ai.prompts import CommunityPrompts

def test_qa_prompt_creation():
    prompt = CommunityPrompts.get_qa_prompt()
    assert prompt is not None

def test_weekly_prompt_creation():
    prompt = CommunityPrompts.get_weekly_report_prompt()
    assert prompt is not None

def test_format_qa_context():
    docs = [{"source":"slack","content":"hello","timestamp":"2024-01-01"}]
    ctx = CommunityPrompts.format_qa_context(docs)
    assert "Source: slack" in ctx
    assert "Content: hello" in ctx

def test_format_weekly_data():
    data = {"github":{"commits":1,"prs":0,"issues":0,"contributors":1},"slack":{"messages":10,"users":2,"top_channels":["general"],"topics":["ai"]}}
    out = CommunityPrompts.format_weekly_data(data)
    assert "GitHub:" in out
    assert "Slack:" in out

