# QUICK START GUIDE
## Vigilance Task Suite - Ready to Use!

## ⚡ Super Quick Start

1. **Download the files** (see below)
2. **Open in Spyder** or run from terminal
3. **Click the black screen**
4. **Press SPACEBAR**
5. Follow on-screen instructions

That's it! 🎉

## 📥 Files You Need

### Essential Files (Download These)
- ✅ **digit_vigilance_WORKING.py** - Digit task (24 min)
- ✅ **pvt_task_WORKING.py** - PVT task (10 min)
- ✅ **analyze_data.py** - Analyze results
- ✅ **README_COMPLETE.md** - Full documentation

**IMPORTANT**: Use only the **_WORKING.py** versions! These have the keyboard fixes.

## 🎮 Running the Tasks

### Method 1: Spyder (Easiest)
```
1. Open Spyder
2. File → Open → Select digit_vigilance_WORKING.py
3. Press F5
4. CLICK the black screen
5. Press SPACEBAR
6. You should see: "✓ SPACEBAR WORKS!"
```

### Method 2: Terminal/Command Prompt
```bash
# Navigate to your tasks folder
cd /path/to/tasks

# Run the task
python digit_vigilance_WORKING.py

# Or on Mac/Linux
python3 digit_vigilance_WORKING.py
```

## 📋 What Each Task Does

### Digit Vigilance Task (24 minutes)

**Your Job**: Press SPACEBAR for critical signals only

**Critical Signals** (press spacebar):
- 45 → difference is -1 ✓
- 67 → difference is -1 ✓
- 88 → difference is 0 ✓
- 32 → difference is +1 ✓
- 54 → difference is +1 ✓

**Non-Signals** (don't press):
- 28 → difference is -6 ✗
- 73 → difference is +4 ✗
- 15 → difference is -4 ✗

**Difficulty Levels**:
- Press **1** for HIGH (faster pace)
- Press **2** for LOW (slower pace)

### PVT Task (10 minutes)

**Your Job**: Press SPACEBAR when the counter appears

**Simple!**
1. Wait for counter to appear
2. Press spacebar as fast as possible
3. See your reaction time
4. Repeat for 10 minutes

**Don't** press before the counter appears (that's "anticipatory")

## 🎯 Step-by-Step First Run

### For Digit Vigilance Task

1. **Run the file**
   - In Spyder: Press F5
   - Terminal: `python digit_vigilance_WORKING.py`

2. **Black screen appears** with instructions

3. **IMPORTANT: Click anywhere on the screen**

4. **Press SPACEBAR**
   - You should see: "✓ SPACEBAR WORKS!"

5. **Choose difficulty**
   - Press **1** for HIGH difficulty
   - Press **2** for LOW difficulty

6. **Read final instructions**

7. **Press SPACEBAR to start**

8. **During task**:
   - Numbers appear on screen
   - Press SPACEBAR only for critical signals
   - You'll see feedback: "✓ HIT" or "✗ FALSE ALARM"

9. **After 24 minutes**:
   - Task ends automatically
   - Results displayed
   - Data saved to JSON file

10. **Exit**:
    - Press **ESC** key

### For PVT Task

1. **Run the file**

2. **Click the screen, press SPACEBAR**

3. **Task starts**:
   - Wait... (1-10 seconds)
   - Counter appears: 0, 1, 2, 3...
   - Press SPACEBAR immediately!
   - See your reaction time

4. **Repeat for 10 minutes**

5. **Task ends**, see results

## 💾 Where Is My Data?

Data saves in the **same folder** as the Python scripts.

**File names**:
- `digit_vigilance_high_20240210_143022.json`
- `digit_vigilance_low_20240210_150133.json`
- `pvt_data_20240210_152045.json`

Format: `taskname_difficulty_YYYYMMDD_HHMMSS.json`

## 📊 Analyzing Data

### Quick Analysis
```bash
python analyze_data.py
```

This shows:
- Hit rates and false alarms
- Reaction times
- Vigilance decrement
- Performance by period

### In Python
```python
import json

# Load your data
with open('digit_vigilance_high_20240210_143022.json') as f:
    data = json.load(f)

# Check performance
print(f"Hit Rate: {data['performance']['hit_rate']:.1%}")
print(f"d-prime: {data['performance']['d_prime']:.2f}")
```

## 🔑 Important Keys

During tasks:
- **SPACEBAR** - Respond to signals/counter
- **ESC** - Exit and save data
- **1** or **2** - Select difficulty (digit task only)

## ⚠️ Common Issues & Fixes

### "Spacebar doesn't work"
✅ **FIX**: Click on the black screen first!
- These _WORKING versions should work
- You should see "✓ SPACEBAR WORKS!" message

