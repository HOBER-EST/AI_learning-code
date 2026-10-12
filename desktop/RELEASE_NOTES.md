## 61A 递归实验室

面向 UC Berkeley CS61A 学习者的桌面学习平台：编写或上传 Python 代码，自动运行测试，逐步可视化递归调用和环境图（Environment Diagram），并围绕递归（Recursion）、链表（Link）和树（Tree）提供交互式练习与 AI 导师。**无需安装 Python 或 Node。**

### 下载

| 系统 | 文件 |
| --- | --- |
| Windows（64 位） | `Learn61A-windows-x86_64.zip` |
| macOS（Apple 芯片） | `Learn61A-macos-arm64.zip` |
| Linux（x86_64） | `Learn61A-linux-x86_64.tar.gz` |

解压后启动：

- **Windows**：双击 `Learn61A` 文件夹中的 `Learn61A.exe`。若出现“Windows 已保护你的电脑”，点 **更多信息 → 仍要运行**。
- **macOS**：把 `Learn61A.app` 拖进“应用程序”，第一次**右键点击 → 打开**，在弹窗中再点“打开”。
- **Linux**：运行 `Learn61A/Learn61A`（系统缺少 GTK/Qt 网页组件时会改用浏览器打开）。

安装包未经过 Apple / 微软的付费代码签名，所以首次打开需要按上面的步骤放行。

### 主要功能

- **代码实验室**：编写、上传或拖入 `.py` 文件，上传后自动运行 doctest 与 `test_` 函数。
- **递归可视化**：单步执行，CS61A 风格的环境图（帧、parent、返回值、指针箭头，`Link` 盒子-指针链、`Tree` 树形），以及随执行生长的递归调用树（标出重复子问题）；每一步变化的变量和对象会高亮。
- **22 道练习**：递归 8、链表 6、树 8，带隐藏测试、代码要求、渐进提示、参考答案和进度记录。
- **17 道 WWPD 测验**：What Would Python Display?
- **讲解代码**：讲解整段或选中的几行，先真实运行再讲解，可以继续追问。
- **AI 导师**：离线规则诊断常见递归错误；在“设置”中填写 Anthropic API key 后由 Claude 讲解和答疑。
- **安全运行**：代码在受限的独立进程中运行，有时间限制，禁止写文件、子进程和网络访问。

完整使用说明见仓库中的 [docs/USAGE.md](https://github.com/HOBER-EST/AI_learning-code/blob/v1.0.0/docs/USAGE.md)，程序内“使用说明”页面也可查看。
