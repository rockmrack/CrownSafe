RossNetAgents/
├── agents/
├── config/
├── core_infra/
│   ├── mcp_client_library/ # New folder
│   │   ├── __init__.py
│   │   ├── client.py
│   │   ├── exceptions.py
│   │   ├── models.py
│   │   ├── config.py
│   │   └── requirements.txt
│   └── mcp_router_service/
│       ├── __init__.py
│       ├── main.py
│       ├── router.py
│       ├── discovery.py
│       ├── auth.py
│       ├── config.py
│       ├── requirements.txt
│       ├── state.py
│       └── utils.py
├── docs/
│   └── MCP_Specification_v1.0.md
├── mcp_spec/
│   └── (...)
├── query_analysis_agent/
├── scripts/
├── shared/
├── tests/
└── web_research_agent/