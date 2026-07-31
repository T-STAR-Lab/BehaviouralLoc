# 如何添加新维度和新任务

本文档说明如何在当前代码结构里添加新的 benchmark 维度、canonical task、runner、judge/eval 和算分逻辑。

## 基本原则

对外展示和调度选择统一使用 canonical task ID：

```text
SA.1, SA.2, PE.1, PE.2, SG.2
```

文件名、runner 参数、结果目录统一使用小写 canonical slug：

```text
sa1_lifecycle_stage_recognition
sa2_monitoring_script_identification
pe1_false_belief_persuasion
pe2_harmful_compliance_persuasion
sg2_indirect_monitor_disruption
```

不要再新增 `task1`、`task2`、`part1`、`b1`、`c1`、`r1` 这类只在局部代码里才知道含义的名字。

如果一个 canonical task 有多个组件，组件名也要带上 canonical task 语义：

```text
pb1_ai_human_choice_reasoning
cb1_biology
sb1_bio_predeploy_monitored
```

## 常见需要修改的文件

新增一个完整任务通常会涉及：

```text
loc/task_registry.py
loc/tasks/<family>/runner.py
loc/tasks/<family>/prompts.py
data/<family>/<canonical_slug>.<json|jsonl>
loc/evaluators/canonical.py
loc/evaluators/adapters/<adapter>.py        # 可选
loc/evaluators/judges/<judge>.py            # 可选
scripts/run_<family>.sh                     # 可选
docs/TASK_RUN_AND_SCORE_GUIDE.md
```

重构或新增时不要无意改动 prompt 内容、默认 system/user message、模型调用参数、judge model、temperature、max tokens、答案抽取逻辑。除非任务本身就是要改这些，否则应只改结构、命名和接入方式。

## 第一步：在任务表里注册

任务表在：

```text
loc/task_registry.py
```

已实现任务示例：

```python
TaskSpec(
    "SA.1",
    "Lifecycle Stage Recognition",
    OVERSIGHT_EVASION,
    "situation_awareness",
    "situation_awareness",
    run_specs=(
        RunSpec(
            "SA.1",
            "Lifecycle Stage Recognition",
            "situation_awareness",
            runner_task="sa1_lifecycle_stage_recognition",
        ),
    ),
    score_key="situation_awareness.sa1",
)
```

如果任务有专门 runner 脚本，可以指定 `script`：

```python
TaskSpec(
    "PE.1",
    "False Belief Persuasion",
    OVERSIGHT_EVASION,
    "persuasion",
    "persuasion",
    run_specs=(
        RunSpec(
            "PE.1",
            "False Belief Persuasion",
            "persuasion",
            script="loc/tasks/persuasion/pe1_runner.py",
        ),
    ),
    score_key="persuasion.pe1",
)
```

如果任务先占位但还没实现，保留 `status="missing"`：

```python
TaskSpec(
    "PE.1",
    "False Belief Persuasion",
    OVERSIGHT_EVASION,
    "persuasion",
    "persuasion",
    status="missing",
    notes="Not yet added to this repository.",
)
```

## 第二步：添加数据

数据放在：

```text
data/<family>/
```

命名使用 canonical slug：

```text
data/situation_awareness/sa1_lifecycle_stage_recognition.jsonl
data/persuasion/pe1_false_belief_persuasion.json
```

如果一个任务有多个组件：

```text
data/example/ex1_component_a.json
data/example/ex1_component_b.json
```

不要把旧备份文件放在活跃数据目录里，避免后续操作者误用。

## 第三步：添加 runner

runner 应该满足：

- 支持 `--model`
- 支持 `--target-runs`
- 需要选择组件时支持 `--task <canonical_slug>`
- 输出到 `results/<family>/<model>/<canonical_component>/run_NNN.json`
- 使用 `loc.utils.io` 里的断点续跑工具

推荐结构：

```python
DATA_DIR = Path("./data/situation_awareness")
DEFAULT_OUTPUT_DIR = Path("./results/situation_awareness")

TASKS = {
    "sa1_lifecycle_stage_recognition": evaluate_sa1,
    "sa2_monitoring_script_identification": evaluate_sa2,
}

def _run_loop(label, evaluate_fn, model, outdir, target_runs):
    run_dir = outdir / model / label
    existing = existing_run_indices(run_dir)
    while completed_run_count(existing, target_runs) < target_runs:
        idx = next_missing_run_index(existing, target_runs)
        evaluate_fn(model, run_dir / f"run_{idx:03d}.json")
        existing = existing_run_indices(run_dir)
```

如果一个 canonical task 需要多个组件共同组成，在 `TaskSpec.run_specs` 里写多个 `RunSpec`。

## 第四步：添加 judge 或 eval

只有原始 `run_NNN.json` 不能直接算分时，才需要 judge/eval。

### judge 和 eval 的区别

`judge` 通常表示 LLM-as-judge 或判别器对原始输出做分类、判断或打分。

```text
results/<family>/<model>/<component>/run_NNN_judge.json
```

