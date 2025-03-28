# Dynamic Memory Management Visualizer

Ever wondered how your computer manages memory? This project is a visual journey into the world of memory management! Built as part of my Operating Systems course project, this tool helps students and developers understand how different memory allocation strategies work in practice.

## What's This All About?

This isn't just another memory management tool - it's an interactive playground where you can experiment with different memory allocation strategies and see exactly how they work. Whether you're a student trying to wrap your head around memory management concepts or a developer looking to visualize memory allocation patterns, this tool is designed to make complex concepts more accessible.

### Why I Built This

During my Operating Systems course, I found that understanding memory management concepts through textbooks alone was challenging. I wanted to create something that would make these concepts more tangible and easier to understand. This visualization tool is the result of that effort.

## Features

### 1. Memory Allocation Strategies
- First-fit, Best-fit, Worst-fit, and Next-fit algorithms
- Dynamic memory allocation and deallocation
- Visual representation of memory blocks
- Real-time visualization of how each algorithm makes decisions

### 2. Paging System
- Configurable page size and maximum pages
- FIFO and LRU page replacement algorithms
- Page table visualization
- Page fault simulation
- See exactly how pages are loaded and replaced

### 3. Segmentation System
- Named segment creation
- Segment visualization
- Page allocation within segments
- Understand how segmentation works in practice

### 4. Visualization Features
- Interactive memory block visualization
- Color-coded process representation
- Zoom controls for detailed inspection
- Process list with detailed information
- Real-time status updates

## Getting Started

### Requirements
- Python 3.x (I developed this using Python 3.8)
- Tkinter (usually comes with Python)

### Installation
1. Clone the repository:
```bash
git clone https://github.com/deepanshu682/Dynamic-Memory-Management-Visualizer.git
```

2. Navigate to the project directory:
```bash
cd Dynamic-Memory-Management-Visualizer
```

3. Run the application:
```bash
python main.py
```

## How to Use It

### Basic Operations

1. **Memory Allocation**:
   - Enter size in "Memory Size" field
   - Click "Allocate" to create new process
   - Select allocation algorithm from dropdown
   - Watch how different algorithms handle the same request!

2. **Memory Deallocation**:
   - Select process from list
   - Click "Deallocate" to free memory
   - See how memory blocks are merged

3. **Paging System**:
   - Switch to "Paging" mode
   - Configure page size and max pages
   - Select replacement algorithm
   - Use page access controls
   - Observe page faults and hits

4. **Segmentation**:
   - Switch to "Segmentation" mode
   - Enter segment name and size
   - Click "Create Segment"
   - See how segments are organized

### Advanced Features

1. **Zoom Control**:
   - Use slider to adjust visualization scale
   - Perfect for examining detailed memory layouts

2. **Configuration Management**:
   - Save/Load configurations via File menu
   - Great for saving interesting scenarios

3. **Process Management**:
   - Double-click processes to select
   - View details in status bar
   - Track process states in real-time

## Project Structure

```
Dynamic-Memory-Management-Visualizer/
├── main.py              # Main application file
└── README.md           # Project documentation
```

## Contributing

I built this tool to help others learn, and I'd love your help to make it even better! Whether you're fixing bugs, adding features, or improving documentation, your contributions are welcome. Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License. Feel free to use it for your own learning or teaching purposes!

## Contact

Your Name - your.email@example.com

Project Link: [https://github.com/deepanshu682/Dynamic-Memory-Management-Visualizer](https://github.com/deepanshu682/Dynamic-Memory-Management-Visualizer)

## Acknowledgments

Special thanks to my Operating Systems professor for the inspiration and guidance. This project wouldn't have been possible without the support of the open-source community and the Python ecosystem. 