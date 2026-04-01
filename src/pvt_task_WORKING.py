"""
Psychomotor Vigilance Task (PVT) - WORKING VERSION
Compatible with all tkinter versions
10 minutes of stimuli at random intervals (1-10 seconds)
"""

import tkinter as tk
from tkinter import messagebox
import random
import time
import json
from datetime import datetime
import os
import statistics

class PsychomotorVigilanceTask:
    def __init__(self, root):
        self.root = root
        self.root.title("Psychomotor Vigilance Task (PVT)")
        
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Make fullscreen
        self.root.geometry(f"{screen_width}x{screen_height}+0+0")
        try:
            self.root.state('zoomed')  # Windows
        except:
            pass
        try:
            self.root.attributes('-fullscreen', True)  # Linux/Mac
        except:
            pass
        
        self.root.configure(bg='black')
        
        # Force focus
        self.root.focus_set()
        self.root.update()
        
        # Task parameters
        self.task_duration = 10 * 60 * 1000  # 10 minutes in ms
        self.min_isi = 1000  # 1 second
        self.max_isi = 10000  # 10 seconds
        
        # Performance thresholds
        self.anticipatory_threshold = 100  # RT < 100ms
        self.lapse_threshold = 500  # RT > 500ms
        
        # Data collection
        self.trial_data = []
        self.task_start_time = None
        self.stimulus_onset_time = None
        self.isi_start_time = None
        self.current_isi = None
        
        # State tracking
        self.waiting_for_stimulus = False
        self.stimulus_active = False
        self.task_running = False
        self.instructions_mode = True
        
        # Performance tracking
        self.reaction_times = []
        self.lapses = 0
        self.anticipatory_responses = 0
        
        # Create UI
        self.create_widgets()
        
        # Bind keyboard - only lowercase (compatible)
        self.root.bind('<space>', self.response_made)
        self.root.bind('<Escape>', lambda e: self.emergency_exit())
        self.root.bind('<KeyPress>', self.key_pressed)
        
        # Show instructions
        self.show_instructions()
        
    def create_widgets(self):
        """Create UI elements"""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Main stimulus display
        self.stimulus_label = tk.Label(
            self.root,
            text="",
            font=("Arial", 72, "bold"),
            bg='black',
            fg='red',
            width=10
        )
        self.stimulus_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        # Instructions/info label
        self.info_label = tk.Label(
            self.root,
            text="",
            font=("Arial", 16),
            bg='black',
            fg='white',
            wraplength=900,
            justify=tk.CENTER
        )
        self.info_label.place(relx=0.5, rely=0.3, anchor=tk.CENTER)
        
        # Feedback label
        self.feedback_label = tk.Label(
            self.root,
            text="",
            font=("Arial", 24),
            bg='black',
            fg='white'
        )
        self.feedback_label.place(relx=0.5, rely=0.7, anchor=tk.CENTER)
        
        # Progress bar
        self.progress_label = tk.Label(
            self.root,
            text="",
            font=("Arial", 12),
            bg='black',
            fg='gray'
        )
        self.progress_label.place(x=10, y=10)
        
        # Trial counter
        self.trial_label = tk.Label(
            self.root,
            text="",
            font=("Arial", 12),
            bg='black',
            fg='gray'
        )
        self.trial_label.place(x=10, y=40)
        
        # Debug label
        self.debug_label = tk.Label(
            self.root,
            text="",
            font=("Arial", 10),
            bg='black',
            fg='cyan'
        )
        self.debug_label.place(relx=0.5, rely=0.95, anchor=tk.CENTER)
        
    def key_pressed(self, event):
        """Debug: Show which key was pressed"""
        self.debug_label.config(text=f"Key: {event.keysym}")
        
    def show_instructions(self):
        """Display task instructions"""
        instructions = """
PSYCHOMOTOR VIGILANCE TASK (PVT)

A counter will appear at random intervals.
The counter starts at 0 and counts up in milliseconds.

YOUR TASK:
Press SPACEBAR as quickly as possible when the counter appears.

IMPORTANT:
• Wait for the counter - don't press early
• Respond as fast as possible
• Stay focused for 10 minutes
• Intervals are random (1-10 seconds)

After each response, you'll see your reaction time.

═══════════════════════════════════════════════

Click anywhere on screen, then press SPACEBAR to begin
        """
        
        self.info_label.config(text=instructions)
        self.feedback_label.config(text="👆 CLICK SCREEN, then press SPACEBAR 👆", fg='yellow')
        
    def response_made(self, event):
        """Handle spacebar response"""
        response_time = time.time()
        
        # Instructions mode
        if self.instructions_mode:
            self.feedback_label.config(text="✓ SPACEBAR WORKS! Starting task...", fg='green')
            self.instructions_mode = False
            self.root.after(1000, self.start_task)
            return
        
        # Ignore if task not running
        if not self.task_running:
            return
        
        # Anticipatory response (during ISI)
        if self.waiting_for_stimulus:
            actual_isi = (response_time - self.isi_start_time) * 1000
            
            self.anticipatory_responses += 1
            
            # Record trial
            trial_data = {
                'trial': len(self.trial_data) + 1,
                'time_on_watch_s': round(response_time - self.task_start_time, 3),
                'scheduled_isi_ms': self.current_isi,
                'actual_isi_ms': round(actual_isi, 2),
                'reaction_time_ms': None,
                'response_type': 'anticipatory',
                'lapse': False
            }
            self.trial_data.append(trial_data)
            
            # Show feedback
            self.feedback_label.config(
                text="TOO EARLY! Wait for counter.",
                fg='red'
            )
            
            # Continue with next trial
            self.root.after(2000, self.start_isi)
            
        # Valid response to stimulus
        elif self.stimulus_active:
            rt = (response_time - self.stimulus_onset_time) * 1000
            
            # Check if lapse
            is_lapse = rt > self.lapse_threshold
            if is_lapse:
                self.lapses += 1
            
            # Store RT
            self.reaction_times.append(rt)
            
            # Stop stimulus
            self.stimulus_active = False
            
            # Record trial
            trial_data = {
                'trial': len(self.trial_data) + 1,
                'time_on_watch_s': round(response_time - self.task_start_time, 3),
                'scheduled_isi_ms': self.current_isi,
                'actual_isi_ms': self.current_isi,
                'reaction_time_ms': round(rt, 2),
                'response_type': 'valid',
                'lapse': is_lapse
            }
            self.trial_data.append(trial_data)
            
            # Show feedback
            if is_lapse:
                self.feedback_label.config(
                    text=f"{int(rt)} ms (Lapse)",
                    fg='orange'
                )
            elif rt < self.anticipatory_threshold:
                self.feedback_label.config(
                    text=f"{int(rt)} ms (Very Fast!)",
                    fg='yellow'
                )
            else:
                self.feedback_label.config(
                    text=f"{int(rt)} ms",
                    fg='green'
                )
            
            # Clear stimulus
            self.stimulus_label.config(text="")
            
            # Continue with next trial
            self.root.after(1000, self.start_isi)
    
    def start_task(self):
        """Initialize and start PVT"""
        # Clear instructions
        self.info_label.config(text="")
        self.feedback_label.config(text="")
        
        # Start task
        self.task_running = True
        self.task_start_time = time.time()
        
        # Begin first ISI
        self.start_isi()
        
        # Schedule task end
        self.root.after(self.task_duration, self.end_task)
        
    def start_isi(self):
        """Begin inter-stimulus interval"""
        self.waiting_for_stimulus = True
        self.stimulus_active = False
        
        # Clear display
        self.stimulus_label.config(text="")
        self.feedback_label.config(text="")
        
        # Generate random ISI
        self.current_isi = random.randint(self.min_isi, self.max_isi)
        self.isi_start_time = time.time()
        
        # Update progress
        elapsed = (time.time() - self.task_start_time)
        progress = (elapsed / (self.task_duration / 1000)) * 100
        self.progress_label.config(
            text=f"Progress: {progress:.1f}% | Time: {elapsed/60:.1f} / 10.0 min"
        )
        self.trial_label.config(text=f"Trials: {len(self.trial_data)}")
        
        # Schedule stimulus onset
        self.root.after(self.current_isi, self.present_stimulus)
        
    def present_stimulus(self):
        """Display counting stimulus"""
        if not self.task_running:
            return
        
        self.waiting_for_stimulus = False
        self.stimulus_active = True
        self.stimulus_onset_time = time.time()
        
        # Start counter animation
        self.update_counter()
        
    def update_counter(self):
        """Animate millisecond counter"""
        if not self.stimulus_active or not self.task_running:
            return
        
        # Calculate elapsed time
        elapsed_ms = int((time.time() - self.stimulus_onset_time) * 1000)
        
        # Display counter
        self.stimulus_label.config(text=str(elapsed_ms))
        
        # Continue updating
        self.root.after(10, self.update_counter)
        
    def end_task(self):
        """Complete task"""
        self.task_running = False
        self.stimulus_active = False
        
        # Calculate performance
        self.calculate_performance()
        
        # Save data
        self.save_data()
        
        # Show results
        self.show_results()
        
    def calculate_performance(self):
        """Calculate PVT metrics"""
        if not self.reaction_times:
            self.mean_rt = 0
            self.median_rt = 0
            self.std_rt = 0
            self.min_rt = 0
            self.max_rt = 0
            self.reciprocal_rt = 0
            self.fastest_10_mean = 0
            self.slowest_10_mean = 0
            self.lapse_percentage = 0
            return
        
        # Standard metrics
        self.mean_rt = statistics.mean(self.reaction_times)
        self.median_rt = statistics.median(self.reaction_times)
        self.std_rt = statistics.stdev(self.reaction_times) if len(self.reaction_times) > 1 else 0
        self.min_rt = min(self.reaction_times)
        self.max_rt = max(self.reaction_times)
        
        # Fastest 10%
        fastest_10_pct = sorted(self.reaction_times)[:max(1, len(self.reaction_times) // 10)]
        self.fastest_10_mean = statistics.mean(fastest_10_pct) if fastest_10_pct else 0
        
        # Slowest 10%
        slowest_10_pct = sorted(self.reaction_times, reverse=True)[:max(1, len(self.reaction_times) // 10)]
        self.slowest_10_mean = statistics.mean(slowest_10_pct) if slowest_10_pct else 0
        
        # Reciprocal RT
        reciprocal_rts = [1000 / rt for rt in self.reaction_times if rt > 0]
        self.reciprocal_rt = statistics.mean(reciprocal_rts) if reciprocal_rts else 0
        
        # Lapse percentage
        self.lapse_percentage = (self.lapses / len(self.reaction_times) * 100) if self.reaction_times else 0
        
    def save_data(self):
        """Save data to JSON"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"pvt_data_{timestamp}.json"
        
        output_data = {
            'metadata': {
                'timestamp': timestamp,
                'task_duration_minutes': 10,
                'isi_range_seconds': [1, 10],
                'lapse_threshold_ms': self.lapse_threshold,
                'anticipatory_threshold_ms': self.anticipatory_threshold
            },
            'performance': {
                'total_trials': len(self.trial_data),
                'valid_responses': len(self.reaction_times),
                'anticipatory_responses': self.anticipatory_responses,
                'mean_rt_ms': round(self.mean_rt, 2),
                'median_rt_ms': round(self.median_rt, 2),
                'std_rt_ms': round(self.std_rt, 2),
                'min_rt_ms': round(self.min_rt, 2),
                'max_rt_ms': round(self.max_rt, 2),
                'fastest_10pct_mean_ms': round(self.fastest_10_mean, 2),
                'slowest_10pct_mean_ms': round(self.slowest_10_mean, 2),
                'reciprocal_rt': round(self.reciprocal_rt, 3),
                'lapses': self.lapses,
                'lapse_percentage': round(self.lapse_percentage, 2)
            },
            'trial_data': self.trial_data
        }
        
        with open(filename, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"\nData saved to: {filename}")
        self.output_filename = filename
        
    def show_results(self):
        """Display performance summary"""
        results_text = f"""
TASK COMPLETE

PVT Performance Summary:
  Total Trials: {len(self.trial_data)}
  Valid Responses: {len(self.reaction_times)}
  Anticipatory: {self.anticipatory_responses}

Reaction Time:
  Mean: {self.mean_rt:.0f} ms
  Median: {self.median_rt:.0f} ms
  SD: {self.std_rt:.0f} ms

Vigilance:
  Lapses (>500ms): {self.lapses} ({self.lapse_percentage:.1f}%)
  Fastest 10%: {self.fastest_10_mean:.0f} ms
  Slowest 10%: {self.slowest_10_mean:.0f} ms

Data saved to: {self.output_filename}

Press ESC to exit
        """
        
        # Clear other labels
        self.stimulus_label.config(text="")
        self.feedback_label.config(text="")
        self.progress_label.config(text="")
        self.trial_label.config(text="")
        self.debug_label.config(text="")
        
        # Show results
        self.info_label.config(text=results_text)
        self.info_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
    def emergency_exit(self):
        """Exit with data save"""
        if messagebox.askyesno("Exit", "Exit and save data?"):
            self.task_running = False
            if self.trial_data:
                self.calculate_performance()
                self.save_data()
            self.root.quit()

def main():
    root = tk.Tk()
    app = PsychomotorVigilanceTask(root)
    root.mainloop()

if __name__ == "__main__":
    main()
