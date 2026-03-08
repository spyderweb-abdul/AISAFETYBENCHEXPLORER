"""
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025-2026 AISafetyBenchExplorer Contributors

"""


import requests
import pandas as pd
from datetime import datetime, timedelta
import time
from dotenv import load_dotenv
import os

# Load your benchmark data
df = pd.read_excel("Copy-of-AISafetyBenchExplorer.xlsx", sheet_name='Safety Evaluation Benchmarks')
load_dotenv()

# GitHub API token (replace with your actual token)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Headers for GitHub API
headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def parse_github_url(url):
    """Extract owner and repo name from GitHub URL"""
    if not url or pd.isna(url):
        return None, None
    url = str(url).strip()
    if not url.startswith("https://github.com/"):
        return None, None
    
    # Remove trailing slashes and .git
    url = url.rstrip('/').replace('.git', '')
    parts = url.split("/")
    
    if len(parts) >= 5:
        return parts[3], parts[4]
    return None, None

def get_github_stars(owner, repo):
    """Get number of stars for a GitHub repository"""
    try:
        url = f"https://api.github.com/repos/{owner}/{repo}"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return data.get("stargazers_count", 0)
        elif response.status_code == 404:
            print(f"Repository not found: {owner}/{repo}")
            return 0
        elif response.status_code == 403:
            print(f"Rate limit exceeded. Waiting 60 seconds...")
            time.sleep(60)
            return get_github_stars(owner, repo)  # Retry
        else:
            print(f"Error {response.status_code} for {owner}/{repo}")
            return 0
    except Exception as e:
        print(f"Exception getting stars for {owner}/{repo}: {str(e)}")
        return 0

def get_last_commit_date(owner, repo):
    """Get the date of the last commit for a GitHub repository"""
    try:
        url = f"https://api.github.com/repos/{owner}/{repo}/commits"
        response = requests.get(url, headers=headers, params={"per_page": 1}, timeout=10)
        
        if response.status_code == 200:
            commits = response.json()
            
            # Check if commits is a list and has at least one element
            if isinstance(commits, list) and len(commits) > 0:
                commit_data = commits[0]
                if isinstance(commit_data, dict):
                    date = commit_data.get("commit", {}).get("author", {}).get("date")
                    return date
            return None
            
        elif response.status_code == 409:
            # Repository is empty (no commits)
            print(f"Empty repository: {owner}/{repo}")
            return None
        elif response.status_code == 404:
            print(f"Repository not found: {owner}/{repo}")
            return None
        elif response.status_code == 403:
            print(f"Rate limit exceeded. Waiting 60 seconds...")
            time.sleep(60)
            return get_last_commit_date(owner, repo)  # Retry
        else:
            print(f"Error {response.status_code} for {owner}/{repo}")
            return None
            
    except Exception as e:
        print(f"Exception getting last commit for {owner}/{repo}: {str(e)}")
        return None

def get_activity_status(last_commit_date):
    """Determine if repo is Active or Stale"""
    if not last_commit_date:
        return "Unknown"
    
    try:
        commit_date = datetime.strptime(last_commit_date, "%Y-%m-%dT%H:%M:%SZ")
        days_since = (datetime.now() - commit_date).days
        
        if days_since < 0:
            return "Unknown"  # Future date (shouldn't happen)
        elif days_since < 180:
            return "Active"
        else:
            return "Stale"
    except Exception as e:
        print(f"Error parsing date {last_commit_date}: {str(e)}")
        return "Unknown"

def format_days_since_commit(last_commit_date):
    """Calculate days since last commit"""
    if not last_commit_date:
        return None
    
    try:
        commit_date = datetime.strptime(last_commit_date, "%Y-%m-%dT%H:%M:%SZ")
        days_since = (datetime.now() - commit_date).days
        return max(0, days_since)  # Ensure non-negative
    except:
        return None

# Process each repository
print(f"Processing {len(df)} benchmarks...")
print("="*80)

