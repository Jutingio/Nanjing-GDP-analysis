# 上传 GitHub

源码版已具备 README、MIT LICENSE（Jutingio）、CITATION、依赖、JSON Schema、测试、GitHub Actions 和来源说明。建议从导出的源码包建立仓库，避免把本机整个旧交付目录直接上传。

```sh
python scripts/export_source.py
```

得到 output/github-source.zip。包内是仓库根目录内容，含 SOURCE-MANIFEST.json；保留 .github、.gitignore 等点目录/文件。原始.blend、贴图/照片/字体、成片、缓存、日志、个人配置和生成的demo输入都不在包里。导出前对候选源码做凭据/个人路径启发式检查，遇到命中会停止，不输出凭据内容；这不代替人工审阅。

将包解压到新的空目录，再选择 GitHub 网页上传或 Git 命令。仓库名与公开可见性由你确定，本次未替你创建或推送。

Git 命令示例（自行填写真正仓库URL）：

```sh
git init
git add --dry-run .
git add .
git commit -m "Publish configurable city geography film source"
git branch -M main
git remote add origin YOUR_REPOSITORY_URL
git push -u origin main
```

GitHub Actions 在 push / pull request 时运行 Python 3.12 和3.13源码检查、几何测试、配置与演示预处理；不下载私有资源，也不声称在CI渲染完整影片。工作流仅申请 contents:read。它已完成本机相同步骤验证，尚未在远端GitHub实际运行。

别人克隆源码后可以直接按 city-migration.md 运行离线合成演示；复现原南京成片则需另行准备具备分发依据的原资产。源码发布与完整原资产发布是两件需要分别核查的事项。原目录没有Git历史，本次不能证明其他旧仓库/远端历史无敏感内容。
