#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DMXAPI Free Models RSS Feed & Dashboard Generator
Fetches free AI models from https://www.dmxapi.cn/v1/models,
tracks model history in data/history.json, and generates:
- dist/rss.xml (Standard RSS 2.0 with Atom namespace)
- dist/atom.xml (Standard Atom 1.0)
- dist/models.json (Structured JSON data)
- dist/index.html (Modern responsive dark-mode web page)
"""

import os
import sys
import json
import logging
import xml.sax.saxutils as saxutils
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import requests
from dateutil import parser as date_parser

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("dmxapi_free_models")

# API & Base URLs
API_URL = "https://www.dmxapi.cn/v1/models"
SITE_URL = "https://www.dmxapi.cn"
DEFAULT_API_KEY = "sk-oLm648AcatWOQQB9N0rFvylA5roHsuk0BI5iDqIPte2awTfX"
FEED_TITLE = "DMXAPI 免费模型动态 | Free Models Feed"
FEED_DESCRIPTION = "实时追踪 DMXAPI 平台所有免费 AI 模型与可用端点更新 (https://www.dmxapi.cn)"
BASE_PAGE_URL = "https://mmschzs.github.io/dmxapi-free-models-rss"
FEED_URL_RSS = f"{BASE_PAGE_URL}/rss.xml"
FEED_URL_ATOM = f"{BASE_PAGE_URL}/atom.xml"

# Project paths
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")


def get_api_key() -> str:
    """Retrieve DMX API Key from environment or fallback default."""
    api_key = os.environ.get("DMX_API_KEY", "").strip()
    if not api_key:
        api_key = DEFAULT_API_KEY
    return api_key


def fetch_models(api_key: str) -> List[Dict[str, Any]]:
    """Fetch model list from DMXAPI."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "User-Agent": "DMXAPI-Free-Models-RSS/1.0"
    }
    logger.info(f"Requesting models from {API_URL} ...")
    resp = requests.get(API_URL, headers=headers, timeout=30)
    resp.raise_for_status()
    payload = resp.json()
    
    models = payload.get("data", [])
    if not isinstance(models, list):
        logger.warning(f"Unexpected API response structure: {type(payload)}")
        models = []
    
    logger.info(f"Successfully fetched {len(models)} total models from DMXAPI.")
    return models


def filter_free_models(all_models: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter models ending with 'free' (case-insensitive)."""
    free_models = []
    for m in all_models:
        if not isinstance(m, dict):
            continue
        model_id = str(m.get("id", "")).strip()
        if model_id.lower().endswith("free"):
            free_models.append(m)
    
    logger.info(f"Found {len(free_models)} free models ending with 'free'.")
    return free_models


def load_history() -> Dict[str, Any]:
    """Load historical tracking data from data/history.json."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "models" in data:
                    return data
        except Exception as e:
            logger.warning(f"Failed to read history file, initializing fresh: {e}")
    
    return {
        "version": "1.0",
        "last_updated": None,
        "models": {}
    }


def update_history(current_free_models: List[Dict[str, Any]], history: Dict[str, Any], now_dt: datetime) -> Dict[str, Any]:
    """
    Update historical model records:
    - Track first_seen, last_seen, is_active
    - Detect newly added, back online, and offline models
    """
    now_iso = now_dt.isoformat()
    tracked_models = history.setdefault("models", {})
    current_model_ids = {m["id"]: m for m in current_free_models if "id" in m}

    # 1. Update existing models or add new ones
    for model_id, model_data in current_model_ids.items():
        endpoints = model_data.get("supported_endpoint_types", [])
        owned_by = model_data.get("owned_by", "unknown")
        created_ts = model_data.get("created", 0)

        if model_id not in tracked_models:
            # Newly discovered free model
            logger.info(f"🎉 New free model discovered: {model_id} (Owned by: {owned_by})")
            tracked_models[model_id] = {
                "id": model_id,
                "owned_by": owned_by,
                "created": created_ts,
                "supported_endpoint_types": endpoints,
                "first_seen": now_iso,
                "last_seen": now_iso,
                "is_active": True,
                "status_history": [
                    {
                        "status": "added",
                        "timestamp": now_iso,
                        "message": "First discovered"
                    }
                ],
                "last_change": {
                    "type": "added",
                    "timestamp": now_iso
                }
            }
        else:
            # Model already tracked
            entry = tracked_models[model_id]
            entry["last_seen"] = now_iso
            entry["owned_by"] = owned_by
            entry["supported_endpoint_types"] = endpoints
            if created_ts:
                entry["created"] = created_ts

            if not entry.get("is_active", True):
                # Model is back online
                logger.info(f"🔄 Free model back online: {model_id}")
                entry["is_active"] = True
                entry.setdefault("status_history", []).append({
                    "status": "recovered",
                    "timestamp": now_iso,
                    "message": "Model back online"
                })
                entry["last_change"] = {
                    "type": "recovered",
                    "timestamp": now_iso
                }

    # 2. Check for offline models
    for model_id, entry in tracked_models.items():
        if model_id not in current_model_ids and entry.get("is_active", True):
            logger.info(f"⚠️ Free model went offline: {model_id}")
            entry["is_active"] = False
            entry["last_offline"] = now_iso
            entry.setdefault("status_history", []).append({
                "status": "offline",
                "timestamp": now_iso,
                "message": "No longer present in DMXAPI free models list"
            })
            entry["last_change"] = {
                "type": "offline",
                "timestamp": now_iso
            }

    history["last_updated"] = now_iso
    return history


def save_history(history: Dict[str, Any]) -> None:
    """Save history to data/history.json."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved model history to {HISTORY_FILE}")


def generate_curl_example(model_id: str, endpoints: List[str], owned_by: str) -> str:
    """Generate realistic test cURL command according to supported endpoint types."""
    is_rerank = any("rerank" in ep.lower() for ep in endpoints) or "reranker" in model_id.lower()
    
    if is_rerank:
        return f"""curl https://www.dmxapi.cn/v1/rerank \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer $DMX_API_KEY" \\
  -d '{{
    "model": "{model_id}",
    "query": "What is artificial intelligence?",
    "documents": [
      "Artificial intelligence is intelligence demonstrated by machines.",
      "Organic food refers to food produced by methods complying with standards of organic farming."
    ]
  }}'"""
    else:
        return f"""curl https://www.dmxapi.cn/v1/chat/completions \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer $DMX_API_KEY" \\
  -d '{{
    "model": "{model_id}",
    "messages": [
      {{"role": "user", "content": "Hello, introduce yourself!"}}
    ]
  }}'"""


