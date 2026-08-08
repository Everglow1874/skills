# gaussdb-etl-builder 字段类型白名单扩展设计

日期：2026-08-08
状态：已确认

## 1. 背景与目标

`gaussdb-etl-builder` 的字段类型白名单（`references/supported-column-types.md`）目前只有 8 个类型。用户给出 GaussDB(DWS) 官方数据类型表，需要：

1. 在现有基础上**追加**新类型：`TINYINT`、`TIME`、`TIMESTAMP WITHOUT TIME ZONE`、`BOOLEAN`，并补充官方等价命名说明。
2. 白名单中 `INT` **改为 `INTEGER`**（对应官方 `integer(int4/int)`），全量同步（文档、示例 SQL、脚本校验、测试）。

目标：白名单与 GaussDB(DWS) 官方类型对齐，决策处同步，脚本校验与测试保持一致。

## 2. 白名单最终内容

| 类型 | 用途 | 备注 |
|---|---|---|
| `VARCHAR(n)` | 变长字符串(姓名、编码、名称) | 必须给长度 `n` |
| `CHAR(n)` | 定长字符串(状态码、标志位) | 不足补空格 |
| `TINYINT` | 小整数(-128~127) | 官方 `tinyint`，取值小用 |
| `SMALLINT` | 小整数(枚举、0/1 标志) | 等价官方 `smallint(int2)` |
| `INTEGER` | 整数(计数、小范围 ID) | 等价官方 `integer(int4/int)` |
| `BIGINT` | 大整数(主键、大计数) | 等价官方 `bigint(int8)` |
| `NUMERIC(p,s)` | 精确数值(金额、比率) | 等价 `DECIMAL(p,s)`、官方 `numeric(p,s)/decimal(p,s)` |
| `DATE` | 仅日期 | 4 字节 |
| `TIME` | 仅时分秒 | 官方 `time` |
| `TIMESTAMP` | 日期+时间,带时区 | 官方 `timestamp` |
| `TIMESTAMP WITHOUT TIME ZONE` | 日期+时间,无时区 | 官方 `timestamp without time zone` |
| `BOOLEAN` | 布尔 true/false/null | 主要用于标志位,数仓统计场景少用 |

## 4. 改动文件

### 4.1 `gaussdb-etl-builder/references/supported-column-types.md`

- **允许的类型**表按上表更新：删除原 `INT` 行，改为 `INTEGER`；新增 `TINYINT`、`TIME`、`TIMESTAMP WITHOUT TIME ZONE`、`BOOLEAN` 行；其余行补齐官方等价命名。
- **使用约定**补一条：类型取表中任一命名的等价写法都算白名单内；`INTEGER`/`INT` 等价、`NUMERIC`/`DECIMAL` 等价、`TIMESTAMP` 与 `TIMESTAMP WITHOUT TIME ZONE` 用时区区分。

### 4.2 `gaussdb-etl-builder/references/gaussdb-sql.md`

- 第 20 行「选型经验」更新为：……仅日期用 `DATE`;仅时分秒用 `TIME`;需含时区的日期时间用 `TIMESTAMP`、不含时区用 `TIMESTAMP WITHOUT TIME ZONE`;布尔标志用 `BOOLEAN`(数仓统计少用)……
- 示例 SQL 中 4 处 `INT` 类型改为 `INTEGER`（Line 64 模板、Line 101/124/212 RN 列）。

### 4.3 `gaussdb-etl-builder/scripts/generate_field_excel.py`

- `WHITELIST_TYPES` 中 `"INT"` 改为 `"INTEGER"`，并追加：`"TINYINT"`, `"TIME"`, `"TIMESTAMP WITHOUT TIME ZONE"`, `"BOOLEAN"`。

### 4.4 `gaussdb-etl-builder/tests/test_generate_field_excel.py`

- 第 19 行 `"type": "INT"` 改为 `"type": "INTEGER"`（测试用字段定义）。

## 5. 版本号与验收

- `SKILL.md` frontmatter `version: 1.2.0` → `1.3.0`（功能变更）。
- 验收标准：
  1. supported-column-types.md 白名单含 TINYINT/INTEGER/TIME/TIMESTAMP WITHOUT TIME ZONE/BOOLEAN，无 `INT` 行。
  2. gaussdb-sql.md 无 `INT` 类型残留（示例均 `INTEGER`），选型经验含时间/布尔类型。
  3. generate_field_excel.py WHITELIST_TYPES 无 `INT`，含新类型。
  4. 测试用例用 `INTEGER`，7 个 pytest 全部通过。
  5. 文档中占位符统一不带空格 `${TX_DATE}`。