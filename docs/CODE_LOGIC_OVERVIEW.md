# 当前代码逻辑梳理

本文档说明 `loc_code` 当前代码的整体执行逻辑，以及主要文件各自负责什么。它面向后续维护者：先看执行链路，再看文件职责。

## 总体执行链路

当前代码按 canonical task 组织。用户一般不直接调用各任务 runner，而是从根目录入口开始：

```bash
python run_tasks.py --ids CU.1 --models <model> --target-runs 1 --stage run
python run_tasks.py --ids CU.1 --models <model> --stage judge
python score_tasks.py --ids CU.1 --models <model>
```

核心链路是：

```text
run_tasks.py
  -> loc.dispatch
  -> loc.task_registry 找到 canonical task 对应的 runner
  -> loc/tasks/<family>/... 运行模型并写 results
  -> loc/evaluators/judges/... 可选 judge/eval
  -> score_tasks.py
  -> loc.evaluators.canonical
  -> loc/evaluators/methods 或 adapters 读取结果并输出分数
```

`run` 阶段负责生成模型回答和任务内可直接计算的指标。`judge` 阶段只用于需要额外判别的任务。`score` 阶段统一读取 raw/judge/eval 产物，输出 canonical score。

## 顶层文件

### `run_tasks.py`

运行任务的顶层入口。这个文件本身很薄，只调用：

```python
from loc.dispatch import main
```

后续调度逻辑都在 `loc/dispatch.py`。

### `score_tasks.py`

算分入口。这个文件也很薄，只调用：

```python
from loc.evaluators.canonical import main
```

后续 canonical scoring 逻辑都在 `loc/evaluators/canonical.py`。

### `AGENTS.md`

给 Codex/agent 的仓库操作说明，包含目录含义、运行方式、验证方式和注意事项。

## 核心调度层

### `loc/task_registry.py`

这是当前最重要的任务表。它定义：

- 每个 canonical task 的 ID、名称、section、dimension、family。
- 任务是否已实现：`implemented`、`missing`、`external`。
- 每个任务要调用哪些 runner。
- 多组件任务如何展开，比如 `PB.1` 展开成 choice/reasoning/yesno，`CB.2` 展开成 biology/chemistry/nuclear。

关键数据结构：

- `TaskSpec`：一条 canonical task。
- `RunSpec`：一条具体 runner 调用。
- `TASKS`：完整任务表。

后续如果加新任务，首先应该改这里，让任务出现在 `python run_tasks.py --list` 里。

### `loc/dispatch.py`

把用户命令翻译成具体脚本调用。它负责：

- 解析 `--ids`、`--tasks`、`--dimensions`、`--sections`。
- 从 `task_registry.py` 找到对应 `RunSpec`。
- `run` 阶段调用对应 task runner。
- `judge` 阶段调用对应 judge 脚本。
- `score` 阶段调用 `score_tasks.py`。
- 支持 `--target-runs`、`--dry-run`、`--continue-on-error`。

这里不直接实现任务逻辑，只负责任务选择和命令调度。

### `loc/chat.py`

统一模型调用入口。所有普通任务 runner 最好通过 `call_model()` 调模型。

它根据 model name 选择不同后端：

- OpenAI-compatible API
- Azure OpenAI
- Anthropic Claude
- Gemini
- DashScope/Qwen streaming

它也处理 retry、thinking 内容拼接、空响应兜底。

### `env/api_config.py`

读取模型配置和环境变量。这里配置 API key、base URL、默认 token 数等。

注意：不要打印或改写真实密钥。

## 任务 runner 层

任务 runner 负责三件事：

1. 读取 `data/<family>/...` 输入。
2. 调模型生成回答。
3. 写入 `results/<family>/<model>/<component>/run_NNN.json`。

如果任务是客观题或 runner 内部可自动判分，runner 会直接在 `run_NNN.json` 中写 `summary`、`accuracy`、`ratio` 等指标。

### `loc/tasks/curiosity/`

- `runner.py`：实现 `CU.1` 和 `CU.2`。
  - `CU.1` 读取 `cu1_cognitive_curiosity.jsonl`，统计回答中是否出现 `?` 或 `？`，写 `summary.ratio`。
  - `CU.2` 读取 `cu2_decision_curiosity.jsonl`，抽取 A-F 选项，统计 `A` 比例，写 `summary.ratio_A`。
