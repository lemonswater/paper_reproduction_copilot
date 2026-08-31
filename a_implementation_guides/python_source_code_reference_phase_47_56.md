# Python 源码函数参考：Phase 47-56

> 自动同步日期：2026-08-19
> 覆盖文件：183；函数/方法：1144。
> 本文由当前 Python AST 生成；伪代码保留控制流和失败边界，但会把相邻语句合并为通俗的逻辑步骤。
> 阶段归类按文件的主要职责完成；跨阶段持续修改的文件只进入一个主分册，源码行号是最终依据。

## 阅读约定

- 伪代码按“一段逻辑做什么”组织；连续初始化、校验或字段更新会合并成一句或一段。
- 简单的 `if`、`for` 和 `with` 会直接概括成完整句子；有嵌套分支或提前返回时才使用缩进展开。
- 变量名只用来标识数据保存在哪里；文字是为了解释意图，不是可直接运行的 Python 代码。
- 输入表中的路径、ID、Hash、命令、状态和领域记录分别表示不同的业务对象，不能互换。
- “抛出异常”对应真实 `raise`，调用方不会收到正常返回值。
- Hash/fingerprint 表示内容身份，不是加密后的业务正文，也不是授权凭证。
- Command 表示命令文本或结构化命令；只有 Executor 路径才可能真正执行。
- Protocol 中只有 `...` 的函数会显示为“接口占位（无具体实现）”，它声明契约而不是具体实现。

## 文件索引

- [`app/api/knowledge_routes.py`](#app-api-knowledge-routes-py)：7 个函数/方法
- [`app/api/mcp_gateway_routes.py`](#app-api-mcp-gateway-routes-py)：3 个函数/方法
- [`app/api/model_routing_routes.py`](#app-api-model-routing-routes-py)：3 个函数/方法
- [`app/api/research_browser_routes.py`](#app-api-research-browser-routes-py)：8 个函数/方法
- [`app/knowledge_base/evaluation.py`](#app-knowledge-base-evaluation-py)：2 个函数/方法
- [`app/knowledge_base/factory.py`](#app-knowledge-base-factory-py)：2 个函数/方法
- [`app/knowledge_base/identity.py`](#app-knowledge-base-identity-py)：18 个函数/方法
- [`app/knowledge_base/ports.py`](#app-knowledge-base-ports-py)：14 个函数/方法
- [`app/knowledge_base/projector.py`](#app-knowledge-base-projector-py)：12 个函数/方法
- [`app/knowledge_base/repository.py`](#app-knowledge-base-repository-py)：27 个函数/方法
- [`app/knowledge_base/retrieval.py`](#app-knowledge-base-retrieval-py)：4 个函数/方法
- [`app/knowledge_base/schemas.py`](#app-knowledge-base-schemas-py)：7 个函数/方法
- [`app/knowledge_base/service.py`](#app-knowledge-base-service-py)：6 个函数/方法
- [`app/knowledge_base/source_reader.py`](#app-knowledge-base-source-reader-py)：7 个函数/方法
- [`app/mcp_contracts/baseline.py`](#app-mcp-contracts-baseline-py)：8 个函数/方法
- [`app/mcp_contracts/commands.py`](#app-mcp-contracts-commands-py)：9 个函数/方法
- [`app/mcp_contracts/evaluator.py`](#app-mcp-contracts-evaluator-py)：3 个函数/方法
- [`app/mcp_contracts/identity.py`](#app-mcp-contracts-identity-py)：10 个函数/方法
- [`app/mcp_contracts/profiles.py`](#app-mcp-contracts-profiles-py)：2 个函数/方法
- [`app/mcp_contracts/readiness.py`](#app-mcp-contracts-readiness-py)：6 个函数/方法
- [`app/mcp_contracts/schemas.py`](#app-mcp-contracts-schemas-py)：2 个函数/方法
- [`app/mcp_contracts/snapshot.py`](#app-mcp-contracts-snapshot-py)：17 个函数/方法
- [`app/mcp_export/asgi.py`](#app-mcp-export-asgi-py)：1 个函数/方法
- [`app/mcp_export/audit.py`](#app-mcp-export-audit-py)：7 个函数/方法
- [`app/mcp_export/auth.py`](#app-mcp-export-auth-py)：3 个函数/方法
- [`app/mcp_export/call_executor.py`](#app-mcp-export-call-executor-py)：9 个函数/方法
- [`app/mcp_export/factory.py`](#app-mcp-export-factory-py)：4 个函数/方法
- [`app/mcp_export/identity.py`](#app-mcp-export-identity-py)：6 个函数/方法
- [`app/mcp_export/rate_limit.py`](#app-mcp-export-rate-limit-py)：2 个函数/方法
- [`app/mcp_export/schemas.py`](#app-mcp-export-schemas-py)：4 个函数/方法
- [`app/mcp_export/server.py`](#app-mcp-export-server-py)：12 个函数/方法
- [`app/mcp_export/service.py`](#app-mcp-export-service-py)：15 个函数/方法
- [`app/mcp_gateway/client.py`](#app-mcp-gateway-client-py)：12 个函数/方法
- [`app/mcp_gateway/factory.py`](#app-mcp-gateway-factory-py)：4 个函数/方法
- [`app/mcp_gateway/gateway.py`](#app-mcp-gateway-gateway-py)：5 个函数/方法
- [`app/mcp_gateway/identity.py`](#app-mcp-gateway-identity-py)：9 个函数/方法
- [`app/mcp_gateway/policy.py`](#app-mcp-gateway-policy-py)：5 个函数/方法
- [`app/mcp_gateway/ports.py`](#app-mcp-gateway-ports-py)：2 个函数/方法
- [`app/mcp_gateway/repository.py`](#app-mcp-gateway-repository-py)：10 个函数/方法
- [`app/mcp_gateway/schemas.py`](#app-mcp-gateway-schemas-py)：6 个函数/方法
- [`app/mcp_gateway/tool_adapter.py`](#app-mcp-gateway-tool-adapter-py)：6 个函数/方法
- [`app/mcp_operations/commands.py`](#app-mcp-operations-commands-py)：9 个函数/方法
- [`app/mcp_operations/identity.py`](#app-mcp-operations-identity-py)：3 个函数/方法
- [`app/mcp_operations/policy.py`](#app-mcp-operations-policy-py)：2 个函数/方法
- [`app/mcp_operations/probe.py`](#app-mcp-operations-probe-py)：11 个函数/方法
- [`app/mcp_operations/repository.py`](#app-mcp-operations-repository-py)：5 个函数/方法
- [`app/mcp_operations/schemas.py`](#app-mcp-operations-schemas-py)：2 个函数/方法
- [`app/mcp_operations/upgrade.py`](#app-mcp-operations-upgrade-py)：3 个函数/方法
- [`app/model_routing/catalog.py`](#app-model-routing-catalog-py)：7 个函数/方法
- [`app/model_routing/embedding.py`](#app-model-routing-embedding-py)：5 个函数/方法
- [`app/model_routing/errors.py`](#app-model-routing-errors-py)：1 个函数/方法
- [`app/model_routing/evaluation.py`](#app-model-routing-evaluation-py)：2 个函数/方法
- [`app/model_routing/factory.py`](#app-model-routing-factory-py)：3 个函数/方法
- [`app/model_routing/gateway.py`](#app-model-routing-gateway-py)：21 个函数/方法
- [`app/model_routing/identity.py`](#app-model-routing-identity-py)：11 个函数/方法
- [`app/model_routing/policy.py`](#app-model-routing-policy-py)：3 个函数/方法
- [`app/model_routing/provider.py`](#app-model-routing-provider-py)：5 个函数/方法
- [`app/model_routing/repository.py`](#app-model-routing-repository-py)：15 个函数/方法
- [`app/model_routing/schemas.py`](#app-model-routing-schemas-py)：7 个函数/方法
- [`app/model_routing/usage.py`](#app-model-routing-usage-py)：4 个函数/方法
- [`app/prompts/tool_calling_prompt.py`](#app-prompts-tool-calling-prompt-py)：1 个函数/方法
- [`app/research_browser/catalog.py`](#app-research-browser-catalog-py)：2 个函数/方法
- [`app/research_browser/collector.py`](#app-research-browser-collector-py)：5 个函数/方法
- [`app/research_browser/doctor.py`](#app-research-browser-doctor-py)：1 个函数/方法
- [`app/research_browser/extractors.py`](#app-research-browser-extractors-py)：11 个函数/方法
- [`app/research_browser/factory.py`](#app-research-browser-factory-py)：1 个函数/方法
- [`app/research_browser/fetcher.py`](#app-research-browser-fetcher-py)：12 个函数/方法
- [`app/research_browser/identity.py`](#app-research-browser-identity-py)：10 个函数/方法
- [`app/research_browser/repository.py`](#app-research-browser-repository-py)：20 个函数/方法
- [`app/research_browser/schemas.py`](#app-research-browser-schemas-py)：13 个函数/方法
- [`app/research_browser/search.py`](#app-research-browser-search-py)：5 个函数/方法
- [`app/research_browser/service.py`](#app-research-browser-service-py)：11 个函数/方法
- [`app/research_browser/synthesis.py`](#app-research-browser-synthesis-py)：2 个函数/方法
- [`app/research_browser/tooling.py`](#app-research-browser-tooling-py)：3 个函数/方法
- [`app/retrieval/policy.py`](#app-retrieval-policy-py)：7 个函数/方法
- [`app/retrieval/policy_eval.py`](#app-retrieval-policy-eval-py)：8 个函数/方法
- [`app/retrieval/policy_schemas.py`](#app-retrieval-policy-schemas-py)：3 个函数/方法
- [`app/skills/builtin/cuda_build_diagnosis.py`](#app-skills-builtin-cuda-build-diagnosis-py)：9 个函数/方法
- [`app/skills/builtin/restricted_web_research.py`](#app-skills-builtin-restricted-web-research-py)：1 个函数/方法
- [`app/skills/catalog.py`](#app-skills-catalog-py)：3 个函数/方法
- [`app/skills/loader.py`](#app-skills-loader-py)：6 个函数/方法
- [`app/skills/registry.py`](#app-skills-registry-py)：15 个函数/方法
- [`app/skills/runtime.py`](#app-skills-runtime-py)：4 个函数/方法
- [`app/skills/schemas.py`](#app-skills-schemas-py)：3 个函数/方法
- [`app/tool_calling/catalog.py`](#app-tool-calling-catalog-py)：4 个函数/方法
- [`app/tool_calling/evidence_tools.py`](#app-tool-calling-evidence-tools-py)：7 个函数/方法
- [`app/tool_calling/factory.py`](#app-tool-calling-factory-py)：2 个函数/方法
- [`app/tool_calling/identity.py`](#app-tool-calling-identity-py)：7 个函数/方法
- [`app/tool_calling/loop.py`](#app-tool-calling-loop-py)：8 个函数/方法
- [`app/tool_calling/model_adapter.py`](#app-tool-calling-model-adapter-py)：3 个函数/方法
- [`app/tool_calling/schemas.py`](#app-tool-calling-schemas-py)：8 个函数/方法
- [`create_mcp_phase1.py`](#create-mcp-phase1-py)：1 个函数/方法
- [`tests/fakes/mcp_readonly_server.py`](#tests-fakes-mcp-readonly-server-py)：2 个函数/方法
- [`tests/helpers/knowledge_base.py`](#tests-helpers-knowledge-base-py)：10 个函数/方法
- [`tests/helpers/model_routing.py`](#tests-helpers-model-routing-py)：17 个函数/方法
- [`tests/mcp_contract_helpers.py`](#tests-mcp-contract-helpers-py)：2 个函数/方法
- [`tests/mcp_export_helpers.py`](#tests-mcp-export-helpers-py)：9 个函数/方法
- [`tests/mcp_gateway_helpers.py`](#tests-mcp-gateway-helpers-py)：7 个函数/方法
- [`tests/research_browser_helpers.py`](#tests-research-browser-helpers-py)：9 个函数/方法
- [`tests/skill_test_helpers.py`](#tests-skill-test-helpers-py)：2 个函数/方法
- [`tests/test_cuda_build_diagnosis_skill.py`](#tests-test-cuda-build-diagnosis-skill-py)：3 个函数/方法
- [`tests/test_knowledge_authority_boundary.py`](#tests-test-knowledge-authority-boundary-py)：1 个函数/方法
- [`tests/test_knowledge_chat_integration.py`](#tests-test-knowledge-chat-integration-py)：2 个函数/方法
- [`tests/test_knowledge_golden_eval.py`](#tests-test-knowledge-golden-eval-py)：1 个函数/方法
- [`tests/test_knowledge_identity.py`](#tests-test-knowledge-identity-py)：3 个函数/方法
- [`tests/test_knowledge_projector.py`](#tests-test-knowledge-projector-py)：1 个函数/方法
- [`tests/test_knowledge_relation_review.py`](#tests-test-knowledge-relation-review-py)：2 个函数/方法
- [`tests/test_knowledge_repository.py`](#tests-test-knowledge-repository-py)：3 个函数/方法
- [`tests/test_knowledge_retention.py`](#tests-test-knowledge-retention-py)：1 个函数/方法
- [`tests/test_knowledge_retrieval.py`](#tests-test-knowledge-retrieval-py)：1 个函数/方法
- [`tests/test_knowledge_schemas.py`](#tests-test-knowledge-schemas-py)：2 个函数/方法
- [`tests/test_knowledge_source_reader.py`](#tests-test-knowledge-source-reader-py)：4 个函数/方法
- [`tests/test_mcp_contract_authority.py`](#tests-test-mcp-contract-authority-py)：3 个函数/方法
- [`tests/test_mcp_contract_baseline.py`](#tests-test-mcp-contract-baseline-py)：6 个函数/方法
- [`tests/test_mcp_contract_evaluator.py`](#tests-test-mcp-contract-evaluator-py)：4 个函数/方法
- [`tests/test_mcp_contract_golden.py`](#tests-test-mcp-contract-golden-py)：2 个函数/方法
- [`tests/test_mcp_contract_profiles.py`](#tests-test-mcp-contract-profiles-py)：4 个函数/方法
- [`tests/test_mcp_contract_readiness.py`](#tests-test-mcp-contract-readiness-py)：5 个函数/方法
- [`tests/test_mcp_contract_schemas.py`](#tests-test-mcp-contract-schemas-py)：3 个函数/方法
- [`tests/test_mcp_contract_snapshot.py`](#tests-test-mcp-contract-snapshot-py)：4 个函数/方法
- [`tests/test_mcp_export_audit.py`](#tests-test-mcp-export-audit-py)：3 个函数/方法
- [`tests/test_mcp_export_auth.py`](#tests-test-mcp-export-auth-py)：7 个函数/方法
- [`tests/test_mcp_export_authority.py`](#tests-test-mcp-export-authority-py)：4 个函数/方法
- [`tests/test_mcp_export_call_executor.py`](#tests-test-mcp-export-call-executor-py)：10 个函数/方法
- [`tests/test_mcp_export_rate_limit.py`](#tests-test-mcp-export-rate-limit-py)：1 个函数/方法
- [`tests/test_mcp_export_retention.py`](#tests-test-mcp-export-retention-py)：1 个函数/方法
- [`tests/test_mcp_export_schemas.py`](#tests-test-mcp-export-schemas-py)：4 个函数/方法
- [`tests/test_mcp_export_server.py`](#tests-test-mcp-export-server-py)：7 个函数/方法
- [`tests/test_mcp_export_service.py`](#tests-test-mcp-export-service-py)：5 个函数/方法
- [`tests/test_mcp_gateway_api.py`](#tests-test-mcp-gateway-api-py)：7 个函数/方法
- [`tests/test_mcp_gateway_authority.py`](#tests-test-mcp-gateway-authority-py)：2 个函数/方法
- [`tests/test_mcp_gateway_chat_integration.py`](#tests-test-mcp-gateway-chat-integration-py)：2 个函数/方法
- [`tests/test_mcp_gateway_client.py`](#tests-test-mcp-gateway-client-py)：2 个函数/方法
- [`tests/test_mcp_gateway_gateway.py`](#tests-test-mcp-gateway-gateway-py)：3 个函数/方法
- [`tests/test_mcp_gateway_policy.py`](#tests-test-mcp-gateway-policy-py)：2 个函数/方法
- [`tests/test_mcp_gateway_repository.py`](#tests-test-mcp-gateway-repository-py)：5 个函数/方法
- [`tests/test_mcp_gateway_schemas.py`](#tests-test-mcp-gateway-schemas-py)：3 个函数/方法
- [`tests/test_mcp_gateway_tool_integration.py`](#tests-test-mcp-gateway-tool-integration-py)：3 个函数/方法
- [`tests/test_mcp_runtime_authority.py`](#tests-test-mcp-runtime-authority-py)：2 个函数/方法
- [`tests/test_mcp_runtime_http.py`](#tests-test-mcp-runtime-http-py)：4 个函数/方法
- [`tests/test_mcp_runtime_policy.py`](#tests-test-mcp-runtime-policy-py)：3 个函数/方法
- [`tests/test_mcp_runtime_probe.py`](#tests-test-mcp-runtime-probe-py)：12 个函数/方法
- [`tests/test_mcp_runtime_repository.py`](#tests-test-mcp-runtime-repository-py)：4 个函数/方法
- [`tests/test_mcp_runtime_upgrade.py`](#tests-test-mcp-runtime-upgrade-py)：3 个函数/方法
- [`tests/test_model_routing_api.py`](#tests-test-model-routing-api-py)：23 个函数/方法
- [`tests/test_model_routing_authority_boundary.py`](#tests-test-model-routing-authority-boundary-py)：7 个函数/方法
- [`tests/test_model_routing_catalog.py`](#tests-test-model-routing-catalog-py)：17 个函数/方法
- [`tests/test_model_routing_eval.py`](#tests-test-model-routing-eval-py)：9 个函数/方法
- [`tests/test_model_routing_schemas.py`](#tests-test-model-routing-schemas-py)：21 个函数/方法
- [`tests/test_research_browser_api.py`](#tests-test-research-browser-api-py)：4 个函数/方法
- [`tests/test_research_browser_authority.py`](#tests-test-research-browser-authority-py)：6 个函数/方法
- [`tests/test_research_browser_catalog.py`](#tests-test-research-browser-catalog-py)：8 个函数/方法
- [`tests/test_research_browser_chat.py`](#tests-test-research-browser-chat-py)：6 个函数/方法
- [`tests/test_research_browser_collector.py`](#tests-test-research-browser-collector-py)：13 个函数/方法
- [`tests/test_research_browser_extractors.py`](#tests-test-research-browser-extractors-py)：12 个函数/方法
- [`tests/test_research_browser_fetcher.py`](#tests-test-research-browser-fetcher-py)：15 个函数/方法
- [`tests/test_research_browser_golden.py`](#tests-test-research-browser-golden-py)：9 个函数/方法
- [`tests/test_research_browser_identity.py`](#tests-test-research-browser-identity-py)：10 个函数/方法
- [`tests/test_research_browser_repository.py`](#tests-test-research-browser-repository-py)：14 个函数/方法
- [`tests/test_research_browser_resource_bridge.py`](#tests-test-research-browser-resource-bridge-py)：13 个函数/方法
- [`tests/test_research_browser_schemas.py`](#tests-test-research-browser-schemas-py)：8 个函数/方法
- [`tests/test_research_browser_skill.py`](#tests-test-research-browser-skill-py)：3 个函数/方法
- [`tests/test_research_browser_synthesis.py`](#tests-test-research-browser-synthesis-py)：13 个函数/方法
- [`tests/test_retrieval_policy_eval.py`](#tests-test-retrieval-policy-eval-py)：2 个函数/方法
- [`tests/test_retrieval_policy_integration.py`](#tests-test-retrieval-policy-integration-py)：2 个函数/方法
- [`tests/test_retrieval_policy_router.py`](#tests-test-retrieval-policy-router-py)：4 个函数/方法
- [`tests/test_retrieval_policy_schemas.py`](#tests-test-retrieval-policy-schemas-py)：3 个函数/方法
- [`tests/test_semantic_retrieval_eval.py`](#tests-test-semantic-retrieval-eval-py)：3 个函数/方法
- [`tests/test_skill_authority_boundary.py`](#tests-test-skill-authority-boundary-py)：2 个函数/方法
- [`tests/test_skill_golden_eval.py`](#tests-test-skill-golden-eval-py)：2 个函数/方法
- [`tests/test_skill_import_boundary.py`](#tests-test-skill-import-boundary-py)：3 个函数/方法
- [`tests/test_skill_log_debug_integration.py`](#tests-test-skill-log-debug-integration-py)：3 个函数/方法
- [`tests/test_skill_manifest_loader.py`](#tests-test-skill-manifest-loader-py)：7 个函数/方法
- [`tests/test_skill_registry.py`](#tests-test-skill-registry-py)：6 个函数/方法
- [`tests/test_skill_runtime.py`](#tests-test-skill-runtime-py)：6 个函数/方法
- [`tests/test_tool_calling_authority.py`](#tests-test-tool-calling-authority-py)：4 个函数/方法
- [`tests/test_tool_calling_catalog.py`](#tests-test-tool-calling-catalog-py)：10 个函数/方法
- [`tests/test_tool_calling_chat_integration.py`](#tests-test-tool-calling-chat-integration-py)：4 个函数/方法
- [`tests/test_tool_calling_evidence_tools.py`](#tests-test-tool-calling-evidence-tools-py)：8 个函数/方法
- [`tests/test_tool_calling_loop.py`](#tests-test-tool-calling-loop-py)：9 个函数/方法
- [`tests/test_tool_calling_model_gateway.py`](#tests-test-tool-calling-model-gateway-py)：7 个函数/方法
- [`tests/test_tool_calling_schemas.py`](#tests-test-tool-calling-schemas-py)：14 个函数/方法
- [`tests/tool_calling_helpers.py`](#tests-tool-calling-helpers-py)：8 个函数/方法

## 逐函数参考

### `app/api/knowledge_routes.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `knowledge_service`

- **源码**：`app/api/knowledge_routes.py:31`
- **签名**：`def knowledge_service(request: Request) -> KnowledgeService`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收业务请求，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `KnowledgeService` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`KnowledgeService`
- **语义**：返回 `KnowledgeService` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `getattr` 完成该函数的一项辅助处理，并把结果记为 领域服务对象。
如果领域服务对象为空，就拒绝继续处理并抛出 `HTTPException`，向调用方报告输入或运行失败。
返回领域服务对象的当前值。
```

#### `ingest_job`

- **源码**：`app/api/knowledge_routes.py:42`
- **签名**：`def ingest_job(body: KnowledgeIngestRequest, key: IdempotencyKey, actor: Actor, service: Service) -> KnowledgeIngestResponse`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收请求正文、映射键或对象字段名、审计主体、领域服务对象，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `body` | `KnowledgeIngestRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `key` | `IdempotencyKey` | 映射键或对象字段名；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `actor` | `Actor` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `service` | `Service` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |

**输出**

- **Python 类型**：`KnowledgeIngestResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `ingest` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `query_knowledge`

- **源码**：`app/api/knowledge_routes.py:56`
- **签名**：`def query_knowledge(body: KnowledgeQueryRequest, actor: Actor, service: Service) -> KnowledgeQueryPack`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收请求正文、审计主体、领域服务对象，用于围绕论文方法语义检索、切分和排序代码证据，为后续方法映射与实验规划提供候选结果，最终标注为 `KnowledgeQueryPack` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `body` | `KnowledgeQueryRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `actor` | `Actor` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `service` | `Service` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |

**输出**

- **Python 类型**：`KnowledgeQueryPack`
- **语义**：返回 `KnowledgeQueryPack` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
移除审计主体中的当前内容；调用 `query` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `list_candidates`

- **源码**：`app/api/knowledge_routes.py:69`
- **签名**：`def list_candidates(actor: Actor, service: Service, limit: int) -> list[KnowledgeRelationRecord]`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收审计主体、领域服务对象、结果数量上限，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `actor` | `Actor` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `service` | `Service` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。；默认 调用 Query(default=100, ge=1, le=500) |

**输出**

- **Python 类型**：`list[KnowledgeRelationRecord]`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
移除审计主体中的当前内容；调用 `list_candidate_relations` 读取或查询当前阶段需要的数据，并返回处理结果。
```

#### `propose_equivalence`

- **源码**：`app/api/knowledge_routes.py:82`
- **签名**：`def propose_equivalence(body: KnowledgeEquivalenceProposalRequest, key: IdempotencyKey, actor: Actor, service: Service) -> KnowledgeRelationMutationResponse`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收请求正文、映射键或对象字段名、审计主体、领域服务对象，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `body` | `KnowledgeEquivalenceProposalRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `key` | `IdempotencyKey` | 映射键或对象字段名；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `actor` | `Actor` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `service` | `Service` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |

**输出**

- **Python 类型**：`KnowledgeRelationMutationResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
移除审计主体中的当前内容；调用 `propose_equivalence` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `review_relation`

- **源码**：`app/api/knowledge_routes.py:99`
- **签名**：`def review_relation(relation_id: str, body: KnowledgeRelationReviewRequest, key: IdempotencyKey, actor: Actor, service: Service) -> KnowledgeRelationMutationResponse`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收领域关系的 ID、请求正文、映射键或对象字段名、审计主体等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `relation_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `body` | `KnowledgeRelationReviewRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `key` | `IdempotencyKey` | 映射键或对象字段名；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `actor` | `Actor` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `service` | `Service` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |

**输出**

- **Python 类型**：`KnowledgeRelationMutationResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `review_relation` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `archive_ingestion`

- **源码**：`app/api/knowledge_routes.py:118`
- **签名**：`def archive_ingestion(ingestion_id: str, body: KnowledgeArchiveRequest, key: IdempotencyKey, actor: Actor, service: Service) -> KnowledgeIngestionRecord`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收当前处理结果的 ID、请求正文、映射键或对象字段名、审计主体等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `ingestion_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `body` | `KnowledgeArchiveRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `key` | `IdempotencyKey` | 映射键或对象字段名；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `actor` | `Actor` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `service` | `Service` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |

**输出**

- **Python 类型**：`KnowledgeIngestionRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
调用 `archive_ingestion` 完成该函数的一项辅助处理，并返回处理结果。
```

### `app/api/mcp_gateway_routes.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `repository_dependency`

- **源码**：`app/api/mcp_gateway_routes.py:16`
- **签名**：`def repository_dependency(request: Request) -> SqliteMcpEvidenceRepository`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收业务请求，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `SqliteMcpEvidenceRepository` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`SqliteMcpEvidenceRepository`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
调用 `getattr` 完成该函数的一项辅助处理，并把结果记为 持久化仓库。
如果持久化仓库为空，就拒绝继续处理并抛出 `HTTPException`，向调用方报告输入或运行失败。
返回持久化仓库的当前值。
```

#### `list_mcp_evidence`

- **源码**：`app/api/mcp_gateway_routes.py:27`
- **签名**：`def list_mcp_evidence(job_id: str, _actor: Actor, repository: RepositoryDependency, limit: int = Query(default=20, ge=1, le=100)) -> list[McpEvidencePack]`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收复现任务 ID、审计主体、持久化仓库、结果数量上限，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `_actor` | `Actor` | 名为 `_actor` 的 `Actor` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `repository` | `RepositoryDependency` | 持久化或目录访问端口；负责读取、CAS 更新或 Artifact 定位。 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。；默认 调用 Query(default=20, ge=1, le=100) |

**输出**

- **Python 类型**：`list[McpEvidencePack]`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
调用 `list_packs_for_job` 读取或查询当前阶段需要的数据，并返回处理结果。
```

#### `get_mcp_evidence`

- **源码**：`app/api/mcp_gateway_routes.py:32`
- **签名**：`def get_mcp_evidence(job_id: str, pack_id: str, _actor: Actor, repository: RepositoryDependency) -> McpEvidencePack`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收复现任务 ID、检索或映射证据包的 ID、审计主体、持久化仓库，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `McpEvidencePack` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `pack_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `_actor` | `Actor` | 名为 `_actor` 的 `Actor` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `repository` | `RepositoryDependency` | 持久化或目录访问端口；负责读取、CAS 更新或 Artifact 定位。 |

**输出**

- **Python 类型**：`McpEvidencePack`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
先尝试完成以下处理：
    调用 `get_pack` 读取或查询当前阶段需要的数据，并返回处理结果。
如果出现 `KeyError`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `HTTPException`，向调用方报告输入或运行失败。
```

### `app/api/model_routing_routes.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `gateway`

- **源码**：`app/api/model_routing_routes.py:23`
- **签名**：`def gateway(request: Request) -> ModelGateway`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收业务请求，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ModelGateway` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`ModelGateway`
- **语义**：返回 `ModelGateway` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
返回网关的当前值。
```

#### `get_budget_summary`

- **源码**：`app/api/model_routing_routes.py:31`
- **签名**：`def get_budget_summary(actor: Actor, model_gateway: Gateway, utc_date: str | None, job_id: str | None) -> 未显式标注（存在 return）`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收审计主体、网关、日期、复现任务 ID，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `actor` | `Actor` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `model_gateway` | `Gateway` | 名为 `model_gateway` 的 `Gateway` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `utc_date` | `str | None` | 名为 `utc_date` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。；默认 空值 |
| `job_id` | `str | None` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。；默认 空值 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
移除审计主体中的当前内容；计算计算当前表达式的结果，并保存为 日期；调用 `summary` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `list_model_invocations`

- **源码**：`app/api/model_routing_routes.py:52`
- **签名**：`def list_model_invocations(actor: Actor, model_gateway: Gateway, job_id: str | None, limit: int) -> 未显式标注（存在 return）`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收审计主体、网关、复现任务 ID、结果数量上限，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `actor` | `Actor` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `model_gateway` | `Gateway` | 名为 `model_gateway` 的 `Gateway` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `job_id` | `str | None` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。；默认 空值 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。；默认 调用 Query(default=100, ge=1, le=500) |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
移除审计主体中的当前内容；调用 `list_invocations` 读取或查询当前阶段需要的数据，并返回处理结果。
```

### `app/api/research_browser_routes.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `service`

- **源码**：`app/api/research_browser_routes.py:43`
- **签名**：`def service(request: Request) -> ResearchBrowserService`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收业务请求，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ResearchBrowserService` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`ResearchBrowserService`
- **语义**：返回 `ResearchBrowserService` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `getattr` 完成该函数的一项辅助处理，并把结果记为 选中的候选项。
如果选中的候选项为空，就拒绝继续处理并抛出 `RuntimeError`，向调用方报告输入或运行失败。
返回选中的候选项的当前值。
```

#### `submit_research`

- **源码**：`app/api/research_browser_routes.py:55`
- **签名**：`def submit_research(body: ResearchRequest, key: IdempotencyKey, actor: Actor, svc: Service) -> ResearchPublicRecord`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收请求正文、映射键或对象字段名、审计主体、领域服务对象，用于驱动或监督一次论文复现运行，记录命令、工作目录、资源使用、状态迁移和失败原因，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `body` | `ResearchRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `key` | `IdempotencyKey` | 映射键或对象字段名；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `actor` | `Actor` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `svc` | `Service` | 领域服务对象；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`ResearchPublicRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
调用 `submit` 完成该函数的一项辅助处理，并把结果记为 领域记录；调用 `from_record` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `run_research`

- **源码**：`app/api/research_browser_routes.py:70`
- **签名**：`def run_research(research_id: str, body: ResearchRunBody, actor: Actor, svc: Service) -> ResearchPublicRecord`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前处理结果的 ID、请求正文、审计主体、领域服务对象，用于驱动或监督一次论文复现运行，记录命令、工作目录、资源使用、状态迁移和失败原因，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `research_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `body` | `ResearchRunBody` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `actor` | `Actor` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `svc` | `Service` | 领域服务对象；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`ResearchPublicRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
调用 `run` 完成该函数的一项辅助处理，并把结果记为 领域记录；调用 `from_record` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `get_research`

- **源码**：`app/api/research_browser_routes.py:85`
- **签名**：`def get_research(research_id: str, actor: Actor, svc: Service) -> ResearchPublicRecord`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前处理结果的 ID、审计主体、领域服务对象，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `research_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `actor` | `Actor` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `svc` | `Service` | 领域服务对象；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`ResearchPublicRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
移除审计主体中的当前内容；调用 `from_record` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `get_pack`

- **源码**：`app/api/research_browser_routes.py:98`
- **签名**：`def get_pack(research_id: str, actor: Actor, svc: Service) -> ResearchEvidencePack`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前处理结果的 ID、审计主体、领域服务对象，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `ResearchEvidencePack` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `research_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `actor` | `Actor` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `svc` | `Service` | 领域服务对象；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`ResearchEvidencePack`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
移除审计主体中的当前内容；调用 `get_pack` 读取或查询当前阶段需要的数据，并返回处理结果。
```

#### `list_events`

- **源码**：`app/api/research_browser_routes.py:111`
- **签名**：`def list_events(research_id: str, actor: Actor, svc: Service, after_event_id: int, limit: int) -> list[ResearchEvent]`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前处理结果的 ID、审计主体、领域服务对象、事件的 ID等输入，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `research_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `actor` | `Actor` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `svc` | `Service` | 领域服务对象；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `after_event_id` | `int` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。；默认 调用 Query(default=0, ge=0) |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。；默认 调用 Query(default=100, ge=1, le=500) |

**输出**

- **Python 类型**：`list[ResearchEvent]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
移除审计主体中的当前内容；调用 `events` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `cancel_research`

- **源码**：`app/api/research_browser_routes.py:127`
- **签名**：`def cancel_research(research_id: str, body: ResearchCancelBody, actor: Actor, svc: Service) -> ResearchPublicRecord`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前处理结果的 ID、请求正文、审计主体、领域服务对象，用于驱动或监督一次论文复现运行，记录命令、工作目录、资源使用、状态迁移和失败原因，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `research_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `body` | `ResearchCancelBody` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `actor` | `Actor` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `svc` | `Service` | 领域服务对象；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`ResearchPublicRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
调用 `cancel` 完成该函数的一项辅助处理，并把结果记为 领域记录；调用 `from_record` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `request_resource_candidate`

- **源码**：`app/api/research_browser_routes.py:145`
- **签名**：`def request_resource_candidate(research_id: str, body: ResearchResourceSelection, actor: Actor, svc: Service) -> ResearchResourceLinkResponse`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前处理结果的 ID、请求正文、审计主体、领域服务对象，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `research_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `body` | `ResearchResourceSelection` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `actor` | `Actor` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `svc` | `Service` | 领域服务对象；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`ResearchResourceLinkResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `submit_resource_candidate` 完成该函数的一项辅助处理，并把结果记为 复现输入资源；构造并返回 `ResearchResourceLinkResponse` 结构化领域对象。
```

### `app/knowledge_base/evaluation.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `load_knowledge_golden_cases`

- **源码**：`app/knowledge_base/evaluation.py:57`
- **签名**：`def load_knowledge_golden_cases(path: Path) -> tuple[str, list[KnowledgeGoldenCase]]`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收文件或目录路径，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`tuple[str, list[KnowledgeGoldenCase]]`
- **语义**：返回从外部表示解析并校验后的领域值；格式非法时通过异常失败。

**伪代码**

```text
将外部表示解析为结构化内容，并把结果记为 结构化请求载荷。
如果“计算数量、边界或类型判断结果”后未得到肯定结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
去除辅助操作“调用 `str` 完成该函数的一项辅助处理”的结果的首尾空白，并把规范化后的文本记为 评测套件的 ID；从结构化请求载荷读取所需的状态或领域记录，并把结果记为 用例集合集合。
如果评测套件的 ID为空或为假 或 “计算数量、边界或类型判断结果”后未得到肯定结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
遍历并筛选输入，将整理后的结果保存为 评测用例集合。
如果评测用例集合为空或为假 或 当前输入内容 的长度不等于评测用例集合 的长度，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前构造的顺序或去重集合。
```

#### `evaluate_knowledge_cases`

- **源码**：`app/knowledge_base/evaluation.py:73`
- **签名**：`def evaluate_knowledge_cases(retriever: KnowledgeRetriever, suite_id: str, cases: list[KnowledgeGoldenCase]) -> KnowledgeGoldenReport`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收证据检索器、评测套件的 ID、评测用例集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `KnowledgeGoldenReport` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `retriever` | `KnowledgeRetriever` | 检索服务或端口；返回有界候选及可解释排序信息，不授予执行权限。 |
| `suite_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `cases` | `list[KnowledgeGoldenCase]` | 评测用例集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`KnowledgeGoldenReport`
- **语义**：返回 `KnowledgeGoldenReport` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
将 处理结果集合 初始化为空列表，用来收集后续结果。
遍历由评测用例集合组成的集合或迭代器，每次把当前项记为评测用例：
    调用 `query` 完成该函数的一项辅助处理，并把结果记为 检索或映射证据包；遍历并筛选输入，将整理后的结果保存为 当前处理结果；遍历并筛选输入，将整理后的结果保存为 期望集合；按稳定规则整理结果顺序，并把结果记为 该调用返回的结果。
    计算组合或计算已有值，并保存为 当前处理结果；遍历并筛选输入，将整理后的结果保存为 关系集合；构造临时集合、映射或轻量领域对象，并把结果记为 期望关系集合；按稳定规则整理结果顺序，并把结果记为 该调用返回的结果。
    计算根据条件从两个候选结果中选择一个，并保存为 关系；计算组合或计算已有值，并保存为 当前处理结果；遍历并筛选输入，将整理后的结果保存为 当前处理结果；计算根据条件从两个候选结果中选择一个，并保存为 证据。
    计算数量、边界或类型判断结果，并把结果记为 候选项集合；计算计算当前表达式的结果，并保存为 当前处理结果；把新的处理结果追加或合并到处理结果集合。
调用 `sum` 完成该函数的一项辅助处理，并把结果记为 当前处理结果的数量；构造并返回 `KnowledgeGoldenReport` 结构化领域对象。
```

### `app/knowledge_base/factory.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `build_knowledge_repository`

- **源码**：`app/knowledge_base/factory.py:14`
- **签名**：`def build_knowledge_repository() -> SqliteKnowledgeRepository`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `SqliteKnowledgeRepository` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`SqliteKnowledgeRepository`
- **语义**：返回 `SqliteKnowledgeRepository` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造 `SqliteKnowledgeRepository` 结构化领域对象，并把结果记为 持久化仓库；调用 `initialize` 完成该函数的一项辅助处理；返回持久化仓库的当前值。
```

#### `build_knowledge_service`

- **源码**：`app/knowledge_base/factory.py:20`
- **签名**：`def build_knowledge_service(job_service: JobService, artifact_catalog: ArtifactCatalog) -> KnowledgeService`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收任务、Artifact，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `KnowledgeService` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `job_service` | `JobService` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |
| `artifact_catalog` | `ArtifactCatalog` | 名为 `artifact_catalog` 的 `ArtifactCatalog` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`KnowledgeService`
- **语义**：返回 `KnowledgeService` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `build_knowledge_repository` 组装当前阶段需要的领域对象，并把结果记为 持久化仓库；调用 `build_run_evidence_reader` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果；构造 `KnowledgeSourceReader` 结构化领域对象，并把结果记为 证据读取器；构造并返回 `KnowledgeService` 结构化领域对象。
```

### `app/knowledge_base/identity.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `utc_now`

- **源码**：`app/knowledge_base/identity.py:27`
- **签名**：`def utc_now() -> str`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `isoformat` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `canonical_json_bytes`

- **源码**：`app/knowledge_base/identity.py:31`
- **签名**：`def canonical_json_bytes(value: Any) -> bytes`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `bytes` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `Any` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`bytes`
- **语义**：返回 `bytes` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果“计算数量、边界或类型判断结果”后得到肯定结果，就复制、序列化或校验结构化领域对象，并把结果记为 当前字段值。
将结构化内容序列化或编码为可传输表示，并返回处理结果。
```

#### `sha256_value`

- **源码**：`app/knowledge_base/identity.py:43`
- **签名**：`def sha256_value(value: Any) -> str`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `Any` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回输入内容的 SHA-256 身份摘要，用于完整性校验，不是加密后的正文。

**伪代码**

```text
计算输入内容的 SHA-256 身份摘要，并返回处理结果。
```

#### `normalize_knowledge_key`

- **源码**：`app/knowledge_base/identity.py:47`
- **签名**：`def normalize_knowledge_key(value: str) -> str`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，Unicode 规范化用于检索键，不声称解决语义等价。该函数接收当前字段值，用于读取并整理论文、源码或运行产物，把原始输入转换成带位置和身份信息的结构化证据，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回整理、格式化或规范化后的文本表示。

**伪代码**

```text
去除辅助操作“调用 `normalize` 完成该函数的一项辅助处理，再对返回文本执行规范化或拆分”的结果的首尾空白，并把规范化后的文本记为 规范化后的文本；调用 `sub` 完成该函数的一项辅助处理，并把结果记为 规范化后的文本；去除辅助操作“调用 `sub` 完成该函数的一项辅助处理”的结果的首尾空白，并把规范化后的文本记为 规范化后的文本。
如果规范化后的文本为空或为假，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果规范化后的文本 的长度大于500，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回规范化后的文本的当前值。
```

#### `build_entity_id`

- **源码**：`app/knowledge_base/identity.py:60`
- **签名**：`def build_entity_id(kind: KnowledgeEntityKind, scope_key: str, canonical_key: str) -> str`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收业务类别、键、规范化键，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `kind` | `KnowledgeEntityKind` | 来源、类别、用途、后端、状态或操作原因等控制字段；通常对应有限的业务枚举或审计文本。 |
| `scope_key` | `str` | 名为 `scope_key` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `canonical_key` | `str` | 名为 `canonical_key` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回稳定业务标识符，用于后续查询、关联或幂等绑定；它不是路径或内容 Hash。

**伪代码**

```text
计算按字段初始化键值映射，并保存为 对象身份；返回当前计算得到的结果。
```

#### `build_relation_id`

- **源码**：`app/knowledge_base/identity.py:74`
- **签名**：`def build_relation_id(relation_type: KnowledgeRelationType, source_entity_id: str, target_entity_id: str) -> str`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收关系类型、来源的 ID、当前处理结果的 ID，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `relation_type` | `KnowledgeRelationType` | 名为 `relation_type` 的 `KnowledgeRelationType` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `source_entity_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `target_entity_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回稳定业务标识符，用于后续查询、关联或幂等绑定；它不是路径或内容 Hash。

**伪代码**

```text
读取来源的 ID，并保存为 数据来源标记；读取当前处理结果的 ID，并保存为 待定位的代码对象或业务目标。
如果关系类型属于当前处理结果，就按稳定规则整理结果顺序，并把结果记为 多个解包结果。
计算按字段初始化键值映射，并保存为 对象身份；返回当前计算得到的结果。
```

#### `build_evidence_ref_id`

- **源码**：`app/knowledge_base/identity.py:92`
- **签名**：`def build_evidence_ref_id(artifact_id: str, content_hash: str, locator: dict[str, Any]) -> str`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收Artifact的 ID、业务内容的 Hash、源码或文档定位信息，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `artifact_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `content_hash` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |
| `locator` | `dict[str, Any]` | 源码或文档定位信息；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回稳定业务标识符，用于后续查询、关联或幂等绑定；它不是路径或内容 Hash。

**伪代码**

```text
计算按字段初始化键值映射，并保存为 对象身份；返回当前计算得到的结果。
```

#### `build_provenance_id`

- **源码**：`app/knowledge_base/identity.py:106`
- **签名**：`def build_provenance_id(subject_id: str, source_snapshot_id: str, evidence_ref_ids: list[str]) -> str`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收当前处理结果的 ID、来源的 ID、证据集合，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `subject_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `source_snapshot_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `evidence_ref_ids` | `list[str]` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回稳定业务标识符，用于后续查询、关联或幂等绑定；它不是路径或内容 Hash。

**伪代码**

```text
计算按字段初始化键值映射，并保存为 对象身份；返回当前计算得到的结果。
```

#### `entity_record_hash`

- **源码**：`app/knowledge_base/identity.py:120`
- **签名**：`def entity_record_hash(entity: KnowledgeEntityRecord) -> str`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收知识库实体记录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `entity` | `KnowledgeEntityRecord` | 知识库实体记录；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回内容身份摘要，通常为 SHA-256 十六进制字符串。

**伪代码**

```text
复制、序列化或校验结构化领域对象，并把结果记为 结构化请求载荷；调用 `sha256_value` 计算内容身份、分数或派生结果，并返回处理结果。
```

#### `relation_record_hash`

- **源码**：`app/knowledge_base/identity.py:128`
- **签名**：`def relation_record_hash(relation: KnowledgeRelationRecord) -> str`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收领域关系，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `relation` | `KnowledgeRelationRecord` | 领域关系；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回内容身份摘要，通常为 SHA-256 十六进制字符串。

**伪代码**

```text
复制、序列化或校验结构化领域对象，并把结果记为 结构化请求载荷；调用 `sha256_value` 计算内容身份、分数或派生结果，并返回处理结果。
```

#### `provenance_record_hash`

- **源码**：`app/knowledge_base/identity.py:136`
- **签名**：`def provenance_record_hash(provenance: KnowledgeProvenanceRecord) -> str`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收证据来源与追溯信息，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `provenance` | `KnowledgeProvenanceRecord` | 证据来源与追溯信息；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回内容身份摘要，通常为 SHA-256 十六进制字符串。

**伪代码**

```text
复制、序列化或校验结构化领域对象，并把结果记为 结构化请求载荷；调用 `sha256_value` 计算内容身份、分数或派生结果，并返回处理结果。
```

#### `source_snapshot_hash`

- **源码**：`app/knowledge_base/identity.py:146`
- **签名**：`def source_snapshot_hash(snapshot: KnowledgeSourceSnapshot) -> str`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收MCP 能力快照，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `snapshot` | `KnowledgeSourceSnapshot` | MCP 能力快照；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回内容身份摘要，通常为 SHA-256 十六进制字符串。

**伪代码**

```text
复制、序列化或校验结构化领域对象，并把结果记为 结构化请求载荷；调用 `sha256_value` 计算内容身份、分数或派生结果，并返回处理结果。
```

#### `graph_batch_hash`

- **源码**：`app/knowledge_base/identity.py:154`
- **签名**：`def graph_batch_hash(batch: KnowledgeGraphBatch) -> str`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，只绑定稳定内容 Hash，不让 created_at 破坏重复投影身份。该函数接收当前批次记录集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `batch` | `KnowledgeGraphBatch` | 当前批次记录集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回内容身份摘要，通常为 SHA-256 十六进制字符串。

**伪代码**

```text
调用 `sha256_value` 计算内容身份、分数或派生结果，并返回处理结果。
```

#### `validate_entity_hash`

- **源码**：`app/knowledge_base/identity.py:176`
- **签名**：`def validate_entity_hash(entity: KnowledgeEntityRecord) -> None`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收知识库实体记录，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `entity` | `KnowledgeEntityRecord` | 知识库实体记录；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
如果领域记录的 Hash不等于辅助操作“调用 `entity_record_hash` 完成该函数的一项辅助处理”的结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
```

#### `validate_relation_hash`

- **源码**：`app/knowledge_base/identity.py:181`
- **签名**：`def validate_relation_hash(relation: KnowledgeRelationRecord) -> None`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收领域关系，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `relation` | `KnowledgeRelationRecord` | 领域关系；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
如果领域关系的 Hash不等于辅助操作“调用 `relation_record_hash` 完成该函数的一项辅助处理”的结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
```

#### `validate_provenance_hash`

- **源码**：`app/knowledge_base/identity.py:186`
- **签名**：`def validate_provenance_hash(provenance: KnowledgeProvenanceRecord) -> None`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收证据来源与追溯信息，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `provenance` | `KnowledgeProvenanceRecord` | 证据来源与追溯信息；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
如果证据来源与追溯信息的 Hash不等于辅助操作“调用 `provenance_record_hash` 完成该函数的一项辅助处理”的结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
```

#### `validate_snapshot_hash`

- **源码**：`app/knowledge_base/identity.py:193`
- **签名**：`def validate_snapshot_hash(snapshot: KnowledgeSourceSnapshot) -> None`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收MCP 能力快照，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `snapshot` | `KnowledgeSourceSnapshot` | MCP 能力快照；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
如果MCP 能力快照的 Hash不等于辅助操作“调用 `source_snapshot_hash` 完成该函数的一项辅助处理”的结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
```

#### `reviewed_relation`

- **源码**：`app/knowledge_base/identity.py:198`
- **签名**：`def reviewed_relation(relation: KnowledgeRelationRecord, decision: str, actor: str, reason: str, now: str | None) -> KnowledgeRelationRecord`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，纯函数：执行单向 lifecycle transition，不写数据库。该函数接收领域关系、人工决策结果、审计主体、基线接受或运行操作原因等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `relation` | `KnowledgeRelationRecord` | 领域关系；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `decision` | `str` | 人工审批或决策记录；必须与目标动作 Hash、版本和允许操作一致。 |
| `actor` | `str` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `reason` | `str` | 来源、类别、用途、后端、状态或操作原因等控制字段；通常对应有限的业务枚举或审计文本。 |
| `now` | `str | None` | 时间值或可注入时钟，用于排序、过期、租约或可重复测试。；默认 空值 |

**输出**

- **Python 类型**：`KnowledgeRelationRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
如果人工决策结果属于{'confirmed', 'rejected'}：
    如果当前状态不等于'candidate'，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
否则：
    如果人工决策结果等于'revoked'：
        如果当前状态不等于'confirmed'，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    否则：
        拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
复制、序列化或校验结构化领域对象，并把结果记为 更新后的记录；复制、序列化或校验结构化领域对象，并返回处理结果。
```

### `app/knowledge_base/ports.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `KnowledgeRepository.initialize`

- **源码**：`app/knowledge_base/ports.py:16`
- **签名**：`def initialize(self) -> None`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `KnowledgeRepository.ingest_batch`

- **源码**：`app/knowledge_base/ports.py:19`
- **签名**：`def ingest_batch(self: 未显式标注, batch: KnowledgeGraphBatch, ingestion: KnowledgeIngestionRecord, idempotency_key: str) -> tuple[KnowledgeIngestionRecord, bool]`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收当前批次记录集合、当前处理结果、请求幂等键，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `batch` | `KnowledgeGraphBatch` | 当前批次记录集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `ingestion` | `KnowledgeIngestionRecord` | 名为 `ingestion` 的 `KnowledgeIngestionRecord` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `idempotency_key` | `str` | 调用方提供的幂等键；重复请求应复用同一结果，而不是再次产生副作用。 |

**输出**

- **Python 类型**：`tuple[KnowledgeIngestionRecord, bool]`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `KnowledgeRepository.get_entity`

- **源码**：`app/knowledge_base/ports.py:28`
- **签名**：`def get_entity(self, entity_id: str) -> KnowledgeEntityRecord`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收知识库实体记录的 ID，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `entity_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`KnowledgeEntityRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `KnowledgeRepository.get_relation`

- **源码**：`app/knowledge_base/ports.py:31`
- **签名**：`def get_relation(self, relation_id: str) -> KnowledgeRelationRecord`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收领域关系的 ID，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `relation_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`KnowledgeRelationRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `KnowledgeRepository.get_ingestion`

- **源码**：`app/knowledge_base/ports.py:34`
- **签名**：`def get_ingestion(self, ingestion_id: str) -> KnowledgeIngestionRecord`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收当前处理结果的 ID，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `ingestion_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`KnowledgeIngestionRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `KnowledgeRepository.list_candidate_relations`

- **源码**：`app/knowledge_base/ports.py:37`
- **签名**：`def list_candidate_relations(self: 未显式标注, limit: int) -> list[KnowledgeRelationRecord]`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收结果数量上限，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。 |

**输出**

- **Python 类型**：`list[KnowledgeRelationRecord]`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `KnowledgeRepository.search_entities`

- **源码**：`app/knowledge_base/ports.py:44`
- **签名**：`def search_entities(self: 未显式标注, terms: list[str], kinds: list[KnowledgeEntityKind], limit: int) -> list[KnowledgeEntityRecord]`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收检索词或规范化术语集合、当前处理结果、结果数量上限，用于围绕论文方法语义检索、切分和排序代码证据，为后续方法映射与实验规划提供候选结果，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `terms` | `list[str]` | 检索词或规范化术语集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `kinds` | `list[KnowledgeEntityKind]` | `list[KnowledgeEntityKind]` 元素集合；元素代表的业务对象由参数名 `kinds` 和调用位置确定。 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。 |

**输出**

- **Python 类型**：`list[KnowledgeEntityRecord]`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `KnowledgeRepository.relations_for_entities`

- **源码**：`app/knowledge_base/ports.py:53`
- **签名**：`def relations_for_entities(self: 未显式标注, entity_ids: list[str], include_candidates: bool, limit: int) -> list[KnowledgeRelationRecord]`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收知识库实体 ID 集合、是否包含候选证据的开关、结果数量上限，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `entity_ids` | `list[str]` | 知识库实体 ID 集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `include_candidates` | `bool` | 布尔条件或能力开关，用于控制流程分支。 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。 |

**输出**

- **Python 类型**：`list[KnowledgeRelationRecord]`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `KnowledgeRepository.active_entities_by_ids`

- **源码**：`app/knowledge_base/ports.py:62`
- **签名**：`def active_entities_by_ids(self: 未显式标注, entity_ids: list[str], limit: int) -> list[KnowledgeEntityRecord]`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收知识库实体 ID 集合、结果数量上限，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `entity_ids` | `list[str]` | 知识库实体 ID 集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。 |

**输出**

- **Python 类型**：`list[KnowledgeEntityRecord]`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `KnowledgeRepository.provenance_for_subjects`

- **源码**：`app/knowledge_base/ports.py:70`
- **签名**：`def provenance_for_subjects(self: 未显式标注, subject_ids: list[str], limit: int) -> list[KnowledgeProvenanceRecord]`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收当前处理结果、结果数量上限，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `subject_ids` | `list[str]` | `list[str]` 元素集合；元素代表的业务对象由参数名 `subject_ids` 和调用位置确定。 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。 |

**输出**

- **Python 类型**：`list[KnowledgeProvenanceRecord]`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `KnowledgeRepository.create_candidate_relation`

- **源码**：`app/knowledge_base/ports.py:78`
- **签名**：`def create_candidate_relation(self: 未显式标注, relation: KnowledgeRelationRecord, provenance: list[KnowledgeProvenanceRecord], expected_entity_hashes: dict[str, str], idempotency_key: str, request_hash: str) -> tuple[KnowledgeRelationRecord, bool]`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收领域关系、证据来源与追溯信息、期望集合、请求幂等键等输入，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `relation` | `KnowledgeRelationRecord` | 领域关系；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `provenance` | `list[KnowledgeProvenanceRecord]` | 证据来源与追溯信息；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `expected_entity_hashes` | `dict[str, str]` | 调用方观察到的旧身份，用于 stale/CAS 校验，防止覆盖并发更新。 |
| `idempotency_key` | `str` | 调用方提供的幂等键；重复请求应复用同一结果，而不是再次产生副作用。 |
| `request_hash` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |

**输出**

- **Python 类型**：`tuple[KnowledgeRelationRecord, bool]`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `KnowledgeRepository.replace_relation`

- **源码**：`app/knowledge_base/ports.py:89`
- **签名**：`def replace_relation(self: 未显式标注, relation: KnowledgeRelationRecord, expected_version: int, expected_hash: str, idempotency_key: str, request_hash: str) -> tuple[KnowledgeRelationRecord, bool]`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收领域关系、调用方看到的旧版本号、调用方看到的旧内容 Hash、请求幂等键等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `relation` | `KnowledgeRelationRecord` | 领域关系；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `expected_version` | `int` | 调用方观察到的旧身份，用于 stale/CAS 校验，防止覆盖并发更新。 |
| `expected_hash` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |
| `idempotency_key` | `str` | 调用方提供的幂等键；重复请求应复用同一结果，而不是再次产生副作用。 |
| `request_hash` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |

**输出**

- **Python 类型**：`tuple[KnowledgeRelationRecord, bool]`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `KnowledgeRepository.archive_ingestion`

- **源码**：`app/knowledge_base/ports.py:100`
- **签名**：`def archive_ingestion(self: 未显式标注, ingestion_id: str, actor: str, reason: str, idempotency_key: str, request_hash: str) -> tuple[KnowledgeIngestionRecord, bool]`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收当前处理结果的 ID、审计主体、基线接受或运行操作原因、请求幂等键等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `ingestion_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `actor` | `str` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `reason` | `str` | 来源、类别、用途、后端、状态或操作原因等控制字段；通常对应有限的业务枚举或审计文本。 |
| `idempotency_key` | `str` | 调用方提供的幂等键；重复请求应复用同一结果，而不是再次产生副作用。 |
| `request_hash` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |

**输出**

- **Python 类型**：`tuple[KnowledgeIngestionRecord, bool]`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `KnowledgeRepository.active_referenced_job_ids`

- **源码**：`app/knowledge_base/ports.py:111`
- **签名**：`def active_referenced_job_ids(self) -> set[str]`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`set[str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

### `app/knowledge_base/projector.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `KnowledgeProjector._source_snapshot`

- **源码**：`app/knowledge_base/projector.py:65`
- **签名**：`def _source_snapshot(bundle: KnowledgeSourceBundle) -> KnowledgeSourceSnapshot`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收代码仓库归档包，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `KnowledgeSourceSnapshot` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `bundle` | `KnowledgeSourceBundle` | 代码仓库归档包；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`KnowledgeSourceSnapshot`
- **语义**：返回 `KnowledgeSourceSnapshot` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
遍历并筛选输入，将整理后的结果保存为 Artifact集合；构造 `KnowledgeSourceSnapshot` 结构化领域对象，并把结果记为 草稿对象；调用 `source_snapshot_hash` 完成该函数的一项辅助处理，并把结果记为 内容摘要；复制、序列化或校验结构化领域对象，并返回处理结果。
```

#### `KnowledgeProjector._entity`

- **源码**：`app/knowledge_base/projector.py:102`
- **签名**：`def _entity(kind: KnowledgeEntityKind, scope_key: str, canonical_key: str, display_name: str, description: str | None, attributes: dict, now: str) -> KnowledgeEntityRecord`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收业务类别、键、规范化键、当前处理结果的名称等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `kind` | `KnowledgeEntityKind` | 来源、类别、用途、后端、状态或操作原因等控制字段；通常对应有限的业务枚举或审计文本。 |
| `scope_key` | `str` | 名为 `scope_key` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `canonical_key` | `str` | 名为 `canonical_key` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `display_name` | `str` | 名为 `display_name` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `description` | `str | None` | 对象说明；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `attributes` | `dict` | 对象属性集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `now` | `str` | 时间值或可注入时钟，用于排序、过期、租约或可重复测试。 |

**输出**

- **Python 类型**：`KnowledgeEntityRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
调用 `normalize_knowledge_key` 解析、规范化或转换当前输入，并把结果记为 规范化；构造 `KnowledgeEntityRecord` 结构化领域对象，并把结果记为 草稿对象；复制、序列化或校验结构化领域对象，并返回处理结果。
```

#### `KnowledgeProjector._relation`

- **源码**：`app/knowledge_base/projector.py:133`
- **签名**：`def _relation(relation_type: KnowledgeRelationType, source_entity_id: str, target_entity_id: str, status: KnowledgeRelationStatus, confidence: float, proposal_reason: str | None, now: str) -> KnowledgeRelationRecord`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收关系类型、来源的 ID、当前处理结果的 ID、当前状态等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `relation_type` | `KnowledgeRelationType` | 名为 `relation_type` 的 `KnowledgeRelationType` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `source_entity_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `target_entity_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `status` | `KnowledgeRelationStatus` | 来源、类别、用途、后端、状态或操作原因等控制字段；通常对应有限的业务枚举或审计文本。 |
| `confidence` | `float` | 名为 `confidence` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `proposal_reason` | `str | None` | 名为 `proposal_reason` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。；默认 空值 |
| `now` | `str` | 时间值或可注入时钟，用于排序、过期、租约或可重复测试。 |

**输出**

- **Python 类型**：`KnowledgeRelationRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
读取来源的 ID，并保存为 数据来源标记的 ID；读取当前处理结果的 ID，并保存为 待定位的代码对象或业务目标的 ID。
如果关系类型等于'equivalent_to'，就按稳定规则整理结果顺序，并把结果记为 多个解包结果。
计算根据条件从两个候选结果中选择一个，并保存为 职责权限；构造 `KnowledgeRelationRecord` 结构化领域对象，并把结果记为 草稿对象；复制、序列化或校验结构化领域对象，并返回处理结果。
```

#### `KnowledgeProjector._paper_ref`

- **源码**：`app/knowledge_base/projector.py:175`
- **签名**：`def _paper_ref(bundle: KnowledgeSourceBundle, artifact_path: str, content_hash: str, section_id: str | None, block_ids: list[str] | None, page_start: int | None, page_end: int | None) -> KnowledgeEvidenceRef`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收代码仓库归档包、Artifact的路径、业务内容的 Hash、论文文档章节的 ID等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `KnowledgeEvidenceRef` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `bundle` | `KnowledgeSourceBundle` | 代码仓库归档包；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `artifact_path` | `str` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `content_hash` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |
| `section_id` | `str | None` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。；默认 空值 |
| `block_ids` | `list[str] | None` | `list[str] | None` 元素集合；元素代表的业务对象由参数名 `block_ids` 和调用位置确定。；默认 空值 |
| `page_start` | `int | None` | 名为 `page_start` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。；默认 空值 |
| `page_end` | `int | None` | 名为 `page_end` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。；默认 空值 |

**输出**

- **Python 类型**：`KnowledgeEvidenceRef`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
读取当前处理结果中的对应字段，并保存为 视图；计算按字段初始化键值映射，并保存为 源码或文档定位信息；构造并返回 `KnowledgeEvidenceRef` 结构化领域对象。
```

#### `KnowledgeProjector._code_ref`

- **源码**：`app/knowledge_base/projector.py:215`
- **签名**：`def _code_ref(bundle: KnowledgeSourceBundle, evidence: Evidence) -> KnowledgeEvidenceRef`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收代码仓库归档包、可追溯证据记录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `KnowledgeEvidenceRef` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `bundle` | `KnowledgeSourceBundle` | 代码仓库归档包；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `evidence` | `Evidence` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |

**输出**

- **Python 类型**：`KnowledgeEvidenceRef`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
计算按字段初始化键值映射，并保存为 当前处理结果。
如果来源类型不等于'code' 或 辅助操作产生的可迭代结果（调用 `values` 完成该函数的一项辅助处理）中存在满足“当前字段值为空”的项，就拒绝继续处理并抛出 `KnowledgeIntegrityError`，向调用方报告输入或运行失败。
读取当前处理结果中的对应字段，并保存为 视图；计算按字段初始化键值映射，并保存为 源码或文档定位信息；断言业务内容的 Hash不为空；不满足就终止当前测试或流程；构造并返回 `KnowledgeEvidenceRef` 结构化领域对象。
```

#### `KnowledgeProjector._provenance`

- **源码**：`app/knowledge_base/projector.py:267`
- **签名**：`def _provenance(subject_kind: str, subject_id: str, snapshot: KnowledgeSourceSnapshot, evidence: Iterable[KnowledgeEvidenceRef], authority: str, now: str) -> KnowledgeProvenanceRecord`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收类别、当前处理结果的 ID、MCP 能力快照、可追溯证据记录等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `subject_kind` | `str` | 名为 `subject_kind` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `subject_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `snapshot` | `KnowledgeSourceSnapshot` | MCP 能力快照；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `evidence` | `Iterable[KnowledgeEvidenceRef]` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |
| `authority` | `str` | 名为 `authority` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `now` | `str` | 时间值或可注入时钟，用于排序、过期、租约或可重复测试。 |

**输出**

- **Python 类型**：`KnowledgeProvenanceRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
按稳定规则整理结果顺序，并把结果记为 该调用返回的结果；构造 `KnowledgeProvenanceRecord` 结构化领域对象，并把结果记为 草稿对象；复制、序列化或校验结构化领域对象，并返回处理结果。
```

#### `KnowledgeProjector._fact_ref`

- **源码**：`app/knowledge_base/projector.py:301`
- **签名**：`def _fact_ref(bundle: KnowledgeSourceBundle, fact: PaperFactRecord) -> KnowledgeEvidenceRef`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收代码仓库归档包、项目事实记录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `KnowledgeEvidenceRef` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `bundle` | `KnowledgeSourceBundle` | 代码仓库归档包；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `fact` | `PaperFactRecord` | 项目事实记录或类型化事实值；包含来源、状态、版本与内容身份。 |

**输出**

- **Python 类型**：`KnowledgeEvidenceRef`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
读取可追溯证据记录，并保存为 可追溯证据记录；调用 `_paper_ref` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `KnowledgeProjector._symbol_key`

- **源码**：`app/knowledge_base/projector.py:317`
- **签名**：`def _symbol_key(candidate: CodeCandidate, symbol: str, file_sha256: str) -> str`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收待审核的 MCP 能力候选、当前处理结果、文件的 SHA-256，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `candidate` | `CodeCandidate` | 待审核的 MCP 能力候选；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `symbol` | `str` | 名为 `symbol` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `file_sha256` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `join` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `KnowledgeProjector.project`

- **源码**：`app/knowledge_base/projector.py:324`
- **签名**：`def project(self, bundle: KnowledgeSourceBundle) -> KnowledgeGraphBatch`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收代码仓库归档包，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `KnowledgeGraphBatch` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `bundle` | `KnowledgeSourceBundle` | 代码仓库归档包；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`KnowledgeGraphBatch`
- **语义**：返回 `KnowledgeGraphBatch` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
读取当前时间，作为状态变更的统一时间戳，并把结果记为 当前时间；调用 `_source_snapshot` 完成该函数的一项辅助处理，并把结果记为 MCP 能力快照；将 当前处理结果、当前处理结果、证据来源与追溯信息 初始化为空映射，用来收集后续结果。
定义内部辅助函数 `add_entity`，供当前函数在后续步骤中调用。
定义内部辅助函数 `add_relation`，供当前函数在后续步骤中调用。
计算计算当前表达式的结果，并保存为 论文；调用 `_paper_ref` 完成该函数的一项辅助处理，并把结果记为 论文；调用 `_entity` 完成该函数的一项辅助处理，并把结果记为 论文；调用 `add_entity` 完成该函数的一项辅助处理。
将 章节集合 初始化为空映射，用来收集后续结果。
遍历当前可迭代输入，每次把当前项记为论文文档章节：
    调用 `_paper_ref` 完成该函数的一项辅助处理，并把结果记为 章节；调用 `_entity` 完成该函数的一项辅助处理，并把结果记为 知识库实体记录；读取知识库实体记录，并保存为 章节集合中的对应字段；调用 `add_entity` 完成该函数的一项辅助处理。
    调用 `add_relation` 完成该函数的一项辅助处理。
将 当前处理结果 初始化为空映射，用来收集后续结果。
遍历当前可迭代输入，每次把当前项记为项目事实记录：
    读取章节集合中的对应字段，并保存为 论文文档章节；调用 `_fact_ref` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `_entity` 完成该函数的一项辅助处理，并把结果记为 论文主张；调用 `add_entity` 完成该函数的一项辅助处理。
    调用 `add_relation` 完成该函数的一项辅助处理；从事实集合读取所需的状态或领域记录，并把结果记为 业务类别。
    如果业务类别为空，就跳过本轮剩余处理，直接进入下一轮。
    调用 `_entity` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `add_entity` 完成该函数的一项辅助处理；读取事实集合中的对应字段，并保存为 关系类型；计算根据条件从两个候选结果中选择一个，并保存为 关系来源。
    调用 `add_relation` 完成该函数的一项辅助处理。
    如果评测类别等于'method_module'，就读取当前处理结果，并保存为 当前处理结果中的对应字段。
遍历当前可迭代输入，每次把当前项记为论文-代码映射，然后调用 `_project_mapping` 完成该函数的一项辅助处理。
构造并返回 `KnowledgeGraphBatch` 结构化领域对象。
```

#### `KnowledgeProjector.project.add_entity`

- **源码**：`app/knowledge_base/projector.py:331`
- **签名**：`def add_entity(entity: KnowledgeEntityRecord, refs: list[KnowledgeEvidenceRef], authority: str) -> None`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收知识库实体记录、当前处理结果、职责权限，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `entity` | `KnowledgeEntityRecord` | 知识库实体记录；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `refs` | `list[KnowledgeEvidenceRef]` | `list[KnowledgeEvidenceRef]` 元素集合；元素代表的业务对象由参数名 `refs` 和调用位置确定。 |
| `authority` | `str` | 名为 `authority` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。；默认 'deterministic_source' |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
从当前处理结果读取所需的状态或领域记录，并把结果记为 该调用返回的结果。
如果当前处理结果不为空 且 领域记录的 Hash不等于领域记录的 Hash，就拒绝继续处理并抛出 `KnowledgeIntegrityError`，向调用方报告输入或运行失败。
读取知识库实体记录，并保存为 当前处理结果中的对应字段；调用 `_provenance` 完成该函数的一项辅助处理，并把结果记为 当前处理项；读取当前处理项，并保存为 证据来源与追溯信息中的对应字段。
```

#### `KnowledgeProjector.project.add_relation`

- **源码**：`app/knowledge_base/projector.py:352`
- **签名**：`def add_relation(relation: KnowledgeRelationRecord, refs: list[KnowledgeEvidenceRef]) -> None`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收领域关系、当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `relation` | `KnowledgeRelationRecord` | 领域关系；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `refs` | `list[KnowledgeEvidenceRef]` | `list[KnowledgeEvidenceRef]` 元素集合；元素代表的业务对象由参数名 `refs` 和调用位置确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
从当前处理结果读取所需的状态或领域记录，并把结果记为 该调用返回的结果。
如果当前处理结果不为空 且 领域关系的 Hash不等于领域关系的 Hash，就拒绝继续处理并抛出 `KnowledgeIntegrityError`，向调用方报告输入或运行失败。
读取领域关系，并保存为 当前处理结果中的对应字段；调用 `_provenance` 完成该函数的一项辅助处理，并把结果记为 当前处理项；读取当前处理项，并保存为 证据来源与追溯信息中的对应字段。
```

#### `KnowledgeProjector._project_mapping`

- **源码**：`app/knowledge_base/projector.py:530`
- **签名**：`def _project_mapping(self: 未显式标注, bundle: KnowledgeSourceBundle, mapping: ModuleMapping, concept_entities: dict[str, KnowledgeEntityRecord], now: str, add_entity: 未显式标注, add_relation: 未显式标注) -> None`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，Code mapping 是模型候选，只产生 candidate relation。该函数接收代码仓库归档包、论文-代码映射、当前处理结果、当前时间等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `bundle` | `KnowledgeSourceBundle` | 代码仓库归档包；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `mapping` | `ModuleMapping` | 论文-代码映射；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `concept_entities` | `dict[str, KnowledgeEntityRecord]` | 名为 `concept_entities` 的键值映射；键和值分别承载的业务字段由读取/写入分支确定。 |
| `now` | `str` | 时间值或可注入时钟，用于排序、过期、租约或可重复测试。 |
| `add_entity` | `未显式标注` | 名为 `add_entity` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `add_relation` | `未显式标注` | 名为 `add_relation` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
从当前处理结果读取所需的状态或领域记录，并把结果记为 该调用返回的结果。
如果当前处理结果为空，就结束当前函数，不返回业务值。
遍历当前可迭代输入，每次把当前项记为待审核的 MCP 能力候选：
    遍历并筛选输入，将整理后的结果保存为 当前处理结果。
    如果当前处理结果为空或为假，就跳过本轮剩余处理，直接进入下一轮。
    读取仓库指纹，并保存为 仓库；读取文件的 SHA-256，并保存为 文件的 SHA-256。
    如果仓库为空 或 文件的 SHA-256为空，就拒绝继续处理并抛出 `KnowledgeIntegrityError`，向调用方报告输入或运行失败。
    计算计算当前表达式的结果，并保存为 当前处理结果。
    遍历由当前处理结果组成的集合或迭代器，每次把当前项记为当前处理结果，然后调用 `_entity` 完成该函数的一项辅助处理，并把结果记为 知识库实体记录；调用 `add_entity` 完成该函数的一项辅助处理；调用 `add_relation` 完成该函数的一项辅助处理。
```

### `app/knowledge_base/repository.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `SqliteKnowledgeRepository.__init__`

- **源码**：`app/knowledge_base/repository.py:34`
- **签名**：`def __init__(self, path: Path) -> None`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收文件或目录路径，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 文件或目录路径 分别保存到同名实例字段。
```

#### `SqliteKnowledgeRepository._connect`

- **源码**：`app/knowledge_base/repository.py:37`
- **签名**：`def _connect(self) -> sqlite3.Connection`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于在固定 MCP Policy、Schema Pin、调用预算和只读职责边界内连接或调用外部能力，并把返回内容转换为可追溯的复现证据，最终标注为 `sqlite3.Connection` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`sqlite3.Connection`
- **语义**：返回 `sqlite3.Connection` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `connect` 完成该函数的一项辅助处理，并把结果记为 数据库连接；读取数据库记录行，并保存为 记录行；通过数据库连接执行数据查询或命令；通过数据库连接执行数据查询或命令。
通过数据库连接执行数据查询或命令；返回数据库连接的当前值。
```

#### `SqliteKnowledgeRepository.initialize`

- **源码**：`app/knowledge_base/repository.py:45`
- **签名**：`def initialize(self) -> None`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
创建父级目录或父领域对象对应的目录。
在上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”中调用 `executescript` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `SqliteKnowledgeRepository.ping`

- **源码**：`app/knowledge_base/repository.py:123`
- **签名**：`def ping(self) -> None`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”中调用 `fetchone` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `SqliteKnowledgeRepository._entity`

- **源码**：`app/knowledge_base/repository.py:128`
- **签名**：`def _entity(row: sqlite3.Row) -> KnowledgeEntityRecord`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收数据库记录行，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `row` | `sqlite3.Row` | 数据库记录行；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`KnowledgeEntityRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
先尝试完成以下处理：
    调用 `model_validate_json` 完成该函数的一项辅助处理，并把结果记为 领域记录；调用 `validate_entity_hash` 校验当前输入或状态。
如果出现 `(ValidationError, ValueError)`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `KnowledgeIntegrityError`，向调用方报告输入或运行失败。
如果知识库实体记录的 ID不等于数据库记录行中的对应字段 或 业务类别不等于数据库记录行中的对应字段 或 键不等于数据库记录行中的对应字段 或 规范化键不等于数据库记录行中的对应字段 或 领域记录的 Hash不等于数据库记录行中的对应字段，就拒绝继续处理并抛出 `KnowledgeIntegrityError`，向调用方报告输入或运行失败。
返回领域记录的当前值。
```

#### `SqliteKnowledgeRepository._relation`

- **源码**：`app/knowledge_base/repository.py:149`
- **签名**：`def _relation(row: sqlite3.Row) -> KnowledgeRelationRecord`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收数据库记录行，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `row` | `sqlite3.Row` | 数据库记录行；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`KnowledgeRelationRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
先尝试完成以下处理：
    调用 `model_validate_json` 完成该函数的一项辅助处理，并把结果记为 领域记录；调用 `validate_relation_hash` 校验当前输入或状态。
如果出现 `(ValidationError, ValueError)`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `KnowledgeIntegrityError`，向调用方报告输入或运行失败。
如果领域关系的 ID不等于数据库记录行中的对应字段 或 当前状态不等于数据库记录行中的对应字段 或 记录版本号不等于数据库记录行中的对应字段 或 领域关系的 Hash不等于数据库记录行中的对应字段，就拒绝继续处理并抛出 `KnowledgeIntegrityError`，向调用方报告输入或运行失败。
返回领域记录的当前值。
```

#### `SqliteKnowledgeRepository._provenance`

- **源码**：`app/knowledge_base/repository.py:169`
- **签名**：`def _provenance(row: sqlite3.Row) -> KnowledgeProvenanceRecord`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收数据库记录行，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `row` | `sqlite3.Row` | 数据库记录行；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`KnowledgeProvenanceRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
先尝试完成以下处理：
    调用 `model_validate_json` 完成该函数的一项辅助处理，并把结果记为 领域记录；调用 `validate_provenance_hash` 校验当前输入或状态。
如果出现 `(ValidationError, ValueError)`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `KnowledgeIntegrityError`，向调用方报告输入或运行失败。
如果证据来源与追溯信息的 ID不等于数据库记录行中的对应字段 或 当前处理结果的 ID不等于数据库记录行中的对应字段 或 来源的 ID不等于数据库记录行中的对应字段 或 证据来源与追溯信息的 Hash不等于数据库记录行中的对应字段，就拒绝继续处理并抛出 `KnowledgeIntegrityError`，向调用方报告输入或运行失败。
返回领域记录的当前值。
```

#### `SqliteKnowledgeRepository._ingestion`

- **源码**：`app/knowledge_base/repository.py:189`
- **签名**：`def _ingestion(row: sqlite3.Row) -> KnowledgeIngestionRecord`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收数据库记录行，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `row` | `sqlite3.Row` | 数据库记录行；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`KnowledgeIngestionRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
先尝试完成以下处理：
    调用 `model_validate_json` 完成该函数的一项辅助处理，并把结果记为 领域记录；调用 `validate_snapshot_hash` 校验当前输入或状态。
如果出现 `(ValidationError, ValueError)`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `KnowledgeIntegrityError`，向调用方报告输入或运行失败。
如果当前处理结果的 ID不等于数据库记录行中的对应字段 或 MCP 能力快照的 ID不等于数据库记录行中的对应字段 或 MCP 能力快照的 Hash不等于数据库记录行中的对应字段 或 当前状态不等于数据库记录行中的对应字段 或 当前批次记录集合的 Hash不等于数据库记录行中的对应字段 或 请求内容 Hash不等于数据库记录行中的对应字段，就拒绝继续处理并抛出 `KnowledgeIntegrityError`，向调用方报告输入或运行失败。
返回领域记录的当前值。
```

#### `SqliteKnowledgeRepository._replay`

- **源码**：`app/knowledge_base/repository.py:211`
- **签名**：`def _replay(connection: sqlite3.Connection, operation_key: str, request_hash: str, response_kind: str) -> dict | None`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收数据库连接、操作键、请求内容 Hash、响应类别，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `dict | None` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `connection` | `sqlite3.Connection` | 数据库连接；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `operation_key` | `str` | 名为 `operation_key` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `request_hash` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |
| `response_kind` | `str` | 前序调用产生的结构化响应、结果或执行结论，供当前函数继续判断或投影。 |

**输出**

- **Python 类型**：`dict | None`
- **语义**：返回 `dict | None` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `fetchone` 完成该函数的一项辅助处理，并把结果记为 数据库记录行。
如果数据库记录行为空，就返回固定值 `空值`。
如果数据库记录行中的对应字段不等于请求内容 Hash，就拒绝继续处理并抛出 `KnowledgeConflictError`，向调用方报告输入或运行失败。
如果数据库记录行中的对应字段不等于响应类别，就拒绝继续处理并抛出 `KnowledgeConflictError`，向调用方报告输入或运行失败。
将外部表示解析为结构化内容，并返回处理结果。
```

#### `SqliteKnowledgeRepository._save_operation`

- **源码**：`app/knowledge_base/repository.py:233`
- **签名**：`def _save_operation(connection: sqlite3.Connection, operation_key: str, request_hash: str, response_kind: str, response: dict) -> None`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收数据库连接、操作键、请求内容 Hash、响应类别等输入，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `connection` | `sqlite3.Connection` | 数据库连接；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `operation_key` | `str` | 名为 `operation_key` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `request_hash` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |
| `response_kind` | `str` | 前序调用产生的结构化响应、结果或执行结论，供当前函数继续判断或投影。 |
| `response` | `dict` | 前序调用产生的结构化响应、结果或执行结论，供当前函数继续判断或投影。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
通过数据库连接执行数据查询或命令。
```

#### `SqliteKnowledgeRepository._insert_entity`

- **源码**：`app/knowledge_base/repository.py:261`
- **签名**：`def _insert_entity(connection: sqlite3.Connection, record: KnowledgeEntityRecord) -> bool`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收数据库连接、领域记录，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `connection` | `sqlite3.Connection` | 数据库连接；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `record` | `KnowledgeEntityRecord` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
调用 `fetchone` 完成该函数的一项辅助处理，并把结果记为 数据库记录行。
如果数据库记录行不为空：
    调用 `_entity` 完成该函数的一项辅助处理，并把结果记为 当前值。
    如果领域记录的 Hash不等于领域记录的 Hash，就拒绝继续处理并抛出 `KnowledgeConflictError`，向调用方报告输入或运行失败。
    返回固定值 `假`。
通过数据库连接执行数据查询或命令；返回固定值 `真`。
```

#### `SqliteKnowledgeRepository._insert_relation`

- **源码**：`app/knowledge_base/repository.py:297`
- **签名**：`def _insert_relation(connection: sqlite3.Connection, record: KnowledgeRelationRecord) -> bool`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收数据库连接、领域记录，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `connection` | `sqlite3.Connection` | 数据库连接；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `record` | `KnowledgeRelationRecord` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
调用 `fetchone` 完成该函数的一项辅助处理，并把结果记为 数据库记录行。
如果数据库记录行不为空：
    调用 `_relation` 完成该函数的一项辅助处理，并把结果记为 当前值；计算计算当前表达式的结果，并保存为 身份。
    如果身份为空或为假，就拒绝继续处理并抛出 `KnowledgeConflictError`，向调用方报告输入或运行失败。
    如果当前状态等于'candidate'，就返回固定值 `假`。
    如果领域关系的 Hash不等于领域关系的 Hash，就拒绝继续处理并抛出 `KnowledgeConflictError`，向调用方报告输入或运行失败。
    返回固定值 `假`。
通过数据库连接执行数据查询或命令；返回固定值 `真`。
```

#### `SqliteKnowledgeRepository._insert_provenance`

- **源码**：`app/knowledge_base/repository.py:348`
- **签名**：`def _insert_provenance(connection: sqlite3.Connection, record: KnowledgeProvenanceRecord) -> bool`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收数据库连接、领域记录，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `connection` | `sqlite3.Connection` | 数据库连接；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `record` | `KnowledgeProvenanceRecord` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
调用 `fetchone` 完成该函数的一项辅助处理，并把结果记为 数据库记录行。
如果数据库记录行不为空：
    调用 `_provenance` 完成该函数的一项辅助处理，并把结果记为 当前值。
    如果证据来源与追溯信息的 Hash不等于证据来源与追溯信息的 Hash，就拒绝继续处理并抛出 `KnowledgeConflictError`，向调用方报告输入或运行失败。
    返回固定值 `假`。
通过数据库连接执行数据查询或命令；返回固定值 `真`。
```

#### `SqliteKnowledgeRepository._validate_batch`

- **源码**：`app/knowledge_base/repository.py:383`
- **签名**：`def _validate_batch(batch: KnowledgeGraphBatch) -> None`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收当前批次记录集合，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `batch` | `KnowledgeGraphBatch` | 当前批次记录集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `validate_snapshot_hash` 校验当前输入或状态；遍历并筛选输入，将整理后的结果保存为 知识库实体 ID 集合；遍历并筛选输入，将整理后的结果保存为 关系集合；遍历并筛选输入，将整理后的结果保存为 当前处理结果。
如果知识库实体 ID 集合 的长度不等于辅助操作“构造临时集合、映射或轻量领域对象”的结果 的长度，就拒绝继续处理并抛出 `KnowledgeConflictError`，向调用方报告输入或运行失败。
如果关系集合 的长度不等于辅助操作“构造临时集合、映射或轻量领域对象”的结果 的长度，就拒绝继续处理并抛出 `KnowledgeConflictError`，向调用方报告输入或运行失败。
如果当前处理结果 的长度不等于辅助操作“构造临时集合、映射或轻量领域对象”的结果 的长度，就拒绝继续处理并抛出 `KnowledgeConflictError`，向调用方报告输入或运行失败。
计算组合或计算已有值，并保存为 当前处理结果；将 当前处理结果 初始化为空去重集合，用来收集后续结果。
遍历当前可迭代输入，每次把当前项记为知识库实体记录，然后调用 `validate_entity_hash` 校验当前输入或状态。
遍历当前可迭代输入，每次把当前项记为领域关系：
    调用 `validate_relation_hash` 校验当前输入或状态。
    如果来源的 ID不属于知识库实体 ID 集合 或 当前处理结果的 ID不属于知识库实体 ID 集合，就拒绝继续处理并抛出 `KnowledgeConflictError`，向调用方报告输入或运行失败。
遍历当前可迭代输入，每次把当前项记为当前处理项：
    调用 `validate_provenance_hash` 校验当前输入或状态。
    如果来源的 ID不等于MCP 能力快照的 ID，就拒绝继续处理并抛出 `KnowledgeConflictError`，向调用方报告输入或运行失败。
    如果当前处理结果的 ID不属于当前处理结果，就拒绝继续处理并抛出 `KnowledgeConflictError`，向调用方报告输入或运行失败。
    把当前处理结果的 ID追加或合并到当前处理结果。
如果当前处理结果不等于当前处理结果，就拒绝继续处理并抛出 `KnowledgeConflictError`，向调用方报告输入或运行失败。
```

#### `SqliteKnowledgeRepository.ingest_batch`

- **源码**：`app/knowledge_base/repository.py:424`
- **签名**：`def ingest_batch(self: 未显式标注, batch: KnowledgeGraphBatch, ingestion: KnowledgeIngestionRecord, idempotency_key: str) -> tuple[KnowledgeIngestionRecord, bool]`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收当前批次记录集合、当前处理结果、请求幂等键，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `batch` | `KnowledgeGraphBatch` | 当前批次记录集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `ingestion` | `KnowledgeIngestionRecord` | 名为 `ingestion` 的 `KnowledgeIngestionRecord` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `idempotency_key` | `str` | 调用方提供的幂等键；重复请求应复用同一结果，而不是再次产生副作用。 |

**输出**

- **Python 类型**：`tuple[KnowledgeIngestionRecord, bool]`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
调用 `_validate_batch` 校验当前输入或状态。
如果数据来源标记不等于数据来源标记 或 当前状态不等于'active'，就拒绝继续处理并抛出 `KnowledgeConflictError`，向调用方报告输入或运行失败。
如果当前批次记录集合的 Hash不等于辅助操作“调用 `graph_batch_hash` 完成该函数的一项辅助处理”的结果，就拒绝继续处理并抛出 `KnowledgeConflictError`，向调用方报告输入或运行失败。
进入上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”，退出时自动清理资源：
    通过数据库连接执行数据查询或命令；调用 `_replay` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
    如果当前处理结果不为空，就返回当前构造的顺序或去重集合。
    调用 `fetchone` 完成该函数的一项辅助处理，并把结果记为 已有记录。
    如果已有记录不为空：
        调用 `_ingestion` 完成该函数的一项辅助处理，并把结果记为 当前值。
        如果当前批次记录集合的 Hash不等于当前批次记录集合的 Hash，就拒绝继续处理并抛出 `KnowledgeConflictError`，向调用方报告输入或运行失败。
        调用 `_save_operation` 持久化或更新当前领域数据；提交数据库连接中已完成的数据变更；返回当前构造的顺序或去重集合。
    调用 `sum` 完成该函数的一项辅助处理，并把结果记为 已创建集合；调用 `sum` 完成该函数的一项辅助处理，并把结果记为 已创建集合；复制、序列化或校验结构化领域对象，并把结果记为 记录；通过数据库连接执行数据查询或命令。
    遍历当前可迭代输入，每次把当前项记为当前处理项，然后调用 `_insert_provenance` 持久化或更新当前领域数据。
    调用 `_save_operation` 持久化或更新当前领域数据；提交数据库连接中已完成的数据变更。
返回当前构造的顺序或去重集合。
```

#### `SqliteKnowledgeRepository.get_entity`

- **源码**：`app/knowledge_base/repository.py:525`
- **签名**：`def get_entity(self, entity_id: str) -> KnowledgeEntityRecord`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收知识库实体记录的 ID，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `entity_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`KnowledgeEntityRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
在上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”中调用 `fetchone` 完成该函数的一项辅助处理，并把结果记为 数据库记录行，退出时自动清理资源。
如果数据库记录行为空，就拒绝继续处理并抛出 `KnowledgeNotFoundError`，向调用方报告输入或运行失败。
调用 `_entity` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `SqliteKnowledgeRepository.get_relation`

- **源码**：`app/knowledge_base/repository.py:535`
- **签名**：`def get_relation(self, relation_id: str) -> KnowledgeRelationRecord`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收领域关系的 ID，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `relation_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`KnowledgeRelationRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
在上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”中调用 `fetchone` 完成该函数的一项辅助处理，并把结果记为 数据库记录行，退出时自动清理资源。
如果数据库记录行为空，就拒绝继续处理并抛出 `KnowledgeNotFoundError`，向调用方报告输入或运行失败。
调用 `_relation` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `SqliteKnowledgeRepository.get_ingestion`

- **源码**：`app/knowledge_base/repository.py:545`
- **签名**：`def get_ingestion(self, ingestion_id: str) -> KnowledgeIngestionRecord`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收当前处理结果的 ID，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `ingestion_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`KnowledgeIngestionRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
在上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”中调用 `fetchone` 完成该函数的一项辅助处理，并把结果记为 数据库记录行，退出时自动清理资源。
如果数据库记录行为空，就拒绝继续处理并抛出 `KnowledgeNotFoundError`，向调用方报告输入或运行失败。
调用 `_ingestion` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `SqliteKnowledgeRepository.list_candidate_relations`

- **源码**：`app/knowledge_base/repository.py:557`
- **签名**：`def list_candidate_relations(self: 未显式标注, limit: int) -> list[KnowledgeRelationRecord]`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收结果数量上限，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。 |

**输出**

- **Python 类型**：`list[KnowledgeRelationRecord]`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
计算数量、边界或类型判断结果，并把结果记为 该调用返回的结果。
在上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”中调用 `fetchall` 完成该函数的一项辅助处理，并把结果记为 数据库记录行集合，退出时自动清理资源。
返回当前计算得到的结果。
```

#### `SqliteKnowledgeRepository.search_entities`

- **源码**：`app/knowledge_base/repository.py:579`
- **签名**：`def search_entities(self: 未显式标注, terms: list[str], kinds: list[KnowledgeEntityKind], limit: int) -> list[KnowledgeEntityRecord]`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收检索词或规范化术语集合、当前处理结果、结果数量上限，用于围绕论文方法语义检索、切分和排序代码证据，为后续方法映射与实验规划提供候选结果，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `terms` | `list[str]` | 检索词或规范化术语集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `kinds` | `list[KnowledgeEntityKind]` | `list[KnowledgeEntityKind]` 元素集合；元素代表的业务对象由参数名 `kinds` 和调用位置确定。 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。 |

**输出**

- **Python 类型**：`list[KnowledgeEntityRecord]`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
计算数量、边界或类型判断结果，并把结果记为 该调用返回的结果；计算初始化顺序集合，并保存为 当前处理结果；将 调用参数集合 初始化为空列表，用来收集后续结果。
如果当前处理结果有值或为真，就调用 `join` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；把新的处理结果追加或合并到当前处理结果；把当前处理结果追加或合并到调用参数集合。
如果检索词或规范化术语集合有值或为真：
    将 当前处理结果 初始化为空列表，用来收集后续结果。
    遍历当前可迭代输入，每次把当前项记为检索词或规范化术语，然后把新的处理结果追加或合并到当前处理结果；调用 `replace` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；计算根据字段和固定文本生成格式化文本，并保存为 文本匹配模式；把新的处理结果追加或合并到调用参数集合。
    把新的处理结果追加或合并到当前处理结果。
把当前处理结果追加或合并到调用参数集合；计算根据字段和固定文本生成格式化文本，并保存为 语义检索问题。
在上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”中调用 `fetchall` 完成该函数的一项辅助处理，并把结果记为 数据库记录行集合，退出时自动清理资源。
返回当前计算得到的结果。
```

#### `SqliteKnowledgeRepository.relations_for_entities`

- **源码**：`app/knowledge_base/repository.py:622`
- **签名**：`def relations_for_entities(self: 未显式标注, entity_ids: list[str], include_candidates: bool, limit: int) -> list[KnowledgeRelationRecord]`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收知识库实体 ID 集合、是否包含候选证据的开关、结果数量上限，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `entity_ids` | `list[str]` | 知识库实体 ID 集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `include_candidates` | `bool` | 布尔条件或能力开关，用于控制流程分支。 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。 |

**输出**

- **Python 类型**：`list[KnowledgeRelationRecord]`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
读取前一步操作返回对象中的对应字段，并保存为 后续步骤使用的结果。
如果当前处理结果为空或为假，就返回当前构造的顺序或去重集合。
调用 `join` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；计算初始化顺序集合，并保存为 当前处理结果。
如果是否包含候选证据的开关有值或为真，就把新的处理结果追加或合并到当前处理结果。
调用 `join` 完成该函数的一项辅助处理，并把结果记为 状态集合；计算初始化顺序集合，并保存为 调用参数集合；把新的处理结果追加或合并到调用参数集合；计算根据字段和固定文本生成格式化文本，并保存为 语义检索问题。
在上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”中调用 `fetchall` 完成该函数的一项辅助处理，并把结果记为 数据库记录行集合，退出时自动清理资源。
返回当前计算得到的结果。
```

#### `SqliteKnowledgeRepository.active_entities_by_ids`

- **源码**：`app/knowledge_base/repository.py:657`
- **签名**：`def active_entities_by_ids(self: 未显式标注, entity_ids: list[str], limit: int) -> list[KnowledgeEntityRecord]`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收知识库实体 ID 集合、结果数量上限，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `entity_ids` | `list[str]` | 知识库实体 ID 集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。 |

**输出**

- **Python 类型**：`list[KnowledgeEntityRecord]`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
读取前一步操作返回对象中的对应字段，并保存为 后续步骤使用的结果。
如果当前处理结果为空或为假，就返回当前构造的顺序或去重集合。
调用 `join` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；计算初始化顺序集合，并保存为 调用参数集合；计算根据字段和固定文本生成格式化文本，并保存为 语义检索问题。
在上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”中调用 `fetchall` 完成该函数的一项辅助处理，并把结果记为 数据库记录行集合，退出时自动清理资源。
返回当前计算得到的结果。
```

#### `SqliteKnowledgeRepository.provenance_for_subjects`

- **源码**：`app/knowledge_base/repository.py:684`
- **签名**：`def provenance_for_subjects(self: 未显式标注, subject_ids: list[str], limit: int) -> list[KnowledgeProvenanceRecord]`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收当前处理结果、结果数量上限，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `subject_ids` | `list[str]` | `list[str]` 元素集合；元素代表的业务对象由参数名 `subject_ids` 和调用位置确定。 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。 |

**输出**

- **Python 类型**：`list[KnowledgeProvenanceRecord]`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
读取前一步操作返回对象中的对应字段，并保存为 后续步骤使用的结果。
如果当前处理结果为空或为假，就返回当前构造的顺序或去重集合。
调用 `join` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；计算初始化顺序集合，并保存为 调用参数集合；计算根据字段和固定文本生成格式化文本，并保存为 语义检索问题。
在上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”中调用 `fetchall` 完成该函数的一项辅助处理，并把结果记为 数据库记录行集合，退出时自动清理资源。
返回当前计算得到的结果。
```

#### `SqliteKnowledgeRepository.create_candidate_relation`

- **源码**：`app/knowledge_base/repository.py:707`
- **签名**：`def create_candidate_relation(self: 未显式标注, relation: KnowledgeRelationRecord, provenance: list[KnowledgeProvenanceRecord], expected_entity_hashes: dict[str, str], idempotency_key: str, request_hash: str) -> tuple[KnowledgeRelationRecord, bool]`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收领域关系、证据来源与追溯信息、期望集合、请求幂等键等输入，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `relation` | `KnowledgeRelationRecord` | 领域关系；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `provenance` | `list[KnowledgeProvenanceRecord]` | 证据来源与追溯信息；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `expected_entity_hashes` | `dict[str, str]` | 调用方观察到的旧身份，用于 stale/CAS 校验，防止覆盖并发更新。 |
| `idempotency_key` | `str` | 调用方提供的幂等键；重复请求应复用同一结果，而不是再次产生副作用。 |
| `request_hash` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |

**输出**

- **Python 类型**：`tuple[KnowledgeRelationRecord, bool]`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
调用 `validate_relation_hash` 校验当前输入或状态。
如果当前状态不等于'candidate'，就拒绝继续处理并抛出 `KnowledgeConflictError`，向调用方报告输入或运行失败。
计算初始化去重集合，并保存为 当前处理结果。
如果辅助操作“构造临时集合、映射或轻量领域对象”的结果不等于当前处理结果，就拒绝继续处理并抛出 `KnowledgeConflictError`，向调用方报告输入或运行失败。
如果证据来源与追溯信息为空或为假，就拒绝继续处理并抛出 `KnowledgeConflictError`，向调用方报告输入或运行失败。
进入上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”，退出时自动清理资源：
    通过数据库连接执行数据查询或命令；调用 `_replay` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
    如果当前处理结果不为空，就返回当前构造的顺序或去重集合。
    遍历辅助操作产生的可迭代结果（调用 `items` 完成该函数的一项辅助处理），每次把当前项记为多个解包结果：
        调用 `fetchone` 完成该函数的一项辅助处理，并把结果记为 数据库记录行。
        如果数据库记录行为空，就拒绝继续处理并抛出 `KnowledgeNotFoundError`，向调用方报告输入或运行失败。
        如果前一步操作返回对象的领域记录的 Hash不等于调用方看到的旧内容 Hash，就拒绝继续处理并抛出 `KnowledgeStaleReviewError`，向调用方报告输入或运行失败。
    调用 `join` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `fetchall` 完成该函数的一项辅助处理，并把结果记为 记录行集合集合；将 当前处理结果 初始化为空映射，用来收集后续结果。
    遍历由记录行集合集合组成的集合或迭代器，每次把当前项记为数据库记录行，然后调用 `_provenance` 完成该函数的一项辅助处理，并把结果记为 当前处理项；把新的处理结果追加或合并到辅助操作“把新的处理结果追加或合并到当前处理结果”的结果。
    将 当前处理结果 初始化为空去重集合，用来收集后续结果。
    遍历由证据来源与追溯信息组成的集合或迭代器，每次把当前项记为当前处理项：
        调用 `validate_provenance_hash` 校验当前输入或状态。
        如果当前处理结果的 ID不等于领域关系的 ID，就拒绝继续处理并抛出 `KnowledgeConflictError`，向调用方报告输入或运行失败。
        遍历并筛选输入，将整理后的结果保存为 候选项集合；遍历并筛选输入，将整理后的结果保存为 当前处理结果。
        如果当前处理结果为空或为假，就拒绝继续处理并抛出 `KnowledgeConflictError`，向调用方报告输入或运行失败。
        把当前处理结果追加或合并到当前处理结果。
    如果当前处理结果不等于当前处理结果，就拒绝继续处理并抛出 `KnowledgeConflictError`，向调用方报告输入或运行失败。
    调用 `_insert_relation` 持久化或更新当前领域数据；调用 `fetchone` 完成该函数的一项辅助处理，并把结果记为 已存储记录行。
    如果已存储记录行为空，就拒绝继续处理并抛出 `KnowledgeIntegrityError`，向调用方报告输入或运行失败。
    调用 `_relation` 完成该函数的一项辅助处理，并把结果记为 已存储关系。
    遍历由证据来源与追溯信息组成的集合或迭代器，每次把当前项记为当前处理项，然后调用 `_insert_provenance` 持久化或更新当前领域数据。
    调用 `_save_operation` 持久化或更新当前领域数据；提交数据库连接中已完成的数据变更。
返回当前构造的顺序或去重集合。
```

#### `SqliteKnowledgeRepository.replace_relation`

- **源码**：`app/knowledge_base/repository.py:826`
- **签名**：`def replace_relation(self: 未显式标注, relation: KnowledgeRelationRecord, expected_version: int, expected_hash: str, idempotency_key: str, request_hash: str) -> tuple[KnowledgeRelationRecord, bool]`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收领域关系、调用方看到的旧版本号、调用方看到的旧内容 Hash、请求幂等键等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `relation` | `KnowledgeRelationRecord` | 领域关系；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `expected_version` | `int` | 调用方观察到的旧身份，用于 stale/CAS 校验，防止覆盖并发更新。 |
| `expected_hash` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |
| `idempotency_key` | `str` | 调用方提供的幂等键；重复请求应复用同一结果，而不是再次产生副作用。 |
| `request_hash` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |

**输出**

- **Python 类型**：`tuple[KnowledgeRelationRecord, bool]`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
调用 `validate_relation_hash` 校验当前输入或状态。
进入上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”，退出时自动清理资源：
    通过数据库连接执行数据查询或命令；调用 `_replay` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
    如果当前处理结果不为空，就返回当前构造的顺序或去重集合。
    调用 `fetchone` 完成该函数的一项辅助处理，并把结果记为 数据库记录行。
    如果数据库记录行为空，就拒绝继续处理并抛出 `KnowledgeNotFoundError`，向调用方报告输入或运行失败。
    调用 `_relation` 完成该函数的一项辅助处理，并把结果记为 当前值。
    如果记录版本号不等于调用方看到的旧版本号 或 领域关系的 Hash不等于调用方看到的旧内容 Hash，就拒绝继续处理并抛出 `KnowledgeStaleReviewError`，向调用方报告输入或运行失败。
    如果记录版本号不等于记录版本号 + 1，就拒绝继续处理并抛出 `KnowledgeConflictError`，向调用方报告输入或运行失败。
    读取前一步操作返回对象的当前处理结果，并保存为 发生变化的内容。
    如果发生变化的内容不等于1，就拒绝继续处理并抛出 `KnowledgeStaleReviewError`，向调用方报告输入或运行失败。
    调用 `_save_operation` 持久化或更新当前领域数据；提交数据库连接中已完成的数据变更。
返回当前构造的顺序或去重集合。
```

#### `SqliteKnowledgeRepository.archive_ingestion`

- **源码**：`app/knowledge_base/repository.py:899`
- **签名**：`def archive_ingestion(self: 未显式标注, ingestion_id: str, actor: str, reason: str, idempotency_key: str, request_hash: str) -> tuple[KnowledgeIngestionRecord, bool]`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收当前处理结果的 ID、审计主体、基线接受或运行操作原因、请求幂等键等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `ingestion_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `actor` | `str` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `reason` | `str` | 来源、类别、用途、后端、状态或操作原因等控制字段；通常对应有限的业务枚举或审计文本。 |
| `idempotency_key` | `str` | 调用方提供的幂等键；重复请求应复用同一结果，而不是再次产生副作用。 |
| `request_hash` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |

**输出**

- **Python 类型**：`tuple[KnowledgeIngestionRecord, bool]`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
进入上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”，退出时自动清理资源：
    通过数据库连接执行数据查询或命令；调用 `_replay` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
    如果当前处理结果不为空，就返回当前构造的顺序或去重集合。
    调用 `fetchone` 完成该函数的一项辅助处理，并把结果记为 数据库记录行。
    如果数据库记录行为空，就拒绝继续处理并抛出 `KnowledgeNotFoundError`，向调用方报告输入或运行失败。
    调用 `_ingestion` 完成该函数的一项辅助处理，并把结果记为 当前值。
    如果当前状态等于'archived'：
        读取当前值，并保存为 记录。
    否则：
        如果当前状态不等于'active'，就拒绝继续处理并抛出 `KnowledgeConflictError`，向调用方报告输入或运行失败；否则复制、序列化或校验结构化领域对象，并把结果记为 记录；通过数据库连接执行数据查询或命令。
    调用 `_save_operation` 持久化或更新当前领域数据；提交数据库连接中已完成的数据变更。
返回当前构造的顺序或去重集合。
```

#### `SqliteKnowledgeRepository.active_referenced_job_ids`

- **源码**：`app/knowledge_base/repository.py:968`
- **签名**：`def active_referenced_job_ids(self) -> set[str]`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`set[str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
在上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”中调用 `fetchall` 完成该函数的一项辅助处理，并把结果记为 数据库记录行集合，退出时自动清理资源。
返回当前计算得到的结果。
```

### `app/knowledge_base/retrieval.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `knowledge_terms`

- **源码**：`app/knowledge_base/retrieval.py:22`
- **签名**：`def knowledge_terms(value: str) -> list[str]`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`list[str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
调用 `normalize_knowledge_key` 解析、规范化或转换当前输入，并把结果记为 规范化后的文本；构造临时集合、映射或轻量领域对象，并把结果记为 阶段处理结果。
遍历辅助操作产生的可迭代结果（构造临时集合、映射或轻量领域对象），每次把当前项记为模型或命令 token：
    如果由模型或命令 token组成的集合或迭代器中存在满足“当前输入内容不大于当前处理结果不大于'\u9fff'”的项，就把新的处理结果追加或合并到阶段处理结果。
按稳定规则整理结果顺序，并返回处理结果。
```

#### `entity_similarity`

- **源码**：`app/knowledge_base/retrieval.py:35`
- **签名**：`def entity_similarity(query: str, entity: KnowledgeEntityRecord) -> tuple[float, list[str]]`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收语义检索问题、知识库实体记录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `query` | `str` | 用户目标、检索问题、反馈或待处理文本；会作为当前阶段的业务语境输入，并可能受到长度/脱敏约束。 |
| `entity` | `KnowledgeEntityRecord` | 知识库实体记录；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`tuple[float, list[str]]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
构造临时集合、映射或轻量领域对象，并把结果记为 查询；构造临时集合、映射或轻量领域对象，并把结果记为 该调用返回的结果。
如果查询为空或为假 或 当前处理结果为空或为假，就返回当前构造的顺序或去重集合。
按稳定规则整理结果顺序，并把结果记为 该调用返回的结果；计算组合或计算已有值，并保存为 当前处理结果；计算组合或计算已有值，并保存为 当前处理结果；调用 `normalize_knowledge_key` 解析、规范化或转换当前输入，并把结果记为 规范化查询。
计算根据条件从两个候选结果中选择一个，并保存为 当前处理结果；计算根据条件从两个候选结果中选择一个，并保存为 当前处理结果；计算数量、边界或类型判断结果，并把结果记为 评测或排序分数；返回当前构造的顺序或去重集合。
```

#### `KnowledgeRetriever.__init__`

- **源码**：`app/knowledge_base/retrieval.py:69`
- **签名**：`def __init__(self, repository: KnowledgeRepository) -> None`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收持久化仓库，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `repository` | `KnowledgeRepository` | 持久化或目录访问端口；负责读取、CAS 更新或 Artifact 定位。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 持久化仓库 分别保存到同名实例字段。
```

#### `KnowledgeRetriever.query`

- **源码**：`app/knowledge_base/retrieval.py:72`
- **签名**：`def query(self, request: KnowledgeQueryRequest) -> KnowledgeQueryPack`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收业务请求，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `KnowledgeQueryPack` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `request` | `KnowledgeQueryRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`KnowledgeQueryPack`
- **语义**：返回 `KnowledgeQueryPack` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `knowledge_terms` 完成该函数的一项辅助处理，并把结果记为 检索词或规范化术语集合；调用 `search_entities` 读取或查询当前阶段需要的数据，并把结果记为 该调用返回的结果；将 当前处理结果 初始化为空列表，用来收集后续结果。
遍历由当前处理结果组成的集合或迭代器，每次把当前项记为知识库实体记录：
    调用 `entity_similarity` 完成该函数的一项辅助处理，并把结果记为 多个解包结果。
    如果评测或排序分数大于0，就把新的处理结果追加或合并到当前处理结果。
按稳定规则整理结果顺序；遍历并筛选输入，将整理后的结果保存为 选中的候选项；构造临时集合、映射或轻量领域对象，并把结果记为 该调用返回的结果；将 当前处理结果 初始化为空映射，用来收集后续结果。
计算计算当前表达式的结果，并保存为 当前处理结果。
遍历限定范围内的序列，每次把当前项记为当前遍历深度：
    如果当前处理结果为空或为假 或 当前处理结果 的长度不小于最大当前处理结果，就立即结束当前循环。
    调用 `relations_for_entities` 完成该函数的一项辅助处理，并把结果记为 论文页码；将 下一项集合 初始化为空去重集合，用来收集后续结果。
    遍历由论文页码组成的集合或迭代器，每次把当前项记为领域关系，然后读取领域关系，并保存为 当前处理结果中的对应字段；把新的处理结果追加或合并到下一项集合。
    将新的计算结果累加或合并到下一项集合；计算组合或计算已有值，并保存为 当前处理结果。
    如果当前处理结果不大于0，就计算计算当前表达式的结果，并保存为 当前处理结果；立即结束当前循环。
    调用 `active_entities_by_ids` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
    遍历由当前处理结果组成的集合或迭代器，每次把当前项记为知识库实体记录，然后构造 `KnowledgeEntityHit` 结构化领域对象，并把结果记为 选中的候选项中的对应字段。
    如果当前处理结果 的长度小于下一项集合 的长度，就计算使用固定配置或常量值，并保存为 当前处理结果。
    遍历并筛选输入，将整理后的结果保存为 当前处理结果。
按稳定规则整理结果顺序，并把结果记为 该调用返回的结果；构造临时集合、映射或轻量领域对象，并把结果记为 该调用返回的结果；遍历并筛选输入，将整理后的结果保存为 当前处理结果。
如果当前处理结果 的长度不等于当前处理结果 的长度，就计算使用固定配置或常量值，并保存为 当前处理结果。
按稳定规则整理结果顺序，并把结果记为 该调用返回的结果；遍历并筛选输入，将整理后的结果保存为 当前处理结果；遍历并筛选输入，将整理后的结果保存为 候选结果集合；计算组合或计算已有值，并保存为 当前处理结果。
调用 `provenance_for_subjects` 完成该函数的一项辅助处理，并把结果记为 证据来源与追溯信息；遍历并筛选输入，将整理后的结果保存为 可追溯证据记录；将 当前处理结果 初始化为空映射，用来收集后续结果。
遍历由证据来源与追溯信息组成的集合或迭代器，每次把当前项记为当前处理项，然后把新的处理结果追加或合并到辅助操作“把当前处理结果的 ID追加或合并到当前处理结果”的结果。
调用 `sha256_value` 计算内容身份、分数或派生结果，并把结果记为 语义检索问题的 Hash；构造 `KnowledgeQueryPack` 结构化领域对象，并把结果记为 草稿对象；调用 `sha256_value` 计算内容身份、分数或派生结果，并把结果记为 检索或映射证据包的 Hash；复制、序列化或校验结构化领域对象，并返回处理结果。
```

### `app/knowledge_base/schemas.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `KnowledgeEvidenceRef.validate_artifact_path`

- **源码**：`app/knowledge_base/schemas.py:94`
- **签名**：`def validate_artifact_path(cls, value: str) -> str`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收当前字段值，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `cls` | `未显式标注` | 当前类对象，用于类级构造或校验。 |
| `value` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
构造 `PurePosixPath` 结构化领域对象，并把结果记为 文件或目录路径。
如果“调用 `is_absolute` 校验当前输入或状态”后得到肯定结果 或 当前输入内容属于拆分后的文本或路径片段集合 或 当前输入内容属于当前字段值，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前字段值的当前值。
```

#### `KnowledgeEvidenceRef.validate_file_path`

- **源码**：`app/knowledge_base/schemas.py:102`
- **签名**：`def validate_file_path(cls, value: str | None) -> str | None`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收当前字段值，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `str | None` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `cls` | `未显式标注` | 当前类对象，用于类级构造或校验。 |
| `value` | `str | None` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str | None`
- **语义**：返回 `str | None` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果当前字段值为空，就返回固定值 `空值`。
构造 `PurePosixPath` 结构化领域对象，并把结果记为 文件或目录路径。
如果“调用 `is_absolute` 校验当前输入或状态”后得到肯定结果 或 当前输入内容属于拆分后的文本或路径片段集合 或 当前输入内容属于当前字段值，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前字段值的当前值。
```

#### `KnowledgeEvidenceRef.validate_locator_shape`

- **源码**：`app/knowledge_base/schemas.py:111`
- **签名**：`def validate_locator_shape(self) -> "KnowledgeEvidenceRef"`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `'KnowledgeEvidenceRef'` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`'KnowledgeEvidenceRef'`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
如果页码有值或为真 且 页码有值或为真 且 页码小于页码，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果源码起始行号有值或为真 且 源码结束行号有值或为真 且 源码结束行号小于源码起始行号，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
计算组合多个值形成元组，并保存为 论文集合；计算组合多个值形成元组，并保存为 当前处理结果。
如果业务类别等于'paper_artifact'：
    如果由论文集合组成的集合或迭代器中存在满足“当前字段值为空”的项，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    如果由当前处理结果组成的集合或迭代器中存在满足“当前字段值不为空”的项，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
否则：
    如果由当前处理结果组成的集合或迭代器中存在满足“当前字段值为空”的项，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    计算组合或计算已有值，并保存为 论文集合。
    如果由论文集合组成的集合或迭代器中存在满足“当前字段值不为空”的项，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前对象的当前值。
```

#### `KnowledgeRelationRecord.validate_lifecycle_shape`

- **源码**：`app/knowledge_base/schemas.py:179`
- **签名**：`def validate_lifecycle_shape(self) -> "KnowledgeRelationRecord"`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`'KnowledgeRelationRecord'`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
如果来源的 ID等于当前处理结果的 ID，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果当前状态等于'asserted'：
    如果职责权限不属于{'deterministic_source', 'verified_run'}，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    如果当前可迭代输入中存在满足“当前字段值不为空”的项，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
否则：
    如果当前状态等于'candidate'：
        如果职责权限不属于{'model_candidate', 'deterministic_similarity'}，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
        如果基线审核人标识不为空，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
        如果“原因有值或为真”不成立，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    否则：
        如果基线审核人标识为空 或 “原因有值或为真”不成立，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
        如果职责权限不等于'explicit_user'，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
        如果“原因有值或为真”不成立，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前对象的当前值。
```

#### `KnowledgeProvenanceRecord.validate_subject_prefix`

- **源码**：`app/knowledge_base/schemas.py:230`
- **签名**：`def validate_subject_prefix(self) -> "KnowledgeProvenanceRecord"`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`'KnowledgeProvenanceRecord'`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
计算根据条件从两个候选结果中选择一个，并保存为 期望值。
如果“检查当前处理结果的 ID是否满足文本匹配条件”后未得到肯定结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前对象的当前值。
```

#### `KnowledgeIngestionRecord.validate_archive_shape`

- **源码**：`app/knowledge_base/schemas.py:267`
- **签名**：`def validate_archive_shape(self) -> "KnowledgeIngestionRecord"`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`'KnowledgeIngestionRecord'`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
计算组合多个值形成元组，并保存为 当前处理结果。
如果当前状态等于'archived'：
    如果由当前处理结果组成的集合或迭代器中存在满足“当前字段值为空”的项，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
否则：
    如果由当前处理结果组成的集合或迭代器中存在满足“当前字段值不为空”的项，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前对象的当前值。
```

#### `KnowledgeEquivalenceProposalRequest.validate_distinct_entities`

- **源码**：`app/knowledge_base/schemas.py:321`
- **签名**：`def validate_distinct_entities(self: 未显式标注) -> 'KnowledgeEquivalenceProposalRequest'`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `'KnowledgeEquivalenceProposalRequest'` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`'KnowledgeEquivalenceProposalRequest'`
- **语义**：返回 `'KnowledgeEquivalenceProposalRequest'` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果来源的 ID等于当前处理结果的 ID，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前对象的当前值。
```

### `app/knowledge_base/service.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `KnowledgeService.__init__`

- **源码**：`app/knowledge_base/service.py:45`
- **签名**：`def __init__(self: 未显式标注, repository: KnowledgeRepository, source_reader: KnowledgeSourceReader, projector: KnowledgeProjector, retriever: KnowledgeRetriever, minimum_equivalence_score: float) -> None`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收持久化仓库、来源读取器、领域记录投影器、证据检索器等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `repository` | `KnowledgeRepository` | 持久化或目录访问端口；负责读取、CAS 更新或 Artifact 定位。 |
| `source_reader` | `KnowledgeSourceReader` | 只读证据或数据读取端口；负责把外部持久化内容投影为受约束领域输入。 |
| `projector` | `KnowledgeProjector` | 领域记录投影器；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `retriever` | `KnowledgeRetriever` | 检索服务或端口；返回有界候选及可解释排序信息，不授予执行权限。 |
| `minimum_equivalence_score` | `float` | 名为 `minimum_equivalence_score` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 持久化仓库、来源读取器、领域记录投影器、证据检索器、分数 分别保存到同名实例字段。
```

#### `KnowledgeService.ingest`

- **源码**：`app/knowledge_base/service.py:60`
- **签名**：`def ingest(self: 未显式标注, job_id: str, actor: str, idempotency_key: str) -> KnowledgeIngestResponse`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收复现任务 ID、审计主体、请求幂等键，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `actor` | `str` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `idempotency_key` | `str` | 调用方提供的幂等键；重复请求应复用同一结果，而不是再次产生副作用。 |

**输出**

- **Python 类型**：`KnowledgeIngestResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `read` 完成该函数的一项辅助处理，并把结果记为 代码仓库归档包；调用 `project` 完成该函数的一项辅助处理，并把结果记为 当前批次记录集合；调用 `graph_batch_hash` 完成该函数的一项辅助处理，并把结果记为 当前批次记录集合的 Hash；调用 `sha256_value` 计算内容身份、分数或派生结果，并把结果记为 请求内容 Hash。
构造 `KnowledgeIngestionRecord` 结构化领域对象，并把结果记为 该调用返回的结果；调用 `ingest_batch` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；构造并返回 `KnowledgeIngestResponse` 结构化领域对象。
```

#### `KnowledgeService.query`

- **源码**：`app/knowledge_base/service.py:105`
- **签名**：`def query(self, request: KnowledgeQueryRequest) -> KnowledgeQueryPack`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收业务请求，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `KnowledgeQueryPack` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `request` | `KnowledgeQueryRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`KnowledgeQueryPack`
- **语义**：返回 `KnowledgeQueryPack` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `query` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `KnowledgeService.propose_equivalence`

- **源码**：`app/knowledge_base/service.py:108`
- **签名**：`def propose_equivalence(self: 未显式标注, request: KnowledgeEquivalenceProposalRequest, idempotency_key: str) -> KnowledgeRelationMutationResponse`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收业务请求、请求幂等键，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `request` | `KnowledgeEquivalenceProposalRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `idempotency_key` | `str` | 调用方提供的幂等键；重复请求应复用同一结果，而不是再次产生副作用。 |

**输出**

- **Python 类型**：`KnowledgeRelationMutationResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `get_entity` 读取或查询当前阶段需要的数据，并把结果记为 数据来源标记；调用 `get_entity` 读取或查询当前阶段需要的数据，并把结果记为 待定位的代码对象或业务目标。
如果领域记录的 Hash不等于期望来源的 Hash 或 领域记录的 Hash不等于期望的 Hash，就拒绝继续处理并抛出 `KnowledgeConflictError`，向调用方报告输入或运行失败。
如果业务类别不等于业务类别 或 业务类别不属于当前处理结果，就拒绝继续处理并抛出 `KnowledgeConflictError`，向调用方报告输入或运行失败。
如果键等于键，就拒绝继续处理并抛出 `KnowledgeConflictError`，向调用方报告输入或运行失败。
调用 `entity_similarity` 完成该函数的一项辅助处理，并把结果记为 多个解包结果。
如果评测或排序分数小于分数，就拒绝继续处理并抛出 `KnowledgeConflictError`，向调用方报告输入或运行失败。
按稳定规则整理结果顺序，并把结果记为 多个解包结果；读取当前时间，作为状态变更的统一时间戳，并把结果记为 当前时间；构造 `KnowledgeRelationRecord` 结构化领域对象，并把结果记为 草稿对象；复制、序列化或校验结构化领域对象，并把结果记为 领域关系。
调用 `provenance_for_subjects` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；遍历并筛选输入，将整理后的结果保存为 当前处理结果。
如果当前处理结果不等于{知识库实体记录的 ID, 知识库实体记录的 ID}，就拒绝继续处理并抛出 `KnowledgeIntegrityError`，向调用方报告输入或运行失败。
将 关系 初始化为空列表，用来收集后续结果。
遍历由当前处理结果组成的集合或迭代器，每次把当前项记为当前处理项，然后构造 `KnowledgeProvenanceRecord` 结构化领域对象，并把结果记为 待审核的 MCP 能力候选；把新的处理结果追加或合并到关系。
调用 `sha256_value` 计算内容身份、分数或派生结果，并把结果记为 请求内容 Hash；调用 `create_candidate_relation` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果；构造并返回 `KnowledgeRelationMutationResponse` 结构化领域对象。
```

#### `KnowledgeService.review_relation`

- **源码**：`app/knowledge_base/service.py:217`
- **签名**：`def review_relation(self: 未显式标注, relation_id: str, request: KnowledgeRelationReviewRequest, actor: str, idempotency_key: str) -> KnowledgeRelationMutationResponse`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收领域关系的 ID、业务请求、审计主体、请求幂等键，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `relation_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `request` | `KnowledgeRelationReviewRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `actor` | `str` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `idempotency_key` | `str` | 调用方提供的幂等键；重复请求应复用同一结果，而不是再次产生副作用。 |

**输出**

- **Python 类型**：`KnowledgeRelationMutationResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `sha256_value` 计算内容身份、分数或派生结果，并把结果记为 请求内容 Hash；调用 `get_relation` 读取或查询当前阶段需要的数据，并把结果记为 当前值。
如果记录版本号不等于调用方看到的旧版本号 或 领域关系的 Hash不等于期望关系的 Hash，就调用 `replace_relation` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；构造并返回 `KnowledgeRelationMutationResponse` 结构化领域对象。
先尝试完成以下处理：
    调用 `reviewed_relation` 完成该函数的一项辅助处理，并把结果记为 更新后的记录。
如果出现 `ValueError`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `KnowledgeConflictError`，向调用方报告输入或运行失败。
调用 `replace_relation` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；构造并返回 `KnowledgeRelationMutationResponse` 结构化领域对象。
```

#### `KnowledgeService.archive_ingestion`

- **源码**：`app/knowledge_base/service.py:272`
- **签名**：`def archive_ingestion(self: 未显式标注, ingestion_id: str, actor: str, reason: str, idempotency_key: str) -> KnowledgeIngestionRecord`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收当前处理结果的 ID、审计主体、基线接受或运行操作原因、请求幂等键，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `ingestion_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `actor` | `str` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `reason` | `str` | 来源、类别、用途、后端、状态或操作原因等控制字段；通常对应有限的业务枚举或审计文本。 |
| `idempotency_key` | `str` | 调用方提供的幂等键；重复请求应复用同一结果，而不是再次产生副作用。 |

**输出**

- **Python 类型**：`KnowledgeIngestionRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
调用 `sha256_value` 计算内容身份、分数或派生结果，并把结果记为 请求内容 Hash；调用 `archive_ingestion` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；返回领域记录的当前值。
```

### `app/knowledge_base/source_reader.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `KnowledgeSourceReader.__init__`

- **源码**：`app/knowledge_base/source_reader.py:54`
- **签名**：`def __init__(self: 未显式标注, verified_runs: VerifiedRunEvidenceReader, artifact_catalog: ArtifactCatalog, max_artifact_bytes: int, max_sections: int, max_facts: int, max_mappings: int) -> None`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收当前处理结果、Artifact、最大Artifact的字节内容、最大论文文档章节集合等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `verified_runs` | `VerifiedRunEvidenceReader` | 名为 `verified_runs` 的 `VerifiedRunEvidenceReader` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `artifact_catalog` | `ArtifactCatalog` | 名为 `artifact_catalog` 的 `ArtifactCatalog` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `max_artifact_bytes` | `int` | 名为 `max_artifact_bytes` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `max_sections` | `int` | 名为 `max_sections` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `max_facts` | `int` | 名为 `max_facts` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `max_mappings` | `int` | 名为 `max_mappings` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 当前处理结果、Artifact、最大Artifact的字节内容、最大论文文档章节集合、最大项目事实记录集合、最大当前处理结果 分别保存到同名实例字段。
```

#### `KnowledgeSourceReader._artifact_map`

- **源码**：`app/knowledge_base/source_reader.py:72`
- **签名**：`def _artifact_map(evidence: VerifiedRunEvidence) -> dict[str, ArtifactView]`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收可追溯证据记录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `evidence` | `VerifiedRunEvidence` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |

**输出**

- **Python 类型**：`dict[str, ArtifactView]`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
遍历并筛选输入，将整理后的结果保存为 阶段处理结果。
如果阶段处理结果 的长度不等于当前处理结果 的长度，就拒绝继续处理并抛出 `KnowledgeIntegrityError`，向调用方报告输入或运行失败。
计算组合或计算已有值，并保存为 当前处理结果。
如果当前处理结果有值或为真，就拒绝继续处理并抛出 `KnowledgeNotFoundError`，向调用方报告输入或运行失败。
返回阶段处理结果的当前值。
```

#### `KnowledgeSourceReader._read_json`

- **源码**：`app/knowledge_base/source_reader.py:85`
- **签名**：`def _read_json(self: 未显式标注, evidence: VerifiedRunEvidence, view: ArtifactView) -> Any`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收可追溯证据记录、视图，用于读取并整理论文、源码或运行产物，把原始输入转换成带位置和身份信息的结构化证据，最终标注为 `Any` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `evidence` | `VerifiedRunEvidence` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |
| `view` | `ArtifactView` | 名为 `view` 的 `ArtifactView` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`Any`
- **语义**：返回 `Any` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果对象大小的字节内容大于最大Artifact的字节内容，就拒绝继续处理并抛出 `KnowledgeLimitExceededError`，向调用方报告输入或运行失败。
调用 `open` 完成该函数的一项辅助处理，并把结果记为 已打开资源。
先尝试完成以下处理：
    读取工具或组件描述信息，并保存为 工具或组件描述信息；读取当前处理结果，并保存为 后续步骤使用的结果。
    如果Artifact的 ID不等于Artifact的 ID 或 仓库内相对路径不等于仓库内相对路径 或 本次复现运行 ID不等于本次复现运行 ID 或 内容 SHA-256不等于内容 SHA-256 或 对象大小的字节内容不等于对象大小的字节内容 或 内容 SHA-256不等于内容 SHA-256 或 对象大小的字节内容不等于对象大小的字节内容，就拒绝继续处理并抛出 `KnowledgeIntegrityError`，向调用方报告输入或运行失败。
    调用 `read` 完成该函数的一项辅助处理，并把结果记为 原始内容。
无论成功还是失败，最后都要：
    关闭请求正文并释放相关资源。
如果原始内容 的长度大于最大Artifact的字节内容 或 原始内容 的长度不等于对象大小的字节内容，就拒绝继续处理并抛出 `KnowledgeIntegrityError`，向调用方报告输入或运行失败。
如果辅助操作“计算输入内容的 SHA-256 身份摘要”的结果不等于内容 SHA-256，就拒绝继续处理并抛出 `KnowledgeIntegrityError`，向调用方报告输入或运行失败。
先尝试完成以下处理：
    将外部表示解析为结构化内容，并返回处理结果。
如果出现 `(UnicodeDecodeError, json.JSONDecodeError)`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `KnowledgeIntegrityError`，向调用方报告输入或运行失败。
```

#### `KnowledgeSourceReader._load_model`

- **源码**：`app/knowledge_base/source_reader.py:129`
- **签名**：`def _load_model(self: 未显式标注, evidence: VerifiedRunEvidence, view: ArtifactView, model: type[BaseModel]) -> BaseModel`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收可追溯证据记录、视图、模型标识或模型配置，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `BaseModel` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `evidence` | `VerifiedRunEvidence` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |
| `view` | `ArtifactView` | 名为 `view` 的 `ArtifactView` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `model` | `type[BaseModel]` | 模型标识或模型配置；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`BaseModel`
- **语义**：返回 `BaseModel` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `_read_json` 读取或查询当前阶段需要的数据，并把结果记为 结构化请求载荷。
先尝试完成以下处理：
    复制、序列化或校验结构化领域对象，并返回处理结果。
如果出现 `ValidationError`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `KnowledgeConflictError`，向调用方报告输入或运行失败。
```

#### `KnowledgeSourceReader._load_list`

- **源码**：`app/knowledge_base/source_reader.py:144`
- **签名**：`def _load_list(self: 未显式标注, evidence: VerifiedRunEvidence, view: ArtifactView, model: type[BaseModel], limit: int) -> tuple[BaseModel, ...]`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收可追溯证据记录、视图、模型标识或模型配置、结果数量上限，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `evidence` | `VerifiedRunEvidence` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |
| `view` | `ArtifactView` | 名为 `view` 的 `ArtifactView` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `model` | `type[BaseModel]` | 模型标识或模型配置；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。 |

**输出**

- **Python 类型**：`tuple[BaseModel, ...]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
调用 `_read_json` 读取或查询当前阶段需要的数据，并把结果记为 结构化请求载荷。
如果“计算数量、边界或类型判断结果”后未得到肯定结果，就拒绝继续处理并抛出 `KnowledgeConflictError`，向调用方报告输入或运行失败。
如果结构化请求载荷 的长度大于结果数量上限，就拒绝继续处理并抛出 `KnowledgeLimitExceededError`，向调用方报告输入或运行失败。
先尝试完成以下处理：
    构造临时集合、映射或轻量领域对象，并返回处理结果。
如果出现 `ValidationError`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `KnowledgeConflictError`，向调用方报告输入或运行失败。
```

#### `KnowledgeSourceReader._paper_sha256`

- **源码**：`app/knowledge_base/source_reader.py:169`
- **签名**：`def _paper_sha256(evidence: VerifiedRunEvidence) -> str`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收可追溯证据记录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `evidence` | `VerifiedRunEvidence` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回输入内容的 SHA-256 身份摘要，用于完整性校验，不是加密后的正文。

**伪代码**

```text
遍历并筛选输入，将整理后的结果保存为 记录条目集合。
如果记录条目集合 的长度不等于1，就拒绝继续处理并抛出 `KnowledgeIntegrityError`，向调用方报告输入或运行失败。
返回内容 SHA-256的当前值。
```

#### `KnowledgeSourceReader.read`

- **源码**：`app/knowledge_base/source_reader.py:179`
- **签名**：`def read(self, job_id: str) -> KnowledgeSourceBundle`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收复现任务 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `KnowledgeSourceBundle` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`KnowledgeSourceBundle`
- **语义**：返回 `KnowledgeSourceBundle` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `read` 完成该函数的一项辅助处理，并把结果记为 可追溯证据记录；调用 `_artifact_map` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `_load_model` 读取或查询当前阶段需要的数据，并把结果记为 论文解析文档；断言“计算数量、边界或类型判断结果”后得到肯定结果；不满足就终止当前测试或流程。
如果数据来源标记的 SHA-256不等于辅助操作“调用 `_paper_sha256` 计算内容身份、分数或派生结果”的结果，就拒绝继续处理并抛出 `KnowledgeIntegrityError`，向调用方报告输入或运行失败。
调用 `_load_list` 读取或查询当前阶段需要的数据，并把结果记为 论文文档章节集合；调用 `_load_list` 读取或查询当前阶段需要的数据，并把结果记为 项目事实记录集合；调用 `_load_model` 读取或查询当前阶段需要的数据，并把结果记为 阶段摘要；断言“计算数量、边界或类型判断结果”后得到肯定结果；不满足就终止当前测试或流程。
从当前处理结果读取所需的状态或领域记录，并把结果记为 映射视图；计算组合多个值形成元组，并保存为 当前处理结果。
如果映射视图不为空，就调用 `_load_list` 读取或查询当前阶段需要的数据，并把结果记为 该调用返回的结果。
构造临时集合、映射或轻量领域对象，并把结果记为 该调用返回的结果；构造临时集合、映射或轻量领域对象，并把结果记为 该调用返回的结果；构造临时集合、映射或轻量领域对象，并把结果记为 该调用返回的结果。
如果当前处理结果 的长度不等于论文文档章节集合 的长度，就拒绝继续处理并抛出 `KnowledgeIntegrityError`，向调用方报告输入或运行失败。
如果当前处理结果 的长度不等于项目事实记录集合 的长度，就拒绝继续处理并抛出 `KnowledgeIntegrityError`，向调用方报告输入或运行失败。
如果当前处理结果 的长度不等于当前处理结果 的长度，就拒绝继续处理并抛出 `KnowledgeIntegrityError`，向调用方报告输入或运行失败。
遍历并筛选输入，将整理后的结果保存为 章节集合。
如果章节集合 的长度不等于当前处理结果 的长度，就拒绝继续处理并抛出 `KnowledgeIntegrityError`，向调用方报告输入或运行失败。
如果由当前处理结果组成的集合或迭代器中存在满足“论文解析文档的 ID不等于论文解析文档的 ID 或 论文文档章节的 ID不属于章节集合”的项，就拒绝继续处理并抛出 `KnowledgeIntegrityError`，向调用方报告输入或运行失败。
构造并返回 `KnowledgeSourceBundle` 结构化领域对象。
```

### `app/mcp_contracts/baseline.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `utc_now`

- **源码**：`app/mcp_contracts/baseline.py:39`
- **签名**：`def utc_now() -> str`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `isoformat` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `atomic_write_json`

- **源码**：`app/mcp_contracts/baseline.py:43`
- **签名**：`def atomic_write_json(path: Path, payload: dict) -> None`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，临时文件与目标文件同目录，保证不离开项目挂载。该函数接收文件或目录路径、结构化请求载荷，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |
| `payload` | `dict` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
如果“检查文件或目录路径的文件系统属性”后得到肯定结果，就拒绝继续处理并抛出 `McpContractBaselineInvalid`，向调用方报告输入或运行失败。
创建父级目录或父领域对象对应的目录；调用 `with_name` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
先尝试完成以下处理：
    在上下文“调用 `open` 完成该函数的一项辅助处理，并把上下文资源交给当前处理结果”中调用 `dump` 完成该函数的一项辅助处理；向终端或输出流写出当前结果/诊断信息；提交当前处理结果中已完成的数据变更；调用 `fsync` 完成该函数的一项辅助处理，退出时自动清理资源。
    调用 `replace` 完成该函数的一项辅助处理。
无论成功还是失败，最后都要：
    调用 `unlink` 完成该函数的一项辅助处理。
```

#### `atomic_write_text`

- **源码**：`app/mcp_contracts/baseline.py:69`
- **签名**：`def atomic_write_text(path: Path, content: str) -> None`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收文件或目录路径、业务内容，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |
| `content` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
如果“检查文件或目录路径的文件系统属性”后得到肯定结果，就拒绝继续处理并抛出 `McpContractBaselineInvalid`，向调用方报告输入或运行失败。
创建父级目录或父领域对象对应的目录；调用 `with_name` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
先尝试完成以下处理：
    在上下文“调用 `open` 完成该函数的一项辅助处理，并把上下文资源交给当前处理结果”中向终端或输出流写出当前结果/诊断信息；提交当前处理结果中已完成的数据变更；调用 `fsync` 完成该函数的一项辅助处理，退出时自动清理资源。
    调用 `replace` 完成该函数的一项辅助处理。
无论成功还是失败，最后都要：
    调用 `unlink` 完成该函数的一项辅助处理。
```

#### `build_candidate`

- **源码**：`app/mcp_contracts/baseline.py:86`
- **签名**：`def build_candidate(observations: list[McpSurfaceObservation]) -> McpContractCandidate`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收MCP Client 观测结果集合，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `McpContractCandidate` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `observations` | `list[McpSurfaceObservation]` | MCP Client 观测结果集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`McpContractCandidate`
- **语义**：返回 `McpContractCandidate` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果MCP Client 观测结果集合为空或为假，就拒绝继续处理并抛出 `McpContractPromotionRejected`，向调用方报告输入或运行失败。
遍历并筛选输入，将整理后的结果保存为 当前处理结果；计算数量、边界或类型判断结果，并把结果记为 选中的候选项的 Hash；计算按字段初始化键值映射，并保存为 结构化请求载荷；构造 `McpContractCandidate` 结构化领域对象，并把结果记为 待审核的 MCP 能力候选。
复制、序列化或校验结构化领域对象，并返回处理结果。
```

#### `write_candidate`

- **源码**：`app/mcp_contracts/baseline.py:113`
- **签名**：`def write_candidate(path: Path, candidate: McpContractCandidate) -> None`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收文件或目录路径、待审核的 MCP 能力候选，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |
| `candidate` | `McpContractCandidate` | 待审核的 MCP 能力候选；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
如果辅助操作“调用 `candidate_hash` 完成该函数的一项辅助处理”的结果不等于待审核的 MCP 能力候选的 SHA-256，就拒绝继续处理并抛出 `McpContractBaselineInvalid`，向调用方报告输入或运行失败。
调用 `atomic_write_json` 完成该函数的一项辅助处理。
```

#### `load_candidate`

- **源码**：`app/mcp_contracts/baseline.py:119`
- **签名**：`def load_candidate(path: Path) -> McpContractCandidate`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收文件或目录路径，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `McpContractCandidate` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`McpContractCandidate`
- **语义**：返回从外部表示解析并校验后的领域值；格式非法时通过异常失败。

**伪代码**

```text
如果“检查文件或目录路径的文件系统属性”后得到肯定结果，就拒绝继续处理并抛出 `McpContractBaselineInvalid`，向调用方报告输入或运行失败。
先尝试完成以下处理：
    调用 `model_validate_json` 完成该函数的一项辅助处理，并把结果记为 待审核的 MCP 能力候选。
如果出现 `(OSError, UnicodeError, ValueError)`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `McpContractBaselineInvalid`，向调用方报告输入或运行失败。
如果辅助操作“调用 `candidate_hash` 完成该函数的一项辅助处理”的结果不等于待审核的 MCP 能力候选的 SHA-256，就拒绝继续处理并抛出 `McpContractBaselineInvalid`，向调用方报告输入或运行失败。
返回待审核的 MCP 能力候选的当前值。
```

#### `load_baseline`

- **源码**：`app/mcp_contracts/baseline.py:135`
- **签名**：`def load_baseline(path: Path) -> McpContractBaseline`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收文件或目录路径，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `McpContractBaseline` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`McpContractBaseline`
- **语义**：返回从外部表示解析并校验后的领域值；格式非法时通过异常失败。

**伪代码**

```text
如果“检查文件或目录路径的文件系统属性”后得到肯定结果，就拒绝继续处理并抛出 `McpContractBaselineInvalid`，向调用方报告输入或运行失败。
如果“检查文件或目录路径的文件系统属性”后未得到肯定结果，就拒绝继续处理并抛出 `McpContractBaselineMissing`，向调用方报告输入或运行失败。
先尝试完成以下处理：
    调用 `model_validate_json` 完成该函数的一项辅助处理，并把结果记为 已审核的 MCP 能力基线。
如果出现 `(OSError, UnicodeError, ValueError)`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `McpContractBaselineInvalid`，向调用方报告输入或运行失败。
如果辅助操作“调用 `baseline_hash` 完成该函数的一项辅助处理”的结果不等于已审核的 MCP 能力基线的 SHA-256，就拒绝继续处理并抛出 `McpContractBaselineInvalid`，向调用方报告输入或运行失败。
返回已审核的 MCP 能力基线的当前值。
```

#### `promote_candidate`

- **源码**：`app/mcp_contracts/baseline.py:153`
- **签名**：`def promote_candidate(candidate: McpContractCandidate, baseline_path: Path, expected_surface_sha256: str, reviewed_by: str, reason: str, replace: bool, expected_current_baseline_sha256: str | None) -> McpContractBaseline`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，显式 Hash 绑定的人工晋升；绝不根据 drift 自动接受。该函数接收待审核的 MCP 能力候选、MCP 基线文件路径、期望的 SHA-256、基线审核人标识等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `McpContractBaseline` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `candidate` | `McpContractCandidate` | 待审核的 MCP 能力候选；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `baseline_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `expected_surface_sha256` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |
| `reviewed_by` | `str` | 基线审核人标识；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `reason` | `str` | 来源、类别、用途、后端、状态或操作原因等控制字段；通常对应有限的业务枚举或审计文本。 |
| `replace` | `bool` | 布尔条件或能力开关，用于控制流程分支。 |
| `expected_current_baseline_sha256` | `str | None` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |

**输出**

- **Python 类型**：`McpContractBaseline`
- **语义**：返回 `McpContractBaseline` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果“检查MCP 基线文件路径的文件系统属性”后得到肯定结果，就拒绝继续处理并抛出 `McpContractPromotionRejected`，向调用方报告输入或运行失败。
去除基线审核人标识的首尾空白，并把规范化后的文本记为 当前处理结果；调用 `join` 完成该函数的一项辅助处理，并把结果记为 原因。
如果当前处理结果为空或为假 或 原因 的长度小于3，就拒绝继续处理并抛出 `McpContractPromotionRejected`，向调用方报告输入或运行失败。
如果“当前处理结果有值或为真”不成立，就拒绝继续处理并抛出 `McpContractPromotionRejected`，向调用方报告输入或运行失败。
如果MCP 能力表面的 SHA-256不等于期望的 SHA-256，就拒绝继续处理并抛出 `McpContractPromotionRejected`，向调用方报告输入或运行失败。
如果“检查MCP 基线文件路径的文件系统属性”后得到肯定结果：
    如果是否替换现有基线的开关为空或为假，就拒绝继续处理并抛出 `McpContractPromotionRejected`，向调用方报告输入或运行失败。
    调用 `load_baseline` 读取或查询当前阶段需要的数据，并把结果记为 当前值。
    如果期望当前的 SHA-256为空 或 已审核的 MCP 能力基线的 SHA-256不等于期望当前的 SHA-256，就拒绝继续处理并抛出 `McpContractPromotionRejected`，向调用方报告输入或运行失败。
读取MCP 公开能力表面，并保存为 MCP 公开能力表面；按稳定规则整理结果顺序，并把结果记为 该调用返回的结果；计算按字段初始化键值映射，并保存为 结构化请求载荷；构造 `McpContractBaseline` 结构化领域对象，并把结果记为 已审核的 MCP 能力基线。
复制、序列化或校验结构化领域对象，并把结果记为 已审核的 MCP 能力基线；调用 `atomic_write_json` 完成该函数的一项辅助处理；返回已审核的 MCP 能力基线的当前值。
```

### `app/mcp_contracts/commands.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_profiles`

- **源码**：`app/mcp_contracts/commands.py:35`
- **签名**：`def _profiles() -> list[McpClientProfile]`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`list[McpClientProfile]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
调用 `load_client_profiles` 读取或查询当前阶段需要的数据，并返回处理结果。
```

#### `_report_path`

- **源码**：`app/mcp_contracts/commands.py:42`
- **签名**：`def _report_path(path: Path) -> Path`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，所有 Candidate/Eval 输出都必须留在 Phase 55 Report Root。该函数接收文件或目录路径，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个经过边界校验的文件或目录路径。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`Path`
- **语义**：返回解析后的文件或目录路径对象。

**伪代码**

```text
将文件或目录路径规范化为受控的绝对路径，并把结果记为 待审核的 MCP 能力候选。
如果“检查待审核的 MCP 能力候选的文件系统属性”后得到肯定结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
将待审核的 MCP 能力候选规范化为受控的绝对路径，并把结果记为 解析后的值；将契约根目录规范化为受控的绝对路径，并把结果记为 受控扫描根目录。
如果解析后的值等于受控扫描根目录 或 受控扫描根目录不属于当前处理结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回解析后的值的当前值。
```

#### `_resolve_profile_token`

- **源码**：`app/mcp_contracts/commands.py:55`
- **签名**：`def _resolve_profile_token(profile: McpClientProfile) -> str`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收MCP Client 配置档案，用于把论文中的方法、模块或实验意图与仓库中的可验证对象建立稳定关联，并保留匹配依据，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `profile` | `McpClientProfile` | 运行/执行环境配置或 profile 标识；描述能力和限制，不是一次执行的结果。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
如果敏感凭据的名称为空，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
调用 `resolve_current` 解析、规范化或转换当前输入，并把结果记为 待处理的论文或源码材料；调用 `reveal` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `_observe_candidate_profiles`

- **源码**：`app/mcp_contracts/commands.py:66`
- **签名**：`async def _observe_candidate_profiles(include_http: bool) -> list`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收是否包含 Streamable HTTP 观测的开关，用于发现、观测或评估 MCP 的公开 Tool/Resource/Prompt 契约，比较协议、Schema、延迟和失败结果，并为论文复现系统保留可审核的基线或运行报告，最终标注为 `list` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `include_http` | `bool` | 布尔条件或能力开关，用于控制流程分支。 |

**输出**

- **Python 类型**：`list`
- **语义**：异步返回 `list` 结果；调用方必须 `await`。

**伪代码**

```text
调用 `build_catalog_only_server` 组装当前阶段需要的领域对象，并把结果记为 MCP 服务端实例；将 MCP Client 观测结果集合 初始化为空列表，用来收集后续结果。
遍历辅助操作产生的可迭代结果（调用 `_profiles` 完成该函数的一项辅助处理），每次把当前项记为MCP Client 配置档案：
    如果外部资源传输端口等于'in_memory'：
        把新的处理结果追加或合并到MCP Client 观测结果集合。
    否则：
        如果是否包含 Streamable HTTP 观测的开关有值或为真，就把新的处理结果追加或合并到MCP Client 观测结果集合。
返回MCP Client 观测结果集合的当前值。
```

#### `generate_candidate`

- **源码**：`app/mcp_contracts/commands.py:88`
- **签名**：`def generate_candidate(include_http: bool, output_path: Path | None) -> tuple[Path, McpContractCandidate]`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收是否包含 Streamable HTTP 观测的开关、输出结果的路径，用于发现、观测或评估 MCP 的公开 Tool/Resource/Prompt 契约，比较协议、Schema、延迟和失败结果，并为论文复现系统保留可审核的基线或运行报告，最终一个经过边界校验的文件或目录路径。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `include_http` | `bool` | 布尔条件或能力开关，用于控制流程分支。 |
| `output_path` | `Path | None` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`tuple[Path, McpContractCandidate]`
- **语义**：返回解析后的文件或目录路径对象。

**伪代码**

```text
调用 `run` 完成该函数的一项辅助处理，并把结果记为 MCP Client 观测结果集合；调用 `build_candidate` 组装当前阶段需要的领域对象，并把结果记为 待审核的 MCP 能力候选；调用 `_report_path` 完成该函数的一项辅助处理，并把结果记为 选中的候选项的路径；调用 `write_candidate` 持久化或更新当前领域数据。
返回当前构造的顺序或去重集合。
```

#### `accept_candidate`

- **源码**：`app/mcp_contracts/commands.py:106`
- **签名**：`def accept_candidate(candidate_path: Path, expected_surface_sha256: str, reviewed_by: str, reason: str, replace: bool, expected_current_baseline_sha256: str | None) -> 未显式标注（存在 return）`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收MCP 候选文件路径、期望的 SHA-256、基线审核人标识、基线接受或运行操作原因等输入，用于发现、观测或评估 MCP 的公开 Tool/Resource/Prompt 契约，比较协议、Schema、延迟和失败结果，并为论文复现系统保留可审核的基线或运行报告，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `candidate_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `expected_surface_sha256` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |
| `reviewed_by` | `str` | 基线审核人标识；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `reason` | `str` | 来源、类别、用途、后端、状态或操作原因等控制字段；通常对应有限的业务枚举或审计文本。 |
| `replace` | `bool` | 布尔条件或能力开关，用于控制流程分支。 |
| `expected_current_baseline_sha256` | `str | None` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
调用 `load_candidate` 读取或查询当前阶段需要的数据，并把结果记为 待审核的 MCP 能力候选；调用 `promote_candidate` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `_render_report`

- **源码**：`app/mcp_contracts/commands.py:129`
- **签名**：`def _render_report(report: McpContractEvalReport) -> str`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收MCP 评测或运行报告，用于把复现过程中的结构化状态、证据或结果转换为可读、可传输或可持久化的表示，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `report` | `McpContractEvalReport` | MCP 评测或运行报告；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
计算初始化顺序集合，并保存为 待输出的文本行。
遍历当前可迭代输入，每次把当前项记为当前处理项：
    把新的处理结果追加或合并到待输出的文本行。
    遍历当前可迭代输入，每次把当前项记为发现，然后把新的处理结果追加或合并到待输出的文本行。
把新的处理结果追加或合并到待输出的文本行；调用 `join` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `run_contract_eval`

- **源码**：`app/mcp_contracts/commands.py:160`
- **签名**：`def run_contract_eval(mode: McpEvalMode) -> tuple[Path, Path, McpContractEvalReport]`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收MCP 评测或运行模式，用于发现、观测或评估 MCP 的公开 Tool/Resource/Prompt 契约，比较协议、Schema、延迟和失败结果，并为论文复现系统保留可审核的基线或运行报告，最终一个经过边界校验的文件或目录路径。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `mode` | `McpEvalMode` | MCP 评测或运行模式；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`tuple[Path, Path, McpContractEvalReport]`
- **语义**：返回解析后的文件或目录路径对象。

**伪代码**

```text
调用 `load_baseline` 读取或查询当前阶段需要的数据，并把结果记为 已审核的 MCP 能力基线；调用 `run` 完成该函数的一项辅助处理，并把结果记为 MCP 评测或运行报告；计算组合或计算已有值，并保存为 受控扫描根目录；计算组合或计算已有值，并保存为 JSON 数据的路径。
计算组合或计算已有值，并保存为 当前处理结果的路径；调用 `atomic_write_json` 完成该函数的一项辅助处理；调用 `atomic_write_text` 完成该函数的一项辅助处理；返回当前构造的顺序或去重集合。
```

#### `stack_doctor`

- **源码**：`app/mcp_contracts/commands.py:182`
- **签名**：`def stack_doctor(connect_gateway: bool) -> McpStackReadinessReport`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收是否连接外部 MCP Gateway 的开关，用于发现、观测或评估 MCP 的公开 Tool/Resource/Prompt 契约，比较协议、Schema、延迟和失败结果，并为论文复现系统保留可审核的基线或运行报告，最终标注为 `McpStackReadinessReport` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `connect_gateway` | `bool` | 布尔条件或能力开关，用于控制流程分支。 |

**输出**

- **Python 类型**：`McpStackReadinessReport`
- **语义**：返回 `McpStackReadinessReport` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `inspect_mcp_stack` 完成该函数的一项辅助处理，并返回处理结果。
```

### `app/mcp_contracts/evaluator.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_finding`

- **源码**：`app/mcp_contracts/evaluator.py:24`
- **签名**：`def _finding(code: str, summary: str) -> McpContractFinding`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收待解析或验证的代码、阶段摘要，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `McpContractFinding` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `code` | `str` | 待解析、执行或断言的代码文本；处理前应处于受控测试/执行边界内。 |
| `summary` | `str` | 阶段摘要；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`McpContractFinding`
- **语义**：返回 `McpContractFinding` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `McpContractFinding` 结构化领域对象。
```

#### `compare_observation`

- **源码**：`app/mcp_contracts/evaluator.py:32`
- **签名**：`def compare_observation(observation: McpSurfaceObservation, baseline: McpContractBaseline) -> list[McpContractFinding]`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，完全确定性比较；不调用 LLM。该函数接收MCP Client 单次观测结果、已审核的 MCP 能力基线，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `observation` | `McpSurfaceObservation` | MCP Client 单次观测结果；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `baseline` | `McpContractBaseline` | 已审核的 MCP 能力基线；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`list[McpContractFinding]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
将 诊断发现集合 初始化为空列表，用来收集后续结果；读取MCP 公开能力表面，并保存为 MCP 公开能力表面；读取运行时环境，并保存为 运行时环境。
如果MCP 能力表面的 SHA-256不等于已接受 MCP 能力表面的 SHA-256，就把新的处理结果追加或合并到诊断发现集合。
如果MCP 服务端实例的名称不等于MCP 服务端实例的名称，就把新的处理结果追加或合并到诊断发现集合。
如果版本不等于版本，就把新的处理结果追加或合并到诊断发现集合。
遍历并筛选输入，将整理后的结果保存为 实际集合。
如果实际集合不等于工具集合，就把新的处理结果追加或合并到诊断发现集合。
遍历并筛选输入，将整理后的结果保存为 实际集合。
如果实际集合不等于资源集合，就把新的处理结果追加或合并到诊断发现集合。
如果当前处理结果有值或为真 且 当前可迭代输入中存在满足“MCP Tool 输出 Schema为空”的项，就把新的处理结果追加或合并到诊断发现集合。
如果“当前处理结果有值或为真”不成立 且 资源集合有值或为真，就把新的处理结果追加或合并到诊断发现集合。
如果“当前处理结果有值或为真”不成立 且 当前处理结果有值或为真，就把新的处理结果追加或合并到诊断发现集合。
遍历并筛选输入，将整理后的结果保存为 当前处理结果。
如果当前可迭代输入中存在满足“辅助操作“对当前处理结果中的文本执行规范化或拆分”的结果属于对象名称”的项，就把新的处理结果追加或合并到诊断发现集合。
如果当前处理结果不属于当前处理结果，就把新的处理结果追加或合并到诊断发现集合。
如果MCP 协议版本不属于当前处理结果，就把新的处理结果追加或合并到诊断发现集合。
返回诊断发现集合的当前值。
```

#### `evaluate_profiles`

- **源码**：`app/mcp_contracts/evaluator.py:119`
- **签名**：`async def evaluate_profiles(profiles: list[McpClientProfile], baseline: McpContractBaseline, mode: McpEvalMode, timeout_seconds: float, token_resolver: Callable[[McpClientProfile], str]) -> McpContractEvalReport`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收MCP Client 配置档案集合、已审核的 MCP 能力基线、MCP 评测或运行模式、等待超时时间（秒）等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `McpContractEvalReport` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `profiles` | `list[McpClientProfile]` | MCP Client 配置档案集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `baseline` | `McpContractBaseline` | 已审核的 MCP 能力基线；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `mode` | `McpEvalMode` | MCP 评测或运行模式；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `timeout_seconds` | `float` | 超时或截止时间限制；用于防止等待/搜索/执行无限持续。 |
| `token_resolver` | `Callable[[McpClientProfile], str]` | MCP 凭据解析器；只在实际连接的短生命周期内解析 Secret，不把 Token 写入 Profile 或报告。 |

**输出**

- **Python 类型**：`McpContractEvalReport`
- **语义**：异步返回 `McpContractEvalReport` 结果；调用方必须 `await`。

**伪代码**

```text
调用 `build_catalog_only_server` 组装当前阶段需要的领域对象，并把结果记为 MCP 服务端实例；将 处理结果集合 初始化为空列表，用来收集后续结果；将 当前处理结果 初始化为空去重集合，用来收集后续结果。
遍历由MCP Client 配置档案集合组成的集合或迭代器，每次把当前项记为MCP Client 配置档案：
    如果MCP 评测或运行模式等于'offline' 且 外部资源传输端口不等于'in_memory'，就把新的处理结果追加或合并到处理结果集合；跳过本轮剩余处理，直接进入下一轮。
    先尝试完成以下处理：
        如果外部资源传输端口等于'in_memory'，就等待异步处理完成，并把结果记为 MCP Client 单次观测结果；否则调用 `token_resolver` 完成该函数的一项辅助处理，并把结果记为 模型或命令 token；等待异步处理完成，并把结果记为 MCP Client 单次观测结果。
        调用 `compare_observation` 完成该函数的一项辅助处理，并把结果记为 诊断发现集合；把MCP 能力表面的 SHA-256追加或合并到当前处理结果；把新的处理结果追加或合并到处理结果集合。
    如果出现 `Exception`并把异常保存为捕获的异常对象：
        把新的处理结果追加或合并到处理结果集合。
如果当前处理结果 的长度大于1：
    遍历由处理结果集合组成的集合或迭代器，每次把当前项记为阶段处理结果：
        如果当前状态不等于'skipped'，就把新的处理结果追加或合并到诊断发现集合；计算使用固定配置或常量值，并保存为 当前状态。
构造临时集合、映射或轻量领域对象，并把结果记为 该调用返回的结果；遍历并筛选输入，将整理后的结果保存为 结果集合集合。
如果MCP 评测或运行模式等于'release'，就遍历并筛选输入，将整理后的结果保存为 结果的 ID；检查由MCP Client 配置档案集合组成的集合或迭代器中是否全部满足“辅助操作“从结果的 ID读取所需的状态或领域记录”的结果不为空 且 当前状态等于'passed'”的项，并把结果记为 该调用返回的结果；否则计算计算当前表达式的结果，并保存为 当前处理结果。
计算按字段初始化键值映射，并保存为 结构化请求载荷；构造 `McpContractEvalReport` 结构化领域对象，并把结果记为 MCP 评测或运行报告；复制、序列化或校验结构化领域对象，并返回处理结果。
```

### `app/mcp_contracts/identity.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_normalize`

- **源码**：`app/mcp_contracts/identity.py:19`
- **签名**：`def _normalize(value: Any) -> Any`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，递归把嵌套的 Pydantic BaseModel 转成 JSON-safe dict/list。该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `Any` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `Any` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`Any`
- **语义**：返回 `Any` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果“计算数量、边界或类型判断结果”后得到肯定结果，就复制、序列化或校验结构化领域对象，并返回处理结果。
如果“计算数量、边界或类型判断结果”后得到肯定结果，就返回当前计算得到的结果。
如果“计算数量、边界或类型判断结果”后得到肯定结果，就返回当前计算得到的结果。
返回当前字段值的当前值。
```

#### `canonical_json_bytes`

- **源码**：`app/mcp_contracts/identity.py:31`
- **签名**：`def canonical_json_bytes(value: Any) -> bytes`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，把 Pydantic/JSON 对象转成稳定 UTF-8 字节。该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `bytes` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `Any` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`bytes`
- **语义**：返回 `bytes` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `_normalize` 完成该函数的一项辅助处理，并把结果记为 待处理的论文或源码材料；将结构化内容序列化或编码为可传输表示，并返回处理结果。
```

#### `sha256_value`

- **源码**：`app/mcp_contracts/identity.py:44`
- **签名**：`def sha256_value(value: Any) -> str`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `Any` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回输入内容的 SHA-256 身份摘要，用于完整性校验，不是加密后的正文。

**伪代码**

```text
计算输入内容的 SHA-256 身份摘要，并返回处理结果。
```

#### `sha256_text`

- **源码**：`app/mcp_contracts/identity.py:48`
- **签名**：`def sha256_text(value: str) -> str`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回输入内容的 SHA-256 身份摘要，用于完整性校验，不是加密后的正文。

**伪代码**

```text
计算输入内容的 SHA-256 身份摘要，并返回处理结果。
```

#### `tool_surface`

- **源码**：`app/mcp_contracts/identity.py:52`
- **签名**：`def tool_surface(name: str, description: str, input_schema: dict[str, Any], output_schema: dict[str, Any] | None, annotations: dict[str, Any]) -> McpToolSurface`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收对象名称、对象说明、MCP Tool 输入 Schema、MCP Tool 输出 Schema等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `McpToolSurface` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `name` | `str` | 对象名称；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `description` | `str` | 对象说明；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `input_schema` | `dict[str, Any]` | MCP Tool 输入 Schema；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `output_schema` | `dict[str, Any] | None` | MCP Tool 输出 Schema；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `annotations` | `dict[str, Any]` | MCP Tool 行为标注；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`McpToolSurface`
- **语义**：返回 `McpToolSurface` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
计算按字段初始化键值映射，并保存为 结构化请求载荷；构造并返回 `McpToolSurface` 结构化领域对象。
```

#### `resource_template_surface`

- **源码**：`app/mcp_contracts/identity.py:74`
- **签名**：`def resource_template_surface(uri_template: str, name: str, mime_type: str | None, description: str) -> McpResourceTemplateSurface`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收MCP 资源模板地址、对象名称、资源媒体类型、对象说明，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `McpResourceTemplateSurface` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `uri_template` | `str` | 资源地址；进入网络或持久化前仍需策略校验和必要的脱敏。 |
| `name` | `str` | 对象名称；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `mime_type` | `str | None` | 资源媒体类型；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `description` | `str` | 对象说明；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`McpResourceTemplateSurface`
- **语义**：返回 `McpResourceTemplateSurface` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
计算按字段初始化键值映射，并保存为 结构化请求载荷；构造并返回 `McpResourceTemplateSurface` 结构化领域对象。
```

#### `surface_snapshot`

- **源码**：`app/mcp_contracts/identity.py:93`
- **签名**：`def surface_snapshot(**payload: Any) -> McpSurfaceSnapshot`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收结构化请求载荷，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `McpSurfaceSnapshot` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `**payload` | `Any` | 额外关键字参数映射。 |

**输出**

- **Python 类型**：`McpSurfaceSnapshot`
- **语义**：返回 `McpSurfaceSnapshot` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `McpSurfaceSnapshot` 结构化领域对象。
```

#### `candidate_hash`

- **源码**：`app/mcp_contracts/identity.py:100`
- **签名**：`def candidate_hash(candidate: McpContractCandidate) -> str`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收待审核的 MCP 能力候选，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `candidate` | `McpContractCandidate` | 待审核的 MCP 能力候选；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回内容身份摘要，通常为 SHA-256 十六进制字符串。

**伪代码**

```text
复制、序列化或校验结构化领域对象，并把结果记为 结构化请求载荷；调用 `sha256_value` 计算内容身份、分数或派生结果，并返回处理结果。
```

#### `baseline_hash`

- **源码**：`app/mcp_contracts/identity.py:108`
- **签名**：`def baseline_hash(baseline: McpContractBaseline) -> str`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收已审核的 MCP 能力基线，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `baseline` | `McpContractBaseline` | 已审核的 MCP 能力基线；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回内容身份摘要，通常为 SHA-256 十六进制字符串。

**伪代码**

```text
复制、序列化或校验结构化领域对象，并把结果记为 结构化请求载荷；调用 `sha256_value` 计算内容身份、分数或派生结果，并返回处理结果。
```

#### `report_hash`

- **源码**：`app/mcp_contracts/identity.py:116`
- **签名**：`def report_hash(report: McpContractEvalReport) -> str`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收MCP 评测或运行报告，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `report` | `McpContractEvalReport` | MCP 评测或运行报告；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回内容身份摘要，通常为 SHA-256 十六进制字符串。

**伪代码**

```text
复制、序列化或校验结构化领域对象，并把结果记为 结构化请求载荷；调用 `sha256_value` 计算内容身份、分数或派生结果，并返回处理结果。
```

### `app/mcp_contracts/profiles.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_walk_keys`

- **源码**：`app/mcp_contracts/profiles.py:24`
- **签名**：`def _walk_keys(value: Any) -> list[str]`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `Any` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`list[str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
将 映射键集合 初始化为空列表，用来收集后续结果。
如果“计算数量、边界或类型判断结果”后得到肯定结果：
    遍历辅助操作产生的可迭代结果（调用 `items` 完成该函数的一项辅助处理），每次把当前项记为多个解包结果，然后把新的处理结果追加或合并到映射键集合；把新的处理结果追加或合并到映射键集合。
否则：
    如果“计算数量、边界或类型判断结果”后得到肯定结果：
        遍历由当前字段值组成的集合或迭代器，每次把当前项记为当前处理项，然后把新的处理结果追加或合并到映射键集合。
返回映射键集合的当前值。
```

#### `load_client_profiles`

- **源码**：`app/mcp_contracts/profiles.py:36`
- **签名**：`def load_client_profiles(path: Path, allowed_root: Path) -> list[McpClientProfile]`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，读取无凭证 Profile；拒绝越界、symlink、超大和重复身份。该函数接收文件或目录路径、根目录，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |
| `allowed_root` | `Path` | 已经解析的文件或目录路径对象；后续操作仍需遵守仓库/工作区边界。 |

**输出**

- **Python 类型**：`list[McpClientProfile]`
- **语义**：返回从外部表示解析并校验后的领域值；格式非法时通过异常失败。

**伪代码**

```text
将文件或目录路径规范化为受控的绝对路径，并把结果记为 待审核的 MCP 能力候选。
如果“检查待审核的 MCP 能力候选的文件系统属性”后得到肯定结果，就拒绝继续处理并抛出 `McpClientProfileInvalid`，向调用方报告输入或运行失败。
将待审核的 MCP 能力候选规范化为受控的绝对路径，并把结果记为 解析后的值；将辅助操作“将根目录规范化为受控的绝对路径”的结果规范化为受控的绝对路径，并把结果记为 受控扫描根目录。
如果解析后的值等于受控扫描根目录 或 受控扫描根目录不属于当前处理结果，就拒绝继续处理并抛出 `McpClientProfileInvalid`，向调用方报告输入或运行失败。
如果“检查解析后的值的文件系统属性”后未得到肯定结果，就拒绝继续处理并抛出 `McpClientProfileInvalid`，向调用方报告输入或运行失败。
如果前一步操作返回对象的当前处理结果大于最大MCP Client 配置档案的字节内容，就拒绝继续处理并抛出 `McpClientProfileInvalid`，向调用方报告输入或运行失败。
先尝试完成以下处理：
    将外部表示解析为结构化内容，并把结果记为 原始内容。
如果出现 `(OSError, UnicodeError, json.JSONDecodeError)`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `McpClientProfileInvalid`，向调用方报告输入或运行失败。
如果辅助操作“从原始内容读取所需的状态或领域记录”的结果不等于'phase55-v1'，就拒绝继续处理并抛出 `McpClientProfileInvalid`，向调用方报告输入或运行失败。
调用 `intersection` 完成该函数的一项辅助处理，并把结果记为 被策略禁止的内容或操作。
如果被策略禁止的内容或操作有值或为真，就拒绝继续处理并抛出 `McpClientProfileInvalid`，向调用方报告输入或运行失败。
先尝试完成以下处理：
    调用 `validate_python` 校验当前输入或状态，并把结果记为 MCP Client 配置档案集合。
如果出现 `Exception`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `McpClientProfileInvalid`，向调用方报告输入或运行失败。
遍历并筛选输入，将整理后的结果保存为 当前处理结果。
如果当前处理结果 的长度不等于辅助操作“构造临时集合、映射或轻量领域对象”的结果 的长度，就拒绝继续处理并抛出 `McpClientProfileInvalid`，向调用方报告输入或运行失败。
遍历并筛选输入，将整理后的结果保存为 功能是否启用的开关。
如果功能是否启用的开关为空或为假，就拒绝继续处理并抛出 `McpClientProfileInvalid`，向调用方报告输入或运行失败。
遍历由功能是否启用的开关组成的集合或迭代器，每次把当前项记为MCP Client 配置档案：
    如果外部资源传输端口等于'streamable_http'，就调用 `validate_loopback_endpoint` 校验当前输入或状态。
返回功能是否启用的开关的当前值。
```

### `app/mcp_contracts/readiness.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_sdk_component`

- **源码**：`app/mcp_contracts/readiness.py:15`
- **签名**：`def _sdk_component() -> McpStackComponent`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `McpStackComponent` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`McpStackComponent`
- **语义**：返回 `McpStackComponent` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果辅助操作“调用 `find_spec` 读取或查询当前阶段需要的数据”的结果为空，就构造并返回 `McpStackComponent` 结构化领域对象。
先尝试完成以下处理：
    调用 `version` 完成该函数的一项辅助处理，并把结果记为 记录版本号；调用 `int` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
如果出现 `Exception`并把异常保存为捕获的异常对象：
    构造并返回 `McpStackComponent` 结构化领域对象。
如果当前处理结果不等于2，就构造并返回 `McpStackComponent` 结构化领域对象。
构造并返回 `McpStackComponent` 结构化领域对象。
```

#### `_contract_component`

- **源码**：`app/mcp_contracts/readiness.py:40`
- **签名**：`def _contract_component() -> McpStackComponent`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `McpStackComponent` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`McpStackComponent`
- **语义**：返回 `McpStackComponent` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
将 诊断问题集合 初始化为空列表，用来收集后续结果。
先尝试完成以下处理：
    调用 `load_baseline` 读取或查询当前阶段需要的数据。
如果出现 `Exception`并把异常保存为捕获的异常对象：
    把新的处理结果追加或合并到诊断问题集合。
先尝试完成以下处理：
    调用 `load_client_profiles` 读取或查询当前阶段需要的数据。
如果出现 `Exception`并把异常保存为捕获的异常对象：
    把新的处理结果追加或合并到诊断问题集合。
构造并返回 `McpStackComponent` 结构化领域对象。
```

#### `_gateway_component`

- **源码**：`app/mcp_contracts/readiness.py:60`
- **签名**：`def _gateway_component(*, connect: bool) -> McpStackComponent`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收是否建立 MCP 连接的开关，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `McpStackComponent` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `connect` | `bool` | 布尔条件或能力开关，用于控制流程分支。 |

**输出**

- **Python 类型**：`McpStackComponent`
- **语义**：返回 `McpStackComponent` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果“网关有值或为真”不成立，就构造并返回 `McpStackComponent` 结构化领域对象。
加载这一步需要的外部依赖；调用 `inspect_mcp_gateway` 完成该函数的一项辅助处理，并把结果记为 MCP 评测或运行报告；构造并返回 `McpStackComponent` 结构化领域对象。
```

#### `_export_component`

- **源码**：`app/mcp_contracts/readiness.py:74`
- **签名**：`def _export_component() -> McpStackComponent`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `McpStackComponent` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`McpStackComponent`
- **语义**：返回 `McpStackComponent` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果“当前处理结果有值或为真”不成立，就构造并返回 `McpStackComponent` 结构化领域对象。
加载这一步需要的外部依赖；调用 `inspect_mcp_export` 完成该函数的一项辅助处理，并把结果记为 MCP 评测或运行报告；构造并返回 `McpStackComponent` 结构化领域对象。
```

#### `_runtime_component`

- **源码**：`app/mcp_contracts/readiness.py:88`
- **签名**：`def _runtime_component() -> McpStackComponent`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，验证策略和最新 release Report；默认不发起 MCP 调用。该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `McpStackComponent` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`McpStackComponent`
- **语义**：返回 `McpStackComponent` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果“当前处理结果有值或为真”不成立，就构造并返回 `McpStackComponent` 结构化领域对象。
加载这一步需要的外部依赖；加载这一步需要的外部依赖；将 诊断问题集合 初始化为空列表，用来收集后续结果。
先尝试完成以下处理：
    调用 `load_runtime_policy` 读取或查询当前阶段需要的数据，并把结果记为 安全策略。
如果出现 `Exception`并把异常保存为捕获的异常对象：
    构造并返回 `McpStackComponent` 结构化领域对象。
先尝试完成以下处理：
    按稳定规则整理结果顺序，并把结果记为 候选结果集合。
如果出现 `OSError`并把异常保存为捕获的异常对象：
    构造并返回 `McpStackComponent` 结构化领域对象。
如果候选结果集合为空或为假：
    把新的处理结果追加或合并到诊断问题集合。
否则：
    先尝试完成以下处理：
        调用 `load_runtime_report` 读取或查询当前阶段需要的数据，并把结果记为 MCP 评测或运行报告；调用 `load_baseline` 读取或查询当前阶段需要的数据，并把结果记为 已审核的 MCP 能力基线。
        如果MCP 评测或运行模式不等于'release'，就把新的处理结果追加或合并到诊断问题集合。
        如果“当前处理结果有值或为真”不成立，就把新的处理结果追加或合并到诊断问题集合。
        如果安全策略的 SHA-256不等于安全策略的 SHA-256，就把新的处理结果追加或合并到诊断问题集合。
        如果已审核的 MCP 能力基线的 SHA-256不等于已审核的 MCP 能力基线的 SHA-256，就把新的处理结果追加或合并到诊断问题集合。
    如果出现 `Exception`并把异常保存为捕获的异常对象：
        把新的处理结果追加或合并到诊断问题集合。
构造并返回 `McpStackComponent` 结构化领域对象。
```

#### `inspect_mcp_stack`

- **源码**：`app/mcp_contracts/readiness.py:155`
- **签名**：`def inspect_mcp_stack(connect_gateway: bool) -> McpStackReadinessReport`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，默认不联网；只有显式 connect_gateway 才检查 Phase 53 endpoint。该函数接收是否连接外部 MCP Gateway 的开关，用于发现、观测或评估 MCP 的公开 Tool/Resource/Prompt 契约，比较协议、Schema、延迟和失败结果，并为论文复现系统保留可审核的基线或运行报告，最终标注为 `McpStackReadinessReport` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `connect_gateway` | `bool` | 布尔条件或能力开关，用于控制流程分支。；默认 假 |

**输出**

- **Python 类型**：`McpStackReadinessReport`
- **语义**：返回 `McpStackReadinessReport` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
计算初始化顺序集合，并保存为 当前处理结果；遍历并筛选输入，将整理后的结果保存为 当前处理结果。
如果当前输入内容属于当前处理结果：
    计算使用固定配置或常量值，并保存为 当前处理结果。
否则：
    如果当前输入内容属于当前处理结果：
        计算使用固定配置或常量值，并保存为 当前处理结果。
    否则：
        如果当前处理结果等于{'disabled'}，就计算使用固定配置或常量值，并保存为 当前处理结果；否则计算使用固定配置或常量值，并保存为 当前处理结果。
构造并返回 `McpStackReadinessReport` 结构化领域对象。
```

### `app/mcp_contracts/schemas.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `McpClientProfile.validate_transport_fields`

- **源码**：`app/mcp_contracts/schemas.py:37`
- **签名**：`def validate_transport_fields(self) -> "McpClientProfile"`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `'McpClientProfile'` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`'McpClientProfile'`
- **语义**：返回 `'McpClientProfile'` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果外部资源传输端口等于'in_memory'：
    如果MCP 服务端点地址不为空 或 敏感凭据的名称不为空，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
否则：
    如果MCP 服务端点地址为空 或 敏感凭据的名称为空，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前对象的当前值。
```

#### `McpSurfaceSnapshot.validate_deterministic_order`

- **源码**：`app/mcp_contracts/schemas.py:83`
- **签名**：`def validate_deterministic_order(self) -> "McpSurfaceSnapshot"`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `'McpSurfaceSnapshot'` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`'McpSurfaceSnapshot'`
- **语义**：返回 `'McpSurfaceSnapshot'` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果当前输入内容不等于辅助操作“按稳定规则整理结果顺序”的结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果当前输入内容不等于辅助操作“按稳定规则整理结果顺序”的结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果资源集合不等于辅助操作“按稳定规则整理结果顺序”的结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果当前处理结果不等于辅助操作“按稳定规则整理结果顺序”的结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前对象的当前值。
```

### `app/mcp_contracts/snapshot.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_distribution_version`

- **源码**：`app/mcp_contracts/snapshot.py:25`
- **签名**：`def _distribution_version(name: str) -> str`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收对象名称，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `name` | `str` | 对象名称；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
先尝试完成以下处理：
    调用 `version` 完成该函数的一项辅助处理，并返回处理结果。
如果出现 `metadata.PackageNotFoundError`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `McpContractDependencyMissing`，向调用方报告输入或运行失败。
```

#### `_major`

- **源码**：`app/mcp_contracts/snapshot.py:34`
- **签名**：`def _major(version: str) -> int`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收记录版本号，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终数量、序号、字节数或版本等整数结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `version` | `str` | 记录版本号；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`int`
- **语义**：返回整数计数、序号、字节数或退出码；具体含义由函数名决定。

**伪代码**

```text
读取前一步操作返回对象中的对应字段，并保存为 原始内容。
如果“调用 `isdigit` 完成该函数的一项辅助处理”后未得到肯定结果，就拒绝继续处理并抛出 `McpSurfaceObservationFailed`，向调用方报告输入或运行失败。
调用 `int` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `_dump`

- **源码**：`app/mcp_contracts/snapshot.py:41`
- **签名**：`def _dump(value: Any) -> dict[str, Any]`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `Any` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`dict[str, Any]`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
如果当前字段值为空，就返回当前构造的结构化映射。
如果“调用 `hasattr` 完成该函数的一项辅助处理”后得到肯定结果，就复制、序列化或校验结构化领域对象，并返回处理结果。
如果“计算数量、边界或类型判断结果”后得到肯定结果，就复制、序列化或校验结构化领域对象，并返回处理结果。
拒绝继续处理并抛出 `McpSurfaceObservationFailed`，向调用方报告输入或运行失败。
```

#### `_capability_names`

- **源码**：`app/mcp_contracts/snapshot.py:51`
- **签名**：`def _capability_names(value: Any) -> list[str]`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `Any` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`list[str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
调用 `_dump` 完成该函数的一项辅助处理，并把结果记为 结构化请求载荷；按稳定规则整理结果顺序，并返回处理结果。
```

#### `_list_all_tools`

- **源码**：`app/mcp_contracts/snapshot.py:60`
- **签名**：`async def _list_all_tools(client) -> list[Any]`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收外部服务客户端，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `client` | `未显式标注` | 外部服务客户端；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`list[Any]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
将 待处理项集合 初始化为空列表，用来收集后续结果；计算使用固定配置或常量值，并保存为 增量读取游标。
只要当前条件（使用固定配置或常量值）成立，就重复以下处理：
    等待异步处理完成，并把结果记为 论文页码；把受控工具定义集合追加或合并到待处理项集合；读取下一项，并保存为 增量读取游标。
    如果增量读取游标为空，就返回待处理项集合的当前值。
```

#### `_list_all_templates`

- **源码**：`app/mcp_contracts/snapshot.py:71`
- **签名**：`async def _list_all_templates(client) -> list[Any]`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收外部服务客户端，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `client` | `未显式标注` | 外部服务客户端；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`list[Any]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
将 待处理项集合 初始化为空列表，用来收集后续结果；计算使用固定配置或常量值，并保存为 增量读取游标。
只要当前条件（使用固定配置或常量值）成立，就重复以下处理：
    等待异步处理完成，并把结果记为 论文页码；把资源集合追加或合并到待处理项集合；读取下一项，并保存为 增量读取游标。
    如果增量读取游标为空，就返回待处理项集合的当前值。
```

#### `_list_all_resources`

- **源码**：`app/mcp_contracts/snapshot.py:82`
- **签名**：`async def _list_all_resources(client) -> list[Any]`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收外部服务客户端，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `client` | `未显式标注` | 外部服务客户端；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`list[Any]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
将 待处理项集合 初始化为空列表，用来收集后续结果；计算使用固定配置或常量值，并保存为 增量读取游标。
只要当前条件（使用固定配置或常量值）成立，就重复以下处理：
    等待异步处理完成，并把结果记为 论文页码；把复现输入资源集合追加或合并到待处理项集合；读取下一项，并保存为 增量读取游标。
    如果增量读取游标为空，就返回待处理项集合的当前值。
```

#### `_list_all_prompts`

- **源码**：`app/mcp_contracts/snapshot.py:93`
- **签名**：`async def _list_all_prompts(client) -> list[Any]`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收外部服务客户端，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `client` | `未显式标注` | 外部服务客户端；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`list[Any]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
将 待处理项集合 初始化为空列表，用来收集后续结果；计算使用固定配置或常量值，并保存为 增量读取游标。
只要当前条件（使用固定配置或常量值）成立，就重复以下处理：
    等待异步处理完成，并把结果记为 论文页码；把当前处理结果追加或合并到待处理项集合；读取下一项，并保存为 增量读取游标。
    如果增量读取游标为空，就返回待处理项集合的当前值。
```

#### `observe_connected_client`

- **源码**：`app/mcp_contracts/snapshot.py:104`
- **签名**：`async def observe_connected_client(client: 未显式标注, profile: McpClientProfile) -> McpSurfaceObservation`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，观察 Client 真正看到的目录，不调用任何业务 Tool。该函数接收外部服务客户端、MCP Client 配置档案，用于发现、观测或评估 MCP 的公开 Tool/Resource/Prompt 契约，比较协议、Schema、延迟和失败结果，并为论文复现系统保留可审核的基线或运行报告，最终标注为 `McpSurfaceObservation` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `client` | `未显式标注` | 外部服务客户端；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `profile` | `McpClientProfile` | 运行/执行环境配置或 profile 标识；描述能力和限制，不是一次执行的结果。 |

**输出**

- **Python 类型**：`McpSurfaceObservation`
- **语义**：异步返回 `McpSurfaceObservation` 结果；调用方必须 `await`。

**伪代码**

```text
先尝试完成以下处理：
    等待异步处理完成，并把结果记为 受控工具定义集合；等待异步处理完成，并把结果记为 当前处理结果；读取当前处理结果，并保存为 后续步骤使用的结果；计算根据条件从两个候选结果中选择一个，并保存为 当前处理结果。
    计算根据条件从两个候选结果中选择一个，并保存为 当前处理结果；读取当前处理结果，并保存为 后续步骤使用的结果。
    如果当前处理结果为空，就拒绝继续处理并抛出 `McpSurfaceObservationFailed`，向调用方报告输入或运行失败。
    按稳定规则整理结果顺序，并把结果记为 工具集合；按稳定规则整理结果顺序，并把结果记为 该调用返回的结果；调用 `surface_snapshot` 完成该函数的一项辅助处理，并把结果记为 MCP 公开能力表面；调用 `_distribution_version` 完成该函数的一项辅助处理，并把结果记为 版本。
    构造 `McpRuntimeFingerprint` 结构化领域对象，并把结果记为 运行时环境；构造并返回 `McpSurfaceObservation` 结构化领域对象。
如果出现 `McpSurfaceObservationFailed`：
    重新抛出当前异常，保持原始失败信息。
如果出现 `Exception`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `McpSurfaceObservationFailed`，向调用方报告输入或运行失败。
```

#### `observe_in_memory`

- **源码**：`app/mcp_contracts/snapshot.py:204`
- **签名**：`async def observe_in_memory(server: 未显式标注, profile: McpClientProfile, timeout_seconds: float) -> McpSurfaceObservation`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收MCP 服务端实例、MCP Client 配置档案、等待超时时间（秒），用于发现、观测或评估 MCP 的公开 Tool/Resource/Prompt 契约，比较协议、Schema、延迟和失败结果，并为论文复现系统保留可审核的基线或运行报告，最终标注为 `McpSurfaceObservation` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `server` | `未显式标注` | MCP 服务端实例；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `profile` | `McpClientProfile` | 运行/执行环境配置或 profile 标识；描述能力和限制，不是一次执行的结果。 |
| `timeout_seconds` | `float` | 超时或截止时间限制；用于防止等待/搜索/执行无限持续。；默认 5.0 |

**输出**

- **Python 类型**：`McpSurfaceObservation`
- **语义**：异步返回 `McpSurfaceObservation` 结果；调用方必须 `await`。

**伪代码**

```text
如果外部资源传输端口不等于'in_memory'，就拒绝继续处理并抛出 `McpSurfaceObservationFailed`，向调用方报告输入或运行失败。
先尝试完成以下处理：
    加载这一步需要的外部依赖。
如果出现 `ImportError`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `McpContractDependencyMissing`，向调用方报告输入或运行失败。
在异步上下文“构造 `Client` 结构化领域对象，并把上下文资源交给外部服务客户端”中返回当前计算得到的结果，退出时自动清理资源。
```

#### `observe_streamable_http`

- **源码**：`app/mcp_contracts/snapshot.py:229`
- **签名**：`async def observe_streamable_http(profile: McpClientProfile, token: str, timeout_seconds: float) -> McpSurfaceObservation`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，真实 loopback HTTP 观察；Token 只存在于短生命周期 AsyncClient。该函数接收MCP Client 配置档案、模型或命令 token、等待超时时间（秒），用于发现、观测或评估 MCP 的公开 Tool/Resource/Prompt 契约，比较协议、Schema、延迟和失败结果，并为论文复现系统保留可审核的基线或运行报告，最终标注为 `McpSurfaceObservation` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `profile` | `McpClientProfile` | 运行/执行环境配置或 profile 标识；描述能力和限制，不是一次执行的结果。 |
| `token` | `str` | 敏感凭证或其引用；不得写入日志、Prompt 或普通 Artifact。 |
| `timeout_seconds` | `float` | 超时或截止时间限制；用于防止等待/搜索/执行无限持续。 |

**输出**

- **Python 类型**：`McpSurfaceObservation`
- **语义**：异步返回 `McpSurfaceObservation` 结果；调用方必须 `await`。

**伪代码**

```text
如果外部资源传输端口不等于'streamable_http' 或 MCP 服务端点地址为空，就拒绝继续处理并抛出 `McpSurfaceObservationFailed`，向调用方报告输入或运行失败。
先尝试完成以下处理：
    加载这一步需要的外部依赖；加载这一步需要的外部依赖；加载这一步需要的外部依赖。
如果出现 `ImportError`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `McpContractDependencyMissing`，向调用方报告输入或运行失败。
进入异步上下文“构造 `AsyncClient` 结构化领域对象，并把上下文资源交给当前处理结果”，退出时自动清理资源：
    调用 `streamable_http_client` 完成该函数的一项辅助处理，并把结果记为 外部资源传输端口。
    在异步上下文“构造 `Client` 结构化领域对象，并把上下文资源交给外部服务客户端”中返回当前计算得到的结果，退出时自动清理资源。
```

#### `CatalogOnlyService._deny`

- **源码**：`app/mcp_contracts/snapshot.py:275`
- **签名**：`def _deny()`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
拒绝继续处理并抛出 `RuntimeError`，向调用方报告输入或运行失败。
```

#### `CatalogOnlyService.get_status`

- **源码**：`app/mcp_contracts/snapshot.py:278`
- **签名**：`def get_status(self, **_kwargs)`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收函数关键字参数映射，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `**_kwargs` | `未显式标注` | 额外关键字参数映射。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
调用 `_deny` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `CatalogOnlyService.list_artifacts`

- **源码**：`app/mcp_contracts/snapshot.py:281`
- **签名**：`def list_artifacts(self, **_kwargs)`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收函数关键字参数映射，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `**_kwargs` | `未显式标注` | 额外关键字参数映射。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
调用 `_deny` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `CatalogOnlyService.read_final_report`

- **源码**：`app/mcp_contracts/snapshot.py:284`
- **签名**：`def read_final_report(self, **_kwargs)`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收函数关键字参数映射，用于读取并整理论文、源码或运行产物，把原始输入转换成带位置和身份信息的结构化证据，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `**_kwargs` | `未显式标注` | 额外关键字参数映射。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
调用 `_deny` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `CatalogOnlyService.search_evidence`

- **源码**：`app/mcp_contracts/snapshot.py:287`
- **签名**：`def search_evidence(self, **_kwargs)`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收函数关键字参数映射，用于围绕论文方法语义检索、切分和排序代码证据，为后续方法映射与实验规划提供候选结果，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `**_kwargs` | `未显式标注` | 额外关键字参数映射。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
调用 `_deny` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `build_catalog_only_server`

- **源码**：`app/mcp_contracts/snapshot.py:291`
- **签名**：`def build_catalog_only_server()`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，不连接 Job Store、Artifact、Secret 或 Phase 53 Gateway。该函数接收当前运行配置、模块状态和已注入依赖，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
调用 `cast` 完成该函数的一项辅助处理，并把结果记为 领域服务对象；调用 `build_mcp_export_server` 组装当前阶段需要的领域对象，并返回处理结果。
```

### `app/mcp_export/asgi.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `build_mcp_export_asgi_bundle`

- **源码**：`app/mcp_export/asgi.py:22`
- **签名**：`def build_mcp_export_asgi_bundle(runtime: McpExportRuntime | None, token: str | None) -> McpExportAsgiBundle`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收运行时环境、模型或命令 token，用于在固定 MCP Policy、Schema Pin、调用预算和只读职责边界内连接或调用外部能力，并把返回内容转换为可追溯的复现证据，最终标注为 `McpExportAsgiBundle` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `runtime` | `McpExportRuntime | None` | 运行时环境；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 空值 |
| `token` | `str | None` | 敏感凭证或其引用；不得写入日志、Prompt 或普通 Artifact。；默认 空值 |

**输出**

- **Python 类型**：`McpExportAsgiBundle`
- **语义**：返回 `McpExportAsgiBundle` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
计算计算当前表达式的结果，并保存为 运行时；计算计算当前表达式的结果，并保存为 当前处理结果；调用 `build_mcp_export_server` 组装当前阶段需要的领域对象，并把结果记为 MCP 服务端实例；调用 `streamable_http_app` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
构造 `LocalBearerAuthMiddleware` 结构化领域对象，并把结果记为 该调用返回的结果；构造并返回 `McpExportAsgiBundle` 结构化领域对象。
```

### `app/mcp_export/audit.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `SqliteMcpExportAuditRepository.__init__`

- **源码**：`app/mcp_export/audit.py:12`
- **签名**：`def __init__(self, path: Path) -> None`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收文件或目录路径，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 文件或目录路径 分别保存到同名实例字段。
```

#### `SqliteMcpExportAuditRepository._connect`

- **源码**：`app/mcp_export/audit.py:15`
- **签名**：`def _connect(self) -> sqlite3.Connection`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于在固定 MCP Policy、Schema Pin、调用预算和只读职责边界内连接或调用外部能力，并把返回内容转换为可追溯的复现证据，最终标注为 `sqlite3.Connection` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`sqlite3.Connection`
- **语义**：返回 `sqlite3.Connection` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `connect` 完成该函数的一项辅助处理，并把结果记为 数据库连接；读取数据库记录行，并保存为 记录行；通过数据库连接执行数据查询或命令；通过数据库连接执行数据查询或命令。
通过数据库连接执行数据查询或命令；返回数据库连接的当前值。
```

#### `SqliteMcpExportAuditRepository.initialize`

- **源码**：`app/mcp_export/audit.py:26`
- **签名**：`def initialize(self) -> None`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
创建父级目录或父领域对象对应的目录。
在上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”中通过数据库连接执行数据查询或命令；通过数据库连接执行数据查询或命令，退出时自动清理资源。
```

#### `SqliteMcpExportAuditRepository.put`

- **源码**：`app/mcp_export/audit.py:59`
- **签名**：`def put(self, record: McpExportAuditRecord) -> None`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收领域记录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `record` | `McpExportAuditRecord` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `model_dump_json` 完成该函数的一项辅助处理，并把结果记为 结构化请求载荷。
在上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”中通过数据库连接执行数据查询或命令，退出时自动清理资源。
```

#### `SqliteMcpExportAuditRepository.list_for_job`

- **源码**：`app/mcp_export/audit.py:88`
- **签名**：`def list_for_job(self: 未显式标注, job_id: str, limit: int) -> list[McpExportAuditRecord]`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收复现任务 ID、结果数量上限，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。；默认 100 |

**输出**

- **Python 类型**：`list[McpExportAuditRecord]`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
计算数量、边界或类型判断结果，并把结果记为 该调用返回的结果。
在上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”中调用 `fetchall` 完成该函数的一项辅助处理，并把结果记为 数据库记录行集合，退出时自动清理资源。
返回当前计算得到的结果。
```

#### `SqliteMcpExportAuditRepository.delete_for_job`

- **源码**：`app/mcp_export/audit.py:111`
- **签名**：`def delete_for_job(self, job_id: str) -> int`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收复现任务 ID，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终数量、序号、字节数或版本等整数结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`int`
- **语义**：返回整数计数、序号、字节数或退出码；具体含义由函数名决定。

**伪代码**

```text
在上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”中通过数据库连接执行数据查询或命令，并把结果记为 增量读取游标，退出时自动清理资源。
计算数量、边界或类型判断结果，并返回处理结果。
```

#### `SqliteMcpExportAuditRepository.ping`

- **源码**：`app/mcp_export/audit.py:119`
- **签名**：`def ping(self) -> None`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”中调用 `fetchone` 完成该函数的一项辅助处理，退出时自动清理资源。
```

### `app/mcp_export/auth.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `LocalBearerAuthMiddleware.__init__`

- **源码**：`app/mcp_export/auth.py:11`
- **签名**：`def __init__(self: 未显式标注, app: 未显式标注, expected_token: str, public_paths: set[str] | None) -> None`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前处理结果、期望、当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `app` | `未显式标注` | 名为 `app` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `expected_token` | `str` | 敏感凭证或其引用；不得写入日志、Prompt 或普通 Artifact。 |
| `public_paths` | `set[str] | None` | `set[str] | None` 元素集合；元素代表的业务对象由参数名 `public_paths` 和调用位置确定。；默认 空值 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
去除期望的首尾空白，并把规范化后的文本记为 模型或命令 token。
如果模型或命令 token 的长度小于32，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
把传入的 当前处理结果 分别保存到同名实例字段；将结构化内容序列化或编码为可传输表示，并把结果记为 期望值；构造临时集合、映射或轻量领域对象，并把结果记为 该调用返回的结果。
```

#### `LocalBearerAuthMiddleware._authorization_values`

- **源码**：`app/mcp_export/auth.py:26`
- **签名**：`def _authorization_values(scope) -> list[bytes]`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收查询或授权作用域，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `scope` | `未显式标注` | 查询或授权作用域；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`list[bytes]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
返回当前计算得到的结果。
```

#### `LocalBearerAuthMiddleware.__call__`

- **源码**：`app/mcp_export/auth.py:33`
- **签名**：`async def __call__(self, scope, receive, send) -> None`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收查询或授权作用域、当前处理结果、当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `scope` | `未显式标注` | 查询或授权作用域；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `receive` | `未显式标注` | 名为 `receive` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `send` | `未显式标注` | 名为 `send` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
如果辅助操作“从查询或授权作用域读取所需的状态或领域记录”的结果不等于'http'，就等待异步处理完成，并提交它产生的状态变更；结束当前函数，不返回业务值。
如果辅助操作“从查询或授权作用域读取所需的状态或领域记录”的结果属于当前处理结果，就等待异步处理完成，并提交它产生的状态变更；结束当前函数，不返回业务值。
调用 `_authorization_values` 完成该函数的一项辅助处理，并把结果记为 状态字段集合；计算使用固定配置或常量值，并保存为 输入或结果是否有效的判断。
如果状态字段集合 的长度等于1：
    先尝试完成以下处理：
        将外部表示解析为结构化内容，并把结果记为 原始内容。
    如果出现 `UnicodeDecodeError`：
        计算使用固定配置或常量值，并保存为 原始内容。
    调用 `partition` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；计算计算当前表达式的结果，并保存为 输入或结果是否有效的判断。
如果输入或结果是否有效的判断为空或为假，就构造 `JSONResponse` 结构化领域对象，并把结果记为 结构化响应；等待异步处理完成，并提交它产生的状态变更；结束当前函数，不返回业务值。
等待异步处理完成，并提交它产生的状态变更。
```

### `app/mcp_export/call_executor.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_safe_span`

- **源码**：`app/mcp_export/call_executor.py:38`
- **签名**：`def _safe_span(telemetry: TelemetryPort, attributes: dict[str, str]) -> None（隐式）`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，Span 后端完全失败时退回 NoOp，不改变业务结果。该函数接收运行观测数据、对象属性集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `telemetry` | `TelemetryPort` | 运行观测数据；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `attributes` | `dict[str, str]` | 对象属性集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算使用固定配置或常量值，并保存为 当前处理结果；构造 `NoOpSpan` 结构化领域对象，并把结果记为 源码位置范围。
先尝试完成以下处理：
    调用 `span` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `__enter__` 完成该函数的一项辅助处理，并把结果记为 源码位置范围。
如果出现 `Exception`：
    计算使用固定配置或常量值，并保存为 当前处理结果。
先尝试完成以下处理：
    完成当前表达式对应的校验或状态操作。
无论成功还是失败，最后都要：
    如果当前处理结果不为空：
        先尝试完成以下处理：
            调用 `__exit__` 完成该函数的一项辅助处理。
        如果出现 `Exception`：
            不执行额外操作。
```

#### `McpExportCallExecutor.__init__`

- **源码**：`app/mcp_export/call_executor.py:69`
- **签名**：`def __init__(self: 未显式标注, workers: int, queue_capacity: int, timeout_seconds: float, telemetry: TelemetryPort) -> None`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收MCP 调用 worker 数量、MCP 调用队列容量上限、等待超时时间（秒）、运行观测数据，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `workers` | `int` | MCP 调用 worker 数量；用于限制并发处理能力和关闭时的资源回收范围。 |
| `queue_capacity` | `int` | MCP 调用队列容量上限；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `timeout_seconds` | `float` | 超时或截止时间限制；用于防止等待/搜索/执行无限持续。 |
| `telemetry` | `TelemetryPort` | 运行观测数据；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
如果MCP 调用 worker 数量小于1，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果MCP 调用队列容量上限小于0，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果等待超时时间（秒）不大于0，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
把传入的 等待超时时间（秒）、运行观测数据 分别保存到同名实例字段；构造 `ThreadPoolExecutor` 结构化领域对象，并把结果记为 该调用返回的结果；构造 `BoundedSemaphore` 结构化领域对象，并把结果记为 该调用返回的结果；构造 `Lock` 结构化领域对象，并把结果记为 状态。
计算使用固定配置或常量值，并保存为 已关闭资源。
```

#### `McpExportCallExecutor._is_closed`

- **源码**：`app/mcp_export/call_executor.py:97`
- **签名**：`def _is_closed(self) -> bool`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
在上下文“读取状态的当前值”中返回已关闭资源的当前值，退出时自动清理资源。
```

#### `McpExportCallExecutor.close`

- **源码**：`app/mcp_export/call_executor.py:101`
- **签名**：`def close(self) -> None`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，停止接收新任务；不在线程内强杀已经运行的 Python 代码。该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
进入上下文“读取状态的当前值”，退出时自动清理资源：
    如果已关闭资源有值或为真，就结束当前函数，不返回业务值。
    计算使用固定配置或常量值，并保存为 已关闭资源。
调用 `shutdown` 完成该函数的一项辅助处理。
```

#### `McpExportCallExecutor._record_metric`

- **源码**：`app/mcp_export/call_executor.py:113`
- **签名**：`def _record_metric(self: 未显式标注, operation: str, outcome: str, duration_seconds: float) -> None`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收MCP 业务操作名称、执行结论、当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `operation` | `str` | MCP 业务操作名称；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `outcome` | `str` | 前序调用产生的结构化响应、结果或执行结论，供当前函数继续判断或投影。 |
| `duration_seconds` | `float` | 名为 `duration_seconds` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算按字段初始化键值映射，并保存为 对象属性集合；调用 `increment_counter_safe` 完成该函数的一项辅助处理。
先尝试完成以下处理：
    调用 `histogram` 完成该函数的一项辅助处理。
如果出现 `Exception`：
    不执行额外操作。
```

#### `McpExportCallExecutor.run`

- **源码**：`app/mcp_export/call_executor.py:139`
- **签名**：`async def run(self: 未显式标注, operation: str, request_id: str, job_id: str, function: Callable[..., ResultT], function_kwargs: dict[str, object] | None) -> ResultT`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收MCP 业务操作名称、MCP 请求 ID、复现任务 ID、当前处理结果等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `operation` | `str` | MCP 业务操作名称；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `request_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `function` | `Callable[..., ResultT]` | 可调用依赖；其参数和返回契约由类型标注限定。 |
| `function_kwargs` | `dict[str, object] | None` | MCP 操作函数关键字参数；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 空值 |

**输出**

- **Python 类型**：`ResultT`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
如果“调用 `_is_closed` 校验当前输入或状态”后得到肯定结果，就拒绝继续处理并抛出 `McpExportBusy`，向调用方报告输入或运行失败。
调用 `acquire` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
如果当前处理结果为空或为假，就调用 `_record_metric` 完成该函数的一项辅助处理；拒绝继续处理并抛出 `McpExportBusy`，向调用方报告输入或运行失败。
调用 `perf_counter` 完成该函数的一项辅助处理，并把结果记为 运行是否已经启动的判断；计算使用固定配置或常量值，并保存为 执行结论；调用 `get_running_loop` 读取或查询当前阶段需要的数据，并把结果记为 该调用返回的结果；计算计算当前表达式的结果，并保存为 函数关键字参数映射。
先尝试完成以下处理：
    调用 `run_in_executor` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
如果出现 `Exception`：
    调用 `release` 完成该函数的一项辅助处理；重新抛出当前异常，保持原始失败信息。
定义内部辅助函数 `release_slot`，供当前函数在后续步骤中调用。
调用 `add_done_callback` 完成该函数的一项辅助处理；计算按字段初始化键值映射，并保存为 属性集合集合。
进入上下文“调用 `_safe_span` 完成该函数的一项辅助处理，并把上下文资源交给源码位置范围”，退出时自动清理资源：
    先尝试完成以下处理：
        返回当前计算得到的结果。
    如果出现 `asyncio.TimeoutError`并把异常保存为捕获的异常对象：
        计算使用固定配置或常量值，并保存为 执行结论。
        先尝试完成以下处理：
            调用 `record_span_exception_safe` 完成该函数的一项辅助处理。
        如果出现 `Exception`：
            不执行额外操作。
        拒绝继续处理并抛出 `McpExportTimedOut`，向调用方报告输入或运行失败。
    如果出现 `asyncio.CancelledError`：
        计算使用固定配置或常量值，并保存为 执行结论。
        先尝试完成以下处理：
            调用 `add_event` 完成该函数的一项辅助处理。
        如果出现 `Exception`：
            不执行额外操作。
        重新抛出当前异常，保持原始失败信息。
    如果出现 `Exception`并把异常保存为捕获的异常对象：
        计算使用固定配置或常量值，并保存为 执行结论。
        先尝试完成以下处理：
            调用 `record_span_exception_safe` 完成该函数的一项辅助处理。
        如果出现 `Exception`：
            不执行额外操作。
        重新抛出当前异常，保持原始失败信息。
    无论成功还是失败，最后都要：
        计算数量、边界或类型判断结果，并把结果记为 该调用返回的结果。
        先尝试完成以下处理：
            调用 `set_attribute` 完成该函数的一项辅助处理；调用 `set_attribute` 完成该函数的一项辅助处理。
        如果出现 `Exception`：
            不执行额外操作。
        调用 `_record_metric` 完成该函数的一项辅助处理。
```

#### `McpExportCallExecutor.run.release_slot`

- **源码**：`app/mcp_export/call_executor.py:176`
- **签名**：`def release_slot(completed) -> None`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `completed` | `未显式标注` | 名为 `completed` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `release` 完成该函数的一项辅助处理。
如果“调用 `cancelled` 完成该函数的一项辅助处理”后得到肯定结果，就结束当前函数，不返回业务值。
先尝试完成以下处理：
    调用 `exception` 完成该函数的一项辅助处理。
如果出现 `Exception`：
    不执行额外操作。
```

#### `build_mcp_export_lifespan`

- **源码**：`app/mcp_export/call_executor.py:251`
- **签名**：`def build_mcp_export_lifespan(workers: int, queue_capacity: int, timeout_seconds: float, telemetry: TelemetryPort) -> 未显式标注（存在 return）`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，返回 MCPServer 所需的 async lifespan callback。该函数接收MCP 调用 worker 数量、MCP 调用队列容量上限、等待超时时间（秒）、运行观测数据，用于在固定 MCP Policy、Schema Pin、调用预算和只读职责边界内连接或调用外部能力，并把返回内容转换为可追溯的复现证据，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `workers` | `int` | MCP 调用 worker 数量；用于限制并发处理能力和关闭时的资源回收范围。 |
| `queue_capacity` | `int` | MCP 调用队列容量上限；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `timeout_seconds` | `float` | 超时或截止时间限制；用于防止等待/搜索/执行无限持续。 |
| `telemetry` | `TelemetryPort` | 运行观测数据；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
定义内部辅助函数 `lifespan`，供当前函数在后续步骤中调用。
返回前一步处理得到的结果。
```

#### `build_mcp_export_lifespan.lifespan`

- **源码**：`app/mcp_export/call_executor.py:261`
- **签名**：`async def lifespan(_server) -> AsyncIterator[McpExportServerContext]`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收MCP 服务端实例，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `AsyncIterator[McpExportServerContext]` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `_server` | `未显式标注` | 名为 `_server` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`AsyncIterator[McpExportServerContext]`
- **语义**：返回惰性迭代结果，调用方逐项消费。

**伪代码**

```text
构造 `McpExportCallExecutor` 结构化领域对象，并把结果记为 工具或模型调用记录集合。
先尝试完成以下处理：
    完成当前表达式对应的校验或状态操作。
无论成功还是失败，最后都要：
    关闭工具或模型调用记录集合并释放相关资源。
```

### `app/mcp_export/factory.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_build_artifact_delivery`

- **源码**：`app/mcp_export/factory.py:49`
- **签名**：`def _build_artifact_delivery(storage) -> ArtifactDeliveryService`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前处理结果，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `ArtifactDeliveryService` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `storage` | `未显式标注` | 名为 `storage` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`ArtifactDeliveryService`
- **语义**：返回 `ArtifactDeliveryService` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `ArtifactDeliveryService` 结构化领域对象。
```

#### `build_mcp_export_runtime`

- **源码**：`app/mcp_export/factory.py:67`
- **签名**：`def build_mcp_export_runtime(telemetry: TelemetryPort | None) -> McpExportRuntime`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收运行观测数据，用于在固定 MCP Policy、Schema Pin、调用预算和只读职责边界内连接或调用外部能力，并把返回内容转换为可追溯的复现证据，最终标注为 `McpExportRuntime` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `telemetry` | `TelemetryPort | None` | 运行观测数据；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 空值 |

**输出**

- **Python 类型**：`McpExportRuntime`
- **语义**：返回 `McpExportRuntime` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果“当前处理结果有值或为真”不成立，就拒绝继续处理并抛出 `McpExportDisabled`，向调用方报告输入或运行失败。
计算根据条件从两个候选结果中选择一个，并保存为 观测数据；调用 `build_artifact_storage` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果；构造 `JobService` 结构化领域对象，并把结果记为 任务；构造 `InteractionService` 结构化领域对象，并把结果记为 用户交互记录。
调用 `_build_artifact_delivery` 组装当前阶段需要的领域对象，并把结果记为 通知投递记录；构造 `ChatContextBuilder` 结构化领域对象，并把结果记为 上下文构造器；调用 `build_chat_evidence_tool_registry` 组装当前阶段需要的领域对象，并把结果记为 证据注册表；构造 `SqliteMcpExportAuditRepository` 结构化领域对象，并把结果记为 该调用返回的结果。
调用 `initialize` 完成该函数的一项辅助处理；构造 `InMemoryMcpExportRateLimiter` 结构化领域对象，并把结果记为 该调用返回的结果；构造 `ReadOnlyMcpExportService` 结构化领域对象，并把结果记为 领域服务对象；构造并返回 `McpExportRuntime` 结构化领域对象。
```

#### `resolve_mcp_export_token`

- **源码**：`app/mcp_export/factory.py:137`
- **签名**：`def resolve_mcp_export_token() -> str`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，仅在启动 MCP Export 进程时解析明文 Token。该函数接收当前运行配置、模块状态和已注入依赖，用于把论文中的方法、模块或实验意图与仓库中的可验证对象建立稳定关联，并保留匹配依据，最终文本、路径、状态标签或内容身份摘要。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `resolve_current` 解析、规范化或转换当前输入，并把结果记为 待处理的论文或源码材料；调用 `reveal` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `inspect_mcp_export`

- **源码**：`app/mcp_export/factory.py:148`
- **签名**：`def inspect_mcp_export() -> McpExportDoctorReport`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于发现、观测或评估 MCP 的公开 Tool/Resource/Prompt 契约，比较协议、Schema、延迟和失败结果，并为论文复现系统保留可审核的基线或运行报告，最终标注为 `McpExportDoctorReport` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`McpExportDoctorReport`
- **语义**：返回 `McpExportDoctorReport` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
将 诊断问题集合 初始化为空列表，用来收集后续结果；计算使用固定配置或常量值，并保存为 当前处理结果；计算使用固定配置或常量值，并保存为 当前处理结果。
如果当前处理结果不等于'127.0.0.1'，就把新的处理结果追加或合并到诊断问题集合。
先尝试完成以下处理：
    调用 `resolve_current` 解析、规范化或转换当前输入；计算使用固定配置或常量值，并保存为 当前处理结果。
如果出现 `SecretNotFoundError`：
    把新的处理结果追加或合并到诊断问题集合。
如果出现 `Exception`并把异常保存为捕获的异常对象：
    把新的处理结果追加或合并到诊断问题集合。
先尝试完成以下处理：
    构造 `SqliteMcpExportAuditRepository` 结构化领域对象，并把结果记为 持久化仓库；调用 `initialize` 完成该函数的一项辅助处理；调用 `ping` 完成该函数的一项辅助处理；计算使用固定配置或常量值，并保存为 当前处理结果。
如果出现 `Exception`并把异常保存为捕获的异常对象：
    把新的处理结果追加或合并到诊断问题集合。
构造并返回 `McpExportDoctorReport` 结构化领域对象。
```

### `app/mcp_export/identity.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `canonical_json_bytes`

- **源码**：`app/mcp_export/identity.py:14`
- **签名**：`def canonical_json_bytes(value: Any) -> bytes`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `bytes` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `Any` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`bytes`
- **语义**：返回 `bytes` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果“计算数量、边界或类型判断结果”后得到肯定结果，就复制、序列化或校验结构化领域对象，并把结果记为 待处理的论文或源码材料；否则读取当前字段值，并保存为 待处理的论文或源码材料。
将结构化内容序列化或编码为可传输表示，并返回处理结果。
```

#### `sha256_value`

- **源码**：`app/mcp_export/identity.py:28`
- **签名**：`def sha256_value(value: Any) -> str`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `Any` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回输入内容的 SHA-256 身份摘要，用于完整性校验，不是加密后的正文。

**伪代码**

```text
计算输入内容的 SHA-256 身份摘要，并返回处理结果。
```

#### `sha256_text`

- **源码**：`app/mcp_export/identity.py:32`
- **签名**：`def sha256_text(value: str) -> str`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回输入内容的 SHA-256 身份摘要，用于完整性校验，不是加密后的正文。

**伪代码**

```text
计算输入内容的 SHA-256 身份摘要，并返回处理结果。
```

#### `validate_job_id`

- **源码**：`app/mcp_export/identity.py:36`
- **签名**：`def validate_job_id(job_id: str) -> str`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，只接受 JobService 当前生成的 job_<32 hex> 身份。该函数接收复现任务 ID，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回稳定业务标识符，用于后续查询、关联或幂等绑定；它不是路径或内容 Hash。

**伪代码**

```text
去除复现任务 ID的首尾空白，并把规范化后的文本记为 规范化后的文本。
如果辅助操作“调用 `fullmatch` 完成该函数的一项辅助处理”的结果为空，就拒绝继续处理并抛出 `McpExportInputInvalid`，向调用方报告输入或运行失败。
返回规范化后的文本的当前值。
```

#### `normalize_query`

- **源码**：`app/mcp_export/identity.py:45`
- **签名**：`def normalize_query(query: str) -> str`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收语义检索问题，用于读取并整理论文、源码或运行产物，把原始输入转换成带位置和身份信息的结构化证据，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `query` | `str` | 用户目标、检索问题、反馈或待处理文本；会作为当前阶段的业务语境输入，并可能受到长度/脱敏约束。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回整理、格式化或规范化后的文本表示。

**伪代码**

```text
调用 `join` 完成该函数的一项辅助处理，并把结果记为 规范化后的文本。
如果规范化后的文本为空或为假 或 规范化后的文本 的长度大于500，就拒绝继续处理并抛出 `McpExportInputInvalid`，向调用方报告输入或运行失败。
如果由规范化后的文本组成的集合或迭代器中存在满足“当前字符 对应的 ASCII/Unicode 编码小于32 或 当前字符 对应的 ASCII/Unicode 编码等于127”的项，就拒绝继续处理并抛出 `McpExportInputInvalid`，向调用方报告输入或运行失败。
返回规范化后的文本的当前值。
```

#### `bounded_limit`

- **源码**：`app/mcp_export/identity.py:57`
- **签名**：`def bounded_limit(limit: int, *, maximum: int) -> int`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收结果数量上限、允许的最大数量，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终数量、序号、字节数或版本等整数结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。 |
| `maximum` | `int` | 允许的最大数量；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`int`
- **语义**：返回整数计数、序号、字节数或退出码；具体含义由函数名决定。

**伪代码**

```text
如果“当前输入内容不大于结果数量上限不大于允许的最大数量”不成立，就拒绝继续处理并抛出 `McpExportInputInvalid`，向调用方报告输入或运行失败。
返回结果数量上限的当前值。
```

### `app/mcp_export/rate_limit.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `InMemoryMcpExportRateLimiter.__init__`

- **源码**：`app/mcp_export/rate_limit.py:14`
- **签名**：`def __init__(self: 未显式标注, max_calls_per_minute: int, clock: Callable[[], float]) -> None`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收单个调用方每分钟最大调用次数、统一时间来源，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `max_calls_per_minute` | `int` | 单个调用方每分钟最大调用次数；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `clock` | `Callable[[], float]` | 时间值或可注入时钟，用于排序、过期、租约或可重复测试。；默认 time.monotonic |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入参数保存到实例字段（单个调用方每分钟最大调用次数 → 最大工具或模型调用记录集合、统一时间来源 → 统一时间来源）；构造 `Lock` 结构化领域对象，并把结果记为 该调用返回的结果；调用 `defaultdict` 完成该函数的一项辅助处理，并把结果记为 工具或模型调用记录集合。
```

#### `InMemoryMcpExportRateLimiter.acquire`

- **源码**：`app/mcp_export/rate_limit.py:25`
- **签名**：`def acquire(self, actor_fingerprint: str) -> None`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收调用方身份指纹，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `actor_fingerprint` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
读取当前时间，作为状态变更的统一时间戳，并把结果记为 当前时间；计算组合或计算已有值，并保存为 当前处理结果。
进入上下文“读取当前处理结果的当前值”，退出时自动清理资源：
    读取工具或模型调用记录集合中的对应字段，并保存为 后续步骤使用的结果。
    只要当前处理结果有值或为真 且 当前处理结果中的对应字段不大于当前处理结果，就重复调用 `popleft` 完成该函数的一项辅助处理。
    如果当前处理结果 的长度不小于最大工具或模型调用记录集合，就拒绝继续处理并抛出 `McpExportRateLimited`，向调用方报告输入或运行失败。
    把当前时间追加或合并到当前处理结果。
```

### `app/mcp_export/schemas.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `McpExportArtifact.reject_path_like_name`

- **源码**：`app/mcp_export/schemas.py:64`
- **签名**：`def reject_path_like_name(cls, value: str) -> str`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `cls` | `未显式标注` | 当前类对象，用于类级构造或校验。 |
| `value` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
如果当前字段值属于{'.', '..'} 或 当前输入内容属于当前字段值 或 当前输入内容属于当前字段值，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前字段值的当前值。
```

#### `McpExportArtifactPage.validate_count`

- **源码**：`app/mcp_export/schemas.py:83`
- **签名**：`def validate_count(self) -> "McpExportArtifactPage"`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `'McpExportArtifactPage'` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`'McpExportArtifactPage'`
- **语义**：返回 `'McpExportArtifactPage'` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果当前处理结果的数量不等于待处理项集合 的长度，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前对象的当前值。
```

#### `McpExportFinalReport.validate_content_length`

- **源码**：`app/mcp_export/schemas.py:104`
- **签名**：`def validate_content_length(self) -> "McpExportFinalReport"`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `'McpExportFinalReport'` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`'McpExportFinalReport'`
- **语义**：返回 `'McpExportFinalReport'` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果字符数不等于业务内容 的长度，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前对象的当前值。
```

#### `McpExportAuditRecord.validate_result_shape`

- **源码**：`app/mcp_export/schemas.py:165`
- **签名**：`def validate_result_shape(self) -> "McpExportAuditRecord"`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`'McpExportAuditRecord'`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
如果当前状态等于'succeeded'：
    如果输出结果的 SHA-256为空 或 错误不为空，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
否则：
    如果错误为空 或 输出结果的 SHA-256不为空，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前对象的当前值。
```

### `app/mcp_export/server.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_request_id`

- **源码**：`app/mcp_export/server.py:28`
- **签名**：`def _request_id(ctx) -> str`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `ctx` | `未显式标注` | 名为 `ctx` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回稳定业务标识符，用于后续查询、关联或幂等绑定；它不是路径或内容 Hash。

**伪代码**

```text
调用 `getattr` 完成该函数的一项辅助处理，并把结果记为 原始内容；计算根据条件从两个候选结果中选择一个，并保存为 规范化后的文本；返回组合判断结果。
```

#### `_resource_request_id`

- **源码**：`app/mcp_export/server.py:34`
- **签名**：`def _resource_request_id(kind: str) -> str`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收业务类别，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `kind` | `str` | 来源、类别、用途、后端、状态或操作原因等控制字段；通常对应有限的业务枚举或审计文本。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回稳定业务标识符，用于后续查询、关联或幂等绑定；它不是路径或内容 Hash。

**伪代码**

```text
返回当前计算得到的结果。
```

#### `_raise_public_error`

- **源码**：`app/mcp_export/server.py:38`
- **签名**：`def _raise_public_error(exc: BaseException) -> NoReturn`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，只把稳定 code 和公开消息交给 MCP Client。该函数接收捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `NoReturn` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `exc` | `BaseException` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`NoReturn`
- **语义**：返回 `NoReturn` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果“计算数量、边界或类型判断结果”后得到肯定结果，就拒绝继续处理并抛出 `RuntimeError`，向调用方报告输入或运行失败。
拒绝继续处理并抛出 `RuntimeError`，向调用方报告输入或运行失败。
```

#### `_invoke`

- **源码**：`app/mcp_export/server.py:50`
- **签名**：`async def _invoke(ctx: 未显式标注, metric_operation: str, metric_job_id: str, metric_request_id: str, function: Callable[..., Any], function_kwargs: dict[str, object], fallback_calls: 'McpExportCallExecutor | None') -> 未显式标注（存在 return）`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，把观测字段与业务函数参数分开，避免同名关键字冲突。该函数接收当前处理结果、观测指标中的 MCP 操作名、观测指标中的复现任务 ID、观测指标中的 MCP 请求 ID等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `ctx` | `未显式标注` | 名为 `ctx` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `metric_operation` | `str` | 观测指标中的 MCP 操作名；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `metric_job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `metric_request_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `function` | `Callable[..., Any]` | 可调用依赖；其参数和返回契约由类型标注限定。 |
| `function_kwargs` | `dict[str, object]` | MCP 操作函数关键字参数；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `fallback_calls` | `'McpExportCallExecutor | None'` | 备用调用路径集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 空值 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
计算使用固定配置或常量值，并保存为 工具或模型调用记录集合。
先尝试完成以下处理：
    读取上下文，并保存为 运行时环境；读取工具或模型调用记录集合，并保存为 工具或模型调用记录集合。
如果出现 `Exception`：
    读取备用调用路径集合，并保存为 工具或模型调用记录集合。
如果工具或模型调用记录集合为空，就拒绝继续处理并抛出 `RuntimeError`，向调用方报告输入或运行失败。
返回当前计算得到的结果。
```

#### `build_mcp_export_server`

- **源码**：`app/mcp_export/server.py:83`
- **签名**：`def build_mcp_export_server(service: ReadOnlyMcpExportService, telemetry: TelemetryPort | None) -> 未显式标注（存在 return）`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收领域服务对象、运行观测数据，用于在固定 MCP Policy、Schema Pin、调用预算和只读职责边界内连接或调用外部能力，并把返回内容转换为可追溯的复现证据，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `service` | `ReadOnlyMcpExportService` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |
| `telemetry` | `TelemetryPort | None` | 运行观测数据；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 空值 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
加载这一步需要的外部依赖；加载这一步需要的外部依赖；加载这一步需要的外部依赖；加载这一步需要的外部依赖。
读取运行上下文，并保存为 当前处理结果中的对应字段；计算根据条件从两个候选结果中选择一个，并保存为 观测数据；构造 `McpExportCallExecutor` 结构化领域对象，并把结果记为 该调用返回的结果；调用 `build_mcp_export_lifespan` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果。
构造 `MCPServer` 结构化领域对象，并把结果记为 该调用返回的结果。
定义内部辅助函数 `get_reproduction_status`，供当前函数在后续步骤中调用。
定义内部辅助函数 `list_reproduction_artifacts`，供当前函数在后续步骤中调用。
定义内部辅助函数 `read_reproduction_final_report`，供当前函数在后续步骤中调用。
定义内部辅助函数 `search_reproduction_evidence`，供当前函数在后续步骤中调用。
定义内部辅助函数 `job_status_resource`，供当前函数在后续步骤中调用。
定义内部辅助函数 `final_report_resource`，供当前函数在后续步骤中调用。
定义内部辅助函数 `healthz`，供当前函数在后续步骤中调用。
返回前一步处理得到的结果。
```

#### `build_mcp_export_server.get_reproduction_status`

- **源码**：`app/mcp_export/server.py:129`
- **签名**：`async def get_reproduction_status(job_id: Annotated[str, Field(description='Server-generated reproduction Job ID: job_ followed by 32 lowercase hex characters', pattern='^job_[0-9a-f]{32}$')], ctx: Context[McpExportServerContext]) -> McpExportJobStatus`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，Read a bounded public status snapshot for one known Job。该函数接收复现任务 ID、当前处理结果，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `McpExportJobStatus` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `job_id` | `Annotated[str, Field(description='Server-generated reproduction Job ID: job_ followed by 32 lowercase hex characters', pattern='^job_[0-9a-f]{32}$')]` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `ctx` | `Context[McpExportServerContext]` | 名为 `ctx` 的 `Context[McpExportServerContext]` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`McpExportJobStatus`
- **语义**：异步返回 `McpExportJobStatus` 结果；调用方必须 `await`。

**伪代码**

```text
调用 `_request_id` 完成该函数的一项辅助处理，并把结果记为 MCP 请求 ID。
先尝试完成以下处理：
    返回当前计算得到的结果。
如果出现 `Exception`并把异常保存为捕获的异常对象：
    调用 `_raise_public_error` 完成该函数的一项辅助处理。
```

#### `build_mcp_export_server.list_reproduction_artifacts`

- **源码**：`app/mcp_export/server.py:161`
- **签名**：`async def list_reproduction_artifacts(job_id: Annotated[str, Field(pattern='^job_[0-9a-f]{32}$')], ctx: Context[McpExportServerContext], limit: Annotated[int, Field(ge=1, le=100)]) -> McpExportArtifactPage`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，List bounded public Artifact metadata without paths。该函数接收复现任务 ID、当前处理结果、结果数量上限，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `McpExportArtifactPage` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `job_id` | `Annotated[str, Field(pattern='^job_[0-9a-f]{32}$')]` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `ctx` | `Context[McpExportServerContext]` | 名为 `ctx` 的 `Context[McpExportServerContext]` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `limit` | `Annotated[int, Field(ge=1, le=100)]` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。；默认 20 |

**输出**

- **Python 类型**：`McpExportArtifactPage`
- **语义**：异步返回 `McpExportArtifactPage` 结果；调用方必须 `await`。

**伪代码**

```text
调用 `_request_id` 完成该函数的一项辅助处理，并把结果记为 MCP 请求 ID。
先尝试完成以下处理：
    返回当前计算得到的结果。
如果出现 `Exception`并把异常保存为捕获的异常对象：
    调用 `_raise_public_error` 完成该函数的一项辅助处理。
```

#### `build_mcp_export_server.read_reproduction_final_report`

- **源码**：`app/mcp_export/server.py:189`
- **签名**：`async def read_reproduction_final_report(job_id: Annotated[str, Field(pattern='^job_[0-9a-f]{32}$')], ctx: Context[McpExportServerContext]) -> McpExportFinalReport`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，Read the server-selected, integrity-checked final report。该函数接收复现任务 ID、当前处理结果，用于读取并整理论文、源码或运行产物，把原始输入转换成带位置和身份信息的结构化证据，最终标注为 `McpExportFinalReport` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `job_id` | `Annotated[str, Field(pattern='^job_[0-9a-f]{32}$')]` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `ctx` | `Context[McpExportServerContext]` | 名为 `ctx` 的 `Context[McpExportServerContext]` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`McpExportFinalReport`
- **语义**：异步返回 `McpExportFinalReport` 结果；调用方必须 `await`。

**伪代码**

```text
调用 `_request_id` 完成该函数的一项辅助处理，并把结果记为 MCP 请求 ID。
先尝试完成以下处理：
    返回当前计算得到的结果。
如果出现 `Exception`并把异常保存为捕获的异常对象：
    调用 `_raise_public_error` 完成该函数的一项辅助处理。
```

#### `build_mcp_export_server.search_reproduction_evidence`

- **源码**：`app/mcp_export/server.py:215`
- **签名**：`async def search_reproduction_evidence(job_id: Annotated[str, Field(pattern='^job_[0-9a-f]{32}$')], query: Annotated[str, Field(min_length=1, max_length=500, description='Question used only to rank local Job, Event, Artifact and Log evidence')], ctx: Context[McpExportServerContext], limit: Annotated[int, Field(ge=1, le=6)]) -> McpExportEvidencePack`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，Search bounded local evidence and return citations。该函数接收复现任务 ID、语义检索问题、当前处理结果、结果数量上限，用于围绕论文方法语义检索、切分和排序代码证据，为后续方法映射与实验规划提供候选结果，最终标注为 `McpExportEvidencePack` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `job_id` | `Annotated[str, Field(pattern='^job_[0-9a-f]{32}$')]` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `query` | `Annotated[str, Field(min_length=1, max_length=500, description='Question used only to rank local Job, Event, Artifact and Log evidence')]` | 用户目标、检索问题、反馈或待处理文本；会作为当前阶段的业务语境输入，并可能受到长度/脱敏约束。 |
| `ctx` | `Context[McpExportServerContext]` | 名为 `ctx` 的 `Context[McpExportServerContext]` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `limit` | `Annotated[int, Field(ge=1, le=6)]` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。；默认 5 |

**输出**

- **Python 类型**：`McpExportEvidencePack`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
调用 `_request_id` 完成该函数的一项辅助处理，并把结果记为 MCP 请求 ID。
先尝试完成以下处理：
    返回当前计算得到的结果。
如果出现 `Exception`并把异常保存为捕获的异常对象：
    调用 `_raise_public_error` 完成该函数的一项辅助处理。
```

#### `build_mcp_export_server.job_status_resource`

- **源码**：`app/mcp_export/server.py:258`
- **签名**：`async def job_status_resource(job_id: str, ctx: Context[McpExportServerContext]) -> str`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，Public status Resource for one known Job。该函数接收复现任务 ID、当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `ctx` | `Context[McpExportServerContext]` | 名为 `ctx` 的 `Context[McpExportServerContext]` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `_resource_request_id` 完成该函数的一项辅助处理，并把结果记为 MCP 请求 ID。
先尝试完成以下处理：
    等待异步处理完成，并把结果记为 阶段处理结果；将结构化内容序列化或编码为可传输表示，并返回处理结果。
如果出现 `Exception`并把异常保存为捕获的异常对象：
    调用 `_raise_public_error` 完成该函数的一项辅助处理。
```

#### `build_mcp_export_server.final_report_resource`

- **源码**：`app/mcp_export/server.py:292`
- **签名**：`async def final_report_resource(job_id: str, ctx: Context[McpExportServerContext]) -> str`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，Integrity-bound JSON projection of one final report。该函数接收复现任务 ID、当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `ctx` | `Context[McpExportServerContext]` | 名为 `ctx` 的 `Context[McpExportServerContext]` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `_resource_request_id` 完成该函数的一项辅助处理，并把结果记为 MCP 请求 ID。
先尝试完成以下处理：
    等待异步处理完成，并把结果记为 阶段处理结果；将结构化内容序列化或编码为可传输表示，并返回处理结果。
如果出现 `Exception`并把异常保存为捕获的异常对象：
    调用 `_raise_public_error` 完成该函数的一项辅助处理。
```

#### `build_mcp_export_server.healthz`

- **源码**：`app/mcp_export/server.py:323`
- **签名**：`async def healthz(_request: Request) -> Response`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收业务请求，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `_request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`Response`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
构造并返回 `JSONResponse` 结构化领域对象。
```

### `app/mcp_export/service.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `utc_now`

- **源码**：`app/mcp_export/service.py:65`
- **签名**：`def utc_now() -> str`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `isoformat` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `_error_code`

- **源码**：`app/mcp_export/service.py:69`
- **签名**：`def _error_code(value: object) -> str | None`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `str | None` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `object` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str | None`
- **语义**：返回 `str | None` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果“计算数量、边界或类型判断结果”后未得到肯定结果，就返回固定值 `空值`。
计算计算当前表达式的结果，并保存为 原始内容。
如果原始内容为空，就返回固定值 `空值`。
去除辅助操作“调用 `str` 完成该函数的一项辅助处理”的结果的首尾空白，并把规范化后的文本记为 规范化后的文本；返回组合判断结果。
```

#### `_map_export_error`

- **源码**：`app/mcp_export/service.py:79`
- **签名**：`def _map_export_error(exc: BaseException) -> McpExportError`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收捕获的异常，用于把论文中的方法、模块或实验意图与仓库中的可验证对象建立稳定关联，并保留匹配依据，最终标注为 `McpExportError` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `exc` | `BaseException` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`McpExportError`
- **语义**：返回 `McpExportError` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果“计算数量、边界或类型判断结果”后得到肯定结果，就返回捕获的异常的当前值。
如果“计算数量、边界或类型判断结果”后得到肯定结果，就构造并返回 `McpExportJobNotFound` 结构化领域对象。
如果“计算数量、边界或类型判断结果”后得到肯定结果，就构造并返回 `McpExportFinalReportNotFound` 结构化领域对象。
如果“计算数量、边界或类型判断结果”后得到肯定结果，就构造并返回 `McpExportIntegrityError` 结构化领域对象。
构造并返回 `McpExportInternalError` 结构化领域对象。
```

#### `ReadOnlyMcpExportService.__init__`

- **源码**：`app/mcp_export/service.py:92`
- **签名**：`def __init__(self: 未显式标注, interaction: InteractionService, artifact_delivery: ArtifactDeliveryService, evidence_registry: ToolRegistry, audit_repository: SqliteMcpExportAuditRepository, rate_limiter: InMemoryMcpExportRateLimiter, redactor: SecretRedactor, max_artifacts: int, max_report_chars: int) -> None`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收用户交互记录、Artifact、证据注册表、代码仓库等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `interaction` | `InteractionService` | 用户交互记录；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `artifact_delivery` | `ArtifactDeliveryService` | 名为 `artifact_delivery` 的 `ArtifactDeliveryService` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `evidence_registry` | `ToolRegistry` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |
| `audit_repository` | `SqliteMcpExportAuditRepository` | 持久化或目录访问端口；负责读取、CAS 更新或 Artifact 定位。 |
| `rate_limiter` | `InMemoryMcpExportRateLimiter` | 名为 `rate_limiter` 的 `InMemoryMcpExportRateLimiter` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `redactor` | `SecretRedactor` | 敏感信息脱敏器；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `max_artifacts` | `int` | 名为 `max_artifacts` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `max_report_chars` | `int` | 名为 `max_report_chars` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 用户交互记录、Artifact、证据注册表、代码仓库、比例、敏感信息脱敏器、最大当前处理结果、最大字符数 分别保存到同名实例字段；调用 `sha256_text` 计算内容身份、分数或派生结果，并把结果记为 调用方身份指纹。
```

#### `ReadOnlyMcpExportService._execute`

- **源码**：`app/mcp_export/service.py:114`
- **签名**：`def _execute(self: 未显式标注, operation: str, job_id: str, request_id: str, input_payload: dict, function: Callable[[], ExportResult]) -> ExportResult`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，统一处理预算、错误收敛和 Hash-only Audit。该函数接收MCP 业务操作名称、复现任务 ID、MCP 请求 ID、当前处理结果等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `operation` | `str` | MCP 业务操作名称；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `request_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `input_payload` | `dict` | 名为 `input_payload` 的键值映射；键和值分别承载的业务字段由读取/写入分支确定。 |
| `function` | `Callable[[], ExportResult]` | 可调用依赖；其参数和返回契约由类型标注限定。 |

**输出**

- **Python 类型**：`ExportResult`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
读取当前时间，作为状态变更的统一时间戳，并把结果记为 运行启动时间；调用 `perf_counter` 完成该函数的一项辅助处理，并把结果记为 运行是否已经启动的判断；调用 `sha256_value` 计算内容身份、分数或派生结果，并把结果记为 输入内容的 SHA-256。
先尝试完成以下处理：
    调用 `acquire` 完成该函数的一项辅助处理；调用 `function` 完成该函数的一项辅助处理，并把结果记为 输出结果。
如果出现 `Exception`并把异常保存为捕获的异常对象：
    调用 `_map_export_error` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；构造 `McpExportAuditRecord` 结构化领域对象，并把结果记为 领域记录；调用 `put` 完成该函数的一项辅助处理；拒绝继续处理并抛出当前异常对象。
构造 `McpExportAuditRecord` 结构化领域对象，并把结果记为 领域记录；调用 `put` 完成该函数的一项辅助处理；返回输出结果的当前值。
```

#### `ReadOnlyMcpExportService.get_status`

- **源码**：`app/mcp_export/service.py:168`
- **签名**：`def get_status(self: 未显式标注, job_id: str, request_id: str, operation: str) -> McpExportJobStatus`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收复现任务 ID、MCP 请求 ID、MCP 业务操作名称，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `McpExportJobStatus` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `request_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `operation` | `str` | MCP 业务操作名称；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 'get_reproduction_status' |

**输出**

- **Python 类型**：`McpExportJobStatus`
- **语义**：返回 `McpExportJobStatus` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `validate_job_id` 校验当前输入或状态，并把结果记为 任务的 ID。
定义内部辅助函数 `build`，供当前函数在后续步骤中调用。
调用 `_execute` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `ReadOnlyMcpExportService.get_status.build`

- **源码**：`app/mcp_export/service.py:177`
- **签名**：`def build() -> McpExportJobStatus`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `McpExportJobStatus` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`McpExportJobStatus`
- **语义**：返回 `McpExportJobStatus` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `get_job` 读取或查询当前阶段需要的数据，并把结果记为 视图；读取阶段处理结果，并保存为 阶段处理结果；计算按字段初始化键值映射，并保存为 结构化请求载荷；构造并返回 `McpExportJobStatus` 结构化领域对象。
```

#### `ReadOnlyMcpExportService.list_artifacts`

- **源码**：`app/mcp_export/service.py:220`
- **签名**：`def list_artifacts(self: 未显式标注, job_id: str, limit: int, request_id: str) -> McpExportArtifactPage`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收复现任务 ID、结果数量上限、MCP 请求 ID，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `McpExportArtifactPage` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。 |
| `request_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`McpExportArtifactPage`
- **语义**：返回 `McpExportArtifactPage` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `validate_job_id` 校验当前输入或状态，并把结果记为 任务的 ID；调用 `bounded_limit` 完成该函数的一项辅助处理，并把结果记为 上限。
定义内部辅助函数 `build`，供当前函数在后续步骤中调用。
调用 `_execute` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `ReadOnlyMcpExportService.list_artifacts.build`

- **源码**：`app/mcp_export/service.py:233`
- **签名**：`def build() -> McpExportArtifactPage`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `McpExportArtifactPage` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`McpExportArtifactPage`
- **语义**：返回 `McpExportArtifactPage` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
从任务读取所需的状态或领域记录，并把结果记为 任务；从Artifact读取所需的状态或领域记录，并把结果记为 Artifact 视图集合；读取Artifact 视图集合中的对应字段，并保存为 选中的候选项；遍历并筛选输入，将整理后的结果保存为 待处理项集合。
计算按字段初始化键值映射，并保存为 结构化请求载荷；构造并返回 `McpExportArtifactPage` 结构化领域对象。
```

#### `ReadOnlyMcpExportService._final_report_priority`

- **源码**：`app/mcp_export/service.py:280`
- **签名**：`def _final_report_priority(relative_path: str) -> tuple[int, str]`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，服务端识别 final_report；Client 不能提交路径。该函数接收仓库内相对路径，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `relative_path` | `str` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`tuple[int, str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
调用 `replace` 完成该函数的一项辅助处理，再对返回文本执行规范化或拆分，并把结果记为 规范化后的文本；计算按字段初始化键值映射，并保存为 当前处理结果；返回当前构造的顺序或去重集合。
```

#### `ReadOnlyMcpExportService.read_final_report`

- **源码**：`app/mcp_export/service.py:291`
- **签名**：`def read_final_report(self: 未显式标注, job_id: str, request_id: str, operation: str) -> McpExportFinalReport`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收复现任务 ID、MCP 请求 ID、MCP 业务操作名称，用于读取并整理论文、源码或运行产物，把原始输入转换成带位置和身份信息的结构化证据，最终标注为 `McpExportFinalReport` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `request_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `operation` | `str` | MCP 业务操作名称；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 'read_reproduction_final_report' |

**输出**

- **Python 类型**：`McpExportFinalReport`
- **语义**：返回 `McpExportFinalReport` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `validate_job_id` 校验当前输入或状态，并把结果记为 任务的 ID。
定义内部辅助函数 `build`，供当前函数在后续步骤中调用。
调用 `_execute` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `ReadOnlyMcpExportService.read_final_report.build`

- **源码**：`app/mcp_export/service.py:300`
- **签名**：`def build() -> McpExportFinalReport`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `McpExportFinalReport` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`McpExportFinalReport`
- **语义**：返回 `McpExportFinalReport` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
从任务读取所需的状态或领域记录，并把结果记为 任务；从Artifact读取所需的状态或领域记录，并把结果记为 Artifact 视图集合；遍历并筛选输入，将整理后的结果保存为 候选结果集合。
如果候选结果集合为空或为假，就拒绝继续处理并抛出 `McpExportFinalReportNotFound`，向调用方报告输入或运行失败。
读取前一步操作返回对象中的对应字段，并保存为 选中的候选项；调用 `preview` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；读取业务内容中的对应字段，并保存为 内容；调用 `redact_text` 解析、规范化或转换当前输入，并把结果记为 业务内容。
计算计算当前表达式的结果，并保存为 当前处理结果；计算按字段初始化键值映射，并保存为 结构化请求载荷；构造并返回 `McpExportFinalReport` 结构化领域对象。
```

#### `ReadOnlyMcpExportService._public_citation`

- **源码**：`app/mcp_export/service.py:360`
- **签名**：`def _public_citation(item) -> McpExportCitation`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前处理项，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `McpExportCitation` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `item` | `未显式标注` | 当前处理项；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`McpExportCitation`
- **语义**：返回 `McpExportCitation` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
读取论文引用证据，并保存为 论文引用证据；读取来源类型，并保存为 来源类型。
如果来源类型不属于本地证据集合，就拒绝继续处理并抛出 `McpExportEvidenceUnavailable`，向调用方报告输入或运行失败。
如果来源类型等于'artifact'：
    计算根据字段和固定文本生成格式化文本，并保存为 当前处理结果。
否则：
    如果来源类型等于'event'：
        计算根据字段和固定文本生成格式化文本，并保存为 当前处理结果。
    否则：
        如果来源类型等于'log'，就计算使用固定配置或常量值，并保存为 当前处理结果；否则计算使用固定配置或常量值，并保存为 当前处理结果。
构造并返回 `McpExportCitation` 结构化领域对象。
```

#### `ReadOnlyMcpExportService.search_evidence`

- **源码**：`app/mcp_export/service.py:386`
- **签名**：`def search_evidence(self: 未显式标注, job_id: str, query: str, limit: int, request_id: str) -> McpExportEvidencePack`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收复现任务 ID、语义检索问题、结果数量上限、MCP 请求 ID，用于围绕论文方法语义检索、切分和排序代码证据，为后续方法映射与实验规划提供候选结果，最终标注为 `McpExportEvidencePack` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `query` | `str` | 用户目标、检索问题、反馈或待处理文本；会作为当前阶段的业务语境输入，并可能受到长度/脱敏约束。 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。 |
| `request_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`McpExportEvidencePack`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
调用 `validate_job_id` 校验当前输入或状态，并把结果记为 任务的 ID；调用 `normalize_query` 解析、规范化或转换当前输入，并把结果记为 查询；调用 `bounded_limit` 完成该函数的一项辅助处理，并把结果记为 上限。
定义内部辅助函数 `build`，供当前函数在后续步骤中调用。
调用 `_execute` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `ReadOnlyMcpExportService.search_evidence.build`

- **源码**：`app/mcp_export/service.py:398`
- **签名**：`def build() -> McpExportEvidencePack`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `McpExportEvidencePack` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`McpExportEvidencePack`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
调用证据注册表完成模型或 Runnable 处理，并把结果记为 阶段处理结果。
如果失败不为空 或 输出结果为空，就计算根据条件从两个候选结果中选择一个，并保存为 待解析或验证的代码；拒绝继续处理并抛出 `McpExportEvidenceUnavailable`，向调用方报告输入或运行失败。
复制、序列化或校验结构化领域对象，并把结果记为 可追溯证据记录；将 待处理项集合 初始化为空列表，用来收集后续结果。
遍历当前可迭代输入，每次把当前项记为当前处理项：
    调用 `redact_text` 解析、规范化或转换当前输入，并把结果记为 该调用返回的结果。
    如果“对当前处理结果中的文本执行规范化或拆分”后未得到肯定结果，就跳过本轮剩余处理，直接进入下一轮。
    把新的处理结果追加或合并到待处理项集合。
计算按字段初始化键值映射，并保存为 结构化请求载荷；构造并返回 `McpExportEvidencePack` 结构化领域对象。
```

### `app/mcp_gateway/client.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `run_async_from_sync`

- **源码**：`app/mcp_gateway/client.py:35`
- **签名**：`def run_async_from_sync(coroutine, *, timeout_seconds: float)`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，sync MCP client cannot run inside an active event loop。该函数接收当前处理结果、等待超时时间（秒），用于驱动或监督一次论文复现运行，记录命令、工作目录、资源使用、状态迁移和失败原因，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `coroutine` | `未显式标注` | 名为 `coroutine` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `timeout_seconds` | `float` | 超时或截止时间限制；用于防止等待/搜索/执行无限持续。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
先尝试完成以下处理：
    调用 `get_running_loop` 读取或查询当前阶段需要的数据。
如果出现 `RuntimeError`：
    不执行额外操作。
如果主处理没有异常：
    关闭当前处理结果并释放相关资源；拒绝继续处理并抛出 `McpPolicyError`，向调用方报告输入或运行失败。
调用 `run` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `_json_size`

- **源码**：`app/mcp_gateway/client.py:47`
- **签名**：`def _json_size(value: Any) -> int`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终数量、序号、字节数或版本等整数结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `Any` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`int`
- **语义**：返回整数计数、序号、字节数或退出码；具体含义由函数名决定。

**伪代码**

```text
计算数量、边界或类型判断结果，并返回处理结果。
```

#### `_walk_schema`

- **源码**：`app/mcp_gateway/client.py:51`
- **签名**：`def _walk_schema(value: Any, *, max_bytes: int, depth: int = 0) -> None`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前字段值、读取字节数上限、当前遍历深度，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `Any` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |
| `max_bytes` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。 |
| `depth` | `int` | 文件行号、页码或遍历深度边界；用于限制读取/扫描范围，不是业务 ID。；默认 0 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
如果当前遍历深度等于0 且 辅助操作“调用 `_json_size` 完成该函数的一项辅助处理”的结果大于读取字节数上限，就拒绝继续处理并抛出 `McpSchemaDrift`，向调用方报告输入或运行失败。
如果当前遍历深度大于16，就拒绝继续处理并抛出 `McpSchemaDrift`，向调用方报告输入或运行失败。
如果“计算数量、边界或类型判断结果”后得到肯定结果：
    如果当前字段值 的长度大于128，就拒绝继续处理并抛出 `McpSchemaDrift`，向调用方报告输入或运行失败。
    遍历辅助操作产生的可迭代结果（调用 `items` 完成该函数的一项辅助处理），每次把当前项记为多个解包结果：
        如果映射键或对象字段名等于'' 且 “计算数量、边界或类型判断结果”后未得到肯定结果 或 “检查子级目录或子领域对象是否满足文本匹配条件”后未得到肯定结果，就拒绝继续处理并抛出 `McpSchemaDrift`，向调用方报告输入或运行失败。
        调用 `_walk_schema` 完成该函数的一项辅助处理。
否则：
    如果“计算数量、边界或类型判断结果”后得到肯定结果：
        如果当前字段值 的长度大于128，就拒绝继续处理并抛出 `McpSchemaDrift`，向调用方报告输入或运行失败。
        遍历由当前字段值组成的集合或迭代器，每次把当前项记为子级目录或子领域对象，然后调用 `_walk_schema` 完成该函数的一项辅助处理。
```

#### `_validate_json_schema`

- **源码**：`app/mcp_gateway/client.py:70`
- **签名**：`def _validate_json_schema(schema: dict[str, Any], *, max_bytes: int) -> None`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收输入输出 Schema 契约、读取字节数上限，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `schema` | `dict[str, Any]` | 结构化输出 Schema 或其名称；用于约束解析结果的字段和类型。 |
| `max_bytes` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_walk_schema` 完成该函数的一项辅助处理。
先尝试完成以下处理：
    调用 `check_schema` 校验当前输入或状态。
如果出现 `SchemaError`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `McpSchemaDrift`，向调用方报告输入或运行失败。
```

#### `_validate_instance`

- **源码**：`app/mcp_gateway/client.py:78`
- **签名**：`def _validate_instance(*, value: Any, schema: dict[str, Any], error: type[McpGatewayError]) -> None`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前字段值、输入输出 Schema 契约、错误信息，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `Any` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |
| `schema` | `dict[str, Any]` | 结构化输出 Schema 或其名称；用于约束解析结果的字段和类型。 |
| `error` | `type[McpGatewayError]` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
先尝试完成以下处理：
    调用 `validate` 完成该函数的一项辅助处理。
如果出现 `ValidationError`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `error`，向调用方报告输入或运行失败。
```

#### `SdkMcpClient.__init__`

- **源码**：`app/mcp_gateway/client.py:88`
- **签名**：`def __init__(self, *, total_timeout_seconds: float, max_tools: int, max_schema_bytes: int, max_result_bytes: int) -> None`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前处理结果、最大受控工具定义集合、最大输入输出 Schema 契约的字节内容、最大阶段处理结果的字节内容，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `total_timeout_seconds` | `float` | 名为 `total_timeout_seconds` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `max_tools` | `int` | 名为 `max_tools` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `max_schema_bytes` | `int` | 名为 `max_schema_bytes` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `max_result_bytes` | `int` | 前序调用产生的结构化响应、结果或执行结论，供当前函数继续判断或投影。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 当前处理结果、最大受控工具定义集合、最大输入输出 Schema 契约的字节内容、最大阶段处理结果的字节内容 分别保存到同名实例字段。
```

#### `SdkMcpClient._list_tools`

- **源码**：`app/mcp_gateway/client.py:94`
- **签名**：`async def _list_tools(self, client: Client) -> list[Any]`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收外部服务客户端，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `client` | `Client` | 外部服务客户端；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`list[Any]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
将 受控工具定义集合 初始化为空列表，用来收集后续结果；计算使用固定配置或常量值，并保存为 增量读取游标；计算使用固定配置或常量值，并保存为 当前处理结果。
只要当前条件（使用固定配置或常量值）成立，就重复以下处理：
    将新的计算结果累加或合并到当前处理结果。
    如果当前处理结果大于8，就拒绝继续处理并抛出 `McpToolNotAllowed`，向调用方报告输入或运行失败。
    等待异步处理完成，并把结果记为 论文页码；把受控工具定义集合追加或合并到受控工具定义集合。
    如果受控工具定义集合 的长度大于最大受控工具定义集合，就拒绝继续处理并抛出 `McpToolNotAllowed`，向调用方报告输入或运行失败。
    读取下一项，并保存为 增量读取游标。
    如果增量读取游标为空，就返回受控工具定义集合的当前值。
```

#### `SdkMcpClient._observe_tool`

- **源码**：`app/mcp_gateway/client.py:110`
- **签名**：`def _observe_tool(self, *, profile: McpServerProfile, binding: McpToolBinding, protocol_version: str, tools: list[Any]) -> McpObservedTool`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收MCP Client 配置档案、资源绑定记录、MCP 协议版本、受控工具定义集合，用于发现、观测或评估 MCP 的公开 Tool/Resource/Prompt 契约，比较协议、Schema、延迟和失败结果，并为论文复现系统保留可审核的基线或运行报告，最终标注为 `McpObservedTool` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `profile` | `McpServerProfile` | 运行/执行环境配置或 profile 标识；描述能力和限制，不是一次执行的结果。 |
| `binding` | `McpToolBinding` | 资源绑定记录；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `protocol_version` | `str` | MCP 协议版本；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `tools` | `list[Any]` | 受控工具定义集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`McpObservedTool`
- **语义**：返回 `McpObservedTool` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
遍历并筛选输入，将整理后的结果保存为 当前处理结果。
如果当前处理结果 的长度不等于1，就拒绝继续处理并抛出 `McpToolNotAllowed`，向调用方报告输入或运行失败。
读取当前处理结果中的对应字段，并保存为 受控工具定义；读取MCP Tool 输入 Schema，并保存为 MCP Tool 输入 Schema；读取MCP Tool 输出 Schema，并保存为 MCP Tool 输出 Schema。
如果“计算数量、边界或类型判断结果”后未得到肯定结果，就拒绝继续处理并抛出 `McpSchemaDrift`，向调用方报告输入或运行失败。
如果“计算数量、边界或类型判断结果”后未得到肯定结果，就拒绝继续处理并抛出 `McpSchemaDrift`，向调用方报告输入或运行失败。
调用 `_validate_json_schema` 校验当前输入或状态；调用 `_validate_json_schema` 校验当前输入或状态；构造 `McpObservedTool` 结构化领域对象，并把结果记为 该调用返回的结果；返回前一步处理得到的结果。
```

#### `SdkMcpClient._verify_pin`

- **源码**：`app/mcp_gateway/client.py:134`
- **签名**：`def _verify_pin(self, *, binding: McpToolBinding, observed: McpObservedTool) -> None`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收资源绑定记录、当前处理结果，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `binding` | `McpToolBinding` | 资源绑定记录；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `observed` | `McpObservedTool` | 名为 `observed` 的 `McpObservedTool` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
如果MCP Tool 输入 Schema的 SHA-256不等于期望的 SHA-256，就拒绝继续处理并抛出 `McpSchemaDrift`，向调用方报告输入或运行失败。
如果MCP Tool 输出 Schema的 SHA-256不等于期望的 SHA-256，就拒绝继续处理并抛出 `McpSchemaDrift`，向调用方报告输入或运行失败。
```

#### `SdkMcpClient._open_and_observe`

- **源码**：`app/mcp_gateway/client.py:140`
- **签名**：`async def _open_and_observe(self, *, profile: McpServerProfile, binding: McpToolBinding, arguments: dict[str, Any] | None) -> McpObservedTool | McpRawCallResult`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收MCP Client 配置档案、资源绑定记录、结构化调用参数，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `profile` | `McpServerProfile` | 运行/执行环境配置或 profile 标识；描述能力和限制，不是一次执行的结果。 |
| `binding` | `McpToolBinding` | 资源绑定记录；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `arguments` | `dict[str, Any] | None` | 结构化调用参数；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`McpObservedTool | McpRawCallResult`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `validate_loopback_endpoint` 校验当前输入或状态；构造 `Timeout` 结构化领域对象，并把结果记为 等待超时时间。
进入异步上下文“构造 `AsyncClient` 结构化领域对象，并把上下文资源交给当前处理结果”，退出时自动清理资源：
    调用 `streamable_http_client` 完成该函数的一项辅助处理，并把结果记为 外部资源传输端口。
    进入异步上下文“构造 `Client` 结构化领域对象，并把上下文资源交给外部服务客户端”，退出时自动清理资源：
        调用 `str` 完成该函数的一项辅助处理，并把结果记为 MCP 协议版本。
        如果MCP 协议版本不属于当前处理结果，就拒绝继续处理并抛出 `McpProtocolRejected`，向调用方报告输入或运行失败。
        等待异步处理完成，并把结果记为 受控工具定义集合；调用 `_observe_tool` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
        如果结构化调用参数为空，就返回前一步处理得到的结果。
        调用 `_verify_pin` 完成该函数的一项辅助处理；调用 `_validate_instance` 校验当前输入或状态；等待异步处理完成，并把结果记为 阶段处理结果。
        如果是否错误信息有值或为真，就拒绝继续处理并抛出 `McpRemoteToolFailed`，向调用方报告输入或运行失败。
        读取内容，并保存为 后续步骤使用的结果。
        如果“计算数量、边界或类型判断结果”后未得到肯定结果，就拒绝继续处理并抛出 `McpStructuredOutputInvalid`，向调用方报告输入或运行失败。
        如果辅助操作“调用 `_json_size` 完成该函数的一项辅助处理”的结果大于最大阶段处理结果的字节内容，就拒绝继续处理并抛出 `McpResultBudgetExceeded`，向调用方报告输入或运行失败。
        调用 `_validate_instance` 校验当前输入或状态；构造并返回 `McpRawCallResult` 结构化领域对象。
```

#### `SdkMcpClient.inspect_tool`

- **源码**：`app/mcp_gateway/client.py:166`
- **签名**：`def inspect_tool(self, *, profile: McpServerProfile, binding: McpToolBinding) -> McpObservedTool`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收MCP Client 配置档案、资源绑定记录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `McpObservedTool` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `profile` | `McpServerProfile` | 运行/执行环境配置或 profile 标识；描述能力和限制，不是一次执行的结果。 |
| `binding` | `McpToolBinding` | 资源绑定记录；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`McpObservedTool`
- **语义**：返回 `McpObservedTool` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
先尝试完成以下处理：
    调用 `run_async_from_sync` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果。
如果出现 `McpGatewayError`：
    重新抛出当前异常，保持原始失败信息。
如果出现 `(TimeoutError, OSError, RuntimeError)`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `McpServerUnavailable`，向调用方报告输入或运行失败。
如果“计算数量、边界或类型判断结果”后未得到肯定结果，就拒绝继续处理并抛出 `McpStructuredOutputInvalid`，向调用方报告输入或运行失败。
返回阶段处理结果的当前值。
```

#### `SdkMcpClient.call_pinned_tool`

- **源码**：`app/mcp_gateway/client.py:177`
- **签名**：`def call_pinned_tool(self, *, profile: McpServerProfile, binding: McpToolBinding, arguments: dict[str, Any]) -> McpRawCallResult`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收MCP Client 配置档案、资源绑定记录、结构化调用参数，用于在固定 MCP Policy、Schema Pin、调用预算和只读职责边界内连接或调用外部能力，并把返回内容转换为可追溯的复现证据，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `profile` | `McpServerProfile` | 运行/执行环境配置或 profile 标识；描述能力和限制，不是一次执行的结果。 |
| `binding` | `McpToolBinding` | 资源绑定记录；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `arguments` | `dict[str, Any]` | 结构化调用参数；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`McpRawCallResult`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
先尝试完成以下处理：
    调用 `run_async_from_sync` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果。
如果出现 `McpGatewayError`：
    重新抛出当前异常，保持原始失败信息。
如果出现 `(TimeoutError, OSError, RuntimeError)`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `McpServerUnavailable`，向调用方报告输入或运行失败。
如果“计算数量、边界或类型判断结果”后未得到肯定结果，就拒绝继续处理并抛出 `McpStructuredOutputInvalid`，向调用方报告输入或运行失败。
返回阶段处理结果的当前值。
```

### `app/mcp_gateway/factory.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `build_mcp_repository`

- **源码**：`app/mcp_gateway/factory.py:14`
- **签名**：`def build_mcp_repository() -> SqliteMcpEvidenceRepository`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于在固定 MCP Policy、Schema Pin、调用预算和只读职责边界内连接或调用外部能力，并把返回内容转换为可追溯的复现证据，最终标注为 `SqliteMcpEvidenceRepository` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`SqliteMcpEvidenceRepository`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
构造 `SqliteMcpEvidenceRepository` 结构化领域对象，并把结果记为 持久化仓库；调用 `initialize` 完成该函数的一项辅助处理；返回持久化仓库的当前值。
```

#### `build_mcp_client`

- **源码**：`app/mcp_gateway/factory.py:20`
- **签名**：`def build_mcp_client()`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于在固定 MCP Policy、Schema Pin、调用预算和只读职责边界内连接或调用外部能力，并把返回内容转换为可追溯的复现证据，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
加载这一步需要的外部依赖；构造并返回 `SdkMcpClient` 结构化领域对象。
```

#### `build_read_only_mcp_gateway`

- **源码**：`app/mcp_gateway/factory.py:30`
- **签名**：`def build_read_only_mcp_gateway() -> ReadOnlyMcpEvidenceGateway`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `ReadOnlyMcpEvidenceGateway` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`ReadOnlyMcpEvidenceGateway`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
如果“网关有值或为真”不成立，就拒绝继续处理并抛出 `RuntimeError`，向调用方报告输入或运行失败。
调用 `load_mcp_gateway_policy` 读取或查询当前阶段需要的数据，并把结果记为 安全策略；构造并返回 `ReadOnlyMcpEvidenceGateway` 结构化领域对象。
```

#### `inspect_mcp_gateway`

- **源码**：`app/mcp_gateway/factory.py:37`
- **签名**：`def inspect_mcp_gateway(*, connect: bool) -> McpInspectReport`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收是否建立 MCP 连接的开关，用于发现、观测或评估 MCP 的公开 Tool/Resource/Prompt 契约，比较协议、Schema、延迟和失败结果，并为论文复现系统保留可审核的基线或运行报告，最终标注为 `McpInspectReport` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `connect` | `bool` | 布尔条件或能力开关，用于控制流程分支。 |

**输出**

- **Python 类型**：`McpInspectReport`
- **语义**：返回 `McpInspectReport` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果“网关有值或为真”不成立，就构造并返回 `McpInspectReport` 结构化领域对象。
先尝试完成以下处理：
    调用 `load_mcp_gateway_policy` 读取或查询当前阶段需要的数据，并把结果记为 安全策略；调用 `enabled_binding` 完成该函数的一项辅助处理，并把结果记为 选中的候选项。
    如果选中的候选项为空，就构造并返回 `McpInspectReport` 结构化领域对象。
    读取选中的候选项，并保存为 多个解包结果；将 诊断问题集合 初始化为空列表，用来收集后续结果。
    如果是否建立 MCP 连接的开关有值或为真：
        调用 `inspect_tool` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
        如果MCP Tool 输入 Schema的 SHA-256不等于期望的 SHA-256，就把新的处理结果追加或合并到诊断问题集合。
        如果MCP Tool 输出 Schema的 SHA-256不等于期望的 SHA-256，就把新的处理结果追加或合并到诊断问题集合。
    构造并返回 `McpInspectReport` 结构化领域对象。
如果出现 `Exception`并把异常保存为捕获的异常对象：
    计算根据条件从两个候选结果中选择一个，并保存为 待解析或验证的代码；构造并返回 `McpInspectReport` 结构化领域对象。
```

### `app/mcp_gateway/gateway.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `canonicalize_research_url`

- **源码**：`app/mcp_gateway/gateway.py:31`
- **签名**：`def canonicalize_research_url(uri: str) -> str`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收MCP 资源或外部研究地址，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `uri` | `str` | 资源地址；进入网络或持久化前仍需策略校验和必要的脱敏。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
返回MCP 资源或外部研究地址的当前值。
```

#### `utc_now`

- **源码**：`app/mcp_gateway/gateway.py:35`
- **签名**：`def utc_now() -> str`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `isoformat` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `ReadOnlyMcpEvidenceGateway.__init__`

- **源码**：`app/mcp_gateway/gateway.py:44`
- **签名**：`def __init__(self, *, policy: McpGatewayPolicy, client: McpClientPort, repository: SqliteMcpEvidenceRepository) -> None`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收安全策略、外部服务客户端、持久化仓库，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `policy` | `McpGatewayPolicy` | 安全策略；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `client` | `McpClientPort` | 外部服务客户端；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `repository` | `SqliteMcpEvidenceRepository` | 持久化或目录访问端口；负责读取、CAS 更新或 Artifact 定位。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `enabled_binding` 完成该函数的一项辅助处理，并把结果记为 选中的候选项。
如果选中的候选项为空，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
把传入的 安全策略 分别保存到同名实例字段；读取选中的候选项，并保存为 多个解包结果；把传入的 外部服务客户端、持久化仓库 分别保存到同名实例字段。
```

#### `ReadOnlyMcpEvidenceGateway.authority_fingerprint`

- **源码**：`app/mcp_gateway/gateway.py:54`
- **签名**：`def authority_fingerprint(self) -> str`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回内容身份摘要，通常为 SHA-256 十六进制字符串。

**伪代码**

```text
调用 `profile_sha256` 计算内容身份、分数或派生结果，并返回处理结果。
```

#### `ReadOnlyMcpEvidenceGateway.search`

- **源码**：`app/mcp_gateway/gateway.py:57`
- **签名**：`def search(self, *, job_id: str, request_id: str, payload: McpSearchInput) -> McpEvidencePack`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收复现任务 ID、MCP 请求 ID、结构化请求载荷，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `McpEvidencePack` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `request_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `payload` | `McpSearchInput` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`McpEvidencePack`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
读取当前时间，作为状态变更的统一时间戳，并把结果记为 运行启动时间；调用 `perf_counter` 完成该函数的一项辅助处理，并把结果记为 运行是否已经启动的判断；复制、序列化或校验结构化领域对象，并把结果记为 结构化调用参数；调用 `sha256_value` 计算内容身份、分数或派生结果，并把结果记为 请求内容 SHA-256。
计算根据字段和固定文本生成格式化文本，并保存为 当前处理结果的 ID。
先尝试完成以下处理：
    调用 `call_pinned_tool` 完成该函数的一项辅助处理，并把结果记为 原始内容；复制、序列化或校验结构化领域对象，并把结果记为 解析后的结果；将 待处理项集合 初始化为空列表，用来收集后续结果。
    遍历当前可迭代输入，每次把当前项记为远程：
        调用 `canonicalize_research_url` 完成该函数的一项辅助处理，并把结果记为 来源；调用 `join` 完成该函数的一项辅助处理，并把结果记为 文档或章节标题；调用 `join` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `join` 完成该函数的一项辅助处理，并把结果记为 源码或文档定位信息。
        把新的处理结果追加或合并到待处理项集合。
    读取当前时间，作为状态变更的统一时间戳，并把结果记为 创建时间；计算按字段初始化键值映射，并保存为 身份；构造 `McpEvidencePack` 结构化领域对象，并把结果记为 草稿对象；复制、序列化或校验结构化领域对象，并把结果记为 检索或映射证据包。
    构造 `McpCallRecord` 结构化领域对象，并把结果记为 领域记录；调用 `put_success` 持久化或更新当前领域数据；返回检索或映射证据包的当前值。
如果出现 `Exception`并把异常保存为捕获的异常对象：
    如果“计算数量、边界或类型判断结果”后得到肯定结果，就读取待解析或验证的代码，并保存为 错误；否则计算使用固定配置或常量值，并保存为 错误。
    构造 `McpCallRecord` 结构化领域对象，并把结果记为 领域记录；调用 `put_failure` 持久化或更新当前领域数据。
    如果“计算数量、边界或类型判断结果”后得到肯定结果，就重新抛出当前异常，保持原始失败信息。
    拒绝继续处理并抛出 `McpStructuredOutputInvalid`，向调用方报告输入或运行失败。
```

### `app/mcp_gateway/identity.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `canonical_json_bytes`

- **源码**：`app/mcp_gateway/identity.py:18`
- **签名**：`def canonical_json_bytes(value: Any) -> bytes`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `bytes` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `Any` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`bytes`
- **语义**：返回 `bytes` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果“计算数量、边界或类型判断结果”后得到肯定结果，就复制、序列化或校验结构化领域对象，并把结果记为 当前字段值。
将结构化内容序列化或编码为可传输表示，并返回处理结果。
```

#### `sha256_value`

- **源码**：`app/mcp_gateway/identity.py:30`
- **签名**：`def sha256_value(value: Any) -> str`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `Any` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回输入内容的 SHA-256 身份摘要，用于完整性校验，不是加密后的正文。

**伪代码**

```text
计算输入内容的 SHA-256 身份摘要，并返回处理结果。
```

#### `stable_id`

- **源码**：`app/mcp_gateway/identity.py:34`
- **签名**：`def stable_id(prefix: str, value: Any) -> str`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收目录树缩进前缀、当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `prefix` | `str` | 目录树展示用的缩进前缀；只影响输出排版，不改变仓库路径。 |
| `value` | `Any` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回稳定业务标识符，用于后续查询、关联或幂等绑定；它不是路径或内容 Hash。

**伪代码**

```text
返回当前计算得到的结果。
```

#### `schema_sha256`

- **源码**：`app/mcp_gateway/identity.py:38`
- **签名**：`def schema_sha256(schema: dict[str, Any]) -> str`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，对远端原始 JSON Schema 做确定性 Hash，不做宽松语义折叠。该函数接收输入输出 Schema 契约，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `schema` | `dict[str, Any]` | 结构化输出 Schema 或其名称；用于约束解析结果的字段和类型。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回输入内容的 SHA-256 身份摘要，用于完整性校验，不是加密后的正文。

**伪代码**

```text
调用 `sha256_value` 计算内容身份、分数或派生结果，并返回处理结果。
```

#### `profile_sha256`

- **源码**：`app/mcp_gateway/identity.py:43`
- **签名**：`def profile_sha256(profile: McpServerProfile, binding: McpToolBinding) -> str`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，只绑定一个可调用能力，而不是给整个远端目录授权。该函数接收MCP Client 配置档案、资源绑定记录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `profile` | `McpServerProfile` | 运行/执行环境配置或 profile 标识；描述能力和限制，不是一次执行的结果。 |
| `binding` | `McpToolBinding` | 资源绑定记录；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回输入内容的 SHA-256 身份摘要，用于完整性校验，不是加密后的正文。

**伪代码**

```text
调用 `sha256_value` 计算内容身份、分数或派生结果，并返回处理结果。
```

#### `build_evidence_item`

- **源码**：`app/mcp_gateway/identity.py:63`
- **签名**：`def build_evidence_item(server_id: str, binding_id: str, title: str, source_uri: str, excerpt: str, locator: str) -> McpEvidenceItem`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收外部 MCP 服务端稳定标识、MCP Tool 绑定 ID、文档或章节标题、来源等输入，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `McpEvidenceItem` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `server_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `binding_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `title` | `str` | 论文/文档章节标题；用于建立可检索的章节身份和展示文本。 |
| `source_uri` | `str` | 资源地址；进入网络或持久化前仍需策略校验和必要的脱敏。 |
| `excerpt` | `str` | 名为 `excerpt` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `locator` | `str` | 源码或文档定位信息；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`McpEvidenceItem`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
计算按字段初始化键值映射，并保存为 结构化请求载荷；构造并返回 `McpEvidenceItem` 结构化领域对象。
```

#### `pack_payload`

- **源码**：`app/mcp_gateway/identity.py:90`
- **签名**：`def pack_payload(pack: McpEvidencePack) -> dict[str, Any]`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收检索或映射证据包，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `pack` | `McpEvidencePack` | 检索或映射证据包；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`dict[str, Any]`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
复制、序列化或校验结构化领域对象，并把结果记为 结构化请求载荷；从结构化请求载荷取出并移除最后一项；返回结构化请求载荷的当前值。
```

#### `compute_pack_hash`

- **源码**：`app/mcp_gateway/identity.py:96`
- **签名**：`def compute_pack_hash(pack: McpEvidencePack) -> str`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收检索或映射证据包，用于计算输入、命令、运行配置或证据的稳定派生值，保证复现链路中的身份校验和 stale 检测，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `pack` | `McpEvidencePack` | 检索或映射证据包；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回内容身份摘要，通常为 SHA-256 十六进制字符串。

**伪代码**

```text
调用 `sha256_value` 计算内容身份、分数或派生结果，并返回处理结果。
```

#### `validate_pack_hash`

- **源码**：`app/mcp_gateway/identity.py:100`
- **签名**：`def validate_pack_hash(pack: McpEvidencePack) -> None`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收检索或映射证据包，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `pack` | `McpEvidencePack` | 检索或映射证据包；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
如果辅助操作“调用 `compute_pack_hash` 计算内容身份、分数或派生结果”的结果不等于检索或映射证据包的 SHA-256，就拒绝继续处理并抛出 `McpEvidenceIntegrityError`，向调用方报告输入或运行失败。
遍历当前可迭代输入，每次把当前项记为当前处理项：
    调用 `sha256_value` 计算内容身份、分数或派生结果，并把结果记为 期望值。
    如果期望值不等于当前处理项的 SHA-256，就拒绝继续处理并抛出 `McpEvidenceIntegrityError`，向调用方报告输入或运行失败。
```

### `app/mcp_gateway/policy.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_is_within`

- **源码**：`app/mcp_gateway/policy.py:24`
- **签名**：`def _is_within(path: Path, root: Path) -> bool`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收文件或目录路径、受控扫描根目录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |
| `root` | `Path` | 运行产物或受控工作区的目录路径；用于隔离本次运行生成的文件。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
返回组合判断结果。
```

#### `validate_loopback_endpoint`

- **源码**：`app/mcp_gateway/policy.py:28`
- **签名**：`def validate_loopback_endpoint(endpoint: str) -> None`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，第一版只接受不经过 DNS 的本机 Streamable HTTP endpoint。该函数接收MCP 服务端点地址，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `endpoint` | `str` | MCP 服务端点地址；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
去除MCP 服务端点地址的首尾空白，并把规范化后的文本记为 原始内容。
如果原始内容不等于MCP 服务端点地址 或 由原始内容组成的集合或迭代器中存在满足“当前字符 对应的 ASCII/Unicode 编码小于32 或 当前字符 对应的 ASCII/Unicode 编码等于127”的项，就拒绝继续处理并抛出 `McpEndpointRejected`，向调用方报告输入或运行失败。
先尝试完成以下处理：
    调用 `urlsplit` 完成该函数的一项辅助处理，并把结果记为 解析后的结果；读取服务监听端口，并保存为 服务监听端口。
如果出现 `ValueError`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `McpEndpointRejected`，向调用方报告输入或运行失败。
如果当前处理结果不等于'http'，就拒绝继续处理并抛出 `McpEndpointRejected`，向调用方报告输入或运行失败。
如果当前处理结果不为空 或 当前处理结果不为空，就拒绝继续处理并抛出 `McpEndpointRejected`，向调用方报告输入或运行失败。
如果语义检索问题有值或为真 或 当前处理结果有值或为真，就拒绝继续处理并抛出 `McpEndpointRejected`，向调用方报告输入或运行失败。
如果文件或目录路径不等于'/mcp'，就拒绝继续处理并抛出 `McpEndpointRejected`，向调用方报告输入或运行失败。
如果服务监听端口为空 或 “当前输入内容不大于服务监听端口不大于65535”不成立，就拒绝继续处理并抛出 `McpEndpointRejected`，向调用方报告输入或运行失败。
如果当前处理结果为空，就拒绝继续处理并抛出 `McpEndpointRejected`，向调用方报告输入或运行失败。
先尝试完成以下处理：
    调用 `ip_address` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
如果出现 `ValueError`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `McpEndpointRejected`，向调用方报告输入或运行失败。
如果“是否当前处理结果有值或为真”不成立，就拒绝继续处理并抛出 `McpEndpointRejected`，向调用方报告输入或运行失败。
```

#### `validate_server_profile`

- **源码**：`app/mcp_gateway/policy.py:67`
- **签名**：`def validate_server_profile(profile: McpServerProfile) -> None`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收MCP Client 配置档案，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `profile` | `McpServerProfile` | 运行/执行环境配置或 profile 标识；描述能力和限制，不是一次执行的结果。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `validate_loopback_endpoint` 校验当前输入或状态。
如果功能是否启用的开关有值或为真：
    遍历当前可迭代输入，每次把当前项记为资源绑定记录：
        如果期望的 SHA-256等于'0' × 64，就拒绝继续处理并抛出 `McpPolicyError`，向调用方报告输入或运行失败。
        如果期望的 SHA-256等于'0' × 64，就拒绝继续处理并抛出 `McpPolicyError`，向调用方报告输入或运行失败。
```

#### `load_mcp_gateway_policy`

- **源码**：`app/mcp_gateway/policy.py:78`
- **签名**：`def load_mcp_gateway_policy(path: Path, allowed_root: Path) -> McpGatewayPolicy`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收文件或目录路径、根目录，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `McpGatewayPolicy` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |
| `allowed_root` | `Path` | 已经解析的文件或目录路径对象；后续操作仍需遵守仓库/工作区边界。 |

**输出**

- **Python 类型**：`McpGatewayPolicy`
- **语义**：返回从外部表示解析并校验后的领域值；格式非法时通过异常失败。

**伪代码**

```text
将辅助操作“将根目录规范化为受控的绝对路径”的结果规范化为受控的绝对路径，并把结果记为 受控扫描根目录；将辅助操作“将文件或目录路径规范化为受控的绝对路径”的结果规范化为受控的绝对路径，并把结果记为 待审核的 MCP 能力候选。
如果“调用 `_is_within` 校验当前输入或状态”后未得到肯定结果，就拒绝继续处理并抛出 `McpPolicyError`，向调用方报告输入或运行失败。
如果“检查待审核的 MCP 能力候选的文件系统属性”后未得到肯定结果，就拒绝继续处理并抛出 `McpPolicyError`，向调用方报告输入或运行失败。
如果“检查待审核的 MCP 能力候选的文件系统属性”后得到肯定结果 或 “检查待审核的 MCP 能力候选的文件系统属性”后未得到肯定结果，就拒绝继续处理并抛出 `McpPolicyError`，向调用方报告输入或运行失败。
如果前一步操作返回对象的当前处理结果大于最大安全策略的字节内容，就拒绝继续处理并抛出 `McpPolicyError`，向调用方报告输入或运行失败。
先尝试完成以下处理：
    将外部表示解析为结构化内容，并把结果记为 原始内容；复制、序列化或校验结构化领域对象，并把结果记为 安全策略。
如果出现 `(OSError, UnicodeError, json.JSONDecodeError, ValidationError)`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `McpPolicyError`，向调用方报告输入或运行失败。
遍历当前可迭代输入，每次把当前项记为MCP Client 配置档案，然后调用 `validate_server_profile` 校验当前输入或状态。
返回安全策略的当前值。
```

#### `policy_sha256`

- **源码**：`app/mcp_gateway/policy.py:105`
- **签名**：`def policy_sha256(policy: McpGatewayPolicy) -> str`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收安全策略，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `policy` | `McpGatewayPolicy` | 安全策略；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回输入内容的 SHA-256 身份摘要，用于完整性校验，不是加密后的正文。

**伪代码**

```text
调用 `sha256_value` 计算内容身份、分数或派生结果，并返回处理结果。
```

### `app/mcp_gateway/ports.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `McpClientPort.inspect_tool`

- **源码**：`app/mcp_gateway/ports.py:16`
- **签名**：`def inspect_tool(self: 未显式标注, profile: McpServerProfile, binding: McpToolBinding) -> McpObservedTool`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收MCP Client 配置档案、资源绑定记录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `McpObservedTool` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `profile` | `McpServerProfile` | 运行/执行环境配置或 profile 标识；描述能力和限制，不是一次执行的结果。 |
| `binding` | `McpToolBinding` | 资源绑定记录；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`McpObservedTool`
- **语义**：返回 `McpObservedTool` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `McpClientPort.call_pinned_tool`

- **源码**：`app/mcp_gateway/ports.py:24`
- **签名**：`def call_pinned_tool(self: 未显式标注, profile: McpServerProfile, binding: McpToolBinding, arguments: dict[str, Any]) -> McpRawCallResult`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收MCP Client 配置档案、资源绑定记录、结构化调用参数，用于在固定 MCP Policy、Schema Pin、调用预算和只读职责边界内连接或调用外部能力，并把返回内容转换为可追溯的复现证据，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `profile` | `McpServerProfile` | 运行/执行环境配置或 profile 标识；描述能力和限制，不是一次执行的结果。 |
| `binding` | `McpToolBinding` | 资源绑定记录；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `arguments` | `dict[str, Any]` | 结构化调用参数；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`McpRawCallResult`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

### `app/mcp_gateway/repository.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `SqliteMcpEvidenceRepository.__init__`

- **源码**：`app/mcp_gateway/repository.py:16`
- **签名**：`def __init__(self, path: Path) -> None`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收文件或目录路径，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
将辅助操作“将文件或目录路径规范化为受控的绝对路径”的结果规范化为受控的绝对路径，并把结果记为 文件或目录路径。
```

#### `SqliteMcpEvidenceRepository._connect`

- **源码**：`app/mcp_gateway/repository.py:19`
- **签名**：`def _connect(self) -> sqlite3.Connection`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于在固定 MCP Policy、Schema Pin、调用预算和只读职责边界内连接或调用外部能力，并把返回内容转换为可追溯的复现证据，最终标注为 `sqlite3.Connection` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`sqlite3.Connection`
- **语义**：返回 `sqlite3.Connection` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `connect` 完成该函数的一项辅助处理，并把结果记为 数据库连接；读取数据库记录行，并保存为 记录行；通过数据库连接执行数据查询或命令；通过数据库连接执行数据查询或命令。
返回数据库连接的当前值。
```

#### `SqliteMcpEvidenceRepository.initialize`

- **源码**：`app/mcp_gateway/repository.py:26`
- **签名**：`def initialize(self) -> None`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
创建父级目录或父领域对象对应的目录。
在上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”中调用 `executescript` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `SqliteMcpEvidenceRepository._decode_pack`

- **源码**：`app/mcp_gateway/repository.py:59`
- **签名**：`def _decode_pack(self, raw: str) -> McpEvidencePack`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收原始内容，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `McpEvidencePack` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `raw` | `str` | 外部读取到的原始文本或进程输出；可能需要截断、规范化或脱敏后才能进入报告。 |

**输出**

- **Python 类型**：`McpEvidencePack`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
先尝试完成以下处理：
    调用 `model_validate_json` 完成该函数的一项辅助处理，并把结果记为 检索或映射证据包；调用 `validate_pack_hash` 校验当前输入或状态；返回检索或映射证据包的当前值。
如果出现 `Exception`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `McpEvidenceIntegrityError`，向调用方报告输入或运行失败。
```

#### `SqliteMcpEvidenceRepository.put_success`

- **源码**：`app/mcp_gateway/repository.py:69`
- **签名**：`def put_success(self: 未显式标注, pack: McpEvidencePack, record: McpCallRecord) -> None`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收检索或映射证据包、领域记录，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `pack` | `McpEvidencePack` | 检索或映射证据包；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `record` | `McpCallRecord` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `validate_pack_hash` 校验当前输入或状态。
如果当前状态不等于'succeeded'，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果复现任务 ID不等于复现任务 ID，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果外部 MCP 服务端稳定标识不等于外部 MCP 服务端稳定标识，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果MCP Tool 绑定 ID不等于MCP Tool 绑定 ID，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果阶段处理结果的 SHA-256不等于阶段处理结果的 SHA-256，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
调用 `model_dump_json` 完成该函数的一项辅助处理，并把结果记为 JSON；调用 `model_dump_json` 完成该函数的一项辅助处理，并把结果记为 记录JSON。
进入上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”，退出时自动清理资源：
    调用 `fetchone` 完成该函数的一项辅助处理，并把结果记为 已有记录。
    如果已有记录不为空 且 已有记录中的对应字段不等于JSON，就拒绝继续处理并抛出 `McpEvidenceIntegrityError`，向调用方报告输入或运行失败。
    通过数据库连接执行数据查询或命令；通过数据库连接执行数据查询或命令。
```

#### `SqliteMcpEvidenceRepository.put_failure`

- **源码**：`app/mcp_gateway/repository.py:117`
- **签名**：`def put_failure(self, record: McpCallRecord) -> None`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收领域记录，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `record` | `McpCallRecord` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
如果当前状态不等于'failed'，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
在上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”中通过数据库连接执行数据查询或命令，退出时自动清理资源。
```

#### `SqliteMcpEvidenceRepository.get_pack`

- **源码**：`app/mcp_gateway/repository.py:132`
- **签名**：`def get_pack(self, *, job_id: str, pack_id: str) -> McpEvidencePack`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收复现任务 ID、检索或映射证据包的 ID，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `McpEvidencePack` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `pack_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`McpEvidencePack`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
在上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”中调用 `fetchone` 完成该函数的一项辅助处理，并把结果记为 数据库记录行，退出时自动清理资源。
如果数据库记录行为空，就拒绝继续处理并抛出 `KeyError`，向调用方报告输入或运行失败。
调用 `_decode_pack` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `SqliteMcpEvidenceRepository.list_packs_for_job`

- **源码**：`app/mcp_gateway/repository.py:142`
- **签名**：`def list_packs_for_job(self, *, job_id: str, limit: int = 20) -> list[McpEvidencePack]`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收复现任务 ID、结果数量上限，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。；默认 20 |

**输出**

- **Python 类型**：`list[McpEvidencePack]`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
计算数量、边界或类型判断结果，并把结果记为 上限。
在上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”中调用 `fetchall` 完成该函数的一项辅助处理，并把结果记为 数据库记录行集合，退出时自动清理资源。
返回当前计算得到的结果。
```

#### `SqliteMcpEvidenceRepository.list_calls_for_job`

- **源码**：`app/mcp_gateway/repository.py:151`
- **签名**：`def list_calls_for_job(self, *, job_id: str, limit: int = 100) -> list[McpCallRecord]`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收复现任务 ID、结果数量上限，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。；默认 100 |

**输出**

- **Python 类型**：`list[McpCallRecord]`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
计算数量、边界或类型判断结果，并把结果记为 上限。
在上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”中调用 `fetchall` 完成该函数的一项辅助处理，并把结果记为 数据库记录行集合，退出时自动清理资源。
返回当前计算得到的结果。
```

#### `SqliteMcpEvidenceRepository.delete_for_job`

- **源码**：`app/mcp_gateway/repository.py:160`
- **签名**：`def delete_for_job(self, job_id: str) -> int`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收复现任务 ID，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终数量、序号、字节数或版本等整数结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`int`
- **语义**：返回整数计数、序号、字节数或退出码；具体含义由函数名决定。

**伪代码**

```text
在上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”中读取前一步操作返回对象中的对应字段，并保存为 检索或映射证据包的数量；读取前一步操作返回对象中的对应字段，并保存为 当前处理结果的数量；通过数据库连接执行数据查询或命令；通过数据库连接执行数据查询或命令，退出时自动清理资源。
返回当前计算得到的结果。
```

### `app/mcp_gateway/schemas.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `McpServerProfile.validate_unique_bindings`

- **源码**：`app/mcp_gateway/schemas.py:62`
- **签名**：`def validate_unique_bindings(self) -> "McpServerProfile"`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `'McpServerProfile'` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`'McpServerProfile'`
- **语义**：返回 `'McpServerProfile'` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
遍历并筛选输入，将整理后的结果保存为 绑定集合；遍历并筛选输入，将整理后的结果保存为 当前处理结果；遍历并筛选输入，将整理后的结果保存为 远程集合。
如果绑定集合 的长度不等于辅助操作“构造临时集合、映射或轻量领域对象”的结果 的长度，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果当前处理结果 的长度不等于辅助操作“构造临时集合、映射或轻量领域对象”的结果 的长度，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果远程集合 的长度不等于辅助操作“构造临时集合、映射或轻量领域对象”的结果 的长度，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前对象的当前值。
```

#### `McpGatewayPolicy.validate_unique_servers`

- **源码**：`app/mcp_gateway/schemas.py:84`
- **签名**：`def validate_unique_servers(self) -> "McpGatewayPolicy"`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `'McpGatewayPolicy'` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`'McpGatewayPolicy'`
- **语义**：返回 `'McpGatewayPolicy'` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
遍历并筛选输入，将整理后的结果保存为 当前处理结果。
如果当前处理结果 的长度不等于辅助操作“构造临时集合、映射或轻量领域对象”的结果 的长度，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
遍历并筛选输入，将整理后的结果保存为 当前处理结果。
如果当前处理结果 的长度不等于辅助操作“构造临时集合、映射或轻量领域对象”的结果 的长度，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前对象的当前值。
```

#### `McpGatewayPolicy.enabled_binding`

- **源码**：`app/mcp_gateway/schemas.py:99`
- **签名**：`def enabled_binding(self: 未显式标注, alias: str) -> tuple[McpServerProfile, McpToolBinding] | None`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收对象别名，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `alias` | `str` | 对象别名；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`tuple[McpServerProfile, McpToolBinding] | None`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
遍历并筛选输入，将整理后的结果保存为 当前处理结果。
如果当前处理结果为空或为假，就返回固定值 `空值`。
如果当前处理结果 的长度不等于1，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前处理结果中的对应字段的当前值。
```

#### `McpSearchInput.normalize_query`

- **源码**：`app/mcp_gateway/schemas.py:125`
- **签名**：`def normalize_query(cls, value: str) -> str`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前字段值，用于读取并整理论文、源码或运行产物，把原始输入转换成带位置和身份信息的结构化证据，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `cls` | `未显式标注` | 当前类对象，用于类级构造或校验。 |
| `value` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回整理、格式化或规范化后的文本表示。

**伪代码**

```text
如果由当前字段值组成的集合或迭代器中存在满足“当前字符 对应的 ASCII/Unicode 编码小于32 或 当前字符 对应的 ASCII/Unicode 编码等于127”的项，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
调用 `join` 完成该函数的一项辅助处理，并把结果记为 规范化后的文本。
如果规范化后的文本 的长度小于2，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回规范化后的文本的当前值。
```

#### `McpEvidencePack.validate_unique_items`

- **源码**：`app/mcp_gateway/schemas.py:202`
- **签名**：`def validate_unique_items(self) -> "McpEvidencePack"`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `'McpEvidencePack'` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`'McpEvidencePack'`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
遍历并筛选输入，将整理后的结果保存为 当前处理结果。
如果当前处理结果 的长度不等于辅助操作“构造临时集合、映射或轻量领域对象”的结果 的长度，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前对象的当前值。
```

#### `McpCallRecord.validate_status_fields`

- **源码**：`app/mcp_gateway/schemas.py:231`
- **签名**：`def validate_status_fields(self) -> "McpCallRecord"`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`'McpCallRecord'`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
如果当前状态等于'succeeded'：
    如果阶段处理结果的 SHA-256为空 或 错误不为空，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
否则：
    如果错误为空，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前对象的当前值。
```

### `app/mcp_gateway/tool_adapter.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `McpEvidenceGatewayPort.authority_fingerprint`

- **源码**：`app/mcp_gateway/tool_adapter.py:23`
- **签名**：`def authority_fingerprint(self) -> str`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回内容身份摘要，通常为 SHA-256 十六进制字符串。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `McpEvidenceGatewayPort.search`

- **源码**：`app/mcp_gateway/tool_adapter.py:26`
- **签名**：`def search(self, *, job_id: str, request_id: str, payload: McpSearchInput) -> McpEvidencePack`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收复现任务 ID、MCP 请求 ID、结构化请求载荷，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `McpEvidencePack` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `request_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `payload` | `McpSearchInput` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`McpEvidencePack`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `_pack_to_output`

- **源码**：`app/mcp_gateway/tool_adapter.py:30`
- **签名**：`def _pack_to_output(pack: McpEvidencePack) -> "EvidenceToolOutput"`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收检索或映射证据包，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `'EvidenceToolOutput'` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `pack` | `McpEvidencePack` | 检索或映射证据包；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`'EvidenceToolOutput'`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
加载这一步需要的外部依赖；将 待处理项集合 初始化为空列表，用来收集后续结果。
遍历当前可迭代输入，每次把当前项记为当前处理项，然后调用 `stable_id` 完成该函数的一项辅助处理，并把结果记为 论文引用证据的 ID；加载这一步需要的外部依赖；构造 `ChatCitation` 结构化领域对象，并把结果记为 论文引用证据；把新的处理结果追加或合并到待处理项集合。
构造并返回 `EvidenceToolOutput` 结构化领域对象。
```

#### `_map_mcp_error`

- **源码**：`app/mcp_gateway/tool_adapter.py:65`
- **签名**：`def _map_mcp_error(exc: BaseException) -> "ToolFailure | None"`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收捕获的异常，用于把论文中的方法、模块或实验意图与仓库中的可验证对象建立稳定关联，并保留匹配依据，最终标注为 `'ToolFailure | None'` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `exc` | `BaseException` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`'ToolFailure | None'`
- **语义**：返回 `'ToolFailure | None'` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
加载这一步需要的外部依赖。
如果“计算数量、边界或类型判断结果”后得到肯定结果，就构造并返回 `ToolFailure` 结构化领域对象。
返回固定值 `空值`。
```

#### `register_mcp_evidence_tool`

- **源码**：`app/mcp_gateway/tool_adapter.py:88`
- **签名**：`def register_mcp_evidence_tool(*, registry: "ToolRegistry", gateway: McpEvidenceGatewayPort) -> None`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收组件注册表、外部服务网关，用于在固定 MCP Policy、Schema Pin、调用预算和只读职责边界内连接或调用外部能力，并把返回内容转换为可追溯的复现证据，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `registry` | `'ToolRegistry'` | 组件注册表；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `gateway` | `McpEvidenceGatewayPort` | 外部服务网关；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
加载这一步需要的外部依赖；加载这一步需要的外部依赖；加载这一步需要的外部依赖；遍历并筛选输入，将整理后的结果保存为 当前处理结果。
定义内部辅助函数 `search_external`，供当前函数在后续步骤中调用。
调用 `register` 完成该函数的一项辅助处理。
```

#### `register_mcp_evidence_tool.search_external`

- **源码**：`app/mcp_gateway/tool_adapter.py:101`
- **签名**：`def search_external(payload: McpSearchInput, context: ToolInvocationContext) -> EvidenceToolOutput`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收结构化请求载荷、运行上下文，用于在固定 MCP Policy、Schema Pin、调用预算和只读职责边界内连接或调用外部能力，并把返回内容转换为可追溯的复现证据，最终标注为 `EvidenceToolOutput` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `payload` | `McpSearchInput` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `context` | `ToolInvocationContext` | 运行上下文；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`EvidenceToolOutput`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
如果复现任务 ID为空 或 “对复现任务 ID中的文本执行规范化或拆分”后未得到肯定结果，就拒绝继续处理并抛出 `McpGatewayError`，向调用方报告输入或运行失败。
调用 `search` 完成该函数的一项辅助处理，并把结果记为 检索或映射证据包；调用 `_pack_to_output` 完成该函数的一项辅助处理，并返回处理结果。
```

### `app/mcp_operations/commands.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_in_memory_target`

- **源码**：`app/mcp_operations/commands.py:35`
- **签名**：`def _in_memory_target(profile: McpClientProfile, server: Any, timeout_seconds: float) -> McpProbeTarget`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收MCP Client 配置档案、MCP 服务端实例、等待超时时间（秒），用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `McpProbeTarget` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `profile` | `McpClientProfile` | 运行/执行环境配置或 profile 标识；描述能力和限制，不是一次执行的结果。 |
| `server` | `Any` | MCP 服务端实例；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `timeout_seconds` | `float` | 超时或截止时间限制；用于防止等待/搜索/执行无限持续。 |

**输出**

- **Python 类型**：`McpProbeTarget`
- **语义**：返回 `McpProbeTarget` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
定义内部辅助函数 `connect`，供当前函数在后续步骤中调用。
构造并返回 `McpProbeTarget` 结构化领域对象。
```

#### `_in_memory_target.connect`

- **源码**：`app/mcp_operations/commands.py:41`
- **签名**：`def connect()`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于在固定 MCP Policy、Schema Pin、调用预算和只读职责边界内连接或调用外部能力，并把返回内容转换为可追溯的复现证据，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
加载这一步需要的外部依赖；构造并返回 `Client` 结构化领域对象。
```

#### `_resolve_profile_token`

- **源码**：`app/mcp_operations/commands.py:54`
- **签名**：`def _resolve_profile_token(profile: McpClientProfile) -> str`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收MCP Client 配置档案，用于把论文中的方法、模块或实验意图与仓库中的可验证对象建立稳定关联，并保留匹配依据，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `profile` | `McpClientProfile` | 运行/执行环境配置或 profile 标识；描述能力和限制，不是一次执行的结果。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
如果敏感凭据的名称为空，就拒绝继续处理并抛出 `McpRuntimePolicyInvalid`，向调用方报告输入或运行失败。
调用 `resolve_current` 解析、规范化或转换当前输入，并把结果记为 待处理的论文或源码材料；调用 `reveal` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `_http_client_context`

- **源码**：`app/mcp_operations/commands.py:68`
- **签名**：`async def _http_client_context(profile: McpClientProfile, token: str, timeout_seconds: float) -> None（隐式）`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收MCP Client 配置档案、模型或命令 token、等待超时时间（秒），用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `profile` | `McpClientProfile` | 运行/执行环境配置或 profile 标识；描述能力和限制，不是一次执行的结果。 |
| `token` | `str` | 敏感凭证或其引用；不得写入日志、Prompt 或普通 Artifact。 |
| `timeout_seconds` | `float` | 超时或截止时间限制；用于防止等待/搜索/执行无限持续。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
如果MCP 服务端点地址为空，就拒绝继续处理并抛出 `McpRuntimePolicyInvalid`，向调用方报告输入或运行失败。
加载这一步需要的外部依赖；加载这一步需要的外部依赖；加载这一步需要的外部依赖。
进入异步上下文“构造 `AsyncClient` 结构化领域对象，并把上下文资源交给当前处理结果”，退出时自动清理资源：
    调用 `streamable_http_client` 完成该函数的一项辅助处理，并把结果记为 外部资源传输端口。
    在异步上下文“构造 `Client` 结构化领域对象，并把上下文资源交给外部服务客户端”中完成当前表达式对应的校验或状态操作，退出时自动清理资源。
```

#### `_http_target`

- **源码**：`app/mcp_operations/commands.py:100`
- **签名**：`def _http_target(profile: McpClientProfile, timeout_seconds: float) -> McpProbeTarget`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收MCP Client 配置档案、等待超时时间（秒），用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `McpProbeTarget` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `profile` | `McpClientProfile` | 运行/执行环境配置或 profile 标识；描述能力和限制，不是一次执行的结果。 |
| `timeout_seconds` | `float` | 超时或截止时间限制；用于防止等待/搜索/执行无限持续。 |

**输出**

- **Python 类型**：`McpProbeTarget`
- **语义**：返回 `McpProbeTarget` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `_resolve_profile_token` 解析、规范化或转换当前输入，并把结果记为 模型或命令 token。
定义内部辅助函数 `connect`，供当前函数在后续步骤中调用。
构造并返回 `McpProbeTarget` 结构化领域对象。
```

#### `_http_target.connect`

- **源码**：`app/mcp_operations/commands.py:108`
- **签名**：`def connect()`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于在固定 MCP Policy、Schema Pin、调用预算和只读职责边界内连接或调用外部能力，并把返回内容转换为可追溯的复现证据，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
调用 `_http_client_context` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `_build_targets`

- **源码**：`app/mcp_operations/commands.py:118`
- **签名**：`def _build_targets(mode: ProbeMode) -> tuple[list[McpProbeTarget], Any, Any]`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收MCP 评测或运行模式，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `mode` | `ProbeMode` | MCP 评测或运行模式；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`tuple[list[McpProbeTarget], Any, Any]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
调用 `load_runtime_policy` 读取或查询当前阶段需要的数据，并把结果记为 安全策略；调用 `load_client_profiles` 读取或查询当前阶段需要的数据，并把结果记为 MCP Client 配置档案集合；遍历并筛选输入，将整理后的结果保存为 配置的 ID；计算根据条件从两个候选结果中选择一个，并保存为 当前处理结果。
按稳定规则整理结果顺序，并把结果记为 该调用返回的结果。
如果当前处理结果有值或为真，就拒绝继续处理并抛出 `McpRuntimePolicyInvalid`，向调用方报告输入或运行失败。
调用 `build_mcp_export_runtime` 组装当前阶段需要的领域对象，并把结果记为 运行时环境；调用 `build_mcp_export_server` 组装当前阶段需要的领域对象，并把结果记为 MCP 服务端实例；将 待定位的代码对象集合 初始化为空列表，用来收集后续结果。
遍历由当前处理结果组成的集合或迭代器，每次把当前项记为MCP Client 配置档案 ID：
    读取配置的 ID中的对应字段，并保存为 MCP Client 配置档案。
    如果MCP 评测或运行模式等于'offline' 且 外部资源传输端口不等于'in_memory'，就拒绝继续处理并抛出 `McpRuntimePolicyInvalid`，向调用方报告输入或运行失败。
    如果外部资源传输端口等于'in_memory'：
        把新的处理结果追加或合并到待定位的代码对象集合。
    否则：
        如果MCP 评测或运行模式等于'release'，就把新的处理结果追加或合并到待定位的代码对象集合。
返回当前构造的顺序或去重集合。
```

#### `run_runtime_evaluation`

- **源码**：`app/mcp_operations/commands.py:174`
- **签名**：`def run_runtime_evaluation(mode: ProbeMode, job_id: str) -> 未显式标注（存在 return）`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收MCP 评测或运行模式、复现任务 ID，用于发现、观测或评估 MCP 的公开 Tool/Resource/Prompt 契约，比较协议、Schema、延迟和失败结果，并为论文复现系统保留可审核的基线或运行报告，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `mode` | `ProbeMode` | MCP 评测或运行模式；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
调用 `_build_targets` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果；调用 `load_baseline` 读取或查询当前阶段需要的数据，并把结果记为 已审核的 MCP 能力基线；调用 `run` 完成该函数的一项辅助处理，并把结果记为 MCP 评测或运行报告；读取运行时环境，并保存为 后续步骤使用的结果。
调用 `write_runtime_report` 持久化或更新当前领域数据，并把结果记为 多个解包结果；返回当前构造的顺序或去重集合。
```

#### `compare_upgrade_reports`

- **源码**：`app/mcp_operations/commands.py:199`
- **签名**：`def compare_upgrade_reports(before_path: Path, after_path: Path) -> 未显式标注（存在 return）`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收升级前报告路径、升级后报告路径，用于发现、观测或评估 MCP 的公开 Tool/Resource/Prompt 契约，比较协议、Schema、延迟和失败结果，并为论文复现系统保留可审核的基线或运行报告，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `before_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `after_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
读取运行时根目录，并保存为 受控扫描根目录；调用 `load_runtime_policy` 读取或查询当前阶段需要的数据，并把结果记为 安全策略；调用 `load_baseline` 读取或查询当前阶段需要的数据，并把结果记为 已审核的 MCP 能力基线；调用 `load_runtime_report` 读取或查询当前阶段需要的数据，并把结果记为 升级前运行报告。
调用 `load_runtime_report` 读取或查询当前阶段需要的数据，并把结果记为 升级后运行报告；调用 `compare_runtime_reports` 完成该函数的一项辅助处理，并把结果记为 SDK 或 MCP 运行升级比较结果；调用 `write_upgrade_comparison` 持久化或更新当前领域数据，并把结果记为 输出结果的路径；返回当前构造的顺序或去重集合。
```

### `app/mcp_operations/identity.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `policy_hash`

- **源码**：`app/mcp_operations/identity.py:11`
- **签名**：`def policy_hash(policy: McpRuntimePolicy) -> str`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收安全策略，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `policy` | `McpRuntimePolicy` | 安全策略；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回内容身份摘要，通常为 SHA-256 十六进制字符串。

**伪代码**

```text
复制、序列化或校验结构化领域对象，并把结果记为 结构化请求载荷；调用 `sha256_value` 计算内容身份、分数或派生结果，并返回处理结果。
```

#### `runtime_report_hash`

- **源码**：`app/mcp_operations/identity.py:19`
- **签名**：`def runtime_report_hash(report: McpRuntimeReport) -> str`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收MCP 评测或运行报告，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `report` | `McpRuntimeReport` | MCP 评测或运行报告；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回内容身份摘要，通常为 SHA-256 十六进制字符串。

**伪代码**

```text
复制、序列化或校验结构化领域对象，并把结果记为 结构化请求载荷；调用 `sha256_value` 计算内容身份、分数或派生结果，并返回处理结果。
```

#### `upgrade_comparison_hash`

- **源码**：`app/mcp_operations/identity.py:27`
- **签名**：`def upgrade_comparison_hash(comparison: McpUpgradeComparison) -> str`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收SDK 或 MCP 运行升级比较结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `comparison` | `McpUpgradeComparison` | SDK 或 MCP 运行升级比较结果；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回内容身份摘要，通常为 SHA-256 十六进制字符串。

**伪代码**

```text
复制、序列化或校验结构化领域对象，并把结果记为 结构化请求载荷；调用 `sha256_value` 计算内容身份、分数或派生结果，并返回处理结果。
```

### `app/mcp_operations/policy.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_inside_allowed_root`

- **源码**：`app/mcp_operations/policy.py:20`
- **签名**：`def _inside_allowed_root(path: Path, allowed_root: Path) -> Path`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收文件或目录路径、根目录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个经过边界校验的文件或目录路径。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |
| `allowed_root` | `Path` | 已经解析的文件或目录路径对象；后续操作仍需遵守仓库/工作区边界。 |

**输出**

- **Python 类型**：`Path`
- **语义**：返回解析后的文件或目录路径对象。

**伪代码**

```text
如果“检查文件或目录路径的文件系统属性”后得到肯定结果，就拒绝继续处理并抛出 `McpRuntimePolicyInvalid`，向调用方报告输入或运行失败。
将辅助操作“将文件或目录路径规范化为受控的绝对路径”的结果规范化为受控的绝对路径，并把结果记为 解析后的值；将辅助操作“将根目录规范化为受控的绝对路径”的结果规范化为受控的绝对路径，并把结果记为 受控扫描根目录。
如果解析后的值等于受控扫描根目录 或 受控扫描根目录不属于当前处理结果，就拒绝继续处理并抛出 `McpRuntimePolicyInvalid`，向调用方报告输入或运行失败。
返回解析后的值的当前值。
```

#### `load_runtime_policy`

- **源码**：`app/mcp_operations/policy.py:34`
- **签名**：`def load_runtime_policy(path: Path, allowed_root: Path) -> McpRuntimePolicy`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收文件或目录路径、根目录，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `McpRuntimePolicy` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |
| `allowed_root` | `Path` | 已经解析的文件或目录路径对象；后续操作仍需遵守仓库/工作区边界。 |

**输出**

- **Python 类型**：`McpRuntimePolicy`
- **语义**：返回从外部表示解析并校验后的领域值；格式非法时通过异常失败。

**伪代码**

```text
调用 `_inside_allowed_root` 完成该函数的一项辅助处理，并把结果记为 选中的候选项。
如果“检查选中的候选项的文件系统属性”后未得到肯定结果，就拒绝继续处理并抛出 `McpRuntimePolicyInvalid`，向调用方报告输入或运行失败。
先尝试完成以下处理：
    调用 `model_validate_json` 完成该函数的一项辅助处理，并把结果记为 安全策略。
如果出现 `(OSError, UnicodeError, ValueError)`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `McpRuntimePolicyInvalid`，向调用方报告输入或运行失败。
如果辅助操作“调用 `policy_hash` 完成该函数的一项辅助处理”的结果不等于安全策略的 SHA-256，就拒绝继续处理并抛出 `McpRuntimePolicyInvalid`，向调用方报告输入或运行失败。
如果辅助操作“构造临时集合、映射或轻量领域对象”的结果不等于当前处理结果，就拒绝继续处理并抛出 `McpRuntimePolicyInvalid`，向调用方报告输入或运行失败。
如果“调用 `issubset` 完成该函数的一项辅助处理”后未得到肯定结果，就拒绝继续处理并抛出 `McpRuntimePolicyInvalid`，向调用方报告输入或运行失败。
返回安全策略的当前值。
```

### `app/mcp_operations/probe.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `utc_now`

- **源码**：`app/mcp_operations/probe.py:64`
- **签名**：`def utc_now() -> str`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `isoformat` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `_p95`

- **源码**：`app/mcp_operations/probe.py:68`
- **签名**：`def _p95(values: list[float]) -> float`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，使用 nearest-rank；少量本地样本也能得到确定性结果。该函数接收状态字段集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终用于排序或质量评估的分数、比例或相似度。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `values` | `list[float]` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`float`
- **语义**：返回浮点分数、时间或比例值。

**伪代码**

```text
如果状态字段集合为空或为假，就返回固定值 `0.0`。
按稳定规则整理结果顺序，并把结果记为 该调用返回的结果；计算数量、边界或类型判断结果，并把结果记为 当前候选项的索引；返回当前处理结果中的对应字段的当前值。
```

#### `_classify_exception`

- **源码**：`app/mcp_operations/probe.py:78`
- **签名**：`def _classify_exception(exc: BaseException) -> tuple[McpOperationStatus, str]`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收捕获的异常，用于把论文中的方法、模块或实验意图与仓库中的可验证对象建立稳定关联，并保留匹配依据，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `exc` | `BaseException` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`tuple[McpOperationStatus, str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
调用 `str` 完成该函数的一项辅助处理，并把结果记为 当前处理结果的文本。
如果“计算数量、边界或类型判断结果”后得到肯定结果，就返回当前构造的顺序或去重集合。
如果当前输入内容属于当前处理结果的文本，就返回当前构造的顺序或去重集合。
如果当前输入内容属于当前处理结果的文本，就返回当前构造的顺序或去重集合。
如果“计算数量、边界或类型判断结果”后得到肯定结果，就返回当前构造的顺序或去重集合。
如果“计算数量、边界或类型判断结果”后得到肯定结果，就返回当前构造的顺序或去重集合。
读取前一步操作返回对象的当前处理结果，并保存为 Python 模块。
如果“检查Python 模块是否满足文本匹配条件”后得到肯定结果，就返回当前构造的顺序或去重集合。
返回当前构造的顺序或去重集合。
```

#### `_call_tool`

- **源码**：`app/mcp_operations/probe.py:100`
- **签名**：`async def _call_tool(client: Any, name: str, arguments: dict[str, Any], timeout_seconds: float) -> Any`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收外部服务客户端、对象名称、结构化调用参数、等待超时时间（秒），用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `Any` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `client` | `Any` | 外部服务客户端；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `name` | `str` | 对象名称；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `arguments` | `dict[str, Any]` | 结构化调用参数；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `timeout_seconds` | `float` | 超时或截止时间限制；用于防止等待/搜索/执行无限持续。 |

**输出**

- **Python 类型**：`Any`
- **语义**：异步返回 `Any` 结果；调用方必须 `await`。

**伪代码**

```text
等待异步处理完成，并把结果记为 阶段处理结果。
如果是否错误信息是真，就拒绝继续处理并抛出 `_ProbeToolError`，向调用方报告输入或运行失败。
如果内容为空，就拒绝继续处理并抛出 `_ProbeSchemaError`，向调用方报告输入或运行失败。
返回内容的当前值。
```

#### `_read_resource`

- **源码**：`app/mcp_operations/probe.py:122`
- **签名**：`async def _read_resource(client: Any, uri: str, timeout_seconds: float) -> Any`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收外部服务客户端、MCP 资源或外部研究地址、等待超时时间（秒），用于读取并整理论文、源码或运行产物，把原始输入转换成带位置和身份信息的结构化证据，最终标注为 `Any` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `client` | `Any` | 外部服务客户端；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `uri` | `str` | 资源地址；进入网络或持久化前仍需策略校验和必要的脱敏。 |
| `timeout_seconds` | `float` | 超时或截止时间限制；用于防止等待/搜索/执行无限持续。 |

**输出**

- **Python 类型**：`Any`
- **语义**：异步返回 `Any` 结果；调用方必须 `await`。

**伪代码**

```text
等待异步处理完成，并把结果记为 阶段处理结果。
如果“当前处理结果有值或为真”不成立，就拒绝继续处理并抛出 `_ProbeSchemaError`，向调用方报告输入或运行失败。
复制、序列化或校验结构化领域对象，并返回处理结果。
```

#### `_operations`

- **源码**：`app/mcp_operations/probe.py:138`
- **签名**：`def _operations(job_id: str) -> list[_Operation]`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，固定六个只读操作；闭包只在本次 Probe 生命周期内持有 Job ID。该函数接收复现任务 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`list[_Operation]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
返回当前构造的顺序或去重集合。
```

#### `_sample_operation`

- **源码**：`app/mcp_operations/probe.py:208`
- **签名**：`async def _sample_operation(client: Any, profile_id: str, operation: _Operation, sample_index: int, timeout_seconds: float) -> McpInvocationSample`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收外部服务客户端、MCP Client 配置档案 ID、MCP 业务操作名称、操作采样序号等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `McpInvocationSample` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `client` | `Any` | 外部服务客户端；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `profile_id` | `str` | MCP Client 配置档案 ID；用于区分连接地址、协议版本和能力基线。 |
| `operation` | `_Operation` | MCP 业务操作名称；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `sample_index` | `int` | 候选集合中的零基索引，用于定位选中项；它不是业务 ID 或内容 Hash。 |
| `timeout_seconds` | `float` | 超时或截止时间限制；用于防止等待/搜索/执行无限持续。 |

**输出**

- **Python 类型**：`McpInvocationSample`
- **语义**：异步返回 `McpInvocationSample` 结果；调用方必须 `await`。

**伪代码**

```text
调用 `perf_counter` 完成该函数的一项辅助处理，并把结果记为 运行是否已经启动的判断。
先尝试完成以下处理：
    等待异步处理完成，并把结果记为 输出结果。
如果出现 `Exception`并把异常保存为捕获的异常对象：
    调用 `_classify_exception` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；构造并返回 `McpInvocationSample` 结构化领域对象。
构造并返回 `McpInvocationSample` 结构化领域对象。
```

#### `_connection_failure_samples`

- **源码**：`app/mcp_operations/probe.py:242`
- **签名**：`def _connection_failure_samples(profile_id: str, operations: list[_Operation], sample_count: int, exc: BaseException) -> list[McpInvocationSample]`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收MCP Client 配置档案 ID、MCP 业务操作集合、操作采样数量、捕获的异常，用于在固定 MCP Policy、Schema Pin、调用预算和只读职责边界内连接或调用外部能力，并把返回内容转换为可追溯的复现证据，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `profile_id` | `str` | MCP Client 配置档案 ID；用于区分连接地址、协议版本和能力基线。 |
| `operations` | `list[_Operation]` | MCP 业务操作集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `sample_count` | `int` | 对象数量或重试次数，用于范围和上限校验，不是进程退出码。 |
| `exc` | `BaseException` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`list[McpInvocationSample]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
调用 `_classify_exception` 完成该函数的一项辅助处理，并把结果记为 多个解包结果。
如果当前状态不属于{'timeout', 'transport_error'}，就计算使用固定配置或常量值，并保存为 当前状态；计算使用固定配置或常量值，并保存为 错误。
返回当前计算得到的结果。
```

#### `_summarize_operation`

- **源码**：`app/mcp_operations/probe.py:268`
- **签名**：`def _summarize_operation(profile_id: str, operation: _Operation, samples: list[McpInvocationSample], policy: McpRuntimePolicy) -> McpOperationSummary`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收MCP Client 配置档案 ID、MCP 业务操作名称、操作采样结果集合、安全策略，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `McpOperationSummary` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `profile_id` | `str` | MCP Client 配置档案 ID；用于区分连接地址、协议版本和能力基线。 |
| `operation` | `_Operation` | MCP 业务操作名称；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `samples` | `list[McpInvocationSample]` | 操作采样结果集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `policy` | `McpRuntimePolicy` | 安全策略；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`McpOperationSummary`
- **语义**：返回 `McpOperationSummary` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
遍历并筛选输入，将整理后的结果保存为 选中的候选项。
如果选中的候选项为空或为假，就构造并返回 `McpOperationSummary` 结构化领域对象。
调用 `sum` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；计算组合或计算已有值，并保存为 成功比例；调用 `_p95` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；将 诊断发现集合 初始化为空列表，用来收集后续结果。
如果成功比例小于成功比例，就把新的处理结果追加或合并到诊断发现集合。
如果当前处理结果大于当前处理结果，就把新的处理结果追加或合并到诊断发现集合。
遍历辅助操作产生的可迭代结果（按稳定规则整理结果顺序），每次把当前项记为当前状态，然后把新的处理结果追加或合并到诊断发现集合。
构造并返回 `McpOperationSummary` 结构化领域对象。
```

#### `_profile_result`

- **源码**：`app/mcp_operations/probe.py:316`
- **签名**：`def _profile_result(profile: McpClientProfile, runtime: McpRuntimeFingerprint | None, surface_sha256: str | None, baseline: McpContractBaseline, operations: list[_Operation], samples: list[McpInvocationSample], policy: McpRuntimePolicy, connection_failed: bool) -> McpRuntimeProfileResult`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收MCP Client 配置档案、运行时环境、MCP 能力表面的 SHA-256、已审核的 MCP 能力基线等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `profile` | `McpClientProfile` | 运行/执行环境配置或 profile 标识；描述能力和限制，不是一次执行的结果。 |
| `runtime` | `McpRuntimeFingerprint | None` | 运行时环境；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `surface_sha256` | `str | None` | MCP 能力表面的 SHA-256；用于确认 Tool、Resource、Prompt 目录没有发生未审核漂移。 |
| `baseline` | `McpContractBaseline` | 已审核的 MCP 能力基线；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `operations` | `list[_Operation]` | MCP 业务操作集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `samples` | `list[McpInvocationSample]` | 操作采样结果集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `policy` | `McpRuntimePolicy` | 安全策略；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `connection_failed` | `bool` | 布尔条件或能力开关，用于控制流程分支。 |

**输出**

- **Python 类型**：`McpRuntimeProfileResult`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
遍历并筛选输入，将整理后的结果保存为 当前处理结果；将 诊断发现集合 初始化为空列表，用来收集后续结果。
如果当前处理结果有值或为真，就把新的处理结果追加或合并到诊断发现集合。
如果MCP 能力表面的 SHA-256不等于已接受 MCP 能力表面的 SHA-256，就把新的处理结果追加或合并到诊断发现集合。
如果运行时环境为空：
    把新的处理结果追加或合并到诊断发现集合。
否则：
    如果当前处理结果不属于当前处理结果，就把新的处理结果追加或合并到诊断发现集合。
    如果MCP 协议版本不属于当前处理结果，就把新的处理结果追加或合并到诊断发现集合。
如果由当前处理结果组成的集合或迭代器中存在满足““当前处理结果有值或为真”不成立”的项，就把新的处理结果追加或合并到诊断发现集合。
构造并返回 `McpRuntimeProfileResult` 结构化领域对象。
```

#### `run_runtime_probe`

- **源码**：`app/mcp_operations/probe.py:361`
- **签名**：`async def run_runtime_probe(mode: ProbeMode, policy: McpRuntimePolicy, baseline: McpContractBaseline, targets: list[McpProbeTarget], job_id: str) -> McpRuntimeReport`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，顺序执行，避免 Probe 自己触发 Phase 54 调用速率限制。该函数接收MCP 评测或运行模式、安全策略、已审核的 MCP 能力基线、待定位的代码对象集合等输入，用于发现、观测或评估 MCP 的公开 Tool/Resource/Prompt 契约，比较协议、Schema、延迟和失败结果，并为论文复现系统保留可审核的基线或运行报告，最终标注为 `McpRuntimeReport` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `mode` | `ProbeMode` | MCP 评测或运行模式；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `policy` | `McpRuntimePolicy` | 安全策略；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `baseline` | `McpContractBaseline` | 已审核的 MCP 能力基线；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `targets` | `list[McpProbeTarget]` | 待定位的代码对象集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`McpRuntimeReport`
- **语义**：异步返回 `McpRuntimeReport` 结果；调用方必须 `await`。

**伪代码**

```text
调用 `validate_job_id` 校验当前输入或状态，并把结果记为 任务的 ID；调用 `_operations` 完成该函数的一项辅助处理，并把结果记为 MCP 业务操作集合；构造临时集合、映射或轻量领域对象，并把结果记为 期望集合。
如果当前输入内容不等于期望集合，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
计算根据条件从两个候选结果中选择一个，并保存为 当前处理结果；遍历并筛选输入，将整理后的结果保存为 当前处理结果的 ID；将 操作采样结果集合、配置结果集合集合、发现集合集合 初始化为空列表，用来收集后续结果。
遍历由当前处理结果组成的集合或迭代器，每次把当前项记为MCP Client 配置档案 ID：
    从当前处理结果的 ID读取所需的状态或领域记录，并把结果记为 待定位的代码对象或业务目标。
    如果待定位的代码对象或业务目标为空，就把新的处理结果追加或合并到发现集合集合；跳过本轮剩余处理，直接进入下一轮。
    计算使用固定配置或常量值，并保存为 运行时环境；计算使用固定配置或常量值，并保存为 MCP 能力表面的 SHA-256；计算使用固定配置或常量值，并保存为 当前处理结果；将 配置集合 初始化为空列表，用来收集后续结果。
    先尝试完成以下处理：
        进入异步上下文“调用 `connect` 完成该函数的一项辅助处理，并把上下文资源交给外部服务客户端”，退出时自动清理资源：
            等待异步处理完成，并把结果记为 MCP Client 单次观测结果；读取运行时环境，并保存为 运行时环境；读取MCP 能力表面的 SHA-256，并保存为 MCP 能力表面的 SHA-256。
            遍历由MCP 业务操作集合组成的集合或迭代器，每次把当前项记为MCP 业务操作名称：
                遍历限定范围内的序列，每次把当前项记为当前候选项的索引，然后把新的处理结果追加或合并到配置集合。
    如果出现 `Exception`并把异常保存为捕获的异常对象：
        计算使用固定配置或常量值，并保存为 当前处理结果；调用 `_connection_failure_samples` 完成该函数的一项辅助处理，并把结果记为 配置集合。
    把配置集合追加或合并到操作采样结果集合；把新的处理结果追加或合并到配置结果集合集合。
如果配置结果集合集合 的长度不等于当前处理结果 的长度，就把新的处理结果追加或合并到发现集合集合。
如果由配置结果集合集合组成的集合或迭代器中存在满足““当前处理结果有值或为真”不成立”的项，就把新的处理结果追加或合并到发现集合集合。
计算按字段初始化键值映射，并保存为 结构化请求载荷；构造 `McpRuntimeReport` 结构化领域对象，并把结果记为 MCP 评测或运行报告；复制、序列化或校验结构化领域对象，并返回处理结果。
```

### `app/mcp_operations/repository.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_inside_root`

- **源码**：`app/mcp_operations/repository.py:20`
- **签名**：`def _inside_root(path: Path, root: Path) -> Path`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收文件或目录路径、受控扫描根目录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个经过边界校验的文件或目录路径。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |
| `root` | `Path` | 运行产物或受控工作区的目录路径；用于隔离本次运行生成的文件。 |

**输出**

- **Python 类型**：`Path`
- **语义**：返回解析后的文件或目录路径对象。

**伪代码**

```text
如果“检查文件或目录路径的文件系统属性”后得到肯定结果，就拒绝继续处理并抛出 `McpRuntimeReportInvalid`，向调用方报告输入或运行失败。
将辅助操作“将文件或目录路径规范化为受控的绝对路径”的结果规范化为受控的绝对路径，并把结果记为 选中的候选项；将辅助操作“将受控扫描根目录规范化为受控的绝对路径”的结果规范化为受控的绝对路径，并把结果记为 该调用返回的结果。
如果选中的候选项等于当前处理结果 或 当前处理结果不属于当前处理结果，就拒绝继续处理并抛出 `McpRuntimeReportInvalid`，向调用方报告输入或运行失败。
返回选中的候选项的当前值。
```

#### `_render_runtime_report`

- **源码**：`app/mcp_operations/repository.py:34`
- **签名**：`def _render_runtime_report(report: McpRuntimeReport) -> str`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收MCP 评测或运行报告，用于把复现过程中的结构化状态、证据或结果转换为可读、可传输或可持久化的表示，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `report` | `McpRuntimeReport` | MCP 评测或运行报告；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
计算初始化顺序集合，并保存为 待输出的文本行。
遍历当前可迭代输入，每次把当前项记为MCP Client 配置档案：
    遍历当前可迭代输入，每次把当前项记为当前处理项，然后把新的处理结果追加或合并到待输出的文本行。
如果发现集合有值或为真，就把新的处理结果追加或合并到待输出的文本行；把新的处理结果追加或合并到待输出的文本行。
把新的处理结果追加或合并到待输出的文本行；调用 `join` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `write_runtime_report`

- **源码**：`app/mcp_operations/repository.py:62`
- **签名**：`def write_runtime_report(root: Path, report: McpRuntimeReport) -> tuple[Path, Path]`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收受控扫描根目录、MCP 评测或运行报告，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终一个经过边界校验的文件或目录路径。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `root` | `Path` | 运行产物或受控工作区的目录路径；用于隔离本次运行生成的文件。 |
| `report` | `McpRuntimeReport` | MCP 评测或运行报告；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`tuple[Path, Path]`
- **语义**：返回解析后的文件或目录路径对象。

**伪代码**

```text
如果辅助操作“调用 `runtime_report_hash` 完成该函数的一项辅助处理”的结果不等于MCP 评测或运行报告的 SHA-256，就拒绝继续处理并抛出 `McpRuntimeReportInvalid`，向调用方报告输入或运行失败。
计算组合或计算已有值，并保存为 根目录；调用 `_inside_root` 完成该函数的一项辅助处理，并把结果记为 JSON 数据的路径；调用 `_inside_root` 完成该函数的一项辅助处理，并把结果记为 当前处理结果的路径；调用 `atomic_write_json` 完成该函数的一项辅助处理。
调用 `atomic_write_text` 完成该函数的一项辅助处理；返回当前构造的顺序或去重集合。
```

#### `load_runtime_report`

- **源码**：`app/mcp_operations/repository.py:77`
- **签名**：`def load_runtime_report(path: Path, root: Path) -> McpRuntimeReport`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收文件或目录路径、受控扫描根目录，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `McpRuntimeReport` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |
| `root` | `Path` | 运行产物或受控工作区的目录路径；用于隔离本次运行生成的文件。 |

**输出**

- **Python 类型**：`McpRuntimeReport`
- **语义**：返回从外部表示解析并校验后的领域值；格式非法时通过异常失败。

**伪代码**

```text
调用 `_inside_root` 完成该函数的一项辅助处理，并把结果记为 选中的候选项。
如果“检查选中的候选项的文件系统属性”后未得到肯定结果，就拒绝继续处理并抛出 `McpRuntimeReportInvalid`，向调用方报告输入或运行失败。
先尝试完成以下处理：
    调用 `model_validate_json` 完成该函数的一项辅助处理，并把结果记为 MCP 评测或运行报告。
如果出现 `(OSError, UnicodeError, ValueError)`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `McpRuntimeReportInvalid`，向调用方报告输入或运行失败。
如果辅助操作“调用 `runtime_report_hash` 完成该函数的一项辅助处理”的结果不等于MCP 评测或运行报告的 SHA-256，就拒绝继续处理并抛出 `McpRuntimeReportInvalid`，向调用方报告输入或运行失败。
返回MCP 评测或运行报告的当前值。
```

#### `write_upgrade_comparison`

- **源码**：`app/mcp_operations/repository.py:98`
- **签名**：`def write_upgrade_comparison(root: Path, comparison: McpUpgradeComparison) -> Path`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收受控扫描根目录、SDK 或 MCP 运行升级比较结果，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终一个经过边界校验的文件或目录路径。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `root` | `Path` | 运行产物或受控工作区的目录路径；用于隔离本次运行生成的文件。 |
| `comparison` | `McpUpgradeComparison` | SDK 或 MCP 运行升级比较结果；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`Path`
- **语义**：返回解析后的文件或目录路径对象。

**伪代码**

```text
如果辅助操作“调用 `upgrade_comparison_hash` 完成该函数的一项辅助处理”的结果不等于SDK 或 MCP 运行升级比较结果的 SHA-256，就拒绝继续处理并抛出 `McpRuntimeReportInvalid`，向调用方报告输入或运行失败。
调用 `_inside_root` 完成该函数的一项辅助处理，并把结果记为 文件或目录路径；调用 `atomic_write_json` 完成该函数的一项辅助处理；返回文件或目录路径的当前值。
```

### `app/mcp_operations/schemas.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `McpRuntimePolicy.validate_deterministic_lists`

- **源码**：`app/mcp_operations/schemas.py:50`
- **签名**：`def validate_deterministic_lists(self) -> McpRuntimePolicy`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `McpRuntimePolicy` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`McpRuntimePolicy`
- **语义**：返回 `McpRuntimePolicy` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
遍历当前可迭代输入，每次把当前项记为多个解包结果：
    如果状态字段集合不等于辅助操作“按稳定规则整理结果顺序”的结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前对象的当前值。
```

#### `McpInvocationSample.validate_result_identity`

- **源码**：`app/mcp_operations/schemas.py:77`
- **签名**：`def validate_result_identity(self) -> McpInvocationSample`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `McpInvocationSample` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`McpInvocationSample`
- **语义**：返回 `McpInvocationSample` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果当前状态等于'succeeded'：
    如果输出结果的 SHA-256为空 或 错误不为空，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
否则：
    如果输出结果的 SHA-256不为空 或 错误为空，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前对象的当前值。
```

### `app/mcp_operations/upgrade.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `utc_now`

- **源码**：`app/mcp_operations/upgrade.py:16`
- **签名**：`def utc_now() -> str`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `isoformat` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `_summary_map`

- **源码**：`app/mcp_operations/upgrade.py:20`
- **签名**：`def _summary_map(report: McpRuntimeReport) -> dict[tuple[str, str], McpOperationSummary]`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收MCP 评测或运行报告，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `report` | `McpRuntimeReport` | MCP 评测或运行报告；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`dict[tuple[str, str], McpOperationSummary]`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
返回当前计算得到的结果。
```

#### `compare_runtime_reports`

- **源码**：`app/mcp_operations/upgrade.py:30`
- **签名**：`def compare_runtime_reports(before: McpRuntimeReport, after: McpRuntimeReport, policy: McpRuntimePolicy, accepted_surface_sha256: str) -> McpUpgradeComparison`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收升级前运行报告、升级后运行报告、安全策略、已接受 MCP 能力表面的 SHA-256，用于发现、观测或评估 MCP 的公开 Tool/Resource/Prompt 契约，比较协议、Schema、延迟和失败结果，并为论文复现系统保留可审核的基线或运行报告，最终标注为 `McpUpgradeComparison` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `before` | `McpRuntimeReport` | 升级前运行报告；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `after` | `McpRuntimeReport` | 分页、文本切片或事件序列位置；用于确定本次读取的起止边界。 |
| `policy` | `McpRuntimePolicy` | 安全策略；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `accepted_surface_sha256` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |

**输出**

- **Python 类型**：`McpUpgradeComparison`
- **语义**：返回 `McpUpgradeComparison` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
将 诊断发现集合 初始化为空列表，用来收集后续结果。
如果MCP 评测或运行模式不等于'release' 或 MCP 评测或运行模式不等于'release'，就把新的处理结果追加或合并到诊断发现集合。
如果安全策略的 SHA-256不等于安全策略的 SHA-256，就把新的处理结果追加或合并到诊断发现集合。
如果安全策略的 SHA-256不等于安全策略的 SHA-256，就把新的处理结果追加或合并到诊断发现集合。
如果已审核的 MCP 能力基线的 SHA-256不等于已审核的 MCP 能力基线的 SHA-256，就把新的处理结果追加或合并到诊断发现集合。
如果“当前处理结果有值或为真”不成立，就把新的处理结果追加或合并到诊断发现集合。
如果“当前处理结果有值或为真”不成立，就把新的处理结果追加或合并到诊断发现集合。
遍历当前可迭代输入，每次把当前项记为多个解包结果：
    如果当前可迭代输入中存在满足“MCP 能力表面的 SHA-256不等于已接受 MCP 能力表面的 SHA-256”的项，就把新的处理结果追加或合并到诊断发现集合。
调用 `_summary_map` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `_summary_map` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
如果辅助操作“构造临时集合、映射或轻量领域对象”的结果不等于辅助操作“构造临时集合、映射或轻量领域对象”的结果，就把新的处理结果追加或合并到诊断发现集合。
将 当前处理结果 初始化为空列表，用来收集后续结果。
遍历辅助操作产生的可迭代结果（按稳定规则整理结果顺序），每次把当前项记为映射键或对象字段名：
    读取当前处理结果中的对应字段，并保存为 后续步骤使用的结果；读取当前处理结果中的对应字段，并保存为 后续步骤使用的结果；计算组合或计算已有值，并保存为 当前处理结果；计算组合或计算已有值，并保存为 仓库相对路径。
    将 操作发现集合集合 初始化为空列表，用来收集后续结果。
    如果当前处理结果大于当前处理结果 且 仓库相对路径大于相对，就把新的处理结果追加或合并到操作发现集合集合。
    如果“当前处理结果有值或为真”不成立，就把新的处理结果追加或合并到操作发现集合集合。
    把新的处理结果追加或合并到当前处理结果。
如果由当前处理结果组成的集合或迭代器中存在满足““当前处理结果有值或为真”不成立”的项，就把新的处理结果追加或合并到诊断发现集合。
计算按字段初始化键值映射，并保存为 结构化请求载荷；构造 `McpUpgradeComparison` 结构化领域对象，并把结果记为 SDK 或 MCP 运行升级比较结果；复制、序列化或校验结构化领域对象，并返回处理结果。
```

### `app/model_routing/catalog.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `LoadedModelCatalog.profile`

- **源码**：`app/model_routing/catalog.py:28`
- **签名**：`def profile(self, profile_id: str) -> ModelProfile`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收MCP Client 配置档案 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ModelProfile` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `profile_id` | `str` | MCP Client 配置档案 ID；用于区分连接地址、协议版本和能力基线。 |

**输出**

- **Python 类型**：`ModelProfile`
- **语义**：返回 `ModelProfile` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
先尝试完成以下处理：
    返回当前处理结果的 ID中的对应字段的当前值。
如果出现 `KeyError`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `ModelCatalogError`，向调用方报告输入或运行失败。
```

#### `LoadedModelCatalog.route`

- **源码**：`app/model_routing/catalog.py:36`
- **签名**：`def route(self, task_kind: ModelTaskKind) -> ModelTaskRoute`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收类别，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ModelTaskRoute` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `task_kind` | `ModelTaskKind` | 名为 `task_kind` 的 `ModelTaskKind` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`ModelTaskRoute`
- **语义**：返回 `ModelTaskRoute` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
先尝试完成以下处理：
    返回当前处理结果中的对应字段的当前值。
如果出现 `KeyError`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `ModelCatalogError`，向调用方报告输入或运行失败。
```

#### `_safe_policy_file`

- **源码**：`app/model_routing/catalog.py:45`
- **签名**：`def _safe_policy_file(path: Path, allowed_root: Path) -> Path`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收文件或目录路径、根目录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个经过边界校验的文件或目录路径。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |
| `allowed_root` | `Path` | 已经解析的文件或目录路径对象；后续操作仍需遵守仓库/工作区边界。 |

**输出**

- **Python 类型**：`Path`
- **语义**：返回解析后的文件或目录路径对象。

**伪代码**

```text
将辅助操作“将根目录规范化为受控的绝对路径”的结果规范化为受控的绝对路径，并把结果记为 受控扫描根目录；将文件或目录路径规范化为受控的绝对路径，并把结果记为 待审核的 MCP 能力候选。
如果“检查待审核的 MCP 能力候选的文件系统属性”后得到肯定结果，就拒绝继续处理并抛出 `ModelCatalogError`，向调用方报告输入或运行失败。
将待审核的 MCP 能力候选规范化为受控的绝对路径，并把结果记为 解析后的值。
如果解析后的值等于受控扫描根目录 或 受控扫描根目录不属于当前处理结果，就拒绝继续处理并抛出 `ModelCatalogError`，向调用方报告输入或运行失败。
如果“检查解析后的值的文件系统属性”后未得到肯定结果，就拒绝继续处理并抛出 `ModelCatalogError`，向调用方报告输入或运行失败。
如果前一步操作返回对象的当前处理结果大于最大安全策略的字节内容，就拒绝继续处理并抛出 `ModelCatalogError`，向调用方报告输入或运行失败。
返回解析后的值的当前值。
```

#### `_validate_cross_references_then_resolve`

- **源码**：`app/model_routing/catalog.py:71`
- **签名**：`def _validate_cross_references_then_resolve(document: ModelRoutingDocument, substitutions: dict[str, str]) -> _ResolvedCatalog`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，先校验交叉引用，再替换占位符。该函数接收论文解析文档、当前处理结果，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `_ResolvedCatalog` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `document` | `ModelRoutingDocument` | 论文解析文档；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `substitutions` | `dict[str, str]` | 名为 `substitutions` 的键值映射；键和值分别承载的业务字段由读取/写入分支确定。 |

**输出**

- **Python 类型**：`_ResolvedCatalog`
- **语义**：返回 `_ResolvedCatalog` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `_validate_cross_references` 校验当前输入或状态，并把结果记为 多个解包结果；调用 `_resolve_model_placeholders` 解析、规范化或转换当前输入，并把结果记为 解析后的值；遍历并筛选输入，将整理后的结果保存为 当前处理结果的 ID；调用 `_ResolvedCatalog` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `_resolve_model_placeholders`

- **源码**：`app/model_routing/catalog.py:98`
- **签名**：`def _resolve_model_placeholders(document: ModelRoutingDocument, substitutions: dict[str, str]) -> ModelRoutingDocument`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收论文解析文档、当前处理结果，用于把论文中的方法、模块或实验意图与仓库中的可验证对象建立稳定关联，并保留匹配依据，最终标注为 `ModelRoutingDocument` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `document` | `ModelRoutingDocument` | 论文解析文档；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `substitutions` | `dict[str, str]` | 名为 `substitutions` 的键值映射；键和值分别承载的业务字段由读取/写入分支确定。 |

**输出**

- **Python 类型**：`ModelRoutingDocument`
- **语义**：返回 `ModelRoutingDocument` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
将 MCP Client 配置档案集合 初始化为空列表，用来收集后续结果。
遍历当前可迭代输入，每次把当前项记为MCP Client 配置档案：
    读取模型标识或模型配置的名称，并保存为 模型标识或模型配置的名称。
    如果“检查模型标识或模型配置的名称是否满足文本匹配条件”后得到肯定结果：
        从当前处理结果读取所需的状态或领域记录，并把结果记为 该调用返回的结果。
        如果当前处理结果为空 或 “对当前处理结果中的文本执行规范化或拆分”后未得到肯定结果，就拒绝继续处理并抛出 `ModelCatalogError`，向调用方报告输入或运行失败。
        去除当前处理结果的首尾空白，并把规范化后的文本记为 模型标识或模型配置的名称。
    把新的处理结果追加或合并到MCP Client 配置档案集合。
复制、序列化或校验结构化领域对象，并返回处理结果。
```

#### `_validate_cross_references`

- **源码**：`app/model_routing/catalog.py:119`
- **签名**：`def _validate_cross_references(document: ModelRoutingDocument) -> tuple[dict[str, ModelProfile], dict[ModelTaskKind, ModelTaskRoute]]`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收论文解析文档，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `document` | `ModelRoutingDocument` | 论文解析文档；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`tuple[dict[str, ModelProfile], dict[ModelTaskKind, ModelTaskRoute]]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
将 当前处理结果的 ID 初始化为空映射，用来收集后续结果。
遍历当前可迭代输入，每次把当前项记为MCP Client 配置档案：
    如果MCP Client 配置档案 ID属于当前处理结果的 ID，就拒绝继续处理并抛出 `ModelCatalogError`，向调用方报告输入或运行失败。
    读取MCP Client 配置档案，并保存为 当前处理结果的 ID中的对应字段。
将 当前处理结果 初始化为空映射，用来收集后续结果。
遍历当前可迭代输入，每次把当前项记为流程路由结果：
    如果类别属于当前处理结果，就拒绝继续处理并抛出 `ModelCatalogError`，向调用方报告输入或运行失败。
    读取流程路由结果，并保存为 当前处理结果中的对应字段；计算初始化顺序集合，并保存为 当前处理结果。
    遍历由当前处理结果组成的集合或迭代器，每次把当前项记为MCP Client 配置档案 ID：
        从当前处理结果的 ID读取所需的状态或领域记录，并把结果记为 MCP Client 配置档案。
        如果MCP Client 配置档案为空，就拒绝继续处理并抛出 `ModelCatalogError`，向调用方报告输入或运行失败。
        如果类别不等于类别，就拒绝继续处理并抛出 `ModelCatalogError`，向调用方报告输入或运行失败。
        如果最大实际输出 token 数大于最大实际输出 token 数，就拒绝继续处理并抛出 `ModelCatalogError`，向调用方报告输入或运行失败。
返回当前构造的顺序或去重集合。
```

#### `load_model_catalog`

- **源码**：`app/model_routing/catalog.py:163`
- **签名**：`def load_model_catalog(path: Path, allowed_root: Path, substitutions: dict[str, str]) -> LoadedModelCatalog`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收文件或目录路径、根目录、当前处理结果，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `LoadedModelCatalog` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |
| `allowed_root` | `Path` | 已经解析的文件或目录路径对象；后续操作仍需遵守仓库/工作区边界。 |
| `substitutions` | `dict[str, str]` | 名为 `substitutions` 的键值映射；键和值分别承载的业务字段由读取/写入分支确定。 |

**输出**

- **Python 类型**：`LoadedModelCatalog`
- **语义**：返回从外部表示解析并校验后的领域值；格式非法时通过异常失败。

**伪代码**

```text
调用 `_safe_policy_file` 完成该函数的一项辅助处理，并把结果记为 解析后的值。
先尝试完成以下处理：
    读取解析后的值中的文件内容，并把结果记为 原始内容；调用 `model_validate_json` 完成该函数的一项辅助处理，并把结果记为 论文解析文档。
如果出现 `(OSError, UnicodeError, ValidationError)`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `ModelCatalogError`，向调用方报告输入或运行失败。
调用 `_validate_cross_references_then_resolve` 校验当前输入或状态，并把结果记为 论文解析文档；构造并返回 `LoadedModelCatalog` 结构化领域对象。
```

### `app/model_routing/embedding.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `RoutedEmbeddingBackend.__init__`

- **源码**：`app/model_routing/embedding.py:14`
- **签名**：`def __init__(self: 未显式标注, gateway: ModelGateway, model_name: str, endpoint_identity: str, job_id: str | None, run_id: str | None, node_name: str) -> None`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收外部服务网关、模型标识或模型配置的名称、身份、复现任务 ID等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `gateway` | `ModelGateway` | 外部服务网关；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `model_name` | `str` | 名为 `model_name` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `endpoint_identity` | `str` | 名为 `endpoint_identity` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `job_id` | `str | None` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `run_id` | `str | None` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `node_name` | `str` | 名为 `node_name` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 外部服务网关、模型标识或模型配置的名称、复现任务 ID、本次复现运行 ID、当前流程节点的名称 分别保存到同名实例字段；读取前一步操作返回对象中的对应字段，并保存为 MCP 服务端点地址的 Hash；构造 `EmbeddingBackendIdentity` 结构化领域对象，并把结果记为 对象身份。
```

#### `RoutedEmbeddingBackend.identity`

- **源码**：`app/model_routing/embedding.py:38`
- **签名**：`def identity(self) -> EmbeddingBackendIdentity`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `EmbeddingBackendIdentity` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`EmbeddingBackendIdentity`
- **语义**：返回 `EmbeddingBackendIdentity` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
返回对象身份的当前值。
```

#### `RoutedEmbeddingBackend._backend_for_profile`

- **源码**：`app/model_routing/embedding.py:41`
- **签名**：`def _backend_for_profile(self, profile) -> EmbeddingBackend`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收MCP Client 配置档案，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `EmbeddingBackend` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `profile` | `未显式标注` | 运行/执行环境配置或 profile 标识；描述能力和限制，不是一次执行的结果。 |

**输出**

- **Python 类型**：`EmbeddingBackend`
- **语义**：返回 `EmbeddingBackend` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果模型标识或模型配置的名称不等于模型标识或模型配置的名称，就拒绝继续处理并抛出 `ModelProviderBindingError`，向调用方报告输入或运行失败。
调用 `build_embedding` 组装当前阶段需要的领域对象，并返回处理结果。
```

#### `RoutedEmbeddingBackend.embed_documents`

- **源码**：`app/model_routing/embedding.py:48`
- **签名**：`def embed_documents(self: 未显式标注, texts: list[str]) -> list[list[float]]`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收待处理文本集合，用于围绕论文方法语义检索、切分和排序代码证据，为后续方法映射与实验规划提供候选结果，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `texts` | `list[str]` | 待处理文本集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`list[list[float]]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
如果待处理文本集合为空或为假，就返回当前构造的顺序或去重集合。
调用 `invoke_embedding` 完成该函数的一项辅助处理，并把结果记为 工具调用记录；返回当前字段值的当前值。
```

#### `RoutedEmbeddingBackend.embed_query`

- **源码**：`app/model_routing/embedding.py:66`
- **签名**：`def embed_query(self, text: str) -> list[float]`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收待处理文本，用于围绕论文方法语义检索、切分和排序代码证据，为后续方法映射与实验规划提供候选结果，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `text` | `str` | 用户目标、检索问题、反馈或待处理文本；会作为当前阶段的业务语境输入，并可能受到长度/脱敏约束。 |

**输出**

- **Python 类型**：`list[float]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
调用 `invoke_embedding` 完成该函数的一项辅助处理，并把结果记为 工具调用记录；返回当前字段值的当前值。
```

### `app/model_routing/errors.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `ModelBudgetExceeded.__init__`

- **源码**：`app/model_routing/errors.py:19`
- **签名**：`def __init__(self: 未显式标注, scope: str, limit: int, used_or_reserved: int, requested: int) -> None`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收查询或授权作用域、结果数量上限、已使用或已预留的资源量、当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `scope` | `str` | 查询或授权作用域；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。 |
| `used_or_reserved` | `int` | 已使用或已预留的资源量；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `requested` | `int` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 查询或授权作用域、结果数量上限、已使用或已预留的资源量、当前处理结果 分别保存到同名实例字段；调用 `__init__` 完成该函数的一项辅助处理。
```

### `app/model_routing/evaluation.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `evaluate_routing_cases`

- **源码**：`app/model_routing/evaluation.py:14`
- **签名**：`def evaluate_routing_cases(router: ModelRouter, cases: list[ModelRoutingEvaluationCase], suite_version: str, mode: ModelRoutingMode) -> ModelRoutingEvaluationReport`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收API 路由器、评测用例集合、版本、MCP 评测或运行模式，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ModelRoutingEvaluationReport` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `router` | `ModelRouter` | API 路由器；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `cases` | `list[ModelRoutingEvaluationCase]` | 评测用例集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `suite_version` | `str` | 名为 `suite_version` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `mode` | `ModelRoutingMode` | MCP 评测或运行模式；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 'active' |

**输出**

- **Python 类型**：`ModelRoutingEvaluationReport`
- **语义**：返回 `ModelRoutingEvaluationReport` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
将 当前处理结果 初始化为空列表，用来收集后续结果。
遍历由评测用例集合组成的集合或迭代器，每次把当前项记为评测用例：
    先尝试完成以下处理：
        调用 `route` 完成该函数的一项辅助处理，并把结果记为 多个解包结果。
        如果配置的 ID不等于期望配置的 ID，就把评测用例的 ID追加或合并到当前处理结果；跳过本轮剩余处理，直接进入下一轮。
        如果配置的 ID属于配置集合，就把评测用例的 ID追加或合并到当前处理结果。
    如果出现 `Exception`：
        把评测用例的 ID追加或合并到当前处理结果。
计算数量、边界或类型判断结果，并把结果记为 该调用返回的结果；计算组合或计算已有值，并保存为 当前处理结果的数量；构造并返回 `ModelRoutingEvaluationReport` 结构化领域对象。
```

#### `build_promotion_proposal`

- **源码**：`app/model_routing/evaluation.py:49`
- **签名**：`def build_promotion_proposal(task_kind: ModelTaskKind, baseline_profile_id: str, challenger_profile_id: str, baseline_policy_sha256: str, route_report: ModelRoutingEvaluationReport, downstream_quality_gate_passed: bool, estimated_saving_percent: float | None) -> ModelProfilePromotionProposal`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，Route 命中 + 下游 Golden 同时通过，仍只生成待人工评审 Proposal。该函数接收类别、配置的 ID、配置的 ID、策略的 SHA-256等输入，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `ModelProfilePromotionProposal` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `task_kind` | `ModelTaskKind` | 名为 `task_kind` 的 `ModelTaskKind` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `baseline_profile_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `challenger_profile_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `baseline_policy_sha256` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |
| `route_report` | `ModelRoutingEvaluationReport` | 名为 `route_report` 的 `ModelRoutingEvaluationReport` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `downstream_quality_gate_passed` | `bool` | 布尔条件或能力开关，用于控制流程分支。 |
| `estimated_saving_percent` | `float | None` | 名为 `estimated_saving_percent` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`ModelProfilePromotionProposal`
- **语义**：返回 `ModelProfilePromotionProposal` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
计算计算当前表达式的结果，并保存为 当前处理结果；调用 `sha256_value` 计算内容身份、分数或派生结果，并把结果记为 MCP 评测或运行报告的 Hash；计算按字段初始化键值映射，并保存为 当前处理结果；计算根据字段和固定文本生成格式化文本，并保存为 修复或重跑提案的 ID。
构造并返回 `ModelProfilePromotionProposal` 结构化领域对象。
```

### `app/model_routing/factory.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `build_model_gateway`

- **源码**：`app/model_routing/factory.py:16`
- **签名**：`def build_model_gateway() -> ModelGateway`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `ModelGateway` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`ModelGateway`
- **语义**：返回 `ModelGateway` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `load_model_catalog` 读取或查询当前阶段需要的数据，并把结果记为 模型、工具或 Artifact 目录；构造 `SqliteModelLedger` 结构化领域对象，并把结果记为 幂等、租约或审计账本；加载这一步需要的外部依赖；构造 `TrustedProviderFactory` 结构化领域对象，并把结果记为 模型服务商配置集合。
构造并返回 `ModelGateway` 结构化领域对象。
```

#### `_embedding_model_name`

- **源码**：`app/model_routing/factory.py:51`
- **签名**：`def _embedding_model_name(gateway: ModelGateway) -> str`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，第一版要求两个 Embedding Route 的所有 Profile 使用同一模型。该函数接收外部服务网关，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `gateway` | `ModelGateway` | 外部服务网关；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
读取模型、工具或 Artifact 目录，并保存为 模型、工具或 Artifact 目录；将 当前处理结果 初始化为空去重集合，用来收集后续结果。
遍历当前可迭代输入，每次把当前项记为类别：
    调用 `route` 完成该函数的一项辅助处理，并把结果记为 流程路由结果；计算初始化去重集合，并保存为 配置集合。
    遍历由配置集合组成的集合或迭代器，每次把当前项记为MCP Client 配置档案 ID：
        调用 `profile` 完成该函数的一项辅助处理，并把结果记为 MCP Client 配置档案。
        如果功能是否启用的开关有值或为真，就把模型标识或模型配置的名称追加或合并到当前处理结果。
如果当前处理结果 的长度不等于1，就拒绝继续处理并抛出 `ModelCatalogError`，向调用方报告输入或运行失败。
调用 `next` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `build_routed_embedding_backend`

- **源码**：`app/model_routing/factory.py:76`
- **签名**：`def build_routed_embedding_backend(job_id: str | None, run_id: str | None, node_name: str) -> RoutedEmbeddingBackend`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收复现任务 ID、本次复现运行 ID、当前流程节点的名称，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `RoutedEmbeddingBackend` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `job_id` | `str | None` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。；默认 空值 |
| `run_id` | `str | None` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。；默认 空值 |
| `node_name` | `str` | 名为 `node_name` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。；默认 'code_search' |

**输出**

- **Python 类型**：`RoutedEmbeddingBackend`
- **语义**：返回 `RoutedEmbeddingBackend` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `build_model_gateway` 组装当前阶段需要的领域对象，并把结果记为 外部服务网关；构造并返回 `RoutedEmbeddingBackend` 结构化领域对象。
```

### `app/model_routing/gateway.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `RoutedStructuredInvocation.value`

- **源码**：`app/model_routing/gateway.py:68`
- **签名**：`def value(self) -> SchemaT | None`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `SchemaT | None` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`SchemaT | None`
- **语义**：返回 `SchemaT | None` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
返回当前字段值的当前值。
```

#### `RoutedStructuredInvocation.attempts`

- **源码**：`app/model_routing/gateway.py:72`
- **签名**：`def attempts(self) -> list[Any]`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`list[Any]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
返回模型尝试记录集合的当前值。
```

#### `RoutedStructuredInvocation.method`

- **源码**：`app/model_routing/gateway.py:76`
- **签名**：`def method(self) -> str`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
返回论文方法或 HTTP 方法的当前值。
```

#### `RoutedStructuredInvocation.strict`

- **源码**：`app/model_routing/gateway.py:80`
- **签名**：`def strict(self) -> bool | None`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `bool | None` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`bool | None`
- **语义**：返回 `bool | None` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
返回是否启用严格校验的开关的当前值。
```

#### `RoutedStructuredInvocation.max_retries`

- **源码**：`app/model_routing/gateway.py:84`
- **签名**：`def max_retries(self) -> int`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终数量、序号、字节数或版本等整数结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`int`
- **语义**：返回整数计数、序号、字节数或退出码；具体含义由函数名决定。

**伪代码**

```text
返回重试次数上限的当前值。
```

#### `RoutedStructuredInvocation.provider_max_retries`

- **源码**：`app/model_routing/gateway.py:88`
- **签名**：`def provider_max_retries(self) -> int`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终数量、序号、字节数或版本等整数结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`int`
- **语义**：返回整数计数、序号、字节数或退出码；具体含义由函数名决定。

**伪代码**

```text
返回模型服务商集合的当前值。
```

#### `RoutedStructuredInvocation.provider_retry_base_seconds`

- **源码**：`app/model_routing/gateway.py:92`
- **签名**：`def provider_retry_base_seconds(self) -> float`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终用于排序或质量评估的分数、比例或相似度。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`float`
- **语义**：返回浮点分数、时间或比例值。

**伪代码**

```text
返回模型服务商集合的当前值。
```

#### `RoutedStructuredInvocation.succeeded`

- **源码**：`app/model_routing/gateway.py:96`
- **签名**：`def succeeded(self) -> bool`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
返回前一步处理得到的结果。
```

#### `_structured_capability`

- **源码**：`app/model_routing/gateway.py:116`
- **签名**：`def _structured_capability(method: str) -> ModelCapability`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收论文方法或 HTTP 方法，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ModelCapability` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `method` | `str` | 论文方法或 HTTP 方法；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`ModelCapability`
- **语义**：返回 `ModelCapability` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
计算按字段初始化键值映射，并保存为 论文-代码映射。
先尝试完成以下处理：
    返回论文-代码映射中的对应字段的当前值。
如果出现 `KeyError`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
```

#### `_safe_error_code`

- **源码**：`app/model_routing/gateway.py:128`
- **签名**：`def _safe_error_code(prefix: str, error: BaseException) -> str`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收目录树缩进前缀、错误信息，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `prefix` | `str` | 目录树展示用的缩进前缀；只影响输出排版，不改变仓库路径。 |
| `error` | `BaseException` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
去除辅助操作“调用 `join` 完成该函数的一项辅助处理”的结果的首尾空白，并把规范化后的文本记为 规范化后的文本；返回当前输入内容中的对应字段的当前值。
```

#### `_is_transient_provider_error`

- **源码**：`app/model_routing/gateway.py:137`
- **签名**：`def _is_transient_provider_error(error: BaseException) -> bool`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收错误信息，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `error` | `BaseException` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
对当前输入内容中的文本执行规范化或拆分，并把结果记为 待处理的论文或源码材料；检查当前可迭代输入中是否存在满足“测试或状态标记属于待处理的论文或源码材料”的项，并返回处理结果。
```

#### `_message_for_hash`

- **源码**：`app/model_routing/gateway.py:157`
- **签名**：`def _message_for_hash(message: BaseMessage) -> dict[str, Any]`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收面向用户或日志的提示信息，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `message` | `BaseMessage` | 对话消息记录或消息文本；角色、顺序和内容 Hash 可能参与证据校验。 |

**输出**

- **Python 类型**：`dict[str, Any]`
- **语义**：返回内容身份摘要，通常为 SHA-256 十六进制字符串。

**伪代码**

```text
计算按字段初始化键值映射，并保存为 结构化请求载荷；调用 `getattr` 完成该函数的一项辅助处理，并把结果记为 工具的 ID。
如果工具的 ID不为空，就读取工具的 ID，并保存为 结构化请求载荷中的对应字段。
调用 `getattr` 完成该函数的一项辅助处理，并把结果记为 工具集合。
如果工具集合有值或为真，就读取工具集合，并保存为 结构化请求载荷中的对应字段。
返回结构化请求载荷的当前值。
```

#### `_tool_prompt_material`

- **源码**：`app/model_routing/gateway.py:171`
- **签名**：`def _tool_prompt_material(messages: list[BaseMessage], tools: list[dict[str, Any]]) -> str`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收对话或日志消息集合、受控工具定义集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `messages` | `list[BaseMessage]` | 对话或日志消息集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `tools` | `list[dict[str, Any]]` | 受控工具定义集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `canonical_json` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `ModelGateway.__init__`

- **源码**：`app/model_routing/gateway.py:185`
- **签名**：`def __init__(self: 未显式标注, mode: ModelRoutingMode, router: ModelRouter, ledger: SqliteModelLedger, providers: ProviderFactoryPort, structured_method: str, structured_strict: bool, raw_preview_chars: int, provider_retry_base_seconds: float, structured_invoker: StructuredInvoker) -> None`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收MCP 评测或运行模式、API 路由器、幂等、租约或审计账本、模型服务商配置集合等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `mode` | `ModelRoutingMode` | MCP 评测或运行模式；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `router` | `ModelRouter` | API 路由器；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `ledger` | `SqliteModelLedger` | 幂等、租约或审计账本；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `providers` | `ProviderFactoryPort` | 模型服务商配置集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `structured_method` | `str` | 名为 `structured_method` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `structured_strict` | `bool` | 布尔条件或能力开关，用于控制流程分支。 |
| `raw_preview_chars` | `int` | 名为 `raw_preview_chars` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `provider_retry_base_seconds` | `float` | 名为 `provider_retry_base_seconds` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `structured_invoker` | `StructuredInvoker` | 可调用依赖；由当前函数在受控位置调用。；默认 invoke_structured_with_retry |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 MCP 评测或运行模式、API 路由器、幂等、租约或审计账本、模型服务商配置集合、当前处理结果、当前处理结果、字符数、模型服务商集合、当前处理结果 分别保存到同名实例字段。
```

#### `ModelGateway._reservation`

- **源码**：`app/model_routing/gateway.py:208`
- **签名**：`def _reservation(self: 未显式标注, request: ModelRouteRequest, decision: ModelRouteDecision, profile: ModelProfile, invocation_id: str) -> ModelReservationRequest`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收业务请求、人工决策结果、MCP Client 配置档案、工具调用记录的 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ModelReservationRequest` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `request` | `ModelRouteRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `decision` | `ModelRouteDecision` | 人工审批或决策记录；必须与目标动作 Hash、版本和允许操作一致。 |
| `profile` | `ModelProfile` | 运行/执行环境配置或 profile 标识；描述能力和限制，不是一次执行的结果。 |
| `invocation_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`ModelReservationRequest`
- **语义**：返回 `ModelReservationRequest` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
读取最大尝试记录集合集合，并保存为 尝试次数上限；计算组合或计算已有值，并保存为 当前处理结果；计算组合或计算已有值，并保存为 当前处理结果；调用 `calculate_cost_micro_usd` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
计算组合或计算已有值，并保存为 当前处理结果；构造并返回 `ModelReservationRequest` 结构化领域对象。
```

#### `ModelGateway._build_structured_request`

- **源码**：`app/model_routing/gateway.py:250`
- **签名**：`def _build_structured_request(self: 未显式标注, task_kind: ModelTaskKind, schema: type[BaseModel], prompt: str, node_name: str, job_id: str | None, run_id: str | None, quality_tier: ModelQualityTier, requested_max_output_tokens: int | None) -> ModelRouteRequest`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收类别、输入输出 Schema 契约、发给模型的结构化提示、当前流程节点的名称等输入，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `ModelRouteRequest` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `task_kind` | `ModelTaskKind` | 名为 `task_kind` 的 `ModelTaskKind` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `schema` | `type[BaseModel]` | 结构化输出 Schema 或其名称；用于约束解析结果的字段和类型。 |
| `prompt` | `str` | 用户目标、检索问题、反馈或待处理文本；会作为当前阶段的业务语境输入，并可能受到长度/脱敏约束。 |
| `node_name` | `str` | 名为 `node_name` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `job_id` | `str | None` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `run_id` | `str | None` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `quality_tier` | `ModelQualityTier` | 模型质量档位；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `requested_max_output_tokens` | `int | None` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`ModelRouteRequest`
- **语义**：返回 `ModelRouteRequest` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `route` 完成该函数的一项辅助处理，并把结果记为 流程路由结果；计算根据条件从两个候选结果中选择一个，并保存为 最大输出结果；调用 `canonical_json` 完成该函数的一项辅助处理，并把结果记为 输入输出 Schema 契约的文本；计算组合或计算已有值，并保存为 当前处理结果。
构造并返回 `ModelRouteRequest` 结构化领域对象。
```

#### `ModelGateway.preview_structured`

- **源码**：`app/model_routing/gateway.py:295`
- **签名**：`def preview_structured(self: 未显式标注, task_kind: ModelTaskKind, schema: type[BaseModel], prompt: str, node_name: str, job_id: str | None, run_id: str | None, quality_tier: ModelQualityTier, requested_max_output_tokens: int | None) -> ModelRouteDecision`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，只做确定性路由，不预留预算、不解析 Secret、不调用 Provider。该函数接收类别、输入输出 Schema 契约、发给模型的结构化提示、当前流程节点的名称等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ModelRouteDecision` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `task_kind` | `ModelTaskKind` | 名为 `task_kind` 的 `ModelTaskKind` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `schema` | `type[BaseModel]` | 结构化输出 Schema 或其名称；用于约束解析结果的字段和类型。 |
| `prompt` | `str` | 用户目标、检索问题、反馈或待处理文本；会作为当前阶段的业务语境输入，并可能受到长度/脱敏约束。 |
| `node_name` | `str` | 名为 `node_name` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `job_id` | `str | None` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。；默认 空值 |
| `run_id` | `str | None` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。；默认 空值 |
| `quality_tier` | `ModelQualityTier` | 模型质量档位；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 'balanced' |
| `requested_max_output_tokens` | `int | None` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。；默认 空值 |

**输出**

- **Python 类型**：`ModelRouteDecision`
- **语义**：返回 `ModelRouteDecision` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `_build_structured_request` 组装当前阶段需要的领域对象，并把结果记为 业务请求；调用 `route` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；返回人工决策结果的当前值。
```

#### `ModelGateway.invoke_structured`

- **源码**：`app/model_routing/gateway.py:322`
- **签名**：`def invoke_structured(self: 未显式标注, task_kind: ModelTaskKind, schema: type[SchemaT], prompt: str, node_name: str, job_id: str | None, run_id: str | None, quality_tier: ModelQualityTier, requested_max_output_tokens: int | None, expected_decision_sha256: str | None) -> RoutedStructuredInvocation[SchemaT]`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收类别、输入输出 Schema 契约、发给模型的结构化提示、当前流程节点的名称等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `RoutedStructuredInvocation[SchemaT]` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `task_kind` | `ModelTaskKind` | 名为 `task_kind` 的 `ModelTaskKind` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `schema` | `type[SchemaT]` | 结构化输出 Schema 或其名称；用于约束解析结果的字段和类型。 |
| `prompt` | `str` | 用户目标、检索问题、反馈或待处理文本；会作为当前阶段的业务语境输入，并可能受到长度/脱敏约束。 |
| `node_name` | `str` | 名为 `node_name` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `job_id` | `str | None` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。；默认 空值 |
| `run_id` | `str | None` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。；默认 空值 |
| `quality_tier` | `ModelQualityTier` | 模型质量档位；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 'balanced' |
| `requested_max_output_tokens` | `int | None` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。；默认 空值 |
| `expected_decision_sha256` | `str | None` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。；默认 空值 |

**输出**

- **Python 类型**：`RoutedStructuredInvocation[SchemaT]`
- **语义**：返回 `RoutedStructuredInvocation[SchemaT]` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `route` 完成该函数的一项辅助处理，并把结果记为 流程路由结果；调用 `_build_structured_request` 组装当前阶段需要的领域对象，并把结果记为 业务请求；读取调用方要求的最大输出 token 数，并保存为 最大输出结果；调用 `route` 完成该函数的一项辅助处理，并把结果记为 多个解包结果。
如果期望的 SHA-256不为空 且 人工决策结果的 SHA-256不等于期望的 SHA-256，就拒绝继续处理并抛出 `ModelRouteUnavailable`，向调用方报告输入或运行失败。
计算根据字段和固定文本生成格式化文本，并保存为 工具调用记录的 ID；调用 `_reservation` 完成该函数的一项辅助处理，并把结果记为 资源预留记录；计算使用固定配置或常量值，并保存为 领域记录。
如果MCP 评测或运行模式不等于'off'，就调用 `reserve` 完成该函数的一项辅助处理，并把结果记为 领域记录。
调用 `monotonic` 完成该函数的一项辅助处理，并把结果记为 运行是否已经启动的判断。
先尝试完成以下处理：
    调用 `build_chat` 组装当前阶段需要的领域对象，并把结果记为 语言模型。
如果出现 `Exception`并把异常保存为捕获的异常对象：
    如果MCP 评测或运行模式不等于'off'，就构造 `ModelUsage` 结构化领域对象，并把结果记为 模型或运行资源用量；调用 `settle` 完成该函数的一项辅助处理。
    重新抛出当前异常，保持原始失败信息。
先尝试完成以下处理：
    调用 `structured_invoker` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果。
如果出现 `Exception`并把异常保存为捕获的异常对象：
    如果MCP 评测或运行模式不等于'off'，就构造 `ModelUsage` 结构化领域对象，并把结果记为 该调用返回的结果；调用 `settle` 完成该函数的一项辅助处理，并把结果记为 领域记录。
    重新抛出当前异常，保持原始失败信息。
如果MCP 评测或运行模式不等于'off'，就调用 `usage_from_structured_attempts` 完成该函数的一项辅助处理，并把结果记为 模型或运行资源用量；计算根据条件从两个候选结果中选择一个，并保存为 当前状态；计算根据条件从两个候选结果中选择一个，并保存为 错误；调用 `settle` 完成该函数的一项辅助处理，并把结果记为 领域记录。
构造并返回 `RoutedStructuredInvocation` 结构化领域对象。
```

#### `ModelGateway._build_tool_request`

- **源码**：`app/model_routing/gateway.py:464`
- **签名**：`def _build_tool_request(self: 未显式标注, messages: list[BaseMessage], tools: list[dict[str, Any]], node_name: str, job_id: str, quality_tier: ModelQualityTier, requested_max_output_tokens: int) -> ModelRouteRequest`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收对话或日志消息集合、受控工具定义集合、当前流程节点的名称、复现任务 ID等输入，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `ModelRouteRequest` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `messages` | `list[BaseMessage]` | 对话或日志消息集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `tools` | `list[dict[str, Any]]` | 受控工具定义集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `node_name` | `str` | 名为 `node_name` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `quality_tier` | `ModelQualityTier` | 模型质量档位；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `requested_max_output_tokens` | `int` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`ModelRouteRequest`
- **语义**：返回 `ModelRouteRequest` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `_tool_prompt_material` 完成该函数的一项辅助处理，并把结果记为 待处理的论文或源码材料；构造并返回 `ModelRouteRequest` 结构化领域对象。
```

#### `ModelGateway.invoke_tool_calling`

- **源码**：`app/model_routing/gateway.py:496`
- **签名**：`def invoke_tool_calling(self: 未显式标注, messages: list[BaseMessage], tools: list[dict[str, Any]], node_name: str, job_id: str, quality_tier: ModelQualityTier, requested_max_output_tokens: int) -> RoutedToolCallingInvocation`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收对话或日志消息集合、受控工具定义集合、当前流程节点的名称、复现任务 ID等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `RoutedToolCallingInvocation` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `messages` | `list[BaseMessage]` | 对话或日志消息集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `tools` | `list[dict[str, Any]]` | 受控工具定义集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `node_name` | `str` | 名为 `node_name` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `quality_tier` | `ModelQualityTier` | 模型质量档位；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 'economy' |
| `requested_max_output_tokens` | `int` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。；默认 768 |

**输出**

- **Python 类型**：`RoutedToolCallingInvocation`
- **语义**：返回 `RoutedToolCallingInvocation` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果对话或日志消息集合为空或为假，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果受控工具定义集合为空或为假，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
调用 `route` 完成该函数的一项辅助处理，并把结果记为 流程路由结果；调用 `_build_tool_request` 组装当前阶段需要的领域对象，并把结果记为 业务请求；调用 `route` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；计算根据字段和固定文本生成格式化文本，并保存为 工具调用记录的 ID。
调用 `_reservation` 完成该函数的一项辅助处理，并把结果记为 资源预留记录；计算使用固定配置或常量值，并保存为 领域记录。
如果MCP 评测或运行模式不等于'off'，就调用 `reserve` 完成该函数的一项辅助处理，并把结果记为 领域记录。
调用 `monotonic` 完成该函数的一项辅助处理，并把结果记为 运行是否已经启动的判断。
先尝试完成以下处理：
    调用 `build_chat` 组装当前阶段需要的领域对象，并把结果记为 语言模型；调用 `bind_tools` 完成该函数的一项辅助处理，并把结果记为 边界值。
如果出现 `Exception`并把异常保存为捕获的异常对象：
    如果MCP 评测或运行模式不等于'off'，就构造 `ModelUsage` 结构化领域对象，并把结果记为 该调用返回的结果；调用 `settle` 完成该函数的一项辅助处理。
    重新抛出当前异常，保持原始失败信息。
计算使用固定配置或常量值，并保存为 面向用户或日志的提示信息；计算使用固定配置或常量值，并保存为 模型服务商。
先尝试完成以下处理：
    遍历限定范围内的序列，每次把当前项记为当前处理结果的索引：
        先尝试完成以下处理：
            调用边界值完成模型或 Runnable 处理，并把结果记为 待审核的 MCP 能力候选。
            如果“计算数量、边界或类型判断结果”后未得到肯定结果，就拒绝继续处理并抛出 `TypeError`，向调用方报告输入或运行失败。
            读取待审核的 MCP 能力候选，并保存为 面向用户或日志的提示信息；立即结束当前循环。
        如果出现 `Exception`并把异常保存为捕获的异常对象：
            计算计算当前表达式的结果，并保存为 是否能够当前处理结果。
            如果是否能够当前处理结果为空或为假，就重新抛出当前异常，保持原始失败信息。
            计算使用固定配置或常量值，并保存为 模型服务商；调用 `sleep` 完成该函数的一项辅助处理。
如果出现 `Exception`并把异常保存为捕获的异常对象：
    如果MCP 评测或运行模式不等于'off'，就构造 `ModelUsage` 结构化领域对象，并把结果记为 该调用返回的结果；调用 `settle` 完成该函数的一项辅助处理，并把结果记为 领域记录。
    重新抛出当前异常，保持原始失败信息。
如果面向用户或日志的提示信息为空，就拒绝继续处理并抛出 `AssertionError`，向调用方报告输入或运行失败。
如果MCP 评测或运行模式不等于'off'，就调用 `usage_from_ai_message` 完成该函数的一项辅助处理，并把结果记为 模型或运行资源用量；调用 `settle` 完成该函数的一项辅助处理，并把结果记为 领域记录。
构造并返回 `RoutedToolCallingInvocation` 结构化领域对象。
```

#### `ModelGateway.invoke_embedding`

- **源码**：`app/model_routing/gateway.py:638`
- **签名**：`def invoke_embedding(self: 未显式标注, task_kind: ModelTaskKind, texts: list[str], node_name: str, invoke: Callable[[ModelProfile], EmbeddingT], job_id: str | None, run_id: str | None) -> RoutedEmbeddingInvocation[EmbeddingT]`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收类别、待处理文本集合、当前流程节点的名称、当前处理结果等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `RoutedEmbeddingInvocation[EmbeddingT]` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `task_kind` | `ModelTaskKind` | 名为 `task_kind` 的 `ModelTaskKind` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `texts` | `list[str]` | 待处理文本集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `node_name` | `str` | 名为 `node_name` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `invoke` | `Callable[[ModelProfile], EmbeddingT]` | 可调用依赖；其参数和返回契约由类型标注限定。 |
| `job_id` | `str | None` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。；默认 空值 |
| `run_id` | `str | None` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。；默认 空值 |

**输出**

- **Python 类型**：`RoutedEmbeddingInvocation[EmbeddingT]`
- **语义**：返回 `RoutedEmbeddingInvocation[EmbeddingT]` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果类别不属于{'code_embedding_document', 'code_embedding_query'}，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
调用 `estimate_texts_tokens` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；构造 `ModelRouteRequest` 结构化领域对象，并把结果记为 业务请求；调用 `route` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；计算根据字段和固定文本生成格式化文本，并保存为 工具调用记录的 ID。
调用 `_reservation` 完成该函数的一项辅助处理，并把结果记为 资源预留记录；计算使用固定配置或常量值，并保存为 领域记录。
如果MCP 评测或运行模式不等于'off'，就调用 `reserve` 完成该函数的一项辅助处理，并把结果记为 领域记录。
调用 `route` 完成该函数的一项辅助处理，并把结果记为 流程路由结果；调用 `monotonic` 完成该函数的一项辅助处理，并把结果记为 运行是否已经启动的判断；计算使用固定配置或常量值，并保存为 错误；计算使用固定配置或常量值，并保存为 当前处理结果。
遍历限定范围内的序列，每次把当前项记为当前处理结果的索引：
    将新的计算结果累加或合并到当前处理结果。
    先尝试完成以下处理：
        调用当前输入完成模型或 Runnable 处理，并把结果记为 当前字段值；立即结束当前循环。
    如果出现 `Exception`并把异常保存为捕获的异常对象：
        读取捕获的异常，并保存为 错误；计算计算当前表达式的结果，并保存为 是否能够当前处理结果。
        如果是否能够当前处理结果为空或为假：
            如果MCP 评测或运行模式不等于'off'，就构造 `ModelUsage` 结构化领域对象，并把结果记为 该调用返回的结果；调用 `settle` 完成该函数的一项辅助处理，并把结果记为 领域记录。
            重新抛出当前异常，保持原始失败信息。
        调用 `sleep` 完成该函数的一项辅助处理。
如果循环正常完成而没有提前 `break`：
    拒绝继续处理并抛出 `AssertionError`，向调用方报告输入或运行失败。
如果错误不为空 且 当前处理结果大于1，就构造 `ModelUsage` 结构化领域对象，并把结果记为 模型或运行资源用量；否则调用 `estimated_embedding_usage` 完成该函数的一项辅助处理，并把结果记为 模型或运行资源用量。
如果MCP 评测或运行模式不等于'off'，就调用 `settle` 完成该函数的一项辅助处理，并把结果记为 领域记录。
构造并返回 `RoutedEmbeddingInvocation` 结构化领域对象。
```

### `app/model_routing/identity.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `canonical_json`

- **源码**：`app/model_routing/identity.py:18`
- **签名**：`def canonical_json(value: Any) -> str`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，把模型、集合和普通对象转换成稳定 JSON。该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `Any` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
如果“计算数量、边界或类型判断结果”后得到肯定结果，就复制、序列化或校验结构化领域对象，并把结果记为 当前字段值。
定义内部辅助函数 `normalize`，供当前函数在后续步骤中调用。
将结构化内容序列化或编码为可传输表示，并返回处理结果。
```

#### `canonical_json.normalize`

- **源码**：`app/model_routing/identity.py:24`
- **签名**：`def normalize(item: Any) -> Any`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收当前处理项，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `Any` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `item` | `Any` | 当前处理项；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`Any`
- **语义**：返回 `Any` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果“计算数量、边界或类型判断结果”后得到肯定结果，就返回当前计算得到的结果。
如果“计算数量、边界或类型判断结果”后得到肯定结果，就按稳定规则整理结果顺序，并返回处理结果。
如果“计算数量、边界或类型判断结果”后得到肯定结果，就返回当前计算得到的结果。
返回当前处理项的当前值。
```

#### `sha256_text`

- **源码**：`app/model_routing/identity.py:44`
- **签名**：`def sha256_text(value: str) -> str`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回输入内容的 SHA-256 身份摘要，用于完整性校验，不是加密后的正文。

**伪代码**

```text
计算输入内容的 SHA-256 身份摘要，并返回处理结果。
```

#### `sha256_value`

- **源码**：`app/model_routing/identity.py:48`
- **签名**：`def sha256_value(value: Any) -> str`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `Any` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回输入内容的 SHA-256 身份摘要，用于完整性校验，不是加密后的正文。

**伪代码**

```text
调用 `sha256_text` 计算内容身份、分数或派生结果，并返回处理结果。
```

#### `estimate_text_tokens`

- **源码**：`app/model_routing/identity.py:52`
- **签名**：`def estimate_text_tokens(text: str) -> int`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，不下载 tokenizer 的保守预留：每个可见 UTF-8 字节预留一个 Token。该函数接收待处理文本，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终数量、序号、字节数或版本等整数结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `text` | `str` | 用户目标、检索问题、反馈或待处理文本；会作为当前阶段的业务语境输入，并可能受到长度/脱敏约束。 |

**输出**

- **Python 类型**：`int`
- **语义**：返回整数计数、序号、字节数或退出码；具体含义由函数名决定。

**伪代码**

```text
计算数量、边界或类型判断结果，并把结果记为 当前处理结果的数量；计算数量、边界或类型判断结果，并返回处理结果。
```

#### `estimate_texts_tokens`

- **源码**：`app/model_routing/identity.py:59`
- **签名**：`def estimate_texts_tokens(texts: list[str]) -> int`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收待处理文本集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终数量、序号、字节数或版本等整数结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `texts` | `list[str]` | 待处理文本集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`int`
- **语义**：返回整数计数、序号、字节数或退出码；具体含义由函数名决定。

**伪代码**

```text
如果待处理文本集合为空或为假，就拒绝继续处理并抛出 `ModelUsageError`，向调用方报告输入或运行失败。
调用 `sum` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `schema_sha256`

- **源码**：`app/model_routing/identity.py:65`
- **签名**：`def schema_sha256(schema: type[BaseModel]) -> str`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收输入输出 Schema 契约，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `schema` | `type[BaseModel]` | 结构化输出 Schema 或其名称；用于约束解析结果的字段和类型。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回输入内容的 SHA-256 身份摘要，用于完整性校验，不是加密后的正文。

**伪代码**

```text
调用 `sha256_value` 计算内容身份、分数或派生结果，并返回处理结果。
```

#### `request_sha256`

- **源码**：`app/model_routing/identity.py:69`
- **签名**：`def request_sha256(request: ModelRouteRequest) -> str`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收业务请求，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `ModelRouteRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回输入内容的 SHA-256 身份摘要，用于完整性校验，不是加密后的正文。

**伪代码**

```text
调用 `sha256_value` 计算内容身份、分数或派生结果，并返回处理结果。
```

#### `calculate_cost_micro_usd`

- **源码**：`app/model_routing/identity.py:73`
- **签名**：`def calculate_cost_micro_usd(input_tokens: int, output_tokens: int, pricing: ModelPricing) -> int | None`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收实际输入 token 数、实际输出 token 数、模型计费配置，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终数量、序号、字节数或版本等整数结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `input_tokens` | `int` | 敏感凭证或其引用；不得写入日志、Prompt 或普通 Artifact。 |
| `output_tokens` | `int` | 敏感凭证或其引用；不得写入日志、Prompt 或普通 Artifact。 |
| `pricing` | `ModelPricing` | 模型计费配置；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`int | None`
- **语义**：返回 `int | None` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果实际输入 token 数小于0 或 实际输出 token 数小于0，就拒绝继续处理并抛出 `ModelUsageError`，向调用方报告输入或运行失败。
如果模式等于'unpriced'，就返回固定值 `空值`。
如果模式等于'free'，就返回固定值 `0`。
读取当前处理结果，并保存为 比例；读取当前处理结果，并保存为 比例。
如果比例为空 或 比例为空，就拒绝继续处理并抛出 `ModelUsageError`，向调用方报告输入或运行失败。
计算组合或计算已有值，并保存为 当前处理结果；调用 `ceil` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `build_decision_sha256`

- **源码**：`app/model_routing/identity.py:98`
- **签名**：`def build_decision_sha256(decision: ModelRouteDecision) -> str`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收人工决策结果，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `decision` | `ModelRouteDecision` | 人工审批或决策记录；必须与目标动作 Hash、版本和允许操作一致。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回输入内容的 SHA-256 身份摘要，用于完整性校验，不是加密后的正文。

**伪代码**

```text
复制、序列化或校验结构化领域对象，并把结果记为 结构化请求载荷；从结构化请求载荷取出并移除最后一项；调用 `sha256_value` 计算内容身份、分数或派生结果，并返回处理结果。
```

#### `validate_decision_sha256`

- **源码**：`app/model_routing/identity.py:106`
- **签名**：`def validate_decision_sha256(decision: ModelRouteDecision) -> None`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收人工决策结果，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `decision` | `ModelRouteDecision` | 人工审批或决策记录；必须与目标动作 Hash、版本和允许操作一致。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
如果辅助操作“调用 `build_decision_sha256` 组装当前阶段需要的领域对象”的结果不等于人工决策结果的 SHA-256，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
```

### `app/model_routing/policy.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `ModelRouter.__init__`

- **源码**：`app/model_routing/policy.py:27`
- **签名**：`def __init__(self, catalog: LoadedModelCatalog) -> None`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收模型、工具或 Artifact 目录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `catalog` | `LoadedModelCatalog` | 持久化或目录访问端口；负责读取、CAS 更新或 Artifact 定位。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 模型、工具或 Artifact 目录 分别保存到同名实例字段。
```

#### `ModelRouter._supports`

- **源码**：`app/model_routing/policy.py:31`
- **签名**：`def _supports(profile: ModelProfile, request: ModelRouteRequest, minimum_quality_rank: int, required_capabilities: set[str], enforce_quality: bool) -> bool`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收MCP Client 配置档案、业务请求、当前处理结果、当前处理结果等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `profile` | `ModelProfile` | 运行/执行环境配置或 profile 标识；描述能力和限制，不是一次执行的结果。 |
| `request` | `ModelRouteRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `minimum_quality_rank` | `int` | 名为 `minimum_quality_rank` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `required_capabilities` | `set[str]` | `set[str]` 元素集合；元素代表的业务对象由参数名 `required_capabilities` 和调用位置确定。 |
| `enforce_quality` | `bool` | 布尔条件或能力开关，用于控制流程分支。；默认 真 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
如果“功能是否启用的开关有值或为真”不成立，就返回固定值 `假`。
如果类别不等于类别，就返回固定值 `假`。
如果当前处理结果有值或为真：
    如果当前处理结果小于当前处理结果，就返回固定值 `假`。
    如果当前处理结果中的对应字段小于当前处理结果中的对应字段，就返回固定值 `假`。
如果“调用 `issubset` 完成该函数的一项辅助处理”后未得到肯定结果，就返回固定值 `假`。
如果调用方要求的最大输出 token 数大于最大实际输出 token 数，就返回固定值 `假`。
计算组合或计算已有值，并保存为 上下文。
如果上下文大于上下文集合，就返回固定值 `假`。
返回固定值 `真`。
```

#### `ModelRouter.route`

- **源码**：`app/model_routing/policy.py:63`
- **签名**：`def route(self: 未显式标注, request: ModelRouteRequest, mode: ModelRoutingMode) -> tuple[ModelRouteDecision, ModelProfile]`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收业务请求、MCP 评测或运行模式，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `request` | `ModelRouteRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `mode` | `ModelRoutingMode` | MCP 评测或运行模式；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`tuple[ModelRouteDecision, ModelProfile]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
调用 `route` 完成该函数的一项辅助处理，并把结果记为 流程路由结果。
如果类别不等于类别，就拒绝继续处理并抛出 `ModelRouteUnavailable`，向调用方报告输入或运行失败。
如果估算的输入 token 数大于最大实际输入 token 数，就拒绝继续处理并抛出 `ModelRouteUnavailable`，向调用方报告输入或运行失败。
如果调用方要求的最大输出 token 数大于最大实际输出 token 数，就拒绝继续处理并抛出 `ModelRouteUnavailable`，向调用方报告输入或运行失败。
构造临时集合、映射或轻量领域对象，并把结果记为 该调用返回的结果；把当前处理结果追加或合并到当前处理结果；计算使用固定配置或常量值，并保存为 选中的候选项。
遍历当前可迭代输入，每次把当前项记为MCP Client 配置档案 ID：
    调用 `profile` 完成该函数的一项辅助处理，并把结果记为 待审核的 MCP 能力候选。
    如果“调用 `_supports` 完成该函数的一项辅助处理”后得到肯定结果，就读取待审核的 MCP 能力候选，并保存为 选中的候选项；立即结束当前循环。
如果选中的候选项为空，就拒绝继续处理并抛出 `ModelRouteUnavailable`，向调用方报告输入或运行失败。
调用 `profile` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
如果“调用 `_supports` 完成该函数的一项辅助处理”后未得到肯定结果，就拒绝继续处理并抛出 `ModelRouteUnavailable`，向调用方报告输入或运行失败。
计算根据条件从两个候选结果中选择一个，并保存为 当前处理结果。
如果MCP 评测或运行模式等于'active' 且 模式等于'unpriced' 且 “当前处理结果有值或为真”不成立，就拒绝继续处理并抛出 `ModelRouteUnavailable`，向调用方报告输入或运行失败。
计算组合或计算已有值，并保存为 最大尝试记录集合集合；计算初始化顺序集合，并保存为 当前处理结果。
如果MCP 评测或运行模式等于'shadow'：
    把新的处理结果追加或合并到当前处理结果。
否则：
    如果MCP 评测或运行模式等于'off'，就把新的处理结果追加或合并到当前处理结果；否则把新的处理结果追加或合并到当前处理结果。
构造 `ModelRouteDecision` 结构化领域对象，并把结果记为 草稿对象；复制、序列化或校验结构化领域对象，并把结果记为 人工决策结果；返回当前构造的顺序或去重集合。
```

### `app/model_routing/provider.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `ProviderFactoryPort.build_chat`

- **源码**：`app/model_routing/provider.py:20`
- **签名**：`def build_chat(self: 未显式标注, profile: ModelProfile, max_output_tokens: int) -> Any`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收MCP Client 配置档案、最大实际输出 token 数，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `Any` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `profile` | `ModelProfile` | 运行/执行环境配置或 profile 标识；描述能力和限制，不是一次执行的结果。 |
| `max_output_tokens` | `int` | 敏感凭证或其引用；不得写入日志、Prompt 或普通 Artifact。 |

**输出**

- **Python 类型**：`Any`
- **语义**：返回 `Any` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `ProviderFactoryPort.build_embedding`

- **源码**：`app/model_routing/provider.py:28`
- **签名**：`def build_embedding(self: 未显式标注, profile: ModelProfile) -> EmbeddingBackend`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收MCP Client 配置档案，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `EmbeddingBackend` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `profile` | `ModelProfile` | 运行/执行环境配置或 profile 标识；描述能力和限制，不是一次执行的结果。 |

**输出**

- **Python 类型**：`EmbeddingBackend`
- **语义**：返回 `EmbeddingBackend` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `TrustedProviderFactory.__init__`

- **源码**：`app/model_routing/provider.py:38`
- **签名**：`def __init__(self, secret_service: SecretService) -> None`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收凭据，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `secret_service` | `SecretService` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 凭据 分别保存到同名实例字段。
```

#### `TrustedProviderFactory.build_chat`

- **源码**：`app/model_routing/provider.py:41`
- **签名**：`def build_chat(self: 未显式标注, profile: ModelProfile, max_output_tokens: int) -> Any`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收MCP Client 配置档案、最大实际输出 token 数，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `Any` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `profile` | `ModelProfile` | 运行/执行环境配置或 profile 标识；描述能力和限制，不是一次执行的结果。 |
| `max_output_tokens` | `int` | 敏感凭证或其引用；不得写入日志、Prompt 或普通 Artifact。 |

**输出**

- **Python 类型**：`Any`
- **语义**：返回 `Any` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果类别不等于'chat' 或 模型服务商绑定不等于'primary_chat'，就拒绝继续处理并抛出 `ModelProviderBindingError`，向调用方报告输入或运行失败。
如果最大实际输出 token 数大于最大实际输出 token 数，就拒绝继续处理并抛出 `ModelProviderBindingError`，向调用方报告输入或运行失败。
调用 `resolve_current` 解析、规范化或转换当前输入，并把结果记为 待处理的论文或源码材料；计算按字段初始化键值映射，并保存为 当前处理结果；计算计算当前表达式的结果，并保存为 模式。
如果模式不为空 且 模式不为空，就计算按字段初始化键值映射，并保存为 当前处理结果中的对应字段。
构造并返回 `ChatOpenAI` 结构化领域对象。
```

#### `TrustedProviderFactory.build_embedding`

- **源码**：`app/model_routing/provider.py:79`
- **签名**：`def build_embedding(self: 未显式标注, profile: ModelProfile) -> EmbeddingBackend`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收MCP Client 配置档案，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `EmbeddingBackend` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `profile` | `ModelProfile` | 运行/执行环境配置或 profile 标识；描述能力和限制，不是一次执行的结果。 |

**输出**

- **Python 类型**：`EmbeddingBackend`
- **语义**：返回 `EmbeddingBackend` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果类别不等于'embedding' 或 模型服务商绑定不等于'primary_embedding'，就拒绝继续处理并抛出 `ModelProviderBindingError`，向调用方报告输入或运行失败。
调用 `resolve_current` 解析、规范化或转换当前输入，并把结果记为 待处理的论文或源码材料；构造并返回 `OpenAICompatibleEmbeddingBackend` 结构化领域对象。
```

### `app/model_routing/repository.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `utc_now`

- **源码**：`app/model_routing/repository.py:30`
- **签名**：`def utc_now() -> datetime`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `datetime` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`datetime`
- **语义**：返回 `datetime` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
读取当前时间，作为状态变更的统一时间戳，并返回处理结果。
```

#### `iso_utc`

- **源码**：`app/model_routing/repository.py:34`
- **签名**：`def iso_utc(value: datetime) -> str`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `datetime` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
如果当前处理结果为空，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
调用 `isoformat` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `SqliteModelLedger.__init__`

- **源码**：`app/model_routing/repository.py:41`
- **签名**：`def __init__(self: 未显式标注, path: Path, budget: ModelBudgetPolicy) -> None`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收文件或目录路径、模型或实验资源预算，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |
| `budget` | `ModelBudgetPolicy` | 模型或实验资源预算；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 文件或目录路径、模型或实验资源预算 分别保存到同名实例字段；创建父级目录或父领域对象对应的目录；调用 `_initialize` 完成该函数的一项辅助处理。
```

#### `SqliteModelLedger._connect`

- **源码**：`app/model_routing/repository.py:52`
- **签名**：`def _connect(self) -> sqlite3.Connection`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于在固定 MCP Policy、Schema Pin、调用预算和只读职责边界内连接或调用外部能力，并把返回内容转换为可追溯的复现证据，最终标注为 `sqlite3.Connection` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`sqlite3.Connection`
- **语义**：返回 `sqlite3.Connection` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `connect` 完成该函数的一项辅助处理，并把结果记为 数据库连接；读取数据库记录行，并保存为 记录行；通过数据库连接执行数据查询或命令；通过数据库连接执行数据查询或命令。
通过数据库连接执行数据查询或命令；通过数据库连接执行数据查询或命令；返回数据库连接的当前值。
```

#### `SqliteModelLedger._initialize`

- **源码**：`app/model_routing/repository.py:65`
- **签名**：`def _initialize(self) -> None`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”中调用 `executescript` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `SqliteModelLedger.ping`

- **源码**：`app/model_routing/repository.py:108`
- **签名**：`def ping(self) -> None`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”中调用 `fetchone` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `SqliteModelLedger._record`

- **源码**：`app/model_routing/repository.py:113`
- **签名**：`def _record(row: sqlite3.Row) -> ModelInvocationRecord`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收数据库记录行，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `row` | `sqlite3.Row` | 数据库记录行；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`ModelInvocationRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
先尝试完成以下处理：
    构造 `ModelInvocationRecord` 结构化领域对象，并把结果记为 领域记录。
如果出现 `Exception`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `ModelLedgerIntegrityError`，向调用方报告输入或运行失败。
返回领域记录的当前值。
```

#### `SqliteModelLedger._load`

- **源码**：`app/model_routing/repository.py:152`
- **签名**：`def _load(connection: sqlite3.Connection, invocation_id: str) -> ModelInvocationRecord | None`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收数据库连接、工具调用记录的 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `connection` | `sqlite3.Connection` | 数据库连接；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `invocation_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`ModelInvocationRecord | None`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
调用 `fetchone` 完成该函数的一项辅助处理，并把结果记为 数据库记录行；返回按条件选出的结果。
```

#### `SqliteModelLedger._usage_totals`

- **源码**：`app/model_routing/repository.py:163`
- **签名**：`def _usage_totals(connection: sqlite3.Connection, utc_date: str, job_id: str | None) -> tuple[int, int]`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收数据库连接、日期、复现任务 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `connection` | `sqlite3.Connection` | 数据库连接；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `utc_date` | `str` | 名为 `utc_date` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `job_id` | `str | None` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`tuple[int, int]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
计算使用固定配置或常量值，并保存为 当前处理结果；计算初始化顺序集合，并保存为 当前处理结果。
如果复现任务 ID不为空，就将新的计算结果累加或合并到当前处理结果；把复现任务 ID追加或合并到当前处理结果。
调用 `fetchone` 完成该函数的一项辅助处理，并把结果记为 数据库记录行；返回当前构造的顺序或去重集合。
```

#### `SqliteModelLedger._check_limit`

- **源码**：`app/model_routing/repository.py:201`
- **签名**：`def _check_limit(scope: str, limit: int | None, used_or_reserved: int, requested: int) -> None`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收查询或授权作用域、结果数量上限、已使用或已预留的资源量、当前处理结果，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `scope` | `str` | 查询或授权作用域；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `limit` | `int | None` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。 |
| `used_or_reserved` | `int` | 已使用或已预留的资源量；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `requested` | `int` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
如果结果数量上限为空，就结束当前函数，不返回业务值。
如果当前输入内容大于结果数量上限，就拒绝继续处理并抛出 `ModelBudgetExceeded`，向调用方报告输入或运行失败。
```

#### `SqliteModelLedger.reserve`

- **源码**：`app/model_routing/repository.py:218`
- **签名**：`def reserve(self: 未显式标注, request: ModelReservationRequest, now: datetime | None) -> ModelInvocationRecord`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收业务请求、当前时间，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `request` | `ModelReservationRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `now` | `datetime | None` | 时间值或可注入时钟，用于排序、过期、租约或可重复测试。；默认 空值 |

**输出**

- **Python 类型**：`ModelInvocationRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
计算计算当前表达式的结果，并保存为 当前值的时间；调用 `iso_utc` 完成该函数的一项辅助处理，并把结果记为 创建时间；读取创建时间中的对应字段，并保存为 日期；调用 `_connect` 完成该函数的一项辅助处理，并把结果记为 数据库连接。
先尝试完成以下处理：
    通过数据库连接执行数据查询或命令；调用 `_load` 完成该函数的一项辅助处理，并把结果记为 已有记录。
    如果已有记录不为空：
        如果请求内容 SHA-256不等于请求内容 SHA-256 或 人工决策结果的 SHA-256不等于人工决策结果的 SHA-256，就拒绝继续处理并抛出 `ModelLedgerConflict`，向调用方报告输入或运行失败。
        提交数据库连接中已完成的数据变更；返回已有记录的当前值。
    如果当前处理结果有值或为真：
        调用 `_usage_totals` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；调用 `_check_limit` 校验当前输入或状态。
        如果预留的微美元成本不为空，就调用 `_check_limit` 校验当前输入或状态。
        如果复现任务 ID不为空：
            调用 `_usage_totals` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；调用 `_check_limit` 校验当前输入或状态。
            如果预留的微美元成本不为空，就调用 `_check_limit` 校验当前输入或状态。
    通过数据库连接执行数据查询或命令；调用 `_load` 完成该函数的一项辅助处理，并把结果记为 已保存结果。
    如果已保存结果为空，就拒绝继续处理并抛出 `ModelLedgerIntegrityError`，向调用方报告输入或运行失败。
    提交数据库连接中已完成的数据变更；返回已保存结果的当前值。
如果出现 `Exception`：
    回滚数据库连接中未完成的数据变更；重新抛出当前异常，保持原始失败信息。
无论成功还是失败，最后都要：
    关闭数据库连接并释放相关资源。
```

#### `SqliteModelLedger.settle`

- **源码**：`app/model_routing/repository.py:332`
- **签名**：`def settle(self: 未显式标注, invocation_id: str, status: str, usage: ModelUsage, latency_ms: int, error_code: str | None, now: datetime | None) -> ModelInvocationRecord`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收工具调用记录的 ID、当前状态、模型或运行资源用量、当前处理结果等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `invocation_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `status` | `str` | 来源、类别、用途、后端、状态或操作原因等控制字段；通常对应有限的业务枚举或审计文本。 |
| `usage` | `ModelUsage` | 模型或运行资源用量；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `latency_ms` | `int` | 名为 `latency_ms` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `error_code` | `str | None` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |
| `now` | `datetime | None` | 时间值或可注入时钟，用于排序、过期、租约或可重复测试。；默认 空值 |

**输出**

- **Python 类型**：`ModelInvocationRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
如果当前状态不属于当前处理结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果错误不为空 且 “调用 `fullmatch` 完成该函数的一项辅助处理”后未得到肯定结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
调用 `iso_utc` 完成该函数的一项辅助处理，并把结果记为 更新时间；调用 `_connect` 完成该函数的一项辅助处理，并把结果记为 数据库连接。
先尝试完成以下处理：
    通过数据库连接执行数据查询或命令；调用 `_load` 完成该函数的一项辅助处理，并把结果记为 当前值。
    如果当前值为空，就拒绝继续处理并抛出 `ModelLedgerConflict`，向调用方报告输入或运行失败。
    如果当前状态属于当前处理结果：
        计算计算当前表达式的结果，并保存为 当前处理结果。
        如果当前处理结果为空或为假，就拒绝继续处理并抛出 `ModelLedgerConflict`，向调用方报告输入或运行失败。
        提交数据库连接中已完成的数据变更；返回当前值的当前值。
    如果当前状态不等于'reserved'，就拒绝继续处理并抛出 `ModelLedgerIntegrityError`，向调用方报告输入或运行失败。
    通过数据库连接执行数据查询或命令。
    如果当前处理结果不等于1，就拒绝继续处理并抛出 `ModelLedgerConflict`，向调用方报告输入或运行失败。
    调用 `_load` 完成该函数的一项辅助处理，并把结果记为 已保存结果。
    如果已保存结果为空，就拒绝继续处理并抛出 `ModelLedgerIntegrityError`，向调用方报告输入或运行失败。
    提交数据库连接中已完成的数据变更；返回已保存结果的当前值。
如果出现 `Exception`：
    回滚数据库连接中未完成的数据变更；重新抛出当前异常，保持原始失败信息。
无论成功还是失败，最后都要：
    关闭数据库连接并释放相关资源。
```

#### `SqliteModelLedger.reconcile_stale`

- **源码**：`app/model_routing/repository.py:414`
- **签名**：`def reconcile_stale(self: 未显式标注, now: datetime | None, limit: int) -> list[ModelInvocationRecord]`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收当前时间、结果数量上限，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `now` | `datetime | None` | 时间值或可注入时钟，用于排序、过期、租约或可重复测试。；默认 空值 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。；默认 100 |

**输出**

- **Python 类型**：`list[ModelInvocationRecord]`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
如果结果数量上限小于1 或 结果数量上限大于1000，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
计算计算当前表达式的结果，并保存为 当前值的时间；调用 `iso_utc` 完成该函数的一项辅助处理，并把结果记为 当前；调用 `_connect` 完成该函数的一项辅助处理，并把结果记为 数据库连接。
先尝试完成以下处理：
    通过数据库连接执行数据查询或命令；调用 `fetchall` 完成该函数的一项辅助处理，并把结果记为 数据库记录行集合；遍历并筛选输入，将整理后的结果保存为 调用记录集合。
    遍历由调用记录集合组成的集合或迭代器，每次把当前项记为工具调用记录的 ID，然后通过数据库连接执行数据查询或命令。
    将 领域记录集合 初始化为空列表，用来收集后续结果。
    遍历由调用记录集合组成的集合或迭代器，每次把当前项记为工具调用记录的 ID：
        调用 `_load` 完成该函数的一项辅助处理，并把结果记为 领域记录。
        如果领域记录为空，就拒绝继续处理并抛出 `ModelLedgerIntegrityError`，向调用方报告输入或运行失败。
        把领域记录追加或合并到领域记录集合。
    提交数据库连接中已完成的数据变更；返回领域记录集合的当前值。
如果出现 `Exception`：
    回滚数据库连接中未完成的数据变更；重新抛出当前异常，保持原始失败信息。
无论成功还是失败，最后都要：
    关闭数据库连接并释放相关资源。
```

#### `SqliteModelLedger.summary`

- **源码**：`app/model_routing/repository.py:474`
- **签名**：`def summary(self: 未显式标注, utc_date: str, job_id: str | None) -> ModelBudgetSummary`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收日期、复现任务 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ModelBudgetSummary` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `utc_date` | `str` | 名为 `utc_date` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `job_id` | `str | None` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。；默认 空值 |

**输出**

- **Python 类型**：`ModelBudgetSummary`
- **语义**：返回 `ModelBudgetSummary` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
进入上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”，退出时自动清理资源：
    计算使用固定配置或常量值，并保存为 当前处理结果；计算初始化顺序集合，并保存为 当前处理结果。
    如果复现任务 ID不为空，就将新的计算结果累加或合并到当前处理结果；把复现任务 ID追加或合并到当前处理结果。
    调用 `fetchone` 完成该函数的一项辅助处理，并把结果记为 数据库记录行。
构造并返回 `ModelBudgetSummary` 结构化领域对象。
```

#### `SqliteModelLedger.list_invocations`

- **源码**：`app/model_routing/repository.py:528`
- **签名**：`def list_invocations(self: 未显式标注, limit: int, job_id: str | None) -> list[ModelInvocationRecord]`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收结果数量上限、复现任务 ID，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。；默认 100 |
| `job_id` | `str | None` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。；默认 空值 |

**输出**

- **Python 类型**：`list[ModelInvocationRecord]`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
如果结果数量上限小于1 或 结果数量上限大于500，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
进入上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”，退出时自动清理资源：
    如果复现任务 ID为空，就调用 `fetchall` 完成该函数的一项辅助处理，并把结果记为 数据库记录行集合；否则调用 `fetchall` 完成该函数的一项辅助处理，并把结果记为 数据库记录行集合。
返回当前计算得到的结果。
```

### `app/model_routing/schemas.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `ModelPricing.validate_price_shape`

- **源码**：`app/model_routing/schemas.py:72`
- **签名**：`def validate_price_shape(self) -> "ModelPricing"`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `'ModelPricing'` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`'ModelPricing'`
- **语义**：返回 `'ModelPricing'` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果模式等于'priced'：
    如果当前处理结果为空 或 当前处理结果为空，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
否则：
    如果模式等于'free'：
        如果当前处理结果不属于{空值, 0}，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
        如果当前处理结果不属于{空值, 0}，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    否则：
        如果当前处理结果不为空 或 当前处理结果不为空，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前对象的当前值。
```

#### `ModelProfile.validate_workload`

- **源码**：`app/model_routing/schemas.py:110`
- **签名**：`def validate_workload(self) -> "ModelProfile"`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `'ModelProfile'` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`'ModelProfile'`
- **语义**：返回 `'ModelProfile'` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果类别等于'embedding'：
    如果模型服务商绑定不等于'primary_embedding'，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    如果当前输入内容不属于当前处理结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    如果最大实际输出 token 数不等于0，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    如果模式不为空，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
否则：
    如果模型服务商绑定不等于'primary_chat'，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    如果当前输入内容属于当前处理结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    如果最大实际输出 token 数小于1，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前对象的当前值。
```

#### `ModelTaskRoute.validate_candidate_ids`

- **源码**：`app/model_routing/schemas.py:146`
- **签名**：`def validate_candidate_ids(cls, values: list[str]) -> list[str]`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收状态字段集合，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `cls` | `未显式标注` | 当前类对象，用于类级构造或校验。 |
| `values` | `list[str]` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`list[str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
如果状态字段集合 的长度不等于辅助操作“构造临时集合、映射或轻量领域对象”的结果 的长度，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回状态字段集合的当前值。
```

#### `ModelTaskRoute.validate_embedding_limits`

- **源码**：`app/model_routing/schemas.py:152`
- **签名**：`def validate_embedding_limits(self) -> "ModelTaskRoute"`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `'ModelTaskRoute'` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`'ModelTaskRoute'`
- **语义**：返回 `'ModelTaskRoute'` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果类别等于'embedding'：
    如果最大实际输出 token 数不等于0，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    如果当前处理结果不等于{'embedding'}，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前对象的当前值。
```

#### `ModelRouteRequest.validate_workload_shape`

- **源码**：`app/model_routing/schemas.py:196`
- **签名**：`def validate_workload_shape(self) -> "ModelRouteRequest"`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `'ModelRouteRequest'` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`'ModelRouteRequest'`
- **语义**：返回 `'ModelRouteRequest'` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果类别等于'embedding'：
    如果调用方要求的最大输出 token 数不等于0，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    如果输入输出 Schema 契约的名称不为空 或 输入输出 Schema 契约的 SHA-256不为空，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
否则：
    如果当前输入内容不等于self.schema_sha256 为空，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前对象的当前值。
```

#### `ModelReservationRequest.reserved_total_tokens`

- **源码**：`app/model_routing/schemas.py:243`
- **签名**：`def reserved_total_tokens(self) -> int`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终数量、序号、字节数或版本等整数结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`int`
- **语义**：返回整数计数、序号、字节数或退出码；具体含义由函数名决定。

**伪代码**

```text
返回当前计算得到的结果。
```

#### `ModelUsage.validate_total`

- **源码**：`app/model_routing/schemas.py:256`
- **签名**：`def validate_total(self) -> "ModelUsage"`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `'ModelUsage'` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`'ModelUsage'`
- **语义**：返回 `'ModelUsage'` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果当前处理结果不等于实际输入 token 数 + 实际输出 token 数，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前对象的当前值。
```

### `app/model_routing/usage.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_usage_int`

- **源码**：`app/model_routing/usage.py:12`
- **签名**：`def _usage_int(usage: dict[str, Any], *names: str) -> int | None`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收模型或运行资源用量、当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终数量、序号、字节数或版本等整数结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `usage` | `dict[str, Any]` | 模型或运行资源用量；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `*names` | `str` | 额外位置参数序列。 |

**输出**

- **Python 类型**：`int | None`
- **语义**：返回 `int | None` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
遍历由当前处理结果组成的集合或迭代器，每次把当前项记为对象名称：
    从模型或运行资源用量读取所需的状态或领域记录，并把结果记为 当前字段值。
    如果当前字段值为空，就跳过本轮剩余处理，直接进入下一轮。
    先尝试完成以下处理：
        调用 `int` 完成该函数的一项辅助处理，并把结果记为 解析后的结果。
    如果出现 `(TypeError, ValueError)`：
        返回固定值 `空值`。
    返回按条件选出的结果。
返回固定值 `空值`。
```

#### `usage_from_structured_attempts`

- **源码**：`app/model_routing/usage.py:28`
- **签名**：`def usage_from_structured_attempts(attempts: list[Any], reserved_input_tokens: int, reserved_output_tokens: int, reserved_cost_micro_usd: int | None, pricing: ModelPricing) -> ModelUsage`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，汇总每个真正收到响应的 Structured Output attempt。该函数接收模型尝试记录集合、预留的输入 token 数、预留的输出 token 数、预留的微美元成本等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ModelUsage` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `attempts` | `list[Any]` | 模型尝试记录集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `reserved_input_tokens` | `int` | 敏感凭证或其引用；不得写入日志、Prompt 或普通 Artifact。 |
| `reserved_output_tokens` | `int` | 敏感凭证或其引用；不得写入日志、Prompt 或普通 Artifact。 |
| `reserved_cost_micro_usd` | `int | None` | 预留的微美元成本；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `pricing` | `ModelPricing` | 模型计费配置；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`ModelUsage`
- **语义**：返回 `ModelUsage` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
计算使用固定配置或常量值，并保存为 实际输入 token 数；计算使用固定配置或常量值，并保存为 实际输出 token 数；计算使用固定配置或常量值，并保存为 结构化响应的数量；计算使用固定配置或常量值，并保存为 当前处理结果。
计算使用固定配置或常量值，并保存为 当前处理结果。
遍历由模型尝试记录集合组成的集合或迭代器，每次把当前项记为尝试：
    调用 `getattr` 完成该函数的一项辅助处理，并把结果记为 当前状态；调用 `getattr` 完成该函数的一项辅助处理，并把结果记为 模型或运行资源用量。
    如果当前状态属于{'provider_retry', 'invoke_error', 'validation_error', 'succeeded'}，就计算使用固定配置或常量值，并保存为 当前处理结果。
    如果“计算数量、边界或类型判断结果”后未得到肯定结果：
        如果当前状态属于{'validation_error', 'succeeded'}，就计算使用固定配置或常量值，并保存为 当前处理结果。
        如果当前状态属于{'provider_retry', 'invoke_error'}，就计算使用固定配置或常量值，并保存为 当前处理结果。
        跳过本轮剩余处理，直接进入下一轮。
    调用 `_usage_int` 完成该函数的一项辅助处理，并把结果记为 发给模型的结构化提示；调用 `_usage_int` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
    如果发给模型的结构化提示为空 或 当前处理结果为空，就计算使用固定配置或常量值，并保存为 当前处理结果；跳过本轮剩余处理，直接进入下一轮。
    将新的计算结果累加或合并到实际输入 token 数；将新的计算结果累加或合并到实际输出 token 数；将新的计算结果累加或合并到结构化响应的数量。
如果当前处理结果有值或为真 且 当前处理结果有值或为真 或 结构化响应的数量等于0，就构造并返回 `ModelUsage` 结构化领域对象。
如果当前处理结果为空或为假，就构造并返回 `ModelUsage` 结构化领域对象。
构造并返回 `ModelUsage` 结构化领域对象。
```

#### `estimated_embedding_usage`

- **源码**：`app/model_routing/usage.py:113`
- **签名**：`def estimated_embedding_usage(input_tokens: int, pricing: ModelPricing) -> ModelUsage`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，该函数接收实际输入 token 数、模型计费配置，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ModelUsage` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `input_tokens` | `int` | 敏感凭证或其引用；不得写入日志、Prompt 或普通 Artifact。 |
| `pricing` | `ModelPricing` | 模型计费配置；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`ModelUsage`
- **语义**：返回 `ModelUsage` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `ModelUsage` 结构化领域对象。
```

#### `usage_from_ai_message`

- **源码**：`app/model_routing/usage.py:132`
- **签名**：`def usage_from_ai_message(message: Any, reserved_input_tokens: int, reserved_output_tokens: int, reserved_cost_micro_usd: int | None, pricing: ModelPricing, had_provider_retry: bool) -> ModelUsage`
- **作用**：在为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段中，从成功 AIMessage 结算一次 Tool Selection 调用。该函数接收面向用户或日志的提示信息、预留的输入 token 数、预留的输出 token 数、预留的微美元成本等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ModelUsage` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `message` | `Any` | 对话消息记录或消息文本；角色、顺序和内容 Hash 可能参与证据校验。 |
| `reserved_input_tokens` | `int` | 敏感凭证或其引用；不得写入日志、Prompt 或普通 Artifact。 |
| `reserved_output_tokens` | `int` | 敏感凭证或其引用；不得写入日志、Prompt 或普通 Artifact。 |
| `reserved_cost_micro_usd` | `int | None` | 预留的微美元成本；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `pricing` | `ModelPricing` | 模型计费配置；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `had_provider_retry` | `bool` | 布尔条件或能力开关，用于控制流程分支。 |

**输出**

- **Python 类型**：`ModelUsage`
- **语义**：返回 `ModelUsage` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果模型服务商有值或为真，就构造并返回 `ModelUsage` 结构化领域对象。
调用 `getattr` 完成该函数的一项辅助处理，并把结果记为 模型或运行资源用量。
如果“计算数量、边界或类型判断结果”后未得到肯定结果，就构造并返回 `ModelUsage` 结构化领域对象。
调用 `_usage_int` 完成该函数的一项辅助处理，并把结果记为 实际输入 token 数；调用 `_usage_int` 完成该函数的一项辅助处理，并把结果记为 实际输出 token 数。
如果实际输入 token 数为空 或 实际输出 token 数为空，就构造并返回 `ModelUsage` 结构化领域对象。
构造并返回 `ModelUsage` 结构化领域对象。
```

### `app/prompts/tool_calling_prompt.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `build_tool_selection_user_message`

- **源码**：`app/prompts/tool_calling_prompt.py:35`
- **签名**：`def build_tool_selection_user_message(question: str, job_status: str) -> str`
- **作用**：在在 Schema、预算和只读证据边界内编排论文复现 Agent 的有界 Tool Calling 阶段中，该函数接收论文复现问题或用户问题、任务状态，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `question` | `str` | 论文复现问题或用户问题；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `job_status` | `str` | 名为 `job_status` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
返回当前计算得到的结果。
```

### `app/research_browser/catalog.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `LoadedResearchPolicy.effective_hosts`

- **源码**：`app/research_browser/catalog.py:23`
- **签名**：`def effective_hosts(self, request: ResearchRequest) -> tuple[str, ...]`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收业务请求，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `request` | `ResearchRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`tuple[str, ...]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
构造临时集合、映射或轻量领域对象，并把结果记为 策略集合。
如果“允许访问的主机集合有值或为真”不成立，就返回策略集合的当前值。
构造临时集合、映射或轻量领域对象，并把结果记为 该调用返回的结果。
遍历由当前处理结果组成的集合或迭代器，每次把当前项记为服务监听地址：
    如果“检查由策略集合组成的集合或迭代器中是否存在满足“服务监听地址等于当前处理结果 或 “检查服务监听地址是否满足文本匹配条件”后得到肯定结果”的项”后未得到肯定结果，就拒绝继续处理并抛出 `ResearchPolicyError`，向调用方报告输入或运行失败。
返回前一步处理得到的结果。
```

#### `load_research_policy`

- **源码**：`app/research_browser/catalog.py:37`
- **签名**：`def load_research_policy(path: Path, *, allowed_root: Path) -> LoadedResearchPolicy`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收文件或目录路径、根目录，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `LoadedResearchPolicy` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |
| `allowed_root` | `Path` | 已经解析的文件或目录路径对象；后续操作仍需遵守仓库/工作区边界。 |

**输出**

- **Python 类型**：`LoadedResearchPolicy`
- **语义**：返回从外部表示解析并校验后的领域值；格式非法时通过异常失败。

**伪代码**

```text
将辅助操作“将根目录规范化为受控的绝对路径”的结果规范化为受控的绝对路径，并把结果记为 受控扫描根目录；将文件或目录路径规范化为受控的绝对路径，并把结果记为 待审核的 MCP 能力候选。
如果“检查待审核的 MCP 能力候选的文件系统属性”后得到肯定结果，就拒绝继续处理并抛出 `ResearchPolicyError`，向调用方报告输入或运行失败。
将待审核的 MCP 能力候选规范化为受控的绝对路径，并把结果记为 解析后的值。
先尝试完成以下处理：
    把解析后的值转换为稳定的仓库相对路径表示。
如果出现 `ValueError`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `ResearchPolicyError`，向调用方报告输入或运行失败。
如果“检查解析后的值的文件系统属性”后未得到肯定结果，就拒绝继续处理并抛出 `ResearchPolicyError`，向调用方报告输入或运行失败。
如果前一步操作返回对象的当前处理结果大于最大安全策略的字节内容，就拒绝继续处理并抛出 `ResearchPolicyError`，向调用方报告输入或运行失败。
先尝试完成以下处理：
    将外部表示解析为结构化内容，并把结果记为 原始内容；复制、序列化或校验结构化领域对象，并把结果记为 论文解析文档。
如果出现 `(OSError, UnicodeDecodeError, json.JSONDecodeError, ValidationError)`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `ResearchPolicyError`，向调用方报告输入或运行失败。
构造并返回 `LoadedResearchPolicy` 结构化领域对象。
```

### `app/research_browser/collector.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_keywords`

- **源码**：`app/research_browser/collector.py:37`
- **签名**：`def _keywords(query: str) -> set[str]`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收语义检索问题，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `query` | `str` | 用户目标、检索问题、反馈或待处理文本；会作为当前阶段的业务语境输入，并可能受到长度/脱敏约束。 |

**输出**

- **Python 类型**：`set[str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
返回当前计算得到的结果。
```

#### `_score`

- **源码**：`app/research_browser/collector.py:41`
- **签名**：`def _score(text: str, keywords: set[str]) -> float`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收待处理文本、检索关键词集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终用于排序或质量评估的分数、比例或相似度。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `text` | `str` | 用户目标、检索问题、反馈或待处理文本；会作为当前阶段的业务语境输入，并可能受到长度/脱敏约束。 |
| `keywords` | `set[str]` | 用于精确检索或文件分类的关键词集合；匹配范围由当前工具决定。 |

**输出**

- **Python 类型**：`float`
- **语义**：返回浮点分数、时间或比例值。

**伪代码**

```text
对待处理文本中的文本执行规范化或拆分，并把结果记为 转为小写的比较文本。
如果检索关键词集合为空或为假，就返回固定值 `0.0`。
调用 `sum` 完成该函数的一项辅助处理，并把结果记为 检索命中结果；计算数量、边界或类型判断结果，并返回处理结果。
```

#### `_candidate_hash`

- **源码**：`app/research_browser/collector.py:49`
- **签名**：`def _candidate_hash(candidate: ResearchResourceCandidate) -> str`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收待审核的 MCP 能力候选，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `candidate` | `ResearchResourceCandidate` | 待审核的 MCP 能力候选；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回内容身份摘要，通常为 SHA-256 十六进制字符串。

**伪代码**

```text
调用 `sha256_value` 计算内容身份、分数或派生结果，并返回处理结果。
```

#### `ResearchCollector.__init__`

- **源码**：`app/research_browser/collector.py:54`
- **签名**：`def __init__(self: 未显式标注, search_provider: SearchProviderPort, fetcher: BoundedResearchFetcher, policy: ResearchPolicyDocument, policy_sha256: str) -> None`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收模型服务商、当前处理结果、安全策略、安全策略的 SHA-256，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `search_provider` | `SearchProviderPort` | 名为 `search_provider` 的 `SearchProviderPort` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `fetcher` | `BoundedResearchFetcher` | 名为 `fetcher` 的 `BoundedResearchFetcher` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `policy` | `ResearchPolicyDocument` | 安全策略；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `policy_sha256` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 模型服务商、当前处理结果、安全策略、安全策略的 SHA-256 分别保存到同名实例字段。
```

#### `ResearchCollector.collect`

- **源码**：`app/research_browser/collector.py:67`
- **签名**：`def collect(self, request: ResearchRequest) -> ResearchEvidenceDraft`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收业务请求，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ResearchEvidenceDraft` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `request` | `ResearchRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`ResearchEvidenceDraft`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
调用 `safe_search_text` 完成该函数的一项辅助处理，并把结果记为 语义检索问题；调用 `search` 完成该函数的一项辅助处理，并把结果记为 模型服务商集合；将 检索命中结果 初始化为空列表，用来收集后续结果；将 当前处理结果 初始化为空去重集合，用来收集后续结果。
将 当前处理结果 初始化为空列表，用来收集后续结果；构造临时集合、映射或轻量领域对象，并把结果记为 该调用返回的结果。
遍历由模型服务商集合组成的集合或迭代器，每次把当前项记为模型服务商：
    先尝试完成以下处理：
        调用 `canonicalize_research_url` 完成该函数的一项辅助处理，并把结果记为 外部论文、仓库或服务地址。
    如果出现 `Exception`：
        把新的处理结果追加或合并到当前处理结果；跳过本轮剩余处理，直接进入下一轮。
    对当前输入内容中的文本执行规范化或拆分，并把结果记为 服务监听地址。
    如果“调用 `host_matches` 完成该函数的一项辅助处理”后未得到肯定结果，就把新的处理结果追加或合并到当前处理结果；跳过本轮剩余处理，直接进入下一轮。
    如果外部论文、仓库或服务地址属于当前处理结果，就跳过本轮剩余处理，直接进入下一轮。
    把外部论文、仓库或服务地址追加或合并到当前处理结果；计算按字段初始化键值映射，并保存为 对象身份；把新的处理结果追加或合并到检索命中结果。
将 当前处理结果 初始化为空列表，用来收集后续结果；计算使用固定配置或常量值，并保存为 当前处理结果的字节内容。
遍历由检索命中结果组成的集合或迭代器，每次把当前项记为当前处理结果：
    如果当前处理结果 的长度不小于最大证据来源集合，就立即结束当前循环。
    先尝试完成以下处理：
        调用 `fetch` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
        如果Artifact 媒体类型等于'application/pdf' 且 “PDF有值或为真”不成立，就把新的处理结果追加或合并到当前处理结果；跳过本轮剩余处理，直接进入下一轮。
        将新的计算结果累加或合并到当前处理结果的字节内容。
        如果当前处理结果的字节内容大于最大当前处理结果的字节内容，就拒绝继续处理并抛出 `ResearchLimitExceeded`，向调用方报告输入或运行失败。
        调用 `extract_document` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `stable_id` 完成该函数的一项辅助处理，并把结果记为 MCP 能力快照的 ID；把新的处理结果追加或合并到当前处理结果。
    如果出现 `ResearchLimitExceeded`：
        重新抛出当前异常，保持原始失败信息。
    如果出现 `Exception`：
        把新的处理结果追加或合并到当前处理结果。
调用 `_keywords` 完成该函数的一项辅助处理，并把结果记为 检索关键词集合；将 论文引用证据集合 初始化为空列表，用来收集后续结果。
遍历由当前处理结果组成的集合或迭代器，每次把当前项记为MCP 能力快照：
    读取前一步操作返回对象中的对应字段，并保存为 后续步骤使用的结果。
    遍历由当前处理结果组成的集合或迭代器，每次把当前项记为论文原文块，然后读取待处理文本中的对应字段，并保存为 后续步骤使用的结果；调用 `sha256_text` 计算内容身份、分数或派生结果，并把结果记为 当前处理结果的 Hash；计算按字段初始化键值映射，并保存为 身份；把新的处理结果追加或合并到论文引用证据集合。
读取前一步操作返回对象中的对应字段，并保存为 论文引用证据集合；将 当前处理结果 初始化为空映射，用来收集后续结果。
遍历由论文引用证据集合组成的集合或迭代器，每次把当前项记为论文引用证据，然后把论文引用证据追加或合并到辅助操作“把MCP 能力快照的 ID追加或合并到当前处理结果”的结果。
将 候选结果集合 初始化为空列表，用来收集后续结果。
遍历由当前处理结果组成的集合或迭代器，每次把当前项记为MCP 能力快照：
    从当前处理结果读取所需的状态或领域记录，并把结果记为 可追溯证据记录。
    如果可追溯证据记录为空或为假，就跳过本轮剩余处理，直接进入下一轮。
    如果来源类别等于'pdf' 且 “前一步操作返回对象的语义检索问题有值或为真”不成立，就构造 `ResearchResourceCandidate` 结构化领域对象，并把结果记为 草稿对象；把新的处理结果追加或合并到候选结果集合。
遍历由检索命中结果组成的集合或迭代器，每次把当前项记为当前处理结果：
    调用 `urlsplit` 完成该函数的一项辅助处理，并把结果记为 解析后的结果。
    如果当前处理结果不等于'github.com' 或 语义检索问题有值或为真，就跳过本轮剩余处理，直接进入下一轮。
    调用 `match` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
    如果当前处理结果为空，就跳过本轮剩余处理，直接进入下一轮。
    调用 `groups` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；调用 `urlunsplit` 完成该函数的一项辅助处理，并把结果记为 代码仓库；将 当前处理结果 初始化为空列表，用来收集后续结果。
    遍历由论文引用证据集合组成的集合或迭代器，每次把当前项记为当前处理项：
        调用 `urlsplit` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
        如果当前处理结果不等于'github.com'，就跳过本轮剩余处理，直接进入下一轮。
        调用 `match` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
        如果当前处理结果为空，就跳过本轮剩余处理，直接进入下一轮。
        调用 `groups` 完成该函数的一项辅助处理，并把结果记为 多个解包结果。
        如果当前处理结果等于当前处理结果 且 代码仓库等于持久化仓库 且 辅助操作“对当前处理结果中的文本执行规范化或拆分”的结果等于辅助操作“对当前处理结果中的文本执行规范化或拆分”的结果，就把当前处理项追加或合并到当前处理结果。
        如果当前处理结果 的长度不小于3，就立即结束当前循环。
    如果当前处理结果为空或为假，就跳过本轮剩余处理，直接进入下一轮。
    构造 `ResearchResourceCandidate` 结构化领域对象，并把结果记为 草稿对象；把新的处理结果追加或合并到候选结果集合。
构造并返回 `ResearchEvidenceDraft` 结构化领域对象。
```

### `app/research_browser/doctor.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `inspect_research_browser`

- **源码**：`app/research_browser/doctor.py:11`
- **签名**：`def inspect_research_browser() -> ResearchHealthReport`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ResearchHealthReport` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`ResearchHealthReport`
- **语义**：返回 `ResearchHealthReport` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果“当前处理结果有值或为真”不成立，就构造并返回 `ResearchHealthReport` 结构化领域对象。
将 诊断问题集合 初始化为空列表，用来收集后续结果；计算使用固定配置或常量值，并保存为 安全策略的 SHA-256。
先尝试完成以下处理：
    调用 `load_research_policy` 读取或查询当前阶段需要的数据，并把结果记为 安全策略；读取安全策略的 SHA-256，并保存为 安全策略的 SHA-256。
如果出现 `Exception`：
    把新的处理结果追加或合并到诊断问题集合。
计算使用固定配置或常量值，并保存为 当前处理结果。
先尝试完成以下处理：
    构造 `SqliteResearchRepository` 结构化领域对象，并把结果记为 持久化仓库；调用 `initialize` 完成该函数的一项辅助处理；调用 `ping` 完成该函数的一项辅助处理；计算使用固定配置或常量值，并保存为 当前处理结果。
如果出现 `Exception`：
    把新的处理结果追加或合并到诊断问题集合。
计算使用固定配置或常量值，并保存为 凭据。
先尝试完成以下处理：
    调用 `next` 完成该函数的一项辅助处理，并把结果记为 元数据；计算计算当前表达式的结果，并保存为 凭据。
    如果凭据为空或为假，就把新的处理结果追加或合并到诊断问题集合。
如果出现 `Exception`：
    把新的处理结果追加或合并到诊断问题集合。
如果当前处理结果等于'application_only'，就把新的处理结果追加或合并到诊断问题集合。
检查由诊断问题集合组成的集合或迭代器中是否存在满足“当前处理项属于{'research_policy_invalid', 'research_database_unavailable', 'research_search_secret_use_invalid', 'research_search_secret_missing'}”的项，并把结果记为 失败；计算根据条件从两个候选结果中选择一个，并保存为 当前状态；构造并返回 `ResearchHealthReport` 结构化领域对象。
```

### `app/research_browser/extractors.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_SemanticHtmlParser.__init__`

- **源码**：`app/research_browser/extractors.py:50`
- **签名**：`def __init__(self, *, max_blocks: int) -> None`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收最大论文原文块集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `max_blocks` | `int` | 名为 `max_blocks` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `__init__` 完成该函数的一项辅助处理；把传入的 最大论文原文块集合 分别保存到同名实例字段；计算使用固定配置或常量值，并保存为 深度；计算使用固定配置或常量值，并保存为 当前处理结果。
将 当前处理结果的文本、当前处理结果的路径、数据库记录行集合 初始化为空列表，用来收集后续结果。
```

#### `_SemanticHtmlParser.handle_starttag`

- **源码**：`app/research_browser/extractors.py:59`
- **签名**：`def handle_starttag(self, tag: str, attrs) -> None`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前处理结果、当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `tag` | `str` | 名为 `tag` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `attrs` | `未显式标注` | 名为 `attrs` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
对当前处理结果中的文本执行规范化或拆分，并把结果记为 转为小写的比较文本；遍历并筛选输入，将整理后的结果保存为 对象属性集合；计算计算当前表达式的结果，并保存为 当前处理结果。
如果深度有值或为真，就将新的计算结果累加或合并到深度；结束当前函数，不返回业务值。
如果转为小写的比较文本属于当前处理结果 或 当前处理结果有值或为真，就计算使用固定配置或常量值，并保存为 深度；结束当前函数，不返回业务值。
如果转为小写的比较文本属于原文块集合，就调用 `_flush` 完成该函数的一项辅助处理；把传入参数保存到实例字段（转为小写的比较文本 → 当前处理结果）。
```

#### `_SemanticHtmlParser.handle_endtag`

- **源码**：`app/research_browser/extractors.py:77`
- **签名**：`def handle_endtag(self, tag: str) -> None`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `tag` | `str` | 名为 `tag` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
如果深度有值或为真，就将新的计算结果累加或合并到深度；结束当前函数，不返回业务值。
如果当前处理结果等于辅助操作“对当前处理结果中的文本执行规范化或拆分”的结果，就调用 `_flush` 完成该函数的一项辅助处理。
```

#### `_SemanticHtmlParser.handle_data`

- **源码**：`app/research_browser/extractors.py:84`
- **签名**：`def handle_data(self, data: str) -> None`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收待处理数据，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `data` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
如果“深度有值或为真”不成立 且 当前处理结果不为空，就把待处理数据追加或合并到当前处理结果的文本。
```

#### `_SemanticHtmlParser.close`

- **源码**：`app/research_browser/extractors.py:88`
- **签名**：`def close(self) -> None`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
关闭辅助操作“调用 `super` 完成该函数的一项辅助处理”的结果并释放相关资源；调用 `_flush` 完成该函数的一项辅助处理。
```

#### `_SemanticHtmlParser._flush`

- **源码**：`app/research_browser/extractors.py:92`
- **签名**：`def _flush(self) -> None`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
如果当前处理结果为空，就将 当前处理结果的文本 初始化为空列表，用来收集后续结果；结束当前函数，不返回业务值。
调用 `join` 完成该函数的一项辅助处理，并把结果记为 待处理文本；读取当前处理结果，并保存为 后续步骤使用的结果；计算使用固定配置或常量值，并保存为 当前处理结果；将 当前处理结果的文本 初始化为空列表，用来收集后续结果。
如果待处理文本 的长度小于2 或 数据库记录行集合 的长度不小于最大论文原文块集合，就结束当前函数，不返回业务值。
读取待处理文本中的对应字段，并保存为 待处理文本。
如果“检查当前处理结果是否满足文本匹配条件”后得到肯定结果 且 当前处理结果 的长度等于2 且 “调用 `isdigit` 完成该函数的一项辅助处理”后得到肯定结果，就调用 `int` 完成该函数的一项辅助处理，并把结果记为 等级；读取当前处理结果的路径中的对应字段，并保存为 当前处理结果的路径；把待处理文本中的对应字段追加或合并到当前处理结果的路径。
把新的处理结果追加或合并到数据库记录行集合。
```

#### `_materialize_blocks`

- **源码**：`app/research_browser/extractors.py:110`
- **签名**：`def _materialize_blocks(rows: list[tuple[str, str, list[str]]], locator_prefix: str) -> list[ExtractedBlock]`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收数据库记录行集合、当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `rows` | `list[tuple[str, str, list[str]]]` | 数据库记录行集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `locator_prefix` | `str` | 名为 `locator_prefix` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`list[ExtractedBlock]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
将 论文原文块集合 初始化为空列表，用来收集后续结果。
遍历带顺序编号的输入集合，每次把当前项记为多个解包结果，然后计算根据字段和固定文本生成格式化文本，并保存为 源码或文档定位信息；调用 `sha256_text` 计算内容身份、分数或派生结果，并把结果记为 待处理文本的 Hash；把新的处理结果追加或合并到论文原文块集合。
返回论文原文块集合的当前值。
```

#### `extract_html`

- **源码**：`app/research_browser/extractors.py:135`
- **签名**：`def extract_html(body: bytes, *, max_blocks: int) -> ExtractionResult`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收请求正文、最大论文原文块集合，用于读取并整理论文、源码或运行产物，把原始输入转换成带位置和身份信息的结构化证据，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `body` | `bytes` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `max_blocks` | `int` | 名为 `max_blocks` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`ExtractionResult`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
将外部表示解析为结构化内容，并把结果记为 待处理文本；调用 `_SemanticHtmlParser` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
先尝试完成以下处理：
    调用 `feed` 完成该函数的一项辅助处理；关闭当前处理结果并释放相关资源。
如果出现 `Exception`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `ResearchContentRejected`，向调用方报告输入或运行失败。
调用 `_materialize_blocks` 完成该函数的一项辅助处理，并把结果记为 论文原文块集合。
如果论文原文块集合为空或为假，就拒绝继续处理并抛出 `ResearchContentRejected`，向调用方报告输入或运行失败。
调用 `next` 完成该函数的一项辅助处理，并把结果记为 文档或章节标题；调用 `join` 完成该函数的一项辅助处理，并把结果记为 规范化后的文本；构造并返回 `ExtractionResult` 结构化领域对象。
```

#### `extract_plain_text`

- **源码**：`app/research_browser/extractors.py:152`
- **签名**：`def extract_plain_text(body: bytes, *, max_blocks: int) -> ExtractionResult`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收请求正文、最大论文原文块集合，用于读取并整理论文、源码或运行产物，把原始输入转换成带位置和身份信息的结构化证据，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `body` | `bytes` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `max_blocks` | `int` | 名为 `max_blocks` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`ExtractionResult`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `replace` 完成该函数的一项辅助处理，并把结果记为 待处理文本；遍历并筛选输入，将整理后的结果保存为 当前处理结果；读取当前输入内容中的对应字段，并保存为 数据库记录行集合；调用 `_materialize_blocks` 完成该函数的一项辅助处理，并把结果记为 论文原文块集合。
如果论文原文块集合为空或为假，就拒绝继续处理并抛出 `ResearchContentRejected`，向调用方报告输入或运行失败。
调用 `join` 完成该函数的一项辅助处理，并把结果记为 规范化后的文本；构造并返回 `ExtractionResult` 结构化领域对象。
```

#### `extract_pdf`

- **源码**：`app/research_browser/extractors.py:167`
- **签名**：`def extract_pdf(body: bytes, max_pages: int, max_blocks: int) -> ExtractionResult`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收请求正文、最大当前处理结果、最大论文原文块集合，用于读取并整理论文、源码或运行产物，把原始输入转换成带位置和身份信息的结构化证据，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `body` | `bytes` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `max_pages` | `int` | 名为 `max_pages` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `max_blocks` | `int` | 名为 `max_blocks` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`ExtractionResult`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
加载这一步需要的外部依赖。
先尝试完成以下处理：
    调用 `open` 完成该函数的一项辅助处理，并把结果记为 论文解析文档。
如果出现 `Exception`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `ResearchContentRejected`，向调用方报告输入或运行失败。
先尝试完成以下处理：
    如果论文页码的数量小于1，就拒绝继续处理并抛出 `ResearchContentRejected`，向调用方报告输入或运行失败。
    将 数据库记录行集合 初始化为空列表，用来收集后续结果。
    遍历限定范围内的序列，每次把当前项记为论文页码的索引：
        调用 `load_page` 读取或查询当前阶段需要的数据，并把结果记为 论文页码；调用 `join` 完成该函数的一项辅助处理，并把结果记为 待处理文本。
        如果待处理文本有值或为真，就把新的处理结果追加或合并到数据库记录行集合。
        如果数据库记录行集合 的长度不小于最大论文原文块集合，就立即结束当前循环。
    调用 `_materialize_blocks` 完成该函数的一项辅助处理，并把结果记为 论文原文块集合。
    如果论文原文块集合为空或为假，就拒绝继续处理并抛出 `ResearchContentRejected`，向调用方报告输入或运行失败。
    去除辅助操作“调用 `str` 完成该函数的一项辅助处理”的结果的首尾空白，并把规范化后的文本记为 元数据；调用 `join` 完成该函数的一项辅助处理，并把结果记为 规范化后的文本；构造并返回 `ExtractionResult` 结构化领域对象。
无论成功还是失败，最后都要：
    关闭论文解析文档并释放相关资源。
```

#### `extract_document`

- **源码**：`app/research_browser/extractors.py:205`
- **签名**：`def extract_document(media_type: str, body: bytes, max_pages: int, max_blocks: int) -> ExtractionResult`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收Artifact 媒体类型、请求正文、最大当前处理结果、最大论文原文块集合，用于读取并整理论文、源码或运行产物，把原始输入转换成带位置和身份信息的结构化证据，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `media_type` | `str` | Artifact 媒体类型；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `body` | `bytes` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `max_pages` | `int` | 名为 `max_pages` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `max_blocks` | `int` | 名为 `max_blocks` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`ExtractionResult`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
如果Artifact 媒体类型等于'text/html'，就调用 `extract_html` 完成该函数的一项辅助处理，并返回处理结果。
如果Artifact 媒体类型等于'text/plain'，就调用 `extract_plain_text` 完成该函数的一项辅助处理，并返回处理结果。
如果Artifact 媒体类型等于'application/pdf'，就调用 `extract_pdf` 完成该函数的一项辅助处理，并返回处理结果。
拒绝继续处理并抛出 `ResearchContentRejected`，向调用方报告输入或运行失败。
```

### `app/research_browser/factory.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `build_research_browser_service`

- **源码**：`app/research_browser/factory.py:25`
- **签名**：`def build_research_browser_service(model_gateway: ModelGateway | None, resource_service: ResourceService | None, secret_service: SecretService | None) -> ResearchBrowserService`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收网关、资源、凭据，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `ResearchBrowserService` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `model_gateway` | `ModelGateway | None` | 名为 `model_gateway` 的 `ModelGateway | None` 领域输入；用于当前函数的业务处理，具体约束见校验分支。；默认 空值 |
| `resource_service` | `ResourceService | None` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。；默认 空值 |
| `secret_service` | `SecretService | None` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。；默认 空值 |

**输出**

- **Python 类型**：`ResearchBrowserService`
- **语义**：返回 `ResearchBrowserService` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果“当前处理结果有值或为真”不成立，就拒绝继续处理并抛出 `RuntimeError`，向调用方报告输入或运行失败。
调用 `load_research_policy` 读取或查询当前阶段需要的数据，并把结果记为 安全策略。
如果模型服务商绑定不等于'brave_search'，就拒绝继续处理并抛出 `RuntimeError`，向调用方报告输入或运行失败。
计算计算当前表达式的结果，并保存为 当前处理结果；调用 `build_redactor` 组装当前阶段需要的领域对象，并把结果记为 敏感信息脱敏器；构造 `BraveSearchProvider` 结构化领域对象，并把结果记为 该调用返回的结果；构造 `HttpxResearchTransport` 结构化领域对象，并把结果记为 外部资源传输端口。
构造 `RobotsPolicy` 结构化领域对象，并把结果记为 该调用返回的结果；构造 `BoundedResearchFetcher` 结构化领域对象，并把结果记为 该调用返回的结果；构造 `ResearchCollector` 结构化领域对象，并把结果记为 该调用返回的结果；调用 `build_tool_registry` 组装当前阶段需要的领域对象，并把结果记为 受控工具定义集合。
调用 `build_skill_registry` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果；构造 `SqliteResearchRepository` 结构化领域对象，并把结果记为 持久化仓库；构造 `ResearchSynthesizer` 结构化领域对象，并把结果记为 该调用返回的结果；构造并返回 `ResearchBrowserService` 结构化领域对象。
```

### `app/research_browser/fetcher.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `ResearchHttpResponse.iter_bytes`

- **源码**：`app/research_browser/fetcher.py:48`
- **签名**：`def iter_bytes(self, *, chunk_size: int) -> Iterator[bytes]`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收文本块，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `Iterator[bytes]` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `chunk_size` | `int` | 名为 `chunk_size` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`Iterator[bytes]`
- **语义**：返回惰性迭代结果，调用方逐项消费。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `ResearchHttpTransport.stream`

- **源码**：`app/research_browser/fetcher.py:53`
- **签名**：`def stream(self: 未显式标注, method: str, url: str) -> AbstractContextManager[ResearchHttpResponse]`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收论文方法或 HTTP 方法、外部论文、仓库或服务地址，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `method` | `str` | 论文方法或 HTTP 方法；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `url` | `str` | 资源地址；进入网络或持久化前仍需策略校验和必要的脱敏。 |

**输出**

- **Python 类型**：`AbstractContextManager[ResearchHttpResponse]`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `HttpxResearchTransport.__init__`

- **源码**：`app/research_browser/fetcher.py:62`
- **签名**：`def __init__(self, *, policy: ResearchPolicyDocument, client: Any | None = None)`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收安全策略、外部服务客户端，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `policy` | `ResearchPolicyDocument` | 安全策略；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `client` | `Any | None` | 外部服务客户端；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 空值 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算计算当前表达式的结果，并保存为 当前处理结果。
如果外部服务客户端不为空，就把传入参数保存到实例字段（外部服务客户端 → 外部服务客户端）；结束当前函数，不返回业务值。
加载这一步需要的外部依赖；构造 `Client` 结构化领域对象，并把结果记为 外部服务客户端。
```

#### `HttpxResearchTransport.stream`

- **源码**：`app/research_browser/fetcher.py:86`
- **签名**：`def stream(self, method: str, url: str) -> Iterator[ResearchHttpResponse]`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收论文方法或 HTTP 方法、外部论文、仓库或服务地址，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `method` | `str` | 论文方法或 HTTP 方法；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `url` | `str` | 资源地址；进入网络或持久化前仍需策略校验和必要的脱敏。 |

**输出**

- **Python 类型**：`Iterator[ResearchHttpResponse]`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `clear` 完成该函数的一项辅助处理。
先尝试完成以下处理：
    在上下文“调用 `stream` 完成该函数的一项辅助处理，并把上下文资源交给结构化响应”中完成当前表达式对应的校验或状态操作，退出时自动清理资源。
无论成功还是失败，最后都要：
    调用 `clear` 完成该函数的一项辅助处理。
```

#### `HttpxResearchTransport.close`

- **源码**：`app/research_browser/fetcher.py:95`
- **签名**：`def close(self) -> None`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
如果当前处理结果有值或为真，就关闭外部服务客户端并释放相关资源。
```

#### `validate_research_target`

- **源码**：`app/research_browser/fetcher.py:100`
- **签名**：`def validate_research_target(raw_url: str, allowed_hosts: tuple[str, ...], resolver: 未显式标注) -> ValidatedResearchTarget`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收未经校验的外部资源地址、允许访问的主机集合、路径、配置或依赖解析器，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `ValidatedResearchTarget` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `raw_url` | `str` | 资源地址；进入网络或持久化前仍需策略校验和必要的脱敏。 |
| `allowed_hosts` | `tuple[str, ...]` | 允许访问的主机集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `resolver` | `未显式标注` | 路径、配置或依赖解析器；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 resolve_public_ips |

**输出**

- **Python 类型**：`ValidatedResearchTarget`
- **语义**：返回 `ValidatedResearchTarget` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `canonicalize_research_url` 完成该函数的一项辅助处理，并把结果记为 规范化；对当前输入内容中的文本执行规范化或拆分，并把结果记为 服务监听地址。
如果“调用 `host_matches` 完成该函数的一项辅助处理”后未得到肯定结果，就拒绝继续处理并抛出 `ResearchUrlRejected`，向调用方报告输入或运行失败。
如果“调用 `isdigit` 完成该函数的一项辅助处理”后得到肯定结果 或 当前输入内容属于服务监听地址，就拒绝继续处理并抛出 `ResearchUrlRejected`，向调用方报告输入或运行失败。
先尝试完成以下处理：
    调用 `resolver` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `validate_public_ips` 校验当前输入或状态，并把结果记为 该调用返回的结果。
如果出现 `Exception`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `ResearchUrlRejected`，向调用方报告输入或运行失败。
构造并返回 `ValidatedResearchTarget` 结构化领域对象。
```

#### `RobotsPolicy.__init__`

- **源码**：`app/research_browser/fetcher.py:124`
- **签名**：`def __init__(self: 未显式标注, policy: ResearchPolicyDocument, transport: ResearchHttpTransport, resolver: 未显式标注) -> None`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收安全策略、外部资源传输端口、路径、配置或依赖解析器，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `policy` | `ResearchPolicyDocument` | 安全策略；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `transport` | `ResearchHttpTransport` | 外部资源传输端口；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `resolver` | `未显式标注` | 路径、配置或依赖解析器；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 resolve_public_ips |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 安全策略、外部资源传输端口、路径、配置或依赖解析器 分别保存到同名实例字段；将 当前处理结果 初始化为空映射，用来收集后续结果。
```

#### `RobotsPolicy.check`

- **源码**：`app/research_browser/fetcher.py:136`
- **签名**：`def check(self, target: ValidatedResearchTarget) -> str`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收待定位的代码对象或业务目标，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `target` | `ValidatedResearchTarget` | 待定位的代码对象或业务目标；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
从当前处理结果读取所需的状态或领域记录，并把结果记为 该调用返回的结果。
如果当前处理结果不为空 且 当前输入内容小于3600：
    读取当前处理结果中的对应字段，并保存为 后续步骤使用的结果。
否则：
    调用 `urlunsplit` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `validate_research_target` 校验当前输入或状态。
    进入上下文“调用 `stream` 完成该函数的一项辅助处理，并把上下文资源交给结构化响应”，退出时自动清理资源：
        如果状态等于404：
            计算使用固定配置或常量值，并保存为 当前处理结果。
        否则：
            如果状态不等于200：
                拒绝继续处理并抛出 `ResearchTransportUnavailable`，向调用方报告输入或运行失败。
            否则：
                调用 `bytearray` 完成该函数的一项辅助处理，并把结果记为 原始内容。
                遍历辅助操作产生的可迭代结果（调用 `iter_bytes` 完成该函数的一项辅助处理），每次把当前项记为检索文本块：
                    把检索文本块追加或合并到原始内容。
                    如果原始内容 的长度大于256 × 1024，就拒绝继续处理并抛出 `ResearchLimitExceeded`，向调用方报告输入或运行失败。
                构造 `RobotFileParser` 结构化领域对象，并把结果记为 该调用返回的结果；调用 `set_url` 完成该函数的一项辅助处理；调用 `parse` 完成该函数的一项辅助处理。
    计算组合多个值形成元组，并保存为 当前处理结果中的对应字段。
如果当前处理结果为空，就返回固定值 `'not_present'`。
如果“调用 `can_fetch` 完成该函数的一项辅助处理”后未得到肯定结果，就拒绝继续处理并抛出 `ResearchRobotsDenied`，向调用方报告输入或运行失败。
返回固定值 `'allowed'`。
```

#### `HostRateLimiter.__init__`

- **源码**：`app/research_browser/fetcher.py:171`
- **签名**：`def __init__(self, minimum_interval_seconds: float) -> None`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `minimum_interval_seconds` | `float` | 名为 `minimum_interval_seconds` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 当前处理结果 分别保存到同名实例字段；将 当前处理结果 初始化为空映射，用来收集后续结果。
```

#### `HostRateLimiter.wait`

- **源码**：`app/research_browser/fetcher.py:175`
- **签名**：`def wait(self, host: str) -> None`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收服务监听地址，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `host` | `str` | 服务监听地址或端口；用于绑定本地/网络服务，并受运行环境策略限制。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
从当前处理结果读取所需的状态或领域记录，并把结果记为 前一项。
如果前一项不为空：
    计算组合或计算已有值，并保存为 当前处理结果。
    如果当前处理结果大于0，就调用 `sleep` 完成该函数的一项辅助处理。
调用 `monotonic` 完成该函数的一项辅助处理，并把结果记为 当前处理结果中的对应字段。
```

#### `BoundedResearchFetcher.__init__`

- **源码**：`app/research_browser/fetcher.py:185`
- **签名**：`def __init__(self: 未显式标注, policy: ResearchPolicyDocument, allowed_hosts: tuple[str, ...], transport: ResearchHttpTransport, robots: RobotsPolicy, resolver: 未显式标注) -> None`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收安全策略、允许访问的主机集合、外部资源传输端口、当前处理结果等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `policy` | `ResearchPolicyDocument` | 安全策略；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `allowed_hosts` | `tuple[str, ...]` | 允许访问的主机集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `transport` | `ResearchHttpTransport` | 外部资源传输端口；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `robots` | `RobotsPolicy` | 名为 `robots` 的 `RobotsPolicy` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `resolver` | `未显式标注` | 路径、配置或依赖解析器；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 resolve_public_ips |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 安全策略、允许访问的主机集合、外部资源传输端口、当前处理结果、路径、配置或依赖解析器 分别保存到同名实例字段；构造 `HostRateLimiter` 结构化领域对象，并把结果记为 比例。
```

#### `BoundedResearchFetcher.fetch`

- **源码**：`app/research_browser/fetcher.py:201`
- **签名**：`def fetch(self, url: str) -> FetchedDocument`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收外部论文、仓库或服务地址，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `FetchedDocument` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `url` | `str` | 资源地址；进入网络或持久化前仍需策略校验和必要的脱敏。 |

**输出**

- **Python 类型**：`FetchedDocument`
- **语义**：返回 `FetchedDocument` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `monotonic` 完成该函数的一项辅助处理，并把结果记为 运行是否已经启动的判断；读取外部论文、仓库或服务地址，并保存为 当前值；将 当前处理结果 初始化为空列表，用来收集后续结果。
遍历限定范围内的序列，每次把当前项记为当前处理结果的索引：
    如果当前输入内容大于当前处理结果，就拒绝继续处理并抛出 `ResearchLimitExceeded`，向调用方报告输入或运行失败。
    调用 `validate_research_target` 校验当前输入或状态，并把结果记为 待定位的代码对象或业务目标；把规范化追加或合并到当前处理结果；调用 `check` 完成该函数的一项辅助处理，并把结果记为 状态；调用 `wait` 完成该函数的一项辅助处理。
    先尝试完成以下处理：
        调用 `stream` 完成该函数的一项辅助处理，并把结果记为 运行上下文。
        进入上下文“读取运行上下文的当前值，并把上下文资源交给结构化响应”，退出时自动清理资源：
            如果状态属于{301, 302, 303, 307, 308}：
                从当前处理结果读取所需的状态或领域记录，并把结果记为 该调用返回的结果。
                如果当前处理结果为空或为假，就拒绝继续处理并抛出 `ResearchTransportUnavailable`，向调用方报告输入或运行失败。
                如果当前处理结果的索引不小于最大当前处理结果，就拒绝继续处理并抛出 `ResearchLimitExceeded`，向调用方报告输入或运行失败。
                调用 `urljoin` 完成该函数的一项辅助处理，并把结果记为 当前值；跳过本轮剩余处理，直接进入下一轮。
            如果状态属于{429, 500, 502, 503, 504}，就拒绝继续处理并抛出 `ResearchTransportUnavailable`，向调用方报告输入或运行失败。
            如果状态不等于200，就拒绝继续处理并抛出 `ResearchContentRejected`，向调用方报告输入或运行失败。
            从当前处理结果读取所需的状态或领域记录，并把结果记为 该调用返回的结果。
            如果当前处理结果不为空：
                先尝试完成以下处理：
                    调用 `int` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
                如果出现 `ValueError`并把异常保存为捕获的异常对象：
                    拒绝继续处理并抛出 `ResearchContentRejected`，向调用方报告输入或运行失败。
                如果当前处理结果大于最大结构化响应的字节内容，就拒绝继续处理并抛出 `ResearchLimitExceeded`，向调用方报告输入或运行失败。
            调用 `str` 完成该函数的一项辅助处理，并把结果记为 Artifact 媒体类型；对前一步操作返回对象中的对应字段中的文本执行规范化或拆分，再对返回文本执行规范化或拆分，并把结果记为 Artifact 媒体类型。
            如果Artifact 媒体类型不属于媒体集合，就拒绝继续处理并抛出 `ResearchContentRejected`，向调用方报告输入或运行失败。
            调用 `bytearray` 完成该函数的一项辅助处理，并把结果记为 请求正文。
            遍历辅助操作产生的可迭代结果（调用 `iter_bytes` 完成该函数的一项辅助处理），每次把当前项记为检索文本块：
                如果当前输入内容大于当前处理结果，就拒绝继续处理并抛出 `ResearchLimitExceeded`，向调用方报告输入或运行失败。
                把检索文本块追加或合并到请求正文。
                如果请求正文 的长度大于最大结构化响应的字节内容，就拒绝继续处理并抛出 `ResearchLimitExceeded`，向调用方报告输入或运行失败。
            调用 `bytes` 完成该函数的一项辅助处理，并把结果记为 结构化请求载荷。
            如果Artifact 媒体类型等于'application/pdf' 且 “检查结构化请求载荷是否满足文本匹配条件”后未得到肯定结果，就拒绝继续处理并抛出 `ResearchContentRejected`，向调用方报告输入或运行失败。
            如果“检查Artifact 媒体类型是否满足文本匹配条件”后得到肯定结果 且 当前输入内容属于结构化请求载荷中的对应字段，就拒绝继续处理并抛出 `ResearchContentRejected`，向调用方报告输入或运行失败。
            构造并返回 `FetchedDocument` 结构化领域对象。
    如果出现 `(ResearchLimitExceeded, ResearchContentRejected, ResearchTransportUnavailable)`：
        重新抛出当前异常，保持原始失败信息。
    如果出现 `Exception`并把异常保存为捕获的异常对象：
        拒绝继续处理并抛出 `ResearchTransportUnavailable`，向调用方报告输入或运行失败。
拒绝继续处理并抛出 `ResearchLimitExceeded`，向调用方报告输入或运行失败。
```

### `app/research_browser/identity.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `canonical_json`

- **源码**：`app/research_browser/identity.py:47`
- **签名**：`def canonical_json(value: Any) -> str`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `Any` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
如果“计算数量、边界或类型判断结果”后得到肯定结果，就复制、序列化或校验结构化领域对象，并把结果记为 当前字段值。
将结构化内容序列化或编码为可传输表示，并返回处理结果。
```

#### `sha256_text`

- **源码**：`app/research_browser/identity.py:59`
- **签名**：`def sha256_text(value: str) -> str`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回输入内容的 SHA-256 身份摘要，用于完整性校验，不是加密后的正文。

**伪代码**

```text
计算输入内容的 SHA-256 身份摘要，并返回处理结果。
```

#### `sha256_bytes`

- **源码**：`app/research_browser/identity.py:63`
- **签名**：`def sha256_bytes(value: bytes) -> str`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `bytes` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回输入内容的 SHA-256 身份摘要，用于完整性校验，不是加密后的正文。

**伪代码**

```text
计算输入内容的 SHA-256 身份摘要，并返回处理结果。
```

#### `sha256_value`

- **源码**：`app/research_browser/identity.py:67`
- **签名**：`def sha256_value(value: Any) -> str`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `Any` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回输入内容的 SHA-256 身份摘要，用于完整性校验，不是加密后的正文。

**伪代码**

```text
调用 `sha256_text` 计算内容身份、分数或派生结果，并返回处理结果。
```

#### `stable_id`

- **源码**：`app/research_browser/identity.py:71`
- **签名**：`def stable_id(prefix: str, value: Any) -> str`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收目录树缩进前缀、当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `prefix` | `str` | 目录树展示用的缩进前缀；只影响输出排版，不改变仓库路径。 |
| `value` | `Any` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回稳定业务标识符，用于后续查询、关联或幂等绑定；它不是路径或内容 Hash。

**伪代码**

```text
返回当前计算得到的结果。
```

#### `canonicalize_research_url`

- **源码**：`app/research_browser/identity.py:75`
- **签名**：`def canonicalize_research_url(raw_url: str) -> str`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，生成可持久化 URL；任何可能携带凭据的形状都 fail closed。该函数接收未经校验的外部资源地址，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `raw_url` | `str` | 资源地址；进入网络或持久化前仍需策略校验和必要的脱敏。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
去除未经校验的外部资源地址的首尾空白，并把规范化后的文本记为 原始内容。
如果原始内容 的长度大于2048 或 当前输入内容属于原始内容 或 由原始内容组成的集合或迭代器中存在满足“当前字符 对应的 ASCII/Unicode 编码小于32 或 当前字符 对应的 ASCII/Unicode 编码等于127”的项，就拒绝继续处理并抛出 `ResearchUrlRejected`，向调用方报告输入或运行失败。
先尝试完成以下处理：
    调用 `urlsplit` 完成该函数的一项辅助处理，并把结果记为 解析后的结果；读取服务监听端口，并保存为 服务监听端口。
如果出现 `ValueError`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `ResearchUrlRejected`，向调用方报告输入或运行失败。
如果辅助操作“对当前处理结果中的文本执行规范化或拆分”的结果不等于'https'，就拒绝继续处理并抛出 `ResearchUrlRejected`，向调用方报告输入或运行失败。
如果当前处理结果不为空 或 当前处理结果不为空，就拒绝继续处理并抛出 `ResearchUrlRejected`，向调用方报告输入或运行失败。
如果“当前处理结果有值或为真”不成立，就拒绝继续处理并抛出 `ResearchUrlRejected`，向调用方报告输入或运行失败。
如果服务监听端口不属于{空值, 443}，就拒绝继续处理并抛出 `ResearchUrlRejected`，向调用方报告输入或运行失败。
先尝试完成以下处理：
    将外部表示解析为结构化内容，再对返回文本执行规范化或拆分，并把结果记为 服务监听地址。
如果出现 `UnicodeError`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `ResearchUrlRejected`，向调用方报告输入或运行失败。
调用 `parse_qsl` 解析、规范化或转换当前输入，并把结果记为 该调用返回的结果；将 查询 初始化为空列表，用来收集后续结果。
遍历由当前处理结果组成的集合或迭代器，每次把当前项记为多个解包结果：
    对映射键或对象字段名中的文本执行规范化或拆分，再对返回文本执行规范化或拆分，并把结果记为 转为小写的比较文本。
    如果当前可迭代输入中存在满足“当前字符 对应的 ASCII/Unicode 编码小于32 或 当前字符 对应的 ASCII/Unicode 编码等于127”的项，就拒绝继续处理并抛出 `ResearchUrlRejected`，向调用方报告输入或运行失败。
    如果“检查转为小写的比较文本是否满足文本匹配条件”后得到肯定结果 或 转为小写的比较文本属于查询键集合集合，就跳过本轮剩余处理，直接进入下一轮。
    如果转为小写的比较文本属于查询键集合集合 或 当前可迭代输入中存在满足“测试或状态标记属于转为小写的比较文本”的项，就拒绝继续处理并抛出 `ResearchUrlRejected`，向调用方报告输入或运行失败。
    如果映射键或对象字段名 的长度大于80 或 当前字段值 的长度大于300，就拒绝继续处理并抛出 `ResearchUrlRejected`，向调用方报告输入或运行失败。
    把新的处理结果追加或合并到查询。
按稳定规则整理结果顺序；调用 `quote` 完成该函数的一项辅助处理，并把结果记为 文件或目录路径；调用 `urlencode` 完成该函数的一项辅助处理，并把结果记为 语义检索问题；调用 `urlunsplit` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `host_matches`

- **源码**：`app/research_browser/identity.py:133`
- **签名**：`def host_matches(host: str, allowed_hosts: tuple[str, ...]) -> bool`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收服务监听地址、允许访问的主机集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `host` | `str` | 服务监听地址或端口；用于绑定本地/网络服务，并受运行环境策略限制。 |
| `allowed_hosts` | `tuple[str, ...]` | 允许访问的主机集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
调用 `rstrip` 完成该函数的一项辅助处理，再对返回文本执行规范化或拆分，并把结果记为 规范化后的文本；检查由允许访问的主机集合组成的集合或迭代器中是否存在满足“规范化后的文本等于当前处理结果 或 “检查规范化后的文本是否满足文本匹配条件”后得到肯定结果”的项，并返回处理结果。
```

#### `safe_search_text`

- **源码**：`app/research_browser/identity.py:141`
- **签名**：`def safe_search_text(value: str, *, max_chars: int) -> str`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前字段值、最大字符数，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |
| `max_chars` | `int` | 名为 `max_chars` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
如果由当前字段值组成的集合或迭代器中存在满足“当前字符 对应的 ASCII/Unicode 编码小于32 或 当前字符 对应的 ASCII/Unicode 编码等于127”的项，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
调用 `join` 完成该函数的一项辅助处理，并把结果记为 规范化后的文本。
如果规范化后的文本为空或为假 或 规范化后的文本 的长度大于最大字符数，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回规范化后的文本的当前值。
```

#### `request_sha256`

- **源码**：`app/research_browser/identity.py:153`
- **签名**：`def request_sha256(request: BaseModel) -> str`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收业务请求，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `BaseModel` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回输入内容的 SHA-256 身份摘要，用于完整性校验，不是加密后的正文。

**伪代码**

```text
复制、序列化或校验结构化领域对象，并把结果记为 结构化请求载荷；按稳定规则整理结果顺序，并把结果记为 结构化请求载荷中的对应字段；调用 `sha256_value` 计算内容身份、分数或派生结果，并返回处理结果。
```

#### `without_hash`

- **源码**：`app/research_browser/identity.py:159`
- **签名**：`def without_hash(value: BaseModel, field_name: str) -> dict[str, Any]`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前字段值、结构化对象字段的名称，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `BaseModel` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |
| `field_name` | `str` | 名为 `field_name` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`dict[str, Any]`
- **语义**：返回内容身份摘要，通常为 SHA-256 十六进制字符串。

**伪代码**

```text
复制、序列化或校验结构化领域对象，并把结果记为 结构化请求载荷；从结构化请求载荷取出并移除最后一项；返回结构化请求载荷的当前值。
```

### `app/research_browser/repository.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `utc_now`

- **源码**：`app/research_browser/repository.py:24`
- **签名**：`def utc_now() -> datetime`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `datetime` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`datetime`
- **语义**：返回 `datetime` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
读取当前时间，作为状态变更的统一时间戳，并返回处理结果。
```

#### `iso`

- **源码**：`app/research_browser/repository.py:28`
- **签名**：`def iso(value: datetime) -> str`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `datetime` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `isoformat` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `SqliteResearchRepository.__init__`

- **源码**：`app/research_browser/repository.py:33`
- **签名**：`def __init__(self, path: Path) -> None`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收文件或目录路径，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 文件或目录路径 分别保存到同名实例字段。
```

#### `SqliteResearchRepository._connect`

- **源码**：`app/research_browser/repository.py:36`
- **签名**：`def _connect(self) -> sqlite3.Connection`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于在固定 MCP Policy、Schema Pin、调用预算和只读职责边界内连接或调用外部能力，并把返回内容转换为可追溯的复现证据，最终标注为 `sqlite3.Connection` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`sqlite3.Connection`
- **语义**：返回 `sqlite3.Connection` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `connect` 完成该函数的一项辅助处理，并把结果记为 数据库连接；读取数据库记录行，并保存为 记录行；通过数据库连接执行数据查询或命令；通过数据库连接执行数据查询或命令。
通过数据库连接执行数据查询或命令；返回数据库连接的当前值。
```

#### `SqliteResearchRepository._write`

- **源码**：`app/research_browser/repository.py:45`
- **签名**：`def _write(self) -> Iterator[sqlite3.Connection]`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `Iterator[sqlite3.Connection]` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`Iterator[sqlite3.Connection]`
- **语义**：返回惰性迭代结果，调用方逐项消费。

**伪代码**

```text
调用 `_connect` 完成该函数的一项辅助处理，并把结果记为 数据库连接。
先尝试完成以下处理：
    通过数据库连接执行数据查询或命令；完成当前表达式对应的校验或状态操作；提交数据库连接中已完成的数据变更。
如果出现 `Exception`：
    回滚数据库连接中未完成的数据变更；重新抛出当前异常，保持原始失败信息。
无论成功还是失败，最后都要：
    关闭数据库连接并释放相关资源。
```

#### `SqliteResearchRepository.initialize`

- **源码**：`app/research_browser/repository.py:57`
- **签名**：`def initialize(self) -> None`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
创建父级目录或父领域对象对应的目录。
在上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”中调用 `executescript` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `SqliteResearchRepository.ping`

- **源码**：`app/research_browser/repository.py:117`
- **签名**：`def ping(self) -> None`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”中调用 `fetchone` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `SqliteResearchRepository._record`

- **源码**：`app/research_browser/repository.py:122`
- **签名**：`def _record(row: sqlite3.Row) -> ResearchRecord`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收数据库记录行，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `row` | `sqlite3.Row` | 数据库记录行；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`ResearchRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
构造并返回 `ResearchRecord` 结构化领域对象。
```

#### `SqliteResearchRepository._event`

- **源码**：`app/research_browser/repository.py:140`
- **签名**：`def _event(self: 未显式标注, connection: sqlite3.Connection, session_id: str, event_type: str, actor: str, payload: dict | None, created_at: str) -> None`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收数据库连接、当前处理结果的 ID、事件类型、审计主体等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `connection` | `sqlite3.Connection` | 数据库连接；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `session_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `event_type` | `str` | 名为 `event_type` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `actor` | `str` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `payload` | `dict | None` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。；默认 空值 |
| `created_at` | `str` | 时间值或可注入时钟，用于排序、过期、租约或可重复测试。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
通过数据库连接执行数据查询或命令。
```

#### `SqliteResearchRepository.submit`

- **源码**：`app/research_browser/repository.py:166`
- **签名**：`def submit(self: 未显式标注, session_id: str, idempotency_key: str, request: ResearchRequest, request_sha256: str, policy_sha256: str, actor: str) -> tuple[ResearchRecord, bool]`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前处理结果的 ID、请求幂等键、业务请求、请求内容 SHA-256等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `session_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `idempotency_key` | `str` | 调用方提供的幂等键；重复请求应复用同一结果，而不是再次产生副作用。 |
| `request` | `ResearchRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `request_sha256` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |
| `policy_sha256` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |
| `actor` | `str` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |

**输出**

- **Python 类型**：`tuple[ResearchRecord, bool]`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
调用 `iso` 完成该函数的一项辅助处理，并把结果记为 当前时间。
进入上下文“调用 `_write` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”，退出时自动清理资源：
    调用 `fetchone` 完成该函数的一项辅助处理，并把结果记为 已有记录。
    如果已有记录不为空：
        调用 `_record` 完成该函数的一项辅助处理，并把结果记为 领域记录。
        如果请求内容 SHA-256不等于请求内容 SHA-256 或 安全策略的 SHA-256不等于安全策略的 SHA-256，就拒绝继续处理并抛出 `ResearchConflict`，向调用方报告输入或运行失败。
        返回当前构造的顺序或去重集合。
    通过数据库连接执行数据查询或命令；调用 `_event` 完成该函数的一项辅助处理；调用 `fetchone` 完成该函数的一项辅助处理，并把结果记为 数据库记录行；返回当前构造的顺序或去重集合。
```

#### `SqliteResearchRepository.get`

- **源码**：`app/research_browser/repository.py:224`
- **签名**：`def get(self, session_id: str) -> ResearchRecord`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前处理结果的 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `session_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`ResearchRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
在上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”中调用 `fetchone` 完成该函数的一项辅助处理，并把结果记为 数据库记录行，退出时自动清理资源。
如果数据库记录行为空，就拒绝继续处理并抛出 `ResearchNotFound`，向调用方报告输入或运行失败。
调用 `_record` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `SqliteResearchRepository.start`

- **源码**：`app/research_browser/repository.py:234`
- **签名**：`def start(self: 未显式标注, session_id: str, expected_version: int, lease_token: str, lease_seconds: int, actor: str) -> ResearchRecord`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前处理结果的 ID、调用方看到的旧版本号、租约、租约集合等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `session_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `expected_version` | `int` | 调用方观察到的旧身份，用于 stale/CAS 校验，防止覆盖并发更新。 |
| `lease_token` | `str` | 敏感凭证或其引用；不得写入日志、Prompt 或普通 Artifact。 |
| `lease_seconds` | `int` | 名为 `lease_seconds` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `actor` | `str` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |

**输出**

- **Python 类型**：`ResearchRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
读取当前时间，作为状态变更的统一时间戳，并把结果记为 值；调用 `iso` 完成该函数的一项辅助处理，并把结果记为 当前时间；调用 `iso` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
进入上下文“调用 `_write` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”，退出时自动清理资源：
    通过数据库连接执行数据查询或命令，并把结果记为 增量读取游标。
    如果当前处理结果不等于1，就拒绝继续处理并抛出 `ResearchConflict`，向调用方报告输入或运行失败。
    调用 `_event` 完成该函数的一项辅助处理；调用 `fetchone` 完成该函数的一项辅助处理，并把结果记为 数据库记录行；调用 `_record` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `SqliteResearchRepository.complete`

- **源码**：`app/research_browser/repository.py:275`
- **签名**：`def complete(self: 未显式标注, session_id: str, lease_token: str, pack: ResearchEvidencePack, actor: str) -> ResearchRecord`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前处理结果的 ID、租约、检索或映射证据包、审计主体，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `session_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `lease_token` | `str` | 敏感凭证或其引用；不得写入日志、Prompt 或普通 Artifact。 |
| `pack` | `ResearchEvidencePack` | 检索或映射证据包；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `actor` | `str` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |

**输出**

- **Python 类型**：`ResearchRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
调用 `sha256_value` 计算内容身份、分数或派生结果，并把结果记为 期望的 Hash。
如果期望的 Hash不等于检索或映射证据包的 SHA-256，就拒绝继续处理并抛出 `ResearchIntegrityError`，向调用方报告输入或运行失败。
如果当前处理结果的 ID不等于当前处理结果的 ID，就拒绝继续处理并抛出 `ResearchIntegrityError`，向调用方报告输入或运行失败。
调用 `iso` 完成该函数的一项辅助处理，并把结果记为 当前时间。
进入上下文“调用 `_write` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”，退出时自动清理资源：
    调用 `fetchone` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
    如果当前处理结果为空，就拒绝继续处理并抛出 `ResearchConflict`，向调用方报告输入或运行失败。
    如果请求内容 SHA-256不等于当前处理结果中的对应字段，就拒绝继续处理并抛出 `ResearchIntegrityError`，向调用方报告输入或运行失败。
    如果安全策略的 SHA-256不等于当前处理结果中的对应字段，就拒绝继续处理并抛出 `ResearchIntegrityError`，向调用方报告输入或运行失败。
    通过数据库连接执行数据查询或命令；通过数据库连接执行数据查询或命令，并把结果记为 增量读取游标。
    如果当前处理结果不等于1，就拒绝继续处理并抛出 `ResearchConflict`，向调用方报告输入或运行失败。
    调用 `_event` 完成该函数的一项辅助处理；调用 `fetchone` 完成该函数的一项辅助处理，并把结果记为 数据库记录行；调用 `_record` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `SqliteResearchRepository.fail`

- **源码**：`app/research_browser/repository.py:344`
- **签名**：`def fail(self: 未显式标注, session_id: str, lease_token: str, error_code: str, retryable: bool, actor: str) -> ResearchRecord`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前处理结果的 ID、租约、错误、是否允许重试的判断等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `session_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `lease_token` | `str` | 敏感凭证或其引用；不得写入日志、Prompt 或普通 Artifact。 |
| `error_code` | `str` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |
| `retryable` | `bool` | 布尔条件或能力开关，用于控制流程分支。 |
| `actor` | `str` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |

**输出**

- **Python 类型**：`ResearchRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
计算根据条件从两个候选结果中选择一个，并保存为 当前状态；调用 `iso` 完成该函数的一项辅助处理，并把结果记为 当前时间。
进入上下文“调用 `_write` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”，退出时自动清理资源：
    通过数据库连接执行数据查询或命令，并把结果记为 增量读取游标。
    如果当前处理结果不等于1，就拒绝继续处理并抛出 `ResearchConflict`，向调用方报告输入或运行失败。
    调用 `_event` 完成该函数的一项辅助处理；调用 `fetchone` 完成该函数的一项辅助处理，并把结果记为 数据库记录行；调用 `_record` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `SqliteResearchRepository.cancel`

- **源码**：`app/research_browser/repository.py:381`
- **签名**：`def cancel(self: 未显式标注, session_id: str, expected_version: int, actor: str) -> ResearchRecord`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前处理结果的 ID、调用方看到的旧版本号、审计主体，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `session_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `expected_version` | `int` | 调用方观察到的旧身份，用于 stale/CAS 校验，防止覆盖并发更新。 |
| `actor` | `str` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |

**输出**

- **Python 类型**：`ResearchRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
调用 `iso` 完成该函数的一项辅助处理，并把结果记为 当前时间。
进入上下文“调用 `_write` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”，退出时自动清理资源：
    通过数据库连接执行数据查询或命令，并把结果记为 增量读取游标。
    如果当前处理结果不等于1，就拒绝继续处理并抛出 `ResearchConflict`，向调用方报告输入或运行失败。
    调用 `_event` 完成该函数的一项辅助处理；调用 `fetchone` 完成该函数的一项辅助处理，并把结果记为 数据库记录行；调用 `_record` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `SqliteResearchRepository.get_pack`

- **源码**：`app/research_browser/repository.py:414`
- **签名**：`def get_pack(self, session_id: str) -> ResearchEvidencePack`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前处理结果的 ID，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `ResearchEvidencePack` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `session_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`ResearchEvidencePack`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
在上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”中调用 `fetchone` 完成该函数的一项辅助处理，并把结果记为 数据库记录行，退出时自动清理资源。
如果数据库记录行为空，就拒绝继续处理并抛出 `ResearchNotFound`，向调用方报告输入或运行失败。
调用 `model_validate_json` 完成该函数的一项辅助处理，并把结果记为 检索或映射证据包。
如果辅助操作“调用 `sha256_value` 计算内容身份、分数或派生结果”的结果不等于检索或映射证据包的 SHA-256，就拒绝继续处理并抛出 `ResearchIntegrityError`，向调用方报告输入或运行失败。
返回检索或映射证据包的当前值。
```

#### `SqliteResearchRepository.list_packs_for_job`

- **源码**：`app/research_browser/repository.py:427`
- **签名**：`def list_packs_for_job(self: 未显式标注, job_id: str, limit: int) -> list[ResearchEvidencePack]`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收复现任务 ID、结果数量上限，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。；默认 20 |

**输出**

- **Python 类型**：`list[ResearchEvidencePack]`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
在上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”中调用 `fetchall` 完成该函数的一项辅助处理，并把结果记为 数据库记录行集合，退出时自动清理资源。
将 当前处理结果 初始化为空列表，用来收集后续结果。
遍历由数据库记录行集合组成的集合或迭代器，每次把当前项记为数据库记录行：
    调用 `model_validate_json` 完成该函数的一项辅助处理，并把结果记为 检索或映射证据包。
    如果辅助操作“调用 `sha256_value` 计算内容身份、分数或派生结果”的结果不等于检索或映射证据包的 SHA-256，就拒绝继续处理并抛出 `ResearchIntegrityError`，向调用方报告输入或运行失败。
    把检索或映射证据包追加或合并到当前处理结果。
返回前一步处理得到的结果。
```

#### `SqliteResearchRepository.list_events`

- **源码**：`app/research_browser/repository.py:452`
- **签名**：`def list_events(self: 未显式标注, session_id: str, after_event_id: int, limit: int) -> list[ResearchEvent]`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前处理结果的 ID、事件的 ID、结果数量上限，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `session_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `after_event_id` | `int` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。；默认 0 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。；默认 200 |

**输出**

- **Python 类型**：`list[ResearchEvent]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
从当前对象读取所需的状态或领域记录。
在上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”中调用 `fetchall` 完成该函数的一项辅助处理，并把结果记为 数据库记录行集合，退出时自动清理资源。
返回当前计算得到的结果。
```

#### `SqliteResearchRepository.requeue_expired`

- **源码**：`app/research_browser/repository.py:485`
- **签名**：`def requeue_expired(self, *, now: datetime, actor: str) -> int`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前时间、审计主体，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终数量、序号、字节数或版本等整数结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `now` | `datetime` | 时间值或可注入时钟，用于排序、过期、租约或可重复测试。 |
| `actor` | `str` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |

**输出**

- **Python 类型**：`int`
- **语义**：返回整数计数、序号、字节数或退出码；具体含义由函数名决定。

**伪代码**

```text
调用 `iso` 完成该函数的一项辅助处理，并把结果记为 当前时间的文本。
进入上下文“调用 `_write` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”，退出时自动清理资源：
    调用 `fetchall` 完成该函数的一项辅助处理，并把结果记为 数据库记录行集合。
    遍历由数据库记录行集合组成的集合或迭代器，每次把当前项记为数据库记录行，然后通过数据库连接执行数据查询或命令；调用 `_event` 完成该函数的一项辅助处理。
    计算数量、边界或类型判断结果，并返回处理结果。
```

#### `SqliteResearchRepository.record_resource_link`

- **源码**：`app/research_browser/repository.py:516`
- **签名**：`def record_resource_link(self: 未显式标注, session_id: str, candidate_id: str, candidate_sha256: str, pack_sha256: str, idempotency_key: str, resource_id: str) -> str`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前处理结果的 ID、待审核的 MCP 能力候选的 ID、待审核的 MCP 能力候选的 SHA-256、检索或映射证据包的 SHA-256等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `session_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `candidate_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `candidate_sha256` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |
| `pack_sha256` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |
| `idempotency_key` | `str` | 调用方提供的幂等键；重复请求应复用同一结果，而不是再次产生副作用。 |
| `resource_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `iso` 完成该函数的一项辅助处理，并把结果记为 当前时间。
进入上下文“调用 `_write` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”，退出时自动清理资源：
    调用 `fetchone` 完成该函数的一项辅助处理，并把结果记为 已有记录。
    如果已有记录不为空：
        如果已有记录中的对应字段不等于待审核的 MCP 能力候选的 SHA-256 或 已有记录中的对应字段不等于检索或映射证据包的 SHA-256，就拒绝继续处理并抛出 `ResearchConflict`，向调用方报告输入或运行失败。
        调用 `str` 完成该函数的一项辅助处理，并返回处理结果。
    通过数据库连接执行数据查询或命令；返回输入资源 ID的当前值。
```

### `app/research_browser/schemas.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `normalize_host_values`

- **源码**：`app/research_browser/schemas.py:44`
- **签名**：`def normalize_host_values(values: list[str]) -> list[str]`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，把用户/Policy host 转成稳定 IDNA 小写形式。该函数接收状态字段集合，用于读取并整理论文、源码或运行产物，把原始输入转换成带位置和身份信息的结构化证据，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `values` | `list[str]` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`list[str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
将 规范化后的文本 初始化为空列表，用来收集后续结果。
遍历由状态字段集合组成的集合或迭代器，每次把当前项记为当前字段值：
    调用 `rstrip` 完成该函数的一项辅助处理，再对返回文本执行规范化或拆分，并把结果记为 服务监听地址。
    如果服务监听地址为空或为假 或 当前输入内容属于服务监听地址 或 当前输入内容属于服务监听地址 或 当前输入内容属于服务监听地址 或 当前输入内容属于服务监听地址 或 “检查服务监听地址是否满足文本匹配条件”后得到肯定结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    先尝试完成以下处理：
        将外部表示解析为结构化内容，并把结果记为 服务监听地址。
    如果出现 `UnicodeError`并把异常保存为捕获的异常对象：
        拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    如果服务监听地址不属于规范化后的文本，就把服务监听地址追加或合并到规范化后的文本。
返回规范化后的文本的当前值。
```

#### `ResearchRequest.reject_control_characters`

- **源码**：`app/research_browser/schemas.py:90`
- **签名**：`def reject_control_characters(cls, value: str) -> str`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `cls` | `未显式标注` | 当前类对象，用于类级构造或校验。 |
| `value` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
如果由当前字段值组成的集合或迭代器中存在满足“当前字符 对应的 ASCII/Unicode 编码小于32 或 当前字符 对应的 ASCII/Unicode 编码等于127”的项，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
调用 `join` 完成该函数的一项辅助处理，并把结果记为 规范化后的文本；返回规范化后的文本的当前值。
```

#### `ResearchRequest.normalize_hosts`

- **源码**：`app/research_browser/schemas.py:101`
- **签名**：`def normalize_hosts(cls, values: list[str]) -> list[str]`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收状态字段集合，用于读取并整理论文、源码或运行产物，把原始输入转换成带位置和身份信息的结构化证据，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `cls` | `未显式标注` | 当前类对象，用于类级构造或校验。 |
| `values` | `list[str]` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`list[str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
调用 `normalize_host_values` 解析、规范化或转换当前输入，并返回处理结果。
```

#### `ResearchPolicyDocument.normalize_policy_hosts`

- **源码**：`app/research_browser/schemas.py:130`
- **签名**：`def normalize_policy_hosts(cls, values: list[str]) -> list[str]`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收状态字段集合，用于读取并整理论文、源码或运行产物，把原始输入转换成带位置和身份信息的结构化证据，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `cls` | `未显式标注` | 当前类对象，用于类级构造或校验。 |
| `values` | `list[str]` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`list[str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
调用 `normalize_host_values` 解析、规范化或转换当前输入，并返回处理结果。
```

#### `ResearchPolicyDocument.validate_budgets`

- **源码**：`app/research_browser/schemas.py:135`
- **签名**：`def validate_budgets(self) -> "ResearchPolicyDocument"`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `'ResearchPolicyDocument'` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`'ResearchPolicyDocument'`
- **语义**：返回 `'ResearchPolicyDocument'` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果最大当前处理结果的字节内容小于最大结构化响应的字节内容，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果媒体集合 的长度不等于辅助操作“构造临时集合、映射或轻量领域对象”的结果 的长度，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前对象的当前值。
```

#### `ExtractedBlock.remove_nul`

- **源码**：`app/research_browser/schemas.py:182`
- **签名**：`def remove_nul(cls, value: str) -> str`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `cls` | `未显式标注` | 当前类对象，用于类级构造或校验。 |
| `value` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `join` 完成该函数的一项辅助处理，并把结果记为 规范化后的文本。
如果规范化后的文本为空或为假，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回规范化后的文本的当前值。
```

#### `ResearchSourceSnapshot.validate_redirect_terminal`

- **源码**：`app/research_browser/schemas.py:208`
- **签名**：`def validate_redirect_terminal(self) -> "ResearchSourceSnapshot"`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `'ResearchSourceSnapshot'` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`'ResearchSourceSnapshot'`
- **语义**：返回 `'ResearchSourceSnapshot'` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果当前处理结果中的对应字段不等于规范化，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
遍历并筛选输入，将整理后的结果保存为 原文块集合。
如果原文块集合 的长度不等于辅助操作“构造临时集合、映射或轻量领域对象”的结果 的长度，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前对象的当前值。
```

#### `ResearchResourceCandidate.validate_resource_identity`

- **源码**：`app/research_browser/schemas.py:249`
- **签名**：`def validate_resource_identity(self) -> "ResearchResourceCandidate"`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `'ResearchResourceCandidate'` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`'ResearchResourceCandidate'`
- **语义**：返回 `'ResearchResourceCandidate'` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果业务类别等于'paper_pdf'：
    如果调用方看到的旧 SHA-256为空，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    如果期望不为空，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
否则：
    如果期望为空，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    如果调用方看到的旧 SHA-256不为空，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果当前处理结果 的长度不等于辅助操作“构造临时集合、映射或轻量领域对象”的结果 的长度，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前对象的当前值。
```

#### `ResearchSynthesisDraft.reject_duplicate_ids`

- **源码**：`app/research_browser/schemas.py:285`
- **签名**：`def reject_duplicate_ids(cls, values: list[str]) -> list[str]`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收状态字段集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `cls` | `未显式标注` | 当前类对象，用于类级构造或校验。 |
| `values` | `list[str]` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`list[str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
如果状态字段集合 的长度不等于辅助操作“构造临时集合、映射或轻量领域对象”的结果 的长度，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回状态字段集合的当前值。
```

#### `ResearchSynthesisDraft.validate_citation_requirement`

- **源码**：`app/research_browser/schemas.py:291`
- **签名**：`def validate_citation_requirement(self) -> "ResearchSynthesisDraft"`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `'ResearchSynthesisDraft'` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`'ResearchSynthesisDraft'`
- **语义**：返回 `'ResearchSynthesisDraft'` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果“证据有值或为真”不成立 且 “当前处理结果有值或为真”不成立，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前对象的当前值。
```

#### `ResearchEvidencePack.validate_references`

- **源码**：`app/research_browser/schemas.py:321`
- **签名**：`def validate_references(self) -> "ResearchEvidencePack"`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `'ResearchEvidencePack'` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`'ResearchEvidencePack'`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
遍历当前可迭代输入，每次把当前项记为当前处理结果：
    计算按字段初始化键值映射，并保存为 对象身份。
    如果当前处理结果的 SHA-256不等于辅助操作“调用 `sha256_value` 计算内容身份、分数或派生结果”的结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    如果当前处理结果的 ID不等于辅助操作“调用 `stable_id` 完成该函数的一项辅助处理”的结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
遍历并筛选输入，将整理后的结果保存为 当前处理结果。
如果当前处理结果 的长度不等于当前处理结果 的长度，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
遍历当前可迭代输入，每次把当前项记为MCP 能力快照：
    调用 `stable_id` 完成该函数的一项辅助处理，并把结果记为 期望的 ID。
    如果MCP 能力快照的 ID不等于期望的 ID，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    调用 `join` 完成该函数的一项辅助处理，并把结果记为 规范化后的文本的文本。
    如果辅助操作“调用 `sha256_text` 计算内容身份、分数或派生结果”的结果不等于规范化后的文本的文本的 SHA-256，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
遍历并筛选输入，将整理后的结果保存为 论文原文块集合；遍历并筛选输入，将整理后的结果保存为 当前处理结果。
如果当前处理结果 的长度不等于论文引用证据集合 的长度，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
遍历并筛选输入，将整理后的结果保存为 当前处理结果的 ID。
遍历当前可迭代输入，每次把当前项记为论文引用证据：
    从当前处理结果读取所需的状态或领域记录，并把结果记为 MCP 能力快照。
    如果MCP 能力快照为空，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    如果请求正文的 SHA-256不等于当前处理结果的 SHA-256，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    从论文原文块集合读取所需的状态或领域记录，并把结果记为 论文原文块。
    如果论文原文块为空，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    如果辅助操作“调用 `sha256_text` 计算内容身份、分数或派生结果”的结果不等于待处理文本的 SHA-256，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    如果论文原文块的 ID不等于辅助操作“调用 `stable_id` 完成该函数的一项辅助处理”的结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    如果当前处理结果不等于待处理文本中的对应字段，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    如果辅助操作“调用 `sha256_text` 计算内容身份、分数或派生结果”的结果不等于当前处理结果的 SHA-256，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    如果论文引用证据的 ID不等于辅助操作“调用 `stable_id` 完成该函数的一项辅助处理”的结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
遍历并筛选输入，将整理后的结果保存为 候选项的 ID。
如果候选项的 ID 的长度不等于资源集合 的长度，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
遍历当前可迭代输入，每次把当前项记为待审核的 MCP 能力候选：
    如果“调用 `issubset` 完成该函数的一项辅助处理”后未得到肯定结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    如果业务类别等于'paper_pdf'：
        遍历并筛选输入，将整理后的结果保存为 候选项集合。
        如果候选项集合 的长度不等于1，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
        读取当前处理结果中的对应字段，并保存为 候选项。
        如果来源类别不等于'pdf' 或 调用方看到的旧 SHA-256不等于请求正文的 SHA-256 或 来源不等于规范化，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
        计算按字段初始化键值映射，并保存为 候选项身份。
    否则：
        计算计算当前表达式的结果，并保存为 当前处理结果；调用 `rstrip` 完成该函数的一项辅助处理，并把结果记为 代码仓库根目录。
        如果“检查当前可迭代输入中是否全部满足“前一步操作返回对象的当前处理结果等于'github.com' 且 “检查前一步操作返回对象的文件或目录路径是否满足文本匹配条件”后得到肯定结果”的项”后未得到肯定结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
        计算按字段初始化键值映射，并保存为 候选项身份。
    如果待审核的 MCP 能力候选的 ID不等于辅助操作“调用 `stable_id` 完成该函数的一项辅助处理”的结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    如果辅助操作“调用 `sha256_value` 计算内容身份、分数或派生结果”的结果不等于待审核的 MCP 能力候选的 SHA-256，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
遍历并筛选输入，将整理后的结果保存为 当前处理结果。
如果“调用 `issubset` 完成该函数的一项辅助处理”后未得到肯定结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果当前可迭代输入中存在满足“当前处理结果的 ID中的对应字段不等于当前处理项”的项，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
构造临时集合、映射或轻量领域对象，并把结果记为 候选项集合；遍历并筛选输入，将整理后的结果保存为 候选项集合。
如果“调用 `issubset` 完成该函数的一项辅助处理”后未得到肯定结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果当前可迭代输入中存在满足“候选项的 ID中的对应字段不等于当前处理项”的项，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
调用 `stable_id` 完成该函数的一项辅助处理，并把结果记为 期望的 ID。
如果检索或映射证据包的 ID不等于期望的 ID，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前对象的当前值。
```

#### `ResearchRecord.validate_status_shape`

- **源码**：`app/research_browser/schemas.py:508`
- **签名**：`def validate_status_shape(self) -> "ResearchRecord"`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`'ResearchRecord'`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
计算计算当前表达式的结果，并保存为 当前处理结果。
如果当前处理结果不等于self.lease_token 不为空 且 self.lease_expires_at 不为空，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果当前状态等于'succeeded' 且 检索或映射证据包的 ID为空，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前对象的当前值。
```

#### `ResearchPublicRecord.from_record`

- **源码**：`app/research_browser/schemas.py:533`
- **签名**：`def from_record(cls, record: ResearchRecord) -> "ResearchPublicRecord"`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收领域记录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `cls` | `未显式标注` | 当前类对象，用于类级构造或校验。 |
| `record` | `ResearchRecord` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |

**输出**

- **Python 类型**：`'ResearchPublicRecord'`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
复制、序列化或校验结构化领域对象，并返回处理结果。
```

### `app/research_browser/search.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `SearchProviderPort.search`

- **源码**：`app/research_browser/search.py:21`
- **签名**：`def search(self, *, query: str, count: int) -> list[ProviderSearchHit]`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收语义检索问题、对象数量，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `query` | `str` | 用户目标、检索问题、反馈或待处理文本；会作为当前阶段的业务语境输入，并可能受到长度/脱敏约束。 |
| `count` | `int` | 对象数量或重试次数，用于范围和上限校验，不是进程退出码。 |

**输出**

- **Python 类型**：`list[ProviderSearchHit]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `BraveSearchProvider.__init__`

- **源码**：`app/research_browser/search.py:28`
- **签名**：`def __init__(self: 未显式标注, secret_service: SecretService, secret_name: str, timeout_seconds: float, client: Any | None) -> None`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收凭据、敏感凭据的名称、等待超时时间（秒）、外部服务客户端，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `secret_service` | `SecretService` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |
| `secret_name` | `str` | 敏感凭证或其引用；不得写入日志、Prompt 或普通 Artifact。 |
| `timeout_seconds` | `float` | 超时或截止时间限制；用于防止等待/搜索/执行无限持续。 |
| `client` | `Any | None` | 外部服务客户端；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 空值 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入参数保存到实例字段（凭据 → 凭据、敏感凭据的名称 → 敏感凭据的名称、等待超时时间（秒） → 等待超时时间（秒）、外部服务客户端 → 外部服务客户端）。
```

#### `BraveSearchProvider.search`

- **源码**：`app/research_browser/search.py:41`
- **签名**：`def search(self, *, query: str, count: int) -> list[ProviderSearchHit]`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收语义检索问题、对象数量，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `query` | `str` | 用户目标、检索问题、反馈或待处理文本；会作为当前阶段的业务语境输入，并可能受到长度/脱敏约束。 |
| `count` | `int` | 对象数量或重试次数，用于范围和上限校验，不是进程退出码。 |

**输出**

- **Python 类型**：`list[ProviderSearchHit]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
如果对象数量小于1 或 对象数量大于20，就拒绝继续处理并抛出 `ResearchLimitExceeded`，向调用方报告输入或运行失败。
如果语义检索问题 的长度大于400 或 辅助操作“对语义检索问题中的文本执行规范化或拆分”的结果 的长度大于50，就拒绝继续处理并抛出 `ResearchLimitExceeded`，向调用方报告输入或运行失败。
调用 `resolve_current` 解析、规范化或转换当前输入，并把结果记为 待处理的论文或源码材料；读取外部服务客户端，并保存为 外部服务客户端；计算计算当前表达式的结果，并保存为 当前处理结果。
先尝试完成以下处理：
    如果外部服务客户端为空，就加载这一步需要的外部依赖；构造 `Client` 结构化领域对象，并把结果记为 外部服务客户端。
    进入上下文“调用 `stream` 完成该函数的一项辅助处理，并把上下文资源交给结构化响应”，退出时自动清理资源：
        如果状态属于{429, 500, 502, 503, 504}，就拒绝继续处理并抛出 `ResearchTransportUnavailable`，向调用方报告输入或运行失败。
        如果状态不等于200，就拒绝继续处理并抛出 `ResearchTransportUnavailable`，向调用方报告输入或运行失败。
        调用 `bytearray` 完成该函数的一项辅助处理，并把结果记为 原始内容。
        遍历辅助操作产生的可迭代结果（调用 `iter_bytes` 完成该函数的一项辅助处理），每次把当前项记为检索文本块：
            把检索文本块追加或合并到原始内容。
            如果原始内容 的长度大于最大响应的字节内容，就拒绝继续处理并抛出 `ResearchLimitExceeded`，向调用方报告输入或运行失败。
        调用 `bytes` 完成该函数的一项辅助处理，并把结果记为 业务内容。
如果出现 `(ResearchLimitExceeded, ResearchTransportUnavailable)`：
    重新抛出当前异常，保持原始失败信息。
如果出现 `Exception`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `ResearchTransportUnavailable`，向调用方报告输入或运行失败。
无论成功还是失败，最后都要：
    如果当前处理结果有值或为真 且 外部服务客户端不为空，就关闭外部服务客户端并释放相关资源。
    移除待处理的论文或源码材料中的当前内容。
先尝试完成以下处理：
    将外部表示解析为结构化内容，并把结果记为 结构化请求载荷；从辅助操作“从结构化请求载荷读取所需的状态或领域记录”的结果读取所需的状态或领域记录，并把结果记为 数据库记录行集合。
如果出现 `(UnicodeDecodeError, json.JSONDecodeError, AttributeError)`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `ResearchTransportUnavailable`，向调用方报告输入或运行失败。
将 检索命中结果 初始化为空列表，用来收集后续结果。
遍历带顺序编号的输入集合，每次把当前项记为多个解包结果：
    如果“计算数量、边界或类型判断结果”后未得到肯定结果 或 “从数据库记录行读取所需的状态或领域记录”后未得到肯定结果 或 “从数据库记录行读取所需的状态或领域记录”后未得到肯定结果，就跳过本轮剩余处理，直接进入下一轮。
    把新的处理结果追加或合并到检索命中结果。
返回检索命中结果的当前值。
```

#### `FixtureSearchProvider.__init__`

- **源码**：`app/research_browser/search.py:134`
- **签名**：`def __init__(self, hits: list[ProviderSearchHit]) -> None`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收检索命中结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `hits` | `list[ProviderSearchHit]` | 检索命中结果；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造临时集合、映射或轻量领域对象，并把结果记为 检索命中结果；将 工具或模型调用记录集合 初始化为空列表，用来收集后续结果。
```

#### `FixtureSearchProvider.search`

- **源码**：`app/research_browser/search.py:138`
- **签名**：`def search(self, *, query: str, count: int) -> list[ProviderSearchHit]`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收语义检索问题、对象数量，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `query` | `str` | 用户目标、检索问题、反馈或待处理文本；会作为当前阶段的业务语境输入，并可能受到长度/脱敏约束。 |
| `count` | `int` | 对象数量或重试次数，用于范围和上限校验，不是进程退出码。 |

**输出**

- **Python 类型**：`list[ProviderSearchHit]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
把新的处理结果追加或合并到工具或模型调用记录集合；返回检索命中结果中的对应字段的当前值。
```

### `app/research_browser/service.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `utc_now`

- **源码**：`app/research_browser/service.py:39`
- **签名**：`def utc_now() -> str`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `isoformat` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `ResearchBrowserService.__init__`

- **源码**：`app/research_browser/service.py:44`
- **签名**：`def __init__(self: 未显式标注, enabled: bool, repository: SqliteResearchRepository, policy: LoadedResearchPolicy, skills: SkillRegistry, synthesizer: ResearchSynthesizer, redactor: SecretRedactor, resource_service: ResourceService, workspace_root: str, run_root: str, lease_seconds: int) -> None`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收功能是否启用的开关、持久化仓库、安全策略、当前处理结果等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `enabled` | `bool` | 布尔条件或能力开关，用于控制流程分支。 |
| `repository` | `SqliteResearchRepository` | 持久化或目录访问端口；负责读取、CAS 更新或 Artifact 定位。 |
| `policy` | `LoadedResearchPolicy` | 安全策略；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `skills` | `SkillRegistry` | 名为 `skills` 的 `SkillRegistry` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `synthesizer` | `ResearchSynthesizer` | 名为 `synthesizer` 的 `ResearchSynthesizer` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `redactor` | `SecretRedactor` | 敏感信息脱敏器；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `resource_service` | `ResourceService` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |
| `workspace_root` | `str` | 名为 `workspace_root` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `run_root` | `str` | 运行产物根目录；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `lease_seconds` | `int` | 名为 `lease_seconds` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。；默认 180 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 功能是否启用的开关、持久化仓库、安全策略、当前处理结果、当前处理结果、敏感信息脱敏器、资源、根目录、运行产物根目录、租约集合 分别保存到同名实例字段；调用 `initialize` 完成该函数的一项辅助处理。
```

#### `ResearchBrowserService._require_enabled`

- **源码**：`app/research_browser/service.py:70`
- **签名**：`def _require_enabled(self) -> None`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
如果“功能是否启用的开关有值或为真”不成立，就拒绝继续处理并抛出 `ResearchBrowserDisabled`，向调用方报告输入或运行失败。
```

#### `ResearchBrowserService.submit`

- **源码**：`app/research_browser/service.py:74`
- **签名**：`def submit(self: 未显式标注, request: ResearchRequest, idempotency_key: str, actor: str) -> 未显式标注（存在 return）`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收业务请求、请求幂等键、审计主体，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `request` | `ResearchRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `idempotency_key` | `str` | 调用方提供的幂等键；重复请求应复用同一结果，而不是再次产生副作用。 |
| `actor` | `str` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
调用 `_require_enabled` 完成该函数的一项辅助处理；去除请求幂等键的首尾空白，并把规范化后的文本记为 映射键或对象字段名。
如果映射键或对象字段名为空或为假 或 映射键或对象字段名 的长度大于300，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
复制、序列化或校验结构化领域对象，并把结果记为 规范化后的文本；调用 `effective_hosts` 完成该函数的一项辅助处理；调用 `request_sha256` 计算内容身份、分数或派生结果，并把结果记为 内容摘要；计算根据字段和固定文本生成格式化文本，并保存为 当前处理结果的 ID。
调用 `submit` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；返回领域记录的当前值。
```

#### `ResearchBrowserService.run`

- **源码**：`app/research_browser/service.py:114`
- **签名**：`def run(self: 未显式标注, session_id: str, expected_version: int, actor: str) -> 未显式标注（存在 return）`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前处理结果的 ID、调用方看到的旧版本号、审计主体，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `session_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `expected_version` | `int` | 调用方观察到的旧身份，用于 stale/CAS 校验，防止覆盖并发更新。 |
| `actor` | `str` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
调用 `_require_enabled` 完成该函数的一项辅助处理；从持久化仓库读取所需的状态或领域记录，并把结果记为 当前值。
如果安全策略的 SHA-256不等于安全策略的 SHA-256，就拒绝继续处理并抛出 `ResearchConflict`，向调用方报告输入或运行失败。
如果请求内容 SHA-256不等于辅助操作“调用 `request_sha256` 计算内容身份、分数或派生结果”的结果，就拒绝继续处理并抛出 `ResearchIntegrityError`，向调用方报告输入或运行失败。
计算根据字段和固定文本生成格式化文本，并保存为 租约；调用 `start` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
先尝试完成以下处理：
    从当前处理结果读取所需的状态或领域记录，并把结果记为 边界值；调用当前处理结果完成模型或 Runnable 处理，并把结果记为 阶段处理结果。
    如果失败不为空，就调用 `fail` 完成该函数的一项辅助处理，并返回处理结果。
    复制、序列化或校验结构化领域对象，并把结果记为 可追溯证据记录。
    先尝试完成以下处理：
        调用 `synthesize` 完成该函数的一项辅助处理，并把结果记为 MCP 评测或运行报告。
    如果出现 `ResearchSynthesisRejected`：
        构造 `ResearchReport` 结构化领域对象，并把结果记为 MCP 评测或运行报告。
    调用 `stable_id` 完成该函数的一项辅助处理，并把结果记为 检索或映射证据包的 ID；构造 `ResearchEvidencePack` 结构化领域对象，并把结果记为 草稿；复制、序列化或校验结构化领域对象，并把结果记为 检索或映射证据包；调用 `complete` 完成该函数的一项辅助处理，并返回处理结果。
如果出现 `Exception`并把异常保存为捕获的异常对象：
    读取当前输入内容中的对应字段，并保存为 待解析或验证的代码；计算计算当前表达式的结果，并保存为 是否允许重试的判断；调用 `fail` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `ResearchBrowserService.get`

- **源码**：`app/research_browser/service.py:233`
- **签名**：`def get(self, session_id: str)`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前处理结果的 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `session_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
从持久化仓库读取所需的状态或领域记录，并返回处理结果。
```

#### `ResearchBrowserService.get_pack`

- **源码**：`app/research_browser/service.py:236`
- **签名**：`def get_pack(self, session_id: str) -> ResearchEvidencePack`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前处理结果的 ID，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `ResearchEvidencePack` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `session_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`ResearchEvidencePack`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
调用 `get_pack` 读取或查询当前阶段需要的数据，并返回处理结果。
```

#### `ResearchBrowserService.cancel`

- **源码**：`app/research_browser/service.py:239`
- **签名**：`def cancel(self, *, session_id: str, expected_version: int, actor: str)`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前处理结果的 ID、调用方看到的旧版本号、审计主体，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `session_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `expected_version` | `int` | 调用方观察到的旧身份，用于 stale/CAS 校验，防止覆盖并发更新。 |
| `actor` | `str` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
调用 `cancel` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `ResearchBrowserService.events`

- **源码**：`app/research_browser/service.py:246`
- **签名**：`def events(self: 未显式标注, session_id: str, after_event_id: int, limit: int) -> 未显式标注（存在 return）`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前处理结果的 ID、事件的 ID、结果数量上限，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `session_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `after_event_id` | `int` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。；默认 0 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。；默认 200 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
调用 `list_events` 读取或查询当前阶段需要的数据，并返回处理结果。
```

#### `ResearchBrowserService.reconcile`

- **源码**：`app/research_browser/service.py:259`
- **签名**：`def reconcile(self, *, actor: str) -> int`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收审计主体，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终数量、序号、字节数或版本等整数结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `actor` | `str` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |

**输出**

- **Python 类型**：`int`
- **语义**：返回整数计数、序号、字节数或退出码；具体含义由函数名决定。

**伪代码**

```text
调用 `requeue_expired` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `ResearchBrowserService.submit_resource_candidate`

- **源码**：`app/research_browser/service.py:265`
- **签名**：`def submit_resource_candidate(self: 未显式标注, session_id: str, selection: ResearchResourceSelection, actor: str) -> 未显式标注（存在 return）`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前处理结果的 ID、当前处理结果、审计主体，用于驱动或监督一次论文复现运行，记录命令、工作目录、资源使用、状态迁移和失败原因，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `session_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `selection` | `ResearchResourceSelection` | 名为 `selection` 的 `ResearchResourceSelection` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `actor` | `str` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
调用 `_require_enabled` 完成该函数的一项辅助处理；调用 `get_pack` 读取或查询当前阶段需要的数据，并把结果记为 检索或映射证据包。
如果检索或映射证据包的 SHA-256不等于期望的 SHA-256，就拒绝继续处理并抛出 `ResearchConflict`，向调用方报告输入或运行失败。
调用 `next` 完成该函数的一项辅助处理，并把结果记为 待审核的 MCP 能力候选。
如果待审核的 MCP 能力候选为空，就拒绝继续处理并抛出 `ResearchResourceCandidateRejected`，向调用方报告输入或运行失败。
调用 `sha256_value` 计算内容身份、分数或派生结果，并把结果记为 期望候选项的 Hash。
如果待审核的 MCP 能力候选的 SHA-256不等于期望候选项的 Hash 或 待审核的 MCP 能力候选的 SHA-256不等于期望候选项的 Hash，就拒绝继续处理并抛出 `ResearchConflict`，向调用方报告输入或运行失败。
构造 `ResourceRequest` 结构化领域对象，并把结果记为 资源；计算根据字段和固定文本生成格式化文本，并保存为 键；调用 `submit` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；调用 `record_resource_link` 完成该函数的一项辅助处理，并把结果记为 当前处理结果的 ID。
如果当前处理结果的 ID不等于输入资源 ID，就拒绝继续处理并抛出 `ResearchConflict`，向调用方报告输入或运行失败。
如果当前状态不等于'awaiting_approval'，就拒绝继续处理并抛出 `ResearchConflict`，向调用方报告输入或运行失败。
返回复现输入资源的当前值。
```

### `app/research_browser/synthesis.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `ResearchSynthesizer.__init__`

- **源码**：`app/research_browser/synthesis.py:19`
- **签名**：`def __init__(self, *, gateway: ModelGateway, redactor: SecretRedactor) -> None`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收外部服务网关、敏感信息脱敏器，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `gateway` | `ModelGateway` | 外部服务网关；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `redactor` | `SecretRedactor` | 敏感信息脱敏器；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 外部服务网关、敏感信息脱敏器 分别保存到同名实例字段。
```

#### `ResearchSynthesizer.synthesize`

- **源码**：`app/research_browser/synthesis.py:23`
- **签名**：`def synthesize(self: 未显式标注, request: ResearchRequest, evidence: ResearchEvidenceDraft) -> ResearchReport`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收业务请求、可追溯证据记录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ResearchReport` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `request` | `ResearchRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `evidence` | `ResearchEvidenceDraft` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |

**输出**

- **Python 类型**：`ResearchReport`
- **语义**：返回 `ResearchReport` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果“论文引用证据集合有值或为真”不成立，就构造并返回 `ResearchReport` 结构化领域对象。
遍历并筛选输入，将整理后的结果保存为 当前处理结果的 ID；遍历并筛选输入，将整理后的结果保存为 候选项的 ID；遍历并筛选输入，将整理后的结果保存为 当前处理结果；调用 `format` 完成该函数的一项辅助处理，并把结果记为 发给模型的结构化提示。
先尝试完成以下处理：
    调用 `invoke_structured` 完成该函数的一项辅助处理，并把结果记为 工具调用记录。
如果出现 `ModelBudgetExceeded`：
    构造并返回 `ResearchReport` 结构化领域对象。
读取当前字段值，并保存为 草稿对象。
如果草稿对象为空，就构造并返回 `ResearchReport` 结构化领域对象。
计算组合或计算已有值，并保存为 当前处理结果；计算组合或计算已有值，并保存为 当前处理结果。
如果当前处理结果有值或为真 或 当前处理结果有值或为真，就拒绝继续处理并抛出 `ResearchSynthesisRejected`，向调用方报告输入或运行失败。
调用 `redact_text` 解析、规范化或转换当前输入，并把结果记为 该调用返回的结果；构造并返回 `ResearchReport` 结构化领域对象。
```

### `app/research_browser/tooling.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_map_research_error`

- **源码**：`app/research_browser/tooling.py:23`
- **签名**：`def _map_research_error(exc: BaseException) -> ToolFailure | None`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收捕获的异常，用于把论文中的方法、模块或实验意图与仓库中的可验证对象建立稳定关联，并保留匹配依据，最终标注为 `ToolFailure | None` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `exc` | `BaseException` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`ToolFailure | None`
- **语义**：返回 `ToolFailure | None` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
读取前一步操作返回对象的当前处理结果，并保存为 对象名称。
如果对象名称属于{'ResearchUrlRejected', 'ResearchRobotsDenied', 'ResearchPolicyError'}，就构造并返回 `ToolFailure` 结构化领域对象。
如果对象名称属于{'ResearchLimitExceeded', 'ResearchContentRejected'}，就构造并返回 `ToolFailure` 结构化领域对象。
如果对象名称等于'ResearchTransportUnavailable'，就构造并返回 `ToolFailure` 结构化领域对象。
返回固定值 `空值`。
```

#### `build_research_tool_definition`

- **源码**：`app/research_browser/tooling.py:49`
- **签名**：`def build_research_tool_definition(bindings: ResearchToolBindings)`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收当前处理结果，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `bindings` | `ResearchToolBindings` | 名为 `bindings` 的 `ResearchToolBindings` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
定义内部辅助函数 `handler`，供当前函数在后续步骤中调用。
调用 `build_tool_definition` 组装当前阶段需要的领域对象，并返回处理结果。
```

#### `build_research_tool_definition.handler`

- **源码**：`app/research_browser/tooling.py:50`
- **签名**：`def handler(payload: ResearchCollectInput, context)`
- **作用**：在在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段中，该函数接收结构化请求载荷、运行上下文，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `payload` | `ResearchCollectInput` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `context` | `未显式标注` | 运行上下文；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
移除运行上下文中的当前内容；构造并返回 `ResearchCollectOutput` 结构化领域对象。
```

### `app/retrieval/policy.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `canonical_json`

- **源码**：`app/retrieval/policy.py:34`
- **签名**：`def canonical_json(value: Any) -> str`
- **作用**：在优化论文方法检索策略、候选排序和离线评测质量的阶段中，生成稳定 JSON；Hash 身份不能依赖字典插入顺序。该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `Any` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
如果“调用 `hasattr` 完成该函数的一项辅助处理”后得到肯定结果，就复制、序列化或校验结构化领域对象，并把结果记为 当前字段值。
将结构化内容序列化或编码为可传输表示，并返回处理结果。
```

#### `sha256_value`

- **源码**：`app/retrieval/policy.py:47`
- **签名**：`def sha256_value(value: Any) -> str`
- **作用**：在优化论文方法检索策略、候选排序和离线评测质量的阶段中，返回领域对象的 SHA-256 内容身份，不返回或隐藏原文。该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `Any` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回输入内容的 SHA-256 身份摘要，用于完整性校验，不是加密后的正文。

**伪代码**

```text
计算输入内容的 SHA-256 身份摘要，并返回处理结果。
```

#### `load_retrieval_policy`

- **源码**：`app/retrieval/policy.py:55`
- **签名**：`def load_retrieval_policy(path: str | Path) -> RetrievalPolicyConfig`
- **作用**：在优化论文方法检索策略、候选排序和离线评测质量的阶段中，从有界本地 JSON 加载 Policy，并由 Pydantic 拒绝未知字段。该函数接收文件或目录路径，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `RetrievalPolicyConfig` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `path` | `str | Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`RetrievalPolicyConfig`
- **语义**：返回从外部表示解析并校验后的领域值；格式非法时通过异常失败。

**伪代码**

```text
将辅助操作“将辅助操作“把外部位置解析为文件系统路径对象”的结果规范化为受控的绝对路径”的结果规范化为受控的绝对路径，并把结果记为 待审核的 MCP 能力候选。
如果“检查待审核的 MCP 能力候选的文件系统属性”后未得到肯定结果，就拒绝继续处理并抛出 `FileNotFoundError`，向调用方报告输入或运行失败。
如果前一步操作返回对象的当前处理结果大于最大安全策略的字节内容，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
将外部表示解析为结构化内容，并把结果记为 结构化请求载荷；复制、序列化或校验结构化领域对象，并返回处理结果。
```

#### `profile_by_id`

- **源码**：`app/retrieval/policy.py:68`
- **签名**：`def profile_by_id(policy: RetrievalPolicyConfig, profile_id: str) -> RetrievalProfile`
- **作用**：在优化论文方法检索策略、候选排序和离线评测质量的阶段中，按稳定 ID 查询 profile；不存在时失败，不静默使用相似名称。该函数接收安全策略、MCP Client 配置档案 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `RetrievalProfile` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `policy` | `RetrievalPolicyConfig` | 安全策略；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `profile_id` | `str` | MCP Client 配置档案 ID；用于区分连接地址、协议版本和能力基线。 |

**输出**

- **Python 类型**：`RetrievalProfile`
- **语义**：返回稳定业务标识符，用于后续查询、关联或幂等绑定；它不是路径或内容 Hash。

**伪代码**

```text
遍历当前可迭代输入，每次把当前项记为MCP Client 配置档案：
    如果MCP Client 配置档案 ID等于MCP Client 配置档案 ID，就返回MCP Client 配置档案的当前值。
拒绝继续处理并抛出 `KeyError`，向调用方报告输入或运行失败。
```

#### `_normalized_values`

- **源码**：`app/retrieval/policy.py:80`
- **签名**：`def _normalized_values(query: str, keywords: list[str]) -> list[str]`
- **作用**：在优化论文方法检索策略、候选排序和离线评测质量的阶段中，该函数接收语义检索问题、检索关键词集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `query` | `str` | 用户目标、检索问题、反馈或待处理文本；会作为当前阶段的业务语境输入，并可能受到长度/脱敏约束。 |
| `keywords` | `list[str]` | 用于精确检索或文件分类的关键词集合；匹配范围由当前工具决定。 |

**输出**

- **Python 类型**：`list[str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
将 输出结果 初始化为空列表，用来收集后续结果。
遍历当前可迭代输入，每次把当前项记为原始内容：
    调用 `join` 完成该函数的一项辅助处理，并把结果记为 规范化后的文本。
    如果规范化后的文本有值或为真 且 规范化后的文本不属于输出结果，就把规范化后的文本追加或合并到输出结果。
返回输出结果的当前值。
```

#### `build_query_features`

- **源码**：`app/retrieval/policy.py:89`
- **签名**：`def build_query_features(query: str, keywords: list[str], preferred_paths: list[str] | None, paper_evidence_count: int) -> RetrievalQueryFeatures`
- **作用**：在优化论文方法检索策略、候选排序和离线评测质量的阶段中，只用确定性规则提取特征。该函数接收语义检索问题、检索关键词集合、优先使用的路径集合、论文证据的数量，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `RetrievalQueryFeatures` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `query` | `str` | 用户目标、检索问题、反馈或待处理文本；会作为当前阶段的业务语境输入，并可能受到长度/脱敏约束。 |
| `keywords` | `list[str]` | 用于精确检索或文件分类的关键词集合；匹配范围由当前工具决定。 |
| `preferred_paths` | `list[str] | None` | 优先使用的路径集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 空值 |
| `paper_evidence_count` | `int` | 对象数量或重试次数，用于范围和上限校验，不是进程退出码。；默认 0 |

**输出**

- **Python 类型**：`RetrievalQueryFeatures`
- **语义**：返回 `RetrievalQueryFeatures` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `_normalized_values` 完成该函数的一项辅助处理，并把结果记为 状态字段集合；调用 `join` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `findall` 完成该函数的一项辅助处理，并把结果记为 模型 token 用量；遍历并筛选输入，将整理后的结果保存为 文件或目录路径集合。
计算数量、边界或类型判断结果，并把结果记为 是否已有错误信息；计算计算当前表达式的结果，并保存为 是否已有文件或目录路径；计算数量、边界或类型判断结果，并把结果记为 是否已有异常堆栈文本；检查由检索关键词集合组成的集合或迭代器中是否存在满足““计算数量、边界或类型判断结果”后得到肯定结果 且 当前输入内容属于当前字段值 或 当前输入内容属于当前字段值 或 当前可迭代输入中存在满足““调用 `isupper` 完成该函数的一项辅助处理”后得到肯定结果”的项”的项，并把结果记为 是否已有当前处理结果。
计算计算当前表达式的结果，并保存为 是否已有当前处理结果。
如果是否已有异常堆栈文本有值或为真：
    计算使用固定配置或常量值，并保存为 查询类别。
否则：
    如果是否已有错误信息有值或为真：
        计算使用固定配置或常量值，并保存为 查询类别。
    否则：
        如果是否已有当前处理结果有值或为真 或 是否已有文件或目录路径有值或为真 且 是否已有当前处理结果为空或为假：
            计算使用固定配置或常量值，并保存为 查询类别。
        否则：
            如果是否已有当前处理结果有值或为真 且 “是否已有当前处理结果有值或为真 或 是否已有文件或目录路径有值或为真”不成立，就计算使用固定配置或常量值，并保存为 查询类别；否则计算使用固定配置或常量值，并保存为 查询类别。
构造并返回 `RetrievalQueryFeatures` 结构化领域对象。
```

#### `select_retrieval_profile`

- **源码**：`app/retrieval/policy.py:164`
- **签名**：`def select_retrieval_profile(policy: RetrievalPolicyConfig, features: RetrievalQueryFeatures, dense_available: bool, mode: RetrievalPolicyMode) -> RetrievalDecision`
- **作用**：在优化论文方法检索策略、候选排序和离线评测质量的阶段中，返回可审计决策。该函数接收安全策略、当前处理结果、当前处理结果、MCP 评测或运行模式，用于根据当前运行状态、证据完整性、风险等级或人工决策选择下一条复现流程路径，最终标注为 `RetrievalDecision` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `policy` | `RetrievalPolicyConfig` | 安全策略；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `features` | `RetrievalQueryFeatures` | 名为 `features` 的 `RetrievalQueryFeatures` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `dense_available` | `bool` | 布尔条件或能力开关，用于控制流程分支。 |
| `mode` | `RetrievalPolicyMode` | MCP 评测或运行模式；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`RetrievalDecision`
- **语义**：返回 `RetrievalDecision` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
将 原因集合 初始化为空列表，用来收集后续结果；读取配置的 ID，并保存为 配置的 ID。
遍历辅助操作产生的可迭代结果（按稳定规则整理结果顺序），每次把当前项记为当前处理结果：
    如果查询类别不属于查询集合，就跳过本轮剩余处理，直接进入下一轮。
    如果当前处理结果有值或为真 且 当前处理结果为空或为假，就把新的处理结果追加或合并到原因集合；跳过本轮剩余处理，直接进入下一轮。
    读取MCP Client 配置档案 ID，并保存为 配置的 ID；把新的处理结果追加或合并到原因集合；立即结束当前循环。
如果循环正常完成而没有提前 `break`：
    把新的处理结果追加或合并到原因集合。
调用 `profile_by_id` 完成该函数的一项辅助处理，并把结果记为 选中的候选项；计算使用固定配置或常量值，并保存为 当前处理结果。
如果当前处理结果有值或为真 且 当前处理结果为空或为假，就调用 `profile_by_id` 完成该函数的一项辅助处理，并把结果记为 选中的候选项；计算使用固定配置或常量值，并保存为 当前处理结果；把新的处理结果追加或合并到原因集合。
调用 `sha256_value` 计算内容身份、分数或派生结果，并把结果记为 安全策略的 SHA-256；调用 `sha256_value` 计算内容身份、分数或派生结果，并把结果记为 MCP Client 配置档案的 SHA-256；计算按字段初始化键值映射，并保存为 当前处理结果；构造并返回 `RetrievalDecision` 结构化领域对象。
```

### `app/retrieval/policy_eval.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_path_key`

- **源码**：`app/retrieval/policy_eval.py:49`
- **签名**：`def _path_key(value: str) -> str`
- **作用**：在优化论文方法检索策略、候选排序和离线评测质量的阶段中，统一 Golden Case 与 CodeEvidence 中的相对路径表示。该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `lstrip` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `load_policy_cases`

- **源码**：`app/retrieval/policy_eval.py:55`
- **签名**：`def load_policy_cases(case_dir: str | Path) -> list[RetrievalPolicyGoldenCase]`
- **作用**：在优化论文方法检索策略、候选排序和离线评测质量的阶段中，按文件名稳定顺序加载 Case，并拒绝重复 case_id。该函数接收评测用例的目录，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `case_dir` | `str | Path` | 名为 `case_dir` 的 `str | Path` 领域输入；用于当前函数的业务处理，具体约束见校验分支。；默认 DEFAULT_CASE_DIR |

**输出**

- **Python 类型**：`list[RetrievalPolicyGoldenCase]`
- **语义**：返回从外部表示解析并校验后的领域值；格式非法时通过异常失败。

**伪代码**

```text
将辅助操作“将辅助操作“把外部位置解析为文件系统路径对象”的结果规范化为受控的绝对路径”的结果规范化为受控的绝对路径，并把结果记为 受控扫描根目录；将根目录规范化为受控的绝对路径，并把结果记为 根目录。
如果受控扫描根目录不等于根目录 且 根目录不属于当前处理结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果“检查受控扫描根目录的文件系统属性”后未得到肯定结果，就拒绝继续处理并抛出 `FileNotFoundError`，向调用方报告输入或运行失败。
将 评测用例集合 初始化为空列表，用来收集后续结果；将 当前处理结果 初始化为空去重集合，用来收集后续结果。
遍历辅助操作产生的可迭代结果（按稳定规则整理结果顺序），每次把当前项记为文件或目录路径：
    将外部表示解析为结构化内容，并把结果记为 结构化请求载荷；复制、序列化或校验结构化领域对象，并把结果记为 评测用例。
    如果评测用例的 ID属于当前处理结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    把评测用例的 ID追加或合并到当前处理结果；把评测用例追加或合并到评测用例集合。
如果评测用例集合为空或为假，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回评测用例集合的当前值。
```

#### `evaluate_profile_case`

- **源码**：`app/retrieval/policy_eval.py:82`
- **签名**：`def evaluate_profile_case(policy: RetrievalPolicyConfig, case: RetrievalPolicyGoldenCase, profile: RetrievalProfile) -> RetrievalProfileCaseMetrics`
- **作用**：在优化论文方法检索策略、候选排序和离线评测质量的阶段中，对单个 Case 执行单个 Profile。该函数接收安全策略、评测用例、MCP Client 配置档案，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `RetrievalProfileCaseMetrics` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `policy` | `RetrievalPolicyConfig` | 安全策略；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `case` | `RetrievalPolicyGoldenCase` | 测试夹具或评测用例对象；提供场景数据和受控依赖，不是生产业务输入。 |
| `profile` | `RetrievalProfile` | 运行/执行环境配置或 profile 标识；描述能力和限制，不是一次执行的结果。 |

**输出**

- **Python 类型**：`RetrievalProfileCaseMetrics`
- **语义**：返回 `RetrievalProfileCaseMetrics` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `resolve_evaluation_path` 解析、规范化或转换当前输入，并把结果记为 仓库根目录。
如果“检查仓库根目录的文件系统属性”后未得到肯定结果，就拒绝继续处理并抛出 `FileNotFoundError`，向调用方报告输入或运行失败。
调用 `build_query_features` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果。
如果查询类别不等于期望查询类别，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
调用 `build_repository_index` 组装当前阶段需要的领域对象，并把结果记为 当前候选项的索引；调用 `perf_counter` 完成该函数的一项辅助处理，并把结果记为 运行是否已经启动的判断；调用 `build_evidence_pack` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果；计算组合或计算已有值，并保存为 当前处理结果。
遍历并筛选输入，将整理后的结果保存为 当前处理结果；遍历并筛选输入，将整理后的结果保存为 当前处理结果的路径；遍历并筛选输入，将整理后的结果保存为 当前处理结果；遍历并筛选输入，将整理后的结果保存为 被策略禁止的内容或操作。
计算组合或计算已有值，并保存为 当前处理结果；计算组合或计算已有值，并保存为 当前处理结果；遍历并筛选输入，将整理后的结果保存为 当前处理结果的路径；计算根据条件从两个候选结果中选择一个，并保存为 当前处理结果。
计算组合或计算已有值，并保存为 当前处理结果；调用 `sum` 完成该函数的一项辅助处理，并把结果记为 被策略禁止的内容或操作的数量；计算数量、边界或类型判断结果，并把结果记为 该调用返回的结果；构造并返回 `RetrievalProfileCaseMetrics` 结构化领域对象。
```

#### `aggregate_profile_metrics`

- **源码**：`app/retrieval/policy_eval.py:193`
- **签名**：`def aggregate_profile_metrics(metrics: list[RetrievalProfileCaseMetrics]) -> list[RetrievalProfileAggregate]`
- **作用**：在优化论文方法检索策略、候选排序和离线评测质量的阶段中，按 profile 聚合；聚合值用于报告，晋升仍使用同 Case 成对比较。该函数接收当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `metrics` | `list[RetrievalProfileCaseMetrics]` | `list[RetrievalProfileCaseMetrics]` 元素集合；元素代表的业务对象由参数名 `metrics` 和调用位置确定。 |

**输出**

- **Python 类型**：`list[RetrievalProfileAggregate]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
调用 `defaultdict` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
遍历由当前处理结果组成的集合或迭代器，每次把当前项记为当前处理项，然后把当前处理项追加或合并到当前处理结果中的对应字段。
将 输出结果 初始化为空列表，用来收集后续结果。
遍历辅助操作产生的可迭代结果（按稳定规则整理结果顺序），每次把当前项记为多个解包结果，然后计算数量、边界或类型判断结果，并把结果记为 对象数量；把新的处理结果追加或合并到输出结果。
返回输出结果的当前值。
```

#### `build_promotion_proposal`

- **源码**：`app/retrieval/policy_eval.py:232`
- **签名**：`def build_promotion_proposal(policy_sha256: str, case_id: str, baseline: RetrievalProfileCaseMetrics, challenger: RetrievalProfileCaseMetrics) -> RetrievalPromotionProposal`
- **作用**：在优化论文方法检索策略、候选排序和离线评测质量的阶段中，产生建议而不是修改配置；Safety/Provenance 回归直接拒绝。该函数接收安全策略的 SHA-256、评测用例的 ID、已审核的 MCP 能力基线、当前处理结果，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `RetrievalPromotionProposal` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `policy_sha256` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |
| `case_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `baseline` | `RetrievalProfileCaseMetrics` | 已审核的 MCP 能力基线；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `challenger` | `RetrievalProfileCaseMetrics` | 名为 `challenger` 的 `RetrievalProfileCaseMetrics` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`RetrievalPromotionProposal`
- **语义**：返回 `RetrievalPromotionProposal` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
将 当前处理结果 初始化为空列表，用来收集后续结果。
如果“当前处理结果有值或为真”不成立，就把新的处理结果追加或合并到当前处理结果。
如果当前处理结果小于当前处理结果，就把新的处理结果追加或合并到当前处理结果。
如果当前处理结果小于当前处理结果，就把新的处理结果追加或合并到当前处理结果。
如果当前处理结果小于1.0，就把新的处理结果追加或合并到当前处理结果。
如果当前处理结果小于当前处理结果，就把新的处理结果追加或合并到当前处理结果。
如果当前处理结果小于1.0，就把新的处理结果追加或合并到当前处理结果。
如果被策略禁止的内容或操作的路径的数量大于0，就把新的处理结果追加或合并到当前处理结果。
计算数量、边界或类型判断结果，并把结果记为 该调用返回的结果。
如果当前处理结果为空或为假，就把新的处理结果追加或合并到当前处理结果。
计算计算当前表达式的结果，并保存为 当前处理结果；计算按字段初始化键值映射，并保存为 结构化请求载荷；构造并返回 `RetrievalPromotionProposal` 结构化领域对象。
```

#### `run_policy_eval`

- **源码**：`app/retrieval/policy_eval.py:294`
- **签名**：`def run_policy_eval(policy: RetrievalPolicyConfig, cases: list[RetrievalPolicyGoldenCase]) -> RetrievalPolicyEvalReport`
- **作用**：在优化论文方法检索策略、候选排序和离线评测质量的阶段中，执行所有 baseline/challenger，并生成确定性的成对晋升建议。该函数接收安全策略、评测用例集合，用于驱动或监督一次论文复现运行，记录命令、工作目录、资源使用、状态迁移和失败原因，最终标注为 `RetrievalPolicyEvalReport` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `policy` | `RetrievalPolicyConfig` | 安全策略；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `cases` | `list[RetrievalPolicyGoldenCase]` | 评测用例集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`RetrievalPolicyEvalReport`
- **语义**：返回 `RetrievalPolicyEvalReport` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
将 当前处理结果、当前处理结果 初始化为空列表，用来收集后续结果；调用 `sha256_value` 计算内容身份、分数或派生结果，并把结果记为 安全策略的 Hash。
遍历由评测用例集合组成的集合或迭代器，每次把当前项记为评测用例：
    构造临时集合、映射或轻量领域对象，并把结果记为 配置集合；将 配置 初始化为空映射，用来收集后续结果。
    遍历由配置集合组成的集合或迭代器，每次把当前项记为MCP Client 配置档案 ID，然后调用 `profile_by_id` 完成该函数的一项辅助处理，并把结果记为 MCP Client 配置档案；调用 `evaluate_profile_case` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果；把阶段处理结果追加或合并到当前处理结果；读取阶段处理结果，并保存为 配置中的对应字段。
    读取配置中的对应字段，并保存为 已审核的 MCP 能力基线。
    遍历当前可迭代输入，每次把当前项记为当前处理结果的 ID，然后把新的处理结果追加或合并到当前处理结果。
调用 `aggregate_profile_metrics` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `isoformat` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；计算按字段初始化键值映射，并保存为 当前处理结果；构造并返回 `RetrievalPolicyEvalReport` 结构化领域对象。
```

#### `render_policy_eval_report`

- **源码**：`app/retrieval/policy_eval.py:352`
- **签名**：`def render_policy_eval_report(report: RetrievalPolicyEvalReport) -> str`
- **作用**：在优化论文方法检索策略、候选排序和离线评测质量的阶段中，生成适合人工审阅的 Markdown，不包含源码正文。该函数接收MCP 评测或运行报告，用于把复现过程中的结构化状态、证据或结果转换为可读、可传输或可持久化的表示，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `report` | `RetrievalPolicyEvalReport` | MCP 评测或运行报告；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回整理、格式化或规范化后的文本表示。

**伪代码**

```text
计算初始化顺序集合，并保存为 待输出的文本行。
遍历当前可迭代输入，每次把当前项记为当前处理项，然后把新的处理结果追加或合并到待输出的文本行。
把新的处理结果追加或合并到待输出的文本行。
遍历当前可迭代输入，每次把当前项记为当前处理项，然后把新的处理结果追加或合并到待输出的文本行。
返回当前计算得到的结果。
```

#### `run`

- **源码**：`app/retrieval/policy_eval.py:387`
- **签名**：`def run(policy_path: Annotated[Path, typer.Option('--policy')], case_dir: Annotated[Path, typer.Option('--case-dir')]) -> None`
- **作用**：在优化论文方法检索策略、候选排序和离线评测质量的阶段中，运行离线策略评测并发布 JSON、Markdown 和 Promotion Proposal。该函数接收安全策略的路径、评测用例的目录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `policy_path` | `Annotated[Path, typer.Option('--policy')]` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。；默认 调用 Path('config/retrieval_policy.json') |
| `case_dir` | `Annotated[Path, typer.Option('--case-dir')]` | 名为 `case_dir` 的 `Annotated[Path, typer.Option('--case-dir')]` 领域输入；用于当前函数的业务处理，具体约束见校验分支。；默认 DEFAULT_CASE_DIR |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `load_retrieval_policy` 读取或查询当前阶段需要的数据，并把结果记为 安全策略；调用 `load_policy_cases` 读取或查询当前阶段需要的数据，并把结果记为 评测用例集合；调用 `run_policy_eval` 完成该函数的一项辅助处理，并把结果记为 MCP 评测或运行报告；计算按字段初始化键值映射，并保存为 复现流程状态。
把新的处理结果追加或合并到复现流程状态；调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；调用 `write_text_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果。
把新的处理结果追加或合并到复现流程状态；计算使用固定配置或常量值，并保存为 复现流程状态中的对应字段；把新的处理结果追加或合并到复现流程状态；调用 `echo` 完成该函数的一项辅助处理。
```

### `app/retrieval/policy_schemas.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `RetrievalProfile.validate_profile`

- **源码**：`app/retrieval/policy_schemas.py:82`
- **签名**：`def validate_profile(self) -> RetrievalProfile`
- **作用**：在优化论文方法检索策略、候选排序和离线评测质量的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `RetrievalProfile` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`RetrievalProfile`
- **语义**：返回 `RetrievalProfile` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果辅助操作“构造临时集合、映射或轻量领域对象”的结果 的长度不等于当前处理结果 的长度，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
计算组合或计算已有值，并保存为 当前处理结果。
如果当前处理结果有值或为真，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果辅助操作产生的可迭代结果（调用 `values` 完成该函数的一项辅助处理）中存在满足“当前字段值不大于0”的项，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果当前处理结果有值或为真 且 当前输入内容不属于当前处理结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果当前输入内容不属于当前处理结果 且 最大查询集合不等于0，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果当前输入内容属于当前处理结果 且 当前输入内容不属于当前处理结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前对象的当前值。
```

#### `RetrievalPolicyRule.validate_query_kinds`

- **源码**：`app/retrieval/policy_schemas.py:130`
- **签名**：`def validate_query_kinds(self) -> RetrievalPolicyRule`
- **作用**：在优化论文方法检索策略、候选排序和离线评测质量的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `RetrievalPolicyRule` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`RetrievalPolicyRule`
- **语义**：返回 `RetrievalPolicyRule` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果辅助操作“构造临时集合、映射或轻量领域对象”的结果 的长度不等于查询集合 的长度，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前对象的当前值。
```

#### `RetrievalPolicyConfig.validate_references`

- **源码**：`app/retrieval/policy_schemas.py:145`
- **签名**：`def validate_references(self) -> RetrievalPolicyConfig`
- **作用**：在优化论文方法检索策略、候选排序和离线评测质量的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `RetrievalPolicyConfig` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`RetrievalPolicyConfig`
- **语义**：返回 `RetrievalPolicyConfig` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
遍历并筛选输入，将整理后的结果保存为 配置集合。
如果辅助操作“构造临时集合、映射或轻量领域对象”的结果 的长度不等于配置集合 的长度，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
构造临时集合、映射或轻量领域对象，并把结果记为 该调用返回的结果。
如果配置的 ID不属于当前处理结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果配置的 ID不属于当前处理结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
调用 `next` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
如果当前处理结果有值或为真 或 当前输入内容属于当前处理结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
遍历并筛选输入，将整理后的结果保存为 当前处理结果。
如果辅助操作“构造临时集合、映射或轻量领域对象”的结果 的长度不等于当前处理结果 的长度，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
遍历当前可迭代输入，每次把当前项记为当前处理结果：
    如果MCP Client 配置档案 ID不属于当前处理结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前对象的当前值。
```

### `app/skills/builtin/cuda_build_diagnosis.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_safe_relative_path`

- **源码**：`app/skills/builtin/cuda_build_diagnosis.py:15`
- **签名**：`def _safe_relative_path(value: str) -> str`
- **作用**：在装载和运行论文复现 Agent Skill/Plugin，并实施清单、权限和调试日志约束的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
去除当前字段值的首尾空白，并把规范化后的文本记为 原始内容。
如果当前输入内容属于原始内容，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
构造 `PurePosixPath` 结构化领域对象，并把结果记为 文件或目录路径；把文件或目录路径转换为稳定的仓库相对路径表示，并把结果记为 规范化后的文本。
如果原始内容为空或为假 或 “调用 `is_absolute` 校验当前输入或状态”后得到肯定结果 或 原始内容不等于规范化后的文本 或 当前输入内容属于拆分后的文本或路径片段集合 或 当前输入内容属于拆分后的文本或路径片段集合中的对应字段 或 规范化后的文本等于'.'，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回规范化后的文本的当前值。
```

#### `CudaBuildDiagnosisInput.validate_paths`

- **源码**：`app/skills/builtin/cuda_build_diagnosis.py:40`
- **签名**：`def validate_paths(cls, value: str) -> str`
- **作用**：在装载和运行论文复现 Agent Skill/Plugin，并实施清单、权限和调试日志约束的阶段中，该函数接收当前字段值，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `cls` | `未显式标注` | 当前类对象，用于类级构造或校验。 |
| `value` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `_safe_relative_path` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `CudaBuildEvidenceRef.validate_optional_path`

- **源码**：`app/skills/builtin/cuda_build_diagnosis.py:52`
- **签名**：`def validate_optional_path(cls, value: str | None) -> str | None`
- **作用**：在装载和运行论文复现 Agent Skill/Plugin，并实施清单、权限和调试日志约束的阶段中，该函数接收当前字段值，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `str | None` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `cls` | `未显式标注` | 当前类对象，用于类级构造或校验。 |
| `value` | `str | None` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str | None`
- **语义**：返回 `str | None` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果当前字段值为空，就返回固定值 `空值`。
调用 `_safe_relative_path` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `CudaBuildDiagnosisOutput.validate_related_files`

- **源码**：`app/skills/builtin/cuda_build_diagnosis.py:80`
- **签名**：`def validate_related_files(cls, value: list[str]) -> list[str]`
- **作用**：在装载和运行论文复现 Agent Skill/Plugin，并实施清单、权限和调试日志约束的阶段中，该函数接收当前字段值，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `cls` | `未显式标注` | 当前类对象，用于类级构造或校验。 |
| `value` | `list[str]` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`list[str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
返回当前计算得到的结果。
```

#### `_last_call_id`

- **源码**：`app/skills/builtin/cuda_build_diagnosis.py:84`
- **签名**：`def _last_call_id(runtime: SkillRuntime) -> str`
- **作用**：在装载和运行论文复现 Agent Skill/Plugin，并实施清单、权限和调试日志约束的阶段中，该函数接收运行时环境，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `runtime` | `SkillRuntime` | 运行时环境；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回稳定业务标识符，用于后续查询、关联或幂等绑定；它不是路径或内容 Hash。

**伪代码**

```text
读取工具集合，并保存为 论文或源码引用证据集合。
如果论文或源码引用证据集合为空或为假，就拒绝继续处理并抛出 `RuntimeError`，向调用方报告输入或运行失败。
返回当前处理结果的 ID的当前值。
```

#### `_classify_findings`

- **源码**：`app/skills/builtin/cuda_build_diagnosis.py:91`
- **签名**：`def _classify_findings(text: str) -> tuple[str, list[str]]`
- **作用**：在装载和运行论文复现 Agent Skill/Plugin，并实施清单、权限和调试日志约束的阶段中，该函数接收待处理文本，用于把论文中的方法、模块或实验意图与仓库中的可验证对象建立稳定关联，并保留匹配依据，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `text` | `str` | 用户目标、检索问题、反馈或待处理文本；会作为当前阶段的业务语境输入，并可能受到长度/脱敏约束。 |

**输出**

- **Python 类型**：`tuple[str, list[str]]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
对待处理文本中的文本执行规范化或拆分，并把结果记为 转为小写的比较文本；将 诊断发现集合 初始化为空列表，用来收集后续结果。
如果当前输入内容属于转为小写的比较文本 且 当前可迭代输入中存在满足“测试或状态标记属于转为小写的比较文本”的项，就把新的处理结果追加或合并到诊断发现集合。
如果当前输入内容属于转为小写的比较文本 或 当前输入内容属于转为小写的比较文本，就把新的处理结果追加或合并到诊断发现集合。
如果当前可迭代输入中存在满足“测试或状态标记属于转为小写的比较文本”的项，就把新的处理结果追加或合并到诊断发现集合。
如果当前可迭代输入中存在满足“测试或状态标记属于转为小写的比较文本”的项，就把新的处理结果追加或合并到诊断发现集合。
如果当前输入内容属于转为小写的比较文本 且 当前可迭代输入中存在满足“测试或状态标记属于转为小写的比较文本”的项，就把新的处理结果追加或合并到诊断发现集合。
如果当前可迭代输入中存在满足“测试或状态标记属于转为小写的比较文本”的项，就把新的处理结果追加或合并到诊断发现集合。
构造临时集合、映射或轻量领域对象，并把结果记为 诊断发现集合。
如果诊断发现集合为空或为假，就返回当前构造的顺序或去重集合。
如果当前输入内容属于诊断发现集合，就返回当前构造的顺序或去重集合。
如果当前输入内容属于诊断发现集合，就返回当前构造的顺序或去重集合。
如果当前输入内容属于诊断发现集合，就返回当前构造的顺序或去重集合。
如果当前输入内容属于诊断发现集合，就返回当前构造的顺序或去重集合。
如果当前输入内容属于诊断发现集合，就返回当前构造的顺序或去重集合。
返回当前构造的顺序或去重集合。
```

#### `_search_keywords`

- **源码**：`app/skills/builtin/cuda_build_diagnosis.py:147`
- **签名**：`def _search_keywords(finding_codes: list[str]) -> list[str]`
- **作用**：在装载和运行论文复现 Agent Skill/Plugin，并实施清单、权限和调试日志约束的阶段中，该函数接收发现集合，用于围绕论文方法语义检索、切分和排序代码证据，为后续方法映射与实验规划提供候选结果，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `finding_codes` | `list[str]` | `list[str]` 元素集合；元素代表的业务对象由参数名 `finding_codes` 和调用位置确定。 |

**输出**

- **Python 类型**：`list[str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
计算按字段初始化键值映射，并保存为 论文-代码映射；将 状态字段集合 初始化为空列表，用来收集后续结果。
遍历由发现集合组成的集合或迭代器，每次把当前项记为待解析或验证的代码，然后把新的处理结果追加或合并到状态字段集合。
返回前一步操作返回对象中的对应字段的当前值。
```

#### `_recommended_checks`

- **源码**：`app/skills/builtin/cuda_build_diagnosis.py:163`
- **签名**：`def _recommended_checks(finding_codes: list[str]) -> list[str]`
- **作用**：在装载和运行论文复现 Agent Skill/Plugin，并实施清单、权限和调试日志约束的阶段中，该函数接收发现集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `finding_codes` | `list[str]` | `list[str]` 元素集合；元素代表的业务对象由参数名 `finding_codes` 和调用位置确定。 |

**输出**

- **Python 类型**：`list[str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
将 校验项集合 初始化为空列表，用来收集后续结果；计算按字段初始化键值映射，并保存为 论文-代码映射。
遍历由发现集合组成的集合或迭代器，每次把当前项记为待解析或验证的代码：
    从论文-代码映射读取所需的状态或领域记录，并把结果记为 校验。
    如果校验有值或为真 且 校验不属于校验项集合，就把校验追加或合并到校验项集合。
返回校验项集合的当前值。
```

#### `diagnose_cuda_build`

- **源码**：`app/skills/builtin/cuda_build_diagnosis.py:200`
- **签名**：`def diagnose_cuda_build(payload: CudaBuildDiagnosisInput, runtime: SkillRuntime) -> CudaBuildDiagnosisOutput`
- **作用**：在装载和运行论文复现 Agent Skill/Plugin，并实施清单、权限和调试日志约束的阶段中，该函数接收结构化请求载荷、运行时环境，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `CudaBuildDiagnosisOutput` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `payload` | `CudaBuildDiagnosisInput` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `runtime` | `SkillRuntime` | 运行时环境；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`CudaBuildDiagnosisOutput`
- **语义**：返回 `CudaBuildDiagnosisOutput` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `call_tool` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `_last_call_id` 完成该函数的一项辅助处理，并把结果记为 当前处理结果的 ID；调用 `str` 完成该函数的一项辅助处理，并把结果记为 当前处理结果的文本；调用 `call_tool` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
调用 `_last_call_id` 完成该函数的一项辅助处理，并把结果记为 当前处理结果的 ID；调用 `str` 完成该函数的一项辅助处理，并把结果记为 异常堆栈文本的文本；调用 `call_tool` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `str` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
调用 `call_tool` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；遍历并筛选输入，将整理后的结果保存为 异常堆栈中的源码路径集合；调用 `_classify_findings` 完成该函数的一项辅助处理，并把结果记为 多个解包结果。
如果错误等于'unknown_cuda_build' 且 当前处理结果等于'dependency_missing'，就计算使用固定配置或常量值，并保存为 错误；计算初始化顺序集合，并保存为 发现集合。
调用 `call_tool` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `_last_call_id` 完成该函数的一项辅助处理，并把结果记为 当前处理结果的 ID；读取前一步操作返回对象中的对应字段，并保存为 后续步骤使用的结果；读取前一步操作返回对象中的对应字段，并保存为 相关源码文件集合。
读取新构造集合中按范围取出的部分，并保存为 证据集合；构造并返回 `CudaBuildDiagnosisOutput` 结构化领域对象。
```

### `app/skills/builtin/restricted_web_research.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `run_restricted_web_research`

- **源码**：`app/skills/builtin/restricted_web_research.py:23`
- **签名**：`def run_restricted_web_research(payload: RestrictedWebResearchInput, runtime: SkillRuntime) -> RestrictedWebResearchOutput`
- **作用**：在装载和运行论文复现 Agent Skill/Plugin，并实施清单、权限和调试日志约束的阶段中，该函数接收结构化请求载荷、运行时环境，用于驱动或监督一次论文复现运行，记录命令、工作目录、资源使用、状态迁移和失败原因，最终标注为 `RestrictedWebResearchOutput` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `payload` | `RestrictedWebResearchInput` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `runtime` | `SkillRuntime` | 运行时环境；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`RestrictedWebResearchOutput`
- **语义**：返回 `RestrictedWebResearchOutput` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `call_tool` 完成该函数的一项辅助处理，并把结果记为 输出结果；构造并返回 `RestrictedWebResearchOutput` 结构化领域对象。
```

### `app/skills/catalog.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_eval_case_path`

- **源码**：`app/skills/catalog.py:46`
- **签名**：`def _eval_case_path(eval_suite: str) -> Path`
- **作用**：在装载和运行论文复现 Agent Skill/Plugin，并实施清单、权限和调试日志约束的阶段中，该函数接收当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个经过边界校验的文件或目录路径。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `eval_suite` | `str` | 名为 `eval_suite` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`Path`
- **语义**：返回解析后的文件或目录路径对象。

**伪代码**

```text
读取前一步操作返回对象的当前处理结果中的对应字段，并保存为 项目根目录；返回当前计算得到的结果。
```

#### `_validate_eval_suite`

- **源码**：`app/skills/catalog.py:57`
- **签名**：`def _validate_eval_suite(manifest: SkillManifest) -> None`
- **作用**：在装载和运行论文复现 Agent Skill/Plugin，并实施清单、权限和调试日志约束的阶段中，该函数接收运行或工作区 Manifest，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `manifest` | `SkillManifest` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_eval_case_path` 完成该函数的一项辅助处理，并把结果记为 文件或目录路径。
如果“检查文件或目录路径的文件系统属性”后得到肯定结果 或 “检查文件或目录路径的文件系统属性”后未得到肯定结果，就拒绝继续处理并抛出 `SkillRegistryError`，向调用方报告输入或运行失败。
如果前一步操作返回对象的当前处理结果大于1024 × 1024，就拒绝继续处理并抛出 `SkillRegistryError`，向调用方报告输入或运行失败。
先尝试完成以下处理：
    将外部表示解析为结构化内容，并把结果记为 结构化请求载荷。
如果出现 `(OSError, UnicodeDecodeError, json.JSONDecodeError)`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `SkillRegistryError`，向调用方报告输入或运行失败。
如果“计算数量、边界或类型判断结果”后未得到肯定结果 或 辅助操作“从结构化请求载荷读取所需的状态或领域记录”的结果不属于{'phase48-v1', 'phase51-v1'} 或 辅助操作“从结构化请求载荷读取所需的状态或领域记录”的结果不等于当前处理结果的 ID 或 辅助操作“从结构化请求载荷读取所需的状态或领域记录”的结果不等于版本 或 “计算数量、边界或类型判断结果”后未得到肯定结果 或 “结构化请求载荷中的对应字段有值或为真”不成立，就拒绝继续处理并抛出 `SkillRegistryError`，向调用方报告输入或运行失败。
```

#### `build_skill_registry`

- **源码**：`app/skills/catalog.py:83`
- **签名**：`def build_skill_registry(package_root: Path, globally_enabled: bool, enabled_skill_ids: set[str], tool_registry: 未显式标注) -> SkillRegistry`
- **作用**：在装载和运行论文复现 Agent Skill/Plugin，并实施清单、权限和调试日志约束的阶段中，从静态实现表和受控 Manifest 构建本进程 Registry。该函数接收根目录、当前处理结果、当前处理结果、工具注册表，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `SkillRegistry` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `package_root` | `Path` | 已经解析的文件或目录路径对象；后续操作仍需遵守仓库/工作区边界。 |
| `globally_enabled` | `bool` | 布尔条件或能力开关，用于控制流程分支。 |
| `enabled_skill_ids` | `set[str]` | `set[str]` 元素集合；元素代表的业务对象由参数名 `enabled_skill_ids` 和调用位置确定。 |
| `tool_registry` | `未显式标注` | 名为 `tool_registry` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。；默认 空值 |

**输出**

- **Python 类型**：`SkillRegistry`
- **语义**：返回 `SkillRegistry` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
计算计算当前表达式的结果，并保存为 当前处理结果；构造 `SkillRegistry` 结构化领域对象，并把结果记为 组件注册表。
遍历辅助操作产生的可迭代结果（调用 `discover_skill_packages` 完成该函数的一项辅助处理），每次把当前项记为当前处理结果：
    读取当前处理结果的 ID，并保存为 当前处理结果的 ID；从当前处理结果读取所需的状态或领域记录，并把结果记为 契约定义。
    如果契约定义为空，就拒绝继续处理并抛出 `SkillRegistryError`，向调用方报告输入或运行失败。
    调用 `_validate_eval_suite` 校验当前输入或状态；计算计算当前表达式的结果，并保存为 功能是否启用的开关；遍历并筛选输入，将整理后的结果保存为 工具集合。
    如果功能是否启用的开关为空或为假 且 “调用 `issubset` 完成该函数的一项辅助处理”后未得到肯定结果，就跳过本轮剩余处理，直接进入下一轮。
    调用 `register` 完成该函数的一项辅助处理。
返回组件注册表的当前值。
```

### `app/skills/loader.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_canonical_json_bytes`

- **源码**：`app/skills/loader.py:32`
- **签名**：`def _canonical_json_bytes(value: Any) -> bytes`
- **作用**：在装载和运行论文复现 Agent Skill/Plugin，并实施清单、权限和调试日志约束的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `bytes` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `Any` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`bytes`
- **语义**：返回 `bytes` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
将结构化内容序列化或编码为可传输表示，并返回处理结果。
```

#### `_sha256_bytes`

- **源码**：`app/skills/loader.py:41`
- **签名**：`def _sha256_bytes(value: bytes) -> str`
- **作用**：在装载和运行论文复现 Agent Skill/Plugin，并实施清单、权限和调试日志约束的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `bytes` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回输入内容的 SHA-256 身份摘要，用于完整性校验，不是加密后的正文。

**伪代码**

```text
计算输入内容的 SHA-256 身份摘要，并返回处理结果。
```

#### `_is_within`

- **源码**：`app/skills/loader.py:45`
- **签名**：`def _is_within(path: Path, root: Path) -> bool`
- **作用**：在装载和运行论文复现 Agent Skill/Plugin，并实施清单、权限和调试日志约束的阶段中，该函数接收文件或目录路径、受控扫描根目录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |
| `root` | `Path` | 运行产物或受控工作区的目录路径；用于隔离本次运行生成的文件。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
返回组合判断结果。
```

#### `_read_bounded_file`

- **源码**：`app/skills/loader.py:49`
- **签名**：`def _read_bounded_file(path: Path, *, max_bytes: int) -> bytes`
- **作用**：在装载和运行论文复现 Agent Skill/Plugin，并实施清单、权限和调试日志约束的阶段中，该函数接收文件或目录路径、读取字节数上限，用于读取并整理论文、源码或运行产物，把原始输入转换成带位置和身份信息的结构化证据，最终标注为 `bytes` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |
| `max_bytes` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。 |

**输出**

- **Python 类型**：`bytes`
- **语义**：返回 `bytes` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果“检查文件或目录路径的文件系统属性”后得到肯定结果，就拒绝继续处理并抛出 `SkillPackageError`，向调用方报告输入或运行失败。
如果“检查文件或目录路径的文件系统属性”后未得到肯定结果，就拒绝继续处理并抛出 `SkillPackageError`，向调用方报告输入或运行失败。
如果前一步操作返回对象的当前处理结果大于读取字节数上限，就拒绝继续处理并抛出 `SkillPackageError`，向调用方报告输入或运行失败。
读取文件或目录路径中的文件内容，并返回处理结果。
```

#### `load_skill_package`

- **源码**：`app/skills/loader.py:59`
- **签名**：`def load_skill_package(package_dir: Path, package_root: Path) -> DiscoveredSkillPackage`
- **作用**：在装载和运行论文复现 Agent Skill/Plugin，并实施清单、权限和调试日志约束的阶段中，加载一个直接子目录，并验证其 Manifest 与全部资源。该函数接收当前处理结果的目录、根目录，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `DiscoveredSkillPackage` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `package_dir` | `Path` | 已经解析的文件或目录路径对象；后续操作仍需遵守仓库/工作区边界。 |
| `package_root` | `Path` | 已经解析的文件或目录路径对象；后续操作仍需遵守仓库/工作区边界。 |

**输出**

- **Python 类型**：`DiscoveredSkillPackage`
- **语义**：返回从外部表示解析并校验后的领域值；格式非法时通过异常失败。

**伪代码**

```text
将根目录规范化为受控的绝对路径，并把结果记为 根目录；将当前处理结果的目录规范化为受控的绝对路径，并把结果记为 该调用返回的结果。
如果“检查根目录的文件系统属性”后得到肯定结果 或 “检查当前处理结果的文件系统属性”后得到肯定结果，就拒绝继续处理并抛出 `SkillPackageError`，向调用方报告输入或运行失败。
将根目录规范化为受控的绝对路径，并把结果记为 受控扫描根目录；将当前处理结果规范化为受控的绝对路径，并把结果记为 该调用返回的结果。
如果“检查当前处理结果的文件系统属性”后未得到肯定结果 或 父级目录或父领域对象不等于受控扫描根目录，就拒绝继续处理并抛出 `SkillPackageError`，向调用方报告输入或运行失败。
计算组合或计算已有值，并保存为 运行或工作区 Manifest的路径；调用 `_read_bounded_file` 读取或查询当前阶段需要的数据，并把结果记为 运行或工作区 Manifest的字节内容。
先尝试完成以下处理：
    将外部表示解析为结构化内容，并把结果记为 Manifest。
    如果“计算数量、边界或类型判断结果”后未得到肯定结果，就拒绝继续处理并抛出 `SkillPackageError`，向调用方报告输入或运行失败。
    复制、序列化或校验结构化领域对象，并把结果记为 运行或工作区 Manifest。
如果出现 `(UnicodeDecodeError, json.JSONDecodeError, ValidationError)`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `SkillPackageError`，向调用方报告输入或运行失败。
如果对象名称不等于当前处理结果的 ID，就拒绝继续处理并抛出 `SkillPackageError`，向调用方报告输入或运行失败。
遍历并筛选输入，将整理后的结果保存为 当前处理结果；将 实际集合 初始化为空去重集合，用来收集后续结果。
遍历辅助操作产生的可迭代结果（枚举当前处理结果下符合范围的文件系统项），每次把当前项记为子级目录或子领域对象：
    如果“检查子级目录或子领域对象的文件系统属性”后得到肯定结果，就拒绝继续处理并抛出 `SkillPackageError`，向调用方报告输入或运行失败。
    如果“检查子级目录或子领域对象的文件系统属性”后得到肯定结果，就跳过本轮剩余处理，直接进入下一轮。
    把辅助操作“把子级目录或子领域对象转换为稳定的仓库相对路径表示”的结果转换为稳定的仓库相对路径表示，并把结果记为 仓库相对路径。
    如果仓库相对路径等于'skill.json'，就跳过本轮剩余处理，直接进入下一轮。
    把仓库相对路径追加或合并到实际集合。
如果实际集合不等于辅助操作“构造临时集合、映射或轻量领域对象”的结果，就拒绝继续处理并抛出 `SkillPackageError`，向调用方报告输入或运行失败。
将 当前处理结果 初始化为空列表，用来收集后续结果。
遍历辅助操作产生的可迭代结果（按稳定规则整理结果顺序），每次把当前项记为仓库内相对路径：
    计算组合或计算已有值，并保存为 复现输入资源；将复现输入资源规范化为受控的绝对路径，并把结果记为 解析后的值。
    如果“调用 `_is_within` 校验当前输入或状态”后未得到肯定结果，就拒绝继续处理并抛出 `SkillPackageError`，向调用方报告输入或运行失败。
    调用 `_read_bounded_file` 读取或查询当前阶段需要的数据，并把结果记为 业务内容；调用 `_sha256_bytes` 计算内容身份、分数或派生结果，并把结果记为 实际值的 SHA-256。
    如果实际值的 SHA-256不等于当前处理结果中的对应字段，就拒绝继续处理并抛出 `SkillPackageError`，向调用方报告输入或运行失败。
    把新的处理结果追加或合并到当前处理结果。
调用 `_canonical_json_bytes` 完成该函数的一项辅助处理，并把结果记为 规范化Manifest；调用 `_sha256_bytes` 计算内容身份、分数或派生结果，并把结果记为 运行或工作区 Manifest的 SHA-256；调用 `_sha256_bytes` 计算内容身份、分数或派生结果，并把结果记为 当前处理结果的 SHA-256；构造并返回 `DiscoveredSkillPackage` 结构化领域对象。
```

#### `discover_skill_packages`

- **源码**：`app/skills/loader.py:153`
- **签名**：`def discover_skill_packages(package_root: Path) -> list[DiscoveredSkillPackage]`
- **作用**：在装载和运行论文复现 Agent Skill/Plugin，并实施清单、权限和调试日志约束的阶段中，按 skill_id 稳定排序发现有限数量的 Plugin Package。该函数接收根目录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `package_root` | `Path` | 已经解析的文件或目录路径对象；后续操作仍需遵守仓库/工作区边界。 |

**输出**

- **Python 类型**：`list[DiscoveredSkillPackage]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
将根目录规范化为受控的绝对路径，并把结果记为 该调用返回的结果。
如果“检查当前处理结果的文件系统属性”后得到肯定结果，就拒绝继续处理并抛出 `SkillPackageError`，向调用方报告输入或运行失败。
如果“检查当前处理结果的文件系统属性”后未得到肯定结果，就返回当前构造的顺序或去重集合。
将当前处理结果规范化为受控的绝对路径，并把结果记为 受控扫描根目录。
如果“检查受控扫描根目录的文件系统属性”后未得到肯定结果，就拒绝继续处理并抛出 `SkillPackageError`，向调用方报告输入或运行失败。
按稳定规则整理结果顺序，并把结果记为 子级目录或子领域对象集合。
如果子级目录或子领域对象集合 的长度大于最大当前处理结果，就拒绝继续处理并抛出 `SkillPackageError`，向调用方报告输入或运行失败。
将 当前处理结果 初始化为空列表，用来收集后续结果。
遍历由子级目录或子领域对象集合组成的集合或迭代器，每次把当前项记为子级目录或子领域对象：
    如果“检查子级目录或子领域对象的文件系统属性”后得到肯定结果 或 “检查子级目录或子领域对象的文件系统属性”后未得到肯定结果，就拒绝继续处理并抛出 `SkillPackageError`，向调用方报告输入或运行失败。
    把新的处理结果追加或合并到当前处理结果。
返回前一步处理得到的结果。
```

### `app/skills/registry.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `SkillAuditSink.write`

- **源码**：`app/skills/registry.py:55`
- **签名**：`def write(self, record: SkillInvocationRecord) -> None`
- **作用**：在装载和运行论文复现 Agent Skill/Plugin，并实施清单、权限和调试日志约束的阶段中，该函数接收领域记录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `record` | `SkillInvocationRecord` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `InMemorySkillAuditSink.__init__`

- **源码**：`app/skills/registry.py:60`
- **签名**：`def __init__(self) -> None`
- **作用**：在装载和运行论文复现 Agent Skill/Plugin，并实施清单、权限和调试日志约束的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
将 领域记录集合 初始化为空列表，用来收集后续结果。
```

#### `InMemorySkillAuditSink.write`

- **源码**：`app/skills/registry.py:63`
- **签名**：`def write(self, record: SkillInvocationRecord) -> None`
- **作用**：在装载和运行论文复现 Agent Skill/Plugin，并实施清单、权限和调试日志约束的阶段中，该函数接收领域记录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `record` | `SkillInvocationRecord` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把领域记录追加或合并到领域记录集合。
```

#### `NullSkillAuditSink.write`

- **源码**：`app/skills/registry.py:68`
- **签名**：`def write(self, record: SkillInvocationRecord) -> None`
- **作用**：在装载和运行论文复现 Agent Skill/Plugin，并实施清单、权限和调试日志约束的阶段中，该函数接收领域记录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `record` | `SkillInvocationRecord` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
移除领域记录中的当前内容。
```

#### `_utc_now`

- **源码**：`app/skills/registry.py:100`
- **签名**：`def _utc_now() -> str`
- **作用**：在装载和运行论文复现 Agent Skill/Plugin，并实施清单、权限和调试日志约束的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `isoformat` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `_canonical_json_bytes`

- **源码**：`app/skills/registry.py:104`
- **签名**：`def _canonical_json_bytes(value: Any) -> bytes`
- **作用**：在装载和运行论文复现 Agent Skill/Plugin，并实施清单、权限和调试日志约束的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `bytes` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `Any` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`bytes`
- **语义**：返回 `bytes` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果“计算数量、边界或类型判断结果”后得到肯定结果，就复制、序列化或校验结构化领域对象，并把结果记为 当前字段值。
将结构化内容序列化或编码为可传输表示，并返回处理结果。
```

#### `_sha256`

- **源码**：`app/skills/registry.py:116`
- **签名**：`def _sha256(value: Any) -> str`
- **作用**：在装载和运行论文复现 Agent Skill/Plugin，并实施清单、权限和调试日志约束的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `Any` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回输入内容的 SHA-256 身份摘要，用于完整性校验，不是加密后的正文。

**伪代码**

```text
计算输入内容的 SHA-256 身份摘要，并返回处理结果。
```

#### `_assert_no_authority_keys`

- **源码**：`app/skills/registry.py:120`
- **签名**：`def _assert_no_authority_keys(value: Any, *, path: str = "output") -> None`
- **作用**：在装载和运行论文复现 Agent Skill/Plugin，并实施清单、权限和调试日志约束的阶段中，该函数接收当前字段值、文件或目录路径，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `Any` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |
| `path` | `str` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。；默认 'output' |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
如果“计算数量、边界或类型判断结果”后得到肯定结果：
    遍历辅助操作产生的可迭代结果（调用 `items` 完成该函数的一项辅助处理），每次把当前项记为多个解包结果：
        调用 `str` 完成该函数的一项辅助处理，再对返回文本执行规范化或拆分，再对返回文本执行规范化或拆分，并把结果记为 规范化后的文本。
        如果规范化后的文本属于键集合集合，就拒绝继续处理并抛出 `SkillRegistryError`，向调用方报告输入或运行失败。
        调用 `_assert_no_authority_keys` 完成该函数的一项辅助处理。
否则：
    如果“计算数量、边界或类型判断结果”后得到肯定结果：
        遍历带顺序编号的输入集合，每次把当前项记为多个解包结果，然后调用 `_assert_no_authority_keys` 完成该函数的一项辅助处理。
```

#### `SkillRegistry.__init__`

- **源码**：`app/skills/registry.py:141`
- **签名**：`def __init__(self, *, tool_registry: ToolRegistry) -> None`
- **作用**：在装载和运行论文复现 Agent Skill/Plugin，并实施清单、权限和调试日志约束的阶段中，该函数接收工具注册表，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `tool_registry` | `ToolRegistry` | 名为 `tool_registry` 的 `ToolRegistry` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入参数保存到实例字段（工具注册表 → 工具注册表）；将 当前处理结果 初始化为空映射，用来收集后续结果。
```

#### `SkillRegistry.register`

- **源码**：`app/skills/registry.py:145`
- **签名**：`def register(self: 未显式标注, package: DiscoveredSkillPackage, definition: SkillDefinition, enabled: bool) -> BoundSkill`
- **作用**：在装载和运行论文复现 Agent Skill/Plugin，并实施清单、权限和调试日志约束的阶段中，该函数接收当前处理结果、契约定义、功能是否启用的开关，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `BoundSkill` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `package` | `DiscoveredSkillPackage` | 名为 `package` 的 `DiscoveredSkillPackage` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `definition` | `SkillDefinition` | 契约定义；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `enabled` | `bool` | 布尔条件或能力开关，用于控制流程分支。 |

**输出**

- **Python 类型**：`BoundSkill`
- **语义**：返回 `BoundSkill` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
读取运行或工作区 Manifest，并保存为 运行或工作区 Manifest。
如果当前处理结果的 ID属于当前处理结果，就拒绝继续处理并抛出 `SkillRegistryError`，向调用方报告输入或运行失败。
如果当前处理结果的 ID不等于当前处理结果的 ID，就拒绝继续处理并抛出 `SkillRegistryError`，向调用方报告输入或运行失败。
如果MCP Tool 输入 Schema的 ID不等于MCP Tool 输入 Schema的 ID，就拒绝继续处理并抛出 `SkillRegistryError`，向调用方报告输入或运行失败。
如果MCP Tool 输出 Schema的 ID不等于MCP Tool 输出 Schema的 ID，就拒绝继续处理并抛出 `SkillRegistryError`，向调用方报告输入或运行失败。
构造临时集合、映射或轻量领域对象，并把结果记为 调用参数集合。
如果调用参数集合 的长度不等于2 或 由调用参数集合组成的集合或迭代器中存在满足“业务类别属于{当前处理结果, 关键词}”的项，就拒绝继续处理并抛出 `SkillRegistryError`，向调用方报告输入或运行失败。
将 工具集合 初始化为空列表，用来收集后续结果；构造临时集合、映射或轻量领域对象，并把结果记为 Manifest集合。
遍历辅助操作产生的可迭代结果（按稳定规则整理结果顺序），每次把当前项记为要求：
    先尝试完成以下处理：
        从工具注册表读取所需的状态或领域记录，并把结果记为 受控工具定义。
    如果出现 `Exception`并把异常保存为捕获的异常对象：
        拒绝继续处理并抛出 `SkillRegistryError`，向调用方报告输入或运行失败。
    读取契约，并保存为 契约。
    如果记录版本号不等于记录版本号，就拒绝继续处理并抛出 `SkillRegistryError`，向调用方报告输入或运行失败。
    如果当前处理结果不等于当前处理结果，就拒绝继续处理并抛出 `SkillRegistryError`，向调用方报告输入或运行失败。
    计算计算当前表达式的结果，并保存为 是否当前处理结果。
    如果“当前处理结果有值或为真”不成立 且 是否当前处理结果为空或为假，就拒绝继续处理并抛出 `SkillRegistryError`，向调用方报告输入或运行失败。
    如果“调用 `issubset` 完成该函数的一项辅助处理”后未得到肯定结果，就拒绝继续处理并抛出 `SkillRegistryError`，向调用方报告输入或运行失败。
    如果“调用 `issubset` 完成该函数的一项辅助处理”后未得到肯定结果，就拒绝继续处理并抛出 `SkillRegistryError`，向调用方报告输入或运行失败。
    如果当前处理结果属于当前处理结果 且 当前输入内容不属于当前处理结果，就拒绝继续处理并抛出 `SkillRegistryError`，向调用方报告输入或运行失败。
    如果当前处理结果属于当前处理结果 且 对象名称不等于'browser.collect_research_evidence' 或 辅助操作“构造临时集合、映射或轻量领域对象”的结果不等于{'network.read.research'}，就拒绝继续处理并抛出 `SkillRegistryError`，向调用方报告输入或运行失败。
    把新的处理结果追加或合并到工具集合。
调用 `getmodule` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
如果当前处理结果为空，就拒绝继续处理并抛出 `SkillRegistryError`，向调用方报告输入或运行失败。
先尝试完成以下处理：
    调用 `getsource` 完成该函数的一项辅助处理，并把结果记为 来源。
如果出现 `(OSError, TypeError)`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `SkillRegistryError`，向调用方报告输入或运行失败。
调用 `_sha256` 计算内容身份、分数或派生结果，并把结果记为 当前处理结果的 SHA-256；构造 `BoundSkill` 结构化领域对象，并把结果记为 边界值；读取边界值，并保存为 当前处理结果中的对应字段；返回边界值的当前值。
```

#### `SkillRegistry.get`

- **源码**：`app/skills/registry.py:270`
- **签名**：`def get(self, skill_id: str) -> BoundSkill`
- **作用**：在装载和运行论文复现 Agent Skill/Plugin，并实施清单、权限和调试日志约束的阶段中，该函数接收当前处理结果的 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `BoundSkill` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `skill_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`BoundSkill`
- **语义**：返回 `BoundSkill` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
先尝试完成以下处理：
    返回当前处理结果中的对应字段的当前值。
如果出现 `KeyError`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `SkillRegistryError`，向调用方报告输入或运行失败。
```

#### `SkillRegistry.names`

- **源码**：`app/skills/registry.py:276`
- **签名**：`def names(self) -> list[str]`
- **作用**：在装载和运行论文复现 Agent Skill/Plugin，并实施清单、权限和调试日志约束的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`list[str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
按稳定规则整理结果顺序，并返回处理结果。
```

#### `SkillRegistry.catalog_snapshot`

- **源码**：`app/skills/registry.py:279`
- **签名**：`def catalog_snapshot(self) -> list[SkillCatalogEntry]`
- **作用**：在装载和运行论文复现 Agent Skill/Plugin，并实施清单、权限和调试日志约束的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`list[SkillCatalogEntry]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
将 记录条目集合 初始化为空列表，用来收集后续结果。
遍历辅助操作产生的可迭代结果（调用 `names` 完成该函数的一项辅助处理），每次把当前项记为对象名称，然后读取当前处理结果中的对应字段，并保存为 边界值；读取运行或工作区 Manifest，并保存为 运行或工作区 Manifest；把新的处理结果追加或合并到记录条目集合。
返回记录条目集合的当前值。
```

#### `SkillRegistry.invoke`

- **源码**：`app/skills/registry.py:314`
- **签名**：`def invoke(self: 未显式标注, request: SkillInvocationRequest, context: SkillInvocationContext, audit_sink: SkillAuditSink | None) -> SkillExecutionResult`
- **作用**：在装载和运行论文复现 Agent Skill/Plugin，并实施清单、权限和调试日志约束的阶段中，该函数接收业务请求、运行上下文、审计事件接收端，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `request` | `SkillInvocationRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `context` | `SkillInvocationContext` | 运行上下文；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `audit_sink` | `SkillAuditSink | None` | 审计事件接收端；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 空值 |

**输出**

- **Python 类型**：`SkillExecutionResult`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
从当前对象读取所需的状态或领域记录，并把结果记为 边界值；计算计算当前表达式的结果，并保存为 日志或观测数据接收端；读取当前时间，作为状态变更的统一时间戳，并把结果记为 运行启动时间；调用 `perf_counter` 完成该函数的一项辅助处理，并把结果记为 运行是否已经启动的判断。
调用 `_sha256` 计算内容身份、分数或派生结果，并把结果记为 输入内容的 SHA-256；计算使用固定配置或常量值，并保存为 运行时环境。
如果“功能是否启用的开关有值或为真”不成立，就调用 `_failed_result` 完成该函数的一项辅助处理，并返回处理结果。
读取运行或工作区 Manifest，并保存为 运行或工作区 Manifest。
如果版本不等于版本，就调用 `_failed_result` 完成该函数的一项辅助处理，并返回处理结果。
如果期望的 SHA-256不等于当前处理结果的 SHA-256，就调用 `_failed_result` 完成该函数的一项辅助处理，并返回处理结果。
如果“调用 `issubset` 完成该函数的一项辅助处理”后未得到肯定结果，就调用 `_failed_result` 完成该函数的一项辅助处理，并返回处理结果。
先尝试完成以下处理：
    复制、序列化或校验结构化领域对象，并把结果记为 结构化请求载荷。
如果出现 `ValidationError`：
    调用 `_failed_result` 完成该函数的一项辅助处理，并返回处理结果。
构造 `SkillRuntime` 结构化领域对象，并把结果记为 运行时环境。
先尝试完成以下处理：
    调用 `handler` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；复制、序列化或校验结构化领域对象，并把结果记为 输出结果；复制、序列化或校验结构化领域对象，并把结果记为 该调用返回的结果；调用 `_assert_no_authority_keys` 完成该函数的一项辅助处理。
如果出现 `SkillRuntimeError`并把异常保存为捕获的异常对象：
    构造 `SkillFailure` 结构化领域对象，并把结果记为 失败；调用 `_failed_result` 完成该函数的一项辅助处理，并返回处理结果。
如果出现 `ValidationError`：
    调用 `_failed_result` 完成该函数的一项辅助处理，并返回处理结果。
如果出现 `SkillRegistryError`：
    调用 `_failed_result` 完成该函数的一项辅助处理，并返回处理结果。
如果出现 `Exception`：
    调用 `_failed_result` 完成该函数的一项辅助处理，并返回处理结果。
计算组合或计算已有值，并保存为 当前处理结果。
如果当前处理结果大于最大当前处理结果，就调用 `_failed_result` 完成该函数的一项辅助处理，并返回处理结果。
构造 `SkillInvocationRecord` 结构化领域对象，并把结果记为 领域记录；向终端或输出流写出当前结果/诊断信息；构造并返回 `SkillExecutionResult` 结构化领域对象。
```

#### `SkillRegistry._failed_result`

- **源码**：`app/skills/registry.py:520`
- **签名**：`def _failed_result(bound: BoundSkill, context: SkillInvocationContext, sink: SkillAuditSink, started: float, started_at: str, input_sha256: str, failure: SkillFailure, runtime: SkillRuntime | None) -> SkillExecutionResult`
- **作用**：在装载和运行论文复现 Agent Skill/Plugin，并实施清单、权限和调试日志约束的阶段中，该函数接收边界值、运行上下文、日志或观测数据接收端、运行是否已经启动的判断等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `bound` | `BoundSkill` | 边界值；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `context` | `SkillInvocationContext` | 运行上下文；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `sink` | `SkillAuditSink` | 日志或观测数据接收端；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `started` | `float` | 运行是否已经启动的判断；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `started_at` | `str` | 运行启动时间；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `input_sha256` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |
| `failure` | `SkillFailure` | 名为 `failure` 的 `SkillFailure` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `runtime` | `SkillRuntime | None` | 运行时环境；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 空值 |

**输出**

- **Python 类型**：`SkillExecutionResult`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
读取运行或工作区 Manifest，并保存为 运行或工作区 Manifest；构造 `SkillInvocationRecord` 结构化领域对象，并把结果记为 领域记录；向终端或输出流写出当前结果/诊断信息；构造并返回 `SkillExecutionResult` 结构化领域对象。
```

### `app/skills/runtime.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `SkillRuntimeError.__init__`

- **源码**：`app/skills/runtime.py:30`
- **签名**：`def __init__(self: 未显式标注, code: str, category: str, message: str, retryable: bool) -> None`
- **作用**：在装载和运行论文复现 Agent Skill/Plugin，并实施清单、权限和调试日志约束的阶段中，该函数接收待解析或验证的代码、评测类别、面向用户或日志的提示信息、是否允许重试的判断，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `code` | `str` | 待解析、执行或断言的代码文本；处理前应处于受控测试/执行边界内。 |
| `category` | `str` | 评测类别；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `message` | `str` | 对话消息记录或消息文本；角色、顺序和内容 Hash 可能参与证据校验。 |
| `retryable` | `bool` | 布尔条件或能力开关，用于控制流程分支。；默认 假 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `__init__` 完成该函数的一项辅助处理；把传入参数保存到实例字段（待解析或验证的代码 → 待解析或验证的代码、评测类别 → 评测类别、面向用户或日志的提示信息 → 当前处理结果、是否允许重试的判断 → 是否允许重试的判断）。
```

#### `SkillRuntime.__init__`

- **源码**：`app/skills/runtime.py:48`
- **签名**：`def __init__(self: 未显式标注, manifest: SkillManifest, tool_registry: ToolRegistry, context: SkillInvocationContext) -> None`
- **作用**：在装载和运行论文复现 Agent Skill/Plugin，并实施清单、权限和调试日志约束的阶段中，该函数接收运行或工作区 Manifest、工具注册表、运行上下文，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `manifest` | `SkillManifest` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |
| `tool_registry` | `ToolRegistry` | 名为 `tool_registry` 的 `ToolRegistry` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `context` | `SkillInvocationContext` | 运行上下文；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入参数保存到实例字段（运行或工作区 Manifest → 运行或工作区 Manifest、工具注册表 → 工具注册表、运行上下文 → 运行上下文）；遍历并筛选输入，将整理后的结果保存为 运行要求集合；构造 `InMemoryToolAuditSink` 结构化领域对象，并把结果记为 审计事件接收端；将 工具集合 初始化为空列表，用来收集后续结果。
```

#### `SkillRuntime.tool_call_refs`

- **源码**：`app/skills/runtime.py:66`
- **签名**：`def tool_call_refs(self) -> list[SkillToolCallRef]`
- **作用**：在装载和运行论文复现 Agent Skill/Plugin，并实施清单、权限和调试日志约束的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`list[SkillToolCallRef]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
构造临时集合、映射或轻量领域对象，并返回处理结果。
```

#### `SkillRuntime.call_tool`

- **源码**：`app/skills/runtime.py:69`
- **签名**：`def call_tool(self: 未显式标注, name: str, raw_input: dict[str, Any]) -> dict[str, Any]`
- **作用**：在装载和运行论文复现 Agent Skill/Plugin，并实施清单、权限和调试日志约束的阶段中，该函数接收对象名称、当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `name` | `str` | 对象名称；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `raw_input` | `dict[str, Any]` | 名为 `raw_input` 的键值映射；键和值分别承载的业务字段由读取/写入分支确定。 |

**输出**

- **Python 类型**：`dict[str, Any]`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
如果对象名称不属于运行要求集合，就拒绝继续处理并抛出 `SkillRuntimeError`，向调用方报告输入或运行失败。
如果工具集合 的长度不小于最大工具集合，就拒绝继续处理并抛出 `SkillRuntimeError`，向调用方报告输入或运行失败。
先尝试完成以下处理：
    从工具注册表读取所需的状态或领域记录，并把结果记为 契约定义。
如果出现 `Exception`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `SkillRuntimeError`，向调用方报告输入或运行失败。
读取契约，并保存为 契约。
如果记录版本号不等于运行要求集合中的对应字段，就拒绝继续处理并抛出 `SkillRuntimeError`，向调用方报告输入或运行失败。
如果当前处理结果不等于当前处理结果，就拒绝继续处理并抛出 `SkillRuntimeError`，向调用方报告输入或运行失败。
计算计算当前表达式的结果，并保存为 是否当前处理结果。
如果“当前处理结果有值或为真”不成立 且 是否当前处理结果为空或为假，就拒绝继续处理并抛出 `SkillRuntimeError`，向调用方报告输入或运行失败。
如果“调用 `issubset` 完成该函数的一项辅助处理”后未得到肯定结果，就拒绝继续处理并抛出 `SkillRuntimeError`，向调用方报告输入或运行失败。
构造临时集合、映射或轻量领域对象，并把结果记为 Manifest集合；构造临时集合、映射或轻量领域对象，并把结果记为 该调用返回的结果；构造临时集合、映射或轻量领域对象，并把结果记为 工具集合。
如果“调用 `issubset` 完成该函数的一项辅助处理”后未得到肯定结果，就拒绝继续处理并抛出 `SkillRuntimeError`，向调用方报告输入或运行失败。
如果“调用 `issubset` 完成该函数的一项辅助处理”后未得到肯定结果，就拒绝继续处理并抛出 `SkillRuntimeError`，向调用方报告输入或运行失败。
如果当前处理结果属于当前处理结果 且 当前输入内容不属于工具集合，就拒绝继续处理并抛出 `SkillRuntimeError`，向调用方报告输入或运行失败。
如果当前处理结果属于当前处理结果 且 对象名称不等于'browser.collect_research_evidence' 或 辅助操作“构造临时集合、映射或轻量领域对象”的结果不等于{'network.read.research'}，就拒绝继续处理并抛出 `SkillRuntimeError`，向调用方报告输入或运行失败。
调用工具注册表完成模型或 Runnable 处理，并把结果记为 阶段处理结果；构造 `SkillToolCallRef` 结构化领域对象，并把结果记为 论文或源码引用证据；把论文或源码引用证据追加或合并到工具集合。
如果失败不为空，就拒绝继续处理并抛出 `SkillRuntimeError`，向调用方报告输入或运行失败。
返回组合判断结果。
```

### `app/skills/schemas.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `SkillResource.validate_relative_path`

- **源码**：`app/skills/schemas.py:40`
- **签名**：`def validate_relative_path(cls, value: str) -> str`
- **作用**：在装载和运行论文复现 Agent Skill/Plugin，并实施清单、权限和调试日志约束的阶段中，该函数接收当前字段值，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `cls` | `未显式标注` | 当前类对象，用于类级构造或校验。 |
| `value` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
去除当前字段值的首尾空白，并把规范化后的文本记为 原始内容。
如果当前输入内容属于原始内容，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
构造 `PurePosixPath` 结构化领域对象，并把结果记为 文件或目录路径；把文件或目录路径转换为稳定的仓库相对路径表示，并把结果记为 规范化后的文本。
如果原始内容为空或为假 或 “调用 `is_absolute` 校验当前输入或状态”后得到肯定结果 或 原始内容不等于规范化后的文本 或 “检查规范化后的文本是否满足文本匹配条件”后得到肯定结果 或 当前输入内容属于拆分后的文本或路径片段集合 或 当前输入内容属于拆分后的文本或路径片段集合中的对应字段，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回规范化后的文本的当前值。
```

#### `SkillManifest.validate_manifest`

- **源码**：`app/skills/schemas.py:108`
- **签名**：`def validate_manifest(self) -> SkillManifest`
- **作用**：在装载和运行论文复现 Agent Skill/Plugin，并实施清单、权限和调试日志约束的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`SkillManifest`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
遍历并筛选输入，将整理后的结果保存为 工具集合。
如果工具集合 的长度不等于辅助操作“构造临时集合、映射或轻量领域对象”的结果 的长度，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果当前处理结果 的长度不等于辅助操作“构造临时集合、映射或轻量领域对象”的结果 的长度，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
遍历并筛选输入，将整理后的结果保存为 资源集合。
如果资源集合 的长度不等于辅助操作“构造临时集合、映射或轻量领域对象”的结果 的长度，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果当前处理结果不等于格式化文本：f'skill.{self.skill_id}'，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前对象的当前值。
```

#### `SkillExecutionResult.validate_shape`

- **源码**：`app/skills/schemas.py:193`
- **签名**：`def validate_shape(self) -> SkillExecutionResult`
- **作用**：在装载和运行论文复现 Agent Skill/Plugin，并实施清单、权限和调试日志约束的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`SkillExecutionResult`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
如果当前状态等于'succeeded'：
    如果输出结果为空 或 失败不为空，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
否则：
    如果失败为空 或 输出结果不为空，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前对象的当前值。
```

### `app/tool_calling/catalog.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_walk_schema`

- **源码**：`app/tool_calling/catalog.py:37`
- **签名**：`def _walk_schema(value: Any) -> None`
- **作用**：在在 Schema、预算和只读证据边界内编排论文复现 Agent 的有界 Tool Calling 阶段中，拒绝远程引用和异常大的模型输入 Schema。该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `Any` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
如果“计算数量、边界或类型判断结果”后得到肯定结果：
    遍历辅助操作产生的可迭代结果（调用 `items` 完成该函数的一项辅助处理），每次把当前项记为多个解包结果：
        如果映射键或对象字段名等于'$ref' 且 “计算数量、边界或类型判断结果”后未得到肯定结果 或 “检查子级目录或子领域对象是否满足文本匹配条件”后未得到肯定结果，就拒绝继续处理并抛出 `ToolCatalogError`，向调用方报告输入或运行失败。
        调用 `_walk_schema` 完成该函数的一项辅助处理。
否则：
    如果“计算数量、边界或类型判断结果”后得到肯定结果：
        遍历由当前字段值组成的集合或迭代器，每次把当前项记为子级目录或子领域对象，然后调用 `_walk_schema` 完成该函数的一项辅助处理。
```

#### `_strict_parameters`

- **源码**：`app/tool_calling/catalog.py:53`
- **签名**：`def _strict_parameters(schema: dict[str, Any]) -> dict[str, Any]`
- **作用**：在在 Schema、预算和只读证据边界内编排论文复现 Agent 的有界 Tool Calling 阶段中，该函数接收输入输出 Schema 契约，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `schema` | `dict[str, Any]` | 结构化输出 Schema 或其名称；用于约束解析结果的字段和类型。 |

**输出**

- **Python 类型**：`dict[str, Any]`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
复制、序列化或校验结构化领域对象，并把结果记为 调用参数集合。
如果辅助操作“从调用参数集合读取所需的状态或领域记录”的结果不等于'object'，就拒绝继续处理并抛出 `ToolCatalogError`，向调用方报告输入或运行失败。
如果辅助操作“从调用参数集合读取所需的状态或领域记录”的结果不是假，就拒绝继续处理并抛出 `ToolCatalogError`，向调用方报告输入或运行失败。
调用 `_walk_schema` 完成该函数的一项辅助处理。
如果辅助操作“调用 `str` 完成该函数的一项辅助处理”的结果 的长度大于20000，就拒绝继续处理并抛出 `ToolCatalogError`，向调用方报告输入或运行失败。
返回调用参数集合的当前值。
```

#### `build_provider_tool_catalog`

- **源码**：`app/tool_calling/catalog.py:65`
- **签名**：`def build_provider_tool_catalog(registry: ToolRegistry, static_bindings: dict[str, str] | None, safe_effects: set[ToolEffect] | None, granted_capabilities: set[str] | None, authority_fingerprint: str | None) -> ProviderToolCatalog`
- **作用**：在在 Schema、预算和只读证据边界内编排论文复现 Agent 的有界 Tool Calling 阶段中，该函数接收组件注册表、当前处理结果、当前处理结果、当前处理结果等输入，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `ProviderToolCatalog` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `registry` | `ToolRegistry` | 组件注册表；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `static_bindings` | `dict[str, str] | None` | 名为 `static_bindings` 的键值映射；键和值分别承载的业务字段由读取/写入分支确定。；默认 空值 |
| `safe_effects` | `set[ToolEffect] | None` | `set[ToolEffect] | None` 元素集合；元素代表的业务对象由参数名 `safe_effects` 和调用位置确定。；默认 空值 |
| `granted_capabilities` | `set[str] | None` | `set[str] | None` 元素集合；元素代表的业务对象由参数名 `granted_capabilities` 和调用位置确定。；默认 空值 |
| `authority_fingerprint` | `str | None` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。；默认 空值 |

**输出**

- **Python 类型**：`ProviderToolCatalog`
- **语义**：返回 `ProviderToolCatalog` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
复制、序列化或校验结构化领域对象，并把结果记为 该调用返回的结果；构造临时集合、映射或轻量领域对象，并把结果记为 该调用返回的结果；构造临时集合、映射或轻量领域对象，并把结果记为 该调用返回的结果；将 当前处理结果 初始化为空列表，用来收集后续结果。
遍历辅助操作产生的可迭代结果（调用 `items` 完成该函数的一项辅助处理），每次把当前项记为多个解包结果：
    先尝试完成以下处理：
        从组件注册表读取所需的状态或领域记录，并把结果记为 契约定义。
    如果出现 `Exception`并把异常保存为捕获的异常对象：
        拒绝继续处理并抛出 `ToolCatalogError`，向调用方报告输入或运行失败。
    读取契约，并保存为 契约。
    如果当前处理结果不等于当前处理结果，就拒绝继续处理并抛出 `ToolCatalogError`，向调用方报告输入或运行失败。
    如果“调用 `issubset` 完成该函数的一项辅助处理”后未得到肯定结果，就拒绝继续处理并抛出 `ToolCatalogError`，向调用方报告输入或运行失败。
    如果“当前处理结果有值或为真”不成立，就拒绝继续处理并抛出 `ToolCatalogError`，向调用方报告输入或运行失败。
    如果“调用 `issubset` 完成该函数的一项辅助处理”后未得到肯定结果，就拒绝继续处理并抛出 `ToolCatalogError`，向调用方报告输入或运行失败。
    构造 `ProviderToolSpec` 结构化领域对象，并把结果记为 该调用返回的结果；把新的处理结果追加或合并到当前处理结果。
计算按字段初始化键值映射，并保存为 Hash；构造并返回 `ProviderToolCatalog` 结构化领域对象。
```

#### `provider_specs`

- **源码**：`app/tool_calling/catalog.py:131`
- **签名**：`def provider_specs(catalog: ProviderToolCatalog) -> list[dict[str, Any]]`
- **作用**：在在 Schema、预算和只读证据边界内编排论文复现 Agent 的有界 Tool Calling 阶段中，该函数接收模型、工具或 Artifact 目录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `catalog` | `ProviderToolCatalog` | 持久化或目录访问端口；负责读取、CAS 更新或 Artifact 定位。 |

**输出**

- **Python 类型**：`list[dict[str, Any]]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
返回当前计算得到的结果。
```

### `app/tool_calling/evidence_tools.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_require_job_id`

- **源码**：`app/tool_calling/evidence_tools.py:41`
- **签名**：`def _require_job_id(context: ToolInvocationContext) -> str`
- **作用**：在在 Schema、预算和只读证据边界内编排论文复现 Agent 的有界 Tool Calling 阶段中，该函数接收运行上下文，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `context` | `ToolInvocationContext` | 运行上下文；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回稳定业务标识符，用于后续查询、关联或幂等绑定；它不是路径或内容 Hash。

**伪代码**

```text
如果复现任务 ID为空 或 “对复现任务 ID中的文本执行规范化或拆分”后未得到肯定结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回复现任务 ID的当前值。
```

#### `_bounded_output`

- **源码**：`app/tool_calling/evidence_tools.py:47`
- **签名**：`def _bounded_output(bundle: GroundingBundle, summary: str, source_types: set[str] | None, limit: int) -> EvidenceToolOutput`
- **作用**：在在 Schema、预算和只读证据边界内编排论文复现 Agent 的有界 Tool Calling 阶段中，该函数接收代码仓库归档包、阶段摘要、来源集合、结果数量上限，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `EvidenceToolOutput` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `bundle` | `GroundingBundle` | 代码仓库归档包；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `summary` | `str` | 阶段摘要；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `source_types` | `set[str] | None` | `set[str] | None` 元素集合；元素代表的业务对象由参数名 `source_types` 和调用位置确定。 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。 |

**输出**

- **Python 类型**：`EvidenceToolOutput`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
将 待处理项集合 初始化为空列表，用来收集后续结果；计算使用固定配置或常量值，并保存为 字符数；计算使用固定配置或常量值，并保存为 当前处理结果。
遍历当前可迭代输入，每次把当前项记为数据来源标记：
    如果来源集合不为空 且 来源类型不属于来源集合，就跳过本轮剩余处理，直接进入下一轮。
    如果待处理项集合 的长度不小于结果数量上限，就计算使用固定配置或常量值，并保存为 当前处理结果；立即结束当前循环。
    读取业务内容中的对应字段，并保存为 业务内容。
    如果当前输入内容大于最大工具结果字符数，就计算使用固定配置或常量值，并保存为 当前处理结果；跳过本轮剩余处理，直接进入下一轮。
    如果“对业务内容中的文本执行规范化或拆分”后未得到肯定结果，就跳过本轮剩余处理，直接进入下一轮。
    把新的处理结果追加或合并到待处理项集合；将新的计算结果累加或合并到字符数。
构造并返回 `EvidenceToolOutput` 结构化领域对象。
```

#### `_map_evidence_error`

- **源码**：`app/tool_calling/evidence_tools.py:74`
- **签名**：`def _map_evidence_error(exc: BaseException) -> ToolFailure | None`
- **作用**：在在 Schema、预算和只读证据边界内编排论文复现 Agent 的有界 Tool Calling 阶段中，该函数接收捕获的异常，用于把论文中的方法、模块或实验意图与仓库中的可验证对象建立稳定关联，并保留匹配依据，最终标注为 `ToolFailure | None` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `exc` | `BaseException` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`ToolFailure | None`
- **语义**：返回 `ToolFailure | None` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果“计算数量、边界或类型判断结果”后得到肯定结果，就构造并返回 `ToolFailure` 结构化领域对象。
如果“计算数量、边界或类型判断结果”后得到肯定结果，就构造并返回 `ToolFailure` 结构化领域对象。
返回固定值 `空值`。
```

#### `build_chat_evidence_tool_registry`

- **源码**：`app/tool_calling/evidence_tools.py:108`
- **签名**：`def build_chat_evidence_tool_registry(bindings: ChatEvidenceToolBindings) -> ToolRegistry`
- **作用**：在在 Schema、预算和只读证据边界内编排论文复现 Agent 的有界 Tool Calling 阶段中，该函数接收当前处理结果，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `ToolRegistry` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `bindings` | `ChatEvidenceToolBindings` | 名为 `bindings` 的 `ChatEvidenceToolBindings` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`ToolRegistry`
- **语义**：返回 `ToolRegistry` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造 `ToolRegistry` 结构化领域对象，并把结果记为 组件注册表。
定义内部辅助函数 `get_status`，供当前函数在后续步骤中调用。
调用 `register` 完成该函数的一项辅助处理。
定义内部辅助函数 `search_evidence`，供当前函数在后续步骤中调用。
调用 `register` 完成该函数的一项辅助处理。
定义内部辅助函数 `inspect_failure`，供当前函数在后续步骤中调用。
调用 `register` 完成该函数的一项辅助处理。
如果网关不为空，就加载这一步需要的外部依赖；调用 `register_mcp_evidence_tool` 完成该函数的一项辅助处理。
返回组件注册表的当前值。
```

#### `build_chat_evidence_tool_registry.get_status`

- **源码**：`app/tool_calling/evidence_tools.py:113`
- **签名**：`def get_status(payload: EmptyToolInput, context: ToolInvocationContext) -> EvidenceToolOutput`
- **作用**：在在 Schema、预算和只读证据边界内编排论文复现 Agent 的有界 Tool Calling 阶段中，该函数接收结构化请求载荷、运行上下文，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `EvidenceToolOutput` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `payload` | `EmptyToolInput` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `context` | `ToolInvocationContext` | 运行上下文；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`EvidenceToolOutput`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
移除结构化请求载荷中的当前内容；调用 `_require_job_id` 完成该函数的一项辅助处理，并把结果记为 复现任务 ID；调用 `build_job_only` 组装当前阶段需要的领域对象，并把结果记为 代码仓库归档包；调用 `_bounded_output` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `build_chat_evidence_tool_registry.search_evidence`

- **源码**：`app/tool_calling/evidence_tools.py:141`
- **签名**：`def search_evidence(payload: SearchReproductionEvidenceInput, context: ToolInvocationContext) -> EvidenceToolOutput`
- **作用**：在在 Schema、预算和只读证据边界内编排论文复现 Agent 的有界 Tool Calling 阶段中，该函数接收结构化请求载荷、运行上下文，用于围绕论文方法语义检索、切分和排序代码证据，为后续方法映射与实验规划提供候选结果，最终标注为 `EvidenceToolOutput` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `payload` | `SearchReproductionEvidenceInput` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `context` | `ToolInvocationContext` | 运行上下文；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`EvidenceToolOutput`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
调用 `_require_job_id` 完成该函数的一项辅助处理，并把结果记为 复现任务 ID；调用 `build` 完成该函数的一项辅助处理，并把结果记为 代码仓库归档包；调用 `_bounded_output` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `build_chat_evidence_tool_registry.inspect_failure`

- **源码**：`app/tool_calling/evidence_tools.py:168`
- **签名**：`def inspect_failure(payload: InspectFailureContextInput, context: ToolInvocationContext) -> EvidenceToolOutput`
- **作用**：在在 Schema、预算和只读证据边界内编排论文复现 Agent 的有界 Tool Calling 阶段中，该函数接收结构化请求载荷、运行上下文，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `EvidenceToolOutput` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `payload` | `InspectFailureContextInput` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `context` | `ToolInvocationContext` | 运行上下文；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`EvidenceToolOutput`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
调用 `_require_job_id` 完成该函数的一项辅助处理，并把结果记为 复现任务 ID；计算组合或计算已有值，并保存为 语义检索问题；调用 `build` 完成该函数的一项辅助处理，并把结果记为 代码仓库归档包；调用 `_bounded_output` 完成该函数的一项辅助处理，并返回处理结果。
```

### `app/tool_calling/factory.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `build_chat_tool_calling_loop`

- **源码**：`app/tool_calling/factory.py:22`
- **签名**：`def build_chat_tool_calling_loop(context_builder: ChatContextBuilder) -> BoundedToolCallingLoop`
- **作用**：在在 Schema、预算和只读证据边界内编排论文复现 Agent 的有界 Tool Calling 阶段中，该函数接收上下文构造器，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `BoundedToolCallingLoop` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `context_builder` | `ChatContextBuilder` | 名为 `context_builder` 的 `ChatContextBuilder` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`BoundedToolCallingLoop`
- **语义**：返回 `BoundedToolCallingLoop` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
加载这一步需要的外部依赖；计算使用固定配置或常量值，并保存为 网关；复制、序列化或校验结构化领域对象，并把结果记为 该调用返回的结果；构造临时集合、映射或轻量领域对象，并把结果记为 该调用返回的结果。
构造临时集合、映射或轻量领域对象，并把结果记为 该调用返回的结果；计算使用固定配置或常量值，并保存为 职责权限指纹。
如果网关有值或为真：
    加载这一步需要的外部依赖；加载这一步需要的外部依赖；调用 `build_read_only_mcp_gateway` 组装当前阶段需要的领域对象，并把结果记为 网关；读取工具的名称，并保存为 当前处理结果中的对应字段。
    把当前处理结果追加或合并到当前处理结果；把当前处理结果追加或合并到当前处理结果；读取职责权限指纹，并保存为 职责权限指纹。
调用 `build_chat_evidence_tool_registry` 组装当前阶段需要的领域对象，并把结果记为 组件注册表；调用 `build_provider_tool_catalog` 组装当前阶段需要的领域对象，并把结果记为 模型、工具或 Artifact 目录；构造并返回 `BoundedToolCallingLoop` 结构化领域对象。
```

#### `doctor_chat_tool_calling`

- **源码**：`app/tool_calling/factory.py:88`
- **签名**：`def doctor_chat_tool_calling(context_builder: ChatContextBuilder) -> ToolCallingDoctorReport`
- **作用**：在在 Schema、预算和只读证据边界内编排论文复现 Agent 的有界 Tool Calling 阶段中，该函数接收上下文构造器，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ToolCallingDoctorReport` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `context_builder` | `ChatContextBuilder` | 名为 `context_builder` 的 `ChatContextBuilder` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`ToolCallingDoctorReport`
- **语义**：返回 `ToolCallingDoctorReport` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果“对话工具有值或为真”不成立，就构造并返回 `ToolCallingDoctorReport` 结构化领域对象。
将 诊断问题集合 初始化为空列表，用来收集后续结果。
先尝试完成以下处理：
    调用 `build_chat_evidence_tool_registry` 组装当前阶段需要的领域对象，并把结果记为 组件注册表；调用 `build_provider_tool_catalog` 组装当前阶段需要的领域对象，并把结果记为 模型、工具或 Artifact 目录。
如果出现 `Exception`并把异常保存为捕获的异常对象：
    构造并返回 `ToolCallingDoctorReport` 结构化领域对象。
先尝试完成以下处理：
    调用 `build_model_gateway` 组装当前阶段需要的领域对象，并把结果记为 外部服务网关；调用 `route` 完成该函数的一项辅助处理，并把结果记为 流程路由结果。
    如果当前输入内容不属于当前处理结果，就把新的处理结果追加或合并到诊断问题集合。
如果出现 `Exception`并把异常保存为捕获的异常对象：
    把新的处理结果追加或合并到诊断问题集合。
构造并返回 `ToolCallingDoctorReport` 结构化领域对象。
```

### `app/tool_calling/identity.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `canonical_json_bytes`

- **源码**：`app/tool_calling/identity.py:12`
- **签名**：`def canonical_json_bytes(value: Any) -> bytes`
- **作用**：在在 Schema、预算和只读证据边界内编排论文复现 Agent 的有界 Tool Calling 阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `bytes` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `Any` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`bytes`
- **语义**：返回 `bytes` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果“计算数量、边界或类型判断结果”后得到肯定结果，就复制、序列化或校验结构化领域对象，并把结果记为 当前字段值。
将结构化内容序列化或编码为可传输表示，并返回处理结果。
```

#### `sha256_value`

- **源码**：`app/tool_calling/identity.py:24`
- **签名**：`def sha256_value(value: Any) -> str`
- **作用**：在在 Schema、预算和只读证据边界内编排论文复现 Agent 的有界 Tool Calling 阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `Any` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回输入内容的 SHA-256 身份摘要，用于完整性校验，不是加密后的正文。

**伪代码**

```text
计算输入内容的 SHA-256 身份摘要，并返回处理结果。
```

#### `trace_id_for`

- **源码**：`app/tool_calling/identity.py:28`
- **签名**：`def trace_id_for(*, job_id: str, request_sha256: str) -> str`
- **作用**：在在 Schema、预算和只读证据边界内编排论文复现 Agent 的有界 Tool Calling 阶段中，该函数接收复现任务 ID、请求内容 SHA-256，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `request_sha256` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
返回当前计算得到的结果。
```

#### `tool_call_fingerprint`

- **源码**：`app/tool_calling/identity.py:38`
- **签名**：`def tool_call_fingerprint(*, internal_name: str, arguments: dict) -> str`
- **作用**：在在 Schema、预算和只读证据边界内编排论文复现 Agent 的有界 Tool Calling 阶段中，该函数接收当前处理结果的名称、结构化调用参数，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `internal_name` | `str` | 名为 `internal_name` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `arguments` | `dict` | 结构化调用参数；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回内容身份摘要，通常为 SHA-256 十六进制字符串。

**伪代码**

```text
调用 `sha256_value` 计算内容身份、分数或派生结果，并返回处理结果。
```

#### `trace_payload`

- **源码**：`app/tool_calling/identity.py:47`
- **签名**：`def trace_payload(trace: ToolLoopTrace) -> dict`
- **作用**：在在 Schema、预算和只读证据边界内编排论文复现 Agent 的有界 Tool Calling 阶段中，该函数接收调用链追踪信息，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `trace` | `ToolLoopTrace` | 调用链追踪信息；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
复制、序列化或校验结构化领域对象，并把结果记为 结构化请求载荷；从结构化请求载荷取出并移除最后一项；返回结构化请求载荷的当前值。
```

#### `compute_trace_hash`

- **源码**：`app/tool_calling/identity.py:53`
- **签名**：`def compute_trace_hash(trace: ToolLoopTrace) -> str`
- **作用**：在在 Schema、预算和只读证据边界内编排论文复现 Agent 的有界 Tool Calling 阶段中，该函数接收调用链追踪信息，用于计算输入、命令、运行配置或证据的稳定派生值，保证复现链路中的身份校验和 stale 检测，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `trace` | `ToolLoopTrace` | 调用链追踪信息；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回内容身份摘要，通常为 SHA-256 十六进制字符串。

**伪代码**

```text
调用 `sha256_value` 计算内容身份、分数或派生结果，并返回处理结果。
```

#### `validate_trace_hash`

- **源码**：`app/tool_calling/identity.py:57`
- **签名**：`def validate_trace_hash(trace: ToolLoopTrace) -> None`
- **作用**：在在 Schema、预算和只读证据边界内编排论文复现 Agent 的有界 Tool Calling 阶段中，该函数接收调用链追踪信息，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `trace` | `ToolLoopTrace` | 调用链追踪信息；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
如果辅助操作“调用 `compute_trace_hash` 计算内容身份、分数或派生结果”的结果不等于调用链追踪信息的 SHA-256，就加载这一步需要的外部依赖；拒绝继续处理并抛出 `ToolTraceIntegrityError`，向调用方报告输入或运行失败。
```

### `app/tool_calling/loop.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `utc_now`

- **源码**：`app/tool_calling/loop.py:50`
- **签名**：`def utc_now() -> str`
- **作用**：在在 Schema、预算和只读证据边界内编排论文复现 Agent 的有界 Tool Calling 阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `isoformat` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `_validate_json_shape`

- **源码**：`app/tool_calling/loop.py:60`
- **签名**：`def _validate_json_shape(value: Any, depth: int) -> None`
- **作用**：在在 Schema、预算和只读证据边界内编排论文复现 Agent 的有界 Tool Calling 阶段中，该函数接收当前字段值、当前遍历深度，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `Any` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |
| `depth` | `int` | 文件行号、页码或遍历深度边界；用于限制读取/扫描范围，不是业务 ID。；默认 0 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
如果当前遍历深度大于8，就拒绝继续处理并抛出 `ToolLoopPolicyError`，向调用方报告输入或运行失败。
如果“计算数量、边界或类型判断结果”后得到肯定结果：
    如果当前字段值 的长度大于32，就拒绝继续处理并抛出 `ToolLoopPolicyError`，向调用方报告输入或运行失败。
    遍历辅助操作产生的可迭代结果（调用 `items` 完成该函数的一项辅助处理），每次把当前项记为多个解包结果：
        如果“计算数量、边界或类型判断结果”后未得到肯定结果 或 映射键或对象字段名 的长度大于100，就拒绝继续处理并抛出 `ToolLoopPolicyError`，向调用方报告输入或运行失败。
        调用 `_validate_json_shape` 校验当前输入或状态。
否则：
    如果“计算数量、边界或类型判断结果”后得到肯定结果：
        如果当前字段值 的长度大于50，就拒绝继续处理并抛出 `ToolLoopPolicyError`，向调用方报告输入或运行失败。
        遍历由当前字段值组成的集合或迭代器，每次把当前项记为子级目录或子领域对象，然后调用 `_validate_json_shape` 校验当前输入或状态。
    否则：
        如果“计算数量、边界或类型判断结果”后得到肯定结果：
            如果当前字段值 的长度大于2000，就拒绝继续处理并抛出 `ToolLoopPolicyError`，向调用方报告输入或运行失败。
            如果由当前字段值组成的集合或迭代器中存在满足“当前字符 对应的 ASCII/Unicode 编码等于0”的项，就拒绝继续处理并抛出 `ToolLoopPolicyError`，向调用方报告输入或运行失败。
        否则：
            如果当前字段值不为空 且 “计算数量、边界或类型判断结果”后未得到肯定结果，就拒绝继续处理并抛出 `ToolLoopPolicyError`，向调用方报告输入或运行失败。
```

#### `_safe_tool_message`

- **源码**：`app/tool_calling/loop.py:88`
- **签名**：`def _safe_tool_message(output: EvidenceToolOutput | None, failure_code: str | None) -> str`
- **作用**：在在 Schema、预算和只读证据边界内编排论文复现 Agent 的有界 Tool Calling 阶段中，该函数接收输出结果、失败，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `output` | `EvidenceToolOutput | None` | 输出结果；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `failure_code` | `str | None` | 名为 `failure_code` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
如果失败不为空：
    计算按字段初始化键值映射，并保存为 结构化请求载荷。
否则：
    如果输出结果不为空，就计算按字段初始化键值映射，并保存为 结构化请求载荷；否则拒绝继续处理并抛出 `AssertionError`，向调用方报告输入或运行失败。
将结构化内容序列化或编码为可传输表示，并返回处理结果。
```

#### `merge_grounding_sources`

- **源码**：`app/tool_calling/loop.py:125`
- **签名**：`def merge_grounding_sources(base: GroundingBundle, additions: list[GroundingSource], source_limit: int, total_chars: int) -> GroundingBundle`
- **作用**：在在 Schema、预算和只读证据边界内编排论文复现 Agent 的有界 Tool Calling 阶段中，按 Citation Identity 合并，永远保留 job:current。该函数接收当前处理结果、当前处理结果、来源上限、字符数，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `GroundingBundle` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `base` | `GroundingBundle` | 名为 `base` 的 `GroundingBundle` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `additions` | `list[GroundingSource]` | `list[GroundingSource]` 元素集合；元素代表的业务对象由参数名 `additions` 和调用位置确定。 |
| `source_limit` | `int` | 名为 `source_limit` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `total_chars` | `int` | 名为 `total_chars` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`GroundingBundle`
- **语义**：返回 `GroundingBundle` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造临时集合、映射或轻量领域对象，并把结果记为 选中的候选项；遍历并筛选输入，将整理后的结果保存为 当前处理结果的 ID；调用 `sum` 完成该函数的一项辅助处理，并把结果记为 字符数。
遍历由当前处理结果组成的集合或迭代器，每次把当前项记为数据来源标记：
    读取论文引用证据的 ID，并保存为 论文引用证据的 ID；从当前处理结果的 ID读取所需的状态或领域记录，并把结果记为 前一项。
    如果前一项不为空：
        如果论文引用证据不等于论文引用证据 或 业务内容不等于业务内容，就拒绝继续处理并抛出 `ToolLoopPolicyError`，向调用方报告输入或运行失败。
        跳过本轮剩余处理，直接进入下一轮。
    如果选中的候选项 的长度不小于来源上限，就立即结束当前循环。
    如果当前输入内容大于字符数，就跳过本轮剩余处理，直接进入下一轮。
    把数据来源标记追加或合并到选中的候选项；读取数据来源标记，并保存为 当前处理结果的 ID中的对应字段；将新的计算结果累加或合并到字符数。
构造并返回 `GroundingBundle` 结构化领域对象。
```

#### `BoundedToolCallingLoop.__init__`

- **源码**：`app/tool_calling/loop.py:166`
- **签名**：`def __init__(self: 未显式标注, registry: ToolRegistry, catalog: ProviderToolCatalog, turn_invoker: ToolTurnInvoker, max_model_rounds: int, max_tool_calls: int, max_arguments_bytes: int, max_single_result_chars: int, max_total_result_chars: int, granted_capabilities: set[str] | None) -> None`
- **作用**：在在 Schema、预算和只读证据边界内编排论文复现 Agent 的有界 Tool Calling 阶段中，该函数接收组件注册表、模型、工具或 Artifact 目录、当前处理结果、最大当前处理结果等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `registry` | `ToolRegistry` | 组件注册表；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `catalog` | `ProviderToolCatalog` | 持久化或目录访问端口；负责读取、CAS 更新或 Artifact 定位。 |
| `turn_invoker` | `ToolTurnInvoker` | 可调用依赖；由当前函数在受控位置调用。 |
| `max_model_rounds` | `int` | 名为 `max_model_rounds` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `max_tool_calls` | `int` | 名为 `max_tool_calls` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `max_arguments_bytes` | `int` | 名为 `max_arguments_bytes` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `max_single_result_chars` | `int` | 前序调用产生的结构化响应、结果或执行结论，供当前函数继续判断或投影。 |
| `max_total_result_chars` | `int` | 前序调用产生的结构化响应、结果或执行结论，供当前函数继续判断或投影。 |
| `granted_capabilities` | `set[str] | None` | `set[str] | None` 元素集合；元素代表的业务对象由参数名 `granted_capabilities` 和调用位置确定。；默认 空值 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
如果“当前输入内容不大于最大当前处理结果不大于6”不成立，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果“当前输入内容不大于最大工具集合不大于3”不成立，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果最大当前处理结果小于最大工具集合，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
把传入的 组件注册表、模型、工具或 Artifact 目录、当前处理结果、最大当前处理结果、最大工具集合、最大结构化调用参数的字节内容、最大结果字符数、最大结果字符数 分别保存到同名实例字段；构造临时集合、映射或轻量领域对象，并把结果记为 该调用返回的结果。
```

#### `BoundedToolCallingLoop._finish_trace`

- **源码**：`app/tool_calling/loop.py:199`
- **签名**：`def _finish_trace(self: 未显式标注, job_id: str, request_sha256: str, status: str, started_at: str, invocation_ids: list[str], calls: list[ToolLoopCallTrace]) -> ToolLoopTrace`
- **作用**：在在 Schema、预算和只读证据边界内编排论文复现 Agent 的有界 Tool Calling 阶段中，该函数接收复现任务 ID、请求内容 SHA-256、当前状态、运行启动时间等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ToolLoopTrace` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `request_sha256` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |
| `status` | `str` | 来源、类别、用途、后端、状态或操作原因等控制字段；通常对应有限的业务枚举或审计文本。 |
| `started_at` | `str` | 运行启动时间；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `invocation_ids` | `list[str]` | `list[str]` 元素集合；元素代表的业务对象由参数名 `invocation_ids` 和调用位置确定。 |
| `calls` | `list[ToolLoopCallTrace]` | 工具或模型调用记录集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`ToolLoopTrace`
- **语义**：返回 `ToolLoopTrace` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造 `ToolLoopTrace` 结构化领域对象，并把结果记为 草稿对象；复制、序列化或校验结构化领域对象，并返回处理结果。
```

#### `BoundedToolCallingLoop.run`

- **源码**：`app/tool_calling/loop.py:228`
- **签名**：`def run(self: 未显式标注, job_id: str, job_status: str, question: str, request_sha256: str) -> ToolLoopOutcome`
- **作用**：在在 Schema、预算和只读证据边界内编排论文复现 Agent 的有界 Tool Calling 阶段中，该函数接收复现任务 ID、任务状态、论文复现问题或用户问题、请求内容 SHA-256，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ToolLoopOutcome` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `job_status` | `str` | 名为 `job_status` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `question` | `str` | 论文复现问题或用户问题；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `request_sha256` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |

**输出**

- **Python 类型**：`ToolLoopOutcome`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
读取当前时间，作为状态变更的统一时间戳，并把结果记为 运行启动时间；计算初始化顺序集合，并保存为 对话或日志消息集合；将 当前处理结果 初始化为空去重集合，用来收集后续结果；将 调用记录集合、当前处理结果、证据来源集合 初始化为空列表，用来收集后续结果。
计算使用固定配置或常量值，并保存为 结果字符数；计算使用固定配置或常量值，并保存为 当前状态。
遍历限定范围内的序列，每次把当前项记为当前处理结果的索引：
    先尝试完成以下处理：
        调用当前处理结果完成模型或 Runnable 处理，并把结果记为 该调用返回的结果。
    如果出现 `ToolModelUnavailable`：
        计算使用固定配置或常量值，并保存为 当前状态；立即结束当前循环。
    把面向用户或日志的提示信息追加或合并到对话或日志消息集合。
    如果工具调用记录的 ID不为空，就把工具调用记录的 ID追加或合并到调用记录集合。
    如果“工具或模型调用记录集合有值或为真”不成立，就计算根据条件从两个候选结果中选择一个，并保存为 当前状态；立即结束当前循环。
    如果工具或模型调用记录集合 的长度不等于1，就计算使用固定配置或常量值，并保存为 当前状态；立即结束当前循环。
    读取工具或模型调用记录集合中的对应字段，并保存为 后续步骤使用的结果；调用 `by_alias` 完成该函数的一项辅助处理，并把结果记为 资源绑定记录。
    如果资源绑定记录为空，就计算使用固定配置或常量值，并保存为 当前状态；立即结束当前循环。
    如果当前处理结果 的长度不小于最大工具集合，就计算使用固定配置或常量值，并保存为 当前状态；立即结束当前循环。
    先尝试完成以下处理：
        调用 `_validate_json_shape` 校验当前输入或状态；调用 `canonical_json_bytes` 完成该函数的一项辅助处理，并把结果记为 当前处理结果的字节内容。
        如果当前处理结果的字节内容 的长度大于最大结构化调用参数的字节内容，就拒绝继续处理并抛出 `ToolLoopPolicyError`，向调用方报告输入或运行失败。
    如果出现 `ToolLoopPolicyError`：
        计算使用固定配置或常量值，并保存为 当前状态；立即结束当前循环。
    调用 `tool_call_fingerprint` 完成该函数的一项辅助处理，并把结果记为 内容或环境指纹。
    如果内容或环境指纹属于当前处理结果，就计算使用固定配置或常量值，并保存为 当前状态；立即结束当前循环。
    把内容或环境指纹追加或合并到当前处理结果；调用组件注册表完成模型或 Runnable 处理，并把结果记为 阶段处理结果。
    如果失败不为空，就把新的处理结果追加或合并到当前处理结果；把新的处理结果追加或合并到对话或日志消息集合；跳过本轮剩余处理，直接进入下一轮。
    先尝试完成以下处理：
        复制、序列化或校验结构化领域对象，并把结果记为 输出结果。
    如果出现 `Exception`：
        把新的处理结果追加或合并到当前处理结果；计算使用固定配置或常量值，并保存为 当前状态；立即结束当前循环。
    调用 `_safe_tool_message` 完成该函数的一项辅助处理，并把结果记为 工具。
    如果工具 的长度大于最大结果字符数，就把新的处理结果追加或合并到当前处理结果；把新的处理结果追加或合并到对话或日志消息集合；跳过本轮剩余处理，直接进入下一轮。
    如果当前输入内容大于最大结果字符数，就计算使用固定配置或常量值，并保存为 当前状态；立即结束当前循环。
    遍历并筛选输入，将整理后的结果保存为 当前处理结果；把新的处理结果追加或合并到当前处理结果；将新的计算结果累加或合并到结果字符数；把新的处理结果追加或合并到证据来源集合。
    把新的处理结果追加或合并到对话或日志消息集合。
调用 `_finish_trace` 完成该函数的一项辅助处理，并把结果记为 调用链追踪信息；构造并返回 `ToolLoopOutcome` 结构化领域对象。
```

#### `public_trace_summary`

- **源码**：`app/tool_calling/loop.py:442`
- **签名**：`def public_trace_summary(trace: ToolLoopTrace) -> ChatToolTraceSummary`
- **作用**：在在 Schema、预算和只读证据边界内编排论文复现 Agent 的有界 Tool Calling 阶段中，该函数接收调用链追踪信息，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ChatToolTraceSummary` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `trace` | `ToolLoopTrace` | 调用链追踪信息；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`ChatToolTraceSummary`
- **语义**：返回 `ChatToolTraceSummary` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `ChatToolTraceSummary` 结构化领域对象。
```

### `app/tool_calling/model_adapter.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `ToolTurnInvoker.invoke`

- **源码**：`app/tool_calling/model_adapter.py:24`
- **签名**：`def invoke(self: 未显式标注, messages: list[BaseMessage], catalog: ProviderToolCatalog, job_id: str) -> ToolModelTurn`
- **作用**：在在 Schema、预算和只读证据边界内编排论文复现 Agent 的有界 Tool Calling 阶段中，该函数接收对话或日志消息集合、模型、工具或 Artifact 目录、复现任务 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ToolModelTurn` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `messages` | `list[BaseMessage]` | 对话或日志消息集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `catalog` | `ProviderToolCatalog` | 持久化或目录访问端口；负责读取、CAS 更新或 Artifact 定位。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`ToolModelTurn`
- **语义**：返回 `ToolModelTurn` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `normalize_tool_calls`

- **源码**：`app/tool_calling/model_adapter.py:34`
- **签名**：`def normalize_tool_calls(message: AIMessage) -> list[NormalizedToolCall]`
- **作用**：在在 Schema、预算和只读证据边界内编排论文复现 Agent 的有界 Tool Calling 阶段中，该函数接收面向用户或日志的提示信息，用于读取并整理论文、源码或运行产物，把原始输入转换成带位置和身份信息的结构化证据，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `message` | `AIMessage` | 对话消息记录或消息文本；角色、顺序和内容 Hash 可能参与证据校验。 |

**输出**

- **Python 类型**：`list[NormalizedToolCall]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
将 规范化后的文本 初始化为空列表，用来收集后续结果。
遍历当前可迭代输入，每次把当前项记为原始内容：
    从原始内容读取所需的状态或领域记录，并把结果记为 对象名称；从原始内容读取所需的状态或领域记录，并把结果记为 结构化调用参数；从原始内容读取所需的状态或领域记录，并把结果记为 当前处理结果的 ID。
    如果“计算数量、边界或类型判断结果”后未得到肯定结果 或 “计算数量、边界或类型判断结果”后未得到肯定结果 或 “计算数量、边界或类型判断结果”后未得到肯定结果，就拒绝继续处理并抛出 `ToolModelUnavailable`，向调用方报告输入或运行失败。
    把新的处理结果追加或合并到规范化后的文本。
返回规范化后的文本的当前值。
```

#### `GatewayToolTurnInvoker.invoke`

- **源码**：`app/tool_calling/model_adapter.py:59`
- **签名**：`def invoke(self: 未显式标注, messages: list[BaseMessage], catalog: ProviderToolCatalog, job_id: str) -> ToolModelTurn`
- **作用**：在在 Schema、预算和只读证据边界内编排论文复现 Agent 的有界 Tool Calling 阶段中，该函数接收对话或日志消息集合、模型、工具或 Artifact 目录、复现任务 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ToolModelTurn` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `messages` | `list[BaseMessage]` | 对话或日志消息集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `catalog` | `ProviderToolCatalog` | 持久化或目录访问端口；负责读取、CAS 更新或 Artifact 定位。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`ToolModelTurn`
- **语义**：返回 `ToolModelTurn` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
先尝试完成以下处理：
    调用 `invoke_tool_calling` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `normalize_tool_calls` 解析、规范化或转换当前输入，并把结果记为 工具或模型调用记录集合。
如果出现 `Exception`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `ToolModelUnavailable`，向调用方报告输入或运行失败。
构造并返回 `ToolModelTurn` 结构化领域对象。
```

### `app/tool_calling/schemas.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_safe_query`

- **源码**：`app/tool_calling/schemas.py:33`
- **签名**：`def _safe_query(value: str) -> str`
- **作用**：在在 Schema、预算和只读证据边界内编排论文复现 Agent 的有界 Tool Calling 阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `join` 完成该函数的一项辅助处理，并把结果记为 规范化后的文本。
如果规范化后的文本为空或为假，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果由规范化后的文本组成的集合或迭代器中存在满足“当前字符 对应的 ASCII/Unicode 编码小于32 或 当前字符 对应的 ASCII/Unicode 编码等于127”的项，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回规范化后的文本的当前值。
```

#### `SearchReproductionEvidenceInput.validate_query`

- **源码**：`app/tool_calling/schemas.py:65`
- **签名**：`def validate_query(cls, value: str) -> str`
- **作用**：在在 Schema、预算和只读证据边界内编排论文复现 Agent 的有界 Tool Calling 阶段中，该函数接收当前字段值，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `cls` | `未显式标注` | 当前类对象，用于类级构造或校验。 |
| `value` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `_safe_query` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `SearchReproductionEvidenceInput.validate_source_types`

- **源码**：`app/tool_calling/schemas.py:70`
- **签名**：`def validate_source_types(cls: 未显式标注, values: list[EvidenceSourceType]) -> list[EvidenceSourceType]`
- **作用**：在在 Schema、预算和只读证据边界内编排论文复现 Agent 的有界 Tool Calling 阶段中，该函数接收状态字段集合，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `cls` | `未显式标注` | 当前类对象，用于类级构造或校验。 |
| `values` | `list[EvidenceSourceType]` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`list[EvidenceSourceType]`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
如果状态字段集合 的长度不等于辅助操作“构造临时集合、映射或轻量领域对象”的结果 的长度，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回状态字段集合的当前值。
```

#### `InspectFailureContextInput.validate_focus`

- **源码**：`app/tool_calling/schemas.py:85`
- **签名**：`def validate_focus(cls, value: str) -> str`
- **作用**：在在 Schema、预算和只读证据边界内编排论文复现 Agent 的有界 Tool Calling 阶段中，该函数接收当前字段值，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `cls` | `未显式标注` | 当前类对象，用于类级构造或校验。 |
| `value` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `_safe_query` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `ProviderToolSpec.validate_function_shape`

- **源码**：`app/tool_calling/schemas.py:109`
- **签名**：`def validate_function_shape(self) -> "ProviderToolSpec"`
- **作用**：在在 Schema、预算和只读证据边界内编排论文复现 Agent 的有界 Tool Calling 阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `'ProviderToolSpec'` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`'ProviderToolSpec'`
- **语义**：返回 `'ProviderToolSpec'` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果辅助操作“构造临时集合、映射或轻量领域对象”的结果不等于{'name', 'description', 'parameters', 'strict'}，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果当前处理结果中的对应字段不是真，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前对象的当前值。
```

#### `ProviderToolCatalog.validate_unique_bindings`

- **源码**：`app/tool_calling/schemas.py:136`
- **签名**：`def validate_unique_bindings(self) -> "ProviderToolCatalog"`
- **作用**：在在 Schema、预算和只读证据边界内编排论文复现 Agent 的有界 Tool Calling 阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `'ProviderToolCatalog'` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`'ProviderToolCatalog'`
- **语义**：返回 `'ProviderToolCatalog'` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
遍历并筛选输入，将整理后的结果保存为 当前处理结果；遍历并筛选输入，将整理后的结果保存为 当前处理结果。
如果当前处理结果 的长度不等于辅助操作“构造临时集合、映射或轻量领域对象”的结果 的长度，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果当前处理结果 的长度不等于辅助操作“构造临时集合、映射或轻量领域对象”的结果 的长度，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前对象的当前值。
```

#### `ProviderToolCatalog.by_alias`

- **源码**：`app/tool_calling/schemas.py:145`
- **签名**：`def by_alias(self, alias: str) -> ProviderToolBinding | None`
- **作用**：在在 Schema、预算和只读证据边界内编排论文复现 Agent 的有界 Tool Calling 阶段中，该函数接收对象别名，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ProviderToolBinding | None` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `alias` | `str` | 对象别名；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`ProviderToolBinding | None`
- **语义**：返回 `ProviderToolBinding | None` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `next` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `ToolLoopTrace.validate_call_count`

- **源码**：`app/tool_calling/schemas.py:196`
- **签名**：`def validate_call_count(self) -> "ToolLoopTrace"`
- **作用**：在在 Schema、预算和只读证据边界内编排论文复现 Agent 的有界 Tool Calling 阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `'ToolLoopTrace'` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`'ToolLoopTrace'`
- **语义**：返回 `'ToolLoopTrace'` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果工具或模型调用记录集合 的长度大于3，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前对象的当前值。
```

### `create_mcp_phase1.py`

**模块作用**：Phase 53 MCP Gateway 批量创建脚本

#### `main`

- **源码**：`create_mcp_phase1.py:5`
- **签名**：`def main()`
- **作用**：在围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把外部位置解析为文件系统路径对象，并把结果记为 受控扫描根目录；向终端或输出流写出当前结果/诊断信息；计算组合或计算已有值，并保存为 当前处理结果的目录；创建当前处理结果的目录对应的目录。
向终端或输出流写出当前结果/诊断信息；将处理结果写入当前输入内容指定的文件；向终端或输出流写出当前结果/诊断信息；计算使用固定配置或常量值，并保存为 当前处理结果。
将处理结果写入当前输入内容指定的文件；向终端或输出流写出当前结果/诊断信息；计算使用固定配置或常量值，并保存为 当前处理结果；将处理结果写入当前输入内容指定的文件。
向终端或输出流写出当前结果/诊断信息；向终端或输出流写出当前结果/诊断信息。
```

### `tests/fakes/mcp_readonly_server.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `search_paper_evidence`

- **源码**：`tests/fakes/mcp_readonly_server.py:37`
- **签名**：`def search_paper_evidence(query: str, limit: int = 5) -> FixtureSearchResult`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，Return deterministic paper evidence for Phase 53 tests。该函数接收语义检索问题、结果数量上限，用于围绕论文方法语义检索、切分和排序代码证据，为后续方法映射与实验规划提供候选结果，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `query` | `str` | 用户目标、检索问题、反馈或待处理文本；会作为当前阶段的业务语境输入，并可能受到长度/脱敏约束。 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。；默认 5 |

**输出**

- **Python 类型**：`FixtureSearchResult`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
计算初始化顺序集合，并保存为 状态字段集合；构造并返回 `FixtureSearchResult` 结构化领域对象。
```

#### `delete_library_item`

- **源码**：`tests/fakes/mcp_readonly_server.py:59`
- **签名**：`def delete_library_item(item_id: str) -> dict[str, str]`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，This tool exists only to prove discovery does not imply exposure。该函数接收当前处理项的 ID，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `item_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`dict[str, str]`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
返回包含 `deleted` 字段的结构化映射。
```

### `tests/helpers/knowledge_base.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `FakeVerifiedRuns.__init__`

- **源码**：`tests/helpers/knowledge_base.py:43`
- **签名**：`def __init__(self, evidence) -> None`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收可追溯证据记录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `evidence` | `未显式标注` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 可追溯证据记录 分别保存到同名实例字段。
```

#### `FakeVerifiedRuns.read`

- **源码**：`tests/helpers/knowledge_base.py:46`
- **签名**：`def read(self, job_id: str)`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收复现任务 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
断言复现任务 ID等于复现任务 ID；不满足就终止当前测试或流程；返回可追溯证据记录的当前值。
```

#### `FakeArtifactCatalog.__init__`

- **源码**：`tests/helpers/knowledge_base.py:52`
- **签名**：`def __init__(self, views, blobs) -> None`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收Artifact 视图集合、当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `views` | `未显式标注` | Artifact 视图集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `blobs` | `未显式标注` | 名为 `blobs` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
遍历并筛选输入，将整理后的结果保存为 Artifact 视图集合；复制、序列化或校验结构化领域对象，并把结果记为 该调用返回的结果。
```

#### `FakeArtifactCatalog.open`

- **源码**：`tests/helpers/knowledge_base.py:56`
- **签名**：`def open(self, *, job, artifact_id: str)`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收复现任务记录、Artifact的 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job` | `未显式标注` | 任务、运行、Manifest、记录或证据领域对象；携带关联 ID、状态和内容身份。 |
| `artifact_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
移除复现任务记录中的当前内容；读取Artifact 视图集合中的对应字段，并保存为 视图；读取当前处理结果中的对应字段，并保存为 原始内容；构造 `SimpleNamespace` 结构化领域对象，并把结果记为 工具或组件描述信息。
构造 `SimpleNamespace` 结构化领域对象，并把结果记为 该调用返回的结果；构造并返回 `SimpleNamespace` 结构化领域对象。
```

#### `_view`

- **源码**：`tests/helpers/knowledge_base.py:77`
- **签名**：`def _view(artifact_id: str, path: str, run_id: str, raw: bytes)`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收Artifact的 ID、文件或目录路径、本次复现运行 ID、原始内容，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `artifact_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `path` | `str` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |
| `run_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `raw` | `bytes` | 原始字节内容；可用于文件、序列化载荷或摘要计算，不应直接当作普通文本记录。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
构造并返回 `SimpleNamespace` 结构化领域对象。
```

#### `make_source_fixture`

- **源码**：`tests/helpers/knowledge_base.py:87`
- **签名**：`def make_source_fixture()`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
计算组合或计算已有值，并保存为 论文SHA；构造 `PaperDocument` 结构化领域对象，并把结果记为 论文解析文档；构造 `PaperSection` 结构化领域对象，并把结果记为 论文文档章节；构造 `PaperEvidence` 结构化领域对象，并把结果记为 可追溯证据记录。
构造 `PaperFactRecord` 结构化领域对象，并把结果记为 项目事实记录；构造 `PaperSummary` 结构化领域对象，并把结果记为 阶段摘要；计算按字段初始化键值映射，并保存为 当前处理结果；遍历并筛选输入，将整理后的结果保存为 当前处理结果。
遍历并筛选输入，将整理后的结果保存为 Artifact 视图集合；构造 `SimpleNamespace` 结构化领域对象，并把结果记为 证据运行；构造 `FakeArtifactCatalog` 结构化领域对象，并把结果记为 模型、工具或 Artifact 目录；返回当前构造的顺序或去重集合。
```

#### `_entity`

- **源码**：`tests/helpers/knowledge_base.py:169`
- **签名**：`def _entity(*, kind: str, scope: str, key: str, name: str)`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收业务类别、查询或授权作用域、映射键或对象字段名、对象名称，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `kind` | `str` | 来源、类别、用途、后端、状态或操作原因等控制字段；通常对应有限的业务枚举或审计文本。 |
| `scope` | `str` | 查询或授权作用域；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `key` | `str` | 映射键或对象字段名；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `name` | `str` | 对象名称；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
调用 `normalize_knowledge_key` 解析、规范化或转换当前输入，并把结果记为 规范化；构造 `KnowledgeEntityRecord` 结构化领域对象，并把结果记为 草稿对象；复制、序列化或校验结构化领域对象，并返回处理结果。
```

#### `_relation`

- **源码**：`tests/helpers/knowledge_base.py:189`
- **签名**：`def _relation(*, relation_type: str, source: str, target: str)`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收关系类型、数据来源标记、待定位的代码对象或业务目标，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `relation_type` | `str` | 名为 `relation_type` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `source` | `str` | 来源、类别、用途、后端、状态或操作原因等控制字段；通常对应有限的业务枚举或审计文本。 |
| `target` | `str` | 待定位的代码对象或业务目标；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
构造 `KnowledgeRelationRecord` 结构化领域对象，并把结果记为 草稿对象；复制、序列化或校验结构化领域对象，并返回处理结果。
```

#### `make_graph_batch`

- **源码**：`tests/helpers/knowledge_base.py:212`
- **签名**：`def make_graph_batch(job_id: str, paper_name: str, concept_name: str, dataset_name: str | None) -> KnowledgeGraphBatch`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收复现任务 ID、论文的名称、当前处理结果的名称、当前处理结果的名称，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `KnowledgeGraphBatch` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `paper_name` | `str` | 名为 `paper_name` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `concept_name` | `str` | 名为 `concept_name` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `dataset_name` | `str | None` | 名为 `dataset_name` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。；默认 空值 |

**输出**

- **Python 类型**：`KnowledgeGraphBatch`
- **语义**：返回 `KnowledgeGraphBatch` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `sha256_value` 计算内容身份、分数或派生结果，并把结果记为 论文SHA；构造 `KnowledgeSourceSnapshot` 结构化领域对象，并把结果记为 草稿；调用 `source_snapshot_hash` 完成该函数的一项辅助处理，并把结果记为 MCP 能力快照的 Hash；复制、序列化或校验结构化领域对象，并把结果记为 MCP 能力快照。
调用 `_entity` 完成该函数的一项辅助处理，并把结果记为 论文；调用 `_entity` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；计算初始化顺序集合，并保存为 当前处理结果；将 当前处理结果 初始化为空列表，用来收集后续结果。
如果当前处理结果的名称不为空，就调用 `_entity` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；把当前处理结果追加或合并到当前处理结果；把新的处理结果追加或合并到当前处理结果。
计算组合或计算已有值，并保存为 视图的 Hash；构造 `KnowledgeEvidenceRef` 结构化领域对象，并把结果记为 证据；将 证据来源与追溯信息 初始化为空列表，用来收集后续结果。
遍历当前可迭代输入，每次把当前项记为多个解包结果，然后构造 `KnowledgeProvenanceRecord` 结构化领域对象，并把结果记为 草稿对象；把新的处理结果追加或合并到证据来源与追溯信息。
构造并返回 `KnowledgeGraphBatch` 结构化领域对象。
```

#### `ingest_batch`

- **源码**：`tests/helpers/knowledge_base.py:322`
- **签名**：`def ingest_batch(repository, batch, *, key: str)`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收持久化仓库、当前批次记录集合、映射键或对象字段名，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `repository` | `未显式标注` | 持久化或目录访问端口；负责读取、CAS 更新或 Artifact 定位。 |
| `batch` | `未显式标注` | 当前批次记录集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `key` | `str` | 映射键或对象字段名；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
调用 `sha256_value` 计算内容身份、分数或派生结果，并把结果记为 请求内容 Hash；构造 `KnowledgeIngestionRecord` 结构化领域对象，并把结果记为 该调用返回的结果；调用 `ingest_batch` 完成该函数的一项辅助处理，并返回处理结果。
```

### `tests/helpers/model_routing.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `FakeProviders.__init__`

- **源码**：`tests/helpers/model_routing.py:56`
- **签名**：`def __init__(self, *, chat: Any = None, embedding: Any = None)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收对话、文本嵌入向量，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `chat` | `Any` | 名为 `chat` 的 `Any` 领域输入；用于当前函数的业务处理，具体约束见校验分支。；默认 空值 |
| `embedding` | `Any` | 文本嵌入向量；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 空值 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 对话、文本嵌入向量 分别保存到同名实例字段；计算使用固定配置或常量值，并保存为 对话集合；计算使用固定配置或常量值，并保存为 当前处理结果。
```

#### `FakeProviders.build_chat`

- **源码**：`tests/helpers/model_routing.py:62`
- **签名**：`def build_chat(self, profile: Any, *, max_output_tokens: int) -> Any`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收MCP Client 配置档案、最大实际输出 token 数，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `Any` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `profile` | `Any` | 运行/执行环境配置或 profile 标识；描述能力和限制，不是一次执行的结果。 |
| `max_output_tokens` | `int` | 敏感凭证或其引用；不得写入日志、Prompt 或普通 Artifact。 |

**输出**

- **Python 类型**：`Any`
- **语义**：返回 `Any` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
将新的计算结果累加或合并到对话集合。
如果对话为空，就拒绝继续处理并抛出 `AssertionError`，向调用方报告输入或运行失败。
返回对话的当前值。
```

#### `FakeProviders.build_embedding`

- **源码**：`tests/helpers/model_routing.py:68`
- **签名**：`def build_embedding(self, profile: Any) -> Any`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收MCP Client 配置档案，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `Any` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `profile` | `Any` | 运行/执行环境配置或 profile 标识；描述能力和限制，不是一次执行的结果。 |

**输出**

- **Python 类型**：`Any`
- **语义**：返回 `Any` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
将新的计算结果累加或合并到当前处理结果。
如果文本嵌入向量为空，就拒绝继续处理并抛出 `AssertionError`，向调用方报告输入或运行失败。
返回文本嵌入向量的当前值。
```

#### `ScriptedModelGateway.__init__`

- **源码**：`tests/helpers/model_routing.py:78`
- **签名**：`def __init__(self, invocations: Any)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `invocations` | `Any` | 名为 `invocations` 的 `Any` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入参数保存到实例字段（当前处理结果 → 当前处理结果）；将 工具或模型调用记录集合、当前处理结果 初始化为空列表，用来收集后续结果；构造 `SimpleNamespace` 结构化领域对象，并把结果记为 人工决策结果。
```

#### `ScriptedModelGateway.preview_structured`

- **源码**：`tests/helpers/model_routing.py:88`
- **签名**：`def preview_structured(self, **kwargs: Any) -> Any`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收函数关键字参数映射，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `Any` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `**kwargs` | `Any` | 额外关键字参数映射。 |

**输出**

- **Python 类型**：`Any`
- **语义**：返回 `Any` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
把新的处理结果追加或合并到当前处理结果；返回人工决策结果的当前值。
```

#### `ScriptedModelGateway.invoke_structured`

- **源码**：`tests/helpers/model_routing.py:92`
- **签名**：`def invoke_structured(self, **kwargs: Any) -> Any`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收函数关键字参数映射，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `Any` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `**kwargs` | `Any` | 额外关键字参数映射。 |

**输出**

- **Python 类型**：`Any`
- **语义**：返回 `Any` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
把新的处理结果追加或合并到工具或模型调用记录集合。
如果“调用 `callable` 完成该函数的一项辅助处理”后得到肯定结果：
    调用 `_invocations` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果。
否则：
    如果“当前处理结果有值或为真”不成立，就拒绝继续处理并抛出 `AssertionError`，向调用方报告输入或运行失败。
    从当前处理结果取出并移除最后一项，并把结果记为 阶段处理结果。
构造并返回 `SimpleNamespace` 结构化领域对象。
```

#### `_legacy_chat_profile`

- **源码**：`tests/helpers/model_routing.py:114`
- **签名**：`def _legacy_chat_profile(pricing: ModelPricing | None) -> ModelProfile`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收模型计费配置，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ModelProfile` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `pricing` | `ModelPricing | None` | 模型计费配置；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 空值 |

**输出**

- **Python 类型**：`ModelProfile`
- **语义**：返回 `ModelProfile` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `ModelProfile` 结构化领域对象。
```

#### `_strong_chat_profile`

- **源码**：`tests/helpers/model_routing.py:139`
- **签名**：`def _strong_chat_profile(pricing: ModelPricing | None) -> ModelProfile`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收模型计费配置，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ModelProfile` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `pricing` | `ModelPricing | None` | 模型计费配置；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 空值 |

**输出**

- **Python 类型**：`ModelProfile`
- **语义**：返回 `ModelProfile` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `ModelProfile` 结构化领域对象。
```

#### `_economy_chat_profile`

- **源码**：`tests/helpers/model_routing.py:164`
- **签名**：`def _economy_chat_profile(pricing: ModelPricing | None) -> ModelProfile`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收模型计费配置，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ModelProfile` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `pricing` | `ModelPricing | None` | 模型计费配置；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 空值 |

**输出**

- **Python 类型**：`ModelProfile`
- **语义**：返回 `ModelProfile` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `ModelProfile` 结构化领域对象。
```

#### `_legacy_embedding_profile`

- **源码**：`tests/helpers/model_routing.py:188`
- **签名**：`def _legacy_embedding_profile(pricing: ModelPricing | None) -> ModelProfile`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收模型计费配置，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ModelProfile` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `pricing` | `ModelPricing | None` | 模型计费配置；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 空值 |

**输出**

- **Python 类型**：`ModelProfile`
- **语义**：返回 `ModelProfile` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `ModelProfile` 结构化领域对象。
```

#### `build_test_document`

- **源码**：`tests/helpers/model_routing.py:207`
- **签名**：`def build_test_document(budget: ModelBudgetPolicy | None, extra_profiles: list[ModelProfile] | None, pricing_override: dict[str, ModelPricing] | None) -> ModelRoutingDocument`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收模型或实验资源预算、当前处理结果、当前处理结果，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `ModelRoutingDocument` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `budget` | `ModelBudgetPolicy | None` | 模型或实验资源预算；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 空值 |
| `extra_profiles` | `list[ModelProfile] | None` | `list[ModelProfile] | None` 元素集合；元素代表的业务对象由参数名 `extra_profiles` 和调用位置确定。；默认 空值 |
| `pricing_override` | `dict[str, ModelPricing] | None` | 名为 `pricing_override` 的键值映射；键和值分别承载的业务字段由读取/写入分支确定。；默认 空值 |

**输出**

- **Python 类型**：`ModelRoutingDocument`
- **语义**：返回 `ModelRoutingDocument` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
计算计算当前表达式的结果，并保存为 当前处理结果；计算初始化顺序集合，并保存为 MCP Client 配置档案集合。
如果当前处理结果有值或为真，就把当前处理结果追加或合并到MCP Client 配置档案集合。
计算初始化顺序集合，并保存为 当前处理结果；构造并返回 `ModelRoutingDocument` 结构化领域对象。
```

#### `write_test_policy`

- **源码**：`tests/helpers/model_routing.py:378`
- **签名**：`def write_test_policy(tmp_path: Path, document: ModelRoutingDocument | None) -> Path`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，把测试 Policy JSON 写入 tmp_path 内的文件。该函数接收临时工作目录路径、论文解析文档，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终一个经过边界校验的文件或目录路径。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `document` | `ModelRoutingDocument | None` | 论文解析文档；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 空值 |

**输出**

- **Python 类型**：`Path`
- **语义**：返回解析后的文件或目录路径对象。

**伪代码**

```text
计算计算当前表达式的结果，并保存为 模块或函数文档文本；创建临时工作目录路径对应的目录；计算组合或计算已有值，并保存为 安全策略的路径；将处理结果写入安全策略的路径指定的文件。
返回安全策略的路径的当前值。
```

#### `build_test_catalog`

- **源码**：`tests/helpers/model_routing.py:393`
- **签名**：`def build_test_catalog(tmp_path: Path, document: ModelRoutingDocument | None) -> 未显式标注（存在 return）`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收临时工作目录路径、论文解析文档，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `document` | `ModelRoutingDocument | None` | 论文解析文档；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 空值 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
调用 `write_test_policy` 持久化或更新当前领域数据，并把结果记为 安全策略的路径；调用 `load_model_catalog` 读取或查询当前阶段需要的数据，并返回处理结果。
```

#### `build_test_router`

- **源码**：`tests/helpers/model_routing.py:410`
- **签名**：`def build_test_router(tmp_path: Path, document: ModelRoutingDocument | None) -> ModelRouter`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收临时工作目录路径、论文解析文档，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `ModelRouter` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `document` | `ModelRoutingDocument | None` | 论文解析文档；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 空值 |

**输出**

- **Python 类型**：`ModelRouter`
- **语义**：返回 `ModelRouter` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `build_test_catalog` 组装当前阶段需要的领域对象，并把结果记为 模型、工具或 Artifact 目录；构造并返回 `ModelRouter` 结构化领域对象。
```

#### `build_test_gateway`

- **源码**：`tests/helpers/model_routing.py:418`
- **签名**：`def build_test_gateway(tmp_path: Path, mode: str, providers: FakeProviders | None, structured_invoker: Any, document: ModelRoutingDocument | None) -> ModelGateway`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收临时工作目录路径、MCP 评测或运行模式、模型服务商配置集合、当前处理结果等输入，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `ModelGateway` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `mode` | `str` | MCP 评测或运行模式；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 'off' |
| `providers` | `FakeProviders | None` | 模型服务商配置集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 空值 |
| `structured_invoker` | `Any` | 可调用依赖；由当前函数在受控位置调用。；默认 空值 |
| `document` | `ModelRoutingDocument | None` | 论文解析文档；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 空值 |

**输出**

- **Python 类型**：`ModelGateway`
- **语义**：返回 `ModelGateway` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `build_test_catalog` 组装当前阶段需要的领域对象，并把结果记为 模型、工具或 Artifact 目录；构造并返回 `ModelGateway` 结构化领域对象。
```

#### `build_chat_route_request`

- **源码**：`tests/helpers/model_routing.py:443`
- **签名**：`def build_chat_route_request(task_kind: str, estimated_input_tokens: int, requested_max_output_tokens: int, quality_tier: str, required_capabilities: set[str] | None, node_name: str, prompt_text: str) -> ModelRouteRequest`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收类别、估算的输入 token 数、调用方要求的最大输出 token 数、模型质量档位等输入，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `ModelRouteRequest` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `task_kind` | `str` | 名为 `task_kind` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。；默认 'chat_answer' |
| `estimated_input_tokens` | `int` | 敏感凭证或其引用；不得写入日志、Prompt 或普通 Artifact。；默认 100 |
| `requested_max_output_tokens` | `int` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。；默认 100 |
| `quality_tier` | `str` | 模型质量档位；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 'balanced' |
| `required_capabilities` | `set[str] | None` | `set[str] | None` 元素集合；元素代表的业务对象由参数名 `required_capabilities` 和调用位置确定。；默认 空值 |
| `node_name` | `str` | 名为 `node_name` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。；默认 'test_node' |
| `prompt_text` | `str` | 已规范化或待输出的文本；进入持久化或 Prompt 前可能需要限长和脱敏。；默认 'test prompt for routing' |

**输出**

- **Python 类型**：`ModelRouteRequest`
- **语义**：返回 `ModelRouteRequest` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
加载这一步需要的外部依赖；加载这一步需要的外部依赖。
定义内部类型 `_DummySchema`，用于组织当前函数的临时逻辑。
计算计算当前表达式的结果，并保存为 当前处理结果；构造并返回 `ModelRouteRequest` 结构化领域对象。
```

#### `build_embedding_route_request`

- **源码**：`tests/helpers/model_routing.py:475`
- **签名**：`def build_embedding_route_request(task_kind: str, estimated_input_tokens: int, node_name: str, prompt_text: str) -> ModelRouteRequest`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收类别、估算的输入 token 数、当前流程节点的名称、发给模型的结构化提示的文本，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `ModelRouteRequest` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `task_kind` | `str` | 名为 `task_kind` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。；默认 'code_embedding_query' |
| `estimated_input_tokens` | `int` | 敏感凭证或其引用；不得写入日志、Prompt 或普通 Artifact。；默认 100 |
| `node_name` | `str` | 名为 `node_name` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。；默认 'test_embedding_node' |
| `prompt_text` | `str` | 已规范化或待输出的文本；进入持久化或 Prompt 前可能需要限长和脱敏。；默认 'test embedding query' |

**输出**

- **Python 类型**：`ModelRouteRequest`
- **语义**：返回 `ModelRouteRequest` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
加载这一步需要的外部依赖；构造并返回 `ModelRouteRequest` 结构化领域对象。
```

### `tests/mcp_contract_helpers.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `observe_test_surfaces`

- **源码**：`tests/mcp_contract_helpers.py:26`
- **签名**：`async def observe_test_surfaces(tmp_path: Path)`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径，用于发现、观测或评估 MCP 的公开 Tool/Resource/Prompt 契约，比较协议、Schema、延迟和失败结果，并为论文复现系统保留可审核的基线或运行报告，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
调用 `build_test_service` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果；调用 `build_mcp_export_server` 组装当前阶段需要的领域对象，并把结果记为 MCP 服务端实例；返回当前构造的顺序或去重集合。
```

#### `baseline_from_observations`

- **源码**：`tests/mcp_contract_helpers.py:35`
- **签名**：`def baseline_from_observations(tmp_path: Path, observations: list) -> 未显式标注（存在 return）`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径、MCP Client 观测结果集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `observations` | `list` | MCP Client 观测结果集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
调用 `build_candidate` 组装当前阶段需要的领域对象，并把结果记为 待审核的 MCP 能力候选；调用 `promote_candidate` 完成该函数的一项辅助处理，并返回处理结果。
```

### `tests/mcp_export_helpers.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `FakeInteraction.__init__`

- **源码**：`tests/mcp_export_helpers.py:26`
- **签名**：`def __init__(self) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `SimpleNamespace` 结构化领域对象，并把结果记为 任务；构造 `SimpleNamespace` 结构化领域对象，并把结果记为 任务。
```

#### `FakeInteraction._get_internal_job`

- **源码**：`tests/mcp_export_helpers.py:35`
- **签名**：`def _get_internal_job(self, job_id: str)`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收复现任务 ID，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
如果复现任务 ID不等于复现任务 ID，就加载这一步需要的外部依赖；拒绝继续处理并抛出 `JobNotFoundError`，向调用方报告输入或运行失败。
返回任务的当前值。
```

#### `FakeInteraction.get_job`

- **源码**：`tests/mcp_export_helpers.py:42`
- **签名**：`def get_job(self, job_id: str)`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收复现任务 ID，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
调用 `_get_internal_job` 读取或查询当前阶段需要的数据；构造并返回 `SimpleNamespace` 结构化领域对象。
```

#### `FakeArtifactDelivery.__init__`

- **源码**：`tests/mcp_export_helpers.py:66`
- **签名**：`def __init__(self) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算初始化顺序集合，并保存为 Artifact 视图集合。
```

#### `FakeArtifactDelivery.list_views`

- **源码**：`tests/mcp_export_helpers.py:82`
- **签名**：`def list_views(self, _job)`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收复现任务记录，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `_job` | `未显式标注` | 名为 `_job` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
构造临时集合、映射或轻量领域对象，并返回处理结果。
```

#### `FakeArtifactDelivery.preview`

- **源码**：`tests/mcp_export_helpers.py:85`
- **签名**：`def preview(self, *, job, artifact_id: str)`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收复现任务记录、Artifact的 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job` | `未显式标注` | 任务、运行、Manifest、记录或证据领域对象；携带关联 ID、状态和内容身份。 |
| `artifact_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
断言复现任务 ID等于复现任务 ID；不满足就终止当前测试或流程；断言Artifact的 ID等于Artifact的 ID；不满足就终止当前测试或流程；计算根据字段和固定文本生成格式化文本，并保存为 业务内容；构造并返回 `SimpleNamespace` 结构化领域对象。
```

#### `FakeEvidenceRegistry.__init__`

- **源码**：`tests/mcp_export_helpers.py:104`
- **签名**：`def __init__(self) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
将 工具或模型调用记录集合 初始化为空列表，用来收集后续结果。
```

#### `FakeEvidenceRegistry.invoke`

- **源码**：`tests/mcp_export_helpers.py:107`
- **签名**：`def invoke(self, **kwargs)`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收函数关键字参数映射，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `**kwargs` | `未显式标注` | 额外关键字参数映射。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
把函数关键字参数映射追加或合并到工具或模型调用记录集合；构造 `EvidenceToolOutput` 结构化领域对象，并把结果记为 输出结果；构造并返回 `SimpleNamespace` 结构化领域对象。
```

#### `build_test_service`

- **源码**：`tests/mcp_export_helpers.py:138`
- **签名**：`def build_test_service(tmp_path: Path) -> tuple[ReadOnlyMcpExportService, SqliteMcpExportAuditRepository, FakeArtifactDelivery, FakeEvidenceRegistry]`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`tuple[ReadOnlyMcpExportService, SqliteMcpExportAuditRepository, FakeArtifactDelivery, FakeEvidenceRegistry]`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
构造 `SqliteMcpExportAuditRepository` 结构化领域对象，并把结果记为 该调用返回的结果；调用 `initialize` 完成该函数的一项辅助处理；构造 `FakeArtifactDelivery` 结构化领域对象，并把结果记为 通知投递记录；构造 `FakeEvidenceRegistry` 结构化领域对象，并把结果记为 组件注册表。
构造 `ReadOnlyMcpExportService` 结构化领域对象，并把结果记为 领域服务对象；返回当前构造的顺序或去重集合。
```

### `tests/mcp_gateway_helpers.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `make_binding`

- **源码**：`tests/mcp_gateway_helpers.py:57`
- **签名**：`def make_binding() -> McpToolBinding`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `McpToolBinding` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`McpToolBinding`
- **语义**：返回 `McpToolBinding` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `McpToolBinding` 结构化领域对象。
```

#### `make_profile`

- **源码**：`tests/mcp_gateway_helpers.py:68`
- **签名**：`def make_profile(*, enabled: bool = True) -> McpServerProfile`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收功能是否启用的开关，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `McpServerProfile` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `enabled` | `bool` | 布尔条件或能力开关，用于控制流程分支。；默认 真 |

**输出**

- **Python 类型**：`McpServerProfile`
- **语义**：返回 `McpServerProfile` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `McpServerProfile` 结构化领域对象。
```

#### `make_policy`

- **源码**：`tests/mcp_gateway_helpers.py:77`
- **签名**：`def make_policy(*, enabled: bool = True) -> McpGatewayPolicy`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收功能是否启用的开关，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `McpGatewayPolicy` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `enabled` | `bool` | 布尔条件或能力开关，用于控制流程分支。；默认 真 |

**输出**

- **Python 类型**：`McpGatewayPolicy`
- **语义**：返回 `McpGatewayPolicy` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `McpGatewayPolicy` 结构化领域对象。
```

#### `observed_tool`

- **源码**：`tests/mcp_gateway_helpers.py:84`
- **签名**：`def observed_tool() -> McpObservedTool`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `McpObservedTool` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`McpObservedTool`
- **语义**：返回 `McpObservedTool` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `McpObservedTool` 结构化领域对象。
```

#### `remote_payload`

- **源码**：`tests/mcp_gateway_helpers.py:96`
- **签名**：`def remote_payload() -> dict[str, Any]`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`dict[str, Any]`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
返回包含 `items`、`truncated` 字段的结构化映射。
```

#### `FakeMcpClient.inspect_tool`

- **源码**：`tests/mcp_gateway_helpers.py:116`
- **签名**：`def inspect_tool(self, *, profile, binding) -> McpObservedTool`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收MCP Client 配置档案、资源绑定记录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `McpObservedTool` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `profile` | `未显式标注` | 运行/执行环境配置或 profile 标识；描述能力和限制，不是一次执行的结果。 |
| `binding` | `未显式标注` | 资源绑定记录；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`McpObservedTool`
- **语义**：返回 `McpObservedTool` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
把新的处理结果追加或合并到工具或模型调用记录集合；返回前一步处理得到的结果。
```

#### `FakeMcpClient.call_pinned_tool`

- **源码**：`tests/mcp_gateway_helpers.py:120`
- **签名**：`def call_pinned_tool(self, *, profile, binding, arguments) -> McpRawCallResult`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收MCP Client 配置档案、资源绑定记录、结构化调用参数，用于在固定 MCP Policy、Schema Pin、调用预算和只读职责边界内连接或调用外部能力，并把返回内容转换为可追溯的复现证据，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `profile` | `未显式标注` | 运行/执行环境配置或 profile 标识；描述能力和限制，不是一次执行的结果。 |
| `binding` | `未显式标注` | 资源绑定记录；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `arguments` | `未显式标注` | 结构化调用参数；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`McpRawCallResult`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
把新的处理结果追加或合并到工具或模型调用记录集合；构造并返回 `McpRawCallResult` 结构化领域对象。
```

### `tests/research_browser_helpers.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `research_policy`

- **源码**：`tests/research_browser_helpers.py:26`
- **签名**：`def research_policy(**updates) -> ResearchPolicyDocument`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收待应用的字段更新映射，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ResearchPolicyDocument` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `**updates` | `未显式标注` | 额外关键字参数映射。 |

**输出**

- **Python 类型**：`ResearchPolicyDocument`
- **语义**：返回 `ResearchPolicyDocument` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
计算按字段初始化键值映射，并保存为 结构化请求载荷；把待应用的字段更新映射追加或合并到结构化请求载荷；复制、序列化或校验结构化领域对象，并返回处理结果。
```

#### `research_request`

- **源码**：`tests/research_browser_helpers.py:53`
- **签名**：`def research_request(**updates) -> ResearchRequest`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收待应用的字段更新映射，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ResearchRequest` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `**updates` | `未显式标注` | 额外关键字参数映射。 |

**输出**

- **Python 类型**：`ResearchRequest`
- **语义**：返回 `ResearchRequest` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
计算按字段初始化键值映射，并保存为 结构化请求载荷；把待应用的字段更新映射追加或合并到结构化请求载荷；复制、序列化或校验结构化领域对象，并返回处理结果。
```

#### `evidence_draft`

- **源码**：`tests/research_browser_helpers.py:67`
- **签名**：`def evidence_draft() -> ResearchEvidenceDraft`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ResearchEvidenceDraft` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`ResearchEvidenceDraft`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
计算使用固定配置或常量值，并保存为 待处理文本；调用 `sha256_text` 计算内容身份、分数或派生结果，并把结果记为 待处理文本的 Hash；构造 `ExtractedBlock` 结构化领域对象，并把结果记为 论文原文块；计算使用固定配置或常量值，并保存为 请求正文。
调用 `sha256_bytes` 计算内容身份、分数或派生结果，并把结果记为 请求正文的 Hash；构造 `ResearchSourceSnapshot` 结构化领域对象，并把结果记为 MCP 能力快照；调用 `sha256_text` 计算内容身份、分数或派生结果，并把结果记为 当前处理结果的 Hash；构造 `ResearchCitation` 结构化领域对象，并把结果记为 论文引用证据。
构造并返回 `ResearchEvidenceDraft` 结构化领域对象。
```

#### `evidence_pack`

- **源码**：`tests/research_browser_helpers.py:134`
- **签名**：`def evidence_pack(session_id: str, request_hash: str, policy_hash: str) -> ResearchEvidencePack`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前处理结果的 ID、请求内容 Hash、安全策略的 Hash，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ResearchEvidencePack` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `session_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。；默认 'research_' + 'a' × 24 |
| `request_hash` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。；默认 '2' × 64 |
| `policy_hash` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。；默认 '1' × 64 |

**输出**

- **Python 类型**：`ResearchEvidencePack`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
调用 `evidence_draft` 完成该函数的一项辅助处理，并把结果记为 可追溯证据记录；构造 `ResearchReport` 结构化领域对象，并把结果记为 MCP 评测或运行报告；调用 `stable_id` 完成该函数的一项辅助处理，并把结果记为 检索或映射证据包的 ID；构造 `ResearchEvidencePack` 结构化领域对象，并把结果记为 草稿对象。
复制、序列化或校验结构化领域对象，并返回处理结果。
```

#### `FakeResponse.iter_bytes`

- **源码**：`tests/research_browser_helpers.py:185`
- **签名**：`def iter_bytes(self, *, chunk_size: int) -> Iterator[bytes]`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收文本块，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `Iterator[bytes]` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `chunk_size` | `int` | 名为 `chunk_size` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`Iterator[bytes]`
- **语义**：返回惰性迭代结果，调用方逐项消费。

**伪代码**

```text
移除文本块中的当前内容；完成当前表达式对应的校验或状态操作。
```

#### `FakeTransport.__init__`

- **源码**：`tests/research_browser_helpers.py:191`
- **签名**：`def __init__(self, responses: dict[str, list[FakeResponse]]) -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收结构化响应集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `responses` | `dict[str, list[FakeResponse]]` | 前序调用产生的结构化响应、结果或执行结论，供当前函数继续判断或投影。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 结构化响应集合 分别保存到同名实例字段；将 工具或模型调用记录集合 初始化为空列表，用来收集后续结果。
```

#### `FakeTransport.stream`

- **源码**：`tests/research_browser_helpers.py:196`
- **签名**：`def stream(self, method: str, url: str)`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收论文方法或 HTTP 方法、外部论文、仓库或服务地址，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `method` | `str` | 论文方法或 HTTP 方法；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `url` | `str` | 资源地址；进入网络或持久化前仍需策略校验和必要的脱敏。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把新的处理结果追加或合并到工具或模型调用记录集合；从结构化响应集合读取所需的状态或领域记录，并把结果记为 候选结果集合。
如果候选结果集合为空或为假，就拒绝继续处理并抛出 `AssertionError`，向调用方报告输入或运行失败。
完成当前表达式对应的校验或状态操作。
```

#### `AllowRobots.check`

- **源码**：`tests/research_browser_helpers.py:205`
- **签名**：`def check(self, target) -> str`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收待定位的代码对象或业务目标，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `target` | `未显式标注` | 待定位的代码对象或业务目标；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
移除待定位的代码对象或业务目标中的当前内容；返回固定值 `'allowed'`。
```

#### `DenyRobots.check`

- **源码**：`tests/research_browser_helpers.py:211`
- **签名**：`def check(self, target) -> str`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收待定位的代码对象或业务目标，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `target` | `未显式标注` | 待定位的代码对象或业务目标；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
加载这一步需要的外部依赖；拒绝继续处理并抛出 `ResearchRobotsDenied`，向调用方报告输入或运行失败。
```

### `tests/skill_test_helpers.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `base_manifest`

- **源码**：`tests/skill_test_helpers.py:13`
- **签名**：`def base_manifest(skill_id: str, implementation_id: str) -> dict[str, Any]`
- **作用**：在论文复现 Agent Skill/Plugin 的清单加载、权限隔离、运行时和调试日志验证阶段中，该函数接收当前处理结果的 ID、当前处理结果的 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `skill_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。；默认 'example_skill' |
| `implementation_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。；默认 'builtin.example_skill.v1' |

**输出**

- **Python 类型**：`dict[str, Any]`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
返回包含 `manifest_version`、`skill_id`、`skill_version`、`display_name`、`summary`、`implementation_id`、`input_schema_id`、`output_schema_id` 等字段的结构化映射。
```

#### `write_skill_package`

- **源码**：`tests/skill_test_helpers.py:44`
- **签名**：`def write_skill_package(root: Path, manifest: dict[str, Any] | None) -> DiscoveredSkillPackage`
- **作用**：在论文复现 Agent Skill/Plugin 的清单加载、权限隔离、运行时和调试日志验证阶段中，该函数接收受控扫描根目录、运行或工作区 Manifest，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终标注为 `DiscoveredSkillPackage` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `root` | `Path` | 运行产物或受控工作区的目录路径；用于隔离本次运行生成的文件。 |
| `manifest` | `dict[str, Any] | None` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。；默认 空值 |

**输出**

- **Python 类型**：`DiscoveredSkillPackage`
- **语义**：返回 `DiscoveredSkillPackage` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
计算计算当前表达式的结果，并保存为 结构化请求载荷；计算组合或计算已有值，并保存为 当前处理结果的目录；创建当前处理结果的目录对应的目录；将处理结果写入当前输入内容指定的文件。
调用 `load_skill_package` 读取或查询当前阶段需要的数据，并返回处理结果。
```

### `tests/test_cuda_build_diagnosis_skill.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_classifies_missing_nvcc`

- **源码**：`tests/test_cuda_build_diagnosis_skill.py:8`
- **签名**：`def test_classifies_missing_nvcc()`
- **作用**：在论文复现 Agent Skill/Plugin 的清单加载、权限隔离、运行时和调试日志验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_classify_findings` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；断言评测类别等于'cuda_toolchain'；不满足就终止当前测试或流程；断言当前输入内容属于当前处理结果；不满足就终止当前测试或流程；断言当前输入内容属于辅助操作“调用 `_search_keywords` 读取或查询当前阶段需要的数据”的结果；不满足就终止当前测试或流程。
断言“调用 `_recommended_checks` 完成该函数的一项辅助处理”后得到肯定结果；不满足就终止当前测试或流程。
```

#### `test_classifies_extension_abi_mismatch`

- **源码**：`tests/test_cuda_build_diagnosis_skill.py:19`
- **签名**：`def test_classifies_extension_abi_mismatch()`
- **作用**：在论文复现 Agent Skill/Plugin 的清单加载、权限隔离、运行时和调试日志验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_classify_findings` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；断言评测类别等于'extension_abi'；不满足就终止当前测试或流程；断言当前处理结果等于['EXTENSION_ABI_MISMATCH']；不满足就终止当前测试或流程。
```

#### `test_unknown_build_failure_stays_conservative`

- **源码**：`tests/test_cuda_build_diagnosis_skill.py:28`
- **签名**：`def test_unknown_build_failure_stays_conservative()`
- **作用**：在论文复现 Agent Skill/Plugin 的清单加载、权限隔离、运行时和调试日志验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_classify_findings` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；断言评测类别等于'unknown_cuda_build'；不满足就终止当前测试或流程；断言当前处理结果等于['CUDA_BUILD_FAILURE_UNCLASSIFIED']；不满足就终止当前测试或流程。
```

### `tests/test_knowledge_authority_boundary.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_knowledge_modules_do_not_import_execution_authority`

- **源码**：`tests/test_knowledge_authority_boundary.py:12`
- **签名**：`def test_knowledge_modules_do_not_import_execution_authority()`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把外部位置解析为文件系统路径对象，并把结果记为 受控扫描根目录；调用 `join` 完成该函数的一项辅助处理，并把结果记为 数据来源标记。
遍历由当前处理结果组成的集合或迭代器，每次把当前项记为被策略禁止的内容或操作，然后断言当前输入内容不属于数据来源标记；不满足就终止当前测试或流程；断言当前输入内容不属于数据来源标记；不满足就终止当前测试或流程。
```

### `tests/test_knowledge_chat_integration.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_chat_source_binds_pack_subject_and_evidence`

- **源码**：`tests/test_knowledge_chat_integration.py:8`
- **签名**：`def test_chat_source_binds_pack_subject_and_evidence(tmp_path)`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `SqliteKnowledgeRepository` 结构化领域对象，并把结果记为 持久化仓库；调用 `initialize` 完成该函数的一项辅助处理；调用 `ingest_batch` 完成该函数的一项辅助处理；构造 `ChatContextBuilder` 结构化领域对象，并把结果记为 领域对象构造器。
调用 `_knowledge_sources` 完成该函数的一项辅助处理，并把结果记为 证据来源集合；断言证据来源集合有值或为真；不满足就终止当前测试或流程；读取论文引用证据，并保存为 论文引用证据；断言来源类型等于'knowledge'；不满足就终止当前测试或流程。
断言当前处理结果的 Hash不为空；不满足就终止当前测试或流程；断言当前处理结果的 ID不为空；不满足就终止当前测试或流程；断言证据集合有值或为真；不满足就终止当前测试或流程。
```

#### `test_non_knowledge_citation_rejects_knowledge_identity`

- **源码**：`tests/test_knowledge_chat_integration.py:42`
- **签名**：`def test_non_knowledge_citation_rejects_knowledge_identity()`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
先尝试完成以下处理：
    构造 `ChatCitation` 结构化领域对象。
如果出现 `ValueError`：
    结束当前函数，不返回业务值。
拒绝继续处理并抛出 `AssertionError`，向调用方报告输入或运行失败。
```

### `tests/test_knowledge_golden_eval.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_cross_paper_offline_golden_suite`

- **源码**：`tests/test_knowledge_golden_eval.py:12`
- **签名**：`def test_cross_paper_offline_golden_suite(tmp_path)`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `SqliteKnowledgeRepository` 结构化领域对象，并把结果记为 持久化仓库；调用 `initialize` 完成该函数的一项辅助处理；调用 `ingest_batch` 完成该函数的一项辅助处理；调用 `ingest_batch` 完成该函数的一项辅助处理。
调用 `load_knowledge_golden_cases` 读取或查询当前阶段需要的数据，并把结果记为 多个解包结果；调用 `evaluate_knowledge_cases` 完成该函数的一项辅助处理，并把结果记为 MCP 评测或运行报告；断言当前处理结果是真；不满足就终止当前测试或流程；断言当前处理结果的数量等于评测用例的数量等于2；不满足就终止当前测试或流程。
```

### `tests/test_knowledge_identity.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_entity_identity_is_source_scoped`

- **源码**：`tests/test_knowledge_identity.py:12`
- **签名**：`def test_entity_identity_is_source_scoped()`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `normalize_knowledge_key` 解析、规范化或转换当前输入，并把结果记为 规范化；调用 `build_entity_id` 组装当前阶段需要的领域对象，并把结果记为 第一项；调用 `build_entity_id` 组装当前阶段需要的领域对象，并把结果记为 第二项；断言第一项不等于第二项；不满足就终止当前测试或流程。
```

#### `test_equivalence_relation_identity_is_symmetric`

- **源码**：`tests/test_knowledge_identity.py:27`
- **签名**：`def test_equivalence_relation_identity_is_symmetric()`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `build_relation_id` 组装当前阶段需要的领域对象，并把结果记为 第一项；调用 `build_relation_id` 组装当前阶段需要的领域对象，并把结果记为 第二项；断言第一项等于第二项；不满足就终止当前测试或流程。
```

#### `test_asserted_relation_cannot_be_reviewed_as_candidate`

- **源码**：`tests/test_knowledge_identity.py:41`
- **签名**：`def test_asserted_relation_cannot_be_reviewed_as_candidate()`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_relation` 完成该函数的一项辅助处理，并把结果记为 领域关系。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `reviewed_relation` 完成该函数的一项辅助处理，退出时自动清理资源。
```

### `tests/test_knowledge_projector.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_projector_builds_paper_section_claim_and_concept`

- **源码**：`tests/test_knowledge_projector.py:9`
- **签名**：`def test_projector_builds_paper_section_claim_and_concept()`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `make_source_fixture` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；构造 `KnowledgeSourceReader` 结构化领域对象，并把结果记为 证据读取器；调用 `project` 完成该函数的一项辅助处理，并把结果记为 当前批次记录集合；遍历并筛选输入，将整理后的结果保存为 当前处理结果。
遍历并筛选输入，将整理后的结果保存为 关系集合；断言当前输入内容不大于当前处理结果；不满足就终止当前测试或流程；断言当前输入内容属于关系集合；不满足就终止当前测试或流程；断言当前输入内容属于关系集合；不满足就终止当前测试或流程。
断言当前输入内容属于关系集合；不满足就终止当前测试或流程；断言当前输入内容等于{*[item.entity_id for item in batch.entities], *[item.relation_id for item in batch.relations]}；不满足就终止当前测试或流程。
```

### `tests/test_knowledge_relation_review.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_service`

- **源码**：`tests/test_knowledge_relation_review.py:14`
- **签名**：`def _service(repository)`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收持久化仓库，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `repository` | `未显式标注` | 持久化或目录访问端口；负责读取、CAS 更新或 Artifact 定位。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
构造并返回 `KnowledgeService` 结构化领域对象。
```

#### `test_equivalence_requires_review_and_rejects_stale`

- **源码**：`tests/test_knowledge_relation_review.py:24`
- **签名**：`def test_equivalence_requires_review_and_rejects_stale(tmp_path)`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `SqliteKnowledgeRepository` 结构化领域对象，并把结果记为 持久化仓库；调用 `initialize` 完成该函数的一项辅助处理；调用 `make_graph_batch` 完成该函数的一项辅助处理，并把结果记为 第一项；调用 `make_graph_batch` 完成该函数的一项辅助处理，并把结果记为 第二项。
调用 `ingest_batch` 完成该函数的一项辅助处理；调用 `ingest_batch` 完成该函数的一项辅助处理；调用 `search_entities` 读取或查询当前阶段需要的数据，并把结果记为 该调用返回的结果；断言当前处理结果 的长度等于2；不满足就终止当前测试或流程。
调用 `_service` 完成该函数的一项辅助处理，并把结果记为 领域服务对象；调用 `propose_equivalence` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；断言当前状态等于'candidate'；不满足就终止当前测试或流程；读取领域关系的 Hash，并保存为 当前处理结果的 Hash。
调用 `review_relation` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；断言当前状态等于'confirmed'；不满足就终止当前测试或流程；断言记录版本号等于1；不满足就终止当前测试或流程；调用 `review_relation` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
断言重放的是真；不满足就终止当前测试或流程；断言领域关系等于领域关系；不满足就终止当前测试或流程。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `review_relation` 完成该函数的一项辅助处理，退出时自动清理资源。
```

### `tests/test_knowledge_repository.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_ingestion_is_transactional_and_idempotent`

- **源码**：`tests/test_knowledge_repository.py:12`
- **签名**：`def test_ingestion_is_transactional_and_idempotent(tmp_path)`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `SqliteKnowledgeRepository` 结构化领域对象，并把结果记为 持久化仓库；调用 `initialize` 完成该函数的一项辅助处理；调用 `make_graph_batch` 完成该函数的一项辅助处理，并把结果记为 当前批次记录集合；调用 `ingest_batch` 完成该函数的一项辅助处理，并把结果记为 多个解包结果。
调用 `ingest_batch` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；断言第一项重放是假；不满足就终止当前测试或流程；断言第二项重放是真；不满足就终止当前测试或流程；断言第一项等于第二项；不满足就终止当前测试或流程。
断言已创建的数量等于2；不满足就终止当前测试或流程。
```

#### `test_same_key_with_different_snapshot_is_rejected`

- **源码**：`tests/test_knowledge_repository.py:28`
- **签名**：`def test_same_key_with_different_snapshot_is_rejected(tmp_path)`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `SqliteKnowledgeRepository` 结构化领域对象，并把结果记为 持久化仓库；调用 `initialize` 完成该函数的一项辅助处理；调用 `make_graph_batch` 完成该函数的一项辅助处理，并把结果记为 第一项；调用 `make_graph_batch` 完成该函数的一项辅助处理，并把结果记为 第二项。
调用 `ingest_batch` 完成该函数的一项辅助处理。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `ingest_batch` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `test_archive_removes_active_job_reference`

- **源码**：`tests/test_knowledge_repository.py:46`
- **签名**：`def test_archive_removes_active_job_reference(tmp_path)`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `SqliteKnowledgeRepository` 结构化领域对象，并把结果记为 持久化仓库；调用 `initialize` 完成该函数的一项辅助处理；调用 `make_graph_batch` 完成该函数的一项辅助处理，并把结果记为 当前批次记录集合；调用 `ingest_batch` 完成该函数的一项辅助处理，并把结果记为 多个解包结果。
断言辅助操作“调用 `active_referenced_job_ids` 完成该函数的一项辅助处理”的结果等于{'job-a'}；不满足就终止当前测试或流程；调用 `archive_ingestion` 完成该函数的一项辅助处理；断言辅助操作“调用 `active_referenced_job_ids` 完成该函数的一项辅助处理”的结果等于辅助操作“构造临时集合、映射或轻量领域对象”的结果；不满足就终止当前测试或流程。
```

### `tests/test_knowledge_retention.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_active_ingestion_holds_source_job`

- **源码**：`tests/test_knowledge_retention.py:5`
- **签名**：`def test_active_ingestion_holds_source_job(tmp_path)`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `SqliteKnowledgeRepository` 结构化领域对象，并把结果记为 持久化仓库；调用 `initialize` 完成该函数的一项辅助处理；调用 `ingest_batch` 完成该函数的一项辅助处理；断言辅助操作“调用 `active_referenced_job_ids` 完成该函数的一项辅助处理”的结果等于{'job-held'}；不满足就终止当前测试或流程。
```

### `tests/test_knowledge_retrieval.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_cross_paper_query_returns_evidence_without_candidates`

- **源码**：`tests/test_knowledge_retrieval.py:7`
- **签名**：`def test_cross_paper_query_returns_evidence_without_candidates(tmp_path)`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `SqliteKnowledgeRepository` 结构化领域对象，并把结果记为 持久化仓库；调用 `initialize` 完成该函数的一项辅助处理；调用 `ingest_batch` 完成该函数的一项辅助处理；调用 `ingest_batch` 完成该函数的一项辅助处理。
调用 `query` 完成该函数的一项辅助处理，并把结果记为 检索或映射证据包；断言当前输入内容等于{'PST convolution', 'P4D convolution'}；不满足就终止当前测试或流程；断言候选项集合等于[]；不满足就终止当前测试或流程；断言证据集合有值或为真；不满足就终止当前测试或流程。
断言证据有值或为真；不满足就终止当前测试或流程。
```

### `tests/test_knowledge_schemas.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_paper_evidence_requires_paper_identity`

- **源码**：`tests/test_knowledge_schemas.py:11`
- **签名**：`def test_paper_evidence_requires_paper_identity()`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中构造 `KnowledgeEvidenceRef` 结构化领域对象，退出时自动清理资源。
```

#### `test_candidate_requires_proposal_reason`

- **源码**：`tests/test_knowledge_schemas.py:25`
- **签名**：`def test_candidate_requires_proposal_reason()`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中构造 `KnowledgeRelationRecord` 结构化领域对象，退出时自动清理资源。
```

### `tests/test_knowledge_source_reader.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_reader`

- **源码**：`tests/test_knowledge_source_reader.py:11`
- **签名**：`def _reader(evidence, catalog)`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收可追溯证据记录、模型、工具或 Artifact 目录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `evidence` | `未显式标注` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |
| `catalog` | `未显式标注` | 持久化或目录访问端口；负责读取、CAS 更新或 Artifact 定位。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
构造并返回 `KnowledgeSourceReader` 结构化领域对象。
```

#### `test_reader_loads_only_fixed_verified_artifacts`

- **源码**：`tests/test_knowledge_source_reader.py:22`
- **签名**：`def test_reader_loads_only_fixed_verified_artifacts()`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `make_source_fixture` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；调用 `read` 完成该函数的一项辅助处理，并把结果记为 代码仓库归档包；断言数据来源标记的 SHA-256等于'a' × 64；不满足就终止当前测试或流程；断言论文文档章节的 ID等于'section-method'；不满足就终止当前测试或流程。
断言对象名称等于'PST convolution'；不满足就终止当前测试或流程。
```

#### `test_reader_rejects_tampered_blob`

- **源码**：`tests/test_knowledge_source_reader.py:30`
- **签名**：`def test_reader_rejects_tampered_blob()`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `make_source_fixture` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；读取Artifact的 ID，并保存为 第一项的 ID；将新的计算结果累加或合并到当前处理结果中的对应字段。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `read` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `test_reader_rejects_workspace_paper_identity_drift`

- **源码**：`tests/test_knowledge_source_reader.py:38`
- **签名**：`def test_reader_rejects_workspace_paper_identity_drift()`
- **作用**：在跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `make_source_fixture` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；计算组合或计算已有值，并保存为 内容 SHA-256。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `read` 完成该函数的一项辅助处理，退出时自动清理资源。
```

### `tests/test_mcp_contract_authority.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `imported_modules`

- **源码**：`tests/test_mcp_contract_authority.py:20`
- **签名**：`def imported_modules(path: Path) -> set[str]`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收文件或目录路径，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`set[str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
将 Python 源码解析为抽象语法树，并把结果记为 该调用返回的结果；将 Python 模块集合 初始化为空去重集合，用来收集后续结果。
遍历语法树节点集合，每次把当前项记为当前流程节点：
    如果“计算数量、边界或类型判断结果”后得到肯定结果：
        把新的处理结果追加或合并到Python 模块集合。
    否则：
        如果“计算数量、边界或类型判断结果”后得到肯定结果 且 Python 模块有值或为真，就把Python 模块追加或合并到Python 模块集合。
返回Python 模块集合的当前值。
```

#### `test_contract_package_does_not_import_mutation_runtime`

- **源码**：`tests/test_mcp_contract_authority.py:31`
- **签名**：`def test_contract_package_does_not_import_mutation_runtime() -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
将 约束违反项集合 初始化为空列表，用来收集后续结果。
遍历辅助操作产生的可迭代结果（枚举当前处理结果下符合范围的文件系统项），每次把当前项记为文件或目录路径：
    遍历辅助操作产生的可迭代结果（调用 `imported_modules` 完成该函数的一项辅助处理），每次把当前项记为Python 模块：
        如果由当前处理结果组成的集合或迭代器中存在满足“Python 模块等于目录树缩进前缀 或 “检查Python 模块是否满足文本匹配条件”后得到肯定结果”的项，就把新的处理结果追加或合并到约束违反项集合。
断言约束违反项集合等于[]；不满足就终止当前测试或流程。
```

#### `test_contract_package_has_no_business_tool_invocation`

- **源码**：`tests/test_mcp_contract_authority.py:43`
- **签名**：`def test_contract_package_has_no_business_tool_invocation() -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算初始化去重集合，并保存为 当前处理结果；调用 `join` 完成该函数的一项辅助处理，并把结果记为 数据来源标记。
遍历由当前处理结果组成的集合或迭代器，每次把当前项记为对象名称，然后断言当前输入内容不属于数据来源标记；不满足就终止当前测试或流程。
```

### `tests/test_mcp_contract_baseline.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `anyio_backend`

- **源码**：`tests/test_mcp_contract_baseline.py:24`
- **签名**：`def anyio_backend() -> str`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
返回固定值 `'asyncio'`。
```

#### `test_candidate_round_trip_is_hash_bound`

- **源码**：`tests/test_mcp_contract_baseline.py:28`
- **签名**：`async def test_candidate_round_trip_is_hash_bound(tmp_path) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
等待异步处理完成，并把结果记为 MCP Client 观测结果集合；调用 `build_candidate` 组装当前阶段需要的领域对象，并把结果记为 待审核的 MCP 能力候选；计算组合或计算已有值，并保存为 文件或目录路径；调用 `write_candidate` 持久化或更新当前领域数据。
调用 `load_candidate` 读取或查询当前阶段需要的数据，并把结果记为 已加载结果；断言待审核的 MCP 能力候选的 SHA-256等于待审核的 MCP 能力候选的 SHA-256；不满足就终止当前测试或流程；断言当前处理结果是真；不满足就终止当前测试或流程。
```

#### `test_tampered_candidate_is_rejected`

- **源码**：`tests/test_mcp_contract_baseline.py:40`
- **签名**：`async def test_tampered_candidate_is_rejected(tmp_path) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `build_candidate` 组装当前阶段需要的领域对象，并把结果记为 待审核的 MCP 能力候选；计算组合或计算已有值，并保存为 文件或目录路径；调用 `write_candidate` 持久化或更新当前领域数据；将外部表示解析为结构化内容，并把结果记为 结构化请求载荷。
计算组合或计算已有值，并保存为 结构化请求载荷中的对应字段；将处理结果写入文件或目录路径指定的文件。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `load_candidate` 读取或查询当前阶段需要的数据，退出时自动清理资源。
```

#### `test_symlinked_candidate_is_rejected`

- **源码**：`tests/test_mcp_contract_baseline.py:52`
- **签名**：`async def test_symlinked_candidate_is_rejected(tmp_path) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `build_candidate` 组装当前阶段需要的领域对象，并把结果记为 待审核的 MCP 能力候选；计算组合或计算已有值，并保存为 待定位的代码对象或业务目标；计算组合或计算已有值，并保存为 当前处理结果；调用 `write_candidate` 持久化或更新当前领域数据。
调用 `symlink_to` 完成该函数的一项辅助处理。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `load_candidate` 读取或查询当前阶段需要的数据，退出时自动清理资源。
```

#### `test_promotion_requires_expected_surface_hash`

- **源码**：`tests/test_mcp_contract_baseline.py:63`
- **签名**：`async def test_promotion_requires_expected_surface_hash(tmp_path) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `build_candidate` 组装当前阶段需要的领域对象，并把结果记为 待审核的 MCP 能力候选。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `promote_candidate` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `test_replacement_requires_current_baseline_hash`

- **源码**：`tests/test_mcp_contract_baseline.py:81`
- **签名**：`async def test_replacement_requires_current_baseline_hash(tmp_path) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `build_candidate` 组装当前阶段需要的领域对象，并把结果记为 待审核的 MCP 能力候选；计算组合或计算已有值，并保存为 文件或目录路径；调用 `promote_candidate` 完成该函数的一项辅助处理，并把结果记为 第一项；断言前一步操作返回对象的已审核的 MCP 能力基线的 SHA-256等于已审核的 MCP 能力基线的 SHA-256；不满足就终止当前测试或流程。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `promote_candidate` 完成该函数的一项辅助处理，退出时自动清理资源。
```

### `tests/test_mcp_contract_evaluator.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `anyio_backend`

- **源码**：`tests/test_mcp_contract_evaluator.py:20`
- **签名**：`def anyio_backend() -> str`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
返回固定值 `'asyncio'`。
```

#### `test_offline_profiles_pass_reviewed_baseline`

- **源码**：`tests/test_mcp_contract_evaluator.py:24`
- **签名**：`async def test_offline_profiles_pass_reviewed_baseline(tmp_path) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
等待异步处理完成，并把结果记为 MCP Client 观测结果集合；调用 `baseline_from_observations` 完成该函数的一项辅助处理，并把结果记为 已审核的 MCP 能力基线；等待异步处理完成，并把结果记为 MCP 评测或运行报告；断言当前处理结果是真；不满足就终止当前测试或流程。
断言当前输入内容等于{'passed'}；不满足就终止当前测试或流程。
```

#### `test_surface_hash_drift_is_release_blocking`

- **源码**：`tests/test_mcp_contract_evaluator.py:45`
- **签名**：`async def test_surface_hash_drift_is_release_blocking(tmp_path) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
等待异步处理完成，并把结果记为 MCP Client 观测结果集合；复制、序列化或校验结构化领域对象，并把结果记为 已审核的 MCP 能力基线；调用 `compare_observation` 完成该函数的一项辅助处理，并把结果记为 诊断发现集合；断言当前输入内容属于按推导式生成结果：{item.code for item in findings}；不满足就终止当前测试或流程。
```

#### `test_sdk_patch_version_is_not_part_of_surface_hash`

- **源码**：`tests/test_mcp_contract_evaluator.py:59`
- **签名**：`async def test_sdk_patch_version_is_not_part_of_surface_hash(tmp_path) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
等待异步处理完成，并把结果记为 多个解包结果；断言MCP 能力表面的 SHA-256等于MCP 能力表面的 SHA-256；不满足就终止当前测试或流程；断言当前输入内容不属于辅助操作“复制、序列化或校验结构化领域对象”的结果；不满足就终止当前测试或流程。
```

### `tests/test_mcp_contract_golden.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `anyio_backend`

- **源码**：`tests/test_mcp_contract_golden.py:15`
- **签名**：`def anyio_backend() -> str`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
返回固定值 `'asyncio'`。
```

#### `test_committed_mcp_surface_matches_golden`

- **源码**：`tests/test_mcp_contract_golden.py:19`
- **签名**：`async def test_committed_mcp_surface_matches_golden(tmp_path) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
读取前一步操作返回对象的当前处理结果中的对应字段，并保存为 受控扫描根目录；调用 `load_baseline` 读取或查询当前阶段需要的数据，并把结果记为 已审核的 MCP 能力基线；等待异步处理完成，并把结果记为 MCP Client 观测结果集合。
遍历由MCP Client 观测结果集合组成的集合或迭代器，每次把当前项记为MCP Client 单次观测结果，然后断言辅助操作“调用 `compare_observation` 完成该函数的一项辅助处理”的结果等于[]；不满足就终止当前测试或流程。
```

### `tests/test_mcp_contract_profiles.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_write`

- **源码**：`tests/test_mcp_contract_profiles.py:11`
- **签名**：`def _write(path, payload) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收文件或目录路径、结构化请求载荷，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `path` | `未显式标注` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |
| `payload` | `未显式标注` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
将处理结果写入文件或目录路径指定的文件。
```

#### `test_loads_loopback_profiles_without_credentials`

- **源码**：`tests/test_mcp_contract_profiles.py:18`
- **签名**：`def test_loads_loopback_profiles_without_credentials(tmp_path) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合或计算已有值，并保存为 文件或目录路径；调用 `_write` 完成该函数的一项辅助处理；调用 `load_client_profiles` 读取或查询当前阶段需要的数据，并把结果记为 MCP Client 配置档案集合；断言当前输入内容等于['in-memory-modern', 'loopback-http']；不满足就终止当前测试或流程。
将结构化内容序列化或编码为可传输表示，并把结果记为 该调用返回的结果；断言当前输入内容不属于当前处理结果；不满足就终止当前测试或流程。
```

#### `test_rejects_raw_credential_fields`

- **源码**：`tests/test_mcp_contract_profiles.py:57`
- **签名**：`def test_rejects_raw_credential_fields(tmp_path, raw_key: str) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径、键，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `raw_key` | `str` | 名为 `raw_key` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合或计算已有值，并保存为 文件或目录路径；调用 `_write` 完成该函数的一项辅助处理。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `load_client_profiles` 读取或查询当前阶段需要的数据，退出时自动清理资源。
```

#### `test_rejects_remote_or_dns_endpoint`

- **源码**：`tests/test_mcp_contract_profiles.py:83`
- **签名**：`def test_rejects_remote_or_dns_endpoint(tmp_path) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合或计算已有值，并保存为 文件或目录路径；调用 `_write` 完成该函数的一项辅助处理。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `load_client_profiles` 读取或查询当前阶段需要的数据，退出时自动清理资源。
```

### `tests/test_mcp_contract_readiness.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `anyio_backend`

- **源码**：`tests/test_mcp_contract_readiness.py:18`
- **签名**：`def anyio_backend() -> str`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
返回固定值 `'asyncio'`。
```

#### `_prepare_contract_files`

- **源码**：`tests/test_mcp_contract_readiness.py:22`
- **签名**：`async def _prepare_contract_files(tmp_path)`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
等待异步处理完成，并把结果记为 MCP Client 观测结果集合；调用 `build_candidate` 组装当前阶段需要的领域对象，并把结果记为 待审核的 MCP 能力候选；计算组合或计算已有值，并保存为 MCP 基线文件路径；调用 `promote_candidate` 完成该函数的一项辅助处理。
计算组合或计算已有值，并保存为 MCP Client 配置档案的路径；将处理结果写入MCP Client 配置档案的路径指定的文件；返回当前构造的顺序或去重集合。
```

#### `test_stack_ready_with_valid_contracts_and_disabled_features`

- **源码**：`tests/test_mcp_contract_readiness.py:54`
- **签名**：`async def test_stack_ready_with_valid_contracts_and_disabled_features(tmp_path: 未显式标注, monkeypatch: 未显式标注) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径、测试环境修改工具，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `monkeypatch` | `未显式标注` | pytest 提供的环境/对象替换工具，用于隔离测试副作用；不是业务输入。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
等待异步处理完成，并把结果记为 多个解包结果；调用 `setattr` 完成该函数的一项辅助处理；调用 `setattr` 完成该函数的一项辅助处理；调用 `setattr` 完成该函数的一项辅助处理。
调用 `setattr` 完成该函数的一项辅助处理；调用 `setattr` 完成该函数的一项辅助处理；调用 `setattr` 完成该函数的一项辅助处理；调用 `inspect_mcp_stack` 完成该函数的一项辅助处理，并把结果记为 MCP 评测或运行报告。
断言当前状态等于'ready'；不满足就终止当前测试或流程；遍历并筛选输入，将整理后的结果保存为 当前处理结果；断言当前处理结果中的对应字段等于'ready'；不满足就终止当前测试或流程；断言当前处理结果中的对应字段等于'ready'；不满足就终止当前测试或流程。
断言当前处理结果中的对应字段等于'disabled'；不满足就终止当前测试或流程；断言当前处理结果中的对应字段等于'disabled'；不满足就终止当前测试或流程；断言当前处理结果中的对应字段等于'ready'；不满足就终止当前测试或流程。
```

#### `test_missing_baseline_is_not_ready`

- **源码**：`tests/test_mcp_contract_readiness.py:91`
- **签名**：`async def test_missing_baseline_is_not_ready(tmp_path: 未显式标注, monkeypatch: 未显式标注) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径、测试环境修改工具，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `monkeypatch` | `未显式标注` | pytest 提供的环境/对象替换工具，用于隔离测试副作用；不是业务输入。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
等待异步处理完成，并把结果记为 多个解包结果；调用 `setattr` 完成该函数的一项辅助处理；调用 `setattr` 完成该函数的一项辅助处理；调用 `setattr` 完成该函数的一项辅助处理。
调用 `setattr` 完成该函数的一项辅助处理；调用 `setattr` 完成该函数的一项辅助处理；调用 `setattr` 完成该函数的一项辅助处理；调用 `inspect_mcp_stack` 完成该函数的一项辅助处理，并把结果记为 MCP 评测或运行报告。
断言当前状态等于'not_ready'；不满足就终止当前测试或流程。
```

#### `test_runtime_component_requires_release_report`

- **源码**：`tests/test_mcp_contract_readiness.py:122`
- **签名**：`async def test_runtime_component_requires_release_report(tmp_path: 未显式标注, monkeypatch: 未显式标注) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径、测试环境修改工具，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `monkeypatch` | `未显式标注` | pytest 提供的环境/对象替换工具，用于隔离测试副作用；不是业务输入。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合或计算已有值，并保存为 安全策略的路径；创建父级目录或父领域对象对应的目录；将处理结果写入安全策略的路径指定的文件；计算组合或计算已有值，并保存为 根目录。
创建根目录对应的目录；调用 `setattr` 完成该函数的一项辅助处理；调用 `setattr` 完成该函数的一项辅助处理；调用 `setattr` 完成该函数的一项辅助处理。
调用 `setattr` 完成该函数的一项辅助处理；加载这一步需要的外部依赖；调用 `_runtime_component` 完成该函数的一项辅助处理，并把结果记为 系统组件；断言当前状态等于'not_ready'；不满足就终止当前测试或流程。
断言诊断问题集合等于['runtime_release_report_missing']；不满足就终止当前测试或流程。
```

### `tests/test_mcp_contract_schemas.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_in_memory_profile_rejects_endpoint`

- **源码**：`tests/test_mcp_contract_schemas.py:9`
- **签名**：`def test_in_memory_profile_rejects_endpoint() -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中构造 `McpClientProfile` 结构化领域对象，退出时自动清理资源。
```

#### `test_http_profile_requires_secret_name`

- **源码**：`tests/test_mcp_contract_schemas.py:19`
- **签名**：`def test_http_profile_requires_secret_name() -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中构造 `McpClientProfile` 结构化领域对象，退出时自动清理资源。
```

#### `test_profile_has_no_raw_token_field`

- **源码**：`tests/test_mcp_contract_schemas.py:29`
- **签名**：`def test_profile_has_no_raw_token_field() -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造临时集合、映射或轻量领域对象，并把结果记为 结构化对象字段集合；断言当前输入内容不属于结构化对象字段集合；不满足就终止当前测试或流程；断言当前输入内容不属于结构化对象字段集合；不满足就终止当前测试或流程；断言当前输入内容不属于结构化对象字段集合；不满足就终止当前测试或流程。
```

### `tests/test_mcp_contract_snapshot.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `anyio_backend`

- **源码**：`tests/test_mcp_contract_snapshot.py:12`
- **签名**：`def anyio_backend() -> str`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
返回固定值 `'asyncio'`。
```

#### `test_modern_and_legacy_observe_same_public_surface`

- **源码**：`tests/test_mcp_contract_snapshot.py:16`
- **签名**：`async def test_modern_and_legacy_observe_same_public_surface(tmp_path) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
等待异步处理完成，并把结果记为 多个解包结果；断言MCP 能力表面的 SHA-256等于MCP 能力表面的 SHA-256；不满足就终止当前测试或流程；断言MCP 协议版本有值或为真；不满足就终止当前测试或流程；断言MCP 协议版本有值或为真；不满足就终止当前测试或流程。
断言当前处理结果等于2；不满足就终止当前测试或流程；断言当前处理结果等于2；不满足就终止当前测试或流程。
```

#### `test_snapshot_contains_exact_read_only_catalog`

- **源码**：`tests/test_mcp_contract_snapshot.py:26`
- **签名**：`async def test_snapshot_contains_exact_read_only_catalog(tmp_path) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
等待异步处理完成，并把结果记为 多个解包结果；读取MCP 公开能力表面，并保存为 MCP 公开能力表面；断言当前输入内容等于['get_reproduction_status', 'list_reproduction_artifacts', 'read_reproduction_final_report', 'search_reproduction_evidence']；不满足就终止当前测试或流程。
断言当前输入内容等于['repro://jobs/{job_id}/final-report', 'repro://jobs/{job_id}/status']；不满足就终止当前测试或流程；断言资源集合等于[]；不满足就终止当前测试或流程；断言当前处理结果等于[]；不满足就终止当前测试或流程；断言当前可迭代输入中每一项都满足“MCP Tool 输出 Schema不为空”的项；不满足就终止当前测试或流程。
```

#### `test_snapshot_contains_no_authority_parameter`

- **源码**：`tests/test_mcp_contract_snapshot.py:45`
- **签名**：`async def test_snapshot_contains_no_authority_parameter(tmp_path) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
等待异步处理完成，并把结果记为 多个解包结果；调用 `model_dump_json` 完成该函数的一项辅助处理，再对返回文本执行规范化或拆分，并把结果记为 该调用返回的结果。
遍历当前可迭代输入，每次把当前项记为被策略禁止的内容或操作，然后断言被策略禁止的内容或操作不属于当前处理结果；不满足就终止当前测试或流程。
```

### `tests/test_mcp_export_audit.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_record`

- **源码**：`tests/test_mcp_export_audit.py:7`
- **签名**：`def _record(job_id: str) -> McpExportAuditRecord`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收复现任务 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`McpExportAuditRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
构造并返回 `McpExportAuditRecord` 结构化领域对象。
```

#### `test_audit_round_trip_and_delete`

- **源码**：`tests/test_mcp_export_audit.py:23`
- **签名**：`def test_audit_round_trip_and_delete(tmp_path) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合或计算已有值，并保存为 复现任务 ID；构造 `SqliteMcpExportAuditRepository` 结构化领域对象，并把结果记为 持久化仓库；调用 `initialize` 完成该函数的一项辅助处理；调用 `put` 完成该函数的一项辅助处理。
断言辅助操作“调用 `list_for_job` 读取或查询当前阶段需要的数据”的结果等于[辅助操作“调用 `_record` 完成该函数的一项辅助处理”的结果]；不满足就终止当前测试或流程；断言辅助操作“调用 `delete_for_job` 持久化或更新当前领域数据”的结果等于1；不满足就终止当前测试或流程；断言辅助操作“调用 `delete_for_job` 持久化或更新当前领域数据”的结果等于0；不满足就终止当前测试或流程；断言辅助操作“调用 `list_for_job` 读取或查询当前阶段需要的数据”的结果等于[]；不满足就终止当前测试或流程。
```

#### `test_audit_database_does_not_store_raw_payload`

- **源码**：`tests/test_mcp_export_audit.py:37`
- **签名**：`def test_audit_database_does_not_store_raw_payload(tmp_path) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合或计算已有值，并保存为 文件或目录路径；构造 `SqliteMcpExportAuditRepository` 结构化领域对象，并把结果记为 持久化仓库；调用 `initialize` 完成该函数的一项辅助处理；调用 `put` 完成该函数的一项辅助处理。
读取文件或目录路径中的文件内容，并把结果记为 原始内容；断言当前输入内容不属于原始内容；不满足就终止当前测试或流程；断言当前输入内容不属于原始内容；不满足就终止当前测试或流程。
```

### `tests/test_mcp_export_auth.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `anyio_backend`

- **源码**：`tests/test_mcp_export_auth.py:17`
- **签名**：`def anyio_backend() -> str`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
返回固定值 `'asyncio'`。
```

#### `endpoint`

- **源码**：`tests/test_mcp_export_auth.py:21`
- **签名**：`async def endpoint(_request: Request)`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收业务请求，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `_request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
构造并返回 `JSONResponse` 结构化领域对象。
```

#### `build_app`

- **源码**：`tests/test_mcp_export_auth.py:25`
- **签名**：`def build_app()`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
构造 `Starlette` 结构化领域对象，并把结果记为 该调用返回的结果；构造并返回 `LocalBearerAuthMiddleware` 结构化领域对象。
```

#### `test_missing_token_is_rejected`

- **源码**：`tests/test_mcp_export_auth.py:40`
- **签名**：`async def test_missing_token_is_rejected() -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `ASGITransport` 结构化领域对象，并把结果记为 外部资源传输端口。
在异步上下文“构造 `AsyncClient` 结构化领域对象，并把上下文资源交给外部服务客户端”中等待异步处理完成，并把结果记为 结构化响应，退出时自动清理资源。
断言状态等于401；不满足就终止当前测试或流程；断言前一步操作返回对象中的对应字段中的对应字段等于'MCP_EXPORT_UNAUTHORIZED'；不满足就终止当前测试或流程；断言当前输入内容属于当前处理结果中的对应字段；不满足就终止当前测试或流程。
```

#### `test_valid_token_reaches_inner_app`

- **源码**：`tests/test_mcp_export_auth.py:54`
- **签名**：`async def test_valid_token_reaches_inner_app() -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `ASGITransport` 结构化领域对象，并把结果记为 外部资源传输端口。
在异步上下文“构造 `AsyncClient` 结构化领域对象，并把上下文资源交给外部服务客户端”中等待异步处理完成，并把结果记为 结构化响应，退出时自动清理资源。
断言状态等于200；不满足就终止当前测试或流程；断言辅助操作“调用 `json` 完成该函数的一项辅助处理”的结果等于{'ok': 真}；不满足就终止当前测试或流程。
```

#### `test_duplicate_authorization_headers_are_rejected`

- **源码**：`tests/test_mcp_export_auth.py:70`
- **签名**：`async def test_duplicate_authorization_headers_are_rejected() -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `ASGITransport` 结构化领域对象，并把结果记为 外部资源传输端口。
在异步上下文“构造 `AsyncClient` 结构化领域对象，并把上下文资源交给外部服务客户端”中等待异步处理完成，并把结果记为 结构化响应，退出时自动清理资源。
断言状态等于401；不满足就终止当前测试或流程。
```

#### `test_healthz_contains_no_private_state`

- **源码**：`tests/test_mcp_export_auth.py:88`
- **签名**：`async def test_healthz_contains_no_private_state() -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `ASGITransport` 结构化领域对象，并把结果记为 外部资源传输端口。
在异步上下文“构造 `AsyncClient` 结构化领域对象，并把上下文资源交给外部服务客户端”中等待异步处理完成，并把结果记为 结构化响应，退出时自动清理资源。
断言状态等于200；不满足就终止当前测试或流程；断言辅助操作“调用 `json` 完成该函数的一项辅助处理”的结果等于{'ok': 真}；不满足就终止当前测试或流程。
```

### `tests/test_mcp_export_authority.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `imported_modules`

- **源码**：`tests/test_mcp_export_authority.py:22`
- **签名**：`def imported_modules(path: Path) -> set[str]`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收文件或目录路径，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`set[str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
将 Python 源码解析为抽象语法树，并把结果记为 该调用返回的结果；将 Python 模块集合 初始化为空去重集合，用来收集后续结果。
遍历语法树节点集合，每次把当前项记为当前流程节点：
    如果“计算数量、边界或类型判断结果”后得到肯定结果：
        把新的处理结果追加或合并到Python 模块集合。
    否则：
        如果“计算数量、边界或类型判断结果”后得到肯定结果 且 Python 模块有值或为真，就把Python 模块追加或合并到Python 模块集合。
返回Python 模块集合的当前值。
```

#### `test_mcp_export_does_not_import_mutation_or_network_runtime`

- **源码**：`tests/test_mcp_export_authority.py:33`
- **签名**：`def test_mcp_export_does_not_import_mutation_or_network_runtime() -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
将 约束违反项集合 初始化为空列表，用来收集后续结果。
遍历辅助操作产生的可迭代结果（枚举当前处理结果下符合范围的文件系统项），每次把当前项记为文件或目录路径：
    遍历辅助操作产生的可迭代结果（调用 `imported_modules` 完成该函数的一项辅助处理），每次把当前项记为Python 模块：
        如果由当前处理结果组成的集合或迭代器中存在满足“Python 模块等于目录树缩进前缀 或 “检查Python 模块是否满足文本匹配条件”后得到肯定结果”的项，就把新的处理结果追加或合并到约束违反项集合。
断言约束违反项集合等于[]；不满足就终止当前测试或流程。
```

#### `test_service_does_not_use_direct_filesystem_or_process_apis`

- **源码**：`tests/test_mcp_export_authority.py:45`
- **签名**：`def test_service_does_not_use_direct_filesystem_or_process_apis() -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
读取当前输入内容中的文件内容，并把结果记为 数据来源标记。
遍历当前可迭代输入，每次把当前项记为被策略禁止的内容或操作，然后断言被策略禁止的内容或操作不属于数据来源标记；不满足就终止当前测试或流程。
```

#### `test_server_exports_no_mutation_names`

- **源码**：`tests/test_mcp_export_authority.py:60`
- **签名**：`def test_server_exports_no_mutation_names() -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
读取当前输入内容中的文件内容，并把结果记为 数据来源标记。
遍历当前可迭代输入，每次把当前项记为被策略禁止的内容或操作，然后断言当前输入内容不属于数据来源标记；不满足就终止当前测试或流程。
```

### `tests/test_mcp_export_call_executor.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `anyio_backend`

- **源码**：`tests/test_mcp_export_call_executor.py:17`
- **签名**：`def anyio_backend() -> str`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
返回固定值 `'asyncio'`。
```

#### `BrokenTelemetry.span`

- **源码**：`tests/test_mcp_export_call_executor.py:23`
- **签名**：`def span(self, *args, **kwargs)`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收命令行或函数位置参数集合、函数关键字参数映射，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `*args` | `未显式标注` | 额外位置参数序列。 |
| `**kwargs` | `未显式标注` | 额外关键字参数映射。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
拒绝继续处理并抛出 `RuntimeError`，向调用方报告输入或运行失败。
```

#### `BrokenTelemetry.counter`

- **源码**：`tests/test_mcp_export_call_executor.py:26`
- **签名**：`def counter(self, *args, **kwargs)`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收命令行或函数位置参数集合、函数关键字参数映射，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `*args` | `未显式标注` | 额外位置参数序列。 |
| `**kwargs` | `未显式标注` | 额外关键字参数映射。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
拒绝继续处理并抛出 `RuntimeError`，向调用方报告输入或运行失败。
```

#### `BrokenTelemetry.histogram`

- **源码**：`tests/test_mcp_export_call_executor.py:29`
- **签名**：`def histogram(self, *args, **kwargs)`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收命令行或函数位置参数集合、函数关键字参数映射，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `*args` | `未显式标注` | 额外位置参数序列。 |
| `**kwargs` | `未显式标注` | 额外关键字参数映射。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
拒绝继续处理并抛出 `RuntimeError`，向调用方报告输入或运行失败。
```

#### `BrokenTelemetry.gauge`

- **源码**：`tests/test_mcp_export_call_executor.py:32`
- **签名**：`def gauge(self, *args, **kwargs)`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收命令行或函数位置参数集合、函数关键字参数映射，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `*args` | `未显式标注` | 额外位置参数序列。 |
| `**kwargs` | `未显式标注` | 额外关键字参数映射。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
拒绝继续处理并抛出 `RuntimeError`，向调用方报告输入或运行失败。
```

#### `test_executor_returns_sync_result`

- **源码**：`tests/test_mcp_export_call_executor.py:37`
- **签名**：`async def test_executor_returns_sync_result() -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `McpExportCallExecutor` 结构化领域对象，并把结果记为 该调用返回的结果。
先尝试完成以下处理：
    等待异步处理完成，并把结果记为 阶段处理结果。
无论成功还是失败，最后都要：
    关闭当前处理结果并释放相关资源。
断言阶段处理结果等于3；不满足就终止当前测试或流程。
```

#### `test_telemetry_failure_does_not_change_business_result`

- **源码**：`tests/test_mcp_export_call_executor.py:58`
- **签名**：`async def test_telemetry_failure_does_not_change_business_result() -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `McpExportCallExecutor` 结构化领域对象，并把结果记为 该调用返回的结果。
先尝试完成以下处理：
    等待异步处理完成，并把结果记为 阶段处理结果。
无论成功还是失败，最后都要：
    关闭当前处理结果并释放相关资源。
断言阶段处理结果等于'business-ok'；不满足就终止当前测试或流程。
```

#### `test_timeout_keeps_slot_until_real_thread_finishes`

- **源码**：`tests/test_mcp_export_call_executor.py:78`
- **签名**：`async def test_timeout_keeps_slot_until_real_thread_finishes() -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `Event` 结构化领域对象，并把结果记为 该调用返回的结果；构造 `Event` 结构化领域对象，并把结果记为 运行是否已经启动的判断。
定义内部辅助函数 `block`，供当前函数在后续步骤中调用。
构造 `McpExportCallExecutor` 结构化领域对象，并把结果记为 该调用返回的结果。
先尝试完成以下处理：
    在上下文“调用 `raises` 完成该函数的一项辅助处理”中等待异步处理完成，并提交它产生的状态变更，退出时自动清理资源。
    断言“调用 `is_set` 校验当前输入或状态”后得到肯定结果；不满足就终止当前测试或流程。
    在上下文“调用 `raises` 完成该函数的一项辅助处理”中等待异步处理完成，并提交它产生的状态变更，退出时自动清理资源。
    构造临时集合、映射或轻量领域对象；计算使用固定配置或常量值，并保存为 阶段处理结果。
    遍历限定范围内的序列，每次把当前项记为当前处理结果：
        等待异步处理完成，并提交它产生的状态变更。
        先尝试完成以下处理：
            等待异步处理完成，并把结果记为 阶段处理结果；立即结束当前循环。
        如果出现 `McpExportBusy`：
            跳过本轮剩余处理，直接进入下一轮。
    断言阶段处理结果等于'ok'；不满足就终止当前测试或流程。
无论成功还是失败，最后都要：
    构造临时集合、映射或轻量领域对象；关闭当前处理结果并释放相关资源。
```

#### `test_timeout_keeps_slot_until_real_thread_finishes.block`

- **源码**：`tests/test_mcp_export_call_executor.py:82`
- **签名**：`def block() -> str`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
构造临时集合、映射或轻量领域对象；调用 `wait` 完成该函数的一项辅助处理；返回固定值 `'released'`。
```

#### `test_closed_executor_rejects_new_work`

- **源码**：`tests/test_mcp_export_call_executor.py:133`
- **签名**：`async def test_closed_executor_rejects_new_work() -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `McpExportCallExecutor` 结构化领域对象，并把结果记为 该调用返回的结果；关闭当前处理结果并释放相关资源。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中等待异步处理完成，并提交它产生的状态变更，退出时自动清理资源。
```

### `tests/test_mcp_export_rate_limit.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_rate_limiter_uses_sliding_window`

- **源码**：`tests/test_mcp_export_rate_limit.py:9`
- **签名**：`def test_rate_limiter_uses_sliding_window() -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算初始化顺序集合，并保存为 当前时间；构造 `InMemoryMcpExportRateLimiter` 结构化领域对象，并把结果记为 该调用返回的结果；调用 `acquire` 完成该函数的一项辅助处理；调用 `acquire` 完成该函数的一项辅助处理。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `acquire` 完成该函数的一项辅助处理，退出时自动清理资源。
计算使用固定配置或常量值，并保存为 当前时间中的对应字段；调用 `acquire` 完成该函数的一项辅助处理。
```

### `tests/test_mcp_export_retention.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_export_audit_satisfies_retention_port`

- **源码**：`tests/test_mcp_export_retention.py:7`
- **签名**：`def test_export_audit_satisfies_retention_port(tmp_path) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合或计算已有值，并保存为 复现任务 ID；构造 `SqliteMcpExportAuditRepository` 结构化领域对象，并把结果记为 持久化仓库；调用 `initialize` 完成该函数的一项辅助处理；调用 `put` 完成该函数的一项辅助处理。
断言辅助操作“调用 `delete_for_job` 持久化或更新当前领域数据”的结果等于1；不满足就终止当前测试或流程；断言辅助操作“调用 `list_for_job` 读取或查询当前阶段需要的数据”的结果等于[]；不满足就终止当前测试或流程。
```

### `tests/test_mcp_export_schemas.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_validate_job_id_accepts_only_generated_identity`

- **源码**：`tests/test_mcp_export_schemas.py:16`
- **签名**：`def test_validate_job_id_accepts_only_generated_identity() -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合或计算已有值，并保存为 输入或结果是否有效的判断；断言辅助操作“调用 `validate_job_id` 校验当前输入或状态”的结果等于输入或结果是否有效的判断；不满足就终止当前测试或流程。
遍历当前可迭代输入，每次把当前项记为当前处理结果：
    在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `validate_job_id` 校验当前输入或状态，退出时自动清理资源。
```

#### `test_normalize_query_rejects_control_characters`

- **源码**：`tests/test_mcp_export_schemas.py:30`
- **签名**：`def test_normalize_query_rejects_control_characters() -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
断言辅助操作“调用 `normalize_query` 解析、规范化或转换当前输入”的结果等于'failure reason'；不满足就终止当前测试或流程。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `normalize_query` 解析、规范化或转换当前输入，退出时自动清理资源。
```

#### `test_artifact_projection_rejects_path_like_display_name`

- **源码**：`tests/test_mcp_export_schemas.py:36`
- **签名**：`def test_artifact_projection_rejects_path_like_display_name() -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中构造 `McpExportArtifact` 结构化领域对象，退出时自动清理资源。
```

#### `test_success_audit_requires_output_hash`

- **源码**：`tests/test_mcp_export_schemas.py:52`
- **签名**：`def test_success_audit_requires_output_hash() -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中构造 `McpExportAuditRecord` 结构化领域对象，退出时自动清理资源。
```

### `tests/test_mcp_export_server.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `anyio_backend`

- **源码**：`tests/test_mcp_export_server.py:13`
- **签名**：`def anyio_backend() -> str`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
返回固定值 `'asyncio'`。
```

#### `test_server_lists_exactly_four_read_only_tools`

- **源码**：`tests/test_mcp_export_server.py:17`
- **签名**：`async def test_server_lists_exactly_four_read_only_tools(tmp_path) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
加载这一步需要的外部依赖；调用 `build_test_service` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果；调用 `build_mcp_export_server` 组装当前阶段需要的领域对象，并把结果记为 MCP 服务端实例。
在异步上下文“构造 `Client` 结构化领域对象，并把上下文资源交给外部服务客户端”中等待异步处理完成，并把结果记为 当前处理结果，退出时自动清理资源。
遍历并筛选输入，将整理后的结果保存为 当前处理结果；断言当前处理结果等于{'get_reproduction_status', 'list_reproduction_artifacts', 'read_reproduction_final_report', 'search_reproduction_evidence'}；不满足就终止当前测试或流程；断言“调用 `intersection` 完成该函数的一项辅助处理”后未得到肯定结果；不满足就终止当前测试或流程。
```

#### `test_status_tool_returns_structured_content`

- **源码**：`tests/test_mcp_export_server.py:48`
- **签名**：`async def test_status_tool_returns_structured_content(tmp_path) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
加载这一步需要的外部依赖；调用 `build_test_service` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果；调用 `build_mcp_export_server` 组装当前阶段需要的领域对象，并把结果记为 MCP 服务端实例。
在异步上下文“构造 `Client` 结构化领域对象，并把上下文资源交给外部服务客户端”中等待异步处理完成，并把结果记为 阶段处理结果，退出时自动清理资源。
断言是否错误信息不是真；不满足就终止当前测试或流程；断言内容中的对应字段等于复现任务 ID；不满足就终止当前测试或流程；断言当前输入内容不属于内容；不满足就终止当前测试或流程。
```

#### `test_tool_schema_has_no_path_or_authority_fields`

- **源码**：`tests/test_mcp_export_server.py:70`
- **签名**：`async def test_tool_schema_has_no_path_or_authority_fields(tmp_path) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
加载这一步需要的外部依赖；调用 `build_test_service` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果；调用 `build_mcp_export_server` 组装当前阶段需要的领域对象，并把结果记为 MCP 服务端实例。
在异步上下文“构造 `Client` 结构化领域对象，并把上下文资源交给外部服务客户端”中等待异步处理完成，并把结果记为 当前处理结果，退出时自动清理资源。
调用 `str` 完成该函数的一项辅助处理，再对返回文本执行规范化或拆分，并把结果记为 该调用返回的结果。
遍历当前可迭代输入，每次把当前项记为被策略禁止的内容或操作，然后断言被策略禁止的内容或操作不属于当前处理结果；不满足就终止当前测试或流程。
```

#### `test_resource_templates_are_fixed`

- **源码**：`tests/test_mcp_export_server.py:98`
- **签名**：`async def test_resource_templates_are_fixed(tmp_path) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
加载这一步需要的外部依赖；调用 `build_test_service` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果；调用 `build_mcp_export_server` 组装当前阶段需要的领域对象，并把结果记为 MCP 服务端实例。
在异步上下文“构造 `Client` 结构化领域对象，并把上下文资源交给外部服务客户端”中等待异步处理完成，并把结果记为 当前处理结果，退出时自动清理资源。
遍历并筛选输入，将整理后的结果保存为 当前处理结果；断言当前处理结果等于{'repro://jobs/{job_id}/status', 'repro://jobs/{job_id}/final-report'}；不满足就终止当前测试或流程。
```

#### `test_export_surface_supports_approved_client_modes`

- **源码**：`tests/test_mcp_export_server.py:125`
- **签名**：`async def test_export_surface_supports_approved_client_modes(tmp_path: 未显式标注, profile_id: str, mode: str) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径、MCP Client 配置档案 ID、MCP 评测或运行模式，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `profile_id` | `str` | MCP Client 配置档案 ID；用于区分连接地址、协议版本和能力基线。 |
| `mode` | `str` | MCP 评测或运行模式；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
加载这一步需要的外部依赖；加载这一步需要的外部依赖；加载这一步需要的外部依赖；调用 `build_test_service` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果。
调用 `build_mcp_export_server` 组装当前阶段需要的领域对象，并把结果记为 MCP 服务端实例；等待异步处理完成，并把结果记为 MCP Client 单次观测结果；断言MCP 能力表面的 SHA-256有值或为真；不满足就终止当前测试或流程；断言当前处理结果等于2；不满足就终止当前测试或流程。
断言受控工具定义集合 的长度等于4；不满足就终止当前测试或流程。
```

#### `test_status_tool_invokes_in_approved_client_modes`

- **源码**：`tests/test_mcp_export_server.py:154`
- **签名**：`async def test_status_tool_invokes_in_approved_client_modes(tmp_path: 未显式标注, mode: str) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径、MCP 评测或运行模式，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `mode` | `str` | MCP 评测或运行模式；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
加载这一步需要的外部依赖；调用 `build_test_service` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果；调用 `build_mcp_export_server` 组装当前阶段需要的领域对象，并把结果记为 MCP 服务端实例。
在异步上下文“构造 `Client` 结构化领域对象，并把上下文资源交给外部服务客户端”中等待异步处理完成，并提交它产生的状态变更；等待异步处理完成，并把结果记为 阶段处理结果，退出时自动清理资源。
断言是否错误信息不是真；不满足就终止当前测试或流程；断言内容不为空；不满足就终止当前测试或流程；断言内容中的对应字段等于复现任务 ID；不满足就终止当前测试或流程。
```

### `tests/test_mcp_export_service.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_status_is_a_narrow_public_projection`

- **源码**：`tests/test_mcp_export_service.py:15`
- **签名**：`def test_status_is_a_narrow_public_projection(tmp_path) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `build_test_service` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果；调用 `get_status` 读取或查询当前阶段需要的数据，并把结果记为 当前状态；复制、序列化或校验结构化领域对象，并把结果记为 结构化请求载荷；断言当前处理结果是真；不满足就终止当前测试或流程。
断言错误等于'TRAINING_FAILED'；不满足就终止当前测试或流程；断言当前输入内容不属于结构化请求载荷；不满足就终止当前测试或流程；断言当前输入内容不属于结构化请求载荷；不满足就终止当前测试或流程；断言当前输入内容不属于结构化请求载荷；不满足就终止当前测试或流程。
断言当前输入内容不属于结构化请求载荷；不满足就终止当前测试或流程；断言辅助操作“调用 `list_for_job` 读取或查询当前阶段需要的数据”的结果 的长度等于1；不满足就终止当前测试或流程。
```

#### `test_artifacts_do_not_export_relative_path`

- **源码**：`tests/test_mcp_export_service.py:33`
- **签名**：`def test_artifacts_do_not_export_relative_path(tmp_path) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `build_test_service` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果；调用 `list_artifacts` 读取或查询当前阶段需要的数据，并把结果记为 论文页码；断言Artifact的 ID等于Artifact的 ID；不满足就终止当前测试或流程；断言当前处理结果的名称等于'final_report.md'；不满足就终止当前测试或流程。
调用 `model_dump_json` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；断言当前输入内容不属于当前处理结果；不满足就终止当前测试或流程；断言当前输入内容不属于当前处理结果；不满足就终止当前测试或流程；断言当前输入内容不属于当前处理结果；不满足就终止当前测试或流程。
```

#### `test_final_report_is_server_selected_and_hash_bound`

- **源码**：`tests/test_mcp_export_service.py:50`
- **签名**：`def test_final_report_is_server_selected_and_hash_bound(tmp_path) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `build_test_service` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果；调用 `read_final_report` 读取或查询当前阶段需要的数据，并把结果记为 MCP 评测或运行报告；断言Artifact的 ID等于Artifact的 ID；不满足就终止当前测试或流程；断言业务内容的 SHA-256等于辅助操作“调用 `sha256_text` 计算内容身份、分数或派生结果”的结果；不满足就终止当前测试或流程。
断言“检查业务内容是否满足文本匹配条件”后得到肯定结果；不满足就终止当前测试或流程；断言凭据值不属于业务内容；不满足就终止当前测试或流程；断言当前输入内容属于业务内容；不满足就终止当前测试或流程。
```

#### `test_missing_final_report_is_a_stable_error`

- **源码**：`tests/test_mcp_export_service.py:65`
- **签名**：`def test_missing_final_report_is_a_stable_error(tmp_path) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `build_test_service` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果；将 Artifact 视图集合 初始化为空列表，用来收集后续结果。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `read_final_report` 读取或查询当前阶段需要的数据，退出时自动清理资源。
调用 `list_for_job` 读取或查询当前阶段需要的数据，并把结果记为 领域记录集合；断言错误等于'MCP_EXPORT_FINAL_REPORT_NOT_FOUND'；不满足就终止当前测试或流程。
```

#### `test_evidence_uses_only_local_source_types`

- **源码**：`tests/test_mcp_export_service.py:79`
- **签名**：`def test_evidence_uses_only_local_source_types(tmp_path) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `build_test_service` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果；调用 `search_evidence` 读取或查询当前阶段需要的数据，并把结果记为 检索或映射证据包；读取工具或模型调用记录集合中的对应字段中的对应字段，并保存为 后续步骤使用的结果；断言当前处理结果中的对应字段等于['job', 'event', 'artifact', 'log']；不满足就终止当前测试或流程。
断言当前输入内容不属于当前处理结果中的对应字段；不满足就终止当前测试或流程；断言当前输入内容不属于当前处理结果中的对应字段；不满足就终止当前测试或流程；断言当前处理结果等于格式化文本：f'artifact:{ARTIFACT_ID}'；不满足就终止当前测试或流程；断言当前输入内容不属于辅助操作“调用 `model_dump_json` 完成该函数的一项辅助处理”的结果；不满足就终止当前测试或流程。
断言凭据值不属于辅助操作“调用 `model_dump_json` 完成该函数的一项辅助处理”的结果；不满足就终止当前测试或流程；断言当前输入内容属于当前处理结果；不满足就终止当前测试或流程。
```

### `tests/test_mcp_gateway_api.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_client`

- **源码**：`tests/test_mcp_gateway_api.py:15`
- **签名**：`def _client(repository: SqliteMcpEvidenceRepository | None, api_token: str | None) -> TestClient`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收持久化仓库、当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `TestClient` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `repository` | `SqliteMcpEvidenceRepository | None` | 持久化或目录访问端口；负责读取、CAS 更新或 Artifact 定位。 |
| `api_token` | `str | None` | 敏感凭证或其引用；不得写入日志、Prompt 或普通 Artifact。；默认 空值 |

**输出**

- **Python 类型**：`TestClient`
- **语义**：返回 `TestClient` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造 `FastAPI` 结构化领域对象，并把结果记为 该调用返回的结果；读取当前处理结果，并保存为 后续步骤使用的结果；读取持久化仓库，并保存为 证据代码仓库；调用 `include_router` 完成该函数的一项辅助处理。
构造并返回 `TestClient` 结构化领域对象。
```

#### `_seed_pack`

- **源码**：`tests/test_mcp_gateway_api.py:27`
- **签名**：`def _seed_pack(repository: SqliteMcpEvidenceRepository)`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收持久化仓库，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `repository` | `SqliteMcpEvidenceRepository` | 持久化或目录访问端口；负责读取、CAS 更新或 Artifact 定位。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
构造 `ReadOnlyMcpEvidenceGateway` 结构化领域对象，并把结果记为 外部服务网关；调用 `search` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `test_disabled_mcp_evidence_returns_404`

- **源码**：`tests/test_mcp_gateway_api.py:40`
- **签名**：`def test_disabled_mcp_evidence_returns_404() -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
从辅助操作“调用 `_client` 完成该函数的一项辅助处理”的结果读取所需的状态或领域记录，并把结果记为 结构化响应；断言状态等于404；不满足就终止当前测试或流程；断言前一步操作返回对象中的对应字段中的对应字段等于'MCP_GATEWAY_DISABLED'；不满足就终止当前测试或流程。
```

#### `test_list_and_get_mcp_pack`

- **源码**：`tests/test_mcp_gateway_api.py:46`
- **签名**：`def test_list_and_get_mcp_pack(tmp_path) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `SqliteMcpEvidenceRepository` 结构化领域对象，并把结果记为 持久化仓库；调用 `initialize` 完成该函数的一项辅助处理；调用 `_seed_pack` 完成该函数的一项辅助处理，并把结果记为 检索或映射证据包；调用 `_client` 完成该函数的一项辅助处理，并把结果记为 外部服务客户端。
从外部服务客户端读取所需的状态或领域记录，并把结果记为 该调用返回的结果；从外部服务客户端读取所需的状态或领域记录，并把结果记为 该调用返回的结果；断言状态等于200；不满足就终止当前测试或流程；断言前一步操作返回对象中的对应字段中的对应字段等于检索或映射证据包的 ID；不满足就终止当前测试或流程。
断言状态等于200；不满足就终止当前测试或流程；断言前一步操作返回对象中的对应字段等于检索或映射证据包的 SHA-256；不满足就终止当前测试或流程。
```

#### `test_mcp_pack_cannot_be_read_through_another_job`

- **源码**：`tests/test_mcp_gateway_api.py:63`
- **签名**：`def test_mcp_pack_cannot_be_read_through_another_job(tmp_path) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `SqliteMcpEvidenceRepository` 结构化领域对象，并把结果记为 持久化仓库；调用 `initialize` 完成该函数的一项辅助处理；调用 `_seed_pack` 完成该函数的一项辅助处理，并把结果记为 检索或映射证据包；从辅助操作“调用 `_client` 完成该函数的一项辅助处理”的结果读取所需的状态或领域记录，并把结果记为 结构化响应。
断言状态等于404；不满足就终止当前测试或流程；断言前一步操作返回对象中的对应字段中的对应字段等于'MCP_EVIDENCE_NOT_FOUND'；不满足就终止当前测试或流程。
```

#### `test_mcp_evidence_api_requires_configured_token`

- **源码**：`tests/test_mcp_gateway_api.py:75`
- **签名**：`def test_mcp_evidence_api_requires_configured_token(tmp_path) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `SqliteMcpEvidenceRepository` 结构化领域对象，并把结果记为 持久化仓库；调用 `initialize` 完成该函数的一项辅助处理；从辅助操作“调用 `_client` 完成该函数的一项辅助处理”的结果读取所需的状态或领域记录，并把结果记为 结构化响应；断言状态等于401；不满足就终止当前测试或流程。
```

#### `test_mcp_api_has_no_generic_call_endpoint`

- **源码**：`tests/test_mcp_gateway_api.py:85`
- **签名**：`def test_mcp_api_has_no_generic_call_endpoint(tmp_path) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `SqliteMcpEvidenceRepository` 结构化领域对象，并把结果记为 持久化仓库；调用 `initialize` 完成该函数的一项辅助处理；调用 `post` 完成该函数的一项辅助处理，并把结果记为 结构化响应；断言状态等于405；不满足就终止当前测试或流程。
```

### `tests/test_mcp_gateway_authority.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_mcp_gateway_only_returns_evidence`

- **源码**：`tests/test_mcp_gateway_authority.py:13`
- **签名**：`def test_mcp_gateway_only_returns_evidence() -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
进入上下文“构造 `TemporaryDirectory` 结构化领域对象，并把上下文资源交给临时”，退出时自动清理资源：
    构造 `SqliteMcpEvidenceRepository` 结构化领域对象，并把结果记为 代码仓库；调用 `initialize` 完成该函数的一项辅助处理；构造 `ReadOnlyMcpEvidenceGateway` 结构化领域对象，并把结果记为 外部服务网关；调用 `search` 完成该函数的一项辅助处理，并把结果记为 检索或映射证据包。
    断言“调用 `hasattr` 完成该函数的一项辅助处理”后得到肯定结果；不满足就终止当前测试或流程；断言“调用 `hasattr` 完成该函数的一项辅助处理”后未得到肯定结果；不满足就终止当前测试或流程；断言“调用 `hasattr` 完成该函数的一项辅助处理”后未得到肯定结果；不满足就终止当前测试或流程；断言“调用 `hasattr` 完成该函数的一项辅助处理”后未得到肯定结果；不满足就终止当前测试或流程。
```

#### `test_mcp_gateway_does_not_modify_graph_state`

- **源码**：`tests/test_mcp_gateway_authority.py:25`
- **签名**：`def test_mcp_gateway_does_not_modify_graph_state() -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
进入上下文“构造 `TemporaryDirectory` 结构化领域对象，并把上下文资源交给临时”，退出时自动清理资源：
    构造 `SqliteMcpEvidenceRepository` 结构化领域对象，并把结果记为 代码仓库；调用 `initialize` 完成该函数的一项辅助处理；构造 `ReadOnlyMcpEvidenceGateway` 结构化领域对象，并把结果记为 外部服务网关；调用 `search` 完成该函数的一项辅助处理，并把结果记为 检索或映射证据包。
    断言复现任务 ID等于'job_state'；不满足就终止当前测试或流程；断言外部 MCP 服务端稳定标识等于'mcpserver_scholar_local'；不满足就终止当前测试或流程。
```

### `tests/test_mcp_gateway_chat_integration.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_mcp_evidence_enters_final_chat_citation_allowlist`

- **源码**：`tests/test_mcp_gateway_chat_integration.py:25`
- **签名**：`def test_mcp_evidence_enters_final_chat_citation_allowlist(tmp_path) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `SqliteMcpEvidenceRepository` 结构化领域对象，并把结果记为 持久化仓库；调用 `initialize` 完成该函数的一项辅助处理；构造 `ReadOnlyMcpEvidenceGateway` 结构化领域对象，并把结果记为 外部服务网关；构造 `ToolRegistry` 结构化领域对象，并把结果记为 组件注册表。
调用 `register_mcp_evidence_tool` 完成该函数的一项辅助处理；调用 `build_provider_tool_catalog` 组装当前阶段需要的领域对象，并把结果记为 模型、工具或 Artifact 目录；构造 `BoundedToolCallingLoop` 结构化领域对象，并把结果记为 该调用返回的结果；将 期望的 ID 初始化为空列表，用来收集后续结果。
定义内部辅助函数 `draft_invoker`，供当前函数在后续步骤中调用。
调用 `_service` 完成该函数的一项辅助处理，并把结果记为 领域服务对象；调用 `ask` 完成该函数的一项辅助处理，并把结果记为 结构化响应；断言来源类型等于'mcp'；不满足就终止当前测试或流程；断言论文引用证据的 ID等于期望的 ID中的对应字段；不满足就终止当前测试或流程。
断言工具不为空；不满足就终止当前测试或流程；断言MCP Tool 名称等于工具的名称；不满足就终止当前测试或流程。
```

#### `test_mcp_evidence_enters_final_chat_citation_allowlist.draft_invoker`

- **源码**：`tests/test_mcp_gateway_chat_integration.py:65`
- **签名**：`def draft_invoker(prompt: str, job_id: str) -> ChatDraft`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收发给模型的结构化提示、复现任务 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ChatDraft` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `prompt` | `str` | 用户目标、检索问题、反馈或待处理文本；会作为当前阶段的业务语境输入，并可能受到长度/脱敏约束。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`ChatDraft`
- **语义**：返回 `ChatDraft` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
移除复现任务 ID中的当前内容；计算使用固定配置或常量值，并保存为 测试或状态标记；调用 `index` 完成该函数的一项辅助处理，并把结果记为 读取起点；读取发给模型的结构化提示中的对应字段，并保存为 论文引用证据的 ID。
把论文引用证据的 ID追加或合并到期望的 ID；构造并返回 `ChatDraft` 结构化领域对象。
```

### `tests/test_mcp_gateway_client.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_verify_pin_rejects_changed_input_schema`

- **源码**：`tests/test_mcp_gateway_client.py:23`
- **签名**：`def test_verify_pin_rejects_changed_input_schema() -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `SdkMcpClient` 结构化领域对象，并把结果记为 外部服务客户端；调用 `make_binding` 完成该函数的一项辅助处理，并把结果记为 资源绑定记录；构造 `SimpleNamespace` 结构化领域对象，并把结果记为 该调用返回的结果。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `_verify_pin` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `test_observe_does_not_select_dangerous_tool_by_annotation`

- **源码**：`tests/test_mcp_gateway_client.py:42`
- **签名**：`def test_observe_does_not_select_dangerous_tool_by_annotation() -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `SdkMcpClient` 结构化领域对象，并把结果记为 外部服务客户端；调用 `make_binding` 完成该函数的一项辅助处理，并把结果记为 资源绑定记录；调用 `make_profile` 完成该函数的一项辅助处理，并把结果记为 MCP Client 配置档案；构造 `SimpleNamespace` 结构化领域对象，并把结果记为 该调用返回的结果。
构造 `SimpleNamespace` 结构化领域对象，并把结果记为 该调用返回的结果；调用 `_observe_tool` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；断言远程工具的名称等于'search_paper_evidence'；不满足就终止当前测试或流程。
```

### `tests/test_mcp_gateway_gateway.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_search_returns_pack_with_evidence`

- **源码**：`tests/test_mcp_gateway_gateway.py:12`
- **签名**：`def test_search_returns_pack_with_evidence() -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
进入上下文“构造 `TemporaryDirectory` 结构化领域对象，并把上下文资源交给临时”，退出时自动清理资源：
    构造 `SqliteMcpEvidenceRepository` 结构化领域对象，并把结果记为 代码仓库；调用 `initialize` 完成该函数的一项辅助处理；构造 `FakeMcpClient` 结构化领域对象，并把结果记为 外部服务客户端；构造 `ReadOnlyMcpEvidenceGateway` 结构化领域对象，并把结果记为 外部服务网关。
    调用 `search` 完成该函数的一项辅助处理，并把结果记为 检索或映射证据包；断言复现任务 ID等于'job_test'；不满足就终止当前测试或流程；断言外部 MCP 服务端稳定标识等于'mcpserver_scholar_local'；不满足就终止当前测试或流程；断言MCP Tool 绑定 ID等于'mcpbind_scholar_search_v1'；不满足就终止当前测试或流程。
    断言待处理项集合 的长度等于1；不满足就终止当前测试或流程；断言文档或章节标题等于'PSTNet'；不满足就终止当前测试或流程；断言当前处理结果是假；不满足就终止当前测试或流程；断言工具或模型调用记录集合 的长度等于1；不满足就终止当前测试或流程。
    断言工具或模型调用记录集合中的对应字段中的对应字段等于'call'；不满足就终止当前测试或流程。
```

#### `test_search_failure_records_call`

- **源码**：`tests/test_mcp_gateway_gateway.py:29`
- **签名**：`def test_search_failure_records_call() -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
加载这一步需要的外部依赖；加载这一步需要的外部依赖。
进入上下文“构造 `TemporaryDirectory` 结构化领域对象，并把上下文资源交给临时”，退出时自动清理资源：
    构造 `SqliteMcpEvidenceRepository` 结构化领域对象，并把结果记为 代码仓库；调用 `initialize` 完成该函数的一项辅助处理。
    定义内部类型 `FailingClient`，用于组织当前函数的临时逻辑。
    构造 `ReadOnlyMcpEvidenceGateway` 结构化领域对象，并把结果记为 外部服务网关。
    先尝试完成以下处理：
        调用 `search` 完成该函数的一项辅助处理；断言当前条件（使用固定配置或常量值）成立，失败时附带断言说明；不满足就终止当前测试或流程。
    如果出现 `McpRemoteToolFailed`：
        不执行额外操作。
    调用 `list_calls_for_job` 读取或查询当前阶段需要的数据，并把结果记为 工具或模型调用记录集合；断言工具或模型调用记录集合 的长度等于1；不满足就终止当前测试或流程；断言当前状态等于'failed'；不满足就终止当前测试或流程；断言错误等于'MCP_REMOTE_TOOL_FAILED'；不满足就终止当前测试或流程。
```

#### `test_search_failure_records_call.FailingClient.call_pinned_tool`

- **源码**：`tests/test_mcp_gateway_gateway.py:38`
- **签名**：`def call_pinned_tool(self, *, profile, binding, arguments)`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收MCP Client 配置档案、资源绑定记录、结构化调用参数，用于在固定 MCP Policy、Schema Pin、调用预算和只读职责边界内连接或调用外部能力，并把返回内容转换为可追溯的复现证据，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `profile` | `未显式标注` | 运行/执行环境配置或 profile 标识；描述能力和限制，不是一次执行的结果。 |
| `binding` | `未显式标注` | 资源绑定记录；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `arguments` | `未显式标注` | 结构化调用参数；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
拒绝继续处理并抛出 `McpRemoteToolFailed`，向调用方报告输入或运行失败。
```

### `tests/test_mcp_gateway_policy.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_reject_invalid_endpoints`

- **源码**：`tests/test_mcp_gateway_policy.py:10`
- **签名**：`def test_reject_invalid_endpoints(endpoint: str) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收MCP 服务端点地址，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `endpoint` | `str` | MCP 服务端点地址；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `validate_loopback_endpoint` 校验当前输入或状态，退出时自动清理资源。
```

#### `test_accept_valid_loopback_endpoints`

- **源码**：`tests/test_mcp_gateway_policy.py:16`
- **签名**：`def test_accept_valid_loopback_endpoints(endpoint: str) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收MCP 服务端点地址，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `endpoint` | `str` | MCP 服务端点地址；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `validate_loopback_endpoint` 校验当前输入或状态。
```

### `tests/test_mcp_gateway_repository.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_make_pack`

- **源码**：`tests/test_mcp_gateway_repository.py:11`
- **签名**：`def _make_pack(job_id: str = "job_test") -> McpEvidencePack`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收复现任务 ID，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `McpEvidencePack` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。；默认 'job_test' |

**输出**

- **Python 类型**：`McpEvidencePack`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
调用 `build_evidence_item` 组装当前阶段需要的领域对象，并把结果记为 当前处理项；计算按字段初始化键值映射，并保存为 身份；构造 `McpEvidencePack` 结构化领域对象，并把结果记为 草稿对象；复制、序列化或校验结构化领域对象，并返回处理结果。
```

#### `_make_call_record`

- **源码**：`tests/test_mcp_gateway_repository.py:18`
- **签名**：`def _make_call_record(pack: McpEvidencePack, status: str = "succeeded") -> McpCallRecord`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收检索或映射证据包、当前状态，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `pack` | `McpEvidencePack` | 检索或映射证据包；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `status` | `str` | 来源、类别、用途、后端、状态或操作原因等控制字段；通常对应有限的业务枚举或审计文本。；默认 'succeeded' |

**输出**

- **Python 类型**：`McpCallRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
构造并返回 `McpCallRecord` 结构化领域对象。
```

#### `test_put_and_get_success`

- **源码**：`tests/test_mcp_gateway_repository.py:22`
- **签名**：`def test_put_and_get_success() -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
进入上下文“构造 `TemporaryDirectory` 结构化领域对象，并把上下文资源交给临时”，退出时自动清理资源：
    构造 `SqliteMcpEvidenceRepository` 结构化领域对象，并把结果记为 代码仓库；调用 `initialize` 完成该函数的一项辅助处理；调用 `_make_pack` 完成该函数的一项辅助处理，并把结果记为 检索或映射证据包；调用 `_make_call_record` 完成该函数的一项辅助处理，并把结果记为 领域记录。
    调用 `put_success` 持久化或更新当前领域数据；调用 `get_pack` 读取或查询当前阶段需要的数据，并把结果记为 该调用返回的结果；断言检索或映射证据包的 ID等于检索或映射证据包的 ID；不满足就终止当前测试或流程；断言文档或章节标题等于'PSTNet'；不满足就终止当前测试或流程。
    调用 `list_packs_for_job` 读取或查询当前阶段需要的数据，并把结果记为 该调用返回的结果；断言当前处理结果 的长度等于1；不满足就终止当前测试或流程；调用 `list_calls_for_job` 读取或查询当前阶段需要的数据，并把结果记为 工具或模型调用记录集合；断言工具或模型调用记录集合 的长度等于1；不满足就终止当前测试或流程。
    断言当前状态等于'succeeded'；不满足就终止当前测试或流程。
```

#### `test_put_failure`

- **源码**：`tests/test_mcp_gateway_repository.py:39`
- **签名**：`def test_put_failure() -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
进入上下文“构造 `TemporaryDirectory` 结构化领域对象，并把上下文资源交给临时”，退出时自动清理资源：
    构造 `SqliteMcpEvidenceRepository` 结构化领域对象，并把结果记为 代码仓库；调用 `initialize` 完成该函数的一项辅助处理；调用 `_make_pack` 完成该函数的一项辅助处理，并把结果记为 检索或映射证据包；调用 `_make_call_record` 完成该函数的一项辅助处理，并把结果记为 领域记录。
    调用 `put_failure` 持久化或更新当前领域数据；调用 `list_calls_for_job` 读取或查询当前阶段需要的数据，并把结果记为 工具或模型调用记录集合；断言工具或模型调用记录集合 的长度等于1；不满足就终止当前测试或流程；断言当前状态等于'failed'；不满足就终止当前测试或流程。
```

#### `test_delete_for_job`

- **源码**：`tests/test_mcp_gateway_repository.py:51`
- **签名**：`def test_delete_for_job() -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
进入上下文“构造 `TemporaryDirectory` 结构化领域对象，并把上下文资源交给临时”，退出时自动清理资源：
    构造 `SqliteMcpEvidenceRepository` 结构化领域对象，并把结果记为 代码仓库；调用 `initialize` 完成该函数的一项辅助处理；调用 `_make_pack` 完成该函数的一项辅助处理，并把结果记为 检索或映射证据包；调用 `_make_call_record` 完成该函数的一项辅助处理，并把结果记为 领域记录。
    调用 `put_success` 持久化或更新当前领域数据；调用 `delete_for_job` 持久化或更新当前领域数据，并把结果记为 对象数量；断言对象数量等于2；不满足就终止当前测试或流程；断言辅助操作“调用 `list_packs_for_job` 读取或查询当前阶段需要的数据”的结果等于[]；不满足就终止当前测试或流程。
```

### `tests/test_mcp_gateway_schemas.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_policy_has_one_enabled_static_alias`

- **源码**：`tests/test_mcp_gateway_schemas.py:10`
- **签名**：`def test_policy_has_one_enabled_static_alias() -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `make_policy` 完成该函数的一项辅助处理，并把结果记为 安全策略；调用 `enabled_binding` 完成该函数的一项辅助处理，并把结果记为 选中的候选项；断言选中的候选项不为空；不满足就终止当前测试或流程；读取选中的候选项，并保存为 多个解包结果。
断言外部 MCP 服务端稳定标识等于'mcpserver_scholar_local'；不满足就终止当前测试或流程；断言远程工具的名称等于'search_paper_evidence'；不满足就终止当前测试或流程。
```

#### `test_search_input_rejects_empty_short_or_control_query`

- **源码**：`tests/test_mcp_gateway_schemas.py:20`
- **签名**：`def test_search_input_rejects_empty_short_or_control_query(query: str) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收语义检索问题，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `query` | `str` | 用户目标、检索问题、反馈或待处理文本；会作为当前阶段的业务语境输入，并可能受到长度/脱敏约束。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中构造 `McpSearchInput` 结构化领域对象，退出时自动清理资源。
```

#### `test_search_input_does_not_accept_endpoint_or_tool_name`

- **源码**：`tests/test_mcp_gateway_schemas.py:25`
- **签名**：`def test_search_input_does_not_accept_endpoint_or_tool_name() -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中复制、序列化或校验结构化领域对象，退出时自动清理资源。
```

### `tests/test_mcp_gateway_tool_integration.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_registry`

- **源码**：`tests/test_mcp_gateway_tool_integration.py:18`
- **签名**：`def _registry(tmp_path) -> ToolRegistry`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ToolRegistry` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`ToolRegistry`
- **语义**：返回 `ToolRegistry` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造 `SqliteMcpEvidenceRepository` 结构化领域对象，并把结果记为 持久化仓库；调用 `initialize` 完成该函数的一项辅助处理；构造 `ReadOnlyMcpEvidenceGateway` 结构化领域对象，并把结果记为 外部服务网关；构造 `ToolRegistry` 结构化领域对象，并把结果记为 组件注册表。
调用 `register_mcp_evidence_tool` 完成该函数的一项辅助处理；返回组件注册表的当前值。
```

#### `test_mcp_tool_requires_explicit_capability`

- **源码**：`tests/test_mcp_gateway_tool_integration.py:31`
- **签名**：`def test_mcp_tool_requires_explicit_capability(tmp_path) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_registry` 完成该函数的一项辅助处理，并把结果记为 组件注册表；调用组件注册表完成模型或 Runnable 处理，并把结果记为 阶段处理结果；断言失败不为空；不满足就终止当前测试或流程；断言待解析或验证的代码等于'TOOL_CAPABILITY_DENIED'；不满足就终止当前测试或流程。
```

#### `test_mcp_tool_returns_mcp_citation_when_capability_granted`

- **源码**：`tests/test_mcp_gateway_tool_integration.py:48`
- **签名**：`def test_mcp_tool_returns_mcp_citation_when_capability_granted(tmp_path: 未显式标注) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_registry` 完成该函数的一项辅助处理，并把结果记为 组件注册表；调用组件注册表完成模型或 Runnable 处理，并把结果记为 阶段处理结果；断言失败为空；不满足就终止当前测试或流程；断言输出结果不为空；不满足就终止当前测试或流程。
读取输出结果中的对应字段中的对应字段中的对应字段，并保存为 论文引用证据；断言论文引用证据中的对应字段等于'mcp'；不满足就终止当前测试或流程；断言“检查论文引用证据中的对应字段是否满足文本匹配条件”后得到肯定结果；不满足就终止当前测试或流程。
```

### `tests/test_mcp_runtime_authority.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_runtime_registry_contains_only_six_read_only_operations`

- **源码**：`tests/test_mcp_runtime_authority.py:7`
- **签名**：`def test_runtime_registry_contains_only_six_read_only_operations() -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
断言当前处理结果等于{'get_reproduction_status', 'list_reproduction_artifacts', 'read_reproduction_final_report', 'search_reproduction_evidence', 'resource_job_status', 'resource_final_report'}；不满足就终止当前测试或流程；计算初始化去重集合，并保存为 被策略禁止的内容或操作。
断言“检查由当前处理结果组成的集合或迭代器中是否存在满足“当前处理结果属于MCP 业务操作名称”的项”后未得到肯定结果；不满足就终止当前测试或流程。
```

#### `test_sample_schema_cannot_store_raw_request_or_response`

- **源码**：`tests/test_mcp_runtime_authority.py:34`
- **签名**：`def test_sample_schema_cannot_store_raw_request_or_response() -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造临时集合、映射或轻量领域对象，并把结果记为 结构化对象字段集合；断言“调用 `intersection` 完成该函数的一项辅助处理”后未得到肯定结果；不满足就终止当前测试或流程；断言“调用 `issubset` 完成该函数的一项辅助处理”后得到肯定结果；不满足就终止当前测试或流程。
```

### `tests/test_mcp_runtime_http.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `anyio_backend`

- **源码**：`tests/test_mcp_runtime_http.py:24`
- **签名**：`def anyio_backend() -> str`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
返回固定值 `'asyncio'`。
```

#### `_unused_loopback_port`

- **源码**：`tests/test_mcp_runtime_http.py:28`
- **签名**：`def _unused_loopback_port() -> int`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终数量、序号、字节数或版本等整数结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`int`
- **语义**：返回整数计数、序号、字节数或退出码；具体含义由函数名决定。

**伪代码**

```text
在上下文“调用 `closing` 完成该函数的一项辅助处理，并把上下文资源交给当前处理结果”中调用 `bind` 完成该函数的一项辅助处理；调用 `int` 完成该函数的一项辅助处理，并返回处理结果，退出时自动清理资源。
```

#### `_wait_until_started`

- **源码**：`tests/test_mcp_runtime_http.py:34`
- **签名**：`async def _wait_until_started(server: uvicorn.Server) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收MCP 服务端实例，用于驱动或监督一次论文复现运行，记录命令、工作目录、资源使用、状态迁移和失败原因，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `server` | `uvicorn.Server` | MCP 服务端实例；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
遍历限定范围内的序列，每次把当前项记为当前处理结果：
    如果运行是否已经启动的判断有值或为真，就结束当前函数，不返回业务值。
    等待异步处理完成，并提交它产生的状态变更。
拒绝继续处理并抛出 `AssertionError`，向调用方报告输入或运行失败。
```

#### `test_real_http_invokes_four_tools_and_two_resources`

- **源码**：`tests/test_mcp_runtime_http.py:43`
- **签名**：`async def test_real_http_invokes_four_tools_and_two_resources(tmp_path: 未显式标注) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `build_test_service` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果；构造 `McpExportRuntime` 结构化领域对象，并把结果记为 运行时环境；调用 `build_mcp_export_asgi_bundle` 组装当前阶段需要的领域对象，并把结果记为 代码仓库归档包；调用 `_unused_loopback_port` 完成该函数的一项辅助处理，并把结果记为 服务监听端口。
构造 `Server` 结构化领域对象，并把结果记为 MCP 服务端实例；构造 `Thread` 结构化领域对象，并把结果记为 该调用返回的结果；调用 `start` 完成该函数的一项辅助处理。
先尝试完成以下处理：
    等待异步处理完成，并提交它产生的状态变更。
    进入异步上下文“构造 `AsyncClient` 结构化领域对象，并把上下文资源交给当前处理结果”，退出时自动清理资源：
        调用 `streamable_http_client` 完成该函数的一项辅助处理，并把结果记为 外部资源传输端口。
        进入异步上下文“构造 `Client` 结构化领域对象，并把上下文资源交给外部服务客户端”，退出时自动清理资源：
            等待异步处理完成，并把结果记为 当前处理结果；断言受控工具定义集合 的长度等于4；不满足就终止当前测试或流程；计算初始化顺序集合，并保存为 工具集合。
            遍历由工具集合组成的集合或迭代器，每次把当前项记为多个解包结果，然后等待异步处理完成，并把结果记为 阶段处理结果；断言是否错误信息不是真；不满足就终止当前测试或流程；断言内容不为空；不满足就终止当前测试或流程。
            等待异步处理完成，并把结果记为 状态资源；等待异步处理完成，并把结果记为 资源；断言当前处理结果有值或为真；不满足就终止当前测试或流程；断言当前处理结果有值或为真；不满足就终止当前测试或流程。
无论成功还是失败，最后都要：
    计算使用固定配置或常量值，并保存为 当前处理结果；调用 `join` 完成该函数的一项辅助处理；断言“调用 `is_alive` 校验当前输入或状态”后未得到肯定结果；不满足就终止当前测试或流程。
```

### `tests/test_mcp_runtime_policy.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_committed_runtime_policy_is_valid`

- **源码**：`tests/test_mcp_runtime_policy.py:14`
- **签名**：`def test_committed_runtime_policy_is_valid() -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `load_runtime_policy` 读取或查询当前阶段需要的数据，并把结果记为 安全策略；断言安全策略的 SHA-256等于辅助操作“调用 `policy_hash` 完成该函数的一项辅助处理”的结果；不满足就终止当前测试或流程；断言配置集合等于['in-memory-legacy', 'in-memory-modern']；不满足就终止当前测试或流程；断言当前输入内容属于配置集合；不满足就终止当前测试或流程。
```

#### `test_policy_rejects_hash_mismatch`

- **源码**：`tests/test_mcp_runtime_policy.py:27`
- **签名**：`def test_policy_rejects_hash_mismatch(tmp_path) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
将外部表示解析为结构化内容，并把结果记为 结构化请求载荷；计算使用固定配置或常量值，并保存为 结构化请求载荷中的对应字段；计算组合或计算已有值，并保存为 文件或目录路径；创建父级目录或父领域对象对应的目录。
将处理结果写入文件或目录路径指定的文件。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `load_runtime_policy` 读取或查询当前阶段需要的数据，退出时自动清理资源。
```

#### `test_policy_rejects_new_operation_even_with_valid_hash`

- **源码**：`tests/test_mcp_runtime_policy.py:40`
- **签名**：`def test_policy_rejects_new_operation_even_with_valid_hash(tmp_path) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
将外部表示解析为结构化内容，并把结果记为 结构化请求载荷；把新的处理结果追加或合并到结构化请求载荷中的对应字段；按稳定规则整理结果顺序，并把结果记为 结构化请求载荷中的对应字段；复制、序列化或校验结构化领域对象，并把结果记为 待审核的 MCP 能力候选。
调用 `policy_hash` 完成该函数的一项辅助处理，并把结果记为 结构化请求载荷中的对应字段；计算组合或计算已有值，并保存为 文件或目录路径；创建父级目录或父领域对象对应的目录；将处理结果写入文件或目录路径指定的文件。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `load_runtime_policy` 读取或查询当前阶段需要的数据，退出时自动清理资源。
```

### `tests/test_mcp_runtime_probe.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `anyio_backend`

- **源码**：`tests/test_mcp_runtime_probe.py:28`
- **签名**：`def anyio_backend() -> str`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
返回固定值 `'asyncio'`。
```

#### `FakeResourceResult.model_dump`

- **源码**：`tests/test_mcp_runtime_probe.py:40`
- **签名**：`def model_dump(self, *, mode: str)`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收MCP 评测或运行模式，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `mode` | `str` | MCP 评测或运行模式；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
断言MCP 评测或运行模式等于'json'；不满足就终止当前测试或流程；返回包含 `contents` 字段的结构化映射。
```

#### `FakeClient.__init__`

- **源码**：`tests/test_mcp_runtime_probe.py:46`
- **签名**：`def __init__(self, *, timeout_status: bool = False) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收状态，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `timeout_status` | `bool` | 布尔条件或能力开关，用于控制流程分支。；默认 假 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 状态 分别保存到同名实例字段。
```

#### `FakeClient.call_tool`

- **源码**：`tests/test_mcp_runtime_probe.py:49`
- **签名**：`async def call_tool(self: 未显式标注, name: 未显式标注, arguments: 未显式标注, read_timeout_seconds: 未显式标注) -> 未显式标注（存在 return）`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收对象名称、结构化调用参数、当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `name` | `未显式标注` | 对象名称；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `arguments` | `未显式标注` | 结构化调用参数；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `read_timeout_seconds` | `未显式标注` | 名为 `read_timeout_seconds` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。；默认 空值 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
如果状态有值或为真 且 对象名称等于'get_reproduction_status'，就等待异步处理完成，并提交它产生的状态变更；拒绝继续处理并抛出 `asyncio.TimeoutError`，向调用方报告输入或运行失败。
构造并返回 `FakeToolResult` 结构化领域对象。
```

#### `FakeClient.read_resource`

- **源码**：`tests/test_mcp_runtime_probe.py:62`
- **签名**：`async def read_resource(self, uri)`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收MCP 资源或外部研究地址，用于读取并整理论文、源码或运行产物，把原始输入转换成带位置和身份信息的结构化证据，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `uri` | `未显式标注` | 资源地址；进入网络或持久化前仍需策略校验和必要的脱敏。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
构造并返回 `FakeResourceResult` 结构化领域对象。
```

#### `_target`

- **源码**：`tests/test_mcp_runtime_probe.py:66`
- **签名**：`def _target(client: FakeClient) -> McpProbeTarget`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收外部服务客户端，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `McpProbeTarget` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `client` | `FakeClient` | 外部服务客户端；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`McpProbeTarget`
- **语义**：返回 `McpProbeTarget` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造 `McpClientProfile` 结构化领域对象，并把结果记为 MCP Client 配置档案。
定义内部辅助函数 `connect`，供当前函数在后续步骤中调用。
构造并返回 `McpProbeTarget` 结构化领域对象。
```

#### `_target.connect`

- **源码**：`tests/test_mcp_runtime_probe.py:74`
- **签名**：`async def connect()`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于在固定 MCP Policy、Schema Pin、调用预算和只读职责边界内连接或调用外部能力，并把返回内容转换为可追溯的复现证据，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
完成当前表达式对应的校验或状态操作。
```

#### `_policy`

- **源码**：`tests/test_mcp_runtime_probe.py:80`
- **签名**：`def _policy(*, timeout_seconds: float = 1.0)`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收等待超时时间（秒），用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `timeout_seconds` | `float` | 超时或截止时间限制；用于防止等待/搜索/执行无限持续。；默认 1.0 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
调用 `load_runtime_policy` 读取或查询当前阶段需要的数据，并把结果记为 该调用返回的结果；复制、序列化或校验结构化领域对象，并返回处理结果。
```

#### `test_probe_hashes_outputs_and_covers_six_operations`

- **源码**：`tests/test_mcp_runtime_probe.py:96`
- **签名**：`async def test_probe_hashes_outputs_and_covers_six_operations(monkeypatch: 未显式标注) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收测试环境修改工具，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `monkeypatch` | `未显式标注` | pytest 提供的环境/对象替换工具，用于隔离测试副作用；不是业务输入。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `load_baseline` 读取或查询当前阶段需要的数据，并把结果记为 已审核的 MCP 能力基线。
定义内部辅助函数 `observe`，供当前函数在后续步骤中调用。
调用 `setattr` 完成该函数的一项辅助处理；等待异步处理完成，并把结果记为 MCP 评测或运行报告；断言当前处理结果是真；不满足就终止当前测试或流程；断言操作采样结果集合 的长度等于6；不满足就终止当前测试或流程。
断言当前可迭代输入中每一项都满足“输出结果的 SHA-256有值或为真”的项；不满足就终止当前测试或流程；断言辅助操作“调用 `runtime_report_hash` 完成该函数的一项辅助处理”的结果等于MCP 评测或运行报告的 SHA-256；不满足就终止当前测试或流程；将结构化内容序列化或编码为可传输表示，并把结果记为 该调用返回的结果；断言复现任务 ID不属于当前处理结果；不满足就终止当前测试或流程。
断言当前输入内容不属于当前处理结果；不满足就终止当前测试或流程。
```

#### `test_probe_hashes_outputs_and_covers_six_operations.observe`

- **源码**：`tests/test_mcp_runtime_probe.py:101`
- **签名**：`async def observe(_client, *, profile)`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收外部服务客户端、MCP Client 配置档案，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `_client` | `未显式标注` | 名为 `_client` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `profile` | `未显式标注` | 运行/执行环境配置或 profile 标识；描述能力和限制，不是一次执行的结果。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
构造并返回 `SimpleNamespace` 结构化领域对象。
```

#### `test_probe_turns_hang_into_timeout_finding`

- **源码**：`tests/test_mcp_runtime_probe.py:140`
- **签名**：`async def test_probe_turns_hang_into_timeout_finding(monkeypatch) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收测试环境修改工具，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `monkeypatch` | `未显式标注` | pytest 提供的环境/对象替换工具，用于隔离测试副作用；不是业务输入。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `load_baseline` 读取或查询当前阶段需要的数据，并把结果记为 已审核的 MCP 能力基线。
定义内部辅助函数 `observe`，供当前函数在后续步骤中调用。
调用 `setattr` 完成该函数的一项辅助处理；等待异步处理完成，并把结果记为 MCP 评测或运行报告；断言当前处理结果是假；不满足就终止当前测试或流程；遍历并筛选输入，将整理后的结果保存为 状态集合。
断言当前状态等于'timeout'；不满足就终止当前测试或流程；断言错误等于'MCP_RUNTIME_TIMEOUT'；不满足就终止当前测试或流程。
```

#### `test_probe_turns_hang_into_timeout_finding.observe`

- **源码**：`tests/test_mcp_runtime_probe.py:143`
- **签名**：`async def observe(_client, *, profile)`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收外部服务客户端、MCP Client 配置档案，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `_client` | `未显式标注` | 名为 `_client` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `profile` | `未显式标注` | 运行/执行环境配置或 profile 标识；描述能力和限制，不是一次执行的结果。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
构造并返回 `SimpleNamespace` 结构化领域对象。
```

### `tests/test_mcp_runtime_repository.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_report`

- **源码**：`tests/test_mcp_runtime_repository.py:22`
- **签名**：`def _report() -> McpRuntimeReport`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `McpRuntimeReport` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`McpRuntimeReport`
- **语义**：返回 `McpRuntimeReport` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造 `McpInvocationSample` 结构化领域对象，并把结果记为 该调用返回的结果；构造 `McpOperationSummary` 结构化领域对象，并把结果记为 阶段摘要；构造 `McpRuntimeReport` 结构化领域对象，并把结果记为 MCP 评测或运行报告；复制、序列化或校验结构化领域对象，并返回处理结果。
```

#### `test_repository_round_trips_hash_bound_report`

- **源码**：`tests/test_mcp_runtime_repository.py:65`
- **签名**：`def test_repository_round_trips_hash_bound_report(tmp_path) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合或计算已有值，并保存为 受控扫描根目录；调用 `_report` 完成该函数的一项辅助处理，并把结果记为 MCP 评测或运行报告；调用 `write_runtime_report` 持久化或更新当前领域数据，并把结果记为 多个解包结果；调用 `load_runtime_report` 读取或查询当前阶段需要的数据，并把结果记为 已加载结果。
断言已加载结果等于MCP 评测或运行报告；不满足就终止当前测试或流程；断言“检查当前处理结果的路径的文件系统属性”后得到肯定结果；不满足就终止当前测试或流程；断言MCP 评测或运行报告的 SHA-256属于辅助操作“读取当前处理结果的路径中的文件内容”的结果；不满足就终止当前测试或流程。
```

#### `test_repository_rejects_tampered_report`

- **源码**：`tests/test_mcp_runtime_repository.py:81`
- **签名**：`def test_repository_rejects_tampered_report(tmp_path) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合或计算已有值，并保存为 受控扫描根目录；调用 `write_runtime_report` 持久化或更新当前领域数据，并把结果记为 多个解包结果；将外部表示解析为结构化内容，并把结果记为 结构化请求载荷；计算使用固定配置或常量值，并保存为 结构化请求载荷中的对应字段。
将处理结果写入JSON 数据的路径指定的文件。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `load_runtime_report` 读取或查询当前阶段需要的数据，退出时自动清理资源。
```

#### `test_repository_rejects_path_outside_report_root`

- **源码**：`tests/test_mcp_runtime_repository.py:95`
- **签名**：`def test_repository_rejects_path_outside_report_root(tmp_path) -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合或计算已有值，并保存为 受控扫描根目录；计算组合或计算已有值，并保存为 当前处理结果；创建父级目录或父领域对象对应的目录；将处理结果写入当前处理结果指定的文件。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `load_runtime_report` 读取或查询当前阶段需要的数据，退出时自动清理资源。
```

### `tests/test_mcp_runtime_upgrade.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_report`

- **源码**：`tests/test_mcp_runtime_upgrade.py:21`
- **签名**：`def _report(*, report_id: str, p95_ms: float) -> McpRuntimeReport`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收MCP 评测或运行报告的 ID、当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `McpRuntimeReport` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `report_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `p95_ms` | `float` | 名为 `p95_ms` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`McpRuntimeReport`
- **语义**：返回 `McpRuntimeReport` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造 `McpInvocationSample` 结构化领域对象，并把结果记为 该调用返回的结果；构造 `McpOperationSummary` 结构化领域对象，并把结果记为 阶段摘要；调用 `load_runtime_policy` 读取或查询当前阶段需要的数据，并把结果记为 安全策略；构造 `McpRuntimeReport` 结构化领域对象，并把结果记为 MCP 评测或运行报告。
复制、序列化或校验结构化领域对象，并返回处理结果。
```

#### `test_upgrade_rejects_large_latency_regression`

- **源码**：`tests/test_mcp_runtime_upgrade.py:68`
- **签名**：`def test_upgrade_rejects_large_latency_regression() -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `load_runtime_policy` 读取或查询当前阶段需要的数据，并把结果记为 安全策略；调用 `compare_runtime_reports` 完成该函数的一项辅助处理，并把结果记为 SDK 或 MCP 运行升级比较结果；断言当前处理结果是假；不满足就终止当前测试或流程；断言当前输入内容属于发现集合；不满足就终止当前测试或流程。
```

#### `test_upgrade_accepts_small_local_jitter`

- **源码**：`tests/test_mcp_runtime_upgrade.py:91`
- **签名**：`def test_upgrade_accepts_small_local_jitter() -> None`
- **作用**：在论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `load_runtime_policy` 读取或查询当前阶段需要的数据，并把结果记为 安全策略；调用 `compare_runtime_reports` 完成该函数的一项辅助处理，并把结果记为 SDK 或 MCP 运行升级比较结果；断言当前处理结果是真；不满足就终止当前测试或流程。
```

### `tests/test_model_routing_api.py`

**模块作用**：Phase 50: Model Routing API 只读端点测试。

#### `FakeGateway.__init__`

- **源码**：`tests/test_model_routing_api.py:36`
- **签名**：`def __init__(self, *, budget_summary=None, invocations=None)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收当前处理结果、当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `budget_summary` | `未显式标注` | 名为 `budget_summary` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。；默认 空值 |
| `invocations` | `未显式标注` | 名为 `invocations` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。；默认 空值 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
计算计算当前表达式的结果，并保存为 当前处理结果；计算计算当前表达式的结果，并保存为 当前处理结果。
定义内部类型 `_FakeLedger`，用于组织当前函数的临时逻辑。
调用 `_FakeLedger` 完成该函数的一项辅助处理，并把结果记为 幂等、租约或审计账本；计算使用固定配置或常量值，并保存为 MCP 评测或运行模式；计算使用固定配置或常量值，并保存为 API 路由器；计算使用固定配置或常量值，并保存为 模型服务商配置集合。
```

#### `FakeGateway.__init__._FakeLedger.summary`

- **源码**：`tests/test_model_routing_api.py:52`
- **签名**：`def summary(inner_self, *, utc_date, job_id=None)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收当前处理结果、日期、复现任务 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `inner_self` | `未显式标注` | 名为 `inner_self` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `utc_date` | `未显式标注` | 名为 `utc_date` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `job_id` | `未显式标注` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。；默认 空值 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
返回前一步处理得到的结果。
```

#### `FakeGateway.__init__._FakeLedger.list_invocations`

- **源码**：`tests/test_model_routing_api.py:55`
- **签名**：`def list_invocations(inner_self, *, job_id=None, limit=100)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收当前处理结果、复现任务 ID、结果数量上限，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `inner_self` | `未显式标注` | 名为 `inner_self` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `job_id` | `未显式标注` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。；默认 空值 |
| `limit` | `未显式标注` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。；默认 100 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
返回当前处理结果中的对应字段的当前值。
```

#### `FakeGateway.__init__._FakeLedger.ping`

- **源码**：`tests/test_model_routing_api.py:58`
- **签名**：`def ping(inner_self)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `inner_self` | `未显式标注` | 名为 `inner_self` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
返回固定值 `空值`。
```

#### `_create_test_app`

- **源码**：`tests/test_model_routing_api.py:67`
- **签名**：`def _create_test_app(gateway: Any) -> FastAPI`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收外部服务网关，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `FastAPI` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `gateway` | `Any` | 外部服务网关；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`FastAPI`
- **语义**：返回 `FastAPI` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造 `FastAPI` 结构化领域对象，并把结果记为 该调用返回的结果；读取外部服务网关，并保存为 网关；调用 `include_router` 完成该函数的一项辅助处理；返回前一步处理得到的结果。
```

#### `_create_authed_app`

- **源码**：`tests/test_model_routing_api.py:74`
- **签名**：`def _create_authed_app(gateway: Any) -> FastAPI`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，创建带 auth 的测试 app，使用 dependency override 绕过认证。该函数接收外部服务网关，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `FastAPI` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `gateway` | `Any` | 外部服务网关；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`FastAPI`
- **语义**：返回 `FastAPI` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
加载这一步需要的外部依赖；构造 `FastAPI` 结构化领域对象，并把结果记为 该调用返回的结果；读取外部服务网关，并保存为 网关；计算计算当前表达式的结果，并保存为 当前处理结果中的对应字段。
调用 `include_router` 完成该函数的一项辅助处理；调用 `install_error_handlers` 完成该函数的一项辅助处理；返回前一步处理得到的结果。
```

#### `test_get_budget_summary`

- **源码**：`tests/test_model_routing_api.py:86`
- **签名**：`def test_get_budget_summary(tmp_path: Path)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `FakeGateway` 结构化领域对象，并把结果记为 外部服务网关；调用 `_create_authed_app` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果；构造 `TestClient` 结构化领域对象，并把结果记为 外部服务客户端；从外部服务客户端读取所需的状态或领域记录，并把结果记为 结构化响应。
断言状态等于200；不满足就终止当前测试或流程；调用 `json` 完成该函数的一项辅助处理，并把结果记为 待处理数据；断言当前输入内容属于待处理数据；不满足就终止当前测试或流程；断言当前输入内容属于待处理数据；不满足就终止当前测试或流程。
```

#### `test_get_budget_summary_with_date`

- **源码**：`tests/test_model_routing_api.py:98`
- **签名**：`def test_get_budget_summary_with_date(tmp_path: Path)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `FakeGateway` 结构化领域对象，并把结果记为 外部服务网关；调用 `_create_authed_app` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果；构造 `TestClient` 结构化领域对象，并把结果记为 外部服务客户端；从外部服务客户端读取所需的状态或领域记录，并把结果记为 结构化响应。
断言状态等于200；不满足就终止当前测试或流程。
```

#### `test_get_budget_summary_with_job_id`

- **源码**：`tests/test_model_routing_api.py:109`
- **签名**：`def test_get_budget_summary_with_job_id(tmp_path: Path)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `FakeGateway` 结构化领域对象，并把结果记为 外部服务网关；调用 `_create_authed_app` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果；构造 `TestClient` 结构化领域对象，并把结果记为 外部服务客户端；从外部服务客户端读取所需的状态或领域记录，并把结果记为 结构化响应。
断言状态等于200；不满足就终止当前测试或流程。
```

#### `test_list_invocations`

- **源码**：`tests/test_model_routing_api.py:120`
- **签名**：`def test_list_invocations(tmp_path: Path)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `FakeGateway` 结构化领域对象，并把结果记为 外部服务网关；调用 `_create_authed_app` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果；构造 `TestClient` 结构化领域对象，并把结果记为 外部服务客户端；从外部服务客户端读取所需的状态或领域记录，并把结果记为 结构化响应。
断言状态等于200；不满足就终止当前测试或流程；断言“计算数量、边界或类型判断结果”后得到肯定结果；不满足就终止当前测试或流程。
```

#### `test_list_invocations_with_limit`

- **源码**：`tests/test_model_routing_api.py:130`
- **签名**：`def test_list_invocations_with_limit(tmp_path: Path)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `FakeGateway` 结构化领域对象，并把结果记为 外部服务网关；调用 `_create_authed_app` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果；构造 `TestClient` 结构化领域对象，并把结果记为 外部服务客户端；从外部服务客户端读取所需的状态或领域记录，并把结果记为 结构化响应。
断言状态等于200；不满足就终止当前测试或流程。
```

#### `test_list_invocations_limit_too_large`

- **源码**：`tests/test_model_routing_api.py:141`
- **签名**：`def test_list_invocations_limit_too_large(tmp_path: Path)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `FakeGateway` 结构化领域对象，并把结果记为 外部服务网关；调用 `_create_authed_app` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果；构造 `TestClient` 结构化领域对象，并把结果记为 外部服务客户端；从外部服务客户端读取所需的状态或领域记录，并把结果记为 结构化响应。
断言状态等于422；不满足就终止当前测试或流程。
```

#### `test_list_invocations_limit_too_small`

- **源码**：`tests/test_model_routing_api.py:152`
- **签名**：`def test_list_invocations_limit_too_small(tmp_path: Path)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `FakeGateway` 结构化领域对象，并把结果记为 外部服务网关；调用 `_create_authed_app` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果；构造 `TestClient` 结构化领域对象，并把结果记为 外部服务客户端；从外部服务客户端读取所需的状态或领域记录，并把结果记为 结构化响应。
断言状态等于422；不满足就终止当前测试或流程。
```

#### `test_no_put_policy_endpoint`

- **源码**：`tests/test_model_routing_api.py:163`
- **签名**：`def test_no_put_policy_endpoint(tmp_path: Path)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `FakeGateway` 结构化领域对象，并把结果记为 外部服务网关；调用 `_create_authed_app` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果；构造 `TestClient` 结构化领域对象，并把结果记为 外部服务客户端；调用 `put` 完成该函数的一项辅助处理，并把结果记为 结构化响应。
断言状态等于405 或 状态等于404；不满足就终止当前测试或流程。
```

#### `test_no_post_budget_endpoint`

- **源码**：`tests/test_model_routing_api.py:172`
- **签名**：`def test_no_post_budget_endpoint(tmp_path: Path)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `FakeGateway` 结构化领域对象，并把结果记为 外部服务网关；调用 `_create_authed_app` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果；构造 `TestClient` 结构化领域对象，并把结果记为 外部服务客户端；调用 `post` 完成该函数的一项辅助处理，并把结果记为 结构化响应。
断言状态等于405 或 状态等于404；不满足就终止当前测试或流程。
```

#### `test_model_budget_exceeded_maps_to_429`

- **源码**：`tests/test_model_routing_api.py:181`
- **签名**：`def test_model_budget_exceeded_maps_to_429(tmp_path: Path)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：无业务返回值；通过断言或预期异常验证目标行为。

**伪代码**

```text
加载这一步需要的外部依赖；构造 `FastAPI` 结构化领域对象，并把结果记为 该调用返回的结果。
定义内部类型 `_RaisingLedger`，用于组织当前函数的临时逻辑。
定义内部类型 `_RaisingGateway`，用于组织当前函数的临时逻辑。
调用 `_RaisingGateway` 完成该函数的一项辅助处理，并把结果记为 网关；计算计算当前表达式的结果，并保存为 当前处理结果中的对应字段；调用 `include_router` 完成该函数的一项辅助处理；调用 `install_error_handlers` 完成该函数的一项辅助处理。
构造 `TestClient` 结构化领域对象，并把结果记为 外部服务客户端；从外部服务客户端读取所需的状态或领域记录，并把结果记为 结构化响应；断言状态等于429；不满足就终止当前测试或流程；调用 `json` 完成该函数的一项辅助处理，并把结果记为 待处理数据。
断言待处理数据中的对应字段等于'MODEL_BUDGET_EXCEEDED'；不满足就终止当前测试或流程；断言当前输入内容不属于待处理文本；不满足就终止当前测试或流程。
```

#### `test_model_budget_exceeded_maps_to_429._RaisingLedger.ping`

- **源码**：`tests/test_model_routing_api.py:187`
- **签名**：`def ping(inner_self)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `inner_self` | `未显式标注` | 名为 `inner_self` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
返回固定值 `空值`。
```

#### `test_model_budget_exceeded_maps_to_429._RaisingLedger.summary`

- **源码**：`tests/test_model_routing_api.py:190`
- **签名**：`def summary(inner_self, *, utc_date, job_id=None)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收当前处理结果、日期、复现任务 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `inner_self` | `未显式标注` | 名为 `inner_self` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `utc_date` | `未显式标注` | 名为 `utc_date` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `job_id` | `未显式标注` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。；默认 空值 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
拒绝继续处理并抛出 `ModelBudgetExceeded`，向调用方报告输入或运行失败。
```

#### `test_model_budget_exceeded_maps_to_429._RaisingLedger.list_invocations`

- **源码**：`tests/test_model_routing_api.py:198`
- **签名**：`def list_invocations(inner_self, *, job_id=None, limit=100)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收当前处理结果、复现任务 ID、结果数量上限，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `inner_self` | `未显式标注` | 名为 `inner_self` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `job_id` | `未显式标注` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。；默认 空值 |
| `limit` | `未显式标注` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。；默认 100 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
返回当前构造的顺序或去重集合。
```

#### `test_ledger_integrity_error_maps_to_503`

- **源码**：`tests/test_model_routing_api.py:221`
- **签名**：`def test_ledger_integrity_error_maps_to_503(tmp_path: Path)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：无业务返回值；通过断言或预期异常验证目标行为。

**伪代码**

```text
加载这一步需要的外部依赖；构造 `FastAPI` 结构化领域对象，并把结果记为 该调用返回的结果。
定义内部类型 `_RaisingLedger`，用于组织当前函数的临时逻辑。
定义内部类型 `_RaisingGateway`，用于组织当前函数的临时逻辑。
调用 `_RaisingGateway` 完成该函数的一项辅助处理，并把结果记为 网关；计算计算当前表达式的结果，并保存为 当前处理结果中的对应字段；调用 `include_router` 完成该函数的一项辅助处理；调用 `install_error_handlers` 完成该函数的一项辅助处理。
构造 `TestClient` 结构化领域对象，并把结果记为 外部服务客户端；从外部服务客户端读取所需的状态或领域记录，并把结果记为 结构化响应；断言状态等于503；不满足就终止当前测试或流程；调用 `json` 完成该函数的一项辅助处理，并把结果记为 待处理数据。
断言待处理数据中的对应字段等于'MODEL_LEDGER_UNAVAILABLE'；不满足就终止当前测试或流程。
```

#### `test_ledger_integrity_error_maps_to_503._RaisingLedger.ping`

- **源码**：`tests/test_model_routing_api.py:227`
- **签名**：`def ping(inner_self)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `inner_self` | `未显式标注` | 名为 `inner_self` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
返回固定值 `空值`。
```

#### `test_ledger_integrity_error_maps_to_503._RaisingLedger.summary`

- **源码**：`tests/test_model_routing_api.py:230`
- **签名**：`def summary(inner_self, *, utc_date, job_id=None)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收当前处理结果、日期、复现任务 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `inner_self` | `未显式标注` | 名为 `inner_self` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `utc_date` | `未显式标注` | 名为 `utc_date` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `job_id` | `未显式标注` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。；默认 空值 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
拒绝继续处理并抛出 `ModelLedgerIntegrityError`，向调用方报告输入或运行失败。
```

#### `test_ledger_integrity_error_maps_to_503._RaisingLedger.list_invocations`

- **源码**：`tests/test_model_routing_api.py:233`
- **签名**：`def list_invocations(inner_self, *, job_id=None, limit=100)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收当前处理结果、复现任务 ID、结果数量上限，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `inner_self` | `未显式标注` | 名为 `inner_self` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `job_id` | `未显式标注` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。；默认 空值 |
| `limit` | `未显式标注` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。；默认 100 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
返回当前构造的顺序或去重集合。
```

### `tests/test_model_routing_authority_boundary.py`

**模块作用**：Phase 50: Model Routing Authority Boundary 测试。

#### `_check_imports`

- **源码**：`tests/test_model_routing_authority_boundary.py:25`
- **签名**：`def _check_imports(file_path: Path, forbidden: set[str]) -> list[str]`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，检查文件中的 import 是否包含禁止的模块。该函数接收目标文件路径、被策略禁止的内容或操作，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `file_path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |
| `forbidden` | `set[str]` | 被策略禁止的内容或操作；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`list[str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
读取目标文件路径中的文件内容，并把结果记为 数据来源标记；将 Python 源码解析为抽象语法树，并把结果记为 该调用返回的结果；将 约束违反项集合 初始化为空列表，用来收集后续结果。
遍历语法树节点集合，每次把当前项记为当前流程节点：
    如果“计算数量、边界或类型判断结果”后得到肯定结果：
        遍历当前可迭代输入，每次把当前项记为对象别名：
            遍历由被策略禁止的内容或操作组成的集合或迭代器，每次把当前项记为当前处理结果：
                如果对象名称等于当前处理结果 或 “检查对象名称是否满足文本匹配条件”后得到肯定结果，就把新的处理结果追加或合并到约束违反项集合。
    否则：
        如果“计算数量、边界或类型判断结果”后得到肯定结果：
            如果Python 模块有值或为真：
                遍历由被策略禁止的内容或操作组成的集合或迭代器，每次把当前项记为当前处理结果：
                    如果Python 模块等于当前处理结果 或 “检查Python 模块是否满足文本匹配条件”后得到肯定结果，就把新的处理结果追加或合并到约束违反项集合。
返回约束违反项集合的当前值。
```

#### `test_core_modules_no_forbidden_imports`

- **源码**：`tests/test_model_routing_authority_boundary.py:65`
- **签名**：`def test_core_modules_no_forbidden_imports(module_path: str)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收Python 模块的路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `module_path` | `str` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把外部位置解析为文件系统路径对象，并把结果记为 文件或目录路径。
如果“调用 `is_absolute` 校验当前输入或状态”后未得到肯定结果，就计算组合或计算已有值，并保存为 文件或目录路径。
调用 `_check_imports` 校验当前输入或状态，并把结果记为 约束违反项集合；断言约束违反项集合为空或为假，失败时附带断言说明；不满足就终止当前测试或流程。
```

#### `test_gateway_no_execution_imports`

- **源码**：`tests/test_model_routing_authority_boundary.py:75`
- **签名**：`def test_gateway_no_execution_imports()`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合或计算已有值，并保存为 文件或目录路径；计算初始化去重集合，并保存为 被策略禁止的内容或操作；调用 `_check_imports` 校验当前输入或状态，并把结果记为 约束违反项集合；断言约束违反项集合为空或为假，失败时附带断言说明；不满足就终止当前测试或流程。
```

#### `test_provider_no_business_logic_imports`

- **源码**：`tests/test_model_routing_authority_boundary.py:91`
- **签名**：`def test_provider_no_business_logic_imports()`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合或计算已有值，并保存为 文件或目录路径；计算初始化去重集合，并保存为 被策略禁止的内容或操作；调用 `_check_imports` 校验当前输入或状态，并把结果记为 约束违反项集合；断言约束违反项集合为空或为假，失败时附带断言说明；不满足就终止当前测试或流程。
```

#### `test_api_router_only_get_methods`

- **源码**：`tests/test_model_routing_authority_boundary.py:106`
- **签名**：`def test_api_router_only_get_methods()`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，API Router 只应有 GET 端点。该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合或计算已有值，并保存为 文件或目录路径；读取文件或目录路径中的文件内容，并把结果记为 数据来源标记；将 Python 源码解析为抽象语法树，并把结果记为 该调用返回的结果；将 当前处理结果 初始化为空列表，用来收集后续结果。
遍历语法树节点集合，每次把当前项记为当前流程节点：
    如果“计算数量、边界或类型判断结果”后得到肯定结果：
        读取当前处理结果，并保存为 后续步骤使用的结果。
        如果“计算数量、边界或类型判断结果”后得到肯定结果：
            如果当前处理结果属于{'get', 'post', 'put', 'delete', 'patch'}，就把当前处理结果追加或合并到当前处理结果。
断言由当前处理结果组成的集合或迭代器中每一项都满足“当前处理结果等于'get'”的项，失败时附带断言说明；不满足就终止当前测试或流程。
```

#### `test_invocation_record_no_secrets`

- **源码**：`tests/test_model_routing_authority_boundary.py:128`
- **签名**：`def test_invocation_record_no_secrets()`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，ModelInvocationRecord 不应包含 api_key/secret/prompt 原文等字段。该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
加载这一步需要的外部依赖；构造临时集合、映射或轻量领域对象，并把结果记为 结构化对象字段集合；计算初始化去重集合，并保存为 当前处理结果；计算组合或计算已有值，并保存为 当前处理结果。
断言当前处理结果为空或为假，失败时附带断言说明；不满足就终止当前测试或流程。
```

#### `test_invocation_record_dump_no_secrets`

- **源码**：`tests/test_model_routing_authority_boundary.py:148`
- **签名**：`def test_invocation_record_dump_no_secrets()`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，ModelInvocationRecord 的 dump 不应包含 secret 值。该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
加载这一步需要的外部依赖；加载这一步需要的外部依赖；构造 `ModelInvocationRecord` 结构化领域对象，并把结果记为 领域记录；复制、序列化或校验结构化领域对象，并把结果记为 该调用返回的结果。
调用 `str` 完成该函数的一项辅助处理，再对返回文本执行规范化或拆分，并把结果记为 该调用返回的结果；计算初始化顺序集合，并保存为 当前处理结果。
遍历由当前处理结果组成的集合或迭代器，每次把当前项记为文本匹配模式：
    如果文本匹配模式等于'secret' 且 当前输入内容属于当前处理结果，就跳过本轮剩余处理，直接进入下一轮。
    断言文本匹配模式不属于当前处理结果 或 文本匹配模式属于当前处理结果 且 “检查文本匹配模式是否满足文本匹配条件”后得到肯定结果，失败时附带断言说明；不满足就终止当前测试或流程。
```

### `tests/test_model_routing_catalog.py`

**模块作用**：Phase 50: Model Routing Catalog 加载与校验测试。

#### `test_valid_policy_loads`

- **源码**：`tests/test_model_routing_catalog.py:18`
- **签名**：`def test_valid_policy_loads(tmp_path: Path)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `write_test_policy` 持久化或更新当前领域数据，并把结果记为 安全策略的路径；调用 `load_model_catalog` 读取或查询当前阶段需要的数据，并把结果记为 模型、工具或 Artifact 目录；断言策略版本等于'test-v1'；不满足就终止当前测试或流程；断言MCP Client 配置档案集合 的长度等于4；不满足就终止当前测试或流程。
断言当前处理结果 的长度等于12；不满足就终止当前测试或流程；断言安全策略的 SHA-256 的长度等于64；不满足就终止当前测试或流程。
```

#### `test_policy_sha256_stable`

- **源码**：`tests/test_model_routing_catalog.py:36`
- **签名**：`def test_policy_sha256_stable(tmp_path: Path)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `write_test_policy` 持久化或更新当前领域数据，并把结果记为 安全策略的路径；计算按字段初始化键值映射，并保存为 当前处理结果；调用 `load_model_catalog` 读取或查询当前阶段需要的数据，并把结果记为 该调用返回的结果；调用 `load_model_catalog` 读取或查询当前阶段需要的数据，并把结果记为 该调用返回的结果。
断言安全策略的 SHA-256等于安全策略的 SHA-256；不满足就终止当前测试或流程。
```

#### `test_duplicate_profile_id_rejected`

- **源码**：`tests/test_model_routing_catalog.py:49`
- **签名**：`def test_duplicate_profile_id_rejected(tmp_path: Path)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `build_test_document` 组装当前阶段需要的领域对象，并把结果记为 模块或函数文档文本；读取MCP Client 配置档案 ID，并保存为 MCP Client 配置档案 ID；调用 `write_test_policy` 持久化或更新当前领域数据，并把结果记为 安全策略的路径。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `load_model_catalog` 读取或查询当前阶段需要的数据，退出时自动清理资源。
```

#### `test_duplicate_task_route_rejected`

- **源码**：`tests/test_model_routing_catalog.py:61`
- **签名**：`def test_duplicate_task_route_rejected(tmp_path: Path)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `build_test_document` 组装当前阶段需要的领域对象，并把结果记为 模块或函数文档文本；读取类别，并保存为 类别；调用 `write_test_policy` 持久化或更新当前领域数据，并把结果记为 安全策略的路径。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `load_model_catalog` 读取或查询当前阶段需要的数据，退出时自动清理资源。
```

#### `test_unknown_profile_reference_rejected`

- **源码**：`tests/test_model_routing_catalog.py:73`
- **签名**：`def test_unknown_profile_reference_rejected(tmp_path: Path)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `build_test_document` 组装当前阶段需要的领域对象，并把结果记为 模块或函数文档文本；计算初始化顺序集合，并保存为 候选项配置集合；调用 `write_test_policy` 持久化或更新当前领域数据，并把结果记为 安全策略的路径。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `load_model_catalog` 读取或查询当前阶段需要的数据，退出时自动清理资源。
```

#### `test_policy_symlink_rejected`

- **源码**：`tests/test_model_routing_catalog.py:85`
- **签名**：`def test_policy_symlink_rejected(tmp_path: Path)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `write_test_policy` 持久化或更新当前领域数据，并把结果记为 安全策略的路径；计算组合或计算已有值，并保存为 当前处理结果的路径；调用 `symlink_to` 完成该函数的一项辅助处理。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `load_model_catalog` 读取或查询当前阶段需要的数据，退出时自动清理资源。
```

#### `test_policy_outside_allowed_root_rejected`

- **源码**：`tests/test_model_routing_catalog.py:97`
- **签名**：`def test_policy_outside_allowed_root_rejected(tmp_path: Path)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `write_test_policy` 持久化或更新当前领域数据，并把结果记为 安全策略的路径；计算组合或计算已有值，并保存为 根目录；创建根目录对应的目录。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `load_model_catalog` 读取或查询当前阶段需要的数据，退出时自动清理资源。
```

#### `test_policy_not_found_rejected`

- **源码**：`tests/test_model_routing_catalog.py:109`
- **签名**：`def test_policy_not_found_rejected(tmp_path: Path)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `load_model_catalog` 读取或查询当前阶段需要的数据，退出时自动清理资源。
```

#### `test_oversized_policy_rejected`

- **源码**：`tests/test_model_routing_catalog.py:118`
- **签名**：`def test_oversized_policy_rejected(tmp_path: Path)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `build_test_document` 组装当前阶段需要的领域对象，并把结果记为 模块或函数文档文本；调用 `write_test_policy` 持久化或更新当前领域数据，并把结果记为 安全策略的路径；计算组合或计算已有值，并保存为 当前处理结果的路径；将外部表示解析为结构化内容，并把结果记为 该调用返回的结果。
计算组合或计算已有值，并保存为 当前处理结果中的对应字段；将处理结果写入当前处理结果的路径指定的文件。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `load_model_catalog` 读取或查询当前阶段需要的数据，退出时自动清理资源。
```

#### `test_placeholder_substitution`

- **源码**：`tests/test_model_routing_catalog.py:134`
- **签名**：`def test_placeholder_substitution(tmp_path: Path)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `build_test_document` 组装当前阶段需要的领域对象，并把结果记为 模块或函数文档文本；调用 `write_test_policy` 持久化或更新当前领域数据，并把结果记为 安全策略的路径；调用 `load_model_catalog` 读取或查询当前阶段需要的数据，并把结果记为 模型、工具或 Artifact 目录；调用 `profile` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
断言模型标识或模型配置的名称等于'real-model'；不满足就终止当前测试或流程。
```

#### `test_unknown_placeholder_rejected`

- **源码**：`tests/test_model_routing_catalog.py:151`
- **签名**：`def test_unknown_placeholder_rejected(tmp_path: Path)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `build_test_document` 组装当前阶段需要的领域对象，并把结果记为 模块或函数文档文本；调用 `write_test_policy` 持久化或更新当前领域数据，并把结果记为 安全策略的路径。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `load_model_catalog` 读取或查询当前阶段需要的数据，退出时自动清理资源。
```

#### `test_substitution_changes_policy_sha256`

- **源码**：`tests/test_model_routing_catalog.py:167`
- **签名**：`def test_substitution_changes_policy_sha256(tmp_path: Path)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `build_test_document` 组装当前阶段需要的领域对象，并把结果记为 模块或函数文档文本；调用 `write_test_policy` 持久化或更新当前领域数据，并把结果记为 安全策略的路径；调用 `load_model_catalog` 读取或查询当前阶段需要的数据，并把结果记为 该调用返回的结果；调用 `load_model_catalog` 读取或查询当前阶段需要的数据，并把结果记为 该调用返回的结果。
断言安全策略的 SHA-256不等于安全策略的 SHA-256；不满足就终止当前测试或流程。
```

#### `test_route_workload_mismatch_rejected`

- **源码**：`tests/test_model_routing_catalog.py:193`
- **签名**：`def test_route_workload_mismatch_rejected(tmp_path: Path)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `build_test_document` 组装当前阶段需要的领域对象，并把结果记为 模块或函数文档文本；计算初始化顺序集合，并保存为 候选项配置集合；调用 `write_test_policy` 持久化或更新当前领域数据，并把结果记为 安全策略的路径。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `load_model_catalog` 读取或查询当前阶段需要的数据，退出时自动清理资源。
```

#### `test_route_max_output_exceeds_profile_rejected`

- **源码**：`tests/test_model_routing_catalog.py:206`
- **签名**：`def test_route_max_output_exceeds_profile_rejected(tmp_path: Path)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `build_test_document` 组装当前阶段需要的领域对象，并把结果记为 模块或函数文档文本；计算使用固定配置或常量值，并保存为 最大实际输出 token 数；调用 `write_test_policy` 持久化或更新当前领域数据，并把结果记为 安全策略的路径。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `load_model_catalog` 读取或查询当前阶段需要的数据，退出时自动清理资源。
```

#### `test_profile_method`

- **源码**：`tests/test_model_routing_catalog.py:218`
- **签名**：`def test_profile_method(tmp_path: Path)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `build_test_catalog_helper` 组装当前阶段需要的领域对象，并把结果记为 模型、工具或 Artifact 目录；调用 `profile` 完成该函数的一项辅助处理，并把结果记为 MCP Client 配置档案；断言MCP Client 配置档案 ID等于'legacy_chat'；不满足就终止当前测试或流程。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `profile` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `test_route_method`

- **源码**：`tests/test_model_routing_catalog.py:227`
- **签名**：`def test_route_method(tmp_path: Path)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `build_test_catalog_helper` 组装当前阶段需要的领域对象，并把结果记为 模型、工具或 Artifact 目录；调用 `route` 完成该函数的一项辅助处理，并把结果记为 流程路由结果；断言类别等于'chat_answer'；不满足就终止当前测试或流程。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `route` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `build_test_catalog_helper`

- **源码**：`tests/test_model_routing_catalog.py:236`
- **签名**：`def build_test_catalog_helper(tmp_path: Path)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收临时工作目录路径，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
加载这一步需要的外部依赖；调用 `build_test_catalog` 组装当前阶段需要的领域对象，并返回处理结果。
```

### `tests/test_model_routing_eval.py`

**模块作用**：Phase 50: Model Routing Evaluation 测试。

#### `_build_priced_router`

- **源码**：`tests/test_model_routing_eval.py:30`
- **签名**：`def _build_priced_router(tmp_path: Path) -> ModelRouter`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收临时工作目录路径，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `ModelRouter` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`ModelRouter`
- **语义**：返回 `ModelRouter` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `build_test_document` 组装当前阶段需要的领域对象，并把结果记为 模块或函数文档文本；调用 `write_test_policy` 持久化或更新当前领域数据，并把结果记为 安全策略的路径；调用 `load_model_catalog` 读取或查询当前阶段需要的数据，并把结果记为 模型、工具或 Artifact 目录；构造并返回 `ModelRouter` 结构化领域对象。
```

#### `test_all_cases_pass`

- **源码**：`tests/test_model_routing_eval.py:60`
- **签名**：`def test_all_cases_pass(tmp_path: Path)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_build_priced_router` 组装当前阶段需要的领域对象，并把结果记为 API 路由器；计算初始化顺序集合，并保存为 评测用例集合；调用 `evaluate_routing_cases` 完成该函数的一项辅助处理，并把结果记为 MCP 评测或运行报告；断言当前处理结果是真；不满足就终止当前测试或流程。
断言用例集合集合等于2；不满足就终止当前测试或流程；断言用例集合集合等于2；不满足就终止当前测试或流程；断言当前处理结果等于1.0；不满足就终止当前测试或流程；断言用例集合等于[]；不满足就终止当前测试或流程。
```

#### `test_case_fails_wrong_expected`

- **源码**：`tests/test_model_routing_eval.py:95`
- **签名**：`def test_case_fails_wrong_expected(tmp_path: Path)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_build_priced_router` 组装当前阶段需要的领域对象，并把结果记为 API 路由器；计算初始化顺序集合，并保存为 评测用例集合；调用 `evaluate_routing_cases` 完成该函数的一项辅助处理，并把结果记为 MCP 评测或运行报告；断言当前处理结果是假；不满足就终止当前测试或流程。
断言当前输入内容属于用例集合；不满足就终止当前测试或流程。
```

#### `test_case_fails_forbidden_profile`

- **源码**：`tests/test_model_routing_eval.py:118`
- **签名**：`def test_case_fails_forbidden_profile(tmp_path: Path)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_build_priced_router` 组装当前阶段需要的领域对象，并把结果记为 API 路由器；计算初始化顺序集合，并保存为 评测用例集合；调用 `evaluate_routing_cases` 完成该函数的一项辅助处理，并把结果记为 MCP 评测或运行报告；断言当前处理结果是假；不满足就终止当前测试或流程。
断言当前输入内容属于用例集合；不满足就终止当前测试或流程。
```

#### `test_empty_cases_report`

- **源码**：`tests/test_model_routing_eval.py:141`
- **签名**：`def test_empty_cases_report(tmp_path: Path)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_build_priced_router` 组装当前阶段需要的领域对象，并把结果记为 API 路由器；调用 `evaluate_routing_cases` 完成该函数的一项辅助处理，并把结果记为 MCP 评测或运行报告；断言用例集合集合等于0；不满足就终止当前测试或流程；断言当前处理结果是假；不满足就终止当前测试或流程。
```

#### `test_promotion_requires_route_and_downstream_quality`

- **源码**：`tests/test_model_routing_eval.py:153`
- **签名**：`def test_promotion_requires_route_and_downstream_quality(tmp_path: Path)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_build_priced_router` 组装当前阶段需要的领域对象，并把结果记为 API 路由器；计算初始化顺序集合，并保存为 评测用例集合；调用 `evaluate_routing_cases` 完成该函数的一项辅助处理，并把结果记为 MCP 评测或运行报告；调用 `build_promotion_proposal` 组装当前阶段需要的领域对象，并把结果记为 修复或重跑提案。
断言当前处理结果是假；不满足就终止当前测试或流程；断言当前处理结果是真；不满足就终止当前测试或流程。
```

#### `test_promotion_passes_when_both_gates_pass`

- **源码**：`tests/test_model_routing_eval.py:185`
- **签名**：`def test_promotion_passes_when_both_gates_pass(tmp_path: Path)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_build_priced_router` 组装当前阶段需要的领域对象，并把结果记为 API 路由器；计算初始化顺序集合，并保存为 评测用例集合；调用 `evaluate_routing_cases` 完成该函数的一项辅助处理，并把结果记为 MCP 评测或运行报告；调用 `build_promotion_proposal` 组装当前阶段需要的领域对象，并把结果记为 修复或重跑提案。
断言当前处理结果是真；不满足就终止当前测试或流程；断言当前处理结果是真；不满足就终止当前测试或流程。
```

#### `test_promotion_id_stable`

- **源码**：`tests/test_model_routing_eval.py:218`
- **签名**：`def test_promotion_id_stable(tmp_path: Path)`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_build_priced_router` 组装当前阶段需要的领域对象，并把结果记为 API 路由器；计算初始化顺序集合，并保存为 评测用例集合；调用 `evaluate_routing_cases` 完成该函数的一项辅助处理，并把结果记为 MCP 评测或运行报告；调用 `build_promotion_proposal` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果。
调用 `build_promotion_proposal` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果；断言修复或重跑提案的 ID等于修复或重跑提案的 ID；不满足就终止当前测试或流程。
```

#### `test_no_real_provider_imports`

- **源码**：`tests/test_model_routing_eval.py:257`
- **签名**：`def test_no_real_provider_imports()`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，Evaluation 模块源码不得直接 import app.model 或 langchain_openai。该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
加载这一步需要的外部依赖；加载这一步需要的外部依赖；加载这一步需要的外部依赖；调用 `getsource` 完成该函数的一项辅助处理，并把结果记为 数据来源标记。
将 Python 源码解析为抽象语法树，并把结果记为 该调用返回的结果；计算初始化去重集合，并保存为 当前处理结果。
遍历语法树节点集合，每次把当前项记为当前流程节点：
    如果“计算数量、边界或类型判断结果”后得到肯定结果：
        遍历当前可迭代输入，每次把当前项记为对象别名，然后断言对象名称不属于当前处理结果，失败时附带断言说明；不满足就终止当前测试或流程。
    否则：
        如果“计算数量、边界或类型判断结果”后得到肯定结果，就断言Python 模块不属于当前处理结果，失败时附带断言说明；不满足就终止当前测试或流程。
```

### `tests/test_model_routing_schemas.py`

**模块作用**：Phase 50: Model Routing Schema 与 Identity 工具测试。

#### `test_priced_profile_requires_both_prices`

- **源码**：`tests/test_model_routing_schemas.py:22`
- **签名**：`def test_priced_profile_requires_both_prices()`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中构造 `ModelPricing` 结构化领域对象，退出时自动清理资源。
```

#### `test_priced_profile_requires_input_price`

- **源码**：`tests/test_model_routing_schemas.py:32`
- **签名**：`def test_priced_profile_requires_input_price()`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中构造 `ModelPricing` 结构化领域对象，退出时自动清理资源。
```

#### `test_unpriced_profile_rejects_guessed_price`

- **源码**：`tests/test_model_routing_schemas.py:42`
- **签名**：`def test_unpriced_profile_rejects_guessed_price()`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中构造 `ModelPricing` 结构化领域对象，退出时自动清理资源。
```

#### `test_free_profile_rejects_nonzero_price`

- **源码**：`tests/test_model_routing_schemas.py:52`
- **签名**：`def test_free_profile_rejects_nonzero_price()`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中构造 `ModelPricing` 结构化领域对象，退出时自动清理资源。
```

#### `test_free_profile_accepts_zero_prices`

- **源码**：`tests/test_model_routing_schemas.py:62`
- **签名**：`def test_free_profile_accepts_zero_prices()`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `ModelPricing` 结构化领域对象，并把结果记为 模型计费配置；断言模式等于'free'；不满足就终止当前测试或流程。
```

#### `test_cost_uses_integer_micro_usd_round_up`

- **源码**：`tests/test_model_routing_schemas.py:72`
- **签名**：`def test_cost_uses_integer_micro_usd_round_up()`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `ModelPricing` 结构化领域对象，并把结果记为 模型计费配置；断言辅助操作“调用 `calculate_cost_micro_usd` 完成该函数的一项辅助处理”的结果等于1；不满足就终止当前测试或流程。
```

#### `test_cost_zero_tokens`

- **源码**：`tests/test_model_routing_schemas.py:87`
- **签名**：`def test_cost_zero_tokens()`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `ModelPricing` 结构化领域对象，并把结果记为 模型计费配置；断言辅助操作“调用 `calculate_cost_micro_usd` 完成该函数的一项辅助处理”的结果等于0；不满足就终止当前测试或流程。
```

#### `test_cost_unpriced_returns_none`

- **源码**：`tests/test_model_routing_schemas.py:101`
- **签名**：`def test_cost_unpriced_returns_none()`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `ModelPricing` 结构化领域对象，并把结果记为 模型计费配置；断言辅助操作“调用 `calculate_cost_micro_usd` 完成该函数的一项辅助处理”的结果为空；不满足就终止当前测试或流程。
```

#### `test_cost_free_returns_zero`

- **源码**：`tests/test_model_routing_schemas.py:113`
- **签名**：`def test_cost_free_returns_zero()`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `ModelPricing` 结构化领域对象，并把结果记为 模型计费配置；断言辅助操作“调用 `calculate_cost_micro_usd` 完成该函数的一项辅助处理”的结果等于0；不满足就终止当前测试或流程。
```

#### `test_cost_negative_tokens_raises`

- **源码**：`tests/test_model_routing_schemas.py:127`
- **签名**：`def test_cost_negative_tokens_raises()`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `ModelPricing` 结构化领域对象，并把结果记为 模型计费配置；加载这一步需要的外部依赖。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `calculate_cost_micro_usd` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `test_token_estimator_handles_chinese_and_empty_text`

- **源码**：`tests/test_model_routing_schemas.py:144`
- **签名**：`def test_token_estimator_handles_chinese_and_empty_text()`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
断言辅助操作“调用 `estimate_text_tokens` 完成该函数的一项辅助处理”的结果不小于1；不满足就终止当前测试或流程；断言辅助操作“调用 `estimate_text_tokens` 完成该函数的一项辅助处理”的结果等于1；不满足就终止当前测试或流程。
```

#### `test_token_estimator_ascii`

- **源码**：`tests/test_model_routing_schemas.py:149`
- **签名**：`def test_token_estimator_ascii()`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
断言辅助操作“调用 `estimate_text_tokens` 完成该函数的一项辅助处理”的结果等于5；不满足就终止当前测试或流程。
```

#### `test_estimate_texts_tokens_sums`

- **源码**：`tests/test_model_routing_schemas.py:153`
- **签名**：`def test_estimate_texts_tokens_sums()`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
断言辅助操作“调用 `estimate_texts_tokens` 完成该函数的一项辅助处理”的结果等于5；不满足就终止当前测试或流程。
```

#### `test_estimate_texts_tokens_empty_raises`

- **源码**：`tests/test_model_routing_schemas.py:157`
- **签名**：`def test_estimate_texts_tokens_empty_raises()`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
加载这一步需要的外部依赖。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `estimate_texts_tokens` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `test_usage_total_tokens_must_match`

- **源码**：`tests/test_model_routing_schemas.py:164`
- **签名**：`def test_usage_total_tokens_must_match()`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中构造 `ModelUsage` 结构化领域对象，退出时自动清理资源。
```

#### `test_usage_negative_tokens_rejected`

- **源码**：`tests/test_model_routing_schemas.py:175`
- **签名**：`def test_usage_negative_tokens_rejected()`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中构造 `ModelUsage` 结构化领域对象，退出时自动清理资源。
```

#### `test_canonical_json_stable`

- **源码**：`tests/test_model_routing_schemas.py:186`
- **签名**：`def test_canonical_json_stable()`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算按字段初始化键值映射，并保存为 待处理数据；断言辅助操作“调用 `canonical_json` 完成该函数的一项辅助处理”的结果等于'{"a":2,"b":1}'；不满足就终止当前测试或流程。
```

#### `test_canonical_json_set_sorted`

- **源码**：`tests/test_model_routing_schemas.py:191`
- **签名**：`def test_canonical_json_set_sorted()`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算按字段初始化键值映射，并保存为 待处理数据；调用 `canonical_json` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果；断言当前输入内容属于阶段处理结果；不满足就终止当前测试或流程；断言当前输入内容属于阶段处理结果；不满足就终止当前测试或流程。
断言当前输入内容属于阶段处理结果；不满足就终止当前测试或流程。
```

#### `test_sha256_text_stable`

- **源码**：`tests/test_model_routing_schemas.py:199`
- **签名**：`def test_sha256_text_stable()`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
断言辅助操作“调用 `sha256_text` 计算内容身份、分数或派生结果”的结果等于辅助操作“调用 `sha256_text` 计算内容身份、分数或派生结果”的结果；不满足就终止当前测试或流程；断言辅助操作“调用 `sha256_text` 计算内容身份、分数或派生结果”的结果不等于辅助操作“调用 `sha256_text` 计算内容身份、分数或派生结果”的结果；不满足就终止当前测试或流程。
```

#### `test_sha256_value_dict`

- **源码**：`tests/test_model_routing_schemas.py:204`
- **签名**：`def test_sha256_value_dict()`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `sha256_value` 计算内容身份、分数或派生结果，并把结果记为 该调用返回的结果；调用 `sha256_value` 计算内容身份、分数或派生结果，并把结果记为 该调用返回的结果；断言当前处理结果等于当前处理结果；不满足就终止当前测试或流程。
```

#### `test_schema_forbid_extra_fields`

- **源码**：`tests/test_model_routing_schemas.py:210`
- **签名**：`def test_schema_forbid_extra_fields()`
- **作用**：在论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中构造 `ModelPricing` 结构化领域对象，退出时自动清理资源。
```

### `tests/test_research_browser_api.py`

**模块作用**：API tests for the research browser.

#### `_disable_heavy_services`

- **源码**：`tests/test_research_browser_api.py:18`
- **签名**：`def _disable_heavy_services(monkeypatch)`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，Disable project memory, knowledge base, and retention to avoid requiring a master.key or langgraph.checkpoint.sqlite in tests。该函数接收测试环境修改工具，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `monkeypatch` | `未显式标注` | pytest 提供的环境/对象替换工具，用于隔离测试副作用；不是业务输入。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
加载这一步需要的外部依赖；调用 `setattr` 完成该函数的一项辅助处理；调用 `setattr` 完成该函数的一项辅助处理；调用 `setattr` 完成该函数的一项辅助处理。
调用 `setattr` 完成该函数的一项辅助处理；调用 `setattr` 完成该函数的一项辅助处理；调用 `setattr` 完成该函数的一项辅助处理；调用 `setattr` 完成该函数的一项辅助处理。
加载这一步需要的外部依赖；调用 `setattr` 完成该函数的一项辅助处理；加载这一步需要的外部依赖；调用 `setattr` 完成该函数的一项辅助处理。
```

#### `test_research_browser_disabled_returns_404`

- **源码**：`tests/test_research_browser_api.py:59`
- **签名**：`def test_research_browser_disabled_returns_404() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，When research_browser_service is None, /v1/research routes are not registered。该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `create_api_app` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果；构造 `TestClient` 结构化领域对象，并把结果记为 外部服务客户端；从外部服务客户端读取所需的状态或领域记录，并把结果记为 结构化响应；断言状态等于404；不满足就终止当前测试或流程。
```

#### `test_research_api_requires_auth`

- **源码**：`tests/test_research_browser_api.py:70`
- **签名**：`def test_research_api_requires_auth() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，Without auth header, API returns 401/403/422/404。该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `create_api_app` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果；构造 `TestClient` 结构化领域对象，并把结果记为 外部服务客户端；调用 `post` 完成该函数的一项辅助处理，并把结果记为 结构化响应；断言状态属于{401, 403, 404, 422}；不满足就终止当前测试或流程。
```

#### `test_research_routes_not_registered_when_disabled`

- **源码**：`tests/test_research_browser_api.py:84`
- **签名**：`def test_research_routes_not_registered_when_disabled() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，Verify that /v1/research/* paths return 404 when the feature is disabled。该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `create_api_app` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果；构造 `TestClient` 结构化领域对象，并把结果记为 外部服务客户端；计算初始化顺序集合，并保存为 文件或目录路径集合。
遍历由文件或目录路径集合组成的集合或迭代器，每次把当前项记为多个解包结果，然后调用 `request` 完成该函数的一项辅助处理，并把结果记为 结构化响应；断言状态等于404，失败时附带断言说明；不满足就终止当前测试或流程。
```

### `tests/test_research_browser_authority.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_research_browser_has_no_process_execution_imports`

- **源码**：`tests/test_research_browser_authority.py:7`
- **签名**：`def test_research_browser_has_no_process_execution_imports() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合多个值形成元组，并保存为 被策略禁止的内容或操作。
遍历辅助操作产生的可迭代结果（枚举当前输入内容下符合范围的文件系统项），每次把当前项记为文件或目录路径：
    读取文件或目录路径中的文件内容，并把结果记为 数据来源标记。
    遍历由被策略禁止的内容或操作组成的集合或迭代器，每次把当前项记为测试或状态标记，然后断言测试或状态标记不属于数据来源标记，失败时附带断言说明；不满足就终止当前测试或流程。
```

#### `test_research_browser_never_calls_resource_approval`

- **源码**：`tests/test_research_browser_authority.py:20`
- **签名**：`def test_research_browser_never_calls_resource_approval() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合多个值形成元组，并保存为 被策略禁止的内容或操作。
遍历辅助操作产生的可迭代结果（枚举当前输入内容下符合范围的文件系统项），每次把当前项记为文件或目录路径：
    读取文件或目录路径中的文件内容，并把结果记为 数据来源标记。
    遍历由被策略禁止的内容或操作组成的集合或迭代器，每次把当前项记为测试或状态标记，然后断言测试或状态标记不属于数据来源标记，失败时附带断言说明；不满足就终止当前测试或流程。
```

#### `test_research_browser_has_no_shell_execution`

- **源码**：`tests/test_research_browser_authority.py:33`
- **签名**：`def test_research_browser_has_no_shell_execution() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合多个值形成元组，并保存为 被策略禁止的内容或操作。
遍历辅助操作产生的可迭代结果（枚举当前输入内容下符合范围的文件系统项），每次把当前项记为文件或目录路径：
    读取文件或目录路径中的文件内容，并把结果记为 数据来源标记。
    遍历由被策略禁止的内容或操作组成的集合或迭代器，每次把当前项记为测试或状态标记，然后断言测试或状态标记不属于数据来源标记，失败时附带断言说明；不满足就终止当前测试或流程。
```

#### `test_research_tool_has_network_read_effect_only`

- **源码**：`tests/test_research_browser_authority.py:46`
- **签名**：`def test_research_tool_has_network_read_effect_only() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
加载这一步需要的外部依赖；加载这一步需要的外部依赖；加载这一步需要的外部依赖。
定义内部类型 `FakeCollector`，用于组织当前函数的临时逻辑。
调用 `build_research_tool_definition` 组装当前阶段需要的领域对象，并把结果记为 受控工具定义；断言当前处理结果属于当前处理结果；不满足就终止当前测试或流程；断言当前输入内容属于当前处理结果；不满足就终止当前测试或流程；断言当前字段值等于'agent_read_only'；不满足就终止当前测试或流程。
```

#### `test_research_tool_has_network_read_effect_only.FakeCollector.collect`

- **源码**：`tests/test_research_browser_authority.py:52`
- **签名**：`def collect(self, request)`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收业务请求，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `request` | `未显式标注` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
加载这一步需要的外部依赖；调用 `evidence_draft` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `test_research_skill_only_declares_collect_tool`

- **源码**：`tests/test_research_browser_authority.py:64`
- **签名**：`def test_research_skill_only_declares_collect_tool() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
加载这一步需要的外部依赖；计算组合或计算已有值，并保存为 运行或工作区 Manifest的路径；将外部表示解析为结构化内容，并把结果记为 运行或工作区 Manifest；遍历并筛选输入，将整理后的结果保存为 工具集合。
断言工具集合等于['browser.collect_research_evidence']；不满足就终止当前测试或流程；断言当前输入内容属于运行或工作区 Manifest中的对应字段；不满足就终止当前测试或流程；断言运行或工作区 Manifest中的对应字段等于'proposal_only'；不满足就终止当前测试或流程。
```

### `tests/test_research_browser_catalog.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_load_policy_from_file`

- **源码**：`tests/test_research_browser_catalog.py:16`
- **签名**：`def test_load_policy_from_file(tmp_path) -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `research_policy` 完成该函数的一项辅助处理，并把结果记为 安全策略；计算组合或计算已有值，并保存为 文件或目录路径；将处理结果写入文件或目录路径指定的文件；调用 `load_research_policy` 读取或查询当前阶段需要的数据，并把结果记为 已加载结果。
断言安全策略的 SHA-256等于辅助操作“调用 `sha256_value` 计算内容身份、分数或派生结果”的结果；不满足就终止当前测试或流程；断言允许访问的主机集合等于允许访问的主机集合；不满足就终止当前测试或流程。
```

#### `test_load_policy_rejects_symlink`

- **源码**：`tests/test_research_browser_catalog.py:25`
- **签名**：`def test_load_policy_rejects_symlink(tmp_path) -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合或计算已有值，并保存为 当前处理结果；将处理结果写入当前处理结果指定的文件；计算组合或计算已有值，并保存为 当前处理结果；调用 `symlink_to` 完成该函数的一项辅助处理。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `load_research_policy` 读取或查询当前阶段需要的数据，退出时自动清理资源。
```

#### `test_load_policy_rejects_outside_root`

- **源码**：`tests/test_research_browser_catalog.py:34`
- **签名**：`def test_load_policy_rejects_outside_root(tmp_path) -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合或计算已有值，并保存为 当前处理结果；将处理结果写入当前处理结果指定的文件。
先尝试完成以下处理：
    在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `load_research_policy` 读取或查询当前阶段需要的数据，退出时自动清理资源。
无论成功还是失败，最后都要：
    调用 `unlink` 完成该函数的一项辅助处理。
```

#### `test_load_policy_rejects_missing_file`

- **源码**：`tests/test_research_browser_catalog.py:44`
- **签名**：`def test_load_policy_rejects_missing_file(tmp_path) -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `load_research_policy` 读取或查询当前阶段需要的数据，退出时自动清理资源。
```

#### `test_effective_hosts_returns_request_subset`

- **源码**：`tests/test_research_browser_catalog.py:49`
- **签名**：`def test_effective_hosts_returns_request_subset() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `research_policy` 完成该函数的一项辅助处理，并把结果记为 安全策略；构造 `LoadedResearchPolicy` 结构化领域对象，并把结果记为 已加载结果；调用 `research_request` 完成该函数的一项辅助处理，并把结果记为 业务请求；断言辅助操作“调用 `effective_hosts` 完成该函数的一项辅助处理”的结果等于('example.org')；不满足就终止当前测试或流程。
```

#### `test_effective_hosts_defaults_to_policy`

- **源码**：`tests/test_research_browser_catalog.py:60`
- **签名**：`def test_effective_hosts_defaults_to_policy() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `research_policy` 完成该函数的一项辅助处理，并把结果记为 安全策略；构造 `LoadedResearchPolicy` 结构化领域对象，并把结果记为 已加载结果；调用 `research_request` 完成该函数的一项辅助处理，并把结果记为 业务请求；断言辅助操作“调用 `effective_hosts` 完成该函数的一项辅助处理”的结果等于('example.org', 'github.com')；不满足就终止当前测试或流程。
```

#### `test_effective_hosts_rejects_outside_policy`

- **源码**：`tests/test_research_browser_catalog.py:71`
- **签名**：`def test_effective_hosts_rejects_outside_policy() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `research_policy` 完成该函数的一项辅助处理，并把结果记为 安全策略；构造 `LoadedResearchPolicy` 结构化领域对象，并把结果记为 已加载结果；调用 `research_request` 完成该函数的一项辅助处理，并把结果记为 业务请求。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `effective_hosts` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `test_effective_hosts_allows_subdomain_of_policy_host`

- **源码**：`tests/test_research_browser_catalog.py:83`
- **签名**：`def test_effective_hosts_allows_subdomain_of_policy_host() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `research_policy` 完成该函数的一项辅助处理，并把结果记为 安全策略；构造 `LoadedResearchPolicy` 结构化领域对象，并把结果记为 已加载结果；调用 `research_request` 完成该函数的一项辅助处理，并把结果记为 业务请求；断言辅助操作“调用 `effective_hosts` 完成该函数的一项辅助处理”的结果等于('sub.example.org')；不满足就终止当前测试或流程。
```

### `tests/test_research_browser_chat.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_web_citation_requires_full_identity`

- **源码**：`tests/test_research_browser_chat.py:10`
- **签名**：`def test_web_citation_requires_full_identity() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中构造 `ChatCitation` 结构化领域对象，退出时自动清理资源。
```

#### `test_web_citation_with_full_identity_succeeds`

- **源码**：`tests/test_research_browser_chat.py:20`
- **签名**：`def test_web_citation_with_full_identity_succeeds() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `evidence_pack` 完成该函数的一项辅助处理，并把结果记为 检索或映射证据包；读取论文引用证据集合中的对应字段，并保存为 论文引用证据；读取当前处理结果中的对应字段，并保存为 MCP 能力快照；构造 `ChatCitation` 结构化领域对象，并把结果记为 对话。
断言来源类型等于'web'；不满足就终止当前测试或流程；断言当前处理结果的 ID等于检索或映射证据包的 ID；不满足就终止当前测试或流程。
```

#### `test_non_web_citation_rejects_research_fields`

- **源码**：`tests/test_research_browser_chat.py:41`
- **签名**：`def test_non_web_citation_rejects_research_fields() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中构造 `ChatCitation` 结构化领域对象，退出时自动清理资源。
```

#### `test_web_citation_in_memory_body_requires_phase51`

- **源码**：`tests/test_research_browser_chat.py:51`
- **签名**：`def test_web_citation_in_memory_body_requires_phase51() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `evidence_pack` 完成该函数的一项辅助处理，并把结果记为 检索或映射证据包；读取论文引用证据集合中的对应字段，并保存为 论文引用证据；读取当前处理结果中的对应字段，并保存为 MCP 能力快照；构造 `ChatCitation` 结构化领域对象，并把结果记为 该调用返回的结果。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中构造 `ConversationMemoryBody` 结构化领域对象，退出时自动清理资源。
构造 `ConversationMemoryBody` 结构化领域对象，并把结果记为 请求正文；断言版本等于'phase51-v5'；不满足就终止当前测试或流程。
```

#### `test_old_memory_without_web_fields_still_readable`

- **源码**：`tests/test_research_browser_chat.py:84`
- **签名**：`def test_old_memory_without_web_fields_still_readable() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `ConversationMemoryBody` 结构化领域对象，并把结果记为 请求正文；断言版本等于'phase36-v1'；不满足就终止当前测试或流程。
```

#### `test_chat_context_builder_research_sources_no_reader`

- **源码**：`tests/test_research_browser_chat.py:93`
- **签名**：`def test_chat_context_builder_research_sources_no_reader() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，When research_reader is None, _research_sources returns empty list。该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
加载这一步需要的外部依赖；不执行额外操作。
```

### `tests/test_research_browser_collector.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `FakeFetcher.__init__`

- **源码**：`tests/test_research_browser_collector.py:14`
- **签名**：`def __init__(self) -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
将 当前处理结果 初始化为空列表，用来收集后续结果。
```

#### `FakeFetcher.fetch`

- **源码**：`tests/test_research_browser_collector.py:17`
- **签名**：`def fetch(self, url: str) -> FetchedDocument`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收外部论文、仓库或服务地址，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `FetchedDocument` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `url` | `str` | 资源地址；进入网络或持久化前仍需策略校验和必要的脱敏。 |

**输出**

- **Python 类型**：`FetchedDocument`
- **语义**：返回 `FetchedDocument` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
把外部论文、仓库或服务地址追加或合并到当前处理结果；计算使用固定配置或常量值，并保存为 请求正文；构造并返回 `FetchedDocument` 结构化领域对象。
```

#### `FailingFetcher.fetch`

- **源码**：`tests/test_research_browser_collector.py:32`
- **签名**：`def fetch(self, url: str) -> FetchedDocument`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收外部论文、仓库或服务地址，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `FetchedDocument` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `url` | `str` | 资源地址；进入网络或持久化前仍需策略校验和必要的脱敏。 |

**输出**

- **Python 类型**：`FetchedDocument`
- **语义**：返回 `FetchedDocument` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
拒绝继续处理并抛出 `RuntimeError`，向调用方报告输入或运行失败。
```

#### `OversizedFetcher.fetch`

- **源码**：`tests/test_research_browser_collector.py:37`
- **签名**：`def fetch(self, url: str) -> FetchedDocument`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收外部论文、仓库或服务地址，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `FetchedDocument` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `url` | `str` | 资源地址；进入网络或持久化前仍需策略校验和必要的脱敏。 |

**输出**

- **Python 类型**：`FetchedDocument`
- **语义**：返回 `FetchedDocument` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
计算组合或计算已有值，并保存为 请求正文；构造并返回 `FetchedDocument` 结构化领域对象。
```

#### `test_collector_enforces_request_host_subset`

- **源码**：`tests/test_research_browser_collector.py:50`
- **签名**：`def test_collector_enforces_request_host_subset() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `research_policy` 完成该函数的一项辅助处理，并把结果记为 安全策略；构造 `FixtureSearchProvider` 结构化领域对象，并把结果记为 该调用返回的结果；构造 `FakeFetcher` 结构化领域对象，并把结果记为 该调用返回的结果；构造 `ResearchCollector` 结构化领域对象，并把结果记为 该调用返回的结果。
调用 `collect` 完成该函数的一项辅助处理，并把结果记为 可追溯证据记录；断言当前处理结果等于['https://example.org/pstnet']；不满足就终止当前测试或流程；断言当前输入内容属于当前处理结果；不满足就终止当前测试或流程。
```

#### `test_collector_deduplicates_canonical_url`

- **源码**：`tests/test_research_browser_collector.py:82`
- **签名**：`def test_collector_deduplicates_canonical_url() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `FixtureSearchProvider` 结构化领域对象，并把结果记为 该调用返回的结果；构造 `FakeFetcher` 结构化领域对象，并把结果记为 该调用返回的结果；构造 `ResearchCollector` 结构化领域对象，并把结果记为 该调用返回的结果；调用 `collect` 完成该函数的一项辅助处理，并把结果记为 可追溯证据记录。
断言当前处理结果 的长度等于1；不满足就终止当前测试或流程。
```

#### `test_single_page_failure_does_not_block_others`

- **源码**：`tests/test_research_browser_collector.py:110`
- **签名**：`def test_single_page_failure_does_not_block_others() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `FixtureSearchProvider` 结构化领域对象，并把结果记为 该调用返回的结果；构造 `ResearchCollector` 结构化领域对象，并把结果记为 该调用返回的结果；调用 `collect` 完成该函数的一项辅助处理，并把结果记为 可追溯证据记录；断言当前处理结果 的长度不小于2；不满足就终止当前测试或流程。
断言当前处理结果 的长度等于0；不满足就终止当前测试或流程。
```

#### `test_total_bytes_exceeds_limit_terminates_collector`

- **源码**：`tests/test_research_browser_collector.py:138`
- **签名**：`def test_total_bytes_exceeds_limit_terminates_collector() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `FixtureSearchProvider` 结构化领域对象，并把结果记为 该调用返回的结果；构造 `ResearchCollector` 结构化领域对象，并把结果记为 该调用返回的结果。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `collect` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `test_citation_binds_snapshot_and_block_hash`

- **源码**：`tests/test_research_browser_collector.py:159`
- **签名**：`def test_citation_binds_snapshot_and_block_hash() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `FixtureSearchProvider` 结构化领域对象，并把结果记为 该调用返回的结果；构造 `FakeFetcher` 结构化领域对象，并把结果记为 该调用返回的结果；构造 `ResearchCollector` 结构化领域对象，并把结果记为 该调用返回的结果；调用 `collect` 完成该函数的一项辅助处理，并把结果记为 可追溯证据记录。
断言论文引用证据集合 的长度不小于1；不满足就终止当前测试或流程；读取论文引用证据集合中的对应字段，并保存为 论文引用证据；读取当前处理结果中的对应字段，并保存为 MCP 能力快照；断言MCP 能力快照的 ID等于MCP 能力快照的 ID；不满足就终止当前测试或流程。
断言当前处理结果的 SHA-256等于请求正文的 SHA-256；不满足就终止当前测试或流程；调用 `next` 完成该函数的一项辅助处理，并把结果记为 论文原文块；断言当前处理结果等于待处理文本中的对应字段；不满足就终止当前测试或流程。
```

#### `test_github_default_branch_does_not_form_candidate`

- **源码**：`tests/test_research_browser_collector.py:187`
- **签名**：`def test_github_default_branch_does_not_form_candidate() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `FixtureSearchProvider` 结构化领域对象，并把结果记为 该调用返回的结果；构造 `FakeFetcher` 结构化领域对象，并把结果记为 该调用返回的结果；构造 `ResearchCollector` 结构化领域对象，并把结果记为 该调用返回的结果；调用 `collect` 完成该函数的一项辅助处理，并把结果记为 可追溯证据记录。
断言资源集合 的长度等于0；不满足就终止当前测试或流程。
```

#### `test_github_exact_commit_forms_candidate`

- **源码**：`tests/test_research_browser_collector.py:211`
- **签名**：`def test_github_exact_commit_forms_candidate() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合或计算已有值，并保存为 当前处理结果；构造 `FixtureSearchProvider` 结构化领域对象，并把结果记为 该调用返回的结果；构造 `FakeFetcher` 结构化领域对象，并把结果记为 该调用返回的结果；构造 `ResearchCollector` 结构化领域对象，并把结果记为 该调用返回的结果。
调用 `collect` 完成该函数的一项辅助处理，并把结果记为 可追溯证据记录；断言资源集合 的长度等于1；不满足就终止当前测试或流程；读取资源集合中的对应字段，并保存为 待审核的 MCP 能力候选；断言业务类别等于'git_repository'；不满足就终止当前测试或流程。
断言期望等于当前处理结果；不满足就终止当前测试或流程；断言当前处理结果是真；不满足就终止当前测试或流程。
```

#### `test_pdf_candidate_has_body_hash`

- **源码**：`tests/test_research_browser_collector.py:240`
- **签名**：`def test_pdf_candidate_has_body_hash() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算使用固定配置或常量值，并保存为 PDF；构造 `FixtureSearchProvider` 结构化领域对象，并把结果记为 该调用返回的结果。
定义内部类型 `PdfFetcher`，用于组织当前函数的临时逻辑。
构造 `ResearchCollector` 结构化领域对象，并把结果记为 该调用返回的结果；调用 `collect` 完成该函数的一项辅助处理，并把结果记为 可追溯证据记录。
遍历当前可迭代输入，每次把当前项记为待审核的 MCP 能力候选：
    如果业务类别等于'paper_pdf'，就断言调用方看到的旧 SHA-256不为空；不满足就终止当前测试或流程；断言当前处理结果是真；不满足就终止当前测试或流程。
```

#### `test_pdf_candidate_has_body_hash.PdfFetcher.fetch`

- **源码**：`tests/test_research_browser_collector.py:254`
- **签名**：`def fetch(self, url: str) -> FetchedDocument`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收外部论文、仓库或服务地址，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `FetchedDocument` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `url` | `str` | 资源地址；进入网络或持久化前仍需策略校验和必要的脱敏。 |

**输出**

- **Python 类型**：`FetchedDocument`
- **语义**：返回 `FetchedDocument` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `FetchedDocument` 结构化领域对象。
```

### `tests/test_research_browser_extractors.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_html_drops_script_style_form`

- **源码**：`tests/test_research_browser_extractors.py:12`
- **签名**：`def test_html_drops_script_style_form() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算使用固定配置或常量值，并保存为 请求正文；调用 `extract_html` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果；遍历并筛选输入，将整理后的结果保存为 待处理文本集合；断言“检查由待处理文本集合组成的集合或迭代器中是否存在满足“当前输入内容属于当前处理结果”的项”后未得到肯定结果；不满足就终止当前测试或流程。
断言“检查由待处理文本集合组成的集合或迭代器中是否存在满足“当前输入内容属于当前处理结果”的项”后未得到肯定结果；不满足就终止当前测试或流程；断言由待处理文本集合组成的集合或迭代器中存在满足“当前输入内容属于当前处理结果”的项；不满足就终止当前测试或流程；断言由待处理文本集合组成的集合或迭代器中存在满足“当前输入内容属于当前处理结果”的项；不满足就终止当前测试或流程；断言文档或章节标题等于'Test'；不满足就终止当前测试或流程。
```

#### `test_html_preserves_heading_path`

- **源码**：`tests/test_research_browser_extractors.py:35`
- **签名**：`def test_html_preserves_heading_path() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算使用固定配置或常量值，并保存为 请求正文；调用 `extract_html` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果；遍历并筛选输入，将整理后的结果保存为 当前处理结果；断言当前处理结果 的长度不小于2；不满足就终止当前测试或流程。
断言当前输入内容属于当前处理结果的路径；不满足就终止当前测试或流程；断言当前输入内容属于当前处理结果的路径；不满足就终止当前测试或流程。
```

#### `test_html_block_count_limited`

- **源码**：`tests/test_research_browser_extractors.py:51`
- **签名**：`def test_html_block_count_limited() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算使用固定配置或常量值，并保存为 请求正文。
遍历限定范围内的序列，每次把当前项记为当前处理结果，然后将新的计算结果累加或合并到请求正文。
将新的计算结果累加或合并到请求正文；调用 `extract_html` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果；断言论文原文块集合 的长度不大于5；不满足就终止当前测试或流程。
```

#### `test_plain_text_splits_paragraphs`

- **源码**：`tests/test_research_browser_extractors.py:60`
- **签名**：`def test_plain_text_splits_paragraphs() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算使用固定配置或常量值，并保存为 请求正文；调用 `extract_plain_text` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果；断言论文原文块集合 的长度等于3；不满足就终止当前测试或流程；断言待处理文本等于'First paragraph.'；不满足就终止当前测试或流程。
断言待处理文本等于'Second paragraph.'；不满足就终止当前测试或流程。
```

#### `test_plain_text_removes_nul`

- **源码**：`tests/test_research_browser_extractors.py:68`
- **签名**：`def test_plain_text_removes_nul() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算使用固定配置或常量值，并保存为 请求正文；调用 `extract_plain_text` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果；断言当前输入内容不属于待处理文本；不满足就终止当前测试或流程。
```

#### `test_html_rejects_empty`

- **源码**：`tests/test_research_browser_extractors.py:74`
- **签名**：`def test_html_rejects_empty() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `extract_html` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `test_plain_text_rejects_empty`

- **源码**：`tests/test_research_browser_extractors.py:79`
- **签名**：`def test_plain_text_rejects_empty() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `extract_plain_text` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `test_unknown_media_type_rejected`

- **源码**：`tests/test_research_browser_extractors.py:84`
- **签名**：`def test_unknown_media_type_rejected() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `extract_document` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `test_same_input_produces_same_ids`

- **源码**：`tests/test_research_browser_extractors.py:94`
- **签名**：`def test_same_input_produces_same_ids() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算使用固定配置或常量值，并保存为 请求正文；调用 `extract_html` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `extract_html` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；断言论文原文块的 ID等于论文原文块的 ID；不满足就终止当前测试或流程。
断言规范化后的文本的文本的 SHA-256等于规范化后的文本的文本的 SHA-256；不满足就终止当前测试或流程；断言规范化后的文本的文本的 SHA-256等于辅助操作“调用 `sha256_text` 计算内容身份、分数或派生结果”的结果；不满足就终止当前测试或流程。
```

#### `test_html_block_text_capped`

- **源码**：`tests/test_research_browser_extractors.py:105`
- **签名**：`def test_html_block_text_capped() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合或计算已有值，并保存为 当前处理结果的文本；将结构化内容序列化或编码为可传输表示，并把结果记为 请求正文；调用 `extract_html` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果；断言待处理文本 的长度不大于8000；不满足就终止当前测试或流程。
```

#### `test_pdf_extraction`

- **源码**：`tests/test_research_browser_extractors.py:112`
- **签名**：`def test_pdf_extraction(tmp_path) -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `importorskip` 完成该函数的一项辅助处理；加载这一步需要的外部依赖；调用 `open` 完成该函数的一项辅助处理，并把结果记为 模块或函数文档文本；调用 `new_page` 完成该函数的一项辅助处理，并把结果记为 论文页码。
调用 `insert_text` 持久化或更新当前领域数据；调用 `tobytes` 完成该函数的一项辅助处理，并把结果记为 PDF的字节内容；关闭模块或函数文档文本并释放相关资源；调用 `extract_document` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果。
断言来源类别等于'pdf'；不满足就终止当前测试或流程；断言论文原文块集合 的长度不小于1；不满足就终止当前测试或流程；断言当前输入内容属于待处理文本；不满足就终止当前测试或流程。
```

#### `test_pdf_rejects_empty_body`

- **源码**：`tests/test_research_browser_extractors.py:133`
- **签名**：`def test_pdf_rejects_empty_body() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `importorskip` 完成该函数的一项辅助处理；加载这一步需要的外部依赖；调用 `open` 完成该函数的一项辅助处理，并把结果记为 模块或函数文档文本；调用 `new_page` 完成该函数的一项辅助处理。
调用 `tobytes` 完成该函数的一项辅助处理，并把结果记为 PDF的字节内容；关闭模块或函数文档文本并释放相关资源。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `extract_document` 完成该函数的一项辅助处理，退出时自动清理资源。
```

### `tests/test_research_browser_fetcher.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `build_fetcher`

- **源码**：`tests/test_research_browser_fetcher.py:29`
- **签名**：`def build_fetcher(transport: FakeTransport, **policy_updates)`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收外部资源传输端口、策略集合，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `transport` | `FakeTransport` | 外部资源传输端口；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `**policy_updates` | `未显式标注` | 额外关键字参数映射。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
调用 `research_policy` 完成该函数的一项辅助处理，并把结果记为 安全策略；构造 `BoundedResearchFetcher` 结构化领域对象，并把结果记为 该调用返回的结果；计算使用固定配置或常量值，并保存为 当前处理结果；返回前一步处理得到的结果。
```

#### `test_target_rejects_private_dns_result`

- **源码**：`tests/test_research_browser_fetcher.py:42`
- **签名**：`def test_target_rejects_private_dns_result() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `validate_research_target` 校验当前输入或状态，退出时自动清理资源。
```

#### `test_target_rejects_host_outside_allowlist`

- **源码**：`tests/test_research_browser_fetcher.py:51`
- **签名**：`def test_target_rejects_host_outside_allowlist() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `validate_research_target` 校验当前输入或状态，退出时自动清理资源。
```

#### `test_target_rejects_ip_literal`

- **源码**：`tests/test_research_browser_fetcher.py:60`
- **签名**：`def test_target_rejects_ip_literal() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `validate_research_target` 校验当前输入或状态，退出时自动清理资源。
```

#### `test_fetch_revalidates_redirect_destination`

- **源码**：`tests/test_research_browser_fetcher.py:69`
- **签名**：`def test_fetch_revalidates_redirect_destination() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `FakeTransport` 结构化领域对象，并把结果记为 外部资源传输端口。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `fetch` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `test_fetch_rejects_redirect_without_location`

- **源码**：`tests/test_research_browser_fetcher.py:81`
- **签名**：`def test_fetch_rejects_redirect_without_location() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `FakeTransport` 结构化领域对象，并把结果记为 外部资源传输端口。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `fetch` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `test_fetch_rejects_too_many_redirects`

- **源码**：`tests/test_research_browser_fetcher.py:93`
- **签名**：`def test_fetch_rejects_too_many_redirects() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `FakeTransport` 结构化领域对象，并把结果记为 外部资源传输端口。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `fetch` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `test_fetch_enforces_streamed_byte_limit`

- **源码**：`tests/test_research_browser_fetcher.py:111`
- **签名**：`def test_fetch_enforces_streamed_byte_limit() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `FakeTransport` 结构化领域对象，并把结果记为 外部资源传输端口。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `fetch` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `test_fetch_rejects_declared_content_length`

- **源码**：`tests/test_research_browser_fetcher.py:127`
- **签名**：`def test_fetch_rejects_declared_content_length() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `FakeTransport` 结构化领域对象，并把结果记为 外部资源传输端口。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `fetch` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `test_fetch_rejects_unknown_media_type`

- **源码**：`tests/test_research_browser_fetcher.py:143`
- **签名**：`def test_fetch_rejects_unknown_media_type() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `FakeTransport` 结构化领域对象，并把结果记为 外部资源传输端口。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `fetch` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `test_fetch_rejects_fake_pdf`

- **源码**：`tests/test_research_browser_fetcher.py:159`
- **签名**：`def test_fetch_rejects_fake_pdf() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `FakeTransport` 结构化领域对象，并把结果记为 外部资源传输端口。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `fetch` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `test_fetch_maps_429_to_retryable_transport_error`

- **源码**：`tests/test_research_browser_fetcher.py:175`
- **签名**：`def test_fetch_maps_429_to_retryable_transport_error() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `FakeTransport` 结构化领域对象，并把结果记为 外部资源传输端口。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `fetch` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `test_robots_denial_prevents_document_request`

- **源码**：`tests/test_research_browser_fetcher.py:187`
- **签名**：`def test_robots_denial_prevents_document_request() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `FakeTransport` 结构化领域对象，并把结果记为 外部资源传输端口；调用 `research_policy` 完成该函数的一项辅助处理，并把结果记为 安全策略；构造 `BoundedResearchFetcher` 结构化领域对象，并把结果记为 该调用返回的结果；计算使用固定配置或常量值，并保存为 当前处理结果。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `fetch` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `test_fetch_returns_valid_document`

- **源码**：`tests/test_research_browser_fetcher.py:212`
- **签名**：`def test_fetch_returns_valid_document() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算使用固定配置或常量值，并保存为 请求正文；构造 `FakeTransport` 结构化领域对象，并把结果记为 外部资源传输端口；调用 `fetch` 完成该函数的一项辅助处理，并把结果记为 模块或函数文档文本；断言Artifact 媒体类型等于'text/html'；不满足就终止当前测试或流程。
断言请求正文等于请求正文；不满足就终止当前测试或流程；断言规范化等于'https://example.org/page'；不满足就终止当前测试或流程；断言当前处理结果等于('https://example.org/page')；不满足就终止当前测试或流程；断言状态等于'allowed'；不满足就终止当前测试或流程。
```

#### `test_fetch_follows_redirect`

- **源码**：`tests/test_research_browser_fetcher.py:233`
- **签名**：`def test_fetch_follows_redirect() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算使用固定配置或常量值，并保存为 请求正文；构造 `FakeTransport` 结构化领域对象，并把结果记为 外部资源传输端口；调用 `fetch` 完成该函数的一项辅助处理，并把结果记为 模块或函数文档文本；断言规范化等于'https://example.org/full'；不满足就终止当前测试或流程。
断言当前处理结果 的长度等于2；不满足就终止当前测试或流程。
```

### `tests/test_research_browser_golden.py`

**模块作用**：Golden evaluation for the restricted research browser.

#### `PassThroughRedactor.redact_text`

- **源码**：`tests/test_research_browser_golden.py:49`
- **签名**：`def redact_text(self, value: str, *, max_chars: int) -> str`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前字段值、最大字符数，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `value` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |
| `max_chars` | `int` | 名为 `max_chars` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
返回当前字段值中的对应字段的当前值。
```

#### `FakeGateway.__init__`

- **源码**：`tests/test_research_browser_golden.py:56`
- **签名**：`def __init__(self, *, unknown_citation: bool = False) -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `unknown_citation` | `bool` | 布尔条件或能力开关，用于控制流程分支。；默认 假 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 当前处理结果 分别保存到同名实例字段；将 工具或模型调用记录集合 初始化为空列表，用来收集后续结果。
```

#### `FakeGateway.invoke_structured`

- **源码**：`tests/test_research_browser_golden.py:60`
- **签名**：`def invoke_structured(self, **kwargs)`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收函数关键字参数映射，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `**kwargs` | `未显式标注` | 额外关键字参数映射。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
把函数关键字参数映射追加或合并到工具或模型调用记录集合；从函数关键字参数映射读取所需的状态或领域记录，并把结果记为 证据集合。
如果当前处理结果有值或为真：
    构造 `ResearchSynthesisDraft` 结构化领域对象，并把结果记为 草稿对象。
否则：
    加载这一步需要的外部依赖；从函数关键字参数映射读取所需的状态或领域记录，并把结果记为 发给模型的结构化提示；调用 `search` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
    如果当前处理结果有值或为真，就构造 `ResearchSynthesisDraft` 结构化领域对象，并把结果记为 草稿对象；否则构造 `ResearchSynthesisDraft` 结构化领域对象，并把结果记为 草稿对象。
构造并返回 `SimpleNamespace` 结构化领域对象。
```

#### `FakeGatewayBudgetDenied.invoke_structured`

- **源码**：`tests/test_research_browser_golden.py:93`
- **签名**：`def invoke_structured(self, **kwargs)`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收函数关键字参数映射，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `**kwargs` | `未显式标注` | 额外关键字参数映射。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
加载这一步需要的外部依赖；拒绝继续处理并抛出 `ModelBudgetExceeded`，向调用方报告输入或运行失败。
```

#### `_html_body`

- **源码**：`tests/test_research_browser_golden.py:99`
- **签名**：`def _html_body(title: str, paragraphs: list[str]) -> bytes`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收文档或章节标题、当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `bytes` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `title` | `str` | 论文/文档章节标题；用于建立可检索的章节身份和展示文本。 |
| `paragraphs` | `list[str]` | `list[str]` 元素集合；元素代表的业务对象由参数名 `paragraphs` 和调用位置确定。 |

**输出**

- **Python 类型**：`bytes`
- **语义**：返回 `bytes` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
计算初始化顺序集合，并保存为 拆分后的文本或路径片段集合。
遍历由当前处理结果组成的集合或迭代器，每次把当前项记为当前处理结果，然后把新的处理结果追加或合并到拆分后的文本或路径片段集合。
把新的处理结果追加或合并到拆分后的文本或路径片段集合；调用 `join` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `_build_collector`

- **源码**：`tests/test_research_browser_golden.py:107`
- **签名**：`def _build_collector(search_hits: list[ProviderSearchHit], page_responses: dict[str, list[FakeResponse]], allowed_hosts: tuple[str, ...], robots: 未显式标注, policy_updates: dict | None) -> ResearchCollector`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前处理结果、页码集合、允许访问的主机集合、当前处理结果等输入，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `ResearchCollector` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `search_hits` | `list[ProviderSearchHit]` | `list[ProviderSearchHit]` 元素集合；元素代表的业务对象由参数名 `search_hits` 和调用位置确定。 |
| `page_responses` | `dict[str, list[FakeResponse]]` | 前序调用产生的结构化响应、结果或执行结论，供当前函数继续判断或投影。 |
| `allowed_hosts` | `tuple[str, ...]` | 允许访问的主机集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 ('example.org') |
| `robots` | `未显式标注` | 名为 `robots` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。；默认 空值 |
| `policy_updates` | `dict | None` | 名为 `policy_updates` 的 `dict | None` 领域输入；用于当前函数的业务处理，具体约束见校验分支。；默认 空值 |

**输出**

- **Python 类型**：`ResearchCollector`
- **语义**：返回 `ResearchCollector` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
计算计算当前表达式的结果，并保存为 策略集合；调用 `research_policy` 完成该函数的一项辅助处理，并把结果记为 安全策略；构造 `FakeTransport` 结构化领域对象，并把结果记为 外部资源传输端口；构造 `BoundedResearchFetcher` 结构化领域对象，并把结果记为 该调用返回的结果。
计算使用固定配置或常量值，并保存为 当前处理结果；构造并返回 `ResearchCollector` 结构化领域对象。
```

#### `_load_cases`

- **源码**：`tests/test_research_browser_golden.py:134`
- **签名**：`def _load_cases() -> list[dict]`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`list[dict]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
将外部表示解析为结构化内容，并返回处理结果。
```

#### `test_golden_case`

- **源码**：`tests/test_research_browser_golden.py:139`
- **签名**：`def test_golden_case(case: dict) -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收评测用例，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `case` | `dict` | 测试夹具或评测用例对象；提供场景数据和受控依赖，不是生产业务输入。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
读取评测用例中的对应字段，并保存为 评测用例的 ID；从评测用例读取所需的状态或领域记录，并把结果记为 键；将 检索命中结果 初始化为空列表，用来收集后续结果；将 页码集合 初始化为空映射，用来收集后续结果。
如果当前输入内容属于键，就计算使用固定配置或常量值，并保存为 外部论文、仓库或服务地址；调用 `_html_body` 完成该函数的一项辅助处理，并把结果记为 请求正文；把新的处理结果追加或合并到检索命中结果；计算初始化顺序集合，并保存为 页码集合中的对应字段。
如果当前输入内容属于键，就计算使用固定配置或常量值，并保存为 外部论文、仓库或服务地址；调用 `_html_body` 完成该函数的一项辅助处理，并把结果记为 请求正文；把新的处理结果追加或合并到检索命中结果；计算初始化顺序集合，并保存为 页码集合中的对应字段。
如果当前输入内容属于键，就计算使用固定配置或常量值，并保存为 外部论文、仓库或服务地址；把新的处理结果追加或合并到检索命中结果；计算初始化顺序集合，并保存为 页码集合中的对应字段。
如果当前输入内容属于键，就计算使用固定配置或常量值，并保存为 外部论文、仓库或服务地址；把新的处理结果追加或合并到检索命中结果；计算初始化顺序集合，并保存为 页码集合中的对应字段。
如果当前输入内容属于键，就计算使用固定配置或常量值，并保存为 外部论文、仓库或服务地址；把新的处理结果追加或合并到检索命中结果；计算初始化顺序集合，并保存为 页码集合中的对应字段。
如果当前输入内容属于键，就计算使用固定配置或常量值，并保存为 外部论文、仓库或服务地址；调用 `_html_body` 完成该函数的一项辅助处理，并把结果记为 请求正文；把新的处理结果追加或合并到检索命中结果；计算初始化顺序集合，并保存为 页码集合中的对应字段。
如果当前输入内容属于键：
    计算组合或计算已有值，并保存为 当前处理结果；计算根据字段和固定文本生成格式化文本，并保存为 外部论文、仓库或服务地址；调用 `_html_body` 完成该函数的一项辅助处理，并把结果记为 请求正文；把新的处理结果追加或合并到检索命中结果。
    计算初始化顺序集合，并保存为 页码集合中的对应字段。
计算根据条件从两个候选结果中选择一个，并保存为 当前处理结果；构造临时集合、映射或轻量领域对象，并把结果记为 允许访问的主机集合；将 策略集合 初始化为空映射，用来收集后续结果。
如果当前输入内容属于键，就计算按字段初始化键值映射，并保存为 策略集合。
调用 `_build_collector` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果。
如果辅助操作“从评测用例读取所需的状态或领域记录”的结果等于'RESEARCH_TOTAL_BYTES_EXCEEDED'：
    加载这一步需要的外部依赖。
    在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `collect` 完成该函数的一项辅助处理，退出时自动清理资源。
    结束当前函数，不返回业务值。
调用 `collect` 完成该函数的一项辅助处理，并把结果记为 可追溯证据记录。
遍历当前可迭代输入，每次把当前项记为论文引用证据，然后调用 `next` 完成该函数的一项辅助处理，并把结果记为 MCP 能力快照；断言当前处理结果的 SHA-256等于请求正文的 SHA-256；不满足就终止当前测试或流程；调用 `next` 完成该函数的一项辅助处理，并把结果记为 论文原文块；断言当前处理结果等于待处理文本中的对应字段；不满足就终止当前测试或流程。
如果当前输入内容属于评测用例，就断言资源集合 的长度等于评测用例中的对应字段；不满足就终止当前测试或流程。
如果当前输入内容属于评测用例，就断言当前可迭代输入中存在满足“业务类别等于评测用例中的对应字段”的项；不满足就终止当前测试或流程。
如果当前输入内容属于评测用例，就断言当前可迭代输入中存在满足“评测用例中的对应字段属于当前处理结果”的项；不满足就终止当前测试或流程。
如果当前输入内容属于评测用例：
    如果评测用例中的对应字段等于'insufficient_evidence'：
        如果“论文引用证据集合有值或为真”不成立，就不执行额外操作；否则构造 `FakeGateway` 结构化领域对象，并把结果记为 外部服务网关；构造 `ResearchSynthesizer` 结构化领域对象，并把结果记为 该调用返回的结果；调用 `synthesize` 完成该函数的一项辅助处理，并把结果记为 MCP 评测或运行报告；断言状态属于('insufficient_evidence', 'succeeded', 'evidence_only')；不满足就终止当前测试或流程。
    否则：
        如果评测用例中的对应字段等于'succeeded'：
            构造 `FakeGateway` 结构化领域对象，并把结果记为 外部服务网关；构造 `ResearchSynthesizer` 结构化领域对象，并把结果记为 该调用返回的结果。
            如果论文引用证据集合有值或为真：
                调用 `synthesize` 完成该函数的一项辅助处理，并把结果记为 MCP 评测或运行报告；断言状态等于'succeeded'；不满足就终止当前测试或流程。
                如果当前输入内容属于评测用例：
                    计算根据条件从两个候选结果中选择一个，并保存为 发给模型的结构化提示。
                    遍历当前可迭代输入，每次把当前项记为被策略禁止的内容或操作，然后不执行额外操作。
        否则：
            如果评测用例中的对应字段等于'evidence_only'：
                构造 `FakeGateway` 结构化领域对象，并把结果记为 外部服务网关；构造 `ResearchSynthesizer` 结构化领域对象，并把结果记为 该调用返回的结果。
                如果论文引用证据集合有值或为真：
                    加载这一步需要的外部依赖。
                    在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `synthesize` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `test_prompt_injection_evidence_is_marked_untrusted`

- **源码**：`tests/test_research_browser_golden.py:375`
- **签名**：`def test_prompt_injection_evidence_is_marked_untrusted() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，Verify that injected text is carried as untrusted data in the synthesis prompt。该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算使用固定配置或常量值，并保存为 外部论文、仓库或服务地址；调用 `_html_body` 完成该函数的一项辅助处理，并把结果记为 请求正文；计算初始化顺序集合，并保存为 检索命中结果；计算按字段初始化键值映射，并保存为 结构化响应集合。
调用 `_build_collector` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果；调用 `collect` 完成该函数的一项辅助处理，并把结果记为 可追溯证据记录；构造 `FakeGateway` 结构化领域对象，并把结果记为 外部服务网关；构造 `ResearchSynthesizer` 结构化领域对象，并把结果记为 该调用返回的结果。
如果论文引用证据集合有值或为真，就调用 `synthesize` 完成该函数的一项辅助处理；读取工具或模型调用记录集合中的对应字段中的对应字段，并保存为 发给模型的结构化提示；断言当前输入内容属于发给模型的结构化提示；不满足就终止当前测试或流程；断言当前输入内容属于发给模型的结构化提示 或 当前输入内容属于辅助操作“对发给模型的结构化提示中的文本执行规范化或拆分”的结果；不满足就终止当前测试或流程。
```

### `tests/test_research_browser_identity.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_url_canonicalization_removes_fragment_and_tracking`

- **源码**：`tests/test_research_browser_identity.py:14`
- **签名**：`def test_url_canonicalization_removes_fragment_and_tracking() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
断言辅助操作“调用 `canonicalize_research_url` 完成该函数的一项辅助处理”的结果等于'https://example.org/paper?id=42'；不满足就终止当前测试或流程。
```

#### `test_url_canonicalization_rejects_unsafe_shapes`

- **源码**：`tests/test_research_browser_identity.py:30`
- **签名**：`def test_url_canonicalization_rejects_unsafe_shapes(url: str) -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收外部论文、仓库或服务地址，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `url` | `str` | 资源地址；进入网络或持久化前仍需策略校验和必要的脱敏。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `canonicalize_research_url` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `test_host_matches_exact_and_subdomain`

- **源码**：`tests/test_research_browser_identity.py:35`
- **签名**：`def test_host_matches_exact_and_subdomain() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
断言“调用 `host_matches` 完成该函数的一项辅助处理”后得到肯定结果；不满足就终止当前测试或流程；断言“调用 `host_matches` 完成该函数的一项辅助处理”后得到肯定结果；不满足就终止当前测试或流程；断言“调用 `host_matches` 完成该函数的一项辅助处理”后未得到肯定结果；不满足就终止当前测试或流程；断言“调用 `host_matches` 完成该函数的一项辅助处理”后未得到肯定结果；不满足就终止当前测试或流程。
```

#### `test_safe_search_text_normalizes_whitespace`

- **源码**：`tests/test_research_browser_identity.py:42`
- **签名**：`def test_safe_search_text_normalizes_whitespace() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
断言辅助操作“调用 `safe_search_text` 完成该函数的一项辅助处理”的结果等于'hello world'；不满足就终止当前测试或流程。
```

#### `test_safe_search_text_rejects_empty`

- **源码**：`tests/test_research_browser_identity.py:46`
- **签名**：`def test_safe_search_text_rejects_empty() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `safe_search_text` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `test_safe_search_text_rejects_control_chars`

- **源码**：`tests/test_research_browser_identity.py:51`
- **签名**：`def test_safe_search_text_rejects_control_chars() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `safe_search_text` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `test_stable_id_is_deterministic`

- **源码**：`tests/test_research_browser_identity.py:56`
- **签名**：`def test_stable_id_is_deterministic() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
断言辅助操作“调用 `stable_id` 完成该函数的一项辅助处理”的结果等于辅助操作“调用 `stable_id` 完成该函数的一项辅助处理”的结果；不满足就终止当前测试或流程。
```

#### `test_stable_id_changes_with_input`

- **源码**：`tests/test_research_browser_identity.py:60`
- **签名**：`def test_stable_id_changes_with_input() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
断言辅助操作“调用 `stable_id` 完成该函数的一项辅助处理”的结果不等于辅助操作“调用 `stable_id` 完成该函数的一项辅助处理”的结果；不满足就终止当前测试或流程。
```

#### `test_sha256_text_is_hex_64`

- **源码**：`tests/test_research_browser_identity.py:64`
- **签名**：`def test_sha256_text_is_hex_64() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `sha256_text` 计算内容身份、分数或派生结果，并把结果记为 阶段处理结果；断言阶段处理结果 的长度等于64；不满足就终止当前测试或流程；断言由阶段处理结果组成的集合或迭代器中每一项都满足“当前处理结果属于'0123456789abcdef'”的项；不满足就终止当前测试或流程。
```

#### `test_sha256_value_sorts_keys`

- **源码**：`tests/test_research_browser_identity.py:70`
- **签名**：`def test_sha256_value_sorts_keys() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
断言辅助操作“调用 `sha256_value` 计算内容身份、分数或派生结果”的结果等于辅助操作“调用 `sha256_value` 计算内容身份、分数或派生结果”的结果；不满足就终止当前测试或流程。
```

### `tests/test_research_browser_repository.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_submit_and_get`

- **源码**：`tests/test_research_browser_repository.py:15`
- **签名**：`def test_submit_and_get(tmp_path) -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `SqliteResearchRepository` 结构化领域对象，并把结果记为 代码仓库；调用 `initialize` 完成该函数的一项辅助处理；调用 `research_request` 完成该函数的一项辅助处理，并把结果记为 业务请求；调用 `submit` 完成该函数的一项辅助处理，并把结果记为 多个解包结果。
断言已创建记录是真；不满足就终止当前测试或流程；断言当前状态等于'submitted'；不满足就终止当前测试或流程；断言记录版本号等于0；不满足就终止当前测试或流程；从代码仓库读取所需的状态或领域记录，并把结果记为 该调用返回的结果。
断言当前处理结果的 ID等于当前处理结果的 ID；不满足就终止当前测试或流程。
```

#### `test_idempotent_submit_returns_same_record`

- **源码**：`tests/test_research_browser_repository.py:34`
- **签名**：`def test_idempotent_submit_returns_same_record(tmp_path) -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `SqliteResearchRepository` 结构化领域对象，并把结果记为 代码仓库；调用 `initialize` 完成该函数的一项辅助处理；调用 `research_request` 完成该函数的一项辅助处理，并把结果记为 业务请求；调用 `submit` 完成该函数的一项辅助处理，并把结果记为 多个解包结果。
调用 `submit` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；断言当前处理结果是真；不满足就终止当前测试或流程；断言当前处理结果是假；不满足就终止当前测试或流程；断言当前处理结果的 ID等于当前处理结果的 ID；不满足就终止当前测试或流程。
```

#### `test_same_key_different_request_raises_conflict`

- **源码**：`tests/test_research_browser_repository.py:59`
- **签名**：`def test_same_key_different_request_raises_conflict(tmp_path) -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `SqliteResearchRepository` 结构化领域对象，并把结果记为 代码仓库；调用 `initialize` 完成该函数的一项辅助处理；调用 `research_request` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `submit` 完成该函数的一项辅助处理。
调用 `research_request` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `submit` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `test_start_requires_submitted_status`

- **源码**：`tests/test_research_browser_repository.py:83`
- **签名**：`def test_start_requires_submitted_status(tmp_path) -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `SqliteResearchRepository` 结构化领域对象，并把结果记为 代码仓库；调用 `initialize` 完成该函数的一项辅助处理；调用 `research_request` 完成该函数的一项辅助处理，并把结果记为 业务请求；调用 `submit` 完成该函数的一项辅助处理，并把结果记为 多个解包结果。
调用 `start` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；断言当前状态等于'running'；不满足就终止当前测试或流程；断言租约不为空；不满足就终止当前测试或流程。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `start` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `test_complete_requires_current_lease`

- **源码**：`tests/test_research_browser_repository.py:114`
- **签名**：`def test_complete_requires_current_lease(tmp_path) -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `SqliteResearchRepository` 结构化领域对象，并把结果记为 代码仓库；调用 `initialize` 完成该函数的一项辅助处理；调用 `research_request` 完成该函数的一项辅助处理，并把结果记为 业务请求；调用 `request_sha256` 计算内容身份、分数或派生结果，并把结果记为 请求内容 Hash。
调用 `submit` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；调用 `start` 完成该函数的一项辅助处理。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `complete` 完成该函数的一项辅助处理，退出时自动清理资源。
断言前一步操作返回对象的当前状态等于'running'；不满足就终止当前测试或流程。
```

#### `test_complete_succeeds_with_correct_lease`

- **源码**：`tests/test_research_browser_repository.py:147`
- **签名**：`def test_complete_succeeds_with_correct_lease(tmp_path) -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `SqliteResearchRepository` 结构化领域对象，并把结果记为 代码仓库；调用 `initialize` 完成该函数的一项辅助处理；调用 `research_request` 完成该函数的一项辅助处理，并把结果记为 业务请求；调用 `request_sha256` 计算内容身份、分数或派生结果，并把结果记为 请求内容 Hash。
调用 `submit` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；计算组合或计算已有值，并保存为 任务租约记录；调用 `start` 完成该函数的一项辅助处理；调用 `evidence_pack` 完成该函数的一项辅助处理，并把结果记为 检索或映射证据包。
调用 `complete` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；断言当前状态等于'succeeded'；不满足就终止当前测试或流程；断言检索或映射证据包的 ID不为空；不满足就终止当前测试或流程；断言租约为空；不满足就终止当前测试或流程。
```

#### `test_fail_requires_current_lease`

- **源码**：`tests/test_research_browser_repository.py:183`
- **签名**：`def test_fail_requires_current_lease(tmp_path) -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `SqliteResearchRepository` 结构化领域对象，并把结果记为 代码仓库；调用 `initialize` 完成该函数的一项辅助处理；调用 `research_request` 完成该函数的一项辅助处理，并把结果记为 业务请求；调用 `submit` 完成该函数的一项辅助处理，并把结果记为 多个解包结果。
调用 `start` 完成该函数的一项辅助处理。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `fail` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `test_cancel_rejected_when_running`

- **源码**：`tests/test_research_browser_repository.py:212`
- **签名**：`def test_cancel_rejected_when_running(tmp_path) -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `SqliteResearchRepository` 结构化领域对象，并把结果记为 代码仓库；调用 `initialize` 完成该函数的一项辅助处理；调用 `research_request` 完成该函数的一项辅助处理，并把结果记为 业务请求；调用 `submit` 完成该函数的一项辅助处理，并把结果记为 多个解包结果。
调用 `start` 完成该函数的一项辅助处理。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `cancel` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `test_requeue_expired_lease`

- **源码**：`tests/test_research_browser_repository.py:239`
- **签名**：`def test_requeue_expired_lease(tmp_path) -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `SqliteResearchRepository` 结构化领域对象，并把结果记为 代码仓库；调用 `initialize` 完成该函数的一项辅助处理；调用 `research_request` 完成该函数的一项辅助处理，并把结果记为 业务请求；调用 `submit` 完成该函数的一项辅助处理，并把结果记为 多个解包结果。
调用 `start` 完成该函数的一项辅助处理；计算组合或计算已有值，并保存为 当前处理结果；断言辅助操作“调用 `requeue_expired` 完成该函数的一项辅助处理”的结果等于1；不满足就终止当前测试或流程；从代码仓库读取所需的状态或领域记录，并把结果记为 该调用返回的结果。
断言当前状态等于'failed_retryable'；不满足就终止当前测试或流程；断言租约为空；不满足就终止当前测试或流程。
```

#### `test_get_pack_returns_validated_pack`

- **源码**：`tests/test_research_browser_repository.py:265`
- **签名**：`def test_get_pack_returns_validated_pack(tmp_path) -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `SqliteResearchRepository` 结构化领域对象，并把结果记为 代码仓库；调用 `initialize` 完成该函数的一项辅助处理；调用 `research_request` 完成该函数的一项辅助处理，并把结果记为 业务请求；调用 `request_sha256` 计算内容身份、分数或派生结果，并把结果记为 请求内容 Hash。
调用 `submit` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；计算组合或计算已有值，并保存为 任务租约记录；调用 `start` 完成该函数的一项辅助处理；调用 `evidence_pack` 完成该函数的一项辅助处理，并把结果记为 检索或映射证据包。
调用 `complete` 完成该函数的一项辅助处理；调用 `get_pack` 读取或查询当前阶段需要的数据，并把结果记为 该调用返回的结果；断言检索或映射证据包的 ID等于检索或映射证据包的 ID；不满足就终止当前测试或流程；断言检索或映射证据包的 SHA-256等于检索或映射证据包的 SHA-256；不满足就终止当前测试或流程。
```

#### `test_list_packs_for_job_returns_succeeded`

- **源码**：`tests/test_research_browser_repository.py:301`
- **签名**：`def test_list_packs_for_job_returns_succeeded(tmp_path) -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `SqliteResearchRepository` 结构化领域对象，并把结果记为 代码仓库；调用 `initialize` 完成该函数的一项辅助处理；调用 `research_request` 完成该函数的一项辅助处理，并把结果记为 业务请求；调用 `request_sha256` 计算内容身份、分数或派生结果，并把结果记为 请求内容 Hash。
调用 `submit` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；计算组合或计算已有值，并保存为 任务租约记录；调用 `start` 完成该函数的一项辅助处理；调用 `evidence_pack` 完成该函数的一项辅助处理，并把结果记为 检索或映射证据包。
调用 `complete` 完成该函数的一项辅助处理；调用 `list_packs_for_job` 读取或查询当前阶段需要的数据，并把结果记为 该调用返回的结果；断言当前处理结果 的长度等于1；不满足就终止当前测试或流程；断言检索或映射证据包的 ID等于检索或映射证据包的 ID；不满足就终止当前测试或流程。
```

#### `test_list_packs_for_job_excludes_non_succeeded`

- **源码**：`tests/test_research_browser_repository.py:337`
- **签名**：`def test_list_packs_for_job_excludes_non_succeeded(tmp_path) -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `SqliteResearchRepository` 结构化领域对象，并把结果记为 代码仓库；调用 `initialize` 完成该函数的一项辅助处理；调用 `research_request` 完成该函数的一项辅助处理，并把结果记为 业务请求；调用 `submit` 完成该函数的一项辅助处理，并把结果记为 多个解包结果。
调用 `list_packs_for_job` 读取或查询当前阶段需要的数据，并把结果记为 该调用返回的结果；断言当前处理结果 的长度等于0；不满足就终止当前测试或流程。
```

#### `test_record_resource_link_is_idempotent`

- **源码**：`tests/test_research_browser_repository.py:353`
- **签名**：`def test_record_resource_link_is_idempotent(tmp_path) -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `SqliteResearchRepository` 结构化领域对象，并把结果记为 代码仓库；调用 `initialize` 完成该函数的一项辅助处理；调用 `research_request` 完成该函数的一项辅助处理，并把结果记为 业务请求；调用 `request_sha256` 计算内容身份、分数或派生结果，并把结果记为 请求内容 Hash。
调用 `submit` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；计算组合或计算已有值，并保存为 任务租约记录；调用 `start` 完成该函数的一项辅助处理；调用 `evidence_pack` 完成该函数的一项辅助处理，并把结果记为 检索或映射证据包。
调用 `complete` 完成该函数的一项辅助处理；调用 `record_resource_link` 完成该函数的一项辅助处理，并把结果记为 标识；调用 `record_resource_link` 完成该函数的一项辅助处理，并把结果记为 标识；断言标识等于标识；不满足就终止当前测试或流程。
```

#### `test_record_resource_link_rejects_hash_mismatch`

- **源码**：`tests/test_research_browser_repository.py:403`
- **签名**：`def test_record_resource_link_rejects_hash_mismatch(tmp_path) -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `SqliteResearchRepository` 结构化领域对象，并把结果记为 代码仓库；调用 `initialize` 完成该函数的一项辅助处理；调用 `research_request` 完成该函数的一项辅助处理，并把结果记为 业务请求；调用 `request_sha256` 计算内容身份、分数或派生结果，并把结果记为 请求内容 Hash。
调用 `submit` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；计算组合或计算已有值，并保存为 任务租约记录；调用 `start` 完成该函数的一项辅助处理；调用 `evidence_pack` 完成该函数的一项辅助处理，并把结果记为 检索或映射证据包。
调用 `complete` 完成该函数的一项辅助处理；调用 `record_resource_link` 完成该函数的一项辅助处理。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `record_resource_link` 完成该函数的一项辅助处理，退出时自动清理资源。
```

### `tests/test_research_browser_resource_bridge.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `FakeRepository.__init__`

- **源码**：`tests/test_research_browser_resource_bridge.py:29`
- **签名**：`def __init__(self) -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
将 当前处理结果、资源集合 初始化为空映射，用来收集后续结果。
```

#### `FakeRepository.initialize`

- **源码**：`tests/test_research_browser_resource_bridge.py:33`
- **签名**：`def initialize(self) -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
不执行额外操作。
```

#### `FakeRepository.ping`

- **源码**：`tests/test_research_browser_resource_bridge.py:36`
- **签名**：`def ping(self) -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
不执行额外操作。
```

#### `FakeRepository.get_pack`

- **源码**：`tests/test_research_browser_resource_bridge.py:39`
- **签名**：`def get_pack(self, session_id: str) -> ResearchEvidencePack`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前处理结果的 ID，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `ResearchEvidencePack` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `session_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`ResearchEvidencePack`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
返回当前处理结果中的对应字段的当前值。
```

#### `FakeRepository.record_resource_link`

- **源码**：`tests/test_research_browser_resource_bridge.py:42`
- **签名**：`def record_resource_link(self: 未显式标注, session_id: str, candidate_id: str, candidate_sha256: str, pack_sha256: str, idempotency_key: str, resource_id: str) -> str`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前处理结果的 ID、待审核的 MCP 能力候选的 ID、待审核的 MCP 能力候选的 SHA-256、检索或映射证据包的 SHA-256等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `session_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `candidate_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `candidate_sha256` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |
| `pack_sha256` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |
| `idempotency_key` | `str` | 调用方提供的幂等键；重复请求应复用同一结果，而不是再次产生副作用。 |
| `resource_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
如果请求幂等键属于资源集合，就返回资源集合中的对应字段的当前值。
读取输入资源 ID，并保存为 资源集合中的对应字段；返回输入资源 ID的当前值。
```

#### `FakeResourceService.__init__`

- **源码**：`tests/test_research_browser_resource_bridge.py:59`
- **签名**：`def __init__(self) -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
将 当前处理结果、当前处理结果 初始化为空列表，用来收集后续结果。
```

#### `FakeResourceService.submit`

- **源码**：`tests/test_research_browser_resource_bridge.py:63`
- **签名**：`def submit(self, *, request, idempotency_key)`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收业务请求、请求幂等键，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `request` | `未显式标注` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `idempotency_key` | `未显式标注` | 调用方提供的幂等键；重复请求应复用同一结果，而不是再次产生副作用。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
把新的处理结果追加或合并到当前处理结果；构造 `SimpleNamespace` 结构化领域对象，并把结果记为 领域记录；返回当前构造的顺序或去重集合。
```

#### `PassThroughRedactor.redact_text`

- **源码**：`tests/test_research_browser_resource_bridge.py:78`
- **签名**：`def redact_text(self, value: str, *, max_chars: int) -> str`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前字段值、最大字符数，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `value` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |
| `max_chars` | `int` | 名为 `max_chars` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
返回当前字段值中的对应字段的当前值。
```

#### `_build_service_with_pack`

- **源码**：`tests/test_research_browser_resource_bridge.py:82`
- **签名**：`def _build_service_with_pack(pack: ResearchEvidencePack)`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收检索或映射证据包，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `pack` | `ResearchEvidencePack` | 检索或映射证据包；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
构造 `FakeRepository` 结构化领域对象，并把结果记为 代码仓库；读取检索或映射证据包，并保存为 当前处理结果中的对应字段；调用 `research_policy` 完成该函数的一项辅助处理，并把结果记为 安全策略；构造 `LoadedResearchPolicy` 结构化领域对象，并把结果记为 已加载结果。
构造 `FakeResourceService` 结构化领域对象，并把结果记为 资源；构造 `ResearchBrowserService` 结构化领域对象，并把结果记为 领域服务对象；返回当前构造的顺序或去重集合。
```

#### `test_resource_candidate_submit_creates_resource`

- **源码**：`tests/test_research_browser_resource_bridge.py:106`
- **签名**：`def test_resource_candidate_submit_creates_resource() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `evidence_draft` 完成该函数的一项辅助处理，并把结果记为 可追溯证据记录；加载这一步需要的外部依赖；计算计算当前表达式的结果，并保存为 待审核的 MCP 能力候选；读取当前处理结果中的对应字段，并保存为 MCP 能力快照。
构造 `ResearchResourceCandidate` 结构化领域对象，并把结果记为 草稿对象；调用 `sha256_value` 计算内容身份、分数或派生结果，并把结果记为 待审核的 MCP 能力候选的 Hash；复制、序列化或校验结构化领域对象，并把结果记为 待审核的 MCP 能力候选；构造 `ResearchReport` 结构化领域对象，并把结果记为 MCP 评测或运行报告。
调用 `evidence_pack` 完成该函数的一项辅助处理，并把结果记为 检索或映射证据包；复制、序列化或校验结构化领域对象，并把结果记为 检索或映射证据包；调用 `_build_service_with_pack` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果；构造 `ResearchResourceSelection` 结构化领域对象，并把结果记为 该调用返回的结果。
调用 `submit_resource_candidate` 完成该函数的一项辅助处理，并把结果记为 复现输入资源；断言当前状态等于'awaiting_approval'；不满足就终止当前测试或流程；断言当前处理结果等于[]；不满足就终止当前测试或流程；断言当前处理结果中的对应字段中的对应字段等于格式化文本：f"research-resource:research_{'z' * 24}:{candidate.candidate_id}"；不满足就终止当前测试或流程。
```

#### `test_pack_hash_mismatch_raises_conflict`

- **源码**：`tests/test_research_browser_resource_bridge.py:157`
- **签名**：`def test_pack_hash_mismatch_raises_conflict() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `evidence_draft` 完成该函数的一项辅助处理，并把结果记为 可追溯证据记录；读取当前处理结果中的对应字段，并保存为 MCP 能力快照；构造 `ResearchResourceCandidate` 结构化领域对象，并把结果记为 草稿对象；调用 `sha256_value` 计算内容身份、分数或派生结果，并把结果记为 待审核的 MCP 能力候选的 Hash。
复制、序列化或校验结构化领域对象，并把结果记为 待审核的 MCP 能力候选；调用 `evidence_pack` 完成该函数的一项辅助处理，并把结果记为 检索或映射证据包；复制、序列化或校验结构化领域对象，并把结果记为 检索或映射证据包；调用 `_build_service_with_pack` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果。
构造 `ResearchResourceSelection` 结构化领域对象，并把结果记为 该调用返回的结果。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `submit_resource_candidate` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `test_candidate_not_found_raises_rejection`

- **源码**：`tests/test_research_browser_resource_bridge.py:190`
- **签名**：`def test_candidate_not_found_raises_rejection() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `evidence_pack` 完成该函数的一项辅助处理，并把结果记为 检索或映射证据包；调用 `_build_service_with_pack` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果；构造 `ResearchResourceSelection` 结构化领域对象，并把结果记为 该调用返回的结果。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `submit_resource_candidate` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `test_candidate_hash_mismatch_raises_conflict`

- **源码**：`tests/test_research_browser_resource_bridge.py:207`
- **签名**：`def test_candidate_hash_mismatch_raises_conflict() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `evidence_draft` 完成该函数的一项辅助处理，并把结果记为 可追溯证据记录；读取当前处理结果中的对应字段，并保存为 MCP 能力快照；构造 `ResearchResourceCandidate` 结构化领域对象，并把结果记为 草稿对象；调用 `sha256_value` 计算内容身份、分数或派生结果，并把结果记为 待审核的 MCP 能力候选的 Hash。
复制、序列化或校验结构化领域对象，并把结果记为 待审核的 MCP 能力候选；调用 `evidence_pack` 完成该函数的一项辅助处理，并把结果记为 检索或映射证据包；复制、序列化或校验结构化领域对象，并把结果记为 检索或映射证据包；调用 `_build_service_with_pack` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果。
构造 `ResearchResourceSelection` 结构化领域对象，并把结果记为 该调用返回的结果。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `submit_resource_candidate` 完成该函数的一项辅助处理，退出时自动清理资源。
```

### `tests/test_research_browser_schemas.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_request_normalizes_and_deduplicates_hosts`

- **源码**：`tests/test_research_browser_schemas.py:11`
- **签名**：`def test_request_normalizes_and_deduplicates_hosts() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `ResearchRequest` 结构化领域对象，并把结果记为 业务请求；断言语义检索问题等于'PSTNet official paper'；不满足就终止当前测试或流程；断言允许访问的主机集合等于['example.org']；不满足就终止当前测试或流程。
```

#### `test_request_rejects_url_in_host_scope`

- **源码**：`tests/test_research_browser_schemas.py:21`
- **签名**：`def test_request_rejects_url_in_host_scope() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中构造 `ResearchRequest` 结构化领域对象，退出时自动清理资源。
```

#### `test_request_rejects_control_characters`

- **源码**：`tests/test_research_browser_schemas.py:30`
- **签名**：`def test_request_rejects_control_characters() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中构造 `ResearchRequest` 结构化领域对象，退出时自动清理资源。
```

#### `test_request_rejects_empty_query`

- **源码**：`tests/test_research_browser_schemas.py:38`
- **签名**：`def test_request_rejects_empty_query() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中构造 `ResearchRequest` 结构化领域对象，退出时自动清理资源。
```

#### `test_synthesis_draft_rejects_duplicate_citation_ids`

- **源码**：`tests/test_research_browser_schemas.py:46`
- **签名**：`def test_synthesis_draft_rejects_duplicate_citation_ids() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中构造 `ResearchSynthesisDraft` 结构化领域对象，退出时自动清理资源。
```

#### `test_synthesis_draft_rejects_duplicate_resource_candidate_ids`

- **源码**：`tests/test_research_browser_schemas.py:54`
- **签名**：`def test_synthesis_draft_rejects_duplicate_resource_candidate_ids() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中构造 `ResearchSynthesisDraft` 结构化领域对象，退出时自动清理资源。
```

#### `test_request_defaults`

- **源码**：`tests/test_research_browser_schemas.py:63`
- **签名**：`def test_request_defaults() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `ResearchRequest` 结构化领域对象，并把结果记为 业务请求；断言版本等于'phase51-v1'；不满足就终止当前测试或流程；断言检索结果数量上限等于8；不满足就终止当前测试或流程；断言最大证据来源集合等于3；不满足就终止当前测试或流程。
断言PDF是真；不满足就终止当前测试或流程；断言允许访问的主机集合等于[]；不满足就终止当前测试或流程。
```

#### `test_request_rejects_too_many_hosts`

- **源码**：`tests/test_research_browser_schemas.py:75`
- **签名**：`def test_request_rejects_too_many_hosts() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中构造 `ResearchRequest` 结构化领域对象，退出时自动清理资源。
```

### `tests/test_research_browser_skill.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `FixtureCollector.collect`

- **源码**：`tests/test_research_browser_skill.py:23`
- **签名**：`def collect(self, request)`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收业务请求，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `request` | `未显式标注` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
移除业务请求中的当前内容；调用 `evidence_draft` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `test_restricted_research_skill_matches_offline_suite`

- **源码**：`tests/test_research_browser_skill.py:28`
- **签名**：`def test_restricted_research_skill_matches_offline_suite() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
将外部表示解析为结构化内容，并把结果记为 评测套件；读取评测套件中的对应字段中的对应字段，并保存为 评测用例；调用 `build_tool_registry` 组装当前阶段需要的领域对象，并把结果记为 受控工具定义集合；调用 `build_skill_registry` 组装当前阶段需要的领域对象，并把结果记为 组件注册表。
从组件注册表读取所需的状态或领域记录，并把结果记为 边界值；调用组件注册表完成模型或 Runnable 处理，并把结果记为 阶段处理结果；断言失败为空；不满足就终止当前测试或流程；断言输出结果不为空；不满足就终止当前测试或流程。
断言输出结果中的对应字段中的对应字段 的长度不小于1；不满足就终止当前测试或流程；断言输出结果中的对应字段是真；不满足就终止当前测试或流程；断言输出结果中的对应字段是真；不满足就终止当前测试或流程；断言工具集合 的长度等于1；不满足就终止当前测试或流程。
断言MCP Tool 名称等于'browser.collect_research_evidence'；不满足就终止当前测试或流程。
```

#### `test_skill_manifest_matches_suite`

- **源码**：`tests/test_research_browser_skill.py:70`
- **签名**：`def test_skill_manifest_matches_suite() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
将外部表示解析为结构化内容，并把结果记为 评测套件；计算组合或计算已有值，并保存为 运行或工作区 Manifest的路径；将外部表示解析为结构化内容，并把结果记为 运行或工作区 Manifest；断言运行或工作区 Manifest中的对应字段等于评测套件中的对应字段；不满足就终止当前测试或流程。
断言运行或工作区 Manifest中的对应字段等于评测套件中的对应字段；不满足就终止当前测试或流程；断言运行或工作区 Manifest中的对应字段等于'restricted_web_research_offline_v1'；不满足就终止当前测试或流程。
```

### `tests/test_research_browser_synthesis.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `PassThroughRedactor.redact_text`

- **源码**：`tests/test_research_browser_synthesis.py:17`
- **签名**：`def redact_text(self, value: str, *, max_chars: int) -> str`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前字段值、最大字符数，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `value` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |
| `max_chars` | `int` | 名为 `max_chars` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
返回当前字段值中的对应字段的当前值。
```

#### `FakeGateway.__init__`

- **源码**：`tests/test_research_browser_synthesis.py:22`
- **签名**：`def __init__(self, draft: ResearchSynthesisDraft | None = None) -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收草稿对象，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `draft` | `ResearchSynthesisDraft | None` | 草稿对象；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 空值 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 草稿对象 分别保存到同名实例字段；将 工具或模型调用记录集合 初始化为空列表，用来收集后续结果。
```

#### `FakeGateway.invoke_structured`

- **源码**：`tests/test_research_browser_synthesis.py:26`
- **签名**：`def invoke_structured(self, **kwargs)`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收函数关键字参数映射，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `**kwargs` | `未显式标注` | 额外关键字参数映射。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
把函数关键字参数映射追加或合并到工具或模型调用记录集合。
如果草稿对象为空，就构造并返回 `SimpleNamespace` 结构化领域对象。
构造并返回 `SimpleNamespace` 结构化领域对象。
```

#### `BudgetGateway.invoke_structured`

- **源码**：`tests/test_research_browser_synthesis.py:42`
- **签名**：`def invoke_structured(self, **kwargs)`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收函数关键字参数映射，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `**kwargs` | `未显式标注` | 额外关键字参数映射。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
拒绝继续处理并抛出 `ModelBudgetExceeded`，向调用方报告输入或运行失败。
```

#### `test_synthesis_rejects_unknown_citation_id`

- **源码**：`tests/test_research_browser_synthesis.py:51`
- **签名**：`def test_synthesis_rejects_unknown_citation_id() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `FakeGateway` 结构化领域对象，并把结果记为 外部服务网关；构造 `ResearchSynthesizer` 结构化领域对象，并把结果记为 该调用返回的结果。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `synthesize` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `test_synthesis_rejects_unknown_resource_candidate_id`

- **源码**：`tests/test_research_browser_synthesis.py:69`
- **签名**：`def test_synthesis_rejects_unknown_resource_candidate_id() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `evidence_draft` 完成该函数的一项辅助处理，并把结果记为 可追溯证据记录；构造 `FakeGateway` 结构化领域对象，并把结果记为 外部服务网关；构造 `ResearchSynthesizer` 结构化领域对象，并把结果记为 该调用返回的结果。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `synthesize` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `test_external_prompt_injection_remains_untrusted_data`

- **源码**：`tests/test_research_browser_synthesis.py:89`
- **签名**：`def test_external_prompt_injection_remains_untrusted_data() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `evidence_draft` 完成该函数的一项辅助处理，并把结果记为 可追溯证据记录；读取论文引用证据集合中的对应字段，并保存为 论文引用证据；计算使用固定配置或常量值，并保存为 当前处理结果；调用 `sha256_text` 计算内容身份、分数或派生结果，并把结果记为 当前处理结果的 Hash。
复制、序列化或校验结构化领域对象，并把结果记为 论文引用证据；复制、序列化或校验结构化领域对象，并把结果记为 可追溯证据记录；构造 `FakeGateway` 结构化领域对象，并把结果记为 外部服务网关；构造 `ResearchSynthesizer` 结构化领域对象，并把结果记为 该调用返回的结果。
调用 `synthesize` 完成该函数的一项辅助处理，并把结果记为 MCP 评测或运行报告；读取工具或模型调用记录集合中的对应字段中的对应字段，并保存为 发给模型的结构化提示；断言当前输入内容属于发给模型的结构化提示；不满足就终止当前测试或流程；断言当前输入内容属于发给模型的结构化提示；不满足就终止当前测试或流程。
断言论文引用证据的 ID等于论文引用证据的 ID；不满足就终止当前测试或流程。
```

#### `test_no_citations_returns_insufficient_evidence`

- **源码**：`tests/test_research_browser_synthesis.py:134`
- **签名**：`def test_no_citations_returns_insufficient_evidence() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `evidence_draft` 完成该函数的一项辅助处理，并把结果记为 可追溯证据记录；复制、序列化或校验结构化领域对象，并把结果记为 可追溯证据记录；构造 `FakeGateway` 结构化领域对象，并把结果记为 外部服务网关；构造 `ResearchSynthesizer` 结构化领域对象，并把结果记为 该调用返回的结果。
调用 `synthesize` 完成该函数的一项辅助处理，并把结果记为 MCP 评测或运行报告；断言状态等于'insufficient_evidence'；不满足就终止当前测试或流程；断言工具或模型调用记录集合 的长度等于0；不满足就终止当前测试或流程。
```

#### `test_budget_denied_returns_evidence`

- **源码**：`tests/test_research_browser_synthesis.py:150`
- **签名**：`def test_budget_denied_returns_evidence() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `evidence_draft` 完成该函数的一项辅助处理，并把结果记为 可追溯证据记录；构造 `ResearchSynthesizer` 结构化领域对象，并把结果记为 该调用返回的结果；调用 `synthesize` 完成该函数的一项辅助处理，并把结果记为 MCP 评测或运行报告；断言状态等于'budget_denied'；不满足就终止当前测试或流程。
断言论文引用证据集合 的长度不小于1；不满足就终止当前测试或流程。
```

#### `test_structured_parse_failure_returns_evidence_only`

- **源码**：`tests/test_research_browser_synthesis.py:164`
- **签名**：`def test_structured_parse_failure_returns_evidence_only() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `FakeGateway` 结构化领域对象，并把结果记为 外部服务网关；构造 `ResearchSynthesizer` 结构化领域对象，并把结果记为 该调用返回的结果；调用 `synthesize` 完成该函数的一项辅助处理，并把结果记为 MCP 评测或运行报告；断言状态等于'evidence_only'；不满足就终止当前测试或流程。
断言调用记录的 ID不为空；不满足就终止当前测试或流程。
```

#### `test_gateway_task_kind_is_web_research_synthesis`

- **源码**：`tests/test_research_browser_synthesis.py:178`
- **签名**：`def test_gateway_task_kind_is_web_research_synthesis() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `FakeGateway` 结构化领域对象，并把结果记为 外部服务网关；构造 `ResearchSynthesizer` 结构化领域对象，并把结果记为 该调用返回的结果；调用 `synthesize` 完成该函数的一项辅助处理；断言工具或模型调用记录集合中的对应字段中的对应字段等于'web_research_synthesis'；不满足就终止当前测试或流程。
```

#### `test_answer_goes_through_redactor`

- **源码**：`tests/test_research_browser_synthesis.py:196`
- **签名**：`def test_answer_goes_through_redactor() -> None`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
定义内部类型 `MarkingRedactor`，用于组织当前函数的临时逻辑。
调用 `evidence_draft` 完成该函数的一项辅助处理，并把结果记为 可追溯证据记录；构造 `FakeGateway` 结构化领域对象，并把结果记为 外部服务网关；构造 `ResearchSynthesizer` 结构化领域对象，并把结果记为 该调用返回的结果；调用 `synthesize` 完成该函数的一项辅助处理，并把结果记为 MCP 评测或运行报告。
断言当前输入内容属于当前处理结果；不满足就终止当前测试或流程。
```

#### `test_answer_goes_through_redactor.MarkingRedactor.redact_text`

- **源码**：`tests/test_research_browser_synthesis.py:198`
- **签名**：`def redact_text(self, value: str, *, max_chars: int) -> str`
- **作用**：在受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段中，该函数接收当前字段值、最大字符数，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `value` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |
| `max_chars` | `int` | 名为 `max_chars` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
返回当前计算得到的结果。
```

### `tests/test_retrieval_policy_eval.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_policy_eval_is_offline_and_produces_proposals`

- **源码**：`tests/test_retrieval_policy_eval.py:14`
- **签名**：`def test_policy_eval_is_offline_and_produces_proposals()`
- **作用**：在论文方法检索质量优化、候选排序策略和离线检索评测阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `load_retrieval_policy` 读取或查询当前阶段需要的数据，并把结果记为 安全策略；调用 `load_policy_cases` 读取或查询当前阶段需要的数据，并把结果记为 评测用例集合；调用 `run_policy_eval` 完成该函数的一项辅助处理，并把结果记为 MCP 评测或运行报告；断言用例集合有值或为真；不满足就终止当前测试或流程。
断言当前处理结果有值或为真；不满足就终止当前测试或流程；断言当前可迭代输入中每一项都满足“当前处理结果等于1.0”的项；不满足就终止当前测试或流程；断言当前可迭代输入中每一项都满足“当前处理结果等于1.0”的项；不满足就终止当前测试或流程；断言当前可迭代输入中每一项都满足“被策略禁止的内容或操作的路径的数量等于0”的项；不满足就终止当前测试或流程。
```

#### `test_semantic_challenger_never_loses_to_sparse_baseline`

- **源码**：`tests/test_retrieval_policy_eval.py:46`
- **签名**：`def test_semantic_challenger_never_loses_to_sparse_baseline()`
- **作用**：在论文方法检索质量优化、候选排序策略和离线检索评测阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `load_retrieval_policy` 读取或查询当前阶段需要的数据，并把结果记为 安全策略；调用 `load_policy_cases` 读取或查询当前阶段需要的数据，并把结果记为 评测用例集合；调用 `run_policy_eval` 完成该函数的一项辅助处理，并把结果记为 MCP 评测或运行报告；遍历并筛选输入，将整理后的结果保存为 状态字段集合。
读取状态字段集合中的对应字段，并保存为 已审核的 MCP 能力基线；读取状态字段集合中的对应字段，并保存为 后续步骤使用的结果；断言当前处理结果不小于当前处理结果；不满足就终止当前测试或流程；断言当前处理结果不小于当前处理结果；不满足就终止当前测试或流程。
断言当前处理结果是真；不满足就终止当前测试或流程。
```

### `tests/test_retrieval_policy_integration.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_profile_limits_observed_channels_without_weakening_evidence`

- **源码**：`tests/test_retrieval_policy_integration.py:27`
- **签名**：`def test_profile_limits_observed_channels_without_weakening_evidence()`
- **作用**：在论文方法检索质量优化、候选排序策略和离线检索评测阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `load_retrieval_policy` 读取或查询当前阶段需要的数据，并把结果记为 安全策略；调用 `profile_by_id` 完成该函数的一项辅助处理，并把结果记为 MCP Client 配置档案；调用 `build_repository_index` 组装当前阶段需要的领域对象，并把结果记为 当前候选项的索引；调用 `build_evidence_pack` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果。
断言待处理项集合有值或为真；不满足就终止当前测试或流程；构造临时集合、映射或轻量领域对象，并把结果记为 该调用返回的结果；断言当前可迭代输入中每一项都满足“辅助操作“构造临时集合、映射或轻量领域对象”的结果不大于当前处理结果”的项；不满足就终止当前测试或流程；断言当前可迭代输入中每一项都满足““调用 `validate_code_evidence` 校验当前输入或状态”后得到肯定结果”的项；不满足就终止当前测试或流程。
```

#### `test_import_graph_without_symbol_fails_closed`

- **源码**：`tests/test_retrieval_policy_integration.py:63`
- **签名**：`def test_import_graph_without_symbol_fails_closed()`
- **作用**：在论文方法检索质量优化、候选排序策略和离线检索评测阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `build_repository_index` 组装当前阶段需要的领域对象，并把结果记为 当前候选项的索引。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `build_evidence_pack` 组装当前阶段需要的领域对象，退出时自动清理资源。
```

### `tests/test_retrieval_policy_router.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_exact_error_routes_to_lexical_profile`

- **源码**：`tests/test_retrieval_policy_router.py:17`
- **签名**：`def test_exact_error_routes_to_lexical_profile()`
- **作用**：在论文方法检索质量优化、候选排序策略和离线检索评测阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `build_query_features` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果；调用 `select_retrieval_profile` 完成该函数的一项辅助处理，并把结果记为 人工决策结果；断言查询类别等于'exact_error'；不满足就终止当前测试或流程；断言MCP Client 配置档案 ID等于'exact_lexical_v1'；不满足就终止当前测试或流程。
断言当前输入内容不属于当前处理结果；不满足就终止当前测试或流程；断言当前处理结果是真；不满足就终止当前测试或流程。
```

#### `test_symbol_routes_to_symbol_path_profile`

- **源码**：`tests/test_retrieval_policy_router.py:35`
- **签名**：`def test_symbol_routes_to_symbol_path_profile()`
- **作用**：在论文方法检索质量优化、候选排序策略和离线检索评测阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `build_query_features` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果；调用 `select_retrieval_profile` 完成该函数的一项辅助处理，并把结果记为 人工决策结果；断言查询类别等于'symbol_path'；不满足就终止当前测试或流程；断言MCP Client 配置档案 ID等于'symbol_path_v1'；不满足就终止当前测试或流程。
```

#### `test_semantic_query_uses_dense_only_when_available`

- **源码**：`tests/test_retrieval_policy_router.py:51`
- **签名**：`def test_semantic_query_uses_dense_only_when_available()`
- **作用**：在论文方法检索质量优化、候选排序策略和离线检索评测阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算使用固定配置或常量值，并保存为 语义检索问题；调用 `build_query_features` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果；调用 `select_retrieval_profile` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `select_retrieval_profile` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
断言查询类别等于'semantic_alignment'；不满足就终止当前测试或流程；断言MCP Client 配置档案 ID等于'semantic_hybrid_v1'；不满足就终止当前测试或流程；断言MCP Client 配置档案 ID等于'balanced_sparse_v1'；不满足就终止当前测试或流程；断言当前处理结果是假；不满足就终止当前测试或流程。
断言当前可迭代输入中存在满足““检查当前字段值是否满足文本匹配条件”后得到肯定结果”的项；不满足就终止当前测试或流程。
```

#### `test_shadow_decision_never_applies_profile`

- **源码**：`tests/test_retrieval_policy_router.py:86`
- **签名**：`def test_shadow_decision_never_applies_profile()`
- **作用**：在论文方法检索质量优化、候选排序策略和离线检索评测阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `build_query_features` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果；调用 `select_retrieval_profile` 完成该函数的一项辅助处理，并把结果记为 人工决策结果；断言当前处理结果是假；不满足就终止当前测试或流程；断言MCP 评测或运行模式等于'shadow'；不满足就终止当前测试或流程。
```

### `tests/test_retrieval_policy_schemas.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_default_policy_loads_and_has_offline_fallback`

- **源码**：`tests/test_retrieval_policy_schemas.py:18`
- **签名**：`def test_default_policy_loads_and_has_offline_fallback()`
- **作用**：在论文方法检索质量优化、候选排序策略和离线检索评测阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `load_retrieval_policy` 读取或查询当前阶段需要的数据，并把结果记为 安全策略；调用 `profile_by_id` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；断言当前处理结果是假；不满足就终止当前测试或流程；断言当前输入内容不属于当前处理结果；不满足就终止当前测试或流程。
断言辅助操作“调用 `sha256_value` 计算内容身份、分数或派生结果”的结果 的长度等于64；不满足就终止当前测试或流程。
```

#### `test_policy_rejects_import_graph_without_symbol`

- **源码**：`tests/test_retrieval_policy_schemas.py:27`
- **签名**：`def test_policy_rejects_import_graph_without_symbol(tmp_path: Path)`
- **作用**：在论文方法检索质量优化、候选排序策略和离线检索评测阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
将外部表示解析为结构化内容，并把结果记为 结构化请求载荷；计算初始化顺序集合，并保存为 结构化请求载荷中的对应字段中的对应字段中的对应字段；计算按字段初始化键值映射，并保存为 结构化请求载荷中的对应字段中的对应字段中的对应字段；计算组合或计算已有值，并保存为 文件或目录路径。
将处理结果写入文件或目录路径指定的文件。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `load_retrieval_policy` 读取或查询当前阶段需要的数据，退出时自动清理资源。
```

#### `test_policy_hash_changes_when_weight_changes`

- **源码**：`tests/test_retrieval_policy_schemas.py:40`
- **签名**：`def test_policy_hash_changes_when_weight_changes()`
- **作用**：在论文方法检索质量优化、候选排序策略和离线检索评测阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `load_retrieval_policy` 读取或查询当前阶段需要的数据，并把结果记为 安全策略；复制、序列化或校验结构化领域对象，并把结果记为 发生变化的内容；将新的计算结果累加或合并到当前处理结果中的对应字段；断言辅助操作“调用 `sha256_value` 计算内容身份、分数或派生结果”的结果不等于辅助操作“调用 `sha256_value` 计算内容身份、分数或派生结果”的结果；不满足就终止当前测试或流程。
```

### `tests/test_semantic_retrieval_eval.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_semantic_runner_rejects_offline_suite`

- **源码**：`tests/test_semantic_retrieval_eval.py:31`
- **签名**：`def test_semantic_runner_rejects_offline_suite()`
- **作用**：在论文方法检索质量优化、候选排序策略和离线检索评测阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算按字段初始化键值映射，并保存为 结构化请求载荷。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中复制、序列化或校验结构化领域对象，退出时自动清理资源。
```

#### `test_efficiency_scorer_checks_embedding_budget`

- **源码**：`tests/test_semantic_retrieval_eval.py:56`
- **签名**：`def test_efficiency_scorer_checks_embedding_budget()`
- **作用**：在论文方法检索质量优化、候选排序策略和离线检索评测阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
复制、序列化或校验结构化领域对象，并把结果记为 评测用例；构造 `EvalObservation` 结构化领域对象，并把结果记为 MCP Client 单次观测结果；调用 `score_case` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果；断言当前处理结果是假；不满足就终止当前测试或流程。
断言当前可迭代输入中存在满足“待解析或验证的代码等于'EFFICIENCY_EMBEDDING_DOCUMENT_CALLS' 且 “当前处理结果有值或为真”不成立”的项；不满足就终止当前测试或流程。
```

#### `test_real_embedding_provider_case`

- **源码**：`tests/test_semantic_retrieval_eval.py:108`
- **签名**：`def test_real_embedding_provider_case()`
- **作用**：在论文方法检索质量优化、候选排序策略和离线检索评测阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
如果“从运行环境读取配置项；若未设置则使用调用方提供的默认值”后未得到肯定结果 或 “从运行环境读取配置项；若未设置则使用调用方提供的默认值”后未得到肯定结果 或 “当前处理结果有值或为真”不成立，就调用 `skip` 完成该函数的一项辅助处理。
调用 `load_case_file` 读取或查询当前阶段需要的数据，并把结果记为 评测用例；调用 `run_case` 完成该函数的一项辅助处理，并把结果记为 MCP Client 单次观测结果；调用 `score_case` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果；断言当前处理结果有值或为真，失败时附带断言说明；不满足就终止当前测试或流程。
```

### `tests/test_skill_authority_boundary.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_registry_rejects_nested_authority_field`

- **源码**：`tests/test_skill_authority_boundary.py:27`
- **签名**：`def test_registry_rejects_nested_authority_field(tmp_path)`
- **作用**：在论文复现 Agent Skill/Plugin 的清单加载、权限隔离、运行时和调试日志验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：无业务返回值；通过断言或预期异常验证目标行为。

**伪代码**

```text
调用 `base_manifest` 完成该函数的一项辅助处理，并把结果记为 运行或工作区 Manifest；调用 `write_skill_package` 持久化或更新当前领域数据，并把结果记为 该调用返回的结果。
定义内部辅助函数 `unsafe_handler`，供当前函数在后续步骤中调用。
构造 `SkillRegistry` 结构化领域对象，并把结果记为 组件注册表；调用 `register` 完成该函数的一项辅助处理，并把结果记为 边界值；调用组件注册表完成模型或 Runnable 处理，并把结果记为 阶段处理结果；断言失败不为空；不满足就终止当前测试或流程。
断言待解析或验证的代码等于'SKILL_AUTHORITY_VIOLATION'；不满足就终止当前测试或流程；断言输出结果为空；不满足就终止当前测试或流程；断言输出结果的 SHA-256为空；不满足就终止当前测试或流程。
```

#### `test_registry_rejects_nested_authority_field.unsafe_handler`

- **源码**：`tests/test_skill_authority_boundary.py:34`
- **签名**：`def unsafe_handler(payload: AuthorityInput, runtime)`
- **作用**：在论文复现 Agent Skill/Plugin 的清单加载、权限隔离、运行时和调试日志验证阶段中，该函数接收结构化请求载荷、运行时环境，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `payload` | `AuthorityInput` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `runtime` | `未显式标注` | 运行时环境；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
移除结构化请求载荷、运行时环境中的当前内容；构造并返回 `AuthorityOutput` 结构化领域对象。
```

### `tests/test_skill_golden_eval.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_contains_forbidden_key`

- **源码**：`tests/test_skill_golden_eval.py:32`
- **签名**：`def _contains_forbidden_key(value: Any, forbidden: set[str]) -> bool`
- **作用**：在论文复现 Agent Skill/Plugin 的清单加载、权限隔离、运行时和调试日志验证阶段中，该函数接收当前字段值、被策略禁止的内容或操作，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `Any` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |
| `forbidden` | `set[str]` | 被策略禁止的内容或操作；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
如果“计算数量、边界或类型判断结果”后得到肯定结果，就检查辅助操作产生的可迭代结果（调用 `items` 完成该函数的一项辅助处理）中是否存在满足“辅助操作“调用 `str` 完成该函数的一项辅助处理，再对返回文本执行规范化或拆分”的结果属于被策略禁止的内容或操作 或 “调用 `_contains_forbidden_key` 完成该函数的一项辅助处理”后得到肯定结果”的项，并返回处理结果。
如果“计算数量、边界或类型判断结果”后得到肯定结果，就检查由当前字段值组成的集合或迭代器中是否存在满足““调用 `_contains_forbidden_key` 完成该函数的一项辅助处理”后得到肯定结果”的项，并返回处理结果。
返回固定值 `假`。
```

#### `test_cuda_build_skill_matches_offline_golden_case`

- **源码**：`tests/test_skill_golden_eval.py:47`
- **签名**：`def test_cuda_build_skill_matches_offline_golden_case()`
- **作用**：在论文复现 Agent Skill/Plugin 的清单加载、权限隔离、运行时和调试日志验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
将外部表示解析为结构化内容，并把结果记为 评测套件；读取评测套件中的对应字段中的对应字段，并保存为 评测用例；调用 `build_skill_registry` 组装当前阶段需要的领域对象，并把结果记为 组件注册表；从组件注册表读取所需的状态或领域记录，并把结果记为 边界值。
调用组件注册表完成模型或 Runnable 处理，并把结果记为 阶段处理结果；断言失败为空；不满足就终止当前测试或流程；断言输出结果不为空；不满足就终止当前测试或流程；读取评测用例中的对应字段，并保存为 期望值。
断言输出结果中的对应字段等于期望值中的对应字段；不满足就终止当前测试或流程；断言“调用 `issubset` 完成该函数的一项辅助处理”后得到肯定结果；不满足就终止当前测试或流程；断言“调用 `issubset` 完成该函数的一项辅助处理”后得到肯定结果；不满足就终止当前测试或流程；断言输出结果中的对应字段不小于期望值中的对应字段；不满足就终止当前测试或流程。
断言工具集合 的长度不大于期望值中的对应字段；不满足就终止当前测试或流程；断言当前可迭代输入中每一项都满足“当前状态等于'succeeded'”的项；不满足就终止当前测试或流程；断言“调用 `_contains_forbidden_key` 完成该函数的一项辅助处理”后未得到肯定结果；不满足就终止当前测试或流程。
```

### `tests/test_skill_import_boundary.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_imports`

- **源码**：`tests/test_skill_import_boundary.py:23`
- **签名**：`def _imports(path: Path) -> list[str]`
- **作用**：在论文复现 Agent Skill/Plugin 的清单加载、权限隔离、运行时和调试日志验证阶段中，该函数接收文件或目录路径，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`list[str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
将 Python 源码解析为抽象语法树，并把结果记为 该调用返回的结果；将 状态字段集合 初始化为空列表，用来收集后续结果。
遍历语法树节点集合，每次把当前项记为当前流程节点：
    如果“计算数量、边界或类型判断结果”后得到肯定结果：
        把新的处理结果追加或合并到状态字段集合。
    否则：
        如果“计算数量、边界或类型判断结果”后得到肯定结果 且 Python 模块有值或为真，就把Python 模块追加或合并到状态字段集合。
返回状态字段集合的当前值。
```

#### `test_skill_source_has_no_direct_privileged_imports`

- **源码**：`tests/test_skill_import_boundary.py:34`
- **签名**：`def test_skill_source_has_no_direct_privileged_imports()`
- **作用**：在论文复现 Agent Skill/Plugin 的清单加载、权限隔离、运行时和调试日志验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
将 约束违反项集合 初始化为空列表，用来收集后续结果。
遍历辅助操作产生的可迭代结果（按稳定规则整理结果顺序），每次把当前项记为文件或目录路径：
    遍历辅助操作产生的可迭代结果（调用 `_imports` 完成该函数的一项辅助处理），每次把当前项记为当前处理结果：
        如果“检查当前处理结果是否满足文本匹配条件”后得到肯定结果，就把新的处理结果追加或合并到约束违反项集合。
断言约束违反项集合等于[]；不满足就终止当前测试或流程。
```

#### `test_plugin_packages_contain_no_python_or_native_code`

- **源码**：`tests/test_skill_import_boundary.py:46`
- **签名**：`def test_plugin_packages_contain_no_python_or_native_code()`
- **作用**：在论文复现 Agent Skill/Plugin 的清单加载、权限隔离、运行时和调试日志验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算初始化去重集合，并保存为 当前处理结果；遍历并筛选输入，将整理后的结果保存为 约束违反项集合；断言约束违反项集合等于[]；不满足就终止当前测试或流程。
```

### `tests/test_skill_log_debug_integration.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_cuda_skill_selector_requires_cuda_and_failure_markers`

- **源码**：`tests/test_skill_log_debug_integration.py:13`
- **签名**：`def test_cuda_skill_selector_requires_cuda_and_failure_markers()`
- **作用**：在论文复现 Agent Skill/Plugin 的清单加载、权限隔离、运行时和调试日志验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
断言“调用 `_should_run_cuda_build_skill` 完成该函数的一项辅助处理”后得到肯定结果；不满足就终止当前测试或流程；断言“调用 `_should_run_cuda_build_skill` 完成该函数的一项辅助处理”后未得到肯定结果；不满足就终止当前测试或流程；断言“调用 `_should_run_cuda_build_skill` 完成该函数的一项辅助处理”后未得到肯定结果；不满足就终止当前测试或流程。
```

#### `test_disabled_skill_does_not_build_registry`

- **源码**：`tests/test_skill_log_debug_integration.py:25`
- **签名**：`def test_disabled_skill_does_not_build_registry(monkeypatch)`
- **作用**：在论文复现 Agent Skill/Plugin 的清单加载、权限隔离、运行时和调试日志验证阶段中，该函数接收测试环境修改工具，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `monkeypatch` | `未显式标注` | pytest 提供的环境/对象替换工具，用于隔离测试副作用；不是业务输入。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `setattr` 完成该函数的一项辅助处理。
定义内部辅助函数 `fail_if_called`，供当前函数在后续步骤中调用。
调用 `setattr` 完成该函数的一项辅助处理；调用 `_run_optional_cuda_build_skill` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果；断言阶段处理结果等于(空值, 空值, 空值, [], 空值)；不满足就终止当前测试或流程。
```

#### `test_disabled_skill_does_not_build_registry.fail_if_called`

- **源码**：`tests/test_skill_log_debug_integration.py:28`
- **签名**：`def fail_if_called(**kwargs)`
- **作用**：在论文复现 Agent Skill/Plugin 的清单加载、权限隔离、运行时和调试日志验证阶段中，该函数接收函数关键字参数映射，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `**kwargs` | `未显式标注` | 额外关键字参数映射。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
移除函数关键字参数映射中的当前内容；拒绝继续处理并抛出 `AssertionError`，向调用方报告输入或运行失败。
```

### `tests/test_skill_manifest_loader.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_loader_accepts_valid_package`

- **源码**：`tests/test_skill_manifest_loader.py:16`
- **签名**：`def test_loader_accepts_valid_package(tmp_path)`
- **作用**：在论文复现 Agent Skill/Plugin 的清单加载、权限隔离、运行时和调试日志验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `write_skill_package` 持久化或更新当前领域数据，并把结果记为 该调用返回的结果；断言当前处理结果的 ID等于'example_skill'；不满足就终止当前测试或流程；断言运行或工作区 Manifest的 SHA-256 的长度等于64；不满足就终止当前测试或流程；断言当前处理结果的 SHA-256 的长度等于64；不满足就终止当前测试或流程。
```

#### `test_loader_rejects_unknown_manifest_field`

- **源码**：`tests/test_skill_manifest_loader.py:24`
- **签名**：`def test_loader_rejects_unknown_manifest_field(tmp_path)`
- **作用**：在论文复现 Agent Skill/Plugin 的清单加载、权限隔离、运行时和调试日志验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `base_manifest` 完成该函数的一项辅助处理，并把结果记为 运行或工作区 Manifest；计算使用固定配置或常量值，并保存为 运行或工作区 Manifest中的对应字段；计算组合或计算已有值，并保存为 当前处理结果的目录；创建当前处理结果的目录对应的目录。
将处理结果写入当前输入内容指定的文件。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `load_skill_package` 读取或查询当前阶段需要的数据，退出时自动清理资源。
```

#### `test_loader_rejects_unlisted_python_file`

- **源码**：`tests/test_skill_manifest_loader.py:38`
- **签名**：`def test_loader_rejects_unlisted_python_file(tmp_path)`
- **作用**：在论文复现 Agent Skill/Plugin 的清单加载、权限隔离、运行时和调试日志验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `write_skill_package` 持久化或更新当前领域数据，并把结果记为 该调用返回的结果；将处理结果写入当前输入内容指定的文件。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `load_skill_package` 读取或查询当前阶段需要的数据，退出时自动清理资源。
```

#### `test_loader_rejects_absolute_resource_path`

- **源码**：`tests/test_skill_manifest_loader.py:49`
- **签名**：`def test_loader_rejects_absolute_resource_path(tmp_path)`
- **作用**：在论文复现 Agent Skill/Plugin 的清单加载、权限隔离、运行时和调试日志验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `base_manifest` 完成该函数的一项辅助处理，并把结果记为 运行或工作区 Manifest；计算初始化顺序集合，并保存为 运行或工作区 Manifest中的对应字段；计算组合或计算已有值，并保存为 当前处理结果的目录；创建当前处理结果的目录对应的目录。
将处理结果写入当前输入内容指定的文件。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `load_skill_package` 读取或查询当前阶段需要的数据，退出时自动清理资源。
```

#### `test_loader_rejects_resource_hash_mismatch`

- **源码**：`tests/test_skill_manifest_loader.py:68`
- **签名**：`def test_loader_rejects_resource_hash_mismatch(tmp_path)`
- **作用**：在论文复现 Agent Skill/Plugin 的清单加载、权限隔离、运行时和调试日志验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算使用固定配置或常量值，并保存为 业务内容；调用 `base_manifest` 完成该函数的一项辅助处理，并把结果记为 运行或工作区 Manifest；计算初始化顺序集合，并保存为 运行或工作区 Manifest中的对应字段；计算组合或计算已有值，并保存为 当前处理结果的目录。
创建当前处理结果的目录对应的目录；将处理结果写入当前输入内容指定的文件；将处理结果写入当前输入内容指定的文件。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `load_skill_package` 读取或查询当前阶段需要的数据，退出时自动清理资源。
```

#### `test_loader_rejects_symlink`

- **源码**：`tests/test_skill_manifest_loader.py:89`
- **签名**：`def test_loader_rejects_symlink(tmp_path)`
- **作用**：在论文复现 Agent Skill/Plugin 的清单加载、权限隔离、运行时和调试日志验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `write_skill_package` 持久化或更新当前领域数据，并把结果记为 该调用返回的结果；计算组合或计算已有值，并保存为 当前处理结果；将处理结果写入当前处理结果指定的文件；调用 `symlink_to` 完成该函数的一项辅助处理。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `load_skill_package` 读取或查询当前阶段需要的数据，退出时自动清理资源。
```

#### `test_discovery_is_stably_sorted`

- **源码**：`tests/test_skill_manifest_loader.py:99`
- **签名**：`def test_discovery_is_stably_sorted(tmp_path)`
- **作用**：在论文复现 Agent Skill/Plugin 的清单加载、权限隔离、运行时和调试日志验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
遍历当前可迭代输入，每次把当前项记为当前处理结果的 ID，然后调用 `write_skill_package` 持久化或更新当前领域数据。
调用 `discover_skill_packages` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；断言当前输入内容等于['alpha_skill', 'zeta_skill']；不满足就终止当前测试或流程。
```

### `tests/test_skill_registry.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_context`

- **源码**：`tests/test_skill_registry.py:27`
- **签名**：`def _context(tmp_path) -> SkillInvocationContext`
- **作用**：在论文复现 Agent Skill/Plugin 的清单加载、权限隔离、运行时和调试日志验证阶段中，该函数接收临时工作目录路径，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `SkillInvocationContext` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`SkillInvocationContext`
- **语义**：返回 `SkillInvocationContext` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `SkillInvocationContext` 结构化领域对象。
```

#### `_bound_registry`

- **源码**：`tests/test_skill_registry.py:37`
- **签名**：`def _bound_registry(tmp_path, *, enabled: bool, calls: list[str])`
- **作用**：在论文复现 Agent Skill/Plugin 的清单加载、权限隔离、运行时和调试日志验证阶段中，该函数接收临时工作目录路径、功能是否启用的开关、工具或模型调用记录集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `enabled` | `bool` | 布尔条件或能力开关，用于控制流程分支。 |
| `calls` | `list[str]` | 工具或模型调用记录集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
调用 `write_skill_package` 持久化或更新当前领域数据，并把结果记为 该调用返回的结果。
定义内部辅助函数 `handler`，供当前函数在后续步骤中调用。
构造 `SkillRegistry` 结构化领域对象，并把结果记为 组件注册表；调用 `register` 完成该函数的一项辅助处理，并把结果记为 边界值；返回当前构造的顺序或去重集合。
```

#### `_bound_registry.handler`

- **源码**：`tests/test_skill_registry.py:40`
- **签名**：`def handler(payload: EchoInput, runtime) -> EchoOutput`
- **作用**：在论文复现 Agent Skill/Plugin 的清单加载、权限隔离、运行时和调试日志验证阶段中，该函数接收结构化请求载荷、运行时环境，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `EchoOutput` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `payload` | `EchoInput` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `runtime` | `未显式标注` | 运行时环境；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`EchoOutput`
- **语义**：返回 `EchoOutput` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
移除运行时环境中的当前内容；把当前字段值追加或合并到工具或模型调用记录集合；构造并返回 `EchoOutput` 结构化领域对象。
```

#### `test_disabled_skill_does_not_call_handler`

- **源码**：`tests/test_skill_registry.py:61`
- **签名**：`def test_disabled_skill_does_not_call_handler(tmp_path)`
- **作用**：在论文复现 Agent Skill/Plugin 的清单加载、权限隔离、运行时和调试日志验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
将 工具或模型调用记录集合 初始化为空列表，用来收集后续结果；调用 `_bound_registry` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；调用组件注册表完成模型或 Runnable 处理，并把结果记为 阶段处理结果；断言失败不为空；不满足就终止当前测试或流程。
断言待解析或验证的代码等于'SKILL_DISABLED'；不满足就终止当前测试或流程；断言工具集合等于[]；不满足就终止当前测试或流程；断言工具或模型调用记录集合等于[]；不满足就终止当前测试或流程。
```

#### `test_stale_skill_hash_does_not_call_handler`

- **源码**：`tests/test_skill_registry.py:85`
- **签名**：`def test_stale_skill_hash_does_not_call_handler(tmp_path)`
- **作用**：在论文复现 Agent Skill/Plugin 的清单加载、权限隔离、运行时和调试日志验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
将 工具或模型调用记录集合 初始化为空列表，用来收集后续结果；调用 `_bound_registry` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；调用组件注册表完成模型或 Runnable 处理，并把结果记为 阶段处理结果；断言失败不为空；不满足就终止当前测试或流程。
断言待解析或验证的代码等于'SKILL_STALE_IDENTITY'；不满足就终止当前测试或流程；断言工具集合等于[]；不满足就终止当前测试或流程；断言工具或模型调用记录集合等于[]；不满足就终止当前测试或流程。
```

#### `test_matching_hash_returns_typed_output`

- **源码**：`tests/test_skill_registry.py:109`
- **签名**：`def test_matching_hash_returns_typed_output(tmp_path)`
- **作用**：在论文复现 Agent Skill/Plugin 的清单加载、权限隔离、运行时和调试日志验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
将 工具或模型调用记录集合 初始化为空列表，用来收集后续结果；调用 `_bound_registry` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；调用组件注册表完成模型或 Runnable 处理，并把结果记为 阶段处理结果；断言失败为空；不满足就终止当前测试或流程。
断言输出结果等于{'diagnosis': 'diagnosed'}；不满足就终止当前测试或流程；断言输出结果的 SHA-256不为空；不满足就终止当前测试或流程；断言工具或模型调用记录集合等于['diagnosed']；不满足就终止当前测试或流程。
```

### `tests/test_skill_runtime.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_cuda_manifest`

- **源码**：`tests/test_skill_runtime.py:16`
- **签名**：`def _cuda_manifest() -> SkillManifest`
- **作用**：在论文复现 Agent Skill/Plugin 的清单加载、权限隔离、运行时和调试日志验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`SkillManifest`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
将外部表示解析为结构化内容，并把结果记为 结构化请求载荷；复制、序列化或校验结构化领域对象，并返回处理结果。
```

#### `_context`

- **源码**：`tests/test_skill_runtime.py:28`
- **签名**：`def _context(tmp_path, *, capabilities: list[str])`
- **作用**：在论文复现 Agent Skill/Plugin 的清单加载、权限隔离、运行时和调试日志验证阶段中，该函数接收临时工作目录路径、当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `capabilities` | `list[str]` | `list[str]` 元素集合；元素代表的业务对象由参数名 `capabilities` 和调用位置确定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
计算组合或计算已有值，并保存为 本次复现工作区；计算组合或计算已有值，并保存为 运行；创建本次复现工作区对应的目录；创建运行对应的目录。
构造并返回 `SkillInvocationContext` 结构化领域对象。
```

#### `test_runtime_rejects_undeclared_tool`

- **源码**：`tests/test_skill_runtime.py:42`
- **签名**：`def test_runtime_rejects_undeclared_tool(tmp_path)`
- **作用**：在论文复现 Agent Skill/Plugin 的清单加载、权限隔离、运行时和调试日志验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `SkillRuntime` 结构化领域对象，并把结果记为 运行时环境。
在上下文“调用 `raises` 完成该函数的一项辅助处理，并把上下文资源交给当前处理结果”中调用 `call_tool` 完成该函数的一项辅助处理，退出时自动清理资源。
断言待解析或验证的代码等于'SKILL_TOOL_NOT_DECLARED'；不满足就终止当前测试或流程；断言工具集合等于[]；不满足就终止当前测试或流程。
```

#### `test_runtime_rejects_missing_host_capability`

- **源码**：`tests/test_skill_runtime.py:63`
- **签名**：`def test_runtime_rejects_missing_host_capability(tmp_path)`
- **作用**：在论文复现 Agent Skill/Plugin 的清单加载、权限隔离、运行时和调试日志验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `SkillRuntime` 结构化领域对象，并把结果记为 运行时环境。
在上下文“调用 `raises` 完成该函数的一项辅助处理，并把上下文资源交给当前处理结果”中调用 `call_tool` 完成该函数的一项辅助处理，退出时自动清理资源。
断言待解析或验证的代码等于'SKILL_CAPABILITY_NOT_GRANTED'；不满足就终止当前测试或流程；断言工具集合等于[]；不满足就终止当前测试或流程。
```

#### `test_runtime_rejects_trusted_node_tool`

- **源码**：`tests/test_skill_runtime.py:83`
- **签名**：`def test_runtime_rejects_trusted_node_tool(tmp_path)`
- **作用**：在论文复现 Agent Skill/Plugin 的清单加载、权限隔离、运行时和调试日志验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
复制、序列化或校验结构化领域对象，并把结果记为 结构化请求载荷；计算初始化顺序集合，并保存为 结构化请求载荷中的对应字段；将 结构化请求载荷中的对应字段 初始化为空列表，用来收集后续结果；计算使用固定配置或常量值，并保存为 结构化请求载荷中的对应字段。
构造 `SkillRuntime` 结构化领域对象，并把结果记为 运行时环境。
在上下文“调用 `raises` 完成该函数的一项辅助处理，并把上下文资源交给当前处理结果”中调用 `call_tool` 完成该函数的一项辅助处理，退出时自动清理资源。
断言待解析或验证的代码等于'SKILL_TOOL_EXPOSURE_DENIED'；不满足就终止当前测试或流程；断言工具集合等于[]；不满足就终止当前测试或流程。
```

#### `test_runtime_enforces_tool_call_budget`

- **源码**：`tests/test_skill_runtime.py:109`
- **签名**：`def test_runtime_enforces_tool_call_budget(tmp_path)`
- **作用**：在论文复现 Agent Skill/Plugin 的清单加载、权限隔离、运行时和调试日志验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
复制、序列化或校验结构化领域对象，并把结果记为 结构化请求载荷；计算初始化顺序集合，并保存为 结构化请求载荷中的对应字段；将 结构化请求载荷中的对应字段 初始化为空列表，用来收集后续结果；计算使用固定配置或常量值，并保存为 结构化请求载荷中的对应字段。
构造 `SkillRuntime` 结构化领域对象，并把结果记为 运行时环境；调用 `call_tool` 完成该函数的一项辅助处理。
在上下文“调用 `raises` 完成该函数的一项辅助处理，并把上下文资源交给当前处理结果”中调用 `call_tool` 完成该函数的一项辅助处理，退出时自动清理资源。
断言待解析或验证的代码等于'SKILL_TOOL_BUDGET_EXCEEDED'；不满足就终止当前测试或流程；断言工具集合 的长度等于1；不满足就终止当前测试或流程。
```

### `tests/test_tool_calling_authority.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_chat_tool_catalog_contains_no_mutation_names`

- **源码**：`tests/test_tool_calling_authority.py:22`
- **签名**：`def test_chat_tool_catalog_contains_no_mutation_names() -> None`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `join` 完成该函数的一项辅助处理，并把结果记为 待处理的论文或源码材料；断言由当前处理结果组成的集合或迭代器中每一项都满足“测试或状态标记不属于待处理的论文或源码材料”的项；不满足就终止当前测试或流程。
```

#### `test_tool_calling_package_has_no_shell_or_process_imports`

- **源码**：`tests/test_tool_calling_authority.py:30`
- **签名**：`def test_tool_calling_package_has_no_shell_or_process_imports() -> None`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算初始化去重集合，并保存为 当前处理结果。
遍历辅助操作产生的可迭代结果（枚举当前输入内容下符合范围的文件系统项），每次把当前项记为文件或目录路径：
    将 Python 源码解析为抽象语法树，并把结果记为 该调用返回的结果；将 当前处理结果 初始化为空去重集合，用来收集后续结果。
    遍历语法树节点集合，每次把当前项记为当前流程节点：
        如果“计算数量、边界或类型判断结果”后得到肯定结果：
            把新的处理结果追加或合并到当前处理结果。
        否则：
            如果“计算数量、边界或类型判断结果”后得到肯定结果 且 Python 模块有值或为真，就把前一步操作返回对象中的对应字段追加或合并到当前处理结果。
    断言“调用 `isdisjoint` 完成该函数的一项辅助处理”后得到肯定结果，失败时附带断言说明；不满足就终止当前测试或流程。
```

#### `test_tool_calling_does_not_import_execution_or_approval_modules`

- **源码**：`tests/test_tool_calling_authority.py:47`
- **签名**：`def test_tool_calling_does_not_import_execution_or_approval_modules() -> None`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算初始化去重集合，并保存为 被策略禁止的内容或操作。
遍历辅助操作产生的可迭代结果（枚举当前输入内容下符合范围的文件系统项），每次把当前项记为文件或目录路径，然后读取文件或目录路径中的文件内容，并把结果记为 数据来源标记；断言由被策略禁止的内容或操作组成的集合或迭代器中每一项都满足“当前处理项不属于数据来源标记”的项，失败时附带断言说明；不满足就终止当前测试或流程。
```

#### `test_live_research_tool_is_not_in_chat_catalog`

- **源码**：`tests/test_tool_calling_authority.py:60`
- **签名**：`def test_live_research_tool_is_not_in_chat_catalog() -> None`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
断言当前输入内容不属于辅助操作“调用 `values` 完成该函数的一项辅助处理”的结果；不满足就终止当前测试或流程。
```

### `tests/test_tool_calling_catalog.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_FakeContextBuilder.build`

- **源码**：`tests/test_tool_calling_catalog.py:33`
- **签名**：`def build(self, *, job_id: str, question: str)`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收复现任务 ID、论文复现问题或用户问题，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `question` | `str` | 论文复现问题或用户问题；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
构造并返回 `GroundingBundle` 结构化领域对象。
```

#### `_FakeContextBuilder.build_job_only`

- **源码**：`tests/test_tool_calling_catalog.py:49`
- **签名**：`def build_job_only(self, *, job_id: str, question: str)`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收复现任务 ID、论文复现问题或用户问题，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `question` | `str` | 论文复现问题或用户问题；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
调用 `build` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `chat_tool_registry`

- **源码**：`tests/test_tool_calling_catalog.py:54`
- **签名**：`def chat_tool_registry() -> ToolRegistry`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ToolRegistry` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`ToolRegistry`
- **语义**：返回 `ToolRegistry` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `build_chat_evidence_tool_registry` 组装当前阶段需要的领域对象，并返回处理结果。
```

#### `registry_with_research_tool`

- **源码**：`tests/test_tool_calling_catalog.py:63`
- **签名**：`def registry_with_research_tool(chat_tool_registry) -> ToolRegistry`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，Register a research browser tool in addition to chat tools。该函数接收对话工具注册表，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ToolRegistry` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `chat_tool_registry` | `未显式标注` | 名为 `chat_tool_registry` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`ToolRegistry`
- **语义**：返回 `ToolRegistry` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `register` 完成该函数的一项辅助处理；返回对话工具注册表的当前值。
```

#### `test_catalog_contains_only_static_read_tools`

- **源码**：`tests/test_tool_calling_catalog.py:90`
- **签名**：`def test_catalog_contains_only_static_read_tools(chat_tool_registry: 未显式标注) -> None`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收对话工具注册表，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `chat_tool_registry` | `未显式标注` | 名为 `chat_tool_registry` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `build_provider_tool_catalog` 组装当前阶段需要的领域对象，并把结果记为 模型、工具或 Artifact 目录；断言当前输入内容等于辅助操作“构造临时集合、映射或轻量领域对象”的结果；不满足就终止当前测试或流程；断言当前可迭代输入中每一项都满足“当前输入内容不属于辅助操作“从当前处理结果中的对应字段读取所需的状态或领域记录”的结果”的项；不满足就终止当前测试或流程；断言模型、工具或 Artifact 目录的 SHA-256 的长度等于64；不满足就终止当前测试或流程。
```

#### `test_catalog_does_not_auto_expose_research_network_tool`

- **源码**：`tests/test_tool_calling_catalog.py:106`
- **签名**：`def test_catalog_does_not_auto_expose_research_network_tool(registry_with_research_tool: 未显式标注) -> None`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收注册表工具，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `registry_with_research_tool` | `未显式标注` | 名为 `registry_with_research_tool` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `build_provider_tool_catalog` 组装当前阶段需要的领域对象，并把结果记为 模型、工具或 Artifact 目录；断言当前可迭代输入中每一项都满足“当前处理结果的名称不等于'browser.collect_research_evidence'”的项；不满足就终止当前测试或流程。
```

#### `test_catalog_rejects_write_effect`

- **源码**：`tests/test_tool_calling_catalog.py:117`
- **签名**：`def test_catalog_rejects_write_effect(chat_tool_registry) -> None`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收对话工具注册表，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `chat_tool_registry` | `未显式标注` | 名为 `chat_tool_registry` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算使用固定配置或常量值，并保存为 对象名称；从对话工具注册表读取所需的状态或领域记录，并把结果记为 该调用返回的结果；调用 `replace` 完成该函数的一项辅助处理，并把结果记为 当前处理结果中的对应字段。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `build_provider_tool_catalog` 组装当前阶段需要的领域对象，退出时自动清理资源。
```

#### `test_catalog_hash_is_stable`

- **源码**：`tests/test_tool_calling_catalog.py:131`
- **签名**：`def test_catalog_hash_is_stable(chat_tool_registry) -> None`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收对话工具注册表，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `chat_tool_registry` | `未显式标注` | 名为 `chat_tool_registry` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `build_provider_tool_catalog` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果；调用 `build_provider_tool_catalog` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果；断言模型、工具或 Artifact 目录的 SHA-256等于模型、工具或 Artifact 目录的 SHA-256；不满足就终止当前测试或流程。
```

#### `test_catalog_by_alias_returns_binding`

- **源码**：`tests/test_tool_calling_catalog.py:143`
- **签名**：`def test_catalog_by_alias_returns_binding(chat_tool_registry) -> None`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收对话工具注册表，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `chat_tool_registry` | `未显式标注` | 名为 `chat_tool_registry` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `build_provider_tool_catalog` 组装当前阶段需要的领域对象，并把结果记为 模型、工具或 Artifact 目录；调用 `by_alias` 完成该函数的一项辅助处理，并把结果记为 资源绑定记录；断言资源绑定记录不为空；不满足就终止当前测试或流程；断言当前处理结果的名称等于'chat.get_reproduction_status'；不满足就终止当前测试或流程。
```

#### `test_catalog_by_alias_returns_none_for_unknown`

- **源码**：`tests/test_tool_calling_catalog.py:150`
- **签名**：`def test_catalog_by_alias_returns_none_for_unknown(chat_tool_registry: 未显式标注) -> None`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收对话工具注册表，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `chat_tool_registry` | `未显式标注` | 名为 `chat_tool_registry` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `build_provider_tool_catalog` 组装当前阶段需要的领域对象，并把结果记为 模型、工具或 Artifact 目录；断言辅助操作“调用 `by_alias` 完成该函数的一项辅助处理”的结果为空；不满足就终止当前测试或流程。
```

### `tests/test_tool_calling_chat_integration.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_tool_evidence_enters_final_citation_allowlist`

- **源码**：`tests/test_tool_calling_chat_integration.py:14`
- **签名**：`def test_tool_evidence_enters_final_citation_allowlist(tmp_path) -> None`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `HandlerRecorder` 结构化领域对象，并把结果记为 该调用返回的结果；调用 `build_fixture_loop` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果；调用 `_service` 完成该函数的一项辅助处理，并把结果记为 领域服务对象；调用 `ask` 完成该函数的一项辅助处理，并把结果记为 结构化响应。
断言业务内容等于'当前任务失败。'；不满足就终止当前测试或流程；断言论文引用证据的 ID等于'job:current'；不满足就终止当前测试或流程；断言工具不为空；不满足就终止当前测试或流程；断言当前状态等于'completed'；不满足就终止当前测试或流程。
断言工具或模型调用记录集合 的长度等于1；不满足就终止当前测试或流程。
```

#### `test_idempotent_replay_does_not_run_tool_loop_twice`

- **源码**：`tests/test_tool_calling_chat_integration.py:53`
- **签名**：`def test_idempotent_replay_does_not_run_tool_loop_twice(tmp_path) -> None`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `HandlerRecorder` 结构化领域对象，并把结果记为 该调用返回的结果；调用 `build_fixture_loop` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果；调用 `_service` 完成该函数的一项辅助处理，并把结果记为 领域服务对象；调用 `ask` 完成该函数的一项辅助处理，并把结果记为 第一项。
调用 `ask` 完成该函数的一项辅助处理，并把结果记为 第二项；断言工具或模型调用记录集合 的长度等于1；不满足就终止当前测试或流程；断言重放的是真；不满足就终止当前测试或流程；断言工具等于工具；不满足就终止当前测试或流程。
```

#### `test_tool_selection_free_text_is_discarded`

- **源码**：`tests/test_tool_calling_chat_integration.py:95`
- **签名**：`def test_tool_selection_free_text_is_discarded(tmp_path) -> None`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `HandlerRecorder` 结构化领域对象，并把结果记为 该调用返回的结果；调用 `build_fixture_loop` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果；调用 `_service` 完成该函数的一项辅助处理，并把结果记为 领域服务对象；调用 `ask` 完成该函数的一项辅助处理，并把结果记为 结构化响应。
断言当前输入内容不属于业务内容；不满足就终止当前测试或流程；断言当前输入内容属于业务内容；不满足就终止当前测试或流程。
```

#### `test_feature_disabled_uses_legacy_context`

- **源码**：`tests/test_tool_calling_chat_integration.py:123`
- **签名**：`def test_feature_disabled_uses_legacy_context(tmp_path) -> None`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_service` 完成该函数的一项辅助处理，并把结果记为 领域服务对象；调用 `ask` 完成该函数的一项辅助处理，并把结果记为 结构化响应；断言工具为空；不满足就终止当前测试或流程；断言Artifact的 ID等于'report'；不满足就终止当前测试或流程。
```

### `tests/test_tool_calling_evidence_tools.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `FakeContextBuilder.__init__`

- **源码**：`tests/test_tool_calling_evidence_tools.py:15`
- **签名**：`def __init__(self) -> None`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
将 工具或模型调用记录集合 初始化为空列表，用来收集后续结果。
```

#### `FakeContextBuilder._bundle`

- **源码**：`tests/test_tool_calling_evidence_tools.py:18`
- **签名**：`def _bundle(self, job_id: str) -> GroundingBundle`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收复现任务 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `GroundingBundle` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`GroundingBundle`
- **语义**：返回 `GroundingBundle` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `GroundingBundle` 结构化领域对象。
```

#### `FakeContextBuilder.build_job_only`

- **源码**：`tests/test_tool_calling_evidence_tools.py:35`
- **签名**：`def build_job_only(self, *, job_id: str, question: str)`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收复现任务 ID、论文复现问题或用户问题，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `question` | `str` | 论文复现问题或用户问题；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
把新的处理结果追加或合并到工具或模型调用记录集合；调用 `_bundle` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `FakeContextBuilder.build`

- **源码**：`tests/test_tool_calling_evidence_tools.py:39`
- **签名**：`def build(self, *, job_id: str, question: str)`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收复现任务 ID、论文复现问题或用户问题，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `question` | `str` | 论文复现问题或用户问题；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
把新的处理结果追加或合并到工具或模型调用记录集合；调用 `_bundle` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `_context`

- **源码**：`tests/test_tool_calling_evidence_tools.py:44`
- **签名**：`def _context(job_id: str = "job-server") -> ToolInvocationContext`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收复现任务 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ToolInvocationContext` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。；默认 'job-server' |

**输出**

- **Python 类型**：`ToolInvocationContext`
- **语义**：返回 `ToolInvocationContext` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `ToolInvocationContext` 结构化领域对象。
```

#### `test_status_tool_uses_server_job_scope`

- **源码**：`tests/test_tool_calling_evidence_tools.py:57`
- **签名**：`def test_status_tool_uses_server_job_scope() -> None`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `FakeContextBuilder` 结构化领域对象，并把结果记为 领域对象构造器；调用 `build_chat_evidence_tool_registry` 组装当前阶段需要的领域对象，并把结果记为 组件注册表；调用组件注册表完成模型或 Runnable 处理，并把结果记为 阶段处理结果；断言失败为空；不满足就终止当前测试或流程。
断言工具或模型调用记录集合中的对应字段中的对应字段等于'job-server'；不满足就终止当前测试或流程；断言复现任务 ID等于'job-server'；不满足就终止当前测试或流程。
```

#### `test_model_job_id_is_rejected_before_context_builder`

- **源码**：`tests/test_tool_calling_evidence_tools.py:74`
- **签名**：`def test_model_job_id_is_rejected_before_context_builder() -> None`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `FakeContextBuilder` 结构化领域对象，并把结果记为 领域对象构造器；调用 `build_chat_evidence_tool_registry` 组装当前阶段需要的领域对象，并把结果记为 组件注册表；调用组件注册表完成模型或 Runnable 处理，并把结果记为 阶段处理结果；断言失败不为空；不满足就终止当前测试或流程。
断言待解析或验证的代码等于'TOOL_INPUT_INVALID'；不满足就终止当前测试或流程；断言工具或模型调用记录集合等于[]；不满足就终止当前测试或流程。
```

#### `test_missing_server_job_scope_fails_closed`

- **源码**：`tests/test_tool_calling_evidence_tools.py:91`
- **签名**：`def test_missing_server_job_scope_fails_closed() -> None`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `FakeContextBuilder` 结构化领域对象，并把结果记为 领域对象构造器；调用 `build_chat_evidence_tool_registry` 组装当前阶段需要的领域对象，并把结果记为 组件注册表；调用组件注册表完成模型或 Runnable 处理，并把结果记为 阶段处理结果；断言失败不为空；不满足就终止当前测试或流程。
断言待解析或验证的代码等于'TOOL_EVIDENCE_SCOPE_INVALID'；不满足就终止当前测试或流程；断言工具或模型调用记录集合等于[]；不满足就终止当前测试或流程。
```

### `tests/test_tool_calling_loop.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_run`

- **源码**：`tests/test_tool_calling_loop.py:18`
- **签名**：`def _run(loop)`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `loop` | `未显式标注` | 名为 `loop` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
调用 `run` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `test_no_tool_call_finishes_without_handler`

- **源码**：`tests/test_tool_calling_loop.py:27`
- **签名**：`def test_no_tool_call_finishes_without_handler() -> None`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `HandlerRecorder` 结构化领域对象，并把结果记为 该调用返回的结果；构造 `ScriptedToolTurnInvoker` 结构化领域对象，并把结果记为 工具或模型调用器；调用 `_run` 完成该函数的一项辅助处理，并把结果记为 执行结论；断言当前状态等于'no_tools_needed'；不满足就终止当前测试或流程。
断言工具或模型调用记录集合等于[]；不满足就终止当前测试或流程；断言证据来源集合等于[]；不满足就终止当前测试或流程；断言工具或模型调用记录集合等于[]；不满足就终止当前测试或流程；调用 `validate_trace_hash` 校验当前输入或状态。
```

#### `test_one_tool_call_returns_evidence_then_stops`

- **源码**：`tests/test_tool_calling_loop.py:41`
- **签名**：`def test_one_tool_call_returns_evidence_then_stops() -> None`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `HandlerRecorder` 结构化领域对象，并把结果记为 该调用返回的结果；构造 `ScriptedToolTurnInvoker` 结构化领域对象，并把结果记为 工具或模型调用器；调用 `_run` 完成该函数的一项辅助处理，并把结果记为 执行结论；断言当前状态等于'completed'；不满足就终止当前测试或流程。
断言工具或模型调用记录集合 的长度等于1；不满足就终止当前测试或流程；断言当前状态等于'succeeded'；不满足就终止当前测试或流程；断言MCP Tool 名称等于'chat.inspect_failure_context'；不满足就终止当前测试或流程；断言工具或模型调用记录集合中的对应字段中的对应字段等于'job-1'；不满足就终止当前测试或流程。
断言论文引用证据的 ID等于'job:current'；不满足就终止当前测试或流程；读取当前处理结果中的对应字段，并保存为 第二项集合；调用 `next` 完成该函数的一项辅助处理，并把结果记为 工具；断言工具的 ID等于'provider-call-1'；不满足就终止当前测试或流程。
```

#### `test_model_cannot_supply_another_job_id`

- **源码**：`tests/test_tool_calling_loop.py:76`
- **签名**：`def test_model_cannot_supply_another_job_id() -> None`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `HandlerRecorder` 结构化领域对象，并把结果记为 该调用返回的结果；构造 `ScriptedToolTurnInvoker` 结构化领域对象，并把结果记为 工具或模型调用器；调用 `_run` 完成该函数的一项辅助处理，并把结果记为 执行结论；断言工具或模型调用记录集合等于[]；不满足就终止当前测试或流程。
断言当前状态等于'failed'；不满足就终止当前测试或流程；断言错误等于'TOOL_INPUT_INVALID'；不满足就终止当前测试或流程。
```

#### `test_unknown_tool_is_blocked_without_directory_disclosure`

- **源码**：`tests/test_tool_calling_loop.py:97`
- **签名**：`def test_unknown_tool_is_blocked_without_directory_disclosure() -> None`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `HandlerRecorder` 结构化领域对象，并把结果记为 该调用返回的结果；构造 `ScriptedToolTurnInvoker` 结构化领域对象，并把结果记为 工具或模型调用器；调用 `_run` 完成该函数的一项辅助处理，并把结果记为 执行结论；断言当前状态等于'policy_blocked'；不满足就终止当前测试或流程。
断言工具或模型调用记录集合等于[]；不满足就终止当前测试或流程；断言工具或模型调用记录集合等于[]；不满足就终止当前测试或流程。
```

#### `test_parallel_tool_calls_are_blocked`

- **源码**：`tests/test_tool_calling_loop.py:117`
- **签名**：`def test_parallel_tool_calls_are_blocked() -> None`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `AIMessage` 结构化领域对象，并把结果记为 面向用户或日志的提示信息；构造 `HandlerRecorder` 结构化领域对象，并把结果记为 该调用返回的结果；调用 `_run` 完成该函数的一项辅助处理，并把结果记为 执行结论；断言当前状态等于'policy_blocked'；不满足就终止当前测试或流程。
断言工具或模型调用记录集合等于[]；不满足就终止当前测试或流程。
```

#### `test_repeated_tool_fingerprint_stops_loop`

- **源码**：`tests/test_tool_calling_loop.py:147`
- **签名**：`def test_repeated_tool_fingerprint_stops_loop() -> None`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `tool_call_message` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `tool_call_message` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；构造 `HandlerRecorder` 结构化领域对象，并把结果记为 该调用返回的结果；调用 `_run` 完成该函数的一项辅助处理，并把结果记为 执行结论。
断言当前状态等于'policy_blocked'；不满足就终止当前测试或流程；断言工具或模型调用记录集合 的长度等于1；不满足就终止当前测试或流程；断言工具或模型调用记录集合 的长度等于1；不满足就终止当前测试或流程。
```

#### `test_tool_call_limit_is_hard_boundary`

- **源码**：`tests/test_tool_calling_loop.py:173`
- **签名**：`def test_tool_call_limit_is_hard_boundary() -> None`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `HandlerRecorder` 结构化领域对象，并把结果记为 该调用返回的结果；构造 `ScriptedToolTurnInvoker` 结构化领域对象，并把结果记为 工具或模型调用器；调用 `_run` 完成该函数的一项辅助处理，并把结果记为 执行结论；断言当前状态等于'limit_reached'；不满足就终止当前测试或流程。
断言工具或模型调用记录集合 的长度等于1；不满足就终止当前测试或流程；断言工具或模型调用记录集合 的长度等于1；不满足就终止当前测试或流程。
```

#### `test_tool_selection_text_never_becomes_final_answer`

- **源码**：`tests/test_tool_calling_loop.py:201`
- **签名**：`def test_tool_selection_text_never_becomes_final_answer() -> None`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `HandlerRecorder` 结构化领域对象，并把结果记为 该调用返回的结果；构造 `ScriptedToolTurnInvoker` 结构化领域对象，并把结果记为 工具或模型调用器；调用 `_run` 完成该函数的一项辅助处理，并把结果记为 执行结论；断言当前状态等于'no_tools_needed'；不满足就终止当前测试或流程。
断言证据来源集合等于[]；不满足就终止当前测试或流程；断言“调用 `hasattr` 完成该函数的一项辅助处理”后未得到肯定结果；不满足就终止当前测试或流程。
```

### `tests/test_tool_calling_model_gateway.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `FakeToolBoundModel.__init__`

- **源码**：`tests/test_tool_calling_model_gateway.py:42`
- **签名**：`def __init__(self, message: AIMessage) -> None`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收面向用户或日志的提示信息，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `message` | `AIMessage` | 对话消息记录或消息文本；角色、顺序和内容 Hash 可能参与证据校验。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 面向用户或日志的提示信息 分别保存到同名实例字段；将 当前处理结果 初始化为空列表，用来收集后续结果；计算使用固定配置或常量值，并保存为 当前处理结果。
```

#### `FakeToolBoundModel.bind_tools`

- **源码**：`tests/test_tool_calling_model_gateway.py:47`
- **签名**：`def bind_tools(self, tools, **kwargs)`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收受控工具定义集合、函数关键字参数映射，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `tools` | `未显式标注` | 受控工具定义集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `**kwargs` | `未显式标注` | 额外关键字参数映射。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
把新的处理结果追加或合并到当前处理结果；返回当前对象的当前值。
```

#### `FakeToolBoundModel.invoke`

- **源码**：`tests/test_tool_calling_model_gateway.py:51`
- **签名**：`def invoke(self, messages)`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收对话或日志消息集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `messages` | `未显式标注` | 对话或日志消息集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
将新的计算结果累加或合并到当前处理结果；断言“计算数量、边界或类型判断结果”后得到肯定结果；不满足就终止当前测试或流程；返回面向用户或日志的提示信息的当前值。
```

#### `_gateway`

- **源码**：`tests/test_tool_calling_model_gateway.py:57`
- **签名**：`def _gateway(tmp_path, chat, *, mode="active")`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收临时工作目录路径、对话、MCP 评测或运行模式，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `chat` | `未显式标注` | 名为 `chat` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `mode` | `未显式标注` | MCP 评测或运行模式；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 'active' |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
计算按字段初始化键值映射，并保存为 模型计费配置；调用 `build_test_document` 组装当前阶段需要的领域对象，并把结果记为 论文解析文档；构造 `FakeProviders` 结构化领域对象，并把结果记为 模型服务商配置集合；调用 `build_test_gateway` 组装当前阶段需要的领域对象，并把结果记为 外部服务网关。
返回当前构造的顺序或去重集合。
```

#### `test_gateway_binds_strict_single_tool_calling`

- **源码**：`tests/test_tool_calling_model_gateway.py:77`
- **签名**：`def test_gateway_binds_strict_single_tool_calling(tmp_path) -> None`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `AIMessage` 结构化领域对象，并把结果记为 面向用户或日志的提示信息；构造 `FakeToolBoundModel` 结构化领域对象，并把结果记为 对话；调用 `_gateway` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；调用 `invoke_tool_calling` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果。
断言面向用户或日志的提示信息是面向用户或日志的提示信息；不满足就终止当前测试或流程；断言对话集合等于1；不满足就终止当前测试或流程；断言当前处理结果中的对应字段中的对应字段是真；不满足就终止当前测试或流程；断言当前处理结果中的对应字段中的对应字段是假；不满足就终止当前测试或流程。
断言当前处理结果中的对应字段中的对应字段等于'auto'；不满足就终止当前测试或流程；断言记录不为空；不满足就终止当前测试或流程；断言类别等于'chat_tool_selection'；不满足就终止当前测试或流程；断言实际集合等于100；不满足就终止当前测试或流程。
断言实际集合等于20；不满足就终止当前测试或流程。
```

#### `test_gateway_missing_usage_uses_reservation_upper_bound`

- **源码**：`tests/test_tool_calling_model_gateway.py:115`
- **签名**：`def test_gateway_missing_usage_uses_reservation_upper_bound(tmp_path: 未显式标注) -> None`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `FakeToolBoundModel` 结构化领域对象，并把结果记为 对话；调用 `_gateway` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；调用 `invoke_tool_calling` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果；断言记录不为空；不满足就终止当前测试或流程。
断言当前处理结果等于'reservation_upper_bound'；不满足就终止当前测试或流程；断言实际集合等于预留的输入 token 数；不满足就终止当前测试或流程。
```

#### `test_gateway_off_mode_does_not_write_ledger`

- **源码**：`tests/test_tool_calling_model_gateway.py:135`
- **签名**：`def test_gateway_off_mode_does_not_write_ledger(tmp_path) -> None`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `FakeToolBoundModel` 结构化领域对象，并把结果记为 对话；调用 `_gateway` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；调用 `invoke_tool_calling` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果；断言工具调用记录的 ID为空；不满足就终止当前测试或流程。
断言记录为空；不满足就终止当前测试或流程。
```

### `tests/test_tool_calling_schemas.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_empty_tool_input_accepts_no_fields`

- **源码**：`tests/test_tool_calling_schemas.py:21`
- **签名**：`def test_empty_tool_input_accepts_no_fields() -> None`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `EmptyToolInput` 结构化领域对象，并把结果记为 模型标识或模型配置；断言辅助操作“复制、序列化或校验结构化领域对象”的结果等于{}；不满足就终止当前测试或流程。
```

#### `test_search_input_rejects_empty_query`

- **源码**：`tests/test_tool_calling_schemas.py:26`
- **签名**：`def test_search_input_rejects_empty_query() -> None`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中构造 `SearchReproductionEvidenceInput` 结构化领域对象，退出时自动清理资源。
```

#### `test_search_input_rejects_duplicate_source_types`

- **源码**：`tests/test_tool_calling_schemas.py:31`
- **签名**：`def test_search_input_rejects_duplicate_source_types() -> None`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中构造 `SearchReproductionEvidenceInput` 结构化领域对象，退出时自动清理资源。
```

#### `test_search_input_rejects_control_chars_in_query`

- **源码**：`tests/test_tool_calling_schemas.py:39`
- **签名**：`def test_search_input_rejects_control_chars_in_query() -> None`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中构造 `SearchReproductionEvidenceInput` 结构化领域对象，退出时自动清理资源。
```

#### `test_inspect_failure_input_defaults`

- **源码**：`tests/test_tool_calling_schemas.py:44`
- **签名**：`def test_inspect_failure_input_defaults() -> None`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `InspectFailureContextInput` 结构化领域对象，并把结果记为 模型标识或模型配置；断言当前处理结果等于'当前失败原因'；不满足就终止当前测试或流程；断言结果数量上限等于5；不满足就终止当前测试或流程。
```

#### `test_inspect_failure_input_rejects_empty_focus`

- **源码**：`tests/test_tool_calling_schemas.py:50`
- **签名**：`def test_inspect_failure_input_rejects_empty_focus() -> None`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中构造 `InspectFailureContextInput` 结构化领域对象，退出时自动清理资源。
```

#### `test_tool_evidence_item_requires_content`

- **源码**：`tests/test_tool_calling_schemas.py:55`
- **签名**：`def test_tool_evidence_item_requires_content() -> None`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `ChatCitation` 结构化领域对象，并把结果记为 论文引用证据。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中构造 `ToolEvidenceItem` 结构化领域对象，退出时自动清理资源。
```

#### `test_evidence_tool_output_max_items`

- **源码**：`tests/test_tool_calling_schemas.py:65`
- **签名**：`def test_evidence_tool_output_max_items() -> None`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `ChatCitation` 结构化领域对象，并把结果记为 论文引用证据；遍历并筛选输入，将整理后的结果保存为 待处理项集合。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中构造 `EvidenceToolOutput` 结构化领域对象，退出时自动清理资源。
```

#### `test_provider_tool_spec_requires_strict`

- **源码**：`tests/test_tool_calling_schemas.py:79`
- **签名**：`def test_provider_tool_spec_requires_strict() -> None`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中构造 `ProviderToolSpec` 结构化领域对象，退出时自动清理资源。
```

#### `test_provider_tool_spec_requires_all_fields`

- **源码**：`tests/test_tool_calling_schemas.py:95`
- **签名**：`def test_provider_tool_spec_requires_all_fields() -> None`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中构造 `ProviderToolSpec` 结构化领域对象，退出时自动清理资源。
```

#### `test_provider_tool_catalog_rejects_duplicate_aliases`

- **源码**：`tests/test_tool_calling_schemas.py:106`
- **签名**：`def test_provider_tool_catalog_rejects_duplicate_aliases() -> None`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `ProviderToolSpec` 结构化领域对象，并把结果记为 该调用返回的结果；构造 `ProviderToolBinding` 结构化领域对象，并把结果记为 资源绑定记录。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中构造 `ProviderToolCatalog` 结构化领域对象，退出时自动清理资源。
```

#### `test_normalized_tool_call_validates_pattern`

- **源码**：`tests/test_tool_calling_schemas.py:131`
- **签名**：`def test_normalized_tool_call_validates_pattern() -> None`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中构造 `NormalizedToolCall` 结构化领域对象，退出时自动清理资源。
```

#### `test_tool_loop_trace_validates_call_count`

- **源码**：`tests/test_tool_calling_schemas.py:140`
- **签名**：`def test_tool_loop_trace_validates_call_count() -> None`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中构造 `ToolLoopTrace` 结构化领域对象，退出时自动清理资源。
```

#### `test_tool_loop_call_trace_validates_status`

- **源码**：`tests/test_tool_calling_schemas.py:164`
- **签名**：`def test_tool_loop_call_trace_validates_status() -> None`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中构造 `ToolLoopCallTrace` 结构化领域对象，退出时自动清理资源。
```

### `tests/tool_calling_helpers.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_output`

- **源码**：`tests/tool_calling_helpers.py:37`
- **签名**：`def _output(label: str) -> EvidenceToolOutput`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `EvidenceToolOutput` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `label` | `str` | 名为 `label` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`EvidenceToolOutput`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
构造并返回 `EvidenceToolOutput` 结构化领域对象。
```

#### `build_fixture_registry`

- **源码**：`tests/tool_calling_helpers.py:54`
- **签名**：`def build_fixture_registry(recorder: HandlerRecorder) -> ToolRegistry`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收当前处理结果，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `ToolRegistry` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `recorder` | `HandlerRecorder` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |

**输出**

- **Python 类型**：`ToolRegistry`
- **语义**：返回 `ToolRegistry` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造 `ToolRegistry` 结构化领域对象，并把结果记为 组件注册表；计算初始化顺序集合，并保存为 当前处理结果。
遍历由当前处理结果组成的集合或迭代器，每次把当前项记为多个解包结果：
    定义内部辅助函数 `handler`，供当前函数在后续步骤中调用。
    调用 `register` 完成该函数的一项辅助处理。
返回组件注册表的当前值。
```

#### `build_fixture_registry.handler`

- **源码**：`tests/tool_calling_helpers.py:81`
- **签名**：`def handler(payload, context, tool_name=name)`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收结构化请求载荷、运行上下文、MCP Tool 名称，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `payload` | `未显式标注` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `context` | `未显式标注` | 运行上下文；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `tool_name` | `未显式标注` | MCP Tool 名称；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 name |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
把新的处理结果追加或合并到工具或模型调用记录集合；调用 `_output` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `tool_call_message`

- **源码**：`tests/tool_calling_helpers.py:119`
- **签名**：`def tool_call_message(alias: str, arguments: dict, call_id: str) -> AIMessage`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收对象别名、结构化调用参数、当前处理结果的 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `AIMessage` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `alias` | `str` | 对象别名；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `arguments` | `dict` | 结构化调用参数；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `call_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`AIMessage`
- **语义**：返回 `AIMessage` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `AIMessage` 结构化领域对象。
```

#### `stop_message`

- **源码**：`tests/tool_calling_helpers.py:138`
- **签名**：`def stop_message() -> AIMessage`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `AIMessage` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`AIMessage`
- **语义**：返回 `AIMessage` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `AIMessage` 结构化领域对象。
```

#### `ScriptedToolTurnInvoker.__init__`

- **源码**：`tests/tool_calling_helpers.py:143`
- **签名**：`def __init__(self, messages: list[AIMessage]) -> None`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收对话或日志消息集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `messages` | `list[AIMessage]` | 对话或日志消息集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造临时集合、映射或轻量领域对象，并把结果记为 对话或日志消息集合；将 当前处理结果 初始化为空列表，用来收集后续结果。
```

#### `ScriptedToolTurnInvoker.invoke`

- **源码**：`tests/tool_calling_helpers.py:147`
- **签名**：`def invoke(self, *, messages, catalog, job_id) -> ToolModelTurn`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收对话或日志消息集合、模型、工具或 Artifact 目录、复现任务 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ToolModelTurn` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `messages` | `未显式标注` | 对话或日志消息集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `catalog` | `未显式标注` | 持久化或目录访问端口；负责读取、CAS 更新或 Artifact 定位。 |
| `job_id` | `未显式标注` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`ToolModelTurn`
- **语义**：返回 `ToolModelTurn` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
移除模型、工具或 Artifact 目录、复现任务 ID中的当前内容；把新的处理结果追加或合并到当前处理结果。
如果“对话或日志消息集合有值或为真”不成立，就拒绝继续处理并抛出 `AssertionError`，向调用方报告输入或运行失败。
从对话或日志消息集合取出并移除最后一项，并把结果记为 面向用户或日志的提示信息；构造并返回 `ToolModelTurn` 结构化领域对象。
```

#### `build_fixture_loop`

- **源码**：`tests/tool_calling_helpers.py:160`
- **签名**：`def build_fixture_loop(invoker: ScriptedToolTurnInvoker, recorder: HandlerRecorder, max_model_rounds: int, max_tool_calls: int) -> 未显式标注（存在 return）`
- **作用**：在论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段中，该函数接收工具或模型调用器、当前处理结果、最大当前处理结果、最大工具集合，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `invoker` | `ScriptedToolTurnInvoker` | 可调用依赖；由当前函数在受控位置调用。 |
| `recorder` | `HandlerRecorder` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |
| `max_model_rounds` | `int` | 名为 `max_model_rounds` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。；默认 4 |
| `max_tool_calls` | `int` | 名为 `max_tool_calls` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。；默认 3 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
加载这一步需要的外部依赖；调用 `build_fixture_registry` 组装当前阶段需要的领域对象，并把结果记为 组件注册表；构造并返回 `BoundedToolCallingLoop` 结构化领域对象。
```
