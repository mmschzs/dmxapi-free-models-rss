<div align="center">

# 🚀 DMXAPI Free Models RSS & Feed Tracker

**Real-time RSS, Atom, and JSON Feed tracking for DMXAPI free AI models (`*free`).**

**实时监控并订阅 DMXAPI 免费/限免大模型变更的 RSS / Atom / JSON Feed 聚合源。**

[![RSS Feed](https://img.shields.io/badge/RSS%202.0-Feed-orange?logo=rss&logoColor=white)](https://<username>.github.io/<repo>/rss.xml)
[![Atom Feed](https://img.shields.io/badge/Atom%201.0-Feed-blue?logo=rss&logoColor=white)](https://<username>.github.io/<repo>/atom.xml)
[![JSON Feed](https://img.shields.io/badge/JSON%20Feed-1.1-green?logo=json&logoColor=white)](https://<username>.github.io/<repo>/feed.json)
[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Automated-blue?logo=github-actions&logoColor=white)](https://github.com/<username>/<repo>/actions)
[![Python Version](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[**中文文档**](#-中文文档) | [**English Documentation**](#-english-documentation)

</div>

---

## 📖 中文文档

### 🌟 项目简介

**DMXAPI Free Models RSS** 是一个全自动化、零服务器依赖的 RSS 聚合服务。它定期从 [DMXAPI](https://dmxapi.cn) 接口抓取全部模型信息，智能筛选并监控所有以 `free` 命名或提供免费限额的 AI 大语言模型（例如 `gpt-4o-mini-free`、`claude-3-5-haiku-free`、`deepseek-v3-free`、`gemini-2.5-flash-free` 等）。

当有**新免费模型上线**、**模型限免下线**或**模型配置变动**时，系统会自动生成带有详细模型参数、上下文窗口及调用示例的 Feed 更新，推送至您的 RSS 阅读器。

### ✨ 核心特性

- 🔄 **全自动调度**：基于 GitHub Actions 每 4 小时自动巡检，无缝持久化状态。
- 🎯 **精准识别**：自动识别 `*free` 及官方标记免费模型，提取上下文、所属厂商、价格参数。
- 📡 **全协议支持**：
  - **RSS 2.0** (`rss.xml`)：兼容各类经典 RSS 阅读器。
  - **Atom 1.0** (`atom.xml`)：标准 Atom 格式。
  - **JSON Feed 1.1** (`feed.json`)：适配现代应用与开发者快速集成。
  - **Web 预览页** (`index.html`)：简洁美观的前端静态展示页。
- 📊 **历史增量比对**：通过 `data/history.json` 自动记录模型生命周期（新增 / 下架 / 恢复），并在 RSS 中输出清晰的变更日志（Changelog）。
- 🛡️ **无服务器零成本**：借助 GitHub Pages + GitHub Actions 完全免费托管。

---

### 🔗 订阅链接 (Feed URLs)

> 💡 *将 `<username>` 和 `<repo>` 替换为您 Fork 后的 GitHub 用户名和仓库名：*

| 类型 | 格式 | 订阅地址 | 说明 |
| :--- | :--- | :--- | :--- |
| 🌐 **Web Page** | HTML | `https://<username>.github.io/<repo>/` | 可视化实时免费模型列表与状态 |
| 🍊 **RSS 2.0** | XML | `https://<username>.github.io/<repo>/rss.xml` | 推荐用于 NetNewsWire, Feedly, Inoreader |
| ⚛️ **Atom 1.0** | XML | `https://<username>.github.io/<repo>/atom.xml` | 推荐用于 Follow, Reeder 等 |
| 📜 **JSON Feed**| JSON | `https://<username>.github.io/<repo>/feed.json` | 推荐用于自动化机器人及程序调用 |

---

### 📱 RSS 阅读器订阅推荐

您可以在以下常用阅读器中一键导入订阅地址：

1. **Follow**：点击左下角 `+` -> 添加订阅源 -> 输入 `https://<username>.github.io/<repo>/rss.xml`。
2. **NetNewsWire / Reeder**：添加 Web Feed -> 粘贴 RSS/Atom 地址。
3. **Feedly / Inoreader**：搜索栏直接输入 Feed URL 并点击 Follow。
4. **Telegram Bot**（如 `@FlowerssBot` / `@RSStT_Bot`）：
   ```text
   /sub https://<username>.github.io/<repo>/rss.xml
   ```
5. **微信读书 / 微信群机器人 / 飞书 webhook**：可通过 RSS 轮询服务转发。

---

### 🚀 快速开始与本地开发

#### 1. 克隆代码库并安装依赖

```bash
# 克隆仓库
git clone https://github.com/<username>/dmxapi-free-models-rss.git
cd dmxapi-free-models-rss

# 创建并激活虚拟环境 (可选)
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

#### 2. 本地运行与测试

```bash
# 设置 DMXAPI Key (可选，未设置时自动使用默认测试 Key)
# Windows PowerShell:
$env:DMX_API_KEY="sk-your-dmx-api-key"
# Linux/macOS:
export DMX_API_KEY="sk-your-dmx-api-key"

# 执行抓取与 Feed 生成
python fetch_free_models.py
```

执行后，生成的订阅文件将保存在 `dist/` 目录下（包含 `rss.xml`、`atom.xml`、`feed.json`、`index.html`），历史状态保存在 `data/history.json`。

---

### 🛠️ GitHub Actions 自动化部署指南

只需 3 步即可拥有自己的独立专属追踪服务：

#### 第一步：Fork 本仓库
点击本页面右上角的 **Fork** 按钮，将仓库复制到您的 GitHub 账号下。

#### 第二步：配置 GitHub Secrets（可选）
1. 打开您 Fork 的仓库，进入 **Settings** -> **Secrets and variables** -> **Actions**。
2. 点击 **New repository secret**：
   - **Name**: `DMX_API_KEY`
   - **Value**: 填入您的 DMXAPI 令牌（例如 `sk-...`）。
   > *注：若不配置，工作流将自动使用内置公共体验令牌。*

#### 第三步：开启 GitHub Pages
1. 仓库菜单进入 **Settings** -> **Pages**。
2. 在 **Build and deployment** > **Source** 下拉框中选择 **Deploy from a branch**。
3. Branch 选择 `gh-pages` 分支，目录选择 `/ (root)`，点击 **Save** 保存。
4. 前往 **Actions** 标签页，点击工作流 `Generate and Deploy DMXAPI Free Models RSS` -> **Run workflow** 手动触发首次运行。

部署完成后，即可通过 `https://<your-username>.github.io/<your-repo>/rss.xml` 访问您的订阅源！

---

<br/>

## 🌐 English Documentation

### 🌟 Introduction

**DMXAPI Free Models RSS** is a serverless, zero-maintenance RSS feed generator and tracker for free AI models hosted on [DMXAPI](https://dmxapi.cn). It automatically queries available API models, filters models ending with `*free` or with zero cost, and tracks status changes over time.

Whenever a **new free model is released**, an **existing model is retired**, or **model metadata changes**, a structured feed notification is generated and delivered straight to your favorite RSS reader.

### ✨ Features

- 🔄 **Fully Automated**: Scheduled runs via GitHub Actions every 4 hours.
- 🎯 **Smart Filtering**: Detects free-tier models (`*free`), parses context window sizes and vendor details.
- 📡 **Multi-Format Distribution**:
  - **RSS 2.0** (`rss.xml`)
  - **Atom 1.0** (`atom.xml`)
  - **JSON Feed 1.1** (`feed.json`)
  - **Static Web Dashboard** (`index.html`)
- 📊 **Stateful Changelog Tracking**: Maintains history in `data/history.json` to publish meaningful diffs (New, Deprecated, Restored models).
- ⚡ **100% Free & Serverless**: Built on GitHub Actions and GitHub Pages.

---

### 🔗 Feed Endpoints

| Type | Format | URL Endpoint | Description |
| :--- | :--- | :--- | :--- |
| 🌐 **Web Page** | HTML | `https://<username>.github.io/<repo>/` | Visual dashboard for current free models |
| 🍊 **RSS 2.0** | XML | `https://<username>.github.io/<repo>/rss.xml` | Compatible with NetNewsWire, Feedly, etc. |
| ⚛️ **Atom 1.0** | XML | `https://<username>.github.io/<repo>/atom.xml` | Atom feed for Follow, Reeder, etc. |
| 📜 **JSON Feed**| JSON | `https://<username>.github.io/<repo>/feed.json` | JSON Feed specification for developers |

---

### 🚀 Local Setup

```bash
# 1. Clone repository
git clone https://github.com/<username>/dmxapi-free-models-rss.git
cd dmxapi-free-models-rss

# 2. Install requirements
pip install -r requirements.txt

# 3. Set API Key & Run
export DMX_API_KEY="sk-your-key-here"  # Optional
python fetch_free_models.py
```

Output files will be generated in `./dist` and history saved in `./data/history.json`.

---

### ⚙️ GitHub Actions CI/CD Setup

1. **Fork** this repository.
2. *(Optional)* Go to **Settings** -> **Secrets and variables** -> **Actions** -> add secret `DMX_API_KEY`.
3. Go to **Settings** -> **Pages** -> Set Source to **Deploy from a branch**, Branch: `gh-pages` / `/ (root)`.
4. Go to **Actions** -> select `Generate and Deploy DMXAPI Free Models RSS` -> click **Run workflow**.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
