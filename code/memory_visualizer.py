import tkinter as tk
from tkinter import ttk, messagebox
import random
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import deque
import time
import math

# Constants
MEMORY_SIZE = 100  # Total memory size
BLOCK_HEIGHT = 30  # Increased height for better visibility
BLOCK_WIDTH = 3    # Scaling factor for block visualization
MAX_MEMORY_SIZE = 1000  # Maximum allowed memory size
PAGE_SIZE = 10  # Size of each page for paging visualization

class BuddyBlock:
    def __init__(self, start, size, status="free", process_id=None):
        self.start = start
        self.size = size
        self.status = status
        self.process_id = process_id
        self.split = False
        self.left = None
        self.right = None
        self.parent = None

class Process:
    def __init__(self, pid, size, priority=1):
        self.pid = pid
        self.size = size
        self.priority = priority
        self.wait_time = 0
        self.creation_time = time.time()
        self.pages = []  # For paging visualization
        self.last_access_time = time.time()
        self.access_count = 0

class MemoryBlock:
    def __init__(self, start, size, status="free", process_id=None):
        self.start = start
        self.size = size
        self.status = status
        self.process_id = process_id
        self.internal_fragmentation = 0
        self.protection_bits = "RWX"  # Read, Write, Execute permissions
        self.last_access_time = time.time()
        self.access_count = 0
        self.is_leaked = False

