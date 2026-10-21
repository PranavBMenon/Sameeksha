# Sameeksha: Cultural Fest Management System

A desktop application for running a school inter-house cultural fest. Organizers enter results as events finish, the app keeps live house standings and statistics, and the data is automatically backed up to CSV and pushed to a GitHub repository so a web results page can display it.

Built with Python, CustomTkinter, MySQL and Matplotlib.

---

## Table of Contents

1. [Features](#features)
2. [How It Works](#how-it-works)
3. [Project Structure](#project-structure)
4. [Requirements](#requirements)
5. [Installation](#installation)
6. [Configuration](#configuration)
7. [Running the App](#running-the-app)
8. [Using the App](#using-the-app)
9. [Database Schema](#database-schema)
10. [Scoring and Categories](#scoring-and-categories)
11. [Automatic Backup and GitHub Sync](#automatic-backup-and-github-sync)
12. [CSV Formats](#csv-formats)
13. [Security and Privacy Notes](#security-and-privacy-notes)
14. [Known Limitations](#known-limitations)
15. [Troubleshooting](#troubleshooting)

---

## Features

- **House points dashboard**: live ranking of the four houses (Ganga, Yamuna, Kaveri, Krishna).
- **Data entry** for individual and group events, with the category chosen automatically from the student's class.
- **Update / delete** existing records, filterable by category, event type and event name.
- **Statistics dashboard** with four charts: house points over time, current standings, top performers per category, and participation breakdown.
- **Configurable scoring**: points per position and the class range of each category can be changed from the Settings tab, with optional data migration and point recalculation.
- **CSV export** of all data and a house summary, through a folder picker.
- **Automatic background backup** to CSV every 15 minutes and upload to GitHub every 25 minutes.
- **Light and dark themes** (see [Known Limitations](#known-limitations) for the toggle).
- **Safe bulk delete**: "Delete All Data" needs two confirmations and typing `DELETE`.

---

## How It Works

```
 Organizer enters results
          |
          v
   +--------------+      every 15 min      +---------------------------+
   |    MySQL     | ---------------------> | ~/Desktop/Sameeksha_CSV_  |
   | cultural_fest|     (MySQL exporter)   | Data/*.csv                |
   +--------------+                        +---------------------------+
          ^                                              |
          |                                              | every 25 min
   CustomTkinter GUI                                     | (GitHub REST API)
   (stats, edit, export)                                 v
                                            +---------------------------+
                                            |   GitHub repository       |
                                            |   CSV files + index.html  |
                                            +---------------------------+
```

1. Results are entered through the desktop GUI and stored in a local MySQL database.
2. A background thread exports every table to CSV on the desktop.
3. A second background thread uploads those CSVs to a public GitHub repository using the GitHub Contents API.
4. The web front end in the repository (`index.html`) reads the published CSVs to show results online.

---

## Project Structure

```
Sameeksha/
├── main.py                  # The entire desktop application
├── index.html               # Web results page (reads the published CSVs)
├── sameeksha_settings.json  # Created on first run (points + category ranges)
├── cat1_individual.csv ...  # Auto-exported data (cat1-cat5, individual + group)
└── cat1_group.csv ...
```

`main.py` contains three classes:

| Class | Purpose |
|---|---|
| `MySQLDesktopExporter` | Exports every table to CSV in `~/Desktop/Sameeksha_CSV_Data` (periodic) |
| `GitHubCSVUploader` | Uploads the CSV folder to GitHub via the REST API (periodic) |
| `FestManagementSystem` | The GUI, database logic, scoring, statistics and settings |

---

## Requirements

- Python 3.9 or newer
- MySQL Server (local), reachable on `localhost`
- A GitHub repository (public, if the web page is public) and a Personal Access Token with permission to write repository contents
- Python packages:

| Package | Used for |
|---|---|
| `customtkinter` | GUI |
| `mysql-connector-python` | Database access |
| `matplotlib` | Statistics charts |
| `requests` | GitHub API calls |

Tkinter ships with most Python installers. On some Linux distributions install it separately (for example `sudo apt install python3-tk`).

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/BVBIJK/Sameeksha.git
cd Sameeksha

# 2. (Recommended) create a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install customtkinter mysql-connector-python matplotlib requests
```

Make sure MySQL Server is installed and running. The app creates the `cultural_fest` database and all tables on first launch, so you do not need to create them yourself. The MySQL user you configure must be allowed to run `CREATE DATABASE` and `CREATE TABLE`.

---

## Configuration

Two places in `main.py` need your credentials before the first run.

### 1. MySQL credentials

In `FestManagementSystem.__init__`:

```python
self.db_config = {
    'host': 'localhost',
    'user': 'YOUR_MYSQL_USER',
    'password': 'YOUR_MYSQL_PASSWORD',
    'database': 'cultural_fest'
}
```

### 2. GitHub credentials

In `FestManagementSystem.start_auto_backup`:

```python
github_config = {
    'github_token': 'YOUR_GITHUB_TOKEN',
    'username': 'YOUR_GITHUB_USERNAME',
    'repo_name': 'YOUR_REPO_NAME',
    'branch': 'main',
    'interval_minutes': 25
}
```

Create the token under GitHub **Settings > Developer settings > Personal access tokens**. A fine-grained token limited to this one repository with **Contents: Read and write** is the safest choice.

> **Never commit real credentials.** Prefer reading them from environment variables or an untracked config file (see [Security and Privacy Notes](#security-and-privacy-notes)).

### 3. Optional: backup intervals and folder

- CSV export interval: `run_periodic(interval_minutes=15)` in `start_auto_backup`.
- GitHub upload interval: `interval_minutes` in `github_config`.
- Export folder: `Sameeksha_CSV_Data` on the Desktop (falls back to the home folder if there is no Desktop).

---

## Running the App

```bash
python main.py
```

The window opens at 80% of your screen (minimum 1000x600) and starts the two background sync threads automatically. Console output shows export and upload status.

---

## Using the App

The sidebar has six sections.

### Home
Shows the four houses ranked by total points, color-coded per house.

### Enter Data
1. Choose **Individual** or **Group**.
2. Fill in the student or team name, class (1-12), house, event name and position (1-10).
3. Click **Add Entry**.

The category is picked from the class using the configured ranges. For individual events, points are calculated from the position. Group results store the position only.

### Update Data
1. Pick a category (1-5) and event type, optionally type an event name to filter.
2. Click **Load Records**.
3. Use **Edit** or **Delete** on any row.

**Delete All Data** wipes every table after two confirmation dialogs and a typed `DELETE`.

### Statistics
- **House Points Over Time**: cumulative line chart per house.
- **Current House Standings**: bar chart.
- **Best Individual Performers by Category**: top 3 per category by total points.
- **Event Participation Statistics**: pie of events per category plus a bar chart of participations per house.

### Export Data
- **Export All Data (CSV)**: choose a folder; one CSV per non-empty table (`CatN_Individual.csv`, `CatN_Group.csv`).
- **Export House Summary (CSV)**: total house points plus the leading house in each category.

### Settings
- **Points Configuration**: points for each position, with an option to add more positions.
- **Category Class Ranges**: min and max class for each category. Ranges are validated (1-12, min <= max, no overlap).

When you save:
- If **category ranges** changed, you can migrate existing records so each moves to the table matching its class.
- If **points** changed, you can recalculate all stored points or keep historical values and apply the new points only to future entries.

**Reset to Defaults** restores the values below.

---

## Database Schema

Database: `cultural_fest`. For each category `N` from 1 to 5 there are two tables.

**`catN_individual`**

| Column | Type |
|---|---|
| `id` | INT, auto-increment, primary key |
| `student_name` | VARCHAR(100) |
| `class_num` | INT |
| `house` | ENUM('Ganga','Yamuna','Kaveri','Krishna') |
| `event_name` | VARCHAR(100) |
| `position` | INT |
| `points` | INT |
| `entry_date` | TIMESTAMP, defaults to now |

**`catN_group`**

| Column | Type |
|---|---|
| `id` | INT, auto-increment, primary key |
| `team_name` | VARCHAR(100) |
| `class_num` | INT |
| `house` | ENUM('Ganga','Yamuna','Kaveri','Krishna') |
| `event_name` | VARCHAR(100) |
| `position` | INT |
| `entry_date` | TIMESTAMP, defaults to now |

---

## Scoring and Categories

Defaults (stored in `sameeksha_settings.json`, created on first run):

| Position | Points |
|---|---|
| 1st | 5 |
| 2nd | 3 |
| 3rd | 1 |
| 4th and below | 0 (unless configured) |

| Category | Classes |
|---|---|
| 1 | 1-2 |
| 2 | 3-4 |
| 3 | 5-7 |
| 4 | 8-10 |
| 5 | 11-12 |

House totals on the dashboard and charts are calculated from **individual** event points.

---

## Automatic Backup and GitHub Sync

Both jobs run as daemon threads started when the app opens and stop when it closes.

**CSV export (every 15 minutes)**: exports all 10 tables to `~/Desktop/Sameeksha_CSV_Data/`. Columns exported:

- Group tables: `event_name, team_name, class_num, position`
- Individual tables: `event_name, student_name, class_num, house, position`

**GitHub upload (every 25 minutes)**: for each CSV in that folder, looks up the existing file's SHA and creates or updates it on the configured branch with a commit message such as `Update cat1_individual.csv`. Failures print a hint (for example a bad token or repository not found).

Because every cycle re-uploads each file, the repository's commit history grows quickly during an event.

---

## CSV Formats

There are two different export formats, so keep them straight:

| Source | Files | Columns |
|---|---|---|
| Automatic export (feeds GitHub) | `catN_individual.csv`, `catN_group.csv` | see the lists above |
| Manual export button | `CatN_Individual.csv`, `CatN_Group.csv` | `ID, Student Name/Team Name, Class, House, Event Name, Position, [Points,] Entry Date` |

Manual exports are meant for local use. Do not upload them into the same repository folder as the auto-exported files.

---

## Security and Privacy Notes

- **Credentials**: the MySQL password and GitHub token are plain text in `main.py`. Do not push a version containing real values. Safer approaches: load them with `os.environ`, or from a `config.json` listed in `.gitignore`. If a token ever leaks, revoke it in GitHub settings immediately.
- **Public data**: the exported CSVs contain student names, classes and houses, and a public repository (plus GitHub Pages) makes them visible to everyone and indexable by search engines. This data is about minors and git history keeps old versions even after deletion. Make sure the school has authorized public publication, and consider exporting only the fields the results page needs.
- **Destructive actions**: "Delete All Data" is irreversible. Keep the CSV backups until the event is finalized.
- **MySQL access**: use a dedicated MySQL user with privileges limited to the `cultural_fest` database instead of `root`.

---

## Known Limitations

These are issues in the current version:

1. **Editing a record's class across categories** can update the wrong table. `update_record` recomputes the category from the new class but updates by `id` in the new category's table, not the table the record is in. Avoid changing a class to another category through Edit; delete and re-add instead.
2. **First-run points**: on the very first launch the default points map has integer keys while lookups use string keys, so new entries can get 0 points until the app is restarted once.
3. **Exported CSVs omit some columns**: group exports have no `house`, and individual exports have no `points`, so a front end cannot attribute group results to a house or read points directly.
4. **Group events do not score**: group tables have no points column, so house totals include individual events only.
5. **Dark mode switch is not visible**: the toggle is created but never added to the sidebar layout.
6. **Matplotlib figures are never closed**, so memory use grows if the Statistics tab is opened many times in one session.

---

## Troubleshooting

| Problem | What to check |
|---|---|
| "Error connecting to database" | MySQL is running, credentials in `db_config` are correct, and the user can create the `cultural_fest` database |
| `ModuleNotFoundError` | Run the `pip install` line above inside your active virtual environment |
| GitHub upload prints 401 | Token is wrong, expired, or lacks Contents write permission |
| GitHub upload prints 404 | Wrong username or repository name, or the token cannot access the repository |
| No CSV files appear on the Desktop | The export thread failed to connect to MySQL; read the console output |
| Tkinter import error on Linux | Install `python3-tk` |
| Points look wrong after changing settings | Use Settings > Save and choose **Recalculate All Points** |

---

## License

Released under the [MIT License](LICENSE). You are free to use, modify and distribute the code, including for your own school's events. The license covers the source code only; real event data (student names, classes, results) is not included and must not be published without proper authorization. The CSVs in `sample_csvs/` are randomly generated demo data.
