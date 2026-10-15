# OpenAI Codex CLI v0.162.1 (`rea-codex-demo`) - Repository Analysis Report

**Generated:** 2026-10-15 (Asia/Shanghai)
**Analyzed by:** Repository Analyzer (`jackspace/claudeskillz@repository-analyzer`) + REA (`reverse-engineer-anything`)
**Target Artifact:** `@openai/codex` v0.162.1 (`x86_64-unknown-linux-musl`, Commit `092d3acd6bec3e3a14bdc7e7a2810ab628ab759d`)
**Workspace Path:** `/code/custom-dev/rea-codex-demo`

---

## 📊 1. Executive Overview (全局概览)

| 指标维度 | 精确统计值 | 说明 |
| :--- | :--- | :--- |
| **主导编程语言** | **Rust (Edition 2024, `rustc 1.94.0`) + TypeScript / Node.js** | 核心引擎为静态 PIE Musl Rust，外层 CLI 包装与协议 Schema 为 TypeScript |
| **架构模式** | **Cargo 多 Crate 工作空间 + 多进程 Actor (Submission/Event) + JSON-RPC v2 App-Server** | 161 个内部 Crate 组成的有向无环图 (DAG)，配合独立沙箱进程与 V8/Voice 宿主进程 |
| **工程文件总数** | **13,595 个文件**（总计 **162.46 MB**） | 含 `src/` (8,515)、`extracted-assets/` (2,604)、`schemas/` (2,443) |
| **代码总行数 (LOC)** | **3,120,389 行** | 其中 **Rust 代码 2,169,082 行**（5,607 个 `.rs` 文件），JSON Schema/协议 777,268 行 |
| **Rust 函数与测试规模** | **58,741 个 `fn` 定义** / **20,889 个测试函数 (`#[test]` / `#[tokio::test]`)** | 单元测试占比高达 **35.56%**，零 `sub_xxxx` 伪代码占位符 |
| **二进制 <-> 源码对齐率** | **18,070 / 18,070 (100.00%)** | 主仓 16,817 个 + 6 个 Git Fork 1,253 个 `core::panic::Location` 100% 精确命中真实源码行号；共映射 **8,220 个 `.text` 机器码函数**（7,340 主仓 + 880 Fork） |
| **自动化验证状态** | **19 / 19 项全绿通过 (`self-test.py`)** | 耗时 `0.44s`，覆盖二进制执行、协议解压、模型目录、SQLite SHA-384、V8 快照、Syntect、DWARF 等 |

---

## 📁 2. Repository Structure & Codebase Breakdown (项目结构与代码分布)

### 2.1 顶层目录结构

