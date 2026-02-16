print("Starting imports...")
import os
import re
import time
import requests
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')

if not GITHUB_TOKEN:
    print("Error: GITHUB_TOKEN not found in environment variables.")
    print("Please create a .env file with GITHUB_TOKEN=your_token_here")
    exit(1)

HEADERS = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3+json'
}

def clean_company_name(raw_name):
    """
    Returns a tuple: (clean_name, full_context)
    e.g. "Alphabet (NAS: GOOGL)" -> ("Alphabet", "Alphabet (NAS: GOOGL)")
    """
    # Remove text in parentheses for the 'clean name'
    clean_name = re.sub(r'\(.*?\)', '', raw_name).strip()
    return clean_name, raw_name.strip()

def get_org_details(org_login):
    """Fetches details for a specific org login."""
    try:
        url = f"https://api.github.com/orgs/{org_login}" 
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error fetching details for {org_login}: {e}")
    return None

def search_organization_api(company_tuple):
    """
    Searches for a GitHub organization using ONLY the GitHub API.
    Returns None if no *authenticated* organization (high stats) is found.
    """
    clean_name, full_context = company_tuple
    print(f"\nScanning for: {full_context}...")
    
    candidates = []
    seen_logins = set()

    # 1. GitHub Internal Search
    # Search for the clean name (e.g., "Alphabet", "Microsoft")
    print(f"  > GitHub Search Query: '{clean_name} type:org'")
    search_url = "https://api.github.com/search/users"
    params = {'q': f"{clean_name} type:org", 'per_page': 5}
    
    try:
        response = requests.get(search_url, headers=HEADERS, params=params)
        if response.status_code == 200:
            items = response.json().get('items', [])
            for item in items:
                if item['login'].lower() not in seen_logins:
                    details = get_org_details(item['login'])
                    if details:
                        candidates.append(details)
                        seen_logins.add(item['login'].lower())
    except Exception as e:
        print(f"  > Search API failed: {e}")

    if not candidates:
        print(f"  > No organization found via API.")
        return None

    # 2. Statistical Validation (Rank by Authenticity)
    # Score = (Public Repos * 1) + (Followers * 2)
    scored_candidates = []
    
    print(f"  > Validating {len(candidates)} candidates:")
    for org in candidates:
        score = org.get('public_repos', 0) + (org.get('followers', 0) * 2)
        print(f"    - {org['login']}: Repos={org.get('public_repos')}, Followers={org.get('followers')} (Score: {score})")
        scored_candidates.append((score, org))
    
    # Sort by score descending
    scored_candidates.sort(key=lambda x: x[0], reverse=True)
    
    best_candidate = scored_candidates[0][1]
    best_score = scored_candidates[0][0]
    
    # THRESHOLD: Increased to 500 to weed out false positives like 'symbl-cc' (score ~137)
    # Major tech companies will have scores in the thousands/millions.
    if best_score < 500:
        print(f"  > REJECTED: Best match {best_candidate['login']} has score {best_score} (Threshold: 500). Marking NOT FOUND.")
        return None
    
    return best_candidate

def get_repositories(org_login, limit=None):
    """Fetches public repositories for an organization. Set limit=None for all."""
    print(f"  > Fetching repos for {org_login}...")
    repos = []
    page = 1
    while True:
        url = f"https://api.github.com/orgs/{org_login}/repos"
        params = {'type': 'public', 'per_page': 100, 'page': page}
        response = requests.get(url, headers=HEADERS, params=params)
        
        if response.status_code != 200:
            break
            
        data = response.json()
        if not data:
            break
            
        repos.extend(data)
        if limit and len(repos) >= limit:
            repos = repos[:limit]
            break
            
        page += 1
        
    return repos

