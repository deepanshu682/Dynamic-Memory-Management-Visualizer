import tkinter as tk
from tkinter import ttk, messagebox
import random
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import deque
import time
import math
import numpy as np

# Constants
MEMORY_SIZE = 100  # Total memory size
BLOCK_HEIGHT = 30  # Increased height for better visibility
BLOCK_WIDTH = 3    # Scaling factor for block visualization
MAX_MEMORY_SIZE = 1000  # Maximum allowed memory size
PAGE_SIZE = 10  # Size of each page for paging visualization
CACHE_SIZE = 20  # Cache memory size
CACHE_LINES = 4  # Number of cache lines
VIRTUAL_MEMORY_SIZE = 200  # Virtual memory size

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
        self.access_pattern = []  # Track access patterns
        self.virtual_address = None  # For virtual memory mapping

class CacheLine:
    def __init__(self, tag, data, valid=True, dirty=False):
        self.tag = tag
        self.data = data
        self.valid = valid
        self.dirty = dirty
        self.last_access = time.time()
        self.access_count = 0

class Cache:
    def __init__(self):
        self.lines = [CacheLine(None, None) for _ in range(CACHE_LINES)]
        self.hits = 0
        self.misses = 0
        self.replacements = 0
        self.write_backs = 0

    def access(self, address, data=None, is_write=False):
        tag = address // CACHE_SIZE
        offset = address % CACHE_SIZE
        
        # Check for hit
        for line in self.lines:
            if line.valid and line.tag == tag:
                line.last_access = time.time()
                line.access_count += 1
                self.hits += 1
                if is_write:
                    line.dirty = True
                    line.data = data
                return True, line.data
        
        # Cache miss
        self.misses += 1
        
        # Find victim line (LRU)
        victim = min(self.lines, key=lambda x: x.last_access)
        
        # Write back if dirty
        if victim.dirty:
            self.write_backs += 1
        
        # Replace line
        victim.tag = tag
        victim.data = data if is_write else None
        victim.valid = True
        victim.dirty = is_write
        victim.last_access = time.time()
        victim.access_count = 1
        self.replacements += 1
        
        return False, None

