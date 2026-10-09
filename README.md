# 61A 递归实验室 · CS61A AI 学习平台

一个帮助学习 UC Berkeley **CS61A** 的交互式 Python 学习平台：上传或编写 Python 代码、自动运行测试、**逐步可视化递归调用过程**、生成 **Environment Diagram（环境图）**，并围绕 **Recursion / Link / Tree** 提供交互式练习、WWPD 测验和 AI 导师。

- 前端：React 19 + TypeScript + Vite（CodeMirror 编辑器，自绘 SVG 环境图与调用树）
- 后端：Python + FastAPI（`sys.settrace` 执行追踪、doctest 测试运行器、AST 代码诊断、可选 Claude 导师）

📖 **完整使用说明见 [docs/USAGE.md](docs/USAGE.md)**（平台内“使用说明”页面显示同一份文档）。

## 功能

| 功能 | 说明 |
| --- | --- |
| 上传 Python 代码 | 上传 / 拖拽 `.py` 文件，自动检查语法、列出函数并**自动运行测试** |
| 自动运行测试 | 收集 doctest 与 `test_*` 函数；每个用例独立限时；显示期望 / 实际输出；失败用例一键可视化 |
| 递归调用可视化 | 每次调用一个节点的递归调用树，随执行步骤生长；显示返回值、栈深度、**重复子问题**（记忆化动机），点击节点跳转 |
| Environment Diagram | CS61A 风格：编号帧 `f1: fact [parent=Global]`、Return value、已返回帧、闭包 parent、λ 帧、指针箭头；`Link` 画成盒子-指针链，`Tree` 画成树 |
| 交互式练习 | 22 道练习：递归 8、链表 6、树 8（含函数式 tree ADT）；隐藏测试、代码要求（必须递归 / 不准循环）、渐进提示、参考答案、进度记录 |
| WWPD 测验 | 17 道 “What Would Python Display?” 题，答案经真实 Python 校验 |
| AI 导师 | 离线规则导师（AST 诊断：缺少 base case、参数不变小、丢弃递归结果、`Link.empty` 误用……）；设置 `ANTHROPIC_API_KEY` 后由 Claude 进行苏格拉底式引导 |
| 安全运行 | 学生代码在独立子进程中运行：CPU / 内存 / 时间限制，禁止写文件、子进程与网络 |

## 快速开始

需要 Python 3.10+ 与 Node.js 20.19+。

```bash
make install   # 创建 backend/.venv 并安装前后端依赖
make dev       # 后端 http://localhost:8000 + 前端 http://localhost:5173
```

打开 <http://localhost:5173> 即可使用。单进程部署：`make serve`（构建前端后由后端在 :8000 一并提供）。

可选：启用 Claude 导师

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

## 测试

```bash
make test   # 后端 pytest + 前端 tsc 类型检查 + Vitest 单元测试
make e2e    # Playwright 端到端测试（自动启动前后端）
```

后端测试会逐一验证：每道练习的参考答案能通过全部测试、初始代码不能通过、可视化示例可以运行；每道 WWPD 题的答案与真实 Python 输出一致。

## 项目结构

```
backend/
  app/
    main.py            FastAPI 路由（/api/run、/api/test、/api/trace、/api/upload、练习、测验、导师）
    sandbox.py         启动受限子进程运行学生代码
    runner/
      child.py         子进程入口（审计钩子：禁止写文件 / 子进程 / 网络）
      tracer.py        执行追踪器：环境图快照 + 递归调用树
      test_runner.py   doctest / 练习测试 / test_ 函数运行器（单用例超时）
      prelude.py       内置 Link、Tree、函数式 tree ADT
    analyzer.py        AST 静态分析（规则导师）与练习代码要求检查
    tutor.py           AI 导师（Claude 或离线规则）
    exercises.py       练习题库
    quizzes.py         WWPD 题库
  tests/               pytest 测试
frontend/
  src/
    components/        Visualizer、EnvironmentDiagram、CallTree、TestResults、TutorPanel …
    lib/               调用树布局、堆对象布局等纯函数（有单元测试）
    pages/             代码实验室、练习、练习工作区、WWPD、使用说明
  e2e/                 Playwright 端到端测试
docs/USAGE.md          使用说明
```

## API 概览

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/run` | 运行代码，返回输出与错误 |
| POST | `/api/test` | 运行 doctest / `test_*`（可附加 doctest 格式的测试），附带代码诊断 |
| POST | `/api/trace` | 逐步追踪执行，返回环境图快照与递归调用树 |
| POST | `/api/upload` | 上传 `.py`（multipart），自动运行测试 |
| POST | `/api/analyze` | AST 代码诊断 |
| GET | `/api/exercises`、`/api/exercises/{id}` | 练习列表 / 详情 |
| POST | `/api/exercises/{id}/submit` | 提交练习（含隐藏测试与代码要求） |
| GET | `/api/exercises/{id}/solution` | 参考答案 |
| GET / POST | `/api/quizzes`、`/api/quizzes/{id}/check` | WWPD 测验 |
| POST | `/api/tutor` | AI 导师问答 |

启动后端后访问 <http://localhost:8000/docs> 可查看交互式 API 文档。

## 安全说明

子进程隔离、资源限制和审计钩子适合课堂与个人学习场景，但不是严格的安全边界。如需公开部署，请将后端运行在容器等隔离环境中。