class MemoryManager:
    def __init__(self):
        self.memory = [MemoryBlock(0, MEMORY_SIZE, "free")]
        self.algorithm = "first_fit"
        self.process_counter = 1
        self.process_colors = {}
        self.process_queue = deque()
        self.allocation_history = []
        self.start_time = time.time()
        self.buddy_root = BuddyBlock(0, MEMORY_SIZE)
        self.page_table = {}  # For paging visualization
        self.leak_threshold = 300  # 5 minutes in seconds
        self.leak_check_interval = 60  # 1 minute in seconds
        self.last_leak_check = time.time()

    def get_process_color(self, process_id):
        if process_id not in self.process_colors:
            r = random.randint(180, 255)
            g = random.randint(180, 255)
            b = random.randint(180, 255)
            self.process_colors[process_id] = f'#{r:02x}{g:02x}{b:02x}'
        return self.process_colors[process_id]

    def reset(self):
        self.memory = [MemoryBlock(0, MEMORY_SIZE, "free")]
        self.process_counter = 1
        self.process_colors.clear()
        self.process_queue.clear()
        self.allocation_history.clear()

    def compact_memory(self):
        """Compact memory by moving allocated blocks together"""
        # Create a new list with all allocated blocks first, then free blocks
        allocated_blocks = []
        free_blocks = []
        
        for block in self.memory:
            if block.status == "allocated":
                allocated_blocks.append(block)
            else:
                free_blocks.append(block)
        
        # Sort allocated blocks by start address
        allocated_blocks.sort(key=lambda x: x.start)
        
        # Reassign start addresses
        current_start = 0
        for block in allocated_blocks:
            block.start = current_start
            current_start += block.size
        
        # Combine all free blocks at the end
        if free_blocks:
            total_free = sum(block.size for block in free_blocks)
            self.memory = allocated_blocks + [MemoryBlock(current_start, total_free, "free")]
        else:
            self.memory = allocated_blocks
        
        return True

    def add_to_queue(self, size, priority=1):
        """Add a process to the waiting queue"""
        process = Process(f"P{self.process_counter}", size, priority)
        self.process_queue.append(process)
        self.process_counter += 1
        return process.pid

    def process_queue(self):
        """Process waiting queue items"""
        if not self.process_queue:
            return
        
        # Sort queue by priority and wait time
        sorted_queue = sorted(
            self.process_queue,
            key=lambda x: (x.priority, x.wait_time),
            reverse=True
        )
        
        # Try to allocate memory for highest priority process
        process = sorted_queue[0]
        success, _ = self.allocate_memory(process.size)
        
        if success:
            self.process_queue.remove(process)
        else:
            process.wait_time += 1

    def allocate_memory(self, size):
        """Allocate memory with current algorithm"""
        process_id = f"P{self.process_counter}"
        self.process_counter += 1
        
        if self.algorithm == "buddy":
            success = self.buddy_allocate(size)
        elif self.algorithm == "first_fit":
            success = self.first_fit(size, process_id)
        elif self.algorithm == "best_fit":
            success = self.best_fit(size, process_id)
        elif self.algorithm == "worst_fit":
            success = self.worst_fit(size, process_id)
        
        if success:
            # Record allocation in history
            self.allocation_history.append({
                'time': time.time() - self.start_time,
                'size': size,
                'process_id': process_id,
                'fragmentation': self.calculate_fragmentation()
            })
        
        return success, process_id if success else None

    def first_fit(self, size, process_id):
        """First-fit allocation strategy"""
        for block in self.memory:
            if block.status == "free" and block.size >= size:
                self.split_block(block, size, process_id)
                return True
        return False

    def best_fit(self, size, process_id):
        """Best-fit allocation strategy"""
        best_block = None
        for block in self.memory:
            if block.status == "free" and block.size >= size:
                if best_block is None or block.size < best_block.size:
                    best_block = block
        if best_block:
            self.split_block(best_block, size, process_id)
            return True
        return False

    def worst_fit(self, size, process_id):
        """Worst-fit allocation strategy"""
        worst_block = None
        for block in self.memory:
            if block.status == "free" and block.size >= size:
                if worst_block is None or block.size > worst_block.size:
                    worst_block = block
        if worst_block:
            self.split_block(worst_block, size, process_id)
            return True
        return False

    def split_block(self, block, size, process_id):
        """Split memory block when allocating"""
        if block.size > size:
            new_block = MemoryBlock(
                block.start + size,
                block.size - size,
                "free"
            )
            self.memory.insert(self.memory.index(block) + 1, new_block)
        
        block.size = size
        block.status = "allocated"
        block.process_id = process_id
        block.internal_fragmentation = 0  # Reset internal fragmentation

    def deallocate_memory(self, process_id):
        """Deallocate all blocks belonging to a process"""
        deallocated = False
        for block in self.memory:
            if block.process_id == process_id and block.status == "allocated":
                block.status = "free"
                block.process_id = None
                deallocated = True
        
        if deallocated:
            self.merge_free_blocks()
        return deallocated

    def merge_free_blocks(self):
        """Combine adjacent free blocks"""
        i = 0
        while i < len(self.memory) - 1:
            current = self.memory[i]
            next_block = self.memory[i + 1]
            
            if current.status == "free" and next_block.status == "free":
                current.size += next_block.size
                del self.memory[i + 1]
            else:
                i += 1

    def calculate_fragmentation(self):
        """Calculate external fragmentation percentage"""
        free_blocks = [
            block.size for block in self.memory 
            if block.status == "free"
        ]
        
        if not free_blocks:
            return 0.0
            
        largest_free_block = max(free_blocks)
        total_free = sum(free_blocks)
        return (1 - (largest_free_block / total_free)) * 100

    def calculate_internal_fragmentation(self):
        """Calculate internal fragmentation for each block"""
        total_internal = 0
        for block in self.memory:
            if block.status == "allocated":
                # Assuming 4-byte alignment
                alignment = 4
                block.internal_fragmentation = (alignment - (block.size % alignment)) % alignment
                total_internal += block.internal_fragmentation
        return total_internal

    def buddy_allocate(self, size):
        """Buddy system allocation"""
        # Find the smallest power of 2 that can hold the requested size
        requested_size = 2 ** math.ceil(math.log2(size))
        
        def find_buddy_block(block, size):
            if block.size == size and block.status == "free":
                return block
            if block.size > size and not block.split:
                # Split the block
                block.split = True
                block.left = BuddyBlock(block.start, block.size // 2)
                block.right = BuddyBlock(block.start + block.size // 2, block.size // 2)
                block.left.parent = block
                block.right.parent = block
            if block.left:
                result = find_buddy_block(block.left, size)
                if result:
                    return result
            if block.right:
                result = find_buddy_block(block.right, size)
                if result:
                    return result
            return None

        block = find_buddy_block(self.buddy_root, requested_size)
        if block:
            block.status = "allocated"
            block.process_id = f"P{self.process_counter}"
            self.process_counter += 1
            return True, block.process_id
        return False, None

    def buddy_deallocate(self, process_id):
        """Buddy system deallocation"""
        def find_and_free_block(block, pid):
            if block.process_id == pid:
                block.status = "free"
                block.process_id = None
                return True
            if block.left:
                if find_and_free_block(block.left, pid):
                    return True
            if block.right:
                if find_and_free_block(block.right, pid):
                    return True
            return False

        success = find_and_free_block(self.buddy_root, process_id)
        if success:
            self.merge_buddy_blocks(self.buddy_root)
        return success

    def merge_buddy_blocks(self, block):
        """Merge buddy blocks if both are free"""
        if block.split:
            if (block.left.status == "free" and block.right.status == "free" and
                not block.left.split and not block.right.split):
                block.split = False
                block.left = None
                block.right = None

    def check_memory_leaks(self):
        """Check for potential memory leaks"""
        current_time = time.time()
        if current_time - self.last_leak_check >= self.leak_check_interval:
            for block in self.memory:
                if block.status == "allocated":
                    # Check if block hasn't been accessed recently
                    if current_time - block.last_access_time > self.leak_threshold:
                        block.is_leaked = True
            self.last_leak_check = current_time

    def access_memory(self, process_id):
        """Record memory access for leak detection"""
        for block in self.memory:
            if block.process_id == process_id:
                block.last_access_time = time.time()
                block.access_count += 1
                block.is_leaked = False
                return True
        return False

    def get_page_table(self, process_id):
        """Get page table for a process"""
        if process_id not in self.page_table:
            self.page_table[process_id] = []
        return self.page_table[process_id]

    def allocate_pages(self, process_id, size):
        """Allocate pages for a process"""
        num_pages = math.ceil(size / PAGE_SIZE)
        pages = []
        for i in range(num_pages):
            page = {
                'page_number': i,
                'frame_number': len(pages),
                'valid': True,
                'modified': False,
                'accessed': False
            }
            pages.append(page)
        self.page_table[process_id] = pages
        return pages

class MemoryVisualizer:
    def __init__(self, root):
        self.root = root
        self.root.title("Dynamic Memory Management Visualizer")
        self.memory_manager = MemoryManager()

        # Configure main window
        self.root.geometry("800x600")
        
        # Create main frames
        control_frame = ttk.LabelFrame(root, text="Controls", padding=10)
        control_frame.pack(fill="x", padx=10, pady=5)
        
        # Create canvas with scrollbar
        canvas_frame = ttk.Frame(root)
        canvas_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.canvas = tk.Canvas(
            canvas_frame,
            bg="white",
            highlightthickness=1,
            highlightbackground="black"
        )
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        
        # Control widgets
        ttk.Label(control_frame, text="Memory Size:").grid(row=0, column=0, padx=5)
        self.size_entry = ttk.Entry(control_frame, width=10)
        self.size_entry.grid(row=0, column=1, padx=5)
        
        ttk.Label(control_frame, text="Process ID:").grid(row=0, column=2, padx=5)
        self.process_entry = ttk.Entry(control_frame, width=10)
        self.process_entry.grid(row=0, column=3, padx=5)
        
        self.allocate_button = ttk.Button(
            control_frame, 
            text="Allocate", 
            command=self.allocate
        )
        self.allocate_button.grid(row=0, column=4, padx=5)
        
        self.deallocate_button = ttk.Button(
            control_frame, 
            text="Deallocate", 
            command=self.deallocate
        )
        self.deallocate_button.grid(row=0, column=5, padx=5)
        
        self.reset_button = ttk.Button(
            control_frame,
            text="Reset",
            command=self.reset_memory
        )
        self.reset_button.grid(row=0, column=6, padx=5)
        
        # Algorithm selection
        ttk.Label(control_frame, text="Algorithm:").grid(row=1, column=0, padx=5)
        self.algorithm_var = tk.StringVar(value="first_fit")
        algorithm_menu = ttk.OptionMenu(
            control_frame,
            self.algorithm_var,
            "first_fit",
            "first_fit",
            "best_fit",
            "worst_fit"
        )
        algorithm_menu.grid(row=1, column=1, columnspan=2, padx=5, sticky="ew")
        
        # Legend frame
        legend_frame = ttk.LabelFrame(control_frame, text="Legend", padding=5)
        legend_frame.grid(row=1, column=3, columnspan=4, padx=5, sticky="ew")
        
        # Add legend items
        ttk.Label(legend_frame, text="Free Memory", background="light green").pack(side="left", padx=5)
        ttk.Label(legend_frame, text="Allocated Memory", background="salmon").pack(side="left", padx=5)
        
        # Statistics display
        self.stats_label = ttk.Label(root, text="", font=('Helvetica', 10))
        self.stats_label.pack(pady=5)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(root, textvariable=self.status_var, relief="sunken")
        self.status_bar.pack(fill="x", padx=10, pady=2)
        
        # Bind hover events
        self.canvas.bind("<Motion>", self.on_hover)
        
        # Add compaction button
        self.compact_button = ttk.Button(
            control_frame,
            text="Compact Memory",
            command=self.compact_memory
        )
        self.compact_button.grid(row=0, column=7, padx=5)
        
        # Add process queue display
        queue_frame = ttk.LabelFrame(root, text="Process Queue", padding=5)
        queue_frame.pack(fill="x", padx=10, pady=5)
        
        self.queue_text = tk.Text(queue_frame, height=3, width=50)
        self.queue_text.pack(fill="x", padx=5, pady=5)
        
        # Add statistics graph
        self.fig, self.ax = plt.subplots(figsize=(6, 2))
        self.canvas = FigureCanvasTkAgg(self.fig, master=root)
        self.canvas.get_tk_widget().pack(fill="x", padx=10, pady=5)
        
        # Add memory protection controls
        protection_frame = ttk.LabelFrame(control_frame, text="Memory Protection", padding=5)
        protection_frame.grid(row=2, column=0, columnspan=8, padx=5, sticky="ew")
        
        ttk.Label(protection_frame, text="Process:").pack(side="left", padx=5)
        self.protection_process = ttk.Entry(protection_frame, width=10)
        self.protection_process.pack(side="left", padx=5)
        
        self.read_var = tk.BooleanVar(value=True)
        self.write_var = tk.BooleanVar(value=True)
        self.execute_var = tk.BooleanVar(value=True)
        
        ttk.Checkbutton(protection_frame, text="Read", variable=self.read_var).pack(side="left", padx=5)
        ttk.Checkbutton(protection_frame, text="Write", variable=self.write_var).pack(side="left", padx=5)
        ttk.Checkbutton(protection_frame, text="Execute", variable=self.execute_var).pack(side="left", padx=5)
        
        ttk.Button(
            protection_frame,
            text="Set Protection",
            command=self.set_protection
        ).pack(side="left", padx=5)
        
        # Add buddy system visualization
        buddy_frame = ttk.LabelFrame(root, text="Buddy System Visualization", padding=5)
        buddy_frame.pack(fill="x", padx=10, pady=5)
        
        self.buddy_canvas = tk.Canvas(
            buddy_frame,
            bg="white",
            height=100,
            highlightthickness=1,
            highlightbackground="black"
        )
        self.buddy_canvas.pack(fill="x", padx=5, pady=5)
        
        # Add paging visualization
        paging_frame = ttk.LabelFrame(root, text="Paging Visualization", padding=5)
        paging_frame.pack(fill="x", padx=10, pady=5)
        
        self.paging_text = tk.Text(paging_frame, height=4, width=50)
        self.paging_text.pack(fill="x", padx=5, pady=5)
        
        # Add leak detection controls
        leak_frame = ttk.LabelFrame(control_frame, text="Memory Leak Detection", padding=5)
        leak_frame.grid(row=3, column=0, columnspan=8, padx=5, sticky="ew")
        
        ttk.Label(leak_frame, text="Leak Threshold (seconds):").pack(side="left", padx=5)
        self.leak_threshold = ttk.Entry(leak_frame, width=10)
        self.leak_threshold.insert(0, "300")
        self.leak_threshold.pack(side="left", padx=5)
        
        ttk.Button(
            leak_frame,
            text="Check for Leaks",
            command=self.check_leaks
        ).pack(side="left", padx=5)
        
        # Add help button
        help_button = ttk.Button(
            control_frame,
            text="Help",
            command=self.show_help
        )
        help_button.grid(row=0, column=8, padx=5)
        
        # Add tooltips
        self.create_tooltips()
        
        # Start periodic leak checking
        self.root.after(60000, self.periodic_leak_check)
        
        # Initial visualization
        self.update_visualization()

    def reset_memory(self):
        """Reset memory to initial state"""
        self.memory_manager.reset()
        self.process_entry.delete(0, tk.END)
        self.size_entry.delete(0, tk.END)
        self.update_visualization()
        self.status_var.set("Memory reset to initial state")

    def on_hover(self, event):
        """Handle mouse hover events"""
        # Convert canvas coordinates to memory block coordinates
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        # Find the block under the cursor
        y = 10
        for block in self.memory_manager.memory:
            x1, y1 = 10, y
            x2, y2 = 10 + block.size * BLOCK_WIDTH, y + BLOCK_HEIGHT
            
            if (x1 <= canvas_x <= x2 and y1 <= canvas_y <= y2):
                details = f"Start: {block.start}, Size: {block.size}, Status: {block.status}"
                if block.process_id:
                    details += f", Process: {block.process_id}"
                self.status_var.set(details)
                return
                
            y += BLOCK_HEIGHT + 5
        
        self.status_var.set("Ready")

    def allocate(self):
        """Handle memory allocation"""
        try:
            size = int(self.size_entry.get())
            if size <= 0:
                messagebox.showerror("Error", "Size must be positive")
                return
            if size > MAX_MEMORY_SIZE:
                messagebox.showerror("Error", f"Size cannot exceed {MAX_MEMORY_SIZE} units")
                return
            
            success, process_id = self.memory_manager.allocate_memory(size)
            if success:
                self.process_entry.delete(0, tk.END)
                self.process_entry.insert(0, process_id)
                self.status_var.set(f"Successfully allocated {size} units to {process_id}")
            else:
                self.status_var.set("Failed to allocate memory - not enough contiguous space")
                messagebox.showerror("Error", "Not enough contiguous memory")
            
            self.update_visualization()
        except ValueError:
            self.status_var.set("Error: Please enter a valid size")
            messagebox.showerror("Error", "Please enter a valid size")

    def deallocate(self):
        """Handle memory deallocation"""
        process_id = self.process_entry.get()
        if not process_id:
            self.status_var.set("Error: Please enter a Process ID")
            messagebox.showerror("Error", "Please enter a Process ID")
            return
        
        if self.memory_manager.deallocate_memory(process_id):
            self.status_var.set(f"Successfully deallocated memory for {process_id}")
            self.process_entry.delete(0, tk.END)
        else:
            self.status_var.set(f"Failed to deallocate - no blocks found for {process_id}")
            messagebox.showerror("Error", f"No allocated blocks found for {process_id}")
        
        self.update_visualization()

    def compact_memory(self):
        """Handle memory compaction"""
        if self.memory_manager.compact_memory():
            self.status_var.set("Memory compacted successfully")
            self.update_visualization()
        else:
            self.status_var.set("Compaction failed")

    def set_protection(self):
        """Set memory protection bits for a process"""
        process_id = self.protection_process.get()
        if not process_id:
            messagebox.showerror("Error", "Please enter a Process ID")
            return
        
        protection = ""
        if self.read_var.get(): protection += "R"
        if self.write_var.get(): protection += "W"
        if self.execute_var.get(): protection += "X"
        
        for block in self.memory_manager.memory:
            if block.process_id == process_id:
                block.protection_bits = protection
                self.status_var.set(f"Protection set to {protection} for {process_id}")
                self.update_visualization()
                return
        
        messagebox.showerror("Error", f"No blocks found for process {process_id}")

    def update_queue_display(self):
        """Update the process queue display"""
        self.queue_text.delete("1.0", tk.END)
        for process in self.memory_manager.process_queue:
            self.queue_text.insert(tk.END, 
                f"Process {process.pid} (Size: {process.size}, Priority: {process.priority}, Wait: {process.wait_time}s)\n")

    def update_statistics_graph(self):
        """Update the statistics graph"""
        self.ax.clear()
        if self.memory_manager.allocation_history:
            times = [entry['time'] for entry in self.memory_manager.allocation_history]
            fragmentation = [entry['fragmentation'] for entry in self.memory_manager.allocation_history]
            self.ax.plot(times, fragmentation, 'b-')
            self.ax.set_title("Memory Fragmentation Over Time")
            self.ax.set_xlabel("Time (s)")
            self.ax.set_ylabel("Fragmentation (%)")
        self.canvas.draw()

    def update_buddy_visualization(self):
        """Update buddy system visualization"""
        self.buddy_canvas.delete("all")
        
        def draw_buddy_block(block, x, y, width, height):
            if not block:
                return
            
            # Draw the block
            color = "light green" if block.status == "free" else self.memory_manager.get_process_color(block.process_id)
            self.buddy_canvas.create_rectangle(x, y, x + width, y + height, fill=color)
            
            # Add block information
            text = f"{block.size}\n{block.process_id if block.process_id else 'Free'}"
            self.buddy_canvas.create_text(x + width/2, y + height/2, text=text, justify="center")
            
            # Draw children if split
            if block.split:
                draw_buddy_block(block.left, x, y + height, width/2, height/2)
                draw_buddy_block(block.right, x + width/2, y + height, width/2, height/2)
        
        draw_buddy_block(self.memory_manager.buddy_root, 10, 10, 780, 80)

    def update_paging_visualization(self):
        """Update paging visualization"""
        self.paging_text.delete("1.0", tk.END)
        
        for process_id, pages in self.memory_manager.page_table.items():
            self.paging_text.insert(tk.END, f"Process {process_id} Page Table:\n")
            for page in pages:
                status = "Valid" if page['valid'] else "Invalid"
                modified = "M" if page['modified'] else "-"
                accessed = "A" if page['accessed'] else "-"
                self.paging_text.insert(tk.END, 
                    f"Page {page['page_number']} -> Frame {page['frame_number']} [{status}] [{modified}{accessed}]\n")
            self.paging_text.insert(tk.END, "\n")

    def update_visualization(self):
        """Update the memory visualization"""
        self.canvas.delete("all")
        y = 10
        
        # Draw each memory block
        for block in self.memory_manager.memory:
            # Determine block color and text
            if block.status == "free":
                color = "light green"
                text = f"Free\n{block.size} units"
            else:
                color = self.memory_manager.get_process_color(block.process_id)
                text = f"{block.process_id}\n{block.size} units"
            
            # Draw the block
            x1, y1 = 10, y
            x2, y2 = 10 + block.size * BLOCK_WIDTH, y + BLOCK_HEIGHT
            self.canvas.create_rectangle(x1, y1, x2, y2, fill=color)
            
            # Add block information
            self.canvas.create_text(
                (x1 + x2) / 2, 
                (y1 + y2) / 2, 
                text=text,
                justify="center"
            )
            
            # Add start address
            self.canvas.create_text(
                x1 + 5,
                y1 + 5,
                text=f"{block.start}",
                anchor="nw",
                font=('Helvetica', 8)
            )
            
            y += BLOCK_HEIGHT + 5
        
        # Update canvas scroll region
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
        # Update statistics
        total_memory = MEMORY_SIZE
        used_memory = sum(
            block.size for block in self.memory_manager.memory 
            if block.status == "allocated"
        )
        free_memory = total_memory - used_memory
        fragmentation = self.memory_manager.calculate_fragmentation()
        
        # Update additional displays
        self.update_queue_display()
        self.update_statistics_graph()
        self.update_buddy_visualization()
        self.update_paging_visualization()
        
        # Update leak detection status
        leaked_blocks = [block for block in self.memory_manager.memory if block.is_leaked]
        if leaked_blocks:
            self.status_var.set("WARNING: Memory leaks detected!")
        
        # Add internal fragmentation to statistics
        internal_frag = self.memory_manager.calculate_internal_fragmentation()
        stats_text = (
            f"Total Memory: {total_memory} units | "
            f"Used: {used_memory} units | "
            f"Free: {free_memory} units | "
            f"External Fragmentation: {fragmentation:.1f}% | "
            f"Internal Fragmentation: {internal_frag} bytes"
        )
        self.stats_label.config(text=stats_text)

    def create_tooltips(self):
        """Create tooltips for UI elements"""
        tooltips = {
            self.allocate_button: "Allocate memory for a new process",
            self.deallocate_button: "Free memory allocated to a process",
            self.reset_button: "Reset memory to initial state",
            self.compact_button: "Compact memory to reduce fragmentation",
            self.leak_threshold: "Time threshold for memory leak detection (in seconds)"
        }
        
        for widget, text in tooltips.items():
            self.create_tooltip(widget, text)

    def create_tooltip(self, widget, text):
        """Create a tooltip for a widget"""
        def show_tooltip(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            
            label = ttk.Label(tooltip, text=text, background="#ffffe0", relief="solid", borderwidth=1)
            label.pack()
            
            def hide_tooltip():
                tooltip.destroy()
            
            widget.tooltip = tooltip
            widget.bind('<Leave>', lambda e: hide_tooltip())
        
        widget.bind('<Enter>', show_tooltip)

    def show_help(self):
        """Show help window with explanations"""
        help_window = tk.Toplevel(self.root)
        help_window.title("Memory Management Help")
        help_window.geometry("600x400")
        
        help_text = """
Memory Management Visualizer Help

1. Memory Allocation Algorithms:
   - First Fit: Allocates the first block that fits
   - Best Fit: Allocates the smallest block that fits
   - Worst Fit: Allocates the largest block that fits
   - Buddy System: Uses power-of-2 sized blocks

2. Memory Protection:
   - R: Read permission
   - W: Write permission
   - X: Execute permission

3. Memory Leak Detection:
   - Monitors memory blocks not accessed for threshold time
   - Helps identify potential memory leaks

4. Paging:
   - Visualizes memory paging
   - Shows page tables and frame allocation

5. Memory Compaction:
   - Reduces external fragmentation
   - Moves allocated blocks together

6. Process Queue:
   - Shows pending memory requests
   - Priority-based scheduling
"""
        
        text_widget = tk.Text(help_window, wrap=tk.WORD, padx=10, pady=10)
        text_widget.pack(fill="both", expand=True)
        text_widget.insert("1.0", help_text)
        text_widget.config(state="disabled")

    def check_leaks(self):
        """Check for memory leaks"""
        try:
            threshold = int(self.leak_threshold.get())
            self.memory_manager.leak_threshold = threshold
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid threshold value")
            return
        
        self.memory_manager.check_memory_leaks()
        leaked_blocks = [block for block in self.memory_manager.memory if block.is_leaked]
        
        if leaked_blocks:
            message = "Potential memory leaks detected:\n"
            for block in leaked_blocks:
                message += f"Process {block.process_id}: {block.size} units\n"
            messagebox.showwarning("Memory Leak Warning", message)
        else:
            messagebox.showinfo("Memory Leak Check", "No memory leaks detected")
        
        self.update_visualization()

    def periodic_leak_check(self):
        """Periodically check for memory leaks"""
        self.check_leaks()
        self.root.after(60000, self.periodic_leak_check)

if __name__ == "__main__":
    root = tk.Tk()
    app = MemoryVisualizer(root)
    root.mainloop() 