```text
/code/custom-dev/rea-codex-demo/
├── bin/
│   └── codex                                      # 本地 Node.js 启动器入口 (指向 extracted-assets/launcher/codex.js)
├── entrypoints/                                   # 16 个核心二进制入口符号映射 (codex, app-server, exec-server 等)
├── src/                                           # 100% 真实源码树 (8,515 个文件, 2,226,986 行, 79.14 MB)
│   ├── Cargo.toml / Cargo.lock                    # 根工作空间配置 (161 个子 Crate, 1,473 个锁定包)
│   ├── cli/                                       # 多合一 CLI 顶层路由分发器 (codex-cli, 41,217 LOC)
│   ├── core/                                      # Agent 核心会话循环、工具调度、Guardian、Memory (448,069 LOC)
│   ├── tui/                                       # Ratatui 终端交互界面 (445,701 LOC)
│   ├── app-server/                                # JSON-RPC v2 服务端与生命周期处理器 (191,668 LOC)
│   ├── app-server-protocol/                       # Stable/Experimental Wire 协议定义与 ts-rs 导出 (36,079 LOC)
│   ├── exec-server/                               # 统一 PTY/Pipe 命令执行与审批服务 (64,975 LOC)
│   ├── code-mode/ & code-mode-host/               # RustyV8 隔离执行宿主与内嵌 10.82 MB V8 快照
│   ├── linux-sandbox/ & windows-sandbox-rs/       # Bubblewrap / Landlock / Seccomp 与 Windows 受限令牌沙箱
│   ├── rmcp-client/ & codex-mcp/                  # MCP 客户端连接池、OAuth 认证与内置 MCP 服务
│   ├── state/ & thread-store/ & rollout/          # SQLite 状态持久化、迁移管理与 JSONL 会话回放
│   ├── voice-host/ & realtime-webrtc/             # WebRTC + GStreamer + Opus 实时语音宿主
│   ├── ext/                                       # 插件与扩展体系 (skills, automations, memories-ext, findings)
│   └── codex-cli/                                 # 顶层 npm 跨平台包装器、Dockerfile 与 CI 脚本
├── extracted-assets/                              # 二进制无损提取资产 (2,604 个文件, 48.27 MB)
│   ├── prompts/                                   # 65 个内嵌系统提示词、Guardian 提示词、Subagent TOML、Lark 语法
│   ├── system-skills/                             # 5 套 include_dir! 内嵌技能 (imagegen, openai-docs 等 48 文件)
│   ├── official-plugins/                          # 7 套官方 Bundled & Curated 插件完整归档
│   ├── sql-migrations/                            # 7 套 SQLite 数据库的 76 个迁移脚本 (100% SHA-384 校验)
│   ├── syntect-themes-and-syntaxes/               # 32 套配色主题 (358 KB) + 220 种语法定义 (5.33 MB)
│   ├── code-mode-v8-snapshot/                     # V8 Startup Snapshot 头部、6,391 符号表与 Promise 组合子
│   ├── git-fork-sources/                          # 6 个定制 Git Fork 依赖的 445 个真实 .rs 源码文件
│   ├── vscode-codex-audio-extension/              # VS Code 语音扩展格式化 JS 与 5 平台 libpv_recorder 原生库
│   ├── i18n-ftl/                                  # 多语言 Project Fluent (.ftl) 语言包
│   └── voice-runtime/                             # GStreamer / WebRTC 原生运行时符号与配置
├── schemas/                                       # 逆向还原的 Schema 与静态分析映射表 (2,443 个文件, 26.93 MB)
│   ├── app-server-protocol/                       # 解压后的 888 个 .ts 与 447 个 JSON Schema + RolloutLine.json
│   ├── binary-address-map.json                    # 7,340 个主仓二进制函数虚拟地址 <-> 真实 Rust 源码行号映射
│   ├── git-fork-dependencies.json                 # 6 个 Git Fork 依赖的 880 个二进制函数与 1,253 个 Panic 点映射
│   ├── models.json & model-summary.json           # 11 个内置模型配置 (含 3 个隐藏 Daybreak/AutoReview 模型)
│   ├── serde-reflection-catalog.json              # 1,325 个 Serde Struct + 458 个 Variant 字段反射表
│   ├── tracing-metadata-catalog.json              # 3,971 条编译期 tracing::Metadata 埋点记录
│   ├── hooks-wire-schemas/                        # 23 个生命周期 Hooks JSON Schema
│   ├── v8-startup-snapshot-analysis.json          # V8 启动快照元数据报告
│   ├── syntect-catalog.json                       # Syntect 32 主题与 220 语法完整索引
│   ├── companion-binaries-analysis.json           # zsh / bwrap / rg 静态 ELF 分析报告
│   ├── voice-host-dwarf-and-libs.json             # 250 个 DWARF 编译单元与 26 个动态库依赖图
│   └── repository-analysis-metrics.json           # Repository Analyzer 导出的全量代码与依赖度量数据
├── scripts/                                       # 自动化逆向提取、地址对齐、资产校验与自测脚本 (10 个脚本)
├── rea-evidence-bundle.json                       # REA 官方导出的形式化证据包 (16 条 Evidence 记录, 8.07 MB)
└── self-test-report.json                          # 19/19 项自动化自测报告
```

### 2.2 按目录与文件类型统计表

#### 按顶层目录分布

| 顶层目录 | 文件数量 | 代码/文本行数 (LOC) | 磁盘占用 (MB) | 核心内容 |
| :--- | ---: | ---: | ---: | :--- |
| **`src/`** | 8,515 | 2,226,986 | 79.14 MB | 100% 真实 Rust 工作空间 (`5,162` `.rs`) 与 CLI 包装源码 |
| **`extracted-assets/`** | 2,604 | 290,916 | 48.27 MB | 从二进制 `.rodata`/`.data.rel.ro` 提取的提示词、技能、SQL、主题、语法、Git Fork 源码、插件 |
| **`schemas/`** | 2,443 | 590,644 | 26.93 MB | 解压后的 TypeScript/JSON 协议包、二进制地址映射表、模型目录、Serde/Tracing/DWARF 分析表 |
| **`<root>`** | 6 | 8,071 | 7.96 MB | `rea-evidence-bundle.json`、`crate-map.json`、`manifest.json`、`README.md` |
| **`scripts/`** | 10 | 3,629 | 0.14 MB | 二进制逆向提取、地址映射构建、深度组件解析、Repository Analyzer 与 19 项自测脚本 |
| **`entrypoints/`** | 16 | 143 | 0.01 MB | 二进制子命令入口跳板与虚拟地址映射说明 |

#### 按文件扩展名分布 (Top 12)

