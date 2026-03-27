# GitHub Actions → Flask 检测服务 部署指南

本文档对应你确认的架构：

- GitHub Actions 仅发送 PR 变更 `.c` 文件内容到服务端
- Flask 服务端接收请求，调用 `vulcnn_cicd_detector.py` 执行检测
- 服务端返回 `report.md` 文本给 Actions
- Actions 在 Job Summary 中展示报告并上传产物

---

## 1. 服务端准备（云主机）

项目根目录假设为：`/home/kuafu/vulcnnplus/VulCNNPlus`

### 1.1 安装依赖

```bash
cd /home/kuafu/vulcnnplus/VulCNNPlus
pip install -r CI_CD/requirements.txt
pip install torch numpy pandas networkx pydot scikit-learn transformers tqdm prettytable lap sent2vec
```

> 注意：服务端需要能运行 `joern_graph_gen.py`，即需提前安装并配置好 joern 环境。

### 1.2 配置环境变量

至少需要：

- `VULCNN_SERVER_TOKEN`：Actions 与服务端共享的鉴权 token
- `VULCNN_CHECKPOINT_PATH`：固定 checkpoint 绝对路径

示例：

```bash
export VULCNN_SERVER_TOKEN='replace_with_strong_token'
export VULCNN_CHECKPOINT_PATH='/home/kuafu/vulcnnplus/VulCNNPlus/CI_CD/output/checkpoints/fold0_best.pt'
export VULCNN_DEVICE='auto'
export VULCNN_SERVER_HOST='0.0.0.0'
export VULCNN_SERVER_PORT='5001'
```

### 1.3 启动 Flask 服务

```bash
cd /home/kuafu/vulcnnplus/VulCNNPlus
python CI_CD/server/flask_detector_server.py
```

健康检查：

```bash
curl http://127.0.0.1:5001/healthz
```

---

## 2. GitHub 仓库 Secrets 配置

在仓库 `Settings -> Secrets and variables -> Actions` 新增：

- `VULCNN_SERVER_URL`：例如 `https://your-domain/api/v1/detect-pr`
- `VULCNN_SERVER_TOKEN`：与服务端环境变量一致

---

## 3. Actions 工作流

工作流文件：`.github/workflows/vulcnn-remote-detect.yml`

行为：

1. 获取 PR 变更 `.c` 文件列表
2. 调用 `CI_CD/github_actions/send_changed_files_for_scan.py` 发请求
3. 将返回的 `report.md` 输出到 Job Summary
4. 上传 `CI_CD/output/cicd/**` 作为 artifacts

---

## 4. 请求/响应契约

### 4.1 请求（POST `/api/v1/detect-pr`）

Header:

- `Authorization: Bearer <VULCNN_SERVER_TOKEN>`

Body:

```json
{
  "repo": "owner/repo",
  "pr_number": 123,
  "sha": "commit_sha",
  "files": [
    {"path": "src/a.c", "content": "..."},
    {"path": "src/b.c", "content": "..."}
  ]
}
```

### 4.2 响应

```json
{
  "report_md": "# VulCNN CI 检测报告\n...",
  "results": [...],
  "errors": [...]
}
```

---

## 5. 建议的上线顺序

1. 先用 `workflow_dispatch` 手动触发验证
2. 确认 report 可展示后再开 `pull_request` 自动触发
3. 后续再加“高风险阻断”策略（当前实现默认不强制阻断）
