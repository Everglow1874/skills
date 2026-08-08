# GaussDB SQL 参考

GaussDB 使用 **PostgreSQL 兼容**语法。生成 ETL SQL 前读本文件，照这里的风格和约定写，能避开常见方言坑。

## 目录

- [类型与常见坑](#类型与常见坑)（字段类型白名单见 `supported-column-types.md`）
- [字段长度继承规则](#字段长度继承规则)
- [数据区命名(目标表 / 持久表)](#数据区命名目标表--持久表)
- [标识符大小写(强制大写)](#标识符大小写强制大写)
- [临时表模板](#临时表模板)
- [平台变量套用(日期/增量过滤)](#平台变量套用日期增量过滤)
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

## 平台变量套用(日期/增量过滤)

日期/增量过滤按 P0 确认的**作业类型**处理:

- **P 转换作业**:用平台变量 `$ {TX_DATE}` 占位(业务日期=实例日期的前一天)。SQL 中**原样保留占位符**,不要展开成具体日期。
- **I 初始化作业**:禁用平台变量,日期用**字面量**(用户给的日期或确认值)。

示例(P 作业增量过滤):

```sql
-- 增量装载:取业务日期当天的交易
INSERT INTO tmp_daily_trade
SELECT BIZ_KEY, TX_TIME, AMOUNT
FROM FACT_TRADE
WHERE TX_DATE = '$ {TX_DATE}';
```

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
