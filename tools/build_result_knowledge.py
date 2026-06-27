from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[1]
SOURCE_ROOTS = [WORKSPACE / "book-md", WORKSPACE / "papers-md"]
RESULT_ROOT = WORKSPACE / "result"

STOPWORDS = {
    "about",
    "above",
    "after",
    "again",
    "against",
    "almost",
    "also",
    "although",
    "among",
    "another",
    "anything",
    "around",
    "because",
    "before",
    "been",
    "being",
    "between",
    "chapter",
    "could",
    "design",
    "does",
    "domain",
    "dimension",
    "each",
    "even",
    "ever",
    "from",
    "have",
    "however",
    "into",
    "many",
    "more",
    "most",
    "much",
    "other",
    "same",
    "should",
    "since",
    "some",
    "still",
    "over",
    "page",
    "part",
    "such",
    "than",
    "that",
    "their",
    "there",
    "these",
    "they",
    "this",
    "through",
    "under",
    "which",
    "while",
    "with",
    "were",
    "what",
    "when",
    "where",
    "whether",
    "within",
    "without",
    "would",
    "history",
    "figure",
    "notes",
    "references",
    "contents",
    "index",
}

DOMAIN_DIMENSIONS = [
    {
        "name": "研究对象与问题意识 / Research Object and Problem Framing",
        "terms": [
            "design",
            "history",
            "object",
            "thing",
            "material culture",
            "artifact",
            "everyday",
            "style",
            "form",
            "ornament",
            "method",
            "approach",
            "study",
            "research",
            "sociology",
            "association",
            "associations",
            "actor",
            "network",
            "science",
            "trace",
            "tracing",
            "物",
            "设计",
            "风格",
            "形式",
            "日常",
            "方法",
            "研究",
        ],
        "category": "methodological_insight / 方法论洞见",
    },
    {
        "name": "材料、技术与生产制度 / Materials, Technology and Production",
        "terms": [
            "material",
            "materials",
            "production",
            "manufacture",
            "industry",
            "industrial",
            "technology",
            "machine",
            "craft",
            "labor",
            "work",
            "making",
            "factory",
            "technique",
            "材料",
            "生产",
            "制造",
            "工艺",
            "技术",
            "工业",
            "劳动",
        ],
        "category": "historical_fact / 历史事实",
    },
    {
        "name": "消费、流通与价值建构 / Consumption, Circulation and Value",
        "terms": [
            "consumption",
            "consumer",
            "commodity",
            "commodities",
            "exchange",
            "market",
            "value",
            "demand",
            "taste",
            "fashion",
            "goods",
            "circulation",
            "biography",
            "消费",
            "商品",
            "市场",
            "价值",
            "流通",
            "品味",
            "需求",
        ],
        "category": "theoretical_claim / 理论主张",
    },
    {
        "name": "社会身份、性别与权力关系 / Identity, Gender and Power",
        "terms": [
            "gender",
            "women",
            "woman",
            "men",
            "class",
            "identity",
            "power",
            "politics",
            "political",
            "status",
            "national",
            "colonial",
            "patriarchy",
            "feminist",
            "性别",
            "阶级",
            "身份",
            "权力",
            "政治",
            "女性",
            "民族",
        ],
        "category": "theoretical_claim / 理论主张",
    },
    {
        "name": "视觉、符号与意义生产 / Visuality, Signs and Meaning",
        "terms": [
            "image",
            "visual",
            "representation",
            "meaning",
            "symbol",
            "semiotic",
            "sign",
            "aesthetic",
            "taste",
            "appearance",
            "display",
            "language",
            "视觉",
            "图像",
            "符号",
            "意义",
            "审美",
            "表征",
        ],
        "category": "conceptual_tool / 概念工具",
    },
    {
        "name": "历史变迁、现代性与制度语境 / Historical Change, Modernity and Institutions",
        "terms": [
            "modern",
            "modernity",
            "century",
            "nineteenth",
            "twentieth",
            "movement",
            "revolution",
            "institution",
            "state",
            "war",
            "economy",
            "culture",
            "society",
            "历史",
            "现代",
            "世纪",
            "制度",
            "社会",
            "文化",
            "经济",
        ],
        "category": "historical_context / 历史语境",
    },
]


