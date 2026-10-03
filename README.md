# Company Database Connection & Query Test Suite

This project provides a database setup, SQLite connection manager, automated test suite, interactive query playground, and executive dashboard for the `SQL Test` assessment based on `worker.csv`, `bonus.csv`, and `title.csv`.

---

## 🚀 Quick Start

### 1. Run Interactive Web Dashboard & SQL Workbench
Launch the web-based interactive query runner and executive dashboard:
```bash
python server.py
```
Open **`http://localhost:8080`** in your browser to:
- View executive KPI cards & department breakdown charts.
- Interactively test preset queries (Q1 - Q6) or custom SQL queries.
- Inspect raw dataset tables (`Worker`, `Bonus`, `Title`).

### 2. Run Database Connection CLI
Execute query tests or custom SQL directly from command line:
```bash
# Initialize SQLite database (company.db) and run all preset queries
python db_connection.py --init --run-presets

# Execute a custom SQL query
python db_connection.py --query "SELECT * FROM Worker WHERE SALARY > 100000"
```

### 3. Run Automated Unit Tests
Run unit tests verifying table structure, foreign keys, and query accuracy:
```bash
python test_db_connection.py
```

---

## 📊 SQL Query Solutions (Section A)

### Q1: แสดงเงินเดือนเฉลี่ยของแต่ละแผนก (Average Salary per Department)
```sql
SELECT 
    DEPARTMENT, 
    ROUND(AVG(SALARY), 2) AS AVG_SALARY
FROM Worker
GROUP BY DEPARTMENT
ORDER BY AVG_SALARY DESC;
```
| DEPARTMENT | AVG_SALARY |
| :--- | :--- |
| Admin | 306,250.00 |
| HR | 233,333.33 |
| Account | 105,000.00 |

---

### Q2: แสดงจำนวนพนักงานในแต่ละแผนก โดยให้เรียงจากมากไปน้อย (Worker Count per Department)
```sql
SELECT 
    DEPARTMENT, 
    COUNT(*) AS WORKER_COUNT
FROM Worker
GROUP BY DEPARTMENT
ORDER BY WORKER_COUNT DESC;
```
| DEPARTMENT | WORKER_COUNT |
| :--- | :--- |
| Admin | 8 |
| Account | 5 |
| HR | 3 |

---

### Q3: แสดงพนักงานที่มีเงินเดือนเท่ากัน (Workers with Matching Salaries)
```sql
SELECT 
    SALARY, 
    GROUP_CONCAT(FIRST_NAME || ' ' || LAST_NAME, ', ') AS WORKERS, 
    COUNT(*) AS WORKER_COUNT
FROM Worker
GROUP BY SALARY
HAVING COUNT(*) > 1
ORDER BY SALARY DESC;
```
| SALARY | WORKERS | WORKER_COUNT |
| :--- | :--- | :--- |
| 500,000 | Amitabh Singh, Vivek Bhati, Ami Singh, Viv Bha | 4 |
| 300,000 | Vishal Singhal, Vi Sing | 2 |
| 200,000 | Vipul Diwan, Vipul Diwan | 2 |
| 90,000 | Geetika Chauhan, Mo Ar | 2 |
| 80,000 | Niharika Verma, Ni Ver | 2 |
| 75,000 | Satish Kumar, Satish Kumar | 2 |

---

### Q4: แสดงแผนกที่มีการจ่ายโบนัสเยอะที่สุด (Department Paying Highest Total Bonus)
```sql
SELECT 
    W.DEPARTMENT, 
    SUM(B.BONUS_AMOUNT) AS TOTAL_BONUS
FROM Worker W
JOIN Bonus B ON W.WORKER_ID = B.WORKER_REF_ID
GROUP BY W.DEPARTMENT
ORDER BY TOTAL_BONUS DESC
LIMIT 1;
```
| DEPARTMENT | TOTAL_BONUS |
| :--- | :--- |
| HR | 13,500 |

---

### Q5: แสดงชื่อพนักงานที่เงินเดือนรวมกับโบนัสเยอะที่สุดในแต่ละแผนก (Top Earner [Salary + Bonus] per Department)
```sql
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
```
| DEPARTMENT | WORKER_ID | FULL_NAME | SALARY | TOTAL_BONUS | TOTAL_EARNINGS |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Account | 6 | Vipul Diwan | 200,000 | 0 | 200,000 |
| Admin | 4 | Amitabh Singh | 500,000 | 0 | 500,000 |
| Admin | 5 | Vivek Bhati | 500,000 | 0 | 500,000 |
| Admin | 12 | Ami Singh | 500,000 | 0 | 500,000 |
| Admin | 13 | Viv Bha | 500,000 | 0 | 500,000 |
| HR | 3 | Vishal Singhal | 300,000 | 4,000 | 304,000 |

---

### Q6: แสดงชื่อตำแหน่งที่เงินเดือนรวมกันเยอะที่สุดในแต่ละแผนก (Title with Highest Combined Salary per Department)
*Note: If an employee has no specified title, they are treated as 'Executive'.*
```sql
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
```
| DEPARTMENT | TITLE | TOTAL_SALARY |
| :--- | :--- | :--- |
| Account | Executive | 325,000 |
| Admin | Executive | 1,450,000 |
| HR | Executive | 300,000 |
| HR | Lead | 300,000 |

---

## 📁 File Structure
- **`db_connection.py`**: SQLite database connection manager, table initializer, query runner, and CLI.
- **`test_db_connection.py`**: `unittest` verification suite for database structure and queries.
- **`server.py`**: REST API server for web workbench.
- **`index.html`**: Executive dashboard & web SQL query playground.
- **`company.db`**: Local SQLite database generated automatically from CSV datasets.
