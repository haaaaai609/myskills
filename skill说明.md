# Skill 说明

本文档说明 `/data/yzh/skill-generate` 目录下各个 skill 的用途、适用场景和边界。

## 总览

| Skill | 主要用途 | 典型使用场景 |
| --- | --- | --- |
| `bug-root-cause` | 先诊断根因，再决定是否修复 | 报错、异常、测试失败、服务启动失败、日志排查 |
| `feature-evolution` | 在已有系统上演进功能 | 新增/修改功能、调整流程、改 UI/API、接入集成 |
| `new-project-architect` | 从 0 到 1 规划并创建新项目 | 新应用、新服务、新工具、新网站、原型项目 |
| `release-quick-deploy` | 生成离线快速部署包 | Docker Compose/多服务项目交付到其他服务器快速部署 |

## 如何给 Codex 使用

### 1. 放到 Codex 可发现的 skills 目录

Codex 通常从 `${CODEX_HOME:-$HOME/.codex}/skills` 读取个人 skills。可以把需要启用的 skill 目录放到这个目录下，例如：

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -a /data/yzh/skill-generate/bug-root-cause "${CODEX_HOME:-$HOME/.codex}/skills/"
cp -a /data/yzh/skill-generate/feature-evolution "${CODEX_HOME:-$HOME/.codex}/skills/"
cp -a /data/yzh/skill-generate/new-project-architect "${CODEX_HOME:-$HOME/.codex}/skills/"
cp -a /data/yzh/skill-generate/release-quick-deploy "${CODEX_HOME:-$HOME/.codex}/skills/"
```

如果不想复制，也可以在任务里明确告诉 Codex 使用某个路径下的 skill。

### 2. 在提示词中显式指定 skill

最稳定的方式是在提示词里写 `$skill-name`，例如：

```text
使用 $bug-root-cause 分析这个报错，先说明根因，不要直接改代码。
```

```text
使用 $feature-evolution 给现有系统增加一个数据导入功能，先更新设计和开发文档，再实现。
```

```text
使用 $new-project-architect 从零创建一个后台管理系统，先澄清需求并生成 docs/spec 和 docs/plan。
```

```text
使用 $release-quick-deploy 为这个 Docker Compose 项目生成离线快速部署 release 包。
```

### 3. 让 Codex 自动选择

如果 skill 已经放在 Codex skills 目录下，Codex 也可以根据请求内容自动触发。为了减少误判，建议在任务描述里写清楚目标：

- 报错、失败、日志、异常：Codex 应使用 `bug-root-cause`。
- 已有项目加功能或改功能：Codex 应使用 `feature-evolution`。
- 从零创建新项目：Codex 应使用 `new-project-architect`。
- 生成离线部署 release 包：Codex 应使用 `release-quick-deploy`。

### 4. 临时指定本地路径

如果这些 skill 还没有安装到 Codex skills 目录，可以直接给出本地路径：

```text
使用 /data/yzh/skill-generate/release-quick-deploy 这个 skill，为当前项目生成离线部署包。
```

这种方式适合临时测试；长期使用时，建议放到 Codex 可发现的 skills 目录。

## `bug-root-cause`

这个 skill 用于处理“已经出现问题”的场景。它的核心原则是：先看证据、复现或分析问题、说明根因，再询问用户是否要修改代码。

适合使用在：

- 程序报错、异常、崩溃。
- 命令执行失败、测试失败。
- 服务无法启动、部署失败。
- 用户给出日志、堆栈、错误截图或异常行为描述。
- 用户说“报错了”“帮我 debug”“为什么失败”“修这个错误”。

不适合使用在：

- 没有错误，只是想新增功能。
- 从零创建新项目。
- 纯重构或优化，但没有明确 bug。

这个 skill 的特点是比较谨慎：在没有向用户说明根因并获得确认前，不应该直接改代码、配置、迁移或文档。

## `feature-evolution`

这个 skill 用于在已有项目上做功能演进。它强调先理解当前系统和现有文档，再更新设计/开发文档，最后按更新后的计划实现功能。

适合使用在：

- 给已有系统新增功能。
- 修改已有业务流程。
- 调整 UI、API、数据结构或服务集成。
- 在现有项目基础上扩展能力。
- 用户说“加一个功能”“改一下当前系统”“基于这个项目继续开发”。

不适合使用在：

- 空仓库或从零开始的新项目。
- 主要目标是排查 bug 或报错。
- 用户只是让做代码审查，且没有要求实现功能变化。

这个 skill 的重点是保持系统一致性：优先遵循仓库已有结构、命名、文档位置、测试方式和实现风格。

## `new-project-architect`

这个 skill 用于新项目从想法到落地的全过程。它会先澄清需求，再写系统设计文档和开发计划，之后才开始实现。

适合使用在：

- 创建一个全新的应用、服务、工具、网站、游戏或库。
- 空仓库或几乎没有业务代码的仓库。
- 用户只有初步产品想法，需要整理需求、架构和开发计划。
- 用户说“新建一个项目”“从零做一个系统”“帮我搭一个服务”。

不适合使用在：

- 已有系统上的功能修改，这类应使用 `feature-evolution`。
- 报错、测试失败、部署失败等诊断任务，这类应使用 `bug-root-cause`。
- 用户明确只想咨询或审查，不想进入实现。

这个 skill 会把项目设计放在 `docs/spec/`，把开发计划放在 `docs/plan/`，并要求文档足够具体，方便后续按计划实现。

## `release-quick-deploy`

这个 skill 用于把项目整理成可交付到其他服务器的离线快速部署包。它适合 Docker Compose 或多服务项目，目标是让目标服务器拿到 release 目录后，通过少量脚本命令完成初始化、检查、启动和维护。

适合使用在：

- 需要生成 `release/` 部署目录。
- 需要离线镜像目录，如 `images/infra/`、`images/services/`。
- 需要 `.env.example`、`docker-compose.yml`、`docker-compose.services.yml`。
- 需要部署维护脚本，如 `scripts/release.sh`。
- 项目包含前端静态包、后端服务、中间件、模型、SDK、native libs、SQL 初始化等交付物。
- 希望业务服务可以通过替换 pkg 或服务镜像快速升级。

不适合使用在：

- 纯 Kubernetes/Helm 交付，且不需要 Docker Compose release 包。
- 完全不能容器化、也没有清晰部署脚本边界的项目。
- 只想本地开发运行，不涉及离线交付或服务器部署。

这个 skill 自带 `scripts/generate_release_package.py`，可以根据 `release-manifest.json` 生成通用 release 骨架。生成后仍需要根据具体项目补充真实镜像、pkg、前端产物、runtime 资产、SQL、迁移命令和健康检查。

## 选择建议

- 看到“报错、失败、日志、异常”：优先用 `bug-root-cause`。
- 看到“已有项目上加/改功能”：优先用 `feature-evolution`。
- 看到“从零做一个新项目”：优先用 `new-project-architect`。
- 看到“生成 release 包、离线部署、快速交付到服务器”：优先用 `release-quick-deploy`。

如果一个任务同时包含多个阶段，先按当前最关键阶段选择。例如“服务启动失败后顺便优化部署脚本”，应先用 `bug-root-cause` 查清失败原因；确认修复后，再考虑用 `release-quick-deploy` 优化交付结构。
