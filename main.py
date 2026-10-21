'''Enter your github credentials near to line 2511 and make sure github repo is set to public
    also enter SQL credentails near line 344'''
import customtkinter as ctk
import mysql.connector
from mysql.connector import Error
import tkinter.messagebox as messagebox
from datetime import datetime
import csv
from tkinter import filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
from collections import defaultdict
import os
import time
from datetime import datetime
import logging
import threading
import requests
import json


class MySQLDesktopExporter:
    def __init__(self, db_config, desktop_folder_name='Sameeksha_CSV_Data'):
        """Initialize the MySQL desktop exporter."""
        self.db_config = db_config
        self.desktop_folder_name = desktop_folder_name
        self.desktop_path = self.get_desktop_path()
        self.export_folder = os.path.join(self.desktop_path, desktop_folder_name)
        os.makedirs(self.export_folder, exist_ok=True)

        # Define table configurations
        self.tables_config = {
            'cat1_group': {'type': 'group', 'columns': ['event_name', 'team_name', 'class_num', 'position']},
            'cat2_group': {'type': 'group', 'columns': ['event_name', 'team_name', 'class_num', 'position']},
            'cat3_group': {'type': 'group', 'columns': ['event_name', 'team_name', 'class_num', 'position']},
            'cat4_group': {'type': 'group', 'columns': ['event_name', 'team_name', 'class_num', 'position']},
            'cat5_group': {'type': 'group', 'columns': ['event_name', 'team_name', 'class_num', 'position']},
            'cat1_individual': {'type': 'individual',
                                'columns': ['event_name', 'student_name', 'class_num', 'house', 'position']},
            'cat2_individual': {'type': 'individual',
                                'columns': ['event_name', 'student_name', 'class_num', 'house', 'position']},
            'cat3_individual': {'type': 'individual',
                                'columns': ['event_name', 'student_name', 'class_num', 'house', 'position']},
            'cat4_individual': {'type': 'individual',
                                'columns': ['event_name', 'student_name', 'class_num', 'house', 'position']},
            'cat5_individual': {'type': 'individual',
                                'columns': ['event_name', 'student_name', 'class_num', 'house', 'position']},
        }

    def get_desktop_path(self):
        """Get the desktop path for the current operating system."""
        try:
            if os.name == 'nt':  # Windows
                desktop = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')
            else:  # macOS and Linux
                desktop = os.path.join(os.path.join(os.path.expanduser('~')), 'Desktop')

            if os.path.exists(desktop):
                return desktop
            else:
                return os.path.expanduser('~')
        except Exception as e:
            return os.getcwd()

    def connect_database(self):
        """Establish MySQL database connection."""
        try:
            connection = mysql.connector.connect(**self.db_config)
            return connection
        except Error as e:
            print(f"Database connection failed: {e}")
            raise

    def export_table_to_csv(self, connection, table_name, table_config):
        """Export a single table to CSV file."""
        csv_file_path = os.path.join(self.export_folder, f"{table_name}.csv")

        try:
            cursor = connection.cursor()
            columns = table_config['columns']
            query = f"SELECT {', '.join(columns)} FROM {table_name}"
            cursor.execute(query)
            results = cursor.fetchall()

            with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(columns)
                writer.writerows(results)

            cursor.close()
            print(f"✅ Exported {table_name} ({len(results)} rows)")
            return csv_file_path
        except Error as e:
            print(f"❌ Failed to export table {table_name}: {e}")
            raise

    def export_all_tables(self):
        """Export all configured tables to CSV files."""
        connection = None
        exported_files = []

        try:
            connection = self.connect_database()

            for table_name, table_config in self.tables_config.items():
                try:
                    csv_file = self.export_table_to_csv(connection, table_name, table_config)
                    exported_files.append(csv_file)
                except Exception as e:
                    print(f"Error exporting {table_name}: {e}")
                    continue

            return exported_files
        finally:
            if connection and connection.is_connected():
                connection.close()

    def export_once(self):
        """Run a single export of all tables."""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"🔄 Export started at: {timestamp}")

            exported_files = self.export_all_tables()

            if exported_files:
                print(f"✅ Successfully exported {len(exported_files)} tables to {self.export_folder}")
            else:
                print("❌ No files were exported successfully")
        except Exception as e:
            print(f"Export failed: {e}")

    def run_periodic(self, interval_minutes=15):
        """Run the export process periodically at specified intervals."""
        interval_seconds = interval_minutes * 60
        print(f"🔄 Starting periodic export every {interval_minutes} minutes...")
        print(f"📁 Export folder: {self.export_folder}")

        # Run initial export
        self.export_once()

        while True:
            try:
                print(f"⏰ Sleeping for {interval_minutes} minutes...")
                time.sleep(interval_seconds)
                print("🔄 Starting periodic export...")
                self.export_once()
            except Exception as e:
                print(f"❌ Export process error: {e}")
                time.sleep(interval_seconds)


class GitHubCSVUploader:
    def __init__(self, github_token, username, repo_name, branch="main",
                 local_folder=None, interval_minutes=25):
        """Initialize GitHub CSV uploader"""
        self.github_token = github_token
        self.username = username
        self.repo_name = repo_name
        self.branch = branch
        self.interval_minutes = interval_minutes

        # Set local folder path
        if local_folder:
            self.local_folder = local_folder
        else:
            self.local_folder = os.path.join(
                os.path.expanduser("~/Desktop"),
                "Sameeksha_CSV_Data"
            )

        self.api_base = f"https://api.github.com/repos/{username}/{repo_name}"

    def get_file_content(self, file_path):
        """Read file content and encode it in base64"""
        try:
            import base64
            with open(file_path, 'rb') as file:
                content = file.read()
                return base64.b64encode(content).decode('utf-8')
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return None

    def get_file_sha(self, file_path_in_repo):
        """Get the SHA of existing file in repository"""
        import requests
        url = f"{self.api_base}/contents/{file_path_in_repo}"
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }

        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()['sha']
        except Exception as e:
            print(f"Error getting SHA: {e}")
        return None

    def upload_file_to_github(self, local_file_path, repo_file_path):
        """Upload or update a file in GitHub repository"""
        import requests
        import json
        import base64

        # Get file content
        file_content = self.get_file_content(local_file_path)
        if not file_content:
            return False

        # Check if file already exists
        existing_sha = self.get_file_sha(repo_file_path)

        # Prepare the request
        url = f"{self.api_base}/contents/{repo_file_path}"
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }

        # Prepare the data
        data = {
            "message": f"Update {os.path.basename(local_file_path)}" if existing_sha
            else f"Upload {os.path.basename(local_file_path)}",
            "content": file_content,
            "branch": self.branch
        }

        # If file exists, include SHA for update
        if existing_sha:
            data["sha"] = existing_sha

        # Make the request
        try:
            response = requests.put(url, headers=headers, data=json.dumps(data))

            if response.status_code in [200, 201]:
                action = "Updated" if existing_sha else "Created"
                print(f"✅ {action}: {repo_file_path}")
                return True
            else:
                print(f"❌ Failed to upload {repo_file_path}: {response.status_code}")
                if response.status_code == 401:
                    print("   Check your GitHub token")
                elif response.status_code == 404:
                    print("   Repository not found")
                return False
        except Exception as e:
            print(f"❌ Error uploading {repo_file_path}: {e}")
            return False

    def upload_all_files(self):
        """Upload all CSV files from the folder"""
        # Check if local folder exists
        if not os.path.exists(self.local_folder):
            print(f"❌ Folder not found: {self.local_folder}")
            return 0, 0

        # Find all CSV files
        csv_files = [f for f in os.listdir(self.local_folder) if f.endswith('.csv')]

        if not csv_files:
            print(f"No CSV files found in {self.local_folder}")
            return 0, 0

        print(f"Found {len(csv_files)} CSV files, uploading to GitHub...")
        success_count = 0

        # Upload each file
        for file_name in csv_files:
            local_path = os.path.join(self.local_folder, file_name)
            repo_path = file_name

            if self.upload_file_to_github(local_path, repo_path):
                success_count += 1

        print(f"GitHub upload complete: {success_count}/{len(csv_files)} files uploaded")
        return success_count, len(csv_files)

    def run_periodic(self):
        """Run periodic uploads"""
        interval_seconds = self.interval_minutes * 60
        print(f"🔄 Starting periodic GitHub upload every {self.interval_minutes} minutes...")
        print(f"📁 Local folder: {self.local_folder}")
        print(f"📤 Repository: {self.username}/{self.repo_name}")

        # Run initial upload
        self.upload_all_files()

        while True:
            try:
                print(f"⏰ Sleeping for {self.interval_minutes} minutes...")
                time.sleep(interval_seconds)
                print("🔄 Starting periodic GitHub upload...")
                self.upload_all_files()
            except Exception as e:
                print(f"❌ GitHub upload error: {e}")
                time.sleep(interval_seconds)