### "Task freezes/hangs"
✅ **FIX**: You're using the old version
- Use **digit_vigilance_WORKING.py** and **pvt_task_WORKING.py**
- Old versions had a bug (now fixed)

### "Can't see the window"
✅ **FIX**: Window might be behind Spyder
- Press Alt+Tab (Windows) or Cmd+Tab (Mac)
- Look for "Digit Vigilance Task" or "PVT"

### "Numbers are hard to see"
✅ **FIX**: Normal! This tests sustained attention
- Make sure room is not too bright
- Give eyes time to adjust to black screen

## 🧪 Test Before Using

Run this quick test to make sure everything works:

```python
import tkinter as tk

root = tk.Tk()
root.geometry("400x200")
root.configure(bg='black')

label = tk.Label(root, text="Click here, press SPACEBAR",
                font=("Arial", 16), bg='black', fg='white')
label.pack(expand=True)

def space_test(event):
    label.config(text="✓ IT WORKS!", fg='green')
    print("Spacebar working!")

root.bind('<space>', space_test)
root.mainloop()
```

If you see "✓ IT WORKS!", you're ready!

## 📈 What Gets Measured?

### Digit Vigilance Task
- **Hit Rate**: % of signals you caught
- **False Alarms**: Times you pressed for non-signals
- **d-prime**: How well you discriminate (higher = better)
- **Criterion**: Response bias (negative = liberal, positive = conservative)
- **Vigilance Decrement**: Performance drop over time

### PVT
- **Mean RT**: Average reaction time
- **Lapses**: Slow responses (>500ms)
- **Anticipatory**: Pressing too early
- **Consistency**: RT variability

## 🎯 Performance Targets

### Good Performance (Digit Vigilance)
- Hit Rate: > 80%
- False Alarms: < 10%
- d-prime: > 2.0

### Good Performance (PVT)
- Mean RT: 200-300 ms
- Lapses: < 10%
- Few anticipatory responses

## 🔬 Research Tips

### For Best Results
1. **Quiet environment** - minimize distractions
2. **Consistent time** - test at same time of day
3. **Control caffeine** - if studying alertness
4. **Clear instructions** - practice if needed
5. **Counterbalance** - alternate difficulty order

### Suggested Protocol
```
Session 1:
├─ PVT (10 min) - baseline
├─ Break (5 min)
├─ Digit - Low Difficulty (24 min)
├─ Break (10 min)
└─ Digit - High Difficulty (24 min)

Session 2 (counterbalanced):
├─ PVT (10 min)
├─ Break (5 min)
├─ Digit - High Difficulty (24 min)
├─ Break (10 min)
└─ Digit - Low Difficulty (24 min)
```

## 💡 Pro Tips

1. **Click before pressing spacebar** - ensures keyboard focus
2. **Read instructions carefully** - understand critical signals
3. **Use ESC to exit** - saves your data
4. **Check data files** - make sure they're created
5. **Test run first** - practice before real data collection

## 📱 Emergency Contacts

**Task won't start?**
- Check Python version: `python --version` (need 3.7+)
- Test tkinter: `python -c "import tkinter; print('OK')"`

**Spacebar issues?**
- Use the _WORKING.py versions
- Click screen first
- See "✓ SPACEBAR WORKS!" message

**Data not saving?**
- Check folder permissions
- Look in same folder as .py files
- ESC key forces save

## ✅ Pre-Flight Checklist

Before data collection:
- [ ] Downloaded _WORKING.py files
- [ ] Tested spacebar works
- [ ] Understand critical signals (digit task)
- [ ] Know difference levels (high/low)
- [ ] Data saves correctly
- [ ] Know how to exit (ESC)
- [ ] Environment is quiet
- [ ] Participant understands instructions

## 🎓 Understanding Your Results

### Digit Vigilance
```
Hit Rate = Hits / (Hits + Misses)
FA Rate = False Alarms / (False Alarms + Correct Rejections)
d' = Z(Hit Rate) - Z(FA Rate)
```

**Interpretation**:
- d' > 2.5 = Excellent discrimination
- d' = 1.5-2.5 = Good discrimination
- d' < 1.5 = Poor discrimination

### PVT
```
Lapse % = (Lapses / Total Trials) × 100
```

**Interpretation**:
- < 10% lapses = Alert
- 10-20% lapses = Moderate fatigue
- > 20% lapses = Significant impairment

## 📚 Learn More

For complete details, see:
- **README_COMPLETE.md** - Full documentation
- **analyze_data.py** - Example analysis code

## 🚀 Ready to Go!

You have everything you need:
1. ✅ Working task files
2. ✅ Clear instructions
3. ✅ Analysis tools
4. ✅ Complete documentation

Just run the tasks and start collecting data!

---

**Need help?** Check README_COMPLETE.md for detailed troubleshooting.

**Last Updated**: February 2024  
**Status**: Tested and Working ✓
