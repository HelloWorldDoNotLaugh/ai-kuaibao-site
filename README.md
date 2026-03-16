# AI 快报网站

这是一个可自动生成并发布的静态网站项目，用来每天产出一份 `AI 快报`。

当前实现特点：

- 每天上午 `10:00` 自动执行
- 生成结果只保留 `HTML`
- 最新快报会写到 `site/reports/`
- 首页写到 `site/index.html`
- 可直接发布到 GitHub Pages

## 本地运行

```bash
python3 -m pip install -r requirements.txt
python3 scripts/generate_site.py
```

生成后可查看：

- `site/index.html`
- `site/reports/*.html`

## GitHub Actions 定时执行

已配置工作流：

- `.github/workflows/daily-ai-kuaibao.yml`

执行方式：

- 手动触发：`workflow_dispatch`
- 定时触发：每天 `02:00 UTC`

说明：

- `02:00 UTC` 对应 `Asia/Shanghai` 的 `10:00`

## GitHub Pages 发布

推荐做法：

1. 将当前目录初始化为 Git 仓库
2. 推送到新的 GitHub 仓库
3. 在仓库设置里开启 `GitHub Pages`
4. Source 选择 `GitHub Actions`

工作流会做两件事：

- 生成并提交最新的 `site/*.html`
- 部署 `site/` 到 GitHub Pages

## 目录结构

```text
AI快报/
├── .github/workflows/daily-ai-kuaibao.yml
├── scripts/generate_site.py
├── site/
│   ├── assets/styles.css
│   ├── index.html
│   └── reports/
├── requirements.txt
└── README.md
```

## 当前限制

- 目前数据来源是公开可访问的资讯/RSS 聚合，不依赖 X 官方 API
- 这样可以稳定跑在 GitHub Actions 上，但内容更偏“公开热点聚合”，不是纯 X 热帖榜
