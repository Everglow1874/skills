# gaussdb-etl-builder 装载排序规则设计

日期：2026-08-08
状态：已确认（方案 A）

## 1. 背景与目标

`gaussdb-etl-builder` 生成的装载 SQL 目前不带 `ORDER BY`，目标表数据按自然顺序落盘，可读性差、不利于按索引查询。需要为所有装载步骤增加**默认排序**规则：

- 为可读性：存入目标表的数据有序，人工查看结果更直观。
- 为性能：按主键排序利于查询走索引。

目标：SKILL.md 增加装载排序规则；gaussdb-sql.md 的示例同步带 `ORDER BY`；evals 断言覆盖；demo 验证点更新；版本号升至 1.3.0。

范围约束：纯文档改动，不改 `scripts/`、`tests/` 代码。

## 2. 排序规则（核心）

对所有**写数据的装载步骤**（`INSERT INTO ... SELECT ...`）强制执行：

1. **默认按目标表主键升序**：主键取自该步骤装载的目标表（目标表或临时表）的主键字段；多个主键按字段顺序依次排。
2. **无主键则不排序**：目标表/临时表没有主键字段时，不加 `ORDER BY`（本例中目标表必有主键，普通临时表多无主键）。
3. **用户特殊要求优先**：若用户指定排序字段或升降序（如"按交易日期倒序"），按用户要求写，并在 P2 步骤计划/plan.md 中注明。

## 3. 改动文件

### 3.1 `gaussdb-etl-builder/SKILL.md`

**P3「临时表 / 装载步骤 → SQL」小节**（在现有 3 条 bullet 后）追加：

```markdown
**装载排序规则(强制)**:所有写数据的装载步骤(`INSERT INTO ... SELECT ...`)末尾加 `ORDER BY`,保证结果可读、利于查询索引:
- **默认按目标表主键升序**:主键取自该步骤装载的目标表(目标表或临时表)的主键字段;多个主键按字段顺序依次排。
- **无主键则不排序**:目标表/临时表没有主键字段时,不加 `ORDER BY`(本例中目标表必有主键,普通临时表多无主键)。
- **用户特殊要求优先**:若用户指定排序字段或升降序(如"按交易日期倒序"),按用户要求写,并在 P2 步骤计划/plan.md 中注明。
```

**「关键原则回顾」**追加一条：

```markdown
- **装载必排序**——`INSERT` 装载步骤按主键升序 `ORDER BY`,无主键不排。
```

### 3.2 `gaussdb-etl-builder/references/gaussdb-sql.md`

1. **Worked Example Step 5（装载目标表）**：`WHERE rs.RN <= 10;` 改为：

```sql
WHERE rs.RN <= 10
ORDER BY rs.RN, sub.SUBJECT_NAME;
```

2. **「按月聚合」示例（写入目标表）**：`GROUP BY user_id, to_char(order_date, 'YYYY-MM');` 后加 `ORDER BY USER_ID, STAT_MONTH;`

3. **新增小节 `## 装载排序规则`**（放「常见转换套路」之前或之后，与 SKILL.md 三条一致）：

```markdown
## 装载排序规则

所有写数据的装载步骤(`INSERT INTO ... SELECT ...`)末尾加 `ORDER BY`,保证结果可读、利于查询索引:

- **默认按目标表主键升序**:主键取自该步骤装载的目标表(目标表或临时表)的主键字段;多个主键按字段顺序依次排。
- **无主键则不排序**:目标表/临时表没有主键字段时,不加 `ORDER BY`(目标表必有主键,普通临时表多无主键)。
- **用户特殊要求优先**:用户指定排序字段或升降序时按用户要求写,并在 plan.md 注明。
```

4. **TOC** 补 `- [装载排序规则](#装载排序规则)`，位置与文档内小节顺序一致。

### 3.3 `gaussdb-etl-builder/evals/evals.json`

含装载步骤的用例 `expected_output` 追加排序断言：

| eval | 追加断言 |
|---|---|
| 0 | 装载 `ORDER BY` 主键(RANK 或 STUDENT_ID) |
| 1 | 装载 `ORDER BY USER_ID, STAT_MONTH` |
| 3 | 装载 `ORDER BY` 目标表主键 |
| 4 | 装载 `ORDER BY` 主键 |
| 5 | 装载 `ORDER BY` 主键 |
| 7 | 装载 `ORDER BY` 主键 |

eval 2（索要源表）与 eval 6（仅 Excel）无装载步骤，不补。

### 3.4 `gaussdb-etl-builder/demo/README.md`

场景一（P）与场景二（I）的「预期验证点」各补一条：

- 场景一：装载 SQL 末尾含 `ORDER BY` 目标表主键。
- 场景二：装载 SQL 末尾含 `ORDER BY` 目标表主键。

### 3.5 版本号

`SKILL.md` frontmatter `version: 1.2.0` → `1.3.0`。

## 4. 验收标准

1. SKILL.md P3 含「装载排序规则(强制)」；关键原则回顾含「装载必排序」。
2. gaussdb-sql.md Worked Example 装载步骤、按月聚合示例带 `ORDER BY`；含 `## 装载排序规则` 小节及 TOC 条目。
3. evals 中 eval 0/1/3/4/5/7 的 expected_output 含排序断言；eval 2/6 不含（无装载步骤）。
4. 文档中 `$ {TX_DATE}` 保持带空格写法，无连续 `${TX_DATE}`。
5. 版本号升至 1.3.0。
6. 现有 7 个 pytest 测试仍然通过。
