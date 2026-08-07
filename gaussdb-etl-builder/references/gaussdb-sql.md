# GaussDB SQL 参考

GaussDB 使用 **PostgreSQL 兼容**语法。生成 ETL SQL 前读本文件,照这里的风格和约定写,能避开常见方言坑。

## 目录

- [类型与常见坑](#类型与常见坑)(字段类型白名单见 `supported-column-types.md`)
- [数据区命名(目标表 / 持久表)](#数据区命名目标表--持久表)
- [标识符大小写(强制大写)](#标识符大小写强制大写)
- [建表模板](#建表模板)
- [临时表模板](#临时表模板)
- [常见转换套路](#常见转换套路)
- [完整 Worked Example:各科前十名](#完整-worked-example各科前十名)

## 类型与常见坑

> **字段类型只能从 `supported-column-types.md` 白名单里选**(平台支持有限)。那份文档是类型的唯一权威来源;本节只讲选型经验与方言坑,不另立类型清单。

选型经验:短文本用 `VARCHAR(n)`(给够长度);整数主键用 `BIGINT`;金额/分数用 `NUMERIC(p,s)`/`DECIMAL(p,s)`,绝不用浮点;仅日期用 `DATE`,带时分秒用 `TIMESTAMP`。拿不准就选语义最接近的**白名单内**类型并在 `plan.md` 注明。

常见坑:
- `VARCHAR` 一定带长度,别裸写 `VARCHAR`。
- 日期函数用 PG 风格:`CURRENT_DATE`、`date_trunc('month', d)`、`d - INTERVAL '1 day'`、`to_char(d, 'YYYY-MM')`。不要用 MySQL 的 `DATE_FORMAT`、`DATE_SUB`。
- 字符串拼接用 `||` 或 `concat()`,不要用 `+`。
- 取 Top-N 用窗口函数 `ROW_NUMBER()`,不要依赖 `LIMIT` 来做"每组前 N"。

## 数据区命名(目标表 / 持久表)

落地的目标表和持久中间表必须建在**指定的数据区**里。用户在 P0 提供一个 **4 位数据区编码**(数据库编码,如 `ABCD`),由它推导:

- **Schema** = `<编码>_DATA`(如 `ABCD_DATA`)
- **表名前缀** = `<编码>_`(如 `ABCD_`),这个前缀**取代**普通语义前缀(不再写 `rpt_`/`dws_`)

所以目标表的全名是 `<编码>_DATA.<编码>_<业务名>`,例如业务名 `exam_top10_by_subject`、编码 `ABCD` → `ABCD_DATA.ABCD_exam_top10_by_subject`。创建和引用都用这个 schema 限定全名。

**临时表例外**:`CREATE TEMPORARY TABLE` 走会话临时 schema,放不进数据区,因此**不加** `<编码>_DATA` schema、**不加** `<编码>_` 前缀,用普通名字即可。

## 标识符大小写(强制大写)

生成的 SQL 里**所有标识符一律大写**:数据区编码、schema、表名(目标表 + 临时表)、字段名。引用源表/源字段时也写成大写(GaussDB 未加引号的标识符会折叠大小写,安全)。CTE 名和表别名属局部名,保持小写即可(不影响落地的表名/字段名)。唯一例外:源库里用双引号定义的大小写敏感名,照原样保留。中文注释、步骤文件名不受影响。

> 下面《常见转换套路》里的占位片段为方便阅读用了小写示意(如 `group_col`),但你**实际产出时必须全大写**。本文件的 worked example 即按大写规范书写,以它为准。

## 建表模板

目标表创建步骤(`is_temp_table=false`)用这个形态——表名带数据区 schema 限定,标识符全大写。字段后用 `--` 行内注释写中文口径,可读性好:

```sql
-- ============================================================
-- Step 1: 创建目标表 <编码>_DATA.<编码>_<业务名>
-- ============================================================
CREATE TABLE IF NOT EXISTS <编码>_DATA.<编码>_<业务名> (
    COL_A    VARCHAR(100) NOT NULL,  -- 注释
    COL_B    INT          NOT NULL,  -- 注释
    COL_C    DECIMAL(5,1),           -- 注释
    COL_D    VARCHAR(50)             -- 注释
);
```

可选:GaussDB(DWS)分布式形态支持 `DISTRIBUTE BY HASH(col)` 指定分布列。仅当用户明确要求或源表有明显分布键时才加,否则保持简单,省略让其走默认分布。

```sql
CREATE TABLE IF NOT EXISTS <编码>_DATA.<编码>_<业务名> (
    ...
) DISTRIBUTE BY HASH (id);
```

## 临时表模板

仅在确实需要中间结果落地时使用(`is_temp_table=true`)。能用 `WITH` CTE 在一条语句里算完的,就不要建临时表。

```sql
-- ============================================================
-- Step N: 创建临时表 <tmp_table>
-- ============================================================
CREATE TEMPORARY TABLE <tmp_table> (
    ...
);
```

记住顺序铁律:临时表、目标表都要在写入它们的步骤**之前**创建。

## 常见转换套路

**每组取前 N(窗口函数排名)**:
```sql
WITH ranked AS (
    SELECT
        t.*,
        ROW_NUMBER() OVER (PARTITION BY group_col ORDER BY sort_col DESC) AS rn
    FROM source_t t
)
SELECT * FROM ranked WHERE rn <= 10;
```

**去重(保留每键最新一条)**:
```sql
WITH dedup AS (
    SELECT
        t.*,
        ROW_NUMBER() OVER (PARTITION BY biz_key ORDER BY update_time DESC) AS rn
    FROM source_t t
)
SELECT * FROM dedup WHERE rn = 1;
```

**多表关联补字段(维度补齐)**:用 `INNER JOIN` 保证匹配、`LEFT JOIN` 允许缺失,按基数选择。1:N 关联注意是否会放大行数。

**按月聚合**:
```sql
SELECT
    user_id,
    to_char(order_date, 'YYYY-MM') AS stat_month,
    SUM(amount) AS total_amount,
    COUNT(*)    AS order_cnt
FROM fact_order
GROUP BY user_id, to_char(order_date, 'YYYY-MM');
```

## 完整 Worked Example:各科前十名

需求:统计最后一次考试,年级里各科前十名的学生信息以及班主任信息,生成一张报表表。**假设用户提供的数据区编码为 `ABCD`**(于是 schema=`ABCD_DATA`、表名前缀=`ABCD_`)。

源表(示意):`dim_exam`(考试维度)、`fact_exam_score`(成绩事实,含 `is_absent`)、`dim_student`、`dim_class`(含 `head_teacher`)、`dim_subject`。源表按用户给定的名字引用,不套数据区规则。

**目标表**:`ABCD_DATA.ABCD_EXAM_TOP10_BY_SUBJECT`(业务名 `EXAM_TOP10_BY_SUBJECT`,`ABCD_` 前缀取代了 `rpt_`)

**Step 1 — 创建目标表**(`is_temp_table=false`,字段类型取自《支持的字段类型》白名单,标识符全大写):
```sql
-- ============================================================
-- Step 1: 创建目标表 ABCD_DATA.ABCD_EXAM_TOP10_BY_SUBJECT
-- ============================================================
CREATE TABLE IF NOT EXISTS ABCD_DATA.ABCD_EXAM_TOP10_BY_SUBJECT (
    EXAM_NAME    VARCHAR(100) NOT NULL,  -- 考试名称
    SUBJECT_NAME VARCHAR(20)  NOT NULL,  -- 科目名称
    RANK         INT          NOT NULL,  -- 排名（1-10）
    STUDENT_ID   VARCHAR(20)  NOT NULL,  -- 学号
    STUDENT_NAME VARCHAR(50),            -- 学生姓名
    GENDER       VARCHAR(4),             -- 性别
    CLASS_NAME   VARCHAR(50),            -- 班级名称
    GRADE        VARCHAR(20),            -- 年级
    SCORE        DECIMAL(5,1),           -- 考试得分
    HEAD_TEACHER VARCHAR(50)             -- 班主任姓名
);
```

**Step 2 — 加载各科前十名学生数据**(`is_temp_table=false`,用 CTE 一条语句算完,无需临时表):
```sql
-- ============================================================
-- Step 2: 加载各科前十名学生数据
-- ============================================================
INSERT INTO ABCD_DATA.ABCD_EXAM_TOP10_BY_SUBJECT
WITH
-- 2.1 定位最后一次考试（按考试日期降序 + EXAM_ID 降序取第一条）
latest_exam AS (
    SELECT EXAM_ID, EXAM_NAME
    FROM DIM_EXAM
    ORDER BY EXAM_DATE DESC, EXAM_ID DESC
    LIMIT 1
),
-- 2.2 仅取该次考试且非缺考的成绩，按科目分区、得分降序排名
ranked_scores AS (
    SELECT
        f.EXAM_ID,
        f.SUBJECT_ID,
        f.STUDENT_ID,
        f.SCORE,
        ROW_NUMBER() OVER (PARTITION BY f.SUBJECT_ID ORDER BY f.SCORE DESC) AS rn
    FROM FACT_EXAM_SCORE f
    INNER JOIN latest_exam le ON f.EXAM_ID = le.EXAM_ID
    WHERE f.IS_ABSENT = 0
)
-- 2.3 取排名 ≤ 10，关联维度补齐字段后写入目标表
SELECT
    le.EXAM_NAME,
    sub.SUBJECT_NAME,
    rs.rn          AS RANK,
    stu.STUDENT_ID,
    stu.STUDENT_NAME,
    stu.GENDER,
    cls.CLASS_NAME,
    cls.GRADE,
    rs.SCORE,
    cls.HEAD_TEACHER
FROM ranked_scores rs
INNER JOIN latest_exam  le  ON rs.EXAM_ID    = le.EXAM_ID
INNER JOIN DIM_STUDENT  stu ON rs.STUDENT_ID = stu.STUDENT_ID
INNER JOIN DIM_CLASS    cls ON stu.CLASS_ID  = cls.CLASS_ID
INNER JOIN DIM_SUBJECT  sub ON rs.SUBJECT_ID = sub.SUBJECT_ID
WHERE rs.rn <= 10;
```

注意这个例子里:目标表用数据区全名 `ABCD_DATA.ABCD_EXAM_TOP10_BY_SUBJECT` 创建并引用;schema、表名、字段名全大写(CTE 名 `latest_exam`/`ranked_scores`、表别名 `f`/`le`/`rs` 等是局部名,保持小写不影响);字段类型全部来自《支持的字段类型》白名单;目标表先建(Step 1)后写(Step 2);排名用 `ROW_NUMBER() OVER (PARTITION BY ...)`;维度补齐用 `INNER JOIN`;整个加载一条 `INSERT ... SELECT` 完成,没有为了拆步骤而引入临时表。