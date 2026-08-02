# Developer Notes（开发者私人备忘）

> 本文件存放从 `src/pytexmk/__init__.py` 迁移而来的私人吐槽与打包命令备忘，原文未作任何修改。

---

## 私人吐槽

不能再在这个程序上花时间了, 该看论文学技术了, 要不然博士怎么毕业啊, 吐了。---- 焱铭,2024-07-28 21:02:30
吐了, 又在这个功能上花费了一上午的时间。---- 焱铭,2024-08-02 12:48:23
吐了啊，又搞了两天，我该好好学学 CAN 通信了，该死的强迫症，啊啊啊啊啊啊！ ---- 焱铭,2024-08-07 21:40:29
回家的这几天，尽量更新更新，把一些必要的大块的功能完善一下，开学后尽量只进行小修小改。 ---- 焱铭,2024-08-16 20:20:48

好吧，前两天博士阶段的第一篇sci终于投出去了，这两天改一改pytexmk吧，正好发现 TARE WORK 很好用，我来用这个软件来优化这个程序吧！
我把日志解析功能完善了，另外我给他独立出去了，独立成一个单独的第三方库，方便我管理如果别人想用也可以用。
好吧！这几天改一改pytexmk吧！
---- 焱铭,2026-08-01 22:13:20

---

## 打包命令备忘

```
python -m nuitka --standalone --onefile --nofollow-import-to=numpy --remove-output --include-data-dir=./src/pytexmk/data=data --include-data-dir=./src/pytexmk/locale/=locale --company-name="YanMing" --product-name="pytexmk-cli" --file-version="1.0" --product-version="1.0" --file-description="LaTeX 编译 CLI 工具" ./src/pytexmk/__main__.py 
```

```
pipreqs ./src/pytexmk/ --encoding=utf8  --force
```

## `__init__.py` ASCII banner（已迁出）
