# MultiClientViewer

A powerful multi-window monitoring and management tool designed for efficiently viewing and controlling multiple application windows simultaneously. Perfect for managing multiple game clients, work applications, or any scenario requiring simultaneous window monitoring.

## ✨ Key Features

### 🪟 Advanced Window Management
- **Live Thumbnails**: Real-time capture and display of any window on your system
- **Grid Layout**: Organize windows in a customizable 3-5 column grid that auto-scales to your screen
- **Click to Expand**: Instantly bring any window to focus with a single click
- **Smart Auto-Minimize**: Automatically minimize expanded windows when you switch focus
- **Drag to Reorder**: Use ↑/↓ buttons to reorganize your window layout

### 📊 Performance Monitoring
- **Real-time CPU Usage**: Track CPU consumption for each monitored window
- **Status Indicators**: Color-coded dots show window state (Green = Minimized, Red = Active)
- **Movie Mode**: Reduce capture rate from 20 FPS to 5 FPS to save system resources

### 🎨 Customization
- **Theme Support**: Choose between modern Dark and Light themes
- **Accent Colors**: Personalize with custom accent colors
- **Adaptive Sizing**: Thumbnail sizes automatically adjust based on your screen resolution and grid layout
- **Window Position Memory**: Application remembers its position and size between sessions

### 🛠️ Additional Tools
- **Debug Panel**: Access real-time logs and version information
- **Auto-Updates**: Built-in update checker notifies you of new releases
- **Help Documentation**: Comprehensive in-app help guide
- **ChatGPT Integration**: Quick access to AI assistance

## 📥 Download

Head to the [Releases](../../releases) page to download the latest version of `MultiClientViewer.exe`

## 🚀 Installation

1. Download `MultiClientViewer.exe` from the latest release
2. Run the executable - no installation required!
3. Launch any windows you want to monitor and add them through MultiClientViewer

## 💻 Requirements

- **Operating System**: Windows (7/8/10/11)
- **Python Libraries** (if running from source):
  - tkinter
  - Pillow (PIL)
  - pywin32
  - psutil
  - requests

## 📖 Usage Guide

### Getting Started
1. Launch `MultiClientViewer.exe`
2. Click "＋ Add Window" to select windows to monitor
3. Choose from any open application windows
4. Click on thumbnails to expand and focus windows

### Understanding the Interface
- **Green Dot (●)**: Window is minimized (efficient mode)
- **Red Dot (●)**: Window is active/restored (higher resource usage)
- **CPU %**: Real-time CPU usage for each window
- **↑/↓ Buttons**: Reorder windows in your grid
- **✕ Remove**: Stop monitoring a window

### Settings & Customization

Access the ⚙️ Settings menu to customize:
- **Theme**: Dark or Light mode
- **Accent Color**: Choose your preferred highlight color
- **Grid Columns**: 3-5 columns (thumbnails auto-resize)

### Performance Features
- **⚡ Auto-Minimize**: Toggle automatic minimization when clicking away
- **🎬 Movie Mode**: Reduce capture rate to save CPU resources
- **Pause Capturing**: Automatically pauses capture for focused windows to improve performance

## 🔧 Technical Details

### Architecture
- **Multi-threaded Design**: Separate threads for capture, monitoring, and UI updates
- **Efficient Capture**: Uses Windows PrintWindow API for fast, non-intrusive captures
- **Smart Caching**: Optimized update frequency prevents unnecessary captures
- **Memory Management**: In-memory settings and logs eliminate disk I/O

### Capture Technology
- Utilizes Windows GDI+ for high-quality window captures
- Automatically handles window decorations and client areas
- Supports windows in any state (minimized, hidden, background)

## 🐛 Troubleshooting

### Window Not Appearing?
- Ensure the window is not hidden or closed
- Try refreshing the window list by removing and re-adding

### High CPU Usage?
- Enable Movie Mode to reduce capture frequency
- Reduce the number of monitored windows
- Close or minimize the MultiClientViewer when not actively needed

### Capture Quality Issues?
- The tool automatically adjusts capture quality based on window size
- Thumbnails use Lanczos resampling for optimal quality at reduced sizes

## 🤝 Contributing

Found a bug or have a feature request? Please open an issue on this repository with:
- Detailed description of the issue/feature
- Steps to reproduce (for bugs)
- Screenshots if applicable
- Your Windows version and system specs

## ⚖️ Legal & Disclaimer

This tool is designed as a general-purpose window monitoring and management utility. It:
- Does not automate any actions or inputs
- Does not modify other applications
- Simply captures and displays visual content from windows you specify
- Operates entirely within standard Windows APIs

**Users are responsible for ensuring their use complies with:**
- Terms of Service of any monitored applications
- Local laws and regulations
- Applicable EULAs and usage agreements

*This is an independent third-party tool not affiliated with or endorsed by any game developer, publisher, or company whose applications may be monitored using this software.*

## 📄 License

This project is provided as-is for personal use. See [LICENSE](LICENSE) file for details.

## 🔗 Updates & Releases

Check the [Releases](../../releases) page for:
- Latest version downloads
- Changelog and new features
- Bug fixes and improvements

Built-in update checker will notify you when new versions are available!

---

**Version Detection**: The application automatically detects its version from the executable filename (e.g., `MultiClientViewer-v1.0.35.exe`)

**System Requirements**: Windows 7 or newer, .NET Framework (typically pre-installed)