def get_repo_stats(owner, repo):
    """Fetches additional stats (PRs, Code Frequency)."""
    stats = {}
    
    # PR Count
    pr_url = f"https://api.github.com/search/issues"
    pr_params = {'q': f"repo:{owner}/{repo} is:pr", 'per_page': 1}
    # Sleep briefly to handle search API rate limits
    time.sleep(0.5)
    
    try:
        pr_response = requests.get(pr_url, headers=HEADERS, params=pr_params)
        if pr_response.status_code == 200:
            stats['pr_count'] = pr_response.json()['total_count']
        else:
            stats['pr_count'] = 0
    except:
        stats['pr_count'] = 0

    # Code Frequency (Weekly additions/deletions) - Aggregated
    code_freq_url = f"https://api.github.com/repos/{owner}/{repo}/stats/code_frequency"
    try:
        cf_response = requests.get(code_freq_url, headers=HEADERS)
        
        total_additions = 0
        total_deletions = 0
        
        if cf_response.status_code == 200 and isinstance(cf_response.json(), list):
            data = cf_response.json()
            for week in data:
                total_additions += week[1]
                total_deletions += abs(week[2])
        
        stats['total_additions'] = total_additions
        stats['total_deletions'] = total_deletions
    except:
        stats['total_additions'] = 0
        stats['total_deletions'] = 0
    
    return stats

import json

def main():
    input_file = 'companies.txt'
    output_dir = 'json_data'
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return
        
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(input_file, 'r') as f:
        raw_companies = f.readlines()

    print("Script started...")
    
    # For testing, we can uncomment this limit.
    # For production usage, process all companies.
    # raw_companies = raw_companies[:5] 

    for line in raw_companies:
        company_tuple = clean_company_name(line)
        if not company_tuple[0]:
            continue

        clean_name = company_tuple[0]
        # Create company folder (lowercase, sanitized)
        sanitized_dirname = "".join(x for x in clean_name if x.isalnum() or x in (' ','-','_')).strip().replace(' ', '_').lower()
        company_dir = os.path.join(output_dir, sanitized_dirname)
        
        if not os.path.exists(company_dir):
            os.makedirs(company_dir)
            
        # Search using Pure API logic
        org = search_organization_api(company_tuple)
        
        # Base company info
        company_info = {
            "company_input": company_tuple[1],
            "org_found": False,
            "org_name": None,
            "org_login": None,
            "org_id": None,
            "org_website": None,
            "org_followers": 0,
            "scrape_timestamp": time.time()
        }
        
        if org:
            print(f"  > Selected Org: {org['login']} ({org.get('name', 'N/A')})")
            company_info["org_found"] = True
            company_info["org_name"] = org.get('name')
            company_info["org_login"] = org['login']
            company_info["org_id"] = org['id']
            company_info["org_website"] = org.get('blog') or org.get('html_url')
            company_info["org_followers"] = org.get('followers')
            
            # Save company info first
            with open(os.path.join(company_dir, "_company_info.json"), 'w') as f:
                json.dump(company_info, f, indent=4)
            
            # Fetch repositories (limit=None for production)
            repos = get_repositories(org['login'], limit=None) 
            
            print(f"    Processing {len(repos)} repositories...")
            for repo in repos:
                repo_stats = get_repo_stats(org['login'], repo['name'])
                
                repo_data = {
                    "company_input": company_tuple[1],
                    "org_login": org['login'],
                    "name": repo['name'],
                    "id": repo['id'],
                    "description": repo.get('description'),
                    "is_fork": repo['fork'],
                    "language": repo['language'],
                    "forks_count": repo['forks_count'],
                    "stargazers_count": repo['stargazers_count'],
                    "watchers_count": repo['watchers_count'],
                    "open_issues_count": repo['open_issues_count'],
                    "total_prs": repo_stats['pr_count'],
                    "lines_added": repo_stats['total_additions'],
                    "lines_deleted": repo_stats['total_deletions']
                }
                
                # Sanitize repo name for filename
                safe_repo_name = "".join(x for x in repo['name'] if x.isalnum() or x in ('-','_','.')).strip()
                repo_filename = os.path.join(company_dir, f"{safe_repo_name}.json")
                
                with open(repo_filename, 'w') as rf:
                    json.dump(repo_data, rf, indent=4)
                
                print(f"    - Saved {safe_repo_name}.json")
                
        else:
            print(f"  > Status: NOT FOUND")
            # Save just the negative result
            with open(os.path.join(company_dir, "_company_info.json"), 'w') as f:
                json.dump(company_info, f, indent=4)

    print(f"Done! All data saved in {output_dir}/")

if __name__ == "__main__":
    main()
