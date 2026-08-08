# gaussdb-etl-builder 平台变量支持与作业类型判定实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 恢复 gaussdb-etl-builder 技能的内置平台变量文档（`${TX_DATE}`），在 P0 增加作业类型（I/P）判定，按作业类型决定变量策略（I 禁变量、P 用变量占位），并同步更新 evals 用例。

**Architecture:** 全部改动为文档文件：重建 `references/platform-variables.md`；在 `SKILL.md` 的 P0/P2/P3 与「关键原则回顾」按 I/P 分流变量规则；`gaussdb-sql.md` 补变量套用说明；`evals/evals.json` 更新增量用例断言并新增 I 初始化作业用例。无 Python 代码改动。

**Tech Stack:** Markdown 文档、JSON（evals）、现有 pytest（仅回归，不改）。

**Spec:** `docs/superpowers/specs/2026-08-08-gaussdb-etl-builder-platform-variables-design.md`

**环境注意：**
- pytest 必须禁用插件自动加载：`$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"`
- 用 `C:\app\anaconda3\python.exe` 跑 pytest（有 pytest 7.1.2 + openpyxl），不用 `C:\app\Python\Python310`（无 pytest）
- 验证 JSON 合法：`python -m json.tool` 或 Python 一行读取
- 平台变量占位符的正确写法是不带空格：`${TX_DATE}`；文档中统一用此写法

---

### Task 1: 重建内置平台变量文档

**Files:**
- Create: `gaussdb-etl-builder/references/platform-variables.md`

- [ ] **Step 1: 创建文件**

写入以下内容：

```markdown
# 平台变量

本技能**内置**的变量清单:技能直接读取此文件参考,由调度平台在作业运行时注入,SQL 里**原样保留占位符**。若平台后续新增变量,在此追加即可。

## 变量清单

| 变量 | 含义 |
|---|---|
| `${TX_DATE}` | 业务日期,格式 `YYYY-MM-DD`,即**实例日期的前一天**(运行日减一天) |

## 使用约定

1. **只用于 P 转换作业**。I 初始化作业禁用平台变量(见 SKILL.md P0),日期用字面量。
2. **原样保留占位符**。生成的 SQL 中 `${TX_DATE}` 保持 `$ {...}` 语法,不要展开成字面日期。
3. 需求的日期语义对应到 `${TX_DATE}`;其他格式(去横线等)后续按平台新增变量再补,不臆造变量名。
```

- [ ] **Step 2: 验证文件内容**

Run: `Select-String -Path "gaussdb-etl-builder/references/platform-variables.md" -Pattern "TX_DATE" | Measure-Object | Select-Object -ExpandProperty Count`
Expected: `1`（只出现一个变量 TX_DATE，无 TX_DATE_NODASH / RUN_DATE / MONTH_FIRST_DAY）

Run: `Select-String -Path "gaussdb-etl-builder/references/platform-variables.md" -Pattern "TX_DATE_NODASH|RUN_DATE|MONTH_FIRST_DAY"`
Expected: 无匹配行

- [ ] **Step 3: 提交**

```bash
git add gaussdb-etl-builder/references/platform-variables.md
git commit -m "docs: 重建内置平台变量文档(仅保留 TX_DATE)"
```

---

### Task 2: SKILL.md P0 增加作业类型判定、平台变量改为内置

**Files:**
- Modify: `gaussdb-etl-builder/SKILL.md`

- [ ] **Step 1: 替换 P0 的「注意」块（当前约第 47 行）**

将：

```
> 注意:本技能**不加载外挂文档**(知识文档、平台变量文档均不使用)。需求带日期/增量语义时,直接用用户给的日期或向用户确认,不要臆造变量语法。
```

替换为：

```
> 注意:本技能**不加载知识文档**;平台变量文档为**内置** `references/platform-variables.md`,直接读取参考,不向用户索要。
```

- [ ] **Step 2: 在 P0 收尾（确认数据区编码之后）追加作业类型确认步骤**

在「确认数据区编码」小节结束后、`## P1` 之前，新增一个小节：

