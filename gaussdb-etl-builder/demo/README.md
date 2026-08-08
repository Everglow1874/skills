# gaussdb-etl-builder 测试 demo

用于快速验证 gaussdb-etl-builder 技能的 I/P 作业类型判定与平台变量（`${TX_DATE}`）策略。数据区编码示例统一用 `ABCD`。

---

## 1. 源表设计（3 张）

字段类型全部取自 `references/supported-column-types.md` 白名单。

### 1.1 交易流水事实表 `FACT_TRADE`

| 字段 | 类型 | 说明 |
|---|---|---|
| TRADE_ID | VARCHAR(32) NOT NULL PK | 交易流水号 |
| USER_ID | VARCHAR(20) NOT NULL | 用户 ID |
| CHANNEL | VARCHAR(20) NOT NULL | 渠道编码(APP/WEB/OFFLINE) |
| TRADE_DATE | DATE NOT NULL | 交易日期(增量过滤键) |
| TRADE_TIME | TIMESTAMP NOT NULL | 交易时间 |
| AMOUNT | NUMERIC(12,2) NOT NULL | 交易金额 |
| STATUS | SMALLINT NOT NULL | 1 成功 / 0 失败 |
| REMARK | VARCHAR(200) | 备注 |

```sql
CREATE TABLE ABCD_DATA.ABCD_FACT_TRADE (
    TRADE_ID    VARCHAR(32)   NOT NULL,
    USER_ID     VARCHAR(20)   NOT NULL,
    CHANNEL     VARCHAR(20)   NOT NULL,
    TRADE_DATE  DATE          NOT NULL,
    TRADE_TIME  TIMESTAMP     NOT NULL,
    AMOUNT      NUMERIC(12,2) NOT NULL,
    STATUS      SMALLINT      NOT NULL,
    REMARK      VARCHAR(200),
    PRIMARY KEY (TRADE_ID)
);
```

### 1.2 用户维度表 `DIM_USER`

| 字段 | 类型 | 说明 |
|---|---|---|
| USER_ID | VARCHAR(20) NOT NULL PK | 用户 ID |
| USER_NAME | VARCHAR(50) NOT NULL | 姓名 |
| CITY | VARCHAR(50) | 城市 |

```sql
CREATE TABLE ABCD_DATA.ABCD_DIM_USER (
    USER_ID   VARCHAR(20) NOT NULL,
    USER_NAME VARCHAR(50) NOT NULL,
    CITY      VARCHAR(50),
    PRIMARY KEY (USER_ID)
);
```

### 1.3 渠道维度表 `DIM_CHANNEL`

| 字段 | 类型 | 说明 |
|---|---|---|
| CHANNEL | VARCHAR(20) NOT NULL PK | 渠道编码 |
| CHANNEL_NAME | VARCHAR(50) NOT NULL | 渠道名称 |

```sql
CREATE TABLE ABCD_DATA.ABCD_DIM_CHANNEL (
    CHANNEL      VARCHAR(20) NOT NULL,
    CHANNEL_NAME VARCHAR(50) NOT NULL,
    PRIMARY KEY (CHANNEL)
);
```

---

## 2. 源表表关系

```
DIM_USER ──< FACT_TRADE >── DIM_CHANNEL
   USER_ID     USER_ID   CHANNEL   CHANNEL
```

- `FACT_TRADE.USER_ID → DIM_USER.USER_ID`（N:1，关联用户城市/姓名）
- `FACT_TRADE.CHANNEL → DIM_CHANNEL.CHANNEL`（N:1，关联渠道名称）

---

## 3. 场景一：P 转换作业（按日增量汇总）

### 需求文案（直接发给技能）

```
这是每天 T+1 跑的转换作业(P):把交易流水表 FACT_TRADE 按交易日期+渠道汇总成一张
每日交易汇总表,统计成功交易的金额和笔数。源表结构见 demo 源表。数据区编码 ABCD。
```

### 目标表 `ABCD_DATA.ABCD_DAILY_TRADE_SUMMARY`

| 字段 | 类型 | 备注 |
|---|---|---|
| STAT_DATE | VARCHAR(10) NOT NULL | 交易日期(继承源表) |
| CHANNEL | VARCHAR(20) NOT NULL | 继承源表 |
| CHANNEL_NAME | VARCHAR(50) NOT NULL | 来自 DIM_CHANNEL |
| TRADE_AMOUNT | NUMERIC(12,2) NOT NULL | 金额,仅 STATUS=1 |
| TRADE_CNT | BIGINT NOT NULL | 笔数 |

### 预期验证点

1. P0 询问作业类型 → 识别为 **P 转换作业**。
2. P1 目标表名 `ABCD_DATA.ABCD_DAILY_TRADE_SUMMARY`，字段长度继承源表。
3. P2 日期过滤用 `${TX_DATE}` 占位，**首次出现向用户确认**变量含义。
4. P3 SQL 中增量过滤 `WHERE TRADE_DATE = '${TX_DATE}'` 原样保留占位符、不展开。
5. 产物：目标表字段定义 Excel + step SQL + plan.md 写入输出目录。

---

## 4. 场景二：I 初始化作业（一次性全量装载）

### 需求文案（直接发给技能）

```
这是初始化作业(I):把已存在的交易流水表 FACT_TRADE 全部历史数据一次性装载成一张
交易明细宽表,并关联用户的城市与渠道名称,目标表覆盖全量历史、不是增量。
数据区编码 ABCD。
```

### 目标表 `ABCD_DATA.ABCD_TRADE_DETAIL_WIDE`

| 字段 | 类型 | 来源 |
|---|---|---|
| TRADE_ID | VARCHAR(32) NOT NULL PK | FACT_TRADE |
| USER_ID | VARCHAR(20) NOT NULL | FACT_TRADE |
| USER_NAME | VARCHAR(50) NOT NULL | DIM_USER |
| CITY | VARCHAR(50) | DIM_USER |
| CHANNEL | VARCHAR(20) NOT NULL | FACT_TRADE |
| CHANNEL_NAME | VARCHAR(50) NOT NULL | DIM_CHANNEL |
| TRADE_DATE | DATE NOT NULL | FACT_TRADE |
| AMOUNT | NUMERIC(12,2) NOT NULL | FACT_TRADE |
| STATUS | SMALLINT NOT NULL | FACT_TRADE |

### 预期验证点

1. P0 识别为 **I 初始化作业**。
2. P1 目标表名 `ABCD_DATA.ABCD_TRADE_DETAIL_WIDE`（或技能建议名），字段长度继承源表。
3. P2 计划为**全量装载**（无按日增量过滤），或若带日期条件则用字面量。
4. P3 SQL 中**不出现** `${TX_DATE}` 占位符；日期条件（如有）用字面量。
5. 产物：目标表字段定义 Excel + step SQL + plan.md 写入输出目录。

---

## 5. 测试步骤

1. 新建对话，选中 gaussdb-etl-builder 技能。
2. 把第 1 节的建表语句导入数据库（或直接贴给技能参考）。
3. 把第 3 或第 4 节的需求文案发给技能。
4. 按技能提问逐步确认（作业类型、目标表、计划等），对照「预期验证点」观察。
5. 核对输出目录产物：目标表字段定义 Excel、step SQL、plan.md。

### 验证通过判定

- **场景一（P）**：SQL 日期过滤用 `WHERE TRADE_DATE = '${TX_DATE}'` 且未展开；首次出现有确认。
- **场景二（I）**：SQL 中不出现 `${TX_DATE}`；日期过滤用字面量。