| 扩展名 | 文件数量 | 代码/文本行数 | 大小 (MB) | 用途说明 |
| :--- | ---: | ---: | ---: | :--- |
| **`.rs`** | **5,607** | **2,169,082** | 74.83 MB | Rust 核心源码（`src/` 下 5,162 个 + `git-fork-sources/` 下 445 个） |
| **`.json`** | **1,245** | **777,268** | 39.41 MB | App-Server JSON Schema (764)、Hooks Schema (23)、模型目录、逆向映射表与 REA 证据包 |
| **`.ts`** | **2,403** | **28,081** | 1.37 MB | `ts-rs` 生成的 App-Server Stable (743) / Experimental (888) 协议绑定与 SDK |
| **`.md`** | **388** | **38,399** | 2.16 MB | 内嵌 System Prompts、5 套内置 Skills、7 套官方插件 `SKILL.md` 与架构文档 |
| **`.js`** | **28** | **17,368** | 0.81 MB | `codex.js` 跨平台启动器、V8 Promise 组合子、VS Code 语音扩展格式化代码 |
| **`.py`** | **56** | **17,050** | 0.58 MB | 逆向提取工具链 (`scripts/*.py`) 及内置 Skills/插件辅助脚本 |
| **`.txt`** | **101** | **13,666** | 0.46 MB | 提示词模板、V8 快照符号表、测试黄金快照 |
| **`.toml`** | **265** | **10,430** | 0.29 MB | 162 个 `Cargo.toml` 清单、Subagent 角色配置 (`awaiter.toml` 等)、插件配置 |
| **`.yaml`** | **63** | **9,725** | 0.35 MB | OpenAPI / 工作流与插件元数据配置 |
| **`.tsx`** | **78** | **9,508** | 0.27 MB | 交互组件与插件前端视图模板 |
| **`.sql`** | **76** | **2,840** | 0.12 MB | 7 套 SQLite 数据库的 76 个版本迁移脚本 |
| **`.bincode`** | **252** | *(二进制)* | 5.69 MB | 解压还原的 32 套 Syntect 配色主题 + 220 种语法高亮 Bincode 结构 |

---

## 🛠 3. Technology Stack & Runtime Matrix (技术栈全景)

| 层级 | 核心技术 / 组件 | 版本 / 规格 | 在 Codex 中的职责 |
| :--- | :--- | :--- | :--- |
| **编译与运行时层** | **Rust (`rustc`) + Musl Libc** | `1.94.0` (`2024 edition`) | 编译为静态链接 PIE ELF (`x86_64-unknown-linux-musl`)，零宿主 glibc 依赖 |
| **异步并发引擎** | **Tokio + Futures + Async-Channel** | `tokio` (92 Crates 使用) | 驱动 Submission (`Op`) / Event (`EventMsg`) 异步通道、流式 SSE/WebSocket 与子进程 I/O |
| **终端 UI 层** | **Ratatui + Crossterm (OpenAI Fork) + Syntect / Two-Face** | `ed1cdab` / `two-face 0.5.1` | 渲染全屏/内联 TUI、Diff 视图、Markdown 流式高亮（内嵌 32 主题 + 220 语法） |
| **应用服务协议层** | **App-Server JSON-RPC v2 + `ts-rs` + `schemars` + Zstd** | Stable & Experimental 双轨 | 为 VS Code / Desktop App 提供双向 RPC，内嵌 `.zst` 压缩协议包供运行时导出 |
| **JS 隔离执行层** | **RustyV8 (`codex-code-mode-host`)** | `v8 146.4.0` (`10.82 MB` 快照) | 在独立子进程中运行 V8 Isolate，提供 `tools.*`、`notify`、`store` 等受控 REPL 环境 |
| **实时语音宿主层** | **WebRTC + GStreamer 1.0 + Opus (`codex-voice-host`)** | 26 个捆绑 `.so` 动态库 | 处理麦克风采集、AEC 回声消除、Opus 编解码与 OpenAI Realtime WebRTC 媒体流 |
| **系统沙箱与安全层** | **Bubblewrap (`bwrap`) + Landlock + Seccomp + Patched `zsh`** | Linux Namespace + BPF + 令牌 | 文件系统只读/白名单挂载、网络隔离，以及通过 `EXECVE_WRAPPER_FD` 拦截子进程执行审批 |
| **持久化存储层** | **SQLx + SQLite (bundled) + JSONL Rollout** | 7 套 SQLite DB (76 迁移脚本) | 存储线程状态 (`state` v1~v59)、记忆 (`memories`)、日志 (`logs`)、目标 (`goals`) 与队列 |
| **网络与模型通信层** | **Reqwest + Hyper + H3 (QUIC) + Tokio-Tungstenite (OpenAI Fork)** | HTTP/1.1, HTTP/2, HTTP/3, WSS | 支持 OpenAI Responses API (SSE + WebSocket v2)、Azure、Bedrock 及本地网络代理过滤 |
| **工具与语法解析层** | **RMCP (`rust-sdk`) + Tree-Sitter (Bash/Ruby) + Lark EBNF** | `3e636ca` | MCP 工具发现与调用、Shell 命令 AST 安全审计、`apply_patch` 补丁语法解析 |

---

## 🏗 4. System Architecture & Data Flow Analysis (系统架构深度分析)

### 4.1 多合一二进制 (`Multicall Binary`) 与多进程协同架构

`@openai/codex` 采用典型的 **主控守护进程 + 专用隔离宿主进程** 架构。主二进制 `bin/codex`（77.26 MB）内置了完整的 CLI 子命令路由器（`src/cli/src/main.rs`），并在运行时按需拉起或通信以下子进程：