```
4. **确认作业类型**。在进入 P1 之前,主动向用户确认,不靠猜:
   > "本次作业是 **初始化作业(I)** 还是 **转换作业(P)**?初始化作业指一次性建表并装载存量/历史数据;转换作业指周期性/按日跑的加工。"
   - **I 初始化作业**(一次性建表 + 装载存量/历史):**禁用平台变量**,日期/增量过滤一律用**字面量**或用户确认的日期。
   - **P 转换作业**(周期性/按日加工,如"每天跑""T+1""增量"):**允许平台变量**,日期/增量过滤用 `${TX_DATE}` 占位(业务日期=实例日期的前一天,见 `references/platform-variables.md`)。
```

- [ ] **Step 3: 验证 P0 改动**

Run: `Select-String -Path "gaussdb-etl-builder/SKILL.md" -Pattern "确认作业类型|初始化作业\(I\)|内置"`
Expected: 至少匹配到 `确认作业类型` 与 `初始化作业(I)` 各一次

Run: `Select-String -Path "gaussdb-etl-builder/SKILL.md" -Pattern "TX_DATE_NODASH|RUN_DATE|MONTH_FIRST_DAY"`
Expected: 无匹配行

- [ ] **Step 4: 提交**

```bash
git add gaussdb-etl-builder/SKILL.md
git commit -m "docs: SKILL.md P0 增加作业类型判定,平台变量文档改为内置"
```

---

### Task 3: SKILL.md P2 日期/增量语义按 I/P 分流

**Files:**
- Modify: `gaussdb-etl-builder/SKILL.md`

- [ ] **Step 1: 替换 P2 中的日期/增量语义段落（当前约第 84 行）**

将：

```
如果需求带日期/增量语义(如"每天跑""按交易日""增量"),在这一步要想清楚是全量还是增量装载,反映到步骤设计里。没有平台变量文档,日期用用户指定的值。
```

替换为：

```
如果需求带日期/增量语义(如"每天跑""按交易日""增量"),在这一步要想清楚是全量还是增量装载,反映到步骤设计里。日期/增量过滤按 P0 确认的**作业类型**处理:
- **I 初始化作业**:日期/增量过滤一律用**字面量**(用户给的日期或确认值),禁用平台变量。
- **P 转换作业**:日期/增量过滤用 `${TX_DATE}` 占位(业务日期=实例日期的前一天),**首次出现时向用户确认一次**变量含义(如「TX_DATE 是业务日期,即实例日期的前一天,对吗」),之后沿用。
```

- [ ] **Step 2: 验证 P2 改动**

Run: `Select-String -Path "gaussdb-etl-builder/SKILL.md" -Pattern "I 初始化作业|P 转换作业|首次出现时向用户确认"`
Expected: 匹配到这三处（注意 P0 中也有 I/P 字样，需确认 P2 小节内存在「首次出现时向用户确认」）

- [ ] **Step 3: 提交**

```bash
git add gaussdb-etl-builder/SKILL.md
git commit -m "docs: SKILL.md P2 日期/增量语义按作业类型 I/P 分流"
```

---

### Task 4: SKILL.md P3 变量套用 + 关键原则回顾补一条

**Files:**
- Modify: `gaussdb-etl-builder/SKILL.md`

- [ ] **Step 1: 在 P3「临时表 / 装载步骤 → SQL」小节末尾追加变量套用规则**

在 `INSERT INTO <目标表全名> SELECT ...` 那段之后追加：

```
**日期/增量过滤的变量套用(按 P0 作业类型)**:
- **P 转换作业**:SQL 中日期/增量过滤条件(`WHERE ...`、`>=` 等)用 `${TX_DATE}` 占位;变量首次出现时已向用户确认,后续沿用;**原样输出占位符**,不展开成字面日期。
- **I 初始化作业**:凡涉及日期/增量过滤,用**字面量**(用户给的日期或确认值),绝不用平台变量。
```

- [ ] **Step 2: 在「关键原则回顾」末尾追加一条**

将：

