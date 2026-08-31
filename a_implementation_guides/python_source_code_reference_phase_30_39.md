# Python 源码函数参考：Phase 30-39

> 自动同步日期：2026-08-19
> 覆盖文件：73；函数/方法：684。
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

- [`app/api/app.py`](#app-api-app-py)：13 个函数/方法
- [`app/api/auth.py`](#app-api-auth-py)：1 个函数/方法
- [`app/api/chat_routes.py`](#app-api-chat-routes-py)：5 个函数/方法
- [`app/api/comparison_routes.py`](#app-api-comparison-routes-py)：4 个函数/方法
- [`app/api/errors.py`](#app-api-errors-py)：57 个函数/方法
- [`app/api/failure_case_routes.py`](#app-api-failure-case-routes-py)：8 个函数/方法
- [`app/api/notification_routes.py`](#app-api-notification-routes-py)：8 个函数/方法
- [`app/api/project_memory_routes.py`](#app-api-project-memory-routes-py)：14 个函数/方法
- [`app/api/rerun_routes.py`](#app-api-rerun-routes-py)：5 个函数/方法
- [`app/api/resource_routes.py`](#app-api-resource-routes-py)：8 个函数/方法
- [`app/api/retention_routes.py`](#app-api-retention-routes-py)：10 个函数/方法
- [`app/api/routes.py`](#app-api-routes-py)：22 个函数/方法
- [`app/api/ui_routes.py`](#app-api-ui-routes-py)：3 个函数/方法
- [`app/artifact_delivery/service.py`](#app-artifact-delivery-service-py)：13 个函数/方法
- [`app/chat/context.py`](#app-chat-context-py)：15 个函数/方法
- [`app/chat/memory.py`](#app-chat-memory-py)：17 个函数/方法
- [`app/chat/memory_prompt.py`](#app-chat-memory-prompt-py)：1 个函数/方法
- [`app/chat/prompt.py`](#app-chat-prompt-py)：6 个函数/方法
- [`app/chat/schemas.py`](#app-chat-schemas-py)：6 个函数/方法
- [`app/chat/service.py`](#app-chat-service-py)：13 个函数/方法
- [`app/chat/store.py`](#app-chat-store-py)：27 个函数/方法
- [`app/comparison/factory.py`](#app-comparison-factory-py)：3 个函数/方法
- [`app/comparison/identity.py`](#app-comparison-identity-py)：8 个函数/方法
- [`app/comparison/rendering.py`](#app-comparison-rendering-py)：4 个函数/方法
- [`app/comparison/repository.py`](#app-comparison-repository-py)：9 个函数/方法
- [`app/comparison/schemas.py`](#app-comparison-schemas-py)：3 个函数/方法
- [`app/comparison/service.py`](#app-comparison-service-py)：25 个函数/方法
- [`app/rerun/command_template.py`](#app-rerun-command-template-py)：15 个函数/方法
- [`app/rerun/factory.py`](#app-rerun-factory-py)：1 个函数/方法
- [`app/rerun/identity.py`](#app-rerun-identity-py)：7 个函数/方法
- [`app/rerun/repository.py`](#app-rerun-repository-py)：16 个函数/方法
- [`app/rerun/schemas.py`](#app-rerun-schemas-py)：6 个函数/方法
- [`app/rerun/service.py`](#app-rerun-service-py)：15 个函数/方法
- [`app/retention/checkpoint_adapter.py`](#app-retention-checkpoint-adapter-py)：2 个函数/方法
- [`app/retention/factory.py`](#app-retention-factory-py)：11 个函数/方法
- [`app/retention/inventory.py`](#app-retention-inventory-py)：4 个函数/方法
- [`app/retention/lock.py`](#app-retention-lock-py)：2 个函数/方法
- [`app/retention/paths.py`](#app-retention-paths-py)：7 个函数/方法
- [`app/retention/ports.py`](#app-retention-ports-py)：22 个函数/方法
- [`app/retention/repository.py`](#app-retention-repository-py)：18 个函数/方法
- [`app/retention/schemas.py`](#app-retention-schemas-py)：3 个函数/方法
- [`app/retention/service.py`](#app-retention-service-py)：30 个函数/方法
- [`app/run_evidence/reader.py`](#app-run-evidence-reader-py)：8 个函数/方法
- [`app/service_host.py`](#app-service-host-py)：5 个函数/方法
- [`app/web.py`](#app-web-py)：2 个函数/方法
- [`tests/helpers/comparison.py`](#tests-helpers-comparison-py)：2 个函数/方法
- [`tests/test_artifact_delivery_api.py`](#tests-test-artifact-delivery-api-py)：1 个函数/方法
- [`tests/test_artifact_delivery_service.py`](#tests-test-artifact-delivery-service-py)：15 个函数/方法
- [`tests/test_chat_api.py`](#tests-test-chat-api-py)：11 个函数/方法
- [`tests/test_chat_comparison_grounding.py`](#tests-test-chat-comparison-grounding-py)：5 个函数/方法
- [`tests/test_chat_context.py`](#tests-test-chat-context-py)：9 个函数/方法
- [`tests/test_chat_eval_runner.py`](#tests-test-chat-eval-runner-py)：6 个函数/方法
- [`tests/test_chat_eval_schemas.py`](#tests-test-chat-eval-schemas-py)：12 个函数/方法
- [`tests/test_chat_eval_scorers.py`](#tests-test-chat-eval-scorers-py)：7 个函数/方法
- [`tests/test_chat_memory.py`](#tests-test-chat-memory-py)：15 个函数/方法
- [`tests/test_chat_prompt_budget.py`](#tests-test-chat-prompt-budget-py)：7 个函数/方法
- [`tests/test_chat_provider.py`](#tests-test-chat-provider-py)：1 个函数/方法
- [`tests/test_chat_provider_difficulty_cases.py`](#tests-test-chat-provider-difficulty-cases-py)：1 个函数/方法
- [`tests/test_chat_service.py`](#tests-test-chat-service-py)：18 个函数/方法
- [`tests/test_chat_store.py`](#tests-test-chat-store-py)：7 个函数/方法
- [`tests/test_comparison_api.py`](#tests-test-comparison-api-py)：7 个函数/方法
- [`tests/test_comparison_repository.py`](#tests-test-comparison-repository-py)：5 个函数/方法
- [`tests/test_comparison_retention_inventory.py`](#tests-test-comparison-retention-inventory-py)：1 个函数/方法
- [`tests/test_comparison_schemas.py`](#tests-test-comparison-schemas-py)：3 个函数/方法
- [`tests/test_comparison_service.py`](#tests-test-comparison-service-py)：18 个函数/方法
- [`tests/test_rerun_api.py`](#tests-test-rerun-api-py)：11 个函数/方法
- [`tests/test_rerun_command_template.py`](#tests-test-rerun-command-template-py)：7 个函数/方法
- [`tests/test_rerun_end_to_end.py`](#tests-test-rerun-end-to-end-py)：6 个函数/方法
- [`tests/test_rerun_repository.py`](#tests-test-rerun-repository-py)：8 个函数/方法
- [`tests/test_rerun_seed_node.py`](#tests-test-rerun-seed-node-py)：2 个函数/方法
- [`tests/test_rerun_service.py`](#tests-test-rerun-service-py)：6 个函数/方法
- [`tests/test_ui_api.py`](#tests-test-ui-api-py)：6 个函数/方法
- [`tests/test_web_static.py`](#tests-test-web-static-py)：5 个函数/方法

## 逐函数参考

### `app/api/app.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `create_api_app`

- **源码**：`app/api/app.py:95`
- **签名**：`def create_api_app(job_service: JobService | None, artifact_catalog: ArtifactCatalog | None, artifact_delivery_service: ArtifactDeliveryService | None, api_token: str | None, secret_service: SecretService | None, service_host: Any | None, chat_service: ChatService | None, comparison_service: ComparisonService | None, rerun_service: RerunService | None, notification_service: NotificationService | None, failure_case_service: FailureCaseService | None, project_memory_service: ProjectMemoryService | None, model_gateway: ModelGateway | None, research_browser_service: 'ResearchBrowserService | None') -> FastAPI`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，App factory 允许测试注入临时 Job DB 和伪 checkpoint reader。该函数接收任务、Artifact、Artifact、当前处理结果等输入，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `FastAPI` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `job_service` | `JobService | None` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。；默认 空值 |
| `artifact_catalog` | `ArtifactCatalog | None` | 名为 `artifact_catalog` 的 `ArtifactCatalog | None` 领域输入；用于当前函数的业务处理，具体约束见校验分支。；默认 空值 |
| `artifact_delivery_service` | `ArtifactDeliveryService | None` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。；默认 空值 |
| `api_token` | `str | None` | 敏感凭证或其引用；不得写入日志、Prompt 或普通 Artifact。；默认 空值 |
| `secret_service` | `SecretService | None` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。；默认 空值 |
| `service_host` | `Any | None` | 名为 `service_host` 的 `Any | None` 领域输入；用于当前函数的业务处理，具体约束见校验分支。；默认 空值 |
| `chat_service` | `ChatService | None` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。；默认 空值 |
| `comparison_service` | `ComparisonService | None` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。；默认 空值 |
| `rerun_service` | `RerunService | None` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。；默认 空值 |
| `notification_service` | `NotificationService | None` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。；默认 空值 |
| `failure_case_service` | `FailureCaseService | None` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。；默认 空值 |
| `project_memory_service` | `ProjectMemoryService | None` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。；默认 空值 |
| `model_gateway` | `ModelGateway | None` | 名为 `model_gateway` 的 `ModelGateway | None` 领域输入；用于当前函数的业务处理，具体约束见校验分支。；默认 空值 |
| `research_browser_service` | `'ResearchBrowserService | None'` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。；默认 空值 |

**输出**

- **Python 类型**：`FastAPI`
- **语义**：返回 `FastAPI` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果当前处理结果有值或为真，就调用 `configure_structured_logging` 完成该函数的一项辅助处理。
调用 `build_telemetry_runtime` 组装当前阶段需要的领域对象，并把结果记为 观测数据运行时；读取运行观测数据，并保存为 运行观测数据。
如果凭据为空 且 当前处理结果为空，就加载这一步需要的外部依赖；调用 `build_secret_service` 组装当前阶段需要的领域对象，并把结果记为 凭据。
计算使用固定配置或常量值，并保存为 当前处理结果。
如果任务为空 或 Artifact为空，就调用 `build_artifact_storage` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果。
如果任务为空，就加载这一步需要的外部依赖；断言当前处理结果不为空；不满足就终止当前测试或流程；加载这一步需要的外部依赖；构造 `JobService` 结构化领域对象，并把结果记为 任务。
读取任务，并保存为 任务；构造 `FastAPI` 结构化领域对象，并把结果记为 该调用返回的结果；计算根据条件从两个候选结果中选择一个，并保存为 当前处理结果。
如果当前处理结果为空，就拒绝继续处理并抛出 `RuntimeError`，向调用方报告输入或运行失败。
计算根据条件从两个候选结果中选择一个，并保存为 当前处理结果；读取当前处理结果，并保存为 Artifact；读取当前处理结果，并保存为 Artifact；读取凭据，并保存为 凭据。
读取凭据的名称，并保存为 凭据的名称；计算根据条件从两个候选结果中选择一个，并保存为 当前处理结果；调用 `build_resource_service` 组装当前阶段需要的领域对象，并把结果记为 资源；读取资源，并保存为 资源。
构造 `InteractionService` 结构化领域对象，并把结果记为 该调用返回的结果；计算根据条件从两个候选结果中选择一个，并保存为 当前处理结果；读取当前处理结果，并保存为 后续步骤使用的结果；计算根据条件从两个候选结果中选择一个，并保存为 当前处理结果。
读取当前处理结果，并保存为 后续步骤使用的结果；计算根据条件从两个候选结果中选择一个，并保存为 通知；读取通知，并保存为 通知；计算根据条件从两个候选结果中选择一个，并保存为 失败用例。
读取失败用例，并保存为 失败用例；读取项目记忆，并保存为 项目记忆。
如果项目记忆为空 且 项目记忆有值或为真：
    计算根据条件从两个候选结果中选择一个，并保存为 对话仓库。
    如果对话仓库不为空，就调用 `initialize` 完成该函数的一项辅助处理。
    调用 `build_project_memory_service` 组装当前阶段需要的领域对象，并把结果记为 项目记忆。
读取项目记忆，并保存为 项目记忆；计算使用固定配置或常量值，并保存为 当前处理结果。
如果当前处理结果有值或为真，就加载这一步需要的外部依赖；调用 `build_knowledge_service` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果。
读取当前处理结果，并保存为 后续步骤使用的结果。
如果网关为空，就加载这一步需要的外部依赖；调用 `build_model_gateway` 组装当前阶段需要的领域对象，并把结果记为 网关。
读取网关，并保存为 网关；读取当前处理结果，并保存为 后续步骤使用的结果。
如果当前处理结果为空 且 当前处理结果有值或为真，就加载这一步需要的外部依赖；调用 `build_research_browser_service` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果。
读取当前处理结果，并保存为 后续步骤使用的结果；读取对话，并保存为 对话。
如果对话为空 且 对话有值或为真：
    如果当前处理结果为空，就拒绝继续处理并抛出 `RuntimeError`，向调用方报告输入或运行失败。
    构造 `SqliteChatRepository` 结构化领域对象，并把结果记为 对话代码仓库；调用 `initialize` 完成该函数的一项辅助处理；计算使用固定配置或常量值，并保存为 检索器。
    如果当前处理结果不为空，就读取证据检索器，并保存为 检索器。
    构造 `ChatContextBuilder` 结构化领域对象，并把结果记为 上下文构造器；调用 `build_chat_service` 组装当前阶段需要的领域对象，并把结果记为 对话。
读取对话，并保存为 对话。
定义内部辅助函数 `db_check`，供当前函数在后续步骤中调用。
定义内部辅助函数 `storage_check`，供当前函数在后续步骤中调用。
定义内部辅助函数 `resource_db_check`，供当前函数在后续步骤中调用。
计算初始化顺序集合，并保存为 当前处理结果。
如果当前处理结果不为空，就把新的处理结果追加或合并到当前处理结果。
定义内部辅助函数 `_chat_ping`，供当前函数在后续步骤中调用。
如果对话不为空：
    把新的处理结果追加或合并到当前处理结果。
    如果对话工具有值或为真：
        定义内部辅助函数 `_tool_calling_check`，供当前函数在后续步骤中调用。
        把新的处理结果追加或合并到当前处理结果。
把新的处理结果追加或合并到当前处理结果；把新的处理结果追加或合并到当前处理结果。
定义内部辅助函数 `notification_db_check`，供当前函数在后续步骤中调用。
把新的处理结果追加或合并到当前处理结果。
定义内部辅助函数 `failure_memory_db_check`，供当前函数在后续步骤中调用。
把新的处理结果追加或合并到当前处理结果。
如果项目记忆不为空：
    定义内部辅助函数 `project_memory_db_check`，供当前函数在后续步骤中调用。
    把新的处理结果追加或合并到当前处理结果。
把新的处理结果追加或合并到当前处理结果；构造 `ReadinessService` 结构化领域对象，并把结果记为 该调用返回的结果。
定义内部辅助函数 `observability_middleware`，供当前函数在后续步骤中调用。
定义内部辅助函数 `healthz`，供当前函数在后续步骤中调用。
定义内部辅助函数 `livez`，供当前函数在后续步骤中调用。
定义内部辅助函数 `readyz`，供当前函数在后续步骤中调用。
计算使用固定配置或常量值，并保存为 证据代码仓库。
如果网关有值或为真，就加载这一步需要的外部依赖；构造 `SqliteMcpEvidenceRepository` 结构化领域对象，并把结果记为 代码仓库；调用 `initialize` 完成该函数的一项辅助处理；读取代码仓库，并保存为 证据代码仓库。
调用 `include_router` 完成该函数的一项辅助处理；调用 `include_router` 完成该函数的一项辅助处理；调用 `include_router` 完成该函数的一项辅助处理；调用 `include_router` 完成该函数的一项辅助处理。
调用 `include_router` 完成该函数的一项辅助处理；调用 `include_router` 完成该函数的一项辅助处理；调用 `include_router` 完成该函数的一项辅助处理；调用 `include_router` 完成该函数的一项辅助处理。
调用 `include_router` 完成该函数的一项辅助处理；调用 `include_router` 完成该函数的一项辅助处理。
如果当前处理结果不为空，就调用 `include_router` 完成该函数的一项辅助处理。
调用 `include_router` 完成该函数的一项辅助处理。
如果当前处理结果不为空，就调用 `include_router` 完成该函数的一项辅助处理。
如果证据代码仓库不为空，就加载这一步需要的外部依赖；调用 `include_router` 完成该函数的一项辅助处理。
调用 `install_error_handlers` 完成该函数的一项辅助处理；调用 `mount_web_ui` 完成该函数的一项辅助处理；加载这一步需要的外部依赖；加载这一步需要的外部依赖。
读取运行观测数据，并保存为 运行观测数据；读取当前处理结果，并保存为 后续步骤使用的结果；计算使用固定配置或常量值，并保存为 仓库。
如果当前处理结果不为空，就读取持久化仓库，并保存为 仓库。
调用 `build_retention` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果；返回前一步处理得到的结果。
```

#### `create_api_app.db_check`

- **源码**：`app/api/app.py:407`
- **签名**：`def db_check() -> str`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
先尝试完成以下处理：
    调用 `ping` 完成该函数的一项辅助处理；返回固定值 `'ready'`。
如果出现 `Exception`：
    返回固定值 `'not_ready'`。
```

#### `create_api_app.storage_check`

- **源码**：`app/api/app.py:414`
- **签名**：`def storage_check() -> str`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
先尝试完成以下处理：
    如果当前处理结果不为空 且 “调用 `hasattr` 完成该函数的一项辅助处理”后得到肯定结果，就调用 `ping` 完成该函数的一项辅助处理。
    返回固定值 `'ready'`。
如果出现 `Exception`：
    返回固定值 `'degraded'`。
```

#### `create_api_app.resource_db_check`

- **源码**：`app/api/app.py:422`
- **签名**：`def resource_db_check() -> str`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
先尝试完成以下处理：
    调用 `ping` 完成该函数的一项辅助处理；返回固定值 `'ready'`。
如果出现 `Exception`：
    返回固定值 `'not_ready'`。
```

#### `create_api_app._chat_ping`

- **源码**：`app/api/app.py:462`
- **签名**：`def _chat_ping(service: ChatService) -> bool`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收领域服务对象，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `service` | `ChatService` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
先尝试完成以下处理：
    调用 `ping` 完成该函数的一项辅助处理；返回固定值 `真`。
如果出现 `Exception`：
    返回固定值 `假`。
```

#### `create_api_app._tool_calling_check`

- **源码**：`app/api/app.py:486`
- **签名**：`def _tool_calling_check() -> str`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
先尝试完成以下处理：
    加载这一步需要的外部依赖；调用 `doctor_chat_tool_calling` 完成该函数的一项辅助处理，并把结果记为 MCP 评测或运行报告；返回按条件选出的结果。
如果出现 `Exception`：
    返回固定值 `'not_ready'`。
```

#### `create_api_app.notification_db_check`

- **源码**：`app/api/app.py:534`
- **签名**：`def notification_db_check() -> str`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
先尝试完成以下处理：
    调用 `ping` 完成该函数的一项辅助处理；返回固定值 `'ready'`。
如果出现 `Exception`：
    返回固定值 `'not_ready'`。
```

#### `create_api_app.failure_memory_db_check`

- **源码**：`app/api/app.py:550`
- **签名**：`def failure_memory_db_check() -> str`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
先尝试完成以下处理：
    调用 `ping` 完成该函数的一项辅助处理；返回固定值 `'ready'`。
如果出现 `Exception`：
    返回固定值 `'not_ready'`。
```

#### `create_api_app.project_memory_db_check`

- **源码**：`app/api/app.py:567`
- **签名**：`def project_memory_db_check() -> str`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
先尝试完成以下处理：
    调用 `ping` 完成该函数的一项辅助处理；返回固定值 `'ready'`。
如果出现 `Exception`：
    返回固定值 `'not_ready'`。
```

#### `create_api_app.observability_middleware`

- **源码**：`app/api/app.py:603`
- **签名**：`async def observability_middleware(request: Request, call_next: 未显式标注) -> 未显式标注（存在 return）`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、下一项，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `call_next` | `未显式标注` | 名为 `call_next` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
读取当前输入内容中的对应字段，并保存为 MCP 请求 ID；读取MCP 请求 ID，并保存为 MCP 请求 ID。
先尝试完成以下处理：
    进入上下文“调用 `bind_telemetry_context` 完成该函数的一项辅助处理”，退出时自动清理资源：
        进入上下文“调用 `span` 完成该函数的一项辅助处理，并把上下文资源交给当前处理结果”，退出时自动清理资源：
            调用 `monotonic` 完成该函数的一项辅助处理，并把结果记为 读取起点的时间；等待异步处理完成，并把结果记为 结构化响应；计算组合或计算已有值，并保存为 当前处理结果；读取状态，并保存为 状态。
            计算根据字段和固定文本生成格式化文本，并保存为 状态集合；调用 `getattr` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
            先尝试完成以下处理：
                调用 `set_attribute` 完成该函数的一项辅助处理。
            如果出现 `Exception`：
                不执行额外操作。
            先尝试完成以下处理：
                调用 `counter` 完成该函数的一项辅助处理。
            如果出现 `Exception`：
                不执行额外操作。
            先尝试完成以下处理：
                调用 `histogram` 完成该函数的一项辅助处理。
            如果出现 `Exception`：
                不执行额外操作。
            计算使用固定配置或常量值，并保存为 当前处理结果中的对应字段；计算使用固定配置或常量值，并保存为 当前处理结果中的对应字段；计算使用固定配置或常量值，并保存为 当前处理结果中的对应字段。
            如果当前处理结果有值或为真 且 当前输入内容不属于当前处理结果，就计算使用固定配置或常量值，并保存为 当前处理结果中的对应字段。
            读取MCP 请求 ID，并保存为 当前处理结果中的对应字段；返回结构化响应的当前值。
如果出现 `Exception`：
    重新抛出当前异常，保持原始失败信息。
```

#### `create_api_app.healthz`

- **源码**：`app/api/app.py:713`
- **签名**：`def healthz() -> dict[str, str]`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`dict[str, str]`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
返回包含 `status` 字段的结构化映射。
```

#### `create_api_app.livez`

- **源码**：`app/api/app.py:718`
- **签名**：`def livez() -> dict`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
调用 `build_liveness_probe` 组装当前阶段需要的领域对象；返回包含 `status`、`timestamp` 字段的结构化映射。
```

#### `create_api_app.readyz`

- **源码**：`app/api/app.py:726`
- **签名**：`def readyz() -> Response`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`Response`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `cached_report` 完成该函数的一项辅助处理，并把结果记为 MCP 评测或运行报告；计算根据条件从两个候选结果中选择一个，并保存为 状态；构造并返回 `Response` 结构化领域对象。
```

### `app/api/auth.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `require_api_auth`

- **源码**：`app/api/auth.py:14`
- **签名**：`def require_api_auth(request: Request, authorization: str | None) -> str`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，返回审计 actor。该函数接收业务请求、授权，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `authorization` | `str | None` | 名为 `authorization` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。；默认 调用 Header(default=空值, alias='Authorization') |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `getattr` 完成该函数的一项辅助处理，并把结果记为 覆盖默认配置的字段。
如果覆盖默认配置的字段不为空：
    调用 `get_secret_value` 读取或查询当前阶段需要的数据，并把结果记为 期望值。
否则：
    调用 `getattr` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
    如果当前处理结果不是当前处理结果：
        如果当前处理结果为空或为假，就返回固定值 `'api:local'`。
        调用 `getattr` 完成该函数的一项辅助处理，并把结果记为 凭据值；计算根据条件从两个候选结果中选择一个，并保存为 期望值。
    否则：
        调用 `getattr` 完成该函数的一项辅助处理，并把结果记为 凭据；调用 `getattr` 完成该函数的一项辅助处理，并把结果记为 敏感凭据的名称。
        如果凭据为空 或 敏感凭据的名称为空或为假，就拒绝继续处理并抛出 `RuntimeError`，向调用方报告输入或运行失败。
        先尝试完成以下处理：
            调用 `resolve_current` 解析、规范化或转换当前输入，并把结果记为 待处理的论文或源码材料；调用 `reveal` 完成该函数的一项辅助处理，并把结果记为 期望值。
        如果出现 `SecretNotFoundError`：
            返回固定值 `'api:local'`。
调用 `partition` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；计算计算当前表达式的结果，并保存为 输入或结果是否有效的判断。
如果输入或结果是否有效的判断为空或为假，就拒绝继续处理并抛出 `HTTPException`，向调用方报告输入或运行失败。
返回固定值 `'api:token'`。
```

### `app/api/chat_routes.py`

**模块作用**：Phase 31/36 Chat API routes。

#### `chat_service`

- **源码**：`app/api/chat_routes.py:44`
- **签名**：`def chat_service(request: Request) -> ChatService`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ChatService` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`ChatService`
- **语义**：返回 `ChatService` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `getattr` 完成该函数的一项辅助处理，并把结果记为 领域服务对象。
如果领域服务对象为空，就拒绝继续处理并抛出 `HTTPException`，向调用方报告输入或运行失败。
返回领域服务对象的当前值。
```

#### `list_chat_messages`

- **源码**：`app/api/chat_routes.py:68`
- **签名**：`def list_chat_messages(job_id: str, _actor: Actor, service: ChatDependency, after: AfterSequence, limit: PageLimit) -> ChatMessagePage`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务 ID、审计主体、领域服务对象、升级后运行报告等输入，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `ChatMessagePage` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `_actor` | `Actor` | 名为 `_actor` 的 `Actor` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `service` | `ChatDependency` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |
| `after` | `AfterSequence` | 分页、文本切片或事件序列位置；用于确定本次读取的起止边界。；默认 0 |
| `limit` | `PageLimit` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。；默认 100 |

**输出**

- **Python 类型**：`ChatMessagePage`
- **语义**：返回 `ChatMessagePage` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `list_messages` 读取或查询当前阶段需要的数据，并返回处理结果。
```

#### `list_recent_chat_messages`

- **源码**：`app/api/chat_routes.py:83`
- **签名**：`def list_recent_chat_messages(job_id: str, _actor: Actor, service: ChatDependency, limit: PageLimit) -> ChatMessagePage`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务 ID、审计主体、领域服务对象、结果数量上限，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `ChatMessagePage` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `_actor` | `Actor` | 名为 `_actor` 的 `Actor` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `service` | `ChatDependency` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |
| `limit` | `PageLimit` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。；默认 100 |

**输出**

- **Python 类型**：`ChatMessagePage`
- **语义**：返回 `ChatMessagePage` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `list_recent_messages` 读取或查询当前阶段需要的数据，并返回处理结果。
```

#### `get_chat_memory`

- **源码**：`app/api/chat_routes.py:99`
- **签名**：`def get_chat_memory(job_id: str, _actor: Actor, service: ChatDependency) -> ConversationMemoryView | None`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务 ID、审计主体、领域服务对象，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `ConversationMemoryView | None` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `_actor` | `Actor` | 名为 `_actor` 的 `Actor` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `service` | `ChatDependency` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |

**输出**

- **Python 类型**：`ConversationMemoryView | None`
- **语义**：返回 `ConversationMemoryView | None` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
先尝试完成以下处理：
    调用 `get_memory` 读取或查询当前阶段需要的数据，并返回处理结果。
如果出现 `ChatUnavailableError`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `HTTPException`，向调用方报告输入或运行失败。
```

#### `ask_chat_agent`

- **源码**：`app/api/chat_routes.py:117`
- **签名**：`def ask_chat_agent(job_id: str, body: ChatAskRequest, idempotency_key: IdempotencyKey, _actor: Actor, service: ChatDependency) -> ChatAskResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务 ID、请求正文、请求幂等键、审计主体等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `body` | `ChatAskRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `idempotency_key` | `IdempotencyKey` | 调用方提供的幂等键；重复请求应复用同一结果，而不是再次产生副作用。 |
| `_actor` | `Actor` | 名为 `_actor` 的 `Actor` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `service` | `ChatDependency` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |

**输出**

- **Python 类型**：`ChatAskResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
先尝试完成以下处理：
    调用 `ask` 完成该函数的一项辅助处理，并返回处理结果。
如果出现 `ChatConflictError`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `HTTPException`，向调用方报告输入或运行失败。
如果出现 `ChatUnavailableError`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `HTTPException`，向调用方报告输入或运行失败。
```

### `app/api/comparison_routes.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `comparison_service`

- **源码**：`app/api/comparison_routes.py:20`
- **签名**：`def comparison_service(request: Request) -> ComparisonService`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ComparisonService` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`ComparisonService`
- **语义**：返回 `ComparisonService` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
返回前一步处理得到的结果。
```

#### `create_comparison`

- **源码**：`app/api/comparison_routes.py:35`
- **签名**：`def create_comparison(body: ComparisonCreateRequest, _actor: Actor, service: ComparisonDependency) -> ComparisonReport`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收请求正文、审计主体、领域服务对象，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `ComparisonReport` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `body` | `ComparisonCreateRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `_actor` | `Actor` | 名为 `_actor` 的 `Actor` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `service` | `ComparisonDependency` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |

**输出**

- **Python 类型**：`ComparisonReport`
- **语义**：返回 `ComparisonReport` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `create` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `get_comparison`

- **源码**：`app/api/comparison_routes.py:47`
- **签名**：`def get_comparison(comparison_id: str, _actor: Actor, service: ComparisonDependency) -> ComparisonReport`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收SDK 或 MCP 运行升级比较结果的 ID、审计主体、领域服务对象，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `ComparisonReport` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `comparison_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `_actor` | `Actor` | 名为 `_actor` 的 `Actor` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `service` | `ComparisonDependency` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |

**输出**

- **Python 类型**：`ComparisonReport`
- **语义**：返回 `ComparisonReport` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
从领域服务对象读取所需的状态或领域记录，并返回处理结果。
```

#### `list_job_comparisons`

- **源码**：`app/api/comparison_routes.py:59`
- **签名**：`def list_job_comparisons(job_id: str, _actor: Actor, service: ComparisonDependency, limit: Annotated[int, Query(ge=1, le=500)]) -> ComparisonListResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务 ID、审计主体、领域服务对象、结果数量上限，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `_actor` | `Actor` | 名为 `_actor` 的 `Actor` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `service` | `ComparisonDependency` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |
| `limit` | `Annotated[int, Query(ge=1, le=500)]` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。；默认 100 |

**输出**

- **Python 类型**：`ComparisonListResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `list_for_job` 读取或查询当前阶段需要的数据，并返回处理结果。
```

### `app/api/errors.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_response`

- **源码**：`app/api/errors.py:87`
- **签名**：`def _response(request: Request, status_code: int, code: str, message: str) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、状态、待解析或验证的代码、面向用户或日志的提示信息，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `status_code` | `int` | 名为 `status_code` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `code` | `str` | 待解析、执行或断言的代码文本；处理前应处于受控测试/执行边界内。 |
| `message` | `str` | 对话消息记录或消息文本；角色、顺序和内容 Hash 可能参与证据校验。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
构造 `ApiError` 结构化领域对象，并把结果记为 结构化请求载荷；构造并返回 `JSONResponse` 结构化领域对象。
```

#### `install_error_handlers`

- **源码**：`app/api/errors.py:109`
- **签名**：`def install_error_handlers(app: FastAPI) -> None`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，把内部异常映射成稳定 HTTP 语义。该函数接收当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `app` | `FastAPI` | 名为 `app` 的 `FastAPI` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
定义内部辅助函数 `handle_not_found`，供当前函数在后续步骤中调用。
定义内部辅助函数 `handle_conflict`，供当前函数在后续步骤中调用。
定义内部辅助函数 `handle_job_backend_unavailable`，供当前函数在后续步骤中调用。
定义内部辅助函数 `handle_value_error`，供当前函数在后续步骤中调用。
定义内部辅助函数 `handle_store_error`，供当前函数在后续步骤中调用。
定义内部辅助函数 `handle_artifact_not_found`，供当前函数在后续步骤中调用。
定义内部辅助函数 `handle_artifact_integrity`，供当前函数在后续步骤中调用。
定义内部辅助函数 `handle_artifact_unavailable`，供当前函数在后续步骤中调用。
定义内部辅助函数 `handle_preview_unsupported`，供当前函数在后续步骤中调用。
定义内部辅助函数 `handle_export_limit`，供当前函数在后续步骤中调用。
定义内部辅助函数 `handle_retention_not_found`，供当前函数在后续步骤中调用。
定义内部辅助函数 `handle_retention_conflict`，供当前函数在后续步骤中调用。
定义内部辅助函数 `handle_retention_path_unsafe`，供当前函数在后续步骤中调用。
定义内部辅助函数 `handle_retention_backend_unsupported`，供当前函数在后续步骤中调用。
定义内部辅助函数 `handle_storage_capacity`，供当前函数在后续步骤中调用。
定义内部辅助函数 `handle_comparison_not_found`，供当前函数在后续步骤中调用。
定义内部辅助函数 `handle_comparison_conflict`，供当前函数在后续步骤中调用。
定义内部辅助函数 `handle_comparison_integrity`，供当前函数在后续步骤中调用。
定义内部辅助函数 `handle_comparison_limit`，供当前函数在后续步骤中调用。
定义内部辅助函数 `rerun_not_found_handler`，供当前函数在后续步骤中调用。
定义内部辅助函数 `rerun_expired_handler`，供当前函数在后续步骤中调用。
定义内部辅助函数 `rerun_conflict_handler`，供当前函数在后续步骤中调用。
定义内部辅助函数 `rerun_command_rejected_handler`，供当前函数在后续步骤中调用。
定义内部辅助函数 `rerun_integrity_handler`，供当前函数在后续步骤中调用。
定义内部辅助函数 `handle_notification_not_found`，供当前函数在后续步骤中调用。
定义内部辅助函数 `handle_notification_conflict`，供当前函数在后续步骤中调用。
定义内部辅助函数 `failure_case_not_found_handler`，供当前函数在后续步骤中调用。
定义内部辅助函数 `failure_case_conflict_handler`，供当前函数在后续步骤中调用。
定义内部辅助函数 `failure_case_limit_handler`，供当前函数在后续步骤中调用。
定义内部辅助函数 `failure_case_integrity_handler`，供当前函数在后续步骤中调用。
定义内部辅助函数 `project_not_found_handler`，供当前函数在后续步骤中调用。
定义内部辅助函数 `project_fact_not_found_handler`，供当前函数在后续步骤中调用。
定义内部辅助函数 `project_memory_conflict_handler`，供当前函数在后续步骤中调用。
定义内部辅助函数 `project_memory_integrity_handler`，供当前函数在后续步骤中调用。
定义内部辅助函数 `project_memory_limit_handler`，供当前函数在后续步骤中调用。
定义内部辅助函数 `project_memory_generic_handler`，供当前函数在后续步骤中调用。
定义内部辅助函数 `handle_knowledge_not_found`，供当前函数在后续步骤中调用。
定义内部辅助函数 `handle_knowledge_conflict`，供当前函数在后续步骤中调用。
定义内部辅助函数 `handle_knowledge_integrity`，供当前函数在后续步骤中调用。
定义内部辅助函数 `handle_knowledge_limit`，供当前函数在后续步骤中调用。
定义内部辅助函数 `handle_model_budget_exceeded`，供当前函数在后续步骤中调用。
定义内部辅助函数 `handle_model_route_unavailable`，供当前函数在后续步骤中调用。
定义内部辅助函数 `handle_model_catalog_error`，供当前函数在后续步骤中调用。
定义内部辅助函数 `handle_model_ledger_integrity`，供当前函数在后续步骤中调用。
定义内部辅助函数 `handle_research_not_found`，供当前函数在后续步骤中调用。
定义内部辅助函数 `handle_research_conflict`，供当前函数在后续步骤中调用。
定义内部辅助函数 `handle_research_policy`，供当前函数在后续步骤中调用。
定义内部辅助函数 `handle_research_url_rejected`，供当前函数在后续步骤中调用。
定义内部辅助函数 `handle_research_robots_denied`，供当前函数在后续步骤中调用。
定义内部辅助函数 `handle_research_content_rejected`，供当前函数在后续步骤中调用。
定义内部辅助函数 `handle_research_limit`，供当前函数在后续步骤中调用。
定义内部辅助函数 `handle_research_transport`，供当前函数在后续步骤中调用。
定义内部辅助函数 `handle_research_integrity`，供当前函数在后续步骤中调用。
定义内部辅助函数 `handle_research_synthesis_rejected`，供当前函数在后续步骤中调用。
定义内部辅助函数 `handle_research_resource_candidate_rejected`，供当前函数在后续步骤中调用。
```

#### `install_error_handlers.handle_not_found`

- **源码**：`app/api/errors.py:117`
- **签名**：`async def handle_not_found(request: Request, exc: JobNotFoundError) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `JobNotFoundError` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.handle_conflict`

- **源码**：`app/api/errors.py:131`
- **签名**：`async def handle_conflict(request: Request, exc: JobConflictError) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `JobConflictError` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.handle_job_backend_unavailable`

- **源码**：`app/api/errors.py:145`
- **签名**：`async def handle_job_backend_unavailable(request: Request, exc: JobBackendUnavailable) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `JobBackendUnavailable` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
移除捕获的异常中的当前内容；调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.handle_value_error`

- **源码**：`app/api/errors.py:158`
- **签名**：`async def handle_value_error(request: Request, exc: ValueError) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `ValueError` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.handle_store_error`

- **源码**：`app/api/errors.py:170`
- **签名**：`async def handle_store_error(request: Request, exc: JobStoreError) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `JobStoreError` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.handle_artifact_not_found`

- **源码**：`app/api/errors.py:183`
- **签名**：`async def handle_artifact_not_found(request: Request, exc: ArtifactNotFoundError) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `ArtifactNotFoundError` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.handle_artifact_integrity`

- **源码**：`app/api/errors.py:197`
- **签名**：`async def handle_artifact_integrity(request: Request, exc: ArtifactIntegrityError) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `ArtifactIntegrityError` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.handle_artifact_unavailable`

- **源码**：`app/api/errors.py:211`
- **签名**：`async def handle_artifact_unavailable(request: Request, exc: ArtifactBackendUnavailable) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `ArtifactBackendUnavailable` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.handle_preview_unsupported`

- **源码**：`app/api/errors.py:225`
- **签名**：`async def handle_preview_unsupported(request: Request, exc: ArtifactPreviewUnsupported) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `ArtifactPreviewUnsupported` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.handle_export_limit`

- **源码**：`app/api/errors.py:239`
- **签名**：`async def handle_export_limit(request: Request, exc: ArtifactExportLimitExceeded) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `ArtifactExportLimitExceeded` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.handle_retention_not_found`

- **源码**：`app/api/errors.py:251`
- **签名**：`async def handle_retention_not_found(request: Request, exc: RetentionNotFound) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `RetentionNotFound` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.handle_retention_conflict`

- **源码**：`app/api/errors.py:263`
- **签名**：`async def handle_retention_conflict(request: Request, exc: RetentionConflict) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `RetentionConflict` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.handle_retention_path_unsafe`

- **源码**：`app/api/errors.py:275`
- **签名**：`async def handle_retention_path_unsafe(request: Request, exc: RetentionPathUnsafe) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `RetentionPathUnsafe` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.handle_retention_backend_unsupported`

- **源码**：`app/api/errors.py:287`
- **签名**：`async def handle_retention_backend_unsupported(request: Request, exc: RetentionBackendUnsupported) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `RetentionBackendUnsupported` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.handle_storage_capacity`

- **源码**：`app/api/errors.py:299`
- **签名**：`async def handle_storage_capacity(request: Request, exc: StorageCapacityExceeded) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `StorageCapacityExceeded` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.handle_comparison_not_found`

- **源码**：`app/api/errors.py:311`
- **签名**：`async def handle_comparison_not_found(request: Request, exc: ComparisonNotFoundError) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `ComparisonNotFoundError` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.handle_comparison_conflict`

- **源码**：`app/api/errors.py:323`
- **签名**：`async def handle_comparison_conflict(request: Request, exc: ComparisonConflictError) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `ComparisonConflictError` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.handle_comparison_integrity`

- **源码**：`app/api/errors.py:335`
- **签名**：`async def handle_comparison_integrity(request: Request, exc: ComparisonIntegrityError) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `ComparisonIntegrityError` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.handle_comparison_limit`

- **源码**：`app/api/errors.py:347`
- **签名**：`async def handle_comparison_limit(request: Request, exc: ComparisonLimitExceededError) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `ComparisonLimitExceededError` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.rerun_not_found_handler`

- **源码**：`app/api/errors.py:359`
- **签名**：`async def rerun_not_found_handler(request: Request, exc: RerunNotFoundError) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `RerunNotFoundError` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.rerun_expired_handler`

- **源码**：`app/api/errors.py:371`
- **签名**：`async def rerun_expired_handler(request: Request, exc: RerunExpiredError) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `RerunExpiredError` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.rerun_conflict_handler`

- **源码**：`app/api/errors.py:383`
- **签名**：`async def rerun_conflict_handler(request: Request, exc: RerunConflictError) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `RerunConflictError` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.rerun_command_rejected_handler`

- **源码**：`app/api/errors.py:395`
- **签名**：`async def rerun_command_rejected_handler(request: Request, exc: RerunCommandRejectedError) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `RerunCommandRejectedError` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回已校验/规范化的命令文本、命令对象或命令集合；不等于已经执行。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.rerun_integrity_handler`

- **源码**：`app/api/errors.py:407`
- **签名**：`async def rerun_integrity_handler(request: Request, exc: RerunIntegrityError) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `RerunIntegrityError` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
移除捕获的异常中的当前内容；调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.handle_notification_not_found`

- **源码**：`app/api/errors.py:420`
- **签名**：`async def handle_notification_not_found(request: Request, exc: NotificationNotFoundError) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `NotificationNotFoundError` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.handle_notification_conflict`

- **源码**：`app/api/errors.py:432`
- **签名**：`async def handle_notification_conflict(request: Request, exc: NotificationConflictError) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `NotificationConflictError` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.failure_case_not_found_handler`

- **源码**：`app/api/errors.py:444`
- **签名**：`async def failure_case_not_found_handler(request: Request, exc: FailureCaseNotFoundError) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `FailureCaseNotFoundError` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.failure_case_conflict_handler`

- **源码**：`app/api/errors.py:456`
- **签名**：`async def failure_case_conflict_handler(request: Request, exc: FailureCaseConflictError) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `FailureCaseConflictError` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.failure_case_limit_handler`

- **源码**：`app/api/errors.py:468`
- **签名**：`async def failure_case_limit_handler(request: Request, exc: FailureCaseLimitExceededError) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `FailureCaseLimitExceededError` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.failure_case_integrity_handler`

- **源码**：`app/api/errors.py:480`
- **签名**：`async def failure_case_integrity_handler(request: Request, exc: FailureCaseIntegrityError) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `FailureCaseIntegrityError` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
移除捕获的异常中的当前内容；调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.project_not_found_handler`

- **源码**：`app/api/errors.py:495`
- **签名**：`async def project_not_found_handler(request: Request, exc: ProjectNotFoundError) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `ProjectNotFoundError` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.project_fact_not_found_handler`

- **源码**：`app/api/errors.py:507`
- **签名**：`async def project_fact_not_found_handler(request: Request, exc: ProjectFactNotFoundError) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `ProjectFactNotFoundError` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.project_memory_conflict_handler`

- **源码**：`app/api/errors.py:519`
- **签名**：`async def project_memory_conflict_handler(request: Request, exc: ProjectMemoryConflictError) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `ProjectMemoryConflictError` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.project_memory_integrity_handler`

- **源码**：`app/api/errors.py:531`
- **签名**：`async def project_memory_integrity_handler(request: Request, exc: ProjectMemoryIntegrityError) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `ProjectMemoryIntegrityError` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
移除捕获的异常中的当前内容；调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.project_memory_limit_handler`

- **源码**：`app/api/errors.py:544`
- **签名**：`async def project_memory_limit_handler(request: Request, exc: ProjectMemoryLimitExceededError) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `ProjectMemoryLimitExceededError` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.project_memory_generic_handler`

- **源码**：`app/api/errors.py:556`
- **签名**：`async def project_memory_generic_handler(request: Request, exc: ProjectMemoryError) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `ProjectMemoryError` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
移除捕获的异常中的当前内容；调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.handle_knowledge_not_found`

- **源码**：`app/api/errors.py:571`
- **签名**：`async def handle_knowledge_not_found(request: Request, exc: KnowledgeNotFoundError) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `KnowledgeNotFoundError` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.handle_knowledge_conflict`

- **源码**：`app/api/errors.py:583`
- **签名**：`async def handle_knowledge_conflict(request: Request, exc: KnowledgeConflictError) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `KnowledgeConflictError` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.handle_knowledge_integrity`

- **源码**：`app/api/errors.py:595`
- **签名**：`async def handle_knowledge_integrity(request: Request, exc: KnowledgeIntegrityError) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `KnowledgeIntegrityError` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.handle_knowledge_limit`

- **源码**：`app/api/errors.py:607`
- **签名**：`async def handle_knowledge_limit(request: Request, exc: KnowledgeLimitExceededError) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `KnowledgeLimitExceededError` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.handle_model_budget_exceeded`

- **源码**：`app/api/errors.py:621`
- **签名**：`async def handle_model_budget_exceeded(request: Request, exc: ModelBudgetExceeded) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `ModelBudgetExceeded` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
移除捕获的异常中的当前内容；调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.handle_model_route_unavailable`

- **源码**：`app/api/errors.py:634`
- **签名**：`async def handle_model_route_unavailable(request: Request, exc: ModelRouteUnavailable) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `ModelRouteUnavailable` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
移除捕获的异常中的当前内容；调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.handle_model_catalog_error`

- **源码**：`app/api/errors.py:647`
- **签名**：`async def handle_model_catalog_error(request: Request, exc: ModelCatalogError) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `ModelCatalogError` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
移除捕获的异常中的当前内容；调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.handle_model_ledger_integrity`

- **源码**：`app/api/errors.py:660`
- **签名**：`async def handle_model_ledger_integrity(request: Request, exc: ModelLedgerIntegrityError) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `ModelLedgerIntegrityError` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
移除捕获的异常中的当前内容；调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.handle_research_not_found`

- **源码**：`app/api/errors.py:675`
- **签名**：`async def handle_research_not_found(request: Request, exc: ResearchNotFound) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `ResearchNotFound` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.handle_research_conflict`

- **源码**：`app/api/errors.py:687`
- **签名**：`async def handle_research_conflict(request: Request, exc: ResearchConflict) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `ResearchConflict` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.handle_research_policy`

- **源码**：`app/api/errors.py:699`
- **签名**：`async def handle_research_policy(request: Request, exc: ResearchPolicyError) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `ResearchPolicyError` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.handle_research_url_rejected`

- **源码**：`app/api/errors.py:711`
- **签名**：`async def handle_research_url_rejected(request: Request, exc: ResearchUrlRejected) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `ResearchUrlRejected` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.handle_research_robots_denied`

- **源码**：`app/api/errors.py:723`
- **签名**：`async def handle_research_robots_denied(request: Request, exc: ResearchRobotsDenied) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `ResearchRobotsDenied` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.handle_research_content_rejected`

- **源码**：`app/api/errors.py:735`
- **签名**：`async def handle_research_content_rejected(request: Request, exc: ResearchContentRejected) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `ResearchContentRejected` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.handle_research_limit`

- **源码**：`app/api/errors.py:747`
- **签名**：`async def handle_research_limit(request: Request, exc: ResearchLimitExceeded) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `ResearchLimitExceeded` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.handle_research_transport`

- **源码**：`app/api/errors.py:759`
- **签名**：`async def handle_research_transport(request: Request, exc: ResearchTransportUnavailable) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `ResearchTransportUnavailable` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.handle_research_integrity`

- **源码**：`app/api/errors.py:771`
- **签名**：`async def handle_research_integrity(request: Request, exc: ResearchIntegrityError) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `ResearchIntegrityError` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
移除捕获的异常中的当前内容；调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.handle_research_synthesis_rejected`

- **源码**：`app/api/errors.py:784`
- **签名**：`async def handle_research_synthesis_rejected(request: Request, exc: ResearchSynthesisRejected) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `ResearchSynthesisRejected` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `install_error_handlers.handle_research_resource_candidate_rejected`

- **源码**：`app/api/errors.py:796`
- **签名**：`async def handle_research_resource_candidate_rejected(request: Request, exc: ResearchResourceCandidateRejected) -> JSONResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `exc` | `ResearchResourceCandidateRejected` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`JSONResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并返回处理结果。
```

### `app/api/failure_case_routes.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `failure_case_service`

- **源码**：`app/api/failure_case_routes.py:33`
- **签名**：`def failure_case_service(request: Request) -> FailureCaseService`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `FailureCaseService` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`FailureCaseService`
- **语义**：返回 `FailureCaseService` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
返回失败用例的当前值。
```

#### `create_candidate`

- **源码**：`app/api/failure_case_routes.py:47`
- **签名**：`def create_candidate(body: FailureCaseCreateRequest, idempotency_key: IdempotencyKey, actor: Actor, service: FailureCaseDependency) -> FailureCaseMutationResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收请求正文、请求幂等键、审计主体、领域服务对象，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `body` | `FailureCaseCreateRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `idempotency_key` | `IdempotencyKey` | 调用方提供的幂等键；重复请求应复用同一结果，而不是再次产生副作用。 |
| `actor` | `Actor` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `service` | `FailureCaseDependency` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |

**输出**

- **Python 类型**：`FailureCaseMutationResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
移除审计主体中的当前内容；调用 `create_candidate` 组装当前阶段需要的领域对象，并返回处理结果。
```

#### `list_cases`

- **源码**：`app/api/failure_case_routes.py:61`
- **签名**：`def list_cases(actor: Actor, service: FailureCaseDependency, include_deprecated: bool, limit: int) -> list[FailureCaseRecord]`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收审计主体、领域服务对象、当前处理结果、结果数量上限，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `actor` | `Actor` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `service` | `FailureCaseDependency` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |
| `include_deprecated` | `bool` | 布尔条件或能力开关，用于控制流程分支。；默认 假 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。；默认 调用 Query(default=100, ge=1, le=500) |

**输出**

- **Python 类型**：`list[FailureCaseRecord]`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
移除审计主体中的当前内容；调用 `list_cases` 读取或查询当前阶段需要的数据，并返回处理结果。
```

#### `search_source_job`

- **源码**：`app/api/failure_case_routes.py:79`
- **签名**：`def search_source_job(job_id: str, actor: Actor, service: FailureCaseDependency) -> FailureCasePack`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务 ID、审计主体、领域服务对象，用于围绕论文方法语义检索、切分和排序代码证据，为后续方法映射与实验规划提供候选结果，最终标注为 `FailureCasePack` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `actor` | `Actor` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `service` | `FailureCaseDependency` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |

**输出**

- **Python 类型**：`FailureCasePack`
- **语义**：返回 `FailureCasePack` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
移除审计主体中的当前内容；调用 `search_source_job` 读取或查询当前阶段需要的数据，并返回处理结果。
```

#### `get_case`

- **源码**：`app/api/failure_case_routes.py:89`
- **签名**：`def get_case(case_id: str, actor: Actor, service: FailureCaseDependency) -> FailureCaseRecord`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收评测用例的 ID、审计主体、领域服务对象，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `case_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `actor` | `Actor` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `service` | `FailureCaseDependency` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |

**输出**

- **Python 类型**：`FailureCaseRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
移除审计主体中的当前内容；从领域服务对象读取所需的状态或领域记录，并返回处理结果。
```

#### `confirm_case`

- **源码**：`app/api/failure_case_routes.py:102`
- **签名**：`def confirm_case(case_id: str, body: FailureCaseConfirmRequest, idempotency_key: IdempotencyKey, actor: Actor, service: FailureCaseDependency) -> FailureCaseMutationResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收评测用例的 ID、请求正文、请求幂等键、审计主体等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `case_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `body` | `FailureCaseConfirmRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `idempotency_key` | `IdempotencyKey` | 调用方提供的幂等键；重复请求应复用同一结果，而不是再次产生副作用。 |
| `actor` | `Actor` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `service` | `FailureCaseDependency` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |

**输出**

- **Python 类型**：`FailureCaseMutationResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `confirm` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `verify_case`

- **源码**：`app/api/failure_case_routes.py:121`
- **签名**：`def verify_case(case_id: str, body: FailureCaseVerifyRequest, idempotency_key: IdempotencyKey, actor: Actor, service: FailureCaseDependency) -> FailureCaseMutationResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收评测用例的 ID、请求正文、请求幂等键、审计主体等输入，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `case_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `body` | `FailureCaseVerifyRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `idempotency_key` | `IdempotencyKey` | 调用方提供的幂等键；重复请求应复用同一结果，而不是再次产生副作用。 |
| `actor` | `Actor` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `service` | `FailureCaseDependency` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |

**输出**

- **Python 类型**：`FailureCaseMutationResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
移除审计主体中的当前内容；调用 `verify` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `deprecate_case`

- **源码**：`app/api/failure_case_routes.py:140`
- **签名**：`def deprecate_case(case_id: str, body: FailureCaseDeprecateRequest, idempotency_key: IdempotencyKey, actor: Actor, service: FailureCaseDependency) -> FailureCaseMutationResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收评测用例的 ID、请求正文、请求幂等键、审计主体等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `case_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `body` | `FailureCaseDeprecateRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `idempotency_key` | `IdempotencyKey` | 调用方提供的幂等键；重复请求应复用同一结果，而不是再次产生副作用。 |
| `actor` | `Actor` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `service` | `FailureCaseDependency` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |

**输出**

- **Python 类型**：`FailureCaseMutationResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
移除审计主体中的当前内容；调用 `deprecate` 完成该函数的一项辅助处理，并返回处理结果。
```

### `app/api/notification_routes.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `notification_service`

- **源码**：`app/api/notification_routes.py:43`
- **签名**：`def notification_service(request: Request) -> NotificationService`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `NotificationService` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`NotificationService`
- **语义**：返回 `NotificationService` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
返回通知的当前值。
```

#### `_sse`

- **源码**：`app/api/notification_routes.py:55`
- **签名**：`def _sse(notification: NotificationView) -> str`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收通知，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `notification` | `NotificationView` | 名为 `notification` 的 `NotificationView` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
将结构化内容序列化或编码为可传输表示，并把结果记为 结构化请求载荷；返回当前计算得到的结果。
```

#### `list_notifications`

- **源码**：`app/api/notification_routes.py:69`
- **签名**：`def list_notifications(_actor: Actor, service: NotificationDependency, after: AfterQuery, unread_only: UnreadOnlyQuery, limit: LimitQuery) -> NotificationPage`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收审计主体、领域服务对象、升级后运行报告、是否只读取未读通知的开关等输入，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `NotificationPage` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `_actor` | `Actor` | 名为 `_actor` 的 `Actor` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `service` | `NotificationDependency` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |
| `after` | `AfterQuery` | 分页、文本切片或事件序列位置；用于确定本次读取的起止边界。；默认 0 |
| `unread_only` | `UnreadOnlyQuery` | 是否只读取未读通知的开关；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 假 |
| `limit` | `LimitQuery` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。；默认 100 |

**输出**

- **Python 类型**：`NotificationPage`
- **语义**：返回 `NotificationPage` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `list_notifications` 读取或查询当前阶段需要的数据，并返回处理结果。
```

#### `unread_count`

- **源码**：`app/api/notification_routes.py:87`
- **签名**：`def unread_count(_actor: Actor, service: NotificationDependency) -> NotificationUnreadCount`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收审计主体、领域服务对象，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `NotificationUnreadCount` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `_actor` | `Actor` | 名为 `_actor` 的 `Actor` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `service` | `NotificationDependency` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |

**输出**

- **Python 类型**：`NotificationUnreadCount`
- **语义**：返回 `NotificationUnreadCount` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `unread_count` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `mark_all_read`

- **源码**：`app/api/notification_routes.py:99`
- **签名**：`def mark_all_read(body: MarkNotificationsReadRequest, _actor: Actor, service: NotificationDependency) -> MarkNotificationsReadResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收请求正文、审计主体、领域服务对象，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `body` | `MarkNotificationsReadRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `_actor` | `Actor` | 名为 `_actor` 的 `Actor` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `service` | `NotificationDependency` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |

**输出**

- **Python 类型**：`MarkNotificationsReadResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `mark_all_read` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `mark_read`

- **源码**：`app/api/notification_routes.py:113`
- **签名**：`def mark_read(notification_id: str, body: MarkNotificationReadRequest, _actor: Actor, service: NotificationDependency) -> NotificationView`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收通知的 ID、请求正文、审计主体、领域服务对象，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `NotificationView` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `notification_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `body` | `MarkNotificationReadRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `_actor` | `Actor` | 名为 `_actor` 的 `Actor` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `service` | `NotificationDependency` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |

**输出**

- **Python 类型**：`NotificationView`
- **语义**：返回 `NotificationView` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `mark_read` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `stream_notifications`

- **源码**：`app/api/notification_routes.py:128`
- **签名**：`async def stream_notifications(request: Request, _actor: Actor, service: NotificationDependency, after: AfterQuery, last_event_id: LastEventIdHeader, follow: FollowQuery) -> StreamingResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，SSE id 使用 notification_seq；follow=false 便于测试 backlog。该函数接收业务请求、审计主体、领域服务对象、升级后运行报告等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `_actor` | `Actor` | 名为 `_actor` 的 `Actor` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `service` | `NotificationDependency` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |
| `after` | `AfterQuery` | 分页、文本切片或事件序列位置；用于确定本次读取的起止边界。；默认 0 |
| `last_event_id` | `LastEventIdHeader` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。；默认 空值 |
| `follow` | `FollowQuery` | 名为 `follow` 的 `FollowQuery` 领域输入；用于当前函数的业务处理，具体约束见校验分支。；默认 真 |

**输出**

- **Python 类型**：`StreamingResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
等待异步处理完成，并提交它产生的状态变更。
定义内部辅助函数 `generate`，供当前函数在后续步骤中调用。
构造并返回 `StreamingResponse` 结构化领域对象。
```

#### `stream_notifications.generate`

- **源码**：`app/api/notification_routes.py:141`
- **签名**：`async def generate()`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算数量、边界或类型判断结果，并把结果记为 增量读取游标；调用 `monotonic` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
只要当前条件（使用固定配置或常量值）成立，就重复以下处理：
    等待异步处理完成，并把结果记为 论文页码。
    遍历当前可迭代输入，每次把当前项记为当前处理项，然后读取通知，并保存为 增量读取游标；完成当前表达式对应的校验或状态操作。
    如果当前处理结果为空或为假，就结束当前函数，不返回业务值。
    如果当前条件（等待异步操作完成并取得结果（调用 `is_disconnected` 校验当前输入或状态））成立，就结束当前函数，不返回业务值。
    调用 `monotonic` 完成该函数的一项辅助处理，并把结果记为 当前时间。
    如果当前输入内容不小于当前处理结果，就完成当前表达式对应的校验或状态操作；读取当前时间，并保存为 后续步骤使用的结果。
    等待异步处理完成，并提交它产生的状态变更。
```

### `app/api/project_memory_routes.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `service`

- **源码**：`app/api/project_memory_routes.py:36`
- **签名**：`def service(request: Request)`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
返回项目记忆的当前值。
```

#### `create_project`

- **源码**：`app/api/project_memory_routes.py:44`
- **签名**：`def create_project(body: ProjectCreateRequest, key: IdempotencyKey, actor: Actor, svc: Service) -> 未显式标注（存在 return）`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收请求正文、映射键或对象字段名、审计主体、领域服务对象，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `body` | `ProjectCreateRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `key` | `IdempotencyKey` | 映射键或对象字段名；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `actor` | `Actor` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `svc` | `Service` | 领域服务对象；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
调用 `create_project` 组装当前阶段需要的领域对象，并返回处理结果。
```

#### `list_projects`

- **源码**：`app/api/project_memory_routes.py:56`
- **签名**：`def list_projects(actor: Actor, svc: Service, include_archived: bool, limit: int) -> 未显式标注（存在 return）`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收审计主体、领域服务对象、是否包含已归档记录的开关、结果数量上限，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `actor` | `Actor` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `svc` | `Service` | 领域服务对象；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `include_archived` | `bool` | 布尔条件或能力开关，用于控制流程分支。；默认 假 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。；默认 调用 Query(default=100, ge=1, le=500) |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
移除审计主体中的当前内容；调用 `list_projects` 读取或查询当前阶段需要的数据，并返回处理结果。
```

#### `get_project`

- **源码**：`app/api/project_memory_routes.py:70`
- **签名**：`def get_project(project_id: str, actor: Actor, svc: Service)`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现项目 ID、审计主体、领域服务对象，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `project_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `actor` | `Actor` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `svc` | `Service` | 领域服务对象；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
移除审计主体中的当前内容；调用 `get_project` 读取或查询当前阶段需要的数据，并返回处理结果。
```

#### `archive_project`

- **源码**：`app/api/project_memory_routes.py:76`
- **签名**：`def archive_project(project_id: str, body: ProjectArchiveRequest, key: IdempotencyKey, actor: Actor, svc: Service) -> 未显式标注（存在 return）`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现项目 ID、请求正文、映射键或对象字段名、审计主体等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `project_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `body` | `ProjectArchiveRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `key` | `IdempotencyKey` | 映射键或对象字段名；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `actor` | `Actor` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `svc` | `Service` | 领域服务对象；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
调用 `archive_project` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `bind_job`

- **源码**：`app/api/project_memory_routes.py:92`
- **签名**：`def bind_job(project_id: str, body: ProjectBindJobRequest, key: IdempotencyKey, actor: Actor, svc: Service, expected_project_version: int, expected_project_hash: str) -> 未显式标注（存在 return）`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现项目 ID、请求正文、映射键或对象字段名、审计主体等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `project_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `body` | `ProjectBindJobRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `key` | `IdempotencyKey` | 映射键或对象字段名；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `actor` | `Actor` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `svc` | `Service` | 领域服务对象；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `expected_project_version` | `int` | 调用方观察到的旧身份，用于 stale/CAS 校验，防止覆盖并发更新。；默认 调用 Header(alias='X-Project-Version') |
| `expected_project_hash` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。；默认 调用 Header(alias='X-Project-Hash') |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
调用 `bind_job` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `propose_manual`

- **源码**：`app/api/project_memory_routes.py:115`
- **签名**：`def propose_manual(project_id: str, body: ManualFactProposalRequest, key: IdempotencyKey, actor: Actor, svc: Service) -> 未显式标注（存在 return）`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现项目 ID、请求正文、映射键或对象字段名、审计主体等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `project_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `body` | `ManualFactProposalRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `key` | `IdempotencyKey` | 映射键或对象字段名；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `actor` | `Actor` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `svc` | `Service` | 领域服务对象；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
调用 `propose_manual` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `propose_from_chat`

- **源码**：`app/api/project_memory_routes.py:134`
- **签名**：`def propose_from_chat(project_id: str, body: ChatFactProposalRequest, key: IdempotencyKey, actor: Actor, svc: Service) -> 未显式标注（存在 return）`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现项目 ID、请求正文、映射键或对象字段名、审计主体等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `project_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `body` | `ChatFactProposalRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `key` | `IdempotencyKey` | 映射键或对象字段名；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `actor` | `Actor` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `svc` | `Service` | 领域服务对象；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
调用 `propose_from_chat` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `list_facts`

- **源码**：`app/api/project_memory_routes.py:150`
- **签名**：`def list_facts(project_id: str, actor: Actor, svc: Service, include_terminal: bool, limit: int) -> 未显式标注（存在 return）`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现项目 ID、审计主体、领域服务对象、是否包含已终止运行的开关等输入，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `project_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `actor` | `Actor` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `svc` | `Service` | 领域服务对象；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `include_terminal` | `bool` | 布尔条件或能力开关，用于控制流程分支。；默认 假 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。；默认 调用 Query(default=100, ge=1, le=1000) |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
移除审计主体中的当前内容；调用 `list_facts` 读取或查询当前阶段需要的数据，并返回处理结果。
```

#### `fact_context`

- **源码**：`app/api/project_memory_routes.py:166`
- **签名**：`def fact_context(project_id: str, actor: Actor, svc: Service)`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现项目 ID、审计主体、领域服务对象，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `project_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `actor` | `Actor` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `svc` | `Service` | 领域服务对象；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
移除审计主体中的当前内容；调用 `for_project` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `confirm_fact`

- **源码**：`app/api/project_memory_routes.py:175`
- **签名**：`def confirm_fact(project_id: str, fact_id: str, body: FactConfirmRequest, key: IdempotencyKey, actor: Actor, svc: Service) -> 未显式标注（存在 return）`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现项目 ID、项目事实记录的 ID、请求正文、映射键或对象字段名等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `project_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `fact_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `body` | `FactConfirmRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `key` | `IdempotencyKey` | 映射键或对象字段名；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `actor` | `Actor` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `svc` | `Service` | 领域服务对象；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
调用 `get_fact` 读取或查询当前阶段需要的数据，并把结果记为 项目事实记录。
如果复现项目 ID不等于复现项目 ID，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
调用 `confirm` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `correct_fact`

- **源码**：`app/api/project_memory_routes.py:195`
- **签名**：`def correct_fact(project_id: str, fact_id: str, body: FactCorrectRequest, key: IdempotencyKey, actor: Actor, svc: Service) -> 未显式标注（存在 return）`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现项目 ID、项目事实记录的 ID、请求正文、映射键或对象字段名等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `project_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `fact_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `body` | `FactCorrectRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `key` | `IdempotencyKey` | 映射键或对象字段名；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `actor` | `Actor` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `svc` | `Service` | 领域服务对象；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
调用 `get_fact` 读取或查询当前阶段需要的数据，并把结果记为 项目事实记录。
如果复现项目 ID不等于复现项目 ID，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
调用 `correct` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `revoke_fact`

- **源码**：`app/api/project_memory_routes.py:215`
- **签名**：`def revoke_fact(project_id: str, fact_id: str, body: FactTerminalRequest, key: IdempotencyKey, actor: Actor, svc: Service) -> 未显式标注（存在 return）`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现项目 ID、项目事实记录的 ID、请求正文、映射键或对象字段名等输入，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `project_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `fact_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `body` | `FactTerminalRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `key` | `IdempotencyKey` | 映射键或对象字段名；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `actor` | `Actor` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `svc` | `Service` | 领域服务对象；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
调用 `get_fact` 读取或查询当前阶段需要的数据，并把结果记为 项目事实记录。
如果复现项目 ID不等于复现项目 ID，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
调用 `revoke` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `delete_fact`

- **源码**：`app/api/project_memory_routes.py:235`
- **签名**：`def delete_fact(project_id: str, fact_id: str, body: FactTerminalRequest, key: IdempotencyKey, actor: Actor, svc: Service) -> 未显式标注（存在 return）`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现项目 ID、项目事实记录的 ID、请求正文、映射键或对象字段名等输入，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `project_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `fact_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `body` | `FactTerminalRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `key` | `IdempotencyKey` | 映射键或对象字段名；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `actor` | `Actor` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `svc` | `Service` | 领域服务对象；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
调用 `get_fact` 读取或查询当前阶段需要的数据，并把结果记为 项目事实记录。
如果复现项目 ID不等于复现项目 ID，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
调用 `delete` 完成该函数的一项辅助处理，并返回处理结果。
```

### `app/api/rerun_routes.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `rerun_service`

- **源码**：`app/api/rerun_routes.py:32`
- **签名**：`def rerun_service(request: Request) -> RerunService`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `RerunService` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`RerunService`
- **语义**：返回 `RerunService` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
返回前一步处理得到的结果。
```

#### `create_rerun_proposal`

- **源码**：`app/api/rerun_routes.py:46`
- **签名**：`def create_rerun_proposal(body: RerunProposalCreateRequest, idempotency_key: IdempotencyKey, actor: Actor, service: RerunDependency) -> RerunProposalMutationResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收请求正文、请求幂等键、审计主体、领域服务对象，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `body` | `RerunProposalCreateRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `idempotency_key` | `IdempotencyKey` | 调用方提供的幂等键；重复请求应复用同一结果，而不是再次产生副作用。 |
| `actor` | `Actor` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `service` | `RerunDependency` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |

**输出**

- **Python 类型**：`RerunProposalMutationResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
移除审计主体中的当前内容；调用 `create_proposal` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果；构造并返回 `RerunProposalMutationResponse` 结构化领域对象。
```

#### `get_rerun_proposal`

- **源码**：`app/api/rerun_routes.py:67`
- **签名**：`def get_rerun_proposal(proposal_id: str, actor: Actor, service: RerunDependency) -> RerunProposalRecord`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收修复或重跑提案的 ID、审计主体、领域服务对象，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `proposal_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `actor` | `Actor` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `service` | `RerunDependency` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |

**输出**

- **Python 类型**：`RerunProposalRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
移除审计主体中的当前内容；调用 `get_proposal` 读取或查询当前阶段需要的数据，并返回处理结果。
```

#### `submit_rerun_proposal`

- **源码**：`app/api/rerun_routes.py:80`
- **签名**：`def submit_rerun_proposal(proposal_id: str, body: RerunProposalSubmitRequest, idempotency_key: IdempotencyKey, actor: Actor, service: RerunDependency) -> RerunSubmissionResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收修复或重跑提案的 ID、请求正文、请求幂等键、审计主体等输入，用于驱动或监督一次论文复现运行，记录命令、工作目录、资源使用、状态迁移和失败原因，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `proposal_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `body` | `RerunProposalSubmitRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `idempotency_key` | `IdempotencyKey` | 调用方提供的幂等键；重复请求应复用同一结果，而不是再次产生副作用。 |
| `actor` | `Actor` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `service` | `RerunDependency` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |

**输出**

- **Python 类型**：`RerunSubmissionResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
移除审计主体中的当前内容；调用 `submit_proposal` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；构造并返回 `RerunSubmissionResponse` 结构化领域对象。
```

#### `cancel_rerun_proposal`

- **源码**：`app/api/rerun_routes.py:104`
- **签名**：`def cancel_rerun_proposal(proposal_id: str, body: RerunProposalCancelRequest, actor: Actor, service: RerunDependency) -> RerunProposalRecord`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收修复或重跑提案的 ID、请求正文、审计主体、领域服务对象，用于驱动或监督一次论文复现运行，记录命令、工作目录、资源使用、状态迁移和失败原因，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `proposal_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `body` | `RerunProposalCancelRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `actor` | `Actor` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `service` | `RerunDependency` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |

**输出**

- **Python 类型**：`RerunProposalRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
移除审计主体中的当前内容；调用 `cancel_proposal` 完成该函数的一项辅助处理，并返回处理结果。
```

### `app/api/resource_routes.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `resource_service`

- **源码**：`app/api/resource_routes.py:118`
- **签名**：`def resource_service(request: Request) -> ResourceService`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ResourceService` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`ResourceService`
- **语义**：返回 `ResourceService` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `getattr` 完成该函数的一项辅助处理，并把结果记为 领域服务对象。
如果领域服务对象为空，就拒绝继续处理并抛出 `HTTPException`，向调用方报告输入或运行失败。
返回领域服务对象的当前值。
```

#### `_to_response`

- **源码**：`app/api/resource_routes.py:138`
- **签名**：`def _to_response(record: 未显式标注, replayed: bool | None) -> ResourceMutationResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收领域记录、重放的，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `record` | `未显式标注` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |
| `replayed` | `bool | None` | 重放的；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 空值 |

**输出**

- **Python 类型**：`ResourceMutationResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `sanitize_resource_view` 完成该函数的一项辅助处理，并把结果记为 视图；构造并返回 `ResourceMutationResponse` 结构化领域对象。
```

#### `_decided_at`

- **源码**：`app/api/resource_routes.py:150`
- **签名**：`def _decided_at() -> str`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `isoformat` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `submit_resource`

- **源码**：`app/api/resource_routes.py:159`
- **签名**：`def submit_resource(body: ResourceSubmitBody, idempotency_key: IdempotencyKey, _actor: Actor, service: ResourceServiceDependency) -> ResourceMutationResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收请求正文、请求幂等键、审计主体、领域服务对象，用于驱动或监督一次论文复现运行，记录命令、工作目录、资源使用、状态迁移和失败原因，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `body` | `ResourceSubmitBody` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `idempotency_key` | `IdempotencyKey` | 调用方提供的幂等键；重复请求应复用同一结果，而不是再次产生副作用。 |
| `_actor` | `Actor` | 名为 `_actor` 的 `Actor` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `service` | `ResourceServiceDependency` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |

**输出**

- **Python 类型**：`ResourceMutationResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
先尝试完成以下处理：
    构造 `ResourceRequest` 结构化领域对象，并把结果记为 业务请求。
如果出现 `ValueError`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `HTTPException`，向调用方报告输入或运行失败。
先尝试完成以下处理：
    调用 `submit` 完成该函数的一项辅助处理，并把结果记为 多个解包结果。
如果出现 `ValueError`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `HTTPException`，向调用方报告输入或运行失败。
调用 `_to_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `get_resource`

- **源码**：`app/api/resource_routes.py:201`
- **签名**：`def get_resource(resource_id: str, _actor: Actor, service: ResourceServiceDependency) -> ResourceResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收输入资源 ID、审计主体、领域服务对象，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `resource_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `_actor` | `Actor` | 名为 `_actor` 的 `Actor` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `service` | `ResourceServiceDependency` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |

**输出**

- **Python 类型**：`ResourceResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
先尝试完成以下处理：
    从领域服务对象读取所需的状态或领域记录，并把结果记为 领域记录。
如果出现 `ResourceNotFoundError`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `HTTPException`，向调用方报告输入或运行失败。
构造并返回 `ResourceResponse` 结构化领域对象。
```

#### `list_resource_events`

- **源码**：`app/api/resource_routes.py:225`
- **签名**：`def list_resource_events(resource_id: str, _actor: Actor, service: ResourceServiceDependency, limit: int) -> EventPage`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收输入资源 ID、审计主体、领域服务对象、结果数量上限，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `EventPage` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `resource_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `_actor` | `Actor` | 名为 `_actor` 的 `Actor` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `service` | `ResourceServiceDependency` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。；默认 100 |

**输出**

- **Python 类型**：`EventPage`
- **语义**：返回 `EventPage` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
先尝试完成以下处理：
    调用 `events` 完成该函数的一项辅助处理，并把结果记为 审计事件集合。
如果出现 `ResourceNotFoundError`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `HTTPException`，向调用方报告输入或运行失败。
遍历并筛选输入，将整理后的结果保存为 待处理项集合；构造并返回 `EventPage` 结构化领域对象。
```

#### `submit_decision`

- **源码**：`app/api/resource_routes.py:259`
- **签名**：`def submit_decision(resource_id: str, body: ResourceDecisionBody, _actor: Actor, service: ResourceServiceDependency) -> ResourceMutationResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收输入资源 ID、请求正文、审计主体、领域服务对象，用于驱动或监督一次论文复现运行，记录命令、工作目录、资源使用、状态迁移和失败原因，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `resource_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `body` | `ResourceDecisionBody` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `_actor` | `Actor` | 名为 `_actor` 的 `Actor` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `service` | `ResourceServiceDependency` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |

**输出**

- **Python 类型**：`ResourceMutationResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
构造 `ResourceApproval` 结构化领域对象，并把结果记为 人工审批记录。
先尝试完成以下处理：
    调用 `approve` 完成该函数的一项辅助处理，并把结果记为 领域记录。
如果出现 `ResourceNotFoundError`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `HTTPException`，向调用方报告输入或运行失败。
如果出现 `ResourceConflictError`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `HTTPException`，向调用方报告输入或运行失败。
调用 `_to_response` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `cancel_resource`

- **源码**：`app/api/resource_routes.py:301`
- **签名**：`def cancel_resource(resource_id: str, body: CancelBody, _actor: Actor, service: ResourceServiceDependency) -> ResourceMutationResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收输入资源 ID、请求正文、审计主体、领域服务对象，用于驱动或监督一次论文复现运行，记录命令、工作目录、资源使用、状态迁移和失败原因，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `resource_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `body` | `CancelBody` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `_actor` | `Actor` | 名为 `_actor` 的 `Actor` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `service` | `ResourceServiceDependency` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |

**输出**

- **Python 类型**：`ResourceMutationResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
先尝试完成以下处理：
    调用 `cancel` 完成该函数的一项辅助处理，并把结果记为 领域记录。
如果出现 `ResourceNotFoundError`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `HTTPException`，向调用方报告输入或运行失败。
如果出现 `ResourceConflictError`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `HTTPException`，向调用方报告输入或运行失败。
调用 `_to_response` 完成该函数的一项辅助处理，并返回处理结果。
```

### `app/api/retention_routes.py`

**模块作用**：Phase 35 Retention API 路由。

#### `_bundle`

- **源码**：`app/api/retention_routes.py:19`
- **签名**：`def _bundle(request: Request)`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
返回前一步处理得到的结果。
```

#### `_service`

- **源码**：`app/api/retention_routes.py:22`
- **签名**：`def _service(request: Request)`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
读取前一步操作返回对象的领域服务对象，并保存为 领域服务对象。
如果领域服务对象为空，就拒绝继续处理并抛出 `RetentionBackendUnsupported`，向调用方报告输入或运行失败。
返回领域服务对象的当前值。
```

#### `storage_summary`

- **源码**：`app/api/retention_routes.py:31`
- **签名**：`def storage_summary(request: Request, _actor: Actor) -> StorageSummaryView`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、审计主体，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `StorageSummaryView` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `_actor` | `Actor` | 名为 `_actor` 的 `Actor` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`StorageSummaryView`
- **语义**：返回 `StorageSummaryView` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `from_summary` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `create_plan`

- **源码**：`app/api/retention_routes.py:37`
- **签名**：`def create_plan(request: Request, _actor: Actor) -> CleanupPlanView`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、审计主体，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `CleanupPlanView` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `_actor` | `Actor` | 名为 `_actor` 的 `Actor` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`CleanupPlanView`
- **语义**：返回 `CleanupPlanView` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `from_plan` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `get_plan`

- **源码**：`app/api/retention_routes.py:41`
- **签名**：`def get_plan(plan_id: str, request: Request, _actor: Actor) -> CleanupPlanView`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收实验计划的 ID、业务请求、审计主体，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `CleanupPlanView` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `plan_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `_actor` | `Actor` | 名为 `_actor` 的 `Actor` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`CleanupPlanView`
- **语义**：返回 `CleanupPlanView` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `from_plan` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `confirm_plan`

- **源码**：`app/api/retention_routes.py:48`
- **签名**：`def confirm_plan(plan_id: str, body: PlanConfirmRequest, request: Request, _actor: Actor) -> CleanupPlanView`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收实验计划的 ID、请求正文、业务请求、审计主体，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `CleanupPlanView` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `plan_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `body` | `PlanConfirmRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `_actor` | `Actor` | 名为 `_actor` 的 `Actor` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`CleanupPlanView`
- **语义**：返回 `CleanupPlanView` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `from_plan` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `sweep_plan`

- **源码**：`app/api/retention_routes.py:65`
- **签名**：`def sweep_plan(plan_id: str, body: PlanConfirmRequest, request: Request, _actor: Actor) -> CleanupResultView`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收实验计划的 ID、请求正文、业务请求、审计主体，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `plan_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `body` | `PlanConfirmRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `_actor` | `Actor` | 名为 `_actor` 的 `Actor` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`CleanupResultView`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `from_result` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `list_holds`

- **源码**：`app/api/retention_routes.py:79`
- **签名**：`def list_holds(request: Request, _actor: Actor) -> list[RetentionHold]`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、审计主体，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `_actor` | `Actor` | 名为 `_actor` 的 `Actor` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`list[RetentionHold]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
调用 `list_holds` 读取或查询当前阶段需要的数据，并返回处理结果。
```

#### `put_hold`

- **源码**：`app/api/retention_routes.py:83`
- **签名**：`def put_hold(job_id: str, body: HoldRequest, request: Request, actor: Actor) -> RetentionHold`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务 ID、请求正文、业务请求、审计主体，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终标注为 `RetentionHold` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `body` | `HoldRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `actor` | `Actor` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |

**输出**

- **Python 类型**：`RetentionHold`
- **语义**：返回 `RetentionHold` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `create_hold` 组装当前阶段需要的领域对象，并返回处理结果。
```

#### `delete_hold`

- **源码**：`app/api/retention_routes.py:96`
- **签名**：`def delete_hold(job_id: str, request: Request, _actor: Actor) -> None`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务 ID、业务请求、审计主体，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `_actor` | `Actor` | 名为 `_actor` 的 `Actor` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `delete_hold` 持久化或更新当前领域数据。
```

### `app/api/routes.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `interaction_service`

- **源码**：`app/api/routes.py:64`
- **签名**：`def interaction_service(request: Request) -> InteractionService`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `InteractionService` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`InteractionService`
- **语义**：返回 `InteractionService` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
返回前一步处理得到的结果。
```

#### `artifact_catalog`

- **源码**：`app/api/routes.py:70`
- **签名**：`def artifact_catalog(request: Request) -> ArtifactCatalog`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ArtifactCatalog` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`ArtifactCatalog`
- **语义**：返回 `ArtifactCatalog` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
返回Artifact的当前值。
```

#### `artifact_delivery_service`

- **源码**：`app/api/routes.py:76`
- **签名**：`def artifact_delivery_service(request: Request) -> ArtifactDeliveryService`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ArtifactDeliveryService` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`ArtifactDeliveryService`
- **语义**：返回 `ArtifactDeliveryService` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
返回Artifact的当前值。
```

#### `_get_telemetry`

- **源码**：`app/api/routes.py:136`
- **签名**：`def _get_telemetry(request: Request)`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
先尝试完成以下处理：
    调用 `getattr` 完成该函数的一项辅助处理，并把结果记为 运行观测数据。
    如果运行观测数据不为空，就返回运行观测数据的当前值。
如果出现 `Exception`：
    不执行额外操作。
构造并返回 `NoOpTelemetry` 结构化领域对象。
```

#### `_sse`

- **源码**：`app/api/routes.py:146`
- **签名**：`def _sse(event: dict) -> str`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，把单个事件编码为标准 SSE frame。该函数接收事件，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `event` | `dict` | 名为 `event` 的键值映射；键和值分别承载的业务字段由读取/写入分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
将结构化内容序列化或编码为可传输表示，并把结果记为 结构化请求载荷；返回当前计算得到的结果。
```

#### `_iter_blob`

- **源码**：`app/api/routes.py:161`
- **签名**：`def _iter_blob(body: 未显式标注, chunk_bytes: int) -> Iterator[bytes]`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，无论客户端正常完成还是中断，最终都关闭后端 body。该函数接收请求正文、检索文本块的字节内容，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `Iterator[bytes]` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `body` | `未显式标注` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `chunk_bytes` | `int` | 名为 `chunk_bytes` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`Iterator[bytes]`
- **语义**：返回惰性迭代结果，调用方逐项消费。

**伪代码**

```text
先尝试完成以下处理：
    只要当前条件（使用固定配置或常量值）成立，就重复以下处理：
        调用 `read` 完成该函数的一项辅助处理，并把结果记为 检索文本块。
        如果检索文本块为空或为假，就立即结束当前循环。
        完成当前表达式对应的校验或状态操作。
无论成功还是失败，最后都要：
    关闭请求正文并释放相关资源。
```

#### `_attachment_disposition`

- **源码**：`app/api/routes.py:183`
- **签名**：`def _attachment_disposition(filename: str) -> str`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，同时提供保守 ASCII fallback 和 RFC 5987 UTF-8 文件名。该函数接收目标文件名，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `filename` | `str` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
计算计算当前表达式的结果，并保存为 当前处理结果；读取前一步操作返回对象中的对应字段，并保存为 后续步骤使用的结果。
如果当前处理结果为空或为假，就计算使用固定配置或常量值，并保存为 当前处理结果。
返回当前计算得到的结果。
```

#### `_iter_file_and_delete`

- **源码**：`app/api/routes.py:201`
- **签名**：`def _iter_file_and_delete(path: Path, chunk_bytes: int) -> Iterator[bytes]`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，导出响应完成或断开时都删除临时 ZIP。该函数接收文件或目录路径、检索文本块的字节内容，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `Iterator[bytes]` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |
| `chunk_bytes` | `int` | 名为 `chunk_bytes` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`Iterator[bytes]`
- **语义**：返回惰性迭代结果，调用方逐项消费。

**伪代码**

```text
先尝试完成以下处理：
    进入上下文“调用 `open` 完成该函数的一项辅助处理，并把上下文资源交给当前处理结果”，退出时自动清理资源：
        只要当前条件（使用固定配置或常量值）成立，就重复以下处理：
            调用 `read` 完成该函数的一项辅助处理，并把结果记为 检索文本块。
            如果检索文本块为空或为假，就立即结束当前循环。
            完成当前表达式对应的校验或状态操作。
无论成功还是失败，最后都要：
    调用 `unlink` 完成该函数的一项辅助处理。
```

#### `create_job`

- **源码**：`app/api/routes.py:224`
- **签名**：`def create_job(request: Request, body: JobCreateRequest, idempotency_key: IdempotencyKey, _actor: Actor, service: InteractionDependency) -> JobMutationResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、请求正文、请求幂等键、审计主体等输入，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `body` | `JobCreateRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `idempotency_key` | `IdempotencyKey` | 调用方提供的幂等键；重复请求应复用同一结果，而不是再次产生副作用。 |
| `_actor` | `Actor` | 名为 `_actor` 的 `Actor` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `service` | `InteractionDependency` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |

**输出**

- **Python 类型**：`JobMutationResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_get_telemetry` 读取或查询当前阶段需要的数据，并把结果记为 运行观测数据。
先尝试完成以下处理：
    在上下文“调用 `span` 完成该函数的一项辅助处理”中调用 `create_job` 组装当前阶段需要的领域对象，并返回处理结果，退出时自动清理资源。
如果出现 `Exception`：
    调用 `create_job` 组装当前阶段需要的领域对象，并返回处理结果。
```

#### `list_jobs`

- **源码**：`app/api/routes.py:255`
- **签名**：`def list_jobs(request: Request, _actor: Actor, service: InteractionDependency, status: JobStatusQuery, limit: PageLimitQuery) -> JobListResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、审计主体、领域服务对象、当前状态等输入，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `_actor` | `Actor` | 名为 `_actor` 的 `Actor` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `service` | `InteractionDependency` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |
| `status` | `JobStatusQuery` | 来源、类别、用途、后端、状态或操作原因等控制字段；通常对应有限的业务枚举或审计文本。；默认 空值 |
| `limit` | `PageLimitQuery` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。；默认 50 |

**输出**

- **Python 类型**：`JobListResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_get_telemetry` 读取或查询当前阶段需要的数据，并把结果记为 运行观测数据。
先尝试完成以下处理：
    在上下文“调用 `span` 完成该函数的一项辅助处理”中计算数量、边界或类型判断结果，并把结果记为 该调用返回的结果；调用 `list_jobs` 读取或查询当前阶段需要的数据，并把结果记为 待处理项集合；构造并返回 `JobListResponse` 结构化领域对象，退出时自动清理资源。
如果出现 `Exception`：
    计算数量、边界或类型判断结果，并把结果记为 该调用返回的结果；调用 `list_jobs` 读取或查询当前阶段需要的数据，并把结果记为 待处理项集合；构造并返回 `JobListResponse` 结构化领域对象。
```

#### `get_job`

- **源码**：`app/api/routes.py:301`
- **签名**：`def get_job(request: Request, job_id: str, _actor: Actor, service: InteractionDependency) -> JobView`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、复现任务 ID、审计主体、领域服务对象，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `JobView` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `_actor` | `Actor` | 名为 `_actor` 的 `Actor` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `service` | `InteractionDependency` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |

**输出**

- **Python 类型**：`JobView`
- **语义**：返回 `JobView` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `_get_telemetry` 读取或查询当前阶段需要的数据，并把结果记为 运行观测数据。
先尝试完成以下处理：
    在上下文“调用 `span` 完成该函数的一项辅助处理”中调用 `get_job` 读取或查询当前阶段需要的数据，并返回处理结果，退出时自动清理资源。
如果出现 `Exception`：
    调用 `get_job` 读取或查询当前阶段需要的数据，并返回处理结果。
```

#### `submit_decision`

- **源码**：`app/api/routes.py:324`
- **签名**：`def submit_decision(job_id: str, body: DecisionEnvelope, idempotency_key: IdempotencyKey, actor: Actor, service: InteractionDependency) -> JobMutationResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务 ID、请求正文、请求幂等键、审计主体等输入，用于驱动或监督一次论文复现运行，记录命令、工作目录、资源使用、状态迁移和失败原因，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `body` | `DecisionEnvelope` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `idempotency_key` | `IdempotencyKey` | 调用方提供的幂等键；重复请求应复用同一结果，而不是再次产生副作用。 |
| `actor` | `Actor` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `service` | `InteractionDependency` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |

**输出**

- **Python 类型**：`JobMutationResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `submit_decision` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `cancel_job`

- **源码**：`app/api/routes.py:345`
- **签名**：`def cancel_job(job_id: str, body: CancelEnvelope, idempotency_key: IdempotencyKey, actor: Actor, service: InteractionDependency) -> JobMutationResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务 ID、请求正文、请求幂等键、审计主体等输入，用于驱动或监督一次论文复现运行，记录命令、工作目录、资源使用、状态迁移和失败原因，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `body` | `CancelEnvelope` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `idempotency_key` | `IdempotencyKey` | 调用方提供的幂等键；重复请求应复用同一结果，而不是再次产生副作用。 |
| `actor` | `Actor` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |
| `service` | `InteractionDependency` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |

**输出**

- **Python 类型**：`JobMutationResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `cancel_job` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `list_events`

- **源码**：`app/api/routes.py:364`
- **签名**：`def list_events(job_id: str, _actor: Actor, service: InteractionDependency, after: EventCursorQuery, limit: PageLimitQuery) -> EventPage`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务 ID、审计主体、领域服务对象、升级后运行报告等输入，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `EventPage` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `_actor` | `Actor` | 名为 `_actor` 的 `Actor` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `service` | `InteractionDependency` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |
| `after` | `EventCursorQuery` | 分页、文本切片或事件序列位置；用于确定本次读取的起止边界。；默认 0 |
| `limit` | `PageLimitQuery` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。；默认 100 |

**输出**

- **Python 类型**：`EventPage`
- **语义**：返回 `EventPage` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `events_after` 完成该函数的一项辅助处理，并把结果记为 审计事件集合；构造并返回 `EventPage` 结构化领域对象。
```

#### `stream_events`

- **源码**：`app/api/routes.py:392`
- **签名**：`async def stream_events(request: Request, job_id: str, _actor: Actor, service: InteractionDependency, after: EventCursorQuery, last_event_id: LastEventIdHeader, follow: FollowQuery) -> StreamingResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，follow=false 用于读取当前 backlog 后关闭，也让离线测试不会永久阻塞。该函数接收业务请求、复现任务 ID、审计主体、领域服务对象等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `_actor` | `Actor` | 名为 `_actor` 的 `Actor` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `service` | `InteractionDependency` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |
| `after` | `EventCursorQuery` | 分页、文本切片或事件序列位置；用于确定本次读取的起止边界。；默认 0 |
| `last_event_id` | `LastEventIdHeader` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。；默认 空值 |
| `follow` | `FollowQuery` | 名为 `follow` 的 `FollowQuery` 领域输入；用于当前函数的业务处理，具体约束见校验分支。；默认 真 |

**输出**

- **Python 类型**：`StreamingResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_get_telemetry` 读取或查询当前阶段需要的数据，并把结果记为 运行观测数据。
定义内部辅助函数 `run_with_telemetry`，供当前函数在后续步骤中调用。
先尝试完成以下处理：
    在上下文“调用 `span` 完成该函数的一项辅助处理”中返回当前计算得到的结果，退出时自动清理资源。
如果出现 `Exception`：
    返回当前计算得到的结果。
```

#### `stream_events.run_with_telemetry`

- **源码**：`app/api/routes.py:407`
- **签名**：`async def run_with_telemetry()`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于驱动或监督一次论文复现运行，记录命令、工作目录、资源使用、状态迁移和失败原因，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
调用 `get_job` 读取或查询当前阶段需要的数据。
定义内部辅助函数 `generate`，供当前函数在后续步骤中调用。
构造并返回 `StreamingResponse` 结构化领域对象。
```

#### `stream_events.run_with_telemetry.generate`

- **源码**：`app/api/routes.py:412`
- **签名**：`async def generate()`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算数量、边界或类型判断结果，并把结果记为 增量读取游标；调用 `monotonic` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
只要当前条件（使用固定配置或常量值）成立，就重复以下处理：
    等待异步处理完成，并把结果记为 审计事件集合。
    遍历由审计事件集合组成的集合或迭代器，每次把当前项记为事件，然后读取事件的 ID，并保存为 增量读取游标；完成当前表达式对应的校验或状态操作。
    如果当前处理结果为空或为假，就结束当前函数，不返回业务值。
    等待异步处理完成，并把结果记为 当前值。
    如果当前状态属于任务集合 且 审计事件集合为空或为假，就结束当前函数，不返回业务值。
    如果当前条件（等待异步操作完成并取得结果（调用 `is_disconnected` 校验当前输入或状态））成立，就结束当前函数，不返回业务值。
    调用 `monotonic` 完成该函数的一项辅助处理，并把结果记为 当前时间。
    如果当前输入内容不小于当前处理结果，就完成当前表达式对应的校验或状态操作；读取当前时间，并保存为 后续步骤使用的结果。
    等待异步处理完成，并提交它产生的状态变更。
```

#### `list_artifacts`

- **源码**：`app/api/routes.py:489`
- **签名**：`def list_artifacts(job_id: str, _actor: Actor, service: InteractionDependency, delivery: ArtifactDeliveryDependency) -> ArtifactListResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务 ID、审计主体、领域服务对象、通知投递记录，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `_actor` | `Actor` | 名为 `_actor` 的 `Actor` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `service` | `InteractionDependency` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |
| `delivery` | `ArtifactDeliveryDependency` | 通知投递记录；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`ArtifactListResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
从任务读取所需的状态或领域记录，并把结果记为 任务；从通知投递记录读取所需的状态或领域记录，并把结果记为 待处理项集合；构造并返回 `ArtifactListResponse` 结构化领域对象。
```

#### `preview_artifact`

- **源码**：`app/api/routes.py:510`
- **签名**：`def preview_artifact(job_id: str, artifact_id: str, _actor: Actor, service: InteractionDependency, delivery: ArtifactDeliveryDependency) -> ArtifactPreviewResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务 ID、Artifact的 ID、审计主体、领域服务对象等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `artifact_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `_actor` | `Actor` | 名为 `_actor` 的 `Actor` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `service` | `InteractionDependency` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |
| `delivery` | `ArtifactDeliveryDependency` | 通知投递记录；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`ArtifactPreviewResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
从任务读取所需的状态或领域记录，并把结果记为 任务；调用 `preview` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `download_artifact`

- **源码**：`app/api/routes.py:535`
- **签名**：`def download_artifact(job_id: str, artifact_id: str, _actor: Actor, service: InteractionDependency, catalog: ArtifactCatalogDependency) -> StreamingResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务 ID、Artifact的 ID、审计主体、领域服务对象等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `artifact_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `_actor` | `Actor` | 名为 `_actor` 的 `Actor` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `service` | `InteractionDependency` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |
| `catalog` | `ArtifactCatalogDependency` | 持久化或目录访问端口；负责读取、CAS 更新或 Artifact 定位。 |

**输出**

- **Python 类型**：`StreamingResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
从任务读取所需的状态或领域记录，并把结果记为 任务；调用 `open` 完成该函数的一项辅助处理，并把结果记为 已打开资源；读取工具或组件描述信息，并保存为 工具或组件描述信息；读取前一步操作返回对象的对象名称，并保存为 目标文件名。
构造并返回 `StreamingResponse` 结构化领域对象。
```

#### `export_job`

- **源码**：`app/api/routes.py:590`
- **签名**：`def export_job(job_id: str, _actor: Actor, service: InteractionDependency, delivery: ArtifactDeliveryDependency) -> StreamingResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务 ID、审计主体、领域服务对象、通知投递记录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `_actor` | `Actor` | 名为 `_actor` 的 `Actor` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `service` | `InteractionDependency` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |
| `delivery` | `ArtifactDeliveryDependency` | 通知投递记录；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`StreamingResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
从任务读取所需的状态或领域记录，并把结果记为 任务；调用 `get_job` 读取或查询当前阶段需要的数据，并把结果记为 任务；调用 `build_export` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果。
先尝试完成以下处理：
    构造并返回 `StreamingResponse` 结构化领域对象。
如果出现 `Exception`：
    调用 `unlink` 完成该函数的一项辅助处理；重新抛出当前异常，保持原始失败信息。
```

#### `tail_log`

- **源码**：`app/api/routes.py:646`
- **签名**：`def tail_log(request: Request, job_id: str, _actor: Actor, service: InteractionDependency, lines: LogLinesQuery) -> LogTailResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收业务请求、复现任务 ID、审计主体、领域服务对象等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `_actor` | `Actor` | 名为 `_actor` 的 `Actor` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `service` | `InteractionDependency` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |
| `lines` | `LogLinesQuery` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。；默认 100 |

**输出**

- **Python 类型**：`LogTailResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_get_telemetry` 读取或查询当前阶段需要的数据，并把结果记为 运行观测数据。
先尝试完成以下处理：
    在上下文“调用 `span` 完成该函数的一项辅助处理”中调用 `tail_log` 完成该函数的一项辅助处理，并返回处理结果，退出时自动清理资源。
如果出现 `Exception`：
    调用 `tail_log` 完成该函数的一项辅助处理，并返回处理结果。
```

### `app/api/ui_routes.py`

**模块作用**：Phase 30 UI API：Timeline 投影与 UI 配置。

#### `interaction_service`

- **源码**：`app/api/ui_routes.py:30`
- **签名**：`def interaction_service(request: Request) -> InteractionService`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，从 app.state 取用例服务。该函数接收业务请求，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `InteractionService` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `request` | `Request` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`InteractionService`
- **语义**：返回 `InteractionService` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
返回前一步处理得到的结果。
```

#### `ui_config`

- **源码**：`app/api/ui_routes.py:49`
- **签名**：`def ui_config(_actor: Actor) -> UiConfigResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收审计主体，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `_actor` | `Actor` | 名为 `_actor` 的 `Actor` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`UiConfigResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `load_execution_profiles` 读取或查询当前阶段需要的数据，并把结果记为 MCP Client 配置档案集合；构造并返回 `UiConfigResponse` 结构化领域对象。
```

#### `job_timeline`

- **源码**：`app/api/ui_routes.py:76`
- **签名**：`def job_timeline(job_id: str, _actor: Actor, service: InteractionDependency) -> TimelineResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务 ID、审计主体、领域服务对象，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `_actor` | `Actor` | 名为 `_actor` 的 `Actor` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `service` | `InteractionDependency` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |

**输出**

- **Python 类型**：`TimelineResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `get_job` 读取或查询当前阶段需要的数据，并把结果记为 复现任务记录；调用 `events_after` 完成该函数的一项辅助处理，并把结果记为 审计事件集合；调用 `build_timeline` 组装当前阶段需要的领域对象，并返回处理结果。
```

### `app/artifact_delivery/service.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `utc_now`

- **源码**：`app/artifact_delivery/service.py:62`
- **签名**：`def utc_now() -> str`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

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

- **源码**：`app/artifact_delivery/service.py:66`
- **签名**：`def canonical_json_bytes(payload: dict[str, Any]) -> bytes`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，manifest hash 使用稳定 JSON 编码，不能依赖缩进或 key 顺序。该函数接收结构化请求载荷，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `bytes` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `payload` | `dict[str, Any]` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`bytes`
- **语义**：返回 `bytes` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
将结构化内容序列化或编码为可传输表示，并返回处理结果。
```

#### `preview_supported`

- **源码**：`app/artifact_delivery/service.py:77`
- **签名**：`def preview_supported(*, media_type: str, relative_path: str) -> bool`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，公开给 API 与 Web 共用的确定性预览能力判断。该函数接收Artifact 媒体类型、仓库内相对路径，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `media_type` | `str` | Artifact 媒体类型；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `relative_path` | `str` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
对前一步操作返回对象中的对应字段中的文本执行规范化或拆分，再对返回文本执行规范化或拆分，并把结果记为 媒体类型；对前一步操作返回对象的文件扩展名或文本后缀中的文本执行规范化或拆分，并把结果记为 文件扩展名或文本后缀；返回组合判断结果。
```

#### `_archive_path`

- **源码**：`app/artifact_delivery/service.py:88`
- **签名**：`def _archive_path(relative_path: str) -> str`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，把 Catalog 相对路径变成安全 ZIP member 名称。该函数接收仓库内相对路径，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `relative_path` | `str` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
如果当前输入内容属于仓库内相对路径 或 当前输入内容属于仓库内相对路径，就拒绝继续处理并抛出 `ArtifactIntegrityError`，向调用方报告输入或运行失败。
对仓库内相对路径中的文本执行规范化或拆分，并把结果记为 拆分后的文本或路径片段集合。
如果仓库内相对路径为空或为假 或 “检查仓库内相对路径是否满足文本匹配条件”后得到肯定结果 或 由拆分后的文本或路径片段集合组成的集合或迭代器中存在满足“拆分后的文本或路径片段属于{'', '.', '..'}”的项，就拒绝继续处理并抛出 `ArtifactIntegrityError`，向调用方报告输入或运行失败。
构造 `PurePosixPath` 结构化领域对象，并把结果记为 规范化后的文本。
如果“调用 `is_absolute` 校验当前输入或状态”后得到肯定结果，就拒绝继续处理并抛出 `ArtifactIntegrityError`，向调用方报告输入或运行失败。
调用 `str` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `_zip_info`

- **源码**：`app/artifact_delivery/service.py:109`
- **签名**：`def _zip_info(name: str) -> zipfile.ZipInfo`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，使用普通文件权限，避免把宿主机权限带入导出包。该函数接收对象名称，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `zipfile.ZipInfo` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `name` | `str` | 对象名称；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`zipfile.ZipInfo`
- **语义**：返回 `zipfile.ZipInfo` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造 `ZipInfo` 结构化领域对象，并把结果记为 补充诊断信息；读取当前处理结果，并保存为 类型；计算组合或计算已有值，并保存为 当前处理结果；返回补充诊断信息的当前值。
```

#### `_same_snapshot`

- **源码**：`app/artifact_delivery/service.py:118`
- **签名**：`def _same_snapshot(view: ArtifactView, descriptor: ArtifactDescriptor) -> bool`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，list_views() 后到 open() 前不能发生身份漂移。该函数接收视图、工具或组件描述信息，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `view` | `ArtifactView` | 名为 `view` 的 `ArtifactView` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `descriptor` | `ArtifactDescriptor` | 工具或组件描述信息；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
检查集合中是否全部满足条件的项，并返回处理结果。
```

#### `ArtifactDeliveryService.__init__`

- **源码**：`app/artifact_delivery/service.py:140`
- **签名**：`def __init__(self: 未显式标注, catalog: ArtifactCatalog, preview_max_bytes: int, stream_chunk_bytes: int, export_allowed_root: Path, export_staging_root: Path, export_max_artifacts: int, export_max_uncompressed_bytes: int, export_max_archive_bytes: int, export_staging_ttl_seconds: int) -> None`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收模型、工具或 Artifact 目录、当前处理结果的字节内容、文本块的字节内容、根目录等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `catalog` | `ArtifactCatalog` | 持久化或目录访问端口；负责读取、CAS 更新或 Artifact 定位。 |
| `preview_max_bytes` | `int` | 名为 `preview_max_bytes` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `stream_chunk_bytes` | `int` | 名为 `stream_chunk_bytes` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `export_allowed_root` | `Path` | 已经解析的文件或目录路径对象；后续操作仍需遵守仓库/工作区边界。 |
| `export_staging_root` | `Path` | 已经解析的文件或目录路径对象；后续操作仍需遵守仓库/工作区边界。 |
| `export_max_artifacts` | `int` | 名为 `export_max_artifacts` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `export_max_uncompressed_bytes` | `int` | 名为 `export_max_uncompressed_bytes` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `export_max_archive_bytes` | `int` | 名为 `export_max_archive_bytes` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `export_staging_ttl_seconds` | `int` | 名为 `export_staging_ttl_seconds` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 模型、工具或 Artifact 目录、当前处理结果的字节内容、文本块的字节内容、根目录、根目录、当前处理结果、当前处理结果的字节内容、当前处理结果的字节内容、当前处理结果 分别保存到同名实例字段。
```

#### `ArtifactDeliveryService.list_views`

- **源码**：`app/artifact_delivery/service.py:165`
- **签名**：`def list_views(self, job: JobRecord) -> list[ArtifactView]`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，只增加能力标记，不暴露 BlobStore 内部字段。该函数接收复现任务记录，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job` | `JobRecord` | 任务、运行、Manifest、记录或证据领域对象；携带关联 ID、状态和内容身份。 |

**输出**

- **Python 类型**：`list[ArtifactView]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
返回当前计算得到的结果。
```

#### `ArtifactDeliveryService.preview`

- **源码**：`app/artifact_delivery/service.py:180`
- **签名**：`def preview(self: 未显式标注, job: JobRecord, artifact_id: str) -> ArtifactPreviewResponse`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，读取最多 max + 1 字节，额外一字节只用于判断截断。该函数接收复现任务记录、Artifact的 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job` | `JobRecord` | 任务、运行、Manifest、记录或证据领域对象；携带关联 ID、状态和内容身份。 |
| `artifact_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`ArtifactPreviewResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `open` 完成该函数的一项辅助处理，并把结果记为 已打开资源；读取工具或组件描述信息，并保存为 工具或组件描述信息。
先尝试完成以下处理：
    如果“调用 `preview_supported` 完成该函数的一项辅助处理”后未得到肯定结果，就拒绝继续处理并抛出 `ArtifactPreviewUnsupported`，向调用方报告输入或运行失败。
    调用 `read` 完成该函数的一项辅助处理，并把结果记为 原始内容。
无论成功还是失败，最后都要：
    关闭请求正文并释放相关资源。
如果对象大小的字节内容不大于当前处理结果的字节内容：
    如果原始内容 的长度不等于对象大小的字节内容 或 辅助操作“计算输入内容的 SHA-256 身份摘要”的结果不等于内容 SHA-256，就拒绝继续处理并抛出 `ArtifactIntegrityError`，向调用方报告输入或运行失败。
否则：
    如果原始内容 的长度不等于当前处理结果的字节内容 + 1，就拒绝继续处理并抛出 `ArtifactIntegrityError`，向调用方报告输入或运行失败。
计算计算当前表达式的结果，并保存为 当前处理结果；读取原始内容中的对应字段，并保存为 后续步骤使用的结果。
如果当前输入内容属于当前处理结果，就拒绝继续处理并抛出 `ArtifactPreviewUnsupported`，向调用方报告输入或运行失败。
调用 `辅助操作` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
先尝试完成以下处理：
    将外部表示解析为结构化内容，并把结果记为 业务内容。
如果出现 `UnicodeDecodeError`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `ArtifactPreviewUnsupported`，向调用方报告输入或运行失败。
调用 `getstate` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；计算组合或计算已有值，并保存为 当前处理结果的字节内容。
如果由业务内容组成的集合或迭代器中存在满足“当前处理结果 对应的 ASCII/Unicode 编码小于32 且 当前处理结果不属于文本（3 个字符）”的项，就拒绝继续处理并抛出 `ArtifactPreviewUnsupported`，向调用方报告输入或运行失败。
构造并返回 `ArtifactPreviewResponse` 结构化领域对象。
```

#### `ArtifactDeliveryService._prepare_staging`

- **源码**：`app/artifact_delivery/service.py:259`
- **签名**：`def _prepare_staging(self) -> Path`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，创建项目内 staging，并顺带清理崩溃遗留的小范围文件。该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个经过边界校验的文件或目录路径。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`Path`
- **语义**：返回解析后的文件或目录路径对象。

**伪代码**

```text
将辅助操作“将根目录规范化为受控的绝对路径”的结果规范化为受控的绝对路径，并把结果记为 根目录。
如果“检查根目录的文件系统属性”后未得到肯定结果，就拒绝继续处理并抛出 `ArtifactIntegrityError`，向调用方报告输入或运行失败。
将根目录规范化为受控的绝对路径，并把结果记为 该调用返回的结果。
如果“调用 `is_absolute` 校验当前输入或状态”后未得到肯定结果，就计算组合或计算已有值，并保存为 当前处理结果。
将当前处理结果规范化为受控的绝对路径，并把结果记为 解析后的值。
如果解析后的值等于根目录 或 根目录不属于当前处理结果，就拒绝继续处理并抛出 `ArtifactIntegrityError`，向调用方报告输入或运行失败。
如果“检查当前处理结果的文件系统属性”后得到肯定结果 且 “检查当前处理结果的文件系统属性”后得到肯定结果，就拒绝继续处理并抛出 `ArtifactIntegrityError`，向调用方报告输入或运行失败。
创建当前处理结果对应的目录；将当前处理结果规范化为受控的绝对路径，并把结果记为 解析后的值。
如果根目录不属于当前处理结果，就拒绝继续处理并抛出 `ArtifactIntegrityError`，向调用方报告输入或运行失败。
计算组合或计算已有值，并保存为 当前处理结果。
遍历辅助操作产生的可迭代结果（枚举解析后的值下符合范围的文件系统项），每次把当前项记为待审核的 MCP 能力候选：
    如果“检查待审核的 MCP 能力候选的文件系统属性”后未得到肯定结果 或 文件扩展名或文本后缀不属于{'.part', '.zip'}，就跳过本轮剩余处理，直接进入下一轮。
    先尝试完成以下处理：
        如果前一步操作返回对象的当前处理结果小于当前处理结果，就调用 `unlink` 完成该函数的一项辅助处理。
    如果出现 `FileNotFoundError`：
        不执行额外操作。
返回解析后的值的当前值。
```

#### `ArtifactDeliveryService._snapshot_entries`

- **源码**：`app/artifact_delivery/service.py:297`
- **签名**：`def _snapshot_entries(self: 未显式标注, job: JobRecord) -> tuple[list[ArtifactView], list[ExportArtifactEntry], int]`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务记录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job` | `JobRecord` | 任务、运行、Manifest、记录或证据领域对象；携带关联 ID、状态和内容身份。 |

**输出**

- **Python 类型**：`tuple[list[ArtifactView], list[ExportArtifactEntry], int]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
从模型、工具或 Artifact 目录读取所需的状态或领域记录，并把结果记为 Artifact 视图集合。
如果Artifact 视图集合 的长度大于当前处理结果，就拒绝继续处理并抛出 `ArtifactExportLimitExceeded`，向调用方报告输入或运行失败。
调用 `sum` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
如果当前处理结果大于当前处理结果的字节内容，就拒绝继续处理并抛出 `ArtifactExportLimitExceeded`，向调用方报告输入或运行失败。
将 记录条目集合 初始化为空列表，用来收集后续结果；将 当前处理结果、当前处理结果、Artifact集合 初始化为空去重集合，用来收集后续结果。
遍历辅助操作产生的可迭代结果（按稳定规则整理结果顺序），每次把当前项记为视图：
    如果本次复现运行 ID不等于本次复现运行 ID，就拒绝继续处理并抛出 `ArtifactIntegrityError`，向调用方报告输入或运行失败。
    如果Artifact的 ID属于Artifact集合，就拒绝继续处理并抛出 `ArtifactIntegrityError`，向调用方报告输入或运行失败。
    把Artifact的 ID追加或合并到Artifact集合；调用 `_archive_path` 完成该函数的一项辅助处理，并把结果记为 当前处理结果的路径；对当前处理结果的路径中的文本执行规范化或拆分，并把结果记为 当前处理结果的路径。
    如果当前处理结果的路径属于当前处理结果 或 当前处理结果的路径属于当前处理结果，就拒绝继续处理并抛出 `ArtifactIntegrityError`，向调用方报告输入或运行失败。
    把当前处理结果的路径追加或合并到当前处理结果；把当前处理结果的路径追加或合并到当前处理结果；把新的处理结果追加或合并到记录条目集合。
返回当前构造的顺序或去重集合。
```

#### `ArtifactDeliveryService._write_artifact`

- **源码**：`app/artifact_delivery/service.py:349`
- **签名**：`def _write_artifact(self: 未显式标注, archive: zipfile.ZipFile, job: JobRecord, view: ArtifactView, entry: ExportArtifactEntry) -> None`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前处理结果、复现任务记录、视图、条目，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `archive` | `zipfile.ZipFile` | 名为 `archive` 的 `zipfile.ZipFile` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `job` | `JobRecord` | 任务、运行、Manifest、记录或证据领域对象；携带关联 ID、状态和内容身份。 |
| `view` | `ArtifactView` | 名为 `view` 的 `ArtifactView` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `entry` | `ExportArtifactEntry` | 名为 `entry` 的 `ExportArtifactEntry` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `open` 完成该函数的一项辅助处理，并把结果记为 已打开资源；读取工具或组件描述信息，并保存为 工具或组件描述信息；计算输入内容的 SHA-256 身份摘要，并把结果记为 内容摘要；计算使用固定配置或常量值，并保存为 当前处理结果。
先尝试完成以下处理：
    如果“调用 `_same_snapshot` 完成该函数的一项辅助处理”后未得到肯定结果，就拒绝继续处理并抛出 `ArtifactIntegrityError`，向调用方报告输入或运行失败。
    进入上下文“调用 `open` 完成该函数的一项辅助处理，并把上下文资源交给待定位的代码对象或业务目标”，退出时自动清理资源：
        只要当前条件（使用固定配置或常量值）成立，就重复以下处理：
            调用 `read` 完成该函数的一项辅助处理，并把结果记为 检索文本块。
            如果检索文本块为空或为假，就立即结束当前循环。
            将新的计算结果累加或合并到当前处理结果。
            如果当前处理结果大于对象大小的字节内容，就拒绝继续处理并抛出 `ArtifactIntegrityError`，向调用方报告输入或运行失败。
            把检索文本块追加或合并到内容摘要；向终端或输出流写出当前结果/诊断信息。
无论成功还是失败，最后都要：
    关闭请求正文并释放相关资源。
如果当前处理结果不等于对象大小的字节内容 或 辅助操作“计算输入内容的 SHA-256 身份摘要”的结果不等于内容 SHA-256，就拒绝继续处理并抛出 `ArtifactIntegrityError`，向调用方报告输入或运行失败。
```

#### `ArtifactDeliveryService.build_export`

- **源码**：`app/artifact_delivery/service.py:388`
- **签名**：`def build_export(self: 未显式标注, job: JobRecord, public_job: dict[str, Any]) -> PreparedJobExport`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，完整构建成功后才返回 PreparedJobExport。该函数接收复现任务记录、任务，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `PreparedJobExport` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job` | `JobRecord` | 任务、运行、Manifest、记录或证据领域对象；携带关联 ID、状态和内容身份。 |
| `public_job` | `dict[str, Any]` | 名为 `public_job` 的键值映射；键和值分别承载的业务字段由读取/写入分支确定。 |

**输出**

- **Python 类型**：`PreparedJobExport`
- **语义**：返回 `PreparedJobExport` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `_snapshot_entries` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；遍历并筛选输入，将整理后的结果保存为 条目集合的 ID；调用 `_prepare_staging` 完成该函数的一项辅助处理，并把结果记为 暂存工作区根目录；读取前一步操作返回对象的当前处理结果，并保存为 模型或命令 token。
计算组合或计算已有值，并保存为 拆分后的文本或路径片段的路径；计算组合或计算已有值，并保存为 当前处理结果的路径；读取当前时间，作为状态变更的统一时间戳，并把结果记为 该调用返回的结果；计算按字段初始化键值映射，并保存为 Manifest的 Hash。
计算输入内容的 SHA-256 身份摘要，并把结果记为 运行或工作区 Manifest的 Hash；构造 `JobExportManifest` 结构化领域对象，并把结果记为 运行或工作区 Manifest。
先尝试完成以下处理：
    进入上下文“构造 `ZipFile` 结构化领域对象，并把上下文资源交给当前处理结果”，退出时自动清理资源：
        调用 `writestr` 完成该函数的一项辅助处理。
        遍历辅助操作产生的可迭代结果（按稳定规则整理结果顺序），每次把当前项记为视图，然后调用 `_write_artifact` 持久化或更新当前领域数据。
        调用 `writestr` 完成该函数的一项辅助处理。
    读取前一步操作返回对象的当前处理结果，并保存为 后续步骤使用的结果。
    如果当前处理结果大于当前处理结果的字节内容，就拒绝继续处理并抛出 `ArtifactExportLimitExceeded`，向调用方报告输入或运行失败。
    计算输入内容的 SHA-256 身份摘要，并把结果记为 该调用返回的结果。
    进入上下文“调用 `open` 完成该函数的一项辅助处理，并把上下文资源交给当前处理结果”，退出时自动清理资源：
        只要当前条件（使用固定配置或常量值）成立，就重复以下处理：
            调用 `read` 完成该函数的一项辅助处理，并把结果记为 检索文本块。
            如果检索文本块为空或为假，就立即结束当前循环。
            把检索文本块追加或合并到当前处理结果。
    调用 `replace` 完成该函数的一项辅助处理；计算计算当前表达式的结果，并保存为 任务；计算计算当前表达式的结果，并保存为 运行；计算根据字段和固定文本生成格式化文本，并保存为 目标文件名。
    构造并返回 `PreparedJobExport` 结构化领域对象。
如果出现 `Exception`：
    调用 `unlink` 完成该函数的一项辅助处理；调用 `unlink` 完成该函数的一项辅助处理；重新抛出当前异常，保持原始失败信息。
```

### `app/chat/context.py`

**模块作用**：有界 Grounding Context Builder。

#### `ResearchPackReaderPort.list_packs_for_job`

- **源码**：`app/chat/context.py:64`
- **签名**：`def list_packs_for_job(self: 未显式标注, job_id: str, limit: int) -> list[ResearchEvidencePack]`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收复现任务 ID、结果数量上限，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。 |

**输出**

- **Python 类型**：`list[ResearchEvidencePack]`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `ComparisonReader.get`

- **源码**：`app/chat/context.py:74`
- **签名**：`def get(self, comparison_id: str) -> ComparisonReport`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收SDK 或 MCP 运行升级比较结果的 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ComparisonReport` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `comparison_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`ComparisonReport`
- **语义**：返回 `ComparisonReport` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `ComparisonReader.list_for_job`

- **源码**：`app/chat/context.py:77`
- **签名**：`def list_for_job(self: 未显式标注, job_id: str, limit: int) -> ComparisonListResponse`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收复现任务 ID、结果数量上限，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。；默认 100 |

**输出**

- **Python 类型**：`ComparisonListResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `_keywords`

- **源码**：`app/chat/context.py:86`
- **签名**：`def _keywords(question: str) -> set[str]`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，轻量中英文关键词，不声称替代语义检索。该函数接收论文复现问题或用户问题，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `question` | `str` | 论文复现问题或用户问题；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`set[str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
返回当前计算得到的结果。
```

#### `_score`

- **源码**：`app/chat/context.py:98`
- **签名**：`def _score(text: str, keywords: set[str], base: int) -> int`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收待处理文本、检索关键词集合、当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终数量、序号、字节数或版本等整数结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `text` | `str` | 用户目标、检索问题、反馈或待处理文本；会作为当前阶段的业务语境输入，并可能受到长度/脱敏约束。 |
| `keywords` | `set[str]` | 用于精确检索或文件分类的关键词集合；匹配范围由当前工具决定。 |
| `base` | `int` | 名为 `base` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`int`
- **语义**：返回整数计数、序号、字节数或退出码；具体含义由函数名决定。

**伪代码**

```text
对待处理文本中的文本执行规范化或拆分，并把结果记为 转为小写的比较文本；返回当前计算得到的结果。
```

#### `_text_chunks`

- **源码**：`app/chat/context.py:105`
- **签名**：`def _text_chunks(text: str, max_chars: int = 3500) -> list[str]`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，按行构造有界 chunk，避免在 JSON/Markdown 中间无限截取。该函数接收待处理文本、最大字符数，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `text` | `str` | 用户目标、检索问题、反馈或待处理文本；会作为当前阶段的业务语境输入，并可能受到长度/脱敏约束。 |
| `max_chars` | `int` | 名为 `max_chars` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。；默认 3500 |

**输出**

- **Python 类型**：`list[str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
将 检索文本块集合、当前值 初始化为空列表，用来收集后续结果；计算使用固定配置或常量值，并保存为 当前字符数。
遍历辅助操作产生的可迭代结果（调用 `replace` 完成该函数的一项辅助处理，再对返回文本执行规范化或拆分），每次把当前项记为源码行号：
    读取源码行号中的对应字段，并保存为 后续步骤使用的结果；计算组合或计算已有值，并保存为 当前处理结果。
    如果当前值有值或为真 且 当前输入内容大于最大字符数，就把新的处理结果追加或合并到检索文本块集合；将 当前值 初始化为空列表，用来收集后续结果；计算使用固定配置或常量值，并保存为 当前字符数。
    把当前处理结果追加或合并到当前值；将新的计算结果累加或合并到当前字符数。
如果当前值有值或为真，就把新的处理结果追加或合并到检索文本块集合。
返回组合判断结果。
```

#### `ChatContextBuilder.__init__`

- **源码**：`app/chat/context.py:126`
- **签名**：`def __init__(self: 未显式标注, interaction: InteractionService, artifact_catalog: ArtifactCatalog, artifacts_to_open: int, source_limit: int, artifact_max_bytes: int, total_context_chars: int, log_max_bytes: int, comparison_reader: ComparisonReader | None, comparison_limit: int, comparison_max_chars: int, project_fact_retriever: 未显式标注, knowledge_retriever: 未显式标注, knowledge_max_entities: int, knowledge_max_relations: int, knowledge_max_chars: int, research_reader: ResearchPackReaderPort | None, research_pack_limit: int, research_max_chars: int) -> None（隐式）`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收用户交互记录、Artifact、当前处理结果、来源上限等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `interaction` | `InteractionService` | 用户交互记录；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `artifact_catalog` | `ArtifactCatalog` | 名为 `artifact_catalog` 的 `ArtifactCatalog` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `artifacts_to_open` | `int` | 名为 `artifacts_to_open` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `source_limit` | `int` | 名为 `source_limit` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `artifact_max_bytes` | `int` | 名为 `artifact_max_bytes` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `total_context_chars` | `int` | 名为 `total_context_chars` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `log_max_bytes` | `int` | 名为 `log_max_bytes` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `comparison_reader` | `ComparisonReader | None` | 只读证据或数据读取端口；负责把外部持久化内容投影为受约束领域输入。；默认 空值 |
| `comparison_limit` | `int` | 名为 `comparison_limit` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。；默认 3 |
| `comparison_max_chars` | `int` | 名为 `comparison_max_chars` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。；默认 12000 |
| `project_fact_retriever` | `未显式标注` | 检索服务或端口；返回有界候选及可解释排序信息，不授予执行权限。；默认 空值 |
| `knowledge_retriever` | `未显式标注` | 检索服务或端口；返回有界候选及可解释排序信息，不授予执行权限。；默认 空值 |
| `knowledge_max_entities` | `int` | 名为 `knowledge_max_entities` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。；默认 12 |
| `knowledge_max_relations` | `int` | 名为 `knowledge_max_relations` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。；默认 24 |
| `knowledge_max_chars` | `int` | 名为 `knowledge_max_chars` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。；默认 16000 |
| `research_reader` | `ResearchPackReaderPort | None` | 只读证据或数据读取端口；负责把外部持久化内容投影为受约束领域输入。；默认 空值 |
| `research_pack_limit` | `int` | 名为 `research_pack_limit` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。；默认 3 |
| `research_max_chars` | `int` | 名为 `research_max_chars` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。；默认 12000 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 用户交互记录、Artifact、当前处理结果、来源上限、Artifact的字节内容、上下文字符数、当前处理结果的字节内容、读取器、上限、字符数、项目事实检索器、检索器、当前处理结果、当前处理结果、字符数、读取器、上限、字符数 分别保存到同名实例字段。
```

#### `ChatContextBuilder._artifact_sources`

- **源码**：`app/chat/context.py:167`
- **签名**：`def _artifact_sources(self: 未显式标注, job_id: str, keywords: set[str]) -> list[GroundingSource]`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收复现任务 ID、检索关键词集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `keywords` | `set[str]` | 用于精确检索或文件分类的关键词集合；匹配范围由当前工具决定。 |

**输出**

- **Python 类型**：`list[GroundingSource]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
从任务读取所需的状态或领域记录，并把结果记为 任务；遍历并筛选输入，将整理后的结果保存为 Artifact 视图集合；按稳定规则整理结果顺序；将 证据来源集合 初始化为空列表，用来收集后续结果。
遍历当前可迭代输入，每次把当前项记为视图：
    调用 `open` 完成该函数的一项辅助处理，并把结果记为 已打开资源。
    先尝试完成以下处理：
        调用 `read` 完成该函数的一项辅助处理，并把结果记为 原始内容。
    无论成功还是失败，最后都要：
        关闭请求正文并释放相关资源。
    计算计算当前表达式的结果，并保存为 当前处理结果；将外部表示解析为结构化内容，并把结果记为 待处理文本。
    遍历带顺序编号的输入集合，每次把当前项记为多个解包结果：
        如果“对检索文本块中的文本执行规范化或拆分”后未得到肯定结果，就跳过本轮剩余处理，直接进入下一轮。
        计算根据字段和固定文本生成格式化文本，并保存为 源码或文档定位信息。
        如果当前处理结果有值或为真，就将新的计算结果累加或合并到源码或文档定位信息。
        计算根据字段和固定文本生成格式化文本，并保存为 论文引用证据的 ID；把新的处理结果追加或合并到证据来源集合。
返回证据来源集合的当前值。
```

#### `ChatContextBuilder._comparison_sources`

- **源码**：`app/chat/context.py:243`
- **签名**：`def _comparison_sources(self: 未显式标注, job_id: str, keywords: set[str]) -> list[GroundingSource]`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收复现任务 ID、检索关键词集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `keywords` | `set[str]` | 用于精确检索或文件分类的关键词集合；匹配范围由当前工具决定。 |

**输出**

- **Python 类型**：`list[GroundingSource]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
如果读取器为空，就返回当前构造的顺序或去重集合。
调用 `list_for_job` 读取或查询当前阶段需要的数据，并把结果记为 论文页码；将 证据来源集合 初始化为空列表，用来收集后续结果；计算使用固定配置或常量值，并保存为 字符数。
遍历当前可迭代输入，每次把当前项记为当前处理项：
    从读取器读取所需的状态或领域记录，并把结果记为 MCP 评测或运行报告；调用 `comparison_chat_projection` 完成该函数的一项辅助处理，并把结果记为 业务内容。
    如果当前输入内容大于字符数，就跳过本轮剩余处理，直接进入下一轮。
    将新的计算结果累加或合并到字符数；计算根据字段和固定文本生成格式化文本，并保存为 当前处理结果；把新的处理结果追加或合并到证据来源集合。
返回证据来源集合的当前值。
```

#### `ChatContextBuilder._project_fact_sources`

- **源码**：`app/chat/context.py:292`
- **签名**：`def _project_fact_sources(self: 未显式标注, job_id: str, keywords: set[str]) -> list[GroundingSource]`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收复现任务 ID、检索关键词集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `keywords` | `set[str]` | 用于精确检索或文件分类的关键词集合；匹配范围由当前工具决定。 |

**输出**

- **Python 类型**：`list[GroundingSource]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
如果项目事实检索器为空，就返回当前构造的顺序或去重集合。
调用 `for_job` 完成该函数的一项辅助处理，并把结果记为 检索或映射证据包。
如果检索或映射证据包为空，就返回当前构造的顺序或去重集合。
将 证据来源集合 初始化为空列表，用来收集后续结果。
遍历当前可迭代输入，每次把当前项记为当前处理项，然后将结构化内容序列化或编码为可传输表示，并把结果记为 业务内容；把新的处理结果追加或合并到证据来源集合。
返回证据来源集合的当前值。
```

#### `ChatContextBuilder._knowledge_sources`

- **源码**：`app/chat/context.py:335`
- **签名**：`def _knowledge_sources(self: 未显式标注, question: str, keywords: set[str]) -> list[GroundingSource]`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收论文复现问题或用户问题、检索关键词集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `question` | `str` | 论文复现问题或用户问题；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `keywords` | `set[str]` | 用于精确检索或文件分类的关键词集合；匹配范围由当前工具决定。 |

**输出**

- **Python 类型**：`list[GroundingSource]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
如果检索器为空，就返回当前构造的顺序或去重集合。
调用 `query` 完成该函数的一项辅助处理，并把结果记为 检索或映射证据包；遍历并筛选输入，将整理后的结果保存为 证据；将 证据来源集合 初始化为空列表，用来收集后续结果；计算使用固定配置或常量值，并保存为 字符数。
遍历当前可迭代输入，每次把当前项记为当前处理结果：
    读取知识库实体记录，并保存为 知识库实体记录；遍历并筛选输入，将整理后的结果保存为 当前处理结果；按稳定规则整理结果顺序，并把结果记为 该调用返回的结果。
    如果当前处理结果为空或为假，就跳过本轮剩余处理，直接进入下一轮。
    遍历并筛选输入，将整理后的结果保存为 当前处理结果；将结构化内容序列化或编码为可传输表示，并把结果记为 业务内容。
    如果当前输入内容大于字符数，就立即结束当前循环。
    将新的计算结果累加或合并到字符数；把新的处理结果追加或合并到证据来源集合。
返回证据来源集合的当前值。
```

#### `ChatContextBuilder._research_sources`

- **源码**：`app/chat/context.py:420`
- **签名**：`def _research_sources(self: 未显式标注, job_id: str, keywords: set[str]) -> list[GroundingSource]`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收复现任务 ID、检索关键词集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `keywords` | `set[str]` | 用于精确检索或文件分类的关键词集合；匹配范围由当前工具决定。 |

**输出**

- **Python 类型**：`list[GroundingSource]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
如果读取器为空，就返回当前构造的顺序或去重集合。
将 证据来源集合 初始化为空列表，用来收集后续结果；计算使用固定配置或常量值，并保存为 字符数；调用 `list_packs_for_job` 读取或查询当前阶段需要的数据，并把结果记为 该调用返回的结果。
遍历由当前处理结果组成的集合或迭代器，每次把当前项记为检索或映射证据包：
    遍历并筛选输入，将整理后的结果保存为 当前处理结果。
    遍历当前可迭代输入，每次把当前项记为论文引用证据：
        从当前处理结果读取所需的状态或领域记录，并把结果记为 MCP 能力快照。
        如果MCP 能力快照为空，就跳过本轮剩余处理，直接进入下一轮。
        如果当前处理结果的 SHA-256不等于请求正文的 SHA-256，就跳过本轮剩余处理，直接进入下一轮。
        如果当前输入内容大于字符数，就跳过本轮剩余处理，直接进入下一轮。
        把新的处理结果追加或合并到证据来源集合；将新的计算结果累加或合并到字符数。
返回证据来源集合的当前值。
```

#### `ChatContextBuilder._job_source`

- **源码**：`app/chat/context.py:477`
- **签名**：`def _job_source(self: 未显式标注, job: JobView, keywords: set[str]) -> GroundingSource`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收复现任务记录、检索关键词集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `GroundingSource` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job` | `JobView` | 任务、运行、Manifest、记录或证据领域对象；携带关联 ID、状态和内容身份。 |
| `keywords` | `set[str]` | 用于精确检索或文件分类的关键词集合；匹配范围由当前工具决定。 |

**输出**

- **Python 类型**：`GroundingSource`
- **语义**：返回 `GroundingSource` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
将结构化内容序列化或编码为可传输表示，并把结果记为 任务内容；构造并返回 `GroundingSource` 结构化领域对象。
```

#### `ChatContextBuilder.build_job_only`

- **源码**：`app/chat/context.py:511`
- **签名**：`def build_job_only(self: 未显式标注, job_id: str, question: str) -> GroundingBundle`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收复现任务 ID、论文复现问题或用户问题，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `GroundingBundle` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `question` | `str` | 论文复现问题或用户问题；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`GroundingBundle`
- **语义**：返回 `GroundingBundle` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `get_job` 读取或查询当前阶段需要的数据，并把结果记为 复现任务记录；调用 `_job_source` 完成该函数的一项辅助处理，并把结果记为 数据来源标记；构造并返回 `GroundingBundle` 结构化领域对象。
```

#### `ChatContextBuilder.build`

- **源码**：`app/chat/context.py:524`
- **签名**：`def build(self: 未显式标注, job_id: str, question: str) -> GroundingBundle`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收复现任务 ID、论文复现问题或用户问题，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `GroundingBundle` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `question` | `str` | 论文复现问题或用户问题；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`GroundingBundle`
- **语义**：返回 `GroundingBundle` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `get_job` 读取或查询当前阶段需要的数据，并把结果记为 复现任务记录；调用 `_keywords` 完成该函数的一项辅助处理，并把结果记为 检索关键词集合；计算初始化顺序集合，并保存为 候选结果集合；将 审计事件集合 初始化为空列表，用来收集后续结果。
计算使用固定配置或常量值，并保存为 增量读取游标。
遍历限定范围内的序列，每次把当前项记为当前处理结果：
    调用 `events_after` 完成该函数的一项辅助处理，并把结果记为 论文页码；把论文页码追加或合并到审计事件集合。
    如果论文页码 的长度小于100，就立即结束当前循环。
    读取事件的 ID，并保存为 增量读取游标。
读取审计事件集合中的对应字段，并保存为 审计事件集合。
遍历由审计事件集合组成的集合或迭代器，每次把当前项记为事件，然后将结构化内容序列化或编码为可传输表示，并把结果记为 事件内容；把新的处理结果追加或合并到候选结果集合。
调用 `tail_log` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
如果“对业务内容中的文本执行规范化或拆分”后得到肯定结果，就计算根据条件从两个候选结果中选择一个，并保存为 当前处理结果；把新的处理结果追加或合并到候选结果集合。
把新的处理结果追加或合并到候选结果集合；把新的处理结果追加或合并到候选结果集合；把新的处理结果追加或合并到候选结果集合；把新的处理结果追加或合并到候选结果集合。
把新的处理结果追加或合并到候选结果集合；读取候选结果集合中的对应字段，并保存为 任务来源；按稳定规则整理结果顺序，并把结果记为 该调用返回的结果；计算初始化顺序集合，并保存为 选中的候选项。
计算数量、边界或类型判断结果，并把结果记为 字符数。
遍历由当前处理结果组成的集合或迭代器，每次把当前项记为数据来源标记：
    如果选中的候选项 的长度不小于来源上限，就立即结束当前循环。
    如果当前输入内容大于上下文字符数，就跳过本轮剩余处理，直接进入下一轮。
    把数据来源标记追加或合并到选中的候选项；将新的计算结果累加或合并到字符数。
构造并返回 `GroundingBundle` 结构化领域对象。
```

### `app/chat/memory.py`

**模块作用**：ConversationMemoryCompactor：增量压缩旧对话成可审计 Memory。

#### `_canonical`

- **源码**：`app/chat/memory.py:39`
- **签名**：`def _canonical(value: object) -> str`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `object` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
将结构化内容序列化或编码为可传输表示，并返回处理结果。
```

#### `_sha256`

- **源码**：`app/chat/memory.py:49`
- **签名**：`def _sha256(value: object) -> str`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `object` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回输入内容的 SHA-256 身份摘要，用于完整性校验，不是加密后的正文。

**伪代码**

```text
计算输入内容的 SHA-256 身份摘要，并返回处理结果。
```

#### `_messages_sha256`

- **源码**：`app/chat/memory.py:53`
- **签名**：`def _messages_sha256(messages: list[ChatMessage]) -> str`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收对话或日志消息集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `messages` | `list[ChatMessage]` | 对话或日志消息集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回输入内容的 SHA-256 身份摘要，用于完整性校验，不是加密后的正文。

**伪代码**

```text
调用 `_sha256` 计算内容身份、分数或派生结果，并返回处理结果。
```

#### `_memory_sha256_payload`

- **源码**：`app/chat/memory.py:59`
- **签名**：`def _memory_sha256_payload(memory_id: str, job_id: str, version: int, covered_from_sequence: int, covered_through_sequence: int, delta_messages_sha256: str, parent_memory_id: str | None, parent_memory_sha256: str | None, body: ConversationMemoryBody, prompt_version: str, model_name: str, structured_method: str, strict: bool, created_at: str) -> dict`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收记忆的 ID、复现任务 ID、记录版本号、当前处理结果等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `memory_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `version` | `int` | 记录版本号；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `covered_from_sequence` | `int` | 名为 `covered_from_sequence` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `covered_through_sequence` | `int` | 名为 `covered_through_sequence` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `delta_messages_sha256` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |
| `parent_memory_id` | `str | None` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `parent_memory_sha256` | `str | None` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |
| `body` | `ConversationMemoryBody` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `prompt_version` | `str` | 名为 `prompt_version` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `model_name` | `str` | 名为 `model_name` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `structured_method` | `str` | 名为 `structured_method` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `strict` | `bool` | 布尔条件或能力开关，用于控制流程分支。 |
| `created_at` | `str` | 时间值或可注入时钟，用于排序、过期、租约或可重复测试。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回输入内容的 SHA-256 身份摘要，用于完整性校验，不是加密后的正文。

**伪代码**

```text
返回包含 `memory_id`、`job_id`、`version`、`covered_from_sequence`、`covered_through_sequence`、`delta_messages_sha256`、`parent_memory_id`、`parent_memory_sha256` 等字段的结构化映射。
```

#### `_memory_body_hash_payload`

- **源码**：`app/chat/memory.py:115`
- **签名**：`def _memory_body_hash_payload(body: ConversationMemoryBody) -> dict`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，按 body 创建时的 Citation schema 生成稳定 hash 投影。该函数接收请求正文，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `body` | `ConversationMemoryBody` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回内容身份摘要，通常为 SHA-256 十六进制字符串。

**伪代码**

```text
复制、序列化或校验结构化领域对象，并把结果记为 结构化请求载荷；读取版本，并保存为 记录版本号。
如果记录版本号等于'phase36-v1'：
    从结构化请求载荷取出并移除最后一项；计算组合或计算已有值，并保存为 当前处理结果。
    遍历辅助操作产生的可迭代结果（从结构化请求载荷读取所需的状态或领域记录），每次把当前项记为论文引用证据：
        遍历由当前处理结果组成的集合或迭代器，每次把当前项记为结构化对象字段的名称，然后从论文引用证据取出并移除最后一项。
否则：
    如果记录版本号等于'phase38-v2'：
        计算组合或计算已有值，并保存为 当前处理结果。
        遍历辅助操作产生的可迭代结果（从结构化请求载荷读取所需的状态或领域记录），每次把当前项记为论文引用证据：
            遍历由当前处理结果组成的集合或迭代器，每次把当前项记为结构化对象字段的名称，然后从论文引用证据取出并移除最后一项。
    否则：
        如果记录版本号等于'phase46-v3'：
            读取当前处理结果，并保存为 后续步骤使用的结果。
            遍历辅助操作产生的可迭代结果（从结构化请求载荷读取所需的状态或领域记录），每次把当前项记为论文引用证据：
                遍历由当前处理结果组成的集合或迭代器，每次把当前项记为结构化对象字段的名称，然后从论文引用证据取出并移除最后一项。
返回结构化请求载荷的当前值。
```

#### `validate_memory_hash`

- **源码**：`app/chat/memory.py:146`
- **签名**：`def validate_memory_hash(memory: ConversationMemory) -> None`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收记忆，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `memory` | `ConversationMemory` | 名为 `memory` 的 `ConversationMemory` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_memory_sha256_payload` 计算内容身份、分数或派生结果，并把结果记为 结构化请求载荷。
如果辅助操作“调用 `_sha256` 计算内容身份、分数或派生结果”的结果不等于记忆的 SHA-256，就拒绝继续处理并抛出 `ChatMemoryConflict`，向调用方报告输入或运行失败。
```

#### `_complete_exchange_prefix`

- **源码**：`app/chat/memory.py:175`
- **签名**：`def _complete_exchange_prefix(messages: list[ChatMessage]) -> list[ChatMessage]`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，只接受连续、原子写入的 user/assistant pairs。该函数接收对话或日志消息集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `messages` | `list[ChatMessage]` | 对话或日志消息集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`list[ChatMessage]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
将 当前处理结果 初始化为空列表，用来收集后续结果；计算使用固定配置或常量值，并保存为 当前候选项的索引。
只要当前输入内容小于对话或日志消息集合 的长度，就重复以下处理：
    读取对话或日志消息集合中的对应字段，并保存为 后续步骤使用的结果；读取对话或日志消息集合中的对应字段，并保存为 后续步骤使用的结果。
    如果调用方职责角色不等于'user' 或 调用方职责角色不等于'assistant' 或 当前处理结果不等于面向用户或日志的提示信息的 ID 或 当前处理结果不等于当前处理结果 + 1，就拒绝继续处理并抛出 `ChatMemoryConflict`，向调用方报告输入或运行失败。
    把新的处理结果追加或合并到当前处理结果；将新的计算结果累加或合并到当前候选项的索引。
返回前一步处理得到的结果。
```

#### `_bounded_delta`

- **源码**：`app/chat/memory.py:199`
- **签名**：`def _bounded_delta(messages: list[ChatMessage], max_messages: int, max_chars: int) -> list[ChatMessage]`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收对话或日志消息集合、最大对话或日志消息集合、最大字符数，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `messages` | `list[ChatMessage]` | 对话或日志消息集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `max_messages` | `int` | 名为 `max_messages` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `max_chars` | `int` | 名为 `max_chars` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`list[ChatMessage]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
将 选中的候选项 初始化为空列表，用来收集后续结果。
遍历限定范围内的序列，每次把当前项记为当前候选项的索引：
    读取对话或日志消息集合中的对应字段，并保存为 后续步骤使用的结果。
    如果当前处理结果 的长度小于2，就立即结束当前循环。
    计算初始化顺序集合，并保存为 待审核的 MCP 能力候选；调用 `_canonical` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
    如果当前处理结果 的长度大于最大字符数，就立即结束当前循环。
    读取待审核的 MCP 能力候选，并保存为 选中的候选项。
返回选中的候选项的当前值。
```

#### `ConversationMemoryCompactor.__init__`

- **源码**：`app/chat/memory.py:222`
- **签名**：`def __init__(self: 未显式标注, repository: ChatRepository, invoker: MemoryDraftInvoker, enabled: bool, recent_messages: int, min_messages: int, max_messages: int, max_input_chars: int, memory_max_chars: int, prompt_version: str, model_name: str, structured_method: str, strict: bool) -> None（隐式）`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收持久化仓库、工具或模型调用器、功能是否启用的开关、当前处理结果等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `repository` | `ChatRepository` | 持久化或目录访问端口；负责读取、CAS 更新或 Artifact 定位。 |
| `invoker` | `MemoryDraftInvoker` | 可调用依赖；由当前函数在受控位置调用。 |
| `enabled` | `bool` | 布尔条件或能力开关，用于控制流程分支。 |
| `recent_messages` | `int` | 名为 `recent_messages` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `min_messages` | `int` | 名为 `min_messages` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `max_messages` | `int` | 名为 `max_messages` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `max_input_chars` | `int` | 名为 `max_input_chars` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `memory_max_chars` | `int` | 名为 `memory_max_chars` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `prompt_version` | `str` | 名为 `prompt_version` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `model_name` | `str` | 名为 `model_name` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `structured_method` | `str` | 名为 `structured_method` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `strict` | `bool` | 布尔条件或能力开关，用于控制流程分支。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 持久化仓库、工具或模型调用器、功能是否启用的开关、当前处理结果、最小对话或日志消息集合、最大对话或日志消息集合、最大字符数、记忆字符数、版本、模型标识或模型配置的名称、当前处理结果、是否启用严格校验的开关 分别保存到同名实例字段。
```

#### `ConversationMemoryCompactor._delta`

- **源码**：`app/chat/memory.py:251`
- **签名**：`def _delta(self: 未显式标注, job_id: str, previous: ConversationMemory | None) -> list[ChatMessage]`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收复现任务 ID、前一项，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `previous` | `ConversationMemory | None` | 前一项；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`list[ChatMessage]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
调用 `latest_sequence` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；计算根据条件从两个候选结果中选择一个，并保存为 前一项；计算组合或计算已有值，并保存为 当前处理结果。
如果当前处理结果不大于前一项，就返回当前构造的顺序或去重集合。
计算组合或计算已有值，并保存为 读取起点；调用 `list_messages_range` 读取或查询当前阶段需要的数据，并把结果记为 数据库记录行集合。
如果数据库记录行集合为空或为假，就返回当前构造的顺序或去重集合。
读取读取起点，并保存为 期望值。
遍历由数据库记录行集合组成的集合或迭代器，每次把当前项记为当前处理项：
    如果当前处理结果不等于期望值，就拒绝继续处理并抛出 `ChatMemoryConflict`，向调用方报告输入或运行失败。
    将新的计算结果累加或合并到期望值。
调用 `_complete_exchange_prefix` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `_bounded_delta` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `ConversationMemoryCompactor._citation_map`

- **源码**：`app/chat/memory.py:291`
- **签名**：`def _citation_map(previous: ConversationMemory | None, delta: list[ChatMessage]) -> dict[str, ChatCitation]`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收前一项、当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `previous` | `ConversationMemory | None` | 前一项；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `delta` | `list[ChatMessage]` | `list[ChatMessage]` 元素集合；元素代表的业务对象由参数名 `delta` 和调用位置确定。 |

**输出**

- **Python 类型**：`dict[str, ChatCitation]`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
遍历并筛选输入，将整理后的结果保存为 论文引用证据集合。
遍历由当前处理结果组成的集合或迭代器，每次把当前项记为面向用户或日志的提示信息：
    遍历当前可迭代输入，每次把当前项记为论文引用证据：
        从论文引用证据集合读取所需的状态或领域记录，并把结果记为 已有记录。
        如果已有记录不为空 且 已有记录不等于论文引用证据，就拒绝继续处理并抛出 `ChatMemoryConflict`，向调用方报告输入或运行失败。
        读取论文引用证据，并保存为 论文引用证据集合中的对应字段。
返回论文引用证据集合的当前值。
```

#### `ConversationMemoryCompactor._validate_statement_sources`

- **源码**：`app/chat/memory.py:315`
- **签名**：`def _validate_statement_sources(draft: MemoryDraft, previous: ConversationMemory | None, delta: list[ChatMessage]) -> None`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收草稿对象、前一项、当前处理结果，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `draft` | `MemoryDraft` | 草稿对象；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `previous` | `ConversationMemory | None` | 前一项；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `delta` | `list[ChatMessage]` | `list[ChatMessage]` 元素集合；元素代表的业务对象由参数名 `delta` 和调用位置确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
遍历并筛选输入，将整理后的结果保存为 当前处理结果；将 前一项来源集合集合、前一项来源集合集合 初始化为空去重集合，用来收集后续结果。
如果前一项不为空：
    遍历当前可迭代输入，每次把当前项记为当前处理项，然后把来源集合追加或合并到前一项来源集合集合。
    遍历当前可迭代输入，每次把当前项记为当前处理项，然后把来源集合追加或合并到前一项来源集合集合。
定义内部辅助函数 `validate`，供当前函数在后续步骤中调用。
调用 `validate` 完成该函数的一项辅助处理；调用 `validate` 完成该函数的一项辅助处理；调用 `validate` 完成该函数的一项辅助处理。
```

#### `ConversationMemoryCompactor._validate_statement_sources.validate`

- **源码**：`app/chat/memory.py:337`
- **签名**：`def validate(statements: list[MemoryStatement], user_only: bool) -> None`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收源码语句集合、当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `statements` | `list[MemoryStatement]` | 源码语句集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `user_only` | `bool` | 布尔条件或能力开关，用于控制流程分支。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
遍历由源码语句集合组成的集合或迭代器，每次把当前项记为当前源码语句：
    遍历当前可迭代输入，每次把当前项记为当前处理结果：
        如果当前处理结果属于当前处理结果：
            如果当前处理结果有值或为真 且 当前处理结果中的对应字段不等于'user'，就拒绝继续处理并抛出 `ChatMemoryConflict`，向调用方报告输入或运行失败。
            跳过本轮剩余处理，直接进入下一轮。
        计算根据条件从两个候选结果中选择一个，并保存为 前一项集合。
        如果当前处理结果不属于前一项集合，就拒绝继续处理并抛出 `ChatMemoryConflict`，向调用方报告输入或运行失败。
```

#### `ConversationMemoryCompactor._project_body`

- **源码**：`app/chat/memory.py:364`
- **签名**：`def _project_body(self: 未显式标注, draft: MemoryDraft, previous: ConversationMemory | None, delta: list[ChatMessage]) -> ConversationMemoryBody`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收草稿对象、前一项、当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ConversationMemoryBody` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `draft` | `MemoryDraft` | 草稿对象；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `previous` | `ConversationMemory | None` | 前一项；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `delta` | `list[ChatMessage]` | `list[ChatMessage]` 元素集合；元素代表的业务对象由参数名 `delta` 和调用位置确定。 |

**输出**

- **Python 类型**：`ConversationMemoryBody`
- **语义**：返回 `ConversationMemoryBody` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `_validate_statement_sources` 校验当前输入或状态；调用 `_citation_map` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；遍历并筛选输入，将整理后的结果保存为 当前处理结果。
如果当前处理结果有值或为真，就拒绝继续处理并抛出 `ChatMemoryConflict`，向调用方报告输入或运行失败。
构造 `ConversationMemoryBody` 结构化领域对象，并把结果记为 请求正文。
如果辅助操作“调用 `_canonical` 完成该函数的一项辅助处理”的结果 的长度大于记忆字符数，就拒绝继续处理并抛出 `ChatMemoryConflict`，向调用方报告输入或运行失败。
返回请求正文的当前值。
```

#### `ConversationMemoryCompactor.ensure_memory`

- **源码**：`app/chat/memory.py:428`
- **签名**：`def ensure_memory(self, job_id: str) -> MemoryCompactionOutcome`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收复现任务 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `MemoryCompactionOutcome` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`MemoryCompactionOutcome`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
先尝试完成以下处理：
    调用 `get_latest_memory` 读取或查询当前阶段需要的数据，并把结果记为 前一项。
    如果前一项不为空，就调用 `validate_memory_hash` 校验当前输入或状态。
如果出现 `Exception`并把异常保存为捕获的异常对象：
    构造并返回 `MemoryCompactionOutcome` 结构化领域对象。
如果“功能是否启用的开关有值或为真”不成立，就构造并返回 `MemoryCompactionOutcome` 结构化领域对象。
先尝试完成以下处理：
    调用 `_delta` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
    如果当前处理结果 的长度小于最小对话或日志消息集合，就构造并返回 `MemoryCompactionOutcome` 结构化领域对象。
    调用 `build_memory_prompt` 组装当前阶段需要的领域对象，并把结果记为 发给模型的结构化提示。
    如果发给模型的结构化提示 的长度大于最大字符数 + 记忆字符数 + 8000，就拒绝继续处理并抛出 `ChatMemoryConflict`，向调用方报告输入或运行失败。
    调用 `invoker` 完成该函数的一项辅助处理，并把结果记为 工具调用记录；读取草稿对象，并保存为 草稿对象；读取模型标识或模型配置的名称，并保存为 后续步骤使用的结果；调用 `_project_body` 完成该函数的一项辅助处理，并把结果记为 请求正文。
    调用 `isoformat` 完成该函数的一项辅助处理，并把结果记为 创建时间；计算根据字段和固定文本生成格式化文本，并保存为 记忆的 ID；计算根据条件从两个候选结果中选择一个，并保存为 记录版本号；计算根据条件从两个候选结果中选择一个，并保存为 当前处理结果。
    读取当前处理结果，并保存为 后续步骤使用的结果；调用 `_messages_sha256` 计算内容身份、分数或派生结果，并把结果记为 当前处理结果的 Hash；计算根据条件从两个候选结果中选择一个，并保存为 父级目录或父领域对象的 ID；计算根据条件从两个候选结果中选择一个，并保存为 父级目录或父领域对象的 Hash。
    调用 `_memory_sha256_payload` 计算内容身份、分数或派生结果，并把结果记为 结构化请求载荷；构造 `ConversationMemory` 结构化领域对象，并把结果记为 记忆；调用 `save_memory` 持久化或更新当前领域数据，并把结果记为 多个解包结果；调用 `validate_memory_hash` 校验当前输入或状态。
    构造并返回 `MemoryCompactionOutcome` 结构化领域对象。
如果出现 `ChatMemoryError`并把异常保存为捕获的异常对象：
    构造并返回 `MemoryCompactionOutcome` 结构化领域对象。
如果出现 `Exception`并把异常保存为捕获的异常对象：
    构造并返回 `MemoryCompactionOutcome` 结构化领域对象。
```

#### `build_memory_draft_invoker`

- **源码**：`app/chat/memory.py:536`
- **签名**：`def build_memory_draft_invoker() -> MemoryDraftInvoker`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，Memory Provider adapter；预算失败时由 Compactor 安全降级。该函数接收当前运行配置、模块状态和已注入依赖，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `MemoryDraftInvoker` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`MemoryDraftInvoker`
- **语义**：返回 `MemoryDraftInvoker` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
定义内部辅助函数 `invoke`，供当前函数在后续步骤中调用。
返回前一步处理得到的结果。
```

#### `build_memory_draft_invoker.invoke`

- **源码**：`app/chat/memory.py:539`
- **签名**：`def invoke(prompt: str, job_id: str) -> MemoryDraftResult`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收发给模型的结构化提示、复现任务 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `prompt` | `str` | 用户目标、检索问题、反馈或待处理文本；会作为当前阶段的业务语境输入，并可能受到长度/脱敏约束。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`MemoryDraftResult`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
加载这一步需要的外部依赖；调用 `invoke_structured` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果。
如果当前字段值为空，就拒绝继续处理并抛出 `ChatMemoryUnavailable`，向调用方报告输入或运行失败。
构造并返回 `MemoryDraftResult` 结构化领域对象。
```

### `app/chat/memory_prompt.py`

**模块作用**：Memory Prompt 构造：增量压缩旧对话成结构化 Memory。

#### `build_memory_prompt`

- **源码**：`app/chat/memory_prompt.py:32`
- **签名**：`def build_memory_prompt(previous: ConversationMemory | None, delta: list[ChatMessage]) -> str`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收前一项、当前处理结果，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `previous` | `ConversationMemory | None` | 前一项；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `delta` | `list[ChatMessage]` | `list[ChatMessage]` 元素集合；元素代表的业务对象由参数名 `delta` 和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
计算根据条件从两个候选结果中选择一个，并保存为 前一项；遍历并筛选输入，将整理后的结果保存为 当前处理结果；遍历并筛选输入，将整理后的结果保存为 前一项集合；按稳定规则整理结果顺序，并把结果记为 该调用返回的结果。
按稳定规则整理结果顺序，并把结果记为 该调用返回的结果；调用 `join` 完成该函数的一项辅助处理，并返回处理结果。
```

### `app/chat/prompt.py`

**模块作用**：Chat Prompt 构造：JSON 编码动态值，统一总预算。

#### `_history_item`

- **源码**：`app/chat/prompt.py:79`
- **签名**：`def _history_item(item: ChatMessage) -> dict`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收当前处理项，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `item` | `ChatMessage` | 当前处理项；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
返回包含 `sequence`、`role`、`content` 字段的结构化映射。
```

#### `_source_item`

- **源码**：`app/chat/prompt.py:87`
- **签名**：`def _source_item(item: GroundingSource) -> dict`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收当前处理项，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `item` | `GroundingSource` | 当前处理项；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
返回包含 `citation_id`、`source_type`、`label`、`locator`、`content` 字段的结构化映射。
```

#### `_history_exchanges`

- **源码**：`app/chat/prompt.py:97`
- **签名**：`def _history_exchanges(history: list[ChatMessage]) -> list[list[ChatMessage]]`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，验证并返回完整的 user/assistant exchange。该函数接收历史对话或运行记录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `history` | `list[ChatMessage]` | 历史对话或运行记录；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`list[list[ChatMessage]]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
如果当前输入内容不等于0，就拒绝继续处理并抛出 `ChatConflictError`，向调用方报告输入或运行失败。
将 当前处理结果 初始化为空列表，用来收集后续结果。
遍历限定范围内的序列，每次把当前项记为当前候选项的索引：
    读取历史对话或运行记录中的对应字段，并保存为 后续步骤使用的结果；读取历史对话或运行记录中的对应字段，并保存为 后续步骤使用的结果。
    如果调用方职责角色不等于'user' 或 调用方职责角色不等于'assistant' 或 当前处理结果不等于面向用户或日志的提示信息的 ID 或 当前处理结果不等于当前处理结果 + 1，就拒绝继续处理并抛出 `ChatConflictError`，向调用方报告输入或运行失败。
    把新的处理结果追加或合并到当前处理结果。
返回前一步处理得到的结果。
```

#### `_render_chat_prompt`

- **源码**：`app/chat/prompt.py:121`
- **签名**：`def _render_chat_prompt(question: str, operations: list[dict], memory_payload: dict | None, history: list[ChatMessage], sources: list[GroundingSource]) -> str`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收论文复现问题或用户问题、MCP 业务操作集合、记忆、历史对话或运行记录等输入，用于把复现过程中的结构化状态、证据或结果转换为可读、可传输或可持久化的表示，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `question` | `str` | 论文复现问题或用户问题；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `operations` | `list[dict]` | MCP 业务操作集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `memory_payload` | `dict | None` | 名为 `memory_payload` 的 `dict | None` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `history` | `list[ChatMessage]` | 历史对话或运行记录；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `sources` | `list[GroundingSource]` | 证据来源集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `join` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `build_budgeted_chat_prompt`

- **源码**：`app/chat/prompt.py:167`
- **签名**：`def build_budgeted_chat_prompt(question: str, history: list[ChatMessage], memory: ConversationMemory | None, bundle: GroundingBundle, prompt_max_chars: int, history_max_chars: int, memory_max_chars: int) -> ChatPromptBuild`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收论文复现问题或用户问题、历史对话或运行记录、记忆、代码仓库归档包等输入，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `ChatPromptBuild` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `question` | `str` | 论文复现问题或用户问题；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `history` | `list[ChatMessage]` | 历史对话或运行记录；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `memory` | `ConversationMemory | None` | 名为 `memory` 的 `ConversationMemory | None` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `bundle` | `GroundingBundle` | 代码仓库归档包；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `prompt_max_chars` | `int` | 名为 `prompt_max_chars` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `history_max_chars` | `int` | 名为 `history_max_chars` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `memory_max_chars` | `int` | 名为 `memory_max_chars` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`ChatPromptBuild`
- **语义**：返回 `ChatPromptBuild` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
遍历并筛选输入，将整理后的结果保存为 MCP 业务操作集合；计算根据条件从两个候选结果中选择一个，并保存为 记忆。
如果记忆不为空 且 辅助操作“将结构化内容序列化或编码为可传输表示”的结果 的长度大于记忆字符数，就计算使用固定配置或常量值，并保存为 记忆；计算使用固定配置或常量值，并保存为 记忆。
将 当前处理结果 初始化为空列表，用来收集后续结果；计算使用固定配置或常量值，并保存为 字符数。
遍历辅助操作产生的可迭代结果（调用 `reversed` 完成该函数的一项辅助处理），每次把当前项记为当前处理结果：
    计算数量、边界或类型判断结果，并把结果记为 字符数。
    如果当前输入内容大于字符数，就立即结束当前循环。
    调用 `insert` 完成该函数的一项辅助处理；将新的计算结果累加或合并到字符数。
定义内部辅助函数 `flatten_history`，供当前函数在后续步骤中调用。
如果“证据来源集合有值或为真”不成立 或 论文引用证据的 ID不等于'job:current'，就拒绝继续处理并抛出 `ChatPromptBudgetExceeded`，向调用方报告输入或运行失败。
计算初始化顺序集合，并保存为 来源集合集合。
只要当前条件（使用固定配置或常量值）成立，就重复以下处理：
    调用 `_render_chat_prompt` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
    如果当前处理结果 的长度不大于字符数，就立即结束当前循环。
    如果记忆不为空，就计算使用固定配置或常量值，并保存为 记忆；计算使用固定配置或常量值，并保存为 记忆；跳过本轮剩余处理，直接进入下一轮。
    如果当前处理结果有值或为真，就从当前处理结果取出并移除最后一项；跳过本轮剩余处理，直接进入下一轮。
    拒绝继续处理并抛出 `ChatPromptBudgetExceeded`，向调用方报告输入或运行失败。
遍历当前可迭代输入，每次把当前项记为数据来源标记：
    计算初始化顺序集合，并保存为 待审核的 MCP 能力候选；调用 `_render_chat_prompt` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
    如果当前处理结果 的长度不大于字符数，就读取待审核的 MCP 能力候选，并保存为 来源集合集合。
调用 `flatten_history` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `_render_chat_prompt` 完成该函数的一项辅助处理，并把结果记为 发给模型的结构化提示。
如果发给模型的结构化提示 的长度大于字符数，就拒绝继续处理并抛出 `ChatPromptBudgetExceeded`，向调用方报告输入或运行失败。
构造并返回 `ChatPromptBuild` 结构化领域对象。
```

#### `build_budgeted_chat_prompt.flatten_history`

- **源码**：`app/chat/prompt.py:219`
- **签名**：`def flatten_history() -> list[ChatMessage]`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`list[ChatMessage]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
返回当前计算得到的结果。
```

### `app/chat/schemas.py`

**模块作用**：Chat schema：消息、citation、draft 和 API 响应。

#### `ChatCitation.validate_citation_identity`

- **源码**：`app/chat/schemas.py:155`
- **签名**：`def validate_citation_identity(self) -> "ChatCitation"`
- **作用**：在约束论文复现请求、运行状态、证据和结果结构的契约校验阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `'ChatCitation'` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`'ChatCitation'`
- **语义**：返回 `'ChatCitation'` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
计算组合多个值形成元组，并保存为 当前处理结果；计算组合多个值形成元组，并保存为 项目集合。
如果来源类型等于'comparison'：
    如果由当前处理结果组成的集合或迭代器中存在满足“当前字段值为空”的项，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
否则：
    如果由当前处理结果组成的集合或迭代器中存在满足“当前字段值不为空”的项，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果来源类型等于'project_fact'：
    如果由项目集合组成的集合或迭代器中存在满足“当前字段值为空”的项，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
否则：
    如果由项目集合组成的集合或迭代器中存在满足“当前字段值不为空”的项，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
计算组合多个值形成元组，并保存为 当前处理结果。
如果来源类型等于'knowledge'：
    如果由当前处理结果组成的集合或迭代器中存在满足“当前字段值为空”的项，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    如果“证据集合有值或为真”不成立，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    如果证据集合 的长度不等于辅助操作“构造临时集合、映射或轻量领域对象”的结果 的长度，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
否则：
    如果由当前处理结果组成的集合或迭代器中存在满足“当前字段值不为空”的项 或 证据集合有值或为真，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
计算组合多个值形成元组，并保存为 当前处理结果。
如果来源类型等于'web'：
    如果由当前处理结果组成的集合或迭代器中存在满足“当前字段值为空”的项，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
否则：
    如果由当前处理结果组成的集合或迭代器中存在满足“当前字段值不为空”的项，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
计算组合多个值形成元组，并保存为 当前处理结果。
如果来源类型等于'mcp'：
    如果由当前处理结果组成的集合或迭代器中存在满足“当前字段值为空”的项，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
否则：
    如果由当前处理结果组成的集合或迭代器中存在满足“当前字段值不为空”的项，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前对象的当前值。
```

#### `ChatMessage.validate_tool_trace_role`

- **源码**：`app/chat/schemas.py:295`
- **签名**：`def validate_tool_trace_role(self) -> "ChatMessage"`
- **作用**：在约束论文复现请求、运行状态、证据和结果结构的契约校验阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `'ChatMessage'` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`'ChatMessage'`
- **语义**：返回 `'ChatMessage'` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果调用方职责角色等于'user' 且 工具不为空，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前对象的当前值。
```

#### `ChatRequestedOperation.validate_decision_kind`

- **源码**：`app/chat/schemas.py:332`
- **签名**：`def validate_decision_kind(self) -> "ChatRequestedOperation"`
- **作用**：在约束论文复现请求、运行状态、证据和结果结构的契约校验阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `'ChatRequestedOperation'` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`'ChatRequestedOperation'`
- **语义**：返回 `'ChatRequestedOperation'` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果业务类别等于'submit_decision'：
    如果类别为空，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
否则：
    如果类别不为空，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前对象的当前值。
```

#### `ChatDraft.validate_operation_intent`

- **源码**：`app/chat/schemas.py:362`
- **签名**：`def validate_operation_intent(self) -> "ChatDraft"`
- **作用**：在约束论文复现请求、运行状态、证据和结果结构的契约校验阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `'ChatDraft'` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`'ChatDraft'`
- **语义**：返回 `'ChatDraft'` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果当前处理结果等于'operation_request'：
    如果操作为空，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
否则：
    如果操作不为空，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前对象的当前值。
```

#### `ConversationMemoryBody.validate_citation_schema`

- **源码**：`app/chat/schemas.py:436`
- **签名**：`def validate_citation_schema(self) -> "ConversationMemoryBody"`
- **作用**：在约束论文复现请求、运行状态、证据和结果结构的契约校验阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `'ConversationMemoryBody'` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`'ConversationMemoryBody'`
- **语义**：返回 `'ConversationMemoryBody'` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果版本等于'phase36-v1' 且 当前可迭代输入中存在满足“来源类型等于'comparison'”的项，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果版本属于('phase36-v1', 'phase38-v2') 且 当前可迭代输入中存在满足“来源类型等于'project_fact'”的项，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果版本不等于'phase49-v4' 且 版本不等于'phase51-v5' 且 当前可迭代输入中存在满足“来源类型等于'knowledge'”的项，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果版本不等于'phase51-v5' 且 当前可迭代输入中存在满足“来源类型等于'web'”的项，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前对象的当前值。
```

#### `ConversationMemoryView.from_memory`

- **源码**：`app/chat/schemas.py:515`
- **签名**：`def from_memory(cls: 未显式标注, memory: ConversationMemory) -> 'ConversationMemoryView'`
- **作用**：在约束论文复现请求、运行状态、证据和结果结构的契约校验阶段中，该函数接收记忆，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `'ConversationMemoryView'` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `cls` | `未显式标注` | 当前类对象，用于类级构造或校验。 |
| `memory` | `ConversationMemory` | 名为 `memory` 的 `ConversationMemory` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`'ConversationMemoryView'`
- **语义**：返回 `'ConversationMemoryView'` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `cls` 完成该函数的一项辅助处理，并返回处理结果。
```

### `app/chat/service.py`

**模块作用**：Chat Service：编排 context、prompt、provider 和 citation 校验。

#### `_request_sha256`

- **源码**：`app/chat/service.py:46`
- **签名**：`def _request_sha256(job_id: str, question: str) -> str`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收复现任务 ID、论文复现问题或用户问题，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `question` | `str` | 论文复现问题或用户问题；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回输入内容的 SHA-256 身份摘要，用于完整性校验，不是加密后的正文。

**伪代码**

```text
将结构化内容序列化或编码为可传输表示，并把结果记为 结构化请求载荷；计算输入内容的 SHA-256 身份摘要，并返回处理结果。
```

#### `_idempotency_key`

- **源码**：`app/chat/service.py:59`
- **签名**：`def _idempotency_key(value: str) -> str`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
去除当前字段值的首尾空白，并把规范化后的文本记为 映射键或对象字段名。
如果映射键或对象字段名为空或为假 或 映射键或对象字段名 的长度大于300，就拒绝继续处理并抛出 `ChatConflictError`，向调用方报告输入或运行失败。
返回映射键或对象字段名的当前值。
```

#### `build_chat_draft_invoker`

- **源码**：`app/chat/service.py:68`
- **签名**：`def build_chat_draft_invoker() -> ChatDraftInvoker`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，Chat Provider adapter；只允许结构化回答，不绑定 Tool。该函数接收当前运行配置、模块状态和已注入依赖，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `ChatDraftInvoker` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`ChatDraftInvoker`
- **语义**：返回 `ChatDraftInvoker` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
定义内部辅助函数 `invoke`，供当前函数在后续步骤中调用。
返回前一步处理得到的结果。
```

#### `build_chat_draft_invoker.invoke`

- **源码**：`app/chat/service.py:71`
- **签名**：`def invoke(prompt: str, job_id: str) -> ChatDraft`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收发给模型的结构化提示、复现任务 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ChatDraft` 的领域结果。

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
加载这一步需要的外部依赖；调用 `invoke_structured` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果。
如果当前字段值为空，就调用 `join` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；拒绝继续处理并抛出 `ChatUnavailableError`，向调用方报告输入或运行失败。
返回当前字段值的当前值。
```

#### `ChatService.__init__`

- **源码**：`app/chat/service.py:96`
- **签名**：`def __init__(self: 未显式标注, repository: ChatRepository, interaction: InteractionService, context_builder: ChatContextBuilder, draft_invoker: ChatDraftInvoker, memory_compactor: ConversationMemoryCompactor, recent_messages: int, history_max_chars: int, memory_max_chars: int, prompt_max_chars: int, redactor: SecretRedactor | None, tool_loop: BoundedToolCallingLoop | None, source_limit: int, total_context_chars: int) -> None（隐式）`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收持久化仓库、用户交互记录、上下文构造器、草稿等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `repository` | `ChatRepository` | 持久化或目录访问端口；负责读取、CAS 更新或 Artifact 定位。 |
| `interaction` | `InteractionService` | 用户交互记录；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `context_builder` | `ChatContextBuilder` | 名为 `context_builder` 的 `ChatContextBuilder` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `draft_invoker` | `ChatDraftInvoker` | 可调用依赖；由当前函数在受控位置调用。 |
| `memory_compactor` | `ConversationMemoryCompactor` | 名为 `memory_compactor` 的 `ConversationMemoryCompactor` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `recent_messages` | `int` | 名为 `recent_messages` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `history_max_chars` | `int` | 名为 `history_max_chars` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `memory_max_chars` | `int` | 名为 `memory_max_chars` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `prompt_max_chars` | `int` | 名为 `prompt_max_chars` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `redactor` | `SecretRedactor | None` | 敏感信息脱敏器；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 空值 |
| `tool_loop` | `BoundedToolCallingLoop | None` | 名为 `tool_loop` 的 `BoundedToolCallingLoop | None` 领域输入；用于当前函数的业务处理，具体约束见校验分支。；默认 空值 |
| `source_limit` | `int` | 名为 `source_limit` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。；默认 8 |
| `total_context_chars` | `int` | 名为 `total_context_chars` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。；默认 48000 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 持久化仓库、用户交互记录、上下文构造器、草稿、记忆、当前处理结果、字符数、记忆字符数、字符数 分别保存到同名实例字段；计算计算当前表达式的结果，并保存为 敏感信息脱敏器；把传入的 工具、来源上限、上下文字符数 分别保存到同名实例字段；构造 `Lock` 结构化领域对象，并把结果记为 该调用返回的结果。
```

#### `ChatService.ping`

- **源码**：`app/chat/service.py:130`
- **签名**：`def ping(self) -> None`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `ping` 完成该函数的一项辅助处理。
```

#### `ChatService.list_messages`

- **源码**：`app/chat/service.py:133`
- **签名**：`def list_messages(self: 未显式标注, job_id: str, after_sequence: int, limit: int) -> ChatMessagePage`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收复现任务 ID、增量读取的起始序号、结果数量上限，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `ChatMessagePage` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `after_sequence` | `int` | 增量读取的起始序号；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。 |

**输出**

- **Python 类型**：`ChatMessagePage`
- **语义**：返回 `ChatMessagePage` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `get_job` 读取或查询当前阶段需要的数据；调用 `list_messages` 读取或查询当前阶段需要的数据，并把结果记为 待处理项集合；构造并返回 `ChatMessagePage` 结构化领域对象。
```

#### `ChatService.list_recent_messages`

- **源码**：`app/chat/service.py:155`
- **签名**：`def list_recent_messages(self: 未显式标注, job_id: str, limit: int) -> ChatMessagePage`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，给 Web 首屏返回 newest N 条，响应内仍按时间正序。该函数接收复现任务 ID、结果数量上限，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `ChatMessagePage` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。 |

**输出**

- **Python 类型**：`ChatMessagePage`
- **语义**：返回 `ChatMessagePage` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `get_job` 读取或查询当前阶段需要的数据；调用 `list_recent_messages` 读取或查询当前阶段需要的数据，并把结果记为 待处理项集合；构造并返回 `ChatMessagePage` 结构化领域对象。
```

#### `ChatService.get_memory`

- **源码**：`app/chat/service.py:173`
- **签名**：`def get_memory(self: 未显式标注, job_id: str) -> ConversationMemoryView | None`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收复现任务 ID，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `ConversationMemoryView | None` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`ConversationMemoryView | None`
- **语义**：返回 `ConversationMemoryView | None` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `get_job` 读取或查询当前阶段需要的数据；调用 `get_latest_memory` 读取或查询当前阶段需要的数据，并把结果记为 记忆。
如果记忆为空，就返回固定值 `空值`。
先尝试完成以下处理：
    调用 `validate_memory_hash` 校验当前输入或状态。
如果出现 `Exception`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `ChatUnavailableError`，向调用方报告输入或运行失败。
调用 `from_memory` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `ChatService._memory_status`

- **源码**：`app/chat/service.py:190`
- **签名**：`def _memory_status(self: 未显式标注, outcome: MemoryCompactionOutcome | None) -> ChatMemoryStatus`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收执行结论，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ChatMemoryStatus` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `outcome` | `MemoryCompactionOutcome | None` | 前序调用产生的结构化响应、结果或执行结论，供当前函数继续判断或投影。；默认 空值 |

**输出**

- **Python 类型**：`ChatMemoryStatus`
- **语义**：返回 `ChatMemoryStatus` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
计算根据条件从两个候选结果中选择一个，并保存为 记忆；构造并返回 `ChatMemoryStatus` 结构化领域对象。
```

#### `ChatService._current_memory_outcome`

- **源码**：`app/chat/service.py:208`
- **签名**：`def _current_memory_outcome(self: 未显式标注, job_id: str) -> MemoryCompactionOutcome`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收复现任务 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `MemoryCompactionOutcome` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`MemoryCompactionOutcome`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
先尝试完成以下处理：
    调用 `get_latest_memory` 读取或查询当前阶段需要的数据，并把结果记为 记忆。
    如果记忆不为空，就调用 `validate_memory_hash` 校验当前输入或状态。
    构造并返回 `MemoryCompactionOutcome` 结构化领域对象。
如果出现 `Exception`并把异常保存为捕获的异常对象：
    构造并返回 `MemoryCompactionOutcome` 结构化领域对象。
```

#### `ChatService.ask`

- **源码**：`app/chat/service.py:225`
- **签名**：`def ask(self: 未显式标注, job_id: str, question: str, idempotency_key: str) -> ChatAskResponse`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收复现任务 ID、论文复现问题或用户问题、请求幂等键，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `question` | `str` | 论文复现问题或用户问题；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `idempotency_key` | `str` | 调用方提供的幂等键；重复请求应复用同一结果，而不是再次产生副作用。 |

**输出**

- **Python 类型**：`ChatAskResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
去除论文复现问题或用户问题的首尾空白，并把规范化后的文本记为 当前处理结果。
如果当前处理结果为空或为假，就拒绝继续处理并抛出 `ChatConflictError`，向调用方报告输入或运行失败。
调用 `redact_text` 解析、规范化或转换当前输入，并把结果记为 该调用返回的结果；调用 `_idempotency_key` 完成该函数的一项辅助处理，并把结果记为 映射键或对象字段名；调用 `_request_sha256` 计算内容身份、分数或派生结果，并把结果记为 请求内容 Hash；调用 `get_job` 读取或查询当前阶段需要的数据，并把结果记为 复现任务记录。
调用 `find_exchange` 读取或查询当前阶段需要的数据，并把结果记为 该调用返回的结果。
如果当前处理结果不为空，就调用 `_current_memory_outcome` 完成该函数的一项辅助处理，并把结果记为 记忆；构造并返回 `ChatAskResponse` 结构化领域对象。
进入上下文“读取当前处理结果的当前值”，退出时自动清理资源：
    调用 `find_exchange` 读取或查询当前阶段需要的数据，并把结果记为 该调用返回的结果。
    如果当前处理结果不为空，就调用 `_current_memory_outcome` 完成该函数的一项辅助处理，并把结果记为 记忆；构造并返回 `ChatAskResponse` 结构化领域对象。
    调用 `ensure_memory` 完成该函数的一项辅助处理，并把结果记为 记忆；读取记忆，并保存为 记忆；调用 `info` 完成该函数的一项辅助处理；调用 `list_recent_messages` 读取或查询当前阶段需要的数据，并把结果记为 该调用返回的结果。
    遍历并筛选输入，将整理后的结果保存为 历史对话或运行记录；计算使用固定配置或常量值，并保存为 工具。
    如果工具为空：
        调用 `build` 完成该函数的一项辅助处理，并把结果记为 代码仓库归档包。
    否则：
        调用 `build_job_only` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果。
        先尝试完成以下处理：
            调用 `run` 完成该函数的一项辅助处理，并把结果记为 执行结论；调用 `public_trace_summary` 完成该函数的一项辅助处理，并把结果记为 工具。
            如果当前状态属于{'planner_unavailable', 'policy_blocked'}，就调用 `build` 完成该函数的一项辅助处理，并把结果记为 代码仓库归档包；否则调用 `merge_grounding_sources` 完成该函数的一项辅助处理，并把结果记为 代码仓库归档包。
        如果出现 `Exception`并把异常保存为捕获的异常对象：
            调用 `warning` 完成该函数的一项辅助处理；调用 `build` 完成该函数的一项辅助处理，并把结果记为 代码仓库归档包。
    调用 `build_budgeted_chat_prompt` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果；调用 `redact_text` 解析、规范化或转换当前输入，并把结果记为 该调用返回的结果。
    如果当前处理结果 的长度大于字符数，就拒绝继续处理并抛出 `ChatUnavailableError`，向调用方报告输入或运行失败。
    调用 `draft_invoker` 完成该函数的一项辅助处理，并把结果记为 草稿对象；遍历并筛选输入，将整理后的结果保存为 来源的 ID；遍历并筛选输入，将整理后的结果保存为 当前处理结果；构造临时集合、映射或轻量领域对象，并把结果记为 该调用返回的结果。
    如果当前处理结果有值或为真 或 当前处理结果为空或为假，就计算使用固定配置或常量值，并保存为 当前处理结果；将 论文引用证据集合 初始化为空列表，用来收集后续结果；否则调用 `redact_text` 解析、规范化或转换当前输入，并把结果记为 该调用返回的结果；遍历并筛选输入，将整理后的结果保存为 论文引用证据集合。
    调用 `append_exchange` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；调用 `get_job` 读取或查询当前阶段需要的数据，并把结果记为 当前任务；构造并返回 `ChatAskResponse` 结构化领域对象。
```

#### `build_chat_service`

- **源码**：`app/chat/service.py:441`
- **签名**：`def build_chat_service(repository: ChatRepository, interaction: InteractionService, context_builder: ChatContextBuilder) -> ChatService`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收持久化仓库、用户交互记录、上下文构造器，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `ChatService` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `repository` | `ChatRepository` | 持久化或目录访问端口；负责读取、CAS 更新或 Artifact 定位。 |
| `interaction` | `InteractionService` | 用户交互记录；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `context_builder` | `ChatContextBuilder` | 名为 `context_builder` 的 `ChatContextBuilder` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`ChatService`
- **语义**：返回 `ChatService` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
加载这一步需要的外部依赖；调用 `build_redactor` 组装当前阶段需要的领域对象，并把结果记为 敏感信息脱敏器；构造 `ConversationMemoryCompactor` 结构化领域对象，并把结果记为 记忆；计算使用固定配置或常量值，并保存为 工具。
如果对话工具有值或为真，就加载这一步需要的外部依赖；调用 `build_chat_tool_calling_loop` 组装当前阶段需要的领域对象，并把结果记为 工具。
构造并返回 `ChatService` 结构化领域对象。
```

### `app/chat/store.py`

**模块作用**：SQLite Chat Store：每个 Job 拥有独立聊天序列。

#### `ChatRepository.initialize`

- **源码**：`app/chat/store.py:23`
- **签名**：`def initialize(self) -> None`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

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

#### `ChatRepository.ping`

- **源码**：`app/chat/store.py:26`
- **签名**：`def ping(self) -> None`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

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

#### `ChatRepository.list_messages`

- **源码**：`app/chat/store.py:29`
- **签名**：`def list_messages(self: 未显式标注, job_id: str, after_sequence: int, limit: int) -> list[ChatMessage]`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收复现任务 ID、增量读取的起始序号、结果数量上限，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `after_sequence` | `int` | 增量读取的起始序号；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。 |

**输出**

- **Python 类型**：`list[ChatMessage]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `ChatRepository.list_recent_messages`

- **源码**：`app/chat/store.py:38`
- **签名**：`def list_recent_messages(self: 未显式标注, job_id: str, limit: int) -> list[ChatMessage]`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收复现任务 ID、结果数量上限，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。 |

**输出**

- **Python 类型**：`list[ChatMessage]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `ChatRepository.list_messages_range`

- **源码**：`app/chat/store.py:46`
- **签名**：`def list_messages_range(self: 未显式标注, job_id: str, start_sequence: int, end_sequence: int, limit: int) -> list[ChatMessage]`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收复现任务 ID、当前处理结果、当前处理结果、结果数量上限，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `start_sequence` | `int` | 名为 `start_sequence` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `end_sequence` | `int` | 名为 `end_sequence` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。 |

**输出**

- **Python 类型**：`list[ChatMessage]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `ChatRepository.latest_sequence`

- **源码**：`app/chat/store.py:56`
- **签名**：`def latest_sequence(self, job_id: str) -> int`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收复现任务 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终数量、序号、字节数或版本等整数结果。

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
仅声明接口契约，这里没有具体实现。
```

#### `ChatRepository.find_exchange`

- **源码**：`app/chat/store.py:59`
- **签名**：`def find_exchange(self: 未显式标注, job_id: str, idempotency_key: str, request_sha256: str) -> tuple[ChatMessage, ChatMessage] | None`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收复现任务 ID、请求幂等键、请求内容 SHA-256，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `idempotency_key` | `str` | 调用方提供的幂等键；重复请求应复用同一结果，而不是再次产生副作用。 |
| `request_sha256` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |

**输出**

- **Python 类型**：`tuple[ChatMessage, ChatMessage] | None`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `ChatRepository.append_exchange`

- **源码**：`app/chat/store.py:68`
- **签名**：`def append_exchange(self: 未显式标注, job_id: str, idempotency_key: str, request_sha256: str, question: str, answer: str, citations: Sequence[ChatCitation], tool_trace: ChatToolTraceSummary | None) -> tuple[ChatMessage, ChatMessage, bool]`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收复现任务 ID、请求幂等键、请求内容 SHA-256、论文复现问题或用户问题等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `idempotency_key` | `str` | 调用方提供的幂等键；重复请求应复用同一结果，而不是再次产生副作用。 |
| `request_sha256` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |
| `question` | `str` | 论文复现问题或用户问题；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `answer` | `str` | 名为 `answer` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `citations` | `Sequence[ChatCitation]` | 论文引用证据集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `tool_trace` | `ChatToolTraceSummary | None` | 名为 `tool_trace` 的 `ChatToolTraceSummary | None` 领域输入；用于当前函数的业务处理，具体约束见校验分支。；默认 空值 |

**输出**

- **Python 类型**：`tuple[ChatMessage, ChatMessage, bool]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `ChatRepository.get_latest_memory`

- **源码**：`app/chat/store.py:81`
- **签名**：`def get_latest_memory(self: 未显式标注, job_id: str) -> ConversationMemory | None`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收复现任务 ID，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `ConversationMemory | None` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`ConversationMemory | None`
- **语义**：返回 `ConversationMemory | None` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `ChatRepository.save_memory`

- **源码**：`app/chat/store.py:87`
- **签名**：`def save_memory(self: 未显式标注, memory: ConversationMemory, expected_parent_memory_id: str | None) -> tuple[ConversationMemory, bool]`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收记忆、期望记忆的 ID，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `memory` | `ConversationMemory` | 名为 `memory` 的 `ConversationMemory` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `expected_parent_memory_id` | `str | None` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`tuple[ConversationMemory, bool]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `_now`

- **源码**：`app/chat/store.py:96`
- **签名**：`def _now() -> str`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `isoformat` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `SqliteChatRepository.__init__`

- **源码**：`app/chat/store.py:103`
- **签名**：`def __init__(self, path: Path)`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收文件或目录路径，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 文件或目录路径 分别保存到同名实例字段。
```

#### `SqliteChatRepository._connect`

- **源码**：`app/chat/store.py:106`
- **签名**：`def _connect(self) -> sqlite3.Connection`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于在固定 MCP Policy、Schema Pin、调用预算和只读职责边界内连接或调用外部能力，并把返回内容转换为可追溯的复现证据，最终标注为 `sqlite3.Connection` 的领域结果。

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

#### `SqliteChatRepository.initialize`

- **源码**：`app/chat/store.py:116`
- **签名**：`def initialize(self) -> None`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

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
进入上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”，退出时自动清理资源：
    通过数据库连接执行数据查询或命令；调用 `executescript` 完成该函数的一项辅助处理；遍历并筛选输入，将整理后的结果保存为 当前处理结果。
    如果当前输入内容不属于当前处理结果，就通过数据库连接执行数据查询或命令。
```

#### `SqliteChatRepository.ping`

- **源码**：`app/chat/store.py:190`
- **签名**：`def ping(self) -> None`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

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

#### `SqliteChatRepository._message`

- **源码**：`app/chat/store.py:195`
- **签名**：`def _message(row: sqlite3.Row) -> ChatMessage`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收数据库记录行，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ChatMessage` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `row` | `sqlite3.Row` | 数据库记录行；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`ChatMessage`
- **语义**：返回 `ChatMessage` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
计算根据条件从两个候选结果中选择一个，并保存为 当前处理结果；构造并返回 `ChatMessage` 结构化领域对象。
```

#### `SqliteChatRepository._memory`

- **源码**：`app/chat/store.py:217`
- **签名**：`def _memory(row: sqlite3.Row) -> ConversationMemory`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收数据库记录行，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ConversationMemory` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `row` | `sqlite3.Row` | 数据库记录行；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`ConversationMemory`
- **语义**：返回 `ConversationMemory` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `ConversationMemory` 结构化领域对象。
```

#### `SqliteChatRepository.list_messages`

- **源码**：`app/chat/store.py:236`
- **签名**：`def list_messages(self: 未显式标注, job_id: str, after_sequence: int, limit: int) -> list[ChatMessage]`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收复现任务 ID、增量读取的起始序号、结果数量上限，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `after_sequence` | `int` | 增量读取的起始序号；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。 |

**输出**

- **Python 类型**：`list[ChatMessage]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
在上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”中调用 `fetchall` 完成该函数的一项辅助处理，并把结果记为 数据库记录行集合，退出时自动清理资源。
返回当前计算得到的结果。
```

#### `SqliteChatRepository.list_recent_messages`

- **源码**：`app/chat/store.py:256`
- **签名**：`def list_recent_messages(self: 未显式标注, job_id: str, limit: int) -> list[ChatMessage]`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收复现任务 ID、结果数量上限，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。 |

**输出**

- **Python 类型**：`list[ChatMessage]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
计算数量、边界或类型判断结果，并把结果记为 该调用返回的结果。
在上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”中调用 `fetchall` 完成该函数的一项辅助处理，并把结果记为 数据库记录行集合，退出时自动清理资源。
返回当前计算得到的结果。
```

#### `SqliteChatRepository.list_messages_range`

- **源码**：`app/chat/store.py:277`
- **签名**：`def list_messages_range(self: 未显式标注, job_id: str, start_sequence: int, end_sequence: int, limit: int) -> list[ChatMessage]`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收复现任务 ID、当前处理结果、当前处理结果、结果数量上限，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `start_sequence` | `int` | 名为 `start_sequence` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `end_sequence` | `int` | 名为 `end_sequence` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。 |

**输出**

- **Python 类型**：`list[ChatMessage]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
如果当前处理结果小于1 或 当前处理结果小于当前处理结果，就返回当前构造的顺序或去重集合。
计算数量、边界或类型判断结果，并把结果记为 该调用返回的结果。
在上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”中调用 `fetchall` 完成该函数的一项辅助处理，并把结果记为 数据库记录行集合，退出时自动清理资源。
返回当前计算得到的结果。
```

#### `SqliteChatRepository.latest_sequence`

- **源码**：`app/chat/store.py:302`
- **签名**：`def latest_sequence(self, job_id: str) -> int`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收复现任务 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终数量、序号、字节数或版本等整数结果。

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
在上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”中调用 `fetchone` 完成该函数的一项辅助处理，并把结果记为 数据库记录行，退出时自动清理资源。
调用 `int` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `SqliteChatRepository._exchange_from_user_row`

- **源码**：`app/chat/store.py:314`
- **签名**：`def _exchange_from_user_row(self: 未显式标注, connection: sqlite3.Connection, user_row: sqlite3.Row, request_sha256: str) -> tuple[ChatMessage, ChatMessage]`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收数据库连接、记录行、请求内容 SHA-256，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `connection` | `sqlite3.Connection` | 数据库连接；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `user_row` | `sqlite3.Row` | 名为 `user_row` 的 `sqlite3.Row` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `request_sha256` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |

**输出**

- **Python 类型**：`tuple[ChatMessage, ChatMessage]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
如果记录行中的对应字段不等于请求内容 SHA-256，就拒绝继续处理并抛出 `ChatConflictError`，向调用方报告输入或运行失败。
调用 `fetchone` 完成该函数的一项辅助处理，并把结果记为 记录行。
如果记录行为空，就拒绝继续处理并抛出 `ChatConflictError`，向调用方报告输入或运行失败。
返回当前构造的顺序或去重集合。
```

#### `SqliteChatRepository.find_exchange`

- **源码**：`app/chat/store.py:334`
- **签名**：`def find_exchange(self: 未显式标注, job_id: str, idempotency_key: str, request_sha256: str) -> tuple[ChatMessage, ChatMessage] | None`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收复现任务 ID、请求幂等键、请求内容 SHA-256，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `idempotency_key` | `str` | 调用方提供的幂等键；重复请求应复用同一结果，而不是再次产生副作用。 |
| `request_sha256` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |

**输出**

- **Python 类型**：`tuple[ChatMessage, ChatMessage] | None`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
进入上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”，退出时自动清理资源：
    调用 `fetchone` 完成该函数的一项辅助处理，并把结果记为 记录行。
    如果记录行为空，就返回固定值 `空值`。
    调用 `_exchange_from_user_row` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `SqliteChatRepository.append_exchange`

- **源码**：`app/chat/store.py:357`
- **签名**：`def append_exchange(self: 未显式标注, job_id: str, idempotency_key: str, request_sha256: str, question: str, answer: str, citations: Sequence[ChatCitation], tool_trace: ChatToolTraceSummary | None) -> tuple[ChatMessage, ChatMessage, bool]`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收复现任务 ID、请求幂等键、请求内容 SHA-256、论文复现问题或用户问题等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `idempotency_key` | `str` | 调用方提供的幂等键；重复请求应复用同一结果，而不是再次产生副作用。 |
| `request_sha256` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |
| `question` | `str` | 论文复现问题或用户问题；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `answer` | `str` | 名为 `answer` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `citations` | `Sequence[ChatCitation]` | 论文引用证据集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `tool_trace` | `ChatToolTraceSummary | None` | 名为 `tool_trace` 的 `ChatToolTraceSummary | None` 领域输入；用于当前函数的业务处理，具体约束见校验分支。；默认 空值 |

**输出**

- **Python 类型**：`tuple[ChatMessage, ChatMessage, bool]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
调用 `_connect` 完成该函数的一项辅助处理，并把结果记为 数据库连接。
先尝试完成以下处理：
    通过数据库连接执行数据查询或命令；调用 `fetchone` 完成该函数的一项辅助处理，并把结果记为 已有记录。
    如果已有记录不为空，就调用 `_exchange_from_user_row` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；提交数据库连接中已完成的数据变更；返回当前构造的顺序或去重集合。
    读取前一步操作返回对象中的对应字段，并保存为 下一项；读取当前时间，作为状态变更的统一时间戳，并把结果记为 创建时间；计算根据字段和固定文本生成格式化文本，并保存为 当前处理结果的 ID；计算根据字段和固定文本生成格式化文本，并保存为 当前处理结果的 ID。
    通过数据库连接执行数据查询或命令；通过数据库连接执行数据查询或命令；调用 `fetchone` 完成该函数的一项辅助处理，并把结果记为 记录行；调用 `fetchone` 完成该函数的一项辅助处理，并把结果记为 记录行。
    提交数据库连接中已完成的数据变更；断言记录行不为空 且 记录行不为空；不满足就终止当前测试或流程；返回当前构造的顺序或去重集合。
如果出现 `Exception`：
    回滚数据库连接中未完成的数据变更；重新抛出当前异常，保持原始失败信息。
无论成功还是失败，最后都要：
    关闭数据库连接并释放相关资源。
```

#### `SqliteChatRepository.get_latest_memory`

- **源码**：`app/chat/store.py:469`
- **签名**：`def get_latest_memory(self: 未显式标注, job_id: str) -> ConversationMemory | None`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收复现任务 ID，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `ConversationMemory | None` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`ConversationMemory | None`
- **语义**：返回 `ConversationMemory | None` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
在上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”中调用 `fetchone` 完成该函数的一项辅助处理，并把结果记为 数据库记录行，退出时自动清理资源。
返回按条件选出的结果。
```

#### `SqliteChatRepository.save_memory`

- **源码**：`app/chat/store.py:486`
- **签名**：`def save_memory(self: 未显式标注, memory: ConversationMemory, expected_parent_memory_id: str | None) -> tuple[ConversationMemory, bool]`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收记忆、期望记忆的 ID，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `memory` | `ConversationMemory` | 名为 `memory` 的 `ConversationMemory` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `expected_parent_memory_id` | `str | None` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`tuple[ConversationMemory, bool]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
调用 `_connect` 完成该函数的一项辅助处理，并把结果记为 数据库连接。
先尝试完成以下处理：
    通过数据库连接执行数据查询或命令；调用 `fetchone` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `fetchone` 完成该函数的一项辅助处理，并把结果记为 已有记录。
    如果已有记录不为空：
        如果已有记录中的对应字段不等于当前处理结果的 SHA-256 或 已有记录中的对应字段不等于期望记忆的 ID，就拒绝继续处理并抛出 `ChatMemoryConflict`，向调用方报告输入或运行失败。
        调用 `fetchone` 完成该函数的一项辅助处理，并把结果记为 记录行；提交数据库连接中已完成的数据变更；断言记录行不为空；不满足就终止当前测试或流程；返回当前构造的顺序或去重集合。
    计算根据条件从两个候选结果中选择一个，并保存为 当前。
    如果当前不等于期望记忆的 ID，就拒绝继续处理并抛出 `ChatMemoryConflict`，向调用方报告输入或运行失败。
    计算根据条件从两个候选结果中选择一个，并保存为 调用方看到的旧版本号；计算根据条件从两个候选结果中选择一个，并保存为 期望。
    如果记录版本号不等于调用方看到的旧版本号 或 当前处理结果不等于期望 或 记忆的 ID不等于当前，就拒绝继续处理并抛出 `ChatMemoryConflict`，向调用方报告输入或运行失败。
    通过数据库连接执行数据查询或命令；通过数据库连接执行数据查询或命令；提交数据库连接中已完成的数据变更；返回当前构造的顺序或去重集合。
如果出现 `Exception`：
    回滚数据库连接中未完成的数据变更；重新抛出当前异常，保持原始失败信息。
无论成功还是失败，最后都要：
    关闭数据库连接并释放相关资源。
```

#### `SqliteChatRepository.delete_job_messages`

- **源码**：`app/chat/store.py:624`
- **签名**：`def delete_job_messages(self, job_id: str) -> int`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，删除一个 Job 的全部 Chat durable data（messages + memory）。该函数接收复现任务 ID，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终数量、序号、字节数或版本等整数结果。

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
调用 `_connect` 完成该函数的一项辅助处理，并把结果记为 数据库连接。
先尝试完成以下处理：
    通过数据库连接执行数据查询或命令；通过数据库连接执行数据查询或命令；通过数据库连接执行数据查询或命令；读取前一步操作返回对象的当前处理结果，并保存为 后续步骤使用的结果。
    提交数据库连接中已完成的数据变更；调用 `int` 完成该函数的一项辅助处理，并返回处理结果。
如果出现 `Exception`：
    回滚数据库连接中未完成的数据变更；重新抛出当前异常，保持原始失败信息。
无论成功还是失败，最后都要：
    关闭数据库连接并释放相关资源。
```

### `app/comparison/factory.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `build_comparison_repository`

- **源码**：`app/comparison/factory.py:10`
- **签名**：`def build_comparison_repository() -> FileComparisonRepository`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `FileComparisonRepository` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`FileComparisonRepository`
- **语义**：返回 `FileComparisonRepository` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `FileComparisonRepository` 结构化领域对象。
```

#### `build_run_evidence_reader`

- **源码**：`app/comparison/factory.py:19`
- **签名**：`def build_run_evidence_reader(jobs: ComparisonJobReader, artifact_catalog: ArtifactCatalog) -> VerifiedRunEvidenceReader`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收复现任务记录集合、Artifact，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `VerifiedRunEvidenceReader` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `jobs` | `ComparisonJobReader` | 复现任务记录集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `artifact_catalog` | `ArtifactCatalog` | 名为 `artifact_catalog` 的 `ArtifactCatalog` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`VerifiedRunEvidenceReader`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
构造并返回 `VerifiedRunEvidenceReader` 结构化领域对象。
```

#### `build_comparison_service`

- **源码**：`app/comparison/factory.py:32`
- **签名**：`def build_comparison_service(jobs: ComparisonJobReader, artifact_catalog: ArtifactCatalog, evidence_reader: VerifiedRunEvidenceReader | None) -> ComparisonService`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收复现任务记录集合、Artifact、证据读取器，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `ComparisonService` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `jobs` | `ComparisonJobReader` | 复现任务记录集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `artifact_catalog` | `ArtifactCatalog` | 名为 `artifact_catalog` 的 `ArtifactCatalog` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `evidence_reader` | `VerifiedRunEvidenceReader | None` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。；默认 空值 |

**输出**

- **Python 类型**：`ComparisonService`
- **语义**：返回 `ComparisonService` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
计算计算当前表达式的结果，并保存为 读取器；构造并返回 `ComparisonService` 结构化领域对象。
```

### `app/comparison/identity.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `canonical_json_bytes`

- **源码**：`app/comparison/identity.py:11`
- **签名**：`def canonical_json_bytes(value: Any) -> bytes`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，使用稳定 JSON 编码，避免字典顺序改变内容身份。该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `bytes` 的领域结果。

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

#### `sha256_text`

- **源码**：`app/comparison/identity.py:23`
- **签名**：`def sha256_text(value: str) -> str`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，敏感文本只进入不可逆内容身份，不直接写入 Comparison。该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

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

#### `sha256_payload`

- **源码**：`app/comparison/identity.py:29`
- **签名**：`def sha256_payload(value: Any) -> str`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

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

#### `compute_snapshot_hash`

- **源码**：`app/comparison/identity.py:33`
- **签名**：`def compute_snapshot_hash(snapshot: RunSnapshot | dict[str, Any]) -> str`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收MCP 能力快照，用于计算输入、命令、运行配置或证据的稳定派生值，保证复现链路中的身份校验和 stale 检测，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `snapshot` | `RunSnapshot | dict[str, Any]` | MCP 能力快照；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回内容身份摘要，通常为 SHA-256 十六进制字符串。

**伪代码**

```text
计算根据条件从两个候选结果中选择一个，并保存为 结构化请求载荷；从结构化请求载荷取出并移除最后一项；调用 `sha256_payload` 计算内容身份、分数或派生结果，并返回处理结果。
```

#### `validate_snapshot_hash`

- **源码**：`app/comparison/identity.py:44`
- **签名**：`def validate_snapshot_hash(snapshot: RunSnapshot) -> None`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收MCP 能力快照，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `snapshot` | `RunSnapshot` | MCP 能力快照；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
如果辅助操作“调用 `compute_snapshot_hash` 计算内容身份、分数或派生结果”的结果不等于MCP 能力快照的 Hash，就拒绝继续处理并抛出 `ComparisonIntegrityError`，向调用方报告输入或运行失败。
```

#### `compute_comparison_hash`

- **源码**：`app/comparison/identity.py:49`
- **签名**：`def compute_comparison_hash(report: ComparisonReport | dict[str, Any]) -> str`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收MCP 评测或运行报告，用于计算输入、命令、运行配置或证据的稳定派生值，保证复现链路中的身份校验和 stale 检测，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `report` | `ComparisonReport | dict[str, Any]` | MCP 评测或运行报告；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回内容身份摘要，通常为 SHA-256 十六进制字符串。

**伪代码**

```text
计算根据条件从两个候选结果中选择一个，并保存为 结构化请求载荷；从结构化请求载荷取出并移除最后一项；从结构化请求载荷取出并移除最后一项；从结构化请求载荷取出并移除最后一项。
调用 `sha256_payload` 计算内容身份、分数或派生结果，并返回处理结果。
```

#### `comparison_id_for_hash`

- **源码**：`app/comparison/identity.py:64`
- **签名**：`def comparison_id_for_hash(comparison_hash: str) -> str`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收SDK 或 MCP 运行升级比较结果的 Hash，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `comparison_hash` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回内容身份摘要，通常为 SHA-256 十六进制字符串。

**伪代码**

```text
返回当前计算得到的结果。
```

#### `validate_report_identity`

- **源码**：`app/comparison/identity.py:68`
- **签名**：`def validate_report_identity(report: ComparisonReport) -> None`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收MCP 评测或运行报告，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `report` | `ComparisonReport` | MCP 评测或运行报告；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `validate_snapshot_hash` 校验当前输入或状态；调用 `validate_snapshot_hash` 校验当前输入或状态；调用 `compute_comparison_hash` 计算内容身份、分数或派生结果，并把结果记为 实际值的 Hash。
如果实际值的 Hash不等于SDK 或 MCP 运行升级比较结果的 Hash，就拒绝继续处理并抛出 `ComparisonIntegrityError`，向调用方报告输入或运行失败。
如果辅助操作“调用 `comparison_id_for_hash` 完成该函数的一项辅助处理”的结果不等于SDK 或 MCP 运行升级比较结果的 ID，就拒绝继续处理并抛出 `ComparisonIntegrityError`，向调用方报告输入或运行失败。
```

### `app/comparison/rendering.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_inline`

- **源码**：`app/comparison/rendering.py:9`
- **签名**：`def _inline(value: Any, *, max_chars: int = 240) -> str`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，生成单行、有界、不会破坏 Markdown 表格的值。该函数接收当前字段值、最大字符数，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `Any` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |
| `max_chars` | `int` | 名为 `max_chars` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。；默认 240 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
如果当前字段值为空：
    计算使用固定配置或常量值，并保存为 待处理文本。
否则：
    如果“计算数量、边界或类型判断结果”后得到肯定结果，就读取当前字段值，并保存为 待处理文本；否则将结构化内容序列化或编码为可传输表示，并把结果记为 待处理文本。
调用 `replace` 完成该函数的一项辅助处理，并把结果记为 待处理文本。
如果待处理文本 的长度大于最大字符数，就返回当前计算得到的结果。
返回待处理文本的当前值。
```

#### `_render_change`

- **源码**：`app/comparison/rendering.py:29`
- **签名**：`def _render_change(change: RunChange) -> str`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收当前处理结果，用于把复现过程中的结构化状态、证据或结果转换为可读、可传输或可持久化的表示，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `change` | `RunChange` | 名为 `change` 的 `RunChange` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
返回当前计算得到的结果。
```

#### `render_comparison_markdown`

- **源码**：`app/comparison/rendering.py:40`
- **签名**：`def render_comparison_markdown(report: ComparisonReport) -> str`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，只渲染 Comparison 中已经 allowlist、脱敏的字段。该函数接收MCP 评测或运行报告，用于把复现过程中的结构化状态、证据或结果转换为可读、可传输或可持久化的表示，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `report` | `ComparisonReport` | MCP 评测或运行报告；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回整理、格式化或规范化后的文本表示。

**伪代码**

```text
计算计算当前表达式的结果，并保存为 警告集合；计算计算当前表达式的结果，并保存为 当前处理结果；调用 `join` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `comparison_chat_projection`

- **源码**：`app/comparison/rendering.py:89`
- **签名**：`def comparison_chat_projection(report: ComparisonReport) -> str`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，给 Chat 的有界结构化来源；不把整份 JSON 注入 Prompt。该函数接收MCP 评测或运行报告，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `report` | `ComparisonReport` | MCP 评测或运行报告；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
读取前一步操作返回对象中的对应字段，并保存为 后续步骤使用的结果；计算按字段初始化键值映射，并保存为 结构化请求载荷；将结构化内容序列化或编码为可传输表示，并返回处理结果。
```

### `app/comparison/repository.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `FileComparisonRepository.__init__`

- **源码**：`app/comparison/repository.py:37`
- **签名**：`def __init__(self: 未显式标注, root: Path, max_report_bytes: int, list_scan_limit: int, staging_ttl_seconds: int) -> None（隐式）`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收受控扫描根目录、最大MCP 评测或运行报告的字节内容、上限、当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `root` | `Path` | 运行产物或受控工作区的目录路径；用于隔离本次运行生成的文件。 |
| `max_report_bytes` | `int` | 名为 `max_report_bytes` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `list_scan_limit` | `int` | 名为 `list_scan_limit` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `staging_ttl_seconds` | `int` | 名为 `staging_ttl_seconds` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 最大MCP 评测或运行报告的字节内容、上限、当前处理结果 分别保存到同名实例字段；将受控扫描根目录规范化为受控的绝对路径，并把结果记为 根目录。
如果“检查根目录的文件系统属性”后得到肯定结果，就拒绝继续处理并抛出 `ComparisonConflictError`，向调用方报告输入或运行失败。
创建根目录对应的目录。
如果“检查根目录的文件系统属性”后得到肯定结果 或 “检查根目录的文件系统属性”后未得到肯定结果，就拒绝继续处理并抛出 `ComparisonConflictError`，向调用方报告输入或运行失败。
将根目录规范化为受控的绝对路径，并把结果记为 受控扫描根目录；计算组合或计算已有值，并保存为 暂存工作区根目录。
如果“检查暂存工作区根目录的文件系统属性”后得到肯定结果，就拒绝继续处理并抛出 `ComparisonConflictError`，向调用方报告输入或运行失败。
创建暂存工作区根目录对应的目录。
如果“检查暂存工作区根目录的文件系统属性”后得到肯定结果，就拒绝继续处理并抛出 `ComparisonConflictError`，向调用方报告输入或运行失败。
```

#### `FileComparisonRepository.ping`

- **源码**：`app/comparison/repository.py:63`
- **签名**：`def ping(self) -> None`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
如果“检查受控扫描根目录的文件系统属性”后未得到肯定结果 或 “调用 `access` 完成该函数的一项辅助处理”后未得到肯定结果，就拒绝继续处理并抛出 `ComparisonConflictError`，向调用方报告输入或运行失败。
```

#### `FileComparisonRepository._dir_for`

- **源码**：`app/comparison/repository.py:67`
- **签名**：`def _dir_for(self, comparison_id: str) -> Path`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收SDK 或 MCP 运行升级比较结果的 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个经过边界校验的文件或目录路径。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `comparison_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`Path`
- **语义**：返回解析后的文件或目录路径对象。

**伪代码**

```text
如果“调用 `fullmatch` 完成该函数的一项辅助处理”后未得到肯定结果，就拒绝继续处理并抛出 `ComparisonNotFoundError`，向调用方报告输入或运行失败。
返回当前计算得到的结果。
```

#### `FileComparisonRepository._cleanup_staging`

- **源码**：`app/comparison/repository.py:72`
- **签名**：`def _cleanup_staging(self) -> None`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，只清理由本 Repository 创建、且超过 TTL 的直属 staging 目录。该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `time` 完成该函数的一项辅助处理，并把结果记为 当前时间。
遍历辅助操作产生的可迭代结果（枚举暂存工作区根目录下符合范围的文件系统项），每次把当前项记为子级目录或子领域对象：
    如果“检查子级目录或子领域对象的文件系统属性”后得到肯定结果 或 “检查对象名称是否满足文本匹配条件”后未得到肯定结果，就跳过本轮剩余处理，直接进入下一轮。
    先尝试完成以下处理：
        计算组合或计算已有值，并保存为 当前处理结果。
    如果出现 `FileNotFoundError`：
        跳过本轮剩余处理，直接进入下一轮。
    如果当前处理结果不小于当前处理结果 且 “检查子级目录或子领域对象的文件系统属性”后得到肯定结果，就调用 `rmtree` 完成该函数的一项辅助处理。
```

#### `FileComparisonRepository._read_report_path`

- **源码**：`app/comparison/repository.py:86`
- **签名**：`def _read_report_path(self, path: Path) -> ComparisonReport`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收文件或目录路径，用于读取并整理论文、源码或运行产物，把原始输入转换成带位置和身份信息的结构化证据，最终标注为 `ComparisonReport` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`ComparisonReport`
- **语义**：返回 `ComparisonReport` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果“检查文件或目录路径的文件系统属性”后得到肯定结果 或 “检查文件或目录路径的文件系统属性”后未得到肯定结果，就拒绝继续处理并抛出 `ComparisonNotFoundError`，向调用方报告输入或运行失败。
读取前一步操作返回对象的当前处理结果，并保存为 对象大小。
如果对象大小大于最大MCP 评测或运行报告的字节内容，就拒绝继续处理并抛出 `ComparisonLimitExceededError`，向调用方报告输入或运行失败。
读取文件或目录路径中的文件内容，并把结果记为 原始内容。
如果原始内容 的长度不等于对象大小 或 原始内容 的长度大于最大MCP 评测或运行报告的字节内容，就拒绝继续处理并抛出 `ComparisonIntegrityError`，向调用方报告输入或运行失败。
先尝试完成以下处理：
    调用 `model_validate_json` 完成该函数的一项辅助处理，并把结果记为 MCP 评测或运行报告。
如果出现 `(ValidationError, json.JSONDecodeError)`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `ComparisonIntegrityError`，向调用方报告输入或运行失败。
调用 `validate_report_identity` 校验当前输入或状态；返回MCP 评测或运行报告的当前值。
```

#### `FileComparisonRepository._durable_write`

- **源码**：`app/comparison/repository.py:103`
- **签名**：`def _durable_write(path: Path, payload: bytes) -> None`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，写入、flush、fsync，避免崩溃后留下已重命名但未落盘的空文件。该函数接收文件或目录路径、结构化请求载荷，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |
| `payload` | `bytes` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `open` 完成该函数的一项辅助处理，并把上下文资源交给当前处理结果”中向终端或输出流写出当前结果/诊断信息；提交当前处理结果中已完成的数据变更；调用 `fsync` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `FileComparisonRepository.get`

- **源码**：`app/comparison/repository.py:111`
- **签名**：`def get(self, comparison_id: str) -> ComparisonReport`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收SDK 或 MCP 运行升级比较结果的 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ComparisonReport` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `comparison_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`ComparisonReport`
- **语义**：返回 `ComparisonReport` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `_dir_for` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
如果“检查当前处理结果的文件系统属性”后得到肯定结果 或 “检查当前处理结果的文件系统属性”后未得到肯定结果，就拒绝继续处理并抛出 `ComparisonNotFoundError`，向调用方报告输入或运行失败。
调用 `_read_report_path` 读取或查询当前阶段需要的数据，并把结果记为 MCP 评测或运行报告。
如果SDK 或 MCP 运行升级比较结果的 ID不等于SDK 或 MCP 运行升级比较结果的 ID，就拒绝继续处理并抛出 `ComparisonIntegrityError`，向调用方报告输入或运行失败。
返回MCP 评测或运行报告的当前值。
```

#### `FileComparisonRepository.save`

- **源码**：`app/comparison/repository.py:120`
- **签名**：`def save(self, report: ComparisonReport) -> ComparisonReport`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，幂等保存；同 ID 不同内容必须报冲突，不能覆盖。该函数接收MCP 评测或运行报告，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ComparisonReport` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `report` | `ComparisonReport` | MCP 评测或运行报告；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`ComparisonReport`
- **语义**：返回 `ComparisonReport` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `validate_report_identity` 校验当前输入或状态；调用 `_dir_for` 完成该函数的一项辅助处理，并把结果记为 待定位的代码对象或业务目标。
如果“检查待定位的代码对象或业务目标的文件系统属性”后得到肯定结果：
    从当前对象读取所需的状态或领域记录，并把结果记为 已有记录。
    如果SDK 或 MCP 运行升级比较结果的 Hash不等于SDK 或 MCP 运行升级比较结果的 Hash，就拒绝继续处理并抛出 `ComparisonConflictError`，向调用方报告输入或运行失败。
    返回已有记录的当前值。
调用 `_cleanup_staging` 完成该函数的一项辅助处理；调用 `canonical_json_bytes` 完成该函数的一项辅助处理，并把结果记为 JSON 数据的字节内容；将结构化内容序列化或编码为可传输表示，并把结果记为 当前处理结果的字节内容。
如果JSON 数据的字节内容 的长度大于最大MCP 评测或运行报告的字节内容，就拒绝继续处理并抛出 `ComparisonLimitExceededError`，向调用方报告输入或运行失败。
如果当前处理结果的字节内容 的长度大于最大MCP 评测或运行报告的字节内容，就拒绝继续处理并抛出 `ComparisonLimitExceededError`，向调用方报告输入或运行失败。
把外部位置解析为文件系统路径对象，并把结果记为 该调用返回的结果。
先尝试完成以下处理：
    调用 `_durable_write` 完成该函数的一项辅助处理；调用 `_durable_write` 完成该函数的一项辅助处理。
    先尝试完成以下处理：
        调用 `rename` 完成该函数的一项辅助处理。
    如果出现 `OSError`：
        如果“检查待定位的代码对象或业务目标的文件系统属性”后未得到肯定结果，就重新抛出当前异常，保持原始失败信息。
        从当前对象读取所需的状态或领域记录，并把结果记为 已有记录。
        如果SDK 或 MCP 运行升级比较结果的 Hash不等于SDK 或 MCP 运行升级比较结果的 Hash，就拒绝继续处理并抛出 `ComparisonConflictError`，向调用方报告输入或运行失败。
        返回已有记录的当前值。
    调用 `open` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
    先尝试完成以下处理：
        调用 `fsync` 完成该函数的一项辅助处理。
    无论成功还是失败，最后都要：
        关闭当前处理结果并释放相关资源。
    从当前对象读取所需的状态或领域记录，并返回处理结果。
无论成功还是失败，最后都要：
    如果“检查当前处理结果的文件系统属性”后得到肯定结果，就调用 `rmtree` 完成该函数的一项辅助处理。
```

#### `FileComparisonRepository.list_for_job`

- **源码**：`app/comparison/repository.py:174`
- **签名**：`def list_for_job(self: 未显式标注, job_id: str, limit: int) -> ComparisonListResponse`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收复现任务 ID、结果数量上限，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。；默认 100 |

**输出**

- **Python 类型**：`ComparisonListResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
如果结果数量上限小于1 或 结果数量上限大于500，就拒绝继续处理并抛出 `ComparisonLimitExceededError`，向调用方报告输入或运行失败。
遍历并筛选输入，将整理后的结果保存为 候选结果集合。
如果候选结果集合 的长度大于上限，就拒绝继续处理并抛出 `ComparisonLimitExceededError`，向调用方报告输入或运行失败。
将 待处理项集合 初始化为空列表，用来收集后续结果。
遍历由候选结果集合组成的集合或迭代器，每次把当前项记为文件或目录路径：
    如果“检查文件或目录路径的文件系统属性”后得到肯定结果 或 “检查文件或目录路径的文件系统属性”后未得到肯定结果，就跳过本轮剩余处理，直接进入下一轮。
    从当前对象读取所需的状态或领域记录，并把结果记为 MCP 评测或运行报告。
    如果复现任务 ID属于{复现任务 ID, 复现任务 ID}，就把新的处理结果追加或合并到待处理项集合。
按稳定规则整理结果顺序；读取待处理项集合中的对应字段，并保存为 选中的候选项；构造并返回 `ComparisonListResponse` 结构化领域对象。
```

### `app/comparison/schemas.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `ComparisonCreateRequest.reject_self_comparison`

- **源码**：`app/comparison/schemas.py:56`
- **签名**：`def reject_self_comparison(self) -> "ComparisonCreateRequest"`
- **作用**：在约束论文复现请求、运行状态、证据和结果结构的契约校验阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `'ComparisonCreateRequest'` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`'ComparisonCreateRequest'`
- **语义**：返回 `'ComparisonCreateRequest'` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果任务的 ID等于任务的 ID，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前对象的当前值。
```

#### `ComparisonReport.validate_summary_counts`

- **源码**：`app/comparison/schemas.py:217`
- **签名**：`def validate_summary_counts(self) -> "ComparisonReport"`
- **作用**：在约束论文复现请求、运行状态、证据和结果结构的契约校验阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `'ComparisonReport'` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`'ComparisonReport'`
- **语义**：返回 `'ComparisonReport'` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果复现任务 ID等于复现任务 ID，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果当前处理结果的数量不等于项目或运行状态变更集合 的长度，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
计算按字段初始化键值映射，并保存为 当前处理结果。
遍历辅助操作产生的可迭代结果（调用 `items` 完成该函数的一项辅助处理），每次把当前项记为多个解包结果：
    调用 `sum` 完成该函数的一项辅助处理，并把结果记为 实际值。
    如果实际值不等于期望值，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
按稳定规则整理结果顺序，并把结果记为 实际集合。
如果辅助操作“按稳定规则整理结果顺序”的结果不等于实际集合，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前对象的当前值。
```

#### `ComparisonListItem.from_report`

- **源码**：`app/comparison/schemas.py:250`
- **签名**：`def from_report(cls, report: ComparisonReport) -> "ComparisonListItem"`
- **作用**：在约束论文复现请求、运行状态、证据和结果结构的契约校验阶段中，该函数接收MCP 评测或运行报告，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `'ComparisonListItem'` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `cls` | `未显式标注` | 当前类对象，用于类级构造或校验。 |
| `report` | `ComparisonReport` | MCP 评测或运行报告；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`'ComparisonListItem'`
- **语义**：返回 `'ComparisonListItem'` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `cls` 完成该函数的一项辅助处理，并返回处理结果。
```

### `app/comparison/service.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `ComparisonJobReader.get`

- **源码**：`app/comparison/service.py:69`
- **签名**：`def get(self, job_id: str) -> JobRecord`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收复现任务 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`JobRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `ComparisonJobReader.get_workspace_manifest`

- **源码**：`app/comparison/service.py:72`
- **签名**：`def get_workspace_manifest(self, manifest_id: str) -> WorkspaceManifest`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收运行或工作区 Manifest的 ID，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `manifest_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`WorkspaceManifest`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `utc_now`

- **源码**：`app/comparison/service.py:76`
- **签名**：`def utc_now() -> str`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `isoformat` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `_sha256_bytes`

- **源码**：`app/comparison/service.py:80`
- **签名**：`def _sha256_bytes(payload: bytes) -> str`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收结构化请求载荷，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `payload` | `bytes` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回输入内容的 SHA-256 身份摘要，用于完整性校验，不是加密后的正文。

**伪代码**

```text
计算输入内容的 SHA-256 身份摘要，并返回处理结果。
```

#### `_safe_dict`

- **源码**：`app/comparison/service.py:84`
- **签名**：`def _safe_dict(value: Any) -> dict[str, Any]`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `Any` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`dict[str, Any]`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
返回按条件选出的结果。
```

#### `_safe_list`

- **源码**：`app/comparison/service.py:88`
- **签名**：`def _safe_list(value: Any) -> list[Any]`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `Any` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`list[Any]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
返回按条件选出的结果。
```

#### `_is_sensitive_option`

- **源码**：`app/comparison/service.py:92`
- **签名**：`def _is_sensitive_option(name: str) -> bool`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收对象名称，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `name` | `str` | 对象名称；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
调用 `replace` 完成该函数的一项辅助处理，并把结果记为 规范化后的文本；检查由凭据集合组成的集合或迭代器中是否存在满足“拆分后的文本或路径片段属于规范化后的文本”的项，并返回处理结果。
```

#### `_redact_token`

- **源码**：`app/comparison/service.py:97`
- **签名**：`def _redact_token(token: str) -> str`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，保留参数结构，但移除绝对路径和 option=value 中的敏感值。该函数接收模型或命令 token，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `token` | `str` | 敏感凭证或其引用；不得写入日志、Prompt 或普通 Artifact。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
如果当前输入内容属于模型或命令 token：
    对模型或命令 token中的文本执行规范化或拆分，并把结果记为 多个解包结果。
    如果“调用 `_is_sensitive_option` 校验当前输入或状态”后得到肯定结果，就返回当前计算得到的结果。
    如果“检查当前字段值是否满足文本匹配条件”后得到肯定结果，就返回当前计算得到的结果。
如果“检查模型或命令 token是否满足文本匹配条件”后得到肯定结果，就返回固定值 `'<absolute-path>'`。
返回模型或命令 token的当前值。
```

#### `build_command_snapshot`

- **源码**：`app/comparison/service.py:111`
- **签名**：`def build_command_snapshot(raw: Any) -> CommandSnapshot`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收原始内容，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `CommandSnapshot` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `raw` | `Any` | 外部读取到的原始文本或进程输出；可能需要截断、规范化或脱敏后才能进入报告。 |

**输出**

- **Python 类型**：`CommandSnapshot`
- **语义**：返回已校验/规范化的命令文本、命令对象或命令集合；不等于已经执行。

**伪代码**

```text
去除辅助操作“调用 `str` 完成该函数的一项辅助处理”的结果的首尾空白，并把规范化后的文本记为 当前命令。
如果当前命令为空或为假，就构造并返回 `CommandSnapshot` 结构化领域对象。
调用 `_safe_dict` 完成该函数的一项辅助处理，并把结果记为 当前处理项；调用 `str` 完成该函数的一项辅助处理，并把结果记为 命令执行工作目录；计算使用固定配置或常量值，并保存为 当前处理结果。
先尝试完成以下处理：
    对当前处理结果中的文本执行规范化或拆分，并把结果记为 模型 token 用量；将 当前处理结果 初始化为空列表，用来收集后续结果；计算使用固定配置或常量值，并保存为 下一项。
    遍历由模型 token 用量组成的集合或迭代器，每次把当前项记为模型或命令 token：
        如果下一项有值或为真，就把新的处理结果追加或合并到当前处理结果；计算使用固定配置或常量值，并保存为 下一项；跳过本轮剩余处理，直接进入下一轮。
        如果“检查模型或命令 token是否满足文本匹配条件”后得到肯定结果 且 当前输入内容不属于模型或命令 token 且 “调用 `_is_sensitive_option` 校验当前输入或状态”后得到肯定结果，就把模型或命令 token追加或合并到当前处理结果；计算使用固定配置或常量值，并保存为 下一项；跳过本轮剩余处理，直接进入下一轮。
        把新的处理结果追加或合并到当前处理结果。
    调用 `join` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
如果出现 `ValueError`：
    计算根据字段和固定文本生成格式化文本，并保存为 当前处理结果；计算使用固定配置或常量值，并保存为 当前处理结果。
构造并返回 `CommandSnapshot` 结构化领域对象。
```

#### `ComparisonService.__init__`

- **源码**：`app/comparison/service.py:151`
- **签名**：`def __init__(self: 未显式标注, evidence_reader: VerifiedRunEvidenceReader, repository: FileComparisonRepository, max_changes: int) -> None（隐式）`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收证据读取器、持久化仓库、最大项目或运行状态变更集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `evidence_reader` | `VerifiedRunEvidenceReader` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |
| `repository` | `FileComparisonRepository` | 持久化或目录访问端口；负责读取、CAS 更新或 Artifact 定位。 |
| `max_changes` | `int` | 名为 `max_changes` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 证据读取器 分别保存到同名实例字段；读取复现任务记录集合，并保存为 复现任务记录集合；把传入的 持久化仓库、最大项目或运行状态变更集合 分别保存到同名实例字段。
```

#### `ComparisonService._paper_sha256`

- **源码**：`app/comparison/service.py:164`
- **签名**：`def _paper_sha256(manifest: WorkspaceManifest) -> str`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收运行或工作区 Manifest，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `manifest` | `WorkspaceManifest` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回输入内容的 SHA-256 身份摘要，用于完整性校验，不是加密后的正文。

**伪代码**

```text
遍历并筛选输入，将整理后的结果保存为 记录条目集合。
如果记录条目集合 的长度不等于1，就拒绝继续处理并抛出 `ComparisonIntegrityError`，向调用方报告输入或运行失败。
返回内容 SHA-256的当前值。
```

#### `ComparisonService._dataset_identities`

- **源码**：`app/comparison/service.py:171`
- **签名**：`def _dataset_identities(manifest: WorkspaceManifest) -> list[DatasetIdentity]`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收运行或工作区 Manifest，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `manifest` | `WorkspaceManifest` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |

**输出**

- **Python 类型**：`list[DatasetIdentity]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
按稳定规则整理结果顺序，并返回处理结果。
```

#### `ComparisonService._error_identities`

- **源码**：`app/comparison/service.py:186`
- **签名**：`def _error_identities(payload: dict[str, Any]) -> list[ErrorIdentity]`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收结构化请求载荷，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `payload` | `dict[str, Any]` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`list[ErrorIdentity]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
调用 `_safe_list` 完成该函数的一项辅助处理，并把结果记为 错误信息集合；将 阶段处理结果 初始化为空列表，用来收集后续结果。
遍历由错误信息集合组成的集合或迭代器，每次把当前项记为原始内容，然后调用 `_safe_dict` 完成该函数的一项辅助处理，并把结果记为 当前处理项；把新的处理结果追加或合并到阶段处理结果。
按稳定规则整理结果顺序，并返回处理结果。
```

#### `ComparisonService._artifact_identities`

- **源码**：`app/comparison/service.py:211`
- **签名**：`def _artifact_identities(views: list[ArtifactView]) -> list[ArtifactIdentity]`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收Artifact 视图集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `views` | `list[ArtifactView]` | Artifact 视图集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`list[ArtifactIdentity]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
将 阶段处理结果 初始化为空列表，用来收集后续结果。
遍历由Artifact 视图集合组成的集合或迭代器，每次把当前项记为当前处理项：
    如果仓库内相对路径属于Artifact集合，就跳过本轮剩余处理，直接进入下一轮。
    构造 `PurePosixPath` 结构化领域对象，并把结果记为 文件或目录路径。
    如果“调用 `is_absolute` 校验当前输入或状态”后得到肯定结果 或 当前输入内容属于拆分后的文本或路径片段集合，就拒绝继续处理并抛出 `ComparisonIntegrityError`，向调用方报告输入或运行失败。
    把新的处理结果追加或合并到阶段处理结果。
按稳定规则整理结果顺序，并返回处理结果。
```

#### `ComparisonService._snapshot`

- **源码**：`app/comparison/service.py:233`
- **签名**：`def _snapshot(self, job_id: str) -> RunSnapshot`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收复现任务 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `RunSnapshot` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`RunSnapshot`
- **语义**：返回 `RunSnapshot` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
先尝试完成以下处理：
    调用 `read` 完成该函数的一项辅助处理，并把结果记为 可追溯证据记录。
如果出现 `RunEvidenceNotFoundError`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `ComparisonNotFoundError`，向调用方报告输入或运行失败。
如果出现 `RunEvidenceConflictError`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `ComparisonConflictError`，向调用方报告输入或运行失败。
如果出现 `RunEvidenceIntegrityError`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `ComparisonIntegrityError`，向调用方报告输入或运行失败。
如果出现 `RunEvidenceLimitExceededError`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `ComparisonLimitExceededError`，向调用方报告输入或运行失败。
读取复现任务记录，并保存为 复现任务记录；读取本次复现工作区，并保存为 本次复现工作区；构造临时集合、映射或轻量领域对象，并把结果记为 Artifact 视图集合；读取运行ManifestArtifact，并保存为 运行Manifest视图。
读取运行Manifest，并保存为 运行或工作区 Manifest；调用 `_safe_dict` 完成该函数的一项辅助处理，并把结果记为 执行记录；调用 `_safe_dict` 完成该函数的一项辅助处理，并把结果记为 执行结果；调用 `_safe_dict` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
调用 `_safe_dict` 完成该函数的一项辅助处理，并把结果记为 模型或运行资源用量；调用 `_safe_dict` 完成该函数的一项辅助处理，并把结果记为 MCP Client 配置档案；调用 `_safe_dict` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `_safe_dict` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
调用 `_safe_dict` 完成该函数的一项辅助处理，并把结果记为 文件；构造 `RunSnapshot` 结构化领域对象，并把结果记为 草稿对象；复制、序列化或校验结构化领域对象，并返回处理结果。
```

#### `ComparisonService._job_evidence`

- **源码**：`app/comparison/service.py:317`
- **签名**：`def _job_evidence(snapshot: RunSnapshot, locator: str) -> ComparisonEvidence`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收MCP 能力快照、源码或文档定位信息，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ComparisonEvidence` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `snapshot` | `RunSnapshot` | MCP 能力快照；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `locator` | `str` | 源码或文档定位信息；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`ComparisonEvidence`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
构造并返回 `ComparisonEvidence` 结构化领域对象。
```

#### `ComparisonService._workspace_evidence`

- **源码**：`app/comparison/service.py:327`
- **签名**：`def _workspace_evidence(snapshot: RunSnapshot, locator: str) -> ComparisonEvidence`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收MCP 能力快照、源码或文档定位信息，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ComparisonEvidence` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `snapshot` | `RunSnapshot` | MCP 能力快照；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `locator` | `str` | 源码或文档定位信息；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`ComparisonEvidence`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
构造并返回 `ComparisonEvidence` 结构化领域对象。
```

#### `ComparisonService._manifest_evidence`

- **源码**：`app/comparison/service.py:339`
- **签名**：`def _manifest_evidence(snapshot: RunSnapshot, locator: str) -> ComparisonEvidence`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收MCP 能力快照、源码或文档定位信息，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ComparisonEvidence` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `snapshot` | `RunSnapshot` | MCP 能力快照；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `locator` | `str` | 源码或文档定位信息；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`ComparisonEvidence`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
构造并返回 `ComparisonEvidence` 结构化领域对象。
```

#### `ComparisonService._artifact_evidence`

- **源码**：`app/comparison/service.py:352`
- **签名**：`def _artifact_evidence(snapshot: RunSnapshot, item: ArtifactIdentity) -> ComparisonEvidence`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收MCP 能力快照、当前处理项，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ComparisonEvidence` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `snapshot` | `RunSnapshot` | MCP 能力快照；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `item` | `ArtifactIdentity` | 当前处理项；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`ComparisonEvidence`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
构造并返回 `ComparisonEvidence` 结构化领域对象。
```

#### `ComparisonService._append_change`

- **源码**：`app/comparison/service.py:364`
- **签名**：`def _append_change(self, changes: list[RunChange], change: RunChange) -> None`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收项目或运行状态变更集合、当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `changes` | `list[RunChange]` | 项目或运行状态变更集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `change` | `RunChange` | 名为 `change` 的 `RunChange` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
如果项目或运行状态变更集合 的长度不小于最大项目或运行状态变更集合，就拒绝继续处理并抛出 `ComparisonLimitExceededError`，向调用方报告输入或运行失败。
把当前处理结果追加或合并到项目或运行状态变更集合。
```

#### `ComparisonService._compare_value`

- **源码**：`app/comparison/service.py:369`
- **签名**：`def _compare_value(self: 未显式标注, changes: list[RunChange], category: str, field_path: str, base_value: Any, target_value: Any, importance: str, message: str, base_evidence: ComparisonEvidence, target_evidence: ComparisonEvidence) -> None`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收项目或运行状态变更集合、评测类别、结构化对象字段的路径、值等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `changes` | `list[RunChange]` | 项目或运行状态变更集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `category` | `str` | 评测类别；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `field_path` | `str` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `base_value` | `Any` | 名为 `base_value` 的 `Any` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `target_value` | `Any` | 名为 `target_value` 的 `Any` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `importance` | `str` | 名为 `importance` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `message` | `str` | 对话消息记录或消息文本；角色、顺序和内容 Hash 可能参与证据校验。 |
| `base_evidence` | `ComparisonEvidence` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |
| `target_evidence` | `ComparisonEvidence` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
如果值等于值，就结束当前函数，不返回业务值。
调用 `_append_change` 完成该函数的一项辅助处理。
```

#### `ComparisonService._compare_artifacts`

- **源码**：`app/comparison/service.py:398`
- **签名**：`def _compare_artifacts(self: 未显式标注, changes: list[RunChange], base: RunSnapshot, target: RunSnapshot) -> tuple[int, int, int]`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收项目或运行状态变更集合、当前处理结果、待定位的代码对象或业务目标，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `changes` | `list[RunChange]` | 项目或运行状态变更集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `base` | `RunSnapshot` | 名为 `base` 的 `RunSnapshot` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `target` | `RunSnapshot` | 待定位的代码对象或业务目标；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`tuple[int, int, int]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
遍历并筛选输入，将整理后的结果保存为 当前处理结果；遍历并筛选输入，将整理后的结果保存为 当前处理结果；计算使用固定配置或常量值，并保存为 当前处理结果、当前处理结果、发生变化的内容。
遍历辅助操作产生的可迭代结果（按稳定规则整理结果顺序），每次把当前项记为文件或目录路径：
    从当前处理结果读取所需的状态或领域记录，并把结果记为 关系左侧实体或比较左值；从当前处理结果读取所需的状态或领域记录，并把结果记为 关系右侧实体或比较右值。
    如果关系左侧实体或比较左值为空 且 关系右侧实体或比较右值不为空：
        将新的计算结果累加或合并到当前处理结果；调用 `_append_change` 完成该函数的一项辅助处理。
    否则：
        如果关系右侧实体或比较右值为空 且 关系左侧实体或比较左值不为空：
            将新的计算结果累加或合并到当前处理结果；调用 `_append_change` 完成该函数的一项辅助处理。
        否则：
            如果关系左侧实体或比较左值不为空 且 关系右侧实体或比较右值不为空 且 辅助操作“复制、序列化或校验结构化领域对象”的结果不等于辅助操作“复制、序列化或校验结构化领域对象”的结果，就将新的计算结果累加或合并到发生变化的内容；调用 `_append_change` 完成该函数的一项辅助处理。
返回当前构造的顺序或去重集合。
```

#### `ComparisonService.create`

- **源码**：`app/comparison/service.py:464`
- **签名**：`def create(self, request: ComparisonCreateRequest) -> ComparisonReport`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收业务请求，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ComparisonReport` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `request` | `ComparisonCreateRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`ComparisonReport`
- **语义**：返回 `ComparisonReport` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `_snapshot` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `_snapshot` 完成该函数的一项辅助处理，并把结果记为 待定位的代码对象或业务目标；将 警告集合 初始化为空列表，用来收集后续结果。
如果论文的 SHA-256不等于论文的 SHA-256：
    如果“论文有值或为真”不成立，就拒绝继续处理并抛出 `ComparisonConflictError`，向调用方报告输入或运行失败。
    把新的处理结果追加或合并到警告集合。
将 项目或运行状态变更集合 初始化为空列表，用来收集后续结果；复制、序列化或校验结构化领域对象，并把结果记为 命令；复制、序列化或校验结构化领域对象，并把结果记为 命令；从命令取出并移除最后一项。
从命令取出并移除最后一项；计算初始化顺序集合，并保存为 当前处理结果。
遍历由当前处理结果组成的集合或迭代器，每次把当前项记为多个解包结果，然后读取新构造集合中的指定项，并保存为 证据构造器；调用 `_compare_value` 完成该函数的一项辅助处理。
调用 `_compare_artifacts` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；按稳定规则整理结果顺序；构造 `ComparisonSummary` 结构化领域对象，并把结果记为 阶段摘要；构造 `ComparisonReport` 结构化领域对象，并把结果记为 草稿对象。
调用 `compute_comparison_hash` 计算内容身份、分数或派生结果，并把结果记为 SDK 或 MCP 运行升级比较结果的 Hash；复制、序列化或校验结构化领域对象，并把结果记为 MCP 评测或运行报告；调用 `save` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `ComparisonService.get`

- **源码**：`app/comparison/service.py:556`
- **签名**：`def get(self, comparison_id: str) -> ComparisonReport`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收SDK 或 MCP 运行升级比较结果的 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ComparisonReport` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `comparison_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`ComparisonReport`
- **语义**：返回 `ComparisonReport` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
从持久化仓库读取所需的状态或领域记录，并返回处理结果。
```

#### `ComparisonService.list_for_job`

- **源码**：`app/comparison/service.py:559`
- **签名**：`def list_for_job(self, job_id: str, *, limit: int = 100) -> ComparisonListResponse`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收复现任务 ID、结果数量上限，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。；默认 100 |

**输出**

- **Python 类型**：`ComparisonListResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
从复现任务记录集合读取所需的状态或领域记录；调用 `list_for_job` 读取或查询当前阶段需要的数据，并返回处理结果。
```

### `app/rerun/command_template.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_sha256_text`

- **源码**：`app/rerun/command_template.py:44`
- **签名**：`def _sha256_text(value: str) -> str`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

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

#### `_is_secret_option`

- **源码**：`app/rerun/command_template.py:48`
- **签名**：`def _is_secret_option(option: str) -> bool`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `option` | `str` | 名为 `option` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
调用 `replace` 完成该函数的一项辅助处理，并把结果记为 规范化后的文本；检查由凭据集合组成的集合或迭代器中是否存在满足“拆分后的文本或路径片段属于规范化后的文本”的项，并返回处理结果。
```

#### `_reject_shell_text`

- **源码**：`app/rerun/command_template.py:53`
- **签名**：`def _reject_shell_text(value: str, *, field: str) -> None`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收当前字段值、结构化对象字段，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |
| `field` | `str` | 结构化对象字段；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
如果当前字段值为空或为假 或 当前输入内容属于当前字段值 或 “调用 `search` 完成该函数的一项辅助处理”后得到肯定结果，就拒绝继续处理并抛出 `RerunCommandRejectedError`，向调用方报告输入或运行失败。
```

#### `_pure_absolute`

- **源码**：`app/rerun/command_template.py:60`
- **签名**：`def _pure_absolute(value: str, *, field: str) -> PurePosixPath`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收当前字段值、结构化对象字段，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个经过边界校验的文件或目录路径。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |
| `field` | `str` | 结构化对象字段；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`PurePosixPath`
- **语义**：返回解析后的文件或目录路径对象。

**伪代码**

```text
构造 `PurePosixPath` 结构化领域对象，并把结果记为 文件或目录路径。
如果“调用 `is_absolute` 校验当前输入或状态”后未得到肯定结果 或 当前输入内容属于拆分后的文本或路径片段集合，就拒绝继续处理并抛出 `RerunCommandRejectedError`，向调用方报告输入或运行失败。
返回文件或目录路径的当前值。
```

#### `_relative_under`

- **源码**：`app/rerun/command_template.py:69`
- **签名**：`def _relative_under(value: PurePosixPath, root: PurePosixPath) -> str | None`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收当前字段值、受控扫描根目录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `str | None` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `PurePosixPath` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |
| `root` | `PurePosixPath` | 运行产物或受控工作区的目录路径；用于隔离本次运行生成的文件。 |

**输出**

- **Python 类型**：`str | None`
- **语义**：返回 `str | None` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
先尝试完成以下处理：
    把当前字段值转换为稳定的仓库相对路径表示，并把结果记为 仓库相对路径。
如果出现 `ValueError`：
    返回固定值 `空值`。
把仓库相对路径转换为稳定的仓库相对路径表示，并把结果记为 待处理文本；返回按条件选出的结果。
```

#### `_dataset_root`

- **源码**：`app/rerun/command_template.py:81`
- **签名**：`def _dataset_root(reference: ExternalDataReference) -> PurePosixPath | None`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收论文或源码引用证据，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个经过边界校验的文件或目录路径。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `reference` | `ExternalDataReference` | 论文或源码引用证据；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`PurePosixPath | None`
- **语义**：返回解析后的文件或目录路径对象。

**伪代码**

```text
调用 `urlparse` 完成该函数的一项辅助处理，并把结果记为 解析后的结果。
如果当前处理结果等于'file'：
    如果当前处理结果不属于{'', 'localhost'}，就返回固定值 `空值`。
    调用 `_pure_absolute` 完成该函数的一项辅助处理，并返回处理结果。
如果“当前处理结果有值或为真”不成立 且 “检查MCP 资源或外部研究地址是否满足文本匹配条件”后得到肯定结果，就调用 `_pure_absolute` 完成该函数的一项辅助处理，并返回处理结果。
返回固定值 `空值`。
```

#### `_normalize_option_equals`

- **源码**：`app/rerun/command_template.py:98`
- **签名**：`def _normalize_option_equals(argv: list[str]) -> list[str]`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收实验程序命令行参数序列，用于读取并整理论文、源码或运行产物，把原始输入转换成带位置和身份信息的结构化证据，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `argv` | `list[str]` | 实验程序命令行参数序列；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`list[str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
将 规范化后的文本 初始化为空列表，用来收集后续结果。
遍历由实验程序命令行参数序列组成的集合或迭代器，每次把当前项记为模型或命令 token：
    如果“检查模型或命令 token是否满足文本匹配条件”后得到肯定结果 且 当前输入内容属于模型或命令 token：
        对模型或命令 token中的文本执行规范化或拆分，并把结果记为 多个解包结果。
        如果“调用 `fullmatch` 完成该函数的一项辅助处理”后未得到肯定结果，就拒绝继续处理并抛出 `RerunCommandRejectedError`，向调用方报告输入或运行失败。
        把新的处理结果追加或合并到规范化后的文本。
    否则：
        把模型或命令 token追加或合并到规范化后的文本。
返回规范化后的文本的当前值。
```

#### `_parse_parent_argv`

- **源码**：`app/rerun/command_template.py:113`
- **签名**：`def _parse_parent_argv(command: str, max_command_chars: int, max_argv_items: int) -> list[str]`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收当前命令、最大命令字符数、最大当前处理结果，用于读取并整理论文、源码或运行产物，把原始输入转换成带位置和身份信息的结构化证据，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `command` | `str` | 待展示、校验或执行的命令文本/结构化命令；仅进入 Executor 路径后才可能产生执行副作用。 |
| `max_command_chars` | `int` | 待展示、校验或执行的命令文本/结构化命令；仅进入 Executor 路径后才可能产生执行副作用。 |
| `max_argv_items` | `int` | 名为 `max_argv_items` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`list[str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
如果当前命令 的长度大于最大命令字符数，就拒绝继续处理并抛出 `RerunCommandRejectedError`，向调用方报告输入或运行失败。
调用 `_reject_shell_text` 完成该函数的一项辅助处理。
先尝试完成以下处理：
    对当前处理结果中的文本执行规范化或拆分，并把结果记为 实验程序命令行参数序列。
如果出现 `ValueError`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `RerunCommandRejectedError`，向调用方报告输入或运行失败。
如果实验程序命令行参数序列为空或为假 或 实验程序命令行参数序列 的长度大于最大当前处理结果，就拒绝继续处理并抛出 `RerunCommandRejectedError`，向调用方报告输入或运行失败。
如果“调用 `match` 完成该函数的一项辅助处理”后得到肯定结果，就拒绝继续处理并抛出 `RerunCommandRejectedError`，向调用方报告输入或运行失败。
调用 `_normalize_option_equals` 解析、规范化或转换当前输入，并把结果记为 规范化后的文本。
遍历由规范化后的文本组成的集合或迭代器，每次把当前项记为模型或命令 token：
    如果“调用 `fullmatch` 完成该函数的一项辅助处理”后得到肯定结果 且 “调用 `_is_secret_option` 校验当前输入或状态”后得到肯定结果，就拒绝继续处理并抛出 `RerunCommandRejectedError`，向调用方报告输入或运行失败。
返回规范化后的文本的当前值。
```

#### `_find_edit_span`

- **源码**：`app/rerun/command_template.py:145`
- **签名**：`def _find_edit_span(argv: list[str], edit: RerunArgumentEdit) -> tuple[int, int]`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收实验程序命令行参数序列、编辑文本，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `argv` | `list[str]` | 实验程序命令行参数序列；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `edit` | `RerunArgumentEdit` | 编辑文本；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`tuple[int, int]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
遍历并筛选输入，将整理后的结果保存为 当前处理结果。
如果当前处理结果 的长度不等于1，就拒绝继续处理并抛出 `RerunCommandRejectedError`，向调用方报告输入或运行失败。
读取当前处理结果中的对应字段，并保存为 读取起点；计算组合或计算已有值，并保存为 下一项的索引。
如果期望值为空：
    如果下一项的索引小于实验程序命令行参数序列 的长度 且 “检查实验程序命令行参数序列中的对应字段是否满足文本匹配条件”后未得到肯定结果，就拒绝继续处理并抛出 `RerunCommandRejectedError`，向调用方报告输入或运行失败。
    返回当前构造的顺序或去重集合。
如果下一项的索引不小于实验程序命令行参数序列 的长度 或 实验程序命令行参数序列中的对应字段不等于期望值，就拒绝继续处理并抛出 `RerunConflictError`，向调用方报告输入或运行失败。
返回当前构造的顺序或去重集合。
```

#### `_validate_new_value`

- **源码**：`app/rerun/command_template.py:176`
- **签名**：`def _validate_new_value(value: str) -> None`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收当前字段值，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_reject_shell_text` 完成该函数的一项辅助处理。
如果“检查当前字段值是否满足文本匹配条件”后得到肯定结果，就拒绝继续处理并抛出 `RerunCommandRejectedError`，向调用方报告输入或运行失败。
如果“检查当前字段值是否满足文本匹配条件”后得到肯定结果，就拒绝继续处理并抛出 `RerunCommandRejectedError`，向调用方报告输入或运行失败。
```

#### `apply_argument_edits`

- **源码**：`app/rerun/command_template.py:188`
- **签名**：`def apply_argument_edits(argv: list[str], edits: list[RerunArgumentEdit]) -> list[str]`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收实验程序命令行参数序列、命令修改项集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `argv` | `list[str]` | 实验程序命令行参数序列；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `edits` | `list[RerunArgumentEdit]` | 命令修改项集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`list[str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
构造临时集合、映射或轻量领域对象，并把结果记为 阶段处理结果；将 当前处理结果 初始化为空去重集合，用来收集后续结果。
遍历由命令修改项集合组成的集合或迭代器，每次把当前项记为编辑文本：
    如果当前处理结果属于当前处理结果，就拒绝继续处理并抛出 `RerunCommandRejectedError`，向调用方报告输入或运行失败。
    把当前处理结果追加或合并到当前处理结果。
    如果“调用 `_is_secret_option` 校验当前输入或状态”后得到肯定结果，就拒绝继续处理并抛出 `RerunCommandRejectedError`，向调用方报告输入或运行失败。
    调用 `_find_edit_span` 读取或查询当前阶段需要的数据，并把结果记为 多个解包结果。
    如果MCP 业务操作名称等于'remove'，就将 阶段处理结果中的对应字段 初始化为空列表，用来收集后续结果；否则断言当前字段值不为空；不满足就终止当前测试或流程；调用 `_validate_new_value` 校验当前输入或状态；计算初始化顺序集合，并保存为 阶段处理结果中的对应字段。
返回阶段处理结果的当前值。
```

#### `_template_arg`

- **源码**：`app/rerun/command_template.py:212`
- **签名**：`def _template_arg(token: str, repo_root: PurePosixPath, run_root: PurePosixPath, datasets: list[ExternalDataReference]) -> RerunTemplateArg`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收模型或命令 token、仓库根目录、运行产物根目录、当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `RerunTemplateArg` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `token` | `str` | 敏感凭证或其引用；不得写入日志、Prompt 或普通 Artifact。 |
| `repo_root` | `PurePosixPath` | 代码仓库根目录路径；用于限制文件扫描、相对路径计算和后续工具访问范围。 |
| `run_root` | `PurePosixPath` | 运行产物根目录；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `datasets` | `list[ExternalDataReference]` | `list[ExternalDataReference]` 元素集合；元素代表的业务对象由参数名 `datasets` 和调用位置确定。 |

**输出**

- **Python 类型**：`RerunTemplateArg`
- **语义**：返回 `RerunTemplateArg` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果“检查模型或命令 token是否满足文本匹配条件”后未得到肯定结果，就构造并返回 `RerunTemplateArg` 结构化领域对象。
调用 `_pure_absolute` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `_relative_under` 完成该函数的一项辅助处理，并把结果记为 仓库相对。
如果仓库相对不为空，就构造并返回 `RerunTemplateArg` 结构化领域对象。
调用 `_relative_under` 完成该函数的一项辅助处理，并把结果记为 运行相对。
如果运行相对不为空，就构造并返回 `RerunTemplateArg` 结构化领域对象。
将 当前处理结果 初始化为空列表，用来收集后续结果。
遍历由当前处理结果组成的集合或迭代器，每次把当前项记为论文或源码引用证据：
    调用 `_dataset_root` 完成该函数的一项辅助处理，并把结果记为 受控扫描根目录。
    如果受控扫描根目录为空，就跳过本轮剩余处理，直接进入下一轮。
    调用 `_relative_under` 完成该函数的一项辅助处理，并把结果记为 仓库相对路径。
    如果仓库相对路径不为空，就把新的处理结果追加或合并到当前处理结果。
如果当前处理结果 的长度等于1，就读取当前处理结果中的对应字段，并保存为 多个解包结果；构造并返回 `RerunTemplateArg` 结构化领域对象。
如果当前处理结果 的长度大于1，就拒绝继续处理并抛出 `RerunCommandRejectedError`，向调用方报告输入或运行失败。
拒绝继续处理并抛出 `RerunCommandRejectedError`，向调用方报告输入或运行失败。
```

#### `build_command_template`

- **源码**：`app/rerun/command_template.py:261`
- **签名**：`def build_command_template(selected_action: Any, run_manifest: dict, workspace: WorkspaceManifest, edits: list[RerunArgumentEdit], max_command_chars: int, max_argv_items: int) -> RerunCommandTemplate`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收当前处理结果、运行Manifest、本次复现工作区、命令修改项集合等输入，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `RerunCommandTemplate` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `selected_action` | `Any` | 结构化待执行动作；包含命令、工作目录、风险和内容身份，但尚不表示已执行。 |
| `run_manifest` | `dict` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |
| `workspace` | `WorkspaceManifest` | 本次复现工作区；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `edits` | `list[RerunArgumentEdit]` | 命令修改项集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `max_command_chars` | `int` | 待展示、校验或执行的命令文本/结构化命令；仅进入 Executor 路径后才可能产生执行副作用。 |
| `max_argv_items` | `int` | 名为 `max_argv_items` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`RerunCommandTemplate`
- **语义**：返回已校验/规范化的命令文本、命令对象或命令集合；不等于已经执行。

**伪代码**

```text
如果“计算数量、边界或类型判断结果”后未得到肯定结果，就拒绝继续处理并抛出 `RerunCommandRejectedError`，向调用方报告输入或运行失败。
去除辅助操作“调用 `str` 完成该函数的一项辅助处理”的结果的首尾空白，并把规范化后的文本记为 当前命令；去除辅助操作“调用 `str` 完成该函数的一项辅助处理”的结果的首尾空白，并把规范化后的文本记为 命令执行工作目录；去除辅助操作“调用 `str` 完成该函数的一项辅助处理”的结果的首尾空白，并把规范化后的文本记为 代码仓库根目录；去除辅助操作“调用 `str` 完成该函数的一项辅助处理”的结果的首尾空白，并把规范化后的文本记为 本次复现运行目录。
如果当前命令为空或为假 或 命令执行工作目录为空或为假 或 代码仓库根目录为空或为假 或 本次复现运行目录为空或为假，就拒绝继续处理并抛出 `RerunCommandRejectedError`，向调用方报告输入或运行失败。
调用 `_pure_absolute` 完成该函数的一项辅助处理，并把结果记为 仓库根目录；调用 `_pure_absolute` 完成该函数的一项辅助处理，并把结果记为 运行产物根目录；调用 `_pure_absolute` 完成该函数的一项辅助处理，并把结果记为 命令执行工作目录的路径；调用 `_relative_under` 完成该函数的一项辅助处理，并把结果记为 相对。
如果相对为空，就拒绝继续处理并抛出 `RerunCommandRejectedError`，向调用方报告输入或运行失败。
调用 `_parse_parent_argv` 解析、规范化或转换当前输入，并把结果记为 实验程序命令行参数序列；调用 `apply_argument_edits` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
如果当前处理结果为空或为假，就拒绝继续处理并抛出 `RerunCommandRejectedError`，向调用方报告输入或运行失败。
遍历并筛选输入，将整理后的结果保存为 当前处理结果；构造 `RerunCommandTemplate` 结构化领域对象，并把结果记为 草稿对象；复制、序列化或校验结构化领域对象，并返回处理结果。
```

#### `_resolve_inside`

- **源码**：`app/rerun/command_template.py:324`
- **签名**：`def _resolve_inside(root: Path, relative_path: str) -> Path`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收受控扫描根目录、仓库内相对路径，用于把论文中的方法、模块或实验意图与仓库中的可验证对象建立稳定关联，并保留匹配依据，最终一个经过边界校验的文件或目录路径。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `root` | `Path` | 运行产物或受控工作区的目录路径；用于隔离本次运行生成的文件。 |
| `relative_path` | `str` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`Path`
- **语义**：返回解析后的文件或目录路径对象。

**伪代码**

```text
如果仓库内相对路径等于'.'，就将受控扫描根目录规范化为受控的绝对路径，并返回处理结果。
构造 `PurePosixPath` 结构化领域对象，并把结果记为 该调用返回的结果。
如果“调用 `is_absolute` 校验当前输入或状态”后得到肯定结果 或 当前输入内容属于拆分后的文本或路径片段集合，就拒绝继续处理并抛出 `RerunIntegrityError`，向调用方报告输入或运行失败。
将当前输入内容规范化为受控的绝对路径，并把结果记为 待定位的代码对象或业务目标；将受控扫描根目录规范化为受控的绝对路径，并把结果记为 受控扫描根目录。
如果待定位的代码对象或业务目标不等于受控扫描根目录 且 受控扫描根目录不属于当前处理结果，就拒绝继续处理并抛出 `RerunIntegrityError`，向调用方报告输入或运行失败。
返回待定位的代码对象或业务目标的当前值。
```

#### `resolve_command_template`

- **源码**：`app/rerun/command_template.py:337`
- **签名**：`def resolve_command_template(template: RerunCommandTemplate, repo_path: str, run_dir: str, dataset_mounts: dict[str, str]) -> dict[str, str]`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收当前处理结果、代码仓库根目录、本次复现运行目录、当前处理结果，用于把论文中的方法、模块或实验意图与仓库中的可验证对象建立稳定关联，并保留匹配依据，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `template` | `RerunCommandTemplate` | 名为 `template` 的 `RerunCommandTemplate` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `repo_path` | `str` | 代码仓库根目录路径；用于限制文件扫描、相对路径计算和后续工具访问范围。 |
| `run_dir` | `str` | 运行产物或受控工作区的目录路径；用于隔离本次运行生成的文件。 |
| `dataset_mounts` | `dict[str, str]` | 名为 `dataset_mounts` 的键值映射；键和值分别承载的业务字段由读取/写入分支确定。 |

**输出**

- **Python 类型**：`dict[str, str]`
- **语义**：返回已校验/规范化的命令文本、命令对象或命令集合；不等于已经执行。

**伪代码**

```text
调用 `validate_command_template_hash` 校验当前输入或状态；将辅助操作“把外部位置解析为文件系统路径对象”的结果规范化为受控的绝对路径，并把结果记为 仓库根目录；将辅助操作“把外部位置解析为文件系统路径对象”的结果规范化为受控的绝对路径，并把结果记为 运行根目录；将 实验程序命令行参数序列 初始化为空列表，用来收集后续结果。
遍历当前可迭代输入，每次把当前项记为当前处理项：
    如果业务类别等于'literal'：
        断言当前字段值不为空；不满足就终止当前测试或流程；把当前字段值追加或合并到实验程序命令行参数序列。
    否则：
        如果业务类别等于'repo_path'：
            断言仓库内相对路径不为空；不满足就终止当前测试或流程；把新的处理结果追加或合并到实验程序命令行参数序列。
        否则：
            如果业务类别等于'run_path'：
                断言仓库内相对路径不为空；不满足就终止当前测试或流程；把新的处理结果追加或合并到实验程序命令行参数序列。
            否则：
                断言当前处理结果不为空；不满足就终止当前测试或流程；断言仓库内相对路径不为空；不满足就终止当前测试或流程；从当前处理结果读取所需的状态或领域记录，并把结果记为 该调用返回的结果。
                如果当前处理结果为空或为假，就拒绝继续处理并抛出 `RerunIntegrityError`，向调用方报告输入或运行失败。
                将辅助操作“把外部位置解析为文件系统路径对象”的结果规范化为受控的绝对路径，并把结果记为 根目录；把新的处理结果追加或合并到实验程序命令行参数序列。
调用 `_resolve_inside` 解析、规范化或转换当前输入，并把结果记为 命令执行工作目录；返回包含 `command`、`cwd`、`source`、`risk_level`、`reason` 字段的结构化映射。
```

### `app/rerun/factory.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `build_rerun_service`

- **源码**：`app/rerun/factory.py:15`
- **签名**：`def build_rerun_service(job_service: JobService, artifact_catalog: ArtifactCatalog, comparison_service: 未显式标注) -> RerunService`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收任务、Artifact、当前处理结果，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `RerunService` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `job_service` | `JobService` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |
| `artifact_catalog` | `ArtifactCatalog` | 名为 `artifact_catalog` 的 `ArtifactCatalog` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `comparison_service` | `未显式标注` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。；默认 空值 |

**输出**

- **Python 类型**：`RerunService`
- **语义**：返回 `RerunService` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `build_run_evidence_reader` 组装当前阶段需要的领域对象，并把结果记为 证据读取器；计算根据条件从两个候选结果中选择一个，并保存为 当前处理结果；构造并返回 `RerunService` 结构化领域对象。
```

### `app/rerun/identity.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `canonical_json`

- **源码**：`app/rerun/identity.py:17`
- **签名**：`def canonical_json(value: Any) -> str`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

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

#### `sha256_value`

- **源码**：`app/rerun/identity.py:28`
- **签名**：`def sha256_value(value: Any) -> str`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

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

#### `command_template_hash`

- **源码**：`app/rerun/identity.py:34`
- **签名**：`def command_template_hash(template: RerunCommandTemplate) -> str`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `template` | `RerunCommandTemplate` | 名为 `template` 的 `RerunCommandTemplate` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回内容身份摘要，通常为 SHA-256 十六进制字符串。

**伪代码**

```text
复制、序列化或校验结构化领域对象，并把结果记为 结构化请求载荷；从结构化请求载荷取出并移除最后一项；调用 `sha256_value` 计算内容身份、分数或派生结果，并返回处理结果。
```

#### `validate_command_template_hash`

- **源码**：`app/rerun/identity.py:40`
- **签名**：`def validate_command_template_hash(template: RerunCommandTemplate) -> None`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收当前处理结果，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `template` | `RerunCommandTemplate` | 名为 `template` 的 `RerunCommandTemplate` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `command_template_hash` 完成该函数的一项辅助处理，并把结果记为 实际值。
如果实际值不等于当前处理结果的 Hash，就拒绝继续处理并抛出 `RerunIntegrityError`，向调用方报告输入或运行失败。
```

#### `proposal_hash`

- **源码**：`app/rerun/identity.py:50`
- **签名**：`def proposal_hash(proposal: RerunProposal) -> str`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收修复或重跑提案，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `proposal` | `RerunProposal` | 修复或重跑提案；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回内容身份摘要，通常为 SHA-256 十六进制字符串。

**伪代码**

```text
复制、序列化或校验结构化领域对象，并把结果记为 结构化请求载荷；从结构化请求载荷取出并移除最后一项；从结构化请求载荷取出并移除最后一项；调用 `sha256_value` 计算内容身份、分数或派生结果，并返回处理结果。
```

#### `proposal_id_for_hash`

- **源码**：`app/rerun/identity.py:57`
- **签名**：`def proposal_id_for_hash(value: str) -> str`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回内容身份摘要，通常为 SHA-256 十六进制字符串。

**伪代码**

```text
返回当前计算得到的结果。
```

#### `validate_proposal_hash`

- **源码**：`app/rerun/identity.py:61`
- **签名**：`def validate_proposal_hash(proposal: RerunProposal) -> None`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收修复或重跑提案，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `proposal` | `RerunProposal` | 修复或重跑提案；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `validate_command_template_hash` 校验当前输入或状态；调用 `proposal_hash` 完成该函数的一项辅助处理，并把结果记为 实际值。
如果实际值不等于修复或重跑提案的 Hash，就拒绝继续处理并抛出 `RerunIntegrityError`，向调用方报告输入或运行失败。
如果修复或重跑提案的 ID不等于辅助操作“调用 `proposal_id_for_hash` 完成该函数的一项辅助处理”的结果，就拒绝继续处理并抛出 `RerunIntegrityError`，向调用方报告输入或运行失败。
```

### `app/rerun/repository.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `utc_now`

- **源码**：`app/rerun/repository.py:22`
- **签名**：`def utc_now() -> str`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `isoformat` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `_is_expired`

- **源码**：`app/rerun/repository.py:26`
- **签名**：`def _is_expired(proposal: RerunProposal, now: str) -> bool`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收修复或重跑提案、当前时间，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `proposal` | `RerunProposal` | 修复或重跑提案；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `now` | `str` | 时间值或可注入时钟，用于排序、过期、租约或可重复测试。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
返回比较判断结果。
```

#### `SqliteRerunRepository.__init__`

- **源码**：`app/rerun/repository.py:31`
- **签名**：`def __init__(self: 未显式标注, path: Path, clock: Callable[[], str]) -> None`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收文件或目录路径、统一时间来源，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |
| `clock` | `Callable[[], str]` | 时间值或可注入时钟，用于排序、过期、租约或可重复测试。；默认 utc_now |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 文件或目录路径、统一时间来源 分别保存到同名实例字段。
```

#### `SqliteRerunRepository._connect`

- **源码**：`app/rerun/repository.py:40`
- **签名**：`def _connect(self) -> sqlite3.Connection`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于在固定 MCP Policy、Schema Pin、调用预算和只读职责边界内连接或调用外部能力，并把返回内容转换为可追溯的复现证据，最终标注为 `sqlite3.Connection` 的领域结果。

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

#### `SqliteRerunRepository.initialize`

- **源码**：`app/rerun/repository.py:51`
- **签名**：`def initialize(self) -> None`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
创建父级目录或父领域对象对应的目录；调用 `_connect` 完成该函数的一项辅助处理，并把结果记为 数据库连接。
先尝试完成以下处理：
    通过数据库连接执行数据查询或命令；通过数据库连接执行数据查询或命令；通过数据库连接执行数据查询或命令。
无论成功还是失败，最后都要：
    关闭数据库连接并释放相关资源。
```

#### `SqliteRerunRepository._record`

- **源码**：`app/rerun/repository.py:88`
- **签名**：`def _record(row: sqlite3.Row) -> RerunProposalRecord`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收数据库记录行，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `row` | `sqlite3.Row` | 数据库记录行；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`RerunProposalRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
调用 `model_validate_json` 完成该函数的一项辅助处理，并把结果记为 修复或重跑提案；调用 `validate_proposal_hash` 校验当前输入或状态。
如果修复或重跑提案的 ID不等于数据库记录行中的对应字段，就拒绝继续处理并抛出 `RerunIntegrityError`，向调用方报告输入或运行失败。
如果修复或重跑提案的 Hash不等于数据库记录行中的对应字段，就拒绝继续处理并抛出 `RerunIntegrityError`，向调用方报告输入或运行失败。
构造并返回 `RerunProposalRecord` 结构化领域对象。
```

#### `SqliteRerunRepository._row_by_id`

- **源码**：`app/rerun/repository.py:106`
- **签名**：`def _row_by_id(connection: sqlite3.Connection, proposal_id: str) -> sqlite3.Row`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收数据库连接、修复或重跑提案的 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `sqlite3.Row` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `connection` | `sqlite3.Connection` | 数据库连接；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `proposal_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`sqlite3.Row`
- **语义**：返回稳定业务标识符，用于后续查询、关联或幂等绑定；它不是路径或内容 Hash。

**伪代码**

```text
调用 `fetchone` 完成该函数的一项辅助处理，并把结果记为 数据库记录行。
如果数据库记录行为空，就拒绝继续处理并抛出 `RerunNotFoundError`，向调用方报告输入或运行失败。
返回数据库记录行的当前值。
```

#### `SqliteRerunRepository._expire_if_needed`

- **源码**：`app/rerun/repository.py:120`
- **签名**：`def _expire_if_needed(self: 未显式标注, connection: sqlite3.Connection, row: sqlite3.Row) -> sqlite3.Row`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收数据库连接、数据库记录行，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `sqlite3.Row` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `connection` | `sqlite3.Connection` | 数据库连接；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `row` | `sqlite3.Row` | 数据库记录行；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`sqlite3.Row`
- **语义**：返回 `sqlite3.Row` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `_record` 完成该函数的一项辅助处理，并把结果记为 领域记录。
如果当前状态等于'pending' 且 “调用 `_is_expired` 校验当前输入或状态”后得到肯定结果，就通过数据库连接执行数据查询或命令；调用 `_row_by_id` 完成该函数的一项辅助处理，并返回处理结果。
返回数据库记录行的当前值。
```

#### `SqliteRerunRepository.create`

- **源码**：`app/rerun/repository.py:144`
- **签名**：`def create(self: 未显式标注, proposal: RerunProposal, idempotency_key: str, request_hash: str) -> tuple[RerunProposalRecord, bool]`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收修复或重跑提案、请求幂等键、请求内容 Hash，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `proposal` | `RerunProposal` | 修复或重跑提案；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `idempotency_key` | `str` | 调用方提供的幂等键；重复请求应复用同一结果，而不是再次产生副作用。 |
| `request_hash` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |

**输出**

- **Python 类型**：`tuple[RerunProposalRecord, bool]`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
调用 `validate_proposal_hash` 校验当前输入或状态；调用 `_connect` 完成该函数的一项辅助处理，并把结果记为 数据库连接。
先尝试完成以下处理：
    通过数据库连接执行数据查询或命令；调用 `fetchone` 完成该函数的一项辅助处理，并把结果记为 已有记录。
    如果已有记录不为空：
        如果已有记录中的对应字段不等于请求内容 Hash，就拒绝继续处理并抛出 `RerunConflictError`，向调用方报告输入或运行失败。
        通过数据库连接执行数据查询或命令；返回当前构造的顺序或去重集合。
    读取当前时间，作为状态变更的统一时间戳，并把结果记为 当前时间；通过数据库连接执行数据查询或命令；调用 `_row_by_id` 完成该函数的一项辅助处理，并把结果记为 数据库记录行；通过数据库连接执行数据查询或命令。
    返回当前构造的顺序或去重集合。
如果出现 `Exception`：
    如果当前处理结果有值或为真，就通过数据库连接执行数据查询或命令。
    重新抛出当前异常，保持原始失败信息。
无论成功还是失败，最后都要：
    关闭数据库连接并释放相关资源。
```

#### `SqliteRerunRepository.get`

- **源码**：`app/rerun/repository.py:201`
- **签名**：`def get(self, proposal_id: str) -> RerunProposalRecord`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收修复或重跑提案的 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `proposal_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`RerunProposalRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
调用 `_connect` 完成该函数的一项辅助处理，并把结果记为 数据库连接。
先尝试完成以下处理：
    通过数据库连接执行数据查询或命令；调用 `_row_by_id` 完成该函数的一项辅助处理，并把结果记为 数据库记录行；调用 `_expire_if_needed` 完成该函数的一项辅助处理，并把结果记为 数据库记录行；通过数据库连接执行数据查询或命令。
    调用 `_record` 完成该函数的一项辅助处理，并返回处理结果。
如果出现 `Exception`：
    如果当前处理结果有值或为真，就通过数据库连接执行数据查询或命令。
    重新抛出当前异常，保持原始失败信息。
无论成功还是失败，最后都要：
    关闭数据库连接并释放相关资源。
```

#### `SqliteRerunRepository.find_create_replay`

- **源码**：`app/rerun/repository.py:216`
- **签名**：`def find_create_replay(self: 未显式标注, idempotency_key: str, request_hash: str) -> RerunProposalRecord | None`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收请求幂等键、请求内容 Hash，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `idempotency_key` | `str` | 调用方提供的幂等键；重复请求应复用同一结果，而不是再次产生副作用。 |
| `request_hash` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |

**输出**

- **Python 类型**：`RerunProposalRecord | None`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
调用 `_connect` 完成该函数的一项辅助处理，并把结果记为 数据库连接。
先尝试完成以下处理：
    调用 `fetchone` 完成该函数的一项辅助处理，并把结果记为 数据库记录行。
    如果数据库记录行为空，就返回固定值 `空值`。
    如果数据库记录行中的对应字段不等于请求内容 Hash，就拒绝继续处理并抛出 `RerunConflictError`，向调用方报告输入或运行失败。
    调用 `str` 完成该函数的一项辅助处理，并把结果记为 修复或重跑提案的 ID。
无论成功还是失败，最后都要：
    关闭数据库连接并释放相关资源。
从当前对象读取所需的状态或领域记录，并返回处理结果。
```

#### `SqliteRerunRepository.begin_submission`

- **源码**：`app/rerun/repository.py:243`
- **签名**：`def begin_submission(self: 未显式标注, proposal_id: str, expected_hash: str, expected_version: int, submit_idempotency_key: str) -> RerunProposalRecord`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收修复或重跑提案的 ID、调用方看到的旧内容 Hash、调用方看到的旧版本号、键，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `proposal_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `expected_hash` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |
| `expected_version` | `int` | 调用方观察到的旧身份，用于 stale/CAS 校验，防止覆盖并发更新。 |
| `submit_idempotency_key` | `str` | 名为 `submit_idempotency_key` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`RerunProposalRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
调用 `_connect` 完成该函数的一项辅助处理，并把结果记为 数据库连接。
先尝试完成以下处理：
    通过数据库连接执行数据查询或命令；调用 `_expire_if_needed` 完成该函数的一项辅助处理，并把结果记为 数据库记录行；调用 `_record` 完成该函数的一项辅助处理，并把结果记为 领域记录。
    如果修复或重跑提案的 Hash不等于调用方看到的旧内容 Hash，就拒绝继续处理并抛出 `RerunConflictError`，向调用方报告输入或运行失败。
    如果当前状态等于'expired'，就拒绝继续处理并抛出 `RerunExpiredError`，向调用方报告输入或运行失败。
    如果当前状态等于'submitted'，就通过数据库连接执行数据查询或命令；返回领域记录的当前值。
    如果当前状态等于'submitting'：
        如果键不等于键，就拒绝继续处理并抛出 `RerunConflictError`，向调用方报告输入或运行失败。
        通过数据库连接执行数据查询或命令；返回领域记录的当前值。
    如果当前状态不等于'pending'，就拒绝继续处理并抛出 `RerunConflictError`，向调用方报告输入或运行失败。
    如果记录版本号不等于调用方看到的旧版本号，就拒绝继续处理并抛出 `RerunConflictError`，向调用方报告输入或运行失败。
    读取当前时间，作为状态变更的统一时间戳，并把结果记为 当前时间；通过数据库连接执行数据查询或命令；调用 `_record` 完成该函数的一项辅助处理，并把结果记为 更新后的记录；通过数据库连接执行数据查询或命令。
    返回更新后的记录的当前值。
如果出现 `Exception`：
    如果当前处理结果有值或为真，就通过数据库连接执行数据查询或命令。
    重新抛出当前异常，保持原始失败信息。
无论成功还是失败，最后都要：
    关闭数据库连接并释放相关资源。
```

#### `SqliteRerunRepository.complete_submission`

- **源码**：`app/rerun/repository.py:310`
- **签名**：`def complete_submission(self: 未显式标注, proposal_id: str, submit_idempotency_key: str, child_job_id: str) -> RerunProposalRecord`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收修复或重跑提案的 ID、键、任务的 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `proposal_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `submit_idempotency_key` | `str` | 名为 `submit_idempotency_key` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `child_job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`RerunProposalRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
调用 `_connect` 完成该函数的一项辅助处理，并把结果记为 数据库连接。
先尝试完成以下处理：
    通过数据库连接执行数据查询或命令；调用 `_record` 完成该函数的一项辅助处理，并把结果记为 领域记录。
    如果当前状态等于'submitted'：
        如果任务的 ID不等于任务的 ID，就拒绝继续处理并抛出 `RerunIntegrityError`，向调用方报告输入或运行失败。
        通过数据库连接执行数据查询或命令；返回领域记录的当前值。
    如果当前状态不等于'submitting' 或 键不等于键，就拒绝继续处理并抛出 `RerunConflictError`，向调用方报告输入或运行失败。
    读取当前时间，作为状态变更的统一时间戳，并把结果记为 当前时间；通过数据库连接执行数据查询或命令；调用 `_record` 完成该函数的一项辅助处理，并把结果记为 更新后的记录；通过数据库连接执行数据查询或命令。
    返回更新后的记录的当前值。
如果出现 `Exception`：
    如果当前处理结果有值或为真，就通过数据库连接执行数据查询或命令。
    重新抛出当前异常，保持原始失败信息。
无论成功还是失败，最后都要：
    关闭数据库连接并释放相关资源。
```

#### `SqliteRerunRepository.record_submission_error`

- **源码**：`app/rerun/repository.py:360`
- **签名**：`def record_submission_error(self: 未显式标注, proposal_id: str, submit_idempotency_key: str, detail: str) -> None`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，保持 submitting，重试仍使用同一 Job 幂等键消歧。该函数接收修复或重跑提案的 ID、键、诊断或错误详情，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `proposal_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `submit_idempotency_key` | `str` | 名为 `submit_idempotency_key` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `detail` | `str` | 诊断或错误详情；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_connect` 完成该函数的一项辅助处理，并把结果记为 数据库连接。
先尝试完成以下处理：
    通过数据库连接执行数据查询或命令；调用 `_record` 完成该函数的一项辅助处理，并把结果记为 领域记录。
    如果当前状态等于'submitting' 且 键等于键，就通过数据库连接执行数据查询或命令。
    通过数据库连接执行数据查询或命令。
如果出现 `Exception`：
    如果当前处理结果有值或为真，就通过数据库连接执行数据查询或命令。
    重新抛出当前异常，保持原始失败信息。
无论成功还是失败，最后都要：
    关闭数据库连接并释放相关资源。
```

#### `SqliteRerunRepository.cancel`

- **源码**：`app/rerun/repository.py:395`
- **签名**：`def cancel(self: 未显式标注, proposal_id: str, expected_hash: str, expected_version: int, reason: str) -> RerunProposalRecord`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收修复或重跑提案的 ID、调用方看到的旧内容 Hash、调用方看到的旧版本号、基线接受或运行操作原因，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `proposal_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `expected_hash` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |
| `expected_version` | `int` | 调用方观察到的旧身份，用于 stale/CAS 校验，防止覆盖并发更新。 |
| `reason` | `str` | 来源、类别、用途、后端、状态或操作原因等控制字段；通常对应有限的业务枚举或审计文本。 |

**输出**

- **Python 类型**：`RerunProposalRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
调用 `_connect` 完成该函数的一项辅助处理，并把结果记为 数据库连接。
先尝试完成以下处理：
    通过数据库连接执行数据查询或命令；调用 `_expire_if_needed` 完成该函数的一项辅助处理，并把结果记为 数据库记录行；调用 `_record` 完成该函数的一项辅助处理，并把结果记为 领域记录。
    如果修复或重跑提案的 Hash不等于调用方看到的旧内容 Hash，就拒绝继续处理并抛出 `RerunConflictError`，向调用方报告输入或运行失败。
    如果当前状态等于'cancelled'，就通过数据库连接执行数据查询或命令；返回领域记录的当前值。
    如果当前状态不等于'pending'，就拒绝继续处理并抛出 `RerunConflictError`，向调用方报告输入或运行失败。
    如果记录版本号不等于调用方看到的旧版本号，就拒绝继续处理并抛出 `RerunConflictError`，向调用方报告输入或运行失败。
    通过数据库连接执行数据查询或命令；调用 `_record` 完成该函数的一项辅助处理，并把结果记为 更新后的记录；通过数据库连接执行数据查询或命令；返回更新后的记录的当前值。
如果出现 `Exception`：
    如果当前处理结果有值或为真，就通过数据库连接执行数据查询或命令。
    重新抛出当前异常，保持原始失败信息。
无论成功还是失败，最后都要：
    关闭数据库连接并释放相关资源。
```

#### `SqliteRerunRepository.ping`

- **源码**：`app/rerun/repository.py:443`
- **签名**：`def ping(self) -> bool`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
调用 `_connect` 完成该函数的一项辅助处理，并把结果记为 数据库连接。
先尝试完成以下处理：
    返回比较判断结果。
无论成功还是失败，最后都要：
    关闭数据库连接并释放相关资源。
```

### `app/rerun/schemas.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `RerunArgumentEdit.validate_operation`

- **源码**：`app/rerun/schemas.py:31`
- **签名**：`def validate_operation(self) -> "RerunArgumentEdit"`
- **作用**：在约束论文复现请求、运行状态、证据和结果结构的契约校验阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `'RerunArgumentEdit'` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`'RerunArgumentEdit'`
- **语义**：返回 `'RerunArgumentEdit'` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果MCP 业务操作名称等于'set'：
    如果期望值为空，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    如果当前字段值为空，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
否则：
    如果当前字段值不为空，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前对象的当前值。
```

#### `RerunTemplateArg.reject_control_characters`

- **源码**：`app/rerun/schemas.py:55`
- **签名**：`def reject_control_characters(cls, value: str | None) -> str | None`
- **作用**：在约束论文复现请求、运行状态、证据和结果结构的契约校验阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `str | None` 的领域结果。

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
如果当前字段值等于''，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果当前字段值不为空 且 当前可迭代输入中存在满足“当前处理结果属于当前字段值”的项，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前字段值的当前值。
```

#### `RerunTemplateArg.validate_relative_path`

- **源码**：`app/rerun/schemas.py:66`
- **签名**：`def validate_relative_path(cls, value: str | None) -> str | None`
- **作用**：在约束论文复现请求、运行状态、证据和结果结构的契约校验阶段中，该函数接收当前字段值，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `str | None` 的领域结果。

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
如果当前字段值为空或为假 或 “检查当前字段值是否满足文本匹配条件”后得到肯定结果 或 当前输入内容属于当前字段值，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
对当前字段值中的文本执行规范化或拆分，并把结果记为 拆分后的文本或路径片段集合。
如果由拆分后的文本或路径片段集合组成的集合或迭代器中存在满足“拆分后的文本或路径片段属于{'', '..'}”的项，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前字段值的当前值。
```

#### `RerunTemplateArg.validate_shape`

- **源码**：`app/rerun/schemas.py:77`
- **签名**：`def validate_shape(self) -> "RerunTemplateArg"`
- **作用**：在约束论文复现请求、运行状态、证据和结果结构的契约校验阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `'RerunTemplateArg'` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`'RerunTemplateArg'`
- **语义**：返回 `'RerunTemplateArg'` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果业务类别等于'literal'：
    如果当前字段值为空，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    如果仓库内相对路径不为空 或 当前处理结果不为空，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
否则：
    如果业务类别属于{'repo_path', 'run_path'}：
        如果仓库内相对路径为空，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
        如果当前字段值不为空 或 当前处理结果不为空，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    否则：
        如果仓库内相对路径为空 或 当前处理结果为空，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
        如果“对当前处理结果中的文本执行规范化或拆分”后未得到肯定结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
        如果当前字段值不为空，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前对象的当前值。
```

#### `RerunCommandTemplate.validate_cwd_relative`

- **源码**：`app/rerun/schemas.py:110`
- **签名**：`def validate_cwd_relative(cls, value: str) -> str`
- **作用**：在约束论文复现请求、运行状态、证据和结果结构的契约校验阶段中，该函数接收当前字段值，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终文本、路径、状态标签或内容身份摘要。

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
如果当前字段值为空或为假 或 “检查当前字段值是否满足文本匹配条件”后得到肯定结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
调用 `replace` 完成该函数的一项辅助处理，再对返回文本执行规范化或拆分，并把结果记为 拆分后的文本或路径片段集合。
如果由拆分后的文本或路径片段集合组成的集合或迭代器中存在满足“拆分后的文本或路径片段属于{'', '..'}”的项，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前字段值的当前值。
```

#### `RerunProposalCreateRequest.validate_comparison_binding`

- **源码**：`app/rerun/schemas.py:140`
- **签名**：`def validate_comparison_binding(self) -> "RerunProposalCreateRequest"`
- **作用**：在约束论文复现请求、运行状态、证据和结果结构的契约校验阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `'RerunProposalCreateRequest'` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`'RerunProposalCreateRequest'`
- **语义**：返回 `'RerunProposalCreateRequest'` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果当前输入内容不等于self.expected_comparison_hash 为空，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
遍历并筛选输入，将整理后的结果保存为 当前处理结果。
如果当前处理结果 的长度不等于辅助操作“构造临时集合、映射或轻量领域对象”的结果 的长度，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前对象的当前值。
```

### `app/rerun/service.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `ComparisonReader.get`

- **源码**：`app/rerun/service.py:47`
- **签名**：`def get(self, comparison_id: str) -> ComparisonReport`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收SDK 或 MCP 运行升级比较结果的 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ComparisonReport` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `comparison_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`ComparisonReport`
- **语义**：返回 `ComparisonReport` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `utc_now`

- **源码**：`app/rerun/service.py:51`
- **签名**：`def utc_now() -> str`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `isoformat` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `_required_key`

- **源码**：`app/rerun/service.py:55`
- **签名**：`def _required_key(value: str) -> str`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
去除当前字段值的首尾空白，并把规范化后的文本记为 映射键或对象字段名。
如果映射键或对象字段名为空或为假 或 映射键或对象字段名 的长度大于300，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回映射键或对象字段名的当前值。
```

#### `_expires_at`

- **源码**：`app/rerun/service.py:62`
- **签名**：`def _expires_at(created_at: str, ttl_seconds: int) -> str`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收创建时间、当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `created_at` | `str` | 时间值或可注入时钟，用于排序、过期、租约或可重复测试。 |
| `ttl_seconds` | `int` | 名为 `ttl_seconds` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `fromisoformat` 完成该函数的一项辅助处理，并把结果记为 已创建记录。
如果当前处理结果为空，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
调用 `isoformat` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `_text_sha256`

- **源码**：`app/rerun/service.py:69`
- **签名**：`def _text_sha256(value: str) -> str`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

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

#### `_trusted_requirements`

- **源码**：`app/rerun/service.py:73`
- **签名**：`def _trusted_requirements(profile_id: str) -> JobRequirements`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收MCP Client 配置档案 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `JobRequirements` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `profile_id` | `str` | MCP Client 配置档案 ID；用于区分连接地址、协议版本和能力基线。 |

**输出**

- **Python 类型**：`JobRequirements`
- **语义**：返回 `JobRequirements` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `requirements_from_profile` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `RerunService.__init__`

- **源码**：`app/rerun/service.py:80`
- **签名**：`def __init__(self: 未显式标注, repository: SqliteRerunRepository, evidence_reader: VerifiedRunEvidenceReader, job_service: JobService, comparison_reader: ComparisonReader | None, proposal_ttl_seconds: int, max_command_chars: int, max_argv_items: int, max_edits: int, clock: Callable[[], str], requirements_resolver: Callable[[str], JobRequirements]) -> None`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收持久化仓库、证据读取器、任务、读取器等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `repository` | `SqliteRerunRepository` | 持久化或目录访问端口；负责读取、CAS 更新或 Artifact 定位。 |
| `evidence_reader` | `VerifiedRunEvidenceReader` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |
| `job_service` | `JobService` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |
| `comparison_reader` | `ComparisonReader | None` | 只读证据或数据读取端口；负责把外部持久化内容投影为受约束领域输入。 |
| `proposal_ttl_seconds` | `int` | 名为 `proposal_ttl_seconds` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `max_command_chars` | `int` | 待展示、校验或执行的命令文本/结构化命令；仅进入 Executor 路径后才可能产生执行副作用。 |
| `max_argv_items` | `int` | 名为 `max_argv_items` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `max_edits` | `int` | 名为 `max_edits` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `clock` | `Callable[[], str]` | 时间值或可注入时钟，用于排序、过期、租约或可重复测试。；默认 utc_now |
| `requirements_resolver` | `Callable[[str], JobRequirements]` | 可调用依赖；其参数和返回契约由类型标注限定。；默认 _trusted_requirements |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 持久化仓库、证据读取器、任务、读取器、当前处理结果、最大命令字符数、最大当前处理结果、最大命令修改项集合、统一时间来源、要求集合 分别保存到同名实例字段；调用 `initialize` 完成该函数的一项辅助处理。
```

#### `RerunService._read_evidence`

- **源码**：`app/rerun/service.py:108`
- **签名**：`def _read_evidence(self, job_id: str) -> VerifiedRunEvidence`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收复现任务 ID，用于读取并整理论文、源码或运行产物，把原始输入转换成带位置和身份信息的结构化证据，最终标注为 `VerifiedRunEvidence` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`VerifiedRunEvidence`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
先尝试完成以下处理：
    调用 `read` 完成该函数的一项辅助处理，并返回处理结果。
如果出现 `(RunEvidenceNotFoundError, RunEvidenceConflictError, RunEvidenceLimitExceededError)`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `RerunConflictError`，向调用方报告输入或运行失败。
如果出现 `RunEvidenceIntegrityError`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `RerunIntegrityError`，向调用方报告输入或运行失败。
```

#### `RerunService._verify_comparison`

- **源码**：`app/rerun/service.py:122`
- **签名**：`def _verify_comparison(self: 未显式标注, parent_job_id: str, comparison_id: str | None, expected_hash: str | None) -> None`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收任务的 ID、SDK 或 MCP 运行升级比较结果的 ID、调用方看到的旧内容 Hash，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `parent_job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `comparison_id` | `str | None` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `expected_hash` | `str | None` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
如果SDK 或 MCP 运行升级比较结果的 ID为空，就结束当前函数，不返回业务值。
如果读取器为空 或 调用方看到的旧内容 Hash为空，就拒绝继续处理并抛出 `RerunConflictError`，向调用方报告输入或运行失败。
从读取器读取所需的状态或领域记录，并把结果记为 MCP 评测或运行报告。
如果SDK 或 MCP 运行升级比较结果的 Hash不等于调用方看到的旧内容 Hash，就拒绝继续处理并抛出 `RerunConflictError`，向调用方报告输入或运行失败。
如果任务的 ID不属于{复现任务 ID, 复现任务 ID}，就拒绝继续处理并抛出 `RerunConflictError`，向调用方报告输入或运行失败。
```

#### `RerunService._source_identity`

- **源码**：`app/rerun/service.py:142`
- **签名**：`def _source_identity(evidence: VerifiedRunEvidence) -> RerunSourceIdentity`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收可追溯证据记录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `RerunSourceIdentity` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `evidence` | `VerifiedRunEvidence` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |

**输出**

- **Python 类型**：`RerunSourceIdentity`
- **语义**：返回 `RerunSourceIdentity` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
读取复现任务记录，并保存为 复现任务记录；读取本次复现工作区，并保存为 本次复现工作区；读取运行ManifestArtifact，并保存为 Artifact；构造并返回 `RerunSourceIdentity` 结构化领域对象。
```

#### `RerunService._verify_source_against_proposal`

- **源码**：`app/rerun/service.py:159`
- **签名**：`def _verify_source_against_proposal(evidence: VerifiedRunEvidence, proposal: RerunProposal) -> None`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收可追溯证据记录、修复或重跑提案，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `evidence` | `VerifiedRunEvidence` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |
| `proposal` | `RerunProposal` | 修复或重跑提案；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_source_identity` 完成该函数的一项辅助处理，并把结果记为 当前值。
如果当前值不等于数据来源标记，就拒绝继续处理并抛出 `RerunConflictError`，向调用方报告输入或运行失败。
从运行Manifest读取所需的状态或领域记录，并把结果记为 选中的候选项。
如果“计算数量、边界或类型判断结果”后未得到肯定结果，就拒绝继续处理并抛出 `RerunIntegrityError`，向调用方报告输入或运行失败。
调用 `str` 完成该函数的一项辅助处理，并把结果记为 当前命令。
如果辅助操作“调用 `_text_sha256` 计算内容身份、分数或派生结果”的结果不等于命令的 SHA-256，就拒绝继续处理并抛出 `RerunIntegrityError`，向调用方报告输入或运行失败。
```

#### `RerunService.create_proposal`

- **源码**：`app/rerun/service.py:180`
- **签名**：`def create_proposal(self: 未显式标注, request: RerunProposalCreateRequest, idempotency_key: str) -> tuple[RerunProposalRecord, bool]`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收业务请求、请求幂等键，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `request` | `RerunProposalCreateRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `idempotency_key` | `str` | 调用方提供的幂等键；重复请求应复用同一结果，而不是再次产生副作用。 |

**输出**

- **Python 类型**：`tuple[RerunProposalRecord, bool]`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
调用 `_required_key` 完成该函数的一项辅助处理，并把结果记为 映射键或对象字段名。
如果命令修改项集合 的长度大于最大命令修改项集合，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
调用 `sha256_value` 计算内容身份、分数或派生结果，并把结果记为 请求内容 Hash；调用 `find_create_replay` 读取或查询当前阶段需要的数据，并把结果记为 该调用返回的结果。
如果当前处理结果不为空，就返回当前构造的顺序或去重集合。
调用 `_read_evidence` 读取或查询当前阶段需要的数据，并把结果记为 可追溯证据记录。
如果记录版本号不等于期望任务版本，就拒绝继续处理并抛出 `RerunConflictError`，向调用方报告输入或运行失败。
如果内容 SHA-256不等于期望运行Manifest的 SHA-256，就拒绝继续处理并抛出 `RerunConflictError`，向调用方报告输入或运行失败。
调用 `_verify_comparison` 完成该函数的一项辅助处理；调用 `build_command_template` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果；计算计算当前表达式的结果，并保存为 MCP Client 配置档案 ID；调用 `requirements_resolver` 完成该函数的一项辅助处理，并把结果记为 运行要求集合。
读取当前时间，作为状态变更的统一时间戳，并把结果记为 创建时间；构造 `RerunProposal` 结构化领域对象，并把结果记为 草稿对象；调用 `proposal_hash` 完成该函数的一项辅助处理，并把结果记为 内容摘要；复制、序列化或校验结构化领域对象，并把结果记为 修复或重跑提案。
调用 `create` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `RerunService.get_proposal`

- **源码**：`app/rerun/service.py:266`
- **签名**：`def get_proposal(self, proposal_id: str) -> RerunProposalRecord`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收修复或重跑提案的 ID，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `proposal_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`RerunProposalRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
从持久化仓库读取所需的状态或领域记录，并返回处理结果。
```

#### `RerunService.cancel_proposal`

- **源码**：`app/rerun/service.py:269`
- **签名**：`def cancel_proposal(self: 未显式标注, proposal_id: str, request: RerunProposalCancelRequest) -> RerunProposalRecord`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收修复或重跑提案的 ID、业务请求，用于驱动或监督一次论文复现运行，记录命令、工作目录、资源使用、状态迁移和失败原因，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `proposal_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `request` | `RerunProposalCancelRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`RerunProposalRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
调用 `cancel` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `RerunService.submit_proposal`

- **源码**：`app/rerun/service.py:282`
- **签名**：`def submit_proposal(self: 未显式标注, proposal_id: str, request: RerunProposalSubmitRequest, idempotency_key: str) -> tuple[RerunProposalRecord, JobRecord, bool]`
- **作用**：在围绕复现运行进行问答、结果比较和受控重跑的阶段中，该函数接收修复或重跑提案的 ID、业务请求、请求幂等键，用于驱动或监督一次论文复现运行，记录命令、工作目录、资源使用、状态迁移和失败原因，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `proposal_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `request` | `RerunProposalSubmitRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `idempotency_key` | `str` | 调用方提供的幂等键；重复请求应复用同一结果，而不是再次产生副作用。 |

**输出**

- **Python 类型**：`tuple[RerunProposalRecord, JobRecord, bool]`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
调用 `_required_key` 完成该函数的一项辅助处理，并把结果记为 操作键；调用 `begin_submission` 完成该函数的一项辅助处理，并把结果记为 领域记录。
如果当前状态等于'submitted'：
    如果任务的 ID为空，就拒绝继续处理并抛出 `RerunIntegrityError`，向调用方报告输入或运行失败。
    返回当前构造的顺序或去重集合。
读取修复或重跑提案，并保存为 修复或重跑提案；调用 `validate_proposal_hash` 校验当前输入或状态；调用 `validate_command_template_hash` 校验当前输入或状态。
先尝试完成以下处理：
    调用 `_read_evidence` 读取或查询当前阶段需要的数据，并把结果记为 可追溯证据记录；调用 `_verify_source_against_proposal` 完成该函数的一项辅助处理；调用 `_verify_comparison` 完成该函数的一项辅助处理；调用 `requirements_resolver` 完成该函数的一项辅助处理，并把结果记为 当前要求集合集合。
    如果执行策略的 Hash不等于执行策略的 Hash 或 执行不等于执行，就拒绝继续处理并抛出 `RerunConflictError`，向调用方报告输入或运行失败。
    调用 `submit` 完成该函数的一项辅助处理，并把结果记为 多个解包结果。
如果出现 `Exception`并把异常保存为捕获的异常对象：
    调用 `record_submission_error` 完成该函数的一项辅助处理；重新抛出当前异常，保持原始失败信息。
调用 `complete_submission` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；返回当前构造的顺序或去重集合。
```

### `app/retention/checkpoint_adapter.py`

**模块作用**：LangGraph Checkpoint 删除适配器。

#### `LangGraphCheckpointRetentionAdapter.__init__`

- **源码**：`app/retention/checkpoint_adapter.py:6`
- **签名**：`def __init__(self, checkpointer: Any)`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `checkpointer` | `Any` | 名为 `checkpointer` 的 `Any` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 当前处理结果 分别保存到同名实例字段。
```

#### `LangGraphCheckpointRetentionAdapter.delete_thread`

- **源码**：`app/retention/checkpoint_adapter.py:9`
- **签名**：`def delete_thread(self, thread_id: str) -> None`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收流程线程 ID，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `thread_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `delete_thread` 持久化或更新当前领域数据。
```

### `app/retention/factory.py`

**模块作用**：Retention Factory 与 Backend Fail-Closed.

#### `NoOpChatRetentionPort.delete_job_messages`

- **源码**：`app/retention/factory.py:31`
- **签名**：`def delete_job_messages(self, job_id: str) -> int`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务 ID，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终数量、序号、字节数或版本等整数结果。

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
移除复现任务 ID中的当前内容；返回固定值 `0`。
```

#### `NoOpFailureMemoryRetentionPort.active_referenced_job_ids`

- **源码**：`app/retention/factory.py:37`
- **签名**：`def active_referenced_job_ids(self) -> set[str]`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`set[str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
构造临时集合、映射或轻量领域对象，并返回处理结果。
```

#### `NoOpProjectMemoryRetentionPort.active_referenced_job_ids`

- **源码**：`app/retention/factory.py:42`
- **签名**：`def active_referenced_job_ids(self) -> set[str]`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`set[str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
构造临时集合、映射或轻量领域对象，并返回处理结果。
```

#### `NoOpKnowledgeMemoryRetentionPort.active_referenced_job_ids`

- **源码**：`app/retention/factory.py:47`
- **签名**：`def active_referenced_job_ids(self) -> set[str]`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`set[str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
构造临时集合、映射或轻量领域对象，并返回处理结果。
```

#### `NoOpMcpEvidenceRetentionPort.delete_for_job`

- **源码**：`app/retention/factory.py:52`
- **签名**：`def delete_for_job(self, job_id: str) -> int`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务 ID，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终数量、序号、字节数或版本等整数结果。

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
移除复现任务 ID中的当前内容；返回固定值 `0`。
```

#### `NoOpMcpExportAuditRetentionPort.delete_for_job`

- **源码**：`app/retention/factory.py:58`
- **签名**：`def delete_for_job(self, job_id: str) -> int`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务 ID，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终数量、序号、字节数或版本等整数结果。

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
移除复现任务 ID中的当前内容；返回固定值 `0`。
```

#### `_sqlite_roots`

- **源码**：`app/retention/factory.py:62`
- **签名**：`def _sqlite_roots(name: str, path: Path) -> list[tuple[str, Path]]`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收对象名称、文件或目录路径，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个经过边界校验的文件或目录路径。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `name` | `str` | 对象名称；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`list[tuple[str, Path]]`
- **语义**：返回解析后的文件或目录路径对象。

**伪代码**

```text
返回当前构造的顺序或去重集合。
```

#### `build_inventory`

- **源码**：`app/retention/factory.py:69`
- **签名**：`def build_inventory(*, destructive_supported: bool) -> StorageInventoryService`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前处理结果，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `StorageInventoryService` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `destructive_supported` | `bool` | 布尔条件或能力开关，用于控制流程分支。 |

**输出**

- **Python 类型**：`StorageInventoryService`
- **语义**：返回 `StorageInventoryService` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
计算初始化顺序集合，并保存为 受控扫描根目录集合。
遍历当前可迭代输入，每次把当前项记为多个解包结果，然后把新的处理结果追加或合并到受控扫描根目录集合。
如果项目记忆有值或为真，就把新的处理结果追加或合并到受控扫描根目录集合。
把新的处理结果追加或合并到受控扫描根目录集合；把新的处理结果追加或合并到受控扫描根目录集合；把新的处理结果追加或合并到受控扫描根目录集合；构造并返回 `StorageInventoryService` 结构化领域对象。
```

#### `_build_mcp_evidence_retention`

- **源码**：`app/retention/factory.py:135`
- **签名**：`def _build_mcp_evidence_retention()`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于在固定 MCP Policy、Schema Pin、调用预算和只读职责边界内连接或调用外部能力，并把返回内容转换为可追溯的复现证据，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
如果网关有值或为真 或 “检查网关的路径的文件系统属性”后得到肯定结果，就加载这一步需要的外部依赖；构造 `SqliteMcpEvidenceRepository` 结构化领域对象，并把结果记为 持久化仓库；调用 `initialize` 完成该函数的一项辅助处理；返回持久化仓库的当前值。
构造并返回 `NoOpMcpEvidenceRetentionPort` 结构化领域对象。
```

#### `_build_mcp_export_audit_retention`

- **源码**：`app/retention/factory.py:147`
- **签名**：`def _build_mcp_export_audit_retention()`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于在固定 MCP Policy、Schema Pin、调用预算和只读职责边界内连接或调用外部能力，并把返回内容转换为可追溯的复现证据，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
读取当前处理结果的路径，并保存为 文件或目录路径。
如果当前处理结果有值或为真 或 “检查文件或目录路径的文件系统属性”后得到肯定结果，就加载这一步需要的外部依赖；构造 `SqliteMcpExportAuditRepository` 结构化领域对象，并把结果记为 持久化仓库；调用 `initialize` 完成该函数的一项辅助处理；返回持久化仓库的当前值。
构造并返回 `NoOpMcpExportAuditRetentionPort` 结构化领域对象。
```

#### `build_retention`

- **源码**：`app/retention/factory.py:160`
- **签名**：`def build_retention(job_store: 未显式标注, artifact_storage: ArtifactStorageBundle, project_memory_repository: 未显式标注, knowledge_repository: 未显式标注) -> RetentionBundle`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收任务存储、Artifact、项目记忆代码仓库、代码仓库，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `RetentionBundle` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `job_store` | `未显式标注` | 名为 `job_store` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `artifact_storage` | `ArtifactStorageBundle` | 名为 `artifact_storage` 的 `ArtifactStorageBundle` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `project_memory_repository` | `未显式标注` | 持久化或目录访问端口；负责读取、CAS 更新或 Artifact 定位。；默认 空值 |
| `knowledge_repository` | `未显式标注` | 持久化或目录访问端口；负责读取、CAS 更新或 Artifact 定位。；默认 空值 |

**输出**

- **Python 类型**：`RetentionBundle`
- **语义**：返回 `RetentionBundle` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
计算计算当前表达式的结果，并保存为 当前处理结果；调用 `build_inventory` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果；构造 `StorageQuotaGuard` 结构化领域对象，并把结果记为 该调用返回的结果。
如果当前处理结果为空或为假，就构造并返回 `RetentionBundle` 结构化领域对象。
如果“计算数量、边界或类型判断结果”后未得到肯定结果，就拒绝继续处理并抛出 `RuntimeError`，向调用方报告输入或运行失败。
读取存储，并保存为 后续步骤使用的结果；计算根据条件从两个候选结果中选择一个，并保存为 对话。
如果“计算数量、边界或类型判断结果”后得到肯定结果，就调用 `initialize` 完成该函数的一项辅助处理。
构造 `SqliteResourceRepository` 结构化领域对象，并把结果记为 资源代码仓库；调用 `initialize` 完成该函数的一项辅助处理；构造 `SqliteNotificationRepository` 结构化领域对象，并把结果记为 通知代码仓库；调用 `initialize` 完成该函数的一项辅助处理。
构造 `SqliteRetentionRepository` 结构化领域对象，并把结果记为 持久化仓库；构造 `SqliteFailureCaseRepository` 结构化领域对象，并把结果记为 失败记忆代码仓库；调用 `initialize` 完成该函数的一项辅助处理；读取代码仓库，并保存为 代码仓库。
如果代码仓库为空 且 “检查当前处理结果的路径的文件系统属性”后得到肯定结果，就加载这一步需要的外部依赖；构造 `SqliteKnowledgeRepository` 结构化领域对象，并把结果记为 代码仓库；调用 `initialize` 完成该函数的一项辅助处理。
构造 `RetentionService` 结构化领域对象，并把结果记为 领域服务对象；构造并返回 `RetentionBundle` 结构化领域对象。
```

### `app/retention/inventory.py`

**模块作用**：容量盘点：不跟随符号链接统计受管目录。

#### `_allocated_bytes`

- **源码**：`app/retention/inventory.py:19`
- **签名**：`def _allocated_bytes(stat_result: os.stat_result) -> int`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终数量、序号、字节数或版本等整数结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `stat_result` | `os.stat_result` | 前序调用产生的结构化响应、结果或执行结论，供当前函数继续判断或投影。 |

**输出**

- **Python 类型**：`int`
- **语义**：返回整数计数、序号、字节数或退出码；具体含义由函数名决定。

**伪代码**

```text
调用 `getattr` 完成该函数的一项辅助处理，并把结果记为 论文原文块集合；返回按条件选出的结果。
```

#### `_scan_root`

- **源码**：`app/retention/inventory.py:23`
- **签名**：`def _scan_root(name: str, root: Path, warnings: list[str], max_warnings: int) -> ManagedRootUsage`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，使用 scandir + follow_symlinks=False，绝不穿过 symlink。该函数接收对象名称、受控扫描根目录、警告集合、最大警告集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ManagedRootUsage` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `name` | `str` | 对象名称；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `root` | `Path` | 运行产物或受控工作区的目录路径；用于隔离本次运行生成的文件。 |
| `warnings` | `list[str]` | 警告集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `max_warnings` | `int` | 名为 `max_warnings` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`ManagedRootUsage`
- **语义**：返回 `ManagedRootUsage` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
计算使用固定配置或常量值，并保存为 当前处理结果；计算使用固定配置或常量值，并保存为 当前处理结果；计算使用固定配置或常量值，并保存为 当前处理结果；计算使用固定配置或常量值，并保存为 当前处理结果。
计算使用固定配置或常量值，并保存为 当前处理结果；计算使用固定配置或常量值，并保存为 错误信息集合。
如果“检查受控扫描根目录的文件系统属性”后未得到肯定结果 且 “检查受控扫描根目录的文件系统属性”后未得到肯定结果，就构造并返回 `ManagedRootUsage` 结构化领域对象。
如果“检查受控扫描根目录的文件系统属性”后得到肯定结果，就构造并返回 `ManagedRootUsage` 结构化领域对象。
计算初始化顺序集合，并保存为 当前处理结果。
只要当前处理结果有值或为真，就重复以下处理：
    从当前处理结果取出并移除最后一项，并把结果记为 当前值。
    先尝试完成以下处理：
        调用 `stat` 完成该函数的一项辅助处理，并把结果记为 当前；将新的计算结果累加或合并到当前处理结果；将新的计算结果累加或合并到当前处理结果。
        如果“检查当前值的文件系统属性”后得到肯定结果，就将新的计算结果累加或合并到当前处理结果；跳过本轮剩余处理，直接进入下一轮。
        将新的计算结果累加或合并到当前处理结果。
        进入上下文“调用 `scandir` 完成该函数的一项辅助处理，并把上下文资源交给当前处理结果”，退出时自动清理资源：
            遍历由当前处理结果组成的集合或迭代器，每次把当前项记为条目：
                先尝试完成以下处理：
                    如果“检查条目的文件系统属性”后得到肯定结果，就将新的计算结果累加或合并到当前处理结果；跳过本轮剩余处理，直接进入下一轮。
                    如果“检查条目的文件系统属性”后得到肯定结果，就把新的处理结果追加或合并到当前处理结果；跳过本轮剩余处理，直接进入下一轮。
                    调用 `stat` 完成该函数的一项辅助处理，并把结果记为 结果；将新的计算结果累加或合并到当前处理结果；将新的计算结果累加或合并到当前处理结果；将新的计算结果累加或合并到当前处理结果。
                如果出现 `OSError`并把异常保存为捕获的异常对象：
                    将新的计算结果累加或合并到错误信息集合。
                    如果警告集合 的长度小于最大警告集合，就把新的处理结果追加或合并到警告集合。
    如果出现 `OSError`并把异常保存为捕获的异常对象：
        将新的计算结果累加或合并到错误信息集合。
        如果警告集合 的长度小于最大警告集合，就把新的处理结果追加或合并到警告集合。
构造并返回 `ManagedRootUsage` 结构化领域对象。
```

#### `StorageInventoryService.__init__`

- **源码**：`app/retention/inventory.py:111`
- **签名**：`def __init__(self, config: InventoryConfig)`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收运行配置，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `config` | `InventoryConfig` | 配置或选项对象；描述运行约束，不等同于执行结果。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 运行配置 分别保存到同名实例字段。
```

#### `StorageInventoryService.summarize`

- **源码**：`app/retention/inventory.py:114`
- **签名**：`def summarize(self) -> StorageSummary`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `StorageSummary` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`StorageSummary`
- **语义**：返回 `StorageSummary` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
将 警告集合 初始化为空列表，用来收集后续结果；遍历并筛选输入，将整理后的结果保存为 当前处理结果；调用 `statvfs` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；计算组合或计算已有值，并保存为 当前处理结果。
计算组合或计算已有值，并保存为 当前处理结果；调用 `sum` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；计算计算当前表达式的结果，并保存为 当前处理结果；计算计算当前表达式的结果，并保存为 当前处理结果。
计算根据条件从两个候选结果中选择一个，并保存为 当前处理结果；构造并返回 `StorageSummary` 结构化领域对象。
```

### `app/retention/lock.py`

**模块作用**：单主机 Sweep 文件锁。

#### `SingleHostSweepLock.__init__`

- **源码**：`app/retention/lock.py:10`
- **签名**：`def __init__(self, path: Path)`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收文件或目录路径，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 文件或目录路径 分别保存到同名实例字段。
```

#### `SingleHostSweepLock.acquire`

- **源码**：`app/retention/lock.py:14`
- **签名**：`def acquire(self) -> Iterator[None]`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `Iterator[None]` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`Iterator[None]`
- **语义**：返回惰性迭代结果，调用方逐项消费。

**伪代码**

```text
创建父级目录或父领域对象对应的目录。
进入上下文“调用 `open` 完成该函数的一项辅助处理，并把上下文资源交给文件”，退出时自动清理资源：
    先尝试完成以下处理：
        调用 `flock` 完成该函数的一项辅助处理。
    如果出现 `BlockingIOError`：
        拒绝继续处理并抛出 `RetentionConflict`，向调用方报告输入或运行失败。
    先尝试完成以下处理：
        完成当前表达式对应的校验或状态操作。
    无论成功还是失败，最后都要：
        调用 `flock` 完成该函数的一项辅助处理。
```

### `app/retention/paths.py`

**模块作用**：安全路径验证与删除。

#### `_component`

- **源码**：`app/retention/paths.py:14`
- **签名**：`def _component(value: str, field: str) -> str`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前字段值、结构化对象字段，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |
| `field` | `str` | 结构化对象字段；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
如果当前字段值属于{'.', '..'} 或 “调用 `fullmatch` 完成该函数的一项辅助处理”后未得到肯定结果，就拒绝继续处理并抛出 `RetentionPathUnsafe`，向调用方报告输入或运行失败。
返回当前字段值的当前值。
```

#### `_reject_symlink_chain`

- **源码**：`app/retention/paths.py:19`
- **签名**：`def _reject_symlink_chain(path: Path, root: Path) -> None`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收文件或目录路径、受控扫描根目录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |
| `root` | `Path` | 运行产物或受控工作区的目录路径；用于隔离本次运行生成的文件。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
读取文件或目录路径，并保存为 当前值。
只要当前值不等于受控扫描根目录，就重复以下处理：
    如果“检查当前值的文件系统属性”后得到肯定结果，就拒绝继续处理并抛出 `RetentionPathUnsafe`，向调用方报告输入或运行失败。
    如果受控扫描根目录不属于当前处理结果，就拒绝继续处理并抛出 `RetentionPathUnsafe`，向调用方报告输入或运行失败。
    读取父级目录或父领域对象，并保存为 当前值。
```

#### `_tree_logical_bytes`

- **源码**：`app/retention/paths.py:28`
- **签名**：`def _tree_logical_bytes(root: Path) -> int`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，删除前估算；不跟随 symlink，symlink 本身也不允许存在。该函数接收受控扫描根目录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终数量、序号、字节数或版本等整数结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `root` | `Path` | 运行产物或受控工作区的目录路径；用于隔离本次运行生成的文件。 |

**输出**

- **Python 类型**：`int`
- **语义**：返回整数计数、序号、字节数或退出码；具体含义由函数名决定。

**伪代码**

```text
计算使用固定配置或常量值，并保存为 当前处理结果；计算初始化顺序集合，并保存为 当前处理结果。
只要当前处理结果有值或为真，就重复以下处理：
    从当前处理结果取出并移除最后一项，并把结果记为 当前值。
    如果“检查当前值的文件系统属性”后得到肯定结果，就拒绝继续处理并抛出 `RetentionPathUnsafe`，向调用方报告输入或运行失败。
    进入上下文“调用 `scandir` 完成该函数的一项辅助处理，并把上下文资源交给当前处理结果”，退出时自动清理资源：
        遍历由当前处理结果组成的集合或迭代器，每次把当前项记为条目：
            如果“检查条目的文件系统属性”后得到肯定结果，就拒绝继续处理并抛出 `RetentionPathUnsafe`，向调用方报告输入或运行失败。
            如果“检查条目的文件系统属性”后得到肯定结果，就把新的处理结果追加或合并到当前处理结果；否则将新的计算结果累加或合并到当前处理结果。
返回前一步处理得到的结果。
```

#### `SafePathRemover.__init__`

- **源码**：`app/retention/paths.py:49`
- **签名**：`def __init__(self, *, runs_root: Path, worker_root: Path)`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收根目录、根目录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `runs_root` | `Path` | 已经解析的文件或目录路径对象；后续操作仍需遵守仓库/工作区边界。 |
| `worker_root` | `Path` | 已经解析的文件或目录路径对象；后续操作仍需遵守仓库/工作区边界。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
将根目录规范化为受控的绝对路径，并把结果记为 根目录；将根目录规范化为受控的绝对路径，并把结果记为 根目录。
```

#### `SafePathRemover._workspace_epoch_root`

- **源码**：`app/retention/paths.py:53`
- **签名**：`def _workspace_epoch_root(self, binding: WorkspaceBinding) -> Path`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收资源绑定记录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个经过边界校验的文件或目录路径。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `binding` | `WorkspaceBinding` | 资源绑定记录；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`Path`
- **语义**：返回解析后的文件或目录路径对象。

**伪代码**

```text
计算组合或计算已有值，并保存为 期望值。
如果辅助操作“把外部位置解析为文件系统路径对象”的结果不等于期望值，就拒绝继续处理并抛出 `RetentionPathUnsafe`，向调用方报告输入或运行失败。
调用 `_reject_symlink_chain` 完成该函数的一项辅助处理。
如果“检查期望值的文件系统属性”后得到肯定结果：
    计算组合或计算已有值，并保存为 测试或状态标记。
    如果“检查测试或状态标记的文件系统属性”后未得到肯定结果 或 “检查测试或状态标记的文件系统属性”后得到肯定结果，就拒绝继续处理并抛出 `RetentionPathUnsafe`，向调用方报告输入或运行失败。
    调用 `model_validate_json` 完成该函数的一项辅助处理，并把结果记为 本地；计算组合多个值形成元组，并保存为 对象身份；计算组合多个值形成元组，并保存为 期望身份。
    如果对象身份不等于期望身份，就拒绝继续处理并抛出 `RetentionPathUnsafe`，向调用方报告输入或运行失败。
返回期望值的当前值。
```

#### `SafePathRemover.validate_job_paths`

- **源码**：`app/retention/paths.py:90`
- **签名**：`def validate_job_paths(self: 未显式标注, job: JobRecord, bindings: list[WorkspaceBinding]) -> list[Path]`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务记录、当前处理结果，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终一个经过边界校验的文件或目录路径。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job` | `JobRecord` | 任务、运行、Manifest、记录或证据领域对象；携带关联 ID、状态和内容身份。 |
| `bindings` | `list[WorkspaceBinding]` | `list[WorkspaceBinding]` 元素集合；元素代表的业务对象由参数名 `bindings` 和调用位置确定。 |

**输出**

- **Python 类型**：`list[Path]`
- **语义**：返回解析后的文件或目录路径对象。

**伪代码**

```text
遍历并筛选输入，将整理后的结果保存为 当前处理结果；计算组合或计算已有值，并保存为 当前处理结果；把外部位置解析为文件系统路径对象，并把结果记为 运行；遍历并筛选输入，将整理后的结果保存为 绑定运行集合。
如果运行等于当前处理结果：
    调用 `_reject_symlink_chain` 完成该函数的一项辅助处理；计算初始化顺序集合，并保存为 候选结果集合。
否则：
    如果运行属于绑定运行集合，就读取当前处理结果，并保存为 候选结果集合；否则拒绝继续处理并抛出 `RetentionPathUnsafe`，向调用方报告输入或运行失败。
按稳定规则整理结果顺序，并把结果记为 该调用返回的结果；将 阶段处理结果 初始化为空列表，用来收集后续结果。
遍历由当前处理结果组成的集合或迭代器，每次把当前项记为待审核的 MCP 能力候选：
    如果由阶段处理结果组成的集合或迭代器中存在满足“父级目录或父领域对象等于待审核的 MCP 能力候选 或 父级目录或父领域对象属于当前处理结果”的项，就跳过本轮剩余处理，直接进入下一轮。
    把待审核的 MCP 能力候选追加或合并到阶段处理结果。
返回阶段处理结果的当前值。
```

#### `SafePathRemover.remove_tree`

- **源码**：`app/retention/paths.py:117`
- **签名**：`def remove_tree(self, path: Path) -> int`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，不存在视为已删除；存在时先完整安全扫描，再 rmtree。该函数接收文件或目录路径，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终数量、序号、字节数或版本等整数结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`int`
- **语义**：返回整数计数、序号、字节数或退出码；具体含义由函数名决定。

**伪代码**

```text
如果“检查文件或目录路径的文件系统属性”后未得到肯定结果 且 “检查文件或目录路径的文件系统属性”后未得到肯定结果，就返回固定值 `0`。
如果“检查文件或目录路径的文件系统属性”后得到肯定结果 或 “检查文件或目录路径的文件系统属性”后未得到肯定结果，就拒绝继续处理并抛出 `RetentionPathUnsafe`，向调用方报告输入或运行失败。
调用 `_tree_logical_bytes` 完成该函数的一项辅助处理，并把结果记为 对象大小；调用 `rmtree` 完成该函数的一项辅助处理；返回对象大小的当前值。
```

### `app/retention/ports.py`

**模块作用**：Retention 窄端口定义。

#### `JobRetentionPort.list_retention_candidates`

- **源码**：`app/retention/ports.py:11`
- **签名**：`def list_retention_candidates(self: 未显式标注, updated_before: float, limit: int) -> list[JobRecord]`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收更新后的、结果数量上限，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `updated_before` | `float` | 名为 `updated_before` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。 |

**输出**

- **Python 类型**：`list[JobRecord]`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `JobRetentionPort.get`

- **源码**：`app/retention/ports.py:18`
- **签名**：`def get(self: 未显式标注, job_id: str) -> JobRecord`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`JobRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `JobRetentionPort.list_workspace_bindings_for_retention`

- **源码**：`app/retention/ports.py:20`
- **签名**：`def list_workspace_bindings_for_retention(self: 未显式标注, job_id: str) -> list[WorkspaceBinding]`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务 ID，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`list[WorkspaceBinding]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `JobRetentionPort.list_workspace_manifests_for_retention`

- **源码**：`app/retention/ports.py:25`
- **签名**：`def list_workspace_manifests_for_retention(self: 未显式标注, job_id: str) -> list[WorkspaceManifest]`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务 ID，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`list[WorkspaceManifest]`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `JobRetentionPort.count_workspace_blob_references`

- **源码**：`app/retention/ports.py:30`
- **签名**：`def count_workspace_blob_references(self: 未显式标注, object_key: str) -> int`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收存储对象键，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终数量、序号、字节数或版本等整数结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `object_key` | `str` | 存储对象键；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`int`
- **语义**：返回整数计数、序号、字节数或退出码；具体含义由函数名决定。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `JobRetentionPort.delete_job_for_retention`

- **源码**：`app/retention/ports.py:36`
- **签名**：`def delete_job_for_retention(self: 未显式标注, job_id: str, expected_version: int, expected_status: str) -> bool`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务 ID、调用方看到的旧版本号、期望状态，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `expected_version` | `int` | 调用方观察到的旧身份，用于 stale/CAS 校验，防止覆盖并发更新。 |
| `expected_status` | `str` | 调用方观察到的旧身份，用于 stale/CAS 校验，防止覆盖并发更新。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `ArtifactRetentionPort.list_blob_references_for_job`

- **源码**：`app/retention/ports.py:45`
- **签名**：`def list_blob_references_for_job(self: 未显式标注, job_id: str) -> list[BlobReference]`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务 ID，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`list[BlobReference]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `ArtifactRetentionPort.delete_job_artifacts`

- **源码**：`app/retention/ports.py:50`
- **签名**：`def delete_job_artifacts(self: 未显式标注, job_id: str) -> int`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务 ID，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终数量、序号、字节数或版本等整数结果。

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
仅声明接口契约，这里没有具体实现。
```

#### `ArtifactRetentionPort.count_blob_references`

- **源码**：`app/retention/ports.py:52`
- **签名**：`def count_blob_references(self: 未显式标注, backend: str, object_key: str) -> int`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收模型或检索后端、存储对象键，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终数量、序号、字节数或版本等整数结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `backend` | `str` | 来源、类别、用途、后端、状态或操作原因等控制字段；通常对应有限的业务枚举或审计文本。 |
| `object_key` | `str` | 存储对象键；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`int`
- **语义**：返回整数计数、序号、字节数或退出码；具体含义由函数名决定。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `ChatRetentionPort.delete_job_messages`

- **源码**：`app/retention/ports.py:60`
- **签名**：`def delete_job_messages(self: 未显式标注, job_id: str) -> int`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务 ID，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终数量、序号、字节数或版本等整数结果。

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
仅声明接口契约，这里没有具体实现。
```

#### `NotificationRetentionPort.delete_for_job`

- **源码**：`app/retention/ports.py:64`
- **签名**：`def delete_for_job(self: 未显式标注, job_id: str) -> int`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务 ID，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终数量、序号、字节数或版本等整数结果。

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
仅声明接口契约，这里没有具体实现。
```

#### `FailureMemoryRetentionPort.active_referenced_job_ids`

- **源码**：`app/retention/ports.py:68`
- **签名**：`def active_referenced_job_ids(self: 未显式标注) -> set[str]`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

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

#### `ProjectMemoryRetentionPort.active_referenced_job_ids`

- **源码**：`app/retention/ports.py:72`
- **签名**：`def active_referenced_job_ids(self: 未显式标注) -> set[str]`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

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

#### `KnowledgeMemoryRetentionPort.active_referenced_job_ids`

- **源码**：`app/retention/ports.py:76`
- **签名**：`def active_referenced_job_ids(self: 未显式标注) -> set[str]`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

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

#### `McpEvidenceRetentionPort.delete_for_job`

- **源码**：`app/retention/ports.py:80`
- **签名**：`def delete_for_job(self: 未显式标注, job_id: str) -> int`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务 ID，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终数量、序号、字节数或版本等整数结果。

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
仅声明接口契约，这里没有具体实现。
```

#### `McpExportAuditRetentionPort.delete_for_job`

- **源码**：`app/retention/ports.py:84`
- **签名**：`def delete_for_job(self: 未显式标注, job_id: str) -> int`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务 ID，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终数量、序号、字节数或版本等整数结果。

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
仅声明接口契约，这里没有具体实现。
```

#### `ResourceReferencePort.count_blob_references`

- **源码**：`app/retention/ports.py:88`
- **签名**：`def count_blob_references(self: 未显式标注, backend: str, object_key: str) -> int`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收模型或检索后端、存储对象键，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终数量、序号、字节数或版本等整数结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `backend` | `str` | 来源、类别、用途、后端、状态或操作原因等控制字段；通常对应有限的业务枚举或审计文本。 |
| `object_key` | `str` | 存储对象键；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`int`
- **语义**：返回整数计数、序号、字节数或退出码；具体含义由函数名决定。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `CheckpointRetentionPort.delete_thread`

- **源码**：`app/retention/ports.py:96`
- **签名**：`def delete_thread(self: 未显式标注, thread_id: str) -> None`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收流程线程 ID，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `thread_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `DeletableBlobStore.delete_if_matches`

- **源码**：`app/retention/ports.py:100`
- **签名**：`def delete_if_matches(self: 未显式标注, object_key: str, expected_sha256: str, expected_size: int) -> bool`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收存储对象键、调用方看到的旧 SHA-256、期望，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `object_key` | `str` | 存储对象键；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `expected_sha256` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |
| `expected_size` | `int` | 调用方观察到的旧身份，用于 stale/CAS 校验，防止覆盖并发更新。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `PathRemover.validate_job_paths`

- **源码**：`app/retention/ports.py:109`
- **签名**：`def validate_job_paths(self: 未显式标注, job: JobRecord, bindings: list[WorkspaceBinding]) -> list[Path]`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务记录、当前处理结果，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终一个经过边界校验的文件或目录路径。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job` | `JobRecord` | 任务、运行、Manifest、记录或证据领域对象；携带关联 ID、状态和内容身份。 |
| `bindings` | `list[WorkspaceBinding]` | `list[WorkspaceBinding]` 元素集合；元素代表的业务对象由参数名 `bindings` 和调用位置确定。 |

**输出**

- **Python 类型**：`list[Path]`
- **语义**：返回解析后的文件或目录路径对象。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `PathRemover.remove_tree`

- **源码**：`app/retention/ports.py:116`
- **签名**：`def remove_tree(self: 未显式标注, path: Path) -> int`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收文件或目录路径，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终数量、序号、字节数或版本等整数结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`int`
- **语义**：返回整数计数、序号、字节数或退出码；具体含义由函数名决定。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `SweepLock.acquire`

- **源码**：`app/retention/ports.py:119`
- **签名**：`def acquire(self: 未显式标注) -> AbstractContextManager[None]`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `AbstractContextManager[None]` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`AbstractContextManager[None]`
- **语义**：返回 `AbstractContextManager[None]` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

### `app/retention/repository.py`

**模块作用**：Retention 审计账本：保存 Plan、确认、逐步 journal 和 hold。

#### `_iso`

- **源码**：`app/retention/repository.py:15`
- **签名**：`def _iso(value: float | None = None) -> str`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `float | None` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。；默认 空值 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `isoformat` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `SqliteRetentionRepository.__init__`

- **源码**：`app/retention/repository.py:24`
- **签名**：`def __init__(self, path: Path)`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收文件或目录路径，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 文件或目录路径 分别保存到同名实例字段。
```

#### `SqliteRetentionRepository._connect`

- **源码**：`app/retention/repository.py:27`
- **签名**：`def _connect(self) -> sqlite3.Connection`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于在固定 MCP Policy、Schema Pin、调用预算和只读职责边界内连接或调用外部能力，并把返回内容转换为可追溯的复现证据，最终标注为 `sqlite3.Connection` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`sqlite3.Connection`
- **语义**：返回 `sqlite3.Connection` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
创建父级目录或父领域对象对应的目录；调用 `connect` 完成该函数的一项辅助处理，并把结果记为 数据库连接；读取数据库记录行，并保存为 记录行；通过数据库连接执行数据查询或命令。
通过数据库连接执行数据查询或命令；通过数据库连接执行数据查询或命令；通过数据库连接执行数据查询或命令；返回数据库连接的当前值。
```

#### `SqliteRetentionRepository.initialize`

- **源码**：`app/retention/repository.py:41`
- **签名**：`def initialize(self) -> None`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

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

#### `SqliteRetentionRepository._plan`

- **源码**：`app/retention/repository.py:80`
- **签名**：`def _plan(row: sqlite3.Row) -> CleanupPlan`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收数据库记录行，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `CleanupPlan` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `row` | `sqlite3.Row` | 数据库记录行；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`CleanupPlan`
- **语义**：返回 `CleanupPlan` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
将外部表示解析为结构化内容，并把结果记为 结构化请求载荷；把新的处理结果追加或合并到结构化请求载荷；复制、序列化或校验结构化领域对象，并返回处理结果。
```

#### `SqliteRetentionRepository.create_plan`

- **源码**：`app/retention/repository.py:100`
- **签名**：`def create_plan(self, plan: CleanupPlan) -> CleanupPlan`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收实验计划，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `CleanupPlan` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `plan` | `CleanupPlan` | 实验计划；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`CleanupPlan`
- **语义**：返回 `CleanupPlan` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
复制、序列化或校验结构化领域对象，并把结果记为 结构化请求载荷。
在上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”中通过数据库连接执行数据查询或命令，退出时自动清理资源。
调用 `get_plan` 读取或查询当前阶段需要的数据，并返回处理结果。
```

#### `SqliteRetentionRepository.get_plan`

- **源码**：`app/retention/repository.py:133`
- **签名**：`def get_plan(self, plan_id: str) -> CleanupPlan`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收实验计划的 ID，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `CleanupPlan` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `plan_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`CleanupPlan`
- **语义**：返回 `CleanupPlan` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
在上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”中调用 `fetchone` 完成该函数的一项辅助处理，并把结果记为 数据库记录行，退出时自动清理资源。
如果数据库记录行为空，就拒绝继续处理并抛出 `RetentionNotFound`，向调用方报告输入或运行失败。
调用 `_plan` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `SqliteRetentionRepository.confirm_plan`

- **源码**：`app/retention/repository.py:143`
- **签名**：`def confirm_plan(self, *, plan_id: str, plan_hash: str) -> CleanupPlan`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收实验计划的 ID、实验计划的 Hash，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `CleanupPlan` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `plan_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `plan_hash` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |

**输出**

- **Python 类型**：`CleanupPlan`
- **语义**：返回 `CleanupPlan` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `time` 完成该函数的一项辅助处理，并把结果记为 当前时间；调用 `_connect` 完成该函数的一项辅助处理，并把结果记为 数据库连接。
先尝试完成以下处理：
    通过数据库连接执行数据查询或命令；读取前一步操作返回对象的当前处理结果，并保存为 发生变化的内容。
    如果发生变化的内容不等于1，就拒绝继续处理并抛出 `RetentionConflict`，向调用方报告输入或运行失败。
    提交数据库连接中已完成的数据变更。
如果出现 `Exception`：
    回滚数据库连接中未完成的数据变更；重新抛出当前异常，保持原始失败信息。
无论成功还是失败，最后都要：
    关闭数据库连接并释放相关资源。
调用 `get_plan` 读取或查询当前阶段需要的数据，并返回处理结果。
```

#### `SqliteRetentionRepository.claim_sweep`

- **源码**：`app/retention/repository.py:171`
- **签名**：`def claim_sweep(self, *, plan_id: str, plan_hash: str) -> CleanupPlan`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收实验计划的 ID、实验计划的 Hash，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `CleanupPlan` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `plan_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `plan_hash` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |

**输出**

- **Python 类型**：`CleanupPlan`
- **语义**：返回 `CleanupPlan` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `time` 完成该函数的一项辅助处理，并把结果记为 当前时间；调用 `_connect` 完成该函数的一项辅助处理，并把结果记为 数据库连接。
先尝试完成以下处理：
    通过数据库连接执行数据查询或命令；调用 `fetchone` 完成该函数的一项辅助处理，并把结果记为 数据库记录行。
    如果数据库记录行为空 或 数据库记录行中的对应字段不等于实验计划的 Hash 或 数据库记录行中的对应字段不大于当前时间 或 数据库记录行中的对应字段不属于{'confirmed', 'failed', 'sweeping'}，就拒绝继续处理并抛出 `RetentionConflict`，向调用方报告输入或运行失败。
    通过数据库连接执行数据查询或命令；提交数据库连接中已完成的数据变更。
如果出现 `Exception`：
    回滚数据库连接中未完成的数据变更；重新抛出当前异常，保持原始失败信息。
无论成功还是失败，最后都要：
    关闭数据库连接并释放相关资源。
调用 `get_plan` 读取或查询当前阶段需要的数据，并返回处理结果。
```

#### `SqliteRetentionRepository.step_completed`

- **源码**：`app/retention/repository.py:205`
- **签名**：`def step_completed(self: 未显式标注, plan_id: str, job_id: str, step_name: str) -> bool`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收实验计划的 ID、复现任务 ID、当前处理结果的名称，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `plan_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `step_name` | `str` | 名为 `step_name` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
在上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”中调用 `fetchone` 完成该函数的一项辅助处理，并把结果记为 数据库记录行，退出时自动清理资源。
返回组合判断结果。
```

#### `SqliteRetentionRepository.record_step`

- **源码**：`app/retention/repository.py:222`
- **签名**：`def record_step(self: 未显式标注, plan_id: str, job_id: str, step_name: str, status: str, detail: str | None) -> None`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收实验计划的 ID、复现任务 ID、当前处理结果的名称、当前状态等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `plan_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `step_name` | `str` | 名为 `step_name` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `status` | `str` | 来源、类别、用途、后端、状态或操作原因等控制字段；通常对应有限的业务枚举或审计文本。 |
| `detail` | `str | None` | 诊断或错误详情；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 空值 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”中通过数据库连接执行数据查询或命令，退出时自动清理资源。
```

#### `SqliteRetentionRepository.list_steps`

- **源码**：`app/retention/repository.py:245`
- **签名**：`def list_steps(self, plan_id: str) -> list[CleanupStep]`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收实验计划的 ID，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `plan_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`list[CleanupStep]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
在上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”中调用 `fetchall` 完成该函数的一项辅助处理，并把结果记为 数据库记录行集合，退出时自动清理资源。
返回当前计算得到的结果。
```

#### `SqliteRetentionRepository.finish_plan`

- **源码**：`app/retention/repository.py:267`
- **签名**：`def finish_plan(self, *, plan_id: str) -> CleanupPlan`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收实验计划的 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `CleanupPlan` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `plan_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`CleanupPlan`
- **语义**：返回 `CleanupPlan` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
在上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”中通过数据库连接执行数据查询或命令，退出时自动清理资源。
调用 `get_plan` 读取或查询当前阶段需要的数据，并返回处理结果。
```

#### `SqliteRetentionRepository.fail_plan`

- **源码**：`app/retention/repository.py:279`
- **签名**：`def fail_plan(self, *, plan_id: str, code: str) -> CleanupPlan`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收实验计划的 ID、待解析或验证的代码，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `CleanupPlan` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `plan_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `code` | `str` | 待解析、执行或断言的代码文本；处理前应处于受控测试/执行边界内。 |

**输出**

- **Python 类型**：`CleanupPlan`
- **语义**：返回 `CleanupPlan` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
在上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”中通过数据库连接执行数据查询或命令，退出时自动清理资源。
调用 `get_plan` 读取或查询当前阶段需要的数据，并返回处理结果。
```

#### `SqliteRetentionRepository.put_hold`

- **源码**：`app/retention/repository.py:291`
- **签名**：`def put_hold(self, *, job_id: str, reason: str, actor: str) -> RetentionHold`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务 ID、基线接受或运行操作原因、审计主体，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终标注为 `RetentionHold` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `reason` | `str` | 来源、类别、用途、后端、状态或操作原因等控制字段；通常对应有限的业务枚举或审计文本。 |
| `actor` | `str` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |

**输出**

- **Python 类型**：`RetentionHold`
- **语义**：返回 `RetentionHold` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `time` 完成该函数的一项辅助处理，并把结果记为 当前时间。
在上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”中通过数据库连接执行数据查询或命令，退出时自动清理资源。
构造并返回 `RetentionHold` 结构化领域对象。
```

#### `SqliteRetentionRepository.delete_hold`

- **源码**：`app/retention/repository.py:312`
- **签名**：`def delete_hold(self, job_id: str) -> bool`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务 ID，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
在上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”中返回比较判断结果，退出时自动清理资源。
```

#### `SqliteRetentionRepository.held_job_ids`

- **源码**：`app/retention/repository.py:322`
- **签名**：`def held_job_ids(self) -> set[str]`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

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

#### `SqliteRetentionRepository.list_holds`

- **源码**：`app/retention/repository.py:329`
- **签名**：`def list_holds(self) -> list[RetentionHold]`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`list[RetentionHold]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
在上下文“调用 `_connect` 完成该函数的一项辅助处理，并把上下文资源交给数据库连接”中调用 `fetchall` 完成该函数的一项辅助处理，并把结果记为 数据库记录行集合，退出时自动清理资源。
返回当前计算得到的结果。
```

### `app/retention/schemas.py`

**模块作用**：Retention Schemas 定义。

#### `StorageSummaryView.from_summary`

- **源码**：`app/retention/schemas.py:65`
- **签名**：`def from_summary(cls, summary: StorageSummary) -> "StorageSummaryView"`
- **作用**：在约束论文复现请求、运行状态、证据和结果结构的契约校验阶段中，该函数接收阶段摘要，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `'StorageSummaryView'` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `cls` | `未显式标注` | 当前类对象，用于类级构造或校验。 |
| `summary` | `StorageSummary` | 阶段摘要；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`'StorageSummaryView'`
- **语义**：返回 `'StorageSummaryView'` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
复制、序列化或校验结构化领域对象，并把结果记为 结构化请求载荷；调用 `cls` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `CleanupPlanView.from_plan`

- **源码**：`app/retention/schemas.py:162`
- **签名**：`def from_plan(cls, plan: CleanupPlan) -> "CleanupPlanView"`
- **作用**：在约束论文复现请求、运行状态、证据和结果结构的契约校验阶段中，该函数接收实验计划，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `'CleanupPlanView'` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `cls` | `未显式标注` | 当前类对象，用于类级构造或校验。 |
| `plan` | `CleanupPlan` | 实验计划；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`'CleanupPlanView'`
- **语义**：返回 `'CleanupPlanView'` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `cls` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `CleanupResultView.from_result`

- **源码**：`app/retention/schemas.py:190`
- **签名**：`def from_result(cls, result: CleanupResult) -> "CleanupResultView"`
- **作用**：在约束论文复现请求、运行状态、证据和结果结构的契约校验阶段中，该函数接收阶段处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `cls` | `未显式标注` | 当前类对象，用于类级构造或校验。 |
| `result` | `CleanupResult` | 前序调用产生的结构化响应、结果或执行结论，供当前函数继续判断或投影。 |

**输出**

- **Python 类型**：`'CleanupResultView'`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `cls` 完成该函数的一项辅助处理，并返回处理结果。
```

### `app/retention/service.py`

**模块作用**：Phase 35 核心服务：Plan/确认/预检/幂等 Sweep。

#### `_NoOpProjectMemoryRetentionPort.active_referenced_job_ids`

- **源码**：`app/retention/service.py:51`
- **签名**：`def active_referenced_job_ids(self) -> set[str]`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`set[str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
构造临时集合、映射或轻量领域对象，并返回处理结果。
```

#### `_NoOpKnowledgeMemoryRetentionPort.active_referenced_job_ids`

- **源码**：`app/retention/service.py:56`
- **签名**：`def active_referenced_job_ids(self) -> set[str]`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`set[str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
构造临时集合、映射或轻量领域对象，并返回处理结果。
```

#### `_NoOpMcpEvidenceRetentionPort.delete_for_job`

- **源码**：`app/retention/service.py:61`
- **签名**：`def delete_for_job(self, job_id: str) -> int`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务 ID，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终数量、序号、字节数或版本等整数结果。

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
移除复现任务 ID中的当前内容；返回固定值 `0`。
```

#### `_NoOpMcpExportAuditRetentionPort.delete_for_job`

- **源码**：`app/retention/service.py:67`
- **签名**：`def delete_for_job(self, job_id: str) -> int`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务 ID，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终数量、序号、字节数或版本等整数结果。

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
移除复现任务 ID中的当前内容；返回固定值 `0`。
```

#### `_canonical`

- **源码**：`app/retention/service.py:71`
- **签名**：`def _canonical(value: object) -> str`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `object` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
将结构化内容序列化或编码为可传输表示，并返回处理结果。
```

#### `_sha256`

- **源码**：`app/retention/service.py:80`
- **签名**：`def _sha256(value: object) -> str`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `object` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回输入内容的 SHA-256 身份摘要，用于完整性校验，不是加密后的正文。

**伪代码**

```text
计算输入内容的 SHA-256 身份摘要，并返回处理结果。
```

#### `_token_hash`

- **源码**：`app/retention/service.py:83`
- **签名**：`def _token_hash(token: str) -> str`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收模型或命令 token，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `token` | `str` | 敏感凭证或其引用；不得写入日志、Prompt 或普通 Artifact。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回内容身份摘要，通常为 SHA-256 十六进制字符串。

**伪代码**

```text
计算输入内容的 SHA-256 身份摘要，并返回处理结果。
```

#### `_workspace_blob_references`

- **源码**：`app/retention/service.py:86`
- **签名**：`def _workspace_blob_references(manifests: list[WorkspaceManifest], backend: str) -> list[BlobReference]`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前处理结果、模型或检索后端，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `manifests` | `list[WorkspaceManifest]` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |
| `backend` | `str` | 来源、类别、用途、后端、状态或操作原因等控制字段；通常对应有限的业务枚举或审计文本。 |

**输出**

- **Python 类型**：`list[BlobReference]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
将 当前处理结果 初始化为空映射，用来收集后续结果。
遍历由当前处理结果组成的集合或迭代器，每次把当前项记为运行或工作区 Manifest：
    遍历当前可迭代输入，每次把当前项记为条目：
        构造 `BlobReference` 结构化领域对象，并把结果记为 待审核的 MCP 能力候选；计算组合多个值形成元组，并保存为 映射键或对象字段名；从当前处理结果读取所需的状态或领域记录，并把结果记为 前一项。
        如果前一项不为空 且 前一项不等于待审核的 MCP 能力候选，就拒绝继续处理并抛出 `RetentionConflict`，向调用方报告输入或运行失败。
        读取待审核的 MCP 能力候选，并保存为 当前处理结果中的对应字段。
按稳定规则整理结果顺序，并返回处理结果。
```

#### `_blob_map`

- **源码**：`app/retention/service.py:112`
- **签名**：`def _blob_map(references: list[BlobReference]) -> dict[tuple[str, str], BlobReference]`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收论文或源码引用证据集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `references` | `list[BlobReference]` | 论文或源码引用证据集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`dict[tuple[str, str], BlobReference]`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
将 阶段处理结果 初始化为空映射，用来收集后续结果。
遍历由论文或源码引用证据集合组成的集合或迭代器，每次把当前项记为当前处理项：
    计算组合多个值形成元组，并保存为 映射键或对象字段名；从阶段处理结果读取所需的状态或领域记录，并把结果记为 已有记录。
    如果已有记录不为空 且 已有记录不等于当前处理项，就拒绝继续处理并抛出 `RetentionConflict`，向调用方报告输入或运行失败。
    读取当前处理项，并保存为 阶段处理结果中的对应字段。
返回阶段处理结果的当前值。
```

#### `StorageQuotaGuard.__init__`

- **源码**：`app/retention/service.py:127`
- **签名**：`def __init__(self, inventory: StorageInventoryService)`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `inventory` | `StorageInventoryService` | 名为 `inventory` 的 `StorageInventoryService` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 当前处理结果 分别保存到同名实例字段。
```

#### `StorageQuotaGuard.assert_can_submit`

- **源码**：`app/retention/service.py:130`
- **签名**：`def assert_can_submit(self) -> None`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `summarize` 完成该函数的一项辅助处理，并把结果记为 阶段摘要。
如果当前处理结果等于'hard'，就拒绝继续处理并抛出 `StorageCapacityExceeded`，向调用方报告输入或运行失败。
```

#### `RetentionService.__init__`

- **源码**：`app/retention/service.py:139`
- **签名**：`def __init__(self: 未显式标注, policy: RetentionPolicy, repository: SqliteRetentionRepository, jobs: JobRetentionPort, artifacts: ArtifactRetentionPort, chats: ChatRetentionPort, notifications: NotificationRetentionPort, resources: ResourceReferencePort, checkpoints: CheckpointRetentionPort, blob_store: DeletableBlobStore | None, path_remover: PathRemover, inventory: StorageInventoryService, selected_blob_backend: str, destructive_supported: bool, sweep_lock: SweepLock, failure_memory: FailureMemoryRetentionPort, project_memory: ProjectMemoryRetentionPort | None, knowledge_memory: KnowledgeMemoryRetentionPort | None, mcp_evidence: McpEvidenceRetentionPort | None, mcp_export_audit: McpExportAuditRetentionPort | None) -> None（隐式）`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收安全策略、持久化仓库、复现任务记录集合、当前处理结果等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `policy` | `RetentionPolicy` | 安全策略；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `repository` | `SqliteRetentionRepository` | 持久化或目录访问端口；负责读取、CAS 更新或 Artifact 定位。 |
| `jobs` | `JobRetentionPort` | 复现任务记录集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `artifacts` | `ArtifactRetentionPort` | 名为 `artifacts` 的 `ArtifactRetentionPort` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `chats` | `ChatRetentionPort` | 名为 `chats` 的 `ChatRetentionPort` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `notifications` | `NotificationRetentionPort` | 名为 `notifications` 的 `NotificationRetentionPort` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `resources` | `ResourceReferencePort` | 复现输入资源集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `checkpoints` | `CheckpointRetentionPort` | 名为 `checkpoints` 的 `CheckpointRetentionPort` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `blob_store` | `DeletableBlobStore | None` | 名为 `blob_store` 的 `DeletableBlobStore | None` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `path_remover` | `PathRemover` | 名为 `path_remover` 的 `PathRemover` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `inventory` | `StorageInventoryService` | 名为 `inventory` 的 `StorageInventoryService` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `selected_blob_backend` | `str` | 名为 `selected_blob_backend` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `destructive_supported` | `bool` | 布尔条件或能力开关，用于控制流程分支。 |
| `sweep_lock` | `SweepLock` | 名为 `sweep_lock` 的 `SweepLock` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `failure_memory` | `FailureMemoryRetentionPort` | 名为 `failure_memory` 的 `FailureMemoryRetentionPort` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `project_memory` | `ProjectMemoryRetentionPort | None` | 名为 `project_memory` 的 `ProjectMemoryRetentionPort | None` 领域输入；用于当前函数的业务处理，具体约束见校验分支。；默认 空值 |
| `knowledge_memory` | `KnowledgeMemoryRetentionPort | None` | 名为 `knowledge_memory` 的 `KnowledgeMemoryRetentionPort | None` 领域输入；用于当前函数的业务处理，具体约束见校验分支。；默认 空值 |
| `mcp_evidence` | `McpEvidenceRetentionPort | None` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。；默认 空值 |
| `mcp_export_audit` | `McpExportAuditRetentionPort | None` | 名为 `mcp_export_audit` 的 `McpExportAuditRetentionPort | None` 领域输入；用于当前函数的业务处理，具体约束见校验分支。；默认 空值 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 安全策略、持久化仓库、复现任务记录集合、当前处理结果、当前处理结果、当前处理结果、复现输入资源集合、当前处理结果、Blob 内容存储、路径、当前处理结果、Blob 内容、当前处理结果、当前处理结果、失败记忆 分别保存到同名实例字段；计算计算当前表达式的结果，并保存为 项目记忆；计算计算当前表达式的结果，并保存为 记忆；计算计算当前表达式的结果，并保存为 证据。
计算计算当前表达式的结果，并保存为 当前处理结果；调用 `initialize` 完成该函数的一项辅助处理。
```

#### `RetentionService.storage_summary`

- **源码**：`app/retention/service.py:190`
- **签名**：`def storage_summary(self) -> StorageSummary`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `StorageSummary` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`StorageSummary`
- **语义**：返回 `StorageSummary` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `summarize` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `RetentionService._blocked_job_ids`

- **源码**：`app/retention/service.py:193`
- **签名**：`def _blocked_job_ids(self) -> set[str]`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`set[str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
返回当前计算得到的结果。
```

#### `RetentionService.create_hold`

- **源码**：`app/retention/service.py:201`
- **签名**：`def create_hold(self, *, job_id: str, reason: str, actor: str) -> RetentionHold`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务 ID、基线接受或运行操作原因、审计主体，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `RetentionHold` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `reason` | `str` | 来源、类别、用途、后端、状态或操作原因等控制字段；通常对应有限的业务枚举或审计文本。 |
| `actor` | `str` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |

**输出**

- **Python 类型**：`RetentionHold`
- **语义**：返回 `RetentionHold` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
从复现任务记录集合读取所需的状态或领域记录；调用 `put_hold` 持久化或更新当前领域数据，并返回处理结果。
```

#### `RetentionService.delete_hold`

- **源码**：`app/retention/service.py:209`
- **签名**：`def delete_hold(self, job_id: str) -> bool`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务 ID，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
调用 `delete_hold` 持久化或更新当前领域数据，并返回处理结果。
```

#### `RetentionService.list_holds`

- **源码**：`app/retention/service.py:212`
- **签名**：`def list_holds(self) -> list[RetentionHold]`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`list[RetentionHold]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
调用 `list_holds` 读取或查询当前阶段需要的数据，并返回处理结果。
```

#### `RetentionService._target`

- **源码**：`app/retention/service.py:215`
- **签名**：`def _target(self, job: JobRecord) -> JobCleanupTarget`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务记录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `JobCleanupTarget` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job` | `JobRecord` | 任务、运行、Manifest、记录或证据领域对象；携带关联 ID、状态和内容身份。 |

**输出**

- **Python 类型**：`JobCleanupTarget`
- **语义**：返回 `JobCleanupTarget` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `list_workspace_bindings_for_retention` 读取或查询当前阶段需要的数据，并把结果记为 该调用返回的结果；调用 `list_workspace_manifests_for_retention` 读取或查询当前阶段需要的数据，并把结果记为 该调用返回的结果；调用 `validate_job_paths` 校验当前输入或状态，并把结果记为 文件或目录路径集合；遍历并筛选输入，将整理后的结果保存为 当前处理结果。
调用 `list_blob_references_for_job` 读取或查询当前阶段需要的数据，并把结果记为 Artifact集合；调用 `_workspace_blob_references` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `sum` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；构造并返回 `JobCleanupTarget` 结构化领域对象。
```

#### `RetentionService.create_plan`

- **源码**：`app/retention/service.py:255`
- **签名**：`def create_plan(self) -> CleanupPlan`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `CleanupPlan` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`CleanupPlan`
- **语义**：返回 `CleanupPlan` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
计算组合或计算已有值，并保存为 当前处理结果；调用 `_blocked_job_ids` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `list_retention_candidates` 读取或查询当前阶段需要的数据，并把结果记为 候选结果集合；读取当前输入内容中的对应字段，并保存为 选中的候选项。
读取当前时间，作为状态变更的统一时间戳，并把结果记为 已创建记录；计算组合或计算已有值，并保存为 当前处理结果；计算根据字段和固定文本生成格式化文本，并保存为 实验计划的 ID；计算按字段初始化键值映射，并保存为 Hash。
构造 `CleanupPlan` 结构化领域对象，并把结果记为 实验计划；调用 `create_plan` 组装当前阶段需要的领域对象，并返回处理结果。
```

#### `RetentionService.get_plan`

- **源码**：`app/retention/service.py:283`
- **签名**：`def get_plan(self, plan_id: str) -> CleanupPlan`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收实验计划的 ID，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `CleanupPlan` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `plan_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`CleanupPlan`
- **语义**：返回 `CleanupPlan` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `get_plan` 读取或查询当前阶段需要的数据，并返回处理结果。
```

#### `RetentionService.confirm_plan`

- **源码**：`app/retention/service.py:286`
- **签名**：`def confirm_plan(self, *, plan_id: str, plan_hash: str) -> CleanupPlan`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收实验计划的 ID、实验计划的 Hash，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `CleanupPlan` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `plan_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `plan_hash` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |

**输出**

- **Python 类型**：`CleanupPlan`
- **语义**：返回 `CleanupPlan` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `confirm_plan` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `RetentionService._assert_plan_hash`

- **源码**：`app/retention/service.py:292`
- **签名**：`def _assert_plan_hash(self, plan: CleanupPlan) -> None`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收实验计划，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `plan` | `CleanupPlan` | 实验计划；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算按字段初始化键值映射，并保存为 结构化请求载荷。
如果辅助操作“调用 `_sha256` 计算内容身份、分数或派生结果”的结果不等于实验计划的 Hash，就拒绝继续处理并抛出 `RetentionConflict`，向调用方报告输入或运行失败。
```

#### `RetentionService._assert_target_current`

- **源码**：`app/retention/service.py:303`
- **签名**：`def _assert_target_current(self, target: JobCleanupTarget) -> None`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收待定位的代码对象或业务目标，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `target` | `JobCleanupTarget` | 待定位的代码对象或业务目标；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
从复现任务记录集合读取所需的状态或领域记录，并把结果记为 当前值；计算组合多个值形成元组，并保存为 对象身份；计算组合多个值形成元组，并保存为 期望值。
如果对象身份不等于期望值 或 当前状态不属于任务集合，就拒绝继续处理并抛出 `RetentionConflict`，向调用方报告输入或运行失败。
调用 `list_workspace_bindings_for_retention` 读取或查询当前阶段需要的数据，并把结果记为 该调用返回的结果；调用 `validate_job_paths` 校验当前输入或状态，并把结果记为 文件或目录路径集合；遍历并筛选输入，将整理后的结果保存为 当前处理结果；遍历并筛选输入，将整理后的结果保存为 当前集合。
如果当前处理结果不等于当前集合，就拒绝继续处理并抛出 `RetentionConflict`，向调用方报告输入或运行失败。
遍历并筛选输入，将整理后的结果保存为 当前集合；遍历并筛选输入，将整理后的结果保存为 当前处理结果。
如果当前集合不等于当前处理结果，就拒绝继续处理并抛出 `RetentionConflict`，向调用方报告输入或运行失败。
移除文件或目录路径集合中的当前内容；调用 `list_blob_references_for_job` 读取或查询当前阶段需要的数据，并把结果记为 当前集合；调用 `list_workspace_manifests_for_retention` 读取或查询当前阶段需要的数据，并把结果记为 当前集合；调用 `_workspace_blob_references` 完成该函数的一项辅助处理，并把结果记为 当前集合。
如果辅助操作“调用 `_blob_map` 完成该函数的一项辅助处理”的结果不等于辅助操作“调用 `_blob_map` 完成该函数的一项辅助处理”的结果，就拒绝继续处理并抛出 `RetentionConflict`，向调用方报告输入或运行失败。
如果辅助操作“调用 `_blob_map` 完成该函数的一项辅助处理”的结果不等于辅助操作“调用 `_blob_map` 完成该函数的一项辅助处理”的结果，就拒绝继续处理并抛出 `RetentionConflict`，向调用方报告输入或运行失败。
```

#### `RetentionService._preflight`

- **源码**：`app/retention/service.py:365`
- **签名**：`def _preflight(self, plan: CleanupPlan) -> None`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收实验计划，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `plan` | `CleanupPlan` | 实验计划；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
如果“当前处理结果有值或为真”不成立，就拒绝继续处理并抛出 `RetentionBackendUnsupported`，向调用方报告输入或运行失败。
如果本地集合有值或为真 且 Blob 内容存储为空，就拒绝继续处理并抛出 `RetentionBackendUnsupported`，向调用方报告输入或运行失败。
调用 `_assert_plan_hash` 完成该函数的一项辅助处理；调用 `_blocked_job_ids` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
遍历当前可迭代输入，每次把当前项记为待定位的代码对象或业务目标：
    如果当前可迭代输入中存在满足“模型或检索后端不等于Blob 内容”的项，就拒绝继续处理并抛出 `RetentionBackendUnsupported`，向调用方报告输入或运行失败。
    如果复现任务 ID属于当前处理结果，就拒绝继续处理并抛出 `RetentionConflict`，向调用方报告输入或运行失败。
    如果“调用 `step_completed` 完成该函数的一项辅助处理”后得到肯定结果，就跳过本轮剩余处理，直接进入下一轮。
    先尝试完成以下处理：
        调用 `_assert_target_current` 完成该函数的一项辅助处理。
    如果出现 `JobNotFoundError`：
        计算组合多个值形成元组，并保存为 当前处理结果。
        如果“检查由当前处理结果组成的集合或迭代器中是否全部满足““调用 `step_completed` 完成该函数的一项辅助处理”后得到肯定结果”的项”后未得到肯定结果，就拒绝继续处理并抛出 `RetentionConflict`，向调用方报告输入或运行失败。
        调用 `record_step` 完成该函数的一项辅助处理。
```

#### `RetentionService._run_step`

- **源码**：`app/retention/service.py:421`
- **签名**：`def _run_step(self: 未显式标注, plan_id: str, job_id: str, step_name: str, operation: 未显式标注) -> object | None`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收实验计划的 ID、复现任务 ID、当前处理结果的名称、MCP 业务操作名称，用于驱动或监督一次论文复现运行，记录命令、工作目录、资源使用、状态迁移和失败原因，最终标注为 `object | None` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `plan_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `step_name` | `str` | 名为 `step_name` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `operation` | `未显式标注` | MCP 业务操作名称；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`object | None`
- **语义**：返回 `object | None` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果“调用 `step_completed` 完成该函数的一项辅助处理”后得到肯定结果，就返回固定值 `空值`。
先尝试完成以下处理：
    调用 `operation` 完成该函数的一项辅助处理，并把结果记为 当前字段值；调用 `record_step` 完成该函数的一项辅助处理；返回当前字段值的当前值。
如果出现 `Exception`并把异常保存为捕获的异常对象：
    调用 `record_step` 完成该函数的一项辅助处理；重新抛出当前异常，保持原始失败信息。
```

#### `RetentionService._remove_paths`

- **源码**：`app/retention/service.py:455`
- **签名**：`def _remove_paths(self, target: JobCleanupTarget) -> int`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收待定位的代码对象或业务目标，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终数量、序号、字节数或版本等整数结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `target` | `JobCleanupTarget` | 待定位的代码对象或业务目标；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`int`
- **语义**：返回整数计数、序号、字节数或退出码；具体含义由函数名决定。

**伪代码**

```text
从复现任务记录集合读取所需的状态或领域记录，并把结果记为 复现任务记录；调用 `list_workspace_bindings_for_retention` 读取或查询当前阶段需要的数据，并把结果记为 该调用返回的结果；调用 `validate_job_paths` 校验当前输入或状态，并把结果记为 受控扫描根目录集合；调用 `sum` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `RetentionService._live_blob_references`

- **源码**：`app/retention/service.py:461`
- **签名**：`def _live_blob_references(self, blob: BlobReference) -> int`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收Blob 内容，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终数量、序号、字节数或版本等整数结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `blob` | `BlobReference` | 名为 `blob` 的 `BlobReference` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`int`
- **语义**：返回整数计数、序号、字节数或退出码；具体含义由函数名决定。

**伪代码**

```text
返回当前计算得到的结果。
```

#### `RetentionService._result_from_journal`

- **源码**：`app/retention/service.py:476`
- **签名**：`def _result_from_journal(self, plan: CleanupPlan) -> CleanupResult`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收实验计划，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `plan` | `CleanupPlan` | 实验计划；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`CleanupResult`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `list_steps` 读取或查询当前阶段需要的数据，并把结果记为 该调用返回的结果；计算使用固定配置或常量值，并保存为 当前处理结果；计算使用固定配置或常量值，并保存为 当前处理结果；计算使用固定配置或常量值，并保存为 当前处理结果。
将 当前处理结果 初始化为空去重集合，用来收集后续结果。
遍历由当前处理结果组成的集合或迭代器，每次把当前项记为当前处理结果：
    如果当前状态不等于'completed'，就跳过本轮剩余处理，直接进入下一轮。
    将外部表示解析为结构化内容，并把结果记为 诊断或错误详情。
    如果当前处理结果的名称等于'filesystem'：
        从诊断或错误详情读取所需的状态或领域记录，并把结果记为 当前字段值；将新的计算结果累加或合并到当前处理结果。
    否则：
        如果当前处理结果的名称等于'job_metadata'：
            把复现任务 ID追加或合并到当前处理结果。
        否则：
            如果“检查当前处理结果的名称是否满足文本匹配条件”后得到肯定结果：
                如果辅助操作“从诊断或错误详情读取所需的状态或领域记录”的结果是真：
                    将新的计算结果累加或合并到当前处理结果；将新的计算结果累加或合并到当前处理结果。
                否则：
                    如果辅助操作“调用 `int` 完成该函数的一项辅助处理”的结果大于0，就将新的计算结果累加或合并到当前处理结果。
构造并返回 `CleanupResult` 结构化领域对象。
```

#### `RetentionService.sweep`

- **源码**：`app/retention/service.py:506`
- **签名**：`def sweep(self, *, plan_id: str, plan_hash: str) -> CleanupResult`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收实验计划的 ID、实验计划的 Hash，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `plan_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `plan_hash` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |

**输出**

- **Python 类型**：`CleanupResult`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
进入上下文“调用 `acquire` 完成该函数的一项辅助处理”，退出时自动清理资源：
    调用 `get_plan` 读取或查询当前阶段需要的数据，并把结果记为 已有记录。
    如果实验计划的 Hash不等于实验计划的 Hash，就拒绝继续处理并抛出 `RetentionConflict`，向调用方报告输入或运行失败。
    如果当前状态等于'completed'，就调用 `_result_from_journal` 完成该函数的一项辅助处理，并返回处理结果。
    调用 `_sweep_locked` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `RetentionService._sweep_locked`

- **源码**：`app/retention/service.py:515`
- **签名**：`def _sweep_locked(self: 未显式标注, plan_id: str, plan_hash: str) -> CleanupResult`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收实验计划的 ID、实验计划的 Hash，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `plan_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `plan_hash` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |

**输出**

- **Python 类型**：`CleanupResult`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `claim_sweep` 完成该函数的一项辅助处理，并把结果记为 实验计划。
先尝试完成以下处理：
    调用 `_preflight` 完成该函数的一项辅助处理；调用 `_blob_map` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
    遍历当前可迭代输入，每次把当前项记为待定位的代码对象或业务目标：
        调用 `_run_step` 完成该函数的一项辅助处理；调用 `_run_step` 完成该函数的一项辅助处理；调用 `_run_step` 完成该函数的一项辅助处理；调用 `_run_step` 完成该函数的一项辅助处理。
        调用 `_run_step` 完成该函数的一项辅助处理；调用 `_run_step` 完成该函数的一项辅助处理；调用 `_run_step` 完成该函数的一项辅助处理；调用 `_run_step` 完成该函数的一项辅助处理。
    遍历辅助操作产生的可迭代结果（调用 `values` 完成该函数的一项辅助处理），每次把当前项记为Blob 内容：
        计算组合或计算已有值，并保存为 当前处理结果的名称。
        如果“调用 `step_completed` 完成该函数的一项辅助处理”后得到肯定结果，就跳过本轮剩余处理，直接进入下一轮。
        调用 `_live_blob_references` 完成该函数的一项辅助处理，并把结果记为 论文或源码引用证据集合。
        如果论文或源码引用证据集合大于0 或 “本地集合有值或为真”不成立，就调用 `record_step` 完成该函数的一项辅助处理；跳过本轮剩余处理，直接进入下一轮。
        断言Blob 内容存储不为空；不满足就终止当前测试或流程；调用 `delete_if_matches` 持久化或更新当前领域数据，并把结果记为 该调用返回的结果；调用 `record_step` 完成该函数的一项辅助处理。
    调用 `finish_plan` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `_result_from_journal` 完成该函数的一项辅助处理，并返回处理结果。
如果出现 `Exception`并把异常保存为捕获的异常对象：
    调用 `fail_plan` 完成该函数的一项辅助处理；重新抛出当前异常，保持原始失败信息。
```

### `app/run_evidence/reader.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `RunEvidenceJobReader.get`

- **源码**：`app/run_evidence/reader.py:29`
- **签名**：`def get(self, job_id: str) -> JobRecord`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`JobRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `RunEvidenceJobReader.get_workspace_manifest`

- **源码**：`app/run_evidence/reader.py:32`
- **签名**：`def get_workspace_manifest(self: 未显式标注, manifest_id: str) -> WorkspaceManifest`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收运行或工作区 Manifest的 ID，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `manifest_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`WorkspaceManifest`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `VerifiedRunEvidenceReader.__init__`

- **源码**：`app/run_evidence/reader.py:42`
- **签名**：`def __init__(self: 未显式标注, jobs: RunEvidenceJobReader, artifact_catalog: ArtifactCatalog, max_manifest_bytes: int, max_artifacts: int) -> None`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务记录集合、Artifact、最大运行或工作区 Manifest的字节内容、最大当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `jobs` | `RunEvidenceJobReader` | 复现任务记录集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `artifact_catalog` | `ArtifactCatalog` | 名为 `artifact_catalog` 的 `ArtifactCatalog` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `max_manifest_bytes` | `int` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |
| `max_artifacts` | `int` | 名为 `max_artifacts` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 复现任务记录集合、Artifact、最大运行或工作区 Manifest的字节内容、最大当前处理结果 分别保存到同名实例字段。
```

#### `VerifiedRunEvidenceReader._require_terminal`

- **源码**：`app/run_evidence/reader.py:56`
- **签名**：`def _require_terminal(job: JobRecord) -> None`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务记录，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `job` | `JobRecord` | 任务、运行、Manifest、记录或证据领域对象；携带关联 ID、状态和内容身份。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
如果当前状态不属于任务集合，就拒绝继续处理并抛出 `RunEvidenceConflictError`，向调用方报告输入或运行失败。
```

#### `VerifiedRunEvidenceReader._validate_workspace`

- **源码**：`app/run_evidence/reader.py:63`
- **签名**：`def _validate_workspace(job: JobRecord, manifest: WorkspaceManifest) -> None`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务记录、运行或工作区 Manifest，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `job` | `JobRecord` | 任务、运行、Manifest、记录或证据领域对象；携带关联 ID、状态和内容身份。 |
| `manifest` | `WorkspaceManifest` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
先尝试完成以下处理：
    调用 `validate_manifest_hash` 校验当前输入或状态。
如果出现 `WorkspaceIntegrityError`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `RunEvidenceIntegrityError`，向调用方报告输入或运行失败。
如果运行或工作区 Manifest的 ID不等于Manifest的 ID，就拒绝继续处理并抛出 `RunEvidenceIntegrityError`，向调用方报告输入或运行失败。
如果复现任务 ID不等于复现任务 ID 或 本次复现运行 ID不等于本次复现运行 ID，就拒绝继续处理并抛出 `RunEvidenceIntegrityError`，向调用方报告输入或运行失败。
如果工作区生成代次不等于Manifest，就拒绝继续处理并抛出 `RunEvidenceIntegrityError`，向调用方报告输入或运行失败。
```

#### `VerifiedRunEvidenceReader._list_artifacts`

- **源码**：`app/run_evidence/reader.py:86`
- **签名**：`def _list_artifacts(self, job: JobRecord) -> list[ArtifactView]`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务记录，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job` | `JobRecord` | 任务、运行、Manifest、记录或证据领域对象；携带关联 ID、状态和内容身份。 |

**输出**

- **Python 类型**：`list[ArtifactView]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
从Artifact读取所需的状态或领域记录，并把结果记为 Artifact 视图集合。
如果Artifact 视图集合 的长度大于最大当前处理结果，就拒绝继续处理并抛出 `RunEvidenceLimitExceededError`，向调用方报告输入或运行失败。
遍历并筛选输入，将整理后的结果保存为 当前处理结果；遍历并筛选输入，将整理后的结果保存为 文件或目录路径集合。
如果当前处理结果 的长度不等于辅助操作“构造临时集合、映射或轻量领域对象”的结果 的长度 或 文件或目录路径集合 的长度不等于辅助操作“构造临时集合、映射或轻量领域对象”的结果 的长度，就拒绝继续处理并抛出 `RunEvidenceIntegrityError`，向调用方报告输入或运行失败。
如果由Artifact 视图集合组成的集合或迭代器中存在满足“本次复现运行 ID不等于本次复现运行 ID”的项，就拒绝继续处理并抛出 `RunEvidenceIntegrityError`，向调用方报告输入或运行失败。
按稳定规则整理结果顺序，并返回处理结果。
```

#### `VerifiedRunEvidenceReader._read_manifest_blob`

- **源码**：`app/run_evidence/reader.py:104`
- **签名**：`def _read_manifest_blob(self: 未显式标注, job: JobRecord, views: list[ArtifactView]) -> tuple[ArtifactView, dict]`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务记录、Artifact 视图集合，用于读取并整理论文、源码或运行产物，把原始输入转换成带位置和身份信息的结构化证据，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job` | `JobRecord` | 任务、运行、Manifest、记录或证据领域对象；携带关联 ID、状态和内容身份。 |
| `views` | `list[ArtifactView]` | Artifact 视图集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`tuple[ArtifactView, dict]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
遍历并筛选输入，将整理后的结果保存为 当前处理结果。
如果当前处理结果 的长度不等于1，就拒绝继续处理并抛出 `RunEvidenceNotFoundError`，向调用方报告输入或运行失败。
读取当前处理结果中的对应字段，并保存为 视图。
如果对象大小的字节内容大于最大运行或工作区 Manifest的字节内容，就拒绝继续处理并抛出 `RunEvidenceLimitExceededError`，向调用方报告输入或运行失败。
调用 `open` 完成该函数的一项辅助处理，并把结果记为 已打开资源。
先尝试完成以下处理：
    读取工具或组件描述信息，并保存为 工具或组件描述信息；读取当前处理结果，并保存为 后续步骤使用的结果；计算计算当前表达式的结果，并保存为 身份集合。
    如果身份集合为空或为假，就拒绝继续处理并抛出 `RunEvidenceIntegrityError`，向调用方报告输入或运行失败。
    调用 `read` 完成该函数的一项辅助处理，并把结果记为 原始内容。
无论成功还是失败，最后都要：
    关闭请求正文并释放相关资源。
如果原始内容 的长度大于最大运行或工作区 Manifest的字节内容 或 原始内容 的长度不等于对象大小的字节内容，就拒绝继续处理并抛出 `RunEvidenceIntegrityError`，向调用方报告输入或运行失败。
如果辅助操作“计算输入内容的 SHA-256 身份摘要”的结果不等于内容 SHA-256，就拒绝继续处理并抛出 `RunEvidenceIntegrityError`，向调用方报告输入或运行失败。
先尝试完成以下处理：
    将外部表示解析为结构化内容，并把结果记为 结构化请求载荷。
如果出现 `(UnicodeDecodeError, json.JSONDecodeError)`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `RunEvidenceIntegrityError`，向调用方报告输入或运行失败。
如果“计算数量、边界或类型判断结果”后未得到肯定结果，就拒绝继续处理并抛出 `RunEvidenceConflictError`，向调用方报告输入或运行失败。
从结构化请求载荷读取所需的状态或领域记录，并把结果记为 记录版本号。
如果“计算数量、边界或类型判断结果”后未得到肯定结果 或 记录版本号小于4，就拒绝继续处理并抛出 `RunEvidenceConflictError`，向调用方报告输入或运行失败。
如果辅助操作“从结构化请求载荷读取所需的状态或领域记录”的结果不等于复现任务 ID，就拒绝继续处理并抛出 `RunEvidenceIntegrityError`，向调用方报告输入或运行失败。
如果辅助操作“从结构化请求载荷读取所需的状态或领域记录”的结果不等于本次复现运行 ID，就拒绝继续处理并抛出 `RunEvidenceIntegrityError`，向调用方报告输入或运行失败。
返回当前构造的顺序或去重集合。
```

#### `VerifiedRunEvidenceReader.read`

- **源码**：`app/run_evidence/reader.py:183`
- **签名**：`def read(self, job_id: str) -> VerifiedRunEvidence`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收复现任务 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `VerifiedRunEvidence` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`VerifiedRunEvidence`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
从复现任务记录集合读取所需的状态或领域记录，并把结果记为 复现任务记录；调用 `_require_terminal` 完成该函数的一项辅助处理；从复现任务记录集合读取所需的状态或领域记录，并把结果记为 本次复现工作区；调用 `_validate_workspace` 校验当前输入或状态。
调用 `_list_artifacts` 读取或查询当前阶段需要的数据，并把结果记为 该调用返回的结果；调用 `_read_manifest_blob` 读取或查询当前阶段需要的数据，并把结果记为 多个解包结果；构造并返回 `VerifiedRunEvidence` 结构化领域对象。
```

### `app/service_host.py`

**模块作用**：Phase 30 单进程 Stack Host。

#### `ServiceHost.__init__`

- **源码**：`app/service_host.py:20`
- **签名**：`def __init__(self: 未显式标注, job_worker_factory: Callable[[], object], resource_worker_factory: Callable[[], object], resource_poll_seconds: float) -> None（隐式）`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收任务、资源、资源集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_worker_factory` | `Callable[[], object]` | 可调用依赖；其参数和返回契约由类型标注限定。 |
| `resource_worker_factory` | `Callable[[], object]` | 可调用依赖；其参数和返回契约由类型标注限定。 |
| `resource_poll_seconds` | `float` | 名为 `resource_poll_seconds` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 任务、资源、资源集合 分别保存到同名实例字段；构造 `Event` 结构化领域对象，并把结果记为 事件；将 当前处理结果 初始化为空列表，用来收集后续结果；计算使用固定配置或常量值，并保存为 任务。
计算使用固定配置或常量值，并保存为 资源；计算使用固定配置或常量值，并保存为 失败；构造 `Lock` 结构化领域对象，并把结果记为 失败。
```

#### `ServiceHost._run_worker`

- **源码**：`app/service_host.py:39`
- **签名**：`def _run_worker(self: 未显式标注, name: str, worker: 未显式标注, **kwargs: 未显式标注) -> None`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收对象名称、后台复现工作器、函数关键字参数映射，用于驱动或监督一次论文复现运行，记录命令、工作目录、资源使用、状态迁移和失败原因，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `name` | `str` | 对象名称；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `worker` | `未显式标注` | 后台复现工作器；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `**kwargs` | `未显式标注` | 额外关键字参数映射。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
先尝试完成以下处理：
    调用 `run_forever` 完成该函数的一项辅助处理。
如果出现 `Exception`并把异常保存为捕获的异常对象：
    调用 `exception` 完成该函数的一项辅助处理。
    在上下文“读取失败的当前值”中把传入参数保存到实例字段（捕获的异常 → 失败），退出时自动清理资源。
    构造临时集合、映射或轻量领域对象。
```

#### `ServiceHost.readiness`

- **源码**：`app/service_host.py:56`
- **签名**：`def readiness(self) -> str`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
进入上下文“读取失败的当前值”，退出时自动清理资源：
    如果失败不为空，就返回固定值 `'not_ready'`。
如果“当前处理结果有值或为真”不成立 或 当前可迭代输入中存在满足““调用 `is_alive` 校验当前输入或状态”后未得到肯定结果”的项，就返回固定值 `'not_ready'`。
返回固定值 `'ready'`。
```

#### `ServiceHost.start`

- **源码**：`app/service_host.py:67`
- **签名**：`def start(self) -> None`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `job_worker_factory` 完成该函数的一项辅助处理，并把结果记为 任务；调用 `resource_worker_factory` 完成该函数的一项辅助处理，并把结果记为 资源；计算初始化顺序集合，并保存为 当前处理结果。
遍历当前可迭代输入，每次把当前项记为当前处理结果，然后调用 `start` 完成该函数的一项辅助处理。
```

#### `ServiceHost.stop`

- **源码**：`app/service_host.py:101`
- **签名**：`def stop(self: 未显式标注, timeout_seconds: float) -> None`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收等待超时时间（秒），用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `timeout_seconds` | `float` | 超时或截止时间限制；用于防止等待/搜索/执行无限持续。；默认 15.0 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造临时集合、映射或轻量领域对象。
遍历当前可迭代输入，每次把当前项记为当前处理结果，然后调用 `join` 完成该函数的一项辅助处理。
遍历并筛选输入，将整理后的结果保存为 当前处理结果。
如果当前处理结果有值或为真，就拒绝继续处理并抛出 `RuntimeError`，向调用方报告输入或运行失败。
```

### `app/web.py`

**模块作用**：Phase 30 SPA 静态文件托管。

#### `SpaStaticFiles.get_response`

- **源码**：`app/web.py:20`
- **签名**：`async def get_response(self: 未显式标注, path: str, scope: 未显式标注) -> Response`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收文件或目录路径、查询或授权作用域，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `path` | `str` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |
| `scope` | `未显式标注` | 查询或授权作用域；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`Response`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
先尝试完成以下处理：
    等待异步处理完成，并把结果记为 结构化响应。
如果出现 `HTTPException`并把异常保存为捕获的异常对象：
    如果状态不等于404 或 前一步操作返回对象的文件扩展名或文本后缀有值或为真，就重新抛出当前异常，保持原始失败信息。
    返回当前计算得到的结果。
如果状态等于404 且 “前一步操作返回对象的文件扩展名或文本后缀有值或为真”不成立，就返回当前计算得到的结果。
返回结构化响应的当前值。
```

#### `mount_web_ui`

- **源码**：`app/web.py:47`
- **签名**：`def mount_web_ui(app: FastAPI, dist_dir: Path, required: bool) -> None`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前处理结果、当前处理结果的目录、当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `app` | `FastAPI` | 名为 `app` 的 `FastAPI` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `dist_dir` | `Path` | 已经解析的文件或目录路径对象；后续操作仍需遵守仓库/工作区边界。 |
| `required` | `bool` | 布尔条件或能力开关，用于控制流程分支。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
将辅助操作“将当前处理结果的目录规范化为受控的绝对路径”的结果规范化为受控的绝对路径，并把结果记为 解析后的值；计算组合或计算已有值，并保存为 当前候选项的索引。
如果“检查当前候选项的索引的文件系统属性”后未得到肯定结果：
    如果当前处理结果有值或为真，就拒绝继续处理并抛出 `RuntimeError`，向调用方报告输入或运行失败。
    结束当前函数，不返回业务值。
调用 `mount` 完成该函数的一项辅助处理。
```

### `tests/helpers/comparison.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `make_snapshot`

- **源码**：`tests/helpers/comparison.py:17`
- **签名**：`def make_snapshot(job_id: str, run_id: str, paper_sha256: str, job_status: str, command: str) -> RunSnapshot`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收复现任务 ID、本次复现运行 ID、论文的 SHA-256、任务状态等输入，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `RunSnapshot` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `run_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `paper_sha256` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。；默认 'a' × 64 |
| `job_status` | `str` | 名为 `job_status` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。；默认 'succeeded' |
| `command` | `str` | 待展示、校验或执行的命令文本/结构化命令；仅进入 Executor 路径后才可能产生执行副作用。；默认 'python train.py --batch-size 8' |

**输出**

- **Python 类型**：`RunSnapshot`
- **语义**：返回 `RunSnapshot` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造 `RunSnapshot` 结构化领域对象，并把结果记为 草稿对象；复制、序列化或校验结构化领域对象，并返回处理结果。
```

#### `make_report`

- **源码**：`tests/helpers/comparison.py:66`
- **签名**：`def make_report(created_at: str) -> ComparisonReport`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收创建时间，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `ComparisonReport` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `created_at` | `str` | 时间值或可注入时钟，用于排序、过期、租约或可重复测试。；默认 '2026-08-09T00:00:00+00:00' |

**输出**

- **Python 类型**：`ComparisonReport`
- **语义**：返回 `ComparisonReport` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造 `ComparisonReport` 结构化领域对象，并把结果记为 草稿对象；调用 `compute_comparison_hash` 计算内容身份、分数或派生结果，并把结果记为 内容摘要；复制、序列化或校验结构化领域对象，并返回处理结果。
```

### `tests/test_artifact_delivery_api.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_artifact_preview_download_and_job_export`

- **源码**：`tests/test_artifact_delivery_api.py:27`
- **签名**：`def test_artifact_preview_download_and_job_export(tmp_path: Path, monkeypatch: 未显式标注) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径、测试环境修改工具，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `monkeypatch` | `未显式标注` | pytest 提供的环境/对象替换工具，用于隔离测试副作用；不是业务输入。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `setattr` 完成该函数的一项辅助处理；调用 `setup_local_execution_profile` 完成该函数的一项辅助处理；构造 `JobService` 结构化领域对象，并把结果记为 任务；调用 `submit` 完成该函数的一项辅助处理，并把结果记为 多个解包结果。
把外部位置解析为文件系统路径对象，并把结果记为 运行产物根目录；计算组合或计算已有值，并保存为 MCP 评测或运行报告；计算组合或计算已有值，并保存为 当前处理结果；创建父级目录或父领域对象对应的目录。
将处理结果写入MCP 评测或运行报告指定的文件；将处理结果写入当前处理结果指定的文件；调用 `build_artifact_record` 组装当前阶段需要的领域对象，并把结果记为 记录；调用 `build_artifact_record` 组装当前阶段需要的领域对象，并把结果记为 记录。
构造 `SqliteArtifactRepository` 结构化领域对象，并把结果记为 持久化仓库；构造 `LocalBlobStore` 结构化领域对象，并把结果记为 Blob 内容存储；调用 `publish` 完成该函数的一项辅助处理；构造 `PublishedArtifactCatalog` 结构化领域对象，并把结果记为 模型、工具或 Artifact 目录。
调用 `unlink` 完成该函数的一项辅助处理；调用 `unlink` 完成该函数的一项辅助处理；计算组合或计算已有值，并保存为 暂存工作区根目录；构造 `ArtifactDeliveryService` 结构化领域对象，并把结果记为 通知投递记录。
调用 `create_api_app` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果；计算按字段初始化键值映射，并保存为 当前处理结果。
进入上下文“构造 `TestClient` 结构化领域对象，并把上下文资源交给外部服务客户端”，退出时自动清理资源：
    从外部服务客户端读取所需的状态或领域记录，并把结果记为 该调用返回的结果；断言状态等于401；不满足就终止当前测试或流程；从外部服务客户端读取所需的状态或领域记录，并把结果记为 该调用返回的结果；断言状态等于200；不满足就终止当前测试或流程。
    遍历并筛选输入，将整理后的结果保存为 待处理项集合；断言待处理项集合中的对应字段中的对应字段是真；不满足就终止当前测试或流程；断言待处理项集合中的对应字段中的对应字段是假；不满足就终止当前测试或流程；断言当前输入内容不属于待处理文本；不满足就终止当前测试或流程。
    从外部服务客户端读取所需的状态或领域记录，并把结果记为 该调用返回的结果；断言状态等于200；不满足就终止当前测试或流程；断言当前输入内容属于前一步操作返回对象中的对应字段；不满足就终止当前测试或流程；断言前一步操作返回对象中的对应字段是假；不满足就终止当前测试或流程。
    从外部服务客户端读取所需的状态或领域记录，并把结果记为 该调用返回的结果；断言状态等于415；不满足就终止当前测试或流程；断言前一步操作返回对象中的对应字段等于'ARTIFACT_PREVIEW_UNSUPPORTED'；不满足就终止当前测试或流程；从外部服务客户端读取所需的状态或领域记录，并把结果记为 该调用返回的结果。
    断言状态等于200；不满足就终止当前测试或流程；断言“检查业务内容是否满足文本匹配条件”后得到肯定结果；不满足就终止当前测试或流程；断言“检查当前处理结果中的对应字段是否满足文本匹配条件”后得到肯定结果；不满足就终止当前测试或流程；断言当前输入内容属于当前处理结果中的对应字段；不满足就终止当前测试或流程。
    断言当前处理结果中的对应字段等于内容 SHA-256；不满足就终止当前测试或流程；断言当前处理结果中的对应字段等于'nosniff'；不满足就终止当前测试或流程；断言当前输入内容属于当前处理结果中的对应字段；不满足就终止当前测试或流程；从外部服务客户端读取所需的状态或领域记录，并把结果记为 该调用返回的结果。
    断言状态等于200；不满足就终止当前测试或流程；断言业务内容等于业务内容；不满足就终止当前测试或流程；从外部服务客户端读取所需的状态或领域记录，并把结果记为 该调用返回的结果；断言状态等于200；不满足就终止当前测试或流程。
    断言“检查当前处理结果中的对应字段是否满足文本匹配条件”后得到肯定结果；不满足就终止当前测试或流程；断言当前输入内容属于当前处理结果中的对应字段；不满足就终止当前测试或流程；断言当前处理结果中的对应字段 的长度等于64；不满足就终止当前测试或流程。
断言辅助操作“构造临时集合、映射或轻量领域对象”的结果等于[]；不满足就终止当前测试或流程；断言辅助操作“构造临时集合、映射或轻量领域对象”的结果等于[]；不满足就终止当前测试或流程。
在上下文“构造 `ZipFile` 结构化领域对象，并把上下文资源交给当前处理结果”中断言“检查辅助操作“调用 `read` 完成该函数的一项辅助处理”的结果是否满足文本匹配条件”后得到肯定结果；不满足就终止当前测试或流程；断言辅助操作“调用 `read` 完成该函数的一项辅助处理”的结果等于b'\x00\x01\x02'；不满足就终止当前测试或流程；将外部表示解析为结构化内容，并把结果记为 运行或工作区 Manifest；将外部表示解析为结构化内容，并把结果记为 任务，退出时自动清理资源。
断言运行或工作区 Manifest中的对应字段等于复现任务 ID；不满足就终止当前测试或流程；断言运行或工作区 Manifest中的对应字段等于本次复现运行 ID；不满足就终止当前测试或流程；断言运行或工作区 Manifest中的对应字段等于2；不满足就终止当前测试或流程；将结构化内容序列化或编码为可传输表示，并把结果记为 该调用返回的结果。
断言当前输入内容不属于当前处理结果；不满足就终止当前测试或流程；断言当前输入内容不属于当前处理结果；不满足就终止当前测试或流程；断言当前输入内容不属于当前处理结果；不满足就终止当前测试或流程。
```

### `tests/test_artifact_delivery_service.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `TrackingBytesIO.close`

- **源码**：`tests/test_artifact_delivery_service.py:35`
- **签名**：`def close(self) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算使用固定配置或常量值，并保存为 已关闭；关闭辅助操作“调用 `super` 完成该函数的一项辅助处理”的结果并释放相关资源。
```

#### `make_view`

- **源码**：`tests/test_artifact_delivery_service.py:40`
- **签名**：`def make_view(artifact_id: str, relative_path: str, media_type: str, content: bytes) -> ArtifactView`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收Artifact的 ID、仓库内相对路径、Artifact 媒体类型、业务内容，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `ArtifactView` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `artifact_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `relative_path` | `str` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `media_type` | `str` | Artifact 媒体类型；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `content` | `bytes` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`ArtifactView`
- **语义**：返回 `ArtifactView` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `ArtifactView` 结构化领域对象。
```

#### `FakeCatalog.__init__`

- **源码**：`tests/test_artifact_delivery_service.py:60`
- **签名**：`def __init__(self, items: list[tuple[ArtifactView, bytes]]) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收待处理项集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `items` | `list[tuple[ArtifactView, bytes]]` | 待处理项集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
遍历并筛选输入，将整理后的结果保存为 待处理项集合；计算使用固定配置或常量值，并保存为 当前处理结果。
```

#### `FakeCatalog.list_views`

- **源码**：`tests/test_artifact_delivery_service.py:67`
- **签名**：`def list_views(self, _job: JobRecord) -> list[ArtifactView]`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收复现任务记录，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `_job` | `JobRecord` | 名为 `_job` 的 `JobRecord` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`list[ArtifactView]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
返回当前计算得到的结果。
```

#### `FakeCatalog.open`

- **源码**：`tests/test_artifact_delivery_service.py:70`
- **签名**：`def open(self: 未显式标注, job: JobRecord, artifact_id: str) -> OpenedArtifact`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收复现任务记录、Artifact的 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `OpenedArtifact` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job` | `JobRecord` | 任务、运行、Manifest、记录或证据领域对象；携带关联 ID、状态和内容身份。 |
| `artifact_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`OpenedArtifact`
- **语义**：返回 `OpenedArtifact` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
读取待处理项集合中的对应字段，并保存为 多个解包结果；构造 `ArtifactDescriptor` 结构化领域对象，并把结果记为 工具或组件描述信息；构造 `TrackingBytesIO` 结构化领域对象，并把结果记为 请求正文；把传入参数保存到实例字段（请求正文 → 当前处理结果）。
构造并返回 `OpenedArtifact` 结构化领域对象。
```

#### `fake_job`

- **源码**：`tests/test_artifact_delivery_service.py:111`
- **签名**：`def fake_job() -> JobRecord`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`JobRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
调用 `cast` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `make_service`

- **源码**：`tests/test_artifact_delivery_service.py:119`
- **签名**：`def make_service(tmp_path: Path, catalog: FakeCatalog, preview_max_bytes: int, max_artifacts: int, max_uncompressed: int) -> ArtifactDeliveryService`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径、模型、工具或 Artifact 目录、当前处理结果的字节内容、最大当前处理结果等输入，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `ArtifactDeliveryService` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `catalog` | `FakeCatalog` | 持久化或目录访问端口；负责读取、CAS 更新或 Artifact 定位。 |
| `preview_max_bytes` | `int` | 名为 `preview_max_bytes` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。；默认 8 |
| `max_artifacts` | `int` | 名为 `max_artifacts` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。；默认 20 |
| `max_uncompressed` | `int` | 名为 `max_uncompressed` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。；默认 1024 × 1024 |

**输出**

- **Python 类型**：`ArtifactDeliveryService`
- **语义**：返回 `ArtifactDeliveryService` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `ArtifactDeliveryService` 结构化领域对象。
```

#### `test_preview_is_bounded_utf8_and_closes_body`

- **源码**：`tests/test_artifact_delivery_service.py:140`
- **签名**：`def test_preview_is_bounded_utf8_and_closes_body(tmp_path: Path) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
将结构化内容序列化或编码为可传输表示，并把结果记为 业务内容；调用 `make_view` 完成该函数的一项辅助处理，并把结果记为 视图；构造 `FakeCatalog` 结构化领域对象，并把结果记为 模型、工具或 Artifact 目录；调用 `preview` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果。
断言当前处理结果是真；不满足就终止当前测试或流程；断言当前处理结果的字节内容等于6；不满足就终止当前测试或流程；断言业务内容等于'你好'；不满足就终止当前测试或流程；断言当前处理结果不为空；不满足就终止当前测试或流程。
断言已关闭是真；不满足就终止当前测试或流程。
```

#### `test_preview_rejects_unsafe_or_non_text_content`

- **源码**：`tests/test_artifact_delivery_service.py:172`
- **签名**：`def test_preview_rejects_unsafe_or_non_text_content(tmp_path: Path, path: str, media_type: str, content: bytes) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径、文件或目录路径、Artifact 媒体类型、业务内容，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `path` | `str` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |
| `media_type` | `str` | Artifact 媒体类型；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `content` | `bytes` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `make_view` 完成该函数的一项辅助处理，并把结果记为 视图；构造 `FakeCatalog` 结构化领域对象，并把结果记为 模型、工具或 Artifact 目录。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `preview` 完成该函数的一项辅助处理，退出时自动清理资源。
断言当前处理结果不为空；不满足就终止当前测试或流程；断言已关闭是真；不满足就终止当前测试或流程。
```

#### `test_export_contains_artifacts_and_verifiable_manifest`

- **源码**：`tests/test_artifact_delivery_service.py:191`
- **签名**：`def test_export_contains_artifacts_and_verifiable_manifest(tmp_path: Path) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算使用固定配置或常量值，并保存为 第一项；计算使用固定配置或常量值，并保存为 第二项；计算初始化顺序集合，并保存为 Artifact 视图集合；构造 `FakeCatalog` 结构化领域对象，并把结果记为 模型、工具或 Artifact 目录。
调用 `make_service` 完成该函数的一项辅助处理，并把结果记为 领域服务对象；调用 `build_export` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果；断言“检查文件或目录路径的文件系统属性”后得到肯定结果；不满足就终止当前测试或流程。
在上下文“构造 `ZipFile` 结构化领域对象，并把上下文资源交给当前处理结果”中断言辅助操作“调用 `read` 完成该函数的一项辅助处理”的结果等于第一项；不满足就终止当前测试或流程；断言辅助操作“调用 `read` 完成该函数的一项辅助处理”的结果等于第二项；不满足就终止当前测试或流程；断言辅助操作“将外部表示解析为结构化内容”的结果等于{'job_id': 'job-1', 'status': 'succeeded'}；不满足就终止当前测试或流程；将外部表示解析为结构化内容，并把结果记为 运行或工作区 Manifest，退出时自动清理资源。
从运行或工作区 Manifest取出并移除最后一项，并把结果记为 调用方看到的旧内容 Hash；断言辅助操作“计算输入内容的 SHA-256 身份摘要”的结果等于调用方看到的旧内容 Hash；不满足就终止当前测试或流程；断言内容 SHA-256等于辅助操作“计算输入内容的 SHA-256 身份摘要”的结果；不满足就终止当前测试或流程；调用 `unlink` 完成该函数的一项辅助处理。
```

#### `test_export_rejects_snapshot_drift_and_removes_partial_zip`

- **源码**：`tests/test_artifact_delivery_service.py:230`
- **签名**：`def test_export_rejects_snapshot_drift_and_removes_partial_zip(tmp_path: Path) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算使用固定配置或常量值，并保存为 业务内容；调用 `make_view` 完成该函数的一项辅助处理，并把结果记为 视图。
定义内部类型 `DriftingCatalog`，用于组织当前函数的临时逻辑。
调用 `make_service` 完成该函数的一项辅助处理，并把结果记为 领域服务对象。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `build_export` 组装当前阶段需要的领域对象，退出时自动清理资源。
计算组合或计算已有值，并保存为 当前处理结果；断言辅助操作“构造临时集合、映射或轻量领域对象”的结果等于[]；不满足就终止当前测试或流程；断言辅助操作“构造临时集合、映射或轻量领域对象”的结果等于[]；不满足就终止当前测试或流程。
```

#### `test_export_rejects_snapshot_drift_and_removes_partial_zip.DriftingCatalog.open`

- **源码**：`tests/test_artifact_delivery_service.py:237`
- **签名**：`def open(self, *, job: JobRecord, artifact_id: str) -> OpenedArtifact`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收复现任务记录、Artifact的 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `OpenedArtifact` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job` | `JobRecord` | 任务、运行、Manifest、记录或证据领域对象；携带关联 ID、状态和内容身份。 |
| `artifact_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`OpenedArtifact`
- **语义**：返回 `OpenedArtifact` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `open` 完成该函数的一项辅助处理，并把结果记为 已打开资源；复制、序列化或校验结构化领域对象，并把结果记为 发生变化的内容；构造并返回 `OpenedArtifact` 结构化领域对象。
```

#### `test_export_rejects_duplicate_archive_paths`

- **源码**：`tests/test_artifact_delivery_service.py:265`
- **签名**：`def test_export_rejects_duplicate_archive_paths(tmp_path: Path) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `make_view` 完成该函数的一项辅助处理，并把结果记为 第一项；调用 `make_view` 完成该函数的一项辅助处理，并把结果记为 第二项；构造 `FakeCatalog` 结构化领域对象，并把结果记为 模型、工具或 Artifact 目录。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `build_export` 组装当前阶段需要的领域对象，退出时自动清理资源。
```

#### `test_export_enforces_count_and_uncompressed_limits`

- **源码**：`tests/test_artifact_delivery_service.py:278`
- **签名**：`def test_export_enforces_count_and_uncompressed_limits(tmp_path: Path) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算使用固定配置或常量值，并保存为 业务内容；调用 `make_view` 完成该函数的一项辅助处理，并把结果记为 视图；构造 `FakeCatalog` 结构化领域对象，并把结果记为 模型、工具或 Artifact 目录。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `build_export` 组装当前阶段需要的领域对象，退出时自动清理资源。
```

#### `test_export_staging_cannot_escape_allowed_root`

- **源码**：`tests/test_artifact_delivery_service.py:295`
- **签名**：`def test_export_staging_cannot_escape_allowed_root(tmp_path: Path) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合或计算已有值，并保存为 当前处理结果；创建当前处理结果对应的目录；构造 `FakeCatalog` 结构化领域对象，并把结果记为 模型、工具或 Artifact 目录；构造 `ArtifactDeliveryService` 结构化领域对象，并把结果记为 领域服务对象。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `build_export` 组装当前阶段需要的领域对象，退出时自动清理资源。
```

### `tests/test_chat_api.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_message`

- **源码**：`tests/test_chat_api.py:18`
- **签名**：`def _message(role: Literal['user', 'assistant'], sequence: int) -> ChatMessage`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收调用方职责角色、当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ChatMessage` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `role` | `Literal['user', 'assistant']` | 调用方职责角色；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `sequence` | `int` | 分页、文本切片或事件序列位置；用于确定本次读取的起止边界。 |

**输出**

- **Python 类型**：`ChatMessage`
- **语义**：返回 `ChatMessage` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `ChatMessage` 结构化领域对象。
```

#### `FakeChatService.list_messages`

- **源码**：`tests/test_chat_api.py:38`
- **签名**：`def list_messages(self, **_kwargs)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收函数关键字参数映射，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `未显式标注（存在 return）` 的领域结果。

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
构造并返回 `ChatMessagePage` 结构化领域对象。
```

#### `FakeChatService.list_recent_messages`

- **源码**：`tests/test_chat_api.py:44`
- **签名**：`def list_recent_messages(self, **_kwargs)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收函数关键字参数映射，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `未显式标注（存在 return）` 的领域结果。

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
构造并返回 `ChatMessagePage` 结构化领域对象。
```

#### `FakeChatService.get_memory`

- **源码**：`tests/test_chat_api.py:50`
- **签名**：`def get_memory(self, **_kwargs)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收函数关键字参数映射，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `未显式标注（存在 return）` 的领域结果。

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
构造并返回 `ConversationMemoryView` 结构化领域对象。
```

#### `FakeChatService.ask`

- **源码**：`tests/test_chat_api.py:64`
- **签名**：`def ask(self, **kwargs)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收函数关键字参数映射，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

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
断言函数关键字参数映射中的对应字段等于'ask-api-1'；不满足就终止当前测试或流程；构造并返回 `ChatAskResponse` 结构化领域对象。
```

#### `_client`

- **源码**：`tests/test_chat_api.py:72`
- **签名**：`def _client(service) -> TestClient`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收领域服务对象，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `TestClient` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `service` | `未显式标注` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |

**输出**

- **Python 类型**：`TestClient`
- **语义**：返回 `TestClient` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造 `FastAPI` 结构化领域对象，并把结果记为 该调用返回的结果；计算使用固定配置或常量值，并保存为 当前处理结果；读取领域服务对象，并保存为 对话；调用 `include_router` 完成该函数的一项辅助处理。
构造并返回 `TestClient` 结构化领域对象。
```

#### `test_chat_history_and_ask_contract`

- **源码**：`tests/test_chat_api.py:80`
- **签名**：`def test_chat_history_and_ask_contract()`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_client` 完成该函数的一项辅助处理，并把结果记为 外部服务客户端；从外部服务客户端读取所需的状态或领域记录，并把结果记为 历史对话或运行记录；调用 `post` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；断言状态等于200；不满足就终止当前测试或流程。
断言前一步操作返回对象中的对应字段等于2；不满足就终止当前测试或流程；断言状态等于200；不满足就终止当前测试或流程；断言前一步操作返回对象中的对应字段中的对应字段等于'answer'；不满足就终止当前测试或流程。
```

#### `test_disabled_chat_returns_503`

- **源码**：`tests/test_chat_api.py:96`
- **签名**：`def test_disabled_chat_returns_503()`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
从辅助操作“调用 `_client` 完成该函数的一项辅助处理”的结果读取所需的状态或领域记录，并把结果记为 结构化响应；断言状态等于503；不满足就终止当前测试或流程；断言前一步操作返回对象中的对应字段中的对应字段等于'CHAT_DISABLED'；不满足就终止当前测试或流程。
```

#### `test_recent_history_and_memory_contract`

- **源码**：`tests/test_chat_api.py:105`
- **签名**：`def test_recent_history_and_memory_contract()`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_client` 完成该函数的一项辅助处理，并把结果记为 外部服务客户端；从外部服务客户端读取所需的状态或领域记录，并把结果记为 该调用返回的结果；从外部服务客户端读取所需的状态或领域记录，并把结果记为 记忆；断言状态等于200；不满足就终止当前测试或流程。
断言当前输入内容等于[201, 202]；不满足就终止当前测试或流程；断言状态等于200；不满足就终止当前测试或流程；断言前一步操作返回对象中的对应字段等于2；不满足就终止当前测试或流程；断言前一步操作返回对象中的对应字段等于200；不满足就终止当前测试或流程。
```

#### `test_unavailable_memory_returns_explicit_503`

- **源码**：`tests/test_chat_api.py:120`
- **签名**：`def test_unavailable_memory_returns_explicit_503()`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
定义内部类型 `UnavailableMemoryService`，用于组织当前函数的临时逻辑。
从辅助操作“调用 `_client` 完成该函数的一项辅助处理”的结果读取所需的状态或领域记录，并把结果记为 结构化响应；断言状态等于503；不满足就终止当前测试或流程；断言前一步操作返回对象中的对应字段中的对应字段等于'CHAT_MEMORY_UNAVAILABLE'；不满足就终止当前测试或流程。
```

#### `test_unavailable_memory_returns_explicit_503.UnavailableMemoryService.get_memory`

- **源码**：`tests/test_chat_api.py:122`
- **签名**：`def get_memory(self, **_kwargs)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收函数关键字参数映射，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `**_kwargs` | `未显式标注` | 额外关键字参数映射。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
拒绝继续处理并抛出 `ChatUnavailableError`，向调用方报告输入或运行失败。
```

### `tests/test_chat_comparison_grounding.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `FakeComparisonReader.__init__`

- **源码**：`tests/test_chat_comparison_grounding.py:10`
- **签名**：`def __init__(self)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `make_report` 完成该函数的一项辅助处理，并把结果记为 MCP 评测或运行报告。
```

#### `FakeComparisonReader.get`

- **源码**：`tests/test_chat_comparison_grounding.py:13`
- **签名**：`def get(self, comparison_id: str)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收SDK 或 MCP 运行升级比较结果的 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `comparison_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
断言SDK 或 MCP 运行升级比较结果的 ID等于SDK 或 MCP 运行升级比较结果的 ID；不满足就终止当前测试或流程；返回MCP 评测或运行报告的当前值。
```

#### `FakeComparisonReader.list_for_job`

- **源码**：`tests/test_chat_comparison_grounding.py:17`
- **签名**：`def list_for_job(self, job_id: str, *, limit: int = 100)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收复现任务 ID、结果数量上限，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。；默认 100 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
断言复现任务 ID等于'job-target'；不满足就终止当前测试或流程；断言结果数量上限等于3；不满足就终止当前测试或流程；调用 `from_report` 完成该函数的一项辅助处理，并把结果记为 当前处理项；构造并返回 `ComparisonListResponse` 结构化领域对象。
```

#### `test_chat_builds_bounded_comparison_source`

- **源码**：`tests/test_chat_comparison_grounding.py:24`
- **签名**：`def test_chat_builds_bounded_comparison_source() -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `FakeComparisonReader` 结构化领域对象，并把结果记为 证据读取器；构造 `ChatContextBuilder` 结构化领域对象，并把结果记为 领域对象构造器；调用 `_comparison_sources` 完成该函数的一项辅助处理，并把结果记为 证据来源集合；断言证据来源集合 的长度等于1；不满足就终止当前测试或流程。
读取证据来源集合中的对应字段，并保存为 数据来源标记；断言来源类型等于'comparison'；不满足就终止当前测试或流程；断言论文引用证据的 ID等于格式化文本：f'comparison:{reader.report.comparison_id}'；不满足就终止当前测试或流程；断言SDK 或 MCP 运行升级比较结果的 Hash等于SDK 或 MCP 运行升级比较结果的 Hash；不满足就终止当前测试或流程。
断言任务的 ID等于'job-base'；不满足就终止当前测试或流程；断言任务的 ID等于'job-target'；不满足就终止当前测试或流程；断言当前输入内容属于业务内容；不满足就终止当前测试或流程；断言当前输入内容不属于业务内容；不满足就终止当前测试或流程。
```

#### `test_chat_skips_comparison_when_projection_exceeds_budget`

- **源码**：`tests/test_chat_comparison_grounding.py:57`
- **签名**：`def test_chat_skips_comparison_when_projection_exceeds_budget() -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `FakeComparisonReader` 结构化领域对象，并把结果记为 证据读取器；构造 `ChatContextBuilder` 结构化领域对象，并把结果记为 领域对象构造器；断言辅助操作“调用 `_comparison_sources` 完成该函数的一项辅助处理”的结果等于[]；不满足就终止当前测试或流程。
```

### `tests/test_chat_context.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `FakeInteraction.__init__`

- **源码**：`tests/test_chat_context.py:21`
- **签名**：`def __init__(self)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `SimpleNamespace` 结构化领域对象，并把结果记为 任务；构造 `SimpleNamespace` 结构化领域对象，并把结果记为 任务。
```

#### `FakeInteraction._get_internal_job`

- **源码**：`tests/test_chat_context.py:29`
- **签名**：`def _get_internal_job(self, job_id: str)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收复现任务 ID，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `未显式标注（存在 return）` 的领域结果。

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
断言复现任务 ID等于'job-1'；不满足就终止当前测试或流程；返回任务的当前值。
```

#### `FakeInteraction.get_job`

- **源码**：`tests/test_chat_context.py:33`
- **签名**：`def get_job(self, job_id: str)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收复现任务 ID，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `未显式标注（存在 return）` 的领域结果。

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
断言复现任务 ID等于'job-1'；不满足就终止当前测试或流程；调用 `make_job` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `FakeInteraction.events_after`

- **源码**：`tests/test_chat_context.py:37`
- **签名**：`def events_after(self, **_kwargs)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收函数关键字参数映射，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

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
返回当前构造的顺序或去重集合。
```

#### `FakeInteraction.tail_log`

- **源码**：`tests/test_chat_context.py:40`
- **签名**：`def tail_log(self, **_kwargs)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收函数关键字参数映射，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

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
构造并返回 `LogTailResponse` 结构化领域对象。
```

#### `FakeCatalog.__init__`

- **源码**：`tests/test_chat_context.py:45`
- **签名**：`def __init__(self)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `BytesIO` 结构化领域对象，并把结果记为 请求正文；将 已打开集合 初始化为空列表，用来收集后续结果。
```

#### `FakeCatalog.list_views`

- **源码**：`tests/test_chat_context.py:51`
- **签名**：`def list_views(self, job)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收复现任务记录，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job` | `未显式标注` | 任务、运行、Manifest、记录或证据领域对象；携带关联 ID、状态和内容身份。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
断言复现任务 ID等于'job-1'；不满足就终止当前测试或流程；返回当前构造的顺序或去重集合。
```

#### `FakeCatalog.open`

- **源码**：`tests/test_chat_context.py:78`
- **签名**：`def open(self, *, job, artifact_id: str)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收复现任务记录、Artifact的 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

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
断言复现任务 ID等于'job-1'；不满足就终止当前测试或流程；断言Artifact的 ID等于'report-1'；不满足就终止当前测试或流程；把Artifact的 ID追加或合并到已打开集合；构造 `ArtifactDescriptor` 结构化领域对象，并把结果记为 工具或组件描述信息。
构造并返回 `OpenedArtifact` 结构化领域对象。
```

#### `test_context_uses_allowed_artifact_and_closes_body`

- **源码**：`tests/test_chat_context.py:114`
- **签名**：`def test_context_uses_allowed_artifact_and_closes_body()`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `FakeInteraction` 结构化领域对象，并把结果记为 用户交互记录；构造 `FakeCatalog` 结构化领域对象，并把结果记为 模型、工具或 Artifact 目录；构造 `ChatContextBuilder` 结构化领域对象，并把结果记为 领域对象构造器；调用 `build` 完成该函数的一项辅助处理，并把结果记为 代码仓库归档包。
断言已打开集合等于['report-1']；不满足就终止当前测试或流程；断言已关闭资源有值或为真；不满足就终止当前测试或流程；调用 `join` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；断言当前输入内容属于当前处理结果；不满足就终止当前测试或流程。
断言当前可迭代输入中每一项都满足“Artifact的 ID不等于'patch-1'”的项；不满足就终止当前测试或流程。
```

### `tests/test_chat_eval_runner.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_case`

- **源码**：`tests/test_chat_eval_runner.py:12`
- **签名**：`def _case(case_id: str = "chat-runner") -> EvalCase`
- **作用**：在论文复现的离线评测与回归检查阶段中，该函数接收评测用例的 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `EvalCase` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `case_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。；默认 'chat-runner' |

**输出**

- **Python 类型**：`EvalCase`
- **语义**：返回 `EvalCase` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
复制、序列化或校验结构化领域对象，并返回处理结果。
```

#### `_unknown_citation_scenario`

- **源码**：`tests/test_chat_eval_runner.py:36`
- **签名**：`def _unknown_citation_scenario() -> ChatEvalScenario`
- **作用**：在论文复现的离线评测与回归检查阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ChatEvalScenario` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`ChatEvalScenario`
- **语义**：返回 `ChatEvalScenario` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
复制、序列化或校验结构化领域对象，并返回处理结果。
```

#### `test_offline_runner_uses_real_service_citation_fail_closed`

- **源码**：`tests/test_chat_eval_runner.py:66`
- **签名**：`def test_offline_runner_uses_real_service_citation_fail_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None（隐式）`
- **作用**：在论文复现的离线评测与回归检查阶段中，该函数接收临时工作目录路径、测试环境修改工具，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `monkeypatch` | `pytest.MonkeyPatch` | pytest 提供的环境/对象替换工具，用于隔离测试副作用；不是业务输入。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_unknown_citation_scenario` 完成该函数的一项辅助处理，并把结果记为 复现实验场景；调用 `setattr` 完成该函数的一项辅助处理；调用 `run_chat_eval_case` 完成该函数的一项辅助处理，并把结果记为 MCP Client 单次观测结果；断言对话不为空；不满足就终止当前测试或流程。
读取当前处理结果中的对应字段，并保存为 运行；读取当前处理结果中的对应字段，并保存为 后续步骤使用的结果；断言当前处理结果等于['artifact:unknown:1']；不满足就终止当前测试或流程；断言当前处理结果等于['artifact:unknown:1']；不满足就终止当前测试或流程。
断言当前处理结果等于[]；不满足就终止当前测试或流程；断言当前处理结果是真；不满足就终止当前测试或流程；断言当前处理结果等于1；不满足就终止当前测试或流程；断言记忆集合等于0；不满足就终止当前测试或流程。
断言“检查当前输入内容的文件系统属性”后未得到肯定结果；不满足就终止当前测试或流程。
```

#### `test_offline_runner_creates_valid_memory`

- **源码**：`tests/test_chat_eval_runner.py:97`
- **签名**：`def test_offline_runner_creates_valid_memory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None（隐式）`
- **作用**：在论文复现的离线评测与回归检查阶段中，该函数接收临时工作目录路径、测试环境修改工具，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `monkeypatch` | `pytest.MonkeyPatch` | pytest 提供的环境/对象替换工具，用于隔离测试副作用；不是业务输入。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
复制、序列化或校验结构化领域对象，并把结果记为 复现实验场景；调用 `setattr` 完成该函数的一项辅助处理；调用 `run_chat_eval_case` 完成该函数的一项辅助处理，并把结果记为 MCP Client 单次观测结果；断言对话不为空；不满足就终止当前测试或流程。
读取当前处理结果中的对应字段，并保存为 运行；断言当前处理结果是真；不满足就终止当前测试或流程；断言Hash是真；不满足就终止当前测试或流程；断言来源等于1.0；不满足就终止当前测试或流程。
断言来源集合等于[1]；不满足就终止当前测试或流程。
```

#### `test_offline_runner_compacts_three_memory_generations`

- **源码**：`tests/test_chat_eval_runner.py:180`
- **签名**：`def test_offline_runner_compacts_three_memory_generations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None（隐式）`
- **作用**：在论文复现的离线评测与回归检查阶段中，该函数接收临时工作目录路径、测试环境修改工具，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `monkeypatch` | `pytest.MonkeyPatch` | pytest 提供的环境/对象替换工具，用于隔离测试副作用；不是业务输入。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
复制、序列化或校验结构化领域对象，并把结果记为 复现实验场景；调用 `setattr` 完成该函数的一项辅助处理；调用 `run_chat_eval_case` 完成该函数的一项辅助处理，并把结果记为 MCP Client 单次观测结果；断言对话不为空；不满足就终止当前测试或流程。
读取当前处理结果中的对应字段，并保存为 运行；断言当前处理结果等于5；不满足就终止当前测试或流程；断言记忆集合等于3；不满足就终止当前测试或流程；断言记录版本号等于3；不满足就终止当前测试或流程。
断言当前处理结果等于28；不满足就终止当前测试或流程；断言阶段摘要等于'memory generation 3'；不满足就终止当前测试或流程。
```

#### `test_provider_mode_rejects_scripted_draft`

- **源码**：`tests/test_chat_eval_runner.py:252`
- **签名**：`def test_provider_mode_rejects_scripted_draft(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None（隐式）`
- **作用**：在论文复现的离线评测与回归检查阶段中，该函数接收临时工作目录路径、测试环境修改工具，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `monkeypatch` | `pytest.MonkeyPatch` | pytest 提供的环境/对象替换工具，用于隔离测试副作用；不是业务输入。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
复制、序列化或校验结构化领域对象，并把结果记为 复现实验场景；复制、序列化或校验结构化领域对象，并把结果记为 模型服务商用例；调用 `setattr` 完成该函数的一项辅助处理。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `run_chat_eval_case` 完成该函数的一项辅助处理，退出时自动清理资源。
```

### `tests/test_chat_eval_schemas.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_case`

- **源码**：`tests/test_chat_eval_schemas.py:11`
- **签名**：`def _case(*, suite="chat_offline", runner="chat_scenario")`
- **作用**：在论文复现的离线评测与回归检查阶段中，该函数接收评测套件、运行调度器，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `suite` | `未显式标注` | 评测套件；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 'chat_offline' |
| `runner` | `未显式标注` | 运行调度器；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 'chat_scenario' |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
返回包含 `case_id`、`description`、`suite`、`runner`、`categories`、`input`、`expected` 字段的结构化映射。
```

#### `_scenario`

- **源码**：`tests/test_chat_eval_schemas.py:30`
- **签名**：`def _scenario()`
- **作用**：在论文复现的离线评测与回归检查阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
返回包含 `scenario_id`、`sources`、`turns`、`compaction_enabled` 字段的结构化映射。
```

#### `test_chat_offline_case_requires_matching_runner_and_suite`

- **源码**：`tests/test_chat_eval_schemas.py:58`
- **签名**：`def test_chat_offline_case_requires_matching_runner_and_suite()`
- **作用**：在论文复现的离线评测与回归检查阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
复制、序列化或校验结构化领域对象，并把结果记为 评测用例；断言运行调度器等于'chat_scenario'；不满足就终止当前测试或流程；断言评测套件等于'chat_offline'；不满足就终止当前测试或流程。
```

#### `test_chat_runner_in_wrong_suite_is_rejected`

- **源码**：`tests/test_chat_eval_schemas.py:65`
- **签名**：`def test_chat_runner_in_wrong_suite_is_rejected()`
- **作用**：在论文复现的离线评测与回归检查阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中复制、序列化或校验结构化领域对象，退出时自动清理资源。
```

#### `test_chat_case_requires_a_chat_oracle`

- **源码**：`tests/test_chat_eval_schemas.py:72`
- **签名**：`def test_chat_case_requires_a_chat_oracle()`
- **作用**：在论文复现的离线评测与回归检查阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_case` 完成该函数的一项辅助处理，并把结果记为 结构化请求载荷；将 结构化请求载荷中的对应字段 初始化为空映射，用来收集后续结果。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中复制、序列化或校验结构化领域对象，退出时自动清理资源。
```

#### `test_chat_oracle_rejects_blank_terms`

- **源码**：`tests/test_chat_eval_schemas.py:80`
- **签名**：`def test_chat_oracle_rejects_blank_terms()`
- **作用**：在论文复现的离线评测与回归检查阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_case` 完成该函数的一项辅助处理，并把结果记为 结构化请求载荷；计算初始化顺序集合，并保存为 结构化请求载荷中的对应字段中的对应字段中的对应字段中的对应字段。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中复制、序列化或校验结构化领域对象，退出时自动清理资源。
```

#### `test_required_citation_must_belong_to_allowlist`

- **源码**：`tests/test_chat_eval_schemas.py:90`
- **签名**：`def test_required_citation_must_belong_to_allowlist()`
- **作用**：在论文复现的离线评测与回归检查阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_case` 完成该函数的一项辅助处理，并把结果记为 结构化请求载荷；把新的处理结果追加或合并到结构化请求载荷中的对应字段中的对应字段中的对应字段。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中复制、序列化或校验结构化领域对象，退出时自动清理资源。
```

#### `test_scenario_requires_job_current_as_first_source`

- **源码**：`tests/test_chat_eval_schemas.py:103`
- **签名**：`def test_scenario_requires_job_current_as_first_source()`
- **作用**：在论文复现的离线评测与回归检查阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_scenario` 完成该函数的一项辅助处理，并把结果记为 结构化请求载荷；计算使用固定配置或常量值，并保存为 结构化请求载荷中的对应字段中的对应字段中的对应字段中的对应字段。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中复制、序列化或校验结构化领域对象，退出时自动清理资源。
```

#### `test_scenario_rejects_unknown_seed_citation`

- **源码**：`tests/test_chat_eval_schemas.py:111`
- **签名**：`def test_scenario_rejects_unknown_seed_citation()`
- **作用**：在论文复现的离线评测与回归检查阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_scenario` 完成该函数的一项辅助处理，并把结果记为 结构化请求载荷；计算初始化顺序集合，并保存为 结构化请求载荷中的对应字段。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中复制、序列化或校验结构化领域对象，退出时自动清理资源。
```

#### `test_memory_script_requires_draft_xor_error`

- **源码**：`tests/test_chat_eval_schemas.py:125`
- **签名**：`def test_memory_script_requires_draft_xor_error()`
- **作用**：在论文复现的离线评测与回归检查阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_scenario` 完成该函数的一项辅助处理，并把结果记为 结构化请求载荷；计算初始化顺序集合，并保存为 结构化请求载荷中的对应字段。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中复制、序列化或校验结构化领域对象，退出时自动清理资源。
```

#### `test_repository_chat_offline_cases_are_valid`

- **源码**：`tests/test_chat_eval_schemas.py:138`
- **签名**：`def test_repository_chat_offline_cases_are_valid()`
- **作用**：在论文复现的离线评测与回归检查阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `load_cases` 读取或查询当前阶段需要的数据，并把结果记为 评测用例集合；断言当前输入内容等于{'chat_scenario'}；不满足就终止当前测试或流程；断言评测用例集合 的长度不小于3；不满足就终止当前测试或流程。
```

#### `test_repository_chat_provider_cases_are_valid_and_isolated`

- **源码**：`tests/test_chat_eval_schemas.py:145`
- **签名**：`def test_repository_chat_provider_cases_are_valid_and_isolated()`
- **作用**：在论文复现的离线评测与回归检查阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `load_cases` 读取或查询当前阶段需要的数据，并把结果记为 评测用例集合；断言当前输入内容等于{'chat_provider'}；不满足就终止当前测试或流程；断言评测用例集合 的长度不小于4；不满足就终止当前测试或流程；断言由评测用例集合组成的集合或迭代器中存在满足“评测用例的 ID等于'chat_provider_run_comparison_explanation'”的项；不满足就终止当前测试或流程。
```

### `tests/test_chat_eval_scorers.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_case`

- **源码**：`tests/test_chat_eval_scorers.py:13`
- **签名**：`def _case(min_pass_rate: float = 0.66) -> EvalCase`
- **作用**：在论文复现的离线评测与回归检查阶段中，该函数接收最小比例，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `EvalCase` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `min_pass_rate` | `float` | 名为 `min_pass_rate` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。；默认 0.66 |

**输出**

- **Python 类型**：`EvalCase`
- **语义**：返回 `EvalCase` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
复制、序列化或校验结构化领域对象，并返回处理结果。
```

#### `_run`

- **源码**：`tests/test_chat_eval_scorers.py:67`
- **签名**：`def _run(*, valid: bool, repetition: int)`
- **作用**：在论文复现的离线评测与回归检查阶段中，该函数接收输入或结果是否有效的判断、当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `valid` | `bool` | 布尔条件或能力开关，用于控制流程分支。 |
| `repetition` | `int` | 名为 `repetition` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
构造并返回 `ChatScenarioRunObservation` 结构化领域对象。
```

#### `_observation`

- **源码**：`tests/test_chat_eval_scorers.py:131`
- **签名**：`def _observation(valid_runs: list[bool]) -> EvalObservation`
- **作用**：在论文复现的离线评测与回归检查阶段中，该函数接收当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `EvalObservation` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `valid_runs` | `list[bool]` | `list[bool]` 元素集合；元素代表的业务对象由参数名 `valid_runs` 和调用位置确定。 |

**输出**

- **Python 类型**：`EvalObservation`
- **语义**：返回 `EvalObservation` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `EvalObservation` 结构化领域对象。
```

#### `test_two_of_three_provider_runs_pass_with_point_66_threshold`

- **源码**：`tests/test_chat_eval_scorers.py:147`
- **签名**：`def test_two_of_three_provider_runs_pass_with_point_66_threshold()`
- **作用**：在论文复现的离线评测与回归检查阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `score_case` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果；断言当前处理结果是真；不满足就终止当前测试或流程。
```

#### `test_one_of_three_provider_runs_fails_threshold`

- **源码**：`tests/test_chat_eval_scorers.py:156`
- **签名**：`def test_one_of_three_provider_runs_fails_threshold()`
- **作用**：在论文复现的离线评测与回归检查阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `score_case` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果；断言当前处理结果是假；不满足就终止当前测试或流程；遍历并筛选输入，将整理后的结果保存为 当前处理结果；断言当前输入内容属于当前处理结果；不满足就终止当前测试或流程。
断言当前输入内容属于当前处理结果；不满足就终止当前测试或流程；断言当前输入内容属于当前处理结果；不满足就终止当前测试或流程；断言当前输入内容属于当前处理结果；不满足就终止当前测试或流程。
```

#### `test_missing_chat_observation_does_not_receive_full_score`

- **源码**：`tests/test_chat_eval_scorers.py:175`
- **签名**：`def test_missing_chat_observation_does_not_receive_full_score()`
- **作用**：在论文复现的离线评测与回归检查阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `score_case` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果；断言当前处理结果是假；不满足就终止当前测试或流程。
```

#### `test_memory_trigger_and_coverage_oracles_fail_when_compaction_did_not_run`

- **源码**：`tests/test_chat_eval_scorers.py:187`
- **签名**：`def test_memory_trigger_and_coverage_oracles_fail_when_compaction_did_not_run()`
- **作用**：在论文复现的离线评测与回归检查阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_observation` 完成该函数的一项辅助处理，并把结果记为 MCP Client 单次观测结果；断言对话不为空；不满足就终止当前测试或流程；计算使用固定配置或常量值，并保存为 记忆集合；计算使用固定配置或常量值，并保存为 当前处理结果。
调用 `score_case` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果；遍历并筛选输入，将整理后的结果保存为 当前处理结果；断言当前输入内容属于当前处理结果；不满足就终止当前测试或流程；断言当前输入内容属于当前处理结果；不满足就终止当前测试或流程。
```

### `tests/test_chat_memory.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `repository_with_exchanges`

- **源码**：`tests/test_chat_memory.py:21`
- **签名**：`def repository_with_exchanges(tmp_path: Path, count: int) -> SqliteChatRepository`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径、对象数量，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `SqliteChatRepository` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `count` | `int` | 对象数量或重试次数，用于范围和上限校验，不是进程退出码。 |

**输出**

- **Python 类型**：`SqliteChatRepository`
- **语义**：返回 `SqliteChatRepository` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造 `SqliteChatRepository` 结构化领域对象，并把结果记为 持久化仓库；调用 `initialize` 完成该函数的一项辅助处理；构造 `ChatCitation` 结构化领域对象，并把结果记为 论文引用证据。
遍历限定范围内的序列，每次把当前项记为当前候选项的索引，然后调用 `append_exchange` 完成该函数的一项辅助处理。
返回持久化仓库的当前值。
```

#### `compactor`

- **源码**：`tests/test_chat_memory.py:52`
- **签名**：`def compactor(repository, invoker)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收持久化仓库、工具或模型调用器，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `repository` | `未显式标注` | 持久化或目录访问端口；负责读取、CAS 更新或 Artifact 定位。 |
| `invoker` | `未显式标注` | 可调用依赖；由当前函数在受控位置调用。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
定义内部辅助函数 `routed_invoker`，供当前函数在后续步骤中调用。
构造并返回 `ConversationMemoryCompactor` 结构化领域对象。
```

#### `compactor.routed_invoker`

- **源码**：`tests/test_chat_memory.py:53`
- **签名**：`def routed_invoker(prompt: str, job_id: str) -> MemoryDraftResult`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收发给模型的结构化提示、复现任务 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `prompt` | `str` | 用户目标、检索问题、反馈或待处理文本；会作为当前阶段的业务语境输入，并可能受到长度/脱敏约束。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`MemoryDraftResult`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
移除复现任务 ID中的当前内容；构造并返回 `MemoryDraftResult` 结构化领域对象。
```

#### `test_compaction_creates_hashed_memory_without_deleting_raw_messages`

- **源码**：`tests/test_chat_memory.py:77`
- **签名**：`def test_compaction_creates_hashed_memory_without_deleting_raw_messages(tmp_path: 未显式标注) -> 未显式标注（存在 return）`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：无业务返回值；通过断言或预期异常验证目标行为。

**伪代码**

```text
调用 `repository_with_exchanges` 完成该函数的一项辅助处理，并把结果记为 持久化仓库。
定义内部辅助函数 `invoke`，供当前函数在后续步骤中调用。
调用 `ensure_memory` 完成该函数的一项辅助处理，并把结果记为 执行结论；断言已创建记录是真；不满足就终止当前测试或流程；断言当前处理结果是假；不满足就终止当前测试或流程；断言记忆不为空；不满足就终止当前测试或流程。
断言当前处理结果等于1；不满足就终止当前测试或流程；断言当前处理结果等于6；不满足就终止当前测试或流程；调用 `validate_memory_hash` 校验当前输入或状态；断言Artifact的 ID等于'report'；不满足就终止当前测试或流程。
断言辅助操作“调用 `latest_sequence` 完成该函数的一项辅助处理”的结果等于10；不满足就终止当前测试或流程；断言辅助操作“调用 `list_messages` 读取或查询当前阶段需要的数据”的结果 的长度等于10；不满足就终止当前测试或流程。
```

#### `test_compaction_creates_hashed_memory_without_deleting_raw_messages.invoke`

- **源码**：`tests/test_chat_memory.py:82`
- **签名**：`def invoke(_prompt: str) -> MemoryDraft`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收发给模型的结构化提示，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `MemoryDraft` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `_prompt` | `str` | 名为 `_prompt` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`MemoryDraft`
- **语义**：返回 `MemoryDraft` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `MemoryDraft` 结构化领域对象。
```

#### `test_unknown_memory_sources_degrade_to_previous_memory`

- **源码**：`tests/test_chat_memory.py:111`
- **签名**：`def test_unknown_memory_sources_degrade_to_previous_memory(tmp_path)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `repository_with_exchanges` 完成该函数的一项辅助处理，并把结果记为 持久化仓库；调用 `ensure_memory` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；断言已创建记录是假；不满足就终止当前测试或流程；断言当前处理结果是真；不满足就终止当前测试或流程。
断言记忆为空；不满足就终止当前测试或流程；断言辅助操作“调用 `get_latest_memory` 读取或查询当前阶段需要的数据”的结果为空；不满足就终止当前测试或流程。
```

#### `test_second_compaction_links_to_first_memory`

- **源码**：`tests/test_chat_memory.py:134`
- **签名**：`def test_second_compaction_links_to_first_memory(tmp_path)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：无业务返回值；通过断言或预期异常验证目标行为。

**伪代码**

```text
调用 `repository_with_exchanges` 完成该函数的一项辅助处理，并把结果记为 持久化仓库。
定义内部辅助函数 `first`，供当前函数在后续步骤中调用。
调用 `ensure_memory` 完成该函数的一项辅助处理，并把结果记为 第一项；断言记忆不为空；不满足就终止当前测试或流程；计算组合或计算已有值，并保存为 第二项。
遍历限定范围内的序列，每次把当前项记为当前候选项的索引，然后调用 `append_exchange` 完成该函数的一项辅助处理。
定义内部辅助函数 `second`，供当前函数在后续步骤中调用。
调用 `ensure_memory` 完成该函数的一项辅助处理，并把结果记为 第二项；断言记忆不为空；不满足就终止当前测试或流程；断言记录版本号等于2；不满足就终止当前测试或流程；断言记忆的 ID等于记忆的 ID；不满足就终止当前测试或流程。
断言记忆的 SHA-256等于记忆的 SHA-256；不满足就终止当前测试或流程；调用 `validate_memory_hash` 校验当前输入或状态。
```

#### `test_second_compaction_links_to_first_memory.first`

- **源码**：`tests/test_chat_memory.py:137`
- **签名**：`def first(_prompt: str) -> MemoryDraft`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收发给模型的结构化提示，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `MemoryDraft` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `_prompt` | `str` | 名为 `_prompt` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`MemoryDraft`
- **语义**：返回 `MemoryDraft` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `MemoryDraft` 结构化领域对象。
```

#### `test_second_compaction_links_to_first_memory.second`

- **源码**：`tests/test_chat_memory.py:161`
- **签名**：`def second(_prompt: str) -> MemoryDraft`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收发给模型的结构化提示，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `MemoryDraft` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `_prompt` | `str` | 名为 `_prompt` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`MemoryDraft`
- **语义**：返回 `MemoryDraft` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `MemoryDraft` 结构化领域对象。
```

#### `test_memory_provider_failure_does_not_delete_or_block_history`

- **源码**：`tests/test_chat_memory.py:186`
- **签名**：`def test_memory_provider_failure_does_not_delete_or_block_history(tmp_path)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `repository_with_exchanges` 完成该函数的一项辅助处理，并把结果记为 持久化仓库。
定义内部辅助函数 `fail`，供当前函数在后续步骤中调用。
调用 `ensure_memory` 完成该函数的一项辅助处理，并把结果记为 执行结论；断言当前处理结果是真；不满足就终止当前测试或流程；断言记忆为空；不满足就终止当前测试或流程；断言辅助操作“调用 `latest_sequence` 完成该函数的一项辅助处理”的结果等于8；不满足就终止当前测试或流程。
```

#### `test_memory_provider_failure_does_not_delete_or_block_history.fail`

- **源码**：`tests/test_chat_memory.py:189`
- **签名**：`def fail(_prompt: str)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收发给模型的结构化提示，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `_prompt` | `str` | 名为 `_prompt` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
拒绝继续处理并抛出 `RuntimeError`，向调用方报告输入或运行失败。
```

#### `test_memory_hash_detects_body_tampering`

- **源码**：`tests/test_chat_memory.py:198`
- **签名**：`def test_memory_hash_detects_body_tampering(tmp_path)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `repository_with_exchanges` 完成该函数的一项辅助处理，并把结果记为 持久化仓库；调用 `ensure_memory` 完成该函数的一项辅助处理，并把结果记为 执行结论；断言记忆不为空；不满足就终止当前测试或流程；复制、序列化或校验结构化领域对象，并把结果记为 该调用返回的结果。
复制、序列化或校验结构化领域对象，并把结果记为 该调用返回的结果。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `validate_memory_hash` 校验当前输入或状态，退出时自动清理资源。
```

#### `test_memory_provider_returns_bounded_structured_draft`

- **源码**：`tests/test_chat_memory.py:221`
- **签名**：`def test_memory_provider_returns_bounded_structured_draft()`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
去除当前输入内容的首尾空白，并把规范化后的文本记为 发给模型的结构化提示；读取前一步操作返回对象的草稿对象，并保存为 草稿对象；断言“对阶段摘要中的文本执行规范化或拆分”后得到肯定结果；不满足就终止当前测试或流程；断言当前输入内容不大于{1, 2}；不满足就终止当前测试或流程。
断言辅助操作“构造临时集合、映射或轻量领域对象”的结果不大于{'job:current'}；不满足就终止当前测试或流程。
```

#### `test_phase36_memory_hash_projection_ignores_new_comparison_fields`

- **源码**：`tests/test_chat_memory.py:259`
- **签名**：`def test_phase36_memory_hash_projection_ignores_new_comparison_fields() -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `ConversationMemoryBody` 结构化领域对象，并把结果记为 该调用返回的结果；调用 `_memory_body_hash_payload` 完成该函数的一项辅助处理，并把结果记为 结构化请求载荷；断言当前输入内容不属于结构化请求载荷；不满足就终止当前测试或流程；读取结构化请求载荷中的对应字段中的对应字段，并保存为 源码或文档锚点。
断言当前输入内容不属于源码或文档锚点；不满足就终止当前测试或流程；断言当前输入内容不属于源码或文档锚点；不满足就终止当前测试或流程。
```

#### `test_phase38_memory_hash_projection_binds_comparison_identity`

- **源码**：`tests/test_chat_memory.py:278`
- **签名**：`def test_phase38_memory_hash_projection_binds_comparison_identity() -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `ConversationMemoryBody` 结构化领域对象，并把结果记为 当前值；调用 `_memory_body_hash_payload` 完成该函数的一项辅助处理，并把结果记为 结构化请求载荷；断言结构化请求载荷中的对应字段等于'phase38-v2'；不满足就终止当前测试或流程；读取结构化请求载荷中的对应字段中的对应字段，并保存为 源码或文档锚点。
断言源码或文档锚点中的对应字段等于'a' × 64；不满足就终止当前测试或流程；断言源码或文档锚点中的对应字段等于'job-base'；不满足就终止当前测试或流程。
```

### `tests/test_chat_prompt_budget.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `message_pair`

- **源码**：`tests/test_chat_prompt_budget.py:20`
- **签名**：`def message_pair(index: int, content_chars: int = 120)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前候选项的索引、内容字符数，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `index` | `int` | 候选集合中的零基索引，用于定位选中项；它不是业务 ID 或内容 Hash。 |
| `content_chars` | `int` | 名为 `content_chars` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。；默认 120 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
计算组合或计算已有值，并保存为 当前处理结果；计算根据字段和固定文本生成格式化文本，并保存为 当前处理结果的 ID；构造 `ChatMessage` 结构化领域对象，并把结果记为 该调用返回的结果；构造 `ChatMessage` 结构化领域对象，并把结果记为 该调用返回的结果。
返回当前构造的顺序或去重集合。
```

#### `source`

- **源码**：`tests/test_chat_prompt_budget.py:43`
- **签名**：`def source(citation_id: str, content: str, source_type: str) -> GroundingSource`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收论文引用证据的 ID、业务内容、来源类型，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `GroundingSource` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `citation_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `content` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |
| `source_type` | `str` | 名为 `source_type` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。；默认 'job' |

**输出**

- **Python 类型**：`GroundingSource`
- **语义**：返回 `GroundingSource` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `GroundingSource` 结构化领域对象。
```

#### `bundle`

- **源码**：`tests/test_chat_prompt_budget.py:60`
- **签名**：`def bundle(*extra: GroundingSource) -> GroundingBundle`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `GroundingBundle` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `*extra` | `GroundingSource` | 额外位置参数序列。 |

**输出**

- **Python 类型**：`GroundingBundle`
- **语义**：返回 `GroundingBundle` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `GroundingBundle` 结构化领域对象。
```

#### `test_history_budget_keeps_complete_newest_exchange`

- **源码**：`tests/test_chat_prompt_budget.py:73`
- **签名**：`def test_history_budget_keeps_complete_newest_exchange()`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
遍历并筛选输入，将整理后的结果保存为 当前处理结果；遍历并筛选输入，将整理后的结果保存为 历史对话或运行记录；计算数量、边界或类型判断结果，并把结果记为 字符数；调用 `build_budgeted_chat_prompt` 组装当前阶段需要的领域对象，并把结果记为 阶段处理结果。
断言当前输入内容等于[5, 6]；不满足就终止当前测试或流程；断言调用方职责角色等于'user'；不满足就终止当前测试或流程；断言当前处理结果等于面向用户或日志的提示信息的 ID；不满足就终止当前测试或流程。
```

#### `test_oversized_optional_source_is_not_in_prompt_or_whitelist`

- **源码**：`tests/test_chat_prompt_budget.py:99`
- **签名**：`def test_oversized_optional_source_is_not_in_prompt_or_whitelist()`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `source` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `build_budgeted_chat_prompt` 组装当前阶段需要的领域对象，并把结果记为 阶段处理结果；断言当前输入内容等于{'job:current'}；不满足就终止当前测试或流程；断言当前输入内容不属于发给模型的结构化提示；不满足就终止当前测试或流程。
```

#### `test_malformed_history_is_rejected_instead_of_silently_sliced`

- **源码**：`tests/test_chat_prompt_budget.py:122`
- **签名**：`def test_malformed_history_is_rejected_instead_of_silently_sliced()`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `message_pair` 完成该函数的一项辅助处理，并把结果记为 多个解包结果。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `build_budgeted_chat_prompt` 组装当前阶段需要的领域对象，退出时自动清理资源。
```

#### `test_too_small_budget_fails_closed`

- **源码**：`tests/test_chat_prompt_budget.py:137`
- **签名**：`def test_too_small_budget_fails_closed()`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `build_budgeted_chat_prompt` 组装当前阶段需要的领域对象，退出时自动清理资源。
```

### `tests/test_chat_provider.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_chat_provider_returns_structured_draft`

- **源码**：`tests/test_chat_provider.py:9`
- **签名**：`def test_chat_provider_returns_structured_draft()`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
去除当前输入内容的首尾空白，并把规范化后的文本记为 发给模型的结构化提示；调用 `辅助操作` 完成该函数的一项辅助处理，并把结果记为 草稿对象；断言“对当前处理结果中的文本执行规范化或拆分”后得到肯定结果；不满足就终止当前测试或流程；断言辅助操作“构造临时集合、映射或轻量领域对象”的结果不大于{'job:current'}；不满足就终止当前测试或流程。
```

### `tests/test_chat_provider_difficulty_cases.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_chat_provider_difficulty_matrix_is_complete_and_valid`

- **源码**：`tests/test_chat_provider_difficulty_cases.py:15`
- **签名**：`def test_chat_provider_difficulty_matrix_is_complete_and_valid() -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
按稳定规则整理结果顺序，并把结果记为 该调用返回的结果；断言当前输入内容等于['difficulty_easy.json', 'difficulty_hard.json', 'difficulty_medium.json']；不满足就终止当前测试或流程；遍历并筛选输入，将整理后的结果保存为 当前处理结果；断言当前处理结果等于{'easy': 4, 'hard': 3, 'medium': 3}；不满足就终止当前测试或流程。
遍历并筛选输入，将整理后的结果保存为 评测用例集合；构造 `Counter` 结构化领域对象，并把结果记为 该调用返回的结果；断言当前处理结果等于{'difficulty-easy': 4, 'difficulty-medium': 3, 'difficulty-hard': 3}；不满足就终止当前测试或流程；计算按字段初始化键值映射，并保存为 期望集合。
遍历由评测用例集合组成的集合或迭代器，每次把当前项记为评测用例：
    调用 `resolve_evaluation_path` 解析、规范化或转换当前输入，并把结果记为 测试夹具的路径；复制、序列化或校验结构化领域对象，并把结果记为 复现实验场景；调用 `next` 完成该函数的一项辅助处理，并把结果记为 等级；断言复现实验场景的 ID等于评测用例的 ID；不满足就终止当前测试或流程。
    断言当前处理结果等于期望集合中的对应字段；不满足就终止当前测试或流程；断言记忆集合等于[]；不满足就终止当前测试或流程；断言当前可迭代输入中每一项都满足“草稿为空”的项；不满足就终止当前测试或流程。
计算按字段初始化键值映射，并保存为 当前处理结果；遍历并筛选输入，将整理后的结果保存为 用例集合的 ID。
遍历辅助操作产生的可迭代结果（调用 `items` 完成该函数的一项辅助处理），每次把当前项记为多个解包结果：
    读取用例集合的 ID中的对应字段，并保存为 评测用例；调用 `resolve_evaluation_path` 解析、规范化或转换当前输入，并把结果记为 测试夹具的路径；调用 `model_validate_json` 完成该函数的一项辅助处理，并把结果记为 复现实验场景；读取对话记忆，并保存为 记忆。
    断言记忆不为空；不满足就终止当前测试或流程；断言当前处理结果是真；不满足就终止当前测试或流程；断言当前处理结果 的长度等于期望值中的对应字段；不满足就终止当前测试或流程；断言当前处理结果 的长度等于期望值中的对应字段；不满足就终止当前测试或流程。
    断言最小记录版本号等于期望值中的对应字段；不满足就终止当前测试或流程；断言最小当前处理结果等于期望值中的对应字段；不满足就终止当前测试或流程；断言最大当前处理结果等于期望值中的对应字段；不满足就终止当前测试或流程；断言最小对话记忆运行等于期望值中的对应字段；不满足就终止当前测试或流程。
    断言最大对话记忆运行等于期望值中的对应字段；不满足就终止当前测试或流程。
```

### `tests/test_chat_service.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `FakeInteraction.get_job`

- **源码**：`tests/test_chat_service.py:19`
- **签名**：`def get_job(self, job_id: str)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收复现任务 ID，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `未显式标注（存在 return）` 的领域结果。

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
断言复现任务 ID等于'job-1'；不满足就终止当前测试或流程；调用 `make_job` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `FakeContextBuilder.build`

- **源码**：`tests/test_chat_service.py:25`
- **签名**：`def build(self, *, job_id: str, question: str)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收复现任务 ID、论文复现问题或用户问题，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

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
断言复现任务 ID等于'job-1'；不满足就终止当前测试或流程；断言论文复现问题或用户问题有值或为真；不满足就终止当前测试或流程；构造并返回 `GroundingBundle` 结构化领域对象。
```

#### `FakeContextBuilder.build_job_only`

- **源码**：`tests/test_chat_service.py:56`
- **签名**：`def build_job_only(self, *, job_id: str, question: str)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收复现任务 ID、论文复现问题或用户问题，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `未显式标注（存在 return）` 的领域结果。

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
调用 `build` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；构造并返回 `GroundingBundle` 结构化领域对象。
```

#### `FakeMemoryCompactor.__init__`

- **源码**：`tests/test_chat_service.py:69`
- **签名**：`def __init__(self: 未显式标注, outcome: MemoryCompactionOutcome | None) -> None（隐式）`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收执行结论，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `outcome` | `MemoryCompactionOutcome | None` | 前序调用产生的结构化响应、结果或执行结论，供当前函数继续判断或投影。；默认 空值 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算使用固定配置或常量值，并保存为 功能是否启用的开关；计算计算当前表达式的结果，并保存为 执行结论；计算使用固定配置或常量值，并保存为 工具或模型调用记录集合。
```

#### `FakeMemoryCompactor.ensure_memory`

- **源码**：`tests/test_chat_service.py:81`
- **签名**：`def ensure_memory(self, job_id: str) -> MemoryCompactionOutcome`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收复现任务 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `MemoryCompactionOutcome` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`MemoryCompactionOutcome`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
断言复现任务 ID等于'job-1'；不满足就终止当前测试或流程；将新的计算结果累加或合并到工具或模型调用记录集合；返回执行结论的当前值。
```

#### `_service`

- **源码**：`tests/test_chat_service.py:87`
- **签名**：`def _service(tmp_path: 未显式标注, invoker: 未显式标注, compactor: 未显式标注, prompt_max_chars: 未显式标注, redactor: 未显式标注, tool_loop: 未显式标注) -> 未显式标注（存在 return）`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径、工具或模型调用器、当前处理结果、字符数等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `invoker` | `未显式标注` | 可调用依赖；由当前函数在受控位置调用。 |
| `compactor` | `未显式标注` | 名为 `compactor` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。；默认 空值 |
| `prompt_max_chars` | `未显式标注` | 名为 `prompt_max_chars` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。；默认 12000 |
| `redactor` | `未显式标注` | 敏感信息脱敏器；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 空值 |
| `tool_loop` | `未显式标注` | 名为 `tool_loop` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。；默认 空值 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
构造 `SqliteChatRepository` 结构化领域对象，并把结果记为 持久化仓库；调用 `initialize` 完成该函数的一项辅助处理；构造并返回 `ChatService` 结构化领域对象。
```

#### `test_known_citation_is_projected_by_server`

- **源码**：`tests/test_chat_service.py:115`
- **签名**：`def test_known_citation_is_projected_by_server(tmp_path)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_service` 完成该函数的一项辅助处理，并把结果记为 领域服务对象；调用 `ask` 完成该函数的一项辅助处理，并把结果记为 结构化响应；读取论文引用证据集合中的对应字段，并保存为 论文引用证据；断言Artifact的 ID等于'report'；不满足就终止当前测试或流程。
断言Artifact的 SHA-256等于'a' × 64；不满足就终止当前测试或流程。
```

#### `test_unknown_citation_fails_closed`

- **源码**：`tests/test_chat_service.py:135`
- **签名**：`def test_unknown_citation_fails_closed(tmp_path)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_service` 完成该函数的一项辅助处理，并把结果记为 领域服务对象；调用 `ask` 完成该函数的一项辅助处理，并把结果记为 结构化响应；断言当前输入内容属于业务内容；不满足就终止当前测试或流程；断言论文引用证据集合等于[]；不满足就终止当前测试或流程。
```

#### `test_answer_without_citation_fails_closed`

- **源码**：`tests/test_chat_service.py:154`
- **签名**：`def test_answer_without_citation_fails_closed(tmp_path)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_service` 完成该函数的一项辅助处理，并把结果记为 领域服务对象；调用 `ask` 完成该函数的一项辅助处理，并把结果记为 结构化响应；断言当前输入内容属于业务内容；不满足就终止当前测试或流程；断言论文引用证据集合等于[]；不满足就终止当前测试或流程。
```

#### `test_replayed_request_does_not_call_any_provider_twice`

- **源码**：`tests/test_chat_service.py:174`
- **签名**：`def test_replayed_request_does_not_call_any_provider_twice(tmp_path)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：无业务返回值；通过断言或预期异常验证目标行为。

**伪代码**

```text
计算使用固定配置或常量值，并保存为 当前处理结果；构造 `FakeMemoryCompactor` 结构化领域对象，并把结果记为 该调用返回的结果。
定义内部辅助函数 `invoke`，供当前函数在后续步骤中调用。
调用 `_service` 完成该函数的一项辅助处理，并把结果记为 领域服务对象；调用 `ask` 完成该函数的一项辅助处理，并把结果记为 第一项；调用 `ask` 完成该函数的一项辅助处理，并把结果记为 第二项；断言当前处理结果等于1；不满足就终止当前测试或流程。
断言工具或模型调用记录集合等于1；不满足就终止当前测试或流程；断言重放的是假；不满足就终止当前测试或流程；断言重放的是真；不满足就终止当前测试或流程；断言当前处理结果等于当前处理结果；不满足就终止当前测试或流程。
```

#### `test_replayed_request_does_not_call_any_provider_twice.invoke`

- **源码**：`tests/test_chat_service.py:178`
- **签名**：`def invoke(_prompt: str, _job_id: str) -> ChatDraft`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收发给模型的结构化提示、复现任务 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ChatDraft` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `_prompt` | `str` | 名为 `_prompt` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `_job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`ChatDraft`
- **语义**：返回 `ChatDraft` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
声明后续会读写外层作用域中的 当前处理结果；将新的计算结果累加或合并到当前处理结果；构造并返回 `ChatDraft` 结构化领域对象。
```

#### `test_memory_degradation_does_not_fail_grounded_answer`

- **源码**：`tests/test_chat_service.py:209`
- **签名**：`def test_memory_degradation_does_not_fail_grounded_answer(tmp_path)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `FakeMemoryCompactor` 结构化领域对象，并把结果记为 该调用返回的结果；调用 `_service` 完成该函数的一项辅助处理，并把结果记为 领域服务对象；调用 `ask` 完成该函数的一项辅助处理，并把结果记为 结构化响应；断言Artifact的 ID等于'report'；不满足就终止当前测试或流程。
断言功能是否启用的开关是真；不满足就终止当前测试或流程；断言当前处理结果是真；不满足就终止当前测试或流程。
```

#### `test_service_uses_true_newest_history_after_200_messages`

- **源码**：`tests/test_chat_service.py:238`
- **签名**：`def test_service_uses_true_newest_history_after_200_messages(tmp_path)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：无业务返回值；通过断言或预期异常验证目标行为。

**伪代码**

```text
将 当前处理结果 初始化为空列表，用来收集后续结果。
定义内部辅助函数 `invoke`，供当前函数在后续步骤中调用。
调用 `_service` 完成该函数的一项辅助处理，并把结果记为 领域服务对象。
遍历限定范围内的序列，每次把当前项记为当前候选项的索引，然后调用 `append_exchange` 完成该函数的一项辅助处理。
调用 `ask` 完成该函数的一项辅助处理；断言当前输入内容属于当前处理结果中的对应字段；不满足就终止当前测试或流程；断言当前输入内容不属于当前处理结果中的对应字段；不满足就终止当前测试或流程。
```

#### `test_service_uses_true_newest_history_after_200_messages.invoke`

- **源码**：`tests/test_chat_service.py:241`
- **签名**：`def invoke(prompt: str, _job_id: str) -> ChatDraft`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收发给模型的结构化提示、复现任务 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ChatDraft` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `prompt` | `str` | 用户目标、检索问题、反馈或待处理文本；会作为当前阶段的业务语境输入，并可能受到长度/脱敏约束。 |
| `_job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`ChatDraft`
- **语义**：返回 `ChatDraft` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
把发给模型的结构化提示追加或合并到当前处理结果；构造并返回 `ChatDraft` 结构化领域对象。
```

#### `test_secret_is_redacted_across_all_chat_boundaries`

- **源码**：`tests/test_chat_service.py:269`
- **签名**：`def test_secret_is_redacted_across_all_chat_boundaries(tmp_path)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，Phase 42: 已知 Secret 不能进入 Prompt、Chat Store 或响应。该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：无业务返回值；通过断言或预期异常验证目标行为。

**伪代码**

```text
计算使用固定配置或常量值，并保存为 敏感凭据；调用 `from_values` 完成该函数的一项辅助处理，并把结果记为 敏感信息脱敏器。
定义内部类型 `CapturingInvoker`，用于组织当前函数的临时逻辑。
构造 `CapturingInvoker` 结构化领域对象，并把结果记为 该调用返回的结果；调用 `_service` 完成该函数的一项辅助处理，并把结果记为 领域服务对象；调用 `ask` 完成该函数的一项辅助处理，并把结果记为 结构化响应；断言敏感凭据不属于当前处理结果中的对应字段；不满足就终止当前测试或流程。
断言当前输入内容属于当前处理结果中的对应字段；不满足就终止当前测试或流程；断言敏感凭据不属于业务内容；不满足就终止当前测试或流程；断言敏感凭据不属于业务内容；不满足就终止当前测试或流程；调用 `list_messages` 读取或查询当前阶段需要的数据，并把结果记为 对话或日志消息集合。
遍历由对话或日志消息集合组成的集合或迭代器，每次把当前项记为面向用户或日志的提示信息，然后断言敏感凭据不属于业务内容；不满足就终止当前测试或流程。
```

#### `test_secret_is_redacted_across_all_chat_boundaries.CapturingInvoker.__init__`

- **源码**：`tests/test_chat_service.py:276`
- **签名**：`def __init__(self)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
将 当前处理结果 初始化为空列表，用来收集后续结果。
```

#### `test_secret_is_redacted_across_all_chat_boundaries.CapturingInvoker.__call__`

- **源码**：`tests/test_chat_service.py:279`
- **签名**：`def __call__(self, prompt: str, _job_id: str) -> ChatDraft`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收发给模型的结构化提示、复现任务 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ChatDraft` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `prompt` | `str` | 用户目标、检索问题、反馈或待处理文本；会作为当前阶段的业务语境输入，并可能受到长度/脱敏约束。 |
| `_job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`ChatDraft`
- **语义**：返回 `ChatDraft` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
把发给模型的结构化提示追加或合并到当前处理结果；构造并返回 `ChatDraft` 结构化领域对象。
```

#### `test_chat_package_cannot_import_execution_layers`

- **源码**：`tests/test_chat_service.py:318`
- **签名**：`def test_chat_package_cannot_import_execution_layers()`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，Chat Agent 只能读公开投影，不能依赖任何执行入口。该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合多个值形成元组，并保存为 当前处理结果；读取前一步操作返回对象的当前处理结果中的对应字段，并保存为 项目根目录。
遍历辅助操作产生的可迭代结果（枚举当前输入内容下符合范围的文件系统项），每次把当前项记为文件或目录路径：
    将 Python 源码解析为抽象语法树，并把结果记为 该调用返回的结果；将 当前处理结果 初始化为空列表，用来收集后续结果。
    遍历语法树节点集合，每次把当前项记为当前流程节点：
        如果“计算数量、边界或类型判断结果”后得到肯定结果：
            把新的处理结果追加或合并到当前处理结果。
        否则：
            如果“计算数量、边界或类型判断结果”后得到肯定结果，就把新的处理结果追加或合并到当前处理结果。
    遍历并筛选输入，将整理后的结果保存为 当前处理结果；断言当前处理结果等于[]，失败时附带断言说明；不满足就终止当前测试或流程。
```

### `tests/test_chat_store.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_repository`

- **源码**：`tests/test_chat_store.py:14`
- **签名**：`def _repository(tmp_path) -> SqliteChatRepository`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `SqliteChatRepository` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`SqliteChatRepository`
- **语义**：返回 `SqliteChatRepository` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造 `SqliteChatRepository` 结构化领域对象，并把结果记为 持久化仓库；调用 `initialize` 完成该函数的一项辅助处理；返回持久化仓库的当前值。
```

#### `test_exchange_is_atomic_ordered_and_replayable`

- **源码**：`tests/test_chat_store.py:22`
- **签名**：`def test_exchange_is_atomic_ordered_and_replayable(tmp_path)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_repository` 完成该函数的一项辅助处理，并把结果记为 持久化仓库；构造 `ChatCitation` 结构化领域对象，并把结果记为 论文引用证据；调用 `append_exchange` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；断言已创建记录是真；不满足就终止当前测试或流程。
断言当前处理结果等于1；不满足就终止当前测试或流程；断言当前处理结果等于2；不满足就终止当前测试或流程；断言当前处理结果等于面向用户或日志的提示信息的 ID；不满足就终止当前测试或流程；断言论文引用证据集合等于[论文引用证据]；不满足就终止当前测试或流程。
调用 `append_exchange` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；断言已创建是假；不满足就终止当前测试或流程；断言当前处理结果等于当前处理结果；不满足就终止当前测试或流程；断言当前处理结果等于当前处理结果；不满足就终止当前测试或流程。
断言辅助操作“调用 `list_messages` 读取或查询当前阶段需要的数据”的结果等于[当前处理结果, 当前处理结果]；不满足就终止当前测试或流程。
```

#### `test_idempotency_key_reuse_with_other_question_is_rejected`

- **源码**：`tests/test_chat_store.py:69`
- **签名**：`def test_idempotency_key_reuse_with_other_question_is_rejected(tmp_path)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_repository` 完成该函数的一项辅助处理，并把结果记为 持久化仓库；调用 `append_exchange` 完成该函数的一项辅助处理。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `find_exchange` 读取或查询当前阶段需要的数据，退出时自动清理资源。
```

#### `test_messages_are_isolated_by_job_id`

- **源码**：`tests/test_chat_store.py:88`
- **签名**：`def test_messages_are_isolated_by_job_id(tmp_path)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_repository` 完成该函数的一项辅助处理，并把结果记为 持久化仓库；调用 `append_exchange` 完成该函数的一项辅助处理；断言辅助操作“调用 `list_messages` 读取或查询当前阶段需要的数据”的结果等于[]；不满足就终止当前测试或流程。
```

#### `test_recent_messages_returns_true_newest_after_200`

- **源码**：`tests/test_chat_store.py:106`
- **签名**：`def test_recent_messages_returns_true_newest_after_200(tmp_path)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_repository` 完成该函数的一项辅助处理，并把结果记为 持久化仓库。
遍历限定范围内的序列，每次把当前项记为当前候选项的索引，然后调用 `append_exchange` 完成该函数的一项辅助处理。
调用 `list_recent_messages` 读取或查询当前阶段需要的数据，并把结果记为 该调用返回的结果；断言当前输入内容等于辅助操作“构造临时集合、映射或轻量领域对象”的结果；不满足就终止当前测试或流程；断言业务内容等于'answer 104'；不满足就终止当前测试或流程。
```

#### `test_message_range_is_inclusive_ordered_and_bounded`

- **源码**：`tests/test_chat_store.py:127`
- **签名**：`def test_message_range_is_inclusive_ordered_and_bounded(tmp_path)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_repository` 完成该函数的一项辅助处理，并把结果记为 持久化仓库。
遍历限定范围内的序列，每次把当前项记为当前候选项的索引，然后调用 `append_exchange` 完成该函数的一项辅助处理。
调用 `list_messages_range` 读取或查询当前阶段需要的数据，并把结果记为 数据库记录行集合；断言当前输入内容等于[3, 4, 5, 6]；不满足就终止当前测试或流程；断言辅助操作“调用 `latest_sequence` 完成该函数的一项辅助处理”的结果等于6；不满足就终止当前测试或流程。
```

#### `test_delete_job_messages_also_deletes_memory_versions`

- **源码**：`tests/test_chat_store.py:149`
- **签名**：`def test_delete_job_messages_also_deletes_memory_versions(tmp_path)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_repository` 完成该函数的一项辅助处理，并把结果记为 持久化仓库；调用 `append_exchange` 完成该函数的一项辅助处理；构造 `ConversationMemory` 结构化领域对象，并把结果记为 记忆；调用 `save_memory` 持久化或更新当前领域数据。
调用 `delete_job_messages` 持久化或更新当前领域数据，并把结果记为 该调用返回的结果；断言当前处理结果等于2；不满足就终止当前测试或流程；断言辅助操作“调用 `list_messages` 读取或查询当前阶段需要的数据”的结果等于[]；不满足就终止当前测试或流程；断言辅助操作“调用 `get_latest_memory` 读取或查询当前阶段需要的数据”的结果为空；不满足就终止当前测试或流程。
```

### `tests/test_comparison_api.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `FakeComparisonService.__init__`

- **源码**：`tests/test_comparison_api.py:15`
- **签名**：`def __init__(self)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `make_report` 完成该函数的一项辅助处理，并把结果记为 MCP 评测或运行报告；计算使用固定配置或常量值，并保存为 当前处理结果。
```

#### `FakeComparisonService.create`

- **源码**：`tests/test_comparison_api.py:19`
- **签名**：`def create(self, request)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收业务请求，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

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
把传入参数保存到实例字段（业务请求 → 当前处理结果）；返回MCP 评测或运行报告的当前值。
```

#### `FakeComparisonService.get`

- **源码**：`tests/test_comparison_api.py:23`
- **签名**：`def get(self, comparison_id: str)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收SDK 或 MCP 运行升级比较结果的 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `comparison_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
如果SDK 或 MCP 运行升级比较结果的 ID不等于SDK 或 MCP 运行升级比较结果的 ID，就拒绝继续处理并抛出 `ComparisonNotFoundError`，向调用方报告输入或运行失败。
返回MCP 评测或运行报告的当前值。
```

#### `FakeComparisonService.list_for_job`

- **源码**：`tests/test_comparison_api.py:28`
- **签名**：`def list_for_job(self, job_id: str, *, limit: int = 100)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收复现任务 ID、结果数量上限，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。；默认 100 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
移除结果数量上限中的当前内容。
如果复现任务 ID不属于{'job-base', 'job-target'}，就构造并返回 `ComparisonListResponse` 结构化领域对象。
调用 `from_report` 完成该函数的一项辅助处理，并把结果记为 当前处理项；构造并返回 `ComparisonListResponse` 结构化领域对象。
```

#### `_client`

- **源码**：`tests/test_comparison_api.py:36`
- **签名**：`def _client() -> tuple[TestClient, FakeComparisonService]`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`tuple[TestClient, FakeComparisonService]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
构造 `FakeComparisonService` 结构化领域对象，并把结果记为 领域服务对象；构造 `FastAPI` 结构化领域对象，并把结果记为 该调用返回的结果；计算使用固定配置或常量值，并保存为 当前处理结果；读取领域服务对象，并保存为 后续步骤使用的结果。
调用 `include_router` 完成该函数的一项辅助处理；调用 `install_error_handlers` 完成该函数的一项辅助处理；返回当前构造的顺序或去重集合。
```

#### `test_create_get_and_list_comparison_api`

- **源码**：`tests/test_comparison_api.py:46`
- **签名**：`def test_create_get_and_list_comparison_api() -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_client` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；调用 `post` 完成该函数的一项辅助处理，并把结果记为 已创建记录；断言状态等于201；不满足就终止当前测试或流程；读取前一步操作返回对象中的对应字段，并保存为 SDK 或 MCP 运行升级比较结果的 ID。
断言任务的 ID等于'job-base'；不满足就终止当前测试或流程；从外部服务客户端读取所需的状态或领域记录，并把结果记为 该调用返回的结果；断言状态等于200；不满足就终止当前测试或流程；断言前一步操作返回对象中的对应字段等于SDK 或 MCP 运行升级比较结果的 Hash；不满足就终止当前测试或流程。
从外部服务客户端读取所需的状态或领域记录，并把结果记为 该调用返回的结果；断言状态等于200；不满足就终止当前测试或流程；断言前一步操作返回对象中的对应字段等于1；不满足就终止当前测试或流程。
```

#### `test_missing_comparison_uses_stable_api_error`

- **源码**：`tests/test_comparison_api.py:69`
- **签名**：`def test_missing_comparison_uses_stable_api_error() -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_client` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；从外部服务客户端读取所需的状态或领域记录，并把结果记为 结构化响应；断言状态等于404；不满足就终止当前测试或流程；断言前一步操作返回对象中的对应字段等于'COMPARISON_NOT_FOUND'；不满足就终止当前测试或流程。
```

### `tests/test_comparison_repository.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_repository`

- **源码**：`tests/test_comparison_repository.py:13`
- **签名**：`def _repository(tmp_path)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
构造并返回 `FileComparisonRepository` 结构化领域对象。
```

#### `test_repository_round_trip_is_idempotent`

- **源码**：`tests/test_comparison_repository.py:22`
- **签名**：`def test_repository_round_trip_is_idempotent(tmp_path) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_repository` 完成该函数的一项辅助处理，并把结果记为 持久化仓库；调用 `make_report` 完成该函数的一项辅助处理，并把结果记为 MCP 评测或运行报告；调用 `save` 完成该函数的一项辅助处理，并把结果记为 第一项；调用 `save` 完成该函数的一项辅助处理，并把结果记为 第二项。
断言SDK 或 MCP 运行升级比较结果的 ID等于SDK 或 MCP 运行升级比较结果的 ID；不满足就终止当前测试或流程；断言辅助操作“从持久化仓库读取所需的状态或领域记录”的结果等于MCP 评测或运行报告；不满足就终止当前测试或流程；计算组合或计算已有值，并保存为 当前处理结果；断言“检查当前输入内容的文件系统属性”后得到肯定结果；不满足就终止当前测试或流程。
断言“检查当前输入内容的文件系统属性”后得到肯定结果；不满足就终止当前测试或流程；断言辅助操作“构造临时集合、映射或轻量领域对象”的结果等于[]；不满足就终止当前测试或流程。
```

#### `test_repository_detects_json_tampering`

- **源码**：`tests/test_comparison_repository.py:37`
- **签名**：`def test_repository_detects_json_tampering(tmp_path) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_repository` 完成该函数的一项辅助处理，并把结果记为 持久化仓库；调用 `save` 完成该函数的一项辅助处理，并把结果记为 MCP 评测或运行报告；计算组合或计算已有值，并保存为 文件或目录路径；将外部表示解析为结构化内容，并把结果记为 结构化请求载荷。
计算使用固定配置或常量值，并保存为 结构化请求载荷中的对应字段中的对应字段；将处理结果写入文件或目录路径指定的文件。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中从持久化仓库读取所需的状态或领域记录，退出时自动清理资源。
```

#### `test_repository_rejects_path_like_id`

- **源码**：`tests/test_comparison_repository.py:49`
- **签名**：`def test_repository_rejects_path_like_id(tmp_path) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_repository` 完成该函数的一项辅助处理，并把结果记为 持久化仓库。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中从持久化仓库读取所需的状态或领域记录，退出时自动清理资源。
```

#### `test_list_for_job_returns_both_comparison_sides`

- **源码**：`tests/test_comparison_repository.py:55`
- **签名**：`def test_list_for_job_returns_both_comparison_sides(tmp_path) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_repository` 完成该函数的一项辅助处理，并把结果记为 持久化仓库；调用 `save` 完成该函数的一项辅助处理，并把结果记为 MCP 评测或运行报告；调用 `list_for_job` 读取或查询当前阶段需要的数据，并把结果记为 页码；调用 `list_for_job` 读取或查询当前阶段需要的数据，并把结果记为 页码。
断言当前输入内容等于[SDK 或 MCP 运行升级比较结果的 ID]；不满足就终止当前测试或流程；断言当前输入内容等于[SDK 或 MCP 运行升级比较结果的 ID]；不满足就终止当前测试或流程。
```

### `tests/test_comparison_retention_inventory.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_comparison_root_is_counted_but_not_a_deletion_port`

- **源码**：`tests/test_comparison_retention_inventory.py:5`
- **签名**：`def test_comparison_root_is_counted_but_not_a_deletion_port() -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `build_inventory` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果；复制、序列化或校验结构化领域对象，并把结果记为 受控扫描根目录集合；断言受控扫描根目录集合中的对应字段等于辅助操作“将根目录规范化为受控的绝对路径”的结果；不满足就终止当前测试或流程；断言当前处理结果是假；不满足就终止当前测试或流程。
```

### `tests/test_comparison_schemas.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_comparison_request_rejects_same_job`

- **源码**：`tests/test_comparison_schemas.py:12`
- **签名**：`def test_comparison_request_rejects_same_job() -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中构造 `ComparisonCreateRequest` 结构化领域对象，退出时自动清理资源。
```

#### `test_comparison_hash_ignores_created_at`

- **源码**：`tests/test_comparison_schemas.py:20`
- **签名**：`def test_comparison_hash_ignores_created_at() -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `make_report` 完成该函数的一项辅助处理，并把结果记为 第一项；复制、序列化或校验结构化领域对象，并把结果记为 第二项；断言辅助操作“调用 `compute_comparison_hash` 计算内容身份、分数或派生结果”的结果等于辅助操作“调用 `compute_comparison_hash` 计算内容身份、分数或派生结果”的结果；不满足就终止当前测试或流程。
```

#### `test_report_identity_detects_snapshot_tampering`

- **源码**：`tests/test_comparison_schemas.py:28`
- **签名**：`def test_report_identity_detects_snapshot_tampering() -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `make_report` 完成该函数的一项辅助处理，并把结果记为 MCP 评测或运行报告；复制、序列化或校验结构化领域对象，并把结果记为 该调用返回的结果；复制、序列化或校验结构化领域对象，并把结果记为 该调用返回的结果。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `validate_report_identity` 校验当前输入或状态，退出时自动清理资源。
```

### `tests/test_comparison_service.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_sha`

- **源码**：`tests/test_comparison_service.py:27`
- **签名**：`def _sha(raw: bytes) -> str`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收原始内容，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `raw` | `bytes` | 原始字节内容；可用于文件、序列化载荷或摘要计算，不应直接当作普通文本记录。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回输入内容的 SHA-256 身份摘要，用于完整性校验，不是加密后的正文。

**伪代码**

```text
计算输入内容的 SHA-256 身份摘要，并返回处理结果。
```

#### `_workspace`

- **源码**：`tests/test_comparison_service.py:31`
- **签名**：`def _workspace(job_id: str, run_id: str, paper_sha256: str, commit: str) -> WorkspaceManifest`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收复现任务 ID、本次复现运行 ID、论文的 SHA-256、当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `run_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `paper_sha256` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。；默认 'a' × 64 |
| `commit` | `str` | 名为 `commit` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。；默认 'b' × 40 |

**输出**

- **Python 类型**：`WorkspaceManifest`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
构造 `WorkspaceManifest` 结构化领域对象，并把结果记为 草稿对象；复制、序列化或校验结构化领域对象，并返回处理结果。
```

#### `_job`

- **源码**：`tests/test_comparison_service.py:76`
- **签名**：`def _job(manifest: WorkspaceManifest, status: str) -> 未显式标注（存在 return）`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收运行或工作区 Manifest、当前状态，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `manifest` | `WorkspaceManifest` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |
| `status` | `str` | 来源、类别、用途、后端、状态或操作原因等控制字段；通常对应有限的业务枚举或审计文本。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：返回用于测试或读取流程的任务/夹具对象；对象携带稳定 ID、状态和关联 Manifest。

**伪代码**

```text
构造并返回 `SimpleNamespace` 结构化领域对象。
```

#### `_run_manifest`

- **源码**：`tests/test_comparison_service.py:100`
- **签名**：`def _run_manifest(job_id: str, run_id: str, command: str, final_status: str, ok: bool, returncode: int, errors: list[dict] | None) -> bytes`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收复现任务 ID、本次复现运行 ID、当前命令、状态等输入，用于驱动或监督一次论文复现运行，记录命令、工作目录、资源使用、状态迁移和失败原因，最终标注为 `bytes` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `run_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `command` | `str` | 待展示、校验或执行的命令文本/结构化命令；仅进入 Executor 路径后才可能产生执行副作用。 |
| `final_status` | `str` | 名为 `final_status` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `ok` | `bool` | 布尔条件或能力开关，用于控制流程分支。 |
| `returncode` | `int` | 名为 `returncode` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `errors` | `list[dict] | None` | 异常、错误记录或错误分类信息，用于失败处理和诊断。；默认 空值 |

**输出**

- **Python 类型**：`bytes`
- **语义**：返回序列化后的运行 Manifest 字节载荷，用于测试完整性校验和证据读取。

**伪代码**

```text
计算按字段初始化键值映射，并保存为 结构化请求载荷；将结构化内容序列化或编码为可传输表示，并返回处理结果。
```

#### `FakeJobs.__init__`

- **源码**：`tests/test_comparison_service.py:160`
- **签名**：`def __init__(self)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
将 复现任务记录集合、当前处理结果 初始化为空映射，用来收集后续结果。
```

#### `FakeJobs.add`

- **源码**：`tests/test_comparison_service.py:164`
- **签名**：`def add(self, job, manifest: WorkspaceManifest) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收复现任务记录、运行或工作区 Manifest，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job` | `未显式标注` | 任务、运行、Manifest、记录或证据领域对象；携带关联 ID、状态和内容身份。 |
| `manifest` | `WorkspaceManifest` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
读取复现任务记录，并保存为 复现任务记录集合中的对应字段；读取运行或工作区 Manifest，并保存为 当前处理结果中的对应字段。
```

#### `FakeJobs.get`

- **源码**：`tests/test_comparison_service.py:168`
- **签名**：`def get(self, job_id: str)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收复现任务 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

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
返回复现任务记录集合中的对应字段的当前值。
```

#### `FakeJobs.get_workspace_manifest`

- **源码**：`tests/test_comparison_service.py:171`
- **签名**：`def get_workspace_manifest(self, manifest_id: str) -> WorkspaceManifest`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收运行或工作区 Manifest的 ID，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `manifest_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`WorkspaceManifest`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
返回当前处理结果中的对应字段的当前值。
```

#### `FakeCatalog.__init__`

- **源码**：`tests/test_comparison_service.py:176`
- **签名**：`def __init__(self)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
将 Artifact 视图集合、当前处理结果 初始化为空映射，用来收集后续结果。
```

#### `FakeCatalog.add_run`

- **源码**：`tests/test_comparison_service.py:180`
- **签名**：`def add_run(self: 未显式标注, job: 未显式标注, manifest_bytes: bytes, output_sha: str) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收复现任务记录、运行或工作区 Manifest的字节内容、SHA，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job` | `未显式标注` | 任务、运行、Manifest、记录或证据领域对象；携带关联 ID、状态和内容身份。 |
| `manifest_bytes` | `bytes` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |
| `output_sha` | `str` | 名为 `output_sha` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `ArtifactView` 结构化领域对象，并把结果记为 Manifest视图；构造 `ArtifactView` 结构化领域对象，并把结果记为 视图；计算初始化顺序集合，并保存为 Artifact 视图集合中的对应字段；读取运行或工作区 Manifest的字节内容，并保存为 当前处理结果中的对应字段。
```

#### `FakeCatalog.list_views`

- **源码**：`tests/test_comparison_service.py:212`
- **签名**：`def list_views(self, job)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收复现任务记录，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `job` | `未显式标注` | 任务、运行、Manifest、记录或证据领域对象；携带关联 ID、状态和内容身份。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
构造临时集合、映射或轻量领域对象，并返回处理结果。
```

#### `FakeCatalog.open`

- **源码**：`tests/test_comparison_service.py:215`
- **签名**：`def open(self, *, job, artifact_id: str)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收复现任务记录、Artifact的 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

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
调用 `next` 完成该函数的一项辅助处理，并把结果记为 视图；读取当前处理结果中的对应字段，并保存为 原始内容；构造 `SimpleNamespace` 结构化领域对象，并把结果记为 工具或组件描述信息；构造 `SimpleNamespace` 结构化领域对象，并把结果记为 该调用返回的结果。
构造并返回 `SimpleNamespace` 结构化领域对象。
```

#### `_service`

- **源码**：`tests/test_comparison_service.py:237`
- **签名**：`def _service(tmp_path)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
构造 `FakeJobs` 结构化领域对象，并把结果记为 复现任务记录集合；构造 `FakeCatalog` 结构化领域对象，并把结果记为 模型、工具或 Artifact 目录；调用 `_workspace` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `_workspace` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
调用 `_job` 完成该函数的一项辅助处理，并把结果记为 任务；调用 `_job` 完成该函数的一项辅助处理，并把结果记为 任务；把任务追加或合并到复现任务记录集合；把任务追加或合并到复现任务记录集合。
调用 `_run_manifest` 完成该函数的一项辅助处理，并把结果记为 当前处理结果的字节内容；调用 `_run_manifest` 完成该函数的一项辅助处理，并把结果记为 待定位的代码对象或业务目标的字节内容；调用 `add_run` 完成该函数的一项辅助处理；调用 `add_run` 完成该函数的一项辅助处理。
构造 `FileComparisonRepository` 结构化领域对象，并把结果记为 持久化仓库；构造 `VerifiedRunEvidenceReader` 结构化领域对象，并把结果记为 证据读取器；返回当前构造的顺序或去重集合。
```

#### `test_command_projection_redacts_secrets_and_absolute_paths`

- **源码**：`tests/test_comparison_service.py:308`
- **签名**：`def test_command_projection_redacts_secrets_and_absolute_paths() -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `build_command_snapshot` 组装当前阶段需要的领域对象，并把结果记为 MCP 能力快照；断言当前输入内容不属于当前处理结果；不满足就终止当前测试或流程；断言当前输入内容不属于当前处理结果；不满足就终止当前测试或流程；断言当前输入内容属于当前处理结果；不满足就终止当前测试或流程。
断言当前命令的 SHA-256不为空；不满足就终止当前测试或流程；断言命令执行工作目录的 SHA-256不为空；不满足就终止当前测试或流程。
```

#### `test_service_creates_verified_deterministic_diff`

- **源码**：`tests/test_comparison_service.py:325`
- **签名**：`def test_service_creates_verified_deterministic_diff(tmp_path) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_service` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；构造 `ComparisonCreateRequest` 结构化领域对象，并把结果记为 业务请求；调用 `create` 完成该函数的一项辅助处理，并把结果记为 第一项；调用 `create` 完成该函数的一项辅助处理，并把结果记为 第二项。
断言SDK 或 MCP 运行升级比较结果的 ID等于SDK 或 MCP 运行升级比较结果的 ID；不满足就终止当前测试或流程；断言当前处理结果的数量不小于3；不满足就终止当前测试或流程；断言当前输入内容不小于{'command', 'execution', 'error', 'artifact'}；不满足就终止当前测试或流程；调用 `model_dump_json` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
断言当前输入内容不属于当前处理结果；不满足就终止当前测试或流程；断言当前输入内容不属于当前处理结果；不满足就终止当前测试或流程；断言当前处理结果中的对应字段等于当前处理结果；不满足就终止当前测试或流程；断言当前处理结果中的对应字段等于当前处理结果；不满足就终止当前测试或流程。
```

#### `test_service_rejects_cross_paper_by_default`

- **源码**：`tests/test_comparison_service.py:351`
- **签名**：`def test_service_rejects_cross_paper_by_default(tmp_path) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_service` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；读取当前处理结果中的对应字段，并保存为 待定位的代码对象或业务目标；调用 `_workspace` 完成该函数的一项辅助处理，并把结果记为 发生变化的内容；读取发生变化的内容，并保存为 当前处理结果中的对应字段。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `create` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `test_service_rejects_non_terminal_job`

- **源码**：`tests/test_comparison_service.py:370`
- **签名**：`def test_service_rejects_non_terminal_job(tmp_path) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_service` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；计算使用固定配置或常量值，并保存为 当前状态。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `create` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `test_service_detects_manifest_blob_tampering`

- **源码**：`tests/test_comparison_service.py:382`
- **签名**：`def test_service_detects_manifest_blob_tampering(tmp_path) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_service` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；计算组合多个值形成元组，并保存为 映射键或对象字段名；将新的计算结果累加或合并到当前处理结果中的对应字段。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `create` 完成该函数的一项辅助处理，退出时自动清理资源。
```

### `tests/test_rerun_api.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_proposal_record`

- **源码**：`tests/test_rerun_api.py:36`
- **签名**：`def _proposal_record(status: str, version: int) -> RerunProposalRecord`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前状态、记录版本号，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `status` | `str` | 来源、类别、用途、后端、状态或操作原因等控制字段；通常对应有限的业务枚举或审计文本。；默认 'pending' |
| `version` | `int` | 记录版本号；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 0 |

**输出**

- **Python 类型**：`RerunProposalRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
构造 `RerunCommandTemplate` 结构化领域对象，并把结果记为 草稿；复制、序列化或校验结构化领域对象，并把结果记为 该调用返回的结果；构造 `RerunProposal` 结构化领域对象，并把结果记为 草稿对象；调用 `proposal_hash` 完成该函数的一项辅助处理，并把结果记为 内容摘要。
复制、序列化或校验结构化领域对象，并把结果记为 该调用返回的结果；构造并返回 `RerunProposalRecord` 结构化领域对象。
```

#### `_fake_service`

- **源码**：`tests/test_rerun_api.py:99`
- **签名**：`def _fake_service() -> Mock`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `Mock` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`Mock`
- **语义**：返回 `Mock` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造 `Mock` 结构化领域对象，并把结果记为 领域服务对象；构造 `Mock` 结构化领域对象，并把结果记为 持久化仓库；计算使用固定配置或常量值，并保存为 值；调用 `_proposal_record` 完成该函数的一项辅助处理，并把结果记为 领域记录。
计算组合多个值形成元组，并保存为 值；读取领域记录，并保存为 值；计算组合多个值形成元组，并保存为 值；复制、序列化或校验结构化领域对象，并把结果记为 值。
返回领域服务对象的当前值。
```

#### `_client`

- **源码**：`tests/test_rerun_api.py:121`
- **签名**：`def _client(service: Mock | None = None)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收领域服务对象，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `service` | `Mock | None` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。；默认 空值 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
计算计算当前表达式的结果，并保存为 领域服务对象；构造 `FastAPI` 结构化领域对象，并把结果记为 该调用返回的结果；读取领域服务对象，并保存为 后续步骤使用的结果；计算使用固定配置或常量值，并保存为 当前处理结果。
调用 `include_router` 完成该函数的一项辅助处理；调用 `install_error_handlers` 完成该函数的一项辅助处理；返回当前构造的顺序或去重集合。
```

#### `test_create_rerun_proposal_requires_idempotency_key`

- **源码**：`tests/test_rerun_api.py:131`
- **签名**：`def test_create_rerun_proposal_requires_idempotency_key() -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_client` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；调用 `post` 完成该函数的一项辅助处理，并把结果记为 结构化响应；断言状态等于422；不满足就终止当前测试或流程。
```

#### `test_create_rerun_proposal_success`

- **源码**：`tests/test_rerun_api.py:152`
- **签名**：`def test_create_rerun_proposal_success() -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_client` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；调用 `post` 完成该函数的一项辅助处理，并把结果记为 结构化响应；断言状态等于200；不满足就终止当前测试或流程；调用 `json` 完成该函数的一项辅助处理，并把结果记为 待处理数据。
断言待处理数据中的对应字段是假；不满足就终止当前测试或流程；断言待处理数据中的对应字段中的对应字段等于'pending'；不满足就终止当前测试或流程；调用 `assert_called_once` 完成该函数的一项辅助处理。
```

#### `test_create_rerun_proposal_replay`

- **源码**：`tests/test_rerun_api.py:178`
- **签名**：`def test_create_rerun_proposal_replay() -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_fake_service` 完成该函数的一项辅助处理，并把结果记为 领域服务对象；计算组合多个值形成元组，并保存为 值；调用 `_client` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；调用 `post` 完成该函数的一项辅助处理，并把结果记为 结构化响应。
断言状态等于200；不满足就终止当前测试或流程；断言前一步操作返回对象中的对应字段是真；不满足就终止当前测试或流程。
```

#### `test_get_rerun_proposal_not_found`

- **源码**：`tests/test_rerun_api.py:203`
- **签名**：`def test_get_rerun_proposal_not_found() -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_fake_service` 完成该函数的一项辅助处理，并把结果记为 领域服务对象；构造 `RerunNotFoundError` 结构化领域对象，并把结果记为 该调用返回的结果；调用 `_client` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；从外部服务客户端读取所需的状态或领域记录，并把结果记为 结构化响应。
断言状态等于404；不满足就终止当前测试或流程；断言前一步操作返回对象中的对应字段等于'RERUN_PROPOSAL_NOT_FOUND'；不满足就终止当前测试或流程。
```

#### `test_submit_rerun_proposal_conflict`

- **源码**：`tests/test_rerun_api.py:212`
- **签名**：`def test_submit_rerun_proposal_conflict() -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_fake_service` 完成该函数的一项辅助处理，并把结果记为 领域服务对象；构造 `RerunConflictError` 结构化领域对象，并把结果记为 该调用返回的结果；调用 `_client` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；调用 `_proposal_record` 完成该函数的一项辅助处理，并把结果记为 领域记录。
调用 `post` 完成该函数的一项辅助处理，并把结果记为 结构化响应；断言状态等于409；不满足就终止当前测试或流程；断言前一步操作返回对象中的对应字段等于'RERUN_CONFLICT'；不满足就终止当前测试或流程。
```

#### `test_submit_rerun_proposal_expired`

- **源码**：`tests/test_rerun_api.py:229`
- **签名**：`def test_submit_rerun_proposal_expired() -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_fake_service` 完成该函数的一项辅助处理，并把结果记为 领域服务对象；构造 `RerunExpiredError` 结构化领域对象，并把结果记为 该调用返回的结果；调用 `_client` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；调用 `_proposal_record` 完成该函数的一项辅助处理，并把结果记为 领域记录。
调用 `post` 完成该函数的一项辅助处理，并把结果记为 结构化响应；断言状态等于409；不满足就终止当前测试或流程；断言前一步操作返回对象中的对应字段等于'RERUN_PROPOSAL_EXPIRED'；不满足就终止当前测试或流程。
```

#### `test_create_rerun_proposal_command_rejected`

- **源码**：`tests/test_rerun_api.py:246`
- **签名**：`def test_create_rerun_proposal_command_rejected() -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_fake_service` 完成该函数的一项辅助处理，并把结果记为 领域服务对象；构造 `RerunCommandRejectedError` 结构化领域对象，并把结果记为 该调用返回的结果；调用 `_client` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；调用 `post` 完成该函数的一项辅助处理，并把结果记为 结构化响应。
断言状态等于422；不满足就终止当前测试或流程；断言前一步操作返回对象中的对应字段等于'RERUN_COMMAND_REJECTED'；不满足就终止当前测试或流程。
```

#### `test_integrity_error_does_not_leak_detail`

- **源码**：`tests/test_rerun_api.py:273`
- **签名**：`def test_integrity_error_does_not_leak_detail() -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_fake_service` 完成该函数的一项辅助处理，并把结果记为 领域服务对象；构造 `RerunIntegrityError` 结构化领域对象，并把结果记为 该调用返回的结果；调用 `_client` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；调用 `post` 完成该函数的一项辅助处理，并把结果记为 结构化响应。
断言状态等于500；不满足就终止当前测试或流程；调用 `json` 完成该函数的一项辅助处理，并把结果记为 请求正文；断言请求正文中的对应字段等于'RERUN_INTEGRITY_ERROR'；不满足就终止当前测试或流程；断言当前输入内容不属于请求正文中的对应字段；不满足就终止当前测试或流程。
断言当前输入内容不属于请求正文中的对应字段；不满足就终止当前测试或流程。
```

### `tests/test_rerun_command_template.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_workspace`

- **源码**：`tests/test_rerun_command_template.py:25`
- **签名**：`def _workspace() -> WorkspaceManifest`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`WorkspaceManifest`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
构造并返回 `WorkspaceManifest` 结构化领域对象。
```

#### `_build`

- **源码**：`tests/test_rerun_command_template.py:72`
- **签名**：`def _build(command: str, edits: list[RerunArgumentEdit])`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前命令、命令修改项集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `command` | `str` | 待展示、校验或执行的命令文本/结构化命令；仅进入 Executor 路径后才可能产生执行副作用。 |
| `edits` | `list[RerunArgumentEdit]` | 命令修改项集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
调用 `build_command_template` 组装当前阶段需要的领域对象，并返回处理结果。
```

#### `test_build_and_resolve_template_changes_only_expected_option`

- **源码**：`tests/test_rerun_command_template.py:91`
- **签名**：`def test_build_and_resolve_template_changes_only_expected_option(tmp_path: 未显式标注) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_build` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；计算组合或计算已有值，并保存为 代码仓库；计算组合或计算已有值，并保存为 运行；计算组合或计算已有值，并保存为 当前处理结果。
创建代码仓库对应的目录；创建运行对应的目录；创建当前处理结果对应的目录；调用 `resolve_command_template` 解析、规范化或转换当前输入，并把结果记为 解析后的值。
对当前处理结果中的文本执行规范化或拆分，并把结果记为 实验程序命令行参数序列；断言实验程序命令行参数序列等于['python', 辅助操作“调用 `str` 完成该函数的一项辅助处理”的结果, '--dataset', 辅助操作“调用 `str` 完成该函数的一项辅助处理”的结果, '--output', 辅助操作“调用 `str` 完成该函数的一项辅助处理”的结果, '--epochs', '100', '--batch-size', '8']；不满足就终止当前测试或流程。
断言解析后的值中的对应字段等于辅助操作“调用 `str` 完成该函数的一项辅助处理”的结果；不满足就终止当前测试或流程；断言解析后的值中的对应字段等于'config'；不满足就终止当前测试或流程；断言解析后的值中的对应字段等于'high'；不满足就终止当前测试或流程。
```

#### `test_remove_existing_flag`

- **源码**：`tests/test_rerun_command_template.py:141`
- **签名**：`def test_remove_existing_flag() -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_build` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；遍历并筛选输入，将整理后的结果保存为 当前处理结果；断言当前输入内容不属于当前处理结果；不满足就终止当前测试或流程。
```

#### `test_rejects_unsafe_parent_command`

- **源码**：`tests/test_rerun_command_template.py:170`
- **签名**：`def test_rejects_unsafe_parent_command(command: str) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前命令，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `command` | `str` | 待展示、校验或执行的命令文本/结构化命令；仅进入 Executor 路径后才可能产生执行副作用。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `_build` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `test_rejects_stale_expected_old_value`

- **源码**：`tests/test_rerun_command_template.py:185`
- **签名**：`def test_rejects_stale_expected_old_value() -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `_build` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `test_rejects_new_absolute_path`

- **源码**：`tests/test_rerun_command_template.py:200`
- **签名**：`def test_rejects_new_absolute_path() -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `_build` 完成该函数的一项辅助处理，退出时自动清理资源。
```

### `tests/test_rerun_end_to_end.py`

**模块作用**：Phase 39 端到端控制面闭环测试。

#### `_parent_evidence`

- **源码**：`tests/test_rerun_end_to_end.py:30`
- **签名**：`def _parent_evidence() -> VerifiedRunEvidence`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `VerifiedRunEvidence` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`VerifiedRunEvidence`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
构造 `WorkspaceManifest` 结构化领域对象，并把结果记为 本次复现工作区；构造 `SimpleNamespace` 结构化领域对象，并把结果记为 复现任务记录；构造 `ArtifactView` 结构化领域对象，并把结果记为 Artifact；构造并返回 `VerifiedRunEvidence` 结构化领域对象。
```

#### `_build_service`

- **源码**：`tests/test_rerun_end_to_end.py:113`
- **签名**：`def _build_service(tmp_path)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，Build a RerunService with mocked reader and job_service。该函数接收临时工作目录路径，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
调用 `_parent_evidence` 完成该函数的一项辅助处理，并把结果记为 可追溯证据记录；构造 `Mock` 结构化领域对象，并把结果记为 证据读取器；读取可追溯证据记录，并保存为 值；构造 `SimpleNamespace` 结构化领域对象，并把结果记为 任务。
构造 `Mock` 结构化领域对象，并把结果记为 复现任务记录集合；计算组合多个值形成元组，并保存为 值；读取任务，并保存为 值；构造 `SqliteRerunRepository` 结构化领域对象，并把结果记为 持久化仓库。
构造 `RerunService` 结构化领域对象，并把结果记为 领域服务对象；返回当前构造的顺序或去重集合。
```

#### `test_e2e_create_submit_derives_new_job`

- **源码**：`tests/test_rerun_end_to_end.py:153`
- **签名**：`def test_e2e_create_submit_derives_new_job(tmp_path)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，Full control plane: create -> submit -> verify derived job。该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_build_service` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果；调用 `create_proposal` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果；断言已创建记录是真；不满足就终止当前测试或流程；断言当前状态等于'pending'；不满足就终止当前测试或流程。
读取修复或重跑提案，并保存为 修复或重跑提案；调用 `submit_proposal` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；断言已创建是真；不满足就终止当前测试或流程；断言当前状态等于'submitted'；不满足就终止当前测试或流程。
断言任务的 ID等于复现任务 ID；不满足就终止当前测试或流程；断言复现任务 ID不等于复现任务 ID；不满足就终止当前测试或流程；断言本次复现运行 ID不等于本次复现运行 ID；不满足就终止当前测试或流程；断言流程线程 ID不等于'rerun-thread-parent'；不满足就终止当前测试或流程。
读取函数关键字参数映射，并保存为 函数关键字参数映射；读取函数关键字参数映射中的对应字段，并保存为 业务请求；断言运行不为空；不满足就终止当前测试或流程；断言修复或重跑提案的 ID等于修复或重跑提案的 ID；不满足就终止当前测试或流程。
断言修复或重跑提案的 Hash等于修复或重跑提案的 Hash；不满足就终止当前测试或流程；读取实验程序命令行参数序列，并保存为 实验程序命令行参数序列；调用 `next` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；断言当前字段值等于'100'；不满足就终止当前测试或流程。
断言论文 PDF 路径为空；不满足就终止当前测试或流程；断言代码仓库根目录为空；不满足就终止当前测试或流程；断言论文资源为空；不满足就终止当前测试或流程；断言仓库资源为空；不满足就终止当前测试或流程。
断言函数关键字参数映射中的对应字段等于格式化文本：f'rerun-{proposal.proposal_id}'；不满足就终止当前测试或流程；断言函数关键字参数映射中的对应字段等于格式化文本：f'rerun-submit:{proposal.proposal_id}'；不满足就终止当前测试或流程。
```

#### `test_e2e_submit_is_idempotent`

- **源码**：`tests/test_rerun_end_to_end.py:223`
- **签名**：`def test_e2e_submit_is_idempotent(tmp_path)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，Replaying submit with same idempotency key returns same child。该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_build_service` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果；调用 `create_proposal` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果；读取修复或重跑提案，并保存为 修复或重跑提案；调用 `submit_proposal` 完成该函数的一项辅助处理，并把结果记为 多个解包结果。
断言已创建第一项是真；不满足就终止当前测试或流程；调用 `submit_proposal` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；断言已创建是假；不满足就终止当前测试或流程；断言复现任务 ID等于复现任务 ID；不满足就终止当前测试或流程。
断言当前处理结果的数量等于1；不满足就终止当前测试或流程。
```

#### `test_e2e_command_template_preserves_unedited_options`

- **源码**：`tests/test_rerun_end_to_end.py:271`
- **签名**：`def test_e2e_command_template_preserves_unedited_options(tmp_path)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，Unedited options from parent command must be preserved。该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_build_service` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果；调用 `create_proposal` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果；读取命令，并保存为 后续步骤使用的结果；遍历并筛选输入，将整理后的结果保存为 当前处理结果。
断言当前输入内容属于当前处理结果；不满足就终止当前测试或流程；断言当前输入内容属于当前处理结果；不满足就终止当前测试或流程。
```

#### `test_e2e_derived_job_carries_dataset_refs`

- **源码**：`tests/test_rerun_end_to_end.py:300`
- **签名**：`def test_e2e_derived_job_carries_dataset_refs(tmp_path)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，Dataset refs from parent workspace must be deep-copied to child。该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_build_service` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果；加载这一步需要的外部依赖；计算初始化顺序集合，并保存为 当前处理结果；调用 `create_proposal` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果。
调用 `submit_proposal` 完成该函数的一项辅助处理；读取函数关键字参数映射，并保存为 函数关键字参数映射；读取函数关键字参数映射中的对应字段，并保存为 业务请求；断言当前处理结果 的长度等于1；不满足就终止当前测试或流程。
断言对象名称等于'ntu_dataset'；不满足就终止当前测试或流程。
```

### `tests/test_rerun_repository.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_proposal`

- **源码**：`tests/test_rerun_repository.py:22`
- **签名**：`def _proposal() -> RerunProposal`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `RerunProposal` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`RerunProposal`
- **语义**：返回 `RerunProposal` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造 `RerunCommandTemplate` 结构化领域对象，并把结果记为 草稿；复制、序列化或校验结构化领域对象，并把结果记为 该调用返回的结果；构造 `RerunProposal` 结构化领域对象，并把结果记为 草稿对象；调用 `proposal_hash` 完成该函数的一项辅助处理，并把结果记为 内容摘要。
复制、序列化或校验结构化领域对象，并返回处理结果。
```

#### `_repository`

- **源码**：`tests/test_rerun_repository.py:75`
- **签名**：`def _repository(tmp_path) -> SqliteRerunRepository`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `SqliteRerunRepository` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`SqliteRerunRepository`
- **语义**：返回 `SqliteRerunRepository` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造 `SqliteRerunRepository` 结构化领域对象，并把结果记为 持久化仓库；调用 `initialize` 完成该函数的一项辅助处理；返回持久化仓库的当前值。
```

#### `test_create_is_idempotent`

- **源码**：`tests/test_rerun_repository.py:84`
- **签名**：`def test_create_is_idempotent(tmp_path) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_repository` 完成该函数的一项辅助处理，并把结果记为 持久化仓库；调用 `_proposal` 完成该函数的一项辅助处理，并把结果记为 修复或重跑提案；调用 `create` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；调用 `create` 完成该函数的一项辅助处理，并把结果记为 多个解包结果。
断言第一项已创建是真；不满足就终止当前测试或流程；断言第二项已创建是假；不满足就终止当前测试或流程；断言修复或重跑提案的 ID等于修复或重跑提案的 ID；不满足就终止当前测试或流程。
```

#### `test_same_create_key_with_different_request_conflicts`

- **源码**：`tests/test_rerun_repository.py:102`
- **签名**：`def test_same_create_key_with_different_request_conflicts(tmp_path) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_repository` 完成该函数的一项辅助处理，并把结果记为 持久化仓库；调用 `create` 完成该函数的一项辅助处理。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `find_create_replay` 读取或查询当前阶段需要的数据，退出时自动清理资源。
```

#### `test_submission_recovery_reuses_same_ownership`

- **源码**：`tests/test_rerun_repository.py:116`
- **签名**：`def test_submission_recovery_reuses_same_ownership(tmp_path) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_repository` 完成该函数的一项辅助处理，并把结果记为 持久化仓库；调用 `create` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；调用 `begin_submission` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；断言当前状态等于'submitting'；不满足就终止当前测试或流程。
调用 `begin_submission` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；断言当前状态等于'submitting'；不满足就终止当前测试或流程。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `begin_submission` 完成该函数的一项辅助处理，退出时自动清理资源。
调用 `complete_submission` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；断言当前状态等于'submitted'；不满足就终止当前测试或流程；断言任务的 ID等于'job-child'；不满足就终止当前测试或流程。
```

#### `test_only_pending_proposal_can_be_cancelled`

- **源码**：`tests/test_rerun_repository.py:157`
- **签名**：`def test_only_pending_proposal_can_be_cancelled(tmp_path) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_repository` 完成该函数的一项辅助处理，并把结果记为 持久化仓库；调用 `create` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；调用 `cancel` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；断言当前状态等于'cancelled'；不满足就终止当前测试或流程。
```

#### `test_expired_proposal_returns_expired_on_get`

- **源码**：`tests/test_rerun_repository.py:173`
- **签名**：`def test_expired_proposal_returns_expired_on_get(tmp_path) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算按字段初始化键值映射，并保存为 状态。
定义内部辅助函数 `clock`，供当前函数在后续步骤中调用。
构造 `SqliteRerunRepository` 结构化领域对象，并把结果记为 持久化仓库；调用 `initialize` 完成该函数的一项辅助处理；调用 `create` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；断言当前状态等于'pending'；不满足就终止当前测试或流程。
计算使用固定配置或常量值，并保存为 状态中的对应字段；从持久化仓库读取所需的状态或领域记录，并把结果记为 该调用返回的结果；断言当前状态等于'expired'；不满足就终止当前测试或流程；加载这一步需要的外部依赖。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `begin_submission` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `test_expired_proposal_returns_expired_on_get.clock`

- **源码**：`tests/test_rerun_repository.py:176`
- **签名**：`def clock()`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
返回状态中的对应字段的当前值。
```

### `tests/test_rerun_seed_node.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_normal_job_is_noop`

- **源码**：`tests/test_rerun_seed_node.py:8`
- **签名**：`def test_normal_job_is_noop() -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
断言辅助操作“调用 `rerun_seed_node` 完成该函数的一项辅助处理”的结果等于{}；不满足就终止当前测试或流程。
```

#### `test_rerun_seed_overrides_commands_and_clears_approval`

- **源码**：`tests/test_rerun_seed_node.py:12`
- **签名**：`def test_rerun_seed_overrides_commands_and_clears_approval(tmp_path: 未显式标注, monkeypatch: 未显式标注) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径、测试环境修改工具，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

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
调用 `setattr` 完成该函数的一项辅助处理；计算组合或计算已有值，并保存为 本次复现运行目录；计算按字段初始化键值映射，并保存为 复现流程状态；调用 `rerun_seed_node` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
断言“检查当前处理结果中的对应字段中的对应字段中的对应字段是否满足文本匹配条件”后得到肯定结果；不满足就终止当前测试或流程；断言当前处理结果中的对应字段为空；不满足就终止当前测试或流程；断言当前处理结果中的对应字段为空；不满足就终止当前测试或流程；断言当前处理结果中的对应字段为空；不满足就终止当前测试或流程。
断言当前处理结果中的对应字段为空；不满足就终止当前测试或流程；断言当前处理结果中的对应字段是假；不满足就终止当前测试或流程；断言“检查当前处理结果中的对应字段是否满足文本匹配条件”后得到肯定结果；不满足就终止当前测试或流程；断言当前处理结果中的对应字段 的长度等于1；不满足就终止当前测试或流程。
```

### `tests/test_rerun_service.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_evidence`

- **源码**：`tests/test_rerun_service.py:27`
- **签名**：`def _evidence() -> VerifiedRunEvidence`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `VerifiedRunEvidence` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`VerifiedRunEvidence`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
构造 `WorkspaceManifest` 结构化领域对象，并把结果记为 本次复现工作区；构造 `SimpleNamespace` 结构化领域对象，并把结果记为 复现任务记录；构造 `ArtifactView` 结构化领域对象，并把结果记为 Artifact；构造并返回 `VerifiedRunEvidence` 结构化领域对象。
```

#### `_service`

- **源码**：`tests/test_rerun_service.py:103`
- **签名**：`def _service(tmp_path)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
调用 `_evidence` 完成该函数的一项辅助处理，并把结果记为 可追溯证据记录；构造 `Mock` 结构化领域对象，并把结果记为 证据读取器；读取可追溯证据记录，并保存为 值；构造 `Mock` 结构化领域对象，并把结果记为 复现任务记录集合。
计算组合多个值形成元组，并保存为 值；构造 `SqliteRerunRepository` 结构化领域对象，并把结果记为 持久化仓库；构造 `RerunService` 结构化领域对象，并把结果记为 领域服务对象；返回当前构造的顺序或去重集合。
```

#### `test_create_and_submit_builds_derived_job_request`

- **源码**：`tests/test_rerun_service.py:139`
- **签名**：`def test_create_and_submit_builds_derived_job_request(tmp_path) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_service` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；调用 `create_proposal` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果；断言已创建记录是真；不满足就终止当前测试或流程；断言当前状态等于'pending'；不满足就终止当前测试或流程。
调用 `submit_proposal` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；断言已创建是真；不满足就终止当前测试或流程；断言复现任务 ID等于'job-child'；不满足就终止当前测试或流程；断言当前状态等于'submitted'；不满足就终止当前测试或流程。
断言当前处理结果的数量等于2；不满足就终止当前测试或流程；读取函数关键字参数映射，并保存为 函数关键字参数映射；读取函数关键字参数映射中的对应字段，并保存为 业务请求；断言论文 PDF 路径为空；不满足就终止当前测试或流程。
断言代码仓库根目录为空；不满足就终止当前测试或流程；断言论文资源为空；不满足就终止当前测试或流程；断言仓库资源为空；不满足就终止当前测试或流程；断言修复或重跑提案的 ID等于修复或重跑提案的 ID；不满足就终止当前测试或流程。
断言当前字段值等于'100'；不满足就终止当前测试或流程；断言函数关键字参数映射中的对应字段等于格式化文本：f'rerun-submit:{proposal.proposal.proposal_id}'；不满足就终止当前测试或流程。
```

#### `test_create_with_wrong_manifest_sha_conflicts`

- **源码**：`tests/test_rerun_service.py:186`
- **签名**：`def test_create_with_wrong_manifest_sha_conflicts(tmp_path) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_service` 完成该函数的一项辅助处理，并把结果记为 多个解包结果。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `create_proposal` 组装当前阶段需要的领域对象，退出时自动清理资源。
```

#### `test_create_idempotent_replay`

- **源码**：`tests/test_rerun_service.py:207`
- **签名**：`def test_create_idempotent_replay(tmp_path) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_service` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；构造 `RerunProposalCreateRequest` 结构化领域对象，并把结果记为 业务请求；调用 `create_proposal` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果；调用 `create_proposal` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果。
断言第一项已创建是真；不满足就终止当前测试或流程；断言第二项已创建是假；不满足就终止当前测试或流程；断言修复或重跑提案的 ID等于修复或重跑提案的 ID；不满足就终止当前测试或流程；断言当前处理结果的数量等于1；不满足就终止当前测试或流程。
```

#### `test_cancel_proposal`

- **源码**：`tests/test_rerun_service.py:237`
- **签名**：`def test_cancel_proposal(tmp_path) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_service` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；调用 `create_proposal` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果；加载这一步需要的外部依赖；调用 `cancel_proposal` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
断言当前状态等于'cancelled'；不满足就终止当前测试或流程。
```

### `tests/test_ui_api.py`

**模块作用**：Phase 30 UI API 测试。

#### `FakeInteractionService.get_job`

- **源码**：`tests/test_ui_api.py:18`
- **签名**：`def get_job(self, job_id: str)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收复现任务 ID，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `未显式标注（存在 return）` 的领域结果。

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
断言复现任务 ID等于'job-1'；不满足就终止当前测试或流程；调用 `make_job` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `FakeInteractionService.events_after`

- **源码**：`tests/test_ui_api.py:22`
- **签名**：`def events_after(self, **kwargs)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收函数关键字参数映射，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

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
断言函数关键字参数映射中的对应字段等于0；不满足就终止当前测试或流程；返回当前构造的顺序或去重集合。
```

#### `_client`

- **源码**：`tests/test_ui_api.py:27`
- **签名**：`def _client() -> TestClient`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `TestClient` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`TestClient`
- **语义**：返回 `TestClient` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造 `FastAPI` 结构化领域对象，并把结果记为 该调用返回的结果；计算使用固定配置或常量值，并保存为 当前处理结果；构造 `FakeInteractionService` 结构化领域对象，并把结果记为 该调用返回的结果；调用 `include_router` 完成该函数的一项辅助处理。
构造并返回 `TestClient` 结构化领域对象。
```

#### `test_ui_config_only_contains_public_profile_fields`

- **源码**：`tests/test_ui_api.py:37`
- **签名**：`def test_ui_config_only_contains_public_profile_fields(monkeypatch: 未显式标注) -> None（隐式）`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收测试环境修改工具，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `monkeypatch` | `未显式标注` | pytest 提供的环境/对象替换工具，用于隔离测试副作用；不是业务输入。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `SimpleNamespace` 结构化领域对象，并把结果记为 MCP Client 配置档案；调用 `setattr` 完成该函数的一项辅助处理；调用 `setattr` 完成该函数的一项辅助处理；从辅助操作“调用 `_client` 完成该函数的一项辅助处理”的结果读取所需的状态或领域记录，并把结果记为 结构化响应。
断言状态等于200；不满足就终止当前测试或流程；读取待处理文本，并保存为 后续步骤使用的结果；断言当前输入内容属于当前处理结果；不满足就终止当前测试或流程；断言当前输入内容不属于当前处理结果；不满足就终止当前测试或流程。
断言当前输入内容不属于当前处理结果；不满足就终止当前测试或流程。
```

#### `test_timeline_endpoint_returns_public_projection`

- **源码**：`tests/test_ui_api.py:68`
- **签名**：`def test_timeline_endpoint_returns_public_projection()`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
从辅助操作“调用 `_client` 完成该函数的一项辅助处理”的结果读取所需的状态或领域记录，并把结果记为 结构化响应；断言状态等于200；不满足就终止当前测试或流程；断言前一步操作返回对象中的对应字段中的对应字段等于'job-1'；不满足就终止当前测试或流程；断言前一步操作返回对象中的对应字段中的对应字段中的对应字段等于'user'；不满足就终止当前测试或流程。
```

#### `test_resource_input_name_does_not_call_path_on_none`

- **源码**：`tests/test_ui_api.py:76`
- **签名**：`def test_resource_input_name_does_not_call_path_on_none()`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `SimpleNamespace` 结构化领域对象，并把结果记为 复现输入资源；断言辅助操作“调用 `_public_input_name` 完成该函数的一项辅助处理”的结果等于'paper_pdf:resource-1'；不满足就终止当前测试或流程。
```

### `tests/test_web_static.py`

**模块作用**：Phase 30 SPA 静态文件托管测试。

#### `test_missing_optional_dist_does_not_break_api`

- **源码**：`tests/test_web_static.py:12`
- **签名**：`def test_missing_optional_dist_does_not_break_api(tmp_path)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：无业务返回值；通过断言或预期异常验证目标行为。

**伪代码**

```text
构造 `FastAPI` 结构化领域对象，并把结果记为 该调用返回的结果。
定义内部辅助函数 `readyz`，供当前函数在后续步骤中调用。
调用 `mount_web_ui` 完成该函数的一项辅助处理；断言前一步操作返回对象的状态等于200；不满足就终止当前测试或流程。
```

#### `test_missing_optional_dist_does_not_break_api.readyz`

- **源码**：`tests/test_web_static.py:16`
- **签名**：`def readyz()`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
返回包含 `status` 字段的结构化映射。
```

#### `test_missing_required_dist_fails_fast`

- **源码**：`tests/test_web_static.py:28`
- **签名**：`def test_missing_required_dist_fails_fast(tmp_path)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `mount_web_ui` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `test_spa_fallback_does_not_hide_missing_assets`

- **源码**：`tests/test_web_static.py:37`
- **签名**：`def test_spa_fallback_does_not_hide_missing_assets(tmp_path)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：无业务返回值；通过断言或预期异常验证目标行为。

**伪代码**

```text
计算组合或计算已有值，并保存为 当前处理结果；创建当前处理结果对应的目录；将处理结果写入当前输入内容指定的文件；构造 `FastAPI` 结构化领域对象，并把结果记为 该调用返回的结果。
定义内部辅助函数 `ping`，供当前函数在后续步骤中调用。
调用 `mount_web_ui` 完成该函数的一项辅助处理；构造 `TestClient` 结构化领域对象，并把结果记为 外部服务客户端；断言当前输入内容属于前一步操作返回对象的待处理文本；不满足就终止当前测试或流程；断言当前输入内容属于前一步操作返回对象的待处理文本；不满足就终止当前测试或流程。
断言前一步操作返回对象的状态等于404；不满足就终止当前测试或流程；断言辅助操作“调用 `json` 完成该函数的一项辅助处理”的结果等于{'ok': 真}；不满足就终止当前测试或流程。
```

#### `test_spa_fallback_does_not_hide_missing_assets.ping`

- **源码**：`tests/test_web_static.py:47`
- **签名**：`def ping()`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
返回包含 `ok` 字段的结构化映射。
```
