def migrate(cr, version):
    """
    Rename column 'divisions' to 'division_id' in res_partner table
    This fixes the database schema mismatch where the database has 'divisions'
    but the code expects 'division_id'
    """
    cr.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='res_partner' 
        AND column_name='divisions'
    """)
    
    if cr.fetchone():
        # Column exists, rename it
        cr.execute("ALTER TABLE res_partner RENAME COLUMN divisions TO division_id")
        cr.execute("COMMENT ON COLUMN res_partner.division_id IS 'Department (Many2one to contact.division)'")
    
    # Add company_type_locked column if it doesn't exist
    cr.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='res_partner' 
        AND column_name='company_type_locked'
    """)
    
    if not cr.fetchone():
        # Column doesn't exist, add it
        cr.execute("""
            ALTER TABLE res_partner 
            ADD COLUMN company_type_locked BOOLEAN DEFAULT FALSE
        """)
        cr.execute("COMMENT ON COLUMN res_partner.company_type_locked IS 'Company Type Locked'")






