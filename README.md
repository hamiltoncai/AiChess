# 国际象棋对战平台 ♟️

一款本地运行的国际象棋游戏，支持AI对战、实时评估和LLM智能评论。

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## ✨ 功能特点

- **🎲 三个难度等级**: 简单、中等、困难，适合各种水平的玩家
- **🤖 AI对战**: 支持内置AI和Stockfish引擎
- **📊 实时评估**: 每步棋后显示局势评估和胜率预测
- **💬 智能评论**: 可接入Ollama或OpenCode进行棋步点评
- **🎨 美观界面**: 现代化深色主题，响应式设计

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务器

**macOS/Linux:**
```bash
chmod +x start.sh
./start.sh
```

**Windows:**
```bash
python app.py
```

### 3. 打开浏览器

访问 http://localhost:5001

## 📋 系统要求

- Python 3.8+
- 现代浏览器 (Chrome, Firefox, Safari, Edge)
- 可选: Stockfish 国际象棋引擎

## 🎮 游戏操作

1. **选择难度**: 简单、中等、困难
2. **选择执棋颜色**: 白棋(先手) 或 黑棋(后手)
3. **点击棋子开始走棋**
4. **观看AI回应和评论**

## 🤖 LLM配置

### Ollama

```bash
# 安装 Ollama
# macOS/Linux
curl -fsSL https://ollama.com/install.sh | sh

# 下载模型
ollama pull llama3.2
ollama serve
```

在游戏设置中选择 "Ollama" 后连接即可。

### OpenCode

配置OpenCode服务地址后，选择 "OpenCode" 连接。

## ⚙️ 可选组件

### Stockfish 引擎

Stockfish 是世界最强的开源国际象棋引擎之一，提供更精确的评估和更强的AI。

**安装方法:**

**macOS:**
```bash
brew install stockfish
```

**Ubuntu/Debian:**
```bash
sudo apt install stockfish
```

**Windows:**
从 https://stockfishchess.org/download/ 下载并添加到PATH

## 📁 项目结构

```
chess/
├── app.py              # Flask 服务器
├── engine.py           # 棋引擎封装
├── llm.py              # LLM 集成
├── requirements.txt    # Python依赖
├── start.sh           # 启动脚本
└── static/
    ├── index.html     # 游戏界面
    └── game.js        # 前端逻辑
```

## 🎯 API 接口

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/new_game` | POST | 创建新游戏 |
| `/api/get_state` | GET | 获取游戏状态 |
| `/api/make_move` | POST | 执行玩家走棋 |
| `/api/ai_move` | POST | AI走棋 |
| `/api/evaluate` | GET | 评估当前局面 |
| `/api/legal_moves` | GET | 获取合法走法列表 |
| `/api/undo` | POST | 悔棋 |
| `/api/set_difficulty` | POST | 设置难度 |
| `/api/configure_llm` | POST | 配置LLM |

## 🔧 技术栈

- **后端**: Python 3 + Flask
- **前端**: 原生 JavaScript + Canvas
- **棋局逻辑**: python-chess
- **AI**: Stockfish / 内置Minimax算法
- **LLM**: Ollama / OpenCode API

## 📝 开发计划

- [ ] 支持中国象棋规则
- [ ] 添加开局库支持
- [ ] 支持PGN文件导入导出
- [ ] 添加棋局分析模式
- [ ] 支持网络对战

## 📄 许可证

MIT License - 自由使用和修改

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！