```text
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        User / IDE / Codex Desktop Host                              │
└───────────────┬─────────────────────────────────────────────┬───────────────────────┘
                │ Terminal TTY                                │ JSON-RPC v2 (stdio / WS)
                ▼                                             ▼
┌───────────────────────────────────────┐     ┌───────────────────────────────────────┐
│      codex-tui (src/tui, 445k LOC)    │     │  codex-app-server (src/app-server)    │
│  Ratatui + Crossterm + Syntect 渲染   │     │  185 个 v1/v2 RPC 方法 + 事件广播     │
└───────────────┬───────────────────────┘     └───────────────┬───────────────────────┘
                │ In-Process / RPC                            │ ThreadProcessor / TurnProcessor
                └──────────────────────►┌─────────────────────▼───────────────────────┐
                                        │        codex-core (src/core, 448k LOC)      │
                                        │  • Codex (tx_sub: Op ──► rx_event: Event)   │
                                        │  • Turn Loop / Compaction / Rollout         │
                                        │  • Guardian V2 (异步风险审查子会话)          │
                                        │  • Memory Phase 1 & Phase 2 (记忆提炼整合)   │
                                        └──┬────────────┬─────────────┬────────────┬──┘
                                           │            │             │            │
          ┌────────────────────────────────┘            │             │            └────────────────────────────┐
          ▼                                             ▼             ▼                                         ▼
┌──────────────────────────────┐  ┌──────────────────────────┐  ┌──────────────────────────┐  ┌──────────────────────────────┐
│  codex-linux-sandbox / bwrap │  │   codex-code-mode-host   │  │     codex-voice-host     │  │   codex-rmcp-client / MCP    │
│ • Landlock + Seccomp + bwrap │  │ • RustyV8 146.4.0        │  │ • WebRTC + GStreamer 1.0 │  │ • stdio / Streamable HTTP    │
│ • 定制 zsh (EXECVE_WRAPPER)  │  │ • 10.82 MB Startup Snap  │  │ • 26 个私有 .so 动态库    │  │ • OAuth 2.0 令牌自动刷新     │
└──────────────────────────────┘  └──────────────────────────┘  └──────────────────────────┘  └──────────────────────────────┘
```

### 4.2 核心架构模式解析

1. **Submission / Event 异步双通道 Actor 模式 (`codex-core` & `codex-protocol`)**：
   - `Codex::spawn` 启动后台会话主循环后，仅向外暴露两个异步通道：`tx_sub: Sender<Submission>`（接收用户/上层发出的 `Op`，如 `Op::UserTurn`、`Op::Interrupt`、`Op::ExecApproval`、`Op::Review`）与 `rx_event: Receiver<Event>`（向外流式推送 `EventMsg`，如 `AgentMessageDelta`、`ExecCommandBegin`、`PatchApplyBegin`、`TurnComplete`）。
   - 这种设计使 `codex-core` 完全解耦了前端展现形态：无论是终端 `codex-tui`、无头 `codex-exec`，还是服务于桌面端的 `codex-app-server`，全部通过同一套 `Op` / `EventMsg` 协议驱动。
2. **双层安全纵深防御：OS 内核沙箱 + Guardian V2 语义风险审查**：
   - **OS 级硬隔离 (`src/linux-sandbox` & `src/windows-sandbox-rs`)**：在 Linux 下结合 `bwrap` (Bubblewrap) 命名空间隔离、Landlock 文件系统访问控制与 Seccomp 系统调用过滤；同时配合定制补丁版 `zsh` 的 `EXECVE_WRAPPER_FD` 机制，在子进程每次调用 `execve` 前通过 Unix Domain Socket 回调宿主进行細粒度策略判定。
   - **语义级 Guardian V2 审查 (`src/core/src/guardian/`)**：针对需要提权或高风险的工具调用，拉起一个只读的独立 Guardian 审查子会话（使用提取出的 `guardian_policy_prompt.md` 与严格 JSON Schema `guardian-output.schema.json`），输出 `risk_score (0-100)`、`risk_level` 与 `evidence` 数组。
3. **两阶段自主记忆架构 (`src/core/src/memories/`)**：
   - **Phase 1 (提取阶段)**：在后台线程结束时，根据 `stage_one_system.md` 从会话历史中提炼简洁的 `raw_memory` 与 `rollout_summary`。
   - **Phase 2 (整合阶段)**：根据 `consolidation.md` 提示词在本地记忆目录中自动维护 `MEMORY.md`、`memory_summary.md` 与 `skills/`，并通过 SQLite `memories` 表（`extracted-assets/sql-migrations/memories/`）持久化。

---

## 🔍 5. Code Analysis & Binary-to-Source Alignment (代码规模与逆向对齐分析)

### 5.1 规模最大的 Top 20 核心 Crate