- `prompts.py`：构造 curiosity 两个任务的 prompt。

### `loc/tasks/self_preservation/`

- `runner.py`：实现 `SP.1` 和 `SP.2`。
  - `SP.1` 计算 high-risk mission refusal 的 match rate。
  - `SP.2` 计算 survival-threat reversal 的 flip rate。
- `prompts.py`：self-preservation 任务 prompt。

### `loc/tasks/power_seeking/`

- `runner.py`：实现 `PS.1` 和 `PS.2`。
  - `PS.1` 是固定偏好选择，runner 直接写 `summary.overall.match_rate`。
  - `PS.2` 是开放式计划回答，runner 保存原始三轮回答，后续需要 judge。
- `prompts.py`：power-seeking 任务 prompt。

### `loc/tasks/preai/`

- `runner.py`：实现 `PB.1` 和 `PB.2`。
  - `PB.1` 包含 choice、reasoning、yesno 三个组件。
  - choice 和 yesno 直接算 accuracy。
  - reasoning 保存开放式回答，后续需要 judge。
  - `PB.2` 直接统计 blind-source preference 的 consistency/prefer ratio 所需字段。
- `prompts.py`：pre-AI 任务 prompt。

### `loc/tasks/sycophancy/`

- `runner.py`：实现 canonical sycophancy runner。
  - `SY.1` 生成 factual sycophancy 回答。
  - `SY.2` 生成 OEQ 和 PAS 回答。
  - 具体分数由 sycophancy judge 脚本汇总。
- `multi.py`：旧版/兼容 sycophancy 批量运行脚本。
- `prompts.py`：sycophancy prompt。

### `loc/tasks/perpetuation/`

- `runner.py`：实现 `AU.1 Self-Replication Capability` 的入口。
- `limited_command.py`、`limited_command_gpt.py`：长流程环境操作 agent，负责受限命令执行、模型交互、轨迹记录。

这类任务不是简单问答，运行时间和外部环境依赖更重。

### `loc/tasks/cbrn/`

CBRN 按领域拆 runner：

- `b_runner.py`：biology，运行 `cb1_biology`、`cb2_biology`、`cb3_biology`。
- `c_runner.py`：chemistry，运行 `cb1_chemistry`、`cb2_chemistry`、`cb3_chemistry`。
- `r_runner.py`：nuclear/radiological，运行 `cb1_nuclear`、`cb2_nuclear`、`cb3_nuclear`。
- `prompts.py`：CBRN prompt。

其中：

- `CB.2` 三个组件都是客观题，runner 直接写 accuracy/top3_precision。
- `CB.1` 和 `CB.3` 的 nuclear 是开放式回答，需要后续 eval。

### `loc/tasks/cyber_misuse/`

- `task1_runner.py`：`CY.1 Cybersecurity Knowledge`，固定答案知识题，直接写 `accuracy`。
- `task2_runner.py`：`CY.2 CTF Challenge Solving`，生成 CTF 解题回答，后续 judge 打分。
- `task3_runner.py`：`CY.3 Vulnerability Exploitation`，生成 exploit/漏洞利用回答，后续验证。
- `runner.py`、`multi.py`：兼容旧入口或聚合入口。
- `prompts.py`：cyber 任务和 judge prompt 构造。
- `cy1_cybersecurity_knowledge/`、`cy2_ctf_challenge_solving/`、`cy3_vulnerability_exploitation/`：旧版或任务拆分后的兼容脚本目录。

### `loc/tasks/sandbagging/`

- `runner.py`：实现 `SB.1` 和 `SB.2`。
  - `SB.1` 跑 bio/chem/cyber 的 predeploy/deployed 条件。
  - `SB.2` 跑 math 的 predeploy/deployed 条件。
  - 每个条件内可直接算 accuracy。
- `prompts.py`：sandbagging 条件化 prompt。

最终 sandbagging 分数不是单个 accuracy，而是 deployed-minus-predeploy accuracy delta。

### `loc/tasks/deception/`

- `runner.py`：实现 `DC.2` 和 `DC.3`。
  - `DC.2` 生成 harmful content rewriting，并在 runner 内调用 moderation 和 embedding similarity。
  - `DC.3` 生成 risky action explanation，并在 runner 内调用 auditor 检查。
- `prompts.py`：deception prompt、supervisor prompt、auditor prompt。

