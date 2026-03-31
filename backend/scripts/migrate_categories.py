"""Migrate handbook_terms categories from old 11-category to new 9-category system.

Old: ai-ml, db-data, backend, frontend-ux, network, security, os-core, devops, performance, web3, ai-business
New: cs-fundamentals, math-statistics, ml-fundamentals, deep-learning, llm-genai, data-engineering, infra-hardware, safety-ethics, products-platforms
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_supabase

# Simple old → new fallback mapping
FALLBACK_MAP = {
    "ai-ml": "llm-genai",
    "db-data": "data-engineering",
    "backend": "cs-fundamentals",
    "frontend-ux": "cs-fundamentals",
    "network": "cs-fundamentals",
    "security": "safety-ethics",
    "os-core": "cs-fundamentals",
    "devops": "infra-hardware",
    "performance": "infra-hardware",
    "web3": "cs-fundamentals",
    "ai-business": "products-platforms",
}

NEW_VALID = {
    "cs-fundamentals", "math-statistics", "ml-fundamentals",
    "deep-learning", "llm-genai", "data-engineering",
    "infra-hardware", "safety-ethics", "products-platforms",
}

# Per-term overrides for accurate categorization
OVERRIDES = {
    # CS fundamentals
    "API (Application Programming Interface)": ["cs-fundamentals"],
    "SQL (Structured Query Language)": ["cs-fundamentals"],
    "NoSQL (Not Only SQL)": ["cs-fundamentals", "data-engineering"],
    "DOM (Document Object Model)": ["cs-fundamentals"],
    "OAuth (Open Authorization)": ["cs-fundamentals", "safety-ethics"],
    "SAML (Security Assertion Markup Language)": ["cs-fundamentals", "safety-ethics"],
    "asynchronous programming": ["cs-fundamentals"],
    "Code Review": ["cs-fundamentals"],
    "SI (System Integration)": ["cs-fundamentals"],
    "SM (System Management)": ["cs-fundamentals"],
    "Vue.js": ["cs-fundamentals"],
    "React": ["cs-fundamentals"],
    "Cross-device Tracking": ["cs-fundamentals"],
    "CMMI (Capability Maturity Model Integration)": ["cs-fundamentals"],
    "NFT (Non-Fungible Token)": ["cs-fundamentals"],
    "open-source": ["cs-fundamentals"],
    "MCP (Model Context Protocol)": ["llm-genai", "cs-fundamentals"],

    # Math/statistics
    " Z-Score (Standard Score)": ["math-statistics"],
    "Z-Score (Standard Score)": ["math-statistics"],
    "H\u2080 (Null Hypothesis)": ["math-statistics"],
    "H\u2081/Ha (Alternative Hypothesis)": ["math-statistics"],
    "COV (Covariance)": ["math-statistics"],
    "ARIMA (Auto-Regressive Integrated Moving Average)": ["math-statistics"],
    "MA (Moving Average Model)": ["math-statistics"],
    "LASSO Regression (Least Absolute Shrinkage and Selection Operator)": ["math-statistics", "ml-fundamentals"],
    "Ridge Regression": ["math-statistics", "ml-fundamentals"],
    "Principal Component Analysis (PCA)": ["math-statistics", "ml-fundamentals"],
    "Entropy": ["math-statistics", "deep-learning"],
    "AR": ["math-statistics"],
    "AR ": ["math-statistics"],

    # ML fundamentals
    "KNN (K-Nearest Neighbors)": ["ml-fundamentals"],
    "SVM (Support Vector Machine)": ["ml-fundamentals"],
    "Decision Tree": ["ml-fundamentals"],
    "A/B Test": ["ml-fundamentals", "data-engineering"],
    "CRISP-DM (Cross-Industry Standard Process for Data Mining)": ["ml-fundamentals", "data-engineering"],
    "KDD (Knowledge Discovery in Databases)": ["ml-fundamentals", "data-engineering"],
    "Machine Learning": ["ml-fundamentals"],
    "Feature Extraction": ["ml-fundamentals"],
    "SOTA(State of the Art)": ["ml-fundamentals"],
    "reinforcement learning": ["ml-fundamentals"],
    "RLHF": ["ml-fundamentals", "llm-genai"],
    "MARL": ["ml-fundamentals"],
    "evolutionary search": ["ml-fundamentals"],
    "variation operator": ["ml-fundamentals"],
    "algorithmic overhaul": ["ml-fundamentals"],
    "Avocado": ["products-platforms", "ml-fundamentals"],
    "zero-shot sim-to-real transfer": ["deep-learning", "ml-fundamentals"],

    # Deep learning
    "deep learning": ["deep-learning"],
    "CV (Computer Vision)": ["deep-learning"],
    "Self-Attention": ["deep-learning", "llm-genai"],
    "diffusion model": ["deep-learning"],
    "BERT": ["deep-learning", "llm-genai"],
    "generative AI": ["deep-learning", "llm-genai"],
    "recurrent mechanism": ["deep-learning", "llm-genai"],
    "vision-language model": ["deep-learning", "llm-genai"],
    "multimodal model": ["deep-learning", "llm-genai"],
    "multi-modal systems": ["deep-learning", "llm-genai"],
    "grouped-query attention": ["deep-learning", "llm-genai"],
    "multi-head attention kernel": ["deep-learning"],
    "GPU kernel optimization": ["deep-learning", "infra-hardware"],
    "image generation": ["deep-learning"],
    "real-time neural rendering": ["deep-learning", "infra-hardware"],
    "real-time rendering": ["deep-learning", "infra-hardware"],
    "3D navigation": ["deep-learning"],
    "mixture of experts": ["deep-learning", "llm-genai"],
    "embedding": ["deep-learning", "llm-genai"],
    "DLSS": ["infra-hardware", "deep-learning"],
    "stereo matching": ["deep-learning"],
    "Sora video model": ["products-platforms", "deep-learning"],
    "Imagen Video": ["products-platforms", "deep-learning"],
    "MAI-Image-2": ["products-platforms", "deep-learning"],
    "Adobe Firefly": ["products-platforms", "deep-learning"],
    "natural language processing": ["deep-learning", "llm-genai"],

    # LLM/GenAI
    "hallucination": ["llm-genai"],
    "agentic model": ["llm-genai"],
    "agentic AI": ["llm-genai"],
    "AI agents": ["llm-genai"],
    "multi-hop retrieval": ["llm-genai", "data-engineering"],
    "self-editing context": ["llm-genai"],
    "verification-centric agents": ["llm-genai"],
    "context window": ["llm-genai"],
    "large language model": ["llm-genai"],
    "foundation model": ["llm-genai"],
    "output tokens": ["llm-genai"],
    "Tokenization": ["llm-genai"],
    "reasoning": ["llm-genai"],
    "local inference": ["llm-genai", "infra-hardware"],
    "open-source LLM": ["llm-genai"],
    "open-weight models": ["llm-genai"],
    "open-source models": ["llm-genai"],
    "open frontier models": ["llm-genai"],
    "content retrieval": ["llm-genai", "data-engineering"],
    "content recommendations": ["llm-genai"],
    "Keyword-based Algorithms": ["llm-genai", "data-engineering"],
    "Feed Algorithm": ["llm-genai", "data-engineering"],
    "AI-native framework": ["llm-genai", "infra-hardware"],
    "multi-agent system": ["llm-genai"],
    "self-verification": ["llm-genai"],
    "token usage": ["llm-genai"],
    "fine-tuning": ["ml-fundamentals", "llm-genai"],
    "supervised fine-tuning": ["ml-fundamentals", "llm-genai"],
    "multi-stage training": ["ml-fundamentals", "llm-genai"],
    "pre-training": ["ml-fundamentals", "llm-genai"],
    "post-training": ["ml-fundamentals", "llm-genai"],

    # Data engineering
    "Hadoop": ["data-engineering"],
    "ETL (Extract, Transform, Load)": ["data-engineering"],
    "Data Governance": ["data-engineering"],
    "Data Visualization": ["data-engineering"],
    "knowledge base": ["data-engineering", "llm-genai"],
    "operational data": ["data-engineering"],
    "Real-time Data Processing": ["data-engineering", "infra-hardware"],
    "e-commerce logistics": ["data-engineering"],
    "actionable intelligence": ["data-engineering"],

    # Infra/hardware
    "GPU": ["infra-hardware"],
    "GPU cluster": ["infra-hardware"],
    "supercomputer": ["infra-hardware"],
    "inference cost": ["infra-hardware", "llm-genai"],
    "inference latency": ["infra-hardware", "llm-genai"],
    "real-time inference": ["infra-hardware", "llm-genai"],
    "on-device AI": ["infra-hardware", "llm-genai"],
    "live audio translation": ["llm-genai", "infra-hardware"],
    "AI infrastructure": ["infra-hardware"],
    "AI datacentre": ["infra-hardware"],
    "FlashAttention-4": ["infra-hardware", "deep-learning"],
    "cuDNN": ["infra-hardware", "products-platforms"],
    "Cluster scheduler": ["infra-hardware"],
    "automation": ["infra-hardware"],
    "lightweight installation script": ["infra-hardware"],
    "decentralized AI processing": ["infra-hardware"],
    "adaptive quantization": ["infra-hardware"],
    "data center": ["infra-hardware"],
    "compute": ["infra-hardware"],
    "cross-platform AI": ["infra-hardware", "llm-genai"],
    "dynamic content delivery": ["infra-hardware"],
    "telecommunications services": ["infra-hardware"],
    "workflow orchestration": ["infra-hardware"],
    "computing power": ["infra-hardware"],
    "AWS (Amazon Web Services)": ["infra-hardware", "products-platforms"],

    # Safety/ethics
    "supply chain vulnerability": ["safety-ethics"],
    "agentic access management": ["safety-ethics", "llm-genai"],
    "machine identities": ["safety-ethics"],
    "closed systems": ["safety-ethics"],
    "Mirai": ["safety-ethics"],

    # Products/platforms
    "GPT-4o": ["products-platforms", "llm-genai"],
    "Anthropic": ["products-platforms"],
    "OpenAI": ["products-platforms"],
    "Nvidia": ["products-platforms"],
    "Gemini 3.1": ["products-platforms", "llm-genai"],
    "Gemini AI": ["products-platforms", "llm-genai"],
    "Gemini": ["products-platforms", "llm-genai"],
    "NVIDIA Blackwell": ["products-platforms", "infra-hardware"],
    "NVIDIA DGX Cloud": ["products-platforms", "infra-hardware"],
    "Composer 2": ["products-platforms", "infra-hardware"],
    "ChatGPT": ["products-platforms", "llm-genai"],
    "Claude": ["products-platforms", "llm-genai"],
    "M2.7 model": ["products-platforms"],
    "Vera Rubin platform": ["products-platforms", "infra-hardware"],
    "AI startup fundraising": ["products-platforms"],
    "AI-native precision health": ["products-platforms"],
    "AI-driven efficiencies": ["infra-hardware"],
    "photorealistic graphics": ["deep-learning"],
    "funding round": ["products-platforms"],
    "legacy infrastructure": ["infra-hardware"],
}


def migrate(dry_run: bool = True):
    sb = get_supabase()
    result = sb.table("handbook_terms").select("id,term,categories").neq("status", "archived").execute()
    print(f"Total terms: {len(result.data)}")

    updates = []
    for r in result.data:
        term = r["term"]
        old_cats = r.get("categories", []) or []

        # Check overrides (exact match, then stripped)
        new_cats = OVERRIDES.get(term) or OVERRIDES.get(term.strip())

        if not new_cats:
            # Fallback: map each old category
            mapped = set()
            for old_cat in old_cats:
                if not old_cat:
                    continue
                if old_cat in NEW_VALID:
                    mapped.add(old_cat)  # already new format
                elif old_cat in FALLBACK_MAP:
                    mapped.add(FALLBACK_MAP[old_cat])
            new_cats = sorted(mapped) if mapped else ["llm-genai"]

        if sorted(old_cats) != sorted(new_cats):
            updates.append((r["id"], term, old_cats, new_cats))

    print(f"Updates needed: {len(updates)}")

    for tid, term, old, new in updates:
        print(f"  {term:50s} | {old} -> {new}")
        if not dry_run:
            sb.table("handbook_terms").update({"categories": new}).eq("id", tid).execute()

    if not dry_run:
        print(f"\nApplied {len(updates)} updates.")
    else:
        print(f"\nDry run complete. Pass --apply to execute.")


if __name__ == "__main__":
    apply = "--apply" in sys.argv
    migrate(dry_run=not apply)
