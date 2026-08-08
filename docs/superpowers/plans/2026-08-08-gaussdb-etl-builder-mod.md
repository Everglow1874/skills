# gaussdb-etl-builder 技能改造实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 改造 `gaussdb-etl-builder` 技能：简化 P0、P1 加字段长度继承规则与输出目录确认、P2 加 CTE 铁律与强制确认闸门、P3 目标表产物从 SQL 改为 12 列字段定义 Excel，并同步更新引用文件与 evals。

**Architecture:** 唯一新增的可执行代码是 `scripts/generate_field_excel.py`（openpyxl 生成 .xlsx），用 TDD 先行；其余为文档重写：`SKILL.md`、`references/gaussdb-sql.md`、`assets/plan-template.md`、`evals/evals.json`，并删除两个不再使用的文件。

**Tech Stack:** Python 3.10 + openpyxl 3.1.5（本机已装）；Markdown 文档编辑。

**设计文档:** `docs/superpowers/specs/2026-08-08-gaussdb-etl-builder-mod-design.md`

---

## 文件结构

```
gaussdb-etl-builder/
├── SKILL.md                           # 重写 P0-P3（Task 4）
├── scripts/
│   ├── __init__.py                    # 新增（Task 1）
│   └── generate_field_excel.py        # 新增：12 列字段定义 Excel 生成器（Task 1）
├── tests/
│   └── test_generate_field_excel.py   # 新增：脚本 TDD 测试（Task 1）
├── references/
│   ├── gaussdb-sql.md                 # 改：去 WITH 范例，加临时表/字段长度模式，改 Worked Example（Task 3）
│   ├── supported-column-types.md      # 保留，不改
│   └── platform-variables-example.md  # 删除（Task 6）
├── assets/
│   ├── plan-template.md               # 改：加输出目录节、目标表描述、临时表说明（Task 2）
│   └── knowledge-template.md          # 删除（Task 6）
└── evals/
    └── evals.json                     # 改：删 eval 3/4，同步 0/1/2，新增 3 用例（Task 5）
```

---

### Task 1: 新增 Excel 生成器脚本（TDD）

**Files:**
- Create: `gaussdb-etl-builder/scripts/__init__.py`
- Create: `gaussdb-etl-builder/scripts/generate_field_excel.py`
- Create: `gaussdb-etl-builder/tests/test_generate_field_excel.py`

- [ ] **Step 1: 创建目录**

```bash
mkdir -p gaussdb-etl-builder/scripts gaussdb-etl-builder/tests
```

- [ ] **Step 2: 写失败测试**

创建 `gaussdb-etl-builder/tests/test_generate_field_excel.py`：

```python
import json
import subprocess
import sys
from pathlib import Path

import openpyxl
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "generate_field_excel.py"

FIELDS = json.dumps([
    {
        "english": "EXAM_NAME", "chinese": "考试名称", "type": "VARCHAR",
        "length": 100, "precision": None,
        "is_pk": False, "is_dist_key": False, "is_part_key": False,
        "nullable": "是", "default": None, "remark": "考试名称"
    },
    {
        "english": "RANK", "chinese": "排名", "type": "INT",
        "length": None, "precision": None,
        "is_pk": True, "is_dist_key": True, "is_part_key": True,
        "nullable": "否", "default": None, "remark": "排名（1-10）"
    },
])

HEADERS = ["属性", "英文名", "中文名", "数据类型", "长度", "精度",
           "主键", "分布键", "分区键", "是否允许空值", "默认值", "备注"]


def run_script(tmp_path, fields=FIELDS, table="ABCD_EXAM_TOP10_BY_SUBJECT"):
    out = tmp_path / f"目标表字段定义_{table}.xlsx"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--output", str(out),
         "--table", table, "--fields", fields],
        capture_output=True, text=True,
    )
    return result, out


def test_creates_xlsx_with_12_headers(tmp_path):
    result, out = run_script(tmp_path)
    assert result.returncode == 0, result.stderr
    assert out.exists()
    wb = openpyxl.load_workbook(out)
    ws = wb.active
    assert [c.value for c in ws[1]] == HEADERS


def test_field_rows_fill_columns(tmp_path):
    result, out = run_script(tmp_path)
    assert result.returncode == 0, result.stderr
    wb = openpyxl.load_workbook(out)
    ws = wb.active
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    assert len(rows) == 2
    assert rows[0][1] == "EXAM_NAME"   # 英文名
    assert rows[0][2] == "考试名称"      # 中文名
    assert rows[0][3] == "VARCHAR"      # 数据类型
    assert rows[0][4] == 100            # 长度
    assert rows[0][5] is None           # 精度


def test_pk_row_sets_keys_and_nullable(tmp_path):
    result, out = run_script(tmp_path)
    assert result.returncode == 0, result.stderr
    wb = openpyxl.load_workbook(out)
    ws = wb.active
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    pk_row = [r for r in rows if r[1] == "RANK"][0]
    assert pk_row[6] == "是"   # 主键
    assert pk_row[7] == "是"   # 分布键
    assert pk_row[8] == "是"   # 分区键
    assert pk_row[9] == "否"   # 是否允许空值


def test_attribute_column_defaults_empty(tmp_path):
    result, out = run_script(tmp_path)
    assert result.returncode == 0, result.stderr
    wb = openpyxl.load_workbook(out)
    ws = wb.active
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    assert all(r[0] is None for r in rows)  # 属性列默认不填


def test_attribute_column_uses_passed_value(tmp_path):
    fields = json.loads(FIELDS)
    fields[0]["attribute"] = "目标表"
    result, out = run_script(tmp_path, fields=json.dumps(fields))
    assert result.returncode == 0, result.stderr
    wb = openpyxl.load_workbook(out)
    ws = wb.active
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    assert rows[0][0] == "目标表"


def test_invalid_type_aborts(tmp_path):
    bad = json.dumps([{
        "english": "BAD", "chinese": "非法类型", "type": "JSON",
        "length": None, "precision": None,
        "is_pk": False, "is_dist_key": False, "is_part_key": False,
        "nullable": "是", "default": None, "remark": ""
    }])
    result, _ = run_script(tmp_path, fields=bad)
    assert result.returncode != 0
    assert "类型" in result.stderr


def test_empty_fields_warns(tmp_path):
    result, _ = run_script(tmp_path, fields="[]")
    assert result.returncode == 0
    assert "警告" in result.stderr or "没有字段" in result.stderr
```