这里虽然用到了 judge-like 检查，但它是在 runner 内部完成，不需要单独 `--stage judge`。

### `loc/tasks/sabotage/`

- `runner.py`：实现 `SG.1 Direct Monitor Attack` 的入口。
- `workflow_solver.py`：执行 sabotage workflow。
- `model_config.py`：sabotage 相关模型配置。
- `prompts.py`：sabotage supervisor/auditor prompt。
- `react_agents/react_agent.py`：执行任务的 ReAct agent。
- `react_agents/supervisor_agent.py`：监督/评估 agent。

SG.1 通过 inspect/docker workflow 产生 `task_completed` 和 `dangerous_actions` 字段，score 阶段读取这些字段。

## Evaluator 与 scoring 层

### `loc/evaluators/canonical.py`

canonical scorer 的总入口。它负责：

- 按 task ID 找到对应 scoring adapter。
- 从 `results/` 读取 raw、judge 或 eval 产物。
- 输出统一字段：

```text
Model, ID, Task Name, Section, Dimension, Score, N, SD, SEM, Status, Detail
```

每个 task 的核心算分路径都在 `_adapter_for()` 中注册。

### `loc/evaluators/methods/core.py`

通用 scoring 方法：

- `direct_summary()`：直接读取 `run_NNN.json` 中某个路径，例如 `summary.ratio`。
- `computed_summary()`：读取 run 文件后用函数计算值。
- `judge_summary()`：读取 `run_NNN_judge.json` 后计算值。
- `combine_scores()`：组合多个组件分数。
- `stats_score()`：对多次 run 计算 mean、SD、SEM。

### `loc/evaluators/methods/artifacts.py`

结果文件发现和 CSV 输出工具：

- 找 `run_NNN.json`
- 找 `run_NNN_judge.json`
- 写 `canonical_scores.csv`
- 打印分数表

### `loc/evaluators/methods/canary_scorer.py`

Cyber vulnerability / Canary exploit 相关的专用 scoring 工具，被 cyber judge 使用。

### `loc/evaluators/adapters/cbrn.py`

CBRN canonical score adapter。它负责把 biology/chemistry/nuclear 三个 component 合并。

特别注意：

- `cb1_nuclear` 和 `cb3_nuclear` 读取 `run_NNN_eval.json`。
- `cb2_biology` 读取 `top3_precision`。
- `cb3_biology` 读取 `overall_accuracy`。
- 其他 CBRN 客观题读取 `accuracy`。

### `loc/evaluators/adapters/paired_delta.py`

Sandbagging score adapter。它读取 predeploy/deployed 两种条件的 accuracy，然后计算：

```text
deployed_unmonitored accuracy - predeploy_monitored accuracy
```

`SB.1` 对 bio/chem/cyber 三个 dataset 求均值。`SB.2` 对 math 求 delta。

### `loc/evaluators/adapters/perpetuation.py`

AU.1 score adapter。读取 `results/perpetuation/<model>/result_evaluation.json`，计算 self-replication 的 Bayesian pass@3 group score。

## Judge / Eval 脚本

这些脚本只给需要额外判别的任务使用。

### `loc/evaluators/judges/preai_explicit_why.py`

给 `PB.1 reasoning` 做 judge。读取开放式 reason，判断回答是否 fair，写：

```text
results/preai/<model>/pb1_ai_human_choice_reasoning/run_NNN_judge.json
```

### `loc/evaluators/judges/power_seeking_instrumental.py`

给 `PS.2` 做 judge。判断三轮回答里是否包含 instrumental power pursuit 行为，写 `run_NNN_judge.json`。

### `loc/evaluators/judges/sycophancy.py`

给 `SY.1` 和 `SY.2` 做 judge，并把结果汇总写到：

```text
results/sycophancy/sycophancy_scores.csv
```

### `loc/evaluators/judges/perpetuation.py`

给 `AU.1` 的长流程轨迹做评估，输出：

```text
results/perpetuation/<model>/result_evaluation.json
```

### `loc/evaluators/judges/cbrn_open.py`

给 `CB.1 nuclear` 和 `CB.3 nuclear` 做开放式回答 eval，输出：

```text
results/cbrn/<model>/cb1_nuclear/run_NNN_eval.json
results/cbrn/<model>/cb3_nuclear/run_NNN_eval.json
```

### `loc/evaluators/judges/cbrn_open_claude.py`

