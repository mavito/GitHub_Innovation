# GitHub Organization Scraper

A Python tool designed to automatically find and scrape public repository data for a list of companies from GitHub. It intelligently searches for the correct organization, validates it to avoid fake accounts, and saves detailed statistics for every repository.

## Features

- **Smart Organization Search:** Finds the official GitHub organization for a company name (e.g., "Alphabet" → `symbl-cc` [Rejected], "Microsoft" → `microsoft` [Accepted]).
- **Strict Validation:** Uses a scoring system (Repositories + Followers) to reject fake or squatting organizations.
- **Deep Data Retrieval:** Fetches metadata, star counts, fork counts, pull request totals, and code frequency (lines added/deleted) for **every single public repository**.
- **Structured Output:** Saves data in a clean folder structure (`json_data/company_name/repo_name.json`).

---

## Setup Guide

### 1. Prerequisites
- **Python 3.8+** installed on your machine.
- A **GitHub Account** (to generate an API token).

### 2. Get a GitHub API Token
To scrape data without hitting rate limits immediately, you need a Personal Access Token.
1. Go to [GitHub Developer Settings > Personal Access Tokens](https://github.com/settings/tokens).
2. Click **Generate new token (classic)**.
3. Give it a name (e.g., "Scraper").
4. **Scopes:** You don't need to check any scopes for public data, but checking `public_repo` doesn't hurt.
5. Click **Generate token** and **COPY IT** immediately.

### 3. Installation
1. Unzip this project folder.
2. Open your terminal/command prompt and navigate to the folder.
3. Install the required Python packages:
   ```bash
   pip3 install -r requirements.txt
   ```
   *(Note: You might need to use `pip` instead of `pip3` depending on your system).*

### 4. Configure the Token
Create a file named `.env` in the same directory as the script. Open it with a text editor and add your token:
```ini
GITHUB_TOKEN=ghp_your_secret_token_here_xxxxxxxxx
```

---

## Usage

### 1. Prepare your Input List
Edit the `companies.txt` file. Add the names of the companies you want to scrape, one per line.
The script automatically cleans up ticker symbols or extra text.
**Example `companies.txt`:**
```text
Microsoft (NAS: MSFT)
Alphabet (NAS: GOOGL)
Amazon Web Services
Nvidia
meta platforms
```

### 2. Run the Scraper
Run the script from your terminal:
```bash
python3 github_scraper.py
```

The script will:
1.  Read `companies.txt`.
2.  Search GitHub for each company.
3.  If found and validated, fetch all repositories.
4.  Save the data to `json_data/`.

---

## Output Data

The script creates a `json_data/` folder. Inside, each company gets its own folder.

### Directory Structure
```
json_data/
├── microsoft/
│   ├── _company_info.json         # Organization details and Found/Not Found status
│   ├── BeanSpy.json               # Data for "BeanSpy" repo
│   ├── HealthVault-iOS.json       # Data for another repo
│   └── ... (thousands of files)
├── alphabet/
│   └── _company_info.json         # Status: NOT FOUND (Score too low)
└── ...
```

### JSON Content Example
Each repository file contains:
```json
{
    "name": "BeanSpy",
    "description": "BeanSpy is an open source Java servlet...",
    "language": "Java",
    "stargazers_count": 25,
    "forks_count": 18,
    "total_prs": 5,
    "lines_added": 35787,
    "lines_deleted": 26
}
```

---

## Rate Limits & Performance

GitHub's API has strict rate limits to prevent abuse.

- **Authenticated Limit:** 5,000 requests per hour.
- **Unauthenticated Limit:** 60 requests per hour (You MUST use a token).

**Search vs. Fetching:**
- Searching for an organization costs very little.
- Fetching repository lists costs 1 request per page (100 repos).
- **Fetching Details (PRs/Code Frequency) costs ~2 requests PER REPOSITORY.**

**Implication for Large Companies:**
- A company like **Microsoft** has ~7,500 repositories.
- Scraping Microsoft alone requires **~15,000+ API requests**.
- This exceeds the hourly limit of 5,000.
- **The script handles this by sleeping** briefly, but for massive organizations, it might take several hours to complete or fail if the limit is strictly enforced by GitHub.

**Recommendation:**
If you are scraping massive tech giants, run the script for a few companies at a time, or accept that it will take a long time to run.

---

## How It Works (The Logic)
1.  **Search**: Queries GitHub for organizations matching the company name.
2.  **Scoring**: It calculates a "Truth Score" for the best match:
    -   `Score = (Public Repos) + (Followers * 2)`
3.  **Validation**:
    -   If `Score > 500`: It's considered a legitimate tech company (e.g., Microsoft).
    -   If `Score < 500`: It's considered a "False Positive" or squatter (e.g., `symbl-cc` for Alphabet) and marked as **NOT FOUND**.
