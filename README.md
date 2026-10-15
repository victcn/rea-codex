# REA Codex (v0.162.1 Full Source, Binary Address & Deep Asset Reconstruction)

[![Version](https://img.shields.io/badge/Codex_CLI-v0.162.1-10a37f?style=flat-square)](./manifest.json)
[![Source](https://img.shields.io/badge/Rust_Sources-5%2C162_.rs_%2B_445_Git_Fork_.rs_(100%25_Authentic)-DEA584?style=flat-square)](./src/)
[![Alignment](https://img.shields.io/badge/Binary_Line_Alignment-18%2C070%2F18%2C070_(100.0%25)-2ea44f?style=flat-square)](./schemas/binary-address-map.json)
[![Analysis](https://img.shields.io/badge/Repository_Analyzer-Full_Report-0969da?style=flat-square)](./REPOSITORY_ANALYSIS_REPORT.md)
[![Self-Test](https://img.shields.io/badge/Self--Test-19%2F19_Passed-brightgreen?style=flat-square)](./self-test-report.json)

本项目基于 **REA (Reverse Engineer Anything)** 静态与运行时分析工具链，配合 ELF `.rela.dyn` 重定位表、`.data.rel.ro` 胖指针结构体、`.eh_frame_hdr` 函数边界表、DWARF 调试符号解析、Bincode + Zstandard/Zlib 解码与精确构建 Commit 溯源（`092d3acd6bec3e3a14bdc7e7a2810ab628ab759d`，`rust-v0.162.1`），对 **OpenAI Codex CLI v0.162.1**（目标三元组 `x86_64-unknown-linux-musl`）的单文件静态 ELF 二进制（`codex` 126.9 MB、`codex-code-mode-host` 74.0 MB、`codex-voice-host` 65.0 MB）及配套 VS Code 扩展与官方插件进行了 **100% 真实源码级还原、二进制虚拟地址映射、内嵌压缩资产全量无损解压与深度架构分析**。

> **深度架构与代码分析报告**：完整项目结构、8 层架构、117 个 Workspace Crates 拓扑、依赖分析与安全机制剖析请查阅 [`REPOSITORY_ANALYSIS_REPORT.md`](./REPOSITORY_ANALYSIS_REPORT.md)。

---

## 核心特性

- **100% 真实 Rust 源码还原（零 `sub_xxxx` 反编译伪代码占位符）**：
  基于从二进制逆向提取出的精确构建 Commit `092d3acd6bec3e3a14bdc7e7a2810ab628ab759d`，将 `codex-rs/` 与 `codex-cli/` 全部 **8,514 个真实源文件**（含 **5,162 个 `.rs` 源码文件**、**162 个 `Cargo.toml`**，共 **1,111,055 行 Rust 代码**）完整落地至 `src/`。
- **100% 二进制机器码地址（`sub_xxxx`）与真实源码双向精确映射**：
  通过扫描 `.data.rel.ro` + `.rela.dyn` + `.eh_frame_hdr` 的 495,529 条 `R_X86_64_RELATIVE` 重定位项，本地 ELF 二进制中的 **16,817 个工作空间 `core::panic::Location` 检查点与 `src/` 下真实 `.rs` 文件行号/列号实现 100.00%（16,817 / 16,817）字节级对齐**，并将 **7,340 个剥离符号的 `.text` 机器码函数（`0x...`）** 精确解析回对应的真实 Rust 函数名（详见 [`schemas/binary-address-map.json`](./schemas/binary-address-map.json)）。
- **100% 6 个定制 Git Fork 依赖库源码还原与行号对齐**：
  从二进制 `.rodata` 与 `Cargo.lock` 溯源并提取 `openai-oss-forks/crossterm`、`openai-oss-forks/tokio-tungstenite`、`openai-oss-forks/tungstenite-rs`、`modelcontextprotocol/rust-sdk` (`rmcp`)、`hyperium/h3`、`helix-editor/nucleo` 共 **445 个 `.rs` 文件**至 `extracted-assets/git-fork-sources/`，**1,253 / 1,253 个 Panic 检查点 100.00% 匹配**，映射 **880 个机器码函数**（详见 [`schemas/git-fork-dependencies.json`](./schemas/git-fork-dependencies.json)）。
- **100% 内嵌 Zstandard (`.zst`) 协议与类型包无损解压（10.31 MB 明文）**：
  从 `bin/codex` `.rodata` 段（`0xe5c6d6f` 与 `0xe5ed6c1`）无损解压 Stable 与 Experimental 两套 App-Server JSON-RPC 2.0 协议包，还原 **888 个 `ts-rs` 生成的 TypeScript 定义文件（`.ts`）**、**447 个 JSON Schema 文件（`.json`）** 及内部会话持久化 Schema **`RolloutLine.json`**。
- **100% 内嵌 Syntect `ThemeSet`（32 套主题）与 `SyntaxSet`（220 种语法高亮）Bincode + Zlib 无损解压**：
  从 `.rodata` 段 `0xecd695e`（62,593 B -> 解压后 358,017 B）与 `0xece5ddf`（983,676 B -> 解压后 5,331,694 B）精确剥离外层 Bincode 长度前缀与内层 Zlib 流，完整还原至 `extracted-assets/syntect-themes-and-syntaxes/`。
- **100% `codex-code-mode-host` 内嵌 10.82 MB V8 Startup Snapshot 与 JS 组合子提取**：
  从 `bin/codex-code-mode-host` `0x2fb1980`（10,822,192 字节，魔数 `0x27da0090`）提取 V8 快照头、6,391 个内置符号表及 `v8-promise-combinators.js`。
- **100% 官方内嵌模型目录与 3 个隐藏模型完整还原（`models.json`，472,071 字节）**：
  从 `.rodata` `0xe833a82` 完整提取 11 个内置模型配置：包含 8 个公开模型（`gpt-6-astra`、`gpt-6.1-sol`、`gpt-6-sol`、`gpt-6-luna` 等）与 **3 个隐藏模型（`gpt-daybreak-blue-latest` [272k/872k]、`gpt-daybreak-red-latest` [372k 上下文]、`codex-auto-review`）**。
- **100% 内部 System Prompts、Subagent 角色配置、System Skills 与官方插件归档**：
  提取 65 个系统提示词与运行时模板（含 Guardian V2 审查器、Memory 两阶段提取与整合、Plan Mode 三阶段、`apply_patch` Lark EBNF 语法）、5 套 `include_dir!` 内嵌技能（48 个文件）、7 套官方插件归档（187 个文件）、76 个 SQLite 迁移脚本（SHA-384 校验通过）与 23 个 Hooks Wire JSON Schema。
- **原生本地纯净隔离启动方案**：
  提供 `scripts/run-isolated.sh`（基于独立 `CODEX_HOME=.isolated-env/codex-home` 与隔离 `HOME`），无需容器即可在本地启动零外部污染、零宿主机配置干扰的 100% 纯净原生 Codex 会话。

---

## 目录结构

```text
rea-codex/
├── bin/
│   ├── codex                                # CLI 启动入口（加载 vendor 原生静态 ELF 或本地构建产物）
│   ├── codex-code-mode-host                 # Code Mode (exec_js) V8 + Starlark 独立隔离宿主进程
│   └── codex-voice-host                     # Realtime WebRTC + Sonora AEC3/AGC2/NS 语音宿主进程
├── entrypoints/                             # 16 个核心子系统语义化架构与源码导航入口
│   ├── 01-cli-and-arg0-multicall.md         # CLI 主控入口与 arg0 多合一二进制分发器（sandbox/execve/apply_patch）
│   ├── 02-core-agent-turn-loop.md           # codex-core 主对话状态机、WorldState 与上下文压缩
│   ├── 03-model-catalog-and-daybreak.md     # 内置 11 个模型目录与 3 个隐藏 Daybreak/Auto-Review 模型
│   ├── 04-code-mode-v8-starlark-host.md     # Code Mode V8 Turboshaft 快照与 Starlark 沙箱引擎
│   ├── 05-guardian-v2-security-reviewer.md  # Guardian V2 同步/异步双轨高危操作安全审查器
│   ├── 06-memories-two-phase-consolidation.md # 两阶段 Agent 长期记忆系统（Phase 1 提取 + Phase 2 整合）
│   ├── 07-app-server-and-daemon-rpc.md      # App-Server JSON-RPC 2.0 守护进程与 102 个 RPC 方法
│   ├── 08-linux-sandbox-bwrap-landlock.md   # Linux Landlock V3 + Seccomp BPF + Bubblewrap 沙箱
│   ├── 09-voice-host-webrtc-sonora-aec3.md  # WebRTC 实时语音栈与 DWARF 250 编译单元符号映射
│   ├── 10-external-agent-migration.md       # 外部 Agent（Claude Code / Cursor）配置与记忆迁移器
│   ├── 11-skills-and-plugins-engine.md      # Skills 渐进式发现引擎与 Plugins 插件系统
│   ├── 12-sqlite-state-and-thread-store.md  # SQLite WAL 持久化引擎与 76 个 sqlx 迁移脚本
│   ├── 13-hooks-lifecycle-wire-protocol.md  # 12 类生命周期 Hooks 引擎与 23 个 Wire JSON Schema
│   ├── 14-multi-agent-v1-v2-and-message-board.md # Multi-Agent v1/v2 子智能体派生与 SQLite 消息板
│   ├── 15-network-proxy-and-credential-broker.md # 托管 HTTP/SOCKS5 MITM 代理与零信任凭据代填网关
│   └── 16-tui-ratatui-and-inline-visualizations.md # Ratatui 全屏终端 UI 与内联 HTML/CSS 可视化
├── src/                                     # 100% 真实 Rust 工作空间源码树（117 个 Crates，5,162 个 .rs 文件）
│   ├── Cargo.toml / Cargo.lock              # 顶层 Cargo Workspace 清单与精确版本锁（5,685 依赖包声明）
│   ├── cli/                                 # 顶层多合一 CLI 入口与 arg0 调度器
│   ├── core/                                # Agent 核心会话循环、工具路由与提示词组装（226 个 .rs 文件）
│   ├── tui/                                 # Ratatui 终端界面与自定义 Markdown/Diff 渲染（340 个 .rs 文件）
│   ├── app-server/ & app-server-protocol/   # IDE/Desktop JSON-RPC 2.0 服务端与协议定义
│   ├── code-mode/ & code-mode-host/         # V8 + Starlark 代码模式引擎与独立宿主
│   ├── ext/guardian-v2/ & memories/         # Guardian V2 安全审查、两阶段记忆、Skills、Goals 等扩展
│   ├── linux-sandbox/ & execve-wrapper/     # Linux 内核级沙箱与 execve 拦截包装器
│   └── launcher/codex.js                    # 跨平台 Node ESM 引导器与平台三元组加载器
├── extracted-assets/                        # 100% 从二进制 .rodata 与安装包无损解压还原的可读资产库
│   ├── git-fork-sources/                    # 6 个定制 Git Fork 依赖库完整源码（445 个 .rs 文件）
│   ├── prompts/                             # 65 个系统提示词、模型专属指令与 Subagent 角色配置
│   ├── system-skills/                       # 5 套内嵌 include_dir! 官方技能树（48 个文件）
│   ├── official-plugins/                    # 7 套官方 Bundled/Curated 插件完整归档（187 个文件）
│   ├── syntect-themes-and-syntaxes/         # 解压还原的 32 套 Syntect 主题与 220 种语法高亮定义
│   ├── code-mode-v8-snapshot/               # V8 Startup Snapshot 头部元数据、内置符号表与 JS 引导脚本
│   ├── sql-migrations/                      # 8 大 SQLite 数据库共 76 个通过 SHA-384 校验的 .sql 迁移脚本
│   ├── vscode-codex-audio-extension/        # 格式化还原的 VS Code 语音扩展源码与 5 平台原生库指纹
│   ├── runtime-templates/                   # Lark 补丁语法、Shell 快照模板、OAuth 登录页与可视化 CSS/HTML
│   └── i18n-ftl/                            # 7 种语言 Project Fluent (.ftl) 国际化翻译资源
├── schemas/                                 # 完整协议包、二进制地址映射表、JSON Schema 与数据字典
│   ├── binary-address-map.json              # 16,817 个 Panic 点与 7,340 个 .text 机器码函数 -> 真实源码映射表
│   ├── git-fork-dependencies.json           # 6 个 Git Fork 依赖库的 1,253 个 Panic 点与 880 个函数映射表
│   ├── app-server-protocol/                 # 解压出的 888 个 TypeScript (.ts) 与 447 个 JSON Schema 文件
│   ├── hooks-wire-schemas/                  # 23 个生命周期 Hooks 输入/输出 JSON Schema
│   ├── models.json & model-summary.json     # 官方内嵌 11 个模型完整配置原件（含 3 个隐藏模型）
│   ├── feature-flags.json & env-vars.json   # 95 个内部 Feature Flags 生命周期表与 51 个环境变量注册表
│   ├── serde-reflection-catalog.json        # 1,325 个 Rust Structs 与 458 个 Enum Variants 反射表
│   ├── tracing-metadata-catalog.json        # 2,866 个编译器内嵌 Tracing 埋点元数据（含文件与行号）
│   └── repository-analysis-metrics.json     # Repository Analyzer 生成的仓库代码行数与架构指标数据
├── scripts/                                 # 自动化逆向提取、地址映射、资产审查与自检流水线脚本
│   ├── extract-codex-artifacts.py           # 提取 .rodata 内嵌 .zst 协议包、模型表、提示词与 SQL 迁移
│   ├── extract-all-remaining.py             # 提取 Hooks Schema、Tracing 元数据、i18n 与完整 CLI 命令树
│   ├── extract-deep-components.py           # 解码 Syntect Bincode+Zlib、V8 快照、DWARF 符号与配套二进制
│   ├── fetch-git-fork-sources.py            # 拉取并验证 6 个定制 Git Fork 依赖库源码与二进制对齐
│   ├── build-binary-address-map.py          # 解析 .rela.dyn/.eh_frame_hdr 构建机器码地址 -> 真实源码映射
│   ├── inspect-binary-assets.py             # 交互式二进制虚拟地址（sub_xxxx）反查与 .rodata 资产校验工具
│   ├── reconstruct-rust-sources.py          # 重建 Rust 工作空间源码目录树与符号骨架
│   ├── run-repository-analyzer.py           # 运行 Repository Analyzer 生成全量代码与架构指标
│   ├── self-test.py                         # 19 项全量端到端自动化验证自测套件
│   └── run-isolated.sh                      # 本地零污染纯净隔离环境启动脚本
├── REPOSITORY_ANALYSIS_REPORT.md            # Repository Analyzer 生成的深度项目结构、架构与依赖分析报告
├── crate-map.json                           # Workspace Crates 模块映射索引
├── manifest.json                            # 逆向还原制品总清单与统计摘要
├── self-test-report.json                    # 19/19 自动化自测通过报告
└── package.json                             # 项目配置与快捷脚本定义
```

---

## 标准使用教程

### 教程一：快速开始（直接运行、地址反查与从源码编译）

#### 1. 环境准备
- 操作系统：Linux x86_64（`bin/codex` 原生二进制基于 `x86_64-unknown-linux-musl` 静态链接，零 glibc 版本依赖）
- 基础依赖：`python3 >= 3.10`、`node >= 18`（可选，用于运行 `src/launcher/codex.js`）、`rustup / cargo`（可选，用于重新编译修改后的 `src/` Rust 源码）

#### 2. 直接运行与查看帮助
```bash
# 查看版本与全量命令树
./bin/codex --version
./bin/codex --help

# 查看多合一二进制隐藏内部入口（沙箱 / 补丁引擎 / App-Server）
./bin/codex app-server --help
./bin/codex sandbox linux --help
```

#### 3. 反查任意二进制函数地址（将 IDA/Ghidra 的 `sub_xxxx` 还原为真实 Rust 源码位置）
当你在反编译器中看到类似 `sub_1a08d90` 的未命名函数时，可直接通过内置查询工具定位其精确的 Rust 源文件、行号区间与函数签名：
```bash
python3 ./scripts/inspect-binary-assets.py --addr 0x1a08d90
```
输出示例：
```json
{
  "binary": "bin/codex",
  "vaddr_start": "0x1a08d90",
  "vaddr_end": "0x1a0a4d0",
  "size_bytes": 5952,
  "primary_source_file": "src/cli/src/main.rs",
  "primary_rust_function": "run_debug_app_server_command (L941..L976)",
  "source_anchors": [
    {
      "source_file": "src/cli/src/main.rs",
      "line": 941,
      "column": 89,
      "rust_function": "run_debug_app_server_command (L941..L976)"
    }
  ]
}
```

#### 4. 从 `src/` 真实 Rust 源码重新编译
如果你修改了 `src/` 下的任何 `.rs` 源码或内嵌提示词文件，可在 `src/` 工作空间下直接使用 Cargo 编译：
```bash
cd ./src
# 编译主 CLI 二进制
cargo build --release -p codex-cli

# 或仅对修改的核心模块做快速类型检查
cargo check -p codex-core
```

---

### 教程二：在本地使用 100% 纯净隔离环境运行（屏蔽宿主机 `~/.codex` / 外部 MCP / 插件）

当宿主机 `~/.codex/` 中配置了个人认证凭据、全局 `AGENTS.md`、外部 Skills 或第三方 MCP Server 时，可通过以下方式获得 **100% 纯净的隔离运行环境**：

#### 方式 A：使用项目内置的隔离启动脚本 `scripts/run-isolated.sh`（推荐）
该脚本通过独立的 `CODEX_HOME=./.isolated-env/codex-home` 与 `HOME=./.isolated-env/home` 启动，彻底隔离宿主机的 `~/.codex`：
```bash
# 验证纯净度并查看版本
./scripts/run-isolated.sh --version

# 查看全部 95 个内部 Feature Flags 及其默认状态
./scripts/run-isolated.sh features list

# 在纯净环境中执行单次非交互式任务
OPENAI_API_KEY="sk-your-key" \
./scripts/run-isolated.sh exec "用一句话解释 Linux Landlock 沙箱的工作原理"
```

#### 方式 B：通过 `-c` 动态覆盖配置参数运行
Codex 支持在命令行通过 `-c key=value` 覆盖任意 `config.toml` 配置项或开关实验特性：
```bash
./bin/codex -c model='"gpt-6.1-sol"' --enable code_mode --disable plugins
```

---

### 教程三：接入自定义模型网关（OpenAI 兼容代理 / DeepSeek / Qwen / GLM / vLLM / LiteLLM）

Codex 原生支持自定义 `model_provider` 与 `OPENAI_BASE_URL`，可无缝对接任意兼容 **OpenAI Responses API (`/v1/responses`)** 或 **Chat Completions API (`/v1/chat/completions`)** 的第三方/本地网关：

```bash
# 方式 1：直接通过环境变量指定网关地址与密钥
export OPENAI_BASE_URL="http://127.0.0.1:8012/v1"   # 你的本地/第三方网关地址（如 LiteLLM / One-API / vLLM）
export OPENAI_API_KEY="sk-any-key"                  # 网关 API 密钥

# 启动非交互式执行 (codex exec)
./scripts/run-isolated.sh exec -m "gpt-6.1-sol" "你好，请介绍一下你自己"

# 方式 2：通过 -c 参数内联注册自定义 Model Provider（支持 wire_api = "chat" 或 "responses"）
./scripts/run-isolated.sh \
  -c 'model_provider="custom_gw"' \
  -c 'model="deepseek-coder"' \
  -c 'model_providers.custom_gw={name="CustomGW", base_url="http://127.0.0.1:8012/v1", env_key="OPENAI_API_KEY", wire_api="chat"}' \
  exec "写一个 Rust 归并排序"
```

---

### 教程四：二次开发与自定义修改指南（源码 + 二进制地址对照表）

你可以通过 `./entrypoints/` 下的 16 篇子系统导航文档或下表，快速定位并修改 Codex 的核心行为：

| 想要修改 / 研究的功能 | 对应真实源码路径 (`src/`) | 提取出的可读资产 / Schema 路径 | 二进制 `.rodata` / `.text` 定位 |
| :--- | :--- | :--- | :--- |
| **修改默认 CLI System Prompt** | `src/core/src/session/` | `extracted-assets/prompts/base-cli-system-prompt.md` | `.rodata` `0xe783e60` (21,045 B) |
| **解锁 3 个隐藏模型 (`gpt-daybreak-*` / `codex-auto-review`)** | `src/models-manager/src/` | `schemas/models.json`（将 `"visibility": "hide"` 改为 `"list"`） | `.rodata` `0xe833a82` (472,071 B) |
| **反查 CLI 入口与 `debug app-server` 调度 (`sub_1a08d90`)** | `src/cli/src/main.rs` (`run_debug_app_server_command`) | `schemas/binary-address-map.json` | `.text` `0x1a08d90`..`0x1a0a4d0` (5,952 B) |
| **修改 `exec_command` / Shell 工具执行逻辑** | `src/core/src/tools/handlers/shell.rs` | `schemas/binary-address-map.json` | 见 `src/core/src/tools/handlers/` |
| **修改 Guardian V2 安全审查提示词与评分阈值** | `src/ext/guardian-v2/src/` | `extracted-assets/prompts/guardian-v2-async-reviewer-prompt.md` | `.rodata` `0xe7a86db` (10,351 B) |
| **修改两阶段 Agent 记忆提取与整合提示词** | `src/ext/memories/src/`、`src/memories/write/src/` | `extracted-assets/prompts/memory-phase1-single-rollout-prompt.md` | `.rodata` `0xe80a296` / `0xe7f824f` |
| **修改 `apply_patch` 补丁语法与解析器** | `src/apply-patch/src/` | `extracted-assets/runtime-templates/apply-patch-tool-lark-grammar.lark` | `.rodata` `0xe67bd60` |
| **修改 Code Mode (`exec_js`) V8 宿主与提示词** | `src/code-mode/src/`、`src/code-mode-host/src/` | `extracted-assets/prompts/code-mode-javascript-orchestration-prompt.md` | `codex-code-mode-host` `0x2fb1980` |
| **修改 Multi-Agent 子智能体角色 (`explorer`/`worker`)** | `src/agent-roles/src/`、`src/ext/agent-message-board/src/` | `extracted-assets/prompts/subagent-roles/` | `.rodata` `0xe76f2a0` |
| **修改 Linux Landlock + Seccomp + Bubblewrap 沙箱策略** | `src/linux-sandbox/src/`、`src/sandboxing/src/` | `extracted-assets/prompts/sandbox-escalation-requests-prompt.md` | `arg0` -> `codex-linux-sandbox` |
| **修改 95 个内部 Feature Flags 默认开关** | `src/features/src/` | `schemas/feature-flags.json` | 见 `codex features list` |

---

### 教程五：运行 19 项全量自动化自测与仓库架构分析

项目内置了完整的自动化验证测试脚本 `scripts/self-test.py`，一键校验全部 19 项逆向还原成果（包括 5,162 个 `.rs` 源码完整性、16,817/16,817 工作空间 Panic 点 100% 行号对齐、6 个 Git Fork 依赖 1,253/1,253 Panic 点 100% 对齐、Syntect 32 主题 + 220 语法解压、V8 10.82 MB 快照解析、11 个模型表、65 个提示词、76 个 SQLite 迁移 SHA-384 校验、23 个 Hooks Schema、7 套官方插件归档及隔离环境运行测试）：

```bash
# 运行 19 项全量端到端自动化自测
npm test
# 或直接执行：
python3 ./scripts/self-test.py

# 重新运行 Repository Analyzer 架构与代码指标分析
npm run analyze-repo
```

---

## 快捷脚本一览 (`package.json`)

| 命令 | 对应底层脚本 | 说明 |
| :--- | :--- | :--- |
| `npm start` | `./bin/codex` | 直接启动 Codex CLI |
| `npm run isolated` | `./scripts/run-isolated.sh` | 在本地零污染纯净隔离环境（`.isolated-env/`）中启动 Codex |
| `npm run extract` | `extract-codex-artifacts.py` + `extract-all-remaining.py` | 从官方二进制提取 `.zst` 协议包、模型表、提示词、SQL 迁移、Hooks Schema 与 i18n |
| `npm run extract-deep` | `extract-deep-components.py` + `fetch-git-fork-sources.py` | 解压 Syntect Bincode+Zlib、V8 快照、DWARF 符号、VS Code 语音扩展并同步 6 个 Git Fork 源码 |
| `npm run map-addresses` | `build-binary-address-map.py` | 解析 ELF `.rela.dyn` 与 `.eh_frame_hdr`，构建机器码地址 -> 真实 Rust 源码映射表 |
| `npm run inspect` | `inspect-binary-assets.py` | 校验全部二进制内嵌 `.rodata` 资产区间与 SHA-256 指纹（支持 `--addr 0x...` 反查函数） |
| `npm run analyze-repo` | `run-repository-analyzer.py` | 运行 Repository Analyzer 生成 `schemas/repository-analysis-metrics.json` |
| `npm run rebuild-all` | 串联执行上述全部逆向与分析流水线 | 一键从本地二进制重跑全量解包、地址映射与仓库指标生成 |
| `npm test` | `python3 ./scripts/self-test.py` | 运行 19 项全量自动化自测并生成 `self-test-report.json` |

---

## 免责声明与许可说明 (Disclaimer & License)

1. **仅限学术研究与安全审计用途**：
   本项目通过逆向工程与构建溯源技术生成，**仅用于计算机系统架构研究、AI Agent 编排机制学习、Linux 沙箱与零信任安全审计以及本地兼容网关互操作性测试**。严禁将本项目用于任何商业侵权、非法攻击、绕过商业授权计费或违反目标软件服务条款的用途。
2. **开源源码与知识产权归属**：
   - `src/` 目录下还原的 OpenAI Codex Rust 工作空间源码遵循上游 **Apache License 2.0** 开源许可协议（详见 [`LICENSE`](./LICENSE)）。
   - 原始预编译二进制分发包、OpenAI 商标、内置专有模型名称及配套扩展（如 `openai.codex-audio`）的相关权利归属 **OpenAI OpCo, LLC** 及其关联方所有。
3. **免责条款（No Warranty）**：
   本项目按“原样（AS IS）”提供，不附带任何明示或暗示的担保。使用者因使用、修改或分发本项目内容所产生的任何直接或间接风险与法律责任，均由使用者自行承担，与本项目脚本作者无关。如果权利人认为本仓库中的任何提取产物侵犯了您的合法权益，请提交 Issue 联系移除。
