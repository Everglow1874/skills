# skills

可复用工作流 Skills 集合，用于让 Agent 在执行特定任务时加载对应的专业化指导。

## 仓库结构

```
skills/
├── gaussdb-etl-builder/   # GaussDB 数仓 ETL 作业生成
├── skill-creator/         # 技能创建、评估与优化
├── docs/                  # 设计与实施计划文档
└── LICENSE                # Apache License 2.0
```

## 技能清单

| 技能 | 版本 | 用途 |
|---|---|---|
| [gaussdb-etl-builder](./gaussdb-etl-builder/SKILL.md) | 1.1.0 | 把数据分析需求变成可执行的 GaussDB 数仓 ETL 作业：目标表字段定义 Excel（平台可直接导入建表）+ 临时表与清洗装载 SQL |
| [skill-creator](./skill-creator/SKILL.md) | 1.0.0 | 创建新技能、修改优化已有技能、运行评估与基准测试、优化技能触发描述 |

## 使用方式

将需要的技能目录复制到你的项目或全局技能目录，例如：

```bash
# 以 gaussdb-etl-builder 为例
cp -r gaussdb-etl-builder /path/to/your/project/.claude/skills/
```

随后在对话中按该技能 `SKILL.md` 的指引触发即可。

## 技能开发

本项目使用 [superpowers](https://github.com/obra/superpowers) 的开发流程管理技能迭代：

- 需求设计文档：`docs/superpowers/specs/`
- 实施计划：`docs/superpowers/plans/`

## 测试

Excel 生成器等可执行脚本带单元测试：

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest gaussdb-etl-builder/tests/ -v
```

## 许可证

[Apache License 2.0](./LICENSE)
