# 参考文献 APA 修正建议

## 建议原则

```text
1. 同一篇论文内不要混用 [EB/OL]、arXiv 条目格式和 APA 格式。
2. 会议论文应统一为：Author, A. A., Author, B. B., & Author, C. C. (Year). Title. In Proceedings/Conference Name.
3. arXiv 论文应统一为：Author, A. A., ... (Year). Title. arXiv. URL
4. 无法核验的 DOI、页码、卷期号一律保留 TODO，不得补造。
5. 期刊名、会议录名称、书名应使用斜体；标题仅句首和专有名词大写。
```

## 修正建议表

| 当前条目编号 | 当前问题 | APA 风格修正建议 | 备注 |
|---|---|---|---|
| [1] | 采用中文网络文献体例 `[EB/OL]`，不符合 APA | `Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., Kaiser, Ł., & Polosukhin, I. (2017). Attention is all you need. arXiv. https://arxiv.org/abs/1706.03762` | 作者已可明确核验 |
| [2] | 机构作者可保留，但 `[EB/OL]` 不符合 APA | `OpenAI. (2023). GPT-4 technical report. arXiv. https://arxiv.org/abs/2303.08774` | 如后续使用正式出版版本，可再替换 |
| [3] | 当前是中文网络条目风格，且缺少 APA 标点 | `Seff, A., Ovadia, Y., Zhou, W., & Adams, R. (2020). SketchGraphs: A large-scale dataset for modeling relational geometry in computer-aided design. arXiv. https://arxiv.org/abs/2007.08506` | 建议核对作者列表是否完整 |
| [4] | 同上，需改为 APA；作者列表可能需要再核对 | `Wu, R., Xiao, C., Zheng, C., ... (2021). DeepCAD: A deep generative network for computer-aided design models. arXiv. https://arxiv.org/abs/2105.09492` | `...` 处建议按论文首页补全 |
| [5] | 当前链接为摘要页；APA 中会议录应斜体，作者列表需完整核验 | `Khan, M. S., Sinha, S., Sheikh, T. U., ... (2024). Text2CAD: Generating sequential CAD designs from beginner-to-expert level text prompts. In *Advances in Neural Information Processing Systems*.` | 页码、卷号建议核验后补全 |
| [6] | 技术文档建议采用组织作者 + 页面标题 + URL | `Onshape. (n.d.). FeatureScript documentation. https://cad.onshape.com/FsDoc/index.html` | 若能查到更新时间可替换 `n.d.` |

## 结论

当前正文中的参考文献更接近中文技术报告/网络文献写法，而不是 APA。若后续要投英文模板或采用国际学术体例，建议在转 LaTeX 时统一改写；若学校要求 GB/T 7714，则应另起一版文献格式，不建议直接沿用本文件中的 APA 草案。
