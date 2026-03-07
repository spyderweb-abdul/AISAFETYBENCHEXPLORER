import requests
import pandas as pd
from huggingface_hub import HfApi
from datetime import datetime
import time
import re

# Load your benchmark data
df = pd.read_excel(
    "Copy-of-AISafetyBenchExplorer.xlsx",
    sheet_name='Safety Evaluation Benchmarks'
)

# Initialize APIs
hf_api = HfApi()

# GitHub API token (replace with your actual token if available)
GITHUB_TOKEN = None  # Set to your token or None

# Headers for GitHub API
github_headers = {
    "Accept": "application/vnd.github.v3+json"
}
if GITHUB_TOKEN:
    github_headers["Authorization"] = f"token {GITHUB_TOKEN}"


# ============================================================================
# MODALITY MAPPING
# ============================================================================

MODALITY_KEYWORDS = {
    'Prompts': ['prompt', 'query', 'instruction'],
    'Conversations': ['conversation', 'dialogue', 'chat', 'multi-turn', 'turn'],
    'Examples': ['example', 'sample'],
    'Binary-choice Questions': ['binary', 'yes-no', 'true-false', 'binary-choice'],
    'Multiple-choice Questions': ['multiple-choice', 'multiple choice', 'mcq', 'multi-choice'],
    'Scenarios': ['scenario', 'situation'],
    'Sentences': ['sentence'],
    'Excerpts': ['excerpt', 'passage'],
    'Posts': ['post', 'social media'],
    'Sentence Pairs': ['sentence pair', 'pair'],
    'Entry tuples': ['tuple', 'entry'],
    'Locations Templates': ['location', 'template'],
    'Stories': ['story', 'narrative'],
    'Comments': ['comment'],
    'Anecdotes': ['anecdote'],
    'Transcripts': ['transcript', 'utterance']
}

# ============================================================================
# LANGUAGE MAPPING
# ============================================================================

LANGUAGE_CODE_MAP = {
    'en': 'English',
    'zh': 'Chinese',
    'zh-cn': 'Chinese',
    'zh-tw': 'Chinese',
    'ko': 'Korean',
    'sv': 'Swedish',
    'hi': 'Hindi',
    'ar': 'Arabic',
    'fr': 'French'
}

TARGET_LANGUAGES = ['English', 'Chinese', 'Korean', 'Swedish', 'Hindi', 'Arabic', 'French']


def map_language(lang_string):
    """Map language codes to full names following template format"""
    if not lang_string or pd.isna(lang_string):
        return None

    # Clean and split
    lang_string = str(lang_string).lower().strip()
    langs = [l.strip() for l in re.split(r'[,;]', lang_string)]

    # Map to full names
    mapped_langs = []
    for lang in langs:
        if lang in LANGUAGE_CODE_MAP:
            full_name = LANGUAGE_CODE_MAP[lang]
            if full_name not in mapped_langs:
                mapped_langs.append(full_name)

    if not mapped_langs:
        return None

    # If single language from target list, return it
    if len(mapped_langs) == 1:
        return mapped_langs[0]

    # If multiple languages, return "Multi-Language"
    return "Multi-Language"


def infer_integration_option(repo_type, tags, description, repo_id):
    """
    Infer integration option (API or Export) based on repository metadata

    API: Dataset can be loaded programmatically via libraries/APIs
    Export: Dataset requires manual download/export
    """
    if not repo_type or repo_type == 'unknown':
        return None

    combined_text = f"{str(tags)} {str(description)} {str(repo_id)}".lower()

    # === HuggingFace datasets ===
    if repo_type == 'huggingface':
        # Check for datasets library support (strong indicator of API access)
        if 'library:datasets' in str(tags):
            return 'API'

        # Check for other Python library support
        if any(lib in str(tags) for lib in ['library:transformers', 'library:evaluate', 'library:autotrain']):
            return 'API'

        # If only file formats mentioned and no library support, it's Export
        has_format = any(fmt in str(tags) for fmt in ['format:csv', 'format:json', 'format:parquet'])
        has_library = 'library:' in str(tags)

        if has_format and not has_library:
            return 'Export'

        # Default for HF datasets: API (most HF datasets can be loaded programmatically)
        return 'API'

    # === GitHub repositories ===
    elif repo_type == 'github':
        # Check for API-related keywords in description/repo name
        api_indicators = [
            'api', 'python package', 'pip install', 'library',
            'import', 'client', 'sdk', 'huggingface', 'datasets'
        ]

        if any(indicator in combined_text for indicator in api_indicators):
            return 'API'

        # Check for export-only indicators
        export_indicators = [
            'download', 'clone', 'csv file', 'json file',
            'manual', 'extract', 'archive'
        ]

        if any(indicator in combined_text for indicator in export_indicators):
            return 'Export'

        # Default for GitHub: Export (most repos require cloning/downloading)
        return 'Export'

    # === Kaggle datasets ===
    elif repo_type == 'kaggle':
        # Kaggle datasets can be accessed via Kaggle API
        if 'kaggle api' in combined_text or 'kaggle datasets' in combined_text:
            return 'API'

        # Default for Kaggle: Export (requires download)
        return 'Export'

    return None