class FestManagementSystem:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Sameeksha")
        self.is_dark_mode = False
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        # Get screen dimensions and scale window
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # Scale window to 80% of screen size, with minimum dimensions
        window_width = max(1000, int(screen_width * 0.8))
        window_height = max(600, int(screen_height * 0.8))

        # Center window on screen
        pos_x = (screen_width // 2) - (window_width // 2)
        pos_y = (screen_height // 2) - (window_height // 2)

        self.root.geometry(f"{window_width}x{window_height}+{pos_x}+{pos_y}")
        self.root.resizable(True, True)  # Allow resizing
        self.root.minsize(1000, 600)  # Set minimum size

        # Color scheme
        self.colors = {
            'primary_blue': '#1f538d',
            'light_blue': '#3498db',
            'white': '#ffffff',
            'light_gray': '#f8f9fa',
            'text_dark': '#2c3e50',
            'houses': {
                'Ganga': '#ff8c00',
                'Yamuna': '#3498db',
                'Kaveri': '#27ae60',
                'Krishna': '#e74c3c'
            }
        }

        # Database configuration
        self.db_config = {
            'host': 'localhost',
            'user': '****',
            'password': '****',
            'database': 'cultural_fest'
        }

        # Load settings
        self.settings = self.load_settings()

        # Initialize database
        self.init_database()

        # Create UI
        self.create_ui()

        # Show home by default
        self.show_home()
        self.start_auto_backup()

    def load_settings(self):
        """Load settings from JSON file"""
        settings_file = 'sameeksha_settings.json'
        default_settings = {
            'points_map': {1: 5, 2: 3, 3: 1},
            'category_ranges': {
                '1': {'min': 1, 'max': 2},
                '2': {'min': 3, 'max': 4},
                '3': {'min': 5, 'max': 7},
                '4': {'min': 8, 'max': 10},
                '5': {'min': 11, 'max': 12}
            }
        }

        try:
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    return json.load(f)
            else:
                self.save_settings(default_settings)
                return default_settings
        except Exception as e:
            print(f"Error loading settings: {e}")
            return default_settings

    def save_settings(self, settings):
        """Save settings to JSON file"""
        settings_file = 'sameeksha_settings.json'
        try:
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=4)
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")
            return False

    def init_database(self):
        """Initialize database and create tables if they don't exist"""
        try:
            # Connect to MySQL server
            connection = mysql.connector.connect(
                host=self.db_config['host'],
                user=self.db_config['user'],
                password=self.db_config['password']
            )
            cursor = connection.cursor()

            # Create database if it doesn't exist
            cursor.execute("CREATE DATABASE IF NOT EXISTS cultural_fest")
            cursor.execute("USE cultural_fest")

            # Create tables for all categories
            for cat in range(1, 6):
                # Individual events table
                individual_table = f"""
                CREATE TABLE IF NOT EXISTS cat{cat}_individual (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    student_name VARCHAR(100) NOT NULL,
                    class_num INT NOT NULL,
                    house ENUM('Ganga', 'Yamuna', 'Kaveri', 'Krishna') NOT NULL,
                    event_name VARCHAR(100) NOT NULL,
                    position INT NOT NULL,
                    points INT NOT NULL,
                    entry_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """

                # Group events table
                group_table = f"""
                CREATE TABLE IF NOT EXISTS cat{cat}_group (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    team_name VARCHAR(100) NOT NULL,
                    class_num INT NOT NULL,
                    house ENUM('Ganga', 'Yamuna', 'Kaveri', 'Krishna') NOT NULL,
                    event_name VARCHAR(100) NOT NULL,
                    position INT NOT NULL,
                    entry_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """

                cursor.execute(individual_table)
                cursor.execute(group_table)

            connection.commit()
            cursor.close()
            connection.close()

        except Error as e:
            messagebox.showerror("Database Error", f"Error initializing database: {e}")

    def get_db_connection(self):
        """Get database connection"""
        try:
            connection = mysql.connector.connect(**self.db_config)
            return connection
        except Error as e:
            messagebox.showerror("Database Error", f"Error connecting to database: {e}")
            return None

    def determine_category(self, class_num):
        """Determine category based on class number using settings"""
        for cat, ranges in self.settings['category_ranges'].items():
            if ranges['min'] <= class_num <= ranges['max']:
                return int(cat)
        return None

    def get_points_for_position(self, position):
        """Get points based on position using settings"""
        return self.settings['points_map'].get(str(position), 0)

    def create_ui(self):
        """Create the main UI"""
        # Main container
        self.main_frame = ctk.CTkFrame(self.root, fg_color=self.colors['white'])
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Sidebar
        self.create_sidebar()

        # Content area
        self.content_frame = ctk.CTkFrame(self.main_frame, fg_color=self.colors['light_gray'])
        self.content_frame.pack(side="right", fill="both", expand=True, padx=(0, 10))

    def create_sidebar(self):
        """Create sidebar with navigation buttons"""
        self.sidebar = ctk.CTkFrame(self.main_frame, width=200, fg_color=self.colors['primary_blue'])
        self.sidebar.pack(side="left", fill="y", padx=(10, 10), pady=10)
        self.sidebar.pack_propagate(False)

        # Title
        title_label = ctk.CTkLabel(
            self.sidebar,
            text="Sameeksha",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.colors['white']
        )
        title_label.pack(pady=(20, 30))

        # Dark mode toggle
        self.dark_mode_var = ctk.BooleanVar(value=self.is_dark_mode)
        dark_mode_switch = ctk.CTkSwitch(
            self.sidebar,
            text="Dark Mode",
            variable=self.dark_mode_var,
            command=self.toggle_dark_mode,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=self.colors['white']
        )

        # Navigation buttons
        self.nav_buttons = {}
        nav_items = [
            ("Home", self.show_home),
            ("Enter Data", self.show_enter_data),
            ("Update Data", self.show_update_data),
            ("Statistics", self.show_statistics),
            ("Export Data", self.show_export_data),
            ("Settings", self.show_settings)
        ]

        for text, command in nav_items:
            btn = ctk.CTkButton(
                self.sidebar,
                text=text,
                command=command,
                width=160,
                height=40,
                font=ctk.CTkFont(size=14, weight="bold"),
                fg_color="transparent",
                text_color=self.colors['white'],
                hover_color=self.colors['light_blue']
            )
            btn.pack(pady=5)
            self.nav_buttons[text] = btn

    def toggle_dark_mode(self):
        """Toggle between dark and light mode"""
        self.is_dark_mode = self.dark_mode_var.get()

        if self.is_dark_mode:
            ctk.set_appearance_mode("dark")
            # Update colors for dark mode
            self.colors.update({
                'light_gray': '#2b2b2b',
                'white': '#1a1a1a',
                'text_dark': '#ffffff'
            })
        else:
            ctk.set_appearance_mode("light")
            # Restore light mode colors
            self.colors.update({
                'light_gray': '#f8f9fa',
                'white': '#ffffff',
                'text_dark': '#2c3e50'
            })

        # Refresh current view
        current_view = getattr(self, '_current_view', 'home')
        if current_view == 'home':
            self.show_home()
        elif current_view == 'enter_data':
            self.show_enter_data()
        elif current_view == 'update_data':
            self.show_update_data()
        elif current_view == 'statistics':
            self.show_statistics()
        elif current_view == 'export_data':
            self.show_export_data()
        elif current_view == 'settings':
            self.show_settings()

    def clear_content(self):
        """Clear content frame"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def show_home(self):
        """Show home tab with house total points"""
        self._current_view = 'home'
        self.clear_content()

        # Header
        header = ctk.CTkLabel(
            self.content_frame,
            text="House Points Dashboard",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=self.colors['text_dark']
        )
        header.pack(pady=20)

        # Get total points for each house
        house_points = self.get_total_house_points()

        # Create points display
        points_frame = ctk.CTkFrame(self.content_frame, fg_color=self.colors['white'])
        points_frame.pack(pady=20, padx=40, fill="x")

        # Sort houses by points (descending)
        sorted_houses = sorted(house_points.items(), key=lambda x: x[1], reverse=True)

        for i, (house, points) in enumerate(sorted_houses):
            house_frame = ctk.CTkFrame(points_frame, fg_color=self.colors['houses'][house])
            house_frame.pack(pady=10, padx=20, fill="x")

            house_label = ctk.CTkLabel(
                house_frame,
                text=f"#{i + 1} {house} House",
                font=ctk.CTkFont(size=18, weight="bold"),
                text_color=self.colors['white']
            )
            house_label.pack(side="left", padx=20, pady=15)

            points_label = ctk.CTkLabel(
                house_frame,
                text=f"{points} Points",
                font=ctk.CTkFont(size=18, weight="bold"),
                text_color=self.colors['white']
            )
            points_label.pack(side="right", padx=20, pady=15)

    def get_total_house_points(self):
        """Get total points for all houses across all categories"""
        house_points = {'Ganga': 0, 'Yamuna': 0, 'Kaveri': 0, 'Krishna': 0}

        connection = self.get_db_connection()
        if not connection:
            return house_points

        try:
            cursor = connection.cursor()

            # Sum points from all individual event tables
            for cat in range(1, 6):
                query = f"SELECT house, SUM(points) FROM cat{cat}_individual GROUP BY house"
                cursor.execute(query)
                results = cursor.fetchall()

                for house, points in results:
                    if points:
                        house_points[house] += points

            cursor.close()
            connection.close()

        except Error as e:
            messagebox.showerror("Database Error", f"Error fetching house points: {e}")

        return house_points

    def show_enter_data(self):
        """Show enter data tab"""
        self._current_view = 'enter_data'
        self.clear_content()

        # Header
        header = ctk.CTkLabel(
            self.content_frame,
            text="Enter New Data",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=self.colors['text_dark']
        )
        header.pack(pady=20)

        # Form frame
        form_frame = ctk.CTkFrame(self.content_frame, fg_color=self.colors['white'])
        form_frame.pack(pady=20, padx=40, fill="both", expand=True)

        # Event type selection
        type_label = ctk.CTkLabel(form_frame, text="Event Type:", font=ctk.CTkFont(size=14, weight="bold"))
        type_label.pack(pady=(20, 5))

        self.event_type_var = ctk.StringVar(value="Individual")
        type_menu = ctk.CTkSegmentedButton(
            form_frame,
            values=["Individual", "Group"],
            variable=self.event_type_var,
            command=self.on_event_type_change
        )
        type_menu.pack(pady=(0, 20))

        # Form fields
        self.create_entry_form(form_frame)

    def create_entry_form(self, parent):
        """Create the data entry form"""
        # Name field (changes based on event type)
        self.name_label = ctk.CTkLabel(parent, text="Student Name:", font=ctk.CTkFont(size=14, weight="bold"))
        self.name_label.pack(pady=(10, 5))

        self.name_entry = ctk.CTkEntry(parent, width=300, height=35)
        self.name_entry.pack(pady=(0, 10))

        # Class field
        class_label = ctk.CTkLabel(parent, text="Class (1-12):", font=ctk.CTkFont(size=14, weight="bold"))
        class_label.pack(pady=(10, 5))

        self.class_entry = ctk.CTkEntry(parent, width=300, height=35)
        self.class_entry.pack(pady=(0, 10))

        # House field
        house_label = ctk.CTkLabel(parent, text="House:", font=ctk.CTkFont(size=14, weight="bold"))
        house_label.pack(pady=(10, 5))

        self.house_var = ctk.StringVar(value="Ganga")
        house_menu = ctk.CTkOptionMenu(
            parent,
            values=["Ganga", "Yamuna", "Kaveri", "Krishna"],
            variable=self.house_var,
            width=300,
            height=35
        )
        house_menu.pack(pady=(0, 10))

        # Event name field
        event_label = ctk.CTkLabel(parent, text="Event Name:", font=ctk.CTkFont(size=14, weight="bold"))
        event_label.pack(pady=(10, 5))

        self.event_entry = ctk.CTkEntry(parent, width=300, height=35)
        self.event_entry.pack(pady=(0, 10))

        # Position field
        position_label = ctk.CTkLabel(parent, text="Position Secured:", font=ctk.CTkFont(size=14, weight="bold"))
        position_label.pack(pady=(10, 5))

        self.position_var = ctk.StringVar(value="1")
        position_menu = ctk.CTkOptionMenu(
            parent,
            values=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"],
            variable=self.position_var,
            width=300,
            height=35
        )
        position_menu.pack(pady=(0, 10))

        # Submit button
        submit_btn = ctk.CTkButton(
            parent,
            text="Add Entry",
            command=self.add_entry,
            width=200,
            height=40,
            font=ctk.CTkFont(size=16, weight="bold")
        )
        submit_btn.pack(pady=20)

    def on_event_type_change(self, value):
        """Handle event type change"""
        if value == "Individual":
            self.name_label.configure(text="Student Name:")
        else:
            self.name_label.configure(text="Team Name:")

    def add_entry(self):
        """Add new entry to database"""
        try:
            # Validate inputs
            name = self.name_entry.get().strip()
            class_num = int(self.class_entry.get())
            house = self.house_var.get()
            event_name = self.event_entry.get().strip()
            position = int(self.position_var.get())
            event_type = self.event_type_var.get()

            if not all([name, event_name]) or class_num < 1 or class_num > 12 or position < 1:
                messagebox.showerror("Invalid Input", "Please fill all fields with valid data.")
                return

            # Determine category
            category = self.determine_category(class_num)
            if not category:
                messagebox.showerror("Invalid Class", "Class must be between 1 and 12.")
                return

            # Prepare data
            connection = self.get_db_connection()
            if not connection:
                return

            cursor = connection.cursor()

            if event_type == "Individual":
                points = self.get_points_for_position(position)
                table_name = f"cat{category}_individual"
                query = f"""
                INSERT INTO {table_name} (student_name, class_num, house, event_name, position, points)
                VALUES (%s, %s, %s, %s, %s, %s)
                """
                values = (name, class_num, house, event_name, position, points)
            else:
                table_name = f"cat{category}_group"
                query = f"""
                INSERT INTO {table_name} (team_name, class_num, house, event_name, position)
                VALUES (%s, %s, %s, %s, %s)
                """
                values = (name, class_num, house, event_name, position)

            cursor.execute(query, values)
            connection.commit()
            cursor.close()
            connection.close()

            # Clear form
            self.name_entry.delete(0, 'end')
            self.class_entry.delete(0, 'end')
            self.event_entry.delete(0, 'end')
            self.position_var.set("1")

            messagebox.showinfo("Success", "Entry added successfully!")

        except ValueError:
            messagebox.showerror("Invalid Input", "Class must be a number between 1-12.")
        except Error as e:
            messagebox.showerror("Database Error", f"Error adding entry: {e}")

    def show_update_data(self):
        """Show update data tab"""
        self._current_view = 'update_data'
        self.clear_content()

        # Header
        header = ctk.CTkLabel(
            self.content_frame,
            text="Update/Delete Data",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=self.colors['text_dark']
        )
        header.pack(pady=20)

        # Search frame
        search_frame = ctk.CTkFrame(self.content_frame, fg_color=self.colors['white'])
        search_frame.pack(pady=(0, 20), padx=40, fill="x")

        # Search controls
        search_label = ctk.CTkLabel(search_frame, text="Search Records:", font=ctk.CTkFont(size=16, weight="bold"))
        search_label.pack(pady=(15, 5))

        # Category and Type selection
        cat_type_frame = ctk.CTkFrame(search_frame, fg_color="transparent")
        cat_type_frame.pack(pady=5)

        ctk.CTkLabel(cat_type_frame, text="Category:", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left",
                                                                                                      padx=(0, 10))
        self.search_cat_var = ctk.StringVar(value="1")
        cat_menu = ctk.CTkOptionMenu(
            cat_type_frame,
            values=["1", "2", "3", "4", "5"],
            variable=self.search_cat_var,
            width=100
        )
        cat_menu.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(cat_type_frame, text="Event Type:", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left",
                                                                                                        padx=(0, 10))
        self.search_type_var = ctk.StringVar(value="Individual")
        type_menu = ctk.CTkOptionMenu(
            cat_type_frame,
            values=["Individual", "Group"],
            variable=self.search_type_var,
            width=120
        )
        type_menu.pack(side="left")

        # Event filter
        event_filter_frame = ctk.CTkFrame(search_frame, fg_color="transparent")
        event_filter_frame.pack(pady=5)

        ctk.CTkLabel(event_filter_frame, text="Filter by Event:", font=ctk.CTkFont(size=14, weight="bold")).pack(
            side="left", padx=(0, 10))
        self.event_filter_entry = ctk.CTkEntry(event_filter_frame, width=200,
                                               placeholder_text="Enter event name (optional)")
        self.event_filter_entry.pack(side="left", padx=(0, 20))

        # Clear filter button
        clear_filter_btn = ctk.CTkButton(
            event_filter_frame,
            text="Clear Filter",
            command=self.clear_event_filter,
            width=100,
            height=30,
            font=ctk.CTkFont(size=12)
        )
        clear_filter_btn.pack(side="left")

        # Buttons frame
        buttons_frame = ctk.CTkFrame(search_frame, fg_color="transparent")
        buttons_frame.pack(pady=15)

        # Search button
        search_btn = ctk.CTkButton(
            buttons_frame,
            text="Load Records",
            command=self.load_records,
            width=120,
            height=35
        )
        search_btn.pack(side="left", padx=10)

        # Delete all button
        delete_all_btn = ctk.CTkButton(
            buttons_frame,
            text="Delete All Data",
            command=self.delete_all_data,
            width=120,
            height=35,
            fg_color="#e74c3c",
            hover_color="#c0392b"
        )
        delete_all_btn.pack(side="left", padx=10)

        # Records display frame
        self.records_frame = ctk.CTkScrollableFrame(
            self.content_frame,
            fg_color=self.colors['light_gray'],
            height=300
        )
        self.records_frame.pack(pady=(0, 20), padx=40, fill="both", expand=True)

    def clear_event_filter(self):
        """Clear the event filter"""
        self.event_filter_entry.delete(0, 'end')
        self.load_records()

    def delete_all_data(self):
        """Delete all data from all tables"""
        result = messagebox.askyesno(
            "Confirm Delete All",
            "Are you sure you want to delete ALL data from ALL categories?\n\n"
            "This will permanently delete:\n"
            "• All Individual event records\n"
            "• All Group event records\n"
            "• From all categories (1-5)\n\n"
            "This action CANNOT be undone!"
        )

        if not result:
            return

        # Double confirmation
        confirm_result = messagebox.askyesno(
            "Final Confirmation",
            "This is your FINAL WARNING!\n\n"
            "Are you absolutely sure you want to delete ALL data?\n"
            "Type 'DELETE' in the next dialog to confirm."
        )

        if not confirm_result:
            return

        # Ask user to type DELETE
        from tkinter import simpledialog
        confirmation_text = simpledialog.askstring(
            "Type DELETE to Confirm",
            "Type 'DELETE' (in capital letters) to confirm deletion of all data:",
            parent=self.root
        )

        if confirmation_text != "DELETE":
            messagebox.showinfo("Cancelled", "Data deletion cancelled.")
            return

        try:
            connection = self.get_db_connection()
            if not connection:
                return

            cursor = connection.cursor()

            # Delete from all tables
            tables_cleared = []
            for cat in range(1, 6):
                # Clear individual table
                ind_table = f"cat{cat}_individual"
                cursor.execute(f"DELETE FROM {ind_table}")
                if cursor.rowcount > 0:
                    tables_cleared.append(f"{ind_table} ({cursor.rowcount} records)")

                # Clear group table
                grp_table = f"cat{cat}_group"
                cursor.execute(f"DELETE FROM {grp_table}")
                if cursor.rowcount > 0:
                    tables_cleared.append(f"{grp_table} ({cursor.rowcount} records)")

            connection.commit()
            cursor.close()
            connection.close()

            if tables_cleared:
                cleared_info = "\n".join(tables_cleared)
                messagebox.showinfo("Success", f"All data deleted successfully!\n\nCleared:\n{cleared_info}")
            else:
                messagebox.showinfo("No Data", "No data was found to delete.")

            # Refresh the records display
            self.load_records()

        except Error as e:
            messagebox.showerror("Database Error", f"Error deleting data: {e}")

    def load_records(self):
        """Load records based on selected category, type, and event filter"""
        # Clear existing records
        for widget in self.records_frame.winfo_children():
            widget.destroy()

        category = self.search_cat_var.get()
        event_type = self.search_type_var.get()
        event_filter = self.event_filter_entry.get().strip()

        connection = self.get_db_connection()
        if not connection:
            return

        try:
            cursor = connection.cursor()

            if event_type == "Individual":
                table_name = f"cat{category}_individual"
                base_query = f"""
                SELECT id, student_name, class_num, house, event_name, position, points, entry_date 
                FROM {table_name}
                """
            else:
                table_name = f"cat{category}_group"
                base_query = f"""
                SELECT id, team_name, class_num, house, event_name, position, entry_date 
                FROM {table_name}
                """

            # Add event filter if provided
            if event_filter:
                query = base_query + " WHERE event_name LIKE %s ORDER BY entry_date DESC"
                cursor.execute(query, (f"%{event_filter}%",))
            else:
                query = base_query + " ORDER BY entry_date DESC"
                cursor.execute(query)

            records = cursor.fetchall()

            if not records:
                filter_text = f" matching '{event_filter}'" if event_filter else ""
                no_data_label = ctk.CTkLabel(
                    self.records_frame,
                    text=f"No records found for Category {category} - {event_type} events{filter_text}",
                    font=ctk.CTkFont(size=14)
                )
                no_data_label.pack(pady=20)
            else:
                # Create header
                header_frame = ctk.CTkFrame(self.records_frame, fg_color=self.colors['primary_blue'])
                header_frame.pack(fill="x", pady=(0, 10), padx=5)

                headers = ["Name/Team", "Class", "House", "Event", "Position"]
                if event_type == "Individual":
                    headers.append("Points")
                headers.extend(["Date", "Actions"])

                for i, header in enumerate(headers):
                    header_label = ctk.CTkLabel(
                        header_frame,
                        text=header,
                        font=ctk.CTkFont(size=12, weight="bold"),
                        text_color=self.colors['white']
                    )
                    header_label.grid(row=0, column=i, padx=5, pady=8, sticky="w")

                # Display records
                for record in records:
                    self.create_record_row(record, event_type)

            cursor.close()
            connection.close()

        except Error as e:
            messagebox.showerror("Database Error", f"Error loading records: {e}")

    def create_record_row(self, record, event_type):
        """Create a row for each record with edit/delete options"""
        record_frame = ctk.CTkFrame(self.records_frame, fg_color=self.colors['white'])
        record_frame.pack(fill="x", pady=2, padx=5)

        # Extract record data
        record_id = record[0]
        name = record[1]
        class_num = record[2]
        house = record[3]
        event_name = record[4]
        position = record[5]

        if event_type == "Individual":
            points = record[6]
            entry_date = record[7]
        else:
            entry_date = record[6]

        # Display data
        data_labels = [name, str(class_num), house, event_name, str(position)]
        if event_type == "Individual":
            data_labels.append(str(points))
        data_labels.append(entry_date.strftime("%Y-%m-%d %H:%M"))

        for i, text in enumerate(data_labels):
            label = ctk.CTkLabel(
                record_frame,
                text=text,
                font=ctk.CTkFont(size=11),
                text_color=self.colors['text_dark']
            )
            label.grid(row=0, column=i, padx=5, pady=5, sticky="w")

        # Action buttons
        actions_frame = ctk.CTkFrame(record_frame, fg_color="transparent")
        actions_frame.grid(row=0, column=len(data_labels), padx=5, pady=5)

        edit_btn = ctk.CTkButton(
            actions_frame,
            text="Edit",
            command=lambda: self.edit_record(record_id, record, event_type),
            width=60,
            height=25,
            font=ctk.CTkFont(size=10)
        )
        edit_btn.pack(side="left", padx=2)

        delete_btn = ctk.CTkButton(
            actions_frame,
            text="Delete",
            command=lambda: self.delete_record(record_id, event_type),
            width=60,
            height=25,
            font=ctk.CTkFont(size=10),
            fg_color="#e74c3c",
            hover_color="#c0392b"
        )
        delete_btn.pack(side="left", padx=2)

    def edit_record(self, record_id, record, event_type):
        """Open edit dialog for a record"""
        # Create edit window
        edit_window = ctk.CTkToplevel(self.root)
        edit_window.title("Edit Record")
        edit_window.geometry("400x500")
        edit_window.resizable(False, False)

        # Center the window
        edit_window.transient(self.root)
        edit_window.grab_set()

        # Header
        header = ctk.CTkLabel(
            edit_window,
            text=f"Edit {event_type} Record",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        header.pack(pady=20)

        # Form fields
        # Name field
        name_label = ctk.CTkLabel(
            edit_window,
            text="Student Name:" if event_type == "Individual" else "Team Name:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        name_label.pack(pady=(10, 5))

        name_entry = ctk.CTkEntry(edit_window, width=300, height=35)
        name_entry.pack(pady=(0, 10))
        name_entry.insert(0, record[1])

        # Class field
        class_label = ctk.CTkLabel(edit_window, text="Class (1-12):", font=ctk.CTkFont(size=14, weight="bold"))
        class_label.pack(pady=(10, 5))

        class_entry = ctk.CTkEntry(edit_window, width=300, height=35)
        class_entry.pack(pady=(0, 10))
        class_entry.insert(0, str(record[2]))

        # House field
        house_label = ctk.CTkLabel(edit_window, text="House:", font=ctk.CTkFont(size=14, weight="bold"))
        house_label.pack(pady=(10, 5))

        house_var = ctk.StringVar(value=record[3])
        house_menu = ctk.CTkOptionMenu(
            edit_window,
            values=["Ganga", "Yamuna", "Kaveri", "Krishna"],
            variable=house_var,
            width=300,
            height=35
        )
        house_menu.pack(pady=(0, 10))

        # Event name field
        event_label = ctk.CTkLabel(edit_window, text="Event Name:", font=ctk.CTkFont(size=14, weight="bold"))
        event_label.pack(pady=(10, 5))

        event_entry = ctk.CTkEntry(edit_window, width=300, height=35)
        event_entry.pack(pady=(0, 10))
        event_entry.insert(0, record[4])

        # Position field
        position_label = ctk.CTkLabel(edit_window, text="Position Secured:", font=ctk.CTkFont(size=14, weight="bold"))
        position_label.pack(pady=(10, 5))

        position_var = ctk.StringVar(value=str(record[5]))
        position_menu = ctk.CTkOptionMenu(
            edit_window,
            values=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"],
            variable=position_var,
            width=300,
            height=35
        )
        position_menu.pack(pady=(0, 10))

        # Buttons frame
        btn_frame = ctk.CTkFrame(edit_window, fg_color="transparent")
        btn_frame.pack(pady=20)

        # Update button
        update_btn = ctk.CTkButton(
            btn_frame,
            text="Update",
            command=lambda: self.update_record(
                record_id, name_entry.get(), int(class_entry.get()),
                house_var.get(), event_entry.get(), int(position_var.get()),
                event_type, edit_window
            ),
            width=120,
            height=40
        )
        update_btn.pack(side="left", padx=10)

        # Cancel button
        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="Cancel",
            command=edit_window.destroy,
            width=120,
            height=40,
            fg_color="gray",
            hover_color="darkgray"
        )
        cancel_btn.pack(side="left", padx=10)

    def update_record(self, record_id, name, class_num, house, event_name, position, event_type, edit_window):
        """Update record in database"""
        try:
            # Validate inputs
            if not all([name.strip(), event_name.strip()]) or class_num < 1 or class_num > 12:
                messagebox.showerror("Invalid Input", "Please fill all fields with valid data.")
                return

            # Determine category from class
            category = self.determine_category(class_num)
            if not category:
                messagebox.showerror("Invalid Class", "Class must be between 1 and 12.")
                return

            connection = self.get_db_connection()
            if not connection:
                return

            cursor = connection.cursor()

            if event_type == "Individual":
                points = self.get_points_for_position(position)
                table_name = f"cat{category}_individual"
                query = f"""
                UPDATE {table_name} 
                SET student_name=%s, class_num=%s, house=%s, event_name=%s, position=%s, points=%s 
                WHERE id=%s
                """
                values = (name.strip(), class_num, house, event_name.strip(), position, points, record_id)
            else:
                table_name = f"cat{category}_group"
                query = f"""
                UPDATE {table_name} 
                SET team_name=%s, class_num=%s, house=%s, event_name=%s, position=%s 
                WHERE id=%s
                """
                values = (name.strip(), class_num, house, event_name.strip(), position, record_id)

            cursor.execute(query, values)
            connection.commit()
            cursor.close()
            connection.close()

            messagebox.showinfo("Success", "Record updated successfully!")
            edit_window.destroy()
            self.load_records()

        except ValueError:
            messagebox.showerror("Invalid Input", "Class must be a number between 1-12.")
        except Error as e:
            messagebox.showerror("Database Error", f"Error updating record: {e}")

    def delete_record(self, record_id, event_type):
        """Delete record from database"""
        result = messagebox.askyesno(
            "Confirm Delete",
            "Are you sure you want to delete this record?\nThis action cannot be undone."
        )

        if not result:
            return

        try:
            category = self.search_cat_var.get()

            connection = self.get_db_connection()
            if not connection:
                return

            cursor = connection.cursor()

            if event_type == "Individual":
                table_name = f"cat{category}_individual"
            else:
                table_name = f"cat{category}_group"

            query = f"DELETE FROM {table_name} WHERE id = %s"
            cursor.execute(query, (record_id,))
            connection.commit()
            cursor.close()
            connection.close()

            messagebox.showinfo("Success", "Record deleted successfully!")
            self.load_records()

        except Error as e:
            messagebox.showerror("Database Error", f"Error deleting record: {e}")

    def show_statistics(self):
        """Show enhanced statistics tab with graphs"""
        self._current_view = 'statistics'
        self.clear_content()

        # Header
        header = ctk.CTkLabel(
            self.content_frame,
            text="Statistics Dashboard",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=self.colors['text_dark']
        )
        header.pack(pady=20)

        # Create scrollable frame for all content
        stats_scroll = ctk.CTkScrollableFrame(
            self.content_frame,
            fg_color=self.colors['light_gray']
        )
        stats_scroll.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # 1. House Points Over Time Graph
        self.create_house_points_timeline(stats_scroll)

        # 2. Current House Standings
        self.create_house_standings_chart(stats_scroll)

        # 3. Best Performers by Category
        self.create_best_performers_chart(stats_scroll)

        # 4. Event Participation Statistics
        self.create_participation_stats(stats_scroll)

    def create_house_points_timeline(self, parent):
        """Create house points over time line graph"""
        # Section header
        timeline_header = ctk.CTkLabel(
            parent,
            text="House Points Over Time",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.colors['text_dark']
        )
        timeline_header.pack(pady=(20, 10))

        # Get timeline data
        timeline_data = self.get_house_points_timeline()

        if not timeline_data:
            no_data_label = ctk.CTkLabel(
                parent,
                text="No data available for timeline",
                font=ctk.CTkFont(size=14),
                text_color=self.colors['text_dark']
            )
            no_data_label.pack(pady=20)
            return

        # Create matplotlib figure
        fig, ax = plt.subplots(figsize=(14, 6))

        # Set colors based on current theme
        if self.is_dark_mode:
            fig.patch.set_facecolor('#2b2b2b')
            ax.set_facecolor('#2b2b2b')
            text_color = 'white'
        else:
            fig.patch.set_facecolor('white')
            ax.set_facecolor('white')
            text_color = 'black'

        # Plot lines for each house
        for house in ['Ganga', 'Yamuna', 'Kaveri', 'Krishna']:
            if house in timeline_data:
                dates = [item[0] for item in timeline_data[house]]
                points = [item[1] for item in timeline_data[house]]
                ax.plot(dates, points, marker='o', linewidth=3, markersize=6,
                        label=house, color=self.colors['houses'][house])

        ax.set_xlabel('Date and Time', color=text_color, fontsize=12, fontweight='bold')
        ax.set_ylabel('Cumulative Points', color=text_color, fontsize=12, fontweight='bold')
        ax.set_title('House Points Progression Over Time', color=text_color, fontsize=16, fontweight='bold')
        ax.legend(fontsize=11, framealpha=0.9)
        ax.grid(True, alpha=0.3, linestyle='--')

        # Format x-axis to show date:hour:minute
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))

        # Set intelligent tick spacing based on data range
        if timeline_data:
            all_dates = []
            for house_data in timeline_data.values():
                all_dates.extend([item[0] for item in house_data])

            if all_dates:
                time_span = max(all_dates) - min(all_dates)

                if time_span.days > 7:
                    ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
                    ax.xaxis.set_minor_locator(mdates.HourLocator(interval=6))
                elif time_span.days > 1:
                    ax.xaxis.set_major_locator(mdates.HourLocator(interval=6))
                    ax.xaxis.set_minor_locator(mdates.HourLocator(interval=1))
                else:
                    ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
                    ax.xaxis.set_minor_locator(mdates.MinuteLocator(interval=30))

        ax.tick_params(colors=text_color, labelsize=10)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()

        # Embed in tkinter
        canvas_frame = ctk.CTkFrame(parent, fg_color=self.colors['white'])
        canvas_frame.pack(pady=10, padx=20, fill="x")

        canvas = FigureCanvasTkAgg(fig, canvas_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    def get_house_points_timeline(self):
        """Get house points progression over time"""
        timeline_data = defaultdict(list)

        connection = self.get_db_connection()
        if not connection:
            return timeline_data

        try:
            cursor = connection.cursor()

            # Get all individual events ordered by date
            all_events = []
            for cat in range(1, 6):
                query = f"""
                SELECT house, points, entry_date 
                FROM cat{cat}_individual 
                ORDER BY entry_date ASC
                """
                cursor.execute(query)
                events = cursor.fetchall()
                all_events.extend(events)

            # Sort all events by date
            all_events.sort(key=lambda x: x[2])

            # Calculate cumulative points
            house_totals = {'Ganga': 0, 'Yamuna': 0, 'Kaveri': 0, 'Krishna': 0}

            for house, points, date in all_events:
                house_totals[house] += points
                timeline_data[house].append((date, house_totals[house]))

            cursor.close()
            connection.close()

        except Error as e:
            print(f"Error getting timeline data: {e}")

        return dict(timeline_data)

    def get_best_performers(self):
        """Get best individual performers by category"""
        performers = defaultdict(list)

        connection = self.get_db_connection()
        if not connection:
            return performers

        try:
            cursor = connection.cursor()

            for cat in range(1, 6):
                query = f"""
                SELECT student_name, house, SUM(points) as total_points, COUNT(*) as event_count
                FROM cat{cat}_individual 
                GROUP BY student_name, house 
                ORDER BY total_points DESC, event_count DESC
                LIMIT 5
                """
                cursor.execute(query)
                results = cursor.fetchall()

                for name, house, points, event_count in results:
                    performers[cat].append({
                        'name': name,
                        'house': house,
                        'points': float(points),
                        'event_count': event_count
                    })

            cursor.close()
            connection.close()

        except Error as e:
            print(f"Error getting best performers: {e}")

        return dict(performers)

    def get_participation_stats(self):
        """Get participation statistics"""
        stats = {
            'category_events': defaultdict(int),
            'house_participation': defaultdict(int)
        }

        connection = self.get_db_connection()
        if not connection:
            return stats

        try:
            cursor = connection.cursor()

            for cat in range(1, 6):
                # Count individual events
                cursor.execute(f"SELECT COUNT(*) FROM cat{cat}_individual")
                ind_count = cursor.fetchone()[0]

                # Count group events
                cursor.execute(f"SELECT COUNT(*) FROM cat{cat}_group")
                grp_count = cursor.fetchone()[0]

                stats['category_events'][cat] = ind_count + grp_count

                # Count house participations
                cursor.execute(f"SELECT house, COUNT(*) FROM cat{cat}_individual GROUP BY house")
                ind_house_counts = cursor.fetchall()

                cursor.execute(f"SELECT house, COUNT(*) FROM cat{cat}_group GROUP BY house")
                grp_house_counts = cursor.fetchall()

                for house, count in ind_house_counts:
                    stats['house_participation'][house] += count

                for house, count in grp_house_counts:
                    stats['house_participation'][house] += count

            cursor.close()
            connection.close()

        except Error as e:
            print(f"Error getting participation stats: {e}")

        return stats

    def create_house_standings_chart(self, parent):
        """Create current house standings bar chart"""
        # Section header
        standings_header = ctk.CTkLabel(
            parent,
            text="Current House Standings",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.colors['text_dark']
        )
        standings_header.pack(pady=(30, 10))

        # Get house points
        house_points = self.get_total_house_points()

        # Create matplotlib figure
        fig, ax = plt.subplots(figsize=(10, 6))

        # Set colors based on current theme
        if self.is_dark_mode:
            fig.patch.set_facecolor('#2b2b2b')
            ax.set_facecolor('#2b2b2b')
            text_color = 'white'
        else:
            fig.patch.set_facecolor('white')
            ax.set_facecolor('white')
            text_color = 'black'

        # Sort houses by points
        sorted_houses = sorted(house_points.items(), key=lambda x: x[1], reverse=True)
        houses = [item[0] for item in sorted_houses]
        points = [item[1] for item in sorted_houses]
        colors = [self.colors['houses'][house] for house in houses]

        # Create bar chart
        bars = ax.bar(houses, points, color=colors, alpha=0.8, edgecolor='black', linewidth=1)

        # Add value labels on bars
        for bar, point in zip(bars, points):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2., height + 0.5,
                    f'{point}', ha='center', va='bottom', color=text_color, fontweight='bold')

        ax.set_xlabel('Houses', color=text_color)
        ax.set_ylabel('Total Points', color=text_color)
        ax.set_title('Current House Standings', color=text_color, fontsize=14, fontweight='bold')
        ax.tick_params(colors=text_color)
        ax.grid(axis='y', alpha=0.3)

        plt.tight_layout()

        # Embed in tkinter
        canvas_frame = ctk.CTkFrame(parent, fg_color=self.colors['white'])
        canvas_frame.pack(pady=10, padx=20, fill="x")

        canvas = FigureCanvasTkAgg(fig, canvas_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    def create_best_performers_chart(self, parent):
        """Create best performers chart by category"""
        # Section header
        performers_header = ctk.CTkLabel(
            parent,
            text="Best Individual Performers by Category",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.colors['text_dark']
        )
        performers_header.pack(pady=(30, 10))

        # Get best performers data
        best_performers = self.get_best_performers()

        if not best_performers:
            no_data_label = ctk.CTkLabel(
                parent,
                text="No individual performance data available",
                font=ctk.CTkFont(size=14),
                text_color=self.colors['text_dark']
            )
            no_data_label.pack(pady=20)
            return

        # Create matplotlib figure
        fig, ax = plt.subplots(figsize=(12, 8))

        # Set colors based on current theme
        if self.is_dark_mode:
            fig.patch.set_facecolor('#2b2b2b')
            ax.set_facecolor('#2b2b2b')
            text_color = 'white'
        else:
            fig.patch.set_facecolor('white')
            ax.set_facecolor('white')
            text_color = 'black'

        # Prepare data for horizontal bar chart
        categories = []
        names = []
        points_list = []
        colors_list = []

        for cat, performers in best_performers.items():
            for performer in performers[:3]:
                categories.append(f"Cat {cat}")
                names.append(f"{performer['name']} ({performer['house']})")
                points_list.append(performer['points'])
                colors_list.append(self.colors['houses'][performer['house']])

        if categories:
            # Create horizontal bar chart
            y_pos = range(len(names))
            bars = ax.barh(y_pos, points_list, color=colors_list, alpha=0.8, edgecolor='black')

            # Add value labels
            for i, (bar, points) in enumerate(zip(bars, points_list)):
                ax.text(points + 0.1, bar.get_y() + bar.get_height() / 2,
                        f'{points}', ha='left', va='center', color=text_color, fontweight='bold')

            ax.set_yticks(y_pos)
            ax.set_yticklabels([f"{cat}\n{name}" for cat, name in zip(categories, names)])
            ax.set_xlabel('Total Points', color=text_color)
            ax.set_title('Top Individual Performers by Category', color=text_color, fontsize=14, fontweight='bold')
            ax.tick_params(colors=text_color)
            ax.grid(axis='x', alpha=0.3)

        plt.tight_layout()

        # Embed in tkinter
        canvas_frame = ctk.CTkFrame(parent, fg_color=self.colors['white'])
        canvas_frame.pack(pady=10, padx=20, fill="x")

        canvas = FigureCanvasTkAgg(fig, canvas_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    def create_participation_stats(self, parent):
        """Create event participation statistics"""
        # Section header
        participation_header = ctk.CTkLabel(
            parent,
            text="Event Participation Statistics",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.colors['text_dark']
        )
        participation_header.pack(pady=(30, 10))

        # Get participation data
        participation_data = self.get_participation_stats()

        if not participation_data:
            no_data_label = ctk.CTkLabel(
                parent,
                text="No participation data available",
                font=ctk.CTkFont(size=14),
                text_color=self.colors['text_dark']
            )
            no_data_label.pack(pady=20)
            return

        # Create subplot with 2 charts
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

        # Set colors based on current theme
        if self.is_dark_mode:
            fig.patch.set_facecolor('#2b2b2b')
            for ax in [ax1, ax2]:
                ax.set_facecolor('#2b2b2b')
            text_color = 'white'
        else:
            fig.patch.set_facecolor('white')
            for ax in [ax1, ax2]:
                ax.set_facecolor('white')
            text_color = 'black'

        # Chart 1: Events by Category
        if 'category_events' in participation_data:
            categories = list(participation_data['category_events'].keys())
            event_counts = list(participation_data['category_events'].values())

            ax1.pie(event_counts, labels=[f'Cat {cat}' for cat in categories],
                    autopct='%1.1f%%', startangle=90, colors=plt.cm.Set3.colors)
            ax1.set_title('Events Distribution by Category', color=text_color, fontweight='bold')

        # Chart 2: House Participation
        if 'house_participation' in participation_data:
            houses = list(participation_data['house_participation'].keys())
            participations = list(participation_data['house_participation'].values())
            colors = [self.colors['houses'][house] for house in houses]

            bars = ax2.bar(houses, participations, color=colors, alpha=0.8, edgecolor='black')

            # Add value labels
            for bar, participation in zip(bars, participations):
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width() / 2., height + 0.5,
                         f'{participation}', ha='center', va='bottom', color=text_color, fontweight='bold')

            ax2.set_xlabel('Houses', color=text_color)
            ax2.set_ylabel('Total Participations', color=text_color)
            ax2.set_title('House Participation Count', color=text_color, fontweight='bold')
            ax2.tick_params(colors=text_color)
            ax2.grid(axis='y', alpha=0.3)

        plt.tight_layout()

        # Embed in tkinter
        canvas_frame = ctk.CTkFrame(parent, fg_color=self.colors['white'])
        canvas_frame.pack(pady=10, padx=20, fill="x")

        canvas = FigureCanvasTkAgg(fig, canvas_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    def get_class_range(self, category):
        """Get class range for category"""
        cat_range = self.settings['category_ranges'].get(str(category))
        if cat_range:
            return f"{cat_range['min']}-{cat_range['max']}"
        return ""

    def get_category_leaders(self):
        """Get leading house in each category"""
        leaders = {}

        connection = self.get_db_connection()
        if not connection:
            return leaders

        try:
            cursor = connection.cursor()

            for cat in range(1, 6):
                query = f"""
                SELECT house, SUM(points) as total_points 
                FROM cat{cat}_individual 
                GROUP BY house 
                ORDER BY total_points DESC 
                LIMIT 1
                """
                cursor.execute(query)
                result = cursor.fetchone()

                if result:
                    leaders[cat] = (result[0], result[1])
                else:
                    leaders[cat] = (None, 0)

            cursor.close()
            connection.close()

        except Error as e:
            messagebox.showerror("Database Error", f"Error fetching statistics: {e}")

        return leaders

    def show_export_data(self):
        """Show export data tab"""
        self._current_view = 'export_data'
        self.clear_content()

        # Header
        header = ctk.CTkLabel(
            self.content_frame,
            text="Export Data",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=self.colors['text_dark']
        )
        header.pack(pady=20)

        # Export options
        export_frame = ctk.CTkFrame(self.content_frame, fg_color=self.colors['white'])
        export_frame.pack(pady=20, padx=40, fill="both", expand=True)

        # Export buttons
        export_all_btn = ctk.CTkButton(
            export_frame,
            text="Export All Data (CSV)",
            command=self.export_all_data,
            width=200,
            height=40,
            font=ctk.CTkFont(size=16, weight="bold")
        )
        export_all_btn.pack(pady=20)

        export_summary_btn = ctk.CTkButton(
            export_frame,
            text="Export House Summary (CSV)",
            command=self.export_house_summary,
            width=200,
            height=40,
            font=ctk.CTkFont(size=16, weight="bold")
        )
        export_summary_btn.pack(pady=10)

    def export_all_data(self):
        """Export all data to CSV files"""
        try:
            # Ask user to select directory
            export_dir = filedialog.askdirectory(title="Select Directory to Save CSV Files")

            if not export_dir:
                return

            connection = self.get_db_connection()
            if not connection:
                return

            cursor = connection.cursor()
            exported_files = []

            for cat in range(1, 6):
                # Export Individual events
                ind_query = f"SELECT * FROM cat{cat}_individual ORDER BY entry_date DESC"
                cursor.execute(ind_query)
                ind_data = cursor.fetchall()

                if ind_data:
                    ind_filename = f"{export_dir}/Cat{cat}_Individual.csv"
                    with open(ind_filename, 'w', newline='', encoding='utf-8') as file:
                        writer = csv.writer(file)
                        writer.writerow(
                            ['ID', 'Student Name', 'Class', 'House', 'Event Name', 'Position', 'Points', 'Entry Date'])
                        for row in ind_data:
                            writer.writerow(row)
                    exported_files.append(f"Cat{cat}_Individual.csv")

                # Export Group events
                grp_query = f"SELECT * FROM cat{cat}_group ORDER BY entry_date DESC"
                cursor.execute(grp_query)
                grp_data = cursor.fetchall()

                if grp_data:
                    grp_filename = f"{export_dir}/Cat{cat}_Group.csv"
                    with open(grp_filename, 'w', newline='', encoding='utf-8') as file:
                        writer = csv.writer(file)
                        writer.writerow(['ID', 'Team Name', 'Class', 'House', 'Event Name', 'Position', 'Entry Date'])
                        for row in grp_data:
                            writer.writerow(row)
                    exported_files.append(f"Cat{cat}_Group.csv")

            cursor.close()
            connection.close()

            if exported_files:
                files_list = "\n".join(exported_files)
                messagebox.showinfo("Success", f"Data exported successfully!\n\nFiles created:\n{files_list}")
            else:
                messagebox.showinfo("No Data", "No data found to export.")

        except Exception as e:
            messagebox.showerror("Export Error", f"Error exporting data: {e}")

    def export_house_summary(self):
        """Export house summary to CSV"""
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")],
                title="Save House Summary As"
            )

            if not file_path:
                return

            # Get house points and statistics
            house_points = self.get_total_house_points()
            category_leaders = self.get_category_leaders()

            with open(file_path, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)

                # Write total points summary
                writer.writerow(['TOTAL HOUSE POINTS'])
                writer.writerow(['House', 'Total Points'])

                # Sort houses by points
                sorted_houses = sorted(house_points.items(), key=lambda x: x[1], reverse=True)
                for house, points in sorted_houses:
                    writer.writerow([house, points])

                # Add empty row
                writer.writerow([])

                # Write category leaders
                writer.writerow(['CATEGORY LEADERS'])
                writer.writerow(['Category', 'Class Range', 'Leading House', 'Points'])

                for cat, (house, points) in category_leaders.items():
                    if house:
                        class_range = self.get_class_range(cat)
                        writer.writerow([f'Cat{cat}', class_range, house, points])

            messagebox.showinfo("Success", f"House summary exported successfully to {file_path}")

        except Exception as e:
            messagebox.showerror("Export Error", f"Error exporting summary: {e}")

    def show_settings(self):
        """Show settings tab"""
        self._current_view = 'settings'
        self.clear_content()

        # Header
        header = ctk.CTkLabel(
            self.content_frame,
            text="Application Settings",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=self.colors['text_dark']
        )
        header.pack(pady=20)

        # Create scrollable frame
        settings_scroll = ctk.CTkScrollableFrame(
            self.content_frame,
            fg_color=self.colors['light_gray']
        )
        settings_scroll.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # Points Configuration Section
        points_frame = ctk.CTkFrame(settings_scroll, fg_color=self.colors['white'])
        points_frame.pack(pady=10, padx=20, fill="x")

        points_header = ctk.CTkLabel(
            points_frame,
            text="Points Configuration",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.colors['text_dark']
        )
        points_header.pack(pady=(15, 10))

        points_info = ctk.CTkLabel(
            points_frame,
            text="Configure points awarded for each position in individual events",
            font=ctk.CTkFont(size=12),
            text_color=self.colors['text_dark']
        )
        points_info.pack(pady=(0, 15))

        # Points entries
        self.points_entries = {}
        points_grid = ctk.CTkFrame(points_frame, fg_color="transparent")
        points_grid.pack(pady=10)

        # Convert keys to integers for sorting
        points_map_items = [(int(k), v) for k, v in self.settings['points_map'].items()]

        for i, (position, points) in enumerate(sorted(points_map_items)):
            # Position label
            pos_label = ctk.CTkLabel(
                points_grid,
                text=f"Position {position}:",
                font=ctk.CTkFont(size=14, weight="bold")
            )
            pos_label.grid(row=i, column=0, padx=(20, 10), pady=10, sticky="e")

            # Points entry
            points_entry = ctk.CTkEntry(points_grid, width=100, height=35)
            points_entry.insert(0, str(points))
            points_entry.grid(row=i, column=1, padx=(0, 20), pady=10, sticky="w")
            self.points_entries[position] = points_entry

            # Points label
            ctk.CTkLabel(
                points_grid,
                text="points",
                font=ctk.CTkFont(size=14)
            ).grid(row=i, column=2, padx=(0, 20), pady=10, sticky="w")

        # Add more positions button
        add_position_btn = ctk.CTkButton(
            points_frame,
            text="Add More Position",
            command=self.add_position_points,
            width=150,
            height=35
        )
        add_position_btn.pack(pady=15)

        # Category Ranges Section
        category_frame = ctk.CTkFrame(settings_scroll, fg_color=self.colors['white'])
        category_frame.pack(pady=10, padx=20, fill="x")

        category_header = ctk.CTkLabel(
            category_frame,
            text="Category Class Ranges",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.colors['text_dark']
        )
        category_header.pack(pady=(15, 10))

        category_info = ctk.CTkLabel(
            category_frame,
            text="Configure which classes belong to each category",
            font=ctk.CTkFont(size=12),
            text_color=self.colors['text_dark']
        )
        category_info.pack(pady=(0, 15))

        # Category ranges
        self.category_entries = {}
        category_grid = ctk.CTkFrame(category_frame, fg_color="transparent")
        category_grid.pack(pady=10)

        # Header row
        ctk.CTkLabel(
            category_grid,
            text="Category",
            font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=0, column=0, padx=20, pady=10)

        ctk.CTkLabel(
            category_grid,
            text="Min Class",
            font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=0, column=1, padx=20, pady=10)

        ctk.CTkLabel(
            category_grid,
            text="Max Class",
            font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=0, column=2, padx=20, pady=10)

        ctk.CTkLabel(
            category_grid,
            text="Range",
            font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=0, column=3, padx=20, pady=10)

        # Category entries
        for cat in range(1, 6):
            cat_ranges = self.settings['category_ranges'][str(cat)]

            # Category label
            ctk.CTkLabel(
                category_grid,
                text=f"Category {cat}",
                font=ctk.CTkFont(size=14)
            ).grid(row=cat, column=0, padx=20, pady=10)

            # Min class entry
            min_entry = ctk.CTkEntry(category_grid, width=80, height=35)
            min_entry.insert(0, str(cat_ranges['min']))
            min_entry.grid(row=cat, column=1, padx=20, pady=10)

            # Max class entry
            max_entry = ctk.CTkEntry(category_grid, width=80, height=35)
            max_entry.insert(0, str(cat_ranges['max']))
            max_entry.grid(row=cat, column=2, padx=20, pady=10)

            # Range display
            range_label = ctk.CTkLabel(
                category_grid,
                text=f"Classes {cat_ranges['min']}-{cat_ranges['max']}",
                font=ctk.CTkFont(size=14)
            )
            range_label.grid(row=cat, column=3, padx=20, pady=10)

            self.category_entries[cat] = {
                'min': min_entry,
                'max': max_entry,
                'range_label': range_label
            }

            # Update range label on entry change
            min_entry.bind('<KeyRelease>', lambda e, c=cat: self.update_range_label(c))
            max_entry.bind('<KeyRelease>', lambda e, c=cat: self.update_range_label(c))

        # Save button
        save_btn = ctk.CTkButton(
            settings_scroll,
            text="Save Settings",
            command=self.save_settings_from_ui,
            width=200,
            height=45,
            font=ctk.CTkFont(size=16, weight="bold")
        )
        save_btn.pack(pady=30)

        # Reset to defaults button
        reset_btn = ctk.CTkButton(
            settings_scroll,
            text="Reset to Defaults",
            command=self.reset_settings,
            width=200,
            height=40,
            fg_color="gray",
            hover_color="darkgray"
        )
        reset_btn.pack(pady=(0, 20))

    def add_position_points(self):
        """Add entry for additional position points"""
        # Find the next position number
        current_positions = list(self.points_entries.keys())
        next_position = max(current_positions) + 1 if current_positions else 1

        # Show dialog to add new position
        dialog = ctk.CTkInputDialog(
            text=f"Enter points for position {next_position}:",
            title="Add Position Points"
        )
        points_value = dialog.get_input()

        if points_value:
            try:
                points = int(points_value)
                self.settings['points_map'][str(next_position)] = points
                self.save_settings(self.settings)
                messagebox.showinfo("Success",
                                    f"Added position {next_position} with {points} points.\nReload Settings tab to see changes.")
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter a valid number.")

    def update_range_label(self, category):
        """Update the range label when min/max values change"""
        try:
            min_val = self.category_entries[category]['min'].get()
            max_val = self.category_entries[category]['max'].get()

            if min_val and max_val:
                self.category_entries[category]['range_label'].configure(
                    text=f"Classes {min_val}-{max_val}"
                )
        except:
            pass

    def save_settings_from_ui(self):
        """Save settings from UI inputs"""
        try:
            # Validate and save points configuration
            new_points_map = {}
            for position, entry in self.points_entries.items():
                points = int(entry.get())
                if points < 0:
                    raise ValueError("Points cannot be negative")
                new_points_map[str(position)] = points

            # Validate and save category ranges
            new_category_ranges = {}
            for cat, entries in self.category_entries.items():
                min_class = int(entries['min'].get())
                max_class = int(entries['max'].get())

                if min_class < 1 or max_class > 12:
                    raise ValueError("Classes must be between 1 and 12")
                if min_class > max_class:
                    raise ValueError(f"Category {cat}: Min class cannot be greater than max class")

                new_category_ranges[str(cat)] = {
                    'min': min_class,
                    'max': max_class
                }

            # Check for overlapping ranges
            for cat1 in new_category_ranges:
                for cat2 in new_category_ranges:
                    if cat1 != cat2:
                        range1 = new_category_ranges[cat1]
                        range2 = new_category_ranges[cat2]

                        if not (range1['max'] < range2['min'] or range1['min'] > range2['max']):
                            raise ValueError(f"Category {cat1} and Category {cat2} have overlapping class ranges")

            # Check if category ranges or points changed
            ranges_changed = self.settings['category_ranges'] != new_category_ranges
            points_changed = self.settings['points_map'] != new_points_map

            # Save settings
            self.settings['points_map'] = new_points_map
            self.settings['category_ranges'] = new_category_ranges

            if self.save_settings(self.settings):
                migration_needed = False
                recalculation_needed = False

                # If category ranges changed, offer to migrate data
                if ranges_changed:
                    result = messagebox.askyesno(
                        "Migrate Existing Data?",
                        "Category ranges have changed!\n\n"
                        "Would you like to migrate existing data to match the new category ranges?\n\n"
                        "This will move records between category tables based on their class numbers.\n"
                        "Recommended: YES"
                    )

                    if result:
                        migration_needed = True
                    else:
                        messagebox.showwarning(
                            "Data Not Migrated",
                            "Settings saved, but existing data was NOT migrated.\n\n"
                            "Records may be in incorrect categories until manually updated."
                        )

                # If points changed, offer options
                if points_changed:
                    # Create custom dialog for points recalculation
                    dialog = ctk.CTkToplevel(self.root)
                    dialog.title("Points Configuration Changed")
                    dialog.geometry("500x300")
                    dialog.transient(self.root)
                    dialog.grab_set()

                    # Center dialog
                    dialog.update_idletasks()
                    x = (dialog.winfo_screenwidth() // 2) - (500 // 2)
                    y = (dialog.winfo_screenheight() // 2) - (300 // 2)
                    dialog.geometry(f"500x300+{x}+{y}")

                    # Header
                    header = ctk.CTkLabel(
                        dialog,
                        text="Points Configuration Changed",
                        font=ctk.CTkFont(size=18, weight="bold")
                    )
                    header.pack(pady=20)

                    # Message
                    message = ctk.CTkLabel(
                        dialog,
                        text="How would you like to handle existing records?",
                        font=ctk.CTkFont(size=14),
                        wraplength=450
                    )
                    message.pack(pady=10)

                    # Options frame
                    options_frame = ctk.CTkFrame(dialog, fg_color="transparent")
                    options_frame.pack(pady=20, padx=20, fill="both", expand=True)

                    user_choice = {"value": None}

                    def choose_recalculate():
                        user_choice["value"] = "recalculate"
                        dialog.destroy()

                    def choose_keep():
                        user_choice["value"] = "keep"
                        dialog.destroy()

                    # Recalculate button
                    recalc_btn = ctk.CTkButton(
                        options_frame,
                        text="Recalculate All Points\n(Update existing records with new values)",
                        command=choose_recalculate,
                        width=400,
                        height=60,
                        font=ctk.CTkFont(size=14, weight="bold")
                    )
                    recalc_btn.pack(pady=10)

                    # Keep button
                    keep_btn = ctk.CTkButton(
                        options_frame,
                        text="Keep Historical Points\n(Preserve old values, apply new points to future entries)",
                        command=choose_keep,
                        width=400,
                        height=60,
                        font=ctk.CTkFont(size=14, weight="bold"),
                        fg_color="gray",
                        hover_color="darkgray"
                    )
                    keep_btn.pack(pady=10)

                    # Wait for user choice
                    self.root.wait_window(dialog)

                    if user_choice["value"] == "recalculate":
                        recalculation_needed = True
                    elif user_choice["value"] == "keep":
                        messagebox.showinfo(
                            "Historical Points Preserved",
                            "Existing records will keep their current point values.\n\n"
                            "New point values will only apply to future entries."
                        )

                # Perform operations in correct order
                if migration_needed:
                    self.migrate_data_to_new_categories()

                if recalculation_needed:
                    self.recalculate_all_points()

                if not ranges_changed and not points_changed:
                    messagebox.showinfo("Success", "Settings saved successfully!")

        except ValueError as e:
            messagebox.showerror("Invalid Input", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")

    def migrate_data_to_new_categories(self):
        """Migrate existing data to match new category ranges"""
        try:
            connection = self.get_db_connection()
            if not connection:
                return

            cursor = connection.cursor()

            migration_log = []
            total_migrated = 0

            # Process both individual and group events
            for event_type in ['individual', 'group']:
                for source_cat in range(1, 6):
                    source_table = f"cat{source_cat}_{event_type}"

                    # Get all records from this table
                    cursor.execute(f"SELECT * FROM {source_table}")
                    records = cursor.fetchall()

                    if not records:
                        continue

                    # Get column names
                    cursor.execute(f"DESCRIBE {source_table}")
                    columns = [col[0] for col in cursor.fetchall()]

                    records_to_move = []

                    for record in records:
                        record_dict = dict(zip(columns, record))
                        class_num = record_dict['class_num']

                        # Determine correct category for this class
                        correct_cat = self.determine_category(class_num)

                        if correct_cat and correct_cat != source_cat:
                            records_to_move.append((record_dict, correct_cat))

                    # Move records to correct categories
                    for record_dict, target_cat in records_to_move:
                        target_table = f"cat{target_cat}_{event_type}"

                        # Prepare insert data (exclude id and entry_date, let DB generate new ones)
                        if event_type == 'individual':
                            insert_cols = ['student_name', 'class_num', 'house', 'event_name', 'position', 'points']
                            values = (
                                record_dict['student_name'],
                                record_dict['class_num'],
                                record_dict['house'],
                                record_dict['event_name'],
                                record_dict['position'],
                                record_dict['points']
                            )
                        else:  # group
                            insert_cols = ['team_name', 'class_num', 'house', 'event_name', 'position']
                            values = (
                                record_dict['team_name'],
                                record_dict['class_num'],
                                record_dict['house'],
                                record_dict['event_name'],
                                record_dict['position']
                            )

                        # Insert into target table
                        placeholders = ', '.join(['%s'] * len(values))
                        insert_query = f"INSERT INTO {target_table} ({', '.join(insert_cols)}) VALUES ({placeholders})"
                        cursor.execute(insert_query, values)

                        # Delete from source table
                        cursor.execute(f"DELETE FROM {source_table} WHERE id = %s", (record_dict['id'],))

                        total_migrated += 1

                        name = record_dict.get('student_name') or record_dict.get('team_name')
                        migration_log.append(
                            f"Moved: {name} (Class {record_dict['class_num']}) from Cat{source_cat} to Cat{target_cat}"
                        )

            connection.commit()
            cursor.close()
            connection.close()

            if total_migrated > 0:
                log_text = "\n".join(migration_log[:20])  # Show first 20
                if len(migration_log) > 20:
                    log_text += f"\n... and {len(migration_log) - 20} more"

                messagebox.showinfo(
                    "Migration Complete",
                    f"Successfully migrated {total_migrated} records!\n\n"
                    f"Sample migrations:\n{log_text}"
                )
            else:
                messagebox.showinfo(
                    "No Migration Needed",
                    "All records are already in the correct categories."
                )

        except Error as e:
            messagebox.showerror("Migration Error", f"Error migrating data: {e}")
            if connection:
                connection.rollback()
    def reset_settings(self):
        """Reset settings to defaults"""
        result = messagebox.askyesno(
            "Confirm Reset",
            "Are you sure you want to reset all settings to default values?"
        )

        if result:
            default_settings = {
                'points_map': {'1': 5, '2': 3, '3': 1},
                'category_ranges': {
                    '1': {'min': 1, 'max': 2},
                    '2': {'min': 3, 'max': 4},
                    '3': {'min': 5, 'max': 7},
                    '4': {'min': 8, 'max': 10},
                    '5': {'min': 11, 'max': 12}
                }
            }

            self.settings = default_settings
            self.save_settings(default_settings)
            messagebox.showinfo("Success", "Settings reset to defaults!")
            self.show_settings()

    def start_auto_backup(self):
        """Start automatic CSV backup and GitHub upload in background threads"""

        # Thread 1: Local CSV Export
        def run_csv_backup():
            try:
                exporter = MySQLDesktopExporter(self.db_config, 'Sameeksha_CSV_Data')
                exporter.run_periodic(interval_minutes=15)
            except Exception as e:
                print(f"Backup error: {e}")

        # Thread 2: GitHub Upload
        def run_github_upload():
            try:
                # GitHub configuration
                github_config = {
                    'github_token': '************************************',
                    'username': '***************',
                    'repo_name': '************',
                    'branch': 'main',
                    'interval_minutes': 25
                }

                uploader = GitHubCSVUploader(**github_config)
                uploader.run_periodic()
            except Exception as e:
                print(f"GitHub upload error: {e}")

        # Start both threads
        backup_thread = threading.Thread(target=run_csv_backup, daemon=True)
        github_thread = threading.Thread(target=run_github_upload, daemon=True)

        backup_thread.start()
        github_thread.start()

        print("✅ Automatic CSV backup started (every 15 minutes)")
        print("✅ Automatic GitHub upload started (every 25 minutes)")

    def run(self):
        """Run the application"""
        self.root.mainloop()


if __name__ == "__main__":
    app = FestManagementSystem()
    app.run()