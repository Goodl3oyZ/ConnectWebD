import sqlite3
import csv
import json
import os
from typing import List, Dict, Any, Tuple, Optional

DB_FILE = 'company.db'
CSV_WORKER = 'worker.csv'
CSV_BONUS = 'bonus.csv'
CSV_TITLE = 'title.csv'

class DatabaseConnection:
    """
    Database Manager and Query Runner for Company Database.
    Automatically populates tables from CSV files (worker.csv, bonus.csv, title.csv).
    """

    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path

    def get_connection(self) -> sqlite3.Connection:
        """Establishes and returns a connection to SQLite database."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_db(self, force_reset: bool = True) -> Dict[str, int]:
        """
        Creates schema and populates tables from CSV files.
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        if force_reset:
            cursor.execute("DROP TABLE IF EXISTS Bonus;")
            cursor.execute("DROP TABLE IF EXISTS Title;")
            cursor.execute("DROP TABLE IF EXISTS Worker;")

        # Create Worker table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Worker (
                WORKER_ID INTEGER PRIMARY KEY,
                FIRST_NAME TEXT NOT NULL,
                LAST_NAME TEXT NOT NULL,
                SALARY INTEGER NOT NULL,
                JOINING_DATE DATETIME NOT NULL,
                DEPARTMENT TEXT NOT NULL
            );
        """)

        # Create Bonus table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Bonus (
                WORKER_REF_ID INTEGER NOT NULL,
                BONUS_AMOUNT INTEGER NOT NULL,
                BONUS_DATE DATETIME NOT NULL,
                FOREIGN KEY(WORKER_REF_ID) REFERENCES Worker(WORKER_ID) ON DELETE CASCADE
            );
        """)

        # Create Title table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Title (
                WORKER_REF_ID INTEGER NOT NULL,
                WORKER_TITLE TEXT NOT NULL,
                AFFECTED_FROM DATETIME NOT NULL,
                FOREIGN KEY(WORKER_REF_ID) REFERENCES Worker(WORKER_ID) ON DELETE CASCADE
            );
        """)

        worker_count = 0
        bonus_count = 0
        title_count = 0

        # Load Worker.csv
        if os.path.exists(CSV_WORKER):
            with open(CSV_WORKER, mode='r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row and row.get('WORKER_ID'):
                        cursor.execute("""
                            INSERT INTO Worker (WORKER_ID, FIRST_NAME, LAST_NAME, SALARY, JOINING_DATE, DEPARTMENT)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            int(row['WORKER_ID'].strip('" ')),
                            row['FIRST_NAME'].strip('" '),
                            row['LAST_NAME'].strip('" '),
                            int(row['SALARY'].strip('" ')),
                            row['JOINING_DATE'].strip('" '),
                            row['DEPARTMENT'].strip('" ')
                        ))
                        worker_count += 1

        # Load Bonus.csv
        if os.path.exists(CSV_BONUS):
            with open(CSV_BONUS, mode='r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row and row.get('WORKER_REF_ID'):
                        cursor.execute("""
                            INSERT INTO Bonus (WORKER_REF_ID, BONUS_AMOUNT, BONUS_DATE)
                            VALUES (?, ?, ?)
                        """, (
                            int(row['WORKER_REF_ID'].strip('" ')),
                            int(row['BONUS_AMOUNT'].strip('" ')),
                            row['BONUS_DATE'].strip('" ')
                        ))
                        bonus_count += 1

        # Load Title.csv
        if os.path.exists(CSV_TITLE):
            with open(CSV_TITLE, mode='r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row and row.get('WORKER_REF_ID'):
                        cursor.execute("""
                            INSERT INTO Title (WORKER_REF_ID, WORKER_TITLE, AFFECTED_FROM)
                            VALUES (?, ?, ?)
                        """, (
                            int(row['WORKER_REF_ID'].strip('" ')),
                            row['WORKER_TITLE'].strip('" '),
                            row['AFFECTED_FROM'].strip('" ')
                        ))
                        title_count += 1

        conn.commit()
        conn.close()
        return {"Worker": worker_count, "Bonus": bonus_count, "Title": title_count}

    def execute_query(self, query: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        """
        Executes a SQL query and returns results as a list of dicts.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                results = [dict(zip(columns, row)) for row in rows]
            else:
                conn.commit()
                results = [{"affected_rows": cursor.rowcount}]
            return results
        finally:
            conn.close()

    def get_preset_queries(self) -> Dict[str, Dict[str, str]]:
        """
        Returns the 6 SQL queries required for the SQL Test.
        """
        return {
            "Q1": {
                "title": "เงินเดือนเฉลี่ยของแต่ละแผนก (Average Salary per Department)",
                "description": "Calculates the average salary for each department.",
                "sql": """
SELECT 
    DEPARTMENT, 
    ROUND(AVG(SALARY), 2) AS AVG_SALARY
FROM Worker
GROUP BY DEPARTMENT
ORDER BY AVG_SALARY DESC;
                """.strip()
            },
            "Q2": {
                "title": "จำนวนพนักงานในแต่ละแผนก (Worker Count per Department)",
                "description": "Counts total workers in each department sorted descending.",
                "sql": """
SELECT 
    DEPARTMENT, 
    COUNT(*) AS WORKER_COUNT
FROM Worker
GROUP BY DEPARTMENT
ORDER BY WORKER_COUNT DESC;
                """.strip()
            },
            "Q3": {
                "title": "พนักงานที่มีเงินเดือนเท่ากัน (Workers with Matching Salaries)",
                "description": "Identifies employees who earn identical salaries.",
                "sql": """
SELECT 
    SALARY, 
    GROUP_CONCAT(FIRST_NAME || ' ' || LAST_NAME, ', ') AS WORKERS, 
    COUNT(*) AS WORKER_COUNT
FROM Worker
GROUP BY SALARY
HAVING COUNT(*) > 1
ORDER BY SALARY DESC;
                """.strip()
            },
            "Q4": {
                "title": "แผนกที่มีการจ่ายโบนัสเยอะที่สุด (Department Paying Highest Total Bonus)",
                "description": "Finds the department that distributed the highest total bonus amount.",
                "sql": """
SELECT 
    W.DEPARTMENT, 
    SUM(B.BONUS_AMOUNT) AS TOTAL_BONUS
FROM Worker W
JOIN Bonus B ON W.WORKER_ID = B.WORKER_REF_ID
GROUP BY W.DEPARTMENT
ORDER BY TOTAL_BONUS DESC
LIMIT 1;
                """.strip()
            },
            "Q5": {
                "title": "พนักงานที่เงินเดือนรวมกับโบนัสเยอะที่สุดในแต่ละแผนก (Top Earner per Department)",
                "description": "Finds the employee with highest combined income (Salary + Bonus) in each department.",
                "sql": """
WITH WorkerEarnings AS (
    SELECT 
        W.WORKER_ID,
        W.FIRST_NAME,
        W.LAST_NAME,
        W.DEPARTMENT,
        W.SALARY,
        COALESCE(SUM(B.BONUS_AMOUNT), 0) AS TOTAL_BONUS,
        (W.SALARY + COALESCE(SUM(B.BONUS_AMOUNT), 0)) AS TOTAL_EARNINGS
    FROM Worker W
    LEFT JOIN Bonus B ON W.WORKER_ID = B.WORKER_REF_ID
    GROUP BY W.WORKER_ID, W.FIRST_NAME, W.LAST_NAME, W.DEPARTMENT, W.SALARY
),
RankedEarnings AS (
    SELECT 
        DEPARTMENT,
        WORKER_ID,
        FIRST_NAME || ' ' || LAST_NAME AS FULL_NAME,
        SALARY,
        TOTAL_BONUS,
        TOTAL_EARNINGS,
        DENSE_RANK() OVER (PARTITION BY DEPARTMENT ORDER BY TOTAL_EARNINGS DESC) as rnk
    FROM WorkerEarnings
)
SELECT DEPARTMENT, WORKER_ID, FULL_NAME, SALARY, TOTAL_BONUS, TOTAL_EARNINGS
FROM RankedEarnings
WHERE rnk = 1
ORDER BY DEPARTMENT;
                """.strip()
            },
            "Q6": {
                "title": "ตำแหน่งที่เงินเดือนรวมกันเยอะที่สุดในแต่ละแผนก (Top Title Salary per Department)",
                "description": "Finds the job title with the highest combined total salary in each department (defaults missing titles to 'Executive').",
                "sql": """
WITH WorkerWithTitle AS (
    SELECT 
        W.WORKER_ID,
        W.DEPARTMENT,
        W.SALARY,
        COALESCE(T.WORKER_TITLE, 'Executive') AS TITLE
    FROM Worker W
    LEFT JOIN Title T ON W.WORKER_ID = T.WORKER_REF_ID
),
TitleSalaryPerDept AS (
    SELECT 
        DEPARTMENT,
        TITLE,
        SUM(SALARY) AS TOTAL_SALARY
    FROM WorkerWithTitle
    GROUP BY DEPARTMENT, TITLE
),
RankedTitleSalary AS (
    SELECT 
        DEPARTMENT,
        TITLE,
        TOTAL_SALARY,
        DENSE_RANK() OVER (PARTITION BY DEPARTMENT ORDER BY TOTAL_SALARY DESC) as rnk
    FROM TitleSalaryPerDept
)
SELECT DEPARTMENT, TITLE, TOTAL_SALARY
FROM RankedTitleSalary
WHERE rnk = 1
ORDER BY DEPARTMENT;
                """.strip()
            }
        }

    def run_preset_queries(self) -> Dict[str, Any]:
        """
        Executes all preset test queries and returns formatted results.
        """
        presets = self.get_preset_queries()
        results = {}
        for key, info in presets.items():
            query_res = self.execute_query(info["sql"])
            results[key] = {
                "title": info["title"],
                "description": info["description"],
                "sql": info["sql"],
                "data": query_res
            }
        return results

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Company Database Connection & Query Test Tool")
    parser.add_argument("--init", action="store_true", help="Initialize or reset company database from CSV files")
    parser.add_argument("--query", type=str, help="Execute a custom SQL query")
    parser.add_argument("--run-presets", action="store_true", help="Run all 6 assessment test queries")
    args = parser.parse_args()

    db = DatabaseConnection()

    if args.init or not os.path.exists(DB_FILE):
        counts = db.init_db()
        print(f"Database initialized: {counts}")

    if args.run_presets:
        print("=== RUNNING PRESET ASSESSMENT QUERIES ===")
        results = db.run_preset_queries()
        for q_id, res in results.items():
            print(f"\n[{q_id}] {res['title']}")
            print("-" * 50)
            for row in res["data"]:
                print(row)

    if args.query:
        print(f"=== EXECUTING QUERY: {args.query} ===")
        res = db.execute_query(args.query)
        print(json.dumps(res, indent=2))
