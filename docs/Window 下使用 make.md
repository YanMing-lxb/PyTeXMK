

## Windows 使用 make

在 Windows 中使用 make 需要用 MinGW-w64，但是 MinGW-w64 没有打包好的程序，一般附加在其他软件中，如 Strawberry 中。首先在 CMD 终端中查找是否存在 MinGW-w64，输入以下命令：
```cmd
where mingw32-make.exe
```
结果显示示例：
```cmd
C:\Applications\Strawberry\c\bin\mingw32-make.exe
```
然后将 `mingw32-make.exe` 文件复制一份，然后重命名为 `make.exe` 方便在 CMD 中使用 make。