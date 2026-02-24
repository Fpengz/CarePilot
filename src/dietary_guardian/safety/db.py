import sqlite3
from typing import List, Tuple


class DrugInteractionDB:
    def __init__(self, db_path: str = "clinical_safety.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Create Medications table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS medications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    common_brands TEXT
                )
            """)
            # Create Contraindications table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contraindications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    med_id INTEGER,
                    restricted_item TEXT NOT NULL,
                    reason TEXT,
                    severity TEXT DEFAULT 'Critical',
                    FOREIGN KEY (med_id) REFERENCES medications(id)
                )
            """)
            self._seed_data(cursor)
            conn.commit()

    def _seed_data(self, cursor):
        # Initial clinical seed data for Singapore context
        meds = [
            ("Warfarin", "Marevan"),
            ("Metformin", "Glucophage"),
            ("Atorvastatin", "Lipitor"),
            ("Amlodipine", "Norvasc"),
        ]
        for name, brand in meds:
            cursor.execute(
                "INSERT OR IGNORE INTO medications (name, common_brands) VALUES (?, ?)",
                (name, brand),
            )

        # Get IDs
        cursor.execute("SELECT id, name FROM medications")
        med_map = {name: id for id, name in cursor.fetchall()}

        contra_data = [
            (
                med_map["Warfarin"],
                "Spinach",
                "High Vitamin K interferes with blood thinning",
                "Critical",
            ),
            (
                med_map["Warfarin"],
                "Kale",
                "High Vitamin K interferes with blood thinning",
                "Critical",
            ),
            (med_map["Warfarin"], "Ginkgo", "Increases bleeding risk", "Critical"),
            (med_map["Metformin"], "Alcohol", "Risk of lactic acidosis", "High"),
            (
                med_map["Atorvastatin"],
                "Grapefruit",
                "Increases drug concentration in blood",
                "Medium",
            ),
        ]
        cursor.executemany(
            """
            INSERT OR IGNORE INTO contraindications (med_id, restricted_item, reason, severity) 
            VALUES (?, ?, ?, ?)
        """,
            contra_data,
        )

    def get_contraindications(self, medication_name: str) -> List[Tuple[str, str, str]]:
        """Returns list of (restricted_item, reason, severity)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT c.restricted_item, c.reason, c.severity
                FROM contraindications c
                JOIN medications m ON c.med_id = m.id
                WHERE m.name = ?
            """,
                (medication_name,),
            )
            return cursor.fetchall()
