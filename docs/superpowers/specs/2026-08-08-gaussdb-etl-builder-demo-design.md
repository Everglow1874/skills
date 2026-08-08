# gaussdb-etl-builder 测试 demo 设计

日期：2026-08-08
状态：已确认（方案 A）

## 1. 背景与目标

`gaussdb-etl-builder` 技能刚完成平台变量支持与作业类型（I/P）判定改造。用户需要一个**测试 demo**来快速验证技能功能——重点是：

1. **P 转换作业**：日期/增量过滤用 `${TX_DATE}` 占位，首次出现向用户确认，原样保留占位符。
2. **I 初始化作业**：禁用平台变量，日期过滤用字面量。

目标：在技能目录下提供一组可直接使用的源表 + 两个统计场景（一 P 一 I），用户拿需求文案喂给技能即可手动验证。

范围约束：静态 demo 包，**不包含自动化运行脚本**（技能是交互式引导，自动化驱动成本高，超出「简单测试一下」范围）。

## 2. 目录结构

```
gaussdb-etl-builder/demo/
├── README.md            # 使用说明、目录结构、验证通过判定
├── demo_trade.sql       # 源表建表语句 + 示例数据(可直接导入)
└── demo_scenarios.md    # 两个场景需求文案 + 预期验证点
```

## 3. 源表设计 `demo/demo_trade.sql`

一张交易流水事实表 `FACT_TRADE`，字段全部来自 `references/supported-column-types.md` 白名单：

```sql
-- 交易流水事实表(源表)
-- Schema 与表名按数据区规范:<编码>_DATA.<编码>_FACT_TRADE,示例编码 ABCD
CREATE TABLE ABCD_DATA.ABCD_FACT_TRADE (
    TRADE_ID      VARCHAR(32)   NOT NULL,   -- 交易流水号(主键)
    USER_ID       VARCHAR(20)   NOT NULL,   -- 用户编码
    CHANNEL       VARCHAR(20)   NOT NULL,   -- 渠道编码(如 APP / WEB / OFFLINE)
    TRADE_DATE    DATE          NOT NULL,   -- 交易日(按天增量用)
    TRADE_TIME    TIMESTAMP     NOT NULL,   -- 交易时间
    AMOUNT        NUMERIC(12,2) NOT NULL,   -- 交易金额
    STATUS        SMALLINT      NOT NULL,   -- 状态:1 成功 / 0 失败
    REMARK        VARCHAR(200)              -- 备注(可空)
);
```

要求：

- 字段类型全部取自白名单（`VARCHAR(n)`/`DATE`/`TIMESTAMP`/`NUMERIC(p,s)`/`SMALLINT`）。
- 类型不裸写 `VARCHAR`，均带长度。
- 附带约 10 行**示例数据 INSERT**（含跨两天的记录），便于用户在库里直接灌数据跑 SQL；示例日期用具体字面量（如 `2026-08-05`、`2026-08-06`）。

## 4. 场景设计 `demo/demo_scenarios.md`

### 场景一：P 转换作业（按日增量汇总）

**需求文案（直接发给技能）：**

```
这是每天 T+1 跑的转换作业(P):把交易流水表 FACT_TRADE 按天汇总成一张每日交易汇总表,
按交易日期+渠道统计交易金额和笔数(只统计成功交易)。源表结构见 demo_trade.sql。
数据区编码 ABCD。
```

**预期验证点：**
1. P0 应询问作业类型，回答后识别为 **P 转换作业**。
2. P1 目标表名应为 `ABCD_DATA.ABCD_DAILY_TRADE_SUMMARY`，字段长度继承源表。
3. P2 计划里日期过滤用 `${TX_DATE}` 占位，并首次出现时向用户确认变量含义。
4. P3 生成的 SQL 中增量过滤（`WHERE TRADE_DATE = '${TX_DATE}'`）原样保留占位符，未展开成字面日期。
5. 产物：目标表字段定义 Excel + step SQL + plan.md 写入输出目录。

### 场景二：I 初始化作业（一次性全量装载）

**文案（直接发给玩法）：**

```
> 这是初始化作业(I):一次性把交易流水历史数据全部装载到一张交易明细宽表,
> 目标表覆盖全部历史、不是增量。源表结构见 demo_trade.sql。
> 数据区编码 ABCD。
```

**预期验证点：**
1. P0 应询问作业类型，回答后识别为 **I 初始化作业**。
2. P1 目标表名如 `ABCD_DATA.ABCD_TRADE_DETAIL_WIDE`（或技能建议的名字），字段长度继承源表。
3. P2 计划为全量装载（无按日增量过滤），或若带日期过滤则用**字面量**日期。
4. P3 生成的 SQL 中**不出现** `${TX_DATE}` 占位符；日期过滤（如有）用字面量。
5. 产物：目标表字段定义 Excel + step SQL + plan.md 写入输出目录。

## 5. 使用说明 `demo/README.md`

内容要点：

- 目录结构说明（同第 2 节）。
- 怎么跑：新建对话选中技能 → 导入 `demo_trade.sql`（或贴给技能）→ 发场景文案 → 逐步确认 → 核对产物。
- 验证通过判定：
  - 场景一（P）：SQL 日期过滤出现 `${TX_DATE}` 且未展开；首次出现有确认。
  - 场景二（I）：SQL 中不出现 `${TX_DATE}`；日期过滤用字面量。

## 6. 验收标准

1. `demo/demo_trade.sql` 存在，建表语句字段类型全部在白名单内，含约 10 行示例数据。
2. `demo/demo_scenarios.md` 存在，含场景一（P）/ 场景二（I）需求文案与预期验证点。
3. `demo/README.md` 存在，含使用说明、目录结构、验证通过判定。
4. 文档中占位符统一用不带空格的 `${TX_DATE}`，不出现带空格的 `$ {TX_DATE}`。
5. 不改动 SKILL.md / references / evals / scripts / tests 的任何现有文件。
6. 现有 7 个 pytest 测试仍然通过。