def generate_item_description_html(model: Dict[str, Any]) -> str:
    """Generate clean, rich semantic HTML description for RSS/Atom feed items."""
    model_id = model.get("id", "unknown")
    owned_by = model.get("owned_by", "unknown")
    endpoints = model.get("supported_endpoint_types", [])
    is_active = model.get("is_active", True)
    first_seen = model.get("first_seen", "N/A")
    last_seen = model.get("last_seen", "N/A")
    
    status_badge = "🟢 正常可用 (Active)" if is_active else "🔴 已下线 (Offline)"
    endpoints_str = ", ".join(endpoints) if endpoints else "openai"
    curl_cmd = generate_curl_example(model_id, endpoints, owned_by)

    return f"""<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6;">
  <p><strong>🎯 模型名称:</strong> <code>{saxutils.escape(model_id)}</code></p>
  <p><strong>⚡ 运行状态:</strong> {status_badge}</p>
  <p><strong>🏢 归属/厂商 (owned_by):</strong> <code>{saxutils.escape(owned_by)}</code></p>
  <p><strong>🔌 支持端点类型:</strong> <code>{saxutils.escape(endpoints_str)}</code></p>
  <p><strong>📅 首次发现时间:</strong> {saxutils.escape(first_seen)}</p>
  <p><strong>🕒 最后检测时间:</strong> {saxutils.escape(last_seen)}</p>
  <p><strong>🌐 基础接入地址:</strong> <code>https://www.dmxapi.cn/v1</code></p>
  
  <h4 style="margin-top: 16px; margin-bottom: 8px;">💻 快速调用测试 (cURL):</h4>
  <pre style="background: #1e293b; color: #f8fafc; padding: 12px; border-radius: 6px; overflow-x: auto; font-size: 13px;"><code>{saxutils.escape(curl_cmd)}</code></pre>
  
  <p style="margin-top: 14px; font-size: 13px; color: #64748b;">
    提示：在 DMXAPI 控制台获取 API Key 后，将 <code>$DMX_API_KEY</code> 替换为您自己的密钥即可免费调用。
  </p>
</div>"""