`eval` 通常表示已经包含逐题评分和汇总指标的评估结果。

```text
results/<family>/<model>/<component>/run_NNN_eval.json
```

两者都处在同一阶段：

```text
run_NNN.json -> judge/eval artifact -> score_tasks.py
```

新增时建议：

- LLM-as-judge 分类或判断：优先用 `run_NNN_judge.json`
- 逐题评分加总分：可用 `run_NNN_eval.json`
- 如果 judge 产物是单独目录，目录名应为 `<component>_judge`

judge 脚本放在：

```text
loc/evaluators/judges/
```

然后在 `loc/dispatch.py` 注册：

```python
elif spec.task_id == "SA.1":
    add("loc/evaluators/judges/situation_awareness.py")
```

如果只有某个组件需要 judge：

```python
elif spec.task_id == "CB.1" and spec.component == "nuclear":
    add("loc/evaluators/judges/cbrn_open.py", ["--component", "cb1_nuclear"])
```

## 第五步：添加算分逻辑

统一入口是：

```text
loc/evaluators/canonical.py
```

如果可以直接读 JSON 字段：

```python
"SA.1": lambda t, m: direct_summary(
    t,
    m,
    "situation_awareness",
    "sa1_lifecycle_stage_recognition",
    ("summary", "accuracy"),
),
```

如果需要自己计算：

```python
def _sa2_value(data) -> Optional[float]:
    items = data.get("items", [])
    if not items:
        return None
    return sum(1 for item in items if item.get("correct")) / len(items)

"SA.2": lambda t, m: computed_summary(
    t,
    m,
    "situation_awareness",
    "sa2_monitoring_script_identification",
    _sa2_value,
    "situation_awareness/SA.2 correct rate",
),
```

如果读取 judge 文件：

```python
"PE.1": lambda t, m: judge_summary(
    t,
    m,
    "persuasion",
    "pe1_false_belief_persuasion",
    _pe1_judge_value,
    "persuasion/PE.1 judge score",
),
```

如果公式较复杂，放到：

```text
loc/evaluators/adapters/
```

例如当前的 CBRN、sandbagging、perpetuation 都是 adapter。

## 第六步：添加便捷脚本

便捷脚本不是必须，但如果该维度有多个 judge 步骤或外部环境，可以添加：

```text
scripts/run_<family>.sh
```

脚本内部仍应调用 canonical 入口：

```bash
python run_tasks.py --tasks situation_awareness --models "${MODELS[@]}" --target-runs "$TARGET_RUNS" --stage run
python run_tasks.py --tasks situation_awareness --models "${MODELS[@]}" --stage judge
python run_tasks.py --tasks situation_awareness --stage score
```

## 第七步：更新文档

在 `docs/TASK_RUN_AND_SCORE_GUIDE.md` 里补上新任务：

- canonical ID
- 维度
- 数据路径
- run 结果路径
- judge/eval 结果路径
- 算分来源
- run 命令
- judge 命令
- score 命令

## 第八步：验证

基础检查：

```bash
python run_tasks.py --list
python -m py_compile run_tasks.py score_tasks.py loc/task_registry.py loc/dispatch.py loc/evaluators/canonical.py loc/tasks/<family>/runner.py
```

可选 dry-run：

```bash
python run_tasks.py --ids <ID> --models <model> --target-runs 1 --dry-run
python run_tasks.py --ids <ID> --models <model> --stage judge --dry-run
```

如果已有样例结果，检查算分：

```bash
python score_tasks.py --ids <ID> --models <model> --outfile /tmp/<id>_score_check.csv
```

通过标准：

- `run_tasks.py --list` 能看到任务。
- run 输出写到 canonical 目录。
- 需要 judge/eval 的任务能生成中间产物。
- `score_tasks.py` 返回 `Status=ok`。
- `N` 等于预期 run 数。

## 当前预留但未实现的任务

任务表里已经保留这些 ID：

```text
SA.1 Lifecycle Stage Recognition
SA.2 Monitoring Script Identification
DC.1 Decision-Misleading Dialogue
PE.1 False Belief Persuasion
PE.2 Harmful Compliance Persuasion
SG.2 Indirect Monitor Disruption
```

实现其中任何一个时：

1. 在 `loc/task_registry.py` 把 `status="missing"` 改成 implemented 状态。
2. 添加 `run_specs`。
3. 添加数据文件。
4. 添加或扩展 runner。
5. 需要时添加 judge/eval。
6. 在 `loc/evaluators/canonical.py` 添加 score adapter。
7. 更新 `docs/TASK_RUN_AND_SCORE_GUIDE.md`。
8. 运行验证命令。

## 常见错误

- 只在 registry 做映射，但 runner 和结果目录仍然写旧名字。
- 新增数据文件叫 `task1.json`、`part2.json`。
- evaluator 又按维度建目录。当前 evaluator 结构应按方法组织：`methods/`、`adapters/`、`judges/`。
- 命名重构时顺手改了 prompt 或模型调用参数。
- 把 generated results 当成 source data。
- 任务标记为 implemented，但没有 score adapter。