def infer_modalities_from_tags_and_desc(tags, description, benchmark_name, entry_modalties_original):
    """
    Infer entry modalities from HF tags, description, and original entry
    Returns comma-separated modalities
    """
    modalities_found = set()

    # Combine all text sources
    text_sources = []
    if tags:
        text_sources.append(str(tags).lower())
    if description:
        text_sources.append(str(description).lower())
    if benchmark_name:
        text_sources.append(str(benchmark_name).lower())
    if entry_modalties_original and not pd.isna(entry_modalties_original):
        text_sources.append(str(entry_modalties_original).lower())

    combined_text = ' '.join(text_sources)

    # Check for task_categories in tags
    if 'multiple-choice' in combined_text or 'multiple_choice' in combined_text:
        modalities_found.add('Multiple-choice Questions')
    elif 'binary-choice' in combined_text or 'yes-no' in combined_text:
        modalities_found.add('Binary-choice Questions')
    elif 'question-answering' in combined_text or 'qa' in combined_text:
        if 'multiple' not in combined_text:
            modalities_found.add('Prompts')

    # Check for specific modality keywords
    for modality, keywords in MODALITY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in combined_text:
                modalities_found.add(modality)
                break

    # If nothing found but we have original entry modalities, use that
    if not modalities_found and entry_modalties_original and not pd.isna(entry_modalties_original):
        return str(entry_modalties_original)

    # Return comma-separated modalities
    if modalities_found:
        return ', '.join(sorted(modalities_found))

    return None


# ============================================================================
# URL PARSING FUNCTIONS
# ============================================================================

def parse_huggingface_url(url):
    """Extract dataset owner and name from Hugging Face URL"""
    if not url or pd.isna(url):
        return None, None

    url = str(url).strip()

    if 'huggingface.co' not in url:
        return None, None

    try:
        url = url.replace('https://', '').replace('http://', '')
        url = url.rstrip('/')

        parts = url.split('/')

        if 'datasets' in parts:
            idx = parts.index('datasets')
            if len(parts) > idx + 2:
                owner = parts[idx + 1]
                dataset_name = parts[idx + 2]
                return owner, dataset_name
        else:
            if len(parts) >= 2:
                owner = parts[1]
                dataset_name = parts[2] if len(parts) > 2 else None
                return owner, dataset_name
    except Exception as e:
        print(f"      Error parsing HF URL {url}: {str(e)}")
        return None, None

    return None, None


def parse_github_url(url):
    """Extract owner and repo name from GitHub URL"""
    if not url or pd.isna(url):
        return None, None

    url = str(url).strip()
    if not url.startswith("https://github.com/"):
        return None, None

    url = url.rstrip('/').replace('.git', '')
    parts = url.split("/")
    if len(parts) >= 5:
        return parts[3], parts[4]
    return None, None