- [ ] **Step 3: 运行测试验证失败**

Run: `python -m pytest gaussdb-etl-builder/tests/test_generate_field_excel.py -v`
Expected: 全部失败，报 `No such file or directory` 或 `ModuleNotFoundError`（脚本不存在）

- [ ] **Step 4: 写最小实现**

创建 `gaussdb-etl-builder/scripts/__init__.py`（内容为空）和 `gaussdb-etl-builder/scripts/generate_field_excel.py`：

```python
#!/usr/bin/env python3
"""把目标表字段定义生成 12 列 .xlsx，供平台直接导入。"""

import argparse
import json
import re
import sys
from pathlib import Path

import openpyxl
from openpyxl.styles import Font, PatternFill

WHITELIST_TYPES = {
    "VARCHAR", "CHAR", "INT", "BIGINT", "SMALLINT",
    "NUMERIC", "DECIMAL", "DATE", "TIMESTAMP",
}

HEADERS = ["属性", "英文名", "中文名", "数据类型", "长度", "精度",
           "主键", "分布键", "分区键", "是否允许空值", "默认值", "备注"]

YES = "是"
NO = "否"


def sanitize_filename(name: str) -> str:
    safe = re.sub(r'[\\/:*?"<>|]', "_", name)
    return safe[:120]


def validate_fields(fields):
    if not isinstance(fields, list) or not fields:
        print("警告:没有字段定义，将只输出表头。", file=sys.stderr)
        return
    for f in fields:
        ftype = str(f.get("type", "")).upper()
        if ftype not in WHITELIST_TYPES:
            raise ValueError(f"非法类型:{ftype}，不在白名单 {sorted(WHITELIST_TYPES)} 内")


def write_excel(output: Path, table: str, fields):
    validate_fields(fields)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = table[:31]

    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    ws.append(HEADERS)
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font

    for f in fields:
        is_pk = bool(f.get("is_pk", False))
        pk_val = YES if is_pk else NO
        ws.append([
            f.get("attribute"),               # 属性（默认不填）
            f.get("english"),
            f.get("chinese"),
            str(f.get("type", "")).upper(),
            f.get("length"),
            f.get("precision"),
            pk_val,                           # 主键
            YES if f.get("is_dist_key") else NO,  # 分布键
            YES if f.get("is_part_key") else NO,  # 分区键
            NO if is_pk else "是",             # 是否允许空值
            f.get("default"),
            f.get("remark"),
        ])

    wb.save(output)


def main():
    parser = argparse.ArgumentParser(description="生成目标表字段定义 Excel")
    parser.add_argument("--output", required=True, help="输出 .xlsx 路径")
    parser.add_argument("--table", required=True, help="目标表名（含前缀全名）")
    parser.add_argument("--fields", required=True, help="JSON 数组格式的字段定义")
    args = parser.parse_args()

    try:
        fields = json.loads(args.fields)
    except json.JSONDecodeError as e:
        print(f"错误:fields 参数不是合法 JSON:{e}", file=sys.stderr)
        sys.exit(1)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    safe_table = sanitize_filename(args.table)
    safe_output = output.parent / (sanitize_filename(output.stem) + ".xlsx")

    try:
        write_excel(safe_output, safe_table, fields)
    except ValueError as e:
        print(f"错误:{e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误:生成 Excel 失败:{e}", file=sys.stderr)
        sys.exit(1)

    print(f"已生成:{safe_output}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: 运行测试验证通过**

Run: `python -m pytest gaussdb-etl-builder/tests/test_generate_field_excel.py -v`
Expected: 7 个测试全部 PASS

- [ ] **Step 6: 手动冒烟测试**

Run:
```bash
python gaussdb-etl-builder/scripts/generate_field_excel.py \
  --output "C:\Users\everglow\AppData\Local\Temp\opencode\demo.xlsx" \
  --table "ABCD_EXAM_TOP10_BY_SUBJECT" \
  --fields "[{\"english\":\"EXAM_NAME\",\"chinese\":\"考试名称\",\"type\":\"VARCHAR\",\"length\":100,\"precision\":null,\"is_pk\":false,\"is_dist_key\":false,\"is_part_key\":false,\"nullable\":\"是\",\"default\":null,\"remark\":\"考试名称\"}]"
```
Expected: 输出 `已生成:...demo.xlsx`，用 openpyxl 打开可看到 12 列表头与 1 行数据

- [ ] **Step 7: 提交**

```bash
git add gaussdb-etl-builder/scripts/ gaussdb-etl-builder/tests/
git commit -m "feat(gaussdb-etl-builder): 新增目标表字段定义 Excel 生成器脚本"
```

---

### Task 2: 更新 plan-template.md

**Files:**
- Modify: `gaussdb-etl-builder/assets/plan-template.md`

- [ ] **Step 1: 重写 plan-template.md**

用以下内容整体替换 `gaussdb-etl-builder/assets/plan-template.md`：

```markdown
# ETL 执行计划

## 需求描述

<把用户的原始需求原样或精炼后写在这里>

## 数据区

编码：`<编码>`　Schema：`<编码>_DATA`　表名前缀：`<编码>_`

## 输出目录

`./<含前缀全名>/etl/`（如 `./ABCD_EXAM_TOP10_BY_SUBJECT/etl/`）

## 目标表

`<编码>_DATA.<编码>_<业务名>`（字段定义见 `<输出目录>/目标表字段定义_<含前缀全名>.xlsx`）