```
- **产物落盘**——一定写文件,并报告路径。
```

替换为：

```
- **产物落盘**——一定写文件,并报告路径。
- **作业类型决定变量策略**——P0 确认是初始化作业(I)还是转换作业(P);I 禁用平台变量用字面量,P 用 `${TX_DATE}` 占位(首次出现向用户确认)。
```

- [ ] **Step 3: 验证 P3 改动**

Run: `Select-String -Path "gaussdb-etl-builder/SKILL.md" -Pattern "变量套用|作业类型决定变量策略"`
Expected: 各匹配一次

Run: `Select-String -Path "gaussdb-etl-builder/SKILL.md" -Pattern "\$ \{TX_DATE\}"`
Expected: **无匹配**（占位符统一用不带空格的 `${TX_DATE}`，不存在带空格写法）

- [ ] **Step 4: 提交**

```bash
git add gaussdb-etl-builder/SKILL.md
git commit -m "docs: SKILL.md P3 变量套用规则与关键原则补充"
```

---

### Task 5: gaussdb-sql.md 补平台变量套用说明

**Files:**
- Modify: `gaussdb-etl-builder/references/gaussdb-sql.md`

- [ ] **Step 1: 在「临时表模板」小节末尾（顺序铁律那段之后）追加变量套用小节**

将：

```
记住顺序铁律:临时表、目标表都要在写入它们的步骤**之前**创建。
```

替换为：

```
记住顺序铁律:临时表、目标表都要在写入它们的步骤**之前**创建。

## 平台变量套用(日期/增量过滤)

日期/增量过滤按 P0 确认的**作业类型**处理:

- **P 转换作业**:用平台变量 `${TX_DATE}` 占位(业务日期=实例日期的前一天)。SQL 中**原样保留占位符**,不要展开成具体日期。
- **I 初始化作业**:禁用平台变量,日期用**字面量**(用户给的日期或确认值)。

示例(P 作业增量过滤):

```sql
-- 增量装载:取业务日期当天的交易
INSERT INTO tmp_daily_trade
SELECT BIZ_KEY, TX_TIME, AMOUNT
FROM FACT_TRADE
WHERE TX_DATE = '${TX_DATE}';
```
```

- [ ] **Step 2: 验证改动**

Run: `Select-String -Path "gaussdb-etl-builder/references/gaussdb-sql.md" -Pattern "平台变量套用|TX_DATE"`
Expected: 匹配到新增小节标题与 TX_DATE 示例

- [ ] **Step 3: 提交**

```bash
git add gaussdb-etl-builder/references/gaussdb-sql.md
git commit -m "docs: gaussdb-sql.md 补平台变量套用说明"
```

---

### Task 6: evals.json 更新增量用例断言并新增 I 初始化作业用例

**Files:**
- Modify: `gaussdb-etl-builder/evals/evals.json`

- [ ] **Step 1: 更新 eval 3 的 expected_output**

将 eval 3（id=3）的：

```
"expected_output": "SQL 用用户确认的日期做增量过滤;全量/增量语义反映到步骤设计;目标表出 Excel,临时表/装载出 SQL"
```

替换为：

```
"expected_output": "确认作业类型为 P 转换;日期/增量过滤用 ${TX_DATE} 占位且首次出现向用户确认;全量/增量语义反映到步骤设计;目标表出 Excel,临时表/装载出 SQL"
```

- [ ] **Step 2: 在 eval 6 之后新增 eval 7（I 初始化作业）**

在最后一个对象 `}` 后追加（注意把前一个对象的结尾从 `}` 改成 `},`，再插入新对象）：

```json
,
    {
      "id": 7,
      "prompt": "这是初始化作业(I):一次性把交易流水历史存量数据全部装载到一张交易明细宽表(目标表建好后装载全量历史,不是增量)。源表见附件 trade_source.sql。这是自动化端到端运行,凡需确认处默认确认并继续,直到把目标表字段定义 Excel、plan.md 和每步 SQL 写入输出目录。",
      "expected_output": "确认作业类型为 I 初始化;日期/增量过滤用字面量,SQL 中不出现平台变量占位符;目标表出 Excel,临时表/装载出 SQL",
      "files": ["inputs/trade_source.sql"]
    }
```