def parse_kaggle_url(url):
    """Extract dataset info from Kaggle URL"""
    if not url or pd.isna(url):
        return None, None

    url = str(url).strip()
    if 'kaggle.com' not in url:
        return None, None

    try:
        url = url.replace('https://', '').replace('http://', '')
        url = url.rstrip('/')

        parts = url.split('/')

        if 'datasets' in parts:
            idx = parts.index('datasets')
            if len(parts) > idx + 2:
                owner = parts[idx + 1]
                dataset_name = parts[idx + 2]
                return owner, dataset_name
        elif 'code' in parts:
            idx = parts.index('code')
            if len(parts) > idx + 2:
                owner = parts[idx + 1]
                notebook_name = parts[idx + 2]
                return owner, notebook_name
    except Exception as e:
        print(f"      Error parsing Kaggle URL {url}: {str(e)}")
        return None, None

    return None, None


def detect_repo_type(url):
    """Detect repository type from URL"""
    if not url or pd.isna(url):
        return None

    url = str(url).lower()

    if 'huggingface.co' in url:
        return 'huggingface'
    elif 'github.com' in url:
        return 'github'
    elif 'kaggle.com' in url:
        return 'kaggle'
    else:
        return 'unknown'


# ============================================================================
# HUGGING FACE METADATA EXTRACTION
# ============================================================================

def get_hf_dataset_info(repo_id):
    """Get comprehensive dataset metadata from Hugging Face"""
    try:
        dataset_info = hf_api.dataset_info(repo_id=repo_id)

        metadata = {
            'source': 'huggingface',
            'repo_id': repo_id,
            'downloads_30d': dataset_info.downloads if hasattr(dataset_info, 'downloads') else 0,
            'likes': dataset_info.likes if hasattr(dataset_info, 'likes') else 0,
            'last_modified': dataset_info.last_modified if hasattr(dataset_info, 'last_modified') else None,
            'license': extract_hf_license(dataset_info),
            'languages': extract_hf_languages(dataset_info),
            'task_types': extract_hf_task_types(dataset_info),
            'tags': extract_hf_tags(dataset_info),
            'size_category': extract_hf_size(dataset_info),
            'description': getattr(dataset_info, 'description', None),
        }

        return metadata

    except Exception as e:
        print(f"      Error fetching HF data for {repo_id}: {str(e)}")
        return None


def extract_hf_license(dataset_info):
    """Extract license information"""
    try:
        if hasattr(dataset_info, 'card_data') and dataset_info.card_data:
            if hasattr(dataset_info.card_data, 'license'):
                lic = dataset_info.card_data.license
                if isinstance(lic, list):
                    return ', '.join(lic)
                return str(lic) if lic else None
        return None
    except:
        return None


def extract_hf_tags(dataset_info):
    """Extract all tags"""
    try:
        if hasattr(dataset_info, 'tags') and dataset_info.tags:
            if isinstance(dataset_info.tags, list):
                return ', '.join(dataset_info.tags)
            return str(dataset_info.tags)
        return None
    except:
        return None


def extract_hf_task_types(dataset_info):
    """Extract task types from dataset metadata"""
    try:
        if hasattr(dataset_info, 'card_data') and dataset_info.card_data:
            if hasattr(dataset_info.card_data, 'task_categories'):
                tasks = dataset_info.card_data.task_categories
                if tasks and isinstance(tasks, list):
                    return ', '.join(tasks)
            if hasattr(dataset_info.card_data, 'task_ids'):
                tasks = dataset_info.card_data.task_ids
                if tasks and isinstance(tasks, list):
                    return ', '.join(tasks)
        return None
    except:
        return None


def extract_hf_languages(dataset_info):
    """Extract supported languages"""
    try:
        if hasattr(dataset_info, 'card_data') and dataset_info.card_data:
            if hasattr(dataset_info.card_data, 'language'):
                langs = dataset_info.card_data.language
                if langs:
                    if isinstance(langs, list):
                        return ', '.join(langs)
                    return str(langs)
        return None
    except:
        return None


def extract_hf_size(dataset_info):
    """Extract size category"""
    try:
        if hasattr(dataset_info, 'card_data') and dataset_info.card_data:
            if hasattr(dataset_info.card_data, 'size_categories'):
                size_cat = dataset_info.card_data.size_categories
                if size_cat and isinstance(size_cat, list) and len(size_cat) > 0:
                    return size_cat[0]
        return None
    except:
        return None


# ============================================================================
# GITHUB METADATA EXTRACTION
# ============================================================================

