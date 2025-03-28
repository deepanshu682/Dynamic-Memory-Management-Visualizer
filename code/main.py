import tkinter as tk
from tkinter import ttk, messagebox
import random
from collections import OrderedDict
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Constants
MEMORY_SIZE = 100  # Total memory size
BLOCK_HEIGHT = 30  # Increased height for better visibility
BLOCK_WIDTH = 3    # Scaling factor for block visualization
MAX_MEMORY_SIZE = 1000  # Maximum allowed memory size
PAGE_SIZE = 10  # Default page size
MAX_PAGES = 10  # Maximum number of pages in physical memory

class MemoryBlock:
    def __init__(self, start, size, status="free", process_id=None, block_id=None):
        self.start = start
        self.size = size
        self.status = status
        self.process_id = process_id  # Track which process owns this block
        self.block_id = block_id  # Unique identifier for each block

class Page:
    def __init__(self, page_number, size, process_id=None, is_valid=False):
        self.page_number = page_number
        self.size = size
        self.process_id = process_id
        self.is_valid = is_valid
        self.last_access_time = None
        self.frame_number = None

class Segment:
    def __init__(self, start, size, process_id=None, name=None):
        self.start = start
        self.size = size
        self.process_id = process_id
        self.name = name
        self.pages = []  # List of pages in this segment

