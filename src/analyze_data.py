"""
Vigilance Task Data Analysis
Analyze and visualize data from both vigilance tasks
"""

import json
import os
from datetime import datetime
import statistics

def analyze_digit_vigilance(filename):
    """Analyze digit vigilance task data"""
    print("\n" + "="*60)
    print("DIGIT VIGILANCE TASK ANALYSIS")
    print("="*60)
    
    with open(filename, 'r') as f:
        data = json.load(f)
    
    # Metadata
    print(f"\nMetadata:")
    print(f"  Timestamp: {data['metadata']['timestamp']}")
    print(f"  Difficulty: {data['metadata']['difficulty'].upper()}")
    print(f"  Stimulus Duration: {data['metadata']['stimulus_duration_ms']}ms")
    print(f"  Blank Duration: {data['metadata']['blank_duration_ms']}ms")
    
    # Overall Performance
    perf = data['performance']
    print(f"\nOverall Performance:")
    print(f"  Hits: {perf['hits']}")
    print(f"  Misses: {perf['misses']}")
    print(f"  False Alarms: {perf['false_alarms']}")
    print(f"  Correct Rejections: {perf['correct_rejections']}")
    print(f"  Hit Rate: {perf['hit_rate']:.1%}")
    print(f"  False Alarm Rate: {perf['false_alarm_rate']:.1%}")
    
    # Signal Detection Metrics
    print(f"\nSignal Detection Theory:")
    print(f"  d' (sensitivity): {perf['d_prime']:.2f}")
    print(f"  c (criterion): {perf['criterion']:.2f}")
    
    if perf['criterion'] < -0.2:
        bias = "Liberal (tends to respond)"
    elif perf['criterion'] > 0.2:
        bias = "Conservative (tends not to respond)"
    else:
        bias = "Neutral"
    print(f"  Response Bias: {bias}")
    
    # Reaction Time
    if perf['mean_rt_hits_ms']:
        print(f"\nReaction Time (Hits):")
        print(f"  Mean RT: {perf['mean_rt_hits_ms']:.0f}ms")
    
    # Period Analysis (Vigilance Decrement)
    print(f"\nPerformance by Period (6-min each):")
    print(f"  {'Period':<10}{'Hit Rate':<15}{'Change':<10}")
    print(f"  {'-'*35}")
    
    periods = data['period_performance']
    previous_hr = None
    
    for period in periods:
        hr = period['hit_rate']
        if previous_hr is not None:
            change = (hr - previous_hr) * 100
            change_str = f"{change:+.1f}%"
        else:
            change_str = "-"
        
        print(f"  {period['period']:<10}{hr:.1%}{'':>5}{change_str:<10}")
        previous_hr = hr
    
    # Calculate vigilance decrement
    if len(periods) >= 2:
        first_period_hr = periods[0]['hit_rate']
        last_period_hr = periods[-1]['hit_rate']
        decrement = (first_period_hr - last_period_hr) * 100
        
        print(f"\n  Vigilance Decrement: {decrement:.1f}%")
        if decrement > 10:
            print(f"  Assessment: Significant decline in performance")
        elif decrement > 5:
            print(f"  Assessment: Moderate decline in performance")
        else:
            print(f"  Assessment: Stable performance maintained")