最终 evals.json 结构：`evals` 数组含 id 0..7 共 8 个对象，末尾对象后无多余逗号。

- [ ] **Step 3: 验证 JSON 合法**

Run: `& "C:\app\anaconda3\python.exe" -c "import json;d=json.load(open('gaussdb-etl-builder/evals/evals.json',encoding='utf-8'));print(len(d['evals']), d['evals'][-1]['id'])"`
Expected: `8 7`

Run: `Select-String -Path "gaussdb-etl-builder/evals/evals.json" -Pattern "初始化作业|TX_DATE"`
Expected: eval 7 prompt/expected 与 eval 3 expected 中含相应字样

- [ ] **Step 4: 提交**

```bash
git add gaussdb-etl-builder/evals/evals.json
git commit -m "docs: evals 更新增量用例断言并新增 I 初始化作业用例"
```

---

### Task 7: 回归验证（pytest + 全量 grep）

**Files:**
- 验证（不改代码）

- [ ] **Step 1: 跑现有 pytest 回归**

Run（PowerShell，两条一起）:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"; & "C:\app\anaconda3\python.exe" -m pytest gaussdb-etl-builder/tests/ -v
```

Expected: 7 个测试全部 PASS（`test_creates_xlsx_with_12_headers`、`test_field_rows_fill_columns`、`test_pk_row_sets_keys_and_nullable`、`test_attribute_column_defaults_empty`、`test_attribute_column_uses_passed_value`、`test_invalid_type_aborts`、`test_empty_fields_warns`）

- [ ] **Step 2: 全量 grep 一致性检查**

Run: `Select-String -Path "gaussdb-etl-builder/SKILL.md","gaussdb-etl-builder/references/gaussdb-sql.md","gaussdb-etl-builder/references/platform-variables.md" -Pattern "TX_DATE_NODASH|RUN_DATE|MONTH_FIRST_DAY"`
Expected: 无匹配行（三个被删变量不再出现）

Run: `Select-String -Path "gaussdb-etl-builder/SKILL.md" -Pattern "\$\{TX_DATE\}"`
Expected: 无匹配行（SKILL.md 正文无连续 `$ {` 写法）

- [ ] **Step 3: 更新版本号**

在 `gaussdb-etl-builder/SKILL.md` frontmatter 中，将 `version: 1.1.0` 改为 `version: 1.2.0`（功能变更，次版本号 +1）。

- [ ] **Step 4: 提交**

```bash
git add gaussdb-etl-builder/SKILL.md
git commit -m "docs: gaussdb-etl-builder 版本号升至 1.2.0"
```

---

### Task 8: 端到端验收对照设计文档

**Files:**
- 验证（不改文件，除非发现偏差）

- [ ] **Step 1: 对照验收标准逐条核对**

对照 `docs/superpowers/specs/2026-08-08-gaussdb-etl-builder-platform-variables-design.md` 第 7 节验收标准：

1. `references/platform-variables.md` 存在，只含 `${TX_DATE}` 一个变量，含使用约定 → Task 1
2. SKILL.md P0 含作业类型（I/P）询问步骤；P0 注意块声明平台变量文档为内置、知识文档不支持 → Task 2
3. SKILL.md P2/P3 按 I/P 分流变量策略：I 用字面量、P 用 `${TX_DATE}` 占位且首次出现向用户确认 → Task 3、4
4. SKILL.md 正文不出现硬编码 `$ {...}` 模板 → Task 4 Step 3 已验
5. evals.json 有 eval 7（I 初始化作业），eval 3 断言按 P 作业更新 → Task 6
6. 七个现有 pytest 测试仍然通过；evals.json 为合法 JSON → Task 7

- [ ] **Step 2: 最终提交（若有遗漏文件未提交）**

```bash
git status
```

确认工作区干净；若有未提交改动，先提交再汇报。