class MemoryManager:
    def __init__(self):
        self.memory = [MemoryBlock(0, MEMORY_SIZE, "free")]
        self.algorithm = "first_fit"
        self.process_counter = 1
        self.block_counter = 1  # Counter for unique block IDs
        self.process_colors = {}
        self.last_allocated_index = 0
        self.algorithm_stats = {
            "first_fit": {"allocations": 0, "failures": 0},
            "best_fit": {"allocations": 0, "failures": 0},
            "worst_fit": {"allocations": 0, "failures": 0},
            "next_fit": {"allocations": 0, "failures": 0}
        }
        
        # Paging system
        self.page_size = PAGE_SIZE
        self.max_pages = MAX_PAGES
        self.page_table = {}  # Process ID -> List of Pages
        self.frame_table = {}  # Frame number -> Page
        self.page_faults = 0
        self.page_hits = 0
        self.replacement_algorithm = "FIFO"  # or "LRU"
        self.page_queue = []  # For FIFO
        self.page_access_times = {}  # For LRU
        self.page_loaded_times = {}  # For FIFO - track when each page was loaded
        self.page_references = []  # For LRU - track page reference sequence
        
        # Segmentation system
        self.segments = []
        self.segment_table = {}  # Process ID -> List of Segments

    def get_process_color(self, process_id):
        """Get or generate a color for a process"""
        if process_id not in self.process_colors:
            # Generate a pastel color
            r = random.randint(180, 255)
            g = random.randint(180, 255)
            b = random.randint(180, 255)
            self.process_colors[process_id] = f'#{r:02x}{g:02x}{b:02x}'
        return self.process_colors[process_id]

    def reset(self):
        """Reset memory to initial state"""
        # Reset dynamic allocation
        self.memory = [MemoryBlock(0, MEMORY_SIZE, "free")]
        self.process_counter = 1
        self.block_counter = 1
        self.process_colors.clear()
        self.last_allocated_index = 0
        self.algorithm_stats = {
            "first_fit": {"allocations": 0, "failures": 0},
            "best_fit": {"allocations": 0, "failures": 0},
            "worst_fit": {"allocations": 0, "failures": 0},
            "next_fit": {"allocations": 0, "failures": 0}
        }
        
        # Reset paging system
        self.page_size = PAGE_SIZE
        self.max_pages = MAX_PAGES
        self.page_table.clear()
        self.frame_table.clear()
        self.page_queue.clear()
        self.page_access_times.clear()
        self.page_loaded_times.clear()
        self.page_references.clear()
        self.page_faults = 0
        self.page_hits = 0

    def reset_paging(self):
        """Reset paging system"""
        self.page_table.clear()
        self.frame_table.clear()
        self.page_queue.clear()
        self.page_access_times.clear()
        self.page_loaded_times.clear()
        self.page_references.clear()
        self.page_faults = 0
        self.page_hits = 0

    def reset_segmentation(self):
        """Reset segmentation system"""
        self.segments.clear()
        self.segment_table.clear()
        # Also reset paging since segments use paging
        self.reset_paging()

    def reset_dynamic(self):
        """Reset dynamic allocation system"""
        self.memory = [MemoryBlock(0, MEMORY_SIZE, "free")]
        self.process_counter = 1
        self.block_counter = 1
        self.process_colors.clear()
        self.last_allocated_index = 0
        self.algorithm_stats = {
            "first_fit": {"allocations": 0, "failures": 0},
            "best_fit": {"allocations": 0, "failures": 0},
            "worst_fit": {"allocations": 0, "failures": 0},
            "next_fit": {"allocations": 0, "failures": 0}
        }

    def allocate_memory(self, size):
        """Allocate memory with current algorithm"""
        process_id = f"P{self.process_counter}"
        self.process_counter += 1
        
        success = False
        if self.algorithm == "first_fit":
            success = self.first_fit(size, process_id)
        elif self.algorithm == "best_fit":
            success = self.best_fit(size, process_id)
        elif self.algorithm == "worst_fit":
            success = self.worst_fit(size, process_id)
        elif self.algorithm == "next_fit":
            success = self.next_fit(size, process_id)
        
        # Update statistics
        if success:
            self.algorithm_stats[self.algorithm]["allocations"] += 1
        else:
            self.algorithm_stats[self.algorithm]["failures"] += 1
        
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

    def next_fit(self, size, process_id):
        """Next-fit allocation strategy"""
        start_index = self.last_allocated_index
        current_index = start_index
        
        # Search from last allocated position
        while True:
            block = self.memory[current_index]
            if block.status == "free" and block.size >= size:
                self.split_block(block, size, process_id)
                self.last_allocated_index = current_index
                return True
            
            current_index = (current_index + 1) % len(self.memory)
            if current_index == start_index:
                break
        
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
        block.block_id = f"B{self.block_counter}"
        self.block_counter += 1

    def deallocate_memory(self, process_id, block_id=None):
        """Deallocate memory blocks belonging to a process"""
        deallocated = False
        for block in self.memory:
            if block.process_id == process_id:
                if block_id is None:
                    # If no block_id specified, deallocate all blocks of the process
                    block.status = "free"
                    block.process_id = None
                    block.block_id = None
                    deallocated = True
                elif block.block_id == block_id:
                    # If block_id specified, deallocate only that specific block
                    block.status = "free"
                    block.process_id = None
                    block.block_id = None
                    deallocated = True
                    break  # Exit after deallocating the specific block
        
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

    def get_algorithm_stats(self):
        """Get statistics for all algorithms"""
        return self.algorithm_stats

    def get_process_blocks(self, process_id):
        """Get all blocks belonging to a process"""
        return [block for block in self.memory if block.process_id == process_id]

    def set_page_size(self, size):
        """Set the page size for paging system"""
        self.page_size = size
        self.reset_paging()

    def set_replacement_algorithm(self, algorithm):
        """Set the page replacement algorithm"""
        self.replacement_algorithm = algorithm
        self.page_queue = []
        self.page_access_times = {}
        self.page_loaded_times = {}
        self.page_references = []

    def allocate_pages(self, process_id, size):
        """Allocate pages for a process"""
        num_pages = (size + self.page_size - 1) // self.page_size
        pages = []
        
        for i in range(num_pages):
            page = Page(i, min(self.page_size, size - i * self.page_size), process_id)
            pages.append(page)
            
            # Try to allocate a frame
            if len(self.frame_table) < self.max_pages:
                frame_num = len(self.frame_table)
                self.frame_table[frame_num] = page
                page.frame_number = frame_num
                page.is_valid = True
                page.last_access_time = datetime.now()
                self.page_loaded_times[frame_num] = datetime.now()
                self.page_queue.append(frame_num)
            else:
                # Need page replacement
                self.handle_page_fault(page)
        
        self.page_table[process_id] = pages
        return pages

    def handle_page_fault(self, new_page):
        """Handle page fault using selected replacement algorithm"""
        self.page_faults += 1
        
        if self.replacement_algorithm == "FIFO":
            # If we have free frames
            if len(self.frame_table) < self.max_pages:
                frame_num = len(self.frame_table)
                self.frame_table[frame_num] = new_page
                new_page.frame_number = frame_num
                new_page.is_valid = True
                new_page.last_access_time = datetime.now()
                self.page_loaded_times[frame_num] = datetime.now()
                self.page_queue.append(frame_num)
            else:
                # Find the oldest page (first in queue)
                victim_frame = self.page_queue.pop(0)
                victim_page = self.frame_table[victim_frame]
                victim_page.is_valid = False
                
                # Add new page
                self.frame_table[victim_frame] = new_page
                new_page.frame_number = victim_frame
                new_page.is_valid = True
                new_page.last_access_time = datetime.now()
                self.page_loaded_times[victim_frame] = datetime.now()
                self.page_queue.append(victim_frame)
            
        elif self.replacement_algorithm == "LRU":
            # If we have free frames
            if len(self.frame_table) < self.max_pages:
                frame_num = len(self.frame_table)
                self.frame_table[frame_num] = new_page
                new_page.frame_number = frame_num
                new_page.is_valid = True
                new_page.last_access_time = datetime.now()
                self.page_access_times[frame_num] = datetime.now()
                self.page_references.append(frame_num)
            else:
                # Find least recently used page
                lru_frame = min(self.page_access_times.items(), key=lambda x: x[1])[0]
                victim_page = self.frame_table[lru_frame]
                victim_page.is_valid = False
                
                # Add new page
                self.frame_table[lru_frame] = new_page
                new_page.frame_number = lru_frame
                new_page.is_valid = True
                new_page.last_access_time = datetime.now()
                self.page_access_times[lru_frame] = datetime.now()
                self.page_references.append(lru_frame)

    def access_page(self, process_id, page_number):
        """Simulate page access"""
        if process_id in self.page_table:
            pages = self.page_table[process_id]
            if 0 <= page_number < len(pages):
                page = pages[page_number]
                if page.is_valid:
                    self.page_hits += 1
                    if self.replacement_algorithm == "LRU":
                        # Update access time for LRU
                        self.page_access_times[page.frame_number] = datetime.now()
                        # Update reference sequence
                        if page.frame_number in self.page_references:
                            self.page_references.remove(page.frame_number)
                        self.page_references.append(page.frame_number)
                    return True
                else:
                    self.handle_page_fault(page)
                    return True
        return False

    def create_segment(self, process_id, size, name=None):
        """Create a new segment for a process"""
        segment = Segment(0, size, process_id, name)
        self.segments.append(segment)
        
        if process_id not in self.segment_table:
            self.segment_table[process_id] = []
        self.segment_table[process_id].append(segment)
        
        # Allocate pages for the segment
        segment.pages = self.allocate_pages(process_id, size)
        return segment

    def get_paging_stats(self):
        """Get paging statistics"""
        total_accesses = self.page_faults + self.page_hits
        fault_rate = self.page_faults / total_accesses if total_accesses > 0 else 0
        
        # Calculate additional statistics
        stats = {
            "page_faults": self.page_faults,
            "page_hits": self.page_hits,
            "fault_rate": fault_rate,
            "total_pages": len(self.frame_table),
            "max_pages": self.max_pages
        }
        
        if self.replacement_algorithm == "FIFO":
            stats["queue_length"] = len(self.page_queue)
            if self.page_loaded_times:
                oldest_page = min(self.page_loaded_times.items(), key=lambda x: x[1])[0]
                stats["oldest_page"] = f"Frame {oldest_page}"
        
        elif self.replacement_algorithm == "LRU":
            stats["reference_sequence_length"] = len(self.page_references)
            if self.page_access_times:
                lru_page = min(self.page_access_times.items(), key=lambda x: x[1])[0]
                stats["least_recently_used"] = f"Frame {lru_page}"
        
        return stats