def get_github_repo_info(owner, repo):
    """Get GitHub repository metadata"""
    try:
        url = f"https://api.github.com/repos/{owner}/{repo}"
        response = requests.get(url, headers=github_headers, timeout=10)

        if response.status_code == 200:
            data = response.json()

            metadata = {
                'source': 'github',
                'repo_id': f"{owner}/{repo}",
                'stars': data.get("stargazers_count", 0),
                'last_modified': data.get("pushed_at"),
                'license': data.get("license", {}).get("spdx_id") if data.get("license") else None,
                'description': data.get("description"),
                'topics': ', '.join(data.get("topics", [])) if data.get("topics") else None,
            }

            return metadata
        elif response.status_code == 404:
            print(f"      GitHub repo not found: {owner}/{repo}")
            return None
        elif response.status_code == 403:
            print(f"      GitHub rate limit exceeded. Waiting...")
            time.sleep(60)
            return get_github_repo_info(owner, repo)
        else:
            print(f"      GitHub error {response.status_code} for {owner}/{repo}")
            return None

    except Exception as e:
        print(f"      Exception getting GitHub data for {owner}/{repo}: {str(e)}")
        return None


# ============================================================================
# KAGGLE METADATA EXTRACTION (Limited - Kaggle doesn't have public API)
# ============================================================================

def get_kaggle_dataset_info(owner, dataset_name):
    """Get Kaggle dataset metadata (limited without API key)"""
    try:
        metadata = {
            'source': 'kaggle',
            'repo_id': f"{owner}/{dataset_name}",
            'note': 'Limited metadata - Kaggle API requires authentication'
        }
        return metadata
    except Exception as e:
        print(f"      Error getting Kaggle data: {str(e)}")
        return None


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_activity_status(last_modified):
    """Determine if repository is Active or Stale"""
    if not last_modified:
        return "Unknown"

    try:
        if isinstance(last_modified, str):
            mod_date = datetime.fromisoformat(last_modified.replace('Z', '+00:00'))
        else:
            mod_date = last_modified

        days_since = (datetime.now(mod_date.tzinfo) - mod_date).days

        if days_since < 180:
            return "Active"
        else:
            return "Stale"
    except Exception as e:
        return "Unknown"


def format_date(date_obj):
    """Format date to YYYY-MM-DD"""
    if not date_obj:
        return None

    try:
        if isinstance(date_obj, str):
            date_obj = datetime.fromisoformat(date_obj.replace('Z', '+00:00'))

        return date_obj.strftime('%Y-%m-%d')
    except:
        return None


def calculate_days_since_update(last_modified):
    """Calculate days since last modification"""
    if not last_modified:
        return None

    try:
        if isinstance(last_modified, str):
            mod_date = datetime.fromisoformat(last_modified.replace('Z', '+00:00'))
        else:
            mod_date = last_modified

        days_since = (datetime.now(mod_date.tzinfo) - mod_date).days
        return max(0, days_since)
    except:
        return None


def detect_creation_method(description, tags):
    """Infer creation method from description and tags"""
    try:
        combined = str(description).lower() + ' ' + str(tags).lower()

        human_keywords = ['manually', 'annotated', 'human', 'crowdsourced', 'expert', 'curated']
        machine_keywords = ['automatically', 'generated', 'machine', 'synthetic', 'auto-generated']

        has_human = any(word in combined for word in human_keywords)
        has_machine = any(word in combined for word in machine_keywords)

        if has_human and has_machine:
            return 'Hybrid'
        elif has_human:
            return 'Human'
        elif has_machine:
            return 'Machine'
        else:
            return None
    except:
        return None


def infer_dev_purpose(repo_id, description, tags):
    """Infer development purpose"""
    try:
        combined = str(repo_id).lower() + ' ' + str(description).lower() + ' ' + str(tags).lower()

        has_train = any(word in combined for word in ['train', 'training', 'fine-tune', 'finetune'])
        has_eval = any(word in combined for word in ['eval', 'evaluation', 'benchmark', 'test'])

        if has_train and has_eval:
            return 'Eval and Train'
        elif has_train:
            return 'Train only'
        elif has_eval:
            return 'Eval only'
        else:
            return None
    except:
        return None


# ============================================================================
# MAIN PROCESSING LOGIC
# ============================================================================

print(f"Processing {len(df)} benchmarks...")
print("=" * 100)

