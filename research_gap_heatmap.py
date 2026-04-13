"""
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025-2026 AISafetyBenchExplorer Contributors
"""


import pandas as pd
import numpy as np
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# Load data
excel_file = "Copy-of-AISafetyBenchExplorer.xlsx"
df = pd.read_excel(excel_file, sheet_name='Safety Evaluation Benchmarks')

# Define safety dimensions with keywords
safety_dimensions = {
    'Toxicity': ['toxicity', 'toxic', 'offensive', 'abusive', 'hate speech', 'abuse'],
    'Jailbreak & Adversarial': ['jailbreak', 'adversarial', 'adversarial method', 'attack', 'red teaming', 'red team', 'fuzzing'],
    'Privacy & Security': ['privacy', 'memorization', 'association', 'cybersecurity', 'vulnerability', 'backdoor'],
    'Bias & Fairness': ['bias', 'fairness', 'stereotype', 'sociodemographics', 'gender', 'discrimination'],
    'Factuality & Truthfulness': ['factuality', 'truthfulness', 'hallucination', 'lie detection', 'consistency', 'factual'],
    'Alignment & Values': ['alignment', 'value alignment', 'norm alignment', 'moral', 'ethics', 'cultural'],
    'Harmfulness Evaluation': ['harmfulness', 'harmful', 'harm', 'helpfulness', 'helplessness'],
    'Agent & Tool Safety': ['agent', 'agents safety', 'tool', 'tooluse', 'refusal', 'instruction-following'],
    'Grounding & RAG': ['grounding', 'rag', 'retrieval-augmented', 'faithfulness'],
    'Content Moderation': ['content moderation', 'moderation', 'moderation'],
}

def categorize_benchmark(task_type):
    """Map benchmark to one or more safety dimensions"""
    if not task_type or pd.isna(task_type):
        return []
    
    task_type_lower = str(task_type).lower()
    dimensions = []
    
    for dimension, keywords in safety_dimensions.items():
        for keyword in keywords:
            if keyword in task_type_lower:
                dimensions.append(dimension)
                break
    
    return dimensions if dimensions else ['General Safety']

# Categorize all benchmarks
df['Safety Dimensions'] = df['Task Type'].apply(categorize_benchmark)

# Create heatmap data
heatmap_data = {}
for dimension in safety_dimensions.keys():
    heatmap_data[dimension] = {
        'Popular': 0,
        'High': 0,
        'Medium': 0,
        'Low': 0,
        'Total': 0
    }

# Add 'General Safety' dimension
heatmap_data['General Safety'] = {
    'Popular': 0,
    'High': 0,
    'Medium': 0,
    'Low': 0,
    'Total': 0
}

# Count benchmarks by dimension and complexity
for idx, row in df.iterrows():
    complexity = row['Complexity level']
    dimensions = row['Safety Dimensions']
    
    for dimension in dimensions:
        if dimension in heatmap_data:
            heatmap_data[dimension][complexity] += 1
            heatmap_data[dimension]['Total'] += 1

# Calculate gap severity
def calculate_gap_severity(data):
    """Determine gap severity based on distribution"""
    total = data['Total']
    if total == 0:
        return '⚪ Not Covered'
    
    popular = data['Popular']
    high = data['High']
    
    # Severity rules
    if popular == 0 and high == 0:
        return 'Critical Gap'
    elif popular == 0 and high < 2:
        return 'Under-benchmarked'
    elif (popular + high) / total < 0.3:
        return 'Under-benchmarked'
    elif high == 0 and popular > 0:
        return 'Limited Advanced'
    else:
        return 'Well-covered'

# Add gap severity
for dimension in heatmap_data:
    heatmap_data[dimension]['Gap Severity'] = calculate_gap_severity(heatmap_data[dimension])

print("="*100)
print("RESEARCH GAP HEATMAP DATA")
print("="*100)
print(f"\nTotal benchmarks: {len(df)}")
print(f"Total safety dimensions: {len(heatmap_data)}")

# Create summary table
print("\n" + "="*100)
print("SAFETY DIMENSION COVERAGE ANALYSIS")
print("="*100)

heatmap_df = pd.DataFrame(heatmap_data).T
print(heatmap_df.to_string())

# Identify critical gaps
print("\n" + "="*100)
print("GAP SEVERITY ANALYSIS")
print("="*100)

critical_gaps = heatmap_df[heatmap_df['Gap Severity'] == 'Critical Gap']
under_benchmarked = heatmap_df[heatmap_df['Gap Severity'] == 'Under-benchmarked']
well_covered = heatmap_df[heatmap_df['Gap Severity'] == 'Well-covered']

print(f"\n CRITICAL GAPS ({len(critical_gaps)}):")
for dim in critical_gaps.index:
    print(f"   • {dim}: {int(critical_gaps.loc[dim, 'Total'])} benchmarks")

print(f"\n UNDER-BENCHMARKED ({len(under_benchmarked)}):")
for dim in under_benchmarked.index:
    total = int(under_benchmarked.loc[dim, 'Total'])
    high = int(under_benchmarked.loc[dim, 'High'])
    popular = int(under_benchmarked.loc[dim, 'Popular'])
    print(f"   • {dim}: {total} benchmarks (Popular: {popular}, High: {high})")

print(f"\n WELL-COVERED ({len(well_covered)}):")
for dim in well_covered.index:
    total = int(well_covered.loc[dim, 'Total'])
    high = int(well_covered.loc[dim, 'High'])
    popular = int(well_covered.loc[dim, 'Popular'])
    print(f"   • {dim}: {total} benchmarks (Popular: {popular}, High: {high})")