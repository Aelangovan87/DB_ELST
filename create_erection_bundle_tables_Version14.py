import sqlite3

def create_tables(db_path='EDMS.db'):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 1. Erection Lists (ELST)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS erection_lists (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cust_no TEXT NOT NULL,
        elst_no INTEGER NOT NULL,              -- ELST number, incrementing for each project
        project_name TEXT,
        pdf_filename TEXT,                     -- Uploaded PDF for this ELST
        uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        description TEXT,
        UNIQUE(cust_no, elst_no),
        FOREIGN KEY (cust_no) REFERENCES projects(cust_no) ON DELETE CASCADE
    );
    """)

    # 2. Drawings under each ELST
    cur.execute("""
    CREATE TABLE IF NOT EXISTS elst_drawings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        erection_list_id INTEGER NOT NULL,
        drawing_ref TEXT NOT NULL,             -- Drawing reference (e.g. "DRW-12345")
        sheet_no TEXT,                         -- (Optional) Sheet number or other info
        description TEXT,                      -- (Optional) Drawing description
        FOREIGN KEY (erection_list_id) REFERENCES erection_lists(id) ON DELETE CASCADE
    );
    """)

    # 3. Bundles per ELST
    cur.execute("""
    CREATE TABLE IF NOT EXISTS elst_bundles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        erection_list_id INTEGER NOT NULL,
        bundle_no INTEGER NOT NULL,            -- 1, 2, 3...
        bundle_id TEXT,                        -- e.g., BNDL-001
        total_in_bundle INTEGER,               -- Number of drawings in this bundle
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(erection_list_id, bundle_no),
        FOREIGN KEY (erection_list_id) REFERENCES erection_lists(id) ON DELETE CASCADE
    );
    """)

    # 4. Map drawings to bundles
    cur.execute("""
    CREATE TABLE IF NOT EXISTS elst_bundle_drawings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bundle_id INTEGER NOT NULL,
        drawing_id INTEGER NOT NULL,
        FOREIGN KEY (bundle_id) REFERENCES elst_bundles(id) ON DELETE CASCADE,
        FOREIGN KEY (drawing_id) REFERENCES elst_drawings(id) ON DELETE CASCADE
    );
    """)

    # 5. Bundle dispatch details
    cur.execute("""
    CREATE TABLE IF NOT EXISTS elst_bundle_dispatches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bundle_id INTEGER NOT NULL,
        tracking_number TEXT,
        dispatch_address TEXT,
        dispatch_date DATE,
        dispatched_by TEXT,                    -- (Optional) User or staff
        remarks TEXT,
        FOREIGN KEY (bundle_id) REFERENCES elst_bundles(id) ON DELETE CASCADE
    );
    """)

    # 6. Indexes for performance
    cur.execute("CREATE INDEX IF NOT EXISTS idx_erection_lists_custno ON erection_lists(cust_no);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_elst_drawings_erectionlistid ON elst_drawings(erection_list_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_elst_bundles_erectionlistid ON elst_bundles(erection_list_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_elst_bundle_drawings_bundleid ON elst_bundle_drawings(bundle_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_elst_bundle_drawings_drawingid ON elst_bundle_drawings(drawing_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_elst_bundle_dispatches_bundleid ON elst_bundle_dispatches(bundle_id);")

    conn.commit()
    conn.close()
    print("All erection list and bundle tables created successfully.")

if __name__ == "__main__":
    create_tables()