# AI 技术情报雷达 · AI Tech Intelligence Radar

> 每周自动扫描 AI 社区热点，输出 Top 10 排行 + Fact/Idea 结构化报告。
> 仓库：https://github.com/Stevenwang112/radar-v1-demo

## 快速开始

```bash
# 1. 安装依赖
pip install langchain-core langchain-deepseek langgraph httpx python-dotenv

# 2. 配置 API Key（根目录 .env）
DEEPSEEK_API_KEY=sk-xxx

# 3. 运行
python deliverable/agent/radar_agent.py

# 4. 报告输出
cat deliverable/agent/report_demo.md
```

## 架构

```
START → search_all → final_report → END
          │               │
    ┌─────┼─────┐         ↓
    OR    GH   arXiv   report_demo.md
```

2 节点 LangGraph 线性图。数据源直连 API（无 Tavily），一次 V4-Pro 调用生成报告。

## 输出格式

每条热点包含：
- **Fact**：从 API 提取的客观数据（定价、Star 数、论文编号），标注来源 `[N]`
- **Idea (AI 生成，需人工甄别)**：基于 Fact 推理的机会与风险

首尾带总体趋势分析和 `### Sources` 章节。

## 交付文档

详见 `deliverable/docs/delivery_v1.md`，包含：
1. 需求质疑与假设
2. 方案设计与架构图
3. 6 条关键设计决策
4. LLM 使用说明与成本（¥14.24）
5. 未完成事项

## License

MIT
