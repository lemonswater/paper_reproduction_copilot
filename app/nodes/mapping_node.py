import json
from pathlib import Path

from app.config import settings
from app.model import get_chat_model
from app.prompts.mapping_prompt import MAPPING_PROMPT
from app.schemas import ModuleMapping


def mapping_node(state: dict) -> dict:
    modules = state.get("method_modules", [])
    search_results = state.get("code_search_results", {})
    if not modules or not search_results:
        return {"error": "mapping requires method_modules and code_search_results"}
    
    llm = get_chat_model(temperature=0)
    structured_llm = llm.with_structured_output(ModuleMapping)

    mappings: list[dict] = []
    for module in modules:
        module_name = module["name"]
        result = search_results.get(module_name, {})
        mapping: ModuleMapping = structured_llm.invoke(
            MAPPING_PROMPT.format(
                module = json.dumps(module, ensure_ascii=False, indent=2),
                search_results = json.dumps(result.get("matches", []), ensure_ascii=False, indent=2),
                code_slices = json.dumps(result.get("code_slices", []), ensure_ascii=False, indent=2)
            )
        )
        mappings.append(mapping.model_dump())

    settings.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = settings.output_dir / "paper_code_mapping.json"
    md_path = settings.output_dir / "paper_code_mapping.md"

    json_path.write_text(json.dumps(mappings, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_render_mapping_markdown(mappings), encoding="utf-8")

    return {
        "paper_code_mapping": mappings,
        "output_files":[
            *state.get("output_files", []),
            str(json_path),
            str(md_path)
        ]
    }

def _render_mapping_markdown(mappings: list[dict]) -> str:
    lines = ["# Paper-Code Mapping", ""]
    for mapping in mappings:
        lines.append(f"## {mapping['module_name']}")
        lines.append("")
        unresolved = mapping.get("unresolved_questions", [])
        if unresolved:
            lines.append("### Unresolved Questions")
            for item in unresolved:
                lines.append(f"- {item}")
            lines.append("")

        lines.append("| Candidate File | Symbols | Confidence | Reason |")
        lines.append("|---|---|---|---|")
        for candidate in mapping.get("candidates", []):
            symbols = ", ".join(candidate.get("symbols", []))
            reason = candidate.get("reason", "").replace("\n", " ")
            lines.append(
                f"| `{candidate['file_path']}` | {symbols} | "
                f"{candidate.get('confidence', 'medium')} | {reason} |"
            )
        lines.append("")
    return "\n".join(lines)