results = []

for idx, row in df.iterrows():
    dataset_url = row.get('Dataset repository')
    benchmark_name = row.get('Benchmark Name', f'Benchmark_{idx}')
    original_entry_modalties = row.get('Entry Modalties')
    description = row.get('Description')

    print(f"\n[{idx+1}/{len(df)}] {benchmark_name}")
    print(f"   URL: {dataset_url}")

    # Detect repository type
    repo_type = detect_repo_type(dataset_url)
    print(f"   Type: {repo_type}")

    # Initialize result dictionary
    result = {
        'Benchmark Name': benchmark_name,
        'Repo_Type': repo_type,
        'Repo_ID': None,
        'No_of_Samples': None,
        'Created_By': None,
        'Entry_Modalities': None,
        'Dev_Purpose': None,
        'License': None,
        'Language_Support': None,
        'Integration_Option': None,
        'Downloads_30d': 0,
        'Likes_Stars': 0,
        'Last_Modified': None,
        'Days_Since_Update': None,
        'Activity_Status': 'Unknown',
        'Tags_Topics': None,
    }

    # Extract metadata based on repository type
    metadata = None

    if repo_type == 'huggingface':
        owner, dataset_name = parse_huggingface_url(dataset_url)
        if owner and dataset_name:
            repo_id = f"{owner}/{dataset_name}"
            result['Repo_ID'] = repo_id
            metadata = get_hf_dataset_info(repo_id)

    elif repo_type == 'github':
        owner, repo_name = parse_github_url(dataset_url)
        if owner and repo_name:
            repo_id = f"{owner}/{repo_name}"
            result['Repo_ID'] = repo_id
            metadata = get_github_repo_info(owner, repo_name)

    elif repo_type == 'kaggle':
        owner, dataset_name = parse_kaggle_url(dataset_url)
        if owner and dataset_name:
            repo_id = f"{owner}/{dataset_name}"
            result['Repo_ID'] = repo_id
            metadata = get_kaggle_dataset_info(owner, dataset_name)

    # Process metadata if available
    if metadata:
        # Extract common fields
        last_modified = metadata.get('last_modified')
        result['Last_Modified'] = format_date(last_modified)
        result['Activity_Status'] = get_activity_status(last_modified)
        result['Days_Since_Update'] = calculate_days_since_update(last_modified)
        result['License'] = metadata.get('license')

        # Source-specific fields
        if metadata.get('source') == 'huggingface':
            result['Downloads_30d'] = metadata.get('downloads_30d', 0)
            result['Likes_Stars'] = metadata.get('likes', 0)
            result['Tags_Topics'] = metadata.get('tags')
            result['No_of_Samples'] = metadata.get('size_category')

            # Language mapping
            hf_langs = metadata.get('languages')
            result['Language_Support'] = map_language(hf_langs)

            # Modality inference
            result['Entry_Modalities'] = infer_modalities_from_tags_and_desc(
                metadata.get('tags'),
                description,
                benchmark_name,
                original_entry_modalties
            )

            # Creation method and dev purpose
            result['Created_By'] = detect_creation_method(description, metadata.get('tags'))
            result['Dev_Purpose'] = infer_dev_purpose(
                result['Repo_ID'],
                description,
                metadata.get('tags')
            )

            # Integration option
            result['Integration_Option'] = infer_integration_option(
                repo_type,
                metadata.get('tags'),
                metadata.get('description') or description,
                result['Repo_ID']
            )

            print(f"   Downloads: {result['Downloads_30d']}, Likes: {result['Likes_Stars']}")
            print(f"   Modalities: {result['Entry_Modalities']}")
            print(f"   Language: {result['Language_Support']}")
            print(f"   Integration: {result['Integration_Option']}")

        elif metadata.get('source') == 'github':
            result['Likes_Stars'] = metadata.get('stars', 0)
            result['Tags_Topics'] = metadata.get('topics')

            # Modality inference from GitHub description
            result['Entry_Modalities'] = infer_modalities_from_tags_and_desc(
                metadata.get('topics'),
                metadata.get('description') or description,
                benchmark_name,
                original_entry_modalties
            )

            # Creation method and dev purpose
            result['Created_By'] = detect_creation_method(
                metadata.get('description') or description,
                metadata.get('topics')
            )
            result['Dev_Purpose'] = infer_dev_purpose(
                result['Repo_ID'],
                metadata.get('description') or description,
                metadata.get('topics')
            )

            # Integration option
            result['Integration_Option'] = infer_integration_option(
                repo_type,
                metadata.get('topics'),
                metadata.get('description') or description,
                result['Repo_ID']
            )

            print(f"   Stars: {result['Likes_Stars']}")
            print(f"   Modalities: {result['Entry_Modalities']}")
            print(f"   Integration: {result['Integration_Option']}")

        elif metadata.get('source') == 'kaggle':
            # Kaggle defaults
            result['Integration_Option'] = 'Export'
            result['Entry_Modalities'] = original_entry_modalties
            print(f"   Integration: {result['Integration_Option']} (Kaggle default)")
    else:
        # Use original entry modalities if no metadata available
        result['Entry_Modalities'] = original_entry_modalties
        print(f"   No metadata available")

    results.append(result)

    # Rate limiting
    time.sleep(0.5)

