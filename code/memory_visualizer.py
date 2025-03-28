import tkinter as tk
from tkinter import ttk, messagebox
import random

# Constants
MEMORY_SIZE = 100  # Total memory size
BLOCK_HEIGHT = 30  # Increased height for better visibility
BLOCK_WIDTH = 3    # Scaling factor for block visualization
MAX_MEMORY_SIZE = 1000  # Maximum allowed memory size

class MemoryBlock:
    def __init__(self, start, size, status="free", process_id=None):
        self.start = start
        self.size = size
        self.status = status
        self.process_id = process_id  # Track which process owns this block

class MemoryManager:
    def __init__(self):
        self.memory = [MemoryBlock(0, MEMORY_SIZE, "free")]
        self.algorithm = "first_fit"
        self.process_counter = 1  # To generate unique process IDs
        self.process_colors = {}  # Store colors for each process

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
        self.process_colors.clear()

    def allocate_memory(self, size):
        """Allocate memory with current algorithm"""
        process_id = f"P{self.process_counter}"
        self.process_counter += 1
        
        if self.algorithm == "first_fit":
            success = self.first_fit(size, process_id)
        elif self.algorithm == "best_fit":
            success = self.best_fit(size, process_id)
        elif self.algorithm == "worst_fit":
            success = self.worst_fit(size, process_id)
        
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
        fragmentation = self.calculate_fragmentation()
        
        stats_text = (
            f"Total Memory: {total_memory} units | "
            f"Used: {used_memory} units | "
            f"Free: {free_memory} units | "
            f"Fragmentation: {fragmentation:.1f}%"
        )
        self.stats_label.config(text=stats_text)

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

if __name__ == "__main__":
    root = tk.Tk()
    app = MemoryVisualizer(root)
    root.mainloop() 