# 双重去杠杆陷阱：波动率目标与回撤控制的交互效应

> **Double Deleveraging Trap: The Interaction of Volatility Targeting and Drawdown Control**
> ——来自中国多资产市场的证据与数值模拟

本仓库存放该论文的**全文**与**可复现回测代码**。全部行情数据来自公开免费源（AkShare / 天天基金 F10 页面），无需任何商业数据库即可完整复现文中所有表格与图形。

- 仓库地址：https://github.com/958809518/double-deleveraging-trap
- 样本区间：2013-08-01 至 2026-10-20（约 13.2 年，3210 个交易日）
- 交易成本：全部回测已扣除单边万三，并校正 ETF 份额折算造成的价格假跳变

---

## 一、目录结构

| 路径 | 说明 |
|---|---|
| `论文_双重去杠杆陷阱.md` | 论文全文（Markdown 源，24 表 / 4 图 / 12 公式） |
| `论文_双重去杠杆陷阱.html` | 网页阅读版 |
| `双重去杠杆陷阱_投稿稿_v3.docx` | 投稿用 Word 版（公式已转 OMML） |
| `paper_data/` | **论文全部结果表的原始输出**（CSV / JSON），与正文表格一一对应 |
| `data/` | 原始行情与分红数据（AkShare 下载 + 人工整理） |
| `articles/` | 原始研究语料 |

---

## 二、代码与论文章节的对应关系

### 数据层
| 脚本 | 作用 |
|---|---|
| `download_data.py` | 通过 AkShare 下载 ETF 与国债等六类资产行情 |
| `download_more.py` | 补充下载与数据补齐 |
| `asset_stats.py` | 资产描述性统计 |

### 核心回测层
| 脚本 | 作用 | 对应正文 |
|---|---|---|
| `backtest_v3.py` | **主回测引擎**（波动率目标 × 回撤控制 × 杠杆上限） | 第 4 节主结果、表 2—表 5 |
| `diagnostics.py` | 双引擎一致性校验、敞口实现率诊断 | 第 5.1 节、表 6 |
| `constraint_cost.py` | 以效用 / 收益 / 风险三口径量化约束福利成本 | 第 5.2 节、表 7—表 9 |
| `nosignal.py` | 关闭全部战术信号后的分岔检验 | 第 4.4 节、表 10 |
| `theory_model.py` | 理论模型的数值模拟（引理 1、命题 1—2） | 第 3 节、图 1—图 2 |

### 稳健性与补充检验
| 脚本 | 作用 | 对应正文 |
|---|---|---|
| `robust_engine.py` | 估计窗口 / 调仓频率 / 函数形式等变体 | 第 6.1—6.5 节 |
| `supplement_empirics.py` | 补充实证（事件研究、机制分解） | 第 5.3 节、表 11—表 13 |
| `supplement2.py` | 交易成本与阈值敏感性 | 第 6.7 节 |
| `eventstudy_boot.py` | 状态控制事件研究 + block bootstrap（block=21 日） | 第 5.3 节 |
| `review_empirics.py` | 实证结果的复核脚本 | 审稿返修用 |
| `sensitivity.py` / `variants.py` / `variant_rotate.py` | 参数敏感性 | 第 6.6 节 |

### 图表与排版
| 脚本 | 作用 |
|---|---|
| `make_figs.py` | 生成图 1—图 4（matplotlib，中文字体 Microsoft YaHei） |
| `make_docx_figs.py` | 生成 Word 版图片 |
| `make_paper_html.py` | Markdown → HTML |
| `md2docx.py` | Markdown → Word（LaTeX → MathML → OMML） |
| `patch_docx_v4.py` | 在已定稿 docx 上定点补填投稿信息（无需重排公式） |
| `verify_docx.py` | 成稿 docx 关键点校验 |
| `make_report.py` | 生成研究总报告 |

---

## 三、复现步骤

```bash
pip install akshare pandas numpy matplotlib python-docx

# 1) 取数（若跳过，可直接使用仓库内 data/）
python download_data.py && python download_more.py

# 2) 主回测与机制检验
python backtest_v3.py
python diagnostics.py
python constraint_cost.py
python nosignal.py

# 3) 理论数值模拟
python theory_model.py

# 4) 稳健性与事件研究
python robust_engine.py
python supplement_empirics.py
python supplement2.py
python eventstudy_boot.py

# 5) 出图与排版
python make_figs.py
python make_docx_figs.py
python md2docx.py
```

各脚本的数值输出直接写入 `paper_data/`，与正文表格序号一致。

---

## 四、需要一并声明的两项边界

论文正文已明确写出，此处重申以免误读：

1. 本文策略相对国债 ETF 的风险调整优势**未获统计支持**（差值 +0.116，p = 0.774），故不主张其优于一切基准。
2. 收益—风险前沿的**单峰形状具有条件性**：四组回撤阈值中仅两组出现内点最优；而"回撤控制在高目标波动区造成 4—7 个百分点的收益损失"这一**成本层结论**在全部检验方向上成立。

---

## 五、资助与声明

- 资助：国家社会科学基金一般项目《数字孪生赋能韧性城市建设的机理与实践路径研究》（批准号 24BGL226）
- 利益冲突：作者声明不存在可能影响本文结论的经济利益冲突
- 许可：代码部分 MIT；论文文本版权归作者与发表期刊所有

*本仓库仅供学术研究参考，不构成任何投资建议。*