results = []
for idx, row in df.iterrows():
    repo_url = row.get('Code repository')
    benchmark_name = row.get('Benchmark Name', f'Benchmark_{idx}')
    
    print(f"\n[{idx+1}/{len(df)}] {benchmark_name}")
    print(f"  URL: {repo_url}")
    
    owner, repo = parse_github_url(repo_url)
    
    if owner and repo:
        print(f"  Repository: {owner}/{repo}")
        
        # Get GitHub data
        stars = get_github_stars(owner, repo)
        last_commit = get_last_commit_date(owner, repo)
        activity = get_activity_status(last_commit)
        days_since = format_days_since_commit(last_commit)
        last_commit_date = last_commit.split("T")[0] if last_commit else None
        
        print(f"Stars: {stars}")
        print(f"Last Commit: {last_commit_date if last_commit_date else 'N/A'}")
        print(f"Activity: {activity}")
        if days_since is not None:
            print(f"Days Since Commit: {days_since}")
    else:
        print(f"Invalid or missing GitHub URL")
        stars = 0
        last_commit_date = None
        activity = "Unknown"
        days_since = None
    
    results.append({
        'Benchmark Name': benchmark_name,
        'GitHub Stars': stars,
        'Last Commit Date': last_commit_date,
        'Days Since Last Commit': days_since,
        'Activity Status': activity
    })
    
    # Rate limiting: wait 1 second between requests
    time.sleep(1)

print("\n" + "="*80)
print("GitHub data extraction completed!")
print("="*80)

# Create DataFrame with results
results_df = pd.DataFrame(results)

# Merge with original data
final_df = df.merge(results_df, on='Benchmark Name', how='left')

# Reorder columns to put new data after existing columns
new_columns = [col for col in final_df.columns if col not in results_df.columns or col == 'Benchmark Name']
new_columns.extend(['GitHub Stars', 'Last Commit Date', 'Days Since Last Commit', 'Activity Status'])
final_df = final_df[new_columns]

# Save to new Excel file
output_file = "AI_Safety_Benchmarks_With_GitHub_Data.xlsx"

with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
    # Main data sheet
    final_df.to_excel(writer, sheet_name='Benchmarks with GitHub Data', index=False)
    
    # Summary statistics sheet
    total_benchmarks = len(final_df)
    with_github = len(final_df[final_df['GitHub Stars'] > 0])
    active_repos = len(final_df[final_df['Activity Status'] == 'Active'])
    stale_repos = len(final_df[final_df['Activity Status'] == 'Stale'])
    unknown_status = len(final_df[final_df['Activity Status'] == 'Unknown'])
    
    # Stars distribution
    avg_stars = final_df[final_df['GitHub Stars'] > 0]['GitHub Stars'].mean()
    max_stars = final_df['GitHub Stars'].max()
    
    summary_data = [
        ['Metric', 'Count', 'Percentage'],
        ['Total Benchmarks', total_benchmarks, '100%'],
        ['Benchmarks with GitHub Data', with_github, f'{(with_github/total_benchmarks*100):.1f}%'],
        ['Active Repositories (<180 days)', active_repos, f'{(active_repos/total_benchmarks*100):.1f}%'],
        ['Stale Repositories (>180 days)', stale_repos, f'{(stale_repos/total_benchmarks*100):.1f}%'],
        ['Unknown Status', unknown_status, f'{(unknown_status/total_benchmarks*100):.1f}%'],
        ['', '', ''],
        ['Stars Statistics', '', ''],
        ['Average Stars (repos with data)', f'{avg_stars:.0f}' if pd.notna(avg_stars) else '0', ''],
        ['Maximum Stars', max_stars, ''],
    ]
    
    summary_df = pd.DataFrame(summary_data[1:], columns=summary_data[0])
    summary_df.to_excel(writer, sheet_name='Summary', index=False)
    
    # Top starred repositories
    top_starred = final_df.nlargest(20, 'GitHub Stars')[['Benchmark Name', 'GitHub Stars', 'Activity Status', 'Last Commit Date']]
    top_starred.to_excel(writer, sheet_name='Top Starred', index=False)

print(f"\nResults saved to: {output_file}")
print(f"\nSummary:")
print(f"   Total Benchmarks: {total_benchmarks}")
print(f"   With GitHub Data: {with_github} ({(with_github/total_benchmarks*100):.1f}%)")
print(f"   Active Repos: {active_repos} ({(active_repos/total_benchmarks*100):.1f}%)")
print(f"   Stale Repos: {stale_repos} ({(stale_repos/total_benchmarks*100):.1f}%)")
print(f"   Unknown Status: {unknown_status} ({(unknown_status/total_benchmarks*100):.1f}%)")
