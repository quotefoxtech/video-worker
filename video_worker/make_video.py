#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-command AI video generator.

    python make_video.py                 # asks for a topic
    python make_video.py --topic "..."   # non-interactive

Pipeline: topic -> LLM script JSON (Gemini, fallback OpenRouter)
       -> Camb.ai voiceovers -> free AI images (RedPanda/Raphael/Cloudflare)
       -> Remotion render -> topics/<slug>/video.mp4

Every step is cached -- re-running skips audio/images that already exist.
Keys are read from .env next to this file, falling back to D:/perspective-api/.env
"""

import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import concurrent.futures
import hashlib
import json
import math
import re
import shutil
import subprocess
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
PERSPECTIVE_ENV = Path("D:/perspective-api/.env")

# -- env ----------------------------------------------------------------------


def load_env() -> dict:
    env = {}

    def parse(path: Path) -> None:
        if not path.exists():
            return
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env.setdefault(k.strip(), v.strip().strip('"').strip("'"))

    parse(ROOT / ".env")
    parse(PERSPECTIVE_ENV)  # fallback: existing keys live there
    return env


ENV = load_env()


def first_env(*names: str, default: str = "") -> str:
    for n in names:
        if ENV.get(n):
            return ENV[n]
    return default


def env_keys(prefix: str) -> list[str]:
    keys = []
    for i in range(1, 10):
        v = ENV.get(f"{prefix}_{i}")
        if v:
            keys.append(v)
    return keys


# -- helpers ------------------------------------------------------------------

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36"
)


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:60] or "video"


def banner(msg: str) -> None:
    print(f"\n======== {msg} ========")


# -- 1. LLM script generation -------------------------------------------------

ANIMATIONS = [
    "slideUp",
    "wordPop",
    "typewriter",
    "letterDrop",
    "highlight",
    "blurIn",
    "glowReveal",
    "gradientWave",
]
SCENE_TYPES = [
    "title",
    "bullets",
    "imageGrid",
    "flow",
    "chart",
    "timeline",
    "checklist",
    "stat",
    "quote",
    "comparison",
    "bento",
    "splitHero",
    "outro",
]

BEST_ANIMATION_FOR_SCENE = {
    "title": "wordPop",
    "flow": "letterDrop",
    "comparison": "highlight",
    "bento": "blurIn",
    "bullets": "slideUp",
    "stat": "wordPop",
    "chart": "blurIn",
    "timeline": "letterDrop",
    "checklist": "slideUp",
    "quote": "typewriter",
    "imageGrid": "blurIn",
    "splitHero": "slideUp",
    "outro": "glowReveal",
}


def get_topic_palette(topic: str) -> dict:
    """Returns a sophisticated, non-neon dark palette tailored to the topic domain."""
    t = topic.lower()

    # Marketing / SEO / Growth / Sales / Social
    if any(k in t for k in ["seo", "marketing", "growth", "traffic", "rank", "sale", "ad", "content", "brand", "social"]):
        return {
            "bgFrom": "#140c06",
            "bgTo": "#090502",
            "accent": "#f97316",
            "textColor": "#ffffff",
            "mutedColor": "#94a3b8",
        }
    # Finance / Money / Crypto / Stocks / Investment
    if any(k in t for k in ["finance", "money", "invest", "stock", "crypto", "bitcoin", "wealth", "trading", "profit", "revenue"]):
        return {
            "bgFrom": "#06130e",
            "bgTo": "#020906",
            "accent": "#10b981",
            "textColor": "#ffffff",
            "mutedColor": "#94a3b8",
        }
    # Health / Sleep / Brain / Fitness / Neuroscience / Medicine
    if any(k in t for k in ["health", "sleep", "brain", "neuro", "fitness", "diet", "bio", "doctor", "medical", "wellness", "habit"]):
        return {
            "bgFrom": "#0d0c18",
            "bgTo": "#05050c",
            "accent": "#818cf8",
            "textColor": "#ffffff",
            "mutedColor": "#94a3b8",
        }
    # Engineering / Tech / AI / Architecture / Code / Cloud
    if any(k in t for k in ["code", "tech", "software", "ai", "engineer", "cloud", "devops", "cyber", "python", "data", "system", "llm"]):
        return {
            "bgFrom": "#060e18",
            "bgTo": "#02060c",
            "accent": "#38bdf8",
            "textColor": "#ffffff",
            "mutedColor": "#94a3b8",
        }
    # Business / Management / Strategy / Leadership
    if any(k in t for k in ["business", "leader", "manage", "startup", "strategy", "productiv", "work", "team"]):
        return {
            "bgFrom": "#120e06",
            "bgTo": "#080602",
            "accent": "#f59e0b",
            "textColor": "#ffffff",
            "mutedColor": "#94a3b8",
        }
    # Creative / Design / Art
    if any(k in t for k in ["design", "art", "creative", "ui", "ux", "photo", "film", "video", "music"]):
        return {
            "bgFrom": "#140812",
            "bgTo": "#080307",
            "accent": "#f43f5e",
            "textColor": "#ffffff",
            "mutedColor": "#94a3b8",
        }
    # Science / Physics / Energy / Nature
    if any(k in t for k in ["science", "physic", "energy", "solar", "nature", "space", "quantum", "climate"]):
        return {
            "bgFrom": "#061413",
            "bgTo": "#020807",
            "accent": "#14b8a6",
            "textColor": "#ffffff",
            "mutedColor": "#94a3b8",
        }
    # Default balanced deep charcoal slate with crisp cobalt blue
    return {
        "bgFrom": "#0b0f17",
        "bgTo": "#05070b",
        "accent": "#60a5fa",
        "textColor": "#ffffff",
        "mutedColor": "#94a3b8",
    }

GEMINI_STRICT_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "topic": {"type": "STRING"},
        "slug": {"type": "STRING"},
        "style": {
            "type": "OBJECT",
            "properties": {
                "bgFrom": {"type": "STRING", "description": "Dark gradient hex start (e.g. #061124)"},
                "bgTo": {"type": "STRING", "description": "Darker gradient hex end (e.g. #020610)"},
                "accent": {"type": "STRING", "description": "Vivid saturated hex accent (e.g. #00f0ff, #10b981, #f59e0b)"},
                "textColor": {"type": "STRING", "description": "Clean white hex (#ffffff)"},
                "mutedColor": {"type": "STRING", "description": "Muted slate hex (e.g. #94a3b8)"},
            },
            "required": ["bgFrom", "bgTo", "accent", "textColor", "mutedColor"],
        },
        "scenes": {
            "type": "ARRAY",
            "description": "6 to 8 chronological scenes for a ~55-70-second video.",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "id": {"type": "STRING"},
                    "type": {
                        "type": "STRING",
                        "enum": [
                            "title",
                            "bullets",
                            "imageGrid",
                            "flow",
                            "stat",
                            "quote",
                            "comparison",
                            "bento",
                            "splitHero",
                            "outro",
                        ],
                    },
                    "textAnimation": {
                        "type": "STRING",
                        "enum": [
                            "slideUp",
                            "wordPop",
                            "typewriter",
                            "letterDrop",
                            "highlight",
                            "blurIn",
                            "glowReveal",
                            "gradientWave",
                        ],
                    },
                    "narration": {
                        "type": "STRING",
                        "description": "Spoken voiceover of exactly 20-24 words (2 punchy sentences).",
                    },
                    "imagePrompts": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "badge": {"type": "STRING"},
                    "title": {"type": "STRING"},
                    "subtitle": {"type": "STRING"},
                    "cta": {"type": "STRING"},
                    "heading": {"type": "STRING"},
                    "bullets": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "captions": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "steps": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "title": {"type": "STRING"},
                                "detail": {"type": "STRING"},
                            },
                            "required": ["title", "detail"],
                        },
                    },
                    "data": {
                        "type": "ARRAY",
                        "description": "Three to five comparable numeric data points for a chart.",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "label": {"type": "STRING"},
                                "value": {"type": "NUMBER"},
                                "detail": {"type": "STRING"},
                            },
                            "required": ["label", "value"],
                        },
                    },
                    "timeline": {
                        "type": "ARRAY",
                        "description": "Three or four chronological milestones.",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "label": {"type": "STRING"},
                                "title": {"type": "STRING"},
                                "detail": {"type": "STRING"},
                            },
                            "required": ["label", "title", "detail"],
                        },
                    },
                    "items": {
                        "type": "ARRAY",
                        "description": "Three to five actionable checklist items.",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "title": {"type": "STRING"},
                                "detail": {"type": "STRING"},
                            },
                            "required": ["title", "detail"],
                        },
                    },
                    "value": {"type": "NUMBER"},
                    "suffix": {"type": "STRING"},
                    "label": {"type": "STRING"},
                    "quote": {"type": "STRING"},
                    "attribution": {"type": "STRING"},
                    "leftLabel": {"type": "STRING"},
                    "leftItems": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "rightLabel": {"type": "STRING"},
                    "rightItems": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "heroTitle": {"type": "STRING"},
                    "heroDetail": {"type": "STRING"},
                    "statValue": {"type": "STRING"},
                    "statLabel": {"type": "STRING"},
                    "featureTitle": {"type": "STRING"},
                    "featureDetail": {"type": "STRING"},
                },
                "required": ["id", "type", "textAnimation", "narration", "imagePrompts"],
            },
        },
    },
    "required": ["topic", "slug", "style", "scenes"],
}

LLM_PROMPT = """You are an elite motion graphics creative director and educational video scriptwriter.
Write an electrifying, high-retention ~60-second educational video script about: "{topic}"