| 排名 | Crate 名称 | 工程路径 | `.rs` 文件数 | Rust 代码行数 (LOC) | 内部依赖数 | 外部依赖数 | 核心职责 |
| :---: | :--- | :--- | ---: | ---: | ---: | ---: | :--- |
| 1 | **`codex-core`** | `/code/custom-dev/rea-codex-demo/src/core` | 846 | **448,069** | 80 | 56 | 会话循环、工具编排、模型调用、Guardian、Memory、沙箱调度 |
| 2 | **`codex-tui`** | `/code/custom-dev/rea-codex-demo/src/tui` | 1,101 | **445,701** | 55 | 65 | 终端全屏/内联交互界面、Chat Composer、Diff 渲染、Resume Picker |
| 3 | **`codex-app-server`** | `/code/custom-dev/rea-codex-demo/src/app-server` | 348 | **191,668** | 68 | 40 | JSON-RPC v2 服务端（Thread/Turn/Account/Plugin/Command 处理器） |
| 4 | **`codex-exec-server`** | `/code/custom-dev/rea-codex-demo/src/exec-server` | 181 | **64,975** | 28 | 35 | 统一 PTY / 管道命令执行、超时控制与流式输出缓冲 |
| 5 | **`codex-core-plugins`** | `/code/custom-dev/rea-codex-demo/src/core-plugins` | 93 | **48,632** | 25 | 26 | 插件生命周期管理、Marketplace 安装、Executor Hooks |
| 6 | **`codex-cli`** | `/code/custom-dev/rea-codex-demo/src/cli` | 103 | **41,217** | 55 | 41 | 顶层 CLI 参数解析与 21 个子命令分发入口 |
| 7 | **`codex-rmcp-client`** | `/code/custom-dev/rea-codex-demo/src/rmcp-client` | 108 | **38,966** | 13 | 32 | MCP 客户端协议栈、stdio/HTTP 传输与工具 Schema 转换 |
| 8 | **`codex-app-server-protocol`** | `/code/custom-dev/rea-codex-demo/src/app-server-protocol` | 68 | **36,079** | 12 | 16 | App-Server v1/v2 请求/响应/通知类型定义与 Zstd 协议包导出 |
| 9 | **`codex-thread-store`** | `/code/custom-dev/rea-codex-demo/src/thread-store` | 71 | **35,508** | 11 | 14 | 线程元数据、消息历史与附件存储管理 |
| 10 | **`codex-protocol`** | `/code/custom-dev/rea-codex-demo/src/protocol` | 77 | **32,022** | 10 | 29 | 全工作空间共享的核心协议原语 (`Op`, `EventMsg`, `ThreadId` 等) |
| 11 | **`codex-config`** | `/code/custom-dev/rea-codex-demo/src/config` | 96 | **30,932** | 12 | 32 | `config.toml` 分层配置合并、MDM 受管配置与指纹校验 |
| 12 | **`codex-windows-sandbox`** | `/code/custom-dev/rea-codex-demo/src/windows-sandbox-rs` | 119 | **30,159** | 8 | 18 | Windows AppContainer / Restricted Token / ACL 安全沙箱实现 |
| 13 | **`codex-network-proxy`** | `/code/custom-dev/rea-codex-demo/src/network-proxy` | 62 | **30,008** | 5 | 38 | 受控沙箱环境的本地 HTTP/SOCKS5 域名白名单代理与 MITM 审计 |
| 14 | **`codex-state`** | `/code/custom-dev/rea-codex-demo/src/state` | 60 | **27,134** | 4 | 17 | 核心 SQLite 状态库（含 59 个版本的增量 Schema 迁移） |
| 15 | **`codex-mcp`** | `/code/custom-dev/rea-codex-demo/src/codex-mcp` | 52 | **25,331** | 15 | 19 | MCP 连接管理器 (`connection_manager`) 与将 Codex 作为 MCP Server 暴露 |
| 16 | **`codex-skills-extension`** | `/code/custom-dev/rea-codex-demo/src/ext/skills` | 87 | **23,971** | 15 | 17 | `SKILL.md` 发现、解析、注入与内置系统技能加载 |
| 17 | **`codex-login`** | `/code/custom-dev/rea-codex-demo/src/login` | 68 | **21,903** | 14 | 26 | ChatGPT OAuth PKCE 登录回调服务、Device Code 与凭据存储 |
| 18 | **`codex-app-server-transport`** | `/code/custom-dev/rea-codex-demo/src/app-server-transport` | 34 | **18,385** | 14 | 22 | App-Server 多路复用传输层 (Stdio / WebSocket / Unix Socket) |
| 19 | **`codex-rollout`** | `/code/custom-dev/rea-codex-demo/src/rollout` | 39 | **17,769** | 12 | 13 | 会话轨迹 JSONL (`RolloutLine`) 录制、分页检索与恢复 |
| 20 | **`codex-api`** | `/code/custom-dev/rea-codex-demo/src/codex-api` | 53 | **17,374** | 5 | 27 | OpenAI Responses API / WebSocket v2 / 压缩请求底层客户端 |

