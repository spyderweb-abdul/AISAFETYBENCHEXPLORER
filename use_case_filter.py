"""
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025-2026 AISafetyBenchExplorer Contributors
"""

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation

# Load the data fresh
excel_file = "Copy-of-AISafetyBenchExplorer.xlsx"
df = pd.read_excel(excel_file, sheet_name='Safety Evaluation Benchmarks')

print(f"Loaded {len(df)} benchmarks")
print(f"Columns available: {df.columns.tolist()}")

# Define use-case categories with keywords
use_case_mapping = {
    'Medical AI': [
        'medical', 'healthcare', 'diagnosis', 'clinical', 'patient', 'health', 'disease',
        'drug', 'pharmaceutical', 'treatment', 'therapy', 'doctor', 'hospital'
    ],
    'Financial Services': [
        'financial', 'finance', 'banking', 'investment', 'stock', 'market', 'crypto',
        'trading', 'loan', 'credit', 'mortgage', 'risk', 'fraud', 'compliance', 'regulatory'
    ],
    'Customer Service Chatbots': [
        'conversation', 'dialogue', 'chatbot', 'customer', 'support', 'service', 'assistant',
        'multi-turn', 'interaction', 'chat', 'helpdesk', 'response', 'user interaction', 'dialog'
    ],
    'Content Moderation': [
        'toxicity', 'toxic', 'harmful', 'offensive', 'abuse', 'hate', 'moderation',
        'content filter', 'inappropriate', 'violation', 'explicit', 'jailbreak', 'adversarial', 
        'attack', 'safety', 'safeguard'
    ],
    'Education': [
        'question', 'qa', 'reading comprehension', 'math', 'reasoning',
        'knowledge', 'student', 'learning', 'curriculum', 'exam', 'test', 'education',
        'tutoring', 'explanation', 'teaching'
    ],
    'General Purpose': [
        'general', 'benchmark', 'eval', 'alignment', 'bias', 'fairness', 'stereotype',
        'cultural', 'value', 'norm', 'value alignment', 'instruction following'
    ]
}

def categorize_benchmark(row):
    """Categorize benchmark by use case"""
    task_type = str(row['Task Type']).lower()
    description = str(row['Description']).lower()
    benchmark_name = str(row['Benchmark Name']).lower()
    
    combined_text = f"{task_type} {description} {benchmark_name}"
    
    use_case_scores = {}
    
    for use_case, keywords in use_case_mapping.items():
        score = 0
        for keyword in keywords:
            if keyword in task_type:
                score += 3
            elif keyword in benchmark_name:
                score += 2
            elif keyword in description[:500]:
                score += 1
        if score > 0:
            use_case_scores[use_case] = score
    
    if not use_case_scores:
        return 'General Purpose'
    
    sorted_cases = sorted(use_case_scores.items(), key=lambda x: x[1], reverse=True)
    selected = [case for case, score in sorted_cases[:3]]
    
    return '; '.join(selected)

# Apply categorization
print("\nCategorizing benchmarks...")
df['Recommended For'] = df.apply(categorize_benchmark, axis=1)

# Create filtered view
filtered_data = df[['Benchmark Name', 'Complexity level', 'Task Type', 'Citation Range', 
                    'Dev Purpose', 'Recommended For']].copy()

print(f"Categorized all {len(filtered_data)} benchmarks")

# Count use cases
print("\n" + "="*80)
print("USE-CASE DISTRIBUTION:")
print("="*80)
all_uses = []
for uses in df['Recommended For']:
    all_uses.extend([u.strip() for u in uses.split(';')])

use_counts = pd.Series(all_uses).value_counts()
for use_case, count in use_counts.items():
    pct = (count / len(df)) * 100
    print(f"{use_case:30s} : {count:3d} benchmarks ({pct:5.1f}%)")
    
    
    
# Create a detailed analysis showing strategic examples across use cases
print("="*100)
print("DETAILED USE-CASE CATEGORIZATION ANALYSIS")
print("="*100)

# Show best examples by use case
print("\n EXEMPLAR BENCHMARKS BY USE CASE:\n")

use_case_examples = {
    'Medical AI': [],
    'Financial Services': [],
    'Customer Service Chatbots': [],
    'Content Moderation': [],
    'Education': [],
    'General Purpose': []
}

# Categorize all benchmarks and track examples
for idx, row in filtered_data.iterrows():
    recommended = row['Recommended For']
    for use_case in recommended.split(';'):
        use_case = use_case.strip()
        if use_case in use_case_examples:
            use_case_examples[use_case].append({
                'name': row['Benchmark Name'],
                'task': row['Task Type'],
                'complexity': row['Complexity level'],
                'citations': row['Citation Range']
            })

# Show top 3 examples per use case
for use_case in ['Medical AI', 'Financial Services', 'Customer Service Chatbots', 
                  'Content Moderation', 'Education', 'General Purpose']:
    examples = use_case_examples[use_case][:4]
    print(f"\n {use_case.upper()}")
    print(f"   {len(use_case_examples[use_case])} total benchmarks")
    print(f"   Examples:")
    for ex in examples:
        print(f"   • {ex['name']:40s} | {ex['complexity']:10s} | {ex['citations']:15s}")

# Create a detailed CSV export for reference
detailed_export = filtered_data[['Benchmark Name', 'Task Type', 'Complexity level', 'Citation Range',
                      'Dev Purpose', 'Recommended For']].copy()

detailed_export.to_csv('Benchmarks_UseCase_Detailed.csv', index=False)
print("\n\n" + "="*100)
print("Also created: Benchmarks_UseCase_Detailed.csv")
print("   (Includes code and dataset repository links for easy access)")

# Create a matrix showing complexity vs use-case distribution
print("\n\n" + "="*100)
print("COMPLEXITY DISTRIBUTION BY USE-CASE")
print("="*100)

complexity_levels = ['Popular', 'High', 'Medium', 'Low']

for use_case in ['Medical AI', 'Financial Services', 'Customer Service Chatbots', 
                  'Content Moderation', 'Education', 'General Purpose']:
    filtered_for_use = df[df['Recommended For'].str.contains(use_case, na=False)]
    print(f"\n{use_case}: ({len(filtered_for_use)} benchmarks)")
    for level in complexity_levels:
        count = len(filtered_for_use[filtered_for_use['Complexity level'] == level])
        total = len(filtered_for_use)
        if total > 0:
            pct = (count / total) * 100
            bar_length = int(pct // 5)
            bar = "█" * bar_length
            print(f"  {level:10s}: {count:3d} ({pct:5.1f}%) {bar}")