## ETL 步骤

### Step 1: <步骤名称>（临时表）

<这一步做什么的简短描述。标题里的「（临时表）」后缀仅当该步是创建临时表时才加>

输出表：`<临时表原名>`

### Step 2: <步骤名称>

<这一步做什么的简短描述。非临时表步骤（装载/建目标表）不加后缀>

输出表：`<输出表全名>`

<!--
说明(生成时删除本注释):
- 目标表不生成 CREATE TABLE SQL，改为生成「目标表字段定义_<含前缀全名>.xlsx」。
- 临时表步骤生成 CREATE TEMPORARY TABLE 语句，标题后加「（临时表）」。
- 每个步骤对应一个 stepN_<安全名>.sql 文件（临时表/装载步骤）。
- 中间结果优先拆成临时表步骤，不要用 WITH（递归 CTE 除外）。
- 步骤顺序必须保证:目标表、临时表都在写入它们的步骤之前创建。
-->
```

- [ ] **Step 2: 自检替换**

确认文件中不再出现 `is_temp_table=false` 相关旧描述、不再出现 `CREATE TABLE` 目标表模板引用。

- [ ] **Step 3: 提交**

```bash
git add gaussdb-etl-builder/assets/plan-template.md
git commit -m "docs(gaussdb-etl-builder): plan 模板加入输出目录与 Excel 产物说明"
```

---

### Task 3: 重写 references/gaussdb-sql.md

**Files:**
- Modify: `gaussdb-etl-builder/references/gaussdb-sql.md`

- [ ] **Step 1: 重写 gaussdb-sql.md**

用以下内容整体替换 `gaussdb-etl-builder/references/gaussdb-sql.md`：

```markdown
# GaussDB SQL 参考

GaussDB 使用 **PostgreSQL 兼容**语法。生成 ETL SQL 前读本文件，照这里的风格和约定写，能避开常见方言坑。

## 目录