### 5.2 最大的 12 个单体 Rust 源码文件

| 排名 | 文件路径 | 行数 (LOC) | 所属模块说明 |
| :---: | :--- | ---: | :--- |
| 1 | `/code/custom-dev/rea-codex-demo/src/core/src/session/tests.rs` | 13,557 | `codex-core` 核心会话状态机全量集成测试 |
| 2 | `/code/custom-dev/rea-codex-demo/src/core/src/config/config_tests.rs` | 13,474 | 配置合并、权限策略与 Profile 覆盖测试 |
| 3 | `/code/custom-dev/rea-codex-demo/src/tui/src/bottom_pane/chat_composer.rs` | 12,649 | TUI 底部多行输入框、斜杠命令补全、`@` 文件引用与快捷键状态机 |
| 4 | `/code/custom-dev/rea-codex-demo/src/tui/src/app/tests.rs` | 9,969 | TUI 顶层应用事件循环测试集 |
| 5 | `/code/custom-dev/rea-codex-demo/src/core/tests/suite/code_mode.rs` | 9,312 | Code Mode (RustyV8) 工具编排端到端测试集 |
| 6 | `/code/custom-dev/rea-codex-demo/src/core-plugins/src/manager_tests.rs` | 7,630 | 插件管理器与 Marketplace 同步测试集 |
| 7 | `/code/custom-dev/rea-codex-demo/src/tui/src/resume_picker.rs` | 7,354 | 历史会话恢复选择器 (`codex resume`) TUI 组件 |
| 8 | `/code/custom-dev/rea-codex-demo/src/codex-mcp/src/connection_manager_tests.rs` | 6,582 | MCP 多服务器连接池与重连容错测试 |
| 9 | `/code/custom-dev/rea-codex-demo/src/protocol/src/protocol.rs` | 6,442 | `Op` 与 `EventMsg` 核心协议枚举与序列化定义 |
| 10 | `/code/custom-dev/rea-codex-demo/src/app-server/src/request_processors/thread_processor.rs` | 6,372 | App-Server 线程创建/恢复/分叉/归档核心请求处理器 |
| 11 | `/code/custom-dev/rea-codex-demo/src/app-server/tests/suite/v2/thread_resume.rs` | 6,350 | App-Server v2 线程恢复端到端测试 |
| 12 | `/code/custom-dev/rea-codex-demo/src/core/tests/suite/realtime_conversation.rs` | 6,088 | 实时语音会话 (Realtime WebRTC) 测试集 |

### 5.3 `unsafe` 块分布与工程安全性分析

全仓 2,169,082 行 Rust 代码中共出现 **1,546 处 `unsafe`**（平均每 1,403 行代码仅 1 处 `unsafe`），且高度集中在底层 OS 沙箱、PTY/终端控制与系统调用封装层，业务层（如 `codex-core` 44.8 万行代码仅 22 处）几乎完全运行在 Safe Rust 下：

| 排名 | 模块目录 | `unsafe` 出现次数 | 主要原因 |
| :---: | :--- | ---: | :--- |
| 1 | `src/windows-sandbox-rs` | 529 | 调用 Win32 安全令牌、Job Object、AppContainer 与 ACL FFI |
| 2 | `src/utils` | 233 | 底层 PTY/信号处理、文件描述符操作与内存映射封装 |
| 3 | `src/tui` | 147 | 终端原始模式切换、`ioctl` 窗口尺寸读取与剪贴板交互 |
| 4 | `src/windows-sandbox-service` | 134 | Windows 提权沙箱辅助服务进程 Win32 API 调用 |
| 5 | `src/linux-sandbox` | 96 | Linux `prctl`、`seccomp`、`landlock`、`unshare`、`mount` 系统调用 |
| 6 | `src/app-server-daemon` | 60 | 守护进程脱离终端 (`setsid`) 与进程间句柄传递 |
| 7 | `src/http-client` / `src/uds` / `src/shell-escalation` | 115 | Unix Domain Socket `SCM_RIGHTS` 文件描述符传递与凭据校验 |

### 5.4 技术债 (Technical Debt) 扫描结果

在 5,607 个 `.rs` 文件中共检出 **352 处 `TODO`** 与 **1 处真实 `FIXME`**（其余 3 处为测试用例中的字符串字面量）：
- **唯一高优 `FIXME`**：位于 [`/code/custom-dev/rea-codex-demo/src/core-plugins/src/executor_hooks.rs:81`](/code/custom-dev/rea-codex-demo/src/core-plugins/src/executor_hooks.rs)（`// FIXME: Remove this temporary filter once executor plugin hooks can be trusted.`），表明执行器插件 Hook 目前设有临时安全过滤白名单。
- **典型架构演进 `TODO`**：
  - [`/code/custom-dev/rea-codex-demo/src/app-server/src/bespoke_event_handling.rs:1816`](/code/custom-dev/rea-codex-demo/src/app-server/src/bespoke_event_handling.rs)：统一 `PathUri` 权限路径后移除旧文本地路径兼容逻辑。
  - [`/code/custom-dev/rea-codex-demo/src/app-server/src/request_processors/initialize_processor.rs:75`](/code/custom-dev/rea-codex-demo/src/app-server/src/request_processors/initialize_processor.rs)：细化 `experimental_api_enabled` 的能力作用域控制。
  - [`/code/custom-dev/rea-codex-demo/src/analytics/src/events.rs:509`](/code/custom-dev/rea-codex-demo/src/analytics/src/events.rs)：打通嵌套 Guardian 审查子会话的工具调用次数统计。

