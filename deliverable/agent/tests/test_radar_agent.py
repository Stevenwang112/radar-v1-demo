"""test_radar_agent.py — 雷达 Agent 基本功能测试"""
import sys, os, json, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from radar_agent import radar_agent, _SEARCHES, _REPORT_PROMPT, _PROMPTS_DIR

def test_prompts_dir_exists():
    assert _PROMPTS_DIR.exists()
    assert (_PROMPTS_DIR / "report_prompt.txt").exists()
    assert (_PROMPTS_DIR / "sources.json").exists()

def test_searches_config():
    assert len(_SEARCHES) == 4
    for s in _SEARCHES:
        assert "label" in s
        assert "query" in s
        assert "domains" in s

def test_report_prompt_has_date_and_week():
    assert "{date}" in _REPORT_PROMPT
    assert "{week}" in _REPORT_PROMPT

def test_agent_graph_has_correct_nodes():
    nodes = list(radar_agent.get_graph().nodes)
    assert "search_all" in nodes
    assert "final_report" in nodes

def test_agent_graph_has_correct_edges():
    edges = list(radar_agent.get_graph().edges)
    edge_pairs = [(e.source, e.target) for e in edges]
    assert ("__start__", "search_all") in edge_pairs
    assert ("search_all", "final_report") in edge_pairs
    assert ("final_report", "__end__") in edge_pairs

if __name__ == "__main__":
    test_prompts_dir_exists()
    test_searches_config()
    test_report_prompt_has_date_and_week()
    test_agent_graph_has_correct_nodes()
    test_agent_graph_has_correct_edges()
    print("All tests passed.")