class MemoryVisualizer:
    def __init__(self, root):
        self.root = root
        self.root.title("Dynamic Memory Management Visualizer")
        self.memory_manager = MemoryManager()

        # Configure main window
        self.root.geometry("1200x900")  # Increased window size
        
        # Create main container frame
        main_container = ttk.Frame(root)
        main_container.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Create left and right frames for better organization
        left_frame = ttk.Frame(main_container)
        left_frame.pack(side="left", fill="both", expand=True)
        
        right_frame = ttk.Frame(main_container)
        right_frame.pack(side="right", fill="both", expand=True)
        
        # Create main frames in left frame
        control_frame = ttk.LabelFrame(left_frame, text="Controls", padding=10)
        control_frame.pack(fill="x", pady=5)
        
        # Memory size configuration
        ttk.Label(control_frame, text="Total Memory Size:").grid(row=0, column=0, padx=5)
        self.total_memory_entry = ttk.Entry(control_frame, width=10)
        self.total_memory_entry.insert(0, str(MEMORY_SIZE))
        self.total_memory_entry.grid(row=0, column=1, padx=5)
        
        self.update_memory_button = ttk.Button(
            control_frame,
            text="Update Memory Size",
            command=self.update_total_memory
        )
        self.update_memory_button.grid(row=0, column=2, padx=5)
        
        # Process list frame
        process_frame = ttk.LabelFrame(left_frame, text="Active Processes", padding=10)
        process_frame.pack(fill="x", padx=10, pady=5)
        
        # Create process list with block selection
        columns = ("Process ID", "Block ID", "Size", "Start")
        self.process_tree = ttk.Treeview(process_frame, columns=columns, show="headings")
        
        # Configure columns
        for col in columns:
            self.process_tree.heading(col, text=col)
            self.process_tree.column(col, width=100)
        
        self.process_tree.pack(fill="x", expand=True)
        
        # Add double-click binding for block selection
        self.process_tree.bind("<Double-1>", self.on_block_select)
        
        # Create canvas with scrollbars in left frame
        canvas_frame = ttk.Frame(left_frame)
        canvas_frame.pack(fill="both", expand=True, pady=5)
        
        # Add horizontal scrollbar
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient="horizontal")
        h_scrollbar.pack(side="bottom", fill="x")
        
        # Add vertical scrollbar
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical")
        v_scrollbar.pack(side="right", fill="y")
        
        self.canvas = tk.Canvas(
            canvas_frame,
            bg="white",
            highlightthickness=1,
            highlightbackground="black",
            xscrollcommand=h_scrollbar.set,
            yscrollcommand=v_scrollbar.set
        )
        self.canvas.pack(side="left", fill="both", expand=True)
        
        # Configure scrollbars
        h_scrollbar.config(command=self.canvas.xview)
        v_scrollbar.config(command=self.canvas.yview)
        
        # Control widgets
        ttk.Label(control_frame, text="Memory Size:").grid(row=1, column=0, padx=5)
        self.size_entry = ttk.Entry(control_frame, width=10)
        self.size_entry.grid(row=1, column=1, padx=5)
        
        ttk.Label(control_frame, text="Process ID:").grid(row=1, column=2, padx=5)
        self.process_entry = ttk.Entry(control_frame, width=10)
        self.process_entry.grid(row=1, column=3, padx=5)
        
        self.allocate_button = ttk.Button(
            control_frame, 
            text="Allocate", 
            command=self.allocate
        )
        self.allocate_button.grid(row=1, column=4, padx=5)
        
        self.deallocate_button = ttk.Button(
            control_frame, 
            text="Deallocate", 
            command=self.deallocate
        )
        self.deallocate_button.grid(row=1, column=5, padx=5)
        
        self.reset_button = ttk.Button(
            control_frame,
            text="Reset",
            command=self.reset_memory
        )
        self.reset_button.grid(row=1, column=6, padx=5)
        
        # Algorithm selection
        ttk.Label(control_frame, text="Algorithm:").grid(row=2, column=0, padx=5)
        self.algorithm_var = tk.StringVar(value="first_fit")
        algorithm_menu = ttk.OptionMenu(
            control_frame,
            self.algorithm_var,
            "first_fit",
            "first_fit",
            "best_fit",
            "worst_fit",
            "next_fit"
        )
        algorithm_menu.grid(row=2, column=1, columnspan=2, padx=5, sticky="ew")
        
        # Legend frame
        legend_frame = ttk.LabelFrame(control_frame, text="Legend", padding=5)
        legend_frame.grid(row=2, column=3, columnspan=4, padx=5, sticky="ew")
        
        # Add legend items
        ttk.Label(legend_frame, text="Free Memory", background="light green").pack(side="left", padx=5)
        ttk.Label(legend_frame, text="Allocated Memory", background="salmon").pack(side="left", padx=5)
        
        # Statistics display
        self.stats_label = ttk.Label(left_frame, text="", font=('Helvetica', 10))
        self.stats_label.pack(pady=5)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(left_frame, textvariable=self.status_var, relief="sunken")
        self.status_bar.pack(fill="x", padx=10, pady=2)
        
        # Bind hover events
        self.canvas.bind("<Motion>", self.on_hover)
        
        # Add zoom controls
        zoom_frame = ttk.Frame(control_frame)
        zoom_frame.grid(row=3, column=0, columnspan=7, pady=5)
        
        ttk.Label(zoom_frame, text="Zoom:").pack(side="left", padx=5)
        self.zoom_var = tk.DoubleVar(value=1.0)
        self.zoom_scale = ttk.Scale(
            zoom_frame,
            from_=0.5,
            to=2.0,
            orient="horizontal",
            variable=self.zoom_var,
            command=self.update_zoom
        )
        self.zoom_scale.pack(side="left", fill="x", expand=True, padx=5)
        
        # Add zoom percentage label
        self.zoom_label = ttk.Label(zoom_frame, text="100%")
        self.zoom_label.pack(side="left", padx=5)
        
        # Add algorithm statistics frame
        stats_frame = ttk.LabelFrame(left_frame, text="Algorithm Statistics", padding=10)
        stats_frame.pack(fill="x", padx=10, pady=5)
        
        # Create statistics labels
        self.stats_labels = {}
        for i, algorithm in enumerate(["first_fit", "best_fit", "worst_fit", "next_fit"]):
            ttk.Label(stats_frame, text=algorithm.replace("_", " ").title()).grid(
                row=i, column=0, padx=5, pady=2
            )
            self.stats_labels[algorithm] = ttk.Label(stats_frame, text="")
            self.stats_labels[algorithm].grid(row=i, column=1, padx=5, pady=2)
        
        # Add memory management mode selection
        mode_frame = ttk.LabelFrame(control_frame, text="Memory Management Mode", padding=5)
        mode_frame.grid(row=4, column=0, columnspan=7, pady=5, sticky="ew")
        
        self.mode_var = tk.StringVar(value="dynamic")
        ttk.Radiobutton(mode_frame, text="Dynamic Allocation", variable=self.mode_var, 
                       value="dynamic", command=self.on_mode_change).pack(side="left", padx=5)
        ttk.Radiobutton(mode_frame, text="Paging", variable=self.mode_var, 
                       value="paging", command=self.on_mode_change).pack(side="left", padx=5)
        ttk.Radiobutton(mode_frame, text="Segmentation", variable=self.mode_var, 
                       value="segmentation", command=self.on_mode_change).pack(side="left", padx=5)
        
        # Add paging controls
        self.paging_frame = ttk.LabelFrame(control_frame, text="Paging Controls", padding=5)
        self.paging_frame.grid(row=5, column=0, columnspan=7, pady=5, sticky="ew")
        
        ttk.Label(self.paging_frame, text="Page Size:").pack(side="left", padx=5)
        self.page_size_entry = ttk.Entry(self.paging_frame, width=10)
        self.page_size_entry.insert(0, str(PAGE_SIZE))
        self.page_size_entry.pack(side="left", padx=5)
        
        ttk.Label(self.paging_frame, text="Max Pages:").pack(side="left", padx=5)
        self.max_pages_entry = ttk.Entry(self.paging_frame, width=10)
        self.max_pages_entry.insert(0, str(MAX_PAGES))
        self.max_pages_entry.pack(side="left", padx=5)
        
        ttk.Label(self.paging_frame, text="Replacement:").pack(side="left", padx=5)
        self.replacement_var = tk.StringVar(value="FIFO")
        replacement_menu = ttk.OptionMenu(
            self.paging_frame,
            self.replacement_var,
            "FIFO",
            "FIFO",
            "LRU"
        )
        replacement_menu.pack(side="left", padx=5)
        
        self.update_paging_button = ttk.Button(
            self.paging_frame,
            text="Update Paging Settings",
            command=self.update_paging_settings
        )
        self.update_paging_button.pack(side="left", padx=5)
        
        # Add segmentation controls
        self.segmentation_frame = ttk.LabelFrame(control_frame, text="Segmentation Controls", padding=5)
        self.segmentation_frame.grid(row=6, column=0, columnspan=7, pady=5, sticky="ew")
        
        ttk.Label(self.segmentation_frame, text="Segment Name:").pack(side="left", padx=5)
        self.segment_name_entry = ttk.Entry(self.segmentation_frame, width=15)
        self.segment_name_entry.pack(side="left", padx=5)
        
        self.create_segment_button = ttk.Button(
            self.segmentation_frame,
            text="Create Segment",
            command=self.create_segment
        )
        self.create_segment_button.pack(side="left", padx=5)
        
        # Add page access controls
        self.page_access_frame = ttk.LabelFrame(control_frame, text="Page Access", padding=5)
        self.page_access_frame.grid(row=7, column=0, columnspan=7, pady=5, sticky="ew")
        
        ttk.Label(self.page_access_frame, text="Process ID:").pack(side="left", padx=5)
        self.page_process_entry = ttk.Entry(self.page_access_frame, width=10)
        self.page_process_entry.pack(side="left", padx=5)
        
        ttk.Label(self.page_access_frame, text="Page Number:").pack(side="left", padx=5)
        self.page_number_entry = ttk.Entry(self.page_access_frame, width=10)
        self.page_number_entry.pack(side="left", padx=5)
        
        self.access_page_button = ttk.Button(
            self.page_access_frame,
            text="Access Page",
            command=self.access_page
        )
        self.access_page_button.pack(side="left", padx=5)
        
        # Add paging statistics display
        self.paging_stats_label = ttk.Label(left_frame, text="", font=('Helvetica', 10))
        self.paging_stats_label.pack(pady=5)
        
        # Add access pattern graph to right frame
        self.add_access_pattern_graph(right_frame)
        
        # Initially hide paging and segmentation controls
        self.paging_frame.grid_remove()
        self.segmentation_frame.grid_remove()
        self.page_access_frame.grid_remove()
        
        # Initial visualization
        self.update_visualization()

    def reset_memory(self):
        """Reset memory to initial state"""
        mode = self.mode_var.get()
        
        # Reset based on current mode
        if mode == "dynamic":
            self.memory_manager.reset_dynamic()
        elif mode == "paging":
            self.memory_manager.reset_paging()
        elif mode == "segmentation":
            self.memory_manager.reset_segmentation()
        else:
            self.memory_manager.reset()  # Reset everything
            
        # Clear input fields
        self.process_entry.delete(0, tk.END)
        self.size_entry.delete(0, tk.END)
        self.page_process_entry.delete(0, tk.END)
        self.page_number_entry.delete(0, tk.END)
        self.segment_name_entry.delete(0, tk.END)
        
        # Update visualization and status
        self.update_visualization()
        self.status_var.set(f"Memory reset to initial state ({mode} mode)")

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
        entry_text = self.process_entry.get()
        if not entry_text:
            self.status_var.set("Error: Please enter a Process ID")
            messagebox.showerror("Error", "Please enter a Process ID")
            return
        
        # Parse process ID and block ID if specified
        if ":" in entry_text:
            process_id, block_id = entry_text.split(":")
            self.status_var.set(f"Attempting to deallocate block {block_id} of process {process_id}")
        else:
            process_id = entry_text
            block_id = None
            self.status_var.set(f"Attempting to deallocate all blocks of process {process_id}")
        
        if self.memory_manager.deallocate_memory(process_id, block_id):
            if block_id:
                self.status_var.set(f"Successfully deallocated block {block_id} of process {process_id}")
            else:
                self.status_var.set(f"Successfully deallocated all blocks of process {process_id}")
            self.process_entry.delete(0, tk.END)
        else:
            if block_id:
                self.status_var.set(f"Failed to deallocate block {block_id} of process {process_id}")
                messagebox.showerror("Error", f"No allocated block {block_id} found for process {process_id}")
            else:
                self.status_var.set(f"Failed to deallocate - no blocks found for process {process_id}")
                messagebox.showerror("Error", f"No allocated blocks found for process {process_id}")
        
        self.update_visualization()

    def update_total_memory(self):
        """Update the total memory size"""
        try:
            new_size = int(self.total_memory_entry.get())
            if new_size <= 0:
                messagebox.showerror("Error", "Memory size must be positive")
                return
            if new_size > MAX_MEMORY_SIZE:
                messagebox.showerror("Error", f"Memory size cannot exceed {MAX_MEMORY_SIZE} units")
                return
            
            # Reset memory with new size
            self.memory_manager.memory = [MemoryBlock(0, new_size, "free")]
            self.memory_manager.process_counter = 1
            self.memory_manager.process_colors.clear()
            
            self.update_visualization()
            self.update_process_list()
            self.status_var.set(f"Memory size updated to {new_size} units")
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid memory size")

    def update_process_list(self):
        """Update the process list display"""
        # Clear existing items
        for item in self.process_tree.get_children():
            self.process_tree.delete(item)
        
        # Add each allocated block to tree
        for block in self.memory_manager.memory:
            if block.status == "allocated":
                self.process_tree.insert("", "end", values=(
                    block.process_id,
                    block.block_id,
                    block.size,
                    block.start
                ))

    def update_zoom(self, *args):
        """Update the visualization zoom level"""
        zoom = self.zoom_var.get()
        self.zoom_label.config(text=f"{int(zoom * 100)}%")
        self.update_visualization()

    def on_mode_change(self):
        """Handle memory management mode change"""
        mode = self.mode_var.get()
        
        # Show/hide relevant controls
        if mode == "paging":
            self.paging_frame.grid()
            self.segmentation_frame.grid_remove()
            self.page_access_frame.grid()
            # Show and reset graph
            self.graph_frame.pack(fill="both", expand=True, pady=5)
            self.access_times = []
            self.fault_rates = []
            self.update_access_pattern_graph()
        elif mode == "segmentation":
            self.paging_frame.grid()
            self.segmentation_frame.grid()
            self.page_access_frame.grid()
            # Show and reset graph
            self.graph_frame.pack(fill="both", expand=True, pady=5)
            self.access_times = []
            self.fault_rates = []
            self.update_access_pattern_graph()
        else:
            self.paging_frame.grid_remove()
            self.segmentation_frame.grid_remove()
            self.page_access_frame.grid_remove()
            # Hide graph
            self.graph_frame.pack_forget()
        
        self.update_visualization()

    def update_paging_settings(self):
        """Update paging system settings"""
        try:
            page_size = int(self.page_size_entry.get())
            max_pages = int(self.max_pages_entry.get())
            
            if page_size <= 0 or max_pages <= 0:
                messagebox.showerror("Error", "Values must be positive")
                return
            
            self.memory_manager.set_page_size(page_size)
            self.memory_manager.max_pages = max_pages
            self.memory_manager.set_replacement_algorithm(self.replacement_var.get())
            
            self.status_var.set("Paging settings updated successfully")
            self.update_visualization()
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers")

    def create_segment(self):
        """Create a new segment"""
        try:
            size = int(self.size_entry.get())
            name = self.segment_name_entry.get()
            process_id = self.process_entry.get()
            
            if not process_id:
                messagebox.showerror("Error", "Please enter a Process ID")
                return
            
            if size <= 0:
                messagebox.showerror("Error", "Size must be positive")
                return
            
            segment = self.memory_manager.create_segment(process_id, size, name)
            self.status_var.set(f"Created segment '{name}' for process {process_id}")
            self.update_visualization()
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers")

    def access_page(self):
        """Simulate page access"""
        try:
            process_id = self.page_process_entry.get()
            page_number = int(self.page_number_entry.get())
            
            if not process_id:
                messagebox.showerror("Error", "Please enter a Process ID")
                return
            
            if page_number < 0:
                messagebox.showerror("Error", "Page number must be non-negative")
                return
            
            success = self.memory_manager.access_page(process_id, page_number)
            if success:
                self.status_var.set(f"Accessed page {page_number} of process {process_id}")
            else:
                self.status_var.set(f"Failed to access page {page_number} of process {process_id}")
            
            self.update_visualization()
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers")

    def add_access_pattern_graph(self, parent_frame):
        """Add memory access pattern visualization"""
        # Create graph frame
        self.graph_frame = ttk.LabelFrame(parent_frame, text="Memory Access Patterns", padding=5)
        self.graph_frame.pack(fill="both", expand=True, pady=5)
        
        # Create matplotlib figure with larger size
        self.fig, self.ax = plt.subplots(figsize=(6, 4))
        self.graph_canvas = FigureCanvasTkAgg(self.fig, master=self.graph_frame)
        self.graph_canvas.get_tk_widget().pack(fill="both", expand=True)
        
        # Initialize data
        self.access_times = []
        self.fault_rates = []
        
        # Set up the plot with better styling
        self.ax.set_title("Page Fault Rate Over Time", pad=20)
        self.ax.set_xlabel("Access Time")
        self.ax.set_ylabel("Fault Rate")
        self.ax.grid(True, linestyle='--', alpha=0.7)
        
        # Initialize the line plot with better styling
        self.line, = self.ax.plot([], [], 'b-', label='Fault Rate', linewidth=2)
        self.ax.legend(loc='upper right')
        
        # Set y-axis limits
        self.ax.set_ylim(0, 1.0)
        
        # Add some padding to the plot
        self.fig.tight_layout()

    def update_access_pattern_graph(self):
        """Update the access pattern graph"""
        if not hasattr(self, 'graph_frame'):
            return
            
        # Get current statistics
        stats = self.memory_manager.get_paging_stats()
        current_fault_rate = stats['fault_rate']
        
        # Update data
        self.access_times.append(len(self.access_times))
        self.fault_rates.append(current_fault_rate)
        
        # Update plot
        self.line.set_data(self.access_times, self.fault_rates)
        self.ax.relim()
        self.ax.autoscale_view()
        
        # Ensure y-axis stays between 0 and 1
        self.ax.set_ylim(0, 1.0)
        
        # Add some padding to the plot
        self.fig.tight_layout()
        
        # Draw the canvas
        self.graph_canvas.draw()

    def update_visualization(self):
        """Update the memory visualization"""
        self.canvas.delete("all")
        y = 10
        zoom = self.zoom_var.get()
        
        # Calculate scaled dimensions
        scaled_width = BLOCK_WIDTH * zoom
        scaled_height = BLOCK_HEIGHT * zoom
        
        # Draw grid lines
        for i in range(0, MEMORY_SIZE + 1, 10):
            x = 10 + i * scaled_width
            self.canvas.create_line(x, 0, x, self.canvas.winfo_height(), fill="lightgray")
        
        mode = self.mode_var.get()
        
        if mode == "dynamic":
            # Draw memory blocks for dynamic allocation
            for block in self.memory_manager.memory:
                # Determine block color and text
                if block.status == "free":
                    color = "light green"
                    text = f"Free\n{block.size} units"
                else:
                    color = self.memory_manager.get_process_color(block.process_id)
                    text = f"{block.process_id}\n{block.size} units"
                
                # Draw the block with scaled dimensions
                x1, y1 = 10, y
                x2, y2 = 10 + block.size * scaled_width, y + scaled_height
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
                
                y += scaled_height + 5
                
        elif mode == "paging":
            # Draw physical memory frames
            frame_width = MEMORY_SIZE // self.memory_manager.max_pages
            for i in range(self.memory_manager.max_pages):
                x1 = 10 + i * frame_width * scaled_width
                x2 = x1 + frame_width * scaled_width
                y1 = y
                y2 = y + scaled_height
                
                # Draw frame
                frame = self.memory_manager.frame_table.get(i)
                if frame:
                    color = self.memory_manager.get_process_color(frame.process_id)
                    text = f"P{frame.process_id} P{frame.page_number}"
                else:
                    color = "light green"
                    text = "Free"
                
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color)
                self.canvas.create_text(
                    (x1 + x2) / 2,
                    (y1 + y2) / 2,
                    text=text,
                    justify="center"
                )
                
                # Add frame number
                self.canvas.create_text(
                    x1 + 5,
                    y1 + 5,
                    text=f"Frame {i}",
                    anchor="nw",
                    font=('Helvetica', 8)
                )
            
            y += scaled_height + 5
            
            # Draw page tables
            for process_id, pages in self.memory_manager.page_table.items():
                x1 = 10
                y1 = y
                y2 = y1 + scaled_height
                
                # Draw process header
                color = self.memory_manager.get_process_color(process_id)
                self.canvas.create_rectangle(x1, y1, x1 + 200, y2, fill=color)
                self.canvas.create_text(
                    x1 + 100,
                    (y1 + y2) / 2,
                    text=f"Process {process_id} Page Table",
                    justify="center"
                )
                
                y += scaled_height + 5
                
                # Draw page entries
                for i, page in enumerate(pages):
                    x1 = 10 + i * 100
                    x2 = x1 + 90
                    y1 = y
                    y2 = y1 + scaled_height
                    
                    # Draw page entry
                    if page.is_valid:
                        color = "light blue"
                        text = f"Page {page.page_number}\nFrame {page.frame_number}"
                    else:
                        color = "pink"
                        text = f"Page {page.page_number}\nNot in Memory"
                    
                    self.canvas.create_rectangle(x1, y1, x2, y2, fill=color)
                    self.canvas.create_text(
                        (x1 + x2) / 2,
                        (y1 + y2) / 2,
                        text=text,
                        justify="center"
                    )
                
                y += scaled_height + 5
                
        elif mode == "segmentation":
            # Draw segments
            for segment in self.memory_manager.segments:
                x1 = 10
                x2 = 10 + segment.size * scaled_width
                y1 = y
                y2 = y + scaled_height
                
                # Draw segment
                color = self.memory_manager.get_process_color(segment.process_id)
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color)
                
                # Add segment information
                text = f"Segment: {segment.name}\nProcess: {segment.process_id}\nSize: {segment.size}"
                self.canvas.create_text(
                    (x1 + x2) / 2,
                    (y1 + y2) / 2,
                    text=text,
                    justify="center"
                )
                
                y += scaled_height + 5
                
                # Draw pages in segment
                for page in segment.pages:
                    x1 = 10
                    x2 = 10 + page.size * scaled_width
                    y1 = y
                    y2 = y + scaled_height
                    
                    # Draw page
                    if page.is_valid:
                        color = "light blue"
                        text = f"Page {page.page_number}\nFrame {page.frame_number}"
                    else:
                        color = "pink"
                        text = f"Page {page.page_number}\nNot in Memory"
                    
                    self.canvas.create_rectangle(x1, y1, x2, y2, fill=color)
                    self.canvas.create_text(
                        (x1 + x2) / 2,
                        (y1 + y2) / 2,
                        text=text,
                        justify="center"
                    )
                    
                    y += scaled_height + 5
        
        # Update canvas scroll region
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
        # Update statistics
        total_memory = MEMORY_SIZE
        used_memory = sum(
            block.size for block in self.memory_manager.memory 
            if block.status == "allocated"
        )
        free_memory = total_memory - used_memory
        fragmentation = self.calculate_fragmentation()
        
        stats_text = (
            f"Total Memory: {total_memory} units | "
            f"Used: {used_memory} units | "
            f"Free: {free_memory} units | "
            f"Fragmentation: {fragmentation:.1f}%"
        )
        self.stats_label.config(text=stats_text)
        
        # Update process list
        self.update_process_list()
        
        # Update algorithm statistics
        stats = self.memory_manager.get_algorithm_stats()
        for algorithm, label in self.stats_labels.items():
            stat = stats[algorithm]
            success_rate = (
                stat["allocations"] / (stat["allocations"] + stat["failures"])
                if (stat["allocations"] + stat["failures"]) > 0
                else 0
            )
            label.config(
                text=f"Allocations: {stat['allocations']} | "
                     f"Failures: {stat['failures']} | "
                     f"Success Rate: {success_rate:.1%}"
            )
        
        # Update paging statistics and graph
        if mode in ["paging", "segmentation"]:
            stats = self.memory_manager.get_paging_stats()
            stats_text = (
                f"Page Faults: {stats['page_faults']} | "
                f"Page Hits: {stats['page_hits']} | "
                f"Fault Rate: {stats['fault_rate']:.1%} | "
                f"Pages in Memory: {stats['total_pages']}/{stats['max_pages']}"
            )
            
            # Add algorithm-specific statistics
            if self.memory_manager.replacement_algorithm == "FIFO":
                stats_text += f" | Queue Length: {stats['queue_length']}"
                if 'oldest_page' in stats:
                    stats_text += f" | Oldest Page: {stats['oldest_page']}"
            elif self.memory_manager.replacement_algorithm == "LRU":
                stats_text += f" | Reference Sequence Length: {stats['reference_sequence_length']}"
                if 'least_recently_used' in stats:
                    stats_text += f" | LRU Page: {stats['least_recently_used']}"
            
            self.paging_stats_label.config(text=stats_text)
            
            # Update the access pattern graph
            self.update_access_pattern_graph()
        else:
            self.paging_stats_label.config(text="")
            # Clear the graph when not in paging/segmentation mode
            if hasattr(self, 'graph_frame'):
                self.ax.clear()
                self.graph_canvas.draw()

    def calculate_fragmentation(self):
        """Calculate external fragmentation percentage"""
        free_blocks = [
            block.size for block in self.memory_manager.memory 
            if block.status == "free"
        ]
        
        if not free_blocks:
            return 0.0
            
        largest_free_block = max(free_blocks)
        total_free = sum(free_blocks)
        return (1 - (largest_free_block / total_free)) * 100

    def on_block_select(self, event):
        """Handle block selection in process list"""
        item = self.process_tree.selection()[0]
        values = self.process_tree.item(item)["values"]
        process_id = values[0]
        block_id = values[1]
        
        # Update process entry with selected block
        self.process_entry.delete(0, tk.END)
        self.process_entry.insert(0, f"{process_id}:{block_id}")

if __name__ == "__main__":
    root = tk.Tk()
    app = MemoryVisualizer(root)
    root.mainloop()