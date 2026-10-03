import unittest
import os
import sqlite3
from db_connection import DatabaseConnection, DB_FILE

class TestDatabaseConnection(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.db = DatabaseConnection('test_company.db')
        cls.db.init_db(force_reset=True)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists('test_company.db'):
            os.remove('test_company.db')

    def test_tables_created(self):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        self.assertIn('Worker', tables)
        self.assertIn('Bonus', tables)
        self.assertIn('Title', tables)
        conn.close()

    def test_record_counts(self):
        workers = self.db.execute_query("SELECT COUNT(*) AS count FROM Worker;")[0]['count']
        bonuses = self.db.execute_query("SELECT COUNT(*) AS count FROM Bonus;")[0]['count']
        titles = self.db.execute_query("SELECT COUNT(*) AS count FROM Title;")[0]['count']

        self.assertEqual(workers, 16)
        self.assertEqual(bonuses, 5)
        self.assertEqual(titles, 8)

    def test_query_q1_average_salary(self):
        res = self.db.execute_query(self.db.get_preset_queries()['Q1']['sql'])
        self.assertTrue(len(res) > 0)
        dept_names = [r['DEPARTMENT'] for r in res]
        self.assertIn('Admin', dept_names)
        self.assertIn('HR', dept_names)
        self.assertIn('Account', dept_names)

    def test_query_q2_worker_count(self):
        res = self.db.execute_query(self.db.get_preset_queries()['Q2']['sql'])
        self.assertEqual(res[0]['DEPARTMENT'], 'Admin')
        self.assertEqual(res[0]['WORKER_COUNT'], 8)

    def test_query_q4_highest_bonus_department(self):
        res = self.db.execute_query(self.db.get_preset_queries()['Q4']['sql'])
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]['DEPARTMENT'], 'HR')
        self.assertEqual(res[0]['TOTAL_BONUS'], 13500)

    def test_custom_query_execution(self):
        res = self.db.execute_query("SELECT * FROM Worker WHERE SALARY > ?", (300000,))
        self.assertTrue(len(res) > 0)
        for row in res:
            self.assertGreater(row['SALARY'], 300000)

if __name__ == '__main__':
    unittest.main()
