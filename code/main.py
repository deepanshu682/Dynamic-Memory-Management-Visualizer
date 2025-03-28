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
        
        # Performance metrics
        self.performance_metrics = {
            "memory_usage": [],  # Track memory usage over time
            "peak_memory": 0,    # Peak memory usage
            "allocation_times": [],  # Track allocation operation times
            "deallocation_times": [],  # Track deallocation operation times
            "page_fault_history": [],  # Track page fault occurrences
            "page_hit_history": [],    # Track page hit occurrences
            "fragmentation_history": [],  # Track fragmentation levels
            "algorithm_performance": {  # Track performance of each algorithm
                "first_fit": {"avg_time": 0, "success_rate": 0},
                "best_fit": {"avg_time": 0, "success_rate": 0},
                "worst_fit": {"avg_time": 0, "success_rate": 0},
                "next_fit": {"avg_time": 0, "success_rate": 0}
            }
        }
        
        # Add fragmentation analysis metrics
        self.fragmentation_metrics = {
            "external_fragmentation": [],  # Track external fragmentation over time
            "internal_fragmentation": [],  # Track internal fragmentation over time
            "total_wasted_space": 0,      # Total wasted space due to fragmentation
            "fragmentation_history": []    # Historical fragmentation data
        }
        
        # Add process scheduling metrics
        self.scheduling_metrics = {
            "process_queue": [],           # Processes waiting for memory
            "waiting_times": {},           # Track waiting times for each process
            "cpu_utilization": [],         # Track CPU utilization
            "scheduling_history": []       # Historical scheduling data
        }

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
        """Allocate memory with current algorithm and track performance"""
        start_time = datetime.now()
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
        
        # Track allocation time
        allocation_time = (datetime.now() - start_time).total_seconds()
        self.performance_metrics["allocation_times"].append(allocation_time)
        
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
        """Deallocate memory blocks and track performance"""
        start_time = datetime.now()
        deallocated = False
        
        for block in self.memory:
            if block.process_id == process_id:
                if block_id is None:
                    block.status = "free"
                    block.process_id = None
                    block.block_id = None
                    deallocated = True
                elif block.block_id == block_id:
                    block.status = "free"
                    block.process_id = None
                    block.block_id = None
                    deallocated = True
                    break
        
        if deallocated:
            self.merge_free_blocks()
            # Track deallocation time
            deallocation_time = (datetime.now() - start_time).total_seconds()
            self.performance_metrics["deallocation_times"].append(deallocation_time)
        
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
        """Simulate page access and track performance"""
        if process_id in self.page_table:
            pages = self.page_table[process_id]
            if 0 <= page_number < len(pages):
                page = pages[page_number]
                if page.is_valid:
                    self.page_hits += 1
                    self.performance_metrics["page_hit_history"].append(datetime.now())
                    if self.replacement_algorithm == "LRU":
                        self.page_access_times[page.frame_number] = datetime.now()
                        if page.frame_number in self.page_references:
                            self.page_references.remove(page.frame_number)
                        self.page_references.append(page.frame_number)
                    return True
                else:
                    self.handle_page_fault(page)
                    self.performance_metrics["page_fault_history"].append(datetime.now())
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
        fragmentation = (1 - (largest_free_block / total_free)) * 100
        return fragmentation

    def get_performance_metrics(self):
        """Get current performance metrics"""
        current_usage = sum(block.size for block in self.memory if block.status == "allocated")
        current_fragmentation = self.calculate_fragmentation()
        
        # Update metrics
        self.performance_metrics["memory_usage"].append(current_usage)
        self.performance_metrics["peak_memory"] = max(
            self.performance_metrics["peak_memory"],
            current_usage
        )
        self.performance_metrics["fragmentation_history"].append(current_fragmentation)
        
        # Calculate page management metrics
        total_accesses = self.page_faults + self.page_hits
        if total_accesses > 0:
            hit_ratio = self.page_hits / total_accesses
            fault_ratio = self.page_faults / total_accesses
        else:
            hit_ratio = fault_ratio = 0
            
        # Calculate algorithm performance
        for algorithm in self.algorithm_stats:
            stats = self.algorithm_stats[algorithm]
            total_attempts = stats["allocations"] + stats["failures"]
            if total_attempts > 0:
                self.performance_metrics["algorithm_performance"][algorithm]["success_rate"] = (
                    stats["allocations"] / total_attempts
                )
        
        return {
            "current_usage": current_usage,
            "peak_memory": self.performance_metrics["peak_memory"],
            "memory_usage_history": self.performance_metrics["memory_usage"],
            "fragmentation_history": self.performance_metrics["fragmentation_history"],
            "page_management": {
                "hit_ratio": hit_ratio,
                "fault_ratio": fault_ratio,
                "total_accesses": total_accesses
            },
            "algorithm_performance": self.performance_metrics["algorithm_performance"],
            "operation_times": {
                "allocation": self.performance_metrics["allocation_times"],
                "deallocation": self.performance_metrics["deallocation_times"]
            }
        }

    def analyze_fragmentation(self):
        """Analyze both external and internal fragmentation"""
        # Calculate external fragmentation
        free_blocks = [block for block in self.memory if block.status == "free"]
        total_free = sum(block.size for block in free_blocks)
        if total_free > 0:
            largest_free = max(block.size for block in free_blocks)
            external_frag = (1 - (largest_free / total_free)) * 100
        else:
            external_frag = 0

        # Calculate internal fragmentation
        internal_frag = 0
        total_wasted = 0
        for block in self.memory:
            if block.status == "allocated":
                # Calculate wasted space within allocated blocks
                wasted = block.size - (block.size // self.page_size) * self.page_size
                total_wasted += wasted
                internal_frag += (wasted / block.size) * 100

        # Update metrics
        self.fragmentation_metrics["external_fragmentation"].append(external_frag)
        self.fragmentation_metrics["internal_fragmentation"].append(internal_frag)
        self.fragmentation_metrics["total_wasted_space"] = total_wasted
        self.fragmentation_metrics["fragmentation_history"].append({
            "time": datetime.now(),
            "external": external_frag,
            "internal": internal_frag,
            "total_wasted": total_wasted
        })

        return {
            "external_fragmentation": external_frag,
            "internal_fragmentation": internal_frag,
            "total_wasted_space": total_wasted
        }

    def schedule_process(self, process_id, priority=0):
        """Schedule a process for memory allocation"""
        if process_id not in self.scheduling_metrics["waiting_times"]:
            self.scheduling_metrics["waiting_times"][process_id] = {
                "start_time": datetime.now(),
                "priority": priority
            }
            self.scheduling_metrics["process_queue"].append(process_id)
            self.scheduling_metrics["scheduling_history"].append({
                "time": datetime.now(),
                "process_id": process_id,
                "action": "queued",
                "priority": priority
            })

    def update_scheduling_metrics(self):
        """Update process scheduling metrics"""
        current_time = datetime.now()
        
        # Update waiting times
        for process_id, data in self.scheduling_metrics["waiting_times"].items():
            if process_id in self.scheduling_metrics["process_queue"]:
                wait_time = (current_time - data["start_time"]).total_seconds()
                data["current_wait"] = wait_time

        # Calculate CPU utilization (simplified)
        active_processes = len([p for p in self.scheduling_metrics["process_queue"] 
                              if p in self.page_table])
        total_processes = len(self.scheduling_metrics["process_queue"])
        cpu_util = (active_processes / total_processes * 100) if total_processes > 0 else 0
        
        self.scheduling_metrics["cpu_utilization"].append(cpu_util)

    def get_fragmentation_report(self):
        """Generate a detailed fragmentation report"""
        analysis = self.analyze_fragmentation()
        return {
            "current_metrics": analysis,
            "historical_data": self.fragmentation_metrics["fragmentation_history"],
            "recommendations": self.generate_fragmentation_recommendations(analysis)
        }

    def get_scheduling_report(self):
        """Generate a detailed scheduling report"""
        self.update_scheduling_metrics()
        return {
            "queue_status": {
                "total_processes": len(self.scheduling_metrics["process_queue"]),
                "waiting_times": self.scheduling_metrics["waiting_times"],
                "cpu_utilization": self.scheduling_metrics["cpu_utilization"][-1] if self.scheduling_metrics["cpu_utilization"] else 0
            },
            "scheduling_history": self.scheduling_metrics["scheduling_history"],
            "recommendations": self.generate_scheduling_recommendations()
        }

    def generate_fragmentation_recommendations(self, analysis):
        """Generate recommendations based on fragmentation analysis"""
        recommendations = []
        
        if analysis["external_fragmentation"] > 70:
            recommendations.append("High external fragmentation detected. Consider memory compaction.")
        if analysis["internal_fragmentation"] > 30:
            recommendations.append("High internal fragmentation detected. Consider adjusting page size.")
        if analysis["total_wasted_space"] > MEMORY_SIZE * 0.2:
            recommendations.append("Significant memory waste detected. Review allocation strategy.")
            
        return recommendations

    def generate_scheduling_recommendations(self):
        """Generate recommendations based on scheduling metrics"""
        recommendations = []
        
        avg_wait_time = sum(data["current_wait"] for data in self.scheduling_metrics["waiting_times"].values()) / len(self.scheduling_metrics["waiting_times"]) if self.scheduling_metrics["waiting_times"] else 0
        
        if avg_wait_time > 5:  # 5 seconds threshold
            recommendations.append("High process waiting times detected. Consider increasing memory size.")
        if self.scheduling_metrics["cpu_utilization"][-1] < 50:
            recommendations.append("Low CPU utilization. Consider optimizing memory allocation strategy.")
            
        return recommendations

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
        
        # Create performance metrics panel in right frame
        self.performance_frame = ttk.LabelFrame(right_frame, text="Performance Metrics", padding=10)
        self.performance_frame.pack(fill="x", pady=5)

        # Create metrics display areas
        self.metrics_labels = {}

        # Memory Usage Metrics
        memory_frame = ttk.LabelFrame(self.performance_frame, text="Memory Usage", padding=5)
        memory_frame.pack(fill="x", pady=5)

        self.metrics_labels["current_usage"] = ttk.Label(memory_frame, text="Current Usage: 0 units")
        self.metrics_labels["current_usage"].pack(anchor="w")

        self.metrics_labels["peak_memory"] = ttk.Label(memory_frame, text="Peak Memory: 0 units")
        self.metrics_labels["peak_memory"].pack(anchor="w")

        # Page Management Metrics
        page_frame = ttk.LabelFrame(self.performance_frame, text="Page Management", padding=5)
        page_frame.pack(fill="x", pady=5)

        self.metrics_labels["hit_ratio"] = ttk.Label(page_frame, text="Hit Ratio: 0%")
        self.metrics_labels["hit_ratio"].pack(anchor="w")

        self.metrics_labels["fault_ratio"] = ttk.Label(page_frame, text="Fault Ratio: 0%")
        self.metrics_labels["fault_ratio"].pack(anchor="w")

        # Algorithm Performance
        algo_frame = ttk.LabelFrame(self.performance_frame, text="Algorithm Performance", padding=5)
        algo_frame.pack(fill="x", pady=5)

        self.metrics_labels["algorithm_stats"] = {}
        for algorithm in ["first_fit", "best_fit", "worst_fit", "next_fit"]:
            self.metrics_labels["algorithm_stats"][algorithm] = ttk.Label(
                algo_frame, 
                text=f"{algorithm.replace('_', ' ').title()}: 0% success rate"
            )
            self.metrics_labels["algorithm_stats"][algorithm].pack(anchor="w")

        # Operation Times
        time_frame = ttk.LabelFrame(self.performance_frame, text="Operation Times", padding=5)
        time_frame.pack(fill="x", pady=5)

        self.metrics_labels["avg_allocation"] = ttk.Label(time_frame, text="Avg Allocation Time: 0.0s")
        self.metrics_labels["avg_allocation"].pack(anchor="w")

        self.metrics_labels["avg_deallocation"] = ttk.Label(time_frame, text="Avg Deallocation Time: 0.0s")
        self.metrics_labels["avg_deallocation"].pack(anchor="w")

        # Add access pattern graph below performance metrics
        self.add_access_pattern_graph(right_frame)

        # Add Fragmentation Analysis Frame
        fragmentation_frame = ttk.LabelFrame(right_frame, text="Fragmentation Analysis", padding=10)
        fragmentation_frame.pack(fill="x", pady=5)

        # Create fragmentation metrics labels
        self.fragmentation_labels = {}
        self.fragmentation_labels["external"] = ttk.Label(fragmentation_frame, text="External Fragmentation: 0%")
        self.fragmentation_labels["external"].pack(anchor="w")

        self.fragmentation_labels["internal"] = ttk.Label(fragmentation_frame, text="Internal Fragmentation: 0%")
        self.fragmentation_labels["internal"].pack(anchor="w")

        self.fragmentation_labels["wasted"] = ttk.Label(fragmentation_frame, text="Total Wasted Space: 0 units")
        self.fragmentation_labels["wasted"].pack(anchor="w")

        # Add Process Scheduling Frame
        scheduling_frame = ttk.LabelFrame(right_frame, text="Process Scheduling", padding=10)
        scheduling_frame.pack(fill="x", pady=5)

        # Create scheduling metrics labels
        self.scheduling_labels = {}
        self.scheduling_labels["queue"] = ttk.Label(scheduling_frame, text="Processes in Queue: 0")
        self.scheduling_labels["queue"].pack(anchor="w")

        self.scheduling_labels["avg_wait"] = ttk.Label(scheduling_frame, text="Average Wait Time: 0.0s")
        self.scheduling_labels["avg_wait"].pack(anchor="w")

        self.scheduling_labels["cpu_util"] = ttk.Label(scheduling_frame, text="CPU Utilization: 0%")
        self.scheduling_labels["cpu_util"].pack(anchor="w")

        # Add recommendations frame
        recommendations_frame = ttk.LabelFrame(right_frame, text="Recommendations", padding=10)
        recommendations_frame.pack(fill="x", pady=5)

        self.recommendations_text = tk.Text(recommendations_frame, height=4, wrap=tk.WORD)
        self.recommendations_text.pack(fill="x", expand=True)
        
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
            # Get and validate size
            size_str = self.size_entry.get().strip()
            if not size_str:
                messagebox.showwarning(
                    "Missing Information",
                    "Please enter a Size for the segment.\n\n"
                    "Example: 20, 30, 40, etc.\n"
                    "Tip: Size should be a positive number."
                )
                return
            
            try:
                size = int(size_str)
            except ValueError:
                messagebox.showerror(
                    "Invalid Size",
                    f"The Size '{size_str}' is invalid.\n\n"
                    "Size must be a whole number.\n"
                    "Example: 20, 30, 40, etc.\n"
                    "Please enter a valid number."
                )
                return
            
            if size <= 0:
                messagebox.showerror(
                    "Invalid Size",
                    f"The Size '{size}' is invalid.\n\n"
                    "Size must be positive.\n"
                    "Please enter a positive number."
                )
                return
            
            if size > MAX_MEMORY_SIZE:
                messagebox.showerror(
                    "Size Too Large",
                    f"The Size '{size}' is too large.\n\n"
                    f"Maximum allowed size is {MAX_MEMORY_SIZE} units.\n"
                    "Please enter a smaller size."
                )
                return
            
            # Get and validate segment name
            name = self.segment_name_entry.get().strip()
            if not name:
                messagebox.showwarning(
                    "Missing Information",
                    "Please enter a Segment Name.\n\n"
                    "Example: Code, Data, Stack, etc.\n"
                    "Tip: Use descriptive names for your segments."
                )
                return
            
            # Validate segment name format (only letters, numbers, and underscores)
            if not name.replace('_', '').isalnum():
                messagebox.showerror(
                    "Invalid Segment Name",
                    f"The Segment Name '{name}' is invalid.\n\n"
                    "Segment names can only contain:\n"
                    "• Letters (a-z, A-Z)\n"
                    "• Numbers (0-9)\n"
                    "• Underscores (_)\n\n"
                    "Example: Code_Segment, Data_Segment, Stack_Segment"
                )
                return
            
            # Get and validate process ID
            process_id = self.process_entry.get().strip()
            if not process_id:
                messagebox.showwarning(
                    "Missing Information",
                    "Please enter a Process ID.\n\n"
                    "Example: P1, P2, etc.\n"
                    "Tip: You can find valid Process IDs in the Active Processes list."
                )
                return
            
            if not process_id.startswith('P'):
                messagebox.showerror(
                    "Invalid Process ID",
                    f"The Process ID '{process_id}' is invalid.\n\n"
                    "Process IDs must start with 'P' followed by a number.\n"
                    "Example: P1, P2, P3, etc.\n\n"
                    "Please check the Active Processes list for valid Process IDs."
                )
                return
            
            # Check if process exists
            if process_id not in self.memory_manager.page_table:
                messagebox.showerror(
                    "Process Not Found",
                    f"Process '{process_id}' does not exist.\n\n"
                    "Please check the Active Processes list for valid Process IDs.\n"
                    "You may need to create a process first."
                )
                return
            
            # Check if segment name already exists for this process
            if process_id in self.memory_manager.segment_table:
                existing_segments = [s.name for s in self.memory_manager.segment_table[process_id]]
                if name in existing_segments:
                    messagebox.showerror(
                        "Duplicate Segment Name",
                        f"Segment '{name}' already exists for Process {process_id}.\n\n"
                        "Please choose a different name for your segment."
                    )
                    return
            
            # Create the segment
            segment = self.memory_manager.create_segment(process_id, size, name)
            
            # Show success message with details
            messagebox.showinfo(
                "Segment Created Successfully",
                f"Successfully created segment '{name}' for Process {process_id}.\n\n"
                f"Details:\n"
                f"• Size: {size} units\n"
                f"• Pages Allocated: {len(segment.pages)}\n"
                f"• Page Size: {self.memory_manager.page_size} units"
            )
            
            self.status_var.set(f"Created segment '{name}' for process {process_id}")
            self.update_visualization()
            
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"An unexpected error occurred:\n{str(e)}\n\n"
                "Please try again or contact support if the problem persists."
            )
            self.status_var.set("Error occurred during segment creation")

    def access_page(self):
        """Simulate page access"""
        try:
            process_id = self.page_process_entry.get().strip()
            page_number_str = self.page_number_entry.get().strip()
            
            # Check if fields are empty
            if not process_id:
                messagebox.showwarning(
                    "Missing Information",
                    "Please enter a Process ID.\n\n"
                    "Example: P1, P2, etc.\n"
                    "Tip: You can find valid Process IDs in the Active Processes list."
                )
                return
            
            if not page_number_str:
                messagebox.showwarning(
                    "Missing Information",
                    "Please enter a Page Number.\n\n"
                    "Example: 0, 1, 2, etc.\n"
                    "Tip: Page numbers start from 0."
                )
                return
            
            # Validate process ID format
            if not process_id.startswith('P'):
                messagebox.showerror(
                    "Invalid Process ID",
                    f"The Process ID '{process_id}' is invalid.\n\n"
                    "Process IDs must start with 'P' followed by a number.\n"
                    "Example: P1, P2, P3, etc.\n\n"
                    "Please check the Active Processes list for valid Process IDs."
                )
                return
            
            # Convert and validate page number
            try:
                page_number = int(page_number_str)
            except ValueError:
                messagebox.showerror(
                    "Invalid Page Number",
                    f"The Page Number '{page_number_str}' is invalid.\n\n"
                    "Page numbers must be whole numbers.\n"
                    "Example: 0, 1, 2, etc.\n"
                    "Please enter a valid number."
                )
                return
            
            if page_number < 0:
                messagebox.showerror(
                    "Invalid Page Number",
                    f"The Page Number '{page_number}' is invalid.\n\n"
                    "Page numbers cannot be negative.\n"
                    "Please enter a non-negative number."
                )
                return
            
            # Check if process exists
            if process_id not in self.memory_manager.page_table:
                messagebox.showerror(
                    "Process Not Found",
                    f"Process '{process_id}' does not exist.\n\n"
                    "Please check the Active Processes list for valid Process IDs.\n"
                    "You may need to create a process first."
                )
                return
            
            # Check if page number is valid for the process
            process_pages = self.memory_manager.page_table[process_id]
            if page_number >= len(process_pages):
                messagebox.showerror(
                    "Invalid Page Number",
                    f"Page {page_number} does not exist for Process {process_id}.\n\n"
                    f"Process {process_id} has {len(process_pages)} pages (0 to {len(process_pages)-1}).\n"
                    "Please enter a valid page number."
                )
                return
            
            # Attempt to access the page
            success = self.memory_manager.access_page(process_id, page_number)
            
            if success:
                # Show success message with details
                stats = self.memory_manager.get_paging_stats()
                messagebox.showinfo(
                    "Page Access Successful",
                    f"Successfully accessed Page {page_number} of Process {process_id}.\n\n"
                    f"Current Statistics:\n"
                    f"• Page Faults: {stats['page_faults']}\n"
                    f"• Page Hits: {stats['page_hits']}\n"
                    f"• Fault Rate: {stats['fault_rate']:.1%}\n"
                    f"• Pages in Memory: {stats['total_pages']}/{stats['max_pages']}"
                )
                self.status_var.set(f"Accessed page {page_number} of process {process_id}")
            else:
                messagebox.showerror(
                    "Access Failed",
                    f"Failed to access Page {page_number} of Process {process_id}.\n\n"
                    "This might be due to:\n"
                    "• Invalid page number\n"
                    "• Process not found\n"
                    "• Memory allocation issues"
                )
                self.status_var.set(f"Failed to access page {page_number} of process {process_id}")
            
            self.update_visualization()
            
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"An unexpected error occurred:\n{str(e)}\n\n"
                "Please try again or contact support if the problem persists."
            )
            self.status_var.set("Error occurred during page access")

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

        # Update performance metrics
        metrics = self.memory_manager.get_performance_metrics()
        
        # Update memory usage metrics
        self.metrics_labels["current_usage"].config(
            text=f"Current Usage: {metrics['current_usage']} units"
        )
        self.metrics_labels["peak_memory"].config(
            text=f"Peak Memory: {metrics['peak_memory']} units"
        )
        
        # Update page management metrics
        self.metrics_labels["hit_ratio"].config(
            text=f"Hit Ratio: {metrics['page_management']['hit_ratio']:.1%}"
        )
        self.metrics_labels["fault_ratio"].config(
            text=f"Fault Ratio: {metrics['page_management']['fault_ratio']:.1%}"
        )
        
        # Update algorithm performance metrics
        for algorithm, stats in metrics['algorithm_performance'].items():
            self.metrics_labels["algorithm_stats"][algorithm].config(
                text=f"{algorithm.replace('_', ' ').title()}: {stats['success_rate']:.1%} success rate"
            )
        
        # Update operation times
        if metrics['operation_times']['allocation']:
            avg_alloc = sum(metrics['operation_times']['allocation']) / len(metrics['operation_times']['allocation'])
            self.metrics_labels["avg_allocation"].config(
                text=f"Avg Allocation Time: {avg_alloc:.3f}s"
            )
        
        if metrics['operation_times']['deallocation']:
            avg_dealloc = sum(metrics['operation_times']['deallocation']) / len(metrics['operation_times']['deallocation'])
            self.metrics_labels["avg_deallocation"].config(
                text=f"Avg Deallocation Time: {avg_dealloc:.3f}s"
            )

        # Update fragmentation analysis
        frag_report = self.memory_manager.get_fragmentation_report()
        self.fragmentation_labels["external"].config(
            text=f"External Fragmentation: {frag_report['current_metrics']['external_fragmentation']:.1f}%"
        )
        self.fragmentation_labels["internal"].config(
            text=f"Internal Fragmentation: {frag_report['current_metrics']['internal_fragmentation']:.1f}%"
        )
        self.fragmentation_labels["wasted"].config(
            text=f"Total Wasted Space: {frag_report['current_metrics']['total_wasted_space']} units"
        )
        
        # Update scheduling metrics
        sched_report = self.memory_manager.get_scheduling_report()
        self.scheduling_labels["queue"].config(
            text=f"Processes in Queue: {sched_report['queue_status']['total_processes']}"
        )

        # Calculate average wait time safely
        waiting_times = sched_report['queue_status']['waiting_times']
        if waiting_times:
            avg_wait = sum(data['current_wait'] for data in waiting_times.values()) / len(waiting_times)
        else:
            avg_wait = 0.0

        self.scheduling_labels["avg_wait"].config(
            text=f"Average Wait Time: {avg_wait:.1f}s"
        )

        self.scheduling_labels["cpu_util"].config(
            text=f"CPU Utilization: {sched_report['queue_status']['cpu_utilization']:.1f}%"
        )
        
        # Update recommendations
        self.recommendations_text.delete(1.0, tk.END)
        recommendations = frag_report['recommendations'] + sched_report['recommendations']
        if recommendations:
            for rec in recommendations:
                self.recommendations_text.insert(tk.END, f"• {rec}\n")
        else:
            self.recommendations_text.insert(tk.END, "No recommendations at this time.")

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
        fragmentation = (1 - (largest_free_block / total_free)) * 100
        return fragmentation

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