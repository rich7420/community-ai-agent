import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
from ai.grok_llm import GrokLLM

def test_grok_llm_from_env_dummy():
    # Ensure no crash even if key missing; class provides dummy key
    if 'OPENROUTER_API_KEY' in os.environ:
        del os.environ['OPENROUTER_API_KEY']
    llm = GrokLLM.from_environment()
    info = llm.get_model_info()
    assert 'model_name' in info

