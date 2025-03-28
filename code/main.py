import tkinter as tk
from tkinter import ttk, messagebox
import random

# Constants
MEMORY_SIZE = 100  # Total memory size
BLOCK_HEIGHT = 30  # Increased height for better visibility
BLOCK_WIDTH = 3    # Scaling factor for block visualization
MAX_MEMORY_SIZE = 1000  # Maximum allowed memory size

class MemoryBlock:
    def __init__(self, start, size, status="free", process_id=None, block_id=None):
        self.start = start
        self.size = size
        self.status = status
        self.process_id = process_id  # Track which process owns this block
        self.block_id = block_id  # Unique identifier for each block

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

class MemoryVisualizer:
    def __init__(self, root):
        self.root = root
        self.root.title("Dynamic Memory Management Visualizer")
        self.memory_manager = MemoryManager()

        # Configure main window
        self.root.geometry("1000x700")  # Increased window size
        
        # Create main frames
        control_frame = ttk.LabelFrame(root, text="Controls", padding=10)
        control_frame.pack(fill="x", padx=10, pady=5)
        
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
        process_frame = ttk.LabelFrame(root, text="Active Processes", padding=10)
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
        
        # Create canvas with scrollbars
        canvas_frame = ttk.Frame(root)
        canvas_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
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
        self.stats_label = ttk.Label(root, text="", font=('Helvetica', 10))
        self.stats_label.pack(pady=5)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(root, textvariable=self.status_var, relief="sunken")
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
        stats_frame = ttk.LabelFrame(root, text="Algorithm Statistics", padding=10)
        stats_frame.pack(fill="x", padx=10, pady=5)
        
        # Create statistics labels
        self.stats_labels = {}
        for i, algorithm in enumerate(["first_fit", "best_fit", "worst_fit", "next_fit"]):
            ttk.Label(stats_frame, text=algorithm.replace("_", " ").title()).grid(
                row=i, column=0, padx=5, pady=2
            )
            self.stats_labels[algorithm] = ttk.Label(stats_frame, text="")
            self.stats_labels[algorithm].grid(row=i, column=1, padx=5, pady=2)
        
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
        
        # Draw each memory block
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