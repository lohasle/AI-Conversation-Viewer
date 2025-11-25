# PyPI 发布指南 / PyPI Publishing Guide

## 📋 前置准备 / Prerequisites

### 1. 注册 PyPI 账号 / Register PyPI Account

- 生产环境 (Production): https://pypi.org/account/register/
- 测试环境 (Test): https://test.pypi.org/account/register/

### 2. 安装发布工具 / Install Publishing Tools

```bash
pip install --upgrade pip setuptools wheel twine build
```

### 3. 配置 API Token / Configure API Token

访问 https://pypi.org/manage/account/token/ 创建 API token，然后配置到 `~/.pypirc`:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-AgEIcHlwaS5vcmc...  # 你的 PyPI token

[testpypi]
username = __token__
password = pypi-AgENdGVzdC5weXBpLm9yZw...  # 你的 TestPyPI token
```

## ⚠️ 重要：修改包名 / Important: Change Package Name

当前配置文件中的包名是 `claude-code-viewer`，但你想发布为 `ai-coder-viewer`。需要修改以下文件：

### 修改 setup.py

```python
setup(
    name="ai-coder-viewer",  # 改这里
    version="1.1.0",
    # ... 其他配置
)
```

### 修改 pyproject.toml

```toml
[project]
name = "ai-coder-viewer"  # 改这里
```

## 📦 发布步骤 / Publishing Steps

### 步骤 1: 清理旧的构建文件 / Clean Old Builds

```bash
rm -rf build/ dist/ *.egg-info/
```

### 步骤 2: 构建发行版 / Build Distribution

```bash
python -m build
```

这会在 `dist/` 目录生成两个文件：
- `ai-coder-viewer-1.1.0.tar.gz` (源码包)
- `ai_coder_viewer-1.1.0-py3-none-any.whl` (wheel 包)

### 步骤 3: 检查构建包 / Check Build

```bash
twine check dist/*
```

### 步骤 4: (可选) 先发布到 TestPyPI 测试 / Upload to TestPyPI First

```bash
twine upload --repository testpypi dist/*
```

测试安装：
```bash
pip install --index-url https://test.pypi.org/simple/ ai-coder-viewer
```

### 步骤 5: 发布到正式 PyPI / Upload to PyPI

```bash
twine upload dist/*
```

### 步骤 6: 验证发布 / Verify Publication

```bash
pip install ai-coder-viewer
```

访问你的包页面: https://pypi.org/project/ai-coder-viewer/

## 🔄 版本更新流程 / Version Update Workflow

每次发布新版本时：

1. **更新版本号** / Update version in:
   - `setup.py` (line 17)
   - `pyproject.toml` (line 45)
   - `README.md` badge (line 5)

2. **更新 CHANGELOG** (如果有)

3. **提交代码** / Commit changes:
   ```bash
   git add .
   git commit -m "Release version X.X.X"
   git tag -a vX.X.X -m "Version X.X.X"
   git push origin main --tags
   ```

4. **清理并重新构建** / Clean and rebuild:
   ```bash
   rm -rf build/ dist/ *.egg-info/
   python -m build
   twine check dist/*
   ```

5. **发布** / Upload:
   ```bash
   twine upload dist/*
   ```

## 🛠️ 快速发布脚本 / Quick Publish Script

创建 `publish.sh` 脚本：

```bash
#!/bin/bash
set -e

echo "🧹 Cleaning old builds..."
rm -rf build/ dist/ *.egg-info/

echo "📦 Building package..."
python -m build

echo "✅ Checking package..."
twine check dist/*

echo "📤 Uploading to PyPI..."
twine upload dist/*

echo "✨ Published successfully!"
echo "📦 Install with: pip install ai-coder-viewer"
```

使用方法：
```bash
chmod +x publish.sh
./publish.sh
```

## 🔐 安全建议 / Security Best Practices

1. **使用 API Token** 而不是密码
2. **不要** 将 `.pypirc` 提交到 Git
3. **添加到 .gitignore**:
   ```
   .pypirc
   dist/
   build/
   *.egg-info/
   ```

## ❓ 常见问题 / FAQ

### Q: 包名已被占用怎么办？
A: PyPI 包名是唯一的。如果 `ai-coder-viewer` 被占用，尝试其他名字如：
- `ai-conversation-viewer`
- `claude-ai-viewer`
- `ai-chat-viewer`

### Q: 上传失败显示 403 错误？
A: 检查：
1. API token 是否正确配置
2. 包名是否已被别人注册
3. 是否有该包的上传权限

### Q: 如何删除已发布的版本？
A: PyPI 不允许删除已发布的版本（防止依赖破坏），只能：
1. 发布新版本修复问题
2. 或通过 PyPI 支持团队请求删除（需要充分理由）

### Q: 测试安装时出现依赖错误？
A: TestPyPI 可能没有所有依赖包，使用：
```bash
pip install --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    ai-coder-viewer
```

## 📚 相关资源 / Resources

- PyPI 官方文档: https://packaging.python.org/
- Twine 文档: https://twine.readthedocs.io/
- Python 打包指南: https://packaging.python.org/tutorials/packaging-projects/

## ✅ 检查清单 / Checklist

发布前确认：

- [ ] 已修改所有配置文件中的包名为 `ai-coder-viewer`
- [ ] 版本号已更新
- [ ] README.md 已更新
- [ ] 代码已测试通过
- [ ] 已安装 build 和 twine
- [ ] 已配置 PyPI API token
- [ ] 已清理旧构建文件
- [ ] 已在 TestPyPI 测试（可选但推荐）
- [ ] 所有依赖版本已正确指定
- [ ] LICENSE 文件存在

---

**祝发布顺利！🚀 / Happy Publishing! 🚀**
