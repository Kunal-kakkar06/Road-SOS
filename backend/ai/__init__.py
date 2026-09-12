"""
RoadSOS AI Architecture Package
================================
A modular, pluggable AI layer that sits between FastAPI routes and the
underlying ML services.  Responsibilities are strictly separated:

  schemas/         – typed I/O contracts (input, features, prediction, decision)
  feature_engine/  – wraps existing services to produce a FeatureVector
  models/          – ABC + concrete severity model (wraps fusion_triage)
  decision/        – converts predictions into structured emergency decisions
  rag/             – RAG retrieval interface (stub; not yet configured)
  llm/             – optional LLM explanation interface (wraps Claude)
  pipeline/        – orchestrator that coordinates all components

Nothing here replaces the existing services/ layer.
All existing /api/triage endpoints remain fully backward-compatible.
"""

__version__ = "1.0.0"