@dataclass
class Analysis:
    source: Path
    destination: Path
    title: str
    char_count: int
    word_count: int
    paragraph_count: int
    top_terms: list[tuple[str, int]]
    dimensions: list[dict]
    proper_nouns: list[tuple[str, str]]


def read_text(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gb18030", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def clean_markdown(text: str) -> str:
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[[^\]]+\]\([^)]*\)", " ", text)
    text = re.sub(r"^[#>*\-\s`|:]+", "", text, flags=re.M)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_title(path: Path, text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#"):
            title = line.lstrip("#").strip()
            if title:
                return title[:140]
    return path.stem[:140]


def tokenize(text: str) -> list[str]:
    english = re.findall(r"[A-Za-z][A-Za-z'\-]{3,}", text.lower())
    chinese_terms = re.findall(r"[\u4e00-\u9fff]{2,6}", text)
    tokens = [w.strip("-'") for w in english if w not in STOPWORDS]
    tokens.extend(t for t in chinese_terms if len(t) >= 2)
    return tokens


def top_terms(text: str, limit: int = 18) -> list[tuple[str, int]]:
    counts = Counter(tokenize(text))
    return [(term, count) for term, count in counts.most_common(limit) if count > 1]


def contains_term(text_lower: str, term: str) -> bool:
    term_lower = term.lower()
    if re.search(r"[\u4e00-\u9fff]", term_lower):
        return term_lower in text_lower
    return re.search(rf"\b{re.escape(term_lower)}\b", text_lower) is not None


def count_term(text_lower: str, term: str) -> int:
    term_lower = term.lower()
    if re.search(r"[\u4e00-\u9fff]", term_lower):
        return text_lower.count(term_lower)
    return len(re.findall(rf"\b{re.escape(term_lower)}\b", text_lower))


def split_sentences(text: str) -> list[str]:
    raw = re.split(r"(?<=[.!?。！？])\s+|\n+", text)
    sentences = []
    for item in raw:
        sentence = re.sub(r"\s+", " ", item).strip()
        sentence = sentence.strip("# -*>|")
        if 45 <= len(sentence) <= 420:
            sentences.append(sentence)
    return sentences[:700]


def short_evidence(sentence: str, max_words: int = 18) -> str:
    words = re.findall(r"[\w'\-]+|[\u4e00-\u9fff]+", sentence)
    if not words:
        return ""
    shortened = " ".join(words[:max_words])
    if len(words) > max_words:
        shortened += " ..."
    return shortened.replace("|", "/")


def score_sentence(sentence: str, terms: list[str], global_terms: set[str]) -> int:
    lower = sentence.lower()
    score = sum(count_term(lower, term) for term in terms)
    score += sum(1 for term in global_terms if contains_term(lower, term))
    score += min(len(sentence) // 80, 3)
    return score


def classify_sentence(sentence: str) -> str:
    lower = sentence.lower()
    if any(w in lower for w in ["argue", "concept", "theory", "framework", "claim", "model"]):
        return "theoretical_claim / 理论主张"
    if any(w in lower for w in ["case", "example", "study", "instance"]):
        return "case_study / 个案研究"
    if any(w in lower for w in ["method", "approach", "analysis", "historiography"]):
        return "methodological_insight / 方法论洞见"
    if re.search(r"\b(1[5-9]\d{2}|20\d{2}|19\d{2}|18\d{2})\b", sentence):
        return "historical_fact / 历史事实"
    return "knowledge_point / 知识点"


def extract_proper_nouns(text: str, limit: int = 18) -> list[tuple[str, str]]:
    candidates = []
    patterns = [
        r"\b[A-Z][a-z]+(?:\s+(?:de|du|van|von|of|the|and|[A-Z][a-z]+|[A-Z]\.)){1,5}",
        r"《[^》]{2,80}》",
    ]
    for pattern in patterns:
        candidates.extend(re.findall(pattern, text))
    counts = Counter(c.strip(" ,.;:()[]") for c in candidates)
    result = []
    for name, count in counts.most_common(limit * 3):
        if len(name) < 4 or name.lower() in STOPWORDS:
            continue
        if re.search(r"University|Press|Museum|School|Institute|Council|Association", name):
            kind = "institution / 机构"
        elif name.startswith("《"):
            kind = "work / 著作"
        elif len(name.split()) >= 2:
            kind = "person_or_term / 人名或术语"
        else:
            kind = "term / 术语"
        result.append((name.replace("|", "/"), kind))
        if len(result) >= limit:
            break
    return result


def build_dimensions(text: str, terms: list[tuple[str, int]]) -> list[dict]:
    sentences = split_sentences(text)
    global_terms = {term for term, _ in terms[:8]}
    scored_domains = []
    lower = text.lower()
    for domain in DOMAIN_DIMENSIONS:
        score = 0
        for term in domain["terms"]:
            score += count_term(lower, term)
        scored_domains.append((score, domain))
    selected = [domain for score, domain in sorted(scored_domains, key=lambda item: item[0], reverse=True)[:4]]

    dimensions = []
    used_sentences: set[str] = set()
    for index, domain in enumerate(selected, start=1):
        ranked = sorted(
            sentences,
            key=lambda s: score_sentence(s, domain["terms"], global_terms),
            reverse=True,
        )
        evidence = []
        for sentence in ranked:
            if sentence in used_sentences:
                continue
            if score_sentence(sentence, domain["terms"], global_terms) <= 0:
                continue
            evidence.append(sentence)
            used_sentences.add(sentence)
            if len(evidence) >= 4:
                break
        if not evidence:
            evidence = ranked[:3]

        topic_terms = []
        for term, _count in terms:
            term_lower = term.lower()
            if any(term_lower == domain_term.lower() or contains_term(term_lower, domain_term) for domain_term in domain["terms"]):
                topic_terms.append(term)
            if len(topic_terms) >= 4:
                break
        if len(topic_terms) < 4:
            topic_terms.extend([term for term, _count in terms if term not in topic_terms][: 4 - len(topic_terms)])

        concept_terms = []
        for concept in domain["terms"]:
            if contains_term(lower, concept):
                concept_terms.append(concept)
            if len(concept_terms) >= 5:
                break
        if len(concept_terms) < 3:
            concept_terms.extend([term for term, _count in terms if term not in concept_terms][: 5 - len(concept_terms)])

        dimensions.append(
            {
                "index": index,
                "name": domain["name"],
                "topics": topic_terms[:4],
                "concepts": concept_terms[:5],
                "category": domain["category"],
                "evidence": evidence[:4],
            }
        )
    return dimensions


def destination_for(source: Path) -> Path:
    if source.is_relative_to(WORKSPACE / "book-md"):
        relative = source.relative_to(WORKSPACE / "book-md")
        base = RESULT_ROOT / relative
    else:
        relative = source.relative_to(WORKSPACE / "papers-md")
        base = RESULT_ROOT / "papers-md" / relative

    name = base.name
    full = str(base)
    if len(full) > 245:
        digest = hashlib.sha1(str(source.relative_to(WORKSPACE)).encode("utf-8")).hexdigest()[:10]
        suffix = base.suffix
        stem = base.stem[:80]
        base = base.with_name(f"{stem}-{digest}{suffix}")
    return base


def analyze_file(source: Path, force: bool = False) -> Analysis | None:
    destination = destination_for(source)
    if destination.exists() and not force:
        try:
            existing_head = destination.read_text(encoding="utf-8", errors="ignore")[:500]
        except OSError:
            existing_head = ""
        if "自动生成说明：本文件依据 `Step6_Methodology_Report.md`" not in existing_head:
            return None

    raw = read_text(source)
    text = clean_markdown(raw)
    terms = top_terms(text)
    dimensions = build_dimensions(text, terms)
    nouns = extract_proper_nouns(text)
    paragraphs = [p for p in re.split(r"\n\s*\n", raw) if p.strip()]
    word_count = len(re.findall(r"[A-Za-z][A-Za-z'\-]*|[\u4e00-\u9fff]", text))
    return Analysis(
        source=source,
        destination=destination,
        title=extract_title(source, raw),
        char_count=len(text),
        word_count=word_count,
        paragraph_count=len(paragraphs),
        top_terms=terms,
        dimensions=dimensions,
        proper_nouns=nouns,
    )


def make_core_theme(analysis: Analysis) -> str:
    top = "、".join(term for term, _ in analysis.top_terms[:8]) or "文本主题"
    dimension_names = "；".join(d["name"].split("/")[0].strip() for d in analysis.dimensions[:3])
    return (
        f"本文档围绕“{analysis.title}”展开。根据词频、主题线索与章节标题综合判断，"
        f"其核心问题集中在 {top} 等关键词之间的关系，并可被组织为 {dimension_names} "
        "等互相关联的知识维度。以下分析依据 Step6 方法论中的 DIKW 路径生成：先做文本数据概览，"
        "再提取语义主题、知识点和专有名词，最后整理为可继续扩展的层级化知识体系。"
    )


def render_analysis(analysis: Analysis) -> str:
    source_rel = analysis.source.relative_to(WORKSPACE).as_posix()
    lines: list[str] = []
    lines.append(f"# 文本知识分析：{analysis.title}")
    lines.append("")
    lines.append(f"## Text Knowledge Analysis: {analysis.title}")
    lines.append("")
    lines.append("> 自动生成说明：本文件依据 `Step6_Methodology_Report.md` 的 DIKW 路径生成，属于批量结构化分析稿；它保留机器抽取的可追溯线索，适合后续人工精读、校订和扩展。")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("### 一、文本数据概览 / Data Profile")
    lines.append("")
    lines.append(f"- **来源文件 / Source**: `{source_rel}`")
    lines.append(f"- **字符数 / Characters**: {analysis.char_count}")
    lines.append(f"- **词/字单元数 / Word Units**: {analysis.word_count}")
    lines.append(f"- **段落数 / Paragraphs**: {analysis.paragraph_count}")
    lines.append("")
    lines.append("**高频关键词 / High-Frequency Terms**")
    lines.append("")
    lines.append("| 关键词 / Term | 频次 / Count |")
    lines.append("|---|---:|")
    for term, count in analysis.top_terms[:12]:
        lines.append(f"| {term.replace('|', '/')} | {count} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("### 二、核心主题 / Core Theme")
    lines.append("")
    lines.append(make_core_theme(analysis))
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("### 三、知识维度 / Knowledge Dimensions")
    lines.append("")
    for dimension in analysis.dimensions:
        lines.append(f"#### 维度 {dimension['index']}：{dimension['name']}")
        lines.append("")
        lines.append("**核心议题 / Topics**:")
        for topic in dimension["topics"]:
            lines.append(f"- {topic}")
        lines.append("")
        lines.append("**概念线索 / Conceptual Cues**:")
        lines.append("")
        lines.append("| 概念 / Concept | 分析性定义 / Analytical Definition |")
        lines.append("|---|---|")
        for concept in dimension["concepts"]:
            concept_label = concept.replace("|", "/")
            lines.append(
                f"| {concept_label} | 该概念在本文件中构成“{dimension['name'].split('/')[0].strip()}”维度的分析入口，用于连接文本中的关键词、论证对象与历史/社会语境。 |"
            )
        lines.append("")
        lines.append("**知识点 / Knowledge Points**:")
        lines.append("")
        lines.append("| 知识点摘要 / Knowledge Point Summary | 类别 / Category |")
        lines.append("|---|---|")
        for sentence in dimension["evidence"]:
            evidence = short_evidence(sentence)
            if evidence:
                lines.append(f"| {evidence} | {classify_sentence(sentence)} |")
        lines.append("")
        lines.append("---")
        lines.append("")
    lines.append("### 四、专有名词与术语 / Proper Nouns and Terms")
    lines.append("")
    lines.append("| 名称 / Name | 类型 / Type | 说明 / Note |")
    lines.append("|---|---|---|")
    if analysis.proper_nouns:
        for name, kind in analysis.proper_nouns:
            lines.append(f"| {name} | {kind} | 从文本中自动识别出的高频或显著实体，需在后续人工校订中确认其准确身份与学术作用。 |")
    else:
        lines.append("| 暂无稳定候选 | term / 术语 | 当前文本没有抽取到足够稳定的专有名词候选。 |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("### 五、层级化知识体系 / Hierarchical Knowledge System")
    lines.append("")
    lines.append(f"- **Level 1 核心研究主题**: {analysis.title}")
    lines.append("- **Level 2 核心维度**:")
    for dimension in analysis.dimensions:
        lines.append(f"  - {dimension['name']}")
    lines.append("- **Level 3 议题节点**:")
    for dimension in analysis.dimensions:
        topics = "；".join(dimension["topics"])
        lines.append(f"  - {dimension['name'].split('/')[0].strip()}: {topics}")
    lines.append("- **Level 4 知识要素**: 高频关键词、概念线索、知识点摘要与专有名词表共同构成本文件的初步知识要素库。")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("### 六、后续精读建议 / Refinement Notes")
    lines.append("")
    lines.append("- 对照原文复核自动抽取的概念定义，补充作者明确提出的理论命题。")
    lines.append("- 将表格中的知识点按“理论主张、历史事实、案例材料、方法论洞见”进一步细分。")
    lines.append("- 若本文属于书籍章节，可与同书其他章节的结果交叉合并，形成全书层级知识图谱。")
    lines.append("")
    return "\n".join(lines)


def write_analysis(analysis: Analysis) -> None:
    analysis.destination.parent.mkdir(parents=True, exist_ok=True)
    analysis.destination.write_text(render_analysis(analysis), encoding="utf-8")


def collect_sources() -> list[Path]:
    sources: list[Path] = []
    for root in SOURCE_ROOTS:
        if root.exists():
            sources.extend(sorted(root.rglob("*.md"), key=lambda p: p.as_posix().lower()))
    return sources


def write_summary(records: list[dict], skipped: int, force: bool) -> None:
    manifest_path = RESULT_ROOT / "_processing_manifest.json"
    summary_path = RESULT_ROOT / "_processing_summary.md"
    manifest = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "force": force,
        "generated_count": len(records),
        "skipped_existing_count": skipped,
        "records": records,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# result 批处理生成摘要",
        "",
        f"- 生成时间：{manifest['generated_at']}",
        f"- 本次新生成文件数：{len(records)}",
        f"- 因已存在而跳过文件数：{skipped}",
        f"- 是否覆盖已有结果：{force}",
        "",
        "## 输出说明",
        "",
        "本批处理依据 `Step6_Methodology_Report.md` 中的 DIKW 路径，对 `book-md/` 与 `papers-md/` 中的 Markdown 文档进行结构化文本分析，并将结果写入 `result/`。",
        "",
        "每个输出文件包含：数据概览、核心主题、知识维度、概念线索、知识点、专有名词与层级化知识体系。",
        "",
        "## 本次生成清单",
        "",
        "| 来源 / Source | 输出 / Output |",
        "|---|---|",
    ]
    for record in records[:200]:
        lines.append(f"| `{record['source']}` | `{record['destination']}` |")
    if len(records) > 200:
        lines.append(f"| ... | 其余 {len(records) - 200} 条见 `_processing_manifest.json` |")
    summary_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build structured knowledge analysis files under result/.")
    parser.add_argument("--force", action="store_true", help="Regenerate files even when result files already exist.")
    parser.add_argument("--limit", type=int, default=0, help="Only process the first N pending files.")
    args = parser.parse_args()

    sources = collect_sources()
    records: list[dict] = []
    skipped = 0
    pending = 0
    for source in sources:
        analysis = analyze_file(source, force=args.force)
        if analysis is None:
            skipped += 1
            continue
        pending += 1
        if args.limit and pending > args.limit:
            break
        write_analysis(analysis)
        records.append(
            {
                "source": analysis.source.relative_to(WORKSPACE).as_posix(),
                "destination": analysis.destination.relative_to(WORKSPACE).as_posix(),
                "title": analysis.title,
                "characters": analysis.char_count,
                "word_units": analysis.word_count,
            }
        )

    write_summary(records, skipped=skipped, force=args.force)
    print(f"Generated: {len(records)}")
    print(f"Skipped existing: {skipped}")
    print(f"Sources scanned: {len(sources)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