def analyze_pvt(filename):
    """Analyze PVT task data"""
    print("\n" + "="*60)
    print("PSYCHOMOTOR VIGILANCE TASK (PVT) ANALYSIS")
    print("="*60)
    
    with open(filename, 'r') as f:
        data = json.load(f)
    
    # Metadata
    print(f"\nMetadata:")
    print(f"  Timestamp: {data['metadata']['timestamp']}")
    print(f"  Task Duration: {data['metadata']['task_duration_minutes']} minutes")
    
    # Overall Performance
    perf = data['performance']
    print(f"\nOverall Performance:")
    print(f"  Total Trials: {perf['total_trials']}")
    print(f"  Valid Responses: {perf['valid_responses']}")
    print(f"  Anticipatory Responses: {perf['anticipatory_responses']}")
    
    # Reaction Time Metrics
    print(f"\nReaction Time:")
    print(f"  Mean RT: {perf['mean_rt_ms']:.0f}ms")
    print(f"  Median RT: {perf['median_rt_ms']:.0f}ms")
    print(f"  SD: {perf['std_rt_ms']:.0f}ms")
    print(f"  Range: {perf['min_rt_ms']:.0f}ms - {perf['max_rt_ms']:.0f}ms")
    
    # Performance Classification
    mean_rt = perf['mean_rt_ms']
    if mean_rt < 300:
        classification = "Normal Alert"
    elif mean_rt < 400:
        classification = "Moderate Impairment"
    else:
        classification = "Severe Impairment"
    
    print(f"\n  Performance Level: {classification}")
    
    # Vigilance Metrics
    print(f"\nVigilance Metrics:")
    print(f"  Lapses (RT > 500ms): {perf['lapses']} ({perf['lapse_percentage']:.1f}%)")
    print(f"  Fastest 10% Mean: {perf['fastest_10pct_mean_ms']:.0f}ms")
    print(f"  Slowest 10% Mean: {perf['slowest_10pct_mean_ms']:.0f}ms")
    print(f"  Reciprocal RT: {perf['reciprocal_rt']:.3f}")
    
    # Lapse Assessment
    lapse_pct = perf['lapse_percentage']
    if lapse_pct < 10:
        lapse_assessment = "Good (minimal lapses)"
    elif lapse_pct < 20:
        lapse_assessment = "Moderate (some attention lapses)"
    else:
        lapse_assessment = "Poor (frequent attention lapses)"
    
    print(f"  Lapse Assessment: {lapse_assessment}")
    
    # Time-on-task analysis
    print(f"\nTime-on-Task Analysis:")
    trials = data['trial_data']
    valid_trials = [t for t in trials if t['response_type'] == 'valid']
    
    if len(valid_trials) >= 20:
        # Split into first half and second half
        midpoint = len(valid_trials) // 2
        first_half = valid_trials[:midpoint]
        second_half = valid_trials[midpoint:]
        
        first_half_mean = statistics.mean([t['reaction_time_ms'] for t in first_half])
        second_half_mean = statistics.mean([t['reaction_time_ms'] for t in second_half])
        
        time_effect = second_half_mean - first_half_mean
        
        print(f"  First Half Mean RT: {first_half_mean:.0f}ms")
        print(f"  Second Half Mean RT: {second_half_mean:.0f}ms")
        print(f"  Time-on-Task Effect: {time_effect:+.0f}ms")
        
        if time_effect > 20:
            print(f"  Assessment: Significant slowing over time (fatigue effect)")
        elif time_effect > 10:
            print(f"  Assessment: Moderate slowing over time")
        else:
            print(f"  Assessment: Stable performance maintained")

def list_data_files(directory='/mnt/user-data/outputs'):
    """List all available data files"""
    if not os.path.exists(directory):
        print(f"Output directory not found: {directory}")
        return [], []
    
    files = os.listdir(directory)
    
    digit_files = [f for f in files if f.startswith('digit_vigilance_') and f.endswith('.json')]
    pvt_files = [f for f in files if f.startswith('pvt_data_') and f.endswith('.json')]
    
    return digit_files, pvt_files

def main():
    """Main analysis function"""
    print("\n" + "="*60)
    print("VIGILANCE TASK DATA ANALYSIS")
    print("="*60)
    
    # List available files
    digit_files, pvt_files = list_data_files()
    
    if not digit_files and not pvt_files:
        print("\nNo data files found in /mnt/user-data/outputs/")
        print("Please run the tasks first to generate data.")
        return
    
    print(f"\nFound {len(digit_files)} Digit Vigilance file(s)")
    print(f"Found {len(pvt_files)} PVT file(s)")
    
    # Analyze digit vigilance files
    for filename in digit_files:
        filepath = os.path.join('/mnt/user-data/outputs', filename)
        try:
            analyze_digit_vigilance(filepath)
        except Exception as e:
            print(f"\nError analyzing {filename}: {str(e)}")
    
    # Analyze PVT files
    for filename in pvt_files:
        filepath = os.path.join('/mnt/user-data/outputs', filename)
        try:
            analyze_pvt(filepath)
        except Exception as e:
            print(f"\nError analyzing {filename}: {str(e)}")
    
    print("\n" + "="*60)
    print("Analysis Complete")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
