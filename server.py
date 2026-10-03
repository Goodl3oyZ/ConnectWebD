import http.server
import socketserver
import json
import urllib.parse
import time
import os
from db_connection import DatabaseConnection, DB_FILE

HOST = os.environ.get('HOST', '0.0.0.0')
PORT = int(os.environ.get('PORT', 8085))
db = DatabaseConnection()

# Ensure database exists
if not os.path.exists(DB_FILE):
    db.init_db()

class DBRequestHandler(http.server.SimpleHTTPRequestHandler):

    def log_message(self, format, *args):
        # Clean logging
        print(f"[{time.strftime('%H:%M:%S')}] {args[0]}")

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == '/api/status':
            conn = db.get_connection()
            cur = conn.cursor()
            workers = cur.execute("SELECT COUNT(*) FROM Worker").fetchone()[0]
            bonuses = cur.execute("SELECT COUNT(*) FROM Bonus").fetchone()[0]
            titles = cur.execute("SELECT COUNT(*) FROM Title").fetchone()[0]
            conn.close()
            self.send_json({
                "status": "online",
                "database": DB_FILE,
                "counts": {"Worker": workers, "Bonus": bonuses, "Title": titles}
            })

        elif parsed.path == '/api/preset-queries':
            self.send_json(db.get_preset_queries())

        elif parsed.path == '/api/dashboard-summary':
            # Compute Executive KPIs & Chart data
            workers_count = db.execute_query("SELECT COUNT(*) AS c FROM Worker")[0]['c']
            avg_salary = db.execute_query("SELECT ROUND(AVG(SALARY), 2) AS c FROM Worker")[0]['c']
            total_bonus = db.execute_query("SELECT SUM(BONUS_AMOUNT) AS c FROM Bonus")[0]['c'] or 0
            dept_summary = db.execute_query("""
                SELECT 
                    DEPARTMENT, 
                    COUNT(*) AS WORKER_COUNT,
                    ROUND(AVG(SALARY), 2) AS AVG_SALARY,
                    SUM(SALARY) AS TOTAL_SALARY
                FROM Worker
                GROUP BY DEPARTMENT
                ORDER BY WORKER_COUNT DESC
            """)
            dept_bonus = db.execute_query("""
                SELECT 
                    W.DEPARTMENT, 
                    COALESCE(SUM(B.BONUS_AMOUNT), 0) AS TOTAL_BONUS,
                    COUNT(DISTINCT B.WORKER_REF_ID) AS RECIPIENT_COUNT,
                    ROUND(COALESCE(SUM(B.BONUS_AMOUNT), 0) * 1.0 / COUNT(DISTINCT W.WORKER_ID), 2) AS BONUS_PER_EMPLOYEE
                FROM Worker W
                LEFT JOIN Bonus B ON W.WORKER_ID = B.WORKER_REF_ID
                GROUP BY W.DEPARTMENT
                ORDER BY TOTAL_BONUS DESC
            """)
            
            top_earners = db.execute_query("""
                WITH WorkerEarnings AS (
                    SELECT 
                        W.WORKER_ID,
                        W.FIRST_NAME || ' ' || W.LAST_NAME AS FULL_NAME,
                        W.DEPARTMENT,
                        COALESCE(T.WORKER_TITLE, 'Executive') AS TITLE,
                        W.SALARY,
                        COALESCE(SUM(B.BONUS_AMOUNT), 0) AS TOTAL_BONUS,
                        (W.SALARY + COALESCE(SUM(B.BONUS_AMOUNT), 0)) AS TOTAL_EARNINGS
                    FROM Worker W
                    LEFT JOIN Title T ON W.WORKER_ID = T.WORKER_REF_ID
                    LEFT JOIN Bonus B ON W.WORKER_ID = B.WORKER_REF_ID
                    GROUP BY W.WORKER_ID, FULL_NAME, W.DEPARTMENT, TITLE, W.SALARY
                )
                SELECT * FROM WorkerEarnings ORDER BY TOTAL_EARNINGS DESC
            """)

            self.send_json({
                "total_workers": workers_count,
                "avg_salary": avg_salary,
                "total_bonus": total_bonus,
                "dept_summary": dept_summary,
                "dept_bonus": dept_bonus,
                "top_earners": top_earners
            })

        elif parsed.path == '/api/employees':
            employees = db.execute_query("""
                SELECT 
                    W.WORKER_ID,
                    W.FIRST_NAME || ' ' || W.LAST_NAME AS FULL_NAME,
                    W.FIRST_NAME,
                    W.LAST_NAME,
                    W.DEPARTMENT,
                    COALESCE(T.WORKER_TITLE, 'Executive') AS TITLE,
                    W.SALARY,
                    COALESCE(SUM(B.BONUS_AMOUNT), 0) AS TOTAL_BONUS,
                    (W.SALARY + COALESCE(SUM(B.BONUS_AMOUNT), 0)) AS TOTAL_EARNINGS,
                    W.JOINING_DATE,
                    CASE WHEN T.WORKER_TITLE IS NULL THEN 1 ELSE 0 END AS IS_TITLE_DEFAULTED,
                    COUNT(B.BONUS_AMOUNT) AS BONUS_COUNT
                FROM Worker W
                LEFT JOIN Title T ON W.WORKER_ID = T.WORKER_REF_ID
                LEFT JOIN Bonus B ON W.WORKER_ID = B.WORKER_REF_ID
                GROUP BY W.WORKER_ID, W.FIRST_NAME, W.LAST_NAME, W.DEPARTMENT, TITLE, W.SALARY, W.JOINING_DATE
                ORDER BY W.WORKER_ID ASC;
            """)
            self.send_json(employees)

        elif parsed.path == '/api/tables':
            workers = db.execute_query("SELECT * FROM Worker")
            bonuses = db.execute_query("SELECT * FROM Bonus")
            titles = db.execute_query("SELECT * FROM Title")
            self.send_json({
                "Worker": workers,
                "Bonus": bonuses,
                "Title": titles
            })

        else:
            # Serve static files (index.html, etc.)
            super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/api/query':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            try:
                payload = json.loads(post_data.decode('utf-8'))
                sql = payload.get('sql', '').strip()
                if not sql:
                    return self.send_json({"error": "SQL query cannot be empty"}, status=400)

                start_time = time.time()
                data = db.execute_query(sql)
                execution_time_ms = round((time.time() - start_time) * 1000, 2)

                self.send_json({
                    "success": True,
                    "sql": sql,
                    "execution_time_ms": execution_time_ms,
                    "row_count": len(data),
                    "data": data
                })
            except Exception as e:
                self.send_json({"success": False, "error": str(e)}, status=400)
        else:
            self.send_error(404, "Endpoint not found")

def run_server():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer((HOST, PORT), DBRequestHandler) as httpd:
        print(f"🚀 Server running on http://{HOST}:{PORT}")
        print(f"📊 Dashboard available at http://{HOST}:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped gracefully.")

if __name__ == '__main__':
    run_server()