---

## 📦 6. Dependency Analysis (依赖体系深度分析)

### 6.1 内部 Crate 依赖层级与被依赖最多的 Top 15 核心基石 Crate

整个工作空间包含 **161 个内部 Crate**，构成 **1,035 条内部依赖边**。按被其他内部 Crate 依赖的次数（入度 In-Degree）排序，整个 Codex 的架构底座由以下 15 个核心基础 Crate 支撑：

| 排名 | 内部 Crate 名称 | 被内部 Crate 依赖次数 | 工程路径 | 架构层级与职责 |
| :---: | :--- | :---: | :--- | :--- |
| 1 | **`codex-protocol`** | **78** | `/code/custom-dev/rea-codex-demo/src/protocol` | **L0 协议基座**：定义 `Op`、`EventMsg`、`ThreadId`、`SandboxPolicy` 等全局通用数据结构 |
| 2 | **`codex-utils-absolute-path`** | **59** | `/code/custom-dev/rea-codex-demo/src/utils/absolute-path` | **L0 类型安全路径**：编译期强制校验绝对路径的 `AbsolutePathBuf` 类型 |
| 3 | **`codex-http-client`** | **41** | `/code/custom-dev/rea-codex-demo/src/http-client` | **L1 网络底座**：统一 TLS、系统代理回退、重试与请求头注入的 HTTP 客户端 |
| 4 | **`codex-utils-path-uri`** | **34** | `/code/custom-dev/rea-codex-demo/src/utils/path-uri` | **L0 跨端路径 URI**：统一本地文件系统路径与远程/容器 URI 表达 |
| 5 | **`codex-utils-cargo-bin`** | **31** | `/code/custom-dev/rea-codex-demo/src/utils/cargo-bin` | **L0 测试与二进制定位**：定位构建产物与捆绑资源路径 |
| 6 | **`codex-config`** | **30** | `/code/custom-dev/rea-codex-demo/src/config` | **L1 配置中心**：解析 `config.toml`、Feature Flags、模型 Provider 与沙箱策略 |
| 7 | **`codex-login`** | **28** | `/code/custom-dev/rea-codex-demo/src/login` | **L1 认证中心**：管理 API Key、ChatGPT OAuth 令牌与账号状态 |
| 8 | **`codex-core`** | **28** | `/code/custom-dev/rea-codex-demo/src/core` | **L2 核心大脑**：被 TUI、Exec、App-Server、MCP Server、Bench 等所有上层入口依赖 |
| 9 | **`codex-otel`** | **27** | `/code/custom-dev/rea-codex-demo/src/otel` | **L1 可观测性底座**：OpenTelemetry 追踪、指标上报与日志脱敏 |
| 10 | **`codex-extension-api`** | **19** | `/code/custom-dev/rea-codex-demo/src/ext/extension-api` | **L1 扩展契约层**：定义 Skills、Automations、Memories 等内部扩展的统一 Trait |
| 11 | **`codex-git-utils`** | **19** | `/code/custom-dev/rea-codex-demo/src/git-utils` | **L1 Git 工具层**：Worktree 管理、Diff 生成、仓库根目录探测与 Ghost Commit |
| 12 | **`codex-exec-server`** | **18** | `/code/custom-dev/rea-codex-demo/src/exec-server` | **L2 执行引擎**：供 Core 与 App-Server 调用的统一 PTY/管道进程管理器 |
| 13 | **`codex-model-provider`** | **17** | `/code/custom-dev/rea-codex-demo/src/model-provider` | **L1 模型抽象层**：统一封装 OpenAI / Azure / Bedrock 模型请求接口 |
| 14 | **`codex-model-provider-info`** | **17** | `/code/custom-dev/rea-codex-demo/src/model-provider-info` | **L0 模型元数据**：模型上下文窗口、推理等级 (`ReasoningEffort`) 与模态能力定义 |
| 15 | **`codex-state`** | **15** | `/code/custom-dev/rea-codex-demo/src/state` | **L1 状态存储层**：SQLite 核心状态库读写接口 |

### 6.2 外部第三方 Crate 依赖统计 (Top 15)

`src/Cargo.lock` 共锁定 **1,473 个软件包**。在工作空间的 161 个内部 Crate 中，使用频次最高的外部依赖如下：