TOPIC-TAILORED COLOR PALETTE:
Select a distinctive, sophisticated dark palette for "style" tailored to "{topic}".
NEVER use default electric cyan (#00f0ff). Choose domain-accurate, professional colors:
- Marketing / SEO / Growth / Sales: Coral/Orange accent ("#f97316"), deep dark slate ("bgFrom": "#140c06", "bgTo": "#090502")
- Finance / Money / Crypto / Investment: Emerald accent ("#10b981"), deep forest slate ("bgFrom": "#06130e", "bgTo": "#020906")
- Health / Sleep / Brain / Neuroscience: Indigo accent ("#818cf8"), deep night slate ("bgFrom": "#0d0c18", "bgTo": "#05050c")
- Engineering / Tech / Architecture / Code: Sky accent ("#38bdf8"), deep cobalt slate ("bgFrom": "#060e18", "bgTo": "#02060c")
- Business / Productivity / Strategy: Amber accent ("#f59e0b"), deep warm slate ("bgFrom": "#120e06", "bgTo": "#080602")
- Science / Physics / Energy: Teal accent ("#14b8a6"), deep obsidian ("bgFrom": "#061413", "bgTo": "#020807")
- Creative / Design / Arts: Crimson/Rose accent ("#f43f5e"), deep plum ("bgFrom": "#140812", "bgTo": "#080307")
Always set textColor: "#ffffff" and mutedColor: "#94a3b8".

DYNAMIC SCENE SELECTION & COMPOSITION:
Do NOT produce the exact same sequence for every video. Compose 6 to 8 scenes dynamically selected from the professional Remotion component palette to best teach "{topic}". Every scene must earn its place by advancing the explanation; never add decorative filler.
1. Scene 1 MUST ALWAYS be "title" (Epic visual hook).
2. The FINAL scene MUST ALWAYS be "outro" (Action-driving CTA).
3. The MIDDLE 4 to 6 scenes MUST be chosen from the palette based on "{topic}". Use 4 to 6 different scene types whenever the topic supports it, and do not repeat a scene type unless repetition is clearly pedagogically necessary.
    - "flow": Use when explaining a 3-step actionable framework, process roadmap, or phased methodology. (MANDATORY: steps must have 3 items, AND imagePrompts MUST have EXACTLY 3 DISTINCT image prompts - one for each step card!)
    - "chart": Use only when the topic has defensible comparable measurements, percentages, rankings, or trends. (MANDATORY: data must contain 3 to 5 objects with short label and numeric value; never invent a statistic just to fill this component; imagePrompts MUST be [])
    - "timeline": Use for a genuine chronology, evolution, history, or phased progression. (MANDATORY: timeline must contain 3 or 4 ordered objects with label, title, and detail; imagePrompts MUST be [])
    - "checklist": Use for a practical implementation checklist or repeatable operating routine. (MANDATORY: items must contain 3 to 5 objects with title and detail; imagePrompts MUST be [])
    - "comparison": Use when contrasting traditional/broken vs modern/optimal, problem vs solution, or two contrasting approaches. (MANDATORY: leftLabel, leftItems [3 strings], rightLabel, rightItems [3 strings], AND imagePrompts MUST have EXACTLY 2 DISTINCT image prompts - index 0 for left, index 1 for right!)
   - "bento": Use for modular architectural breakdowns or multi-faceted system overviews. (MANDATORY: heroTitle, heroDetail, statValue [e.g. "10x" or "99.9%"], statLabel, featureTitle, featureDetail, AND 1 hero imagePrompt)
   - "splitHero": Use for cinematic high-impact concept showcases. (MANDATORY: badge, title, subtitle, bullets [3 strings], AND 1 hero imagePrompt)
   - "imageGrid": Use for breaking down 3 foundational pillars or parallel domains. (MANDATORY: captions [3 strings], AND imagePrompts MUST have EXACTLY 3 DISTINCT image prompts - one per pillar)
   - "bullets": Use for core operational principles or mechanics. (MANDATORY: heading, bullets [3 strings], AND 1 tactile macro imagePrompt)
   - "stat": Use to prove a quantifiable breakthrough with hard empirical data. (MANDATORY: heading, value [number], suffix [e.g. "%" or "x"], label, AND 1 instrument imagePrompt)
   - "quote": Use for a provocative thought-leader insight or philosophical principle. (MANDATORY: quote, attribution, imagePrompts: [])

KINETIC TEXT ANIMATIONS MATCHED TO COMPONENTS:
Assign the most visually impactful kinetic animation for each scene based on its component layout:
- "title": "wordPop" or "glowReveal"
- "flow": "letterDrop" (crisp procedural step cadence)
- "comparison": "highlight" (spotlights key contrasting phrases)
- "bento": "blurIn" (cinematic modern interface focus)
- "bullets": "slideUp" (structured vertical rhythm)
- "stat": "wordPop" (high punch impact)
- "chart": "blurIn"
- "timeline": "letterDrop"
- "checklist": "slideUp"
- "quote": "typewriter" (monospaced editorial feel)
- "splitHero": "slideUp"
- "outro": "glowReveal" or "wordPop"
Vary the animation types across scenes (do not repeat the same animation consecutively).

TANGIBLE PHYSICAL METAPHOR PROMPTING (100% Free AI / Flux DiT):
- FORBIDDEN: Abstract glowing neon spheres, cyber-grids, wireframes in a black void, futuristic holograms.
- MANDATORY: Every image prompt must describe a REAL, TANGIBLE, PHYSICAL OBJECT with rich tactile materials (matte black anodized aluminum, polished walnut wood, brushed brass, frosted borosilicate glass, dark architectural slate) resting on a surface or pedestal under professional studio softbox three-point lighting.
- End every prompt with: "clean unprinted surfaces, blank matte finish".
- For "flow": Provide 3 distinct physical object prompts (one for step 1, one for step 2, one for step 3) so that EVERY step card has a stunning custom photo!
- For "comparison": Provide 2 distinct physical object prompts (one depicting the friction/traditional object, one depicting the modern optimized object).
- For "imageGrid": Provide 3 distinct physical object prompts (one per pillar).

SPOKEN NARRATION RULES:
- Target 18-24 words per scene (exactly 2 punchy, human, conversational sentences).
- Total narration across all scenes must be 145-170 words (~55-70 seconds speech).
- Do not make narration repeat the visible text word-for-word. The voiceover should explain the meaning while the graphics show the structure.

CRITICAL SCHEMA & CONTENT RULES:
- "value" is STRICTLY AND EXCLUSIVELY for "stat" scenes (where it must be an integer or rounded metric like 85, 92, 10) and "chart" data items. NEVER INCLUDE A "value" PROPERTY ON ANY OTHER SCENE TYPE! NEVER use random float decimals like 0.54.
- Every scene must contain all of its required fields filled with real, insightful, topic-specific copy. NEVER omit fields!
  - "flow": 3 steps with "title" and "detail", plus 3 distinct physical imagePrompts.
  - "comparison": "leftLabel", 3 specific "leftItems", "rightLabel", 3 specific "rightItems", plus 2 distinct physical imagePrompts.
  - "bento": "heroTitle", "heroDetail", "statValue", "statLabel", "featureTitle", "featureDetail", plus 1 hero physical imagePrompt.
  - "bullets": "heading", 3 specific "bullets", plus 1 tactile physical imagePrompt.
  - "stat": "heading", "value" (integer/number), "suffix" (e.g. "%"), "label", plus 1 instrument physical imagePrompt.
  - "splitHero": "badge", "title", "subtitle", 3 "bullets", plus 1 hero physical imagePrompt.
- Prefer short, scannable on-screen copy: title max 7 words, headings max 6 words, bullets/items max 8 words, details max 14 words.
- Keep the emotional arc: hook -> problem/context -> explanation -> proof/process -> takeaway -> CTA.

Return ONLY valid JSON (no markdown fences, no explanation) in this structure:
{{
  "topic": "{topic}",
  "slug": "slug-name",
  "style": {{
    "bgFrom": "#070b14",
    "bgTo": "#0e1626",
    "accent": "#00f0ff",
    "textColor": "#ffffff",
    "mutedColor": "#94a3b8"
  }},
  "scenes": [
    {{
      "id": "s1",
      "type": "title",
      "badge": "CATEGORY BRIEF (2-3 words uppercase)",
      "title": "Punchy Headline Max 7 Words",
      "subtitle": "Intriguing one-line hook explaining what the viewer will master",
      "textAnimation": "glowReveal",
      "narration": "Opening spoken sentence setting up the core problem. Second spoken sentence promising the solution.",
      "imagePrompts": [
        "Studio tabletop photograph of a tactile physical <hero subject> resting on polished dark walnut wood, warm directional key lighting, softbox illumination, clean unprinted surfaces, blank matte finish"
      ]
    }},
    {{
      "id": "s2",
      "type": "comparison",
      "heading": "The Strategic Shift",
      "leftLabel": "Traditional Approach",
      "leftItems": [
        "High friction manual coordination",
        "Slow disconnected feedback loops",
        "Error-prone repetitive bottlenecks"
      ],
      "rightLabel": "Optimized System",
      "rightItems": [
        "Streamlined automated pipeline",
        "Instant real-time telemetry",
        "Continuous 10x throughput scaling"
      ],
      "textAnimation": "highlight",
      "narration": "First sentence contrasting the old friction-heavy method. Second sentence introducing the massive leverage of modern execution.",
      "imagePrompts": [
        "Macro studio photograph of a tangled worn mechanical gear set resting on rough concrete, dim cool lighting, clean unprinted surfaces, blank matte finish",
        "Macro studio photograph of a precision engineered titanium mechanism on polished dark granite, warm studio softbox rim lighting, clean unprinted surfaces, blank matte finish"
      ]
    }},
    {{
      "id": "s3",
      "type": "bento",
      "heading": "Core System Architecture",
      "heroTitle": "Central Processing Engine",
      "heroDetail": "Engineered for high-throughput scalability and real-time state responsiveness.",
      "statValue": "10x",
      "statLabel": "Execution velocity multiplier",
      "featureTitle": "Telemetry Grid",
      "featureDetail": "Deep instrumentation tracks every micro-state change automatically.",
      "textAnimation": "blurIn",
      "narration": "First sentence explaining the central processing engine. Second sentence highlighting the automated telemetry and speed multiplier.",
      "imagePrompts": [
        "Studio photograph of a tactile physical modular server blade carved from matte black aluminum with subtle copper heatsink accents on dark walnut, studio softbox lighting, clean unprinted surfaces, blank matte finish"
      ]
    }},
    {{
      "id": "s4",
      "type": "flow",
      "heading": "3-Step Implementation Framework",
      "steps": [
        {{"title": "Map System Bounds", "detail": "Identify the foundational constraints and initial prerequisites."}},
        {{"title": "Deploy Pipeline", "detail": "Implement modular components and test real-time data flows."}},
        {{"title": "Scale Execution", "detail": "Optimize bottlenecks to sustain maximum reliable throughput."}}
      ],
      "textAnimation": "letterDrop",
      "narration": "First sentence guiding through the step-by-step roadmap. Second sentence emphasizing the key execution factor.",
      "imagePrompts": [
        "Tactile physical miniature blueprint cube resting on a dark slate circular pedestal, directional softbox lighting, clean unprinted surfaces, blank matte finish",
        "Tactile physical precision brass calipers and calibration block on dark slate circular pedestal, soft overhead lighting, clean unprinted surfaces, blank matte finish",
        "Tactile physical high-grade titanium turbine impeller on dark slate circular pedestal, warm rim lighting, clean unprinted surfaces, blank matte finish"
      ]
    }},
    {{
      "id": "s5",
      "type": "splitHero",
      "badge": "PARADIGM ADVANTAGE",
      "title": "Unrivaled Operational Precision",
      "subtitle": "Eliminating friction to achieve predictable real-world outcomes consistently.",
      "bullets": [
        "Deterministic workflow reliability",
        "Zero-latency state synchronization",
        "Auditable end-to-end telemetry"
      ],
      "textAnimation": "slideUp",
      "narration": "First sentence detailing how precision transforms daily operations. Second sentence highlighting the zero-latency synchronization.",
      "imagePrompts": [
        "Studio shot of an architectural monolith sculptured from obsidian and frosted glass resting on dark basalt stone, soft three-point studio light, clean unprinted surfaces, blank matte finish"
      ]
    }},
    {{
      "id": "s6",
      "type": "outro",
      "title": "Ready to Build the Future?",
      "subtitle": "Apply these proven principles to your workflow today",
      "cta": "Start Implementing Now",
      "textAnimation": "wordPop",
      "narration": "First sentence wrapping up the core transformation. Second sentence giving a clear, urgent directive to act immediately.",
      "imagePrompts": [
        "Sculptural milestone trophy carved from polished black obsidian and satin brass resting on an architectural plinth in a minimalist gallery, warm dramatic spotlight, clean lines, clean unprinted surfaces, blank matte finish"
      ]
    }}
  ]
}}
"""



def clean_flux_prompt(prompt: str) -> str:
    """Removes token-salad that ruins Flux DiT / T5-XXL attention,
    and replaces negative prompt traps with positive surface descriptions."""
    junk = [
        r"\boctane render\b",
        r"\bunreal engine 5\b",
        r"\bunreal engine\b",
        r"\b8k\b",
        r"\bvolumetric neon glow\b",
        r"\bsuspended in a void\b",
        r"\bvoid\b",
        r"\b16:9 widescreen\b",
        r"\b16:9\b",
        r"\bwidescreen\b",
    ]
    for j in junk:
        prompt = re.sub(j, "", prompt, flags=re.I)

    # Replace negative words that confuse T5-XXL with positive physical descriptors
    prompt = re.sub(
        r"\b(no text|no words|no letters|no watermark|no logo|no labels|without text)\b",
        "clean unprinted surfaces, blank matte finish",
        prompt,
        flags=re.I,
    )
    prompt = re.sub(r"\s+", " ", prompt).strip(" ,")
    return prompt


def call_gemini_text(prompt: str) -> str:
    keys = [k for k in [first_env("GEMINI_API_KEY")] if k] or env_keys("GEMINI_KEY")
    model = first_env("GEMINI_MODEL", default="gemini-2.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    for key in keys:
        try:
            r = requests.post(
                url,
                params={"key": key},
                json={
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.7,
                        "maxOutputTokens": 6000,
                        "responseMimeType": "application/json",
                        },
                },
                timeout=120,
            )
            if r.status_code == 200:
                return r.json()["candidates"][0]["content"]["parts"][0]["text"]
            print(f"  gemini key ...{key[-4:]} failed: {r.status_code} {r.text[:120]}")
        except Exception as e:
            print(f"  gemini key error: {e}")
    raise RuntimeError("all Gemini keys failed")


def call_openrouter_text(prompt: str) -> str:
    keys = [k for k in [first_env("OPENROUTER_API_KEY")] if k] or env_keys("OPENROUTER_KEY")
    model = first_env(
        "OPENROUTER_MODEL", default="qwen/qwen3-next-80b-a3b-instruct:free"
    )
    for key in keys:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": model,
                "temperature": 0.7,
                "max_tokens": 6000,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=180,
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        print(f"  openrouter key ...{key[-4:]} failed: {r.status_code} {r.text[:120]}")
    raise RuntimeError("all OpenRouter keys failed")


def llm_json(prompt: str) -> str:
    """Gemini first, OpenRouter fallback -- returns raw JSON text."""
    try:
        return call_gemini_text(prompt)
    except Exception as e:
        print(f"  gemini failed ({str(e)[:120]}); trying openrouter")
        return call_openrouter_text(prompt)


def call_gemini(topic: str) -> str:
    return llm_json(LLM_PROMPT.format(topic=topic, animations=ANIMATIONS))


def parse_json_loose(text: str) -> dict:
    text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"no JSON object in LLM output:\n{text[:300]}")
    return json.loads(text[start : end + 1])


def validate_script(data: dict, topic: str) -> dict:
    if not isinstance(data, dict):
        raise ValueError("script.json must contain a JSON object")
    if not isinstance(data.get("scenes"), list) or len(data["scenes"]) < 4:
        raise ValueError("script.json needs at least 4 scenes")
    for index, scene in enumerate(data["scenes"]):
        if not isinstance(scene, dict):
            data["scenes"][index] = {}
    data["scenes"][0]["type"] = "title"
    data["scenes"][-1]["type"] = "outro"
    clean_topic = (data.get("topic") or topic).strip()
    topic_palette = get_topic_palette(clean_topic)

    style = data.setdefault("style", {})
    if not isinstance(style, dict):
        style = {}
        data["style"] = style

    # If style is using default cyan #00f0ff or missing colors, upgrade to topic-aware palette
    curr_accent = str(style.get("accent", "")).lower()
    if not curr_accent or curr_accent in ("#00f0ff", "#00ffff", "cyan"):
        style["bgFrom"] = topic_palette["bgFrom"]
        style["bgTo"] = topic_palette["bgTo"]
        style["accent"] = topic_palette["accent"]
        style["textColor"] = topic_palette["textColor"]
        style["mutedColor"] = topic_palette["mutedColor"]
    else:
        for k, v in topic_palette.items():
            style.setdefault(k, v)

    for i, s in enumerate(data["scenes"], 1):
        s.setdefault("id", f"s{i}")
        stype = s.get("type", "title")
        if stype not in SCENE_TYPES:
            stype = (
                "title"
                if i == 1
                else "outro" if i == len(data["scenes"]) else "bullets"
            )
            s["type"] = stype
        if s.get("textAnimation") not in ANIMATIONS:
            s["textAnimation"] = BEST_ANIMATION_FOR_SCENE.get(stype, "slideUp")

        # Strip spurious numeric value if present on non-stat / non-chart scenes
        if stype not in ("stat", "chart"):
            s.pop("value", None)
        if not isinstance(s.get("imagePrompts"), list):
            s["imagePrompts"] = []
        # Clean all prompts
        s["imagePrompts"] = [
            clean_flux_prompt(str(prompt))
            for prompt in s["imagePrompts"]
            if isinstance(prompt, str) and prompt.strip()
        ]

        # Smart fallback healing if anything was omitted by LLM:
        if stype == "title":
            s.setdefault("badge", f"{clean_topic.upper()[:16]} BRIEF")
            s.setdefault("title", clean_topic.title())
            s.setdefault("subtitle", f"Mastering {clean_topic} in 60 seconds")
            if not s.get("imagePrompts"):
                s["imagePrompts"] = [
                    f"Studio tabletop photograph of a tactile physical artifact representing {clean_topic} resting on polished dark walnut wood, warm directional key lighting, softbox illumination, clean unprinted surfaces, blank matte finish"
                ]
            s["imagePrompts"] = s["imagePrompts"][:1]
        elif stype == "bullets":
            s.setdefault("heading", f"{clean_topic} Core Architecture")
            if not s.get("bullets") or not isinstance(s["bullets"], list) or len(s["bullets"]) == 0:
                s["bullets"] = [
                    f"Foundational mechanics of {clean_topic}",
                    f"Optimized real-world execution flow",
                    f"Key strategic differentiator in practice",
                ]
            s["bullets"] = s["bullets"][:3]
            if not s.get("imagePrompts"):
                s["imagePrompts"] = [
                    f"Macro photography of tactile precision physical mechanism on dark slate, soft overhead studio softbox light, clean unprinted surfaces, blank matte finish"
                ]
            s["imagePrompts"] = s["imagePrompts"][:1]
        elif stype == "imageGrid":
            s.setdefault("heading", f"Key Pillars of {clean_topic}")
            if not s.get("captions") or not isinstance(s["captions"], list) or len(s["captions"]) == 0:
                s["captions"] = ["Foundation Engine", "Core Execution", "Future Scalability"]
            s["captions"] = s["captions"][:3]
            prompts = s.get("imagePrompts", [])
            while len(prompts) < 3:
                cap = s["captions"][len(prompts)] if len(prompts) < len(s["captions"]) else f"Pillar {len(prompts) + 1}"
                prompts.append(
                    f"Studio photograph of tactile physical {cap} artifact on dark minimalist granite desk, directional softbox light, clean unprinted surfaces, blank matte finish"
                )
            s["imagePrompts"] = prompts[:3]
        elif stype == "flow":
            s.setdefault("heading", f"3-Step {clean_topic} Workflow")
            if not s.get("steps") or not isinstance(s["steps"], list) or len(s["steps"]) == 0:
                s["steps"] = [
                    {"title": "Map Fundamentals", "detail": f"Analyze core constraints and prerequisites of {clean_topic}"},
                    {"title": "Execute System", "detail": f"Deploy proven workflows and concrete implementations"},
                    {"title": "Optimize & Scale", "detail": f"Measure outputs and iterate for maximum efficiency"},
                ]
            while len(s["steps"]) < 3:
                s["steps"].append({"title": f"Phase {len(s['steps']) + 1}", "detail": f"Implement phase {len(s['steps']) + 1} of {clean_topic}"})
            s["steps"] = s["steps"][:3]

            # ENSURE ALL 3 STEP CARDS RECEIVE CONCRETE PHYSICAL IMAGE PROMPTS
            prompts = s.get("imagePrompts", [])
            for step_idx in range(len(prompts), 3):
                step_title = s["steps"][step_idx].get("title", f"Phase {step_idx + 1}")
                prompts.append(
                    f"Tactile physical precision instrument representing {step_title} for {clean_topic} resting on a circular dark slate pedestal, warm studio softbox lighting, clean unprinted surfaces, blank matte finish"
                )
            s["imagePrompts"] = prompts[:3]
        elif stype == "chart":
            s.setdefault("heading", f"Measured Impact of {clean_topic}")
            points = []
            for point in s.get("data", []):
                if not isinstance(point, dict) or not str(point.get("label", "")).strip():
                    continue
                try:
                    value = float(point.get("value"))
                except (TypeError, ValueError):
                    continue
                if not math.isfinite(value) or value < 0:
                    continue
                if value.is_integer():
                    value = int(value)
                points.append({
                    "label": str(point["label"]).strip()[:24],
                    "value": value,
                    "detail": str(point.get("detail", "")).strip()[:80],
                })
            s["data"] = points[:5]
            # Charts are UI/data scenes; they do not need a generated image.
            s["imagePrompts"] = []
        elif stype == "timeline":
            s.setdefault("heading", f"The Evolution of {clean_topic}")
            events = s.get("timeline", [])
            if not isinstance(events, list) or not events:
                events = [
                    {"label": "01", "title": "Starting Point", "detail": f"Understand the foundations of {clean_topic}."},
                    {"label": "02", "title": "Turning Point", "detail": "Apply the first meaningful improvement."},
                    {"label": "03", "title": "Next Horizon", "detail": "Scale the approach with deliberate iteration."},
                ]
            normalized = []
            for index, event in enumerate(events[:4]):
                if not isinstance(event, dict):
                    continue
                normalized.append({
                    "label": str(event.get("label", f"{index + 1:02d}"))[:18],
                    "title": str(event.get("title", f"Phase {index + 1}"))[:44],
                    "detail": str(event.get("detail", "")).strip()[:100],
                })
            s["timeline"] = normalized[:4]
            s["imagePrompts"] = []
        elif stype == "checklist":
            s.setdefault("heading", f"{clean_topic} Checklist")
            items = s.get("items", [])
            if not isinstance(items, list) or not items:
                items = [
                    {"title": "Define the target", "detail": "Clarify the outcome before taking action."},
                    {"title": "Execute the smallest step", "detail": "Turn the plan into a measurable action."},
                    {"title": "Review and improve", "detail": "Use the result to choose the next move."},
                ]
            normalized = []
            for index, item in enumerate(items[:5]):
                if not isinstance(item, dict):
                    continue
                normalized.append({
                    "title": str(item.get("title", f"Action {index + 1}"))[:52],
                    "detail": str(item.get("detail", "")).strip()[:100],
                })
            s["items"] = normalized[:5]
            s["imagePrompts"] = []
        elif stype == "comparison":
            s.setdefault("heading", f"{clean_topic} Strategic Shift")
            s.setdefault("leftLabel", "Traditional Way")
            if not s.get("leftItems") or not isinstance(s["leftItems"], list) or len(s["leftItems"]) == 0:
                s["leftItems"] = [
                    f"Manual friction in {clean_topic}",
                    "Slow disconnected feedback loops",
                    "Error-prone repetitive bottlenecks",
                ]
            s["leftItems"] = s["leftItems"][:3]
            s.setdefault("rightLabel", "Optimized System")
            if not s.get("rightItems") or not isinstance(s["rightItems"], list) or len(s["rightItems"]) == 0:
                s["rightItems"] = [
                    f"Automated {clean_topic} execution",
                    "Instant real-time telemetry",
                    "Continuous 10x throughput scaling",
                ]
            s["rightItems"] = s["rightItems"][:3]

            # ENSURE EXACTLY 2 DISTINCT IMAGE PROMPTS (LEFT & RIGHT)
            prompts = s.get("imagePrompts", [])
            if len(prompts) < 1:
                prompts.append(
                    f"Macro studio photograph of a tangled worn mechanical gear set on dark stone, dim cool lighting, clean unprinted surfaces, blank matte finish"
                )
            if len(prompts) < 2:
                prompts.append(
                    f"Macro studio photograph of a precision engineered titanium mechanism on polished dark granite, warm studio softbox rim lighting, clean unprinted surfaces, blank matte finish"
                )
            s["imagePrompts"] = prompts[:2]
        elif stype == "bento":
            s.setdefault("heading", f"{clean_topic} Architecture")
            s.setdefault("heroTitle", f"{clean_topic} Core Engine")
            s.setdefault("heroDetail", f"Engineered for high-throughput scalability and real-time state responsiveness.")
            s.setdefault("statValue", "10x")
            s.setdefault("statLabel", "Execution velocity multiplier")
            s.setdefault("featureTitle", "Telemetry Grid")
            s.setdefault("featureDetail", "Deep instrumentation tracks every micro-state change automatically.")
            prompts = s.get("imagePrompts", [])
            if not prompts:
                prompts.append(
                    f"Studio photograph of a tactile physical modular server blade carved from matte black aluminum with copper accents on dark walnut, studio softbox lighting, clean unprinted surfaces, blank matte finish"
                )
            s["imagePrompts"] = prompts[:1]
        elif stype == "splitHero":
            s.setdefault("badge", f"{clean_topic.upper()[:16]} SPOTLIGHT")
            s.setdefault("title", clean_topic.title())
            s.setdefault("subtitle", f"High-impact architectural breakdown of {clean_topic} principles")
            if not s.get("bullets") or not isinstance(s["bullets"], list) or len(s["bullets"]) == 0:
                s["bullets"] = [
                    f"Deterministic workflow reliability for {clean_topic}",
                    "Zero-latency state synchronization",
                    "Auditable end-to-end telemetry",
                ]
            s["bullets"] = s["bullets"][:3]
            prompts = s.get("imagePrompts", [])
            if not prompts:
                prompts.append(
                    f"Studio shot of an architectural monolith sculptured from obsidian and frosted glass resting on dark basalt stone, soft three-point studio light, clean unprinted surfaces, blank matte finish"
                )
            s["imagePrompts"] = prompts[:1]
        elif stype == "stat":
            s.setdefault("heading", "MEASURED EFFICIENCY")
            try:
                numeric_value = float(s.get("value", 85))
                if 0 < numeric_value < 1:
                    numeric_value = round(numeric_value * 100)
                elif numeric_value.is_integer():
                    numeric_value = int(numeric_value)
                else:
                    numeric_value = round(numeric_value, 1)
                s["value"] = numeric_value
            except (TypeError, ValueError):
                s["value"] = 85
            s.setdefault("suffix", "%")
            s.setdefault("label", f"Performance gain achieved when implementing {clean_topic}")
            if not s.get("imagePrompts"):
                s["imagePrompts"] = [
                    f"Studio macro shot of an industrial brushed-metal instrument or gauge with precision markings on dark granite, sharp focus, clean unprinted surfaces, blank matte finish"
                ]
            s["imagePrompts"] = s["imagePrompts"][:1]
        elif stype == "quote":
            s.setdefault(
                "quote",
                f"Simplicity is the prerequisite for reliability in any complex {clean_topic.lower()} system.",
            )
            s.setdefault("attribution", "Industry Principle")
            s["imagePrompts"] = []
        elif stype == "outro":
            s.setdefault("title", f"Ready to Master {clean_topic}?")
            s.setdefault("subtitle", "Start applying these principles to your builds today")
            s.setdefault("cta", "Save For Next Build")
            if not s.get("imagePrompts"):
                s["imagePrompts"] = [
                    f"Sculptural milestone trophy carved from polished black obsidian and satin brass resting on an architectural plinth in a minimalist gallery, warm dramatic spotlight, clean lines, clean unprinted surfaces, blank matte finish"
                ]
            s["imagePrompts"] = s["imagePrompts"][:1]

    data["topic"] = clean_topic
    data["slug"] = slugify(data["topic"])
    return data


# -- 2. Camb.ai voiceover -----------------------------------------------------

CAMB_URL = "https://client.camb.ai/apis/tts-stream"


def camb_tts(text: str, out_path: Path) -> None:
    key = first_env("CAMB_API_KEY") or (env_keys("CAMB_AI") or [""])[0]
    if not key:
        raise RuntimeError("no Camb.ai key (set CAMB_API_KEY in .env)")
    # Default voice 165290; override via CAMB_VOICE_ID env/secret if ever needed
    voice = int(first_env("CAMB_VOICE_ID", default="165290"))
    lang = first_env("CAMB_LANG", default="en-in")
    payload = {
        "text": text,
        "language": lang,
        "voice_id": voice,
        "speech_model": "mars-pro",
        "output_configuration": {"format": "wav", "duration": None},
        "voice_settings": {
            "enhance_reference_audio_quality": False,
            "speaking_rate": 1,
        },
    }
    for attempt in range(4):
        try:
            r = requests.post(
                CAMB_URL,
                json=payload,
                headers={"x-api-key": key, "Content-Type": "application/json"},
                timeout=(15, 240),
                stream=True,  # docs: response streams audio chunks, close = end
            )
            # Verified against docs: 200-empty means the server closed the stream
            # immediately (cold LB backend) — an immediate retry hits a warm one.
            content = b"".join(r.iter_content(chunk_size=65536)) if r.status_code == 200 else b""
            if r.status_code == 200 and content[:4] == b"RIFF":
                out_path.write_bytes(content)
                return
            # error text from the bytes we already read — r.text after
            # iter_content raises "already consumed"
            raise RuntimeError(f"camb {r.status_code}: {content[:150]!r}")
        except Exception as e:
            print(f"  camb attempt {attempt + 1} failed: {e}")
            time.sleep(1.5)  # warm backend serves on the very next attempt
    # free fallback so one bad TTS day doesn't kill the video (Indian English PrabhatNeural)
    print("  falling back to edge-tts for this scene")
    import edge_tts

    asyncio_run(edge_tts.Communicate(text, "en-IN-PrabhatNeural").save(str(out_path)))


def asyncio_run(coro):
    import asyncio

    return asyncio.run(coro)


# -- 3. Free AI images (failover chain ported from perspective-api) -----------

import asyncio
import base64
import random
import urllib.parse

import aiohttp
from aiohttp_socks import ProxyConnector

FREEGEN_SIGNER = "https://prompt-signer.freegen.app/"
FREEGEN_GEN = "https://image-generator.freegen.app/"
FREEGEN_WS = "wss://websocket-bridge.freegen.app/ws"
REDPANDA = "https://api.redpandaai.com"
RAPHAEL = "https://api.raphaelai.org"
DIMS = {"width": 1024, "height": 576}

_ALIVE: list[tuple[str, str, str]] | None = None


def _proxies() -> list[tuple[str, str, str]]:
    """PROXY_LIST entries (ip:port:user:pass, separated by , or ;) -> [(host:port, user, pwd)]."""
    out = []
    for line in first_env("PROXY_LIST").replace(";", ",").split(","):
        parts = line.strip().split(":")
        if len(parts) == 4:
            host, port, user, pwd = parts
            out.append((f"{host}:{port}", user, pwd))
    return out


def _socks_url(p: tuple[str, str, str]) -> str:
    hostport, user, pwd = p
    return f"socks5h://{urllib.parse.quote(user)}:{urllib.parse.quote(pwd)}@{hostport}"


def _alive_proxies() -> list[tuple[str, str, str]]:
    """Health-check the SOCKS5 pool once; dead proxies are skipped after."""
    global _ALIVE
    if _ALIVE is None:
        pool = _proxies()

        def check(p):
            try:
                requests.get(
                    "https://api.ipify.org",
                    proxies={"http": _socks_url(p), "https": _socks_url(p)},
                    timeout=15,
                )
                return True
            except Exception:
                return False

        if pool:
            with concurrent.futures.ThreadPoolExecutor(min(10, len(pool))) as ex:
                res = list(ex.map(check, pool))
            _ALIVE = [p for p, ok in zip(pool, res) if ok]
            print(f"  proxy pool: {len(_ALIVE)}/{len(pool)} alive")
        else:
            _ALIVE = []
    return _ALIVE


def _proxy_kwargs() -> dict:
    """requests-style kwargs with a random alive SOCKS5 proxy."""
    pool = _alive_proxies()
    if not pool:
        return {"proxies": None}
    s = _socks_url(random.choice(pool))
    return {"proxies": {"http": s, "https": s}}


async def _freegen_async(prompt: str) -> bytes:
    pool = _alive_proxies()
    if not pool:
        raise RuntimeError("freegen needs PROXY_LIST (all dead?)")
    hostport, user, pwd = random.choice(pool)
    connector = ProxyConnector.from_url(
        f"socks5://{urllib.parse.quote(user)}:{urllib.parse.quote(pwd)}@{hostport}"
    )
    timeout = aiohttp.ClientTimeout(total=120)
    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        async with session.post(FREEGEN_SIGNER, json={"prompt": prompt}) as r:
            r.raise_for_status()
            sd = await r.json()
        async with session.post(
            FREEGEN_GEN,
            json={
                "prompt": sd["prompt"],
                "ts": sd["ts"],
                "sig": sd["sig"],
                "ratio_id": "16:9",
            },
        ) as r:
            r.raise_for_status()
            job_id = (await r.json())["job_id"]
        async with session.ws_connect(FREEGEN_WS, receive_timeout=60.0) as ws:
            await ws.send_json(
                {"type": "subscribe", "job_id": job_id, "auth": f"{sd['sig']}:{sd['ts']}"}
            )
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    if data.get("type") == "error":
                        raise RuntimeError(f"freegen ws: {str(data.get('message', '?'))[:120]}")
                    if data.get("type") == "result":
                        b64 = data["image_data"].split(",", 1)[-1]
                        return base64.b64decode(b64)
                elif msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSED):
                    raise RuntimeError("freegen ws closed unexpectedly")
    raise RuntimeError("freegen ws ended without result")


def _gen_freegen(prompt: str) -> bytes:
    return asyncio.run(_freegen_async(prompt))


def _sse_output_url(url: str, headers: dict, proxies: dict | None) -> str | None:
    with requests.get(
        url, headers=headers, proxies=proxies, stream=True, timeout=(10, 90)
    ) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if line:
                txt = line.decode("utf-8")
                if txt.startswith("data:"):
                    try:
                        out = json.loads(txt[5:].strip()).get("outputUrl")
                        if out:
                            return out
                    except json.JSONDecodeError:
                        continue
    return None


def _gen_via(base: str, origin: str, prompt: str) -> bytes:
    px = _proxy_kwargs()
    h = {"accept": "*/*", "origin": origin, "referer": f"{origin}/", "user-agent": UA}
    ctx = requests.get(f"{base}/v1/guest/context", headers=h, timeout=(10, 30), **px).json()
    if not ctx.get("data", {}).get("token"):
        raise RuntimeError(f"guest context: {json.dumps(ctx)[:120]}")
    token = ctx["data"]["token"]
    job = requests.post(
        f"{base}/v1/image/jobs",
        json={"prompt": prompt, **DIMS},
        headers={**h, "content-type": "application/json", "x-request-context": token},
        timeout=(10, 30),
        **px,
    ).json()
    data = job.get("data") or {}
    if not data.get("jobId"):
        err = data.get("error") or job.get("error") or job
        raise RuntimeError(f"job create: {json.dumps(err)[:120]}")
    url = _sse_output_url(
        f"{base}/v1/jobs/{data['jobId']}/events",
        headers={
            **h,
            "accept": "text/event-stream",
            "x-job-poll-token": data["pollToken"],
            "x-request-context": token,
        },
        proxies=px["proxies"],
    )
    if not url:
        raise RuntimeError("no outputUrl from SSE")
    img = requests.get(url, timeout=(10, 60), proxies=px["proxies"])
    img.raise_for_status()
    return img.content


_STYLE_WORDS = re.compile(
    r"illustration|vector|style|lighting|background|detail|no text|no words"
    r"|no letters|minimal|clean|render|photoreali|digital art|3d|logo|icon|cinematic",
    re.I,
)


def _stock_query(prompt: str) -> str:
    """'digital illustration, a rocket launching, dark navy background, no text'
    -> 'a rocket launching' (Pexels search query)."""
    keep = []
    for chunk in prompt.split(","):
        c = chunk.strip()
        if c and not _STYLE_WORDS.search(c) and len(c.split()) <= 6:
            keep.append(c)
    q = " ".join(keep).strip()
    return q or prompt.split(",")[0].strip()


def _gen_pexels(prompt: str) -> bytes:
    keys = [k for k in [first_env("PEXELS_API_KEY")] if k] or env_keys("PEXELS_API_KEY")
    if not keys:
        raise RuntimeError("no Pexels key")
    q = _stock_query(prompt)
    key = keys[abs(hash(q)) % len(keys)]
    r = requests.get(
        "https://api.pexels.com/v1/search",
        params={"query": q, "per_page": 6, "orientation": "landscape"},
        headers={"Authorization": key},
        timeout=(10, 30),
    )
    r.raise_for_status()
    photos = r.json().get("photos", [])
    if not photos:
        raise RuntimeError(f"pexels: no results for {q!r}")
    pick = random.choice(photos)["src"].get("large2x") or photos[0]["src"]["large"]
    img = requests.get(pick, timeout=(10, 60))
    img.raise_for_status()
    return img.content


def _gen_cloudflare(prompt: str) -> bytes:
    worker = first_env("CLOUDFLARE_WORKER_URL")
    key = first_env("CLOUDFLARE_API_KEY")
    if not worker or not key:
        raise RuntimeError("cloudflare worker not configured")
    r = requests.post(
        worker,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"prompt": prompt},
        timeout=(10, 90),
    )
    r.raise_for_status()
    return r.content


from PIL import Image
import io


def _strip_corner_watermark(img_bytes: bytes) -> bytes:
    """Crops the bottom 32px (where free API watermarks appear) and seamlessly
    restores 16:9 1024x576 using high quality Lanczos resampling."""
    try:
        im = Image.open(io.BytesIO(img_bytes))
        w, h = im.size
        if h > 100:
            cropped = im.crop((0, 0, w, h - 32))
            restored = cropped.resize((w, h), Image.Resampling.LANCZOS)
            out = io.BytesIO()
            restored.save(out, format="JPEG", quality=95)
            return out.getvalue()
    except Exception:
        pass
    return img_bytes


def _valid_image(b: bytes) -> bool:
    return len(b) > 4096 and (b[:4] == b"\x89PNG" or b[:2] == b"\xff\xd8")


def _gen_pollinations(prompt: str, model: str = "flux") -> bytes:
    pool = _alive_proxies()
    if not pool:
        seed = random.randint(1000, 999999)
        url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width=1024&height=576&model={model}&nologo=true&seed={seed}"
        r = requests.get(url, timeout=(15, 60))
        r.raise_for_status()
        if _valid_image(r.content):
            return _strip_corner_watermark(r.content)
        raise RuntimeError("invalid image bytes from direct pollinations")

    # Rotate through proxies until one succeeds
    shuffled = list(pool)
    random.shuffle(shuffled)
    last_err = None
    for p in shuffled:
        s = _socks_url(p)
        px = {"http": s, "https": s}
        seed = random.randint(1000, 999999)
        url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width=1024&height=576&model={model}&nologo=true&seed={seed}"
        try:
            r = requests.get(url, proxies=px, timeout=(15, 60))
            if r.status_code == 200 and _valid_image(r.content):
                return _strip_corner_watermark(r.content)
            if r.status_code == 402:
                # Proxy IP is in 45s cooldown, skip to next proxy
                continue
            r.raise_for_status()
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"pollinations_{model}: all proxies failed ({last_err})")


FAL_QUEUE = "https://queue.fal.run/fal-ai/flux/schnell"


def _gen_fal(prompt: str) -> bytes:
    """fal.ai flux/schnell (paid, ~$0.003/image) — the reliable provider for
    datacenter runners where the free chain is IP-gated. Queue API:
    submit -> poll status -> result.images[0].url."""
    key = first_env("FAL_KEY")
    if not key:
        raise RuntimeError("no FAL_KEY set")
    headers = {"Authorization": f"Key {key}"}
    submit = requests.post(
        FAL_QUEUE,
        headers=headers,
        json={
            "prompt": prompt,
            "image_size": {"width": 1024, "height": 576},  # matches DIMS 16:9
            "num_images": 1,
            "num_inference_steps": 4,  # schnell optimum
            "output_format": "jpeg",
        },
        timeout=30,
    )
    if submit.status_code != 200:
        raise RuntimeError(f"fal submit {submit.status_code}: {submit.text[:120]}")
    request_id = submit.json().get("request_id")
    if not request_id:
        raise RuntimeError("fal submit returned no request_id")

    status_url = f"{FAL_QUEUE}/requests/{request_id}/status"
    result_url = f"{FAL_QUEUE}/requests/{request_id}"
    for _ in range(45):  # ~90s ceiling per image (schnell normally finishes in 2-5s)
        st = requests.get(status_url, headers=headers, timeout=30)
        if st.status_code == 200 and st.json().get("status") == "COMPLETED":
            r = requests.get(result_url, headers=headers, timeout=30)
            if r.status_code != 200:
                raise RuntimeError(f"fal result {r.status_code}: {r.text[:120]}")
            images = r.json().get("images") or []
            if not images:
                raise RuntimeError("fal result has no images")
            img = requests.get(images[0]["url"], timeout=60)
            img.raise_for_status()
            if _valid_image(img.content):
                return img.content
            raise RuntimeError("fal returned invalid image bytes")
        time.sleep(2)
    raise RuntimeError("fal timed out after 90s")


def gen_image(prompt: str) -> tuple[bytes, str]:
    """Image generation chain: fal.ai flux/schnell FIRST when FAL_KEY is set
    (reliable from datacenter runners), then the keyless fallbacks
    (Pollinations Flux/Turbo via SOCKS5 proxy rotation, RedPanda/Raphael).
    Strictly NO Pexels stock photos."""
    prompt = clean_flux_prompt(prompt)
    providers = [
        ("pollinations_flux", lambda: _gen_pollinations(prompt, model="flux")),
        ("pollinations_turbo", lambda: _gen_pollinations(prompt, model="turbo")),
        ("redpanda", lambda: _gen_via(REDPANDA, "https://redpandaai.com", prompt)),
        ("raphael", lambda: _gen_via(RAPHAEL, "https://raphaelai.org", prompt)),
    ]
    if first_env("FAL_KEY"):
        providers.insert(0, ("fal_flux_schnell", lambda: _gen_fal(prompt)))
        # visible reason when fal fails and the free chain takes over
        try:
            return _gen_fal(prompt), "fal_flux_schnell"
        except Exception as fe:
            print(f"  fal_flux_schnell failed ({str(fe)[:120]}) — falling back to free chain")
    errors: list[str] = []
    for attempt in range(4):
        for name, fn in providers:
            try:
                data = fn()
                if _valid_image(data):
                    return data, name
                errors.append(f"{name}: invalid bytes ({len(data)}b)")
            except Exception as e:
                errors.append(f"{name}: {str(e)[:90]}")
        if attempt < 3:
            print(f"  AI providers busy, retrying in 12s (pass {attempt + 2}/4)...")
            time.sleep(12)
    raise RuntimeError("; ".join(errors[-4:]))


# -- main pipeline -------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--topic", help="video topic (prompts if omitted)")
    ap.add_argument("--skip-render", action="store_true", help="only build assets")
    ap.add_argument("--reuse-script", action="store_true",
                    help="reuse existing topics/<slug>/script.json, skip LLM")
    args = ap.parse_args()

    topic = args.topic or input("Enter a video topic: ").strip()
    if not topic:
        sys.exit("empty topic")
    slug = slugify(topic)
    topic_dir = ROOT / "topics" / slug
    audio_dir = topic_dir / "audio"
    images_dir = topic_dir / "images"
    for d in (audio_dir, images_dir):
        d.mkdir(parents=True, exist_ok=True)
    script_path = topic_dir / "script.json"

    # 1. script
    banner("1/4  AI script (Gemini -> OpenRouter)")
    if script_path.exists() and (args.reuse_script or
                                 input(f"script.json exists for '{slug}', reuse? [Y/n] ").strip().lower() in ("y", "")):
        data = validate_script(
            json.loads(script_path.read_text(encoding="utf-8")),
            topic,
        )
        script_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print("  reusing existing script.json")
    else:
        raw = llm_json(LLM_PROMPT.format(topic=topic, animations=ANIMATIONS))
        data = validate_script(parse_json_loose(raw), topic)
        script_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  wrote {len(data['scenes'])} scenes -> {script_path.name}")

    # 1b. narrations too short for ~60s? one LLM expansion pass
    def narration_words(d: dict) -> int:
        return sum(len((s.get("narration") or "").split()) for s in d["scenes"])

    if narration_words(data) < 140 and not args.reuse_script:
        print(f"  narrations only {narration_words(data)} words -- expanding to ~165")
        try:
            expand = llm_json(
                'Here is a video script JSON. Rewrite ONLY the "narration" fields so each '
                "is 18-26 words and the total is 160-175 words. Keep every other field and "
                "the structure exactly the same. Respond with ONLY the JSON.\n\n"
                + json.dumps(data, ensure_ascii=False)
            )
            expanded = validate_script(parse_json_loose(expand), data["topic"])
            if narration_words(expanded) > narration_words(data):
                data = expanded
                script_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
                print(f"  expanded to {narration_words(data)} words")
            else:
                print("  expansion did not help, keeping original")
        except Exception as e:
            print(f"  expansion failed ({str(e)[:100]}), keeping original")
    print(f"  narration total: {narration_words(data)} words (~{narration_words(data) // 2.7:.0f}s speech)")

    # 2. voiceover
    banner("2/4  Camb.ai voiceover")
    for s in data["scenes"]:
        if not s.get("narration"):
            continue
        h8 = hashlib.md5(s["narration"].encode("utf-8")).hexdigest()[:8]
        out = audio_dir / f"{s['id']}-{h8}.wav"
        s["_audio_file"] = out.name
        if out.exists() and out.stat().st_size > 1000:
            print(f"  cached {out.name}")
            continue
        print(f"  tts {s['id']} ...")
        camb_tts(s["narration"], out)
        print(f"  saved {out.name} ({out.stat().st_size // 1024} KB)")

    # 3. images
    image_provider = "fal_flux_schnell (fal.ai)" if first_env("FAL_KEY") \
        else "free chain: Pollinations -> RedPanda -> Raphael (no FAL_KEY)"
    banner(f"3/4  AI images via {image_provider}")
    jobs = []
    for s in data["scenes"]:
        for k, prompt in enumerate(s.get("imagePrompts", [])):
            out = images_dir / f"{s['id']}-{k}.jpg"
            jobs.append((out, prompt, s, k))
    todo = [(o, p, s, k) for o, p, s, k in jobs if not (o.exists() and o.stat().st_size > 4096)]
    for o, _, _, _ in jobs:
        if o not in [t[0] for t in todo]:
            print(f"  cached {o.name}")

    def work(job):
        out, prompt, _, _ = job
        data, provider = gen_image(prompt)
        out.write_bytes(data)
        return out.name, provider

    if todo:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            for name, provider in pool.map(work, todo):
                print(f"  {name} via {provider}")

    # 4. assemble + render
    banner("4/4  assemble + render")
    pub = ROOT / "public" / "assets" / slug
    (pub / "audio").mkdir(parents=True, exist_ok=True)
    (pub / "images").mkdir(parents=True, exist_ok=True)
    for s in data["scenes"]:
        wav = audio_dir / s.get("_audio_file", f"{s['id']}.wav")
        s["audio"] = f"assets/{slug}/audio/{wav.name}" if wav.exists() else None
        s["images"] = []
        for k in range(len(s.get("imagePrompts", []))):
            img = images_dir / f"{s['id']}-{k}.jpg"
            if img.exists():
                s["images"].append(f"assets/{slug}/images/{img.name}")
    for wav in audio_dir.glob("*.wav"):
        shutil.copy2(wav, pub / "audio" / wav.name)
    for img in images_dir.glob("*.jpg"):
        shutil.copy2(img, pub / "images" / img.name)
    script_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    n_audio = len(list(audio_dir.glob("*.wav")))
    n_img = len(list(images_dir.glob("*.jpg")))
    print(f"  assets: {n_audio} voiceovers, {n_img} images -> public/assets/{slug}/")

    # Pre-calculate exact frame timings from voiceovers for frame-perfect sync
    import math
    import struct

    def get_wav_dur(p: Path) -> float:
        if not p.exists():
            return 5.0
        try:
            with open(p, "rb") as f:
                hdr = f.read(44)
            if hdr[12:16] == b"fmt ":
                channels = struct.unpack("<H", hdr[22:24])[0]
                rate = struct.unpack("<I", hdr[24:28])[0]
                bps = struct.unpack("<H", hdr[34:36])[0]
                byte_rate = rate * channels * (bps // 8)
                data_size = p.stat().st_size - 44
                return data_size / float(byte_rate)
        except Exception:
            pass
        return 5.0

    timings = []
    fallback_dur = {
        "title": 4.5,
        "outro": 4.5,
        "bullets": 7.0,
        "imageGrid": 7.0,
        "flow": 7.0,
        "chart": 7.0,
        "timeline": 7.0,
        "checklist": 7.0,
        "stat": 5.0,
        "quote": 6.0,
        "comparison": 7.5,
        "bento": 7.5,
        "splitHero": 7.0,
    }
    for s in data["scenes"]:
        wav = audio_dir / s.get("_audio_file", f"{s['id']}.wav")
        dur = get_wav_dur(wav) if wav.exists() else fallback_dur.get(s.get("type"), 5.0)
        timings.append(math.ceil((dur + 0.45) * 30))

    # remotion --props needs {script: ..., timings: ...}
    props_path = topic_dir / "props.json"
    props_path.write_text(
        json.dumps({"script": data, "timings": timings}, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if args.skip_render:
        print(f"\nassets ready. render later with:\n  npx remotion render TopicVideo topics/{slug}/video.mp4 --props=topics/{slug}/props.json")
        return

    out_mp4 = topic_dir / "video.mp4"
    if sys.platform == "win32":
        npx = shutil.which("npx.cmd") or "npx.cmd"
    else:
        npx = shutil.which("npx") or "npx"
    cmd = [npx, "remotion", "render", "TopicVideo", str(out_mp4),
           f"--props={props_path}", "--log=error"]
    print(f"  rendering: {' '.join(cmd[1:])}")
    r = subprocess.run(cmd, cwd=ROOT)
    if r.returncode != 0 or not out_mp4.exists():
        sys.exit("render failed")
    print(f"\n\033[32mDONE: {out_mp4}  ({out_mp4.stat().st_size // (1024 * 1024)} MB)\033[0m")


if __name__ == "__main__":
    main()
