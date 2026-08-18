"""有界 Grounding Context Builder。

不读取 run_dir，也不接受模型生成的文件路径。
通过 ArtifactCatalog.list_views() 取得公开目录，再通过 open() 打开指定 artifact_id。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Protocol

from app.chat.schemas import ChatCitation
from app.comparison.rendering import comparison_chat_projection
from app.comparison.schemas import ComparisonListResponse, ComparisonReport
from app.interaction.artifacts import ArtifactCatalog
from app.interaction.schemas import JobView
from app.interaction.service import InteractionService
from app.knowledge_base.schemas import KnowledgeQueryRequest
from app.research_browser.schemas import ResearchEvidencePack

TEXT_MEDIA_TYPES = {
    "application/json",
    "text/markdown",
    "text/plain",
}

ALLOWED_LAYERS = {
    "analysis",
    "planning",
    "execution",
    "debug",
    "reports",
}

# 已知高价值报告优先，但最终还会结合问题和内容打分。
PATH_PRIORITY = {
    "reports/final_report.md": 100,
    "reports/run_manifest.json": 90,
    "planning/experiment_plan.md": 85,
    "analysis/paper_summary.json": 80,
    "analysis/paper_code_mapping.md": 78,
    "analysis/repo_summary.md": 72,
    "planning/preflight_report.md": 70,
    "debug/debug_report.md": 68,
}


@dataclass(frozen=True)
class GroundingSource:
    citation: ChatCitation
    content: str
    score: int


@dataclass(frozen=True)
class GroundingBundle:
    job: JobView
    sources: list[GroundingSource]


class ResearchPackReaderPort(Protocol):
    def list_packs_for_job(
        self,
        *,
        job_id: str,
        limit: int,
    ) -> list[ResearchEvidencePack]:
        ...


class ComparisonReader(Protocol):
    def get(self, comparison_id: str) -> ComparisonReport:
        ...

    def list_for_job(
        self,
        job_id: str,
        *,
        limit: int = 100,
    ) -> ComparisonListResponse:
        ...


def _keywords(question: str) -> set[str]:
    """轻量中英文关键词，不声称替代语义检索。"""

    return {
        item.lower()
        for item in re.findall(
            r"[A-Za-z0-9_.-]{2,}|[\u4e00-\u9fff]{2,}",
            question,
        )
    }


def _score(text: str, keywords: set[str], base: int) -> int:
    lowered = text.lower()
    return base + sum(
        12 for keyword in keywords if keyword in lowered
    )


def _text_chunks(text: str, max_chars: int = 3500) -> list[str]:
    """按行构造有界 chunk，避免在 JSON/Markdown 中间无限截取。"""

    chunks: list[str] = []
    current: list[str] = []
    current_chars = 0
    for line in text.replace("\x00", "").splitlines():
        bounded = line[:max_chars]
        additional = len(bounded) + 1
        if current and current_chars + additional > max_chars:
            chunks.append("\n".join(current))
            current = []
            current_chars = 0
        current.append(bounded)
        current_chars += additional
    if current:
        chunks.append("\n".join(current))
    return chunks or [""]


class ChatContextBuilder:
    def __init__(
        self,
        *,
        interaction: InteractionService,
        artifact_catalog: ArtifactCatalog,
        artifacts_to_open: int,
        source_limit: int,
        artifact_max_bytes: int,
        total_context_chars: int,
        log_max_bytes: int,
        comparison_reader: ComparisonReader | None = None,
        comparison_limit: int = 3,
        comparison_max_chars: int = 12000,
        project_fact_retriever=None,
        knowledge_retriever=None,
        knowledge_max_entities: int = 12,
        knowledge_max_relations: int = 24,
        knowledge_max_chars: int = 16000,
        research_reader: ResearchPackReaderPort | None = None,
        research_pack_limit: int = 3,
        research_max_chars: int = 12000,
    ):
        self.interaction = interaction
        self.artifact_catalog = artifact_catalog
        self.artifacts_to_open = artifacts_to_open
        self.source_limit = source_limit
        self.artifact_max_bytes = artifact_max_bytes
        self.total_context_chars = total_context_chars
        self.log_max_bytes = log_max_bytes
        self.comparison_reader = comparison_reader
        self.comparison_limit = comparison_limit
        self.comparison_max_chars = comparison_max_chars
        self.project_fact_retriever = project_fact_retriever
        self.knowledge_retriever = knowledge_retriever
        self.knowledge_max_entities = knowledge_max_entities
        self.knowledge_max_relations = knowledge_max_relations
        self.knowledge_max_chars = knowledge_max_chars
        self.research_reader = research_reader
        self.research_pack_limit = research_pack_limit
        self.research_max_chars = research_max_chars

    def _artifact_sources(
        self,
        *,
        job_id: str,
        keywords: set[str],
    ) -> list[GroundingSource]:
        internal_job = self.interaction.job_service.get(job_id)
        views = [
            item
            for item in self.artifact_catalog.list_views(internal_job)
            if item.layer in ALLOWED_LAYERS
            and item.media_type in TEXT_MEDIA_TYPES
        ]

        # 先用公开 metadata 排序，限制真正打开的对象数量。
        views.sort(
            key=lambda item: _score(
                item.relative_path,
                keywords,
                PATH_PRIORITY.get(item.relative_path, 10),
            ),
            reverse=True,
        )

        sources: list[GroundingSource] = []
        for view in views[: self.artifacts_to_open]:
            opened = self.artifact_catalog.open(
                job=internal_job,
                artifact_id=view.artifact_id,
            )
            try:
                raw = opened.blob.body.read(
                    self.artifact_max_bytes + 1
                )
            finally:
                # 本地文件和 S3 StreamingBody 都必须关闭。
                opened.blob.body.close()

            truncated = len(raw) > self.artifact_max_bytes
            text = raw[: self.artifact_max_bytes].decode(
                "utf-8",
                errors="replace",
            )
            for index, chunk in enumerate(_text_chunks(text), start=1):
                if not chunk.strip():
                    continue
                locator = f"chunk {index}"
                if truncated:
                    locator += ", bounded preview"
                citation_id = (
                    f"artifact:{view.artifact_id}:{index}"
                )
                sources.append(
                    GroundingSource(
                        citation=ChatCitation(
                            citation_id=citation_id,
                            source_type="artifact",
                            label=view.relative_path,
                            artifact_id=view.artifact_id,
                            relative_path=view.relative_path,
                            artifact_sha256=view.sha256,
                            locator=locator,
                        ),
                        content=chunk,
                        score=_score(
                            f"{view.relative_path}\n{chunk}",
                            keywords,
                            PATH_PRIORITY.get(
                                view.relative_path,
                                10,
                            ),
                        ),
                    )
                )
        return sources

    def _comparison_sources(
        self,
        *,
        job_id: str,
        keywords: set[str],
    ) -> list[GroundingSource]:
        if self.comparison_reader is None:
            return []

        page = self.comparison_reader.list_for_job(
            job_id,
            limit=self.comparison_limit,
        )
        sources: list[GroundingSource] = []
        used_chars = 0
        for item in page.items:
            report = self.comparison_reader.get(item.comparison_id)
            content = comparison_chat_projection(report)
            if used_chars + len(content) > self.comparison_max_chars:
                continue
            used_chars += len(content)

            searchable = (
                f"比较 comparison diff 差异 对比 "
                f"{report.comparison_id} {report.base.job_id} "
                f"{report.target.job_id} {content}"
            )
            sources.append(
                GroundingSource(
                    citation=ChatCitation(
                        citation_id=f"comparison:{report.comparison_id}",
                        source_type="comparison",
                        label=(
                            f"Run comparison: {report.base.job_id} "
                            f"-> {report.target.job_id}"
                        ),
                        locator=f"comparator {report.comparator_version}",
                        comparison_id=report.comparison_id,
                        comparison_hash=report.comparison_hash,
                        base_job_id=report.base.job_id,
                        target_job_id=report.target.job_id,
                    ),
                    content=content,
                    # 用户问“比较/差异”时通常高于普通 Artifact，但低于 job:current。
                    score=_score(searchable, keywords, 92),
                )
            )
        return sources

    def _project_fact_sources(
        self,
        *,
        job_id: str,
        keywords: set[str],
    ) -> list[GroundingSource]:
        if self.project_fact_retriever is None:
            return []
        pack = self.project_fact_retriever.for_job(job_id)
        if pack is None:
            return []

        sources = []
        for item in pack.items:
            content = json.dumps(
                {
                    "category": item.category,
                    "key": item.key,
                    "value": item.value.model_dump(mode="json"),
                    "authority": item.authority,
                    "expires_at": item.expires_at,
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            sources.append(
                GroundingSource(
                    citation=ChatCitation(
                        citation_id=f"project_fact:{item.fact_id}",
                        source_type="project_fact",
                        label=f"Project fact: {item.category}/{item.key}",
                        locator=f"record hash {item.fact_hash[:12]}",
                        project_id=pack.project_id,
                        project_fact_id=item.fact_id,
                        project_fact_hash=item.fact_hash,
                    ),
                    content=content,
                    score=_score(content, keywords, 88),
                )
            )
        return sources

    def _knowledge_sources(
        self,
        *,
        question: str,
        keywords: set[str],
    ) -> list[GroundingSource]:
        if self.knowledge_retriever is None:
            return []
        pack = self.knowledge_retriever.query(
            KnowledgeQueryRequest(
                query=question,
                max_entities=self.knowledge_max_entities,
                max_relations=self.knowledge_max_relations,
                max_depth=1,
                include_candidates=False,
            )
        )
        evidence_map = {
            item.subject_id: item.evidence_ref_ids
            for item in pack.subject_evidence
        }
        sources: list[GroundingSource] = []
        used_chars = 0

        for hit in pack.entities:
            entity = hit.entity
            connected_records = [
                relation
                for relation in pack.authoritative_relations
                if entity.entity_id
                in {
                    relation.source_entity_id,
                    relation.target_entity_id,
                }
            ]
            refs = sorted(
                set(evidence_map.get(entity.entity_id, []))
                | {
                    ref_id
                    for relation in connected_records
                    for ref_id in evidence_map.get(
                        relation.relation_id,
                        [],
                    )
                }
            )
            if not refs:
                continue
            connected = [
                relation.model_dump(mode="json")
                for relation in connected_records
            ]
            content = json.dumps(
                {
                    "entity": entity.model_dump(mode="json"),
                    "authoritative_relations": connected,
                    "retrieval_score": hit.score,
                    "matched_terms": hit.matched_terms,
                    "pack_truncated": pack.truncated,
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            if used_chars + len(content) > self.knowledge_max_chars:
                break
            used_chars += len(content)
            sources.append(
                GroundingSource(
                    citation=ChatCitation(
                        citation_id=f"knowledge:{entity.entity_id}",
                        source_type="knowledge",
                        label=f"Knowledge {entity.kind}: {entity.display_name}",
                        locator=f"pack {pack.pack_hash[:12]}",
                        knowledge_pack_hash=pack.pack_hash,
                        knowledge_subject_id=entity.entity_id,
                        knowledge_subject_hash=entity.record_hash,
                        knowledge_evidence_ref_ids=refs,
                    ),
                    content=content,
                    score=_score(content, keywords, 82),
                )
            )
        return sources

    def _research_sources(
        self,
        *,
        job_id: str,
        keywords: set[str],
    ) -> list[GroundingSource]:
        if self.research_reader is None:
            return []

        sources: list[GroundingSource] = []
        used_chars = 0
        packs = self.research_reader.list_packs_for_job(
            job_id=job_id,
            limit=self.research_pack_limit,
        )
        for pack in packs:
            # Reader 必须已校验 pack_hash；这里再校验每条 citation 的局部身份。
            snapshots = {
                item.snapshot_id: item
                for item in pack.snapshots
            }
            for citation in pack.report.citations:
                snapshot = snapshots.get(citation.snapshot_id)
                if snapshot is None:
                    continue
                if citation.snapshot_body_sha256 != snapshot.body_sha256:
                    continue
                if used_chars + len(citation.excerpt) > self.research_max_chars:
                    continue

                sources.append(
                    GroundingSource(
                        citation=ChatCitation(
                            citation_id=f"web:{citation.citation_id}",
                            source_type="web",
                            label=citation.label,
                            locator=citation.locator,
                            research_pack_id=pack.pack_id,
                            research_pack_hash=pack.pack_sha256,
                            research_snapshot_id=snapshot.snapshot_id,
                            research_snapshot_sha256=snapshot.body_sha256,
                            research_citation_id=citation.citation_id,
                            research_excerpt_sha256=citation.excerpt_sha256,
                            canonical_url=snapshot.canonical_url,
                        ),
                        content=(
                            "UNTRUSTED_WEB_EVIDENCE\n"
                            f"title: {citation.label}\n"
                            f"url: {snapshot.canonical_url}\n"
                            f"excerpt: {citation.excerpt}"
                        ),
                        score=_score(citation.excerpt, keywords, 25),
                    )
                )
                used_chars += len(citation.excerpt)
        return sources

    def _job_source(
        self,
        *,
        job: JobView,
        keywords: set[str],
    ) -> GroundingSource:
        job_content = json.dumps(
            {
                "status": job.status,
                "attempt_count": job.attempt_count,
                "max_attempts": job.max_attempts,
                "input": job.input.model_dump(),
                "result": (
                    job.result.model_dump()
                    if job.result is not None
                    else None
                ),
                "error": job.error,
            },
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        )
        return GroundingSource(
            citation=ChatCitation(
                citation_id="job:current",
                source_type="job",
                label="Current job state",
                locator=f"version {job.version}",
            ),
            content=job_content,
            score=_score(job_content, keywords, 120),
        )

    def build_job_only(
        self,
        *,
        job_id: str,
        question: str,
    ) -> GroundingBundle:
        job = self.interaction.get_job(job_id)
        source = self._job_source(
            job=job,
            keywords=_keywords(question),
        )
        return GroundingBundle(job=job, sources=[source])

    def build(
        self,
        *,
        job_id: str,
        question: str,
    ) -> GroundingBundle:
        job = self.interaction.get_job(job_id)
        keywords = _keywords(question)

        # Job 公开投影始终进入上下文，但不包含 run_dir/claim_token。
        candidates = [
            self._job_source(
                job=job,
                keywords=keywords,
            )
        ]

        # events_after 是正向 cursor；分页到当前尾部后再保留最后 20 个，
        # 不能简单读取第一页并误称"最近事件"。总计最多扫描 1000 条。
        events = []
        cursor = 0
        for _ in range(10):
            page = self.interaction.events_after(
                job_id=job_id,
                after_event_id=cursor,
                limit=100,
            )
            events.extend(page)
            if len(page) < 100:
                break
            cursor = page[-1].event_id
        events = events[-20:]
        for event in events:
            event_content = json.dumps(
                {
                    "event_type": event.event_type,
                    "created_at": event.created_at,
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )
            candidates.append(
                GroundingSource(
                    citation=ChatCitation(
                        citation_id=f"event:{event.event_id}",
                        source_type="event",
                        label=event.event_type,
                        event_id=event.event_id,
                        locator=event.created_at,
                    ),
                    content=event_content,
                    score=_score(event_content, keywords, 20),
                )
            )

        log = self.interaction.tail_log(
            job_id=job_id,
            lines=100,
            max_bytes=self.log_max_bytes,
        )
        if log.content.strip():
            log_base = (
                75
                if keywords.intersection(
                    {"error", "failed", "failure", "log", "报错", "失败", "日志"}
                )
                else 8
            )
            candidates.append(
                GroundingSource(
                    citation=ChatCitation(
                        citation_id="log:tail",
                        source_type="log",
                        label=log.relative_path or "execution log",
                        relative_path=log.relative_path,
                        locator="last 100 lines",
                    ),
                    content=log.content,
                    score=_score(log.content, keywords, log_base),
                )
            )

        candidates.extend(
            self._artifact_sources(
                job_id=job_id,
                keywords=keywords,
            )
        )
        candidates.extend(
            self._comparison_sources(
                job_id=job_id,
                keywords=keywords,
            )
        )
        candidates.extend(
            self._project_fact_sources(
                job_id=job_id,
                keywords=keywords,
            )
        )
        candidates.extend(
            self._knowledge_sources(
                question=question,
                keywords=keywords,
            )
        )
        candidates.extend(
            self._research_sources(
                job_id=job_id,
                keywords=keywords,
            )
        )

        # job:current 永远保留，其余来源按相关性和总字符预算选择。
        job_source = candidates[0]
        ranked = sorted(
            candidates[1:],
            key=lambda item: item.score,
            reverse=True,
        )
        selected = [job_source]
        used_chars = len(job_source.content)
        for source in ranked:
            if len(selected) >= self.source_limit:
                break
            if used_chars + len(source.content) > self.total_context_chars:
                continue
            selected.append(source)
            used_chars += len(source.content)

        return GroundingBundle(job=job, sources=selected)