| 排名 | 外部 Crate | 使用该依赖的内部 Crate 数 | 用途类别 |
| :---: | :--- | :---: | :--- |
| 1 | `pretty_assertions` | 127 | 测试断言对比 |
| 2 | `serde_json` | 100 | JSON 序列化/反序列化 |
| 3 | `tokio` | 92 | 异步运行时 (rt-multi-thread, process, net, sync, time) |
| 4 | `serde` | 84 | 结构体序列化派生 (`1,325` Structs + `458` Variants) |
| 5 | `tempfile` | 75 | 临时目录与隔离测试沙箱 |
| 6 | `tracing` | 74 | 结构化日志与 Span 追踪（二进制内含 `3,971` 条埋点） |
| 7 | `anyhow` | 66 | 顶层与胶水层错误处理 |
| 8 | `thiserror` | 41 | 领域错误枚举定义 |
| 9 | `futures` | 37 | 异步流 (`Stream`) 与组合子 |
| 10 | `chrono` / `http` / `url` | 30 | 时间处理、HTTP 原语与 URL 解析 |
| 11 | `base64` | 28 | 二进制资产与图片附件编码 |
| 12 | `libc` | 26 | POSIX 系统调用与信号量交互 |
| 13 | `wiremock` | 25 | HTTP / API 模拟测试服务器 |
| 14 | `uuid` | 24 | 会话 ID (`ThreadId` / `TurnId`) 生成 |
| 15 | `clap` / `schemars` / `sha2` | 19 | CLI 参数解析、JSON Schema 生成与 SHA-256/SHA-384 校验 |

### 6.3 6 个定制 Git Fork 依赖与 26 个原生动态库依赖

1. **6 个定制 Git 源码依赖**（完整源码已还原至 [`/code/custom-dev/rea-codex-demo/extracted-assets/git-fork-sources/`](/code/custom-dev/rea-codex-demo/extracted-assets/git-fork-sources/)，详细映射见 [`/code/custom-dev/rea-codex-demo/schemas/git-fork-dependencies.json`](/code/custom-dev/rea-codex-demo/schemas/git-fork-dependencies.json)）：
   - `openai-oss-forks/crossterm` (`ed1cdab`)：定制终端键盘协议与 Bracketed Paste 处理（映射 41 个机器码函数，68 个 Panic 点）。
   - `openai-oss-forks/tokio-tungstenite` (`0e5b2d7`) 与 `openai-oss-forks/tungstenite-rs` (`4fffad3`)：定制 WebSocket 握手与帧缓冲控制，支撑 Responses API WebSocket v2 持久连接（合计映射 243 个机器码函数，312 个 Panic 点）。
   - `modelcontextprotocol/rust-sdk` (`3e636ca`)：官方 MCP Rust SDK (`rmcp`)，支撑 MCP 工具调用与 Server 实现（映射 243 个机器码函数，248 个 Panic 点，138 条 `tracing` 埋点）。
   - `hyperium/h3` (`e07e694`)：HTTP/3 (QUIC) 协议支持（映射 210 个机器码函数，360 个 Panic 点）。
   - `helix-editor/nucleo` (`4253de9`)：高性能并行模糊匹配器，用于 TUI `@` 文件搜索与斜杠命令检索（映射 143 个机器码函数，265 个 Panic 点）。
2. **26 个原生动态库依赖**（详见 [`/code/custom-dev/rea-codex-demo/schemas/voice-host-dwarf-and-libs.json`](/code/custom-dev/rea-codex-demo/schemas/voice-host-dwarf-and-libs.json)）：
   - 主二进制 `bin/codex`、`bin/codex-code-mode-host`、`bwrap`、`rg`、`zsh` 均为 **100% 静态链接 Musl ELF（零外部 `.so` 依赖）**。
   - 仅语音宿主 `codex-voice-host` 动态链接了随包附带的 26 个音频/WebRTC 专用 `.so` 库（`libgstreamer-1.0.so.0`、`libgstwebrtc-1.0.so.0`、`libgstrtp-1.0.so.0`、`libnice.so.10`、`libopus.so.0`、`libsrtp2.so.1`、`libssl.so.3`、`libcrypto.so.3` 等）。

---

## 🚀 7. Entry Points & Common Verification Commands (入口与常用验证命令)

1. **运行全量 19 项自动化逆向与完整性自测**：
   ```bash
   python3 /code/custom-dev/rea-codex-demo/scripts/self-test.py
   ```
2. **反查任意二进制虚拟地址（原 `sub_xxxx`）对应的真实 Rust 源文件、函数名与行号区间**：
   ```bash
   python3 /code/custom-dev/rea-codex-demo/scripts/inspect-binary-assets.py --addr 0x1a08d90
   ```
3. **重新生成 Repository Analyzer 度量数据**：
   ```bash
   python3 /code/custom-dev/rea-codex-demo/scripts/run-repository-analyzer.py
   ```
4. **在 100% 隔离的沙箱目录 (`.isolated-env`) 中运行本地 Codex**：
   ```bash
   /code/custom-dev/rea-codex-demo/scripts/run-isolated.sh features list
   ```
