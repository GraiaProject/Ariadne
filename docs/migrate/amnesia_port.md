# 0.7.0 移植手册

1. 更改你的入口点文件以符合 `0.7.0` 的方法
2. 从发布页获取 `migrator.py` (源代码仓库的 `migration_src/migrator.py`)
3. 在你的代码根目录运行 `python migrator.py .`
4. 对照着输出的 diff 或者自动改的代码副本进行调整, 包括 `Adapter` 和 `get_running` 的残留使用.
5. 试着运行并进行修改, 确保自己的代码中没有混用. (混用会有警告日志)
6. 迁移完成