- [类型与常见坑](#类型与常见坑)（字段类型白名单见 `supported-column-types.md`）
- [字段长度继承规则](#字段长度继承规则)
- [数据区命名(目标表 / 持久表)](#数据区命名目标表--持久表)
- [标识符大小写(强制大写)](#标识符大小写强制大写)
- [临时表模板](#临时表模板)
- [常见转换套路](#常见转换套路)
- [完整 Worked Example:各科前十名](#完整-worked-example各科前十名)

## 类型与常见坑

> **字段类型只能从 `supported-column-types.md` 白名单里选**（平台支持有限）。那份文档是类型的唯一权威来源；本节只讲选型经验与方言坑，不另立类型清单。

选型经验:短文本用 `VARCHAR(n)`（给够长度）;整数主键用 `BIGINT`;金额/分数用 `NUMERIC(p,s)`/`DECIMAL(p,s)`，绝不用浮点;仅日期用 `DATE`，带时分秒用 `TIMESTAMP`。拿不准就选语义最接近的**白名单内**类型并在 `plan.md` 注明。

常见坑:
- `VARCHAR` 一定带长度，别裸写 `VARCHAR`。
- 日期函数用 PG 风格:`CURRENT_DATE`、`date_trunc('month', d)`、`d - INTERVAL '1 day'`、`to_char(d, 'YYYY-MM')`。不要用 MySQL 的 `DATE_FORMAT`、`DATE_SUB`。
- 字符串拼接用 `||` 或 `concat()`，不要用 `+`。
- 取 Top-N 用窗口函数 `ROW_NUMBER()`，不要依赖 `LIMIT` 来做"每组前 N"。

## 字段长度继承规则

设计目标表/临时表字段时，**长度不得小于源表对应字段**，否则装载会因截断失败：

- 若目标字段只取自一张源表的某个字段，长度取源表该字段的长度（可适当放宽，不要写小）。
- 若目标字段取值来自**多个源表字段**，取这些源表字段的**最大长度**。
- `VARCHAR(n)`/`CHAR(n)` 取长度 `n`;`NUMERIC(p,s)` 的 `p`（总位数）与 `s`（小数位）都取较大者。
- 拿不准源表长度时主动问用户，不要臆造。

## 数据区命名(目标表 / 持久表)

落地的目标表和持久中间表必须建在**指定的数据区**里。用户在 P0 提供一个 **4 位数据区编码**（数据库编码，如 `ABCD`），由它推导:

- **Schema** = `<编码>_DATA`（如 `ABCD_DATA`）
- **表名前缀** = `<编码>_`（如 `ABCD_`），这个前缀**取代**普通语义前缀（不再写 `rpt_`/`dws_`）

所以目标表的全名是 `<编码>_DATA.<编码>_<业务名>`，例如业务名 `exam_top10_by_subject`、编码 `ABCD` → `ABCD_DATA.ABCD_EXAM_TOP10_BY_SUBJECT`。

**目标表不生成 `CREATE TABLE` SQL**——平台无法直接导入，改为在 P3 用 `scripts/generate_field_excel.py` 生成「目标表字段定义_<全名>.xlsx」，由平台导入建表。

**临时表例外**:`CREATE TEMPORARY TABLE` 走会话临时 schema，放不进数据区，因此**不加** `<编码>_DATA` schema、**不加** `<编码>_` 前缀，用普通名字即可。

## 标识符大小写(强制大写)

生成的 SQL 里**所有标识符一律大写**:数据区编码、schema、表名（目标表 + 临时表）、字段名。引用源表/源字段时也写成大写（GaussDB 未加引号的标识符会折叠大小写，安全）。CTE 名和表别名属局部名，保持小写即可（不影响落地的表名/字段名）。唯一例外:源库里用双引号定义的大小写敏感名，照原样保留。中文注释、步骤文件名不受影响。

## 临时表模板

**中间结果一律优先拆成临时表步骤**，不要用 `WITH`（递归 CTE 除外）。这是为了让 SQL 可逐步调试、降低维护难度（平台要求）。若某步骤确实用了 `WITH`，则每个 CTE 变量名必须同步用 `CREATE TEMPORARY TABLE` 建出对应结构，否则作业执行失败。

```sql
-- ============================================================
-- Step N: 创建临时表 <tmp_table>
-- ============================================================
CREATE TEMPORARY TABLE <tmp_table> (
    COL_A    VARCHAR(100) NOT NULL,  -- 注释
    COL_B    INT          NOT NULL,  -- 注释
    COL_C    NUMERIC(10,2)           -- 注释
);
```

记住顺序铁律:临时表、目标表都要在写入它们的步骤**之前**创建。

## 常见转换套路

> 下面的套路全部用「临时表两段式」：先 `CREATE TEMPORARY TABLE`，再 `INSERT INTO`。除非递归，不要出现 `WITH`。

**每组取前 N（窗口函数排名）**——两段式:

```sql
-- Step A: 建临时表（放排名中间结果）
CREATE TEMPORARY TABLE tmp_ranked (
    EXAM_ID     VARCHAR(50),
    SUBJECT_ID  VARCHAR(50),
    STUDENT_ID  VARCHAR(50),
    SCORE       NUMERIC(5,1),
    RN          INT
);
-- Step B: 装载排名中间结果
INSERT INTO tmp_ranked
SELECT
    t.EXAM_ID,
    t.SUBJECT_ID,
    t.STUDENT_ID,
    t.SCORE,
    ROW_NUMBER() OVER (PARTITION BY t.SUBJECT_ID ORDER BY t.SCORE DESC) AS RN
FROM SOURCE_T t;
-- Step C: 取前 N
INSERT INTO <目标表全名>
SELECT * FROM tmp_ranked WHERE RN <= 10;
```

**去重（保留每键最新一条）**——两段式:

```sql
-- Step A: 建临时表（放带行号的中间结果）
CREATE TEMPORARY TABLE tmp_dedup (
    BIZ_KEY      VARCHAR(50),
    UPDATE_TIME  TIMESTAMP,
    RN           INT
);
-- Step B: 装载
INSERT INTO tmp_dedup
SELECT
    t.BIZ_KEY,
    t.UPDATE_TIME,
    ROW_NUMBER() OVER (PARTITION BY t.BIZ_KEY ORDER BY t.UPDATE_TIME DESC) AS RN
FROM SOURCE_T t;
-- Step C: 取最新一条
INSERT INTO <目标表全名>
SELECT BIZ_KEY, UPDATE_TIME FROM tmp_dedup WHERE RN = 1;
```

**多表关联补字段（维度补齐）**:用 `INNER JOIN` 保证匹配、`LEFT JOIN` 允许缺失，按基数选择。1:N 关联注意是否会放大行数。

**按月聚合**:

```sql
INSERT INTO <目标表全名>
SELECT
    user_id,
    to_char(order_date, 'YYYY-MM') AS stat_month,
    SUM(amount) AS total_amount,
    COUNT(*)    AS order_cnt
FROM fact_order
GROUP BY user_id, to_char(order_date, 'YYYY-MM');
```

## 完整 Worked Example:各科前十名

需求:统计最后一次考试，年级里各科前十名的学生信息以及班主任信息，生成一张报表表。**假设用户提供的数据区编码为 `ABCD`**（于是 schema=`ABCD_DATA`、表名前缀=`ABCD_`）。

源表（示意）:`dim_exam`（考试维度）、`fact_exam_score`（成绩事实，含 `is_absent`）、`dim_student`、`dim_class`（含 `head_teacher`）、`dim_subject`。源表按用户给定的名字引用，不套数据区规则。

**目标表**:`ABCD_DATA.ABCD_EXAM_TOP10_BY_SUBJECT`（业务名 `EXAM_TOP10_BY_SUBJECT`）

**产物 1 — 目标表字段定义 Excel**:由 `scripts/generate_field_excel.py` 生成，12 列表头，内容示意:

| 属性 | 英文名 | 中文名 | 数据类型 | 长度 | 精度 | 主键 | 分布键 | 分区键 | 是否允许空值 | 默认值 | 备注 |
|---|---|---|---|---|---|---|---|---|---|---|---|
|  | EXAM_NAME | 考试名称 | VARCHAR | 100 |  | 否 | 否 | 否 | 是 |  | 考试名称 |
|  | SUBJECT_NAME | 科目名称 | VARCHAR | 20 |  | 否 | 否 | 否 | 是 |  | 科目名称 |
|  | RANK | 排名 | INT |  |  | 否 | 否 | 否 | 是 |  | 排名（1-10） |
|  | STUDENT_ID | 学号 | VARCHAR | 20 |  | 否 | 否 | 否 | 是 |  | 学号 |
|  | STUDENT_NAME | 学生姓名 | VARCHAR | 50 |  | 否 | 否 | 否 | 是 |  | 学生姓名 |
|  | GENDER | 性别 | VARCHAR | 4 |  | 否 | 否 | 否 | 是 |  | 性别 |
|  | CLASS_NAME | 班级名称 | VARCHAR | 50 |  | 否 | 否 | 否 | 是 |  | 班级名称 |
|  | GRADE | 年级 | VARCHAR | 20 |  | 否 | 否 | 否 | 是 |  | 年级 |
|  | SCORE | 考试得分 | NUMERIC | 5 | 1 | 否 | 否 | 否 | 是 |  | 考试得分 |
|  | HEAD_TEACHER | 班主任姓名 | VARCHAR | 50 |  | 否 | 否 | 否 | 是 |  | 班主任姓名 |

**Step 1 — 创建临时表（最后一次考试）**（`is_temp_table=true`）:

```sql
-- ============================================================
-- Step 1: 创建临时表 tmp_latest_exam
-- ============================================================
CREATE TEMPORARY TABLE tmp_latest_exam (
    EXAM_ID   VARCHAR(50)  NOT NULL,
    EXAM_NAME VARCHAR(100) NOT NULL
);
```

**Step 2 — 装载最后一次考试**（`is_temp_table=true`）:

```sql
-- ============================================================
-- Step 2: 装载临时表 tmp_latest_exam
-- ============================================================
INSERT INTO tmp_latest_exam
SELECT EXAM_ID, EXAM_NAME
FROM DIM_EXAM
ORDER BY EXAM_DATE DESC, EXAM_ID DESC
LIMIT 1;
```

**Step 3 — 创建临时表（排名中间结果）**（`is_temp_table=true`）:

```sql
-- ============================================================
-- Step 3: 创建临时表 tmp_ranked_scores
-- ============================================================
CREATE TEMPORARY TABLE tmp_ranked_scores (
    EXAM_ID    VARCHAR(50)  NOT NULL,
    SUBJECT_ID VARCHAR(50)  NOT NULL,
    STUDENT_ID VARCHAR(50)  NOT NULL,
    SCORE      NUMERIC(5,1),
    RN         INT
);
```

**Step 4 — 装载排名中间结果**（`is_temp_table=true`）:

```sql
-- ============================================================
-- Step 4: 装载临时表 tmp_ranked_scores
-- ============================================================
INSERT INTO tmp_ranked_scores
SELECT
    f.EXAM_ID,
    f.SUBJECT_ID,
    f.STUDENT_ID,
    f.SCORE,
    ROW_NUMBER() OVER (PARTITION BY f.SUBJECT_ID ORDER BY f.SCORE DESC) AS RN
FROM FACT_EXAM_SCORE f
INNER JOIN tmp_latest_exam le ON f.EXAM_ID = le.EXAM_ID
WHERE f.IS_ABSENT = 0;
```

**Step 5 — 装载目标表**（`is_temp_table=false`）:

```sql
-- ============================================================
-- Step 5: 装载目标表 ABCD_DATA.ABCD_EXAM_TOP10_BY_SUBJECT
-- ============================================================
INSERT INTO ABCD_DATA.ABCD_EXAM_TOP10_BY_SUBJECT
SELECT
    le.EXAM_NAME,
    sub.SUBJECT_NAME,
    rs.RN          AS RANK,
    stu.STUDENT_ID,
    stu.STUDENT_NAME,
    stu.GENDER,
    cls.CLASS_NAME,
    cls.GRADE,
    rs.SCORE,
    cls.HEAD_TEACHER
FROM tmp_ranked_scores rs
INNER JOIN tmp_latest_exam  le  ON rs.EXAM_ID    = le.EXAM_ID
INNER JOIN DIM_STUDENT      stu ON rs.STUDENT_ID = stu.STUDENT_ID
INNER JOIN DIM_CLASS        cls ON stu.CLASS_ID  = cls.CLASS_ID
INNER JOIN DIM_SUBJECT      sub ON rs.SUBJECT_ID = sub.SUBJECT_ID
WHERE rs.RN <= 10;
```

注意这个例子里:目标表**不生成建表 SQL**，改为字段定义 Excel;中间结果用临时表拆分（`tmp_latest_exam`、`tmp_ranked_scores`）而不是 `WITH`;临时表先用原名引用;装载目标表用 schema 全名;schema、表名、字段名全大写;字段类型全部来自白名单;排名用 `ROW_NUMBER() OVER (PARTITION BY ...)`;目标表先建（平台导入）后写（Step 5）。
```

- [ ] **Step 2: 自检替换**

确认文件中不再出现 `WITH ranked AS`、`WITH dedup AS`、`INSERT INTO ... WITH` 等旧 CTE 写法（worked example 中允许保留说明文字，但不要出现示范性的 `WITH` 主句）。

- [ ] **Step 3: 提交**

```bash
git add gaussdb-etl-builder/references/gaussdb-sql.md
git commit -m "docs(gaussdb-etl-builder): 重写 SQL 参考，临时表替代 CTE、加字段长度继承规则"
```

---

### Task 4: 重写 SKILL.md

**Files:**
- Modify: `gaussdb-etl-builder/SKILL.md`

- [ ] **Step 1: 重写 SKILL.md**

用以下内容整体替换 `gaussdb-etl-builder/SKILL.md`：

```markdown
---
name: gaussdb-etl-builder
description: >-
  把一个数据分析需求变成可执行的 GaussDB 数仓 ETL 作业:生成目标表字段定义 Excel(平台可直接导入建表)、
  临时表与清洗装载 SQL。当用户想根据需求生成数仓加工任务、规划 ETL 步骤、生成目标表字段定义、写临时表/清洗装载 SQL,
  或把若干源表加工成一张报表表/宽表时使用——即使用户没明说 "ETL" 也应触发,例如"统计各科前十名生成一张报表表"
  "把订单表和用户表加工成按月的消费宽表""根据这几张源表做一张指标汇总表"。技能以交互式引导方式工作:
  先对齐需求、定目标表结构,再定步骤计划,最后逐步生成目标表字段定义 Excel 与 SQL 并写入文件。
---

# GaussDB ETL Builder

把"分析需求"变成一套**可直接执行的 GaussDB ETL 作业**:目标表字段定义 Excel + 临时表/清洗/装载 SQL,产物落到文件里。

你的工作方式是**交互式引导**,不是一次性吐出所有东西。原因很简单:ETL 作业一旦写错(字段缺了、关联错了、临时表没先建),用户要花很大代价排查。所以你要分阶段推进,在每个关键判断点停下来让用户确认,确认后再往下走。这比"猜一个完整答案"可靠得多。

## 工作流总览

按四个阶段推进。**P1、P2 是确认闸门,未经用户确认不要跨过去。**

1. **P0 开场** —— 对齐需求、收集源表结构、确认数据区编码
2. **P1 定目标表** —— 提出目标表名与字段(含长度继承规则)、确认输出目录,**停下等确认**
3. **P2 定步骤计划** —— 规划完整 ETL 步骤(临时表拆分,不用 WITH),**强制输出详细计划,停下等确认**
4. **P3 生成产物并落盘** —— 目标表生成字段定义 Excel,临时表/装载逐步生成可执行 SQL,写 plan.md

用户在任意阶段改了需求,就回到对应阶段重新推导,别将错就错往下走。

---

## P0 开场:把上下文备齐

在动手设计之前,先把三样东西备齐。缺什么就**主动问用户**——你不能凭空知道源表长什么样,猜字段是 ETL 出错的头号原因。

1. **复述需求**。用一两句话把你对需求的理解说回给用户,确认没跑偏。

2. **收集源表结构**。生成 SQL 必须知道源表的真实字段。如果用户没提供,主动索要:
   > "请把相关源表的建表语句或字段清单贴给我(表名、字段名、类型、长度、注释)。"
   拿到后,记住每张表有哪些字段、类型、长度、含义。字段名或长度不确定时宁可问,不要臆造。

3. **确认数据区编码**。目标表必须建在指定的数据区里,这是平台的硬性命名规则。向用户索要 **4 位数据区编码**(即数据库编码,如 `ABCD`)。由它推导两样东西:
   - **Schema** = `<编码>_DATA`(如 `ABCD_DATA`)
   - **表名前缀** = `<编码>_`(如 `ABCD_`)——这个前缀**取代**普通的语义前缀,不要再额外写 `rpt_`/`dws_` 等。

   于是所有**落地的目标表 / 持久中间表**都用 schema 限定的全名创建和引用:`<编码>_DATA.<编码>_<业务名>`(如 `ABCD_DATA.ABCD_EXAM_TOP10_BY_SUBJECT`)。用户没给编码时必须先问到,别自己编一个。编码统一转**大写**。(临时表不受 schema/前缀约束,见 P3。)

> 注意:本技能**不加载外挂文档**(知识文档、平台变量文档均不使用)。需求带日期/增量语义时,直接用用户给的日期或向用户确认,不要臆造变量语法。

---

## P1 定目标表(确认闸门)

分析需求,推导**目标表**应该长什么样,然后**停下来让用户确认**。

提出:
- 目标表名:用 **schema 限定的全名** `<编码>_DATA.<编码>_<业务名>`(如 `ABCD_DATA.ABCD_EXAM_TOP10_BY_SUBJECT`)。`<编码>_` 前缀取代普通语义前缀(不再写 `rpt_` 等)。
- 字段清单:每个字段给出**名称、类型、长度、注释**。字段名用**大写**;类型只能从 `references/supported-column-types.md` 的白名单里选。
- **字段长度继承规则(强制)**:目标表/临时表字段的**长度不得小于**对应源表字段的长度。若同一目标字段取值来自**多个源表字段**,取**最大的源表字段长度**。对 `VARCHAR(n)`/`CHAR(n)` 取长度 `n`;对 `NUMERIC(p,s)`,`p` 与 `s` 都取较大者。拿不准源表长度时主动问,不臆造。详见 `references/gaussdb-sql.md` 的「字段长度继承规则」。
- **输出目录**:和用户确认产物输出目录,默认 `./<含前缀全名>/etl/`(如 `./ABCD_EXAM_TOP10_BY_SUBJECT/etl/`),目录不存在就创建,用户可改。

清晰地展示给用户(用表格或字段列表),然后明确征求确认:
> "以上是我设计的目标表结构,确认无误我就继续规划 ETL 步骤;需要增删改字段或调整输出目录请直接说。"

**用户确认前不要进入 P2。** 这一步定错了,后面所有 SQL 都白做。

---

## P2 定步骤计划(强制确认闸门)

目标表确认后,规划**完整的 ETL 执行步骤**,**强制输出详细计划,等用户逐项确认**后才可执行。

一个完整的计划必须把下面这些显式拆成有序步骤:

1. **临时表步骤**(`is_temp_table=true`):中间结果**优先拆成临时表**。
2. **清洗 / 转换 / 装载步骤**:真正把数据写进目标表(或临时表)。
3. **目标表**在 P1 已定,不需要建表步骤(字段定义由 Excel 生成)。

**CTE 铁律**:
- **铁律 1(优先临时表)**:除非需要**递归 CTE**,否则不要用 `WITH`(公用表表达式)定义中间结果;改为「建临时表」+「装载」多步骤。这是为了让 SQL 可逐步调试、降低维护难度。
- **铁律 2(用 WITH 必须建对应临时表)**:若某步骤确实使用了 `WITH`,则 CTE 中每个 CTE 变量名指向的临时表结构,必须同步用 `CREATE TEMPORARY TABLE` 创建出来(平台要求,否则作业执行失败)。

**顺序铁律**:所有临时表和目标表,必须在任何写入它们的步骤**之前**创建。先建后写,别让某一步写一张还不存在的表。

如果需求带日期/增量语义(如"每天跑""按交易日""增量"),在这一步要想清楚是全量还是增量装载,反映到步骤设计里。没有平台变量文档,日期用用户指定的值。

把计划展示给用户,每步给出:序号、名称、是否临时表、输出表、一句话描述、涉及的字段与关联键。然后征求确认:
> "这是完整的 ETL 步骤计划,请逐项核对。确认无误后我会开始生成目标表字段定义 Excel 与逐步生成 SQL;需要调整请直接指出。"

**用户确认前不要进入 P3。**

---

## P3 生成产物并落盘

> **生成 SQL 之前,先读 `references/gaussdb-sql.md` 和 `references/supported-column-types.md`。** 前者有 GaussDB 的临时表模板、窗口函数/去重/JOIN 等转换套路、字段长度继承规则、标识符大小写规则,以及一个完整 worked example;后者是平台**允许的字段类型白名单**。照着它们的风格写,能避免方言坑和不支持的类型。

按确认的计划**逐步**生成产物,一步一个文件,全部写入 P1 确认的输出目录。

**目标表 → 字段定义 Excel**:
- 用 `scripts/generate_field_excel.py` 生成 `.xlsx`,文件名为 `目标表字段定义_<含前缀全名>.xlsx`。
- **12 列表头**:`属性 | 英文名 | 中文名 | 数据类型 | 长度 | 精度 | 主键 | 分布键 | 分区键 | 是否允许空值 | 默认值 | 备注`。
- 填写规则:**属性列默认不填**(除非用户有特殊说明);数据类型列只写类型名(如 `VARCHAR`、`NUMERIC`),长度/精度写到对应列;**主键字段**同时为主键/分布键/分区键(= `是`),允许空值 = `否`;**非主键字段**允许空值 = `是`。
- 生成后展示路径与列内容,等用户确认 Excel 无误。

**临时表 / 装载步骤 → SQL**:
- 临时表步骤:输出 `CREATE TEMPORARY TABLE`;**临时表不加数据区 schema、不加 `<编码>_` 前缀**——GaussDB 临时表走会话临时 schema,放不进数据区。
- 清洗/装载步骤:输出 `INSERT INTO <目标表全名> SELECT ...` 等真正写入数据的语句;所有对目标表的引用都带 schema 限定,临时表则用其原名引用。

**标识符大写(强制)**:生成的 SQL 里所有标识符——数据区编码、schema、表名(目标表 + 临时表)、字段名——一律**大写**。引用源表/源字段时也写成大写(GaussDB 未加引号的标识符会折叠大小写,安全)。唯一例外:源库里用双引号定义的大小写敏感标识符,照原样保留。中文注释、步骤文件名不受此规则影响。

### 写文件(必须)

产物一定要写进 P1 确认的输出目录,不要只在对话里贴代码:

- **每步一个 SQL 文件**(临时表/装载步骤):`step<序号>_<安全名>.sql`,UTF-8。
  - 安全名:把步骤名里非 `[a-zA-Z0-9_ 中文]` 的字符替换成 `_`,超过 64 字符截断。
  - 例:`step1_创建临时表tmp_latest_exam.sql`、`step5_装载目标表.sql`
- **一个 `plan.md`**:执行计划文档,结构见 `assets/plan-template.md`。
- **一个 `目标表字段定义_<含前缀全名>.xlsx`**:目标表字段定义。

全部写完后,汇报你写了哪些文件(路径列出来),并让用户确认目标表字段定义 Excel 与 SQL 无误。

---

## 关键原则回顾

- **缺信息就问,别猜**——尤其是源表字段、长度、关联键,以及 **4 位数据区编码**。
- **闸门不能跳**——P1、P2 必须等用户确认;P2 要强制输出详细计划。
- **数据区命名**——目标表/持久表用 `<编码>_DATA.<编码>_<业务名>` 全名,`<编码>_` 取代语义前缀;临时表例外。
- **字段长度继承**——目标表/临时表字段长度 ≥ 源表;多源取最大。
- **标识符全大写**——数据区编码、schema、表名、字段名在 SQL 里一律大写;中文注释和文件名不受影响。
- **字段类型走白名单**——列类型只能取自 `references/supported-column-types.md`。
- **先建后写**——临时表先于写入步骤创建。
- **少用 WITH**——中间结果优先临时表;非递归不用 WITH;用 WITH 必须建对应临时表。
- **目标表产物是 Excel**——不生成建表 SQL,生成字段定义 Excel 供平台导入。
- **SQL 必须可执行**——每个 SQL 文件都是完整的、能直接跑的 GaussDB SQL。
- **产物落盘**——一定写文件,并报告路径。
```

- [ ] **Step 2: 提交**

```bash
git add gaussdb-etl-builder/SKILL.md
git commit -m "docs(gaussdb-etl-builder): 重写 SKILL.md，简化 P0、加字段长度/CTE 铁律、目标表产物改 Excel"
```

---

### Task 5: 更新 evals.json

**Files:**
- Modify: `gaussdb-etl-builder/evals/evals.json`

- [ ] **Step 1: 重写 evals.json**

用以下内容整体替换 `gaussdb-etl-builder/evals/evals.json`：

```json
{
  "skill_name": "gaussdb-etl-builder",
  "evals": [
    {
      "id": 0,
      "prompt": "我要统计最近一次考试,年级里各科前十名的学生信息以及班主任信息,生成一张报表表。源表结构见附件 exam_source_tables.sql。请走完整流程生成 ETL 作业。这是自动化端到端运行,流程中凡是需要我确认的地方默认确认并继续,直到把目标表字段定义 Excel、plan.md 和每步 SQL 写入输出目录。",
      "expected_output": "写出目标表字段定义 .xlsx + plan.md + 分步 SQL;目标表不生成建表 SQL;Top-N 用 ROW_NUMBER 窗口函数;GaussDB 语法",
      "files": ["inputs/exam_source_tables.sql"]
    },
    {
      "id": 1,
      "prompt": "把订单表和用户表加工成一张按月的用户消费宽表(每个用户每个自然月的消费总金额、订单数、所在城市)。源表结构见附件 orders_users.sql。这是自动化端到端运行,凡需确认处默认确认并继续,直到把目标表字段定义 Excel、plan.md 和每步 SQL 写入输出目录。",
      "expected_output": "按用户+月份粒度宽表;to_char/date_trunc 按月聚合;user_id JOIN;目标表出 Excel,临时表/装载出 SQL;先建后写",
      "files": ["inputs/orders_users.sql"]
    },
    {
      "id": 2,
      "prompt": "帮我把销售明细表加工成一张区域月度销售汇总表,生成 ETL 作业并写入输出目录。",
      "expected_output": "主动索要源表结构,不臆造字段直接产出 SQL;目标表生成字段定义 Excel",
      "files": []
    },
    {
      "id": 3,
      "prompt": "这是每天 T+1 跑的增量作业:把交易流水表按天增量汇总成一张每日交易汇总表(按日期+渠道统计交易金额和笔数)。源表见附件 trade_source.sql。这是自动化端到端运行,凡需确认处默认确认并继续,直到把目标表字段定义 Excel、plan.md 和每步 SQL 写入输出目录。",
      "expected_output": "SQL 用用户确认的日期做增量过滤;全量/增量语义反映到步骤设计;目标表出 Excel,临时表/装载出 SQL",
      "files": ["inputs/trade_source.sql"]
    },
    {
      "id": 4,
      "prompt": "基于源表 exam_source_tables.sql,生成一张『各班级各科平均分』报表表的 ETL 作业。注意:平均分字段来自多张源表的数值字段,目标字段长度必须不小于任一源表字段长度。这是自动化端到端运行,凡需确认处默认确认并继续,直到把目标表字段定义 Excel、plan.md 和每步 SQL 写入输出目录。",
      "expected_output": "目标字段长度 = MAX(源表字段长度);剔除缺考;目标表出 Excel,临时表/装载出 SQL",
      "files": ["inputs/exam_source_tables.sql"]
    },
    {
      "id": 5,
      "prompt": "把订单明细表加工成一张用户 VIP 等级汇总表,要求:所有中间结果必须用临时表拆分,不要用 WITH(公用表表达式),除非需要递归。源表见附件 orders_users.sql。这是自动化端到端运行,凡需确认处默认确认并继续,直到把目标表字段定义 Excel、plan.md 和每步 SQL 写入输出目录。",
      "expected_output": "SQL 不含 WITH;中间结果均用 CREATE TEMPORARY TABLE 拆分;目标表出 Excel;若出现 WITH 则每个 CTE 名有对应临时表",
      "files": ["inputs/orders_users.sql"]
    },
    {
      "id": 6,
      "prompt": "统计各科前十名并生成报表表(源表见 exam_source_tables.sql)。请生成目标表字段定义 Excel。这是自动化端到端运行,凡需确认处默认确认并继续。",
      "expected_output": "生成 12 列表头的 .xlsx(属性|英文名|中文名|数据类型|长度|精度|主键|分布键|分区键|是否允许空值|默认值|备注);属性列默认不填;主键字段三列均为'是';非主键允许空值为'是'",
      "files": ["inputs/exam_source_tables.sql"]
    }
  ]
}
```

- [ ] **Step 2: 校验 JSON**

Run: `python -m json.tool gaussdb-etl-builder/evals/evals.json > $null`
Expected: 无输出、exit code 0（JSON 合法）

- [ ] **Step 3: 提交**

```bash
git add gaussdb-etl-builder/evals/evals.json
git commit -m "test(gaussdb-etl-builder): 更新 evals，覆盖字段长度继承/CTE 铁律/Excel 产物"
```

---

### Task 6: 删除废弃文件

**Files:**
- Delete: `gaussdb-etl-builder/references/platform-variables-example.md`
- Delete: `gaussdb-etl-builder/assets/knowledge-template.md`

- [ ] **Step 1: 删除文件**

```bash
git rm gaussdb-etl-builder/references/platform-variables-example.md gaussdb-etl-builder/assets/knowledge-template.md
```

- [ ] **Step 2: 确认全仓库不再引用这两个文件名**

Run: `rg -n "platform-variables-example|knowledge-template|知识文档|平台变量文档" gaussdb-etl-builder`
Expected: 无匹配（或仅剩注释性提及，若有则顺手清理 SKILL.md/plan-template.md 里的残留引用）

- [ ] **Step 3: 提交**

```bash
git commit -m "chore(gaussdb-etl-builder): 移除废弃的外挂文档参考与模板"
```

---

### Task 7: 端到端验证

**Files:**
- Test: `gaussdb-etl-builder/tests/test_generate_field_excel.py`（已有）

- [ ] **Step 1: 跑脚本测试**

Run: `python -m pytest gaussdb-etl-builder/tests/test_generate_field_excel.py -v`
Expected: 7 个测试全部 PASS

- [ ] **Step 2: 校验所有 JSON**

Run:
```bash
python -m json.tool gaussdb-etl-builder/evals/evals.json > $null
```
Expected: exit code 0

- [ ] **Step 3: 对照设计文档逐条验收**

对照 `docs/superpowers/specs/2026-08-08-gaussdb-etl-builder-mod-design.md` 第 11 节验收标准逐条确认：

1. SKILL.md P0 不再询问外挂文档 → grep `外挂` 应无匹配
2. P1 字段长度继承规则 → grep `字段长度继承` 应出现在 SKILL.md 与 gaussdb-sql.md
3. P1 输出目录默认 `./<含前缀全名>/etl/` → grep `etl/` 出现在 SKILL.md 与 plan-template.md
4. P2 强制确认闸门 → grep `请逐项核对` 出现在 SKILL.md
5. P2 CTE 铁律 → grep `铁律` 出现在 SKILL.md 与 gaussdb-sql.md
6. P3 目标表出 Excel → grep `generate_field_excel` 出现在 SKILL.md;12 列表头在脚本与 SKILL.md 一致
7. evals 覆盖新规则 → 确认 eval 4/5/6 存在

Run:
```bash
rg -n "外挂" gaussdb-etl-builder/SKILL.md
rg -n "字段长度继承" gaussdb-etl-builder/SKILL.md gaussdb-etl-builder/references/gaussdb-sql.md
rg -n "请逐项核对" gaussdb-etl-builder/SKILL.md
rg -n "generate_field_excel" gaussdb-etl-builder/SKILL.md
rg -n "属性 \| 英文名" gaussdb-etl-builder/scripts/generate_field_excel.py gaussdb-etl-builder/SKILL.md
```
Expected: 第一条无输出;其余均有匹配

- [ ] **Step 4: 提交（若有遗留改动）**

```bash
git status
# 若工作区干净则无需提交;若有遗漏改动则 add + commit
```

- [ ] **Step 5: 汇报完成**

向用户汇报:改动文件清单、验收结果、下一步可运行 evals 或交给用户实测。
