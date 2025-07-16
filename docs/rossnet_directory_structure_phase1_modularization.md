RossNetAgents/
├── agents/
│   └── research/
│       └── web_research_agent/ # New location
│           ├── __init__.py     # New empty file
│           ├── web_research_agent.py # Moved file (example name)
│           ├── strategic_report.py   # Moved file (example name)
│           └── ...             # Other moved core logic files
├── config/
├── core_infra/
│   ├── mcp_client_library/
│   └── mcp_router_service/
├── docs/
├── mcp_spec/
├── query_analysis_agent/   # Old folder (to be moved/refactored later)
├── scripts/
├── shared/
├── tests/
└── web_research_agent/     # Old folder (can be deleted after moving files)