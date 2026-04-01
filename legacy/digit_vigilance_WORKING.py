"""
Digit Vigilance Task - COMPATIBLE VERSION
Works with all tkinter versions
"""

import tkinter as tk
from tkinter import messagebox
import random
import time
import json
from datetime import datetime
import os

class DigitVigilanceTask:
    def __init__(self, root):
        self.root = root
        self.root.title("Digit Vigilance Task")
        
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
        
        # Experimental parameters
        self.difficulty = None
        self.stimulus_duration = 1000
        self.blank_duration_high = 500
        self.blank_duration_low = 1500
        
        # Task timing
        self.block_duration = 24 * 60 * 1000
        self.period_duration = 6 * 60 * 1000
        self.num_periods = 4
        self.signals_per_period = 5
        self.total_signals = 20
        
        # Screen quadrants
        self.quadrants = ['upper_left', 'upper_right', 'lower_left', 'lower_right']
        
        # Data collection
        self.trial_data = []
        self.current_trial = 0
        self.block_start_time = None
        self.stimulus_onset_time = None
        self.current_stimulus = None
        self.is_signal = False
        self.responded = False
        
        # Performance tracking
        self.hits = 0
        self.misses = 0
        self.false_alarms = 0
        self.correct_rejections = 0
        
        # Create UI
        self.create_widgets()
        
        # Bind keyboard - ONLY lowercase space (compatible with all tkinter)
        self.root.bind('<space>', self.response_made)
        self.root.bind('<Escape>', lambda e: self.emergency_exit())
        self.root.bind('<KeyPress>', self.key_pressed)  # Catch all keys for debugging
        
        # Show welcome
        self.show_welcome()
        
    def create_widgets(self):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Create canvas
        self.canvas = tk.Canvas(
            self.root,
            width=screen_width,
            height=screen_height,
            bg='black',
            highlightthickness=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Make canvas focusable and bind to it
        self.canvas.focus_set()
        self.canvas.bind('<space>', self.response_made)
        self.canvas.bind('<KeyPress>', self.key_pressed)
        self.canvas.bind('<Button-1>', lambda e: self.canvas.focus_set())
        
        # Calculate quadrant positions
        mid_x = screen_width // 2
        mid_y = screen_height // 2
        
        self.quadrant_positions = {
            'upper_left': (mid_x // 2, mid_y // 2),
            'upper_right': (mid_x + mid_x // 2, mid_y // 2),
            'lower_left': (mid_x // 2, mid_y + mid_y // 2),
            'lower_right': (mid_x + mid_x // 2, mid_y + mid_y // 2)
        }
        
        # Info label
        self.info_label = tk.Label(
            self.root,
            text="",
            font=("Arial", 16),
            bg='black',
            fg='white',
            wraplength=900,
            justify=tk.CENTER
        )
        self.info_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        # Progress label
        self.progress_label = tk.Label(
            self.root,
            text="",
            font=("Arial", 12),
            bg='black',
            fg='gray'
        )
        self.progress_label.place(x=10, y=10)
        
        # Feedback box for visual confirmation
        self.feedback_box = tk.Label(
            self.root,
            text="",
            font=("Arial", 16, "bold"),
            bg='black',
            fg='yellow'
        )
        self.feedback_box.place(relx=0.5, rely=0.85, anchor=tk.CENTER)
        
        # Debug label to show last key pressed
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
        self.debug_label.config(text=f"Key pressed: {event.keysym} (char: {event.char})")
        print(f"Key event: keysym={event.keysym}, char={event.char}, keycode={event.keycode}")
        
    def show_welcome(self):
        """Display initial welcome screen"""
        welcome_text = """
DIGIT VIGILANCE TASK

CRITICAL SIGNALS: Two-digit numbers where difference = 0 or ±1
Examples: 45, 67, 88, 32, 54 ✓

NON-SIGNALS: Difference > 1
Examples: 28, 73, 15 ✗

═══════════════════════════════════════════════

INSTRUCTIONS:
1. Click anywhere on this BLACK screen
2. Press the SPACEBAR
3. You should see a message appear below

Try it now!

═══════════════════════════════════════════════
        """
        self.info_label.config(text=welcome_text)
        self.feedback_box.config(text="👆 CLICK SCREEN, then press SPACEBAR 👆", fg='yellow')
        
        self.space_press_count = 0
        self.welcome_mode = True
        
    def response_made(self, event):
        """Handle spacebar press"""
        print(f"SPACEBAR DETECTED! welcome_mode={self.welcome_mode}")
        
        if self.welcome_mode:
            self.space_press_count += 1
            self.feedback_box.config(
                text=f"✓✓✓ SPACEBAR WORKS! (press #{self.space_press_count}) ✓✓✓",
                fg='green'
            )
            print(f"Spacebar press count: {self.space_press_count}")
            
            if self.space_press_count >= 1:
                # Continue after a moment
                self.root.after(1000, self.select_difficulty)
                self.welcome_mode = False
                
        elif hasattr(self, 'difficulty_mode') and self.difficulty_mode:
            # Ignore spacebar during difficulty selection
            pass
            
        elif hasattr(self, 'instructions_mode') and self.instructions_mode:
            self.feedback_box.config(text="✓ Starting task...", fg='green')
            self.instructions_mode = False
            self.root.after(500, self.start_task)
            
        elif self.stimulus_onset_time is not None and not self.responded:
            # During task - record response
            rt = (time.time() - self.stimulus_onset_time) * 1000
            self.responded = True
            
            if self.is_signal:
                self.hits += 1
                outcome = 'hit'
                self.feedback_box.config(text=f"✓ HIT - {int(rt)}ms", fg='green')
            else:
                self.false_alarms += 1
                outcome = 'false_alarm'
                self.feedback_box.config(text=f"✗ FALSE ALARM", fg='red')
            
            self.root.after(300, lambda: self.feedback_box.config(text=""))
            self.record_trial_data(rt, outcome)
        
    def select_difficulty(self):
        """Select difficulty"""
        self.difficulty_mode = True
        
        select_text = """
SELECT DIFFICULTY CONDITION

Press '1' for HIGH DIFFICULTY (faster pace)
Press '2' for LOW DIFFICULTY (slower pace)

Click screen, then press 1 or 2
        """
        self.info_label.config(text=select_text)
        self.feedback_box.config(text="Press 1 or 2", fg='yellow')
        
        # Bind number keys
        self.root.bind('1', lambda e: self.set_difficulty('high'))
        self.root.bind('2', lambda e: self.set_difficulty('low'))
        self.canvas.bind('1', lambda e: self.set_difficulty('high'))
        self.canvas.bind('2', lambda e: self.set_difficulty('low'))
        
    def set_difficulty(self, difficulty):
        """Set difficulty"""
        self.difficulty = difficulty
        self.difficulty_mode = False
        self.feedback_box.config(text=f"✓ {difficulty.upper()} selected", fg='green')
        
        # Unbind number keys
        self.root.unbind('1')
        self.root.unbind('2')
        self.canvas.unbind('1')
        self.canvas.unbind('2')
        
        self.root.after(1000, self.show_instructions)
        
    def show_instructions(self):
        """Show final instructions"""
        self.instructions_mode = True
        
        pace = "faster" if self.difficulty == 'high' else "slower"
        
        instructions = f"""
DIFFICULTY: {self.difficulty.upper()} ({pace} pace)

The task will last 24 minutes.

REMEMBER:
• Press SPACEBAR only for critical signals (diff = 0 or ±1)
• Respond as quickly as possible
• Stay focused throughout
• Numbers appear in different screen locations

Click screen, then press SPACEBAR to begin
        """
        self.info_label.config(text=instructions)
        self.feedback_box.config(text="Press SPACEBAR to start", fg='yellow')
        
    def start_task(self):
        """Start the task"""
        self.info_label.place_forget()
        self.feedback_box.config(text="")
        
        # Generate trial sequence
        self.generate_trial_sequence()
        
        # Start task
        self.block_start_time = time.time()
        self.current_trial = 0
        
        self.present_stimulus()
        
    def generate_trial_sequence(self):
        """Generate trial sequence"""
        blank_duration = (self.blank_duration_high if self.difficulty == 'high' 
                         else self.blank_duration_low)
        
        trial_duration = self.stimulus_duration + blank_duration
        total_trials = self.block_duration // trial_duration
        
        self.trial_sequence = []
        trials_per_period = total_trials // self.num_periods
        
        for period in range(self.num_periods):
            signal_positions = random.sample(range(trials_per_period), self.signals_per_period)
            
            for trial in range(trials_per_period):
                is_signal = trial in signal_positions
                stimulus = self.generate_critical_signal() if is_signal else self.generate_non_signal()
                quadrant = self.quadrants[trial % 4]
                
                self.trial_sequence.append({
                    'stimulus': stimulus,
                    'is_signal': is_signal,
                    'quadrant': quadrant,
                    'period': period + 1
                })
        
        random.shuffle(self.trial_sequence)
        
    def generate_critical_signal(self):
        """Generate critical signal"""
        first_digit = random.randint(0, 9)
        valid_diffs = [0, 1, -1]
        possible_seconds = []
        
        for diff in valid_diffs:
            second = first_digit - diff
            if 0 <= second <= 9:
                possible_seconds.append(second)
        
        second_digit = random.choice(possible_seconds)
        return f"{first_digit}{second_digit}"
    
    def generate_non_signal(self):
        """Generate non-signal"""
        while True:
            first_digit = random.randint(0, 9)
            second_digit = random.randint(0, 9)
            diff = abs(first_digit - second_digit)
            
            if diff > 1:
                return f"{first_digit}{second_digit}"
    
    def present_stimulus(self):
        """Display stimulus"""
        elapsed_time = (time.time() - self.block_start_time) * 1000
        
        if self.current_trial >= len(self.trial_sequence) or elapsed_time >= self.block_duration:
            self.end_task()
            return
        
        trial_info = self.trial_sequence[self.current_trial]
        self.current_stimulus = trial_info['stimulus']
        self.is_signal = trial_info['is_signal']
        self.responded = False
        
        x, y = self.quadrant_positions[trial_info['quadrant']]
        x += random.randint(-50, 50)
        y += random.randint(-50, 50)
        
        self.canvas.delete("all")
        
        self.canvas.create_text(
            x, y,
            text=self.current_stimulus,
            font=("Arial", 72, "bold"),
            fill='white',
            tags="stimulus"
        )
        
        period = trial_info['period']
        self.progress_label.config(
            text=f"Period {period}/4 | Trial {self.current_trial + 1}/{len(self.trial_sequence)}"
        )
        
        self.stimulus_onset_time = time.time()
        
        self.root.after(self.stimulus_duration, self.blank_screen)
    
    def blank_screen(self):
        """Show blank screen"""
        self.canvas.delete("all")
        
        if not self.responded:
            if self.is_signal:
                self.misses += 1
                outcome = 'miss'
            else:
                self.correct_rejections += 1
                outcome = 'correct_rejection'
            
            self.record_trial_data(None, outcome)
        
        blank_duration = (self.blank_duration_high if self.difficulty == 'high' 
                         else self.blank_duration_low)
        
        self.current_trial += 1
        self.root.after(blank_duration, self.present_stimulus)
    
    def record_trial_data(self, rt, outcome):
        """Record trial data"""
        trial_info = self.trial_sequence[self.current_trial]
        elapsed_time = (time.time() - self.block_start_time) * 1000
        
        trial_data = {
            'trial_number': self.current_trial + 1,
            'period': trial_info['period'],
            'time_on_watch_ms': round(elapsed_time, 2),
            'stimulus': self.current_stimulus,
            'is_signal': self.is_signal,
            'quadrant': trial_info['quadrant'],
            'response_made': rt is not None,
            'reaction_time_ms': round(rt, 2) if rt else None,
            'outcome': outcome,
            'difficulty': self.difficulty
        }
        
        self.trial_data.append(trial_data)
    
    def end_task(self):
        """Complete task"""
        self.canvas.delete("all")
        self.progress_label.config(text="")
        self.feedback_box.config(text="")
        self.debug_label.config(text="")
        
        self.calculate_performance()
        self.save_data()
        self.show_results()
    
    def calculate_performance(self):
        """Calculate performance metrics"""
        total_signals = self.hits + self.misses
        total_nonsignals = self.false_alarms + self.correct_rejections
        
        self.hit_rate = self.hits / total_signals if total_signals > 0 else 0
        self.fa_rate = self.false_alarms / total_nonsignals if total_nonsignals > 0 else 0
        
        # Calculate d' and c
        hr = max(0.01, min(0.99, self.hit_rate))
        far = max(0.01, min(0.99, self.fa_rate))
        
        z_hr = self.z_score_approx(hr)
        z_far = self.z_score_approx(far)
        
        self.d_prime = z_hr - z_far
        self.criterion = -0.5 * (z_hr + z_far)
        
        # Period performance
        self.period_performance = []
        for period in range(1, self.num_periods + 1):
            period_trials = [t for t in self.trial_data if t['period'] == period]
            period_hits = sum(1 for t in period_trials if t['outcome'] == 'hit')
            period_signals = sum(1 for t in period_trials if t['is_signal'])
            
            period_hr = period_hits / period_signals if period_signals > 0 else 0
            
            self.period_performance.append({
                'period': period,
                'hit_rate': period_hr
            })
    
    def z_score_approx(self, p):
        """Approximate z-score"""
        if p <= 0.5:
            t = (-2 * (p * (1 - p) + 0.5 * (1 - p))) ** 0.5
            return -t * (2.515517 + t * (0.802853 + t * 0.010328)) / \
                   (1 + t * (1.432788 + t * (0.189269 + t * 0.001308)))
        else:
            t = (-2 * ((1 - p) * p + 0.5 * p)) ** 0.5
            return t * (2.515517 + t * (0.802853 + t * 0.010328)) / \
                   (1 + t * (1.432788 + t * (0.189269 + t * 0.001308)))
    
    def save_data(self):
        """Save data to JSON"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"digit_vigilance_{self.difficulty}_{timestamp}.json"
        
        hit_rts = [t['reaction_time_ms'] for t in self.trial_data if t['outcome'] == 'hit']
        mean_rt = sum(hit_rts) / len(hit_rts) if hit_rts else None
        
        output_data = {
            'metadata': {
                'timestamp': timestamp,
                'difficulty': self.difficulty,
                'stimulus_duration_ms': self.stimulus_duration,
                'blank_duration_ms': (self.blank_duration_high if self.difficulty == 'high' 
                                     else self.blank_duration_low),
                'block_duration_minutes': 24,
                'total_signals': self.total_signals
            },
            'performance': {
                'hits': self.hits,
                'misses': self.misses,
                'false_alarms': self.false_alarms,
                'correct_rejections': self.correct_rejections,
                'hit_rate': round(self.hit_rate, 3),
                'false_alarm_rate': round(self.fa_rate, 3),
                'd_prime': round(self.d_prime, 3),
                'criterion': round(self.criterion, 3),
                'mean_rt_hits_ms': round(mean_rt, 2) if mean_rt else None
            },
            'period_performance': self.period_performance,
            'trial_data': self.trial_data
        }
        
        with open(filename, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"\nData saved to: {filename}")
        self.output_filename = filename
    
    def show_results(self):
        """Display results"""
        results_text = f"""
TASK COMPLETE

Performance Summary:
  Hits: {self.hits}/{self.total_signals} ({self.hit_rate:.1%})
  False Alarms: {self.false_alarms} ({self.fa_rate:.1%})
  d': {self.d_prime:.2f}
  Criterion: {self.criterion:.2f}

Data saved to: {self.output_filename}

Press ESC to exit
        """
        
        self.info_label.config(text=results_text)
        self.info_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
    
    def emergency_exit(self):
        """Exit with data save"""
        if self.trial_data:
            self.calculate_performance()
            self.save_data()
        self.root.quit()

def main():
    root = tk.Tk()
    app = DigitVigilanceTask(root)
    root.mainloop()

if __name__ == "__main__":
    main()
