# NTE Auto-Fishing (NTE 自动钓鱼)

基于 Python + OpenCV + MSS + DearPyGui 的高性能自动化钓鱼方案。

## 🌟 新特性
- **可视化控制面板 (GUI)**：提供实时的状态监控、PID 参数调节和 HSV 颜色阈值调节。
- **参数保存与加载**：在 GUI 中一键保存配置，下次启动自动应用。
- **智能分辨率适配**：即使模板匹配失败，也能根据当前屏幕分辨率自动推算钓鱼UI坐标，支持 1080P/2K/4K 等多种分辨率比例。

## 📁 项目架构
- `start_gui.py`: GUI 模式启动入口（推荐）
- `main.py`: Headless (无界面) 模式启动入口与主程序逻辑
- `config.py`: 全局配置对象 (PID参数、HSV阈值等)
- `gui/`: 包含 DearPyGui 的界面面板设计与通信桥 (BotBridge)
- `modules/`:
  - `io_module.py`: 极速截屏 (MSS) 与 键鼠模拟 (PyDirectInput)
  - `vision.py`: 视觉处理（多尺度模板匹配、颜色追踪）
  - `logic.py`: PID 控制器实现与状态机

## 🚀 使用说明

### 方法 1：使用预编译的 EXE（推荐给普通用户）
在项目的 [Releases](https://github.com/) 页面下载最新构建的压缩包，解压后直接以**管理员权限**运行 `start_gui.exe` 即可，无需安装 Python 环境。

### 方法 2：源码运行（面向开发者）
1. **安装依赖**:
   ```bash
   pip install -r requirements.txt
   ```
2. **准备模板**:
   - 确保 `templates/` 文件夹下包含 `button_f.png`（抛竿按钮）和 `bar_icon_left.png`（进度条左侧图标）。脚本启动时会进行自适应校准，若匹配失败将自动退化为分辨率推算。
3. **运行脚本**:
   - 以**管理员权限**运行终端（因为 `PyDirectInput` 需要高级权限来模拟键鼠操作）。
   - 启动游戏并进入钓鱼区域。
   - 运行带界面的控制台：
     ```bash
     python start_gui.py
     ```
   - 或者运行无界面模式：
     ```bash
     python main.py
     ```

## ⚙️ 界面功能
- **Dashboard**：查看当前钓鱼状态、成功次数、Bot 运行时长等。
- **Settings**：
  - **PID 控制器**：调节拉杆力度反应。抖动过大减小 Kp/Ki，反应太慢增大 Kp。
  - **HSV 阈值**：调节不同环境光下的颜色识别范围（安全区为青色、游标为黄色、咬钩为蓝色）。
  - 点击 `Save Settings` 即可持久化保存配置到本地 `settings.json`。
- **Logs**：实时查看后台日志输出。

## ⚠️ 注意事项
- 必须以**管理员权限**运行，否则无法在游戏中模拟鼠标点击和按键。
- 建议游戏运行在**无边框窗口化**或**窗口化全屏**模式，以便脚本更好地进行屏幕捕获。
- GitHub Actions 会自动在每次推送后打包最新的可执行文件。