class VirtualMemory:
    def __init__(self):
        self.pages = {}  # Virtual page number -> Physical frame number
        self.page_faults = 0
        self.page_hits = 0
        self.disk_accesses = 0
        self.page_table = {}
        self.free_frames = list(range(MEMORY_SIZE // PAGE_SIZE))
        self.access_history = []

    def access(self, virtual_address):
        page_number = virtual_address // PAGE_SIZE
        offset = virtual_address % PAGE_SIZE
        
        if page_number in self.pages:
            self.page_hits += 1
            return True, self.pages[page_number] * PAGE_SIZE + offset
        
        # Page fault
        self.page_faults += 1
        self.disk_accesses += 1
        
        if self.free_frames:
            frame = self.free_frames.pop(0)
        else:
            # Page replacement (FIFO)
            frame = self.pages.pop(next(iter(self.pages)))
        
        self.pages[page_number] = frame
        self.access_history.append((time.time(), page_number))
        return False, frame * PAGE_SIZE + offset

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
        self.cache = Cache()
        self.virtual_memory = VirtualMemory()
        self.performance_metrics = {
            'allocation_time': [],
            'deallocation_time': [],
            'access_time': [],
            'fragmentation_history': [],
            'cache_hit_rate': [],
            'page_fault_rate': []
        }

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

    def access_memory(self, process_id, address, is_write=False):
        """Access memory with cache and virtual memory"""
        start_time = time.time()
        
        # Virtual memory translation
        page_fault, physical_address = self.virtual_memory.access(address)
        
        # Cache access
        cache_hit, data = self.cache.access(physical_address, is_write=is_write)
        
        # Update performance metrics
        access_time = time.time() - start_time
        self.performance_metrics['access_time'].append(access_time)
        
        # Update access pattern
        for block in self.memory:
            if block.process_id == process_id:
                block.access_pattern.append((time.time(), address))
                block.last_access_time = time.time()
                block.access_count += 1
                block.is_leaked = False
                return True, data
        
        return False, None

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

    def get_performance_metrics(self):
        """Calculate current performance metrics"""
        current_time = time.time() - self.start_time
        
        # Calculate cache hit rate
        total_cache_accesses = self.cache.hits + self.cache.misses
        cache_hit_rate = (self.cache.hits / total_cache_accesses * 100) if total_cache_accesses > 0 else 0
        
        # Calculate page fault rate
        total_page_accesses = self.virtual_memory.page_hits + self.virtual_memory.page_faults
        page_fault_rate = (self.virtual_memory.page_faults / total_page_accesses * 100) if total_page_accesses > 0 else 0
        
        # Calculate average access time
        avg_access_time = np.mean(self.performance_metrics['access_time']) if self.performance_metrics['access_time'] else 0
        
        return {
            'cache_hit_rate': cache_hit_rate,
            'page_fault_rate': page_fault_rate,
            'avg_access_time': avg_access_time,
            'total_memory_usage': sum(block.size for block in self.memory if block.status == "allocated"),
            'fragmentation': self.calculate_fragmentation()
        }

class MemoryVisualizer:
    def __init__(self, root):
        self.root = root
        self.root.title("Dynamic Memory Management Visualizer")
        self.memory_manager = MemoryManager()

        # Configure main window with larger size
        self.root.geometry("1000x1000")
        
        # Create main frames
        control_frame = ttk.LabelFrame(root, text="Controls", padding=10)
        control_frame.pack(fill="x", padx=10, pady=5)
        
        visualization_frame = ttk.Frame(root)
        visualization_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
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
        
        # Add virtual memory visualization
        virtual_frame = ttk.LabelFrame(root, text="Virtual Memory", padding=5)
        virtual_frame.pack(fill="x", padx=10, pady=5)
        
        self.virtual_canvas = tk.Canvas(
            virtual_frame,
            bg="white",
            height=100,
            highlightthickness=1,
            highlightbackground="black"
        )
        self.virtual_canvas.pack(fill="x", padx=5, pady=5)
        
        # Add cache visualization
        cache_frame = ttk.LabelFrame(root, text="Cache Memory", padding=5)
        cache_frame.pack(fill="x", padx=10, pady=5)
        
        self.cache_canvas = tk.Canvas(
            cache_frame,
            bg="white",
            height=100,
            highlightthickness=1,
            highlightbackground="black"
        )
        self.cache_canvas.pack(fill="x", padx=5, pady=5)
        
        # Add performance metrics dashboard with scrollbar
        metrics_frame = ttk.LabelFrame(root, text="Performance Metrics", padding=5)
        metrics_frame.pack(fill="x", padx=10, pady=5)
        
        # Create a frame for metrics text and scrollbar
        metrics_text_frame = ttk.Frame(metrics_frame)
        metrics_text_frame.pack(fill="x", padx=5, pady=5)
        
        # Add scrollbar for metrics
        metrics_scrollbar = ttk.Scrollbar(metrics_text_frame)
        metrics_scrollbar.pack(side="right", fill="y")
        
        self.metrics_text = tk.Text(metrics_text_frame, height=6, width=100, yscrollcommand=metrics_scrollbar.set)
        self.metrics_text.pack(side="left", fill="x", expand=True)
        metrics_scrollbar.config(command=self.metrics_text.yview)
        
        # Add memory access controls
        access_frame = ttk.LabelFrame(control_frame, text="Memory Access", padding=5)
        access_frame.grid(row=4, column=0, columnspan=8, padx=5, sticky="ew")
        
        ttk.Label(access_frame, text="Address:").pack(side="left", padx=5)
        self.address_entry = ttk.Entry(access_frame, width=10)
        self.address_entry.pack(side="left", padx=5)
        
        ttk.Button(
            access_frame,
            text="Read",
            command=lambda: self.access_memory(False)
        ).pack(side="left", padx=5)
        
        ttk.Button(
            access_frame,
            text="Write",
            command=lambda: self.access_memory(True)
        ).pack(side="left", padx=5)
        
        # Visualization canvas with scrollbar
        canvas_frame = ttk.Frame(visualization_frame)
        canvas_frame.pack(fill="both", expand=True)
        
        self.canvas = tk.Canvas(
            canvas_frame,
            bg="white",
            highlightthickness=1,
            highlightbackground="black"
        )
        self.canvas.pack(side="left", fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        scrollbar.pack(side="right", fill="y")
        
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # Status bar
        self.status_var = tk.StringVar()
        status_bar = ttk.Label(root, textvariable=self.status_var, relief="sunken")
        status_bar.pack(fill="x", padx=10, pady=5)
        
        # Initial visualization
        self.update_visualization()

    def allocate(self):
        """Handle memory allocation"""
        try:
            size = int(self.size_entry.get())
            if size <= 0:
                messagebox.showerror("Error", "Size must be positive")
                return
            
            success, process_id = self.memory_manager.allocate_memory(size)
            if success:
                self.process_entry.delete(0, tk.END)
                self.process_entry.insert(0, process_id)
                messagebox.showinfo("Success", f"Allocated {size} units to {process_id}")
            else:
                messagebox.showerror("Error", "Not enough contiguous memory")
            
            self.update_visualization()
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid size")

    def deallocate(self):
        """Handle memory deallocation"""
        process_id = self.process_entry.get()
        if not process_id:
            messagebox.showerror("Error", "Please enter a Process ID")
            return
        
        if self.memory_manager.deallocate_memory(process_id):
            messagebox.showinfo("Success", f"Deallocated memory for {process_id}")
            self.process_entry.delete(0, tk.END)
        else:
            messagebox.showerror("Error", f"No allocated blocks found for {process_id}")
        
        self.update_visualization()

    def access_memory(self, is_write):
        """Handle memory access"""
        try:
            address = int(self.address_entry.get())
            process_id = self.process_entry.get()
            
            if not process_id:
                messagebox.showerror("Error", "Please enter a Process ID")
                return
            
            success, data = self.memory_manager.access_memory(process_id, address, is_write)
            
            if success:
                self.status_var.set(f"Memory {'write' if is_write else 'read'} successful")
            else:
                self.status_var.set("Memory access failed")
            
            self.update_visualization()
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid address")

    def update_virtual_memory_visualization(self):
        """Update virtual memory visualization"""
        self.virtual_canvas.delete("all")
        
        # Draw virtual memory space
        for page_num, frame_num in self.memory_manager.virtual_memory.pages.items():
            x1 = 10 + (page_num * 20)
            y1 = 10
            x2 = x1 + 15
            y2 = 90
            
            color = "light blue" if frame_num in self.memory_manager.virtual_memory.free_frames else "salmon"
            self.virtual_canvas.create_rectangle(x1, y1, x2, y2, fill=color)
            
            self.virtual_canvas.create_text(
                (x1 + x2) / 2,
                (y1 + y2) / 2,
                text=f"P{page_num}\nF{frame_num}",
                justify="center"
            )

    def update_cache_visualization(self):
        """Update cache visualization"""
        self.cache_canvas.delete("all")
        
        # Draw cache lines
        for i, line in enumerate(self.memory_manager.cache.lines):
            x1 = 10 + (i * 100)
            y1 = 10
            x2 = x1 + 90
            y2 = 90
            
            color = "light green" if line.valid else "gray"
            self.cache_canvas.create_rectangle(x1, y1, x2, y2, fill=color)
            
            status = "V" if line.valid else "I"
            status += "D" if line.dirty else "-"
            text = f"Tag: {line.tag}\n{status}\nAccess: {line.access_count}"
            
            self.cache_canvas.create_text(
                (x1 + x2) / 2,
                (y1 + y2) / 2,
                text=text,
                justify="center"
            )

    def update_performance_metrics(self):
        """Update performance metrics display"""
        metrics = self.memory_manager.get_performance_metrics()
        
        self.metrics_text.delete("1.0", tk.END)
        self.metrics_text.insert(tk.END, "Performance Metrics:\n\n")
        self.metrics_text.insert(tk.END, f"Cache Hit Rate: {metrics['cache_hit_rate']:.1f}%\n")
        self.metrics_text.insert(tk.END, f"Page Fault Rate: {metrics['page_fault_rate']:.1f}%\n")
        self.metrics_text.insert(tk.END, f"Average Access Time: {metrics['avg_access_time']*1000:.2f}ms\n")
        self.metrics_text.insert(tk.END, f"Memory Usage: {metrics['total_memory_usage']}/{MEMORY_SIZE} units\n")
        self.metrics_text.insert(tk.END, f"Fragmentation: {metrics['fragmentation']:.1f}%")

    def update_visualization(self):
        """Update all visualizations"""
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
        
        # Update additional visualizations
        self.update_virtual_memory_visualization()
        self.update_cache_visualization()
        self.update_performance_metrics()

if __name__ == "__main__":
    root = tk.Tk()
    app = MemoryVisualizer(root)
    root.mainloop() 