def build_rss_xml(models_list: List[Dict[str, Any]], now_dt: datetime) -> str:
    """Generate RSS 2.0 XML feed."""
    now_rfc822 = now_dt.strftime("%a, %d %b %Y %H:%M:%S +0000")
    
    items_xml = []
    for m in models_list:
        model_id = m.get("id", "unknown")
        owned_by = m.get("owned_by", "unknown")
        is_active = m.get("is_active", True)
        endpoints = m.get("supported_endpoint_types", [])
        
        status_icon = "🟢" if is_active else "🔴"
        status_text = "Free" if is_active else "Offline"
        title = f"{status_icon} [{owned_by}] {model_id} ({status_text})"
        link = SITE_URL
        guid = f"dmxapi-free-model-{model_id}"
        
        # Parse pubDate from first_seen or last_seen
        pub_dt = now_dt
        if m.get("last_seen"):
            try:
                pub_dt = date_parser.parse(m["last_seen"]).replace(tzinfo=timezone.utc)
            except Exception:
                pass
        pub_rfc822 = pub_dt.strftime("%a, %d %b %Y %H:%M:%S +0000")
        
        desc_html = generate_item_description_html(m)
        
        categories = ["Free AI Model", owned_by] + endpoints
        cats_xml = "\n".join(f"      <category>{saxutils.escape(c)}</category>" for c in categories if c)

        item = f"""    <item>
      <title>{saxutils.escape(title)}</title>
      <link>{saxutils.escape(link)}</link>
      <guid isPermaLink="false">{saxutils.escape(guid)}</guid>
      <pubDate>{pub_rfc822}</pubDate>
      <description>{saxutils.escape(desc_html)}</description>
{cats_xml}
    </item>"""
        items_xml.append(item)

    items_block = "\n".join(items_xml)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{saxutils.escape(FEED_TITLE)}</title>
    <link>{SITE_URL}</link>
    <description>{saxutils.escape(FEED_DESCRIPTION)}</description>
    <atom:link href="{FEED_URL_RSS}" rel="self" type="application/rss+xml"/>
    <language>zh-CN</language>
    <lastBuildDate>{now_rfc822}</lastBuildDate>
{items_block}
  </channel>
</rss>
"""


def build_atom_xml(models_list: List[Dict[str, Any]], now_dt: datetime) -> str:
    """Generate Atom 1.0 XML feed."""
    now_iso = now_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    entries_xml = []
    for m in models_list:
        model_id = m.get("id", "unknown")
        owned_by = m.get("owned_by", "unknown")
        is_active = m.get("is_active", True)
        
        status_icon = "🟢" if is_active else "🔴"
        status_text = "Free" if is_active else "Offline"
        title = f"{status_icon} [{owned_by}] {model_id} ({status_text})"
        entry_id = f"urn:dmxapi:model:{model_id}"
        
        updated_iso = now_iso
        if m.get("last_seen"):
            try:
                updated_iso = date_parser.parse(m["last_seen"]).strftime("%Y-%m-%dT%H:%M:%SZ")
            except Exception:
                pass
                
        published_iso = updated_iso
        if m.get("first_seen"):
            try:
                published_iso = date_parser.parse(m["first_seen"]).strftime("%Y-%m-%dT%H:%M:%SZ")
            except Exception:
                pass

        desc_html = generate_item_description_html(m)
        summary = f"DMXAPI Free Model: {model_id} (Owned by {owned_by}). Status: {'Active' if is_active else 'Offline'}."

        entry = f"""  <entry>
    <id>{saxutils.escape(entry_id)}</id>
    <title>{saxutils.escape(title)}</title>
    <link href="{SITE_URL}" rel="alternate"/>
    <updated>{updated_iso}</updated>
    <published>{published_iso}</published>
    <summary>{saxutils.escape(summary)}</summary>
    <content type="html">{saxutils.escape(desc_html)}</content>
    <author>
      <name>DMXAPI</name>
      <uri>{SITE_URL}</uri>
    </author>
  </entry>"""
        entries_xml.append(entry)

    entries_block = "\n".join(entries_xml)
    return f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>{saxutils.escape(FEED_TITLE)}</title>
  <subtitle>{saxutils.escape(FEED_DESCRIPTION)}</subtitle>
  <link href="{FEED_URL_ATOM}" rel="self"/>
  <link href="{SITE_URL}"/>
  <id>urn:dmxapi:free-models:feed</id>
  <updated>{now_iso}</updated>
  <author>
    <name>DMXAPI Free Models Bot</name>
    <uri>{SITE_URL}</uri>
  </author>
{entries_block}
</feed>
"""