print("\n" + "=" * 100)
print("Metadata extraction completed!")
print("=" * 100)

# Create DataFrame with results
results_df = pd.DataFrame(results)

# Merge with original data
final_df = df.merge(results_df, on='Benchmark Name', how='left')

# Save to Excel
output_file = "AI_Safety_Benchmarks_Enhanced_Metadata.xlsx"

with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
    # Main data sheet
    final_df.to_excel(writer, sheet_name='Benchmarks Enhanced', index=False)

    # Summary statistics
    total = len(final_df)
    hf_count = len(final_df[final_df['Repo_Type'] == 'huggingface'])
    gh_count = len(final_df[final_df['Repo_Type'] == 'github'])
    kg_count = len(final_df[final_df['Repo_Type'] == 'kaggle'])
    active = len(final_df[final_df['Activity_Status'] == 'Active'])
    stale = len(final_df[final_df['Activity_Status'] == 'Stale'])

    # Integration option counts
    api_count = len(final_df[final_df['Integration_Option'] == 'API'])
    export_count = len(final_df[final_df['Integration_Option'] == 'Export'])

    summary_data = [
        ['Metric', 'Count', 'Percentage'],
        ['Total Benchmarks', total, '100%'],
        ['Hugging Face', hf_count, f'{(hf_count/total*100):.1f}%'],
        ['GitHub', gh_count, f'{(gh_count/total*100):.1f}%'],
        ['Kaggle', kg_count, f'{(kg_count/total*100):.1f}%'],
        ['', '', ''],
        ['Active Repos', active, f'{(active/total*100):.1f}%'],
        ['Stale Repos', stale, f'{(stale/total*100):.1f}%'],
        ['', '', ''],
        ['API Integration', api_count, f'{(api_count/total*100):.1f}%'],
        ['Export Integration', export_count, f'{(export_count/total*100):.1f}%'],
    ]

    summary_df = pd.DataFrame(summary_data[1:], columns=summary_data[0])
    summary_df.to_excel(writer, sheet_name='Summary', index=False)

    # Modality distribution
    modality_dist = final_df['Entry_Modalities'].value_counts().reset_index()
    modality_dist.columns = ['Entry_Modality', 'Count']
    modality_dist.to_excel(writer, sheet_name='Modality Distribution', index=False)

    # Language distribution
    lang_dist = final_df['Language_Support'].value_counts().reset_index()
    lang_dist.columns = ['Language', 'Count']
    lang_dist.to_excel(writer, sheet_name='Language Distribution', index=False)

    # Integration distribution
    integration_dist = final_df['Integration_Option'].value_counts().reset_index()
    integration_dist.columns = ['Integration_Option', 'Count']
    integration_dist.to_excel(writer, sheet_name='Integration Distribution', index=False)

print(f"\nResults saved to: {output_file}")
print(f"\nSummary:")
print(f"  Total: {total}")
print(f"  Hugging Face: {hf_count}")
print(f"  GitHub: {gh_count}")
print(f"  Kaggle: {kg_count}")
print(f"  Active: {active}")
print(f"  Stale: {stale}")
print(f"  API: {api_count}")
rt: {export_count}")