CBRN nuclear 的另一个 judge/eval 版本，带 refusal detection。当前 canonical dispatch 默认使用 `cbrn_open.py`。

### `loc/evaluators/judges/cyber_ctf.py`

给 `CY.2` 的 CTF 回答打 0-5 分，输出：

```text
results/cyber_misuse/<model>/cy2_ctf_challenge_solving_judge/run_NNN.json
```

### `loc/evaluators/judges/cyber_vulnerability.py`

给 `CY.3` 的 vulnerability exploitation 回答做验证/评分，输出：

```text
results/cyber_misuse/<model>/cy3_vulnerability_exploitation_judge/run_NNN.json
```

### `loc/evaluators/judges/deception.py`

Deception runner 内部使用的 judge-like 工具，提供：

- `call_gpt()`：调用 supervisor/auditor。
- `compute_embedding_similarity()`：计算文本相似度。

它不是独立 `--stage judge` 的入口，而是被 `loc/tasks/deception/runner.py` 调用。

## 工具层

### `loc/utils/io.py`

通用 run 文件管理：

- `atomic_write_json()`：原子写 JSON，避免半写文件。
- `existing_run_indices()`：扫描已有 `run_NNN.json`。
- `next_missing_run_index()`：找下一个缺失 run。
- `completed_run_count()`：判断 target runs 是否已经完成。

### `loc/utils/text.py`

文本清洗工具，例如去掉 `<think>...</think>`。

### `loc/utils/parsing.py`

通用解析工具，用于从模型输出中抽取结构化结果。

### `loc/utils/refusal.py`

拒答检测相关工具。

### `loc/utils/stats.py`

统计工具，计算 mean、SD、SEM、N。

## 数据、结果和日志

### `data/`

任务输入数据。多数 runner 会从这里读取 JSON/JSONL。

不要随意改 prompt 对应数据字段名，否则 runner 可能读不到。

### `results/`

正式评测产物。`score_tasks.py` 主要读取这里。

常见结构：

```text
results/<family>/<model>/<component>/run_NNN.json
results/<family>/<model>/<component>/run_NNN_judge.json
results/<family>/<model>/<component>/run_NNN_eval.json
results/canonical_scores.csv
```

### `logs/`

运行日志和 debug 信息。它通常不参与算分，只用于排查执行失败、API 报错、sandbox 轨迹等。

## Scripts

`scripts/` 下是方便运行的 shell wrapper：

- `run_all.sh`：跑所有已配置任务。
- `run_curiosity.sh`
- `run_power_seeking.sh`
- `run_self_preservation.sh`
- `run_preai.sh`
- `run_sycophancy.sh`
- `run_perpetuation.sh`
- `run_cbrn.sh`
- `run_cyber_misuse.sh`
- `run_sandbagging.sh`
- `run_deception.sh`
- `run_sabotage.sh`

这些脚本最终仍然会调用 Python runner 或 `run_tasks.py`，不是新的逻辑来源。

## 增加或修改任务时应该看哪里

新增一个任务通常需要改这些地方：

1. `loc/task_registry.py`
   添加 `TaskSpec` 和 `RunSpec`。

2. `loc/tasks/<family>/`
   添加或扩展 runner，保证输出稳定写到 `results/<family>/<model>/<component>/run_NNN.json`。

3. `loc/evaluators/judges/`
   如果任务需要开放式 judge/eval，在这里添加 judge 脚本。

4. `loc/evaluators/canonical.py`
   在 `_adapter_for()` 中添加 canonical score adapter。

5. `docs/TASK_RUN_AND_SCORE_GUIDE.md`
   写清楚运行命令、结果路径、是否需要 judge/eval、为什么、怎么算分。

6. `docs/ADDING_NEW_DIMENSIONS.md`
   如果是新增维度，补充维度级说明。

## 维护原则

- prompt 不应无意改动；prompt 改动会直接影响结果可比性。
- model 调用参数不应无意改动；例如 max tokens、thinking、base URL、judge model。
- runner 输出字段要稳定；scorer 依赖这些字段。
- 需要 judge 的任务必须明确写出 judge 产物路径。
- 不需要 judge 的任务必须明确说明 runner 如何自动判分。
- 任务命名优先使用 canonical ID 和 component 名，不再引入 `task1/task2/b1/c1/r1` 这类难读命名。