def build_models_json(history: Dict[str, Any], now_dt: datetime) -> str:
    """Generate structured JSON payload for frontend or API consumers."""
    all_models = list(history.get("models", {}).values())
    active_models = [m for m in all_models if m.get("is_active", True)]
    
    # Enrich with curl examples
    enriched_active = []
    for m in active_models:
        item = dict(m)
        item["curl_example"] = generate_curl_example(
            m["id"],
            m.get("supported_endpoint_types", []),
            m.get("owned_by", "")
        )
        enriched_active.append(item)

    payload = {
        "generated_at": now_dt.isoformat(),
        "api_base": "https://www.dmxapi.cn/v1",
        "official_url": SITE_URL,
        "stats": {
            "active_free_models": len(active_models),
            "total_discovered": len(all_models),
            "offline_models": len(all_models) - len(active_models)
        },
        "active_models": enriched_active,
        "history": history.get("models", {})
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>DMXAPI 免费模型监控与 RSS 订阅 | DMXAPI Free Models</title>
  <meta name="description" content="实时监控 DMXAPI 平台所有免费 AI 模型，提供 RSS/Atom 订阅源及一键调用测试代码。">
  <link rel="alternate" type="application/rss+xml" title="DMXAPI Free Models RSS Feed" href="rss.xml">
  <link rel="alternate" type="application/atom+xml" title="DMXAPI Free Models Atom Feed" href="atom.xml">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-primary: #0a0f1d;
      --bg-secondary: #111827;
      --bg-card: rgba(17, 24, 39, 0.75);
      --bg-card-hover: rgba(30, 41, 59, 0.85);
      --border-color: rgba(255, 255, 255, 0.08);
      --border-focus: rgba(59, 130, 246, 0.5);
      --primary: #3b82f6;
      --primary-hover: #2563eb;
      --accent-emerald: #10b981;
      --accent-amber: #f59e0b;
      --accent-rose: #f43f5e;
      --accent-cyan: #06b6d4;
      --accent-purple: #8b5cf6;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --text-dim: #64748b;
      --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      --font-mono: 'Fira Code', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      font-family: var(--font-sans);
      background-color: var(--bg-primary);
      background-image: 
        radial-gradient(at 0% 0%, rgba(59, 130, 246, 0.12) 0px, transparent 50%),
        radial-gradient(at 100% 0%, rgba(16, 185, 129, 0.1) 0px, transparent 50%),
        radial-gradient(at 50% 100%, rgba(139, 92, 246, 0.08) 0px, transparent 50%);
      background-attachment: fixed;
      color: var(--text-main);
      line-height: 1.6;
      padding: 40px 20px;
      min-height: 100vh;
    }

    .container {
      max-width: 1100px;
      margin: 0 auto;
    }

    /* Header */
    header {
      text-align: center;
      margin-bottom: 36px;
    }

    .badge-pill {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 12px;
      background: rgba(16, 185, 129, 0.15);
      border: 1px solid rgba(16, 185, 129, 0.3);
      color: #34d399;
      font-size: 0.8rem;
      font-weight: 700;
      border-radius: 9999px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 12px;
    }

    .live-dot {
      width: 8px;
      height: 8px;
      background-color: #10b981;
      border-radius: 50%;
      box-shadow: 0 0 10px #10b981;
      animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.4; transform: scale(1.2); }
    }

    h1 {
      font-size: 2.6rem;
      font-weight: 800;
      letter-spacing: -0.02em;
      background: linear-gradient(135deg, #ffffff 30%, #94a3b8 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      margin-bottom: 12px;
    }

    p.subtitle {
      color: var(--text-muted);
      font-size: 1.1rem;
      max-width: 650px;
      margin: 0 auto 28px;
    }

    /* Action Buttons */
    .button-group {
      display: flex;
      justify-content: center;
      gap: 12px;
      flex-wrap: wrap;
      margin-bottom: 32px;
    }

    .btn {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 10px 18px;
      border-radius: 10px;
      font-weight: 600;
      font-size: 0.9rem;
      text-decoration: none;
      transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
      cursor: pointer;
      border: 1px solid transparent;
    }

    .btn-rss {
      background: linear-gradient(135deg, #f97316, #ea580c);
      color: #ffffff;
      box-shadow: 0 4px 14px rgba(249, 115, 22, 0.25);
    }
    .btn-rss:hover {
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(249, 115, 22, 0.35);
    }

    .btn-atom {
      background: linear-gradient(135deg, #3b82f6, #2563eb);
      color: #ffffff;
      box-shadow: 0 4px 14px rgba(59, 130, 246, 0.25);
    }
    .btn-atom:hover {
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(59, 130, 246, 0.35);
    }

    .btn-json {
      background: rgba(255, 255, 255, 0.06);
      color: var(--text-main);
      border: 1px solid var(--border-color);
      backdrop-filter: blur(8px);
    }
    .btn-json:hover {
      background: rgba(255, 255, 255, 0.12);
      border-color: rgba(255, 255, 255, 0.2);
      transform: translateY(-2px);
    }

    .btn-portal {
      background: linear-gradient(135deg, #10b981, #059669);
      color: #ffffff;
      box-shadow: 0 4px 14px rgba(16, 185, 129, 0.25);
    }
    .btn-portal:hover {
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(16, 185, 129, 0.35);
    }

    /* Stats Grid */
    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
      margin-bottom: 32px;
    }

    .stat-card {
      background: var(--bg-card);
      backdrop-filter: blur(12px);
      border: 1px solid var(--border-color);
      border-radius: 14px;
      padding: 18px 22px;
      display: flex;
      flex-direction: column;
      gap: 6px;
      position: relative;
      overflow: hidden;
    }

    .stat-card::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 2px;
      background: linear-gradient(90deg, transparent, var(--stat-accent, var(--primary)), transparent);
    }

    .stat-label {
      font-size: 0.85rem;
      color: var(--text-muted);
      font-weight: 500;
    }

    .stat-value {
      font-size: 1.8rem;
      font-weight: 800;
      color: #ffffff;
    }

    /* Search & Filter Bar */
    .filter-bar {
      background: var(--bg-card);
      backdrop-filter: blur(12px);
      border: 1px solid var(--border-color);
      border-radius: 14px;
      padding: 16px 20px;
      margin-bottom: 24px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }

    .search-box {
      position: relative;
      width: 100%;
    }

    .search-input {
      width: 100%;
      background: rgba(15, 23, 42, 0.7);
      border: 1px solid var(--border-color);
      border-radius: 10px;
      padding: 12px 16px 12px 42px;
      color: #ffffff;
      font-size: 0.95rem;
      font-family: inherit;
      outline: none;
      transition: all 0.2s ease;
    }

    .search-input:focus {
      border-color: var(--primary);
      box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
    }

    .search-icon {
      position: absolute;
      left: 14px;
      top: 50%;
      transform: translateY(-50%);
      color: var(--text-dim);
      font-size: 1.1rem;
      pointer-events: none;
    }

    .tags-filter {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }

    .filter-pill {
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--border-color);
      color: var(--text-muted);
      padding: 6px 14px;
      border-radius: 9999px;
      font-size: 0.85rem;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .filter-pill:hover {
      background: rgba(255, 255, 255, 0.1);
      color: #ffffff;
    }

    .filter-pill.active {
      background: var(--primary);
      border-color: var(--primary);
      color: #ffffff;
      font-weight: 600;
    }

    /* Models Cards List */
    .models-list {
      display: flex;
      flex-direction: column;
      gap: 18px;
    }

    .model-card {
      background: var(--bg-card);
      backdrop-filter: blur(12px);
      border: 1px solid var(--border-color);
      border-radius: 16px;
      padding: 22px;
      transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
      position: relative;
    }

    .model-card:hover {
      background: var(--bg-card-hover);
      border-color: rgba(255, 255, 255, 0.15);
      transform: translateY(-2px);
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25);
    }

    .model-card-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 16px;
      margin-bottom: 14px;
      flex-wrap: wrap;
    }

    .model-title-group {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }

    .model-name {
      font-family: var(--font-mono);
      font-size: 1.25rem;
      font-weight: 600;
      color: #ffffff;
      letter-spacing: -0.01em;
    }

    .copy-btn {
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid var(--border-color);
      color: var(--text-muted);
      padding: 4px 8px;
      border-radius: 6px;
      font-size: 0.75rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s ease;
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }

    .copy-btn:hover {
      background: rgba(255, 255, 255, 0.15);
      color: #ffffff;
    }

    .status-badge {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 0.75rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }

    .status-active {
      background: rgba(16, 185, 129, 0.15);
      color: #34d399;
      border: 1px solid rgba(16, 185, 129, 0.3);
    }

    .status-offline {
      background: rgba(244, 63, 94, 0.15);
      color: #fb7185;
      border: 1px solid rgba(244, 63, 94, 0.3);
    }

    .model-badges-row {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      margin-bottom: 16px;
    }

    .badge-vendor {
      background: rgba(59, 130, 246, 0.15);
      color: #60a5fa;
      border: 1px solid rgba(59, 130, 246, 0.3);
      padding: 3px 10px;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 600;
    }

    .badge-endpoint {
      background: rgba(139, 92, 246, 0.15);
      color: #a78bfa;
      border: 1px solid rgba(139, 92, 246, 0.3);
      padding: 3px 10px;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 600;
    }

    .meta-timestamps {
      display: flex;
      gap: 20px;
      font-size: 0.82rem;
      color: var(--text-dim);
      margin-bottom: 16px;
      flex-wrap: wrap;
    }

    .meta-timestamps span strong {
      color: var(--text-muted);
    }

    /* Curl Code Block */
    .curl-container {
      background: rgba(15, 23, 42, 0.85);
      border: 1px solid rgba(255, 255, 255, 0.06);
      border-radius: 10px;
      overflow: hidden;
    }

    .curl-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 14px;
      background: rgba(30, 41, 59, 0.5);
      border-bottom: 1px solid rgba(255, 255, 255, 0.04);
      font-size: 0.75rem;
      color: var(--text-dim);
      font-family: var(--font-mono);
    }

    .curl-code {
      padding: 12px 14px;
      font-family: var(--font-mono);
      font-size: 0.82rem;
      color: #e2e8f0;
      overflow-x: auto;
      white-space: pre;
      line-height: 1.5;
    }

    /* Integration Quick Guide */
    .guide-card {
      background: var(--bg-card);
      backdrop-filter: blur(12px);
      border: 1px solid var(--border-color);
      border-radius: 16px;
      padding: 24px;
      margin-top: 40px;
    }

    .guide-card h3 {
      font-size: 1.2rem;
      margin-bottom: 14px;
      color: #ffffff;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    /* Toast Notification */
    .toast {
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: #10b981;
      color: #ffffff;
      padding: 10px 18px;
      border-radius: 8px;
      font-size: 0.85rem;
      font-weight: 600;
      box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
      opacity: 0;
      transform: translateY(20px);
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      pointer-events: none;
      z-index: 1000;
    }

    .toast.show {
      opacity: 1;
      transform: translateY(0);
    }

    /* Footer */
    footer {
      text-align: center;
      margin-top: 50px;
      padding-top: 24px;
      border-top: 1px solid var(--border-color);
      color: var(--text-dim);
      font-size: 0.85rem;
    }

    footer a {
      color: var(--primary);
      text-decoration: none;
    }
    footer a:hover {
      text-decoration: underline;
    }

    @media (max-width: 640px) {
      h1 { font-size: 2rem; }
      .stat-value { font-size: 1.5rem; }
      .model-card { padding: 16px; }
      .button-group { flex-direction: column; }
      .btn { width: 100%; justify-content: center; }
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="badge-pill">
        <div class="live-dot"></div>
        <span>Live Tracker &bull; 100% Free</span>
      </div>
      <h1>DMXAPI 免费模型动态</h1>
      <p class="subtitle">实时抓取、历史追踪与 RSS/Atom 订阅，助你零成本接入大模型能力</p>
      
      <div class="button-group">
        <a href="rss.xml" class="btn btn-rss" target="_blank">📡 RSS 2.0 订阅</a>
        <a href="atom.xml" class="btn btn-atom" target="_blank">⚛️ Atom 1.0 订阅</a>
        <a href="models.json" class="btn btn-json" target="_blank">📋 JSON 数据源</a>
        <a href="https://www.dmxapi.cn" class="btn btn-portal" target="_blank" rel="noopener noreferrer">🌐 DMXAPI 官方控制台</a>
      </div>
    </header>

    <!-- Stats Summary -->
    <div class="stats-grid">
      <div class="stat-card" style="--stat-accent: #10b981;">
        <span class="stat-label">🟢 当前在线免费模型</span>
        <span class="stat-value" id="stat-active">__ACTIVE_COUNT__</span>
      </div>
      <div class="stat-card" style="--stat-accent: #3b82f6;">
        <span class="stat-label">📦 历史累计发现</span>
        <span class="stat-value" id="stat-total">__TOTAL_COUNT__</span>
      </div>
      <div class="stat-card" style="--stat-accent: #8b5cf6;">
        <span class="stat-label">🔌 基础接口地址</span>
        <span class="stat-value" style="font-size: 1.1rem; font-family: var(--font-mono); margin-top: 6px;">https://www.dmxapi.cn/v1</span>
      </div>
      <div class="stat-card" style="--stat-accent: #f59e0b;">
        <span class="stat-label">🕒 最近检测更新</span>
        <span class="stat-value" style="font-size: 0.95rem; margin-top: 8px;">__NOW_STR_UTC__</span>
      </div>
    </div>

    <!-- Search & Filter Controls -->
    <div class="filter-bar">
      <div class="search-box">
        <span class="search-icon">🔍</span>
        <input type="text" id="searchInput" class="search-input" placeholder="搜索模型名称、厂商、端点类型 (例如: qwen, rerank, claude)..." />
      </div>
      <div class="tags-filter">
        <span style="font-size:0.85rem;color:var(--text-muted);margin-right:4px;">快捷筛选:</span>
        <button class="filter-pill active" onclick="setFilter('all', this)">全部 (__TOTAL_COUNT__)</button>
        <button class="filter-pill" onclick="setFilter('active', this)">🟢 仅在线 (__ACTIVE_COUNT__)</button>
        <button class="filter-pill" onclick="setFilter('openai', this)">OpenAI 兼容</button>
        <button class="filter-pill" onclick="setFilter('rerank', this)">Reranker 重排</button>
      </div>
    </div>

    <!-- Models List Container -->
    <div id="modelsContainer" class="models-list">
      <!-- Dynamically rendered by JS -->
    </div>

    <!-- Quick Guide Card -->
    <div class="guide-card">
      <h3>🚀 快速接入指南</h3>
      <p style="color:var(--text-muted);font-size:0.9rem;margin-bottom:14px;">
        DMXAPI 兼容 OpenAI 与 Anthropic 官方 SDK。设置自定义 Base URL 即可无缝切换：
      </p>
      <div class="curl-container">
        <div class="curl-header">
          <span>Python OpenAI SDK 示例</span>
          <button class="copy-btn" onclick="copySnippet(this, `from openai import OpenAI\\n\\nclient = OpenAI(\\n    base_url='https://www.dmxapi.cn/v1',\\n    api_key='YOUR_DMX_API_KEY'\\n)\\n\\nresponse = client.chat.completions.create(\\n    model='spark-lite-free',\\n    messages=[{'role': 'user', 'content': '你好！'}]\\n)\\nprint(response.choices[0].message.content)`)">复制代码</button>
        </div>
        <pre class="curl-code">from openai import OpenAI

client = OpenAI(
    base_url="https://www.dmxapi.cn/v1",
    api_key="YOUR_DMX_API_KEY"
)

response = client.chat.completions.create(
    model="spark-lite-free",
    messages=[{"role": "user", "content": "你好！"}]
)
print(response.choices[0].message.content)</pre>
      </div>
    </div>

    <footer>
      <p>DMXAPI Free Models RSS Feed &bull; 自动定时检测更新 &bull; 访问 <a href="https://www.dmxapi.cn" target="_blank" rel="noopener noreferrer">DMXAPI 官网</a> 获取更多模型</p>
    </footer>
  </div>

  <div id="toast" class="toast">已复制到剪贴板! ✓</div>

  <script>
    const modelsData = __MODELS_DATA__;
    let currentFilter = 'all';
    let searchQuery = '';

    function showToast(msg = '已复制到剪贴板! ✓') {
      const toast = document.getElementById('toast');
      toast.innerText = msg;
      toast.classList.add('show');
      setTimeout(() => {
        toast.classList.remove('show');
      }, 2000);
    }

    function copySnippet(btn, text) {
      navigator.clipboard.writeText(text).then(() => {
        showToast('已复制到剪贴板! ✓');
        const origText = btn.innerText;
        btn.innerText = '已复制! ✓';
        setTimeout(() => { btn.innerText = origText; }, 1500);
      }).catch(err => {
        console.error('Copy failed:', err);
      });
    }

    function setFilter(filterType, btn) {
      currentFilter = filterType;
      document.querySelectorAll('.filter-pill').forEach(el => el.classList.remove('active'));
      if (btn) btn.classList.add('active');
      renderModels();
    }

    document.getElementById('searchInput').addEventListener('input', (e) => {
      searchQuery = e.target.value.toLowerCase().trim();
      renderModels();
    });

    function escapeHtml(str) {
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
    }

    function renderModels() {
      const container = document.getElementById('modelsContainer');
      const filtered = modelsData.filter(m => {
        // Filter by tab
        if (currentFilter === 'active' && !m.is_active) return false;
        if (currentFilter === 'openai' && !m.endpoints.some(e => e.includes('openai'))) return false;
        if (currentFilter === 'rerank' && !m.endpoints.some(e => e.includes('rerank')) && !m.id.toLowerCase().includes('rerank')) return false;

        // Filter by search query
        if (searchQuery) {
          const matchId = m.id.toLowerCase().includes(searchQuery);
          const matchOwner = m.owned_by.toLowerCase().includes(searchQuery);
          const matchEp = m.endpoints.some(e => e.toLowerCase().includes(searchQuery));
          if (!matchId && !matchOwner && !matchEp) return false;
        }
        return true;
      });

      if (filtered.length === 0) {
        container.innerHTML = `
          <div style="text-align:center;padding:40px;color:var(--text-dim);background:var(--bg-card);border-radius:14px;border:1px solid var(--border-color);">
            <p style="font-size:1.1rem;margin-bottom:8px;">未找到匹配的模型</p>
            <p style="font-size:0.85rem;">请尝试清除筛选条件或更换搜索关键词</p>
          </div>
        `;
        return;
      }

      container.innerHTML = filtered.map(m => {
        const statusHtml = m.is_active
          ? `<span class="status-badge status-active">🟢 在线可用</span>`
          : `<span class="status-badge status-offline">🔴 已下线</span>`;

        const vendorHtml = `<span class="badge-vendor">🏢 ${escapeHtml(m.owned_by)}</span>`;
        const endpointsHtml = m.endpoints.map(ep => `<span class="badge-endpoint">⚡ ${escapeHtml(ep)}</span>`).join(' ');

        return `
          <div class="model-card">
            <div class="model-card-header">
              <div class="model-title-group">
                <span class="model-name">${escapeHtml(m.id)}</span>
                <button class="copy-btn" onclick="copySnippet(this, '${escapeHtml(m.id)}')">复制模型名</button>
              </div>
              <div>${statusHtml}</div>
            </div>
            
            <div class="model-badges-row">
              ${vendorHtml}
              ${endpointsHtml}
            </div>

            <div class="meta-timestamps">
              <span>📅 首次发现: <strong>${escapeHtml(m.first_seen || 'N/A')}</strong></span>
              <span>🕒 最近活跃: <strong>${escapeHtml(m.last_seen || 'N/A')}</strong></span>
            </div>

            <div class="curl-container">
              <div class="curl-header">
                <span>cURL 快速调用测试</span>
                <button class="copy-btn" onclick="copySnippet(this, decodeURIComponent('${encodeURIComponent(m.curl)}'))">复制 cURL</button>
              </div>
              <pre class="curl-code">${escapeHtml(m.curl)}</pre>
            </div>
          </div>
        `;
      }).join('');
    }

    // Initial render
    renderModels();
  </script>
</body>
</html>
"""


def build_index_html(history: Dict[str, Any], now_dt: datetime) -> str:
    """Generate a modern, responsive, glassmorphic dark-mode web page."""
    all_models = list(history.get("models", {}).values())
    
    # Sort active first, then by last_seen descending
    def sort_key(m):
        return (1 if m.get("is_active", True) else 0, m.get("last_seen", ""))
    
    sorted_models = sorted(all_models, key=sort_key, reverse=True)
    active_count = sum(1 for m in all_models if m.get("is_active", True))
    total_count = len(all_models)
    now_str_utc = now_dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    
    # Pre-generate JSON string for client-side search/filter
    models_json_embedded = json.dumps([
        {
            "id": m.get("id", ""),
            "owned_by": m.get("owned_by", "unknown"),
            "endpoints": m.get("supported_endpoint_types", []),
            "is_active": m.get("is_active", True),
            "first_seen": m.get("first_seen", ""),
            "last_seen": m.get("last_seen", ""),
            "curl": generate_curl_example(m.get("id", ""), m.get("supported_endpoint_types", []), m.get("owned_by", ""))
        }
        for m in sorted_models
    ], ensure_ascii=False)

    html = HTML_TEMPLATE
    html = html.replace("__ACTIVE_COUNT__", str(active_count))
    html = html.replace("__TOTAL_COUNT__", str(total_count))
    html = html.replace("__NOW_STR_UTC__", now_str_utc)
    html = html.replace("__MODELS_DATA__", models_json_embedded)
    return html


def main():
    """Main execution entry point."""
    logger.info("=== Starting DMXAPI Free Models RSS Feed Generator ===")
    
    # 1. Prepare directories
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(DIST_DIR, exist_ok=True)
    
    now_dt = datetime.now(timezone.utc)
    
    # 2. Fetch models from API
    api_key = get_api_key()
    try:
        raw_models = fetch_models(api_key)
    except Exception as e:
        logger.exception(f"Failed to fetch models from DMXAPI: {e}")
        sys.exit(1)
        
    # 3. Filter free models ending with 'free'
    current_free_models = filter_free_models(raw_models)
    
    # 4. Load & update history
    history = load_history()
    history = update_history(current_free_models, history, now_dt)
    save_history(history)
    
    # 5. Prepare model list for feed generation
    all_tracked = list(history.get("models", {}).values())
    
    # 6. Generate feeds & files in dist/
    rss_content = build_rss_xml(all_tracked, now_dt)
    rss_path = os.path.join(DIST_DIR, "rss.xml")
    with open(rss_path, "w", encoding="utf-8") as f:
        f.write(rss_content)
    logger.info(f"Generated RSS 2.0 feed: {rss_path} ({os.path.getsize(rss_path)} bytes)")
    
    atom_content = build_atom_xml(all_tracked, now_dt)
    atom_path = os.path.join(DIST_DIR, "atom.xml")
    with open(atom_path, "w", encoding="utf-8") as f:
        f.write(atom_content)
    logger.info(f"Generated Atom 1.0 feed: {atom_path} ({os.path.getsize(atom_path)} bytes)")
    
    models_json_content = build_models_json(history, now_dt)
    models_json_path = os.path.join(DIST_DIR, "models.json")
    with open(models_json_path, "w", encoding="utf-8") as f:
        f.write(models_json_content)
    logger.info(f"Generated JSON data: {models_json_path} ({os.path.getsize(models_json_path)} bytes)")
    
    index_html_content = build_index_html(history, now_dt)
    index_html_path = os.path.join(DIST_DIR, "index.html")
    with open(index_html_path, "w", encoding="utf-8") as f:
        f.write(index_html_content)
    logger.info(f"Generated Landing Page: {index_html_path} ({os.path.getsize(index_html_path)} bytes)")
    
    logger.info("=== DMXAPI Free Models Generation Finished Successfully! ===")


if __name__ == "__main__":
    main()
