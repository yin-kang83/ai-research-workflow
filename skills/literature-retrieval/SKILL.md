# 合规文献检索 · OpenAlex/Crossref/arXiv 工作流技能

> 技能 ID：`literature-retrieval`
> 位置：`skills/literature-retrieval/`（`SKILL.md` + `scripts/` + `tests/`）
> 适用：写综述/论文/研究报告时的**元数据检索、证据核对、引用导出**；不碰付费墙、不转存全文。

## 一、何时用

- 需要按主题检索论文/文献的元数据（标题、作者、年份、期刊、DOI、引用数、OA 链接）；
- 需要核对某篇文献是否真实存在、DOI/标题/年份是否一致（防"幻觉引用"）；
- 需要把检索结果导出 BibTeX，用于论文/报告引用；
- 需要把检索结果接入证据账本（每条带来源、检索时间、核验状态）。

## 二、何时不要用

- 需要下载/转存**非 OA 全文 PDF**（版权风险；本技能只给合法 OA 链接，不下载、不转存、不公开分发全文）；
- 需要绕过付费墙/登录/验证码的数据库（CNKI/万方/维普等需授权接口，不在本技能范围）；
- 需要批量爬取/高频请求（会触发 API 限流或平台风控；本技能默认低频、单查询）；
- 需要法律/税务/投资结论（本技能只做文献线索，结论需人工判断与专业意见）。

## 三、流程

1. **拆概念**：用 `build_query_plan.py` 把中文需求扩展为中英关键词（可加自定义同义词 JSON），输出可审计的 query plan；
2. **查元数据**：`search_openalex.py`（覆盖最广，带引用数与 OA 链接）、`search_crossref.py`（DOI 权威元数据）、`search_arxiv.py`（预印本，合法 OA）；
3. **核验**：对候选 DOI 跑 `verify_metadata.py`，Crossref vs OpenAlex 交叉核对标题/年份，输出 match/partial/mismatch；
4. **导出**：`export_bibtex.py` 生成 `.bib`；结果 JSON 保留来源、查询、检索时间；
5. **入账**（可选）：把记录写入项目证据账本，标注 `source=openalex/crossref/arxiv`、`retrieved_at`、`verified=true/false`。

## 四、证据

- 每条记录保留：来源库、查询词、检索时间、DOI/URL、标题、作者、年份、期刊/来源、引用数（若有）、OA 链接（若有）；
- 交叉核验状态：`match`（标题+年份一致）/`partial`（标题近似或年份差 1）/`mismatch`/`not_found`；
- 引用时以 DOI/出版社页面为准；预印本（arXiv）需注明"预印本，未同行评审"；
- **不把检索结果当结论**：文献只是线索，结论要读原文并做证据分级（L1 原文/L2 计算/L3 二手）。

## 五、失败处理

| 现象 | 处理 |
|---|---|
| API 429/503 | 降频、等待后重试 1–2 次；OpenAlex 共享 IP 可能 429，可加 `--mailto 你的邮箱` 或隔日重试；仍失败记录 `_未取得`，不编造 |
| DOI 查不到 | 标记 `not_found`，改用标题检索核对，仍无则标注"待核验" |
| 标题近似但不同 | 输出 `partial`/`mismatch`，不要强行引用 |
| 网络不可用 | 使用缓存/手动导入 JSON；不要伪造元数据 |

## 六、边界

- 只检索**元数据**；合法 OA 全文只给链接，由用户按许可自行访问；不下载、不转存、不分发；
- 不提供 CNKI/万方/维普等授权库的绕过方案；如需中文库，走机构账号/官方 API；
- 不保证覆盖全部文献；OpenAlex/Crossref/arXiv 各有收录偏差；
- 检索式与关键词扩展是**辅助**，最终检索策略由研究者确认；
- 研究材料，不构成法律/税务/投资建议。

## 七、命令速查

```powershell
$py = "C:\Users\Administrator\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
# 1) 关键词扩展 → query_plan.json
& $py skills/literature-retrieval/scripts/build_query_plan.py --concept "大语言模型 合规" -o query_plan.json
# 2) OpenAlex 检索
& $py skills/literature-retrieval/scripts/search_openalex.py --query "large language model compliance" --from-year 2023 --limit 20 -o openalex.json
# 3) Crossref 检索
& $py skills/literature-retrieval/scripts/search_crossref.py --query "large language model compliance" --from-date 2023-01-01 --limit 20 -o crossref.json
# 4) arXiv 预印本
& $py skills/literature-retrieval/scripts/search_arxiv.py --query "large language model compliance" --max-results 10 -o arxiv.json
# 5) DOI 核验
& $py skills/literature-retrieval/scripts/verify_metadata.py --doi 10.1000/xyz -o verify.json
# 6) BibTeX 导出
& $py skills/literature-retrieval/scripts/export_bibtex.py --input openalex.json -o refs.bib
```

## 八、测试

```powershell
& $py -m pytest skills/literature-retrieval/tests -q
```
