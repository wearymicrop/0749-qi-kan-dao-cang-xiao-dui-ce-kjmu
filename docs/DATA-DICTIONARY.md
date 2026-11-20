# 数据字典

## 输入清册

输入为 UTF-8 JSON 对象，字段 `rules`、`titles`、`receipts` 分别为三张数组，`publication_notes` 可选，缺省视为空表。对应单表上限 3000 行，生成应到期位上限 10000。原始行号从 `receipts` 首个数组项起算，首项为 1。

| 表 | 字段 | 定义 |
|---|---|---|
| 订购 | `chain` | 稳定订阅链字符串，区分大小写 |
| 订购 | `from_year`, `to_year` | 双端包含，整数 1900–2200，单段不超过 12 年 |
| 订购 | `first_volume` | 首年卷号，随后每年加一 |
| 订购 | `issues_per_year` | 单年正刊期数 1–60 |
| 订购 | `numbering`, `first_issue` | `yearly` 按年从 1 起，`continuous` 按出版年度累加，首年首期可指定 |
| 刊名 | `chain`, `title`, `from_year`, `to_year` | 生效年度包含两端，规范化后同刊名每年只有一个映射，同链可登记同年的多个别名 |
| 来刊 | `accession` | 物理件验收号，以字符串原样保留前导零，去除两端空格后参与去重 |
| 来刊 | `title`, `year` | 来刊登记刊名和整数出版年，年度按出版年核对 |
| 来刊 | `volume`, `issue` | 字符串，允许全角与前导零，卷期为 1–9999 |
| 来刊 | `kind` | `regular` 正刊默认值，`supplement` 增刊单列 |
| 来刊 | `note_id` | 可选，引用出版说明编号；只有引用时逆序期号范围才放行 |
| 出版说明 | `note_id` | 说明编号，全表唯一，最长 40 字符 |
| 出版说明 | `chain`, `title` | 订阅链与该链登记过的刊名；改刊名时取来刊登记年度生效的刊名 |
| 出版说明 | `span` | 恰两个不同年度的数组，双端包含，且每一年都落在该链订购段内 |
| 出版说明 | `statement` | 出版方确认原文，最长 200 字符，凭证原样保存 |

期号范围可使用 `-`、`–`、`—`、`~` 或 `至`，包含两端。来刊以验收号分组，同组相同字段视为重放，不同字段保留独立候选。`null`、空字串或空对象记空行，其他坏字段给出字段名并随原值隔离。不使用到达顺序推断卷期。

## 跨年度合期采信

跨年度合期以 `publication_notes` 为唯一采信前提。说明结构错误（`INVALID_NOTE`）、编号重复（`NOTE_ID_DUPLICATE`）、年度区间非法（`NOTE_SPAN`）、年度超出订购段（`NOTE_OUT_OF_ORDER`）或刊名不属于该链（`NOTE_TITLE_MISMATCH`）阻断整份清册。

来刊引用说明后进入 M4 整体校验：订阅链与登记年度须对准说明起始年度（`NOTE_MISMATCH`），说明编号不存在记 `NOTE_NOT_FOUND`，增刊不得引用说明。卷号取合期起始卷；期号范围按编号方式对齐两个边界期位——`yearly` 为末年号倒接首年号（如 `4-1`），`continuous` 为末年号接次年初号（如 `9-10`）。任一不符整条隔离，不拆分采信。通过后生成 `spans`，一件实物只挂两个边界期位。

## 期位核验

期位键为 `(chain, year, issue)`。卷号由订购规则唯一决定，用于来刊交叉检查。相邻订购段须递增接续卷号，两段都连排时还须接续期号。合期只认合法年度内的完整范围。每个期位通过所有候选确定状态，分为覆盖、缺刊、争议。争议包括多个件号覆盖和同件号不同来刊描述。两种争议均可从到藏记录追溯原始清册。

跨年依据在期位上以 `cross_year=true` 与 `note_id` 标记，两个年度的期位引用同一验收号与原始行。`totals.holdings` 按展期后的验收号去重统计实物件数，因此一件跨年合期只计一件在藏，而两个年度各自的覆盖数不变。`note_summary` 逐条说明给出状态（`covered`/`disputed`/`pending`）、涉及年度与卷号、挂接期位数、覆盖与争议数及阻断原因码。

## 调用与归档

各阶段接受 `GET /api/<阶段>/<clean|dirty|crossyear>` 或 `POST /api/<阶段>`。请求体用 `{"sample":"crossyear"}` 或 `{"data":{...}}`，两个来源只能选一个。阶段名为 `orders`、`receipts`、`numbering`、`combined`、`notes`、`titles`、`balance`。

`POST /api/runs` 接受同一请求并保存运行。运行编号为规则版本与规范 JSON 输入摘要的 SHA-256。`GET /api/runs/{id}` 读归档，`POST /api/runs/{id}/rerun` 用归档里的原输入再算。同摘要的重复归档保留首份运行时间与结果。规则版本变化会生成新编号。`GET /api/runs/{id}/export` 下载一份 JSON 凭证，含原始清册（含 `publication_notes` 原文）和计算证据（含 `note_summary` 与跨年期位标记），归档时